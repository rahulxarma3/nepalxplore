from django import forms
from .models import Video, Category


class VideoUploadForm(forms.ModelForm):
    """
    Used by staff/admin to upload new videos.
    Shown at /content/upload/ — staff-only view.
    """
    class Meta:
        model = Video
        fields = [
            "title",
            "description",
            "category",
            "video_file",
            "thumbnail",
            "duration_seconds",
            "location",
            "language",
            "is_feed_preview",
            "is_published",
            "published_at",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full bg-surface-hover border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-brand-500",
                "placeholder": "e.g. History of Pashupatinath Temple",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full bg-surface-hover border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-brand-500 resize-none",
                "rows": 4,
                "placeholder": "Describe what viewers will learn...",
            }),
            "category": forms.Select(attrs={
                "class": "w-full bg-surface-hover border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-brand-500",
            }),
            "location": forms.TextInput(attrs={
                "class": "w-full bg-surface-hover border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-brand-500",
                "placeholder": "e.g. Kathmandu, Bagmati Province",
            }),
            "duration_seconds": forms.NumberInput(attrs={
                "class": "w-full bg-surface-hover border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-brand-500",
                "placeholder": "Duration in seconds",
            }),
            "language": forms.Select(attrs={
                "class": "w-full bg-surface-hover border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-brand-500",
            }),
            "published_at": forms.DateTimeInput(attrs={
                "class": "w-full bg-surface-hover border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-brand-500",
                "type": "datetime-local",
            }),
            "is_feed_preview": forms.CheckboxInput(attrs={
                "class": "rounded border-white/20 bg-surface-hover text-brand-500 focus:ring-brand-500",
            }),
            "is_published": forms.CheckboxInput(attrs={
                "class": "rounded border-white/20 bg-surface-hover text-brand-500 focus:ring-brand-500",
            }),
        }

    def clean_video_file(self):
        video = self.cleaned_data.get("video_file")
        if video:
            # Max 2GB
            max_size = 2 * 1024 * 1024 * 1024
            if video.size > max_size:
                raise forms.ValidationError("Video file must be under 2GB.")
            allowed = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
            if hasattr(video, "content_type") and video.content_type not in allowed:
                raise forms.ValidationError("Unsupported video format. Use MP4, WebM, or MOV.")
        return video

    def clean_thumbnail(self):
        thumb = self.cleaned_data.get("thumbnail")
        if thumb:
            max_size = 5 * 1024 * 1024  # 5MB
            if thumb.size > max_size:
                raise forms.ValidationError("Thumbnail must be under 5MB.")
        return thumb
