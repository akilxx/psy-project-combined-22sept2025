# testing/urls.py

from django.urls import path
from .views import CreatePaymentView, StripeWebhookView

app_name = 'payment'

urlpatterns = [
    path('payments/create/', CreatePaymentView.as_view(), name='create-payment'),
    path('payments/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
