# blog/views.py


from rest_framework import generics
from .models import BlogPost
from .serializers import BlogPostSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view


@extend_schema_view(
    get=extend_schema(
        summary="List All Blog Posts",
        description="Retrieve a list of all blog posts with their ordered contents.",
        responses=BlogPostSerializer(many=True)
    )
)
class BlogPostListAPIView(generics.ListAPIView):
    queryset = BlogPost.objects.all().order_by('-created_at')
    serializer_class = BlogPostSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve a Single Blog Post",
        description="Retrieve a single blog post by its ID, including its sections and images sorted by order.",
        responses=BlogPostSerializer
    )
)
class BlogPostDetailAPIView(generics.RetrieveAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
