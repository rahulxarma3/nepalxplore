"""
python manage.py seed_data

Creates initial subscription plans, categories, and a sample destination
so the app has something to show on first run.
"""
from django.core.management.base import BaseCommand
from apps.subscriptions.models import Plan
from apps.content.models import Category


class Command(BaseCommand):
    help = "Seed initial plans, categories"

    def handle(self, *args, **options):
        # ── Subscription plans ──────────────────────────────────────────────
        plans = [
            {
                "name": "Monthly",
                "slug": "monthly",
                "description": "Full access, billed monthly.",
                "price_npr": 2000,
                "price_usd": 15.00,
                "interval": "monthly",
                "features": [
                    "All destinations unlocked",
                    "HD video streaming",
                    "Live weather for every destination",
                    "Trekking route guides",
                    "Cultural & food guides",
                    "New videos every week",
                ],
            },
            {
                "name": "Yearly",
                "slug": "yearly",
                "description": "Best value — save 17%.",
                "price_npr": 20000,
                "price_usd": 149.00,
                "interval": "yearly",
                "features": [
                    "Everything in Monthly",
                    "Save NPR 4,000 vs monthly",
                    "Priority access to new content",
                    "Download watchlist (coming soon)",
                ],
            },
        ]

        for p in plans:
            obj, created = Plan.objects.get_or_create(slug=p["slug"], defaults=p)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created plan: {obj.name}"))
            else:
                self.stdout.write(f"Plan already exists: {obj.name}")

        # ── Content categories ──────────────────────────────────────────────
        categories = [
            {"name": "Trekking", "slug": "trekking", "icon": "🏔️", "order": 1},
            {"name": "Culture", "slug": "culture", "icon": "🎭", "order": 2},
            {"name": "Food", "slug": "food", "icon": "🍜", "order": 3},
            {"name": "History", "slug": "history", "icon": "🏛️", "order": 4},
            {"name": "Wildlife", "slug": "wildlife", "icon": "🐘", "order": 5},
            {"name": "Festivals", "slug": "festivals", "icon": "🎉", "order": 6},
        ]

        for c in categories:
            obj, created = Category.objects.get_or_create(slug=c["slug"], defaults=c)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {obj.name}"))
            else:
                self.stdout.write(f"Category already exists: {obj.name}")

        self.stdout.write(self.style.SUCCESS("\n✅ Seed complete. Next steps:"))
        self.stdout.write("  1. Add destinations via Django admin (/admin/)")
        self.stdout.write("  2. Upload videos and mark some as is_feed_preview=True")
        self.stdout.write("  3. Set stripe_price_id on plans after creating Stripe products")
