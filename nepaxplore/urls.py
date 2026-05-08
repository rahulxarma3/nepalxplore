from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.bookings.views import availability_json

urlpatterns = [
    path("admin/", admin.site.urls),

    # Core / public pages
    path("", include("apps.core.urls")),

    # Auth
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("apps.accounts.urls")),

    # App sections
    path("feed/", include("apps.content.urls")),
    path("destinations/", include("apps.destinations.urls")),
    path("subscribe/", include("apps.subscriptions.urls")),

    # Hotel bookings (user flow)
    path("bookings/", include("apps.bookings.urls")),

    # Hotel availability calendar API
    path("hotels/availability/<slug:hotel_slug>/", availability_json, name="hotel_availability"),

    # REST API — mobile app
    path("api/v1/", include("apps.core.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=getattr(settings, "MEDIA_ROOT", "media")
    )
