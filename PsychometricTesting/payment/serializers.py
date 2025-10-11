# payment/serializers.py

from rest_framework import serializers
from .models import (
    Payment,
    SubscriptionPlan,
    UserSubscription,
)
from .subscription_service import subscription_balance
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


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price",
            "currency",
            "billing_interval",
            "monthly_allowance",
            "unlimited_tests",
        ]


class SubscriptionCreateSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    payment_method_id = serializers.CharField(required=False, allow_blank=True)

    def validate_plan_id(self, value):
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
        except SubscriptionPlan.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid or inactive subscription plan.") from exc
        return plan

    def create(self, validated_data):
        raise NotImplementedError("Use the payment view to create subscriptions.")


class SubscriptionCancelSerializer(serializers.Serializer):
    cancel_at_period_end = serializers.BooleanField(
        default=True,
        help_text="When true, the subscription remains active until the current period ends.",
    )


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    remaining_tests = serializers.SerializerMethodField()
    is_unlimited = serializers.SerializerMethodField()

    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "plan",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "remaining_tests",
            "is_unlimited",
        ]

    def get_remaining_tests(self, obj):
        balance = subscription_balance(obj)
        return balance.remaining_tests

    def get_is_unlimited(self, obj):
        balance = subscription_balance(obj)
        return balance.is_unlimited
