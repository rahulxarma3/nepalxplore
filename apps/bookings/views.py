"""
apps/bookings/views.py

User booking flow:
  hotel_detail    → book_room → pay_deposit → booking_detail → cancel_booking
  bookings_list   → booking_detail

Staff portal:
  staff_dashboard → staff_confirm → staff_checkin → staff_checkout → staff_block_dates
"""
import stripe
import requests
import base64
import hmac
import hashlib
from decimal import Decimal
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum

from .models import Booking, RoomType, BookingPayment
from apps.destinations.models import Hotel

stripe.api_key = settings.STRIPE_SECRET_KEY


# ── Availability API ───────────────────────────────────────────────────────────

def availability_json(request, hotel_slug):
    """
    Returns available room counts per date for the next 90 days.
    Used by the date picker calendar via HTMX/JS.
    Format: {"2025-05-01": {"standard": 2, "deluxe": 1}, ...}
    """
    hotel = get_object_or_404(Hotel, slug=hotel_slug, is_published=True)
    room_types = RoomType.objects.filter(hotel=hotel, is_active=True)

    today = date.today()
    availability = {}

    for i in range(90):
        d = today + timedelta(days=i)
        d_str = d.isoformat()
        availability[d_str] = {}
        for rt in room_types:
            availability[d_str][rt.slug if hasattr(rt, "slug") else str(rt.pk)] = {
                "name": rt.name,
                "available": rt.get_available_count(d, d + timedelta(days=1)),
                "price_npr": str(rt.price_per_night_npr),
            }

    return JsonResponse({"hotel": hotel.name, "availability": availability})


# ── Hotel detail with booking widget ──────────────────────────────────────────

@login_required
def hotel_detail(request, hotel_slug):
    hotel = get_object_or_404(Hotel, slug=hotel_slug, is_published=True)
    room_types = RoomType.objects.filter(hotel=hotel, is_active=True)

    # Check subscription
    if not request.user.is_subscribed:
        messages.warning(request, "Subscribe to book hotels through NepaXplore.")
        return redirect("subscriptions:plans")

    return render(request, "bookings/hotel_detail.html", {
        "hotel": hotel,
        "room_types": room_types,
        "today": date.today().isoformat(),
        "max_date": (date.today() + timedelta(days=365)).isoformat(),
    })


# ── Book room ──────────────────────────────────────────────────────────────────

@login_required
def book_room(request, hotel_slug):
    hotel = get_object_or_404(Hotel, slug=hotel_slug, is_published=True)

    if not request.user.is_subscribed:
        return redirect("subscriptions:plans")

    if request.method == "POST":
        room_type_id = request.POST.get("room_type")
        check_in_str = request.POST.get("check_in", "")
        check_out_str = request.POST.get("check_out", "")
        guests = int(request.POST.get("guests_count", 1))
        special_requests = request.POST.get("special_requests", "")

        # Validate dates
        try:
            check_in = date.fromisoformat(check_in_str)
            check_out = date.fromisoformat(check_out_str)
        except ValueError:
            messages.error(request, "Invalid dates. Please use the date picker.")
            return redirect("bookings:hotel_detail", hotel_slug=hotel_slug)

        today = date.today()
        if check_in < today:
            messages.error(request, "Check-in date cannot be in the past.")
            return redirect("bookings:hotel_detail", hotel_slug=hotel_slug)
        if check_out <= check_in:
            messages.error(request, "Check-out must be after check-in.")
            return redirect("bookings:hotel_detail", hotel_slug=hotel_slug)
        if (check_out - check_in).days > 30:
            messages.error(request, "Maximum stay is 30 nights.")
            return redirect("bookings:hotel_detail", hotel_slug=hotel_slug)

        # Validate room type
        room_type = get_object_or_404(RoomType, pk=room_type_id, hotel=hotel, is_active=True)

        if not room_type.is_available(check_in, check_out):
            messages.error(
                request,
                f"Sorry, {room_type.name} is not available for those dates. "
                "Please choose different dates or another room type."
            )
            return redirect("bookings:hotel_detail", hotel_slug=hotel_slug)

        if guests > room_type.capacity:
            messages.error(
                request,
                f"{room_type.name} can accommodate max {room_type.capacity} guests."
            )
            return redirect("bookings:hotel_detail", hotel_slug=hotel_slug)

        # Create pending booking
        booking = Booking.objects.create(
            user=request.user,
            hotel=hotel,
            room_type=room_type,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests,
            special_requests=special_requests,
            price_per_night_npr=room_type.price_per_night_npr,
            total_nights=(check_out - check_in).days,
            total_npr=room_type.price_per_night_npr * (check_out - check_in).days,
            deposit_npr=round(room_type.price_per_night_npr * (check_out - check_in).days * Decimal("0.3") / 50) * 50,
        )

        return redirect("bookings:pay_deposit", reference=booking.reference)

    return redirect("bookings:hotel_detail", hotel_slug=hotel_slug)


