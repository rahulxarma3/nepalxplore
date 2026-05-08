from rest_framework import serializers
from apps.content.models import Video, Category
from apps.destinations.models import Destination, TrekkingRoute, Hotel, CulturalContent
from apps.subscriptions.models import Plan, Subscription


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon"]


class VideoListSerializer(serializers.ModelSerializer):
    """Lightweight — used in feed lists."""
    category = CategorySerializer(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            "id", "title", "slug", "category", "thumbnail_url",
            "duration_seconds", "location", "is_feed_preview",
            "view_count", "published_at",
        ]

    def get_thumbnail_url(self, obj):
        return obj.thumbnail_url


class VideoDetailSerializer(VideoListSerializer):
    """Full detail — includes video file URL (signed for private videos)."""
    video_url = serializers.SerializerMethodField()

    class Meta(VideoListSerializer.Meta):
        fields = VideoListSerializer.Meta.fields + ["description", "language", "video_url", "updated_at"]

    def get_video_url(self, obj):
        request = self.context.get("request")
        user = request.user if request else None

        # Only return video URL to subscribers (or if it's a preview)
        if obj.is_feed_preview:
            return obj.video_file.url if obj.video_file else None
        if user and user.is_authenticated and user.is_subscribed:
            return obj.video_file.url if obj.video_file else None
        return None


class DestinationListSerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = ["id", "name", "slug", "region", "cover_image_url", "is_featured", "altitude_m"]

    def get_cover_image_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None


class DestinationDetailSerializer(DestinationListSerializer):
    weather = serializers.SerializerMethodField()

    class Meta(DestinationListSerializer.Meta):
        fields = DestinationListSerializer.Meta.fields + [
            "description", "latitude", "longitude",
            "best_season", "weather",
        ]

    def get_weather(self, obj):
        return obj.get_weather()


class TrekkingRouteSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = TrekkingRoute
        fields = [
            "id", "name", "slug", "destination_name", "cover_image_url",
            "difficulty", "duration_days", "max_altitude_m", "distance_km",
        ]

    def get_cover_image_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None


class HotelSerializer(serializers.ModelSerializer):
    destination_name = serializers.CharField(source="destination.name", read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            "id", "name", "slug", "hotel_type", "destination_name",
            "cover_image_url", "price_per_night_npr", "rating", "altitude_m",
        ]

    def get_cover_image_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None


class CulturalContentSerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = CulturalContent
        fields = ["id", "name", "slug", "content_type", "description", "cover_image_url"]

    def get_cover_image_url(self, obj):
        return obj.cover_image.url if obj.cover_image else None


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name", "slug", "price_npr", "price_usd", "interval", "features"]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "gateway", "status", "is_active",
            "days_remaining", "start_date", "end_date", "auto_renew",
        ]
