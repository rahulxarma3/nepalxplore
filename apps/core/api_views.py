"""
apps/core/api_views.py

REST API for the future Flutter/React Native mobile app.
All endpoints are versioned under /api/v1/
Authentication: JWT (Bearer token)
"""
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from apps.content.models import Video, Category, WatchHistory
from apps.destinations.models import Destination, TrekkingRoute, Hotel, CulturalContent
from apps.subscriptions.models import Plan, Subscription
from .serializers import (
    VideoListSerializer, VideoDetailSerializer, CategorySerializer,
    DestinationListSerializer, DestinationDetailSerializer,
    TrekkingRouteSerializer, HotelSerializer, CulturalContentSerializer,
    PlanSerializer, SubscriptionSerializer,
)

User = get_user_model()


# ── Permissions ────────────────────────────────────────────────────────────────

class IsSubscribedOrPreview(permissions.BasePermission):
    """Allow access to preview content for all; full content for subscribers only."""
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "is_feed_preview") and obj.is_feed_preview:
            return True
        return request.user.is_authenticated and request.user.is_subscribed


class IsSubscribed(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_subscribed


# ── Auth ───────────────────────────────────────────────────────────────────────

class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")

        if not email or not password:
            return Response({"error": "Email and password are required."}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({"error": "An account with this email already exists."}, status=400)
        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters."}, status=400)

        user = User.objects.create_user(
            username=email.split("@")[0],
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
            }
        }, status=201)


class ProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        sub = getattr(user, "subscription", None)
        return Response({
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "preferred_language": user.preferred_language,
            "dark_mode": user.dark_mode,
            "notifications_enabled": user.notifications_enabled,
            "avatar_url": user.avatar.url if user.avatar else None,
            "is_subscribed": user.is_subscribed,
            "subscription": SubscriptionSerializer(sub).data if sub else None,
        })

    def patch(self, request):
        user = request.user
        user.first_name = request.data.get("first_name", user.first_name)
        user.last_name = request.data.get("last_name", user.last_name)
        user.dark_mode = request.data.get("dark_mode", user.dark_mode)
        user.notifications_enabled = request.data.get("notifications_enabled", user.notifications_enabled)
        lang = request.data.get("preferred_language")
        if lang in ("en", "ne"):
            user.preferred_language = lang
        user.save()
        return Response({"ok": True})


# ── Feed / Videos ──────────────────────────────────────────────────────────────

class FeedAPIView(generics.ListAPIView):
    """Public video feed — returns is_feed_preview=True videos. No auth needed."""
    serializer_class = VideoListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Video.objects.filter(is_published=True, is_feed_preview=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)
        return qs


class VideoLibraryAPIView(generics.ListAPIView):
    """Full video library — subscribers only."""
    serializer_class = VideoListSerializer
    permission_classes = [IsSubscribed]

    def get_queryset(self):
        qs = Video.objects.filter(is_published=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)
        return qs


class VideoDetailAPIView(generics.RetrieveAPIView):
    """Single video detail — preview videos public, full videos subscriber-only."""
    serializer_class = VideoDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = Video.objects.filter(is_published=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Gate non-preview videos
        if not instance.is_feed_preview:
            if not request.user.is_authenticated:
                return Response({"error": "Authentication required.", "subscribe_url": "/api/v1/plans/"}, status=401)
            if not request.user.is_subscribed:
                return Response({"error": "Subscription required.", "subscribe_url": "/api/v1/plans/"}, status=403)

        # Track view
        instance.view_count += 1
        instance.save(update_fields=["view_count"])

        if request.user.is_authenticated:
            WatchHistory.objects.update_or_create(
                user=request.user, video=instance,
                defaults={"progress_seconds": 0}
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def update_progress_api(request, slug):
    """Save video watch progress for the mobile player."""
    try:
        video = Video.objects.get(slug=slug, is_published=True)
    except Video.DoesNotExist:
        return Response({"error": "Not found."}, status=404)

    progress = int(request.data.get("progress", 0))
    WatchHistory.objects.update_or_create(
        user=request.user, video=video,
        defaults={"progress_seconds": progress}
    )
    return Response({"ok": True})


class CategoryListAPIView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    queryset = Category.objects.all()


# ── Destinations ───────────────────────────────────────────────────────────────

class DestinationListAPIView(generics.ListAPIView):
    serializer_class = DestinationListSerializer
    permission_classes = [IsSubscribed]
    queryset = Destination.objects.all()


class DestinationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = DestinationDetailSerializer
    permission_classes = [IsSubscribed]
    lookup_field = "slug"
    queryset = Destination.objects.all()


class TrekkingRoutesAPIView(generics.ListAPIView):
    serializer_class = TrekkingRouteSerializer
    permission_classes = [IsSubscribed]

    def get_queryset(self):
        qs = TrekkingRoute.objects.filter(is_published=True).select_related("destination")
        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        return qs


class HotelsAPIView(generics.ListAPIView):
    serializer_class = HotelSerializer
    permission_classes = [IsSubscribed]

    def get_queryset(self):
        qs = Hotel.objects.filter(is_published=True).select_related("destination")
        hotel_type = self.request.query_params.get("type")
        if hotel_type:
            qs = qs.filter(hotel_type=hotel_type)
        return qs


class CultureAPIView(generics.ListAPIView):
    serializer_class = CulturalContentSerializer
    permission_classes = [IsSubscribed]

    def get_queryset(self):
        qs = CulturalContent.objects.filter(is_published=True)
        content_type = self.request.query_params.get("type")
        if content_type:
            qs = qs.filter(content_type=content_type)
        return qs


# ── Subscription / Plans ───────────────────────────────────────────────────────

class PlanListAPIView(generics.ListAPIView):
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Plan.objects.filter(is_active=True)


class SubscriptionStatusAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sub = getattr(request.user, "subscription", None)
        if not sub:
            return Response({"is_subscribed": False, "subscription": None})
        return Response({
            "is_subscribed": sub.is_active,
            "subscription": SubscriptionSerializer(sub).data,
        })


# ── Watch history ──────────────────────────────────────────────────────────────

class WatchHistoryAPIView(generics.ListAPIView):
    serializer_class = VideoListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        watched_slugs = WatchHistory.objects.filter(
            user=self.request.user
        ).order_by("-watched_at").values_list("video__slug", flat=True)[:20]
        return Video.objects.filter(slug__in=watched_slugs, is_published=True)
