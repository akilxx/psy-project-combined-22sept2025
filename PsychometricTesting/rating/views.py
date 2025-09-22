# rating/views.py
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import status
from .models import FeedbackToken, Rating
from .serializers import SubmitRatingSerializer


class SubmitRatingAPIView(APIView):
    def get(self, request, *args, **kwargs):
        serializer = SubmitRatingSerializer(data=request.query_params)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            rating_value = serializer.validated_data['rating']
            try:
                feedback_token = FeedbackToken.objects.get(token=token)
            except FeedbackToken.DoesNotExist:
                return HttpResponse(
                    self.render_centered("Invalid or expired token."),
                    status=status.HTTP_400_BAD_REQUEST,
                    content_type="text/html"
                )

            payment = feedback_token.payment

            # Check if a rating has already been submitted
            if hasattr(payment, 'rating'):
                return HttpResponse(
                    self.render_centered("Rating already submitted."),
                    status=status.HTTP_200_OK,
                    content_type="text/html"
                )

            Rating.objects.create(payment=payment, rating=rating_value)
            feedback_token.delete()  # Invalidate the token

            return HttpResponse(
                self.render_centered("Thank you for your feedback!"),
                status=status.HTTP_200_OK,
                content_type="text/html"
            )
        else:
            return HttpResponse(
                self.render_centered(str(serializer.errors)),
                status=status.HTTP_400_BAD_REQUEST,
                content_type="text/html"
            )

    def render_centered(self, message):
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <title>Feedback Response</title>
          <style>
            body {{
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
              margin: 0;
              font-family: Arial, sans-serif;
            }}
            .message {{
              text-align: center;
              font-size: 1.5em;
            }}
          </style>
        </head>
        <body>
          <div class="message">{message}</div>
        </body>
        </html>
        """
        return html_content
