from django.db import models
from django.core.cache import cache
from django.conf import settings
import requests


class Destination(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    region = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    cover_image = models.ImageField(upload_to="destinations/")
    latitude = models.FloatField()
    longitude = models.FloatField()
    altitude_m = models.PositiveIntegerField(null=True, blank=True)
    best_season = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def get_weather(self):
        """Fetch live weather from OpenWeatherMap with 30-min cache."""
        cache_key = f"weather_{self.slug}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            resp = requests.get(
                url,
                params={
                    "lat": self.latitude,
                    "lon": self.longitude,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            weather = {
                "temp_c": round(data["main"]["temp"]),
                "feels_like": round(data["main"]["feels_like"]),
                "description": data["weather"][0]["description"].capitalize(),
                "icon_code": data["weather"][0]["icon"],
                "humidity": data["main"]["humidity"],
                "wind_kph": round(data["wind"]["speed"] * 3.6),
            }
            cache.set(cache_key, weather, settings.WEATHER_CACHE_SECONDS)
            return weather
        except Exception:
            return None


class TrekkingRoute(models.Model):
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("moderate", "Moderate"),
        ("hard", "Hard"),
        ("extreme", "Extreme"),
    ]

    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="trekking_routes"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    cover_image = models.ImageField(upload_to="routes/")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    duration_days = models.PositiveSmallIntegerField()
    max_altitude_m = models.PositiveIntegerField(null=True, blank=True)
    distance_km = models.FloatField(null=True, blank=True)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Hotel(models.Model):
    TYPE_CHOICES = [
        ("hotel", "Hotel"),
        ("resort", "Resort"),
        ("homestay", "Homestay"),
        ("guesthouse", "Guesthouse"),
    ]

    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="hotels"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    hotel_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    description = models.TextField()
    cover_image = models.ImageField(upload_to="hotels/")
    price_per_night_npr = models.DecimalField(max_digits=8, decimal_places=2)
    altitude_m = models.PositiveIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_hotel_type_display()})"


class CulturalContent(models.Model):
    TYPE_CHOICES = [
        ("festival", "Festival"),
        ("tradition", "Tradition"),
        ("food", "Local Food"),
        ("art", "Art & Craft"),
        ("experience", "Experience"),
    ]

    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="cultural_content", null=True, blank=True
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    description = models.TextField()
    cover_image = models.ImageField(upload_to="culture/")
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.name
