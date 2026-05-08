from django.urls import path
from . import views
from apps.bookings.views import hotel_detail as hotel_booking_detail

app_name = "destinations"

urlpatterns = [
    path("", views.destination_list, name="list"),
    path("trekking/", views.trekking_routes, name="trekking"),
    path("hotels/", views.hotels_stays, name="hotels"),
    path("culture/", views.culture_food, name="culture"),
    path("<slug:slug>/", views.destination_detail, name="detail"),
    path("hotels/<slug:hotel_slug>/book/", hotel_booking_detail, name="hotel_book"),
]
