# payment/admin.py
from django.contrib import admin
from django.contrib import messages
from .models import Payment
import stripe
from .forms import PaymentReadOnlyForm
from .utils import send_webhook_notification_email




#------------------------------Payment System---------------------------------------------------------------------------------------------


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    # Display all fields in the Payment model, plus some
    # custom columns for user/test info
    list_display = [
        'created_at',
        'id',
        'user_email',
        'test_name',
        'test_result_uuid',
        'test_attempt_number',
        'amount',
        'currency',
        'stripe_payment_intent_id',
        'payment_method',
        'status',
        'refund_status',
        'refund_id',
        'refund_reason',
        'formatted_refund_errors',
        'formatted_error_details',
        'country',
    ]
    readonly_fields = list_display

    form = PaymentReadOnlyForm

    list_filter = ['status', 'refund_status']
    search_fields = [
        'id',
        'user__email',
        'stripe_payment_intent_id',
        'refund_id'
    ]
    actions = ['initiate_refund']

    # Map Stripe's refund status to model choices
    REFUND_STATUS_MAPPING = {
        'pending': 'requested',
        'succeeded': 'succeeded',
        'failed': 'not_refunded',
    }

    # Override formfield_for_foreignkey to remove the "Add another" link
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'test':
            # Disable "Add another" (the green plus icon)
            field.widget.can_add_related = False
            # Optionally disable "Change" or "Delete" links, if applicable
            field.widget.can_change_related = False
            field.widget.can_delete_related = False
        return field
    def has_add_permission(self, request):
        # Disallow adding new Payment objects in the admin
        return False

    def has_change_permission(self, request, obj=None):
        """
        Disallow editing Payment objects manually
        (the initiate_refund action can still programmatically update them).
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Set to True or False depending on whether you want
        to allow deleting Payment objects.
        """
        return True
    @admin.display(description="User Email")
    def user_email(self, obj):
        return obj.user.email


    @admin.display(description="Test Name")
    def test_name(self, obj):
        return obj.test.test_name if obj.test else "N/A"

    @admin.display(description="Test Attempt")
    def test_attempt_number(self, obj):
        return obj.test_result.attempt_number if obj.test_result else "N/A"

    @admin.display(description="Test Result UUID")
    def test_result_uuid(self, obj):
        return obj.test_result.uuid if obj.test_result else "N/A"

    @admin.display(description="Error Details")
    def formatted_error_details(self, obj):
        """
        Returns a readable string of the error details stored in obj.error_details.
        Example format: "Attempt 1: payment_failed - The card was declined, Attempt 2: ...".
        """
        if isinstance(obj.error_details, dict) and obj.error_details:
            # Convert the key-value pairs to a readable format
            return ", ".join([
                f"Attempt {k}: {v}"
                for k, v in obj.error_details.items()
            ])
        return "No Errors"

    @admin.display(description="Refund Errors")
    def formatted_refund_errors(self, obj):
        """
        Returns a readable string of the refund errors stored in obj.refund_error_details.
        Example format: "Attempt 1: refund_failed - Expired card, Attempt 2: ...".
        """
        if isinstance(obj.refund_error_details, dict) and obj.refund_error_details:
            return ", ".join([
                f"Attempt {k}: {v}"
                for k, v in obj.refund_error_details.items()
            ])
        return "No Errors"

    def initiate_refund(self, request, queryset):
        """
        Action to initiate a refund via the Stripe API for selected Payments.
        Includes handling of various scenarios and logs errors to
        refund_error_details.
        """
        for payment in queryset:
            # Check if the Payment is in a valid state for refund
            if payment.status != 'succeeded':
                self.message_user(
                    request,
                    f"Payment {payment.id} is not in a valid state for a refund "
                    f"(current status: '{payment.status}').",
                    level=messages.WARNING
                )
                continue

            # Check if it's already refunded or in the process of refund
            if payment.refund_status != 'not_refunded':
                self.message_user(
                    request,
                    f"Payment {payment.id} is already refunded or in a non-refundable status "
                    f"(current refund_status: '{payment.refund_status}').",
                    level=messages.WARNING
                )
                continue

            try:
                # Initiate the refund using Stripe API
                reason = payment.refund_reason or 'requested_by_customer'
                refund = stripe.Refund.create(
                    payment_intent=payment.stripe_payment_intent_id,
                    reason=reason
                )

                # If no exception is raised, the refund was successfully created
                payment.refund_id = refund['id']
                payment.refund_status = self.REFUND_STATUS_MAPPING.get(refund['status'])
                send_webhook_notification_email(payment, message_type='refund_initiated_admin')

                if refund['status'] == 'succeeded':
                    payment.status = 'refund_succeeded'
                else:
                    payment.status = 'refund_requested'
                # clear any old error messages
                payment.refund_error_details = {}
                payment.save()

                self.message_user(
                    request,
                    f"Refund initiated for Payment {payment.id} with status '{refund['status']}'."
                    f"(Refund ID: {refund['id']}).",
                    level=messages.SUCCESS
                )


            except stripe.error.CardError as e:
                # The card has been declined or a card-specific error occurred
                self.append_refund_error(payment, "Card error", e.error.message)
                self.message_user(
                    request,
                    f"Card error for Payment {payment.id}: {e.error.message}",
                    level=messages.ERROR
                )


            except stripe.error.RateLimitError as e:
                # Too many requests made to the Stripe API too quickly
                self.append_refund_error(payment, "Rate limit error", str(e))
                self.message_user(
                    request,
                    f"Rate limit error for Payment {payment.id}: {str(e)}",
                    level=messages.ERROR
                )


            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                self.append_refund_error(payment, "Invalid request", str(e))
                self.message_user(
                    request,
                    f"Invalid request for Payment {payment.id}: {str(e)}",
                    level=messages.ERROR
                )


            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                self.append_refund_error(payment, "Authentication error", str(e))
                self.message_user(
                    request,
                    f"Authentication error for Payment {payment.id}: {str(e)}",
                    level=messages.ERROR
                )


            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                self.append_refund_error(payment, "API connection error", str(e))
                self.message_user(
                    request,
                    f"API connection error for Payment {payment.id}: {str(e)}",
                    level=messages.ERROR
                )


            except stripe.error.StripeError as e:
                # Catch all other Stripe errors
                self.append_refund_error(payment, "Stripe error", str(e))
                self.message_user(
                    request,
                    f"Stripe error for Payment {payment.id}: {str(e)}",
                    level=messages.ERROR
                )


            except Exception as e:
                # Catch any other unforeseen exceptions
                self.append_refund_error(payment, "Unexpected error", str(e))
                self.message_user(
                    request,
                    f"Unexpected error for Payment {payment.id}: {str(e)}",
                    level=messages.ERROR
                )

    initiate_refund.short_description = 'Initiate Refund for Selected Payments'



def append_refund_error( payment, error_type, error_message):
    """
    Append a new entry to the payment.refund_error_details JSONField.
    Each key is the next attempt number (as a string),
    and the value is '<error_type> - <error_message>'.
    """
    current_errors = payment.refund_error_details or {}
    error_count = len(current_errors) + 1
    combined_error = f"{error_type} - {error_message}"

    current_errors[str(error_count)] = combined_error
    payment.refund_error_details = current_errors
    payment.save()