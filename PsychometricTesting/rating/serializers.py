# rating/serializers.py
from rest_framework import serializers
from .models import TrustpilotReview, Rating

class TrustpilotReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustpilotReview
        fields = '__all__'

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['payment', 'rating', 'created_at']
        read_only_fields = ['created_at', 'payment']

class SubmitRatingSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)