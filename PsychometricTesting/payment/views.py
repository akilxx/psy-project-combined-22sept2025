# payment/views.py

import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status, generics
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth import get_user_model
from testing.models import TestResult, PsychometricTest

from .models import Payment, StripeEvent, SubscriptionPlan, UserSubscription
from .serializers import (
    PaymentSerializer,
    PaymentCreationResponseSerializer,
    SubscriptionCreateSerializer,
    SubscriptionPlanSerializer,
    UserSubscriptionSerializer,
)
from .subscription_service import (
    create_subscription,
    handle_subscription_webhook_event,
)
from .utils import (
    handle_payment_intent_event,
    handle_refund_event,
    update_payment_intent,
    append_error_details,
    initiate_refund,
    send_webhook_notification_email,
    verify_and_extract_events,
    create_stripe_payment_and_record,
    send_payment_succeeded_rating_email,
)
from django.conf import settings
import stripe
from django.http import JsonResponse
from django.views import View
from drf_spectacular.utils import extend_schema, OpenApiResponse



User = get_user_model()

logger = logging.getLogger(__name__)

#---------------------------------------------Payment System----------------------------------------------------------------



@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request, *args, **kwargs):
        # raw request body (bytes)
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        # 1) Use our helper to verify signature & parse JSON into events_list
        error_dict, events_list = verify_and_extract_events(
            payload, sig_header, endpoint_secret
        )
        if error_dict:
            # The helper found a signature or JSON parse error; return the appropriate response
            return JsonResponse(error_dict, status=400)

        # 2) Loop over each event dict in events_list
        for raw_event in events_list:
            event_id = raw_event.get('id')
            event_type = raw_event.get('type')
            if not event_id or not event_type:
                logger.error(f"Event missing 'id' or 'type': {raw_event}")
                return JsonResponse({'error': 'Event missing id/type'}, status=400)

            logger.info(f"Stripe Webhook received: {event_type}")

            # Deduplication check
            if StripeEvent.objects.filter(event_id=event_id).exists():
                logger.info(f"Duplicate event received: {event_id} ({event_type}). Skipping.")
                # Skip this event, but continue with next
                continue

            # Record the event so we don't process duplicates
            StripeEvent.objects.create(event_id=event_id, event_type=event_type)

            # Extract data
            event_data = raw_event.get('data', {})
            obj = event_data.get('object', {})

            # 3) Dispatch to your existing logic
            if event_type.startswith('payment_intent.'):
                result = handle_payment_intent_event(
                    event_type=event_type,
                    obj=obj,
                    update_payment_intent=update_payment_intent,
                    append_error_details=append_error_details,
                    initiate_refund=initiate_refund,
                    send_webhook_notification_email=send_webhook_notification_email,
                    send_payment_succeeded_rating_email=send_payment_succeeded_rating_email
                )
                if 'error' in result:
                    if result.get('retry', False) is True:
                        return JsonResponse(result, status=400)
                    else:
                        return JsonResponse(result, status=200)

            elif event_type.startswith('refund.'):
                result = handle_refund_event(
                    event_type=event_type,
                    obj=obj,
                    update_payment_intent=update_payment_intent,
                    append_error_details=append_error_details,
                    send_webhook_notification_email=send_webhook_notification_email
                )
                if 'error' in result:
                    if result.get('retry', False) is True:
                        return JsonResponse(result, status=400)
                    else:
                        return JsonResponse(result, status=200)

            elif event_type.startswith('invoice.') or event_type.startswith('customer.subscription'):
                result = handle_subscription_webhook_event(event_type=event_type, data=obj)
                if 'error' in result:
                    logger.warning("Subscription webhook handler reported error: %s", result['error'])
                    return JsonResponse(result, status=400)
            else:
                logger.info(f"Unhandled event type: {event_type}")

        # 4) If we finish the loop without fatal errors, return success
        return JsonResponse({'status': 'success'}, status=200)






@extend_schema(
    request=PaymentSerializer,
    responses={
        201: PaymentCreationResponseSerializer,
        400: OpenApiResponse(description="Bad Request")
    },
    description="Creates a new Stripe PaymentIntent and a corresponding Payment record."
)
class CreatePaymentView(generics.CreateAPIView):
    """
    View for creating a Stripe PaymentIntent, storing payment details,
    and capturing the user's country via GeoIP2.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            payment, client_secret = create_stripe_payment_and_record(request)
            return Response(
                {
                    "payment_id": str(payment.id),
                    "payment_intent": payment.stripe_payment_intent_id,
                    "client_secret": client_secret,  # ← add this
                    "status": payment.status,
                },
                status=status.HTTP_201_CREATED
            )

        except ValueError as ve:
            # Catches missing `test_result` or `amount`
            return Response({'error': str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as pe:
            # Catches permission issues
            return Response({'error': str(pe)}, status=status.HTTP_403_FORBIDDEN)
        except TestResult.DoesNotExist:
            return Response({'error': 'Invalid test result UUID'}, status=status.HTTP_400_BAD_REQUEST)
        except PsychometricTest.DoesNotExist:
            return Response({'error': 'Invalid test ID'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error in create payment: {e}")
            return Response({'error': f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubscriptionPlanListView(generics.ListAPIView):
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]


class SubscriptionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SubscriptionCreateSerializer,
        responses={201: UserSubscriptionSerializer},
        description="Create a subscription for the authenticated user."
    )
    def post(self, request, *args, **kwargs):
        serializer = SubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan: SubscriptionPlan = serializer.validated_data['plan_id']
        payment_method_id = serializer.validated_data.get('payment_method_id') or None

        active_subscription = UserSubscription.objects.filter(
            user=request.user,
            is_active=True,
            status__in=[
                UserSubscription.STATUS_ACTIVE,
                UserSubscription.STATUS_TRIALING,
                UserSubscription.STATUS_INCOMPLETE,
                UserSubscription.STATUS_PAST_DUE,
            ],
        ).first()

        if active_subscription:
            raise ValidationError('You already have an active subscription.')

        try:
            subscription = create_subscription(
                user=request.user,
                plan=plan,
                payment_method_id=payment_method_id,
            )
        except stripe.error.StripeError as exc:
            logger.error("Stripe error while creating subscription: %s", exc)
            raise ValidationError({'stripe': str(exc)})
        except ValueError as exc:
            raise ValidationError(str(exc))

        response_serializer = UserSubscriptionSerializer(subscription)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CurrentSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSubscriptionSerializer},
        description="Retrieve the authenticated user's current subscription."
    )
    def get(self, request, *args, **kwargs):
        subscription = UserSubscription.objects.filter(user=request.user, is_active=True).order_by('-created_at').first()
        if not subscription:
            raise NotFound('You do not have an active subscription.')
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data)