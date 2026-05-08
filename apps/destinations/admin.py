from django.contrib import admin
from .models import Destination, TrekkingRoute, Hotel, CulturalContent

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ["name", "region", "is_featured", "order"]
    prepopulated_fields = {"slug": ["name"]}
    list_editable = ["is_featured", "order"]

@admin.register(TrekkingRoute)
class TrekkingRouteAdmin(admin.ModelAdmin):
    list_display = ["name", "destination", "difficulty", "duration_days"]
    list_filter = ["difficulty", "destination"]
    prepopulated_fields = {"slug": ["name"]}

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ["name", "destination", "hotel_type", "price_per_night_npr"]
    list_filter = ["hotel_type", "destination"]
    prepopulated_fields = {"slug": ["name"]}

@admin.register(CulturalContent)
class CulturalContentAdmin(admin.ModelAdmin):
    list_display = ["name", "content_type", "destination"]
    list_filter = ["content_type"]
    prepopulated_fields = {"slug": ["name"]}
