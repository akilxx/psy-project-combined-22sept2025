
# authentication/serializers.py


from rest_framework import serializers
from .models import PendingRegistration
from django.contrib.auth import get_user_model
from django.utils import timezone
import random


User = get_user_model()


#---------------------------------------------OTP Verification System----------------------------------------------------------------

class RegistrationSerializer(serializers.ModelSerializer):
    """
        Serializer for user registration, handles the creation of a pending registration with an OTP.
    """

    email = serializers.EmailField(
        help_text='The email address of the user registering.'
    )
    class Meta:
        model = PendingRegistration
        fields = ('email',)

    def validate(self, data):
        email = data.get('email')

        # Check if email is already registered
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Email is already registered.'})

        # Check if a valid pending registration exists
        if PendingRegistration.objects.filter(email=email, is_valid=True).exists():
            raise serializers.ValidationError({'email': 'An OTP has already been sent to this email. Please check your inbox.'})

        return data

    def create(self, validated_data):
        email = validated_data.get('email')

        # Invalidate all existing pending registrations for this email
        PendingRegistration.objects.filter(email=email).update(is_valid=False)

        # Generate a 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        # Set expiration time to 10 minutes from now
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        pending_registration = PendingRegistration.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at,
            failed_attempts=0,
            is_valid=True
        )
        return pending_registration

class VerifyRegistrationSerializer(serializers.Serializer):
    """
        Serializer for verifying the OTP code during user registration.
    """

    registration_id = serializers.UUIDField(help_text='The unique identifier of the pending registration.')
    otp_code = serializers.CharField(max_length=6, help_text="The 6-digit OTP code sent to the user's email.")
    MAX_FAILED_ATTEMPTS = 3  # Maximum allowed attempts

    def validate(self, data):
        registration_id = data.get('registration_id')
        otp_code = data.get('otp_code')

        try:
            pending_registration = PendingRegistration.objects.get(registration_id=registration_id)
        except PendingRegistration.DoesNotExist:
            raise serializers.ValidationError({'registration_id': 'Invalid or expired registration ID.'})

        # Check if the pending registration has expired
        if pending_registration.expires_at < timezone.now():
            # Invalidate the pending registration
            pending_registration.is_valid = False
            pending_registration.save()
            raise serializers.ValidationError({'registration_id': 'This registration has expired. Please register again.'})

        # Check if maximum failed attempts have been reached
        if pending_registration.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            # Invalidate the pending registration
            pending_registration.is_valid = False
            pending_registration.save()
            raise serializers.ValidationError({'otp_code': 'Maximum verification attempts exceeded. Please register again.'})

        # Check if the pending registration is still valid
        if not pending_registration.is_valid:
            raise serializers.ValidationError({'registration_id': 'This registration has expired. Please register again.'})

        # Check if OTP matches
        if pending_registration.otp_code != otp_code:
            # Increment failed attempts
            pending_registration.failed_attempts += 1
            pending_registration.save()
            attempts_left = self.MAX_FAILED_ATTEMPTS - pending_registration.failed_attempts
            if attempts_left <= 0:
                # Invalidate the pending registration
                pending_registration.is_valid = False
                pending_registration.save()
                raise serializers.ValidationError({'otp_code': 'Maximum verification attempts exceeded. Please register again.'})
            else:
                raise serializers.ValidationError({'otp_code': f'Invalid OTP code. You have {attempts_left} attempts left.'})

        data['pending_registration'] = pending_registration
        return data

class RequestOTPSerializer(serializers.Serializer):
    """
        Serializer for requesting an OTP code for login.
    """
    email = serializers.EmailField(help_text='The email address of the user requesting an OTP.')

    def validate(self, data):
        email = data.get('email')

        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'non_field_errors': ['User not found.']})

        # Check for existing valid pending registrations
        existing_pending = PendingRegistration.objects.filter(
            email=email,
            is_valid=True,
            expires_at__gt=timezone.now()
        ).first()

        if existing_pending:
            raise serializers.ValidationError({
                'detail': 'An OTP has already been sent and is still valid. Please check your email or request a new OTP after it expires.'
            })

        return data

    def create(self, validated_data):
        email = validated_data.get('email')

        # Invalidate all existing pending registrations for this email
        PendingRegistration.objects.filter(email=email).update(is_valid=False)

        # Generate a 6-digit OTP
        otp_code = str(random.randint(100000, 999999))
        # Set expiration time to 10 minutes from now
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        pending_registration = PendingRegistration.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at,
            failed_attempts=0,
            is_valid=True
        )
        return validated_data

