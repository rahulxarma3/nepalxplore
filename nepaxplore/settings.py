"""
NepaXplore — Django settings
"""
from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# Trusted origins for CSRF (required for Railway HTTPS + Stripe webhooks)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000",
    cast=Csv(),
)

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "storages",
    "django_htmx",

    # REST API (for future mobile app)
    "rest_framework",
    "rest_framework_simplejwt",

    "apps.accounts",
    "apps.content",
    "apps.subscriptions",
    "apps.destinations",
    "apps.core",
    "apps.bookings",
]

SITE_ID = 1

# ── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    # Custom: blocks unsubscribed users from premium content
    "apps.subscriptions.middleware.SubscriptionMiddleware",
]

ROOT_URLCONF = "nepaxplore.urls"

# ── Templates ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.subscriptions.context_processors.subscription_status",
                "apps.core.context_processors.unread_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "nepaxplore.wsgi.application"

# ── Database (Railway PostgreSQL) ─────────────────────────────────────────────
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        conn_max_age=600,
    )
}

# ── Cache (Railway Redis) ──────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# django-allauth config
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_ADAPTER = "apps.accounts.adapter.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapter.SocialAccountAdapter"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID"),
            "secret": config("GOOGLE_CLIENT_SECRET"),
        },
    }
}

# ── Static & Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Cloudflare R2 for media (videos, thumbnails)
# R2 storage — only enabled when USE_R2_STORAGE=True (set in Railway env)
import os as _os
if _os.environ.get("USE_R2_STORAGE") == "True":
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_ROOT = BASE_DIR / "media"
AWS_ACCESS_KEY_ID = config("CF_R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config("CF_R2_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("CF_R2_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = config("CF_R2_ENDPOINT_URL")  # https://<accountid>.r2.cloudflarestorage.com
AWS_S3_CUSTOM_DOMAIN = config("CF_R2_PUBLIC_DOMAIN", default=None)  # your public R2 domain
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/" if config("CF_R2_PUBLIC_DOMAIN", default=None) else "/media/"

# ── Payments ──────────────────────────────────────────────────────────────────
STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET")

ESEWA_MERCHANT_CODE = config("ESEWA_MERCHANT_CODE")
ESEWA_SECRET_KEY = config("ESEWA_SECRET_KEY")
ESEWA_BASE_URL = "https://rc-epay.esewa.com.np"  # switch to prod URL on go-live

KHALTI_SECRET_KEY = config("KHALTI_SECRET_KEY")
KHALTI_BASE_URL = "https://a.khalti.com/api/v2"

# ── Weather ───────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY = config("OPENWEATHER_API_KEY")
WEATHER_CACHE_SECONDS = 1800  # 30 min

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = "NepaXplore <noreply@nepaxplore.com>"

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Security (production) ─────────────────────────────────────────────────────
if not DEBUG:
    # HTTPS enforcement
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Railway proxy
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"

# Auto-load local overrides if present (never commit local_settings.py)
try:
    from .local_settings import *  # noqa: F401, F403
except ImportError:
    pass

# ── Django REST Framework (mobile API) ───────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
}

# ── Test configuration ────────────────────────────────────────────────────────
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Use faster password hasher in tests
if "test" in __import__("sys").argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    # Silence noisy logging during tests
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": True,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "root": {"handlers": ["null"]},
    }

if DEBUG:
    try:
        from .local_settings import *
    except ImportError:
        pass