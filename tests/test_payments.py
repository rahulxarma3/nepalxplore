"""
tests/test_payments.py

Tests for subscription and payment flows:
- Plan access
- Stripe success callback
- Subscription cancellation
- Sandbox payment simulation
- Payment transaction recording
"""
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from tests.factories import make_user, make_plan, make_subscription, make_yearly_plan


class StripeSuccessViewTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.plan = make_plan()
        self.client.force_login(self.user)

    @patch("apps.subscriptions.views.stripe.checkout.Session.retrieve")
    def test_stripe_success_activates_subscription(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(
            metadata={"plan_slug": "monthly"},
            subscription="sub_stripe_test_123",
            payment_intent="pi_test_123",
        )
        response = self.client.get(
            "/subscribe/stripe/success/?session_id=cs_test_123"
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_subscribed)

    @patch("apps.subscriptions.views.stripe.checkout.Session.retrieve")
    def test_stripe_success_creates_transaction(self, mock_retrieve):
        from apps.subscriptions.models import PaymentTransaction
        mock_retrieve.return_value = MagicMock(
            metadata={"plan_slug": "monthly"},
            subscription="sub_stripe_txn_test",
            payment_intent="pi_txn_test",
        )
        self.client.get("/subscribe/stripe/success/?session_id=cs_txn_test")
        self.assertTrue(
            PaymentTransaction.objects.filter(
                user=self.user,
                gateway="stripe",
                status="success",
            ).exists()
        )

    @patch("apps.subscriptions.views.stripe.checkout.Session.retrieve")
    def test_stripe_success_sends_sub_activated_notification(self, mock_retrieve):
        from apps.core.models import Notification
        mock_retrieve.return_value = MagicMock(
            metadata={"plan_slug": "monthly"},
            subscription="sub_notif_test",
            payment_intent=None,
        )
        self.client.get("/subscribe/stripe/success/?session_id=cs_notif_test")
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                notification_type="sub_activated",
            ).exists()
        )

    def test_stripe_success_without_session_id_redirects(self):
        response = self.client.get("/subscribe/stripe/success/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/subscribe/", response["Location"])


class CancelSubscriptionTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.sub = make_subscription(self.user, gateway="esewa", status="active", days=30)
        self.client.force_login(self.user)

    def test_cancel_requires_post(self):
        response = self.client.get("/subscribe/cancel/")
        self.assertEqual(response.status_code, 302)

    def test_cancel_turns_off_auto_renew(self):
        response = self.client.post("/subscribe/cancel/")
        self.assertEqual(response.status_code, 302)
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.auto_renew)

    def test_cancel_does_not_deactivate_immediately(self):
        self.client.post("/subscribe/cancel/")
        self.sub.refresh_from_db()
        # Status still active — access until end_date
        self.assertEqual(self.sub.status, "active")
        self.assertTrue(self.sub.is_active)

    def test_cancel_redirects_to_profile(self):
        response = self.client.post("/subscribe/cancel/")
        self.assertRedirects(response, "/accounts/profile/")

    def test_cancel_without_subscription_shows_error(self):
        user_no_sub = make_user(email="nosub@cancel.com")
        self.client.force_login(user_no_sub)
        response = self.client.post("/subscribe/cancel/")
        self.assertEqual(response.status_code, 302)

    @patch("apps.subscriptions.views.stripe.Subscription.modify")
    def test_cancel_stripe_subscription_calls_stripe_api(self, mock_modify):
        stripe_user = make_user(email="stripe@cancel.com")
        sub = make_subscription(stripe_user, gateway="stripe", status="active", days=30)
        sub.gateway_subscription_id = "sub_stripe_real"
        sub.save()
        self.client.force_login(stripe_user)
        self.client.post("/subscribe/cancel/")
        mock_modify.assert_called_once_with(
            "sub_stripe_real",
            cancel_at_period_end=True,
        )


class SandboxPaymentTest(TestCase):

    def setUp(self):
        self.user = make_user()
        self.plan = make_plan()
        self.client.force_login(self.user)

    def test_sandbox_picker_accessible_in_debug(self):
        with self.settings(DEBUG=True):
            response = self.client.get("/subscribe/sandbox/")
            self.assertEqual(response.status_code, 200)

    def test_sandbox_pay_success_activates_subscription(self):
        with self.settings(DEBUG=True):
            response = self.client.post(
                f"/subscribe/sandbox/pay/monthly/khalti/",
                {"action": "success"},
            )
            self.assertEqual(response.status_code, 302)
            self.user.refresh_from_db()
            self.assertTrue(self.user.is_subscribed)

    def test_sandbox_pay_success_records_transaction(self):
        from apps.subscriptions.models import PaymentTransaction
        with self.settings(DEBUG=True):
            self.client.post(
                f"/subscribe/sandbox/pay/monthly/esewa/",
                {"action": "success"},
            )
            self.assertTrue(
                PaymentTransaction.objects.filter(
                    user=self.user,
                    gateway="esewa",
                    status="success",
                ).exists()
            )

    def test_sandbox_pay_failure_records_failed_transaction(self):
        from apps.subscriptions.models import PaymentTransaction
        with self.settings(DEBUG=True):
            self.client.post(
                f"/subscribe/sandbox/pay/monthly/stripe/",
                {"action": "fail"},
            )
            self.assertTrue(
                PaymentTransaction.objects.filter(
                    user=self.user,
                    gateway="stripe",
                    status="failed",
                ).exists()
            )
            # No subscription created
            self.assertFalse(self.user.is_subscribed)

    def test_sandbox_reset_removes_subscription(self):
        make_subscription(self.user, status="active", days=30)
        with self.settings(DEBUG=True):
            self.client.post("/subscribe/sandbox/reset/")
            self.user.refresh_from_db()
            self.assertFalse(self.user.is_subscribed)

    def test_sandbox_requires_login(self):
        self.client.logout()
        with self.settings(DEBUG=True):
            response = self.client.get("/subscribe/sandbox/")
            self.assertEqual(response.status_code, 302)


class PaymentTransactionTest(TestCase):

    def test_transaction_str_shows_gateway_and_amount(self):
        from apps.subscriptions.models import PaymentTransaction
        user = make_user()
        txn = PaymentTransaction.objects.create(
            user=user,
            gateway="khalti",
            amount_npr=2000,
            status="success",
            raw_response={},
        )
        self.assertIn("khalti", str(txn))
        self.assertIn("2000", str(txn))

    def test_transaction_default_status_is_initiated(self):
        from apps.subscriptions.models import PaymentTransaction
        user = make_user()
        txn = PaymentTransaction(
            user=user,
            gateway="esewa",
            amount_npr=2000,
            raw_response={},
        )
        self.assertEqual(txn.status, "initiated")
