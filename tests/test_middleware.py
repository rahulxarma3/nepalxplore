"""
tests/test_middleware.py

Tests for SubscriptionMiddleware — verifies the paywall works correctly
for all path combinations and user states.
"""
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage

from apps.subscriptions.middleware import SubscriptionMiddleware
from tests.factories import make_user, make_subscription


def get_response_ok(request):
    """Dummy get_response that always returns 200."""
    from django.http import HttpResponse
    return HttpResponse("OK", status=200)


def make_request(path, user=None):
    """Build a fake request with messages support."""
    factory = RequestFactory()
    request = factory.get(path)
    request.user = user or AnonymousUser()
    # Attach message storage so middleware can call messages.info()
    setattr(request, "session", {})
    messages = FallbackStorage(request)
    setattr(request, "_messages", messages)
    return request


class SubscriptionMiddlewareTest(TestCase):

    def setUp(self):
        self.middleware = SubscriptionMiddleware(get_response_ok)
        self.user = make_user()
        self.subscriber = make_user(email="sub@test.com")
        make_subscription(self.subscriber, status="active", days=30)

    # ── Public paths — must always pass through ────────────────────────────────

    def test_home_passes_anonymous(self):
        request = make_request("/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_feed_passes_anonymous(self):
        request = make_request("/feed/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_subscribe_page_passes_anonymous(self):
        request = make_request("/subscribe/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_accounts_login_passes_anonymous(self):
        request = make_request("/accounts/login/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_admin_passes_anonymous(self):
        request = make_request("/admin/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_static_passes_anonymous(self):
        request = make_request("/static/css/main.css", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    # ── Premium paths — anonymous redirected to login ──────────────────────────

    def test_destinations_redirects_anonymous(self):
        request = make_request("/destinations/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_destinations_includes_next_param(self):
        request = make_request("/destinations/kathmandu/", AnonymousUser())
        response = self.middleware(request)
        self.assertIn("next=/destinations/kathmandu/", response["Location"])

    def test_destinations_trekking_redirects_anonymous(self):
        request = make_request("/destinations/trekking/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)

    def test_destinations_hotels_redirects_anonymous(self):
        request = make_request("/destinations/hotels/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)

    def test_destinations_culture_redirects_anonymous(self):
        request = make_request("/destinations/culture/", AnonymousUser())
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)

    # ── Premium paths — logged in but no subscription ──────────────────────────

    def test_destinations_redirects_non_subscriber_to_plans(self):
        request = make_request("/destinations/", self.user)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/subscribe/", response["Location"])

    # ── Premium paths — active subscriber passes through ──────────────────────

    def test_destinations_passes_subscriber(self):
        request = make_request("/destinations/", self.subscriber)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_destinations_detail_passes_subscriber(self):
        request = make_request("/destinations/kathmandu/", self.subscriber)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_destinations_trekking_passes_subscriber(self):
        request = make_request("/destinations/trekking/", self.subscriber)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    # ── Expired subscription ───────────────────────────────────────────────────

    def test_destinations_redirects_expired_subscriber(self):
        expired_user = make_user(email="expired@test.com")
        make_subscription(expired_user, status="expired", days=-1)
        request = make_request("/destinations/", expired_user)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/subscribe/", response["Location"])
