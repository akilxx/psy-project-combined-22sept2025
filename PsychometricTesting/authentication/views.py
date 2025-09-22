# authentication/views.py
import logging
from rest_framework import status
from django.template.loader import render_to_string
from .serializers import (
    RegistrationSerializer,
    VerifyRegistrationSerializer,
    RequestOTPSerializer,
    VerifyOTPSerializer,
    RegistrationResponseSerializer,
    ErrorResponseSerializer,
    VerifyRegistrationResponseSerializer,
    OTPResponseSerializer,
    VerifyOTPResponseSerializer,
    LogoutResponseSerializer,
)
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.core.mail import send_mail
from .models import PendingRegistration
from django.conf import settings
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
)



User = get_user_model()

logger = logging.getLogger(__name__)



#---------------------------------------------OTP Verification Views----------------------------------------------------------------

class RegistrationView(APIView):
    """
    View for handling user registration requests.

    Accepts an email address and sends an OTP code for verification.
    """

    @extend_schema(
        request=RegistrationSerializer,
        responses={
            201: RegistrationResponseSerializer,
            400: ErrorResponseSerializer,
        },
        description="Register a new user and send an OTP code to the provided email address.",
        examples=[
            OpenApiExample(
                'Successful Response',
                value={"detail": "OTP sent to email.", "registration_id": "123e4567-e89b-12d3-a456-426614174000"},
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                'Error Response',
                value={"email": ["Email is already registered."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        """
                Handle POST request to initiate registration.

                Validates the provided email and sends an OTP code to the email address.

                Returns:
                    Response: Contains a message indicating that the OTP was sent and the `registration_id`.

                Raises:
                    - HTTP 400 Bad Request: If the email is already registered or an OTP has already been sent.
        """
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            pending_registration = serializer.save()
            # Send OTP via email
            otp_code = pending_registration.otp_code

            # Prepare the context for the template
            context = {
                'otp_code': otp_code,
            }

            # Render the email content from the template
            email_body = render_to_string('emails/register_email.txt', context)

            # Send OTP via email
            send_mail(
                subject='Your OTP Code',
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,  # Ideally, use settings.DEFAULT_FROM_EMAIL
                recipient_list=[pending_registration.email],
                fail_silently=False,
            )

            return Response({'detail': 'OTP sent to email.', 'registration_id': str(pending_registration.registration_id)},
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyRegistrationView(APIView):
    """
        View for verifying the OTP code during user registration.

        Verifies the provided OTP and creates a new user account.
    """
    @extend_schema(
        request=VerifyRegistrationSerializer,
        responses={
            201: VerifyRegistrationResponseSerializer,
            400: ErrorResponseSerializer,
        },
        description="Verify the OTP code for registration and create a new user account.",
        examples=[
            OpenApiExample(
                'Successful Response',
                value={
                    "detail": "Registration successful.",
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGci...",
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGci..."
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                'Error Response',
                value={"otp_code": ["Invalid OTP code. You have 2 attempts left."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        """
                Handle POST request to verify the registration OTP.

                Validates the OTP code and creates a new user if successful.

                Returns:
                    Response: Contains a message indicating successful registration and authentication tokens.

                Raises:
                    - HTTP 400 Bad Request: If the OTP is invalid, expired, or maximum attempts exceeded.
        """
        serializer = VerifyRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            pending_registration = serializer.validated_data['pending_registration']
            # Create the user
            user = User.objects.create_user(email=pending_registration.email)
            # Invalidate the pending registration
            pending_registration.is_valid = False
            pending_registration.save()
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'detail': 'Registration successful.',
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestOTPView(APIView):
    """
        View for requesting an OTP code for login.

        Sends an OTP code to the user's email address for authentication.
    """
    @extend_schema(
        request=RequestOTPSerializer,
        responses={
            200: OTPResponseSerializer,
            400: ErrorResponseSerializer,
        },
        description="Request an OTP code for login to be sent to the user's email address.",
        examples=[
            OpenApiExample(
                'Successful Response',
                value={"detail": "OTP sent to email."},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                'Error Response',
                value={"non_field_errors": ["User not found."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):

        """
                Handle POST request to request an OTP for login.

                Validates the email and sends an OTP code to the email address.

                Returns:
                    Response: Contains a message indicating that the OTP was sent.

                Raises:
                    - HTTP 400 Bad Request: If the user is not found or an OTP is already pending.
        """

        serializer = RequestOTPSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.save()
            email = validated_data.get('email')
            pending_registration = PendingRegistration.objects.filter(email=email).order_by('-created_at').first()

            otp_code = pending_registration.otp_code

            # Prepare the context for the template
            context = {
                'otp_code': otp_code,
            }

            # Render the email content from the template
            email_body = render_to_string('emails/login_email.txt', context)

            # Send OTP via email
            send_mail(
                subject='Your OTP Code',
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,  # Ideally, use settings.DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({'detail': 'OTP sent to email.'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class VerifyOTPView(APIView):
    """
        View for verifying the OTP code during user login.

        Verifies the provided OTP and authenticates the user.
    """
    @extend_schema(
        request=VerifyOTPSerializer,
        responses={
            200: VerifyOTPResponseSerializer,
            400: ErrorResponseSerializer,
        },
        description="Verify the OTP code for login and authenticate the user.",
        examples=[
            OpenApiExample(
                'Successful Response',
                value={
                    "detail": "Login successful.",
                    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGci...",
                    "access": "eyJ0eXAiOiJKV1QiLCJhbGci..."
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                'Error Response',
                value={"otp_code": ["Invalid OTP code. You have 1 attempt left."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        """
                Handle POST request to verify the login OTP.

                Validates the OTP code and authenticates the user if successful.

                Returns:
                    Response: Contains a message indicating successful login and authentication tokens.

                Raises:
                    - HTTP 400 Bad Request: If the OTP is invalid, expired, or maximum attempts exceeded.
        """
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            pending_registration = serializer.validated_data['pending_registration']
            # Invalidate the pending registration
            pending_registration.is_valid = False
            pending_registration.save()
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'detail': 'Login successful.',
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """
        View for logging out the user by blacklisting the refresh token.

        Accepts a refresh token and invalidates it.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={
            200: LogoutResponseSerializer,
            400: ErrorResponseSerializer,
        },
        description="Logout the user by blacklisting the provided refresh token.",
        examples=[
            OpenApiExample(
                'Successful Response',
                value={"detail": "Logout successful."},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                'Error Response',
                value={"detail": "Invalid or expired token."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request):
        """
                Handle POST request to log out the user.

                Invalidates the provided refresh token.

                Returns:
                    Response: Contains a message indicating successful logout.

                Raises:
                    - HTTP 400 Bad Request: If the refresh token is invalid or expired.
        """
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token is None:
                return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'detail': 'Logout successful.'},status=status.HTTP_200_OK)
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "An error occurred during logout."}, status=status.HTTP_400_BAD_REQUEST)


