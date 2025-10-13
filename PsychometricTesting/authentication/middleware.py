# authentication/middleware.py


from django.utils import timezone

from .models import PendingRegistration
from .serializers import OTPFlowSerializer



class PendingRegistrationCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Run cleanup on relevant URLs
        if request.path == '/otp/':
            # Invalidate expired pending registrations
            PendingRegistration.objects.filter(
                expires_at__lt=timezone.now(),
                is_valid=True
            ).update(is_valid=False)

            # Invalidate pending registrations with maximum failed attempts
            PendingRegistration.objects.filter(
                failed_attempts__gte=OTPFlowSerializer.MAX_FAILED_ATTEMPTS,
                is_valid=True
            ).update(is_valid=False)

        response = self.get_response(request)
        return response
