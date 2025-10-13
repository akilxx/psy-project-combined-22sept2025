# authentication/views.py

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import OpenApiExample, extend_schema

from .models import PendingRegistration
from .serializers import (
    ErrorResponseSerializer,
    LogoutResponseSerializer,
    OTPFlowSerializer,
    OTPInitiateResponseSerializer,
    OTPVerifyResponseSerializer,
)


User = get_user_model()
logger = logging.getLogger(__name__)


class OTPView(APIView):
    """Combined endpoint for requesting and verifying OTP codes."""

    permission_classes = [AllowAny]

    @extend_schema(
        request=OTPFlowSerializer,
        responses={
            200: OTPInitiateResponseSerializer,
            201: OTPVerifyResponseSerializer,
            400: ErrorResponseSerializer,
        },
        description="Request or verify an OTP for both login and registration flows.",
        examples=[
            OpenApiExample(
                'Request OTP Response',
                value={
                    "detail": "OTP sent to email.",
                    "status": "registration_pending",
                    "resend_available_in": 30,
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                'Verify OTP Response',
                value={
                    "detail": "Login successful.",
                    "status": "logged_in",
                    "refresh": "<refresh>",
                    "access": "<access>",
                },
                response_only=True,
                status_codes=["200", "201"],
            ),
        ],
    )
    def post(self, request):
        serializer = OTPFlowSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        operation = serializer.validated_data['operation']
        intent = serializer.validated_data['intent']
        email = serializer.validated_data['email']

        if operation == 'request':
            pending = serializer.save()

            template_name = (
                'emails/register_email.txt'
                if intent == PendingRegistration.Intent.REGISTER
                else 'emails/login_email.txt'
            )
            context = {'otp_code': pending.otp_code}
            email_body = render_to_string(template_name, context)

            try:
                send_mail(
                    subject='Your OTP Code',
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[pending.email],
                    fail_silently=False,
                )
            except Exception:  # pragma: no cover - email backend specific
                logger.exception("Failed to send OTP email")
                pending.is_valid = False
                pending.save(update_fields=['is_valid'])
                return Response(
                    {'detail': 'Failed to send OTP. Please try again later.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            status_label = (
                'registration_pending'
                if intent == PendingRegistration.Intent.REGISTER
                else 'login_pending'
            )
            return Response(
                {
                    'detail': 'OTP sent to email.',
                    'status': status_label,
                    'resend_available_in': OTPFlowSerializer.RESEND_COOLDOWN_SECONDS,
                },
                status=status.HTTP_200_OK,
            )

        pending_registration = serializer.validated_data['pending_registration']
        user = serializer.validated_data['user']

        pending_registration.is_valid = False
        pending_registration.save(update_fields=['is_valid'])

        if intent == PendingRegistration.Intent.REGISTER and user is None:
            user = User.objects.create_user(email=email)
            detail = 'Registration successful.'
            status_label = 'registered'
            status_code = status.HTTP_201_CREATED
        else:
            if user is None:
                # Fallback for edge cases where the intent mismatches user existence.
                user = User.objects.create_user(email=email)
            detail = 'Login successful.'
            status_label = 'logged_in'
            status_code = status.HTTP_200_OK

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'detail': detail,
                'status': status_label,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status_code,
        )


class LogoutView(APIView):
    """Logout the user by blacklisting the refresh token."""

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
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token is None:
                return Response(
                    {"detail": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'detail': 'Logout successful.'}, status=status.HTTP_200_OK)
        except TokenError:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:  # pragma: no cover - defensive safety
            logger.exception("Unexpected error during logout")
            return Response(
                {"detail": "An error occurred during logout."},
                status=status.HTTP_400_BAD_REQUEST,
            )
