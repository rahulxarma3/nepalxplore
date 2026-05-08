from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ("new_video",       "New video published"),
        ("sub_expiring",    "Subscription expiring soon"),
        ("sub_expired",     "Subscription expired"),
        ("sub_activated",   "Subscription activated"),
        ("welcome",         "Welcome message"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    link = models.CharField(max_length=500, blank=True)  # internal URL
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.get_notification_type_display()}"

    @classmethod
    def create_for_user(cls, user, notification_type, title, body, link=""):
        """Create notification only if user has notifications enabled."""
        if not user.notifications_enabled:
            return None
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            link=link,
        )

    @classmethod
    def broadcast_new_video(cls, video):
        """Notify all active subscribers when a new video is published."""
        from apps.subscriptions.models import Subscription
        from django.utils import timezone

        active_users = (
            Subscription.objects.filter(status="active", end_date__gt=timezone.now())
            .select_related("user")
            .values_list("user", flat=True)
        )

        from django.contrib.auth import get_user_model
        User = get_user_model()

        notifications = []
        for user in User.objects.filter(
            pk__in=active_users,
            notifications_enabled=True,
        ):
            notifications.append(cls(
                user=user,
                notification_type="new_video",
                title=f"New: {video.title}",
                body=f"A new video has been published{' in ' + video.location if video.location else ''}. Watch it now.",
                link=f"/feed/video/{video.slug}/",
            ))

        cls.objects.bulk_create(notifications)
        return len(notifications)
