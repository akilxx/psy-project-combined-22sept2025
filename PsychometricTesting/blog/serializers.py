# blog/serializers.py

from rest_framework import serializers
from .models import BlogPost, Section, BlogImage


class SectionSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ('id', 'order', 'title', 'body', 'type')

    def get_type(self, obj):
        return "section"


class BlogImageSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BlogImage
        fields = ('id', 'order', 'image_url', 'caption', 'type')

    def get_type(self, obj):
        return "image"

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class BlogPostSerializer(serializers.ModelSerializer):
    contents = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            'id', 'title', 'author_name', 'author_bio',
            'introduction', 'contents',
            'created_at', 'updated_at'
        )

    def get_contents(self, obj):
        sections = SectionSerializer(
            obj.sections.order_by('order'),
            many=True,  # Specify that you're serializing multiple objects
            context=self.context
        ).data
        images = BlogImageSerializer(
            obj.images.order_by('order'),
            many=True,  # Specify that you're serializing multiple objects
            context=self.context
        ).data

        # Merge the two lists and sort them.
        # Items with a null 'order' value are treated as if their order is 9999.
        combined = list(sections) + list(images)
        combined.sort(key=lambda item: item.get('order') if item.get('order') is not None else 9999)
        return combined
