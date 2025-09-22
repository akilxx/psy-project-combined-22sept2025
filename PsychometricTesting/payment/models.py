# payment/models.py

from django.db import models
import logging
import uuid


# Configure logging
logger = logging.getLogger(__name__)



#------------------------------Payment System---------------------------------------------------------------------------------------------


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('requires_action', 'Requires Action'),
        ('processing', 'Processing'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('refund_requested', 'Refund Requested'),
        ('refund_succeeded', 'Refund Succeeded'),
    ]

    REFUND_STATUS_CHOICES = [
        ('not_refunded', 'Not Refunded'),
        ('requested', 'Refund Requested'),
        ('succeeded', 'Succeeded'),
        ('attention_required', 'Attention Required'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE)
    test = models.ForeignKey('testing.PsychometricTest', on_delete=models.PROTECT, null=True, blank=True)
    test_result = models.ForeignKey('testing.TestResult', to_field='uuid', on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    payment_method = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    refund_status = models.CharField(max_length=50, choices=REFUND_STATUS_CHOICES, default='not_refunded')
    refund_id = models.CharField(max_length=255, null=True, blank=True)
    refund_reason = models.TextField(null=True, blank=True)
    error_details = models.JSONField(default=dict, null=True, blank=True)
    refund_error_details = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} - {self.status}"


class StripeEvent(models.Model):
    """
    Model to store Stripe event IDs that have been processed to prevent duplicates.
    """
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"StripeEvent: {self.event_id} ({self.event_type})"