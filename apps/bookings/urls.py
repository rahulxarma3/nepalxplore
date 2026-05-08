from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    # User booking flow
    path("", views.my_bookings, name="my_bookings"),
    path("<str:reference>/", views.booking_detail, name="booking_detail"),
    path("<str:reference>/pay/", views.pay_deposit, name="pay_deposit"),
    path("<str:reference>/pay/stripe/", views.pay_stripe, name="pay_stripe"),
    path("<str:reference>/pay/khalti/", views.pay_khalti, name="pay_khalti"),
    path("<str:reference>/pay/esewa/", views.pay_esewa, name="pay_esewa"),
    path("<str:reference>/cancel/", views.cancel_booking, name="cancel_booking"),

    # Payment callbacks
    path("stripe/success/", views.stripe_booking_success, name="stripe_success"),
    path("khalti/verify/", views.khalti_booking_verify, name="khalti_verify"),
    path("esewa/verify/", views.esewa_booking_verify, name="esewa_verify"),

    # Staff portal
    path("staff/<slug:hotel_slug>/", views.staff_dashboard, name="staff_dashboard"),
    path("staff/<slug:hotel_slug>/confirm/<int:booking_id>/", views.staff_confirm_booking, name="staff_confirm"),
    path("staff/<slug:hotel_slug>/checkin/<int:booking_id>/", views.staff_checkin, name="staff_checkin"),
    path("staff/<slug:hotel_slug>/checkout/<int:booking_id>/", views.staff_checkout, name="staff_checkout"),
    path("staff/<slug:hotel_slug>/noshow/<int:booking_id>/", views.staff_no_show, name="staff_no_show"),
    path("staff/<slug:hotel_slug>/block/", views.staff_block_dates, name="staff_block"),
]
