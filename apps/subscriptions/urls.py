from django.urls import path
from django.conf import settings
from . import views

app_name = "subscriptions"

urlpatterns = [
    path("", views.plans, name="plans"),

    # Stripe
    path("stripe/<slug:plan_slug>/", views.stripe_checkout, name="stripe_checkout"),
    path("stripe/success/", views.stripe_success, name="stripe_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),

    # eSewa
    path("esewa/<slug:plan_slug>/", views.esewa_initiate, name="esewa_initiate"),
    path("esewa/verify/", views.esewa_verify, name="esewa_verify"),

    # Khalti
    path("khalti/<slug:plan_slug>/", views.khalti_initiate, name="khalti_initiate"),
    path("khalti/verify/", views.khalti_verify, name="khalti_verify"),

    # Management
    path("cancel/", views.cancel_subscription, name="cancel"),
    path("status/", views.subscription_detail, name="status"),
]

# Sandbox testing — DEBUG only
if settings.DEBUG:
    from . import sandbox_views
    urlpatterns += [
        path("sandbox/", sandbox_views.sandbox_picker, name="sandbox_picker"),
        path("sandbox/pay/<slug:plan_slug>/<str:gateway>/", sandbox_views.sandbox_pay, name="sandbox_pay"),
        path("sandbox/reset/", sandbox_views.sandbox_reset, name="sandbox_reset"),
    ]
