# testing/urls.py

from django.urls import path
from .views import (
    CreatePaymentView,
    CurrentSubscriptionView,
    StripeWebhookView,
    SubscriptionCancelView,
    SubscriptionCreateView,
    SubscriptionPlanListView,
)

app_name = 'payment'

urlpatterns = [
    path('payments/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payments/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('subscriptions/plans/', SubscriptionPlanListView.as_view(), name='subscription-plans'),
    path('subscriptions/', SubscriptionCreateView.as_view(), name='subscription-create'),
    path('subscriptions/me/', CurrentSubscriptionView.as_view(), name='subscription-current'),
    path('subscriptions/me/cancel/', SubscriptionCancelView.as_view(), name='subscription-cancel'),
]
