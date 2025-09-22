# payment/serializers.py

from rest_framework import serializers
from .models import Payment
from django.contrib.auth import get_user_model


User = get_user_model()


#------------------------------Payment System---------------------------------------------------------------------------------------------



class PaymentSerializer(serializers.ModelSerializer):
    # Make error_details and refund_error_details read-only JSON fields
    error_details = serializers.JSONField(read_only=True)
    # If you also need refund_error_details serialized:
    refund_error_details = serializers.JSONField(read_only=True)
    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'currency', 'status', 'payment_method',
            'refund_status', 'refund_id', 'refund_reason', 'error_details', 'refund_error_details',
            'test', 'test_result', 'country'
        ]
        # Ensure that error_details (and refund_error_details if used) are not editable directly
        extra_kwargs = {
            'error_details': {'read_only': True},
            'refund_error_details': {'read_only': True},
        }

# New Response Serializer for Payment creation endpoint
class PaymentCreationResponseSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField(help_text="The ID of the payment record.")
    payment_intent = serializers.CharField(help_text="Stripe PaymentIntent ID.")
    status = serializers.CharField(help_text="Current status of the payment.")
