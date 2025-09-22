# reportgeneration/urls.py

from django.urls import path
from .views import get_test_report

app_name = 'reportgeneration'

urlpatterns = [
    path('test_report/<uuid:payment_id>/', get_test_report, name='get_test_report'),
]
