from django.contrib import admin

from .models import (
    NotificationBatch,
    NotificationLog,
    NotificationPreference,
    NotificationRecipient,
    NotificationSchedule,
)


@admin.register(NotificationSchedule)
class NotificationScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "frequency", "scheduled_time", "timezone", "is_active")
    list_filter = ("frequency", "is_active", "whatsapp_enabled", "email_enabled")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")


class NotificationPreferenceInline(admin.StackedInline):
    model = NotificationPreference
    extra = 0
    max_num = 1


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone_number", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "email", "phone_number")
    inlines = (NotificationPreferenceInline,)
    readonly_fields = ("created_at", "updated_at")


@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    list_display = (
        "batch_id", "trigger_type", "status", "low_stock_count",
        "out_of_stock_count", "total_deliveries", "created_at",
    )
    list_filter = ("trigger_type", "status")
    search_fields = ("batch_id", "idempotency_key")
    readonly_fields = [field.name for field in NotificationBatch._meta.fields]


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "channel", "destination", "status", "attempt_count", "created_at")
    list_filter = ("channel", "status", "alert_type")
    search_fields = ("recipient_name", "destination", "provider_message_id")
    readonly_fields = [field.name for field in NotificationLog._meta.fields]
