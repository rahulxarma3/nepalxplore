"""
apps/bookings/models.py

Full hotel booking system with dual confirmation:
- Staff confirms manually via portal
- Backend engine auto-marks checkout when date passes
- RoomAvailability always accurate from both sources
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, date


class RoomType(models.Model):
    """Room types within a hotel — Standard, Deluxe, Suite, etc."""
    hotel = models.ForeignKey(
        "destinations.Hotel",
        on_delete=models.CASCADE,
        related_name="room_types",
    )
    name = models.CharField(max_length=100)  # e.g. "Deluxe Mountain View"
    description = models.TextField(blank=True)
    capacity = models.PositiveSmallIntegerField(default=2)  # max guests
    total_rooms = models.PositiveSmallIntegerField(default=1)
    price_per_night_npr = models.DecimalField(max_digits=8, decimal_places=2)
    amenities = models.JSONField(default=list)  # ["WiFi", "Hot water", "Breakfast"]
    cover_image = models.ImageField(upload_to="rooms/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "price_per_night_npr"]

    def __str__(self):
        return f"{self.hotel.name} — {self.name}"

    def get_available_count(self, check_in: date, check_out: date) -> int:
        """
        Returns how many rooms are available for the given date range.
        A room is unavailable if it has a confirmed/paid/checked_in booking
        that overlaps the requested dates.
        """
        overlapping = Booking.objects.filter(
            room_type=self,
            status__in=["paid", "confirmed", "checked_in"],
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).count()
        return max(0, self.total_rooms - overlapping)

    def is_available(self, check_in: date, check_out: date) -> bool:
        return self.get_available_count(check_in, check_out) > 0


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending",     "Pending Payment"),
        ("paid",        "Paid — Awaiting Confirmation"),
        ("confirmed",   "Confirmed by Hotel"),
        ("checked_in",  "Checked In"),
        ("checked_out", "Checked Out"),
        ("cancelled",   "Cancelled"),
        ("no_show",     "No Show"),
    ]

    # Unique booking reference — shown to guests
    reference = models.CharField(max_length=12, unique=True, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    hotel = models.ForeignKey(
        "destinations.Hotel",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    check_in = models.DateField()
    check_out = models.DateField()
    guests_count = models.PositiveSmallIntegerField(default=1)
    special_requests = models.TextField(blank=True)

    # Pricing snapshot at booking time
    price_per_night_npr = models.DecimalField(max_digits=8, decimal_places=2)
    total_nights = models.PositiveSmallIntegerField()
    total_npr = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_npr = models.DecimalField(max_digits=10, decimal_places=2)  # 30% upfront

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")

    # Staff tracking
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="confirmed_bookings",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    # Auto-checkout tracking
    auto_checked_out = models.BooleanField(default=False)

    # Cancellation
    cancelled_by = models.CharField(max_length=10, blank=True)  # 'user' or 'hotel'
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — {self.hotel.name} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        if not self.total_nights:
            self.total_nights = (self.check_out - self.check_in).days
        if not self.total_npr:
            self.total_npr = self.price_per_night_npr * self.total_nights
        if not self.deposit_npr:
            # 30% deposit, rounded to nearest 50 NPR
            raw = self.total_npr * 30 / 100
            self.deposit_npr = round(raw / 50) * 50
        super().save(*args, **kwargs)

    def _generate_reference(self):
        import random, string
        while True:
            ref = "NX" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Booking.objects.filter(reference=ref).exists():
                return ref

    @property
    def nights(self):
        return (self.check_out - self.check_in).days

    @property
    def remaining_balance_npr(self):
        paid = self.payments.filter(status="success").aggregate(
            total=models.Sum("amount_npr")
        )["total"] or 0
        return max(0, self.total_npr - paid)

    @property
    def is_cancellable(self):
        """User can cancel up to 24 hours before check-in."""
        return (
            self.status in ("pending", "paid", "confirmed")
            and timezone.now().date() < self.check_in - timedelta(days=1)
        )

    def staff_confirm(self, staff_user):
        self.status = "confirmed"
        self.confirmed_by = staff_user
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])
        self._send_confirmation_notification()

    def staff_check_in(self, staff_user):
        self.status = "checked_in"
        self.checked_in_at = timezone.now()
        self.save(update_fields=["status", "checked_in_at", "updated_at"])
        self._send_checkin_notification()

    def staff_check_out(self, staff_user):
        self.status = "checked_out"
        self.checked_out_at = timezone.now()
        self.auto_checked_out = False
        self.save(update_fields=["status", "checked_out_at", "auto_checked_out", "updated_at"])
        self._free_availability()

    def auto_check_out(self):
        """Called by backend engine when check_out date passes."""
        self.status = "checked_out"
        self.checked_out_at = timezone.now()
        self.auto_checked_out = True
        self.save(update_fields=["status", "checked_out_at", "auto_checked_out", "updated_at"])
        self._free_availability()
        self._send_auto_checkout_notification()

    def cancel(self, cancelled_by="user", reason=""):
        self.status = "cancelled"
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.cancelled_at = timezone.now()
        self.save(update_fields=[
            "status", "cancelled_by", "cancellation_reason",
            "cancelled_at", "updated_at"
        ])
        self._free_availability()

    def _free_availability(self):
        """Availability is recalculated dynamically — nothing to update."""
        pass  # RoomType.get_available_count() queries live bookings

    def _send_confirmation_notification(self):
        from apps.core.models import Notification
        Notification.create_for_user(
            user=self.user,
            notification_type="sub_activated",  # reusing for booking confirmed
            title=f"Booking confirmed — {self.hotel.name}",
            body=(f"Your booking {self.reference} has been confirmed by the hotel. "
                  f"Check-in: {self.check_in.strftime('%b %d, %Y')}. "
                  f"Remaining balance: NPR {self.remaining_balance_npr:,.0f}."),
            link=f"/bookings/{self.reference}/",
        )

    def _send_checkin_notification(self):
        from apps.core.models import Notification
        Notification.create_for_user(
            user=self.user,
            notification_type="welcome",
            title=f"Welcome to {self.hotel.name}! 🏨",
            body=f"Your check-in has been recorded. Booking ref: {self.reference}.",
            link=f"/bookings/{self.reference}/",
        )

    def _send_auto_checkout_notification(self):
        from apps.core.models import Notification
        Notification.create_for_user(
            user=self.user,
            notification_type="welcome",
            title=f"Stay complete — {self.hotel.name}",
            body=(f"Your stay ({self.reference}) has ended. "
                  f"Thank you for choosing NepaXplore. We hope you enjoyed Nepal!"),
            link="/bookings/",
        )


class BookingPayment(models.Model):
    GATEWAY_CHOICES = [
        ("stripe", "Stripe"),
        ("esewa",  "eSewa"),
        ("khalti", "Khalti"),
    ]
    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("success",   "Success"),
        ("failed",    "Failed"),
        ("refunded",  "Refunded"),
    ]
    PAYMENT_TYPE = [
        ("deposit",  "Deposit (30%)"),
        ("balance",  "Remaining Balance"),
        ("full",     "Full Payment"),
    ]

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="payments"
    )
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE, default="deposit")
    amount_npr = models.DecimalField(max_digits=10, decimal_places=2)
    gateway_transaction_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="initiated")
    raw_response = models.JSONField(default=dict)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.reference} — {self.gateway} {self.amount_npr} [{self.status}]"
