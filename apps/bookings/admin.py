from django.contrib import admin
from .models import RoomType, Booking, BookingPayment


class RoomTypeInline(admin.TabularInline):
    model = RoomType
    extra = 1
    fields = ["name", "capacity", "total_rooms", "price_per_night_npr", "is_active", "order"]


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "hotel", "capacity", "total_rooms", "price_per_night_npr", "is_active"]
    list_filter = ["hotel", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["name", "hotel__name"]


class BookingPaymentInline(admin.TabularInline):
    model = BookingPayment
    extra = 0
    readonly_fields = ["gateway", "payment_type", "amount_npr", "status", "paid_at", "created_at"]
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "reference", "user", "hotel", "room_type",
        "check_in", "check_out", "total_nights",
        "total_npr", "status", "created_at",
    ]
    list_filter = ["status", "hotel", "check_in"]
    search_fields = ["reference", "user__email", "hotel__name"]
    readonly_fields = [
        "reference", "total_nights", "total_npr", "deposit_npr",
        "confirmed_at", "checked_in_at", "checked_out_at",
        "cancelled_at", "auto_checked_out", "created_at", "updated_at",
    ]
    inlines = [BookingPaymentInline]
    ordering = ["-created_at"]

    fieldsets = (
        ("Booking", {
            "fields": ("reference", "user", "hotel", "room_type", "status")
        }),
        ("Dates & Guests", {
            "fields": ("check_in", "check_out", "total_nights", "guests_count", "special_requests")
        }),
        ("Pricing", {
            "fields": ("price_per_night_npr", "total_npr", "deposit_npr")
        }),
        ("Staff actions", {
            "fields": ("confirmed_by", "confirmed_at", "checked_in_at", "checked_out_at", "auto_checked_out")
        }),
        ("Cancellation", {
            "fields": ("cancelled_by", "cancellation_reason", "cancelled_at"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["mark_confirmed", "mark_checked_in", "mark_checked_out", "mark_no_show"]

    @admin.action(description="Mark selected as Confirmed")
    def mark_confirmed(self, request, queryset):
        for booking in queryset.filter(status="paid"):
            booking.staff_confirm(request.user)
        self.message_user(request, "Selected bookings confirmed.")

    @admin.action(description="Mark selected as Checked In")
    def mark_checked_in(self, request, queryset):
        for booking in queryset.filter(status="confirmed"):
            booking.staff_check_in(request.user)
        self.message_user(request, "Selected bookings checked in.")

    @admin.action(description="Mark selected as Checked Out")
    def mark_checked_out(self, request, queryset):
        for booking in queryset.filter(status="checked_in"):
            booking.staff_check_out(request.user)
        self.message_user(request, "Selected bookings checked out.")

    @admin.action(description="Mark selected as No Show")
    def mark_no_show(self, request, queryset):
        queryset.filter(status__in=["confirmed", "paid"]).update(status="no_show")
        self.message_user(request, "Selected bookings marked as no show.")


@admin.register(BookingPayment)
class BookingPaymentAdmin(admin.ModelAdmin):
    list_display = ["booking", "gateway", "payment_type", "amount_npr", "status", "paid_at"]
    list_filter = ["gateway", "status", "payment_type"]
    readonly_fields = ["created_at"]
