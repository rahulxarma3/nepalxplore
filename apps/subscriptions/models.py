from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Plan(models.Model):
    INTERVAL_CHOICES = [("monthly", "Monthly"), ("yearly", "Yearly")]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price_npr = models.DecimalField(max_digits=8, decimal_places=2)
    price_usd = models.DecimalField(max_digits=8, decimal_places=2)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    features = models.JSONField(default=list)  # list of feature strings

    class Meta:
        ordering = ["price_npr"]

    def __str__(self):
        return f"{self.name} ({self.interval})"


class Subscription(models.Model):
    GATEWAY_CHOICES = [
        ("stripe", "Stripe"),
        ("esewa", "eSewa"),
        ("khalti", "Khalti"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("pending", "Pending"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES)
    gateway_subscription_id = models.CharField(max_length=200, blank=True)
    gateway_customer_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — {self.plan} [{self.status}]"

    @property
    def is_active(self):
        return self.status == "active" and self.end_date > timezone.now()

    @property
    def days_remaining(self):
        if self.is_active:
            return (self.end_date - timezone.now()).days
        return 0

    def activate(self, gateway_ref=""):
        self.status = "active"
        self.gateway_subscription_id = gateway_ref
        interval_days = 30 if self.plan.interval == "monthly" else 365
        self.end_date = timezone.now() + timedelta(days=interval_days)
        self.save()


class PaymentTransaction(models.Model):
    STATUS_CHOICES = [
        ("initiated", "Initiated"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, null=True, related_name="transactions"
    )
    gateway = models.CharField(max_length=10)
    gateway_transaction_id = models.CharField(max_length=200, blank=True)
    amount_npr = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="initiated")
    raw_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gateway} {self.amount_npr} NPR [{self.status}]"
