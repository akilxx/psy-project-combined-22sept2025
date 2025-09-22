# rating/urls.py


from django.urls import path
from .views import SubmitRatingAPIView


urlpatterns = [
    path('feedback/', SubmitRatingAPIView.as_view(), name='submit_rating_api'),
]
