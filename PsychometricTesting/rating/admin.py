# rating/admin.py

from django.contrib import admin
from .models import Rating


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('payment', 'user_email', 'test_result', 'rating', 'created_at')
    readonly_fields = ('payment', 'rating', 'created_at', 'user_email', 'test_result')

    def user_email(self, obj):
        # Safely access the user email from the related Payment
        return obj.payment.user.email if obj.payment and obj.payment.user else ''

    user_email.short_description = 'User Email'

    def test_result(self, obj):
        # Return a string representation of the test_result if available
        return str(obj.payment.test_result) if obj.payment and obj.payment.test_result else ''

    test_result.short_description = 'Test Result'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
