import stripe
import hmac
import hashlib
import base64
import requests
import uuid
import json

from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Plan, Subscription, PaymentTransaction

stripe.api_key = settings.STRIPE_SECRET_KEY


def generate_order_id(user, plan):
    return (
        f"NPX-{user.pk}-{plan.slug}-"
        f"{timezone.now().strftime('%Y%m%d%H%M%S')}-"
        f"{uuid.uuid4().hex[:10]}"
    )


def plans(request):
    active_plans = Plan.objects.filter(is_active=True)
    user_sub = None

    if request.user.is_authenticated:
        user_sub = getattr(request.user, "subscription", None)

    return render(request, "subscriptions/plans.html", {
        "plans": active_plans,
        "user_subscription": user_sub,
    })


# ── Stripe ─────────────────────────────────────────────────────────────────────

@login_required
def stripe_checkout(request, plan_slug):
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)

    if not plan.stripe_price_id:
        messages.error(request, "Stripe not configured for this plan.")
        return redirect("subscriptions:plans")

    session = stripe.checkout.Session.create(
        customer_email=request.user.email,
        payment_method_types=["card"],
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        mode="subscription",
        success_url=request.build_absolute_uri(
            "/subscribe/stripe/success/?session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=request.build_absolute_uri("/subscribe/"),
        metadata={
            "user_id": request.user.pk,
            "plan_slug": plan.slug,
        },
    )

    return redirect(session.url, permanent=False)


@login_required
def stripe_success(request):
    session_id = request.GET.get("session_id")

    if not session_id:
        return redirect("subscriptions:plans")

    session = stripe.checkout.Session.retrieve(session_id)
    plan = get_object_or_404(Plan, slug=session.metadata["plan_slug"])

    sub, _ = Subscription.objects.get_or_create(
        user=request.user,
        defaults={
            "plan": plan,
            "gateway": "stripe",
            "end_date": timezone.now(),
        },
    )

    sub.plan = plan
    sub.gateway = "stripe"
    sub.activate(gateway_ref=session.subscription)

    PaymentTransaction.objects.update_or_create(
        gateway="stripe",
        gateway_transaction_id=session.payment_intent or session.subscription,
        defaults={
            "user": request.user,
            "subscription": sub,
            "amount_npr": plan.price_npr,
            "status": "success",
            "raw_response": {"session_id": session_id},
        },
    )

    from apps.core.models import Notification

    Notification.create_for_user(
        user=request.user,
        notification_type="sub_activated",
        title="Subscription activated!",
        body=f"Your {sub.plan.name} subscription is now active. Enjoy full access to NepaXplore.",
        link="/destinations/",
    )

    messages.success(request, "Welcome to NepaXplore! Your subscription is active.")
    return redirect("/")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "customer.subscription.deleted":
        stripe_sub_id = event["data"]["object"]["id"]

        try:
            sub = Subscription.objects.get(gateway_subscription_id=stripe_sub_id)
            sub.status = "expired"
            sub.save()
        except Subscription.DoesNotExist:
            pass

    return HttpResponse(status=200)


# ── eSewa ──────────────────────────────────────────────────────────────────────

@login_required
def esewa_initiate(request, plan_slug):
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)

    amount = str(float(plan.price_npr))
    product_id = generate_order_id(request.user, plan)

    sub, _ = Subscription.objects.get_or_create(
        user=request.user,
        defaults={
            "plan": plan,
            "gateway": "esewa",
            "end_date": timezone.now(),
        },
    )

    sub.plan = plan
    sub.gateway = "esewa"
    sub.save()

    PaymentTransaction.objects.create(
        user=request.user,
        subscription=sub,
        gateway="esewa",
        gateway_transaction_id=product_id,
        amount_npr=plan.price_npr,
        status="pending",
        raw_response={
            "transaction_uuid": product_id,
            "plan_slug": plan.slug,
        },
    )

    msg = (
        f"total_amount={amount},"
        f"transaction_uuid={product_id},"
        f"product_code={settings.ESEWA_MERCHANT_CODE}"
    )

    signature = base64.b64encode(
        hmac.new(
            settings.ESEWA_SECRET_KEY.encode(),
            msg.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()

    context = {
        "plan": plan,
        "amount": amount,
        "product_id": product_id,
        "merchant_code": settings.ESEWA_MERCHANT_CODE,
        "signature": signature,
        "esewa_url": f"{settings.ESEWA_BASE_URL}/api/epay/main/v2/form",
        "success_url": request.build_absolute_uri("/subscribe/esewa/verify/"),
        "failure_url": request.build_absolute_uri("/subscribe/"),
    }

    return render(request, "subscriptions/esewa_redirect.html", context)


@login_required
def esewa_verify(request):
    encoded = request.GET.get("data", "")

    if not encoded:
        messages.error(request, "eSewa payment verification failed.")
        return redirect("subscriptions:plans")

    try:
        decoded = json.loads(base64.b64decode(encoded + "==").decode())
    except Exception:
        messages.error(request, "Invalid eSewa response.")
        return redirect("subscriptions:plans")

    if decoded.get("status") != "COMPLETE":
        messages.error(request, "eSewa payment was not completed.")
        return redirect("subscriptions:plans")

    product_id = decoded.get("transaction_uuid", "")

    payment_tx = PaymentTransaction.objects.filter(
        gateway="esewa",
        gateway_transaction_id=product_id,
        user=request.user,
    ).first()

    if not payment_tx:
        messages.error(request, "Payment record not found.")
        return redirect("subscriptions:plans")

    if payment_tx.status == "success":
        messages.success(request, "Payment already verified.")
        return redirect("/")

    sub = payment_tx.subscription
    plan = sub.plan

    sub.plan = plan
    sub.gateway = "esewa"
    sub.activate(gateway_ref=decoded.get("transaction_code", ""))

    payment_tx.status = "success"
    payment_tx.amount_npr = Decimal(str(decoded.get("total_amount", plan.price_npr)))
    payment_tx.raw_response = decoded
    payment_tx.save()

    from apps.core.models import Notification

    Notification.create_for_user(
        user=request.user,
        notification_type="sub_activated",
        title="Subscription activated!",
        body=f"Your {sub.plan.name} subscription is now active. Enjoy full access to NepaXplore.",
        link="/destinations/",
    )

    messages.success(request, "eSewa payment successful! Welcome to NepaXplore.")
    return redirect("/")


# ── Khalti ─────────────────────────────────────────────────────────────────────

@login_required
def khalti_initiate(request, plan_slug):
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)

    amount_paisa = int(plan.price_npr) * 100
    order_id = generate_order_id(request.user, plan)

    sub, _ = Subscription.objects.get_or_create(
        user=request.user,
        defaults={
            "plan": plan,
            "gateway": "khalti",
            "end_date": timezone.now(),
        },
    )

    sub.plan = plan
    sub.gateway = "khalti"
    sub.save()

    PaymentTransaction.objects.create(
        user=request.user,
        subscription=sub,
        gateway="khalti",
        gateway_transaction_id=order_id,
        amount_npr=plan.price_npr,
        status="pending",
        raw_response={
            "purchase_order_id": order_id,
            "plan_slug": plan.slug,
        },
    )

    payload = {
        "return_url": request.build_absolute_uri("/subscribe/khalti/verify/"),
        "website_url": request.build_absolute_uri("/"),
        "amount": amount_paisa,
        "purchase_order_id": order_id,
        "purchase_order_name": f"NepaXplore {plan.name}",
        "customer_info": {
            "name": getattr(request.user, "display_name", request.user.email),
            "email": request.user.email,
        },
    }

    try:
        resp = requests.post(
            f"{settings.KHALTI_BASE_URL}/epayment/initiate/",
            json=payload,
            headers={"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"},
            timeout=10,
        )
    except requests.RequestException:
        messages.error(request, "Khalti connection failed. Please try again.")
        return redirect("subscriptions:plans")

    if resp.status_code == 200:
        data = resp.json()

        payment_tx = PaymentTransaction.objects.filter(
            gateway="khalti",
            gateway_transaction_id=order_id,
            user=request.user,
        ).first()

        if payment_tx:
            payment_tx.raw_response = data
            payment_tx.save()

        return redirect(data["payment_url"])

    messages.error(request, "Khalti initiation failed. Please try another method.")
    return redirect("subscriptions:plans")


@login_required
def khalti_verify(request):
    pidx = request.GET.get("pidx")

    if not pidx:
        messages.error(request, "Invalid Khalti callback.")
        return redirect("subscriptions:plans")

    try:
        resp = requests.post(
            f"{settings.KHALTI_BASE_URL}/epayment/lookup/",
            json={"pidx": pidx},
            headers={"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"},
            timeout=10,
        )
    except requests.RequestException:
        messages.error(request, "Khalti verification connection failed.")
        return redirect("subscriptions:plans")

    if resp.status_code != 200:
        messages.error(request, "Khalti payment verification failed.")
        return redirect("subscriptions:plans")

    data = resp.json()

    if data.get("status") != "Completed":
        messages.error(request, "Khalti payment was not completed.")
        return redirect("subscriptions:plans")

    order_id = data.get("purchase_order_id", "")

    payment_tx = PaymentTransaction.objects.filter(
        gateway="khalti",
        gateway_transaction_id=order_id,
        user=request.user,
    ).first()

    if not payment_tx:
        messages.error(request, "Payment record not found.")
        return redirect("subscriptions:plans")

    if payment_tx.status == "success":
        messages.success(request, "Payment already verified.")
        return redirect("/")

    sub = payment_tx.subscription
    plan = sub.plan

    sub.plan = plan
    sub.gateway = "khalti"
    sub.activate(gateway_ref=pidx)

    payment_tx.status = "success"
    payment_tx.amount_npr = Decimal(str(data.get("total_amount", 0))) / 100
    payment_tx.raw_response = data
    payment_tx.save()

    from apps.core.models import Notification

    Notification.create_for_user(
        user=request.user,
        notification_type="sub_activated",
        title="Subscription activated!",
        body=f"Your {sub.plan.name} subscription is now active. Enjoy full access to NepaXplore.",
        link="/destinations/",
    )

    messages.success(request, "Khalti payment successful! Welcome to NepaXplore.")
    return redirect("/")


# ── Subscription management ────────────────────────────────────────────────────

@login_required
def cancel_subscription(request):
    if request.method != "POST":
        return redirect("accounts:profile")

    sub = getattr(request.user, "subscription", None)

    if not sub or not sub.is_active:
        messages.error(request, "No active subscription found.")
        return redirect("accounts:profile")

    if sub.gateway == "stripe" and sub.gateway_subscription_id:
        try:
            stripe.Subscription.modify(
                sub.gateway_subscription_id,
                cancel_at_period_end=True,
            )
        except stripe.error.StripeError as e:
            messages.error(request, f"Stripe error: {e.user_message}")
            return redirect("accounts:profile")

    sub.auto_renew = False
    sub.save(update_fields=["auto_renew"])

    messages.success(
        request,
        f"Auto-renewal cancelled. You have full access until {sub.end_date.strftime('%B %d, %Y')}.",
    )

    return redirect("accounts:profile")


@login_required
def subscription_detail(request):
    sub = getattr(request.user, "subscription", None)

    return render(request, "subscriptions/partials/status_card.html", {
        "subscription": sub,
        "is_subscribed": sub.is_active if sub else False,
        "days_remaining": sub.days_remaining if sub else 0,
    })