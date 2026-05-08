from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user — email is the primary identifier."""
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    preferred_language = models.CharField(
        max_length=4,
        choices=[("en", "English"), ("ne", "Nepali")],
        default="en",
    )
    dark_mode = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.get_full_name() or self.email.split("@")[0]

    @property
    def is_subscribed(self):
        return hasattr(self, "subscription") and self.subscription.is_active
