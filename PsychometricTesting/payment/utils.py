# payment/utils.py

import stripe
from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings
import logging
import json
from django.template.loader import render_to_string
from payment.models import Payment
from testing.models import TestResult
from reportgeneration.models import TestReport,ReportTemplate
from django.db import IntegrityError
from geoip2.database import Reader
from rating.models import FeedbackToken



logger = logging.getLogger(__name__)

def create_test_report(payment_obj):
    """
    Creates a TestReport for a succeeded Payment using the associated TestResult
    and ReportTemplate. The TestReport will contain a list of dictionaries with keys:
        - "trait": the trait name
        - "percentile": the percentile value from TestResult
        - "text": the content text from the ContentBlock where the percentile falls
                  between its lower and upper bounds.
    """
    # Ensure payment has an associated test and test result.
    if not payment_obj.test:
        logger.error("Payment %s does not have an associated PsychometricTest.", payment_obj.id)
        return
    if not payment_obj.test_result:
        logger.error("Payment %s does not have an associated TestResult.", payment_obj.id)
        return

    psychometric_test = payment_obj.test
    test_result = payment_obj.test_result

    # Retrieve the ReportTemplate for this PsychometricTest.
    try:
        report_template = psychometric_test.report_template
    except ReportTemplate.DoesNotExist:
        logger.error("No ReportTemplate found for PsychometricTest %s.", psychometric_test.id)
        return

    # Ensure that the test_result.percentiles field is available.
    if not test_result.percentiles:
        logger.error("TestResult.percentiles is empty for Payment %s.", payment_obj.id)
        return

    percentiles = []
    for entry in test_result.percentiles:
        # Add the main trait's total percentile.
        percentiles.append({
            "trait": entry["trait"],
            "percentile": entry["total_percentile"]
        })
        # Add each dimension's percentile.
        for dimension, value in entry.get("dimension_percentiles", {}).items():
            percentiles.append({
                "trait": dimension,
                "percentile": value
            })

    # Get the list of expected traits and dimensions from the PsychometricTest.
    expected_traits = []
    for trait in psychometric_test.traits:
        # Add the trait's name if not already added
        if trait['name'] not in expected_traits:
            expected_traits.append(trait['name'])
        # Add each dimension if not already added
        for dimension in trait.get('dimensions', []):
            if dimension not in expected_traits:
                expected_traits.append(dimension)

    # Build the report entries. Assume that expected_traits is a list of trait names
    report_entries = []
    for trait in expected_traits:
        # Find the percentile value for this trait from test_result.percentiles.
        matching_entry = next((entry for entry in percentiles if entry.get("trait") == trait), None)
        if matching_entry is None:
            logger.warning("No percentile found for trait '%s' in Payment %s.", trait, payment_obj.id)
            continue

        percentile_value = matching_entry.get("percentile")

        # Find the appropriate ContentBlock from ReportTemplate for this trait.
        # The content block should have lower and upper bounds that enclose the percentile_value.
        content = ""
        content_blocks = report_template.content_blocks.filter(trait=trait)
        for block in content_blocks:
            if block.percentile_lower_bound <= percentile_value <= block.percentile_upper_bound:
                content = block.content
                break

        report_entries.append({
            "trait": trait,
            "percentile": percentile_value,
            "text": content
        })

    # Create the TestReport instance.
    test_report = TestReport.objects.create(
        payment=payment_obj,
        report_content=report_entries
    )
    logger.info("TestReport created for Payment %s.", payment_obj.id)
    return test_report


