# payment/tests.py
from django.conf import settings
import unittest
from django.test import TestCase, Client
from django.test import TransactionTestCase
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
import uuid
from rest_framework.test import APIClient, APITestCase
import concurrent.futures
from unittest.mock import patch
import json
import jsonref
from .models import Payment, StripeEvent, SubscriptionPlan, UserSubscription
from testing.models import PsychometricTest, TestResult
from .subscription_service import consume_allowance, subscription_balance
from .utils import handle_integrity_conflict
from drf_spectacular.generators import SchemaGenerator
from jsonschema import validate as jsonschema_validate, ValidationError as JSONSchemaValidationError


User = get_user_model()




# #----------------------------------------------------Payment Test-------------------------------------------------------------
#
#
# class AdvancedPaymentTests(APITestCase):
#     """
#     These tests cover scenarios not easily reproducible via manual testing for Create Payment View:
#       - Concurrency / race conditions
#       - Network failures / timeouts
#     """
#     def setUp(self):
#         self.client = APIClient()
#
#         # Create a user and authenticate
#         self.user = User.objects.create_user(email='test@example.com')
#         self.client.force_authenticate(user=self.user)
#
#         # Create a psychometric test and a corresponding test result
#         self.psych_test = PsychometricTest.objects.create( test_name='Concurrency Test',
#                                                            questions=[{'question number': 1, 'text': 'Example?', 'scale': 'Scale1', 'trait': 'Trait1'}],
#                                                            options=['Option A', 'Option B'],
#                                                            traits=['Trait1'])
#         self.test_result = TestResult.objects.create(
#             user=self.user,
#             test=self.psych_test
#         )
#
#         self.create_payment_url = reverse('payment:create-payment')
#
#     @unittest.skipIf('sqlite3' in settings.DATABASES['default']['ENGINE'],
#                      'Concurrency test is skipped under SQLite.')
#     @patch('stripe.PaymentIntent.create')
#     def test_create_payment_concurrently(self, mock_stripe_intent_create):
#         """
#         Test scenario where multiple concurrent requests are made to create a Payment
#         for the same test_result. This is difficult to do manually.
#         We expect that each request will generate its own Payment record unless
#         your code explicitly prevents duplicates.
#         """
#
#         # Simulate Stripe's PaymentIntent response
#         # We'll generate a unique ID for each call to mimic distinct PaymentIntents
#         def side_effect(*args, **kwargs):
#             return {
#                 'id': f'pi_concurrency_{uuid.uuid4().hex[:8]}',
#                 'status': 'requires_payment_method',
#                 'payment_method': None
#             }
#         mock_stripe_intent_create.side_effect = side_effect
#
#         request_data = {
#             'test_result': str(self.test_result.uuid),
#             'amount': 50.00
#         }
#
#         # We'll fire off multiple requests in parallel
#         def create_payment_request():
#             return self.client.post(self.create_payment_url, request_data, format='json')
#
#         # Number of concurrent requests
#         num_requests = 5
#         results = []
#
#         with concurrent.futures.ThreadPoolExecutor() as executor:
#             future_calls = [executor.submit(create_payment_request) for _ in range(num_requests)]
#             for future in concurrent.futures.as_completed(future_calls):
#                 results.append(future.result())
#
#         # Analyze outcomes
#         self.assertEqual(len(results), num_requests, "We should have as many responses as requests.")
#
#         # Count how many were successful vs. any possible concurrency error
#         success_responses = [r for r in results if r.status_code == status.HTTP_201_CREATED]
#         self.assertEqual(len(success_responses), num_requests,
#                          f"Expected all {num_requests} requests to succeed in this example.")
#
#         # Verify how many Payment objects were actually created
#         payments = Payment.objects.filter(test_result=self.test_result)
#         self.assertEqual(payments.count(), num_requests,
#                          "If concurrency is not restricted, each request should create a separate Payment.")
#
#     @patch('stripe.PaymentIntent.create')
#     def test_create_payment_network_failure(self, mock_stripe_intent_create):
#         """
#         Simulate a network failure (timeout or unreachable Stripe) that can't be
#         reliably tested by hand.
#         """
#         mock_stripe_intent_create.side_effect = Exception("Network error: Stripe unreachable")
#
#         data = {
#             'test_result': str(self.test_result.uuid),
#             'amount': 49.99
#         }
#         response = self.client.post(self.create_payment_url, data, format='json')
#
#         # Verify we get a 400 or 500-level response indicating the error
#         self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR])
#
#         # Confirm the response body references our simulated exception
#         self.assertIn('error', response.data)
#         self.assertIn('Stripe unreachable', response.data['error'])
#
#         # Ensure no Payment was created in the DB
#         self.assertFalse(Payment.objects.exists())
#
# # ---------------------------------------------------------------Webhook Tests--------------------------------------------------------------------------
# class TestStripeWebhookView(TransactionTestCase):
#     """
#     Example test class using TransactionTestCase so that
#     any IntegrityError encountered won't poison the entire
#     transaction for subsequent partial commits.
#     """
#
#     def setUp(self):
#         """
#         Instead of setUpTestData, we'll create fresh database objects here.
#         This runs before every test method, ensuring each test is isolated.
#         """
#         self.client = Client()
#
#         # Create a User
#         self.user = User.objects.create(
#             email="test@example.com"
#         )
#
#         # Create a PsychometricTest
#         self.some_test = PsychometricTest.objects.create(
#             test_name='Some Test',
#             questions=[{'question number': 1, 'text': 'Example?', 'scale': 'Scale1', 'trait': 'Trait1'}],
#             options=['Option A', 'Option B'],
#             traits=['Trait1']
#         )
#
#         # Create a TestResult
#         self.test_result = TestResult.objects.create(
#             user=self.user,
#             test=self.some_test
#         )
#
#         # Create a Payment to reuse in tests
#         self.payment = Payment.objects.create(
#             user=self.user,
#             amount=100,
#             currency='usd',
#             stripe_payment_intent_id='pi_existing',
#             status='pending',
#             test_result=self.test_result
#         )
#
#         # Store the webhook URL for repeated use
#         self.webhook_url = reverse('payment:stripe-webhook')
#
#     def post_webhook(self, payload, signature='valid_signature'):
#         """
#         Helper to simulate a POST request to your webhook, optionally with a signature.
#         """
#         return self.client.post(
#             self.webhook_url,
#             data=json.dumps(payload),
#             content_type='application/json',
#             **{'HTTP_STRIPE_SIGNATURE': signature}
#         )
#
#     def mock_stripe_event(self, mock_construct_event, success=True):
#         """
#         Utility to mock Stripe’s construct_event, controlling
#         whether the signature verification passes or fails.
#         """
#         if success:
#             # Simulate a successful signature verification
#             mock_construct_event.return_value = True
#         else:
#             # Raise an error to simulate invalid signature
#             from stripe.error import SignatureVerificationError
#             mock_construct_event.side_effect = SignatureVerificationError(
#                 message="Invalid signature",
#                 sig_header="fake_header",
#                 http_body=""
#             )
#
#     # --------------------------------------------------
#     # 1A. Invalid Signature
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_invalid_signature(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=False)
#
#         payload = {"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_test"}}}
#         response = self.post_webhook(payload, signature="invalid_signature")
#
#         self.assertEqual(response.status_code, 400)
#         self.assertIn("Invalid signature", response.content.decode())
#         self.assertEqual(StripeEvent.objects.count(), 0)
#
#     # --------------------------------------------------
#     # 1B. Invalid JSON Payload
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_invalid_json_payload(self, mock_construct_event):
#         """
#         If the payload isn't valid JSON, your code should return an error before it tries to parse JSON.
#         """
#         self.mock_stripe_event(mock_construct_event, success=True)
#         # Send an invalid JSON string
#         invalid_json = "not valid json"
#
#         response = self.client.post(
#             self.webhook_url,
#             data=invalid_json,
#             content_type='application/json',
#             HTTP_STRIPE_SIGNATURE='valid_signature'
#         )
#
#         self.assertEqual(response.status_code, 400)
#         self.assertIn("Could not parse JSON", response.content.decode())
#         self.assertEqual(StripeEvent.objects.count(), 0)
#
#     # --------------------------------------------------
#     # 1C. Valid Multiple Events in a Single Payload
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_multiple_events_single_payload(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#         payload = [
#             {
#                 "id": "evt_1",
#                 "type": "payment_intent.succeeded",
#                 "data": {"object": {"id": "pi_existing", "metadata": {"test_result_id": str(self.test_result.uuid)}, "status": "succeeded"}}
#             },
#             {
#                 "id": "evt_2",
#                 "type": "payment_intent.payment_failed",
#                 "data": {"object": {"id": "pi_existing", "metadata": {"test_result_id": str(self.test_result.uuid)}, "status": "requires_payment_method"}}
#             }
#         ]
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#
#         # Two events processed => 2 StripeEvent records
#         self.assertEqual(StripeEvent.objects.count(), 2)
#         # Payment should end up with 'succeeded' from the first event.
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, 'failed')
#
#     # --------------------------------------------------
#     # 2A. Re-Sending the Same Event (Duplicate)
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_duplicate_event(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         # First event
#         payload_1 = {
#             "id": "evt_duplicate",
#             "type": "payment_intent.succeeded",
#             "data": {"object": {
#                 "id": "pi_existing",
#                 "metadata": {"test_result_id": str(self.test_result.uuid)},
#                 "status": "succeeded"
#             }}
#         }
#         response_1 = self.post_webhook(payload_1)
#         self.assertEqual(response_1.status_code, 200)
#         self.assertEqual(StripeEvent.objects.count(), 1)
#
#         # Send the same event again
#         response_2 = self.post_webhook(payload_1)
#         self.assertEqual(response_2.status_code, 200)
#         self.assertEqual(StripeEvent.objects.count(), 1, "Still only one event recorded - deduped.")
#
#     # --------------------------------------------------
#     # 3A. payment_intent.succeeded
#     #  -> 3A.2: Existing Payment with status != succeeded
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_payment_intent_succeeded_existing_payment(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#         # Our setUpTestData Payment is pi_existing with status='pending'
#         payload = {
#             "id": "evt_pi_succeeded",
#             "type": "payment_intent.succeeded",
#             "data": {
#                 "object": {
#                     "id": "pi_existing",
#                     "status": "succeeded",
#                     "metadata": {"test_result_id": str(self.test_result.uuid)},
#                     "payment_method": "pm_card_visa"
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(StripeEvent.objects.count(), 1)
#
#         # Payment updated
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "succeeded")
#         self.assertEqual(self.payment.payment_method, "pm_card_visa")
#
#     # --------------------------------------------------
#     # 3B. payment_intent.payment_failed => requires_payment_method
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_payment_intent_payment_failed(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         # Payment is currently 'pending'
#         payload = {
#             "id": "evt_pi_failed",
#             "type": "payment_intent.payment_failed",
#             "data": {
#                 "object": {
#                     "id": "pi_existing",
#                     "status": "requires_payment_method",
#                     "metadata": {"test_result_id": str(self.test_result.uuid)},
#                     "last_payment_error": {
#                         "message": "Card was declined"
#                     }
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(StripeEvent.objects.count(), 1)
#
#         # Payment now 'failed'
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "failed")
#         self.assertIn("Card was declined", str(self.payment.error_details))
#
#     # --------------------------------------------------
#     # 3C. payment_intent.canceled
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_payment_intent_canceled(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         # Payment is currently 'pending'
#         payload = {
#             "id": "evt_pi_canceled",
#             "type": "payment_intent.canceled",
#             "data": {
#                 "object": {
#                     "id": "pi_existing",
#                     "status": "canceled",
#                     "metadata": {"test_result_id": str(self.test_result.uuid)},
#                     "cancellation_reason": "automatic"
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "canceled")
#         self.assertIn("payment_canceled - automatic", self.payment.error_details.values())
#
#     # --------------------------------------------------
#     # 3D. payment_intent.processing
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_payment_intent_processing(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         payload = {
#             "id": "evt_pi_processing",
#             "type": "payment_intent.processing",
#             "data": {
#                 "object": {
#                     "id": "pi_existing",
#                     "status": "processing",
#                     "metadata": {"test_result_id": str(self.test_result.uuid)}
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "processing")
#
#     # --------------------------------------------------
#     # 3E. payment_intent.requires_action
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_payment_intent_requires_action(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         payload = {
#             "id": "evt_pi_requires_action",
#             "type": "payment_intent.requires_action",
#             "data": {
#                 "object": {
#                     "id": "pi_existing",
#                     "status": "requires_action",
#                     "metadata": {"test_result_id": str(self.test_result.uuid)}
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "requires_action")
#
#     # --------------------------------------------------
#     # 3F. Unhandled PaymentIntent State
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_unhandled_payment_intent_state(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         payload = {
#             "id": "evt_pi_unhandled",
#             "type": "payment_intent.something_new",
#             "data": {
#                 "object": {
#                     "id": "pi_existing",
#                     "status": "cool_state",
#                     "metadata": {"test_result_id": str(self.test_result.uuid)}
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         # Payment remains 'pending'
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "pending")
#
#     # --------------------------------------------------
#     # 4A. refund.created => typically 'pending'
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_refund_created_pending(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#         # Payment might be 'refund_requested'
#         self.payment.status = 'refund_requested'
#         self.payment.refund_status = 'not_refunded'
#         self.payment.save()
#
#         payload = {
#             "id": "evt_refund_created",
#             "type": "refund.created",
#             "data": {
#                 "object": {
#                     "id": "re_123",
#                     "status": "pending",
#                     "payment_intent": "pi_existing"
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(StripeEvent.objects.count(), 1)
#
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "refund_requested")
#         self.assertEqual(self.payment.refund_status, "requested")
#
#     # --------------------------------------------------
#     # 4B. refund.succeeded
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_refund_succeeded(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#         self.payment.status = 'refund_requested'
#         self.payment.refund_status = 'requested'
#         self.payment.save()
#
#         payload = {
#             "id": "evt_refund_succeeded",
#             "type": "refund.succeeded",
#             "data": {
#                 "object": {
#                     "id": "re_123",
#                     "status": "succeeded",
#                     "payment_intent": "pi_existing"
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "refund_succeeded")
#         self.assertEqual(self.payment.refund_status, "succeeded")
#         self.assertEqual(self.payment.refund_id, "re_123")
#
#     # --------------------------------------------------
#     # 4C. refund.failed
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_refund_failed(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#         self.payment.status = 'refund_requested'
#         self.payment.refund_status = 'requested'
#         self.payment.save()
#
#         payload = {
#             "id": "evt_refund_failed",
#             "type": "refund.failed",
#             "data": {
#                 "object": {
#                     "id": "re_456",
#                     "status": "failed",
#                     "failure_reason": "lost_or_stolen_card",
#                     "payment_intent": "pi_existing"
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "refund_requested")
#         self.assertEqual(self.payment.refund_status, "attention_required")
#         self.assertIn("lost_or_stolen_card", str(self.payment.refund_error_details))
#
#     # --------------------------------------------------
#     # 4D. refund.updated => can also carry 'pending', 'succeeded', 'failed'
#     #     We'll treat it similarly, just show one example
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_refund_updated_pending(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#         # Payment might be 'refund_requested'
#         self.payment.status = 'refund_requested'
#         self.payment.refund_status = 'not_refunded'
#         self.payment.save()
#
#         payload = {
#             "id": "evt_refund_updated",
#             "type": "refund.updated",
#             "data": {
#                 "object": {
#                     "id": "re_999",
#                     "status": "pending",
#                     "payment_intent": "pi_existing"
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, "refund_requested")
#         self.assertEqual(self.payment.refund_status, "requested")
#         self.assertEqual(self.payment.refund_id, "re_999")
#
#     # --------------------------------------------------
#     # 4E. No Matching Payment for refund.*
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_refund_no_matching_payment(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         payload = {
#             "id": "evt_refund_no_payment",
#             "type": "refund.succeeded",
#             "data": {
#                 "object": {
#                     "id": "re_123",
#                     "status": "succeeded",
#                     "payment_intent": "pi_NOT_EXIST"
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.assertIn("No payment found", response.content.decode())
#
#     # --------------------------------------------------
#     # 5A. Unhandled Event Type
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_unhandled_event_type(self, mock_construct_event):
#         """
#         Test scenario: The request body contains an unhandled event type.
#         We expect the webhook to log the unhandled event and return a success response.
#         """
#         # Mock the Stripe signature verification to pass
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         # Prepare a payload with an unhandled event type
#         payload = {
#             "id": "evt_unhandled",
#             "type": "charge.dispute.created",
#             "data": {"object": {}}
#         }
#
#         # Post the JSON payload to our webhook endpoint
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#
#         # Verify that the event was recorded in StripeEvent
#         stripe_event = StripeEvent.objects.get(event_id="evt_unhandled")
#         self.assertEqual(stripe_event.event_type, "charge.dispute.created")
#
#         # Optionally, ensure that the Payment status remains unchanged
#         self.payment.refresh_from_db()
#         self.assertEqual(self.payment.status, 'pending')  # or the initial status you set
#
#
#
#
#
#
#     # --------------------------------------------------
#     # 6A. IntegrityError in mark_payment_as_succeeded
#     # --------------------------------------------------
#     # REMOVED
#
#
#     # --------------------------------------------------
#     # 6B. Refund Creation Failure in initiate_refund
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     @patch('stripe.Refund.create', side_effect=Exception("Refund creation failed"))
#     def test_refund_creation_failure(self, mock_refund_create, mock_construct_event):
#         """
#         Scenario: trigger a refund due to a 'duplicate' payment -> but refund creation fails.
#         """
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         # Make the payment appear as a "duplicate" scenario:
#         # We'll forcibly pass another Payment with same test_result_id that is succeeded.
#         Payment.objects.create(
#             user=self.user,
#             amount=50,
#             currency='usd',
#             stripe_payment_intent_id='pi_another_succeeded',
#             status='succeeded',
#             test_result=self.test_result
#         )
#
#         payload = {
#             "id": "evt_pi_succeeded_duplicate",
#             "type": "payment_intent.succeeded",
#             "data": {
#                 "object": {
#                     "id": "pi_existing",  # The second one "duplicate"
#                     "status": "succeeded",
#                     "metadata": {"test_result_id": str(self.test_result.uuid)}
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.payment.refresh_from_db()
#         # Because the actual refund call failed, Payment should be in 'attention_required'
#         self.assertEqual(self.payment.refund_status, 'attention_required')
#         self.assertIn("refund_error", str(self.payment.refund_error_details))
#
#     # --------------------------------------------------
#     # 6C. Missing test_result_id in PaymentIntent
#     # --------------------------------------------------
#     @patch('stripe.Webhook.construct_event')
#     def test_missing_test_result_id(self, mock_construct_event):
#         self.mock_stripe_event(mock_construct_event, success=True)
#
#         payload = {
#             "id": "evt_missing_test_result",
#             "type": "payment_intent.succeeded",
#             "data": {
#                 "object": {
#                     "id": "pi_whatever",
#                     "status": "succeeded",
#                     "metadata": {}  # No test_result_id
#                 }
#             }
#         }
#
#         response = self.post_webhook(payload)
#         self.assertEqual(response.status_code, 200)
#         self.assertIn("Missing test_result_id", response.content.decode())
#
#
#
# class TestHandleIntegrityConflict(TestCase):
#     @patch('payment.utils.append_error_details')
#     @patch('payment.utils.initiate_refund')
#     @patch('payment.utils.update_payment_intent')
#     @patch('payment.utils.send_webhook_notification_email')
#     def test_handle_integrity_conflict_appends_error_and_initiates_refund(
#             self,
#             mock_send_email,
#             mock_update_payment_intent,
#             mock_initiate_refund,
#             mock_append_error_details
#     ):
#         user = User.objects.create_user(email='test@example.com')
#
#         # 1) Create a Payment object or a mock. For a real object in the test DB:
#         payment_obj = Payment.objects.create(
#             user=user,  # or create a real user
#             amount=100,
#             stripe_payment_intent_id='pi_mocked',
#             status='pending',
#             refund_status='not_refunded'
#         )
#
#         # 2) Decide what update_payment_intent should return
#         #    We'll say it returns the same payment object to show it's "updated."
#         mock_update_payment_intent.return_value = payment_obj
#
#         # 3) Create a fake IntegrityError
#         fake_error = IntegrityError("Simulated conflict")
#
#         # 4) Call the function under test
#         handle_integrity_conflict(payment_obj, reason='duplicate', error=fake_error)
#
#         # 5) Assert that update_payment_intent was called with expected args
#         mock_update_payment_intent.assert_called_once_with(
#             'pi_mocked',
#             status='refund_requested',
#             refund_status='requested',
#             refund_reason='duplicate'
#         )
#
#         # 6) Assert append_error_details is called properly
#         mock_append_error_details.assert_called_once_with(
#             payment_obj,  # the updated payment
#             'error_details',  # field_name
#             'IntegrityError',  # error_type
#             'Simulated conflict'  # error_message from the IntegrityError
#         )
#
#         # 7) Assert refund was initiated
#         mock_initiate_refund.assert_called_once_with(
#             payment_obj=payment_obj,
#             payment_intent_id='pi_mocked',
#             update_payment_intent=mock_update_payment_intent,
#             append_error_details=mock_append_error_details,
#             reason='duplicate'
#         )
#
#         # 8) Optionally check that an email was sent
#         mock_send_email.assert_called_once_with(
#             payment_obj,
#             message_type='refund_initiated'
#         )



# class PaymentSchemaTests(TestCase):
#     def setUp(self):
#         self.client = Client()
#         # Assuming your schema endpoint is registered with name 'schema' (e.g., /api/schema/)
#         self.schema_url = reverse('schema')
#
#     def get_schema_data(self):
#         # Include an Accept header so the response is in JSON format.
#         response = self.client.get(self.schema_url, HTTP_ACCEPT='application/json')
#         self.assertEqual(response.status_code, 200, "Schema endpoint did not return 200 OK")
#         try:
#             schema_data = json.loads(response.content.decode('utf-8'))
#         except json.JSONDecodeError:
#             self.fail("Schema response is not valid JSON: " + response.content.decode('utf-8'))
#         return schema_data
#
#     def test_schema_returns_valid_json(self):
#         """The schema endpoint should return valid JSON."""
#         schema_data = self.get_schema_data()
#         self.assertIn('paths', schema_data, "Schema JSON does not contain 'paths'")
#
#     def test_create_payment_endpoint_in_schema(self):
#         """The create-payment endpoint should be documented in the schema."""
#         schema_data = self.get_schema_data()
#         paths = schema_data.get("paths", {})
#
#         # Instead of checking for an exact key, look for any endpoint ending with '/payments/create/'
#         matching_paths = [path for path in paths.keys() if path.endswith('/payments/create/')]
#         self.assertTrue(matching_paths, "Create Payment endpoint missing from schema")
#
#     def test_webhook_endpoint_excluded_from_schema(self):
#         """The webhook endpoint should be excluded from the generated schema."""
#         schema_data = self.get_schema_data()
#         paths = schema_data.get("paths", {})
#
#         # Verify that no endpoint ends with '/payments/webhook/'
#         matching_paths = [path for path in paths.keys() if path.endswith('/payments/webhook/')]
#         self.assertFalse(matching_paths, "Webhook endpoint should be excluded from schema")
#
#     def test_generated_schema_valid(self):
#         """
#         Use DRF Spectacular's SchemaGenerator to generate the API schema and then
#         validate that the resulting schema conforms to a minimal OpenAPI schema.
#         """
#         generator = SchemaGenerator()
#         schema = generator.get_schema(request=None, public=True)
#
#         # A minimal OpenAPI schema to validate against. This does not cover every detail
#         # of the spec but ensures that the basic required keys exist.
#         minimal_openapi_schema = {
#             "type": "object",
#             "properties": {
#                 "openapi": {"type": "string"},
#                 "info": {"type": "object"},
#                 "paths": {"type": "object"},
#             },
#             "required": ["openapi", "info", "paths"],
#         }
#
#         # First, ensure the schema is a dict and has the minimal keys.
#         self.assertIsInstance(schema, dict, "Generated schema is not a dictionary.")
#         for key in ["openapi", "info", "paths"]:
#             self.assertIn(key, schema, f"Generated schema missing required key: {key}")
#
#         # Now validate using jsonschema
#         try:
#             jsonschema_validate(instance=schema, schema=minimal_openapi_schema)
#         except JSONSchemaValidationError as e:
#             self.fail(f"Generated schema is invalid: {e}")


class SchemaValidationTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Generate the OpenAPI schema
        generator = SchemaGenerator()
        schema = generator.get_schema(request=None, public=True)
        # Convert the schema to a JSON string
        schema_json = json.dumps(schema)
        # Use jsonref to resolve $ref references
        cls.schema_dict = jsonref.loads(schema_json)

    def get_response_schema(self, path, method, status_code):
        """
        Extracts the JSON schema for the response of a given endpoint.
        """
        paths = self.schema_dict.get('paths', {})
        endpoint = paths.get(path)
        if not endpoint:
            raise KeyError(f"Path '{path}' not found in schema.")
        operation = endpoint.get(method.lower())
        if not operation:
            raise KeyError(f"Method '{method}' for path '{path}' not found in schema.")
        responses = operation.get('responses', {})
        response = responses.get(status_code)
        if not response:
            raise KeyError(f"Response with status code '{status_code}' not found for path '{path}' and method '{method}'.")
        content = response.get('content', {})
        media_type = content.get('application/json')
        if not media_type:
            raise KeyError(f"'application/json' media type not found in responses for path '{path}' and method '{method}'.")
        schema = media_type.get('schema')
        if not schema:
            raise KeyError(f"Schema not found in 'application/json' response for path '{path}' and method '{method}'.")
        return schema

    def validate_response(self, response, schema):
        """
        Validates the API response against the provided JSON schema.
        """
        data = response.json()
        try:
            jsonschema_validate(instance=data, schema=schema)
        except JSONSchemaValidationError as e:
            self.fail(f"Response schema validation failed: {e.message}")

class PaymentEndpointSchemaTests(SchemaValidationTests):
    def setUp(self):
        self.client = APIClient()
        # Create and authenticate a test user
        self.user = User.objects.create_user(email='test@example.com', password='testpass123')
        self.client.force_authenticate(user=self.user)
        # Create a dummy PsychometricTest instance with valid questions, options, and traits
        self.dummy_test = PsychometricTest.objects.create(
            test_name="Dummy Test",
            questions=[{'question number': 1, 'scale': 'Scale1', 'trait': 'Trait1', 'text': 'Dummy question?'}],
            options=['Option A', 'Option B', 'Option C'],
            traits=['Trait1']
        )
        # Create a dummy TestResult instance that belongs to this user
        self.dummy_test_result = TestResult.objects.create(
            user=self.user,
            test=self.dummy_test,
            uuid=uuid.uuid4()
        )
        self.create_payment_url = reverse('payment:create-payment')

    def test_create_payment_response_schema(self):
        # Use a valid payment creation body as described:
        data = {
            "test": self.dummy_test.id,
            "test_result": str(self.dummy_test_result.uuid),
            "amount": 20.00,
            "currency": "usd",
            "payment_method": "pm_card_visa",
            "payment_method_types": ["card"]
        }
        response = self.client.post(self.create_payment_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # The schema might be registered with a prefix. Find the path ending with '/payments/create/'
        matching_paths = [p for p in self.schema_dict.get('paths', {}).keys() if p.endswith('/payments/create/')]
        self.assertTrue(matching_paths, "Create Payment endpoint missing from schema")
        endpoint_path = matching_paths[0]
        # Extract the response schema for status code 201 and POST method
        schema = self.get_response_schema(endpoint_path, 'post', '201')
        # Validate the response against the schema
        self.validate_response(response, schema)

class SubscriptionWorkflowTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='subscriber@example.com')
        self.client.force_authenticate(user=self.user)
        self.plan = SubscriptionPlan.objects.create(
            name='Starter',
            slug='starter',
            description='Monthly starter plan',
            price='49.99',
            currency='usd',
            monthly_allowance=10,
            unlimited_tests=False,
            stripe_product_id='prod_123',
            stripe_price_id='price_123',
        )
        self.list_url = reverse('payment:subscription-plans')
        self.create_url = reverse('payment:subscription-create')
        self.me_url = reverse('payment:subscription-current')

    def test_list_subscription_plans(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['slug'], 'starter')

    @patch('payment.subscription_service.stripe.Customer.modify')
    @patch('payment.subscription_service.stripe.PaymentMethod.attach')
    @patch('payment.subscription_service.stripe.Subscription.create')
    @patch('payment.subscription_service.stripe.Customer.create')
    def test_create_subscription_creates_ledger(self, mock_customer_create, mock_subscription_create, mock_attach, mock_customer_modify):
        mock_customer_create.return_value = {'id': 'cus_123'}
        mock_subscription_create.return_value = {
            'id': 'sub_123',
            'status': 'active',
            'current_period_start': 1696118400,
            'current_period_end': 1698710400,
            'cancel_at_period_end': False,
        }

        payload = {
            'plan_id': str(self.plan.id),
            'payment_method_id': 'pm_123',
        }

        with patch('payment.subscription_service._set_stripe_api_key'):
            response = self.client.post(self.create_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        subscription = UserSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.ledger_entries.count(), 1)
        self.assertEqual(subscription.remaining_tests, self.plan.monthly_allowance)

    def test_current_subscription_endpoint(self):
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=UserSubscription.STATUS_ACTIVE,
            is_active=True,
        )
        subscription.record_accrual(self.plan.monthly_allowance)

        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['remaining_tests'], self.plan.monthly_allowance)

    def test_consume_allowance_reduces_balance(self):
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=UserSubscription.STATUS_ACTIVE,
            is_active=True,
        )
        subscription.record_accrual(self.plan.monthly_allowance)
        consume_allowance(subscription=subscription, quantity=2)
        balance = subscription_balance(subscription)
        self.assertEqual(balance.remaining_tests, self.plan.monthly_allowance - 2)

