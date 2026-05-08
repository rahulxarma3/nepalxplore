"""
NepaXplore — Django settings
"""
from pathlib import Path
from datetime import timedelta

from decouple import config, Csv
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent


# ── Security ─────────────────────────────────────────────────────────────────
SECRET_KEY = config(
    "SECRET_KEY",
    default="dev-secret-key-change-in-production"
)

if not SECRET_KEY:
    SECRET_KEY = "dev-secret-key-change-in-production"

SECRET_KEY = config("SECRET_KEY", default="build-unsafe-secret") or "build-unsafe-secret"
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="*",
    cast=Csv()
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,https://web-production-653c8e.up.railway.app",
    cast=Csv()
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

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "storages",
    "django_htmx",

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


# ── Middleware ────────────────────────────────────────────────────────────────
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


# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default="sqlite:///db.sqlite3"),
        conn_max_age=600,
    )
}


# ── Cache / Redis ─────────────────────────────────────────────────────────────
REDIS_URL = config("REDIS_URL", default="")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "None"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_ADAPTER = "apps.accounts.adapter.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapter.SocialAccountAdapter"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": config("GOOGLE_CLIENT_ID", default="dummy"),
            "secret": config("GOOGLE_CLIENT_SECRET", default="dummy"),
            "key": "",
        },
    }
}


# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# ── Media / Cloudflare R2 ─────────────────────────────────────────────────────
USE_R2_STORAGE = config("USE_R2_STORAGE", default=False, cast=bool)

if USE_R2_STORAGE:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    AWS_ACCESS_KEY_ID = config("CF_R2_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = config("CF_R2_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = config("CF_R2_BUCKET_NAME", default="")
    AWS_S3_ENDPOINT_URL = config("CF_R2_ENDPOINT_URL", default="")
    AWS_S3_CUSTOM_DOMAIN = config("CF_R2_PUBLIC_DOMAIN", default="")

    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False

    MEDIA_URL = (
        f"https://{AWS_S3_CUSTOM_DOMAIN}/"
        if AWS_S3_CUSTOM_DOMAIN
        else "/media/"
    )
else:
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    MEDIA_ROOT = BASE_DIR / "media"
    MEDIA_URL = "/media/"


# ── Payments ──────────────────────────────────────────────────────────────────
STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY", default="dummy")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="dummy")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="dummy")

ESEWA_MERCHANT_CODE = config("ESEWA_MERCHANT_CODE", default="EPAYTEST")
ESEWA_SECRET_KEY = config("ESEWA_SECRET_KEY", default="dummy")
ESEWA_BASE_URL = "https://rc-epay.esewa.com.np"

KHALTI_SECRET_KEY = config("KHALTI_SECRET_KEY", default="dummy")
KHALTI_BASE_URL = "https://a.khalti.com/api/v2"


# ── Weather ───────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY = config("OPENWEATHER_API_KEY", default="dummy")
WEATHER_CACHE_SECONDS = 1800


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


# ── Security for production ───────────────────────────────────────────────────
if not DEBUG:

    SECURE_SSL_REDIRECT = False

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"


# ── Django REST Framework ─────────────────────────────────────────────────────
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

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
}


# ── Test configuration ────────────────────────────────────────────────────────
TEST_RUNNER = "django.test.runner.DiscoverRunner"

import sys

if "test" in sys.argv:
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": True,
        "handlers": {
            "null": {
                "class": "logging.NullHandler",
            }
        },
        "root": {
            "handlers": ["null"],
        },
    }


# ── Local settings override ───────────────────────────────────────────────────
try:
    from .local_settings import *  # noqa
except ImportError:
    pass