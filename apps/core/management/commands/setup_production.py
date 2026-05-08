"""
python manage.py setup_production

Step-by-step guide to wire Railway + Cloudflare R2 + all payment gateways.
Run after deploying to Railway.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Print full production setup guide for Railway + R2 + payments"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("""
╔══════════════════════════════════════════════════════════╗
║        NepaXplore — Production Setup Guide              ║
╚══════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — Railway: Deploy the app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Push your code to a GitHub repo (public or private)
2.  Go to https://railway.app and create a new project
3.  Choose "Deploy from GitHub repo" → select your repo
4.  Railway auto-detects railway.toml and starts building

Add services (from Railway dashboard → "Add Service"):
  • PostgreSQL   (Railway marketplace)
  • Redis        (Railway marketplace)

Railway will auto-set DATABASE_URL and REDIS_URL for you.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — Cloudflare R2: Video & image storage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Go to https://dash.cloudflare.com → R2 → Create bucket
    Bucket name: nepaxplore-media
    Location: Auto (or Asia Pacific)

2.  Enable public access on the bucket:
    R2 → nepaxplore-media → Settings → Public Access → Allow

3.  Create API token:
    R2 → Manage R2 API Tokens → Create API Token
    Permissions: Object Read & Write
    Copy: Access Key ID + Secret Access Key

4.  Set these Railway env vars:
    CF_R2_ACCESS_KEY_ID      = <your access key id>
    CF_R2_SECRET_ACCESS_KEY  = <your secret key>
    CF_R2_BUCKET_NAME        = nepaxplore-media
    CF_R2_ENDPOINT_URL       = https://<ACCOUNT_ID>.r2.cloudflarestorage.com
    CF_R2_PUBLIC_DOMAIN      = pub-<HASH>.r2.dev  (from bucket Public URL)
    USE_R2_STORAGE           = True

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — Google OAuth
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  https://console.cloud.google.com → new project "NepaXplore"
2.  APIs & Services → OAuth consent screen
    - User type: External
    - Authorized domain: yourdomain.railway.app
3.  Credentials → Create → OAuth 2.0 Client ID
    - Type: Web application
    - Redirect URI: https://yourdomain.railway.app/accounts/google/login/callback/
4.  Set Railway env vars:
    GOOGLE_CLIENT_ID     = <client id>
    GOOGLE_CLIENT_SECRET = <client secret>
5.  After deploy, run:
    python manage.py setup_oauth --domain yourdomain.railway.app
6.  Go to /admin/socialaccount/socialapp/add/
    Add Google app with client id + secret, assign to your site

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — Stripe (international cards)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  https://dashboard.stripe.com → Products → Add product
    - Monthly: NPR 2,000 / month
    - Yearly:  NPR 20,000 / year
2.  Copy each Price ID (price_xxx)
3.  Go to Django admin → Plans → set stripe_price_id on each plan
4.  Set Railway env vars:
    STRIPE_PUBLIC_KEY    = pk_live_xxx
    STRIPE_SECRET_KEY    = sk_live_xxx
    STRIPE_WEBHOOK_SECRET= whsec_xxx
5.  Add webhook in Stripe dashboard:
    URL: https://yourdomain.railway.app/subscribe/stripe/webhook/
    Event: customer.subscription.deleted

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — eSewa (Nepal local payments)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Apply for merchant account: https://merchant.esewa.com.np
2.  After approval, get your:
    - Merchant code (live)
    - Secret key (live)
3.  Set Railway env vars:
    ESEWA_MERCHANT_CODE = <your live merchant code>
    ESEWA_SECRET_KEY    = <your live secret key>
4.  Update ESEWA_BASE_URL in settings.py:
    Change: https://rc-epay.esewa.com.np
    To:     https://epay.esewa.com.np

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — Khalti (Nepal local payments)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Apply: https://khalti.com/api/merchant-dashboard
2.  Get live secret key
3.  Set Railway env var:
    KHALTI_SECRET_KEY = <live secret key>
4.  Update KHALTI_BASE_URL in settings.py:
    Change: https://a.khalti.com/api/v2
    To:     https://khalti.com/api/v2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — OpenWeatherMap (live weather)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Register free at https://openweathermap.org/api
2.  APIs → Current Weather Data → Subscribe (free tier: 60 calls/min)
3.  Copy API key from My API Keys
4.  Set Railway env var:
    OPENWEATHER_API_KEY = <your api key>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8 — Email (account verification)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use Gmail with App Password (free):
1.  Google Account → Security → 2-Step Verification → App passwords
2.  Generate password for "Mail" / "Other (NepaXplore)"
3.  Set Railway env vars:
    EMAIL_HOST_USER     = youremail@gmail.com
    EMAIL_HOST_PASSWORD = <16-char app password>

Or use SendGrid / Resend for production volume:
    EMAIL_HOST          = smtp.sendgrid.net
    EMAIL_HOST_USER     = apikey
    EMAIL_HOST_PASSWORD = <sendgrid api key>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 9 — First content setup (after deploy)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python manage.py seed_data          # creates plans + categories
python manage.py createsuperuser    # admin user
python manage.py setup_oauth --domain yourdomain.railway.app

Then in Django admin:
  1. Add Destinations (Kathmandu, Pokhara, Lumbini, Everest Base Camp)
  2. Upload Videos via /feed/upload/ — mark 2-3 as Feed Preview
  3. Set latitude/longitude on destinations for live weather
  4. Set stripe_price_id on both plans

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULL RAILWAY ENV VARS CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECRET_KEY              ✓ generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG                   = False
ALLOWED_HOSTS           = yourdomain.railway.app
DATABASE_URL            ✓ auto-set by Railway PostgreSQL
REDIS_URL               ✓ auto-set by Railway Redis
GOOGLE_CLIENT_ID        ✓ step 3
GOOGLE_CLIENT_SECRET    ✓ step 3
CF_R2_ACCESS_KEY_ID     ✓ step 2
CF_R2_SECRET_ACCESS_KEY ✓ step 2
CF_R2_BUCKET_NAME       = nepaxplore-media
CF_R2_ENDPOINT_URL      ✓ step 2
CF_R2_PUBLIC_DOMAIN     ✓ step 2
USE_R2_STORAGE          = True
STRIPE_PUBLIC_KEY       ✓ step 4
STRIPE_SECRET_KEY       ✓ step 4
STRIPE_WEBHOOK_SECRET   ✓ step 4
ESEWA_MERCHANT_CODE     ✓ step 5
ESEWA_SECRET_KEY        ✓ step 5
KHALTI_SECRET_KEY       ✓ step 6
OPENWEATHER_API_KEY     ✓ step 7
EMAIL_HOST_USER         ✓ step 8
EMAIL_HOST_PASSWORD     ✓ step 8
"""))
