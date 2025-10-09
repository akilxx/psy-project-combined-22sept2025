"""Utilities for managing subscription lifecycle, allowances, and Stripe integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from authentication.models import User
from testing.models import PsychometricTest

from .models import SubscriptionPlan, TestAllowanceLedger, UserSubscription

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionBalance:
    subscription: UserSubscription
    remaining_tests: Optional[int]
    plan_unlimited: bool

    @property
    def is_unlimited(self) -> bool:
        return self.plan_unlimited


def _set_stripe_api_key():
    if not getattr(settings, "STRIPE_SECRET_KEY", None):
        raise ValueError("Stripe secret key is not configured.")
    stripe.api_key = settings.STRIPE_SECRET_KEY


def ensure_stripe_customer(user: User) -> str:
    """Return the Stripe customer ID for the given user, creating one if necessary."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    _set_stripe_api_key()
    customer = stripe.Customer.create(email=user.email)
    user.stripe_customer_id = customer["id"]
    user.save(update_fields=["stripe_customer_id"])
    return user.stripe_customer_id


def create_subscription(
    *,
    user: User,
    plan: SubscriptionPlan,
    payment_method_id: Optional[str] = None,
) -> UserSubscription:
    """Create a Stripe subscription and corresponding local records."""
    if not plan.is_active:
        raise ValueError("Cannot subscribe to an inactive plan.")
    if not plan.stripe_price_id:
        raise ValueError("Plan is missing a Stripe price identifier.")

    customer_id = ensure_stripe_customer(user)

    _set_stripe_api_key()
    if payment_method_id:
        logger.debug("Attaching payment method %s to customer %s", payment_method_id, customer_id)
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

    logger.info("Creating Stripe subscription for user %s on plan %s", user.email, plan.slug)
    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": plan.stripe_price_id}],
        expand=["latest_invoice.payment_intent"],
    )

    with transaction.atomic():
        user_subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            status=subscription["status"],
            stripe_subscription_id=subscription["id"],
            stripe_customer_id=customer_id,
            current_period_start=_parse_timestamp(subscription.get("current_period_start")),
            current_period_end=_parse_timestamp(subscription.get("current_period_end")),
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
        )

        if not plan.unlimited_tests and plan.monthly_allowance:
            logger.debug(
                "Posting initial allowance of %s tests for subscription %s",
                plan.monthly_allowance,
                user_subscription.id,
            )
            user_subscription.record_accrual(plan.monthly_allowance, note="Initial monthly allowance")

    return user_subscription


def record_monthly_accruals(reference_time: Optional[datetime] = None) -> int:
    """Accrue monthly allowances for all active subscriptions whose period has ended."""
    reference_time = reference_time or timezone.now()
    count = 0
    subscriptions = UserSubscription.objects.filter(
        status=UserSubscription.STATUS_ACTIVE,
        is_active=True,
        plan__unlimited_tests=False,
        plan__monthly_allowance__gt=0,
        current_period_end__lte=reference_time,
    )

    for subscription in subscriptions:
        logger.info("Accruing allowance for subscription %s", subscription.id)
        with transaction.atomic():
            subscription.record_accrual(
                subscription.plan.monthly_allowance,
                note=f"Monthly allowance for period ending {subscription.current_period_end}",
            )
            _advance_subscription_period(subscription)
        count += 1

    return count


def consume_allowance(
    *,
    subscription: UserSubscription,
    test: Optional[PsychometricTest] = None,
    quantity: int = 1,
) -> Optional[TestAllowanceLedger]:
    if subscription.plan.unlimited_tests:
        logger.debug("Subscription %s has unlimited allowance; no ledger entry created.", subscription.id)
        return None

    if quantity <= 0:
        raise ValueError("Quantity must be positive when consuming allowance.")

    if subscription.remaining_tests is not None and subscription.remaining_tests < quantity:
        raise ValueError("Insufficient allowance to consume the requested quantity.")

    if subscription.plan.allowed_tests.exists() and test and test not in subscription.plan.allowed_tests.all():
        raise ValueError("The selected test is not permitted by this plan.")

    return subscription.record_consumption(quantity=quantity, test=test)


def subscription_balance(subscription: UserSubscription) -> SubscriptionBalance:
    return SubscriptionBalance(
        subscription=subscription,
        remaining_tests=subscription.remaining_tests,
        plan_unlimited=subscription.plan.unlimited_tests,
    )


def handle_subscription_webhook_event(event_type: str, data: dict) -> dict:
    subscription_id = data.get("id") or data.get("subscription")
    if not subscription_id:
        return {"error": "Subscription identifier missing from webhook payload."}

    try:
        user_subscription = UserSubscription.objects.select_related("plan").get(
            stripe_subscription_id=subscription_id
        )
    except UserSubscription.DoesNotExist:
        logger.warning("Received webhook for unknown subscription %s", subscription_id)
        return {"error": "Subscription not found."}

    logger.info("Handling subscription webhook %s for subscription %s", event_type, subscription_id)

    if event_type == "invoice.payment_succeeded":
        _sync_period_from_invoice(user_subscription, data)
        if not user_subscription.plan.unlimited_tests and user_subscription.plan.monthly_allowance:
            logger.debug("Posting renewal allowance for subscription %s", user_subscription.id)
            user_subscription.record_accrual(
                user_subscription.plan.monthly_allowance,
                note="Monthly renewal allowance",
            )
        user_subscription.status = UserSubscription.STATUS_ACTIVE
        user_subscription.save(update_fields=["status", "current_period_start", "current_period_end", "updated_at"])
    elif event_type == "customer.subscription.deleted":
        user_subscription.status = UserSubscription.STATUS_CANCELED
        user_subscription.is_active = False
        user_subscription.ended_at = timezone.now()
        user_subscription.save(update_fields=["status", "is_active", "ended_at", "updated_at"])
    elif event_type == "customer.subscription.updated":
        user_subscription.status = data.get("status", user_subscription.status)
        user_subscription.cancel_at_period_end = data.get("cancel_at_period_end", False)
        _sync_period_from_subscription_object(user_subscription, data)
        user_subscription.save(
            update_fields=["status", "cancel_at_period_end", "current_period_start", "current_period_end", "updated_at"],
        )
    else:
        logger.info("Unhandled subscription webhook event type %s", event_type)
        return {"status": "ignored"}

    return {"status": "success"}


def _parse_timestamp(timestamp: Optional[int]) -> Optional[datetime]:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def _advance_subscription_period(subscription: UserSubscription) -> None:
    current_end = subscription.current_period_end or timezone.now()
    subscription.current_period_start = current_end
    subscription.current_period_end = current_end + timedelta(days=30)
    subscription.save(update_fields=["current_period_start", "current_period_end", "updated_at"])


def _sync_period_from_invoice(subscription: UserSubscription, data: dict) -> None:
    lines = data.get("lines", {}).get("data", [])
    if lines:
        period = lines[0].get("period", {})
        subscription.current_period_start = _parse_timestamp(period.get("start"))
        subscription.current_period_end = _parse_timestamp(period.get("end"))


def _sync_period_from_subscription_object(subscription: UserSubscription, data: dict) -> None:
    subscription.current_period_start = _parse_timestamp(data.get("current_period_start"))
    subscription.current_period_end = _parse_timestamp(data.get("current_period_end"))

