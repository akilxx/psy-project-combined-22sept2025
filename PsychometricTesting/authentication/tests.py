# authentication/tests.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from django.contrib.auth import get_user_model
import uuid
from rest_framework.test import APIClient, APITestCase
from unittest.mock import patch
from rest_framework_simplejwt.tokens import RefreshToken
from authentication.models import PendingRegistration
from drf_spectacular.generators import SchemaGenerator
import json
import jsonref
from jsonschema import validate as jsonschema_validate, ValidationError as JSONSchemaValidationError

User = get_user_model()


class RegistrationLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.registration_url = reverse('register')
        self.verify_registration_url = reverse('verify-registration')
        self.request_otp_url = reverse('request-otp')
        self.verify_otp_url = reverse('verify-otp')
        self.token_refresh_url = reverse('token_refresh')

        self.test_email = 'testuser@example.com'

    @patch('authentication.views.send_mail')
    def test_registration_success(self, mock_send_mail):
        data = {'email': self.test_email}
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('registration_id', response.data)
        self.assertEqual(response.data['detail'], 'OTP sent to email.')

        # Check that a PendingRegistration object was created
        pending_registrations = PendingRegistration.objects.filter(email=self.test_email, is_valid=True)
        self.assertEqual(pending_registrations.count(), 1)
        pending_registration = pending_registrations.first()
        self.assertEqual(pending_registration.email, self.test_email)
        self.assertTrue(pending_registration.is_valid)

        # Check that send_mail was called
        self.assertTrue(mock_send_mail.called)

    def test_registration_email_already_registered(self):
        # Create a user with the test email
        User.objects.create_user(email=self.test_email)
        data = {'email': self.test_email}
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'][0], 'Email is already registered.')

    @patch('authentication.views.send_mail')
    def test_registration_pending_registration_exists(self, mock_send_mail):
        # Create a pending registration
        PendingRegistration.objects.create(
            email=self.test_email,
            otp_code='123456',
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            is_valid=True
        )
        data = {'email': self.test_email}
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(
            response.data['email'][0],
            'An OTP has already been sent to this email. Please check your inbox.'
        )

    @patch('authentication.views.send_mail')
    def test_verify_registration_success(self, mock_send_mail):
        # First, register to get a pending registration
        data = {'email': self.test_email}
        response = self.client.post(self.registration_url, data, format='json')
        registration_id = response.data['registration_id']

        # Get the pending registration to get the otp_code
        pending_registration = PendingRegistration.objects.get(registration_id=registration_id)

        # Now verify the registration with the correct OTP
        verify_data = {
            'registration_id': registration_id,
            'otp_code': pending_registration.otp_code
        }
        response = self.client.post(self.verify_registration_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['detail'], 'Registration successful.')

        # Check that the user was created
        self.assertTrue(User.objects.filter(email=self.test_email).exists())

        # Check that the pending registration is invalidated
        pending_registration.refresh_from_db()
        self.assertFalse(pending_registration.is_valid)

    def test_verify_registration_invalid_registration_id(self):
        verify_data = {
            'registration_id': str(uuid.uuid4()),  # Valid UUID format but does not exist
            'otp_code': '123456'
        }
        response = self.client.post(self.verify_registration_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('registration_id', response.data)
        self.assertEqual(response.data['registration_id'][0], 'Invalid or expired registration ID.')

    @patch('authentication.views.send_mail')
    def test_verify_registration_incorrect_otp(self, mock_send_mail):
        # First, register to get a pending registration
        data = {'email': self.test_email}
        response = self.client.post(self.registration_url, data, format='json')
        registration_id = response.data['registration_id']

        # Now verify the registration with incorrect OTP
        verify_data = {
            'registration_id': registration_id,
            'otp_code': '654321'  # Incorrect OTP
        }
        response = self.client.post(self.verify_registration_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp_code', response.data)
        self.assertIn('Invalid OTP code.', response.data['otp_code'][0])

        # Check that failed_attempts is incremented
        pending_registration = PendingRegistration.objects.get(registration_id=registration_id)
        self.assertEqual(pending_registration.failed_attempts, 1)

    @patch('authentication.views.send_mail')
    def test_verify_registration_max_failed_attempts_exceeded(self, mock_send_mail):
        # First, register to get a pending registration
        data = {'email': self.test_email}
        response = self.client.post(self.registration_url, data, format='json')
        registration_id = response.data['registration_id']

        pending_registration = PendingRegistration.objects.get(registration_id=registration_id)

        # Exceed the maximum failed attempts
        max_attempts = 3  # As per the serializers
        for attempt in range(max_attempts):
            verify_data = {
                'registration_id': registration_id,
                'otp_code': '654321'  # Incorrect OTP
            }
            self.client.post(self.verify_registration_url, verify_data, format='json')

        # Now the pending registration should be invalidated
        pending_registration.refresh_from_db()
        self.assertFalse(pending_registration.is_valid)

        # Try verifying again
        verify_data = {
            'registration_id': registration_id,
            'otp_code': pending_registration.otp_code  # Even with correct OTP
        }
        response = self.client.post(self.verify_registration_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp_code', response.data)
        self.assertEqual(
            response.data['otp_code'][0],
            'Maximum verification attempts exceeded. Please register again.'
        )

    @patch('authentication.views.send_mail')
    def test_verify_registration_expired_registration(self, mock_send_mail):
        # Create a pending registration with expired expires_at
        pending_registration = PendingRegistration.objects.create(
            email=self.test_email,
            otp_code='123456',
            expires_at=timezone.now() - timezone.timedelta(minutes=1),  # Expired
            is_valid=True
        )

        verify_data = {
            'registration_id': str(pending_registration.registration_id),
            'otp_code': pending_registration.otp_code
        }
        response = self.client.post(self.verify_registration_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('registration_id', response.data)
        self.assertEqual(
            response.data['registration_id'][0],
            'This registration has expired. Please register again.'
        )

    @patch('authentication.views.send_mail')
    def test_request_otp_success(self, mock_send_mail):
        # First, create a user
        User.objects.create_user(email=self.test_email)
        data = {'email': self.test_email}
        response = self.client.post(self.request_otp_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'OTP sent to email.')

        # Check that a PendingRegistration object was created
        pending_registrations = PendingRegistration.objects.filter(email=self.test_email, is_valid=True)
        self.assertEqual(pending_registrations.count(), 1)
        pending_registration = pending_registrations.first()
        self.assertEqual(pending_registration.email, self.test_email)
        self.assertTrue(pending_registration.is_valid)

        # Check that send_mail was called
        self.assertTrue(mock_send_mail.called)

    def test_request_otp_user_not_found(self):
        data = {'email': self.test_email}
        response = self.client.post(self.request_otp_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertEqual(response.data['non_field_errors'][0], 'User not found.')

    @patch('authentication.views.send_mail')
    def test_verify_otp_success(self, mock_send_mail):
        # First, create a user and request OTP
        User.objects.create_user(email=self.test_email)
        data = {'email': self.test_email}
        self.client.post(self.request_otp_url, data, format='json')

        # Get the pending registration to get the otp_code
        pending_registration = PendingRegistration.objects.filter(email=self.test_email).order_by('-created_at').first()

        # Now verify the OTP
        verify_data = {
            'email': self.test_email,
            'otp_code': pending_registration.otp_code
        }
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['detail'], 'Login successful.')

        # Check that the pending registration is invalidated
        pending_registration.refresh_from_db()
        self.assertFalse(pending_registration.is_valid)

    @patch('authentication.views.send_mail')
    def test_verify_otp_incorrect_otp(self, mock_send_mail):
        # First, create a user and request OTP
        User.objects.create_user(email=self.test_email)
        data = {'email': self.test_email}
        self.client.post(self.request_otp_url, data, format='json')

        # Now verify the OTP with incorrect code
        verify_data = {
            'email': self.test_email,
            'otp_code': '654321'  # Incorrect OTP
        }
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp_code', response.data)
        self.assertIn('Invalid OTP code.', response.data['otp_code'][0])

        # Check that failed_attempts is incremented
        pending_registration = PendingRegistration.objects.filter(email=self.test_email).order_by('-created_at').first()
        self.assertEqual(pending_registration.failed_attempts, 1)

    @patch('authentication.views.send_mail')
    def test_verify_otp_max_failed_attempts_exceeded(self, mock_send_mail):
        # First, create a user and request OTP
        User.objects.create_user(email=self.test_email)
        data = {'email': self.test_email}
        self.client.post(self.request_otp_url, data, format='json')

        pending_registration = PendingRegistration.objects.filter(email=self.test_email).order_by('-created_at').first()

        max_attempts = 3  # As per the serializers
        for attempt in range(max_attempts):
            verify_data = {
                'email': self.test_email,
                'otp_code': '654321'  # Incorrect OTP
            }
            self.client.post(self.verify_otp_url, verify_data, format='json')

        # Now the pending registration should be invalidated
        pending_registration.refresh_from_db()
        self.assertFalse(pending_registration.is_valid)

        # Try verifying again
        verify_data = {
            'email': self.test_email,
            'otp_code': pending_registration.otp_code  # Even with correct OTP
        }
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp_code', response.data)
        self.assertEqual(
            response.data['otp_code'][0],
            'Maximum verification attempts exceeded. Please request a new OTP.'
        )

    def test_verify_otp_expired(self):
        # Create a pending registration with expired expires_at
        User.objects.create_user(email=self.test_email)
        pending_registration = PendingRegistration.objects.create(
            email=self.test_email,
            otp_code='123456',
            expires_at=timezone.now() - timezone.timedelta(minutes=1),  # Expired
            is_valid=True
        )

        verify_data = {
            'email': self.test_email,
            'otp_code': pending_registration.otp_code
        }
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('otp_code', response.data)
        self.assertEqual(
            response.data['otp_code'][0],
            'This OTP has expired. Please request a new OTP.'
        )

    @patch('authentication.views.send_mail')
    def test_middleware_invalidates_expired_pending_registrations(self, mock_send_mail):
        # Create an expired pending registration
        pending_registration = PendingRegistration.objects.create(
            email=self.test_email,
            otp_code='123456',
            expires_at=timezone.now() - timezone.timedelta(minutes=1),  # Expired
            is_valid=True
        )

        # Make a request to '/verify-registration/' to trigger the middleware
        data = {'registration_id': str(uuid.uuid4()), 'otp_code': '000000'}
        self.client.post(self.verify_registration_url, data, format='json')

        # Refresh from DB
        pending_registration.refresh_from_db()
        self.assertFalse(pending_registration.is_valid)

    @patch('authentication.views.send_mail')
    def test_middleware_invalidates_pending_registrations_with_max_failed_attempts(self, mock_send_mail):
        # Create a pending registration with failed_attempts >= MAX_FAILED_ATTEMPTS
        max_attempts = 3
        pending_registration = PendingRegistration.objects.create(
            email=self.test_email,
            otp_code='123456',
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            failed_attempts=max_attempts,
            is_valid=True
        )

        # Make a request to '/verify-otp/' to trigger the middleware
        data = {'email': 'anotheruser@example.com', 'otp_code': '000000'}
        self.client.post(self.verify_otp_url, data, format='json')

        # Refresh from DB
        pending_registration.refresh_from_db()
        self.assertFalse(pending_registration.is_valid)

    @patch('authentication.views.send_mail')
    def test_request_otp_when_pending_otp_exists(self, mock_send_mail):
        # Create a user and a pending OTP
        User.objects.create_user(email=self.test_email)
        PendingRegistration.objects.create(
            email=self.test_email,
            otp_code='123456',
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            is_valid=True
        )

        data = {'email': self.test_email}
        response = self.client.post(self.request_otp_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(
            response.data['detail'][0],
            'An OTP has already been sent and is still valid. Please check your email or request a new OTP after it expires.'
        )

        # Ensure send_mail was not called
        mock_send_mail.assert_not_called()

    def test_registration_invalid_email_format(self):
        data = {'email': 'invalid-email-format'}
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('Enter a valid email address.', response.data['email'])

    def test_verify_otp_with_invalid_email(self):
        data = {'email': 'invalid@example.com', 'otp_code': '123456'}
        response = self.client.post(self.verify_otp_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'][0], 'No pending OTP found for this email. Please request a new OTP.')

    def test_sql_injection_attack(self):
        malicious_input = "'; DROP TABLE users; --"
        response = self.client.post(
            self.registration_url,
            {'email': malicious_input},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sensitive_data_not_exposed_on_registration(self):
        data = {'email': self.test_email}
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)
        self.assertNotIn('tokens', response.data)

    def test_sensitive_data_not_exposed_on_login(self):
        # Register and verify user
        data = {'email': self.test_email}
        self.client.post(self.registration_url, data, format='json')
        pending_registration = PendingRegistration.objects.filter(
            email=self.test_email, is_valid=True
        ).order_by('-created_at').first()
        verify_data = {
            'registration_id': str(pending_registration.registration_id),
            'otp_code': pending_registration.otp_code
        }
        response = self.client.post(self.verify_registration_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Request OTP for login
        response = self.client.post(self.request_otp_url, {'email': self.test_email}, format='json')

        # Verify OTP
        pending_registration = PendingRegistration.objects.filter(
            email=self.test_email, is_valid=True
        ).order_by('-created_at').first()
        verify_data = {'email': self.test_email, 'otp_code': pending_registration.otp_code}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('password', response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_error_responses_do_not_expose_sensitive_info(self):
        # Attempt to login with invalid credentials
        data = {'email': self.test_email, 'otp_code': 'invalid'}
        response = self.client.post(self.verify_otp_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that response does not contain sensitive data
        self.assertNotIn('traceback', response.data)
        self.assertNotIn('exception', response.data)


class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.logout_url = reverse('auth_logout')
        self.user = User.objects.create_user(email='user@example.com')
        refresh = RefreshToken.for_user(self.user)
        self.refresh_token = str(refresh)
        self.access_token = str(refresh.access_token)

    def test_valid_logout(self):
        response = self.client.post(self.logout_url, {'refresh': self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Logout successful.')

    def test_logout_with_invalid_token(self):
        response = self.client.post(self.logout_url, {'refresh': 'invalidtoken'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'Invalid or expired token.')

    def test_logout_without_token(self):
        response = self.client.post(self.logout_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertIn('Refresh token is required.', response.data['detail'])


#------------------------------------------------Schema Validation------------------------------------------------




class SchemaValidationTests(APITestCase):
    @classmethod
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

        Args:
            path (str): The path of the endpoint (e.g., '/register/').
            method (str): The HTTP method (e.g., 'post').
            status_code (str): The HTTP status code as a string (e.g., '201').

        Returns:
            dict: The JSON schema of the response.

        Raises:
            KeyError: If the path, method, or status code is not found in the schema.
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

        Args:
            response (Response): The Django REST Framework response object.
            schema (dict): The JSON schema to validate against.

        Raises:
            AssertionError: If the response does not match the schema.
        """
        data = response.json()
        try:
            jsonschema_validate(instance=data, schema=schema)
        except JSONSchemaValidationError as e:
            self.fail(f"Response schema validation failed: {e.message}")


class RegistrationTests(SchemaValidationTests):
    def setUp(self):
        self.client = APIClient()
        self.registration_url = reverse('register')

    def test_registration_response_schema(self):
        data = {'email': 'test@example.com'}
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Extract the response schema
        schema = self.get_response_schema('/register/', 'post', '201')

        # Validate the response
        self.validate_response(response, schema)



class VerifyRegistrationTests(SchemaValidationTests):
    def setUp(self):
        self.client = APIClient()
        self.registration_url = reverse('register')
        self.verify_registration_url = reverse('verify-registration')

    def test_verify_registration_response_schema(self):
        # First, register to get a registration_id
        data = {'email': 'test@example.com'}
        response = self.client.post(self.registration_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        registration_id = response.data['registration_id']

        # Simulate retrieving the OTP code (assuming in test environment)
        pending_registration = PendingRegistration.objects.get(registration_id=registration_id)
        otp_code = pending_registration.otp_code

        # Verify registration
        verify_data = {'registration_id': str(registration_id), 'otp_code': otp_code}
        response = self.client.post(self.verify_registration_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Extract the response schema
        schema = self.get_response_schema('/verify-registration/', 'post', '201')

        # Validate the response
        self.validate_response(response, schema)


class RequestOTPTests(SchemaValidationTests):
    def setUp(self):
        self.client = APIClient()
        self.request_otp_url = reverse('request-otp')
        # Create a user
        User.objects.create_user(email='test@example.com')

    def test_request_otp_response_schema(self):
        data = {'email': 'test@example.com'}
        response = self.client.post(self.request_otp_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Extract the response schema
        schema = self.get_response_schema('/request-otp/', 'post', '200')

        # Validate the response
        self.validate_response(response, schema)


class VerifyOTPTests(SchemaValidationTests):
    def setUp(self):
        self.client = APIClient()
        self.request_otp_url = reverse('request-otp')
        self.verify_otp_url = reverse('verify-otp')
        # Create a user
        User.objects.create_user(email='test@example.com')

    def test_verify_otp_response_schema(self):
        # Request OTP
        data = {'email': 'test@example.com'}
        response = self.client.post(self.request_otp_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Simulate retrieving the OTP code
        pending_registration = PendingRegistration.objects.filter(email='test@example.com').latest('created_at')
        otp_code = pending_registration.otp_code

        # Verify OTP
        verify_data = {'email': 'test@example.com', 'otp_code': otp_code}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Extract the response schema
        schema = self.get_response_schema('/verify-otp/', 'post', '200')

        # Validate the response
        self.validate_response(response, schema)



# class LogoutTests(SchemaValidationTests):
#     def setUp(self):
#         self.client = APIClient()
#         self.logout_url = reverse('auth_logout')
#         # Create a user and obtain tokens
#         self.user = User.objects.create_user(email='test@example.com')
#         self.refresh = RefreshToken.for_user(self.user)
#         self.access_token = str(self.refresh.access_token)
#         self.refresh_token = str(self.refresh)
#
#     def test_logout_response_schema(self):
#         # Set authentication
#         self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.access_token)
#
#         # Logout
#         data = {'refresh': self.refresh_token}
#         response = self.client.post(self.logout_url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#         # Extract the response schema
#         schema = self.get_response_schema('/logout/', 'post', '200')
#
#         # Validate the response
#         self.validate_response(response, schema)