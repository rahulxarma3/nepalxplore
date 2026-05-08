"""
python manage.py process_bookings

The dual confirmation backend engine. Run daily at midnight NPT via Railway cron.

What it does:
  1. Auto checkout: marks checked_in bookings as checked_out when check_out date passes
  2. No-show detection: marks confirmed bookings as no_show if check_in passed 24hrs ago
  3. Staff popup alerts: sends notifications to staff for arriving/departing guests today
  4. Reminder to guests: sends check-in reminder day before arrival
  5. Pending cleanup: cancels unpaid bookings older than 2 hours

Railway cron schedule: 15 18 * * *  (18:15 UTC = midnight 00:00 NPT)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from apps.bookings.models import Booking
from apps.core.models import Notification

User = get_user_model()


class Command(BaseCommand):
    help = "Process booking state transitions and send staff/guest notifications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without making changes",
        )
        parser.add_argument(
            "--date",
            type=str,
            default="",
            help="Override today's date for testing (YYYY-MM-DD)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = date.today()
        if options["date"]:
            try:
                today = date.fromisoformat(options["date"])
                self.stdout.write(f"Using override date: {today}")
            except ValueError:
                self.stdout.write(self.style.ERROR("Invalid date format. Use YYYY-MM-DD"))
                return

        now = timezone.now()
        self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Processing bookings for {today}\n{'='*55}")

        total_actions = 0

        # ── 1. Auto checkout ───────────────────────────────────────────────────
        self.stdout.write("\n── Auto checkout ─────────────────────────────────────")
        past_checkout = Booking.objects.filter(
            status="checked_in",
            check_out__lt=today,
        ).select_related("user", "hotel", "room_type")

        if past_checkout.exists():
            self.stdout.write(f"Found {past_checkout.count()} booking(s) to auto checkout:")
            for booking in past_checkout:
                self.stdout.write(
                    f"  → {booking.reference} | {booking.hotel.name} | "
                    f"Guest: {booking.user.display_name} | "
                    f"Was due: {booking.check_out}"
                )
                if not dry_run:
                    booking.auto_check_out()
                    # Notify staff
                    self._notify_staff(
                        title=f"Auto checkout — {booking.reference}",
                        body=(
                            f"{booking.user.display_name} auto checked out from "
                            f"{booking.room_type.name}. "
                            f"Room is now available. Please verify with guest."
                        ),
                        link=f"/hotels/staff/{booking.hotel.slug}/",
                    )
                total_actions += 1
            self.stdout.write(self.style.SUCCESS(f"  ✅ {past_checkout.count()} booking(s) auto checked out"))
        else:
            self.stdout.write("  No bookings to auto checkout")

        # ── 2. No-show detection ───────────────────────────────────────────────
        self.stdout.write("\n── No-show detection ─────────────────────────────────")
        no_show_cutoff = today - timedelta(days=1)
        no_shows = Booking.objects.filter(
            status__in=["confirmed", "paid"],
            check_in__lt=no_show_cutoff,
        ).select_related("user", "hotel")

        if no_shows.exists():
            self.stdout.write(f"Found {no_shows.count()} potential no-show(s):")
            for booking in no_shows:
                self.stdout.write(
                    f"  → {booking.reference} | {booking.hotel.name} | "
                    f"Check-in was: {booking.check_in}"
                )
                if not dry_run:
                    booking.status = "no_show"
                    booking.save(update_fields=["status"])
                    self._notify_staff(
                        title=f"No-show — {booking.reference}",
                        body=(
                            f"{booking.user.display_name} did not check in. "
                            f"Booking {booking.reference} marked as no-show."
                        ),
                        link=f"/hotels/staff/{booking.hotel.slug}/",
                    )
                    Notification.create_for_user(
                        user=booking.user,
                        notification_type="sub_expired",
                        title=f"Booking {booking.reference} — no-show recorded",
                        body=(
                            "Your booking was marked as no-show as you did not check in. "
                            "Contact support if this is an error."
                        ),
                        link=f"/bookings/{booking.reference}/",
                    )
                total_actions += 1
            self.stdout.write(self.style.WARNING(f"  ⚠️  {no_shows.count()} no-show(s) recorded"))
        else:
            self.stdout.write("  No no-shows detected")

        # ── 3. Arriving today — staff popup notification ───────────────────────
        self.stdout.write("\n── Arriving today ────────────────────────────────────")
        arriving = Booking.objects.filter(
            status="confirmed",
            check_in=today,
        ).select_related("user", "hotel", "room_type")

        if arriving.exists():
            self.stdout.write(f"Found {arriving.count()} guest(s) arriving today:")
            for booking in arriving:
                self.stdout.write(
                    f"  → {booking.reference} | {booking.hotel.name} | "
                    f"{booking.room_type.name} | {booking.user.display_name} "
                    f"({booking.guests_count} guest(s))"
                )
                if not dry_run:
                    self._notify_staff(
                        title=f"🛎 Guest arriving today — {booking.reference}",
                        body=(
                            f"{booking.user.display_name} is checking into "
                            f"{booking.room_type.name} today. "
                            f"Balance due: NPR {booking.remaining_balance_npr:,.0f}. "
                            "Mark check-in when guest arrives."
                        ),
                        link=f"/hotels/staff/{booking.hotel.slug}/",
                    )
                total_actions += 1
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Staff notified for {arriving.count()} arrival(s)")
            )
        else:
            self.stdout.write("  No arrivals today")

        # ── 4. Departing today — staff popup notification ──────────────────────
        self.stdout.write("\n── Departing today ───────────────────────────────────")
        departing = Booking.objects.filter(
            status="checked_in",
            check_out=today,
        ).select_related("user", "hotel", "room_type")

        if departing.exists():
            self.stdout.write(f"Found {departing.count()} guest(s) departing today:")
            for booking in departing:
                self.stdout.write(
                    f"  → {booking.reference} | {booking.hotel.name} | "
                    f"{booking.user.display_name}"
                )
                if not dry_run:
                    self._notify_staff(
                        title=f"🏁 Guest departing today — {booking.reference}",
                        body=(
                            f"{booking.user.display_name} checks out from "
                            f"{booking.room_type.name} today. "
                            "Please mark checkout once guest leaves. "
                            "If guest does not leave by end of day it will be auto-marked."
                        ),
                        link=f"/hotels/staff/{booking.hotel.slug}/",
                    )
                total_actions += 1
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Staff notified for {departing.count()} departure(s)")
            )
        else:
            self.stdout.write("  No departures today")

        # ── 5. Guest check-in reminders (day before) ───────────────────────────
        self.stdout.write("\n── Guest reminders (arriving tomorrow) ───────────────")
        tomorrow = today + timedelta(days=1)
        tomorrow_arrivals = Booking.objects.filter(
            status="confirmed",
            check_in=tomorrow,
        ).select_related("user", "hotel")

        if tomorrow_arrivals.exists():
            self.stdout.write(f"Sending reminders to {tomorrow_arrivals.count()} guest(s):")
            for booking in tomorrow_arrivals:
                self.stdout.write(
                    f"  → {booking.reference} | {booking.user.display_name}"
                )
                if not dry_run:
                    Notification.create_for_user(
                        user=booking.user,
                        notification_type="sub_expiring",
                        title=f"Check-in reminder — {booking.hotel.name} tomorrow!",
                        body=(
                            f"Your stay at {booking.hotel.name} starts tomorrow "
                            f"({booking.check_in.strftime('%B %d, %Y')}). "
                            f"Booking ref: {booking.reference}. "
                            f"Remaining balance: NPR {booking.remaining_balance_npr:,.0f}."
                        ),
                        link=f"/bookings/{booking.reference}/",
                    )
                total_actions += 1
            self.stdout.write(
                self.style.SUCCESS(f"  ✅ Reminders sent to {tomorrow_arrivals.count()} guest(s)")
            )
        else:
            self.stdout.write("  No guests arriving tomorrow")

        # ── 6. Cleanup expired pending bookings ────────────────────────────────
        self.stdout.write("\n── Cleanup unpaid bookings (>2 hours old) ────────────")
        cutoff = now - timedelta(hours=2)
        stale = Booking.objects.filter(status="pending", created_at__lt=cutoff)

        if stale.exists():
            count = stale.count()
            self.stdout.write(f"Found {count} stale pending booking(s) to cancel")
            if not dry_run:
                stale.update(
                    status="cancelled",
                    cancelled_by="system",
                    cancellation_reason="Payment not completed within 2 hours",
                )
            total_actions += count
            self.stdout.write(self.style.WARNING(f"  ⚠️  {count} stale booking(s) cancelled"))
        else:
            self.stdout.write("  No stale bookings")

        # ── Summary ────────────────────────────────────────────────────────────
        self.stdout.write(f"\n{'='*55}")
        suffix = " (dry run — no changes made)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Done. {total_actions} action(s) processed{suffix}\n"
            )
        )

    def _notify_staff(self, title, body, link=""):
        """Send notification to all staff users."""
        for staff in User.objects.filter(is_staff=True, notifications_enabled=True):
            Notification.objects.create(
                user=staff,
                notification_type="new_video",
                title=title,
                body=body,
                link=link,
            )
