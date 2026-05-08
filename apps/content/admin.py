from django.contrib import admin
from .models import Video, Category, WatchHistory

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "order"]
    prepopulated_fields = {"slug": ["name"]}

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "is_feed_preview", "is_published", "view_count"]
    list_filter = ["category", "is_feed_preview", "is_published"]
    search_fields = ["title", "description", "location"]
    prepopulated_fields = {"slug": ["title"]}
    list_editable = ["is_feed_preview", "is_published"]


# Override save_model to auto-notify subscribers when video is published
from django.contrib import admin as _admin

_original_VideoAdmin = VideoAdmin

class VideoAdmin(_original_VideoAdmin):
    def save_model(self, request, obj, form, change):
        was_published = False
        if change:
            try:
                old = type(obj).objects.get(pk=obj.pk)
                was_published = not old.is_published and obj.is_published
            except type(obj).DoesNotExist:
                pass
        else:
            was_published = obj.is_published

        super().save_model(request, obj, form, change)

        if was_published:
            from apps.core.models import Notification
            count = Notification.broadcast_new_video(obj)
            self.message_user(
                request,
                f'"{obj.title}" published. Notified {count} subscriber(s).',
                level="success",
            )

# Re-register with the enhanced version
_admin.site.unregister(Video)
_admin.site.register(Video, VideoAdmin)
