# blog/models.py
from django.db import models


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    author_name = models.CharField(max_length=255)
    author_bio = models.TextField(help_text="HTML content allowed")
    introduction = models.TextField(help_text="HTML content allowed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Section(models.Model):
    blogpost = models.ForeignKey(BlogPost, related_name="sections", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    body = models.TextField(help_text="HTML content allowed")
    order = models.PositiveIntegerField(
        null=True,  # Allow NULL values in the database
        blank=True,  # Allow the field to be empty in forms
        help_text="Position in the blog post. Lower numbers appear first. If left blank, will appear after ordered items."
    )

    def __str__(self):
        return f"{self.blogpost.title} - {self.title}"


class BlogImage(models.Model):
    blogpost = models.ForeignKey(BlogPost, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="blog_images/")
    caption = models.TextField(help_text="HTML content allowed")
    order = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Position in the blog post. Lower numbers appear first. If left blank, will appear after ordered items."
    )

    def __str__(self):
        return f"{self.blogpost.title} Image"
