from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

# All premium content lives under /destinations/ or /feed/video/<slug>/
# /feed/ itself (the listing) is public — only individual full videos are gated
PREMIUM_PREFIXES = [
    "/destinations/",
]

# Feed video detail is premium UNLESS the video is marked is_feed_preview
# We handle that logic in the view itself, not here
# The middleware only blocks /destinations/*

PUBLIC_PREFIXES = [
    "/feed/",        # public feed listing + preview videos
    "/accounts/",    # auth
    "/subscribe/",   # plans + payment flows
    "/admin/",
    "/static/",
    "/media/",
    "/",             # home
]


class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        is_premium = any(path.startswith(p) for p in PREMIUM_PREFIXES)
        if not is_premium:
            return self.get_response(request)

        if not request.user.is_authenticated:
            messages.info(request, "Please log in to access this content.")
            return redirect(f"{reverse('account_login')}?next={path}")

        if not request.user.is_subscribed:
            messages.warning(request, "Subscribe to unlock full access to NepaXplore.")
            return redirect("subscriptions:plans")

        return self.get_response(request)
