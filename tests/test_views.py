"""
tests/test_views.py

Tests for all views — public pages, authenticated pages, subscription gating.
"""
from django.test import TestCase, Client
from django.urls import reverse

from tests.factories import (
    make_user, make_subscription, make_video,
    make_category, make_destination, make_plan,
)


class HomeViewTest(TestCase):

    def test_home_loads_for_anonymous(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NepaXplore")

    def test_home_uses_correct_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "core/home.html")


class FeedViewTest(TestCase):

    def setUp(self):
        self.cat = make_category()
        self.preview_video = make_video(
            slug="preview-1", is_feed_preview=True, is_published=True, category=self.cat
        )
        self.full_video = make_video(
            slug="full-1", is_feed_preview=False, is_published=True, category=self.cat
        )
        self.draft_video = make_video(
            slug="draft-1", is_feed_preview=True, is_published=False, category=self.cat
        )

    def test_feed_accessible_without_login(self):
        response = self.client.get("/feed/")
        self.assertEqual(response.status_code, 200)

    def test_feed_shows_only_published_preview_videos(self):
        response = self.client.get("/feed/")
        self.assertContains(response, self.preview_video.title)
        self.assertNotContains(response, self.full_video.title)
        self.assertNotContains(response, self.draft_video.title)

    def test_feed_filters_by_category(self):
        other_cat = make_category(name="Culture", slug="culture")
        other_video = make_video(
            slug="other-cat", title="Culture Video",
            is_feed_preview=True, is_published=True, category=other_cat
        )
        response = self.client.get(f"/feed/?category={other_cat.slug}")
        self.assertContains(response, other_video.title)
        self.assertNotContains(response, self.preview_video.title)

    def test_feed_uses_correct_template(self):
        response = self.client.get("/feed/")
        self.assertTemplateUsed(response, "content/feed.html")