def send_webhook_notification_email(payment_obj, message_type):
    """
    Helper function to send an email notification to the user whenever a webhook event occurs,
    without repeating large blocks of code for each event type.
    """
    if not payment_obj or not payment_obj.user:
        return

    user_email = payment_obj.user.email
    context = {
        'payment_intent_id': payment_obj.stripe_payment_intent_id,
    }

    # Define the subjects and email templates in dictionaries
    subjects = {
        "payment_succeeded": "Confirmation of Successful Payment",
        "payment_failed": "Notification of Payment Failure",
        "refund_initiated": f"Refund Initiated for Payment ID: {payment_obj.stripe_payment_intent_id}",
        "refund_succeeded": "Refund Processed Successfully",
        "refund_failed": f"Refund Processing Update for Payment ID: {payment_obj.stripe_payment_intent_id}",
        "refund_initiated_admin": f"Refund Initiated for Payment ID: {payment_obj.stripe_payment_intent_id}",
    }

    templates = {
        "payment_succeeded": 'emails/payment_succeeded.txt',
        "payment_failed": 'emails/payment_failed.txt',
        "refund_initiated": 'emails/refund_initiated.txt',
        "refund_succeeded": "emails/refund_succeeded.txt",
        "refund_failed": 'emails/refund_failed.txt',
        "refund_initiated_admin": 'emails/refund_initiated_admin.txt',
    }

    # Get the subject and template path for the current message_type
    subject = subjects.get(message_type)
    template_path = templates.get(message_type)

    # If the message_type isn't recognized, just return (or log/handle as needed)
    if not subject or not template_path:
        logger.warning(f"Unhandled or unknown email message_type: {message_type}")
        return

    # Render the email body from the template
    email_body = render_to_string(template_path, context)

    # Send the email in one try/except block
    try:
        send_mail(
            subject=subject,
            from_email=settings.DEFAULT_FROM_EMAIL,
            message=email_body,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info(f"Email sent to {user_email} for event '{message_type}'")
    except Exception as e:
        logger.error(f"Error sending email to {user_email}: {e}")

def send_payment_succeeded_rating_email(payment_obj):
    """
    Sends an HTML email to the user confirming a successful payment,
    including star links for submitting a rating via a GET request.
    The email template 'emails/payment_succeeded.html' uses the 'domain'
    and 'feedback_token' context variables to build proper feedback URLs.
    """
    if not payment_obj or not payment_obj.user:
        return

    user_email = payment_obj.user.email
    # Retrieve domain from settings (set this in your settings, e.g., DOMAIN = "https://yourdomain.com")
    domain = getattr(settings, 'DOMAIN', 'http://localhost:8000')


    # Get or create a one-time feedback token for the payment
    feedback_token_obj, created = FeedbackToken.objects.get_or_create(payment=payment_obj)
    feedback_token = feedback_token_obj.token

    # Prepare the context for the HTML template
    context = {
        'domain': domain,
        'feedback_token': feedback_token,
    }

    subject = "Your Opinion Matters: Rate Us Today"
    template_path = 'emails/payment_succeeded.html'

    # Render the HTML email body using the updated template
    email_body = render_to_string(template_path, context)

    # Send the email using Django's send_mail, with html_message provided
    try:
        send_mail(
            subject=subject,
            from_email=settings.DEFAULT_FROM_EMAIL,
            message="Your email client does not support HTML messages.",
            html_message=email_body,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info(f"Rating email sent to {user_email} for payment succeeded event.")
    except Exception as e:
        logger.error(f"Error sending rating email to {user_email}: {e}")


def initiate_refund(
    payment_obj,
    payment_intent_id,
    update_payment_intent,
    append_error_details,
    reason='requested_by_customer'
):
    """
    Attempts to create a Stripe refund for payment_obj (only one attempt).
    If it fails, marks Payment as requiring manual attention.

    :param payment_obj: Payment instance to update.
    :param payment_intent_id: The Stripe PaymentIntent ID (string/UUID).
    :param update_payment_intent: Function to safely fetch/update the Payment object.
    :param append_error_details: Function to append error info to Payment's JSONField.
    :param reason: The reason for refund (e.g. 'duplicate', 'requested_by_customer').
    """
    try:
        with transaction.atomic():
            refund = stripe.Refund.create(
                payment_intent=payment_obj.stripe_payment_intent_id,
                reason=reason
            )
            # If it didn't raise an error, update Payment
            payment_obj.refund_id = refund['id']
            payment_obj.refund_status = 'requested'
            payment_obj.status = 'refund_requested'
            payment_obj.save()

    except Exception as refund_error:
        logger.error(
            f"Refund error for PaymentIntent {payment_intent_id}: {refund_error}"
        )
        # Re-fetch payment to ensure we have the latest data
        payment_obj = update_payment_intent(payment_intent_id)
        if payment_obj:
            # Mark Payment as needing attention
            payment_obj.refund_status = 'attention_required'
            append_error_details(
                payment_obj,
                'refund_error_details',
                'refund_error',
                str(refund_error)
            )
            payment_obj.save()

# A utility function to fetch/update the Payment model safely
def update_payment_intent(payment_intent_id, payment_method=None, **kwargs):
    try:
        payment_obj = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
        if payment_method is not None:
            payment_obj.payment_method = payment_method
        for field, value in kwargs.items():
            setattr(payment_obj, field, value)
        payment_obj.save()
        return payment_obj
    except Payment.DoesNotExist:
        logger.error(f"Payment with intent ID {payment_intent_id} not found.")
        return None
    except Exception as e:
        logger.error(f"Error updating Payment object: {e}")
        return None

def append_error_details(payment_obj, field_name, error_type, error_message):
    current_errors = getattr(payment_obj, field_name) or {}
    error_count = len(current_errors) + 1
    combined_error = f"{error_type} - {error_message}"
    current_errors[str(error_count)] = combined_error
    setattr(payment_obj, field_name, current_errors)
    payment_obj.save()




def handle_refund_event(
    event_type,
    obj,
    update_payment_intent,
    append_error_details,
    send_webhook_notification_email
):
    """
    Handles all refund.* events. Returns a dict that may include:
      {
        'error': 'Some error message',
        'retry': True/False
      }


    :param event_type: The string event type (e.g., 'refund.created', 'refund.updated').
    :param obj: The Stripe 'object' dict from the event payload (refund object).
    :param update_payment_intent: A reference to your function that updates Payment objects.
    :param append_error_details: A reference to your function that appends error details in JSON.
    :param send_webhook_notification_email: A reference to your function that sends email notifications.
    """
    payment_obj = None
    refund_obj = obj
    payment_intent_id = refund_obj.get('payment_intent')
    new_refund_status = refund_obj.get('status')  # e.g. 'pending', 'succeeded', 'failed'

    payment_obj = Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
    if not payment_obj:
        logger.error(f"No Payment found for PaymentIntent {payment_intent_id}")
        return {'error': 'No payment found', 'retry': False}

    current_status = payment_obj.refund_status or ''
    if new_refund_status == 'succeeded' and current_status != 'succeeded':
        updated_payment = update_payment_intent(
            payment_intent_id,
            status='refund_succeeded',
            refund_status='succeeded',
            refund_id=refund_obj.get('id')
        )
        if updated_payment:
            send_webhook_notification_email(updated_payment, message_type='refund_succeeded')
            logger.info(f"Refund succeeded for {payment_intent_id}")

    elif new_refund_status == 'failed' and current_status != 'attention_required':
        updated_payment = update_payment_intent(
            payment_intent_id,
            status='refund_requested',
            refund_status='attention_required',
            refund_id=refund_obj.get('id')
        )
        if updated_payment:
            append_error_details(
                updated_payment,
                'refund_error_details',
                'refund_failed',
                refund_obj.get('failure_reason', '')
            )
            send_webhook_notification_email(updated_payment, message_type='refund_failed')
            logger.warning(f"Refund {refund_obj.get('id')} failed for {payment_intent_id}")

    elif new_refund_status == 'pending' and current_status != 'requested':
        updated_payment = update_payment_intent(
            payment_intent_id,
            status='refund_requested',
            refund_status='requested',
            refund_id=refund_obj.get('id')
        )
        if updated_payment:
            logger.info(f"Refund {refund_obj.get('id')} has been requested for {payment_intent_id}")

    else:
        logger.info(f"Unhandled or unchanged refund status '{new_refund_status}' for Payment {payment_intent_id}.")

    return {}


def handle_integrity_conflict(payment_obj, reason, error):
    """
    Handles IntegrityError by setting Payment to refund_requested,
    appending error details, and initiating a refund if needed.
    """
    try:
        updated_obj = update_payment_intent(
            payment_obj.stripe_payment_intent_id,
            status='refund_requested',
            refund_status='requested',
            refund_reason=reason
        )
        if updated_obj:
            append_error_details(updated_obj, 'error_details', 'IntegrityError', str(error))
            send_webhook_notification_email(updated_obj, message_type='refund_initiated')

        initiate_refund(
            payment_obj=updated_obj,
            payment_intent_id=payment_obj.stripe_payment_intent_id,
            update_payment_intent=update_payment_intent,
            append_error_details=append_error_details,
            reason=reason
        )
    except Exception as refund_error:
        logger.error(
            f"Error refunding Payment {payment_obj.stripe_payment_intent_id} after IntegrityError: {refund_error}"
        )
        if payment_obj:
            append_error_details(
                payment_obj,
                'refund_error_details',
                'refund_error',
                str(refund_error)
            )
    return {}

def handle_payment_intent_event(
    event_type,
    obj,
    update_payment_intent,
    append_error_details,
    initiate_refund,
    send_webhook_notification_email,
    send_payment_succeeded_rating_email
):
    """
    Handles all payment_intent.* events. Returns a dict that may include:
      {
        'error': 'Some error message',
        'retry': True/False
      }
    If 'error' is present:
      - 'retry': True means we want a non-2xx response so Stripe retries
      - 'retry': False means we’ll return 200 so Stripe does NOT retry
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Helper Functions
    # ─────────────────────────────────────────────────────────────────────────

    def mark_payment_as_succeeded(payment_obj, payment_method=None):
        """
        Helper to set a Payment's status to 'succeeded', with minimal try/except.
        """
        logger.debug("Inside mark_payment_as_succeeded with payment %s, old status=%s",
                     payment_obj.id, payment_obj.status)
        try:
            with transaction.atomic():
                if payment_obj.status != 'succeeded':
                    payment_obj.status = 'succeeded'
                    if payment_method:
                        payment_obj.payment_method = payment_method
                    payment_obj.save()

                    send_webhook_notification_email(payment_obj, message_type='payment_succeeded')
                    send_payment_succeeded_rating_email(payment_obj)

                    # Create the TestReport using TestResult and ReportTemplate.
                    create_test_report(payment_obj)

                    logger.info(f"Payment {payment_obj.stripe_payment_intent_id} marked as succeeded.")
        except IntegrityError as e:
            logger.error(f"IntegrityError while marking Payment {payment_obj.stripe_payment_intent_id} succeeded: {e}")
            handle_integrity_conflict(payment_obj, reason='duplicate', error=e)
            return {
                'error': f"IntegrityError marking payment succeeded: {str(e)}",
                'retry': False
            }
        return {}



    def handle_duplicate_payment(payment_obj, payment_intent_id):
        """
        If we detect a duplicate payment scenario, set 'refund_requested' and initiate a refund.
        """
        if (payment_obj.refund_status not in ['requested', 'succeeded', 'attention_required']
                and payment_obj.status not in ['refund_requested', 'refund_succeeded']):
            try:
                updated_obj = update_payment_intent(
                    payment_intent_id,
                    status='refund_requested',
                    refund_status='requested',
                    refund_reason='duplicate',
                )
                if updated_obj:
                    initiate_refund(
                        payment_obj=updated_obj,
                        payment_intent_id=payment_intent_id,
                        update_payment_intent=update_payment_intent,
                        append_error_details=append_error_details,
                        reason='duplicate'
                    )
                    send_webhook_notification_email(updated_obj, message_type='refund_initiated')
                    logger.info(f"Duplicate payment {payment_intent_id}: refund requested.")
            except IntegrityError as e:
                logger.error(f"IntegrityError while handling duplicate Payment {payment_intent_id}: {e}")
                # Possibly add logic if a further conflict arises
                return {
                    'error': f"IntegrityError with duplicate Payment: {str(e)}",
                    'retry': False
                }
        return {}

    # ─────────────────────────────────────────────────────────────────────────
    # Main Logic
    # ─────────────────────────────────────────────────────────────────────────

    payment_intent_id = obj.get('id')
    new_stripe_status = obj.get('status')
    payment_method = obj.get('payment_method')
    test_result_id = obj.get('metadata', {}).get('test_result_id')

    if not test_result_id:
        logger.error(f"PaymentIntent {payment_intent_id} has no test_result_id.")
        return {'error': 'Missing test_result_id', 'retry': False}

    # Fetch the Payment from DB
    payment_obj = Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
    if not payment_obj:
        logger.error(f"No Payment found for PaymentIntent {payment_intent_id}")
        return {'error': 'Payment not found', 'retry': False}


    old_status = payment_obj.status

    # ─────────────────────────────────────────────────────────────────────────
    # 1) PaymentIntent Succeeded
    # ─────────────────────────────────────────────────────────────────────────
    if new_stripe_status == 'succeeded':
        existing_payment = Payment.objects.filter(
            test_result_id=test_result_id,
            status='succeeded'
        ).order_by('created_at').first()

        if old_status != 'succeeded':
            if existing_payment:
                # If this PaymentIntent is the same one that already succeeded
                if existing_payment.stripe_payment_intent_id == payment_intent_id:
                    result_dict = mark_payment_as_succeeded(payment_obj, payment_method=payment_method)
                    if 'error' in result_dict:
                        return result_dict
                else:
                    # It's a genuine duplicate scenario
                    result_dict = handle_duplicate_payment(payment_obj, payment_intent_id)
                    if 'error' in result_dict:
                        return result_dict
            else:
                # No existing succeeded payment => mark this one as succeeded
                result_dict = mark_payment_as_succeeded(payment_obj, payment_method=payment_method)
                if 'error' in result_dict:
                    return result_dict
        else:
            logger.info(f"Payment {payment_intent_id} is already succeeded; skipping.")

    # ─────────────────────────────────────────────────────────────────────────
    # 2) PaymentIntent Requires Payment Method => Payment Failed
    # ─────────────────────────────────────────────────────────────────────────
    elif new_stripe_status == 'requires_payment_method' and event_type == 'payment_intent.payment_failed':
        if old_status != 'failed':
            updated_obj = update_payment_intent(payment_intent_id, payment_method=payment_method,  status='failed')
            if updated_obj:
                last_payment_error = obj.get('last_payment_error', {})
                error_message = last_payment_error.get('message', 'Unknown payment failure')

                append_error_details(updated_obj, 'error_details', 'payment_failed', error_message)
                send_webhook_notification_email(updated_obj, message_type='payment_failed')
                logger.info(f"Payment {payment_intent_id} marked as failed.")
        else:
            logger.info(f"Payment {payment_intent_id} already marked as failed; skipping.")

    # ─────────────────────────────────────────────────────────────────────────
    # 3) PaymentIntent Canceled
    # ─────────────────────────────────────────────────────────────────────────
    elif new_stripe_status == 'canceled':
        if old_status != 'canceled':
            updated_obj = update_payment_intent(payment_intent_id, payment_method=payment_method,  status='canceled')
            if updated_obj:
                cancellation_reason = obj.get('cancellation_reason', 'No reason provided')
                append_error_details(
                    updated_obj,
                    'error_details',
                    'payment_canceled',
                    cancellation_reason
                )
            logger.info(f"Payment {payment_intent_id} canceled.")
        else:
            logger.info(f"Payment {payment_intent_id} already canceled; skipping.")

    # ─────────────────────────────────────────────────────────────────────────
    # 4) PaymentIntent Requires Action
    # ─────────────────────────────────────────────────────────────────────────
    elif new_stripe_status == 'requires_action':
        if old_status != 'requires_action':
            logger.info(f"PaymentIntent {payment_intent_id} requires additional user action.")
            updated_obj = update_payment_intent(payment_intent_id, payment_method=payment_method,  status='requires_action')
            if updated_obj:
                logger.info(f"Marked Payment {payment_intent_id} as awaiting user action.")
        else:
            logger.info(f"Payment {payment_intent_id} is already in a final state; skipping requires_action.")

    # ─────────────────────────────────────────────────────────────────────────
    # 5) PaymentIntent Processing
    # ─────────────────────────────────────────────────────────────────────────
    elif new_stripe_status == 'processing':
        if old_status != 'processing':
            logger.info(f"PaymentIntent {payment_intent_id} is processing.")
            updated_obj = update_payment_intent(payment_intent_id, payment_method=payment_method,  status='processing')
            if updated_obj:
                logger.info(f"Marked Payment {payment_intent_id} as pending/processing locally.")
        else:
            logger.info(f"Payment {payment_intent_id} in processing, but local status is final; skipping.")

    # ─────────────────────────────────────────────────────────────────────────
    # 6) Default / Unhandled PaymentIntent States
    # ─────────────────────────────────────────────────────────────────────────
    else:
        logger.info(f"Unhandled payment_intent status '{new_stripe_status}' for ID {payment_intent_id}.")

    return {}


def verify_and_extract_events(payload, sig_header, endpoint_secret):
    """
    Helper function to:
      1) Verify the Stripe signature against the raw payload once.
      2) Parse the JSON body.
      3) Return either a list of event dicts or an error dict.

    :param payload: The raw request body (bytes).
    :param sig_header: The signature header from Stripe.
    :param endpoint_secret: Your STRIPE_WEBHOOK_SECRET.
    :return: (error_dict, events_list)
      - error_dict is either None or a dict like {'error': 'message'}.
      - events_list is None if there's an error, otherwise a list of raw event dicts.
    """

    # Step A: Verify the entire raw payload once
    try:
        stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info("Stripe signature verified successfully for the entire request body.")
    except ValueError as e:
        logger.error(f"Invalid payload (not valid JSON) during signature check: {e}")
        return {'error': 'Invalid JSON payload'}, None
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return {'error': 'Invalid signature'}, None

    # Step B: Parse JSON after successful signature verification
    try:
        possible_events = json.loads(payload)
        if isinstance(possible_events, dict):
            events_list = [possible_events]  # single event
        else:
            events_list = possible_events  # multiple events
    except ValueError as e:
        logger.error(f"Could not parse JSON even after signature verification: {e}")
        return {'error': 'Could not parse JSON'}, None

    # If everything is good, return (None, events_list).
    return None, events_list


@transaction.atomic
def create_stripe_payment_and_record(request) -> Payment:
    """
    1. Validates fields
    2. Geo-IP lookup
    3. Creates Stripe PaymentIntent (unconfirmed unless PM supplied)
    4. Creates & returns local Payment record
    """
    # ------------------------------------------------------------
    # 1. Extract & validate input
    test_result_id        = request.data.get("test_result")
    amount_dollars        = request.data.get("amount")
    currency              = request.data.get("currency", "usd")
    payment_method        = request.data.get("payment_method")          # optional
    payment_method_types  = request.data.get("payment_method_types", [])# optional

    if not test_result_id:
        raise ValueError("test_result field is required.")
    if not amount_dollars:
        raise ValueError("amount field is required.")

    test_result = TestResult.objects.get(uuid=test_result_id)
    if test_result.user != request.user:
        raise PermissionError("You do not have permission for this test result.")

    # ------------------------------------------------------------
    # 2. Geo-IP country lookup (same as before)
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    user_ip = (forwarded_for.split(",")[0].strip() if forwarded_for
               else request.META.get("REMOTE_ADDR", "127.0.0.1"))
    try:
        geoip_db_path = settings.GEOIP_PATH / "GeoLite2-Country.mmdb"
        with Reader(str(geoip_db_path)) as reader:
            country_name = reader.country(user_ip).country.name or ""
    except Exception as geo_error:
        logger.warning(f"GeoIP lookup failed for IP {user_ip}: {geo_error}")
        country_name = ""

    # ------------------------------------------------------------
    # 3. Build PaymentIntent params
    cents = int(float(amount_dollars) * 100)
    payment_intent_data = {
        "amount": cents,
        "currency": currency,
        "metadata": {
            "user_email": request.user.email,
            "test_name": str(test_result.test.test_name or ""),
            "test_result_id": str(test_result.uuid),
            "country": country_name,
        },
    }

    if payment_method and payment_method_types:
        # Front-end provided a ready PaymentMethod → confirm server-side
        payment_intent_data["payment_method"] = payment_method
        payment_intent_data["payment_method_types"] = payment_method_types
        payment_intent_data["confirmation_method"] = "automatic"
        payment_intent_data["confirm"] = True
    else:
        # Let Stripe decide PM types; front-end will confirm later
        payment_intent_data["automatic_payment_methods"] = {
            "enabled": True,
            "allow_redirects": "never",
        }
        # do NOT set "confirm": True here

    # 4. Create PaymentIntent
    payment_intent = stripe.PaymentIntent.create(**payment_intent_data)

    # ------------------------------------------------------------
    # 5. Local DB record
    payment = Payment.objects.create(
        user       = request.user,
        amount     = amount_dollars,
        currency   = currency,
        stripe_payment_intent_id = payment_intent.id,
        payment_method           = payment_intent.get("payment_method"),
        status                   = payment_intent.status,
        test        = test_result.test,
        test_result = test_result,
        country     = country_name,
    )

    if payment.status == "succeeded":
        send_webhook_notification_email(payment, message_type="payment_succeeded")
        send_payment_succeeded_rating_email(payment)
        create_test_report(payment)

    return payment, payment_intent.client_secret