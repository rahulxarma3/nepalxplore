from django.contrib import admin
from .models import Plan, Subscription, PaymentTransaction

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "interval", "price_npr", "price_usd", "is_active"]
    prepopulated_fields = {"slug": ["name"]}

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "gateway", "status", "start_date", "end_date"]
    list_filter = ["gateway", "status"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at", "updated_at"]

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "gateway", "amount_npr", "status", "created_at"]
    list_filter = ["gateway", "status"]
    readonly_fields = ["created_at"]
