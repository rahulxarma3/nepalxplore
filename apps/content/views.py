from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET, require_POST
from apps.content.models import Video, Category


def feed(request):
    """Public feed — shows is_feed_preview=True videos only."""
    categories = Category.objects.all()
    category_slug = request.GET.get("category", "")

    videos = Video.objects.filter(is_published=True, is_feed_preview=True)
    if category_slug:
        videos = videos.filter(category__slug=category_slug)

    paginator = Paginator(videos, 6)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # HTMX infinite scroll — return only cards partial
    if request.htmx:
        return render(request, "partials/feed_cards.html", {"page_obj": page_obj})

    return render(request, "content/feed.html", {
        "page_obj": page_obj,
        "categories": categories,
        "active_category": category_slug,
    })


@require_GET
def video_detail(request, slug):
    """Full video page — non-preview videos require active subscription."""
    video = get_object_or_404(Video, slug=slug, is_published=True)

    # Gate full videos behind subscription — previews are always free
    if not video.is_feed_preview:
        if not request.user.is_authenticated:
            from django.urls import reverse
            messages.info(request, "Log in to watch this video.")
            return redirect(f"{reverse('account_login')}?next=/feed/video/{slug}/")
        if not request.user.is_subscribed:
            messages.warning(request, "Subscribe to watch the full video library.")
            return redirect("subscriptions:plans")

    # Track view
    video.view_count += 1
    video.save(update_fields=["view_count"])

    # Record watch history for logged-in users
    if request.user.is_authenticated:
        from apps.content.models import WatchHistory
        WatchHistory.objects.update_or_create(
            user=request.user, video=video,
            defaults={"progress_seconds": 0}
        )

    # Related videos (same category, excluding current)
    related = Video.objects.filter(
        category=video.category, is_published=True
    ).exclude(pk=video.pk)[:4]

    return render(request, "content/video_detail.html", {
        "video": video,
        "related": related,
    })


@require_POST
def update_progress(request, slug):
    """HTMX endpoint — saves watch progress every 10s."""
    if not request.user.is_authenticated or not request.htmx:
        return JsonResponse({"ok": False}, status=403)

    video = get_object_or_404(Video, slug=slug)
    progress = int(request.POST.get("progress", 0))

    from apps.content.models import WatchHistory
    WatchHistory.objects.update_or_create(
        user=request.user, video=video,
        defaults={"progress_seconds": progress}
    )
    return JsonResponse({"ok": True})


# ── Staff video upload ─────────────────────────────────────────────────────────

from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .forms import VideoUploadForm


@staff_member_required
def upload_video(request):
    """Staff-only video upload page."""
    if request.method == "POST":
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            if video.is_published and not video.published_at:
                video.published_at = timezone.now()
            video.save()
            messages.success(request, f'"{video.title}" uploaded successfully.')
            return redirect("content:upload_video")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = VideoUploadForm()

    recent = Video.objects.order_by("-created_at")[:10]
    return render(request, "content/upload.html", {"form": form, "recent": recent})