# ── Pay deposit ────────────────────────────────────────────────────────────────

@login_required
def pay_deposit(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)

    if booking.status != "pending":
        return redirect("bookings:booking_detail", reference=reference)

    return render(request, "bookings/pay_deposit.html", {
        "booking": booking,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    })


@login_required
def pay_stripe(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if booking.status != "pending":
        return redirect("bookings:booking_detail", reference=reference)

    session = stripe.checkout.Session.create(
        customer_email=request.user.email,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "npr",
                "unit_amount": int(booking.deposit_npr * 100),
                "product_data": {
                    "name": f"Deposit — {booking.hotel.name} ({booking.room_type.name})",
                    "description": (
                        f"{booking.check_in.strftime('%b %d')} – "
                        f"{booking.check_out.strftime('%b %d, %Y')}, "
                        f"{booking.total_nights} night(s)"
                    ),
                },
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=request.build_absolute_uri(
            f"/bookings/stripe/success/?session_id={{CHECKOUT_SESSION_ID}}&ref={reference}"
        ),
        cancel_url=request.build_absolute_uri(f"/bookings/{reference}/pay/"),
        metadata={"booking_reference": reference},
    )
    return redirect(session.url, permanent=False)


@login_required
def stripe_booking_success(request):
    session_id = request.GET.get("session_id")
    reference = request.GET.get("ref")

    if not session_id or not reference:
        return redirect("bookings:my_bookings")

    booking = get_object_or_404(Booking, reference=reference, user=request.user)

    if booking.status == "pending":
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            BookingPayment.objects.create(
                booking=booking,
                gateway="stripe",
                payment_type="deposit",
                amount_npr=booking.deposit_npr,
                gateway_transaction_id=session.payment_intent or session_id,
                status="success",
                paid_at=timezone.now(),
                raw_response={"session_id": session_id},
            )
            booking.status = "paid"
            booking.save(update_fields=["status"])
            _notify_hotel_staff(booking)
            messages.success(
                request,
                f"Deposit paid! Booking {reference} is awaiting hotel confirmation."
            )

    return redirect("bookings:booking_detail", reference=reference)


@login_required
def pay_khalti(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if booking.status != "pending":
        return redirect("bookings:booking_detail", reference=reference)

    payload = {
        "return_url": request.build_absolute_uri(f"/bookings/khalti/verify/?ref={reference}"),
        "website_url": request.build_absolute_uri("/"),
        "amount": int(booking.deposit_npr * 100),
        "purchase_order_id": f"BK-{reference}",
        "purchase_order_name": f"Deposit — {booking.hotel.name}",
        "customer_info": {
            "name": request.user.display_name,
            "email": request.user.email,
        },
    }
    resp = requests.post(
        f"{settings.KHALTI_BASE_URL}/epayment/initiate/",
        json=payload,
        headers={"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"},
        timeout=10,
    )
    if resp.status_code == 200:
        return redirect(resp.json()["payment_url"])
    messages.error(request, "Khalti initiation failed. Try another payment method.")
    return redirect("bookings:pay_deposit", reference=reference)


@login_required
def khalti_booking_verify(request):
    pidx = request.GET.get("pidx")
    reference = request.GET.get("ref")
    if not pidx or not reference:
        return redirect("bookings:my_bookings")

    booking = get_object_or_404(Booking, reference=reference, user=request.user)

    resp = requests.post(
        f"{settings.KHALTI_BASE_URL}/epayment/lookup/",
        json={"pidx": pidx},
        headers={"Authorization": f"Key {settings.KHALTI_SECRET_KEY}"},
        timeout=10,
    )
    if resp.status_code == 200 and resp.json().get("status") == "Completed":
        data = resp.json()
        if booking.status == "pending":
            BookingPayment.objects.create(
                booking=booking,
                gateway="khalti",
                payment_type="deposit",
                amount_npr=Decimal(str(data.get("total_amount", 0))) / 100,
                gateway_transaction_id=pidx,
                status="success",
                paid_at=timezone.now(),
                raw_response=data,
            )
            booking.status = "paid"
            booking.save(update_fields=["status"])
            _notify_hotel_staff(booking)
            messages.success(
                request,
                f"Deposit paid via Khalti! Booking {reference} awaiting hotel confirmation."
            )
    else:
        messages.error(request, "Khalti payment verification failed.")

    return redirect("bookings:booking_detail", reference=reference)


@login_required
def pay_esewa(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if booking.status != "pending":
        return redirect("bookings:booking_detail", reference=reference)

    amount = int(booking.deposit_npr)
    product_id = f"BK-{reference}"
    msg = f"total_amount={amount},transaction_uuid={product_id},product_code={settings.ESEWA_MERCHANT_CODE}"
    signature = base64.b64encode(
        hmac.new(
            settings.ESEWA_SECRET_KEY.encode(),
            msg.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()

    return render(request, "bookings/esewa_redirect.html", {
        "booking": booking,
        "amount": amount,
        "product_id": product_id,
        "merchant_code": settings.ESEWA_MERCHANT_CODE,
        "signature": signature,
        "esewa_url": f"{settings.ESEWA_BASE_URL}/api/epay/main/v2/form",
        "success_url": request.build_absolute_uri(f"/bookings/esewa/verify/?ref={reference}"),
        "failure_url": request.build_absolute_uri(f"/bookings/{reference}/pay/"),
    })


@login_required
def esewa_booking_verify(request):
    reference = request.GET.get("ref")
    encoded = request.GET.get("data", "")
    if not reference or not encoded:
        return redirect("bookings:my_bookings")

    booking = get_object_or_404(Booking, reference=reference, user=request.user)

    import json
    try:
        decoded = json.loads(base64.b64decode(encoded + "==").decode())
    except Exception:
        messages.error(request, "eSewa verification failed.")
        return redirect("bookings:pay_deposit", reference=reference)

    if decoded.get("status") == "COMPLETE" and booking.status == "pending":
        BookingPayment.objects.create(
            booking=booking,
            gateway="esewa",
            payment_type="deposit",
            amount_npr=Decimal(str(decoded.get("total_amount", 0))),
            gateway_transaction_id=decoded.get("transaction_code", ""),
            status="success",
            paid_at=timezone.now(),
            raw_response=decoded,
        )
        booking.status = "paid"
        booking.save(update_fields=["status"])
        _notify_hotel_staff(booking)
        messages.success(
            request,
            f"Deposit paid via eSewa! Booking {reference} awaiting hotel confirmation."
        )
    else:
        messages.error(request, "eSewa payment was not completed.")

    return redirect("bookings:booking_detail", reference=reference)


def _notify_hotel_staff(booking):
    """Create notification for all staff users + send booking to hotel."""
    from apps.core.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()
    for staff in User.objects.filter(is_staff=True):
        Notification.objects.create(
            user=staff,
            notification_type="new_video",  # reuse — generic alert type
            title=f"New booking — {booking.hotel.name}",
            body=(
                f"Booking {booking.reference} from {booking.user.display_name}. "
                f"Check-in: {booking.check_in.strftime('%b %d, %Y')}. "
                f"Deposit paid: NPR {booking.deposit_npr:,.0f}. "
                "Please confirm in the staff portal."
            ),
            link=f"/hotels/staff/{booking.hotel.slug}/",
        )


# ── User bookings ──────────────────────────────────────────────────────────────

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related(
        "hotel", "room_type"
    )
    return render(request, "bookings/my_bookings.html", {"bookings": bookings})


@login_required
def booking_detail(request, reference):
    booking = get_object_or_404(
        Booking.objects.select_related("hotel", "room_type", "confirmed_by"),
        reference=reference,
        user=request.user,
    )
    payments = booking.payments.all()
    return render(request, "bookings/booking_detail.html", {
        "booking": booking,
        "payments": payments,
    })


@login_required
@require_POST
def cancel_booking(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)

    if not booking.is_cancellable:
        messages.error(
            request,
            "This booking cannot be cancelled. Cancellations must be made at least 24 hours before check-in."
        )
        return redirect("bookings:booking_detail", reference=reference)

    reason = request.POST.get("reason", "Cancelled by guest")
    booking.cancel(cancelled_by="user", reason=reason)
    messages.success(
        request,
        f"Booking {reference} has been cancelled. "
        "Refund policy applies — contact support for refund queries."
    )
    return redirect("bookings:my_bookings")


# ── Staff portal ───────────────────────────────────────────────────────────────

@staff_member_required
def staff_dashboard(request, hotel_slug):
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    status_filter = request.GET.get("status", "paid")

    bookings = Booking.objects.filter(hotel=hotel).select_related(
        "user", "room_type"
    )

    if status_filter != "all":
        bookings = bookings.filter(status=status_filter)

    # Stats for today
    today = date.today()
    arriving_today = Booking.objects.filter(
        hotel=hotel, check_in=today, status="confirmed"
    ).count()
    departing_today = Booking.objects.filter(
        hotel=hotel, check_out=today, status="checked_in"
    ).count()
    pending_confirm = Booking.objects.filter(hotel=hotel, status="paid").count()
    active_stays = Booking.objects.filter(hotel=hotel, status="checked_in").count()

    room_types = RoomType.objects.filter(hotel=hotel, is_active=True)

    return render(request, "bookings/staff/dashboard.html", {
        "hotel": hotel,
        "bookings": bookings,
        "status_filter": status_filter,
        "arriving_today": arriving_today,
        "departing_today": departing_today,
        "pending_confirm": pending_confirm,
        "active_stays": active_stays,
        "room_types": room_types,
        "today": today,
        "status_choices": Booking.STATUS_CHOICES,
    })


@staff_member_required
def staff_confirm_booking(request, hotel_slug, booking_id):
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    booking = get_object_or_404(Booking, pk=booking_id, hotel=hotel, status="paid")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "confirm":
            booking.staff_confirm(request.user)
            messages.success(
                request,
                f"Booking {booking.reference} confirmed. Guest has been notified."
            )
        elif action == "reject":
            reason = request.POST.get("reason", "Rejected by hotel")
            booking.cancel(cancelled_by="hotel", reason=reason)
            messages.warning(
                request,
                f"Booking {booking.reference} rejected. Guest has been notified."
            )
        return redirect("bookings:staff_dashboard", hotel_slug=hotel_slug)

    return render(request, "bookings/staff/confirm_popup.html", {
        "hotel": hotel,
        "booking": booking,
    })


@staff_member_required
def staff_checkin(request, hotel_slug, booking_id):
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    booking = get_object_or_404(Booking, pk=booking_id, hotel=hotel, status="confirmed")

    if request.method == "POST":
        booking.staff_check_in(request.user)
        messages.success(
            request,
            f"Guest checked in — Booking {booking.reference}. Welcome to {hotel.name}!"
        )
        return redirect("bookings:staff_dashboard", hotel_slug=hotel_slug)

    return render(request, "bookings/staff/checkin_popup.html", {
        "hotel": hotel,
        "booking": booking,
    })


@staff_member_required
def staff_checkout(request, hotel_slug, booking_id):
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    booking = get_object_or_404(Booking, pk=booking_id, hotel=hotel, status="checked_in")

    if request.method == "POST":
        booking.staff_check_out(request.user)
        messages.success(
            request,
            f"Booking {booking.reference} checked out. Room is now available."
        )
        return redirect("bookings:staff_dashboard", hotel_slug=hotel_slug)

    return render(request, "bookings/staff/checkout_popup.html", {
        "hotel": hotel,
        "booking": booking,
    })


@staff_member_required
def staff_no_show(request, hotel_slug, booking_id):
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    booking = get_object_or_404(Booking, pk=booking_id, hotel=hotel)

    if request.method == "POST" and booking.status in ("confirmed", "paid"):
        booking.status = "no_show"
        booking.save(update_fields=["status"])
        messages.warning(request, f"Booking {booking.reference} marked as no show.")

    return redirect("bookings:staff_dashboard", hotel_slug=hotel_slug)


@staff_member_required
def staff_block_dates(request, hotel_slug):
    """Staff manually blocks dates for maintenance, renovation, etc."""
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    room_types = RoomType.objects.filter(hotel=hotel, is_active=True)

    if request.method == "POST":
        room_type_id = request.POST.get("room_type")
        block_from = request.POST.get("block_from")
        block_to = request.POST.get("block_to")
        reason = request.POST.get("reason", "Blocked by staff")

        try:
            room_type = RoomType.objects.get(pk=room_type_id, hotel=hotel)
            start = date.fromisoformat(block_from)
            end = date.fromisoformat(block_to)

            # Create a cancelled placeholder booking to block availability
            block_booking = Booking.objects.create(
                user=request.user,
                hotel=hotel,
                room_type=room_type,
                check_in=start,
                check_out=end,
                guests_count=room_type.total_rooms,  # blocks all rooms
                special_requests=f"[BLOCKED] {reason}",
                price_per_night_npr=0,
                total_nights=(end - start).days,
                total_npr=0,
                deposit_npr=0,
                status="confirmed",  # confirmed = blocks availability
            )
            messages.success(
                request,
                f"{room_type.name} blocked from {start} to {end}. Ref: {block_booking.reference}"
            )
        except Exception as e:
            messages.error(request, f"Error blocking dates: {e}")

        return redirect("bookings:staff_dashboard", hotel_slug=hotel_slug)

    return render(request, "bookings/staff/block_dates.html", {
        "hotel": hotel,
        "room_types": room_types,
        "today": date.today().isoformat(),
    })
