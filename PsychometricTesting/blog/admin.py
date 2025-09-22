
# blog/admin.py

from django.contrib import admin
from .models import BlogPost, Section, BlogImage

class SectionInline(admin.StackedInline):
    model = Section
    extra = 1  # how many empty forms to display


class BlogImageInline(admin.StackedInline):
    model = BlogImage
    extra = 1


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author_name', 'created_at', 'updated_at')
    inlines = [SectionInline, BlogImageInline]
