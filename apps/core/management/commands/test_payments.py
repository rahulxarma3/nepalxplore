"""
Payment sandbox testing harness.

Provides:
  1. A management command: python manage.py test_payments
  2. Sandbox test views (DEBUG only) at /subscribe/sandbox/

DO NOT deploy sandbox views to production — they are gated behind DEBUG=True.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = "Test payment flows and create sandbox subscriptions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="",
            help="User email to test with (creates if not exists)",
        )
        parser.add_argument(
            "--plan",
            type=str,
            default="monthly",
            choices=["monthly", "yearly"],
            help="Plan to subscribe to",
        )
        parser.add_argument(
            "--gateway",
            type=str,
            default="stripe",
            choices=["stripe", "esewa", "khalti"],
            help="Payment gateway to simulate",
        )
        parser.add_argument(
            "--expire",
            action="store_true",
            help="Set subscription to expire in 2 minutes (test expire_subscriptions command)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove subscription from user",
        )

    def handle(self, *args, **options):
        from apps.subscriptions.models import Plan, Subscription, PaymentTransaction

        email = options["email"] or "testuser@nepaxplore.com"
        plan_slug = options["plan"]
        gateway = options["gateway"]

        # Get or create test user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email.split("@")[0],
                "first_name": "Test",
                "last_name": "User",
            }
        )
        if created:
            user.set_password("TestPass123!")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user: {email} / TestPass123!"))
        else:
            self.stdout.write(f"Using existing user: {email}")

        # Reset if requested
        if options["reset"]:
            Subscription.objects.filter(user=user).delete()
            PaymentTransaction.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING(f"Subscription removed for {email}"))
            return

        # Get plan
        try:
            plan = Plan.objects.get(slug=plan_slug)
        except Plan.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f"Plan '{plan_slug}' not found. Run: python manage.py seed_data"
            ))
            return

        # Create or update subscription
        end_date = (
            timezone.now() + timedelta(minutes=2)
            if options["expire"]
            else timezone.now() + timedelta(days=30 if plan_slug == "monthly" else 365)
        )

        sub, created = Subscription.objects.update_or_create(
            user=user,
            defaults={
                "plan": plan,
                "gateway": gateway,
                "status": "active",
                "gateway_subscription_id": f"sandbox_{gateway}_{user.pk}",
                "end_date": end_date,
                "auto_renew": not options["expire"],
            }
        )

        # Create transaction record
        PaymentTransaction.objects.create(
            user=user,
            subscription=sub,
            gateway=gateway,
            gateway_transaction_id=f"sandbox_txn_{user.pk}_{timezone.now().timestamp():.0f}",
            amount_npr=plan.price_npr,
            status="success",
            raw_response={"source": "sandbox", "test": True},
        )

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ {action} sandbox subscription:\n"
            f"   User:     {email}\n"
            f"   Plan:     {plan.name} (NPR {plan.price_npr})\n"
            f"   Gateway:  {gateway}\n"
            f"   Status:   active\n"
            f"   Expires:  {end_date.strftime('%Y-%m-%d %H:%M')}\n"
            f"   {'⚠️  Expires in 2 min — run expire_subscriptions to test' if options['expire'] else ''}"
        ))

        self.stdout.write("\nTo log in as this user:")
        self.stdout.write(f"  Email:    {email}")
        self.stdout.write(f"  Password: TestPass123!")
        self.stdout.write(f"\nAdmin URL: /admin/subscriptions/subscription/\n")
