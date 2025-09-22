# blog/urls.py


from django.urls import path
from .views import BlogPostListAPIView, BlogPostDetailAPIView

urlpatterns = [
    path('posts/', BlogPostListAPIView.as_view(), name='blogpost-list'),
    path('posts/<int:pk>/', BlogPostDetailAPIView.as_view(), name='blogpost-detail'),
]
