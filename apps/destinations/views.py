from django.shortcuts import render, get_object_or_404
from .models import Destination, TrekkingRoute, Hotel, CulturalContent


def destination_list(request):
    destinations = Destination.objects.all()
    return render(request, "destinations/list.html", {"destinations": destinations})


def destination_detail(request, slug):
    destination = get_object_or_404(Destination, slug=slug)
    weather = destination.get_weather()
    routes = destination.trekking_routes.filter(is_published=True)
    hotels = destination.hotels.filter(is_published=True)
    culture = destination.cultural_content.filter(is_published=True)

    return render(request, "destinations/detail.html", {
        "destination": destination,
        "weather": weather,
        "routes": routes,
        "hotels": hotels,
        "culture": culture,
    })


def trekking_routes(request):
    routes = TrekkingRoute.objects.filter(is_published=True).select_related("destination")
    difficulty = request.GET.get("difficulty", "")
    if difficulty:
        routes = routes.filter(difficulty=difficulty)
    return render(request, "destinations/trekking.html", {
        "routes": routes,
        "active_difficulty": difficulty,
        "difficulty_choices": TrekkingRoute.DIFFICULTY_CHOICES,
    })


def hotels_stays(request):
    hotels = Hotel.objects.filter(is_published=True).select_related("destination")
    hotel_type = request.GET.get("type", "")
    if hotel_type:
        hotels = hotels.filter(hotel_type=hotel_type)
    return render(request, "destinations/hotels.html", {
        "hotels": hotels,
        "active_type": hotel_type,
        "type_choices": Hotel.TYPE_CHOICES,
    })


def culture_food(request):
    items = CulturalContent.objects.filter(is_published=True)
    content_type = request.GET.get("type", "")
    if content_type:
        items = items.filter(content_type=content_type)
    return render(request, "destinations/culture.html", {
        "items": items,
        "active_type": content_type,
        "type_choices": CulturalContent.TYPE_CHOICES,
    })
