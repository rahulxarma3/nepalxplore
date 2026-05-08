from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import api_views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("auth/register/", api_views.RegisterAPIView.as_view(), name="api_register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="api_login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
    path("auth/profile/", api_views.ProfileAPIView.as_view(), name="api_profile"),

    # ── Feed & Videos ──────────────────────────────────────────────────────────
    path("feed/", api_views.FeedAPIView.as_view(), name="api_feed"),
    path("videos/", api_views.VideoLibraryAPIView.as_view(), name="api_videos"),
    path("videos/<slug:slug>/", api_views.VideoDetailAPIView.as_view(), name="api_video_detail"),
    path("videos/<slug:slug>/progress/", api_views.update_progress_api, name="api_progress"),
    path("categories/", api_views.CategoryListAPIView.as_view(), name="api_categories"),
    path("history/", api_views.WatchHistoryAPIView.as_view(), name="api_history"),

    # ── Destinations ───────────────────────────────────────────────────────────
    path("destinations/", api_views.DestinationListAPIView.as_view(), name="api_destinations"),
    path("destinations/<slug:slug>/", api_views.DestinationDetailAPIView.as_view(), name="api_destination_detail"),
    path("trekking/", api_views.TrekkingRoutesAPIView.as_view(), name="api_trekking"),
    path("hotels/", api_views.HotelsAPIView.as_view(), name="api_hotels"),
    path("culture/", api_views.CultureAPIView.as_view(), name="api_culture"),

    # ── Subscription ───────────────────────────────────────────────────────────
    path("plans/", api_views.PlanListAPIView.as_view(), name="api_plans"),
    path("subscription/", api_views.SubscriptionStatusAPIView.as_view(), name="api_subscription"),
]
