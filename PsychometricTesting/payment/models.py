# payment/models.py

from django.db import models
from django.utils import timezone
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


class SubscriptionPlan(models.Model):
    INTERVAL_MONTHLY = "monthly"
    INTERVAL_CHOICES = [
        (INTERVAL_MONTHLY, "Monthly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default="usd")
    billing_interval = models.CharField(
        max_length=32,
        choices=INTERVAL_CHOICES,
        default=INTERVAL_MONTHLY,
        help_text="Billing frequency for the plan. Only monthly is currently supported.",
    )
    monthly_allowance = models.PositiveIntegerField(
        help_text="Number of tests granted per billing cycle when not unlimited.",
        default=0,
    )
    unlimited_tests = models.BooleanField(
        default=False,
        help_text="When true the subscriber may take unlimited tests without consuming allowance.",
    )
    allowed_tests = models.ManyToManyField(
        "testing.PsychometricTest",
        blank=True,
        related_name="subscription_plans",
        help_text="Optional whitelist of tests the plan grants access to.",
    )
    stripe_product_id = models.CharField(max_length=255, blank=True)
    stripe_price_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_INCOMPLETE = "incomplete"
    STATUS_INCOMPLETE_EXPIRED = "incomplete_expired"
    STATUS_TRIALING = "trialing"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELED = "canceled"
    STATUS_UNPAID = "unpaid"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INCOMPLETE, "Incomplete"),
        (STATUS_INCOMPLETE_EXPIRED, "Incomplete Expired"),
        (STATUS_TRIALING, "Trialing"),
        (STATUS_PAST_DUE, "Past Due"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_UNPAID, "Unpaid"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("authentication.User", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_INCOMPLETE)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "is_active"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscription for {self.user.email} - {self.plan.name}"

    @property
    def remaining_tests(self):
        if self.plan.unlimited_tests:
            return None
        total = self.ledger_entries.aggregate(total=models.Sum("quantity"))
        return total["total"] or 0

    def record_accrual(self, quantity, note="Monthly allowance", test=None):
        if self.plan.unlimited_tests:
            return None
        return TestAllowanceLedger.objects.create(
            subscription=self,
            entry_type=TestAllowanceLedger.ENTRY_ACCRUAL,
            quantity=quantity,
            test=test,
            note=note,
        )

    def record_consumption(self, quantity=1, test=None, note="Test consumption"):
        if self.plan.unlimited_tests:
            return None
        return TestAllowanceLedger.objects.create(
            subscription=self,
            entry_type=TestAllowanceLedger.ENTRY_CONSUMPTION,
            quantity=-abs(quantity),
            test=test,
            note=note,
        )


class TestAllowanceLedger(models.Model):
    ENTRY_ACCRUAL = "accrual"
    ENTRY_CONSUMPTION = "consumption"
    ENTRY_ADJUSTMENT = "adjustment"

    ENTRY_CHOICES = [
        (ENTRY_ACCRUAL, "Accrual"),
        (ENTRY_CONSUMPTION, "Consumption"),
        (ENTRY_ADJUSTMENT, "Adjustment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    entry_type = models.CharField(max_length=32, choices=ENTRY_CHOICES)
    quantity = models.IntegerField(help_text="Positive for accrual, negative for consumption.")
    test = models.ForeignKey("testing.PsychometricTest", on_delete=models.SET_NULL, blank=True, null=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    effective_date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.entry_type} {self.quantity} for {self.subscription}"