import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


phone_validator = RegexValidator(
    regex=r"^\+[1-9]\d{7,14}$",
    message="Enter a phone number in international format, e.g. +919876543210.",
)


class NotificationSchedule(models.Model):
    """A configurable recurring schedule for stock-alert notifications."""

    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Every day"
        WEEKLY = "WEEKLY", "Selected days"
        MANUAL = "MANUAL", "Manual only"

    name = models.CharField(max_length=100, default="Daily stock alert")
    frequency = models.CharField(
        max_length=10, choices=Frequency.choices, default=Frequency.DAILY
    )
    scheduled_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Local time in the selected timezone. Required for daily/weekly schedules.",
    )
    # ISO weekday numbers: Monday=1 ... Sunday=7.
    weekdays = models.JSONField(
        default=list,
        blank=True,
        help_text="For weekly schedules, use ISO weekday numbers from 1 (Monday) to 7 (Sunday).",
    )
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    is_active = models.BooleanField(default=True)

    whatsapp_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    low_stock_enabled = models.BooleanField(default=True)
    out_of_stock_enabled = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notification_schedules",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_notification_schedules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["is_active", "frequency"])]

    def clean(self):
        super().clean()
        errors = {}
        if self.frequency in {self.Frequency.DAILY, self.Frequency.WEEKLY} and not self.scheduled_time:
            errors["scheduled_time"] = "A sending time is required for scheduled automation."
        if self.frequency == self.Frequency.WEEKLY:
            if not self.weekdays:
                errors["weekdays"] = "Select at least one day for a weekly schedule."
            elif (
                not isinstance(self.weekdays, list)
                or any(type(day) is not int or day < 1 or day > 7 for day in self.weekdays)
                or len(set(self.weekdays)) != len(self.weekdays)
            ):
                errors["weekdays"] = "Use unique ISO weekday numbers from 1 (Monday) to 7 (Sunday)."
        elif self.weekdays:
            errors["weekdays"] = "Weekdays should only be set for a weekly schedule."
        if self.timezone:
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(self.timezone)
            except Exception:
                errors["timezone"] = "Enter a valid IANA timezone, e.g. Asia/Kolkata."
        if not self.whatsapp_enabled and not self.email_enabled:
            errors["email_enabled"] = "Enable at least one notification channel."
        if not self.low_stock_enabled and not self.out_of_stock_enabled:
            errors["out_of_stock_enabled"] = "Enable at least one stock alert type."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.name


class NotificationRecipient(models.Model):
    """A person or team that can receive alerts, whether or not they log in."""

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(
        max_length=16,
        blank=True,
        validators=[phone_validator],
        help_text="Include country code, e.g. +919876543210.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=250, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_notification_recipients",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["is_active", "name"])]

    def clean(self):
        super().clean()
        if not self.email and not self.phone_number:
            raise ValidationError("Add at least an email address or WhatsApp phone number.")

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if self.phone_number:
            self.phone_number = self.phone_number.strip().replace(" ", "")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class NotificationPreference(models.Model):
    """Per-recipient channel and alert-type choices."""

    recipient = models.OneToOneField(
        NotificationRecipient,
        on_delete=models.CASCADE,
        related_name="preference",
    )
    receive_whatsapp = models.BooleanField(default=False)
    receive_email = models.BooleanField(default=False)
    receive_low_stock = models.BooleanField(default=True)
    receive_out_of_stock = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "notification preference"
        verbose_name_plural = "notification preferences"

    def clean(self):
        super().clean()
        recipient = self.recipient
        if self.receive_email and not recipient.email:
            raise ValidationError({"receive_email": "This recipient does not have an email address."})
        if self.receive_whatsapp and not recipient.phone_number:
            raise ValidationError({"receive_whatsapp": "This recipient does not have a WhatsApp phone number."})

    def __str__(self):
        return f"Preferences for {self.recipient.name}"


class NotificationBatch(models.Model):
    """One logical stock-alert run, which may create several delivery logs."""

    class TriggerType(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        MANUAL = "MANUAL", "Manual"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        PARTIAL = "PARTIAL", "Partially completed"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped – no stock alerts"

    batch_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # A deterministic key supplied by the scheduler/manual endpoint prevents duplicate runs.
    idempotency_key = models.CharField(max_length=160, unique=True, null=True, blank=True)
    schedule = models.ForeignKey(
        NotificationSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="batches",
    )
    trigger_type = models.CharField(max_length=10, choices=TriggerType.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    low_stock_count = models.PositiveIntegerField(default=0)
    out_of_stock_count = models.PositiveIntegerField(default=0)
    total_deliveries = models.PositiveIntegerField(default=0)
    successful_deliveries = models.PositiveIntegerField(default=0)
    failed_deliveries = models.PositiveIntegerField(default=0)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notification_batches",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"Stock alert {self.batch_id} ({self.get_status_display()})"


class NotificationLog(models.Model):
    """An auditable delivery attempt for one recipient and one channel."""

    class Channel(models.TextChoices):
        WHATSAPP = "WHATSAPP", "WhatsApp"
        EMAIL = "EMAIL", "Email"

    class AlertType(models.TextChoices):
        STOCK_SUMMARY = "STOCK_SUMMARY", "Stock summary"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Skipped"

    batch = models.ForeignKey(
        NotificationBatch,
        on_delete=models.CASCADE,
        related_name="delivery_logs",
    )
    recipient = models.ForeignKey(
        NotificationRecipient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_logs",
    )
    # Snapshots preserve the destination/name even if a recipient is later edited or deleted.
    recipient_name = models.CharField(max_length=120)
    destination = models.CharField(max_length=254)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    alert_type = models.CharField(
        max_length=20, choices=AlertType.choices, default=AlertType.STOCK_SUMMARY
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    provider_message_id = models.CharField(max_length=180, blank=True)
    error_message = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "recipient", "channel"],
                name="uniq_stock_alert_batch_recipient_channel",
            )
        ]
        indexes = [
            models.Index(fields=["status", "channel", "created_at"]),
            models.Index(fields=["recipient", "created_at"]),
        ]

    def __str__(self):
        return f"{self.channel} to {self.destination} – {self.get_status_display()}"
