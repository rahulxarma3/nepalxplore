"""
tests/test_api.py

Tests for the REST API (/api/v1/) used by the future mobile app.
Covers: auth, feed, video detail, destinations, subscriptions.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from tests.factories import (
    make_user, make_subscription, make_video,
    make_category, make_destination, make_plan,
)


class APIAuthTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_register_creates_user(self):
        from django.contrib.auth import get_user_model
        response = self.client.post("/api/v1/auth/register/", {
            "email": "newuser@api.com",
            "password": "SecurePass123!",
            "first_name": "Ram",
        })
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        User = get_user_model()
        self.assertTrue(User.objects.filter(email="newuser@api.com").exists())

    def test_register_rejects_duplicate_email(self):
        make_user(email="dup@api.com")
        response = self.client.post("/api/v1/auth/register/", {
            "email": "dup@api.com",
            "password": "SecurePass123!",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_register_rejects_short_password(self):
        response = self.client.post("/api/v1/auth/register/", {
            "email": "short@api.com",
            "password": "123",
        })
        self.assertEqual(response.status_code, 400)

    def test_login_returns_tokens(self):
        make_user(email="login@api.com", password="TestPass123!")
        response = self.client.post("/api/v1/auth/login/", {
            "email": "login@api.com",
            "password": "TestPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_login_wrong_password_fails(self):
        make_user(email="wrong@api.com", password="TestPass123!")
        response = self.client.post("/api/v1/auth/login/", {
            "email": "wrong@api.com",
            "password": "WrongPass!",
        })
        self.assertEqual(response.status_code, 401)

    def test_profile_requires_auth(self):
        response = self.client.get("/api/v1/auth/profile/")
        self.assertEqual(response.status_code, 401)

    def test_profile_returns_user_data(self):
        user = make_user(email="profile@api.com")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/auth/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "profile@api.com")
        self.assertIn("is_subscribed", response.data)

    def test_profile_patch_updates_name(self):
        user = make_user(email="patch@api.com")
        self.client.force_authenticate(user=user)
        response = self.client.patch("/api/v1/auth/profile/", {
            "first_name": "Updated",
            "last_name": "Name",
        })
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")

    def test_profile_patch_updates_language(self):
        user = make_user(email="lang@api.com")
        self.client.force_authenticate(user=user)
        self.client.patch("/api/v1/auth/profile/", {"preferred_language": "ne"})
        user.refresh_from_db()
        self.assertEqual(user.preferred_language, "ne")


class APIFeedTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.cat = make_category()
        self.preview = make_video(
            slug="api-preview", is_feed_preview=True, is_published=True, category=self.cat
        )
        self.full = make_video(
            slug="api-full", is_feed_preview=False, is_published=True, category=self.cat
        )

    def test_feed_accessible_without_auth(self):
        response = self.client.get("/api/v1/feed/")
        self.assertEqual(response.status_code, 200)

    def test_feed_returns_only_preview_videos(self):
        response = self.client.get("/api/v1/feed/")
        slugs = [v["slug"] for v in response.data["results"]]
        self.assertIn(self.preview.slug, slugs)
        self.assertNotIn(self.full.slug, slugs)

    def test_feed_filter_by_category(self):
        other_cat = make_category(name="Culture", slug="api-culture")
        other = make_video(
            slug="api-culture-vid", is_feed_preview=True,
            is_published=True, category=other_cat
        )
        response = self.client.get(f"/api/v1/feed/?category={other_cat.slug}")
        slugs = [v["slug"] for v in response.data["results"]]
        self.assertIn(other.slug, slugs)
        self.assertNotIn(self.preview.slug, slugs)

    def test_feed_is_paginated(self):
        response = self.client.get("/api/v1/feed/")
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)


class APIVideoLibraryTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email="libuser@api.com")
        self.subscriber = make_user(email="libsub@api.com")
        make_subscription(self.subscriber, status="active", days=30)
        make_video(slug="lib-video", is_feed_preview=False, is_published=True)

    def test_library_requires_auth(self):
        response = self.client.get("/api/v1/videos/")
        self.assertEqual(response.status_code, 401)

    def test_library_requires_subscription(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/videos/")
        self.assertEqual(response.status_code, 403)

    def test_library_accessible_to_subscriber(self):
        self.client.force_authenticate(user=self.subscriber)
        response = self.client.get("/api/v1/videos/")
        self.assertEqual(response.status_code, 200)


class APIVideoDetailTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.preview = make_video(
            slug="api-det-preview", is_feed_preview=True, is_published=True
        )
        self.full = make_video(
            slug="api-det-full", is_feed_preview=False, is_published=True
        )
        self.subscriber = make_user(email="detailsub@api.com")
        make_subscription(self.subscriber, status="active", days=30)

    def test_preview_video_accessible_without_auth(self):
        response = self.client.get(f"/api/v1/videos/{self.preview.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_full_video_returns_401_for_anonymous(self):
        response = self.client.get(f"/api/v1/videos/{self.full.slug}/")
        self.assertEqual(response.status_code, 401)
        self.assertIn("subscribe_url", response.data)

    def test_full_video_returns_403_for_non_subscriber(self):
        user = make_user(email="nosubdet@api.com")
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/api/v1/videos/{self.full.slug}/")
        self.assertEqual(response.status_code, 403)

    def test_full_video_accessible_to_subscriber(self):
        self.client.force_authenticate(user=self.subscriber)
        response = self.client.get(f"/api/v1/videos/{self.full.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_video_detail_increments_view_count(self):
        before = self.preview.view_count
        self.client.get(f"/api/v1/videos/{self.preview.slug}/")
        self.preview.refresh_from_db()
        self.assertEqual(self.preview.view_count, before + 1)

    def test_progress_update_saves_watch_history(self):
        from apps.content.models import WatchHistory
        self.client.force_authenticate(user=self.subscriber)
        self.client.post(f"/api/v1/videos/{self.preview.slug}/progress/", {
            "progress": 120,
        })
        wh = WatchHistory.objects.filter(
            user=self.subscriber, video=self.preview
        ).first()
        self.assertIsNotNone(wh)
        self.assertEqual(wh.progress_seconds, 120)

    def test_progress_update_requires_auth(self):
        response = self.client.post(f"/api/v1/videos/{self.preview.slug}/progress/", {
            "progress": 60,
        })
        self.assertEqual(response.status_code, 401)


class APIDestinationsTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.dest = make_destination()
        self.subscriber = make_user(email="destsub@api.com")
        make_subscription(self.subscriber, status="active", days=30)

    def test_destinations_requires_subscription(self):
        response = self.client.get("/api/v1/destinations/")
        self.assertEqual(response.status_code, 401)

    def test_destinations_list_accessible_to_subscriber(self):
        self.client.force_authenticate(user=self.subscriber)
        response = self.client.get("/api/v1/destinations/")
        self.assertEqual(response.status_code, 200)
        slugs = [d["slug"] for d in response.data["results"]]
        self.assertIn(self.dest.slug, slugs)

    def test_destination_detail_accessible_to_subscriber(self):
        self.client.force_authenticate(user=self.subscriber)
        response = self.client.get(f"/api/v1/destinations/{self.dest.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.dest.name)

    def test_destination_detail_includes_weather_key(self):
        self.client.force_authenticate(user=self.subscriber)
        response = self.client.get(f"/api/v1/destinations/{self.dest.slug}/")
        self.assertIn("weather", response.data)


class APIPlansTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.monthly = make_plan()
        from tests.factories import make_yearly_plan
        self.yearly = make_yearly_plan()

    def test_plans_accessible_without_auth(self):
        response = self.client.get("/api/v1/plans/")
        self.assertEqual(response.status_code, 200)

    def test_plans_shows_monthly_price_2000(self):
        response = self.client.get("/api/v1/plans/")
        prices = [p["price_npr"] for p in response.data["results"]]
        self.assertIn("2000.00", prices)

    def test_plans_shows_yearly_price_20000(self):
        response = self.client.get("/api/v1/plans/")
        prices = [p["price_npr"] for p in response.data["results"]]
        self.assertIn("20000.00", prices)


class APISubscriptionStatusTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_subscription_status_requires_auth(self):
        response = self.client.get("/api/v1/subscription/")
        self.assertEqual(response.status_code, 401)

    def test_subscription_status_not_subscribed(self):
        user = make_user(email="nostatus@api.com")
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/subscription/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_subscribed"])
        self.assertIsNone(response.data["subscription"])

    def test_subscription_status_subscribed(self):
        user = make_user(email="yesstatus@api.com")
        make_subscription(user, status="active", days=30)
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/v1/subscription/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_subscribed"])
        self.assertIsNotNone(response.data["subscription"])
        self.assertEqual(
            response.data["subscription"]["plan"]["price_npr"],
            "2000.00"
        )


class APIWatchHistoryTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(email="hist@api.com")
        self.video = make_video(slug="hist-video", is_published=True)

    def test_history_requires_auth(self):
        response = self.client.get("/api/v1/history/")
        self.assertEqual(response.status_code, 401)

    def test_history_returns_watched_videos(self):
        from apps.content.models import WatchHistory
        WatchHistory.objects.create(
            user=self.user,
            video=self.video,
            progress_seconds=100,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/history/")
        self.assertEqual(response.status_code, 200)
        slugs = [v["slug"] for v in response.data["results"]]
        self.assertIn(self.video.slug, slugs)
