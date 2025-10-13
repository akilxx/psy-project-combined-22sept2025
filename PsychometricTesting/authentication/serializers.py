# authentication/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
import random

from .models import PendingRegistration


User = get_user_model()


class OTPFlowSerializer(serializers.Serializer):
    """Serializer that powers the combined login/registration OTP flow."""

    email = serializers.EmailField(help_text="The email address for login or registration.")
    otp_code = serializers.CharField(
        max_length=4,
        required=False,
        help_text="The 4-digit OTP code sent to the user's email.",
    )

    MAX_FAILED_ATTEMPTS = 3
    RESEND_COOLDOWN_SECONDS = 30

    def validate_email(self, value):
        return User.objects.normalize_email(value)

    def validate_otp_code(self, value):
        if value and (not value.isdigit() or len(value) != 4):
            raise serializers.ValidationError("OTP codes must be 4 digits.")
        return value

    def validate(self, data):
        email = data['email']
        otp_code = data.get('otp_code')
        now = timezone.now()

        user = User.objects.filter(email=email).first()
        data['user'] = user

        if otp_code:
            data['operation'] = 'verify'
            pending = PendingRegistration.objects.filter(
                email=email,
                is_valid=True,
            ).order_by('-created_at').first()

            if not pending:
                raise serializers.ValidationError({
                    'otp_code': 'No active OTP found for this email. Please request a new code.'
                })

            if pending.expires_at < now:
                pending.is_valid = False
                pending.save(update_fields=['is_valid'])
                raise serializers.ValidationError({
                    'otp_code': 'This OTP has expired. Please request a new code.'
                })

            if pending.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                pending.is_valid = False
                pending.save(update_fields=['is_valid'])
                raise serializers.ValidationError({
                    'otp_code': 'Maximum verification attempts exceeded. Please request a new OTP.'
                })

            if pending.otp_code != otp_code:
                pending.failed_attempts += 1
                update_fields = ['failed_attempts']
                if pending.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                    pending.is_valid = False
                    update_fields.append('is_valid')
                    message = 'Maximum verification attempts exceeded. Please request a new OTP.'
                else:
                    attempts_left = self.MAX_FAILED_ATTEMPTS - pending.failed_attempts
                    message = f'Invalid OTP code. You have {attempts_left} attempts left.'

                pending.save(update_fields=update_fields)
                raise serializers.ValidationError({'otp_code': message})

            data['intent'] = pending.intent
            data['pending_registration'] = pending
            return data

        data['operation'] = 'request'
        intent = PendingRegistration.Intent.LOGIN if user else PendingRegistration.Intent.REGISTER
        data['intent'] = intent

        recent_valid = PendingRegistration.objects.filter(
            email=email,
            is_valid=True,
        ).order_by('-created_at').first()

        if recent_valid:
            elapsed = (now - recent_valid.created_at).total_seconds()
            if elapsed < self.RESEND_COOLDOWN_SECONDS:
                wait_seconds = max(1, int(self.RESEND_COOLDOWN_SECONDS - elapsed))
                raise serializers.ValidationError({
                    'detail': f'Please wait {wait_seconds} seconds before requesting a new OTP.',
                    'retry_after': wait_seconds,
                })

        return data

    def create(self, validated_data):
        email = validated_data['email']
        intent = validated_data['intent']
        now = timezone.now()

        PendingRegistration.objects.filter(email=email, is_valid=True).update(is_valid=False)

        otp_code = f"{random.randint(0, 9999):04d}"
        expires_at = now + timezone.timedelta(minutes=10)

        pending = PendingRegistration.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at,
            failed_attempts=0,
            is_valid=True,
            intent=intent,
        )

        return pending


class OTPInitiateResponseSerializer(serializers.Serializer):
    """Schema for responses after requesting/resending an OTP."""

    detail = serializers.CharField(help_text="A message indicating the OTP was sent.")
    status = serializers.CharField(help_text="Identifies whether the flow is for login or registration.")
    resend_available_in = serializers.IntegerField(
        help_text="Seconds until another OTP can be requested."
    )


class OTPVerifyResponseSerializer(serializers.Serializer):
    """Schema for responses after successfully verifying an OTP."""

    detail = serializers.CharField(help_text="A message indicating success.")
    status = serializers.CharField(help_text="Indicates whether the user logged in or registered.")
    refresh = serializers.CharField(help_text="The refresh token issued upon success.")
    access = serializers.CharField(help_text="The access token issued upon success.")


class LogoutResponseSerializer(serializers.Serializer):
    """Serializer for the response returned after a successful logout."""

    detail = serializers.CharField(help_text="A message indicating that the logout was successful.")


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    detail = serializers.CharField(help_text="A message describing the error.")
