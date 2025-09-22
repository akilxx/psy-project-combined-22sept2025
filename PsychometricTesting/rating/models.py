# rating/models.py

from django.db import models
from payment.models import Payment
import uuid
from django.contrib.auth import get_user_model



User = get_user_model()

# Model to store the one-time token sent via email.
class FeedbackToken(models.Model):
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='feedback_token'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FeedbackToken for Payment {self.payment.id}"

# Choices for rating values.
RATING_CHOICES = [
    (1, '1 - Very Unsatisfied'),
    (2, '2 - Unsatisfied'),
    (3, '3 - Neutral'),
    (4, '4 - Satisfied'),
    (5, '5 - Very Satisfied'),
]

# Model to store the customer rating.
class Rating(models.Model):
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='rating'
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating for Payment {self.payment.id}: {self.rating}"


class TrustpilotReview(models.Model):
    review_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    rating = models.IntegerField()
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    # A reference to correlate the review with your internal records (e.g., order ID)
    reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review {self.review_id} - Rating: {self.rating}"