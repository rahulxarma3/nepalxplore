from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("destinations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RoomType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("hotel", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="room_types", to="destinations.hotel",
                )),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("capacity", models.PositiveSmallIntegerField(default=2)),
                ("total_rooms", models.PositiveSmallIntegerField(default=1)),
                ("price_per_night_npr", models.DecimalField(decimal_places=2, max_digits=8)),
                ("amenities", models.JSONField(default=list)),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to="rooms/")),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering": ["order", "price_per_night_npr"]},
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("reference", models.CharField(editable=False, max_length=12, unique=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="bookings", to=settings.AUTH_USER_MODEL,
                )),
                ("hotel", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="bookings", to="destinations.hotel",
                )),
                ("room_type", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="bookings", to="bookings.roomtype",
                )),
                ("check_in", models.DateField()),
                ("check_out", models.DateField()),
                ("guests_count", models.PositiveSmallIntegerField(default=1)),
                ("special_requests", models.TextField(blank=True)),
                ("price_per_night_npr", models.DecimalField(decimal_places=2, max_digits=8)),
                ("total_nights", models.PositiveSmallIntegerField()),
                ("total_npr", models.DecimalField(decimal_places=2, max_digits=10)),
                ("deposit_npr", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending Payment"),
                        ("paid", "Paid — Awaiting Confirmation"),
                        ("confirmed", "Confirmed by Hotel"),
                        ("checked_in", "Checked In"),
                        ("checked_out", "Checked Out"),
                        ("cancelled", "Cancelled"),
                        ("no_show", "No Show"),
                    ],
                    default="pending", max_length=12,
                )),
                ("confirmed_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="confirmed_bookings", to=settings.AUTH_USER_MODEL,
                )),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("checked_in_at", models.DateTimeField(blank=True, null=True)),
                ("checked_out_at", models.DateTimeField(blank=True, null=True)),
                ("auto_checked_out", models.BooleanField(default=False)),
                ("cancelled_by", models.CharField(blank=True, max_length=10)),
                ("cancellation_reason", models.TextField(blank=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BookingPayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("booking", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="payments", to="bookings.booking",
                )),
                ("gateway", models.CharField(
                    choices=[("stripe", "Stripe"), ("esewa", "eSewa"), ("khalti", "Khalti")],
                    max_length=10,
                )),
                ("payment_type", models.CharField(
                    choices=[("deposit", "Deposit (30%)"), ("balance", "Remaining Balance"), ("full", "Full Payment")],
                    default="deposit", max_length=10,
                )),
                ("amount_npr", models.DecimalField(decimal_places=2, max_digits=10)),
                ("gateway_transaction_id", models.CharField(blank=True, max_length=200)),
                ("status", models.CharField(
                    choices=[
                        ("initiated", "Initiated"), ("success", "Success"),
                        ("failed", "Failed"), ("refunded", "Refunded"),
                    ],
                    default="initiated", max_length=10,
                )),
                ("raw_response", models.JSONField(default=dict)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
