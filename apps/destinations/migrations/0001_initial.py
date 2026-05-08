from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Destination",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True)),
                ("region", models.CharField(blank=True, max_length=200)),
                ("description", models.TextField()),
                ("cover_image", models.ImageField(upload_to="destinations/")),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("altitude_m", models.PositiveIntegerField(blank=True, null=True)),
                ("best_season", models.CharField(blank=True, max_length=200)),
                ("is_featured", models.BooleanField(default=False)),
                ("order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering": ["order", "name"]},
        ),
        migrations.CreateModel(
            name="TrekkingRoute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("destination", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="trekking_routes", to="destinations.destination",
                )),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField()),
                ("cover_image", models.ImageField(upload_to="routes/")),
                ("difficulty", models.CharField(
                    choices=[
                        ("easy", "Easy"), ("moderate", "Moderate"),
                        ("hard", "Hard"), ("extreme", "Extreme"),
                    ],
                    max_length=10,
                )),
                ("duration_days", models.PositiveSmallIntegerField()),
                ("max_altitude_m", models.PositiveIntegerField(blank=True, null=True)),
                ("distance_km", models.FloatField(blank=True, null=True)),
                ("is_published", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Hotel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("destination", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="hotels", to="destinations.destination",
                )),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True)),
                ("hotel_type", models.CharField(
                    choices=[
                        ("hotel", "Hotel"), ("resort", "Resort"),
                        ("homestay", "Homestay"), ("guesthouse", "Guesthouse"),
                    ],
                    max_length=15,
                )),
                ("description", models.TextField()),
                ("cover_image", models.ImageField(upload_to="hotels/")),
                ("price_per_night_npr", models.DecimalField(decimal_places=2, max_digits=8)),
                ("altitude_m", models.PositiveIntegerField(blank=True, null=True)),
                ("rating", models.DecimalField(decimal_places=1, default=0, max_digits=3)),
                ("is_published", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="CulturalContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True)),
                ("destination", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="cultural_content", to="destinations.destination",
                )),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(unique=True)),
                ("content_type", models.CharField(
                    choices=[
                        ("festival", "Festival"), ("tradition", "Tradition"),
                        ("food", "Local Food"), ("art", "Art & Craft"),
                        ("experience", "Experience"),
                    ],
                    max_length=15,
                )),
                ("description", models.TextField()),
                ("cover_image", models.ImageField(upload_to="culture/")),
                ("is_published", models.BooleanField(default=True)),
            ],
        ),
    ]
