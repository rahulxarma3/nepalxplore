"""
python manage.py check_production

Validates that every required environment variable and config is set correctly
before going live. Run this from Railway console after first deploy.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Check production readiness — validates all config before go-live"

    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  NepaXplore — Production Readiness Check")
        self.stdout.write("=" * 60 + "\n")

        checks = []

        def ok(label):
            checks.append(("✅", label))
            self.stdout.write(self.style.SUCCESS(f"  ✅  {label}"))

        def fail(label, hint=""):
            checks.append(("❌", label))
            msg = f"  ❌  {label}"
            if hint:
                msg += f"\n       → {hint}"
            self.stdout.write(self.style.ERROR(msg))

        def warn(label, hint=""):
            checks.append(("⚠️", label))
            msg = f"  ⚠️   {label}"
            if hint:
                msg += f"\n       → {hint}"
            self.stdout.write(self.style.WARNING(msg))

        self.stdout.write("\n── Core ──────────────────────────────────────────────")

        # DEBUG must be False
        if settings.DEBUG:
            fail("DEBUG is True", "Set DEBUG=False in Railway environment variables")
        else:
            ok("DEBUG=False")

        # Secret key must not be the dev default
        if "dev-secret-key" in settings.SECRET_KEY or len(settings.SECRET_KEY) < 40:
            fail("SECRET_KEY is weak or default",
                 "Generate: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"")
        else:
            ok("SECRET_KEY is strong")

        # ALLOWED_HOSTS must have real domain
        if "localhost" in settings.ALLOWED_HOSTS and len(settings.ALLOWED_HOSTS) == 1:
            fail("ALLOWED_HOSTS only has localhost",
                 "Add your Railway domain: ALLOWED_HOSTS=yourapp.up.railway.app")
        else:
            ok(f"ALLOWED_HOSTS: {', '.join(settings.ALLOWED_HOSTS)}")

        # CSRF trusted origins
        if not getattr(settings, "CSRF_TRUSTED_ORIGINS", []):
            fail("CSRF_TRUSTED_ORIGINS not set",
                 "Set: CSRF_TRUSTED_ORIGINS=https://yourapp.up.railway.app")
        elif "http://localhost" in str(settings.CSRF_TRUSTED_ORIGINS) and len(settings.CSRF_TRUSTED_ORIGINS) == 1:
            fail("CSRF_TRUSTED_ORIGINS only has localhost",
                 "Add: CSRF_TRUSTED_ORIGINS=https://yourapp.up.railway.app")
        else:
            ok(f"CSRF_TRUSTED_ORIGINS set")

        self.stdout.write("\n── Database ──────────────────────────────────────────")

        db = settings.DATABASES["default"]
        if "sqlite" in db.get("ENGINE", ""):
            fail("Using SQLite in production", "Use PostgreSQL — add Railway PostgreSQL service")
        else:
            ok(f"PostgreSQL configured")

        self.stdout.write("\n── Cache ─────────────────────────────────────────────")

        cache = settings.CACHES["default"]
        if "LocMem" in cache.get("BACKEND", "") or "locmem" in cache.get("BACKEND", ""):
            warn("Using LocMemCache", "Add Railway Redis service for production caching")
        else:
            ok("Redis cache configured")

        self.stdout.write("\n── Storage ───────────────────────────────────────────")

        if os.environ.get("USE_R2_STORAGE") != "True":
            fail("USE_R2_STORAGE not enabled",
                 "Set USE_R2_STORAGE=True and fill in CF_R2_* variables")
        else:
            ok("Cloudflare R2 storage enabled")

        for key in ["CF_R2_ACCESS_KEY_ID", "CF_R2_SECRET_ACCESS_KEY", "CF_R2_BUCKET_NAME",
                    "CF_R2_ENDPOINT_URL", "CF_R2_PUBLIC_DOMAIN"]:
            val = os.environ.get(key, "")
            if not val or val == "dummy":
                fail(f"{key} not set")
            else:
                ok(f"{key} set")

        self.stdout.write("\n── Authentication ────────────────────────────────────")

        google_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        if not google_id or "dummy" in google_id:
            warn("Google OAuth not configured", "Set GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET")
        else:
            ok("Google OAuth credentials set")

        # Check Social App in database
        try:
            from allauth.socialaccount.models import SocialApp
            if SocialApp.objects.filter(provider="google").exists():
                ok("Google SocialApp configured in database")
            else:
                fail("No Google SocialApp in database",
                     "Go to /admin/socialaccount/socialapp/add/ and add Google OAuth app")
        except Exception:
            warn("Could not check SocialApp (run after migrate)")

        self.stdout.write("\n── Payments ──────────────────────────────────────────")

        for key, label in [
            ("STRIPE_PUBLIC_KEY", "Stripe public key"),
            ("STRIPE_SECRET_KEY", "Stripe secret key"),
            ("STRIPE_WEBHOOK_SECRET", "Stripe webhook secret"),
        ]:
            val = os.environ.get(key, "")
            if not val or "dummy" in val or "test" in val.lower():
                warn(f"{label} is test/dummy", f"Set live key: {key}")
            else:
                ok(f"{label} set (live)")

        for key, label in [
            ("ESEWA_MERCHANT_CODE", "eSewa merchant code"),
            ("ESEWA_SECRET_KEY", "eSewa secret key"),
            ("KHALTI_SECRET_KEY", "Khalti secret key"),
        ]:
            val = os.environ.get(key, "")
            if not val or val in ("EPAYTEST", "8gBm/:&EnhH.1/q", "test_secret_key_dummy"):
                warn(f"{label} is sandbox value", f"Replace with live credentials: {key}")
            else:
                ok(f"{label} set (live)")

        # Check plans have Stripe price IDs
        try:
            from apps.subscriptions.models import Plan
            plans_without_stripe = Plan.objects.filter(stripe_price_id="", is_active=True)
            if plans_without_stripe.exists():
                names = ", ".join(plans_without_stripe.values_list("name", flat=True))
                warn(f"Plans missing Stripe price_id: {names}",
                     "Set via /admin/subscriptions/plan/ after creating Stripe products")
            else:
                ok("All plans have Stripe price IDs")
        except Exception:
            warn("Could not check plans (run after migrate)")

        self.stdout.write("\n── Weather & Email ───────────────────────────────────")

        weather_key = os.environ.get("OPENWEATHER_API_KEY", "")
        if not weather_key or weather_key == "your-openweather-api-key":
            fail("OPENWEATHER_API_KEY not set", "Register free at openweathermap.org/api")
        else:
            ok("OpenWeatherMap API key set")

        email_user = os.environ.get("EMAIL_HOST_USER", "")
        if not email_user:
            warn("EMAIL_HOST_USER not set", "Set for account verification emails")
        else:
            ok(f"Email configured: {email_user}")

        self.stdout.write("\n── Site config ───────────────────────────────────────")

        try:
            from django.contrib.sites.models import Site
            site = Site.objects.get(id=1)
            if site.domain in ("example.com", "localhost:8000"):
                fail(f"Site domain is still default: {site.domain}",
                     "Run: python manage.py setup_oauth --domain yourapp.up.railway.app")
            else:
                ok(f"Site domain: {site.domain}")
        except Exception:
            warn("Could not check Site (run after migrate)")

        self.stdout.write("\n── Content ───────────────────────────────────────────")

        try:
            from apps.content.models import Video
            from apps.destinations.models import Destination
            video_count = Video.objects.filter(is_published=True).count()
            dest_count = Destination.objects.count()
            preview_count = Video.objects.filter(is_published=True, is_feed_preview=True).count()

            if video_count == 0:
                warn("No published videos", "Upload videos via /feed/upload/")
            else:
                ok(f"{video_count} published videos")

            if preview_count == 0:
                warn("No feed preview videos", "Mark at least 2-3 videos as feed preview")
            else:
                ok(f"{preview_count} free feed preview videos")

            if dest_count == 0:
                warn("No destinations", "Add destinations via /admin/destinations/destination/")
            else:
                ok(f"{dest_count} destinations configured")
        except Exception:
            warn("Could not check content (run after migrate)")

        # Summary
        passed = sum(1 for s, _ in checks if s == "✅")
        failed = sum(1 for s, _ in checks if s == "❌")
        warned = sum(1 for s, _ in checks if s == "⚠️")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"  Results: {passed} passed, {warned} warnings, {failed} failed")
        self.stdout.write("=" * 60)

        if failed == 0 and warned == 0:
            self.stdout.write(self.style.SUCCESS("\n  🚀 ALL CHECKS PASSED — ready to go live!\n"))
        elif failed == 0:
            self.stdout.write(self.style.WARNING(f"\n  ⚠️  {warned} warning(s) — review before launch\n"))
        else:
            self.stdout.write(self.style.ERROR(f"\n  ❌ {failed} critical issue(s) must be fixed before launch\n"))
