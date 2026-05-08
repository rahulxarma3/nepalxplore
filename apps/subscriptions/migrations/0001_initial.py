from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Plan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                ("price_npr", models.DecimalField(decimal_places=2, max_digits=8)),
                ("price_usd", models.DecimalField(decimal_places=2, max_digits=8)),
                ("interval", models.CharField(
                    choices=[("monthly", "Monthly"), ("yearly", "Yearly")], max_length=10,
                )),
                ("stripe_price_id", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("features", models.JSONField(default=list)),
            ],
            options={"ordering": ["price_npr"]},
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="subscription", to=settings.AUTH_USER_MODEL,
                )),
                ("plan", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, to="subscriptions.plan",
                )),
                ("gateway", models.CharField(
                    choices=[("stripe", "Stripe"), ("esewa", "eSewa"), ("khalti", "Khalti")],
                    max_length=10,
                )),
                ("gateway_subscription_id", models.CharField(blank=True, max_length=200)),
                ("gateway_customer_id", models.CharField(blank=True, max_length=200)),
                ("status", models.CharField(
                    choices=[
                        ("active", "Active"), ("expired", "Expired"),
                        ("cancelled", "Cancelled"), ("pending", "Pending"),
                    ],
                    default="pending", max_length=12,
                )),
                ("start_date", models.DateTimeField(auto_now_add=True)),
                ("end_date", models.DateTimeField()),
                ("auto_renew", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="transactions", to=settings.AUTH_USER_MODEL,
                )),
                ("subscription", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="transactions", to="subscriptions.subscription",
                )),
                ("gateway", models.CharField(max_length=10)),
                ("gateway_transaction_id", models.CharField(blank=True, max_length=200)),
                ("amount_npr", models.DecimalField(decimal_places=2, max_digits=8)),
                ("status", models.CharField(
                    choices=[
                        ("initiated", "Initiated"), ("success", "Success"),
                        ("failed", "Failed"), ("refunded", "Refunded"),
                    ],
                    default="initiated", max_length=12,
                )),
                ("raw_response", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