class VideoDetailViewTest(TestCase):

    def setUp(self):
        self.preview_video = make_video(
            slug="free-video", is_feed_preview=True, is_published=True
        )
        self.full_video = make_video(
            slug="paid-video", is_feed_preview=False, is_published=True
        )
        self.user = make_user()
        self.subscriber = make_user(email="sub@test.com")
        make_subscription(self.subscriber, status="active", days=30)

    def test_preview_video_accessible_anonymous(self):
        response = self.client.get(f"/feed/video/{self.preview_video.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_full_video_redirects_anonymous_to_login(self):
        response = self.client.get(f"/feed/video/{self.full_video.slug}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_full_video_redirects_non_subscriber_to_plans(self):
        self.client.force_login(self.user)
        response = self.client.get(f"/feed/video/{self.full_video.slug}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/subscribe/", response["Location"])

    def test_full_video_accessible_to_subscriber(self):
        self.client.force_login(self.subscriber)
        response = self.client.get(f"/feed/video/{self.full_video.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_video_view_count_increments(self):
        before = self.preview_video.view_count
        self.client.get(f"/feed/video/{self.preview_video.slug}/")
        self.preview_video.refresh_from_db()
        self.assertEqual(self.preview_video.view_count, before + 1)

    def test_unpublished_video_returns_404(self):
        unpublished = make_video(slug="unpub", is_published=False)
        response = self.client.get(f"/feed/video/{unpublished.slug}/")
        self.assertEqual(response.status_code, 404)


class SubscriptionPlansViewTest(TestCase):

    def setUp(self):
        self.monthly = make_plan()
        from tests.factories import make_yearly_plan
        self.yearly = make_yearly_plan()

    def test_plans_page_loads_for_anonymous(self):
        response = self.client.get("/subscribe/")
        self.assertEqual(response.status_code, 200)

    def test_plans_page_shows_monthly_price(self):
        response = self.client.get("/subscribe/")
        self.assertContains(response, "2,000")

    def test_plans_page_shows_yearly_price(self):
        response = self.client.get("/subscribe/")
        self.assertContains(response, "20,000")

    def test_plans_page_shows_login_button_for_anonymous(self):
        response = self.client.get("/subscribe/")
        self.assertContains(response, "Log in to subscribe")

    def test_plans_page_shows_payment_buttons_for_logged_in(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.get("/subscribe/")
        self.assertContains(response, "Khalti")
        self.assertContains(response, "eSewa")
        self.assertContains(response, "Stripe")


class DestinationsViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.subscriber = make_user(email="sub@test.com")
        make_subscription(self.subscriber, status="active", days=30)
        self.destination = make_destination()

    def test_destinations_redirects_anonymous_to_login(self):
        response = self.client.get("/destinations/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_destinations_redirects_non_subscriber_to_plans(self):
        self.client.force_login(self.user)
        response = self.client.get("/destinations/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/subscribe/", response["Location"])

    def test_destinations_accessible_to_subscriber(self):
        self.client.force_login(self.subscriber)
        response = self.client.get("/destinations/")
        self.assertEqual(response.status_code, 200)

    def test_destination_detail_accessible_to_subscriber(self):
        self.client.force_login(self.subscriber)
        response = self.client.get(f"/destinations/{self.destination.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.destination.name)

    def test_trekking_page_gated(self):
        response = self.client.get("/destinations/trekking/")
        self.assertEqual(response.status_code, 302)

    def test_culture_page_gated(self):
        response = self.client.get("/destinations/culture/")
        self.assertEqual(response.status_code, 302)

    def test_hotels_page_gated(self):
        response = self.client.get("/destinations/hotels/")
        self.assertEqual(response.status_code, 302)


class ProfileViewTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_profile_requires_login(self):
        response = self.client.get("/accounts/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_profile_loads_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get("/accounts/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")

    def test_profile_update_personal_saves_name(self):
        self.client.force_login(self.user)
        response = self.client.post("/accounts/profile/update/", {
            "section": "personal",
            "first_name": "Sita",
            "last_name": "Rai",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Sita")
        self.assertEqual(self.user.last_name, "Rai")

    def test_profile_update_preferences_saves_dark_mode_off(self):
        self.client.force_login(self.user)
        # dark_mode checkbox not sent = off
        self.client.post("/accounts/profile/update/", {
            "section": "preferences",
            "preferred_language": "en",
        })
        self.user.refresh_from_db()
        self.assertFalse(self.user.dark_mode)

    def test_profile_update_preferences_saves_language(self):
        self.client.force_login(self.user)
        self.client.post("/accounts/profile/update/", {
            "section": "preferences",
            "preferred_language": "ne",
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.preferred_language, "ne")


class SearchViewTest(TestCase):

    def setUp(self):
        self.preview_video = make_video(
            slug="search-preview",
            title="History of Kathmandu Durbar",
            is_feed_preview=True,
            is_published=True,
        )
        self.full_video = make_video(
            slug="search-full",
            title="Everest Base Camp Trek Guide",
            is_feed_preview=False,
            is_published=True,
        )

    def test_search_page_loads(self):
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 200)

    def test_search_finds_preview_video_for_anonymous(self):
        response = self.client.get("/search/?q=Kathmandu")
        self.assertContains(response, self.preview_video.title)

    def test_search_hides_full_video_for_non_subscriber(self):
        response = self.client.get("/search/?q=Everest")
        self.assertNotContains(response, self.full_video.title)

    def test_search_finds_full_video_for_subscriber(self):
        subscriber = make_user(email="searchsub@test.com")
        make_subscription(subscriber, status="active", days=30)
        self.client.force_login(subscriber)
        response = self.client.get("/search/?q=Everest")
        self.assertContains(response, self.full_video.title)

    def test_search_empty_query_shows_no_results(self):
        response = self.client.get("/search/?q=")
        self.assertNotContains(response, self.preview_video.title)

    def test_search_short_query_shows_no_results(self):
        # Less than 2 chars should not trigger search
        response = self.client.get("/search/?q=K")
        self.assertNotContains(response, self.preview_video.title)


class UploadVideoViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.staff = make_user(email="staff@test.com", is_staff=True)

    def test_upload_requires_login(self):
        response = self.client.get("/feed/upload/")
        self.assertEqual(response.status_code, 302)

    def test_upload_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get("/feed/upload/")
        self.assertEqual(response.status_code, 302)  # redirects to admin login

    def test_upload_accessible_to_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get("/feed/upload/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "content/upload.html")


class AdminDashboardViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.staff = make_user(email="staff@test.com", is_staff=True)

    def test_dashboard_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_dashboard_accessible_to_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/admin_dashboard.html")

    def test_dashboard_shows_subscriber_count(self):
        subscriber = make_user(email="sub@test.com")
        make_subscription(subscriber, status="active", days=30)
        self.client.force_login(self.staff)
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Active subscribers")


class NotificationViewTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_notifications_requires_login(self):
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, 302)

    def test_notifications_loads_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get("/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/notifications.html")

    def test_notifications_marks_all_as_read_on_load(self):
        from apps.core.models import Notification
        notif = Notification.objects.create(
            user=self.user,
            notification_type="welcome",
            title="Welcome",
            body="Welcome!",
            is_read=False,
        )
        self.client.force_login(self.user)
        self.client.get("/notifications/")
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
