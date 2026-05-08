from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.content.models import WatchHistory


@login_required
def profile(request):
    watch_history = WatchHistory.objects.filter(
        user=request.user
    ).select_related("video").order_by("-watched_at")[:20]

    nav_sections = [
        ("Personal information", "personal"),
        ("Preferences", "preferences"),
        ("Watch history", "history"),
    ]

    return render(request, "accounts/profile.html", {
        "watch_history": watch_history,
        "nav_sections": nav_sections,
    })


@login_required
def profile_update(request):
    if request.method != "POST":
        return redirect("accounts:profile")

    user = request.user
    section = request.POST.get("section")

    if section == "personal":
        user.first_name = request.POST.get("first_name", user.first_name).strip()
        user.last_name = request.POST.get("last_name", user.last_name).strip()
        if request.FILES.get("avatar"):
            user.avatar = request.FILES["avatar"]
        user.save()
        messages.success(request, "Profile updated successfully.")

    elif section == "preferences":
        user.dark_mode = "dark_mode" in request.POST
        user.notifications_enabled = "notifications_enabled" in request.POST
        lang = request.POST.get("preferred_language", "en")
        if lang in ("en", "ne"):
            user.preferred_language = lang
        user.save()
        messages.success(request, "Preferences saved.")

    return redirect("accounts:profile")
