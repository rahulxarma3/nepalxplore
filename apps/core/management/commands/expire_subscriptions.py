"""
python manage.py expire_subscriptions

Marks subscriptions as expired when end_date has passed.
Schedule this on Railway as a cron job — runs daily at midnight NPT.

Railway cron setup:
  1. Add a new "Cron" service in Railway
  2. Command: python manage.py expire_subscriptions
  3. Schedule: 0 18 * * *  (18:00 UTC = midnight NPT)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.subscriptions.models import Subscription


class Command(BaseCommand):
    help = "Expire subscriptions that have passed their end_date"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be expired without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        # Find active subscriptions that have expired
        expired_qs = Subscription.objects.filter(
            status="active",
            end_date__lt=now,
        )

        count = expired_qs.count()

        if count == 0:
            self.stdout.write("✅ No expired subscriptions found.")
            return

        if dry_run:
            self.stdout.write(f"[DRY RUN] Would expire {count} subscription(s):")
            for sub in expired_qs.select_related("user", "plan"):
                self.stdout.write(
                    f"  - {sub.user.email} | {sub.plan.name} | ended {sub.end_date.strftime('%Y-%m-%d %H:%M')}"
                )
            return

        # Send expiry notifications before marking expired
        from apps.core.models import Notification
        for sub in expired_qs.select_related("user", "plan"):
            Notification.create_for_user(
                user=sub.user,
                notification_type="sub_expired",
                title="Your subscription has expired",
                body=f"Your {sub.plan.name} subscription expired. Renew now to keep accessing NepaXplore.",
                link="/subscribe/",
            )

        # Mark as expired
        updated = expired_qs.update(status="expired")

        self.stdout.write(
            self.style.SUCCESS(f"✅ Expired {updated} subscription(s).")
        )

        # Send 7-day expiry warnings
        warning_qs = Subscription.objects.filter(
            status="active",
            end_date__gt=now,
            end_date__lte=now + timezone.timedelta(days=7),
            auto_renew=False,
        ).select_related("user", "plan")

        warned = 0
        for sub in warning_qs:
            days = (sub.end_date - now).days
            existing = Notification.objects.filter(
                user=sub.user,
                notification_type="sub_expiring",
                created_at__gte=now - timezone.timedelta(hours=20),
            ).exists()
            if not existing:
                Notification.create_for_user(
                    user=sub.user,
                    notification_type="sub_expiring",
                    title=f"Subscription expiring in {days} day{'s' if days != 1 else ''}",
                    body="Your NepaXplore subscription is expiring soon. Renew to keep full access.",
                    link="/subscribe/",
                )
                warned += 1

        if warned:
            self.stdout.write(self.style.WARNING(f"⚠️  Sent {warned} expiry warning(s)."))

        # Log each one
        for sub in Subscription.objects.filter(
            status="expired",
            end_date__gte=now - timezone.timedelta(minutes=5),
        ).select_related("user", "plan"):
            self.stdout.write(
                f"  → {sub.user.email} | {sub.plan.name} | expired {sub.end_date.strftime('%Y-%m-%d')}"
            )