class VerifyOTPSerializer(serializers.Serializer):
    """
        Serializer for verifying the OTP code during user login.
    """
    email = serializers.EmailField(help_text='The email address of the user logging in.')
    otp_code = serializers.CharField(max_length=6, help_text="The 6-digit OTP code sent to the user's email.")
    MAX_FAILED_ATTEMPTS = 3  # Maximum allowed attempts

    def validate(self, data):
        email = data.get('email')
        otp_code = data.get('otp_code')

        # Retrieve all pending registrations for the email, ordered by newest first
        pending_registrations = PendingRegistration.objects.filter(email=email).order_by('-created_at')

        if not pending_registrations.exists():
            raise serializers.ValidationError({'email': 'No pending OTP found for this email. Please request a new OTP.'})

        # Get the most recent pending registration
        pending_registration = pending_registrations.first()

        # Check if the pending OTP has expired
        if pending_registration.expires_at < timezone.now():
            # Invalidate the pending registration
            pending_registration.is_valid = False
            pending_registration.save()
            raise serializers.ValidationError({'otp_code': 'This OTP has expired. Please request a new OTP.'})

        # Check if maximum failed attempts have been reached
        if pending_registration.failed_attempts >= self.MAX_FAILED_ATTEMPTS:
            # Invalidate the pending registration
            pending_registration.is_valid = False
            pending_registration.save()
            raise serializers.ValidationError(
                {'otp_code': 'Maximum verification attempts exceeded. Please request a new OTP.'})

        # Check if the pending registration is still valid
        if not pending_registration.is_valid:
            raise serializers.ValidationError({'otp_code': 'This OTP is no longer valid. Please request a new OTP.'})

        # Check if OTP matches
        if pending_registration.otp_code != otp_code:
            # Increment failed attempts
            pending_registration.failed_attempts += 1
            pending_registration.save()
            attempts_left = self.MAX_FAILED_ATTEMPTS - pending_registration.failed_attempts
            if attempts_left <= 0:
                # Invalidate the pending registration
                pending_registration.is_valid = False
                pending_registration.save()
                raise serializers.ValidationError({'otp_code': 'Maximum verification attempts exceeded. Please request a new OTP.'})
            else:
                raise serializers.ValidationError({'otp_code': f'Invalid OTP code. You have {attempts_left} attempts left.'})

        data['user'] = User.objects.get(email=email)
        data['pending_registration'] = pending_registration  # Include pending_registration for view
        return data


class RegistrationResponseSerializer(serializers.Serializer):
    """
        Serializer for the response returned after a successful registration request.
    """
    detail = serializers.CharField(help_text="A message indicating that the OTP was sent to the user's email.")
    registration_id = serializers.UUIDField(help_text="The unique identifier for the pending registration.")

class VerifyRegistrationResponseSerializer(serializers.Serializer):
    """
        Serializer for the response returned after successful OTP verification during registration.
    """
    detail = serializers.CharField(help_text="A message indicating that the registration was successful.")
    refresh = serializers.CharField(help_text="The refresh token issued upon successful registration.")
    access = serializers.CharField(help_text="The access token issued upon successful registration.")

class OTPResponseSerializer(serializers.Serializer):
    """
       Serializer for the response returned after requesting an OTP for login.
    """
    detail = serializers.CharField(help_text="A message indicating that the OTP was sent to the user's email.")

class VerifyOTPResponseSerializer(serializers.Serializer):
    """
        Serializer for the response returned after successful OTP verification during login.
    """
    detail = serializers.CharField(help_text="A message indicating that the login was successful.")
    refresh = serializers.CharField(help_text="The refresh token issued upon successful login.")
    access = serializers.CharField(help_text="The access token issued upon successful login.")

class LogoutResponseSerializer(serializers.Serializer):
    """
        Serializer for the response returned after a successful logout.
    """
    detail = serializers.CharField(help_text="A message indicating that the logout was successful.")

class ErrorResponseSerializer(serializers.Serializer):
    """
        Serializer for error responses.
    """
    detail = serializers.CharField(help_text="A message describing the error.")