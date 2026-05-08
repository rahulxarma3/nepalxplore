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
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("icon", models.CharField(blank=True, max_length=50)),
                ("order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"verbose_name_plural": "categories", "ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="Video",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("title", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True, blank=True)),
                ("description", models.TextField()),
                ("category", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="videos", to="content.category",
                )),
                ("video_file", models.FileField(upload_to="videos/")),
                ("thumbnail", models.ImageField(upload_to="thumbnails/")),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("location", models.CharField(blank=True, max_length=200)),
                ("language", models.CharField(
                    choices=[("en", "English"), ("ne", "Nepali"), ("both", "Both")],
                    default="en", max_length=4,
                )),
                ("is_feed_preview", models.BooleanField(default=False)),
                ("is_published", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(null=True, blank=True)),
                ("view_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-published_at"]},
        ),
        migrations.CreateModel(
            name="WatchHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="watch_history", to=settings.AUTH_USER_MODEL,
                )),
                ("video", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="watches", to="content.video",
                )),
                ("watched_at", models.DateTimeField(auto_now=True)),
                ("progress_seconds", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["-watched_at"], "unique_together": {("user", "video")}},
        ),
        migrations.CreateModel(
            name="SavedVideo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="saved_videos", to=settings.AUTH_USER_MODEL,
                )),
                ("video", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="saves", to="content.video",
                )),
                ("saved_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"unique_together": {("user", "video")}},
        ),
    ]
