# authentication/middleware.py


from django.utils import timezone
from .models import PendingRegistration
from .serializers import VerifyRegistrationSerializer, VerifyOTPSerializer



class PendingRegistrationCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Run cleanup on relevant URLs
        if request.path in ['/register/', '/verify-registration/', '/verify-otp/']:
            # Invalidate expired pending registrations
            PendingRegistration.objects.filter(
                expires_at__lt=timezone.now(),
                is_valid=True
            ).update(is_valid=False)

            # Invalidate pending registrations with maximum failed attempts
            max_attempts = max(
                VerifyRegistrationSerializer.MAX_FAILED_ATTEMPTS,
                VerifyOTPSerializer.MAX_FAILED_ATTEMPTS
            )
            PendingRegistration.objects.filter(
                failed_attempts__gte=max_attempts,
                is_valid=True
            ).update(is_valid=False)

        response = self.get_response(request)
        return response