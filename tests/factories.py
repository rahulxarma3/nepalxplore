"""
tests/factories.py

Helper functions to create test objects.
Used by all test files — keeps tests DRY and readable.
"""
from django.utils import timezone
from datetime import timedelta


def make_user(email="user@test.com", password="TestPass123!", subscribed=False, **kwargs):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password=password,
        **kwargs,
    )
    if subscribed:
        make_subscription(user)
    return user


def make_staff_user(email="staff@test.com", password="TestPass123!"):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="staff",
        email=email,
        password=password,
        is_staff=True,
    )


def make_plan(name="Monthly", slug="monthly", price_npr=2000, interval="monthly"):
    from apps.subscriptions.models import Plan
    plan, _ = Plan.objects.get_or_create(
        slug=slug,
        defaults={
            "name": name,
            "price_npr": price_npr,
            "price_usd": 15.00,
            "interval": interval,
            "is_active": True,
            "features": ["Full access", "HD video"],
        }
    )
    return plan


def make_yearly_plan():
    return make_plan(
        name="Yearly", slug="yearly",
        price_npr=20000, interval="yearly"
    )


def make_subscription(user, gateway="stripe", status="active", days=30):
    from apps.subscriptions.models import Subscription
    plan = make_plan()
    sub, _ = Subscription.objects.update_or_create(
        user=user,
        defaults={
            "plan": plan,
            "gateway": gateway,
            "status": status,
            "end_date": timezone.now() + timedelta(days=days),
            "gateway_subscription_id": f"test_sub_{user.pk}",
        }
    )
    return sub


def make_expired_subscription(user):
    return make_subscription(user, status="expired", days=-1)


def make_category(name="Trekking", slug="trekking"):
    from apps.content.models import Category
    cat, _ = Category.objects.get_or_create(
        slug=slug,
        defaults={"name": name, "icon": "🏔️", "order": 1}
    )
    return cat


def make_video(title="Test Video", slug="test-video", is_feed_preview=False,
               is_published=True, category=None, **kwargs):
    from apps.content.models import Video
    from django.utils import timezone
    if category is None:
        category = make_category()
    video, _ = Video.objects.get_or_create(
        slug=slug,
        defaults={
            "title": title,
            "description": "A test video about Nepal.",
            "category": category,
            "duration_seconds": 300,
            "location": "Kathmandu",
            "language": "en",
            "is_feed_preview": is_feed_preview,
            "is_published": is_published,
            "published_at": timezone.now() if is_published else None,
            **kwargs,
        }
    )
    return video


def make_destination(name="Kathmandu", slug="kathmandu"):
    from apps.destinations.models import Destination
    dest, _ = Destination.objects.get_or_create(
        slug=slug,
        defaults={
            "name": name,
            "region": "Bagmati Province",
            "description": "Capital of Nepal.",
            "latitude": 27.7172,
            "longitude": 85.3240,
            "altitude_m": 1400,
            "is_featured": True,
        }
    )
    return dest
