# testing/urls.py

from django.urls import path
from .views import TestResultViewSet, TestResultListView

app_name = 'testing'

urlpatterns = [
    path('test/start/', TestResultViewSet.as_view({'post': 'create'}), name='test-start'),
    path('test/', TestResultViewSet.as_view({'get': 'retrieve'}), name='test-detail'),
    path('test/list/', TestResultListView.as_view(), name='test-list'),
    path('test/answer/', TestResultViewSet.as_view({'post': 'submit_or_update_answer'}), name='test-answer'),
    path('test/associate-user/', TestResultViewSet.as_view({'post': 'associate_user'}), name='test-associate-user'),
    path('test/complete/', TestResultViewSet.as_view({'post': 'set_complete'}), name='test-complete'),
]
