# reportgeneration/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Fetch a generated report
    path('report/<uuid:test_result_id>/', views.get_test_report, name='get_test_report'),

    # Unlock a report using subscription credits
    path('report/<uuid:test_result_id>/unlock/', views.unlock_report_with_subscription, name='unlock_report'),
]