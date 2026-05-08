from django.shortcuts import render
from apps.content.models import Video, Category
from apps.destinations.models import Destination


def home(request):
    """Splash / home page — fully public."""
    featured_destinations = Destination.objects.filter(is_featured=True)[:4]
    preview_videos = Video.objects.filter(
        is_published=True, is_feed_preview=True
    )[:6]
    categories = Category.objects.all()

    return render(request, "core/home.html", {
        "featured_destinations": featured_destinations,
        "preview_videos": preview_videos,
        "categories": categories,
    })


# ── Search ─────────────────────────────────────────────────────────────────────

from django.db.models import Q
from apps.content.models import Video
from apps.destinations.models import Destination, TrekkingRoute


def search(request):
    query = request.GET.get("q", "").strip()
    results = {"videos": [], "destinations": [], "routes": []}
    total = 0

    if query and len(query) >= 2:
        # Videos — search title, description, location
        videos = Video.objects.filter(
            is_published=True
        ).filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )
        # Non-subscribers only see feed previews
        if not (request.user.is_authenticated and request.user.is_subscribed):
            videos = videos.filter(is_feed_preview=True)
        results["videos"] = videos[:12]

        # Destinations (subscribers only)
        if request.user.is_authenticated and request.user.is_subscribed:
            results["destinations"] = Destination.objects.filter(
                Q(name__icontains=query) |
                Q(region__icontains=query) |
                Q(description__icontains=query)
            )[:6]

            results["routes"] = TrekkingRoute.objects.filter(
                is_published=True
            ).filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            ).select_related("destination")[:6]

        total = (
            len(results["videos"]) +
            len(results["destinations"]) +
            len(results["routes"])
        )

    return render(request, "core/search.html", {
        "query": query,
        "results": results,
        "total": total,
    })


# ── Admin dashboard ────────────────────────────────────────────────────────────

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from apps.subscriptions.models import Subscription, PaymentTransaction


@staff_member_required
def admin_dashboard(request):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # Subscriber stats
    active_subs = Subscription.objects.filter(status="active", end_date__gt=now)
    new_this_month = active_subs.filter(start_date__gte=thirty_days_ago)
    expiring_soon = active_subs.filter(end_date__lte=now + timedelta(days=7))

    # Revenue this month
    revenue_month = PaymentTransaction.objects.filter(
        status="success",
        created_at__gte=thirty_days_ago,
    ).aggregate(total=Sum("amount_npr"))["total"] or 0

    # Gateway breakdown
    gateway_stats = PaymentTransaction.objects.filter(
        status="success",
        created_at__gte=thirty_days_ago,
    ).values("gateway").annotate(
        count=Count("id"),
        revenue=Sum("amount_npr"),
    ).order_by("-revenue")

    # Recent uploads
    recent_videos = Video.objects.order_by("-created_at")[:5]

    # Video stats
    total_videos = Video.objects.filter(is_published=True).count()
    preview_videos = Video.objects.filter(is_published=True, is_feed_preview=True).count()

    return render(request, "core/admin_dashboard.html", {
        "active_sub_count": active_subs.count(),
        "new_this_month": new_this_month.count(),
        "expiring_soon": expiring_soon.count(),
        "revenue_month": revenue_month,
        "gateway_stats": list(gateway_stats),
        "recent_videos": recent_videos,
        "total_videos": total_videos,
        "preview_videos": preview_videos,
    })


# ── API Docs ───────────────────────────────────────────────────────────────────

def api_docs(request):
    auth_endpoints = [
        {"method": "POST", "path": "/api/v1/auth/register/",    "description": "Create a new account with email + password", "auth": False, "sub": False},
        {"method": "POST", "path": "/api/v1/auth/login/",       "description": "Get access + refresh JWT tokens", "auth": False, "sub": False},
        {"method": "POST", "path": "/api/v1/auth/refresh/",     "description": "Exchange refresh token for new access token", "auth": False, "sub": False},
        {"method": "GET",  "path": "/api/v1/auth/profile/",     "description": "Get current user profile + subscription status", "auth": True, "sub": False},
        {"method": "PATCH","path": "/api/v1/auth/profile/",     "description": "Update name, language, dark mode, notifications", "auth": True, "sub": False},
    ]
    video_endpoints = [
        {"method": "GET", "path": "/api/v1/feed/",              "description": "Public feed — free preview videos. Supports ?category=<slug>", "auth": False, "sub": False},
        {"method": "GET", "path": "/api/v1/videos/",            "description": "Full video library. Supports ?category=<slug>", "auth": True, "sub": True},
        {"method": "GET", "path": "/api/v1/videos/<slug>/",     "description": "Video detail + signed video URL", "auth": True, "sub": True},
        {"method": "POST","path": "/api/v1/videos/<slug>/progress/", "description": "Save watch progress. Body: {progress: seconds}", "auth": True, "sub": False},
        {"method": "GET", "path": "/api/v1/categories/",        "description": "List all video categories", "auth": False, "sub": False},
        {"method": "GET", "path": "/api/v1/history/",           "description": "Current user watch history (last 20)", "auth": True, "sub": False},
    ]
    destination_endpoints = [
        {"method": "GET", "path": "/api/v1/destinations/",       "description": "List all destinations", "auth": True, "sub": True},
        {"method": "GET", "path": "/api/v1/destinations/<slug>/","description": "Destination detail with live weather data", "auth": True, "sub": True},
        {"method": "GET", "path": "/api/v1/trekking/",           "description": "All trekking routes. Supports ?difficulty=easy|moderate|hard|extreme", "auth": True, "sub": True},
        {"method": "GET", "path": "/api/v1/hotels/",             "description": "Hotels & stays. Supports ?type=hotel|resort|homestay|guesthouse", "auth": True, "sub": True},
        {"method": "GET", "path": "/api/v1/culture/",            "description": "Culture & food. Supports ?type=festival|tradition|food|art|experience", "auth": True, "sub": True},
    ]
    sub_endpoints = [
        {"method": "GET", "path": "/api/v1/plans/",             "description": "List subscription plans (NPR 2,000/mo, NPR 20,000/yr)", "auth": False, "sub": False},
        {"method": "GET", "path": "/api/v1/subscription/",      "description": "Current user subscription status", "auth": True, "sub": False},
    ]
    return render(request, "core/api_docs.html", {
        "auth_endpoints": auth_endpoints,
        "video_endpoints": video_endpoints,
        "destination_endpoints": destination_endpoints,
        "sub_endpoints": sub_endpoints,
    })


# ── Notifications ──────────────────────────────────────────────────────────────

from django.contrib.auth.decorators import login_required as _login_required
from django.http import JsonResponse
from .models import Notification


@_login_required
def notifications_list(request):
    notifs = Notification.objects.filter(user=request.user)[:30]
    # Mark all as read on page load
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, "core/notifications.html", {"notifications": notifs})


@_login_required
def notifications_count(request):
    """HTMX endpoint — returns unread count badge."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return render(request, "partials/notif_badge.html", {"count": count})


@_login_required
def mark_notification_read(request, pk):
    if request.method == "POST":
        Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return JsonResponse({"ok": True})
