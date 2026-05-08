"""
apps/subscriptions/sandbox_views.py

Sandbox views for testing all 3 payment gateways without real money.
Only accessible when DEBUG=True. Registered in urls.py conditionally.

Usage:
  /subscribe/sandbox/              - gateway picker
  /subscribe/sandbox/pay/<plan>/   - simulate payment
  /subscribe/sandbox/success/      - fake success callback
  /subscribe/sandbox/fail/         - fake failure callback
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Plan, Subscription, PaymentTransaction


def sandbox_guard(func):
    """Decorator: block in production."""
    def wrapper(request, *args, **kwargs):
        if not settings.DEBUG:
            from django.http import Http404
            raise Http404("Sandbox only available in DEBUG mode.")
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@sandbox_guard
@login_required
def sandbox_picker(request):
    """Show all plans + gateway options for sandbox testing."""
    plans = Plan.objects.filter(is_active=True)
    current_sub = getattr(request.user, "subscription", None)
    return render(request, "subscriptions/sandbox/picker.html", {
        "plans": plans,
        "current_sub": current_sub,
        "gateways": [
            {"id": "khalti", "name": "Khalti", "emoji": "💜", "color": "purple",
             "test_numbers": "9800000001–9800000005", "mpin": "1111", "otp": "987654"},
            {"id": "esewa",  "name": "eSewa",  "emoji": "💚", "color": "green",
             "test_numbers": "9806800001", "mpin": "Nepal@123", "otp": "123456"},
            {"id": "stripe", "name": "Stripe", "emoji": "💳", "color": "indigo",
             "test_numbers": "4242 4242 4242 4242", "mpin": "Any future date", "otp": "Any 3 digits"},
        ]
    })


@sandbox_guard
@login_required
def sandbox_pay(request, plan_slug, gateway):
    """Simulate a successful payment for any gateway."""
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)

    if request.method == "POST":
        action = request.POST.get("action", "success")

        if action == "success":
            interval_days = 30 if plan.interval == "monthly" else 365
            sub, _ = Subscription.objects.update_or_create(
                user=request.user,
                defaults={
                    "plan": plan,
                    "gateway": gateway,
                    "status": "active",
                    "gateway_subscription_id": f"sandbox_{gateway}_{request.user.pk}_{timezone.now().timestamp():.0f}",
                    "end_date": timezone.now() + timedelta(days=interval_days),
                    "auto_renew": True,
                }
            )
            PaymentTransaction.objects.create(
                user=request.user,
                subscription=sub,
                gateway=gateway,
                gateway_transaction_id=f"sandbox_txn_{timezone.now().timestamp():.0f}",
                amount_npr=plan.price_npr,
                status="success",
                raw_response={"sandbox": True, "gateway": gateway, "plan": plan.slug},
            )
            messages.success(request, f"✅ Sandbox {gateway.title()} payment successful! Subscription activated.")
            return redirect("accounts:profile")

        else:  # failure
            PaymentTransaction.objects.create(
                user=request.user,
                subscription=None,
                gateway=gateway,
                gateway_transaction_id="",
                amount_npr=plan.price_npr,
                status="failed",
                raw_response={"sandbox": True, "reason": "user_cancelled"},
            )
            messages.error(request, f"❌ Sandbox {gateway.title()} payment failed (simulated).")
            return redirect("subscriptions:sandbox_picker")

    return render(request, "subscriptions/sandbox/pay.html", {
        "plan": plan,
        "gateway": gateway,
        'cli_cmds': cli_cmds,
    })


@sandbox_guard
@login_required
def sandbox_reset(request):
    """Remove current user's subscription for fresh testing."""
    if request.method == "POST":
        Subscription.objects.filter(user=request.user).delete()
        PaymentTransaction.objects.filter(user=request.user).delete()
        messages.warning(request, "Subscription reset. You can test a fresh payment flow.")
    return redirect("subscriptions:sandbox_picker")
