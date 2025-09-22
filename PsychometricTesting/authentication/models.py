# authentication/models.py


from django.db import models
import logging
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Configure logging
logger = logging.getLogger(__name__)

#---------------------------------------------OTP Login System--------------------------------------------------------------------------------


class UserManager(BaseUserManager):
    def create_user(self, email, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_unusable_password()  # Disable password login
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        user = self.create_user(email, **extra_fields)
        user.set_password(password)  # Superusers need a password
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # Add any additional fields if necessary

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class PendingRegistration(models.Model):
    email = models.EmailField()
    registration_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    otp_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    failed_attempts = models.IntegerField(default=0)
    is_valid = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_valid']),
        ]

    def __str__(self):
        return f"{self.email} ({self.registration_id})"