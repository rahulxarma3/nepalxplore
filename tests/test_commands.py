"""
tests/test_commands.py

Tests for management commands:
- seed_data: creates plans + categories
- expire_subscriptions: marks expired subs + sends notifications
- test_payments: creates sandbox subscribers
"""
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from io import StringIO

from tests.factories import make_user, make_plan, make_subscription


class SeedDataCommandTest(TestCase):

    def test_seed_data_creates_monthly_plan(self):
        from apps.subscriptions.models import Plan
        call_command("seed_data", stdout=StringIO())
        self.assertTrue(Plan.objects.filter(slug="monthly").exists())

    def test_seed_data_creates_yearly_plan(self):
        from apps.subscriptions.models import Plan
        call_command("seed_data", stdout=StringIO())
        self.assertTrue(Plan.objects.filter(slug="yearly").exists())

    def test_seed_data_monthly_price_is_2000(self):
        from apps.subscriptions.models import Plan
        call_command("seed_data", stdout=StringIO())
        plan = Plan.objects.get(slug="monthly")
        self.assertEqual(plan.price_npr, 2000)

    def test_seed_data_yearly_price_is_20000(self):
        from apps.subscriptions.models import Plan
        call_command("seed_data", stdout=StringIO())
        plan = Plan.objects.get(slug="yearly")
        self.assertEqual(plan.price_npr, 20000)

    def test_seed_data_creates_categories(self):
        from apps.content.models import Category
        call_command("seed_data", stdout=StringIO())
        self.assertGreater(Category.objects.count(), 0)

    def test_seed_data_idempotent(self):
        """Running twice should not create duplicates."""
        from apps.subscriptions.models import Plan
        call_command("seed_data", stdout=StringIO())
        call_command("seed_data", stdout=StringIO())
        self.assertEqual(Plan.objects.filter(slug="monthly").count(), 1)
        self.assertEqual(Plan.objects.filter(slug="yearly").count(), 1)


class ExpireSubscriptionsCommandTest(TestCase):

    def setUp(self):
        self.user = make_user()
        make_plan()

    def test_expires_subscriptions_past_end_date(self):
        from apps.subscriptions.models import Subscription
        sub = make_subscription(self.user, status="active", days=-1)
        call_command("expire_subscriptions", stdout=StringIO())
        sub.refresh_from_db()
        self.assertEqual(sub.status, "expired")

    def test_does_not_expire_active_subscriptions(self):
        from apps.subscriptions.models import Subscription
        sub = make_subscription(self.user, status="active", days=30)
        call_command("expire_subscriptions", stdout=StringIO())
        sub.refresh_from_db()
        self.assertEqual(sub.status, "active")

    def test_sends_expired_notification(self):
        from apps.core.models import Notification
        self.user.notifications_enabled = True
        self.user.save()
        make_subscription(self.user, status="active", days=-1)
        call_command("expire_subscriptions", stdout=StringIO())
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                notification_type="sub_expired",
            ).exists()
        )

    def test_sends_expiry_warning_for_7_day_subs(self):
        from apps.core.models import Notification
        self.user.notifications_enabled = True
        self.user.save()
        sub = make_subscription(self.user, status="active", days=5)
        sub.auto_renew = False
        sub.save()
        call_command("expire_subscriptions", stdout=StringIO())
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                notification_type="sub_expiring",
            ).exists()
        )

    def test_does_not_warn_auto_renew_subscriptions(self):
        from apps.core.models import Notification
        self.user.notifications_enabled = True
        self.user.save()
        sub = make_subscription(self.user, status="active", days=5)
        sub.auto_renew = True  # auto-renew ON — no warning needed
        sub.save()
        call_command("expire_subscriptions", stdout=StringIO())
        self.assertFalse(
            Notification.objects.filter(
                user=self.user,
                notification_type="sub_expiring",
            ).exists()
        )

    def test_dry_run_does_not_change_status(self):
        from apps.subscriptions.models import Subscription
        sub = make_subscription(self.user, status="active", days=-1)
        call_command("expire_subscriptions", "--dry-run", stdout=StringIO())
        sub.refresh_from_db()
        self.assertEqual(sub.status, "active")

    def test_no_output_when_nothing_to_expire(self):
        make_subscription(self.user, status="active", days=30)
        out = StringIO()
        call_command("expire_subscriptions", stdout=out)
        self.assertIn("No expired", out.getvalue())


class TestPaymentsCommandTest(TestCase):

    def setUp(self):
        make_plan()

    def test_creates_test_user_when_not_exists(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        call_command(
            "test_payments",
            "--email", "fresh@cmd.com",
            stdout=StringIO(),
        )
        self.assertTrue(User.objects.filter(email="fresh@cmd.com").exists())

    def test_creates_active_subscription(self):
        from apps.subscriptions.models import Subscription
        call_command(
            "test_payments",
            "--email", "subtest@cmd.com",
            "--gateway", "khalti",
            stdout=StringIO(),
        )
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.get(email="subtest@cmd.com")
        self.assertTrue(user.is_subscribed)

    def test_creates_transaction_record(self):
        from apps.subscriptions.models import PaymentTransaction
        call_command(
            "test_payments",
            "--email", "txncmd@cmd.com",
            "--gateway", "esewa",
            stdout=StringIO(),
        )
        self.assertTrue(
            PaymentTransaction.objects.filter(
                gateway="esewa",
                status="success",
            ).exists()
        )

    def test_expire_flag_sets_short_end_date(self):
        from apps.subscriptions.models import Subscription
        from django.utils import timezone
        call_command(
            "test_payments",
            "--email", "expirecmd@cmd.com",
            "--expire",
            stdout=StringIO(),
        )
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.get(email="expirecmd@cmd.com")
        sub = Subscription.objects.get(user=user)
        # End date should be very close to now (2 min ahead)
        diff = (sub.end_date - timezone.now()).total_seconds()
        self.assertLess(diff, 180)

    def test_reset_flag_removes_subscription(self):
        from apps.subscriptions.models import Subscription
        from django.contrib.auth import get_user_model
        # First create a subscription
        call_command(
            "test_payments",
            "--email", "resetcmd@cmd.com",
            stdout=StringIO(),
        )
        # Then reset
        call_command(
            "test_payments",
            "--email", "resetcmd@cmd.com",
            "--reset",
            stdout=StringIO(),
        )
        user = get_user_model().objects.get(email="resetcmd@cmd.com")
        self.assertFalse(
            Subscription.objects.filter(user=user).exists()
        )

    def test_fails_gracefully_without_plans(self):
        from apps.subscriptions.models import Plan
        Plan.objects.all().delete()
        out = StringIO()
        call_command(
            "test_payments",
            "--email", "noplan@cmd.com",
            stdout=out,
        )
        self.assertIn("not found", out.getvalue())
