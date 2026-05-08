from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.cache import cache

# import boto3
# from botocore.config import Config


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["order"]

    def __str__(self):
        return self.name


class Video(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="videos",
    )

    video_file = models.FileField(upload_to="videos/")
    thumbnail = models.ImageField(upload_to="thumbnails/", blank=True, null=True)

    duration_seconds = models.PositiveIntegerField(default=0)

    location = models.CharField(max_length=200, blank=True)
    language = models.CharField(
        max_length=4,
        choices=[
            ("en", "English"),
            ("ne", "Nepali"),
            ("both", "Both"),
        ],
        default="en",
    )

    is_feed_preview = models.BooleanField(
        default=False,
        help_text="Show on public feed — no subscription needed",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1

            while Video.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    # @property
    # def video_url(self):
        # if not self.video_file:
            # return None

        # if settings.DEBUG:
            # return self.video_file.url

        # cache_key = f"video_url_{self.pk}"
        # cached_url = cache.get(cache_key)

        # if cached_url:
            # return cached_url

        # try:
            # client = boto3.client(
            #     "s3",
            #     endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            #     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            #     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            #     config=Config(signature_version="s3v4"),
            #     region_name="auto",
            # )

            # url = client.generate_presigned_url(
            #     "get_object",
            #     Params={
            #         "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            #         "Key": self.video_file.name,
            #         "ResponseContentType": "video/mp4",
            #     },
            #     ExpiresIn=7200,
            # )

            # cache.set(cache_key, url, 6000)
            # return url

        # except Exception:
       
     #     return self.video_file.url
    @property
    def video_url(self):
     if self.video_file:
        return self.video_file.url
     return None

    @property
    def thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        return "/static/images/placeholder.jpg"

    @property
    def duration_display(self):
        minutes, seconds = divmod(self.duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"


class WatchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watch_history",
    )
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="watches",
    )
    watched_at = models.DateTimeField(auto_now=True)
    progress_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["user", "video"]
        ordering = ["-watched_at"]

    def __str__(self):
        return f"{self.user} watched {self.video}"


class SavedVideo(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_videos",
    )
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name="saves",
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "video"]
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.user} saved {self.video}"