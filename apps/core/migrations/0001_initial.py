from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("notification_type", models.CharField(
                    choices=[
                        ("new_video", "New video published"),
                        ("sub_expiring", "Subscription expiring soon"),
                        ("sub_expired", "Subscription expired"),
                        ("sub_activated", "Subscription activated"),
                        ("welcome", "Welcome message"),
                    ],
                    max_length=20,
                )),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("link", models.CharField(blank=True, max_length=500)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
