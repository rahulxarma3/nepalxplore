"""
tests/test_models.py

Tests for all model methods and properties.
Covers: User, Subscription, Plan, Video, Notification
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from tests.factories import (
    make_user, make_plan, make_subscription,
    make_video, make_category, make_destination,
)


# ── User model ─────────────────────────────────────────────────────────────────

class UserModelTest(TestCase):

    def test_display_name_uses_full_name_when_set(self):
        user = make_user(first_name="Sita", last_name="Rai")
        self.assertEqual(user.display_name, "Sita Rai")

    def test_display_name_falls_back_to_email_prefix(self):
        user = make_user(email="rohan@example.com")
        self.assertEqual(user.display_name, "rohan")

    def test_is_subscribed_false_with_no_subscription(self):
        user = make_user()
        self.assertFalse(user.is_subscribed)

    def test_is_subscribed_true_with_active_subscription(self):
        user = make_user()
        make_subscription(user, status="active", days=30)
        # Refresh from DB
        user.refresh_from_db()
        self.assertTrue(user.is_subscribed)

    def test_is_subscribed_false_when_subscription_expired(self):
        user = make_user()
        make_subscription(user, status="expired", days=-1)
        user.refresh_from_db()
        self.assertFalse(user.is_subscribed)

    def test_dark_mode_default_is_true(self):
        user = make_user()
        self.assertTrue(user.dark_mode)

    def test_notifications_enabled_default_is_true(self):
        user = make_user()
        self.assertTrue(user.notifications_enabled)

    def test_preferred_language_default_is_en(self):
        user = make_user()
        self.assertEqual(user.preferred_language, "en")


# ── Plan model ─────────────────────────────────────────────────────────────────

class PlanModelTest(TestCase):

    def test_plan_str(self):
        plan = make_plan()
        self.assertIn("Monthly", str(plan))
        self.assertIn("monthly", str(plan))

    def test_monthly_plan_price(self):
        plan = make_plan()
        self.assertEqual(plan.price_npr, 2000)

    def test_yearly_plan_price(self):
        from tests.factories import make_yearly_plan
        plan = make_yearly_plan()
        self.assertEqual(plan.price_npr, 20000)

    def test_plan_is_active_by_default(self):
        plan = make_plan()
        self.assertTrue(plan.is_active)


# ── Subscription model ─────────────────────────────────────────────────────────

class SubscriptionModelTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.plan = make_plan()

    def test_is_active_true_when_active_and_future_end_date(self):
        sub = make_subscription(self.user, status="active", days=30)
        self.assertTrue(sub.is_active)

    def test_is_active_false_when_status_expired(self):
        sub = make_subscription(self.user, status="expired", days=30)
        self.assertFalse(sub.is_active)

    def test_is_active_false_when_end_date_past(self):
        sub = make_subscription(self.user, status="active", days=-1)
        self.assertFalse(sub.is_active)

    def test_days_remaining_correct(self):
        sub = make_subscription(self.user, status="active", days=10)
        self.assertAlmostEqual(sub.days_remaining, 10, delta=1)

    def test_days_remaining_zero_when_expired(self):
        sub = make_subscription(self.user, status="expired", days=-5)
        self.assertEqual(sub.days_remaining, 0)

    def test_activate_sets_status_active(self):
        from apps.subscriptions.models import Subscription
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            gateway="stripe",
            status="pending",
            end_date=timezone.now(),
        )
        sub.activate(gateway_ref="stripe_sub_123")
        self.assertEqual(sub.status, "active")

    def test_activate_sets_gateway_ref(self):
        from apps.subscriptions.models import Subscription
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            gateway="khalti",
            status="pending",
            end_date=timezone.now(),
        )
        sub.activate(gateway_ref="khalti_pidx_abc")
        self.assertEqual(sub.gateway_subscription_id, "khalti_pidx_abc")

    def test_activate_monthly_sets_end_date_30_days(self):
        from apps.subscriptions.models import Subscription
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,  # monthly
            gateway="esewa",
            status="pending",
            end_date=timezone.now(),
        )
        before = timezone.now()
        sub.activate()
        after = timezone.now()
        expected_min = before + timedelta(days=29)
        expected_max = after + timedelta(days=31)
        self.assertGreater(sub.end_date, expected_min)
        self.assertLess(sub.end_date, expected_max)

    def test_activate_yearly_sets_end_date_365_days(self):
        from tests.factories import make_yearly_plan
        from apps.subscriptions.models import Subscription
        yearly_plan = make_yearly_plan()
        sub = Subscription.objects.create(
            user=self.user,
            plan=yearly_plan,
            gateway="stripe",
            status="pending",
            end_date=timezone.now(),
        )
        sub.activate()
        expected = timezone.now() + timedelta(days=364)
        self.assertGreater(sub.end_date, expected)

    def test_subscription_str(self):
        sub = make_subscription(self.user)
        self.assertIn(self.user.email, str(sub))


# ── Video model ────────────────────────────────────────────────────────────────

class VideoModelTest(TestCase):

    def test_duration_display_formats_correctly(self):
        video = make_video(slug="v1")
        video.duration_seconds = 315  # 5:15
        self.assertEqual(video.duration_display, "5:15")

    def test_duration_display_pads_seconds(self):
        video = make_video(slug="v2")
        video.duration_seconds = 65  # 1:05
        self.assertEqual(video.duration_display, "1:05")

    def test_duration_display_zero(self):
        video = make_video(slug="v3")
        video.duration_seconds = 0
        self.assertEqual(video.duration_display, "0:00")

    def test_slug_auto_generated_from_title(self):
        from apps.content.models import Video
        video = Video(
            title="History of Pashupatinath",
            description="test",
            duration_seconds=100,
        )
        video.save()
        self.assertEqual(video.slug, "history-of-pashupatinath")

    def test_thumbnail_url_returns_placeholder_when_no_thumbnail(self):
        video = make_video(slug="v-no-thumb")
        # No file uploaded in tests
        self.assertIn("placeholder", video.thumbnail_url)

    def test_is_feed_preview_default_false(self):
        video = make_video(slug="v-default")
        self.assertFalse(video.is_feed_preview)

    def test_view_count_default_zero(self):
        video = make_video(slug="v-views")
        self.assertEqual(video.view_count, 0)


# ── Notification model ─────────────────────────────────────────────────────────

class NotificationModelTest(TestCase):

    def setUp(self):
        self.user = make_user(notifications_enabled=True)

    def test_create_for_user_creates_notification(self):
        from apps.core.models import Notification
        notif = Notification.create_for_user(
            user=self.user,
            notification_type="welcome",
            title="Welcome!",
            body="Welcome to NepaXplore.",
        )
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, "Welcome!")
        self.assertEqual(notif.user, self.user)

    def test_create_for_user_returns_none_when_notifications_disabled(self):
        from apps.core.models import Notification
        self.user.notifications_enabled = False
        self.user.save()
        result = Notification.create_for_user(
            user=self.user,
            notification_type="new_video",
            title="New video",
            body="Check it out.",
        )
        self.assertIsNone(result)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 0)

    def test_notification_is_unread_by_default(self):
        from apps.core.models import Notification
        notif = Notification.create_for_user(
            user=self.user,
            notification_type="welcome",
            title="Hi",
            body="Welcome.",
        )
        self.assertFalse(notif.is_read)

    def test_broadcast_new_video_notifies_active_subscribers(self):
        from apps.core.models import Notification

        # Active subscriber
        subscriber = make_user(
            email="sub@test.com",
            notifications_enabled=True,
        )
        make_subscription(subscriber, status="active", days=30)

        # Expired subscriber — should NOT be notified
        expired_user = make_user(
            email="expired@test.com",
            notifications_enabled=True,
        )
        make_subscription(expired_user, status="expired", days=-1)

        # Non-subscriber — should NOT be notified
        non_sub = make_user(email="nosub@test.com", notifications_enabled=True)

        video = make_video(slug="broadcast-video", is_published=True)
        count = Notification.broadcast_new_video(video)

        self.assertEqual(count, 1)
        self.assertTrue(
            Notification.objects.filter(user=subscriber, notification_type="new_video").exists()
        )
        self.assertFalse(
            Notification.objects.filter(user=expired_user).exists()
        )
        self.assertFalse(
            Notification.objects.filter(user=non_sub).exists()
        )

    def test_broadcast_respects_notifications_disabled(self):
        from apps.core.models import Notification
        subscriber = make_user(
            email="quiet@test.com",
            notifications_enabled=False,
        )
        make_subscription(subscriber, status="active", days=30)
        video = make_video(slug="quiet-video", is_published=True)
        count = Notification.broadcast_new_video(video)
        self.assertEqual(count, 0)
