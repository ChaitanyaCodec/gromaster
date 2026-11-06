from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model

from notifications.models import (
    NotificationBatch,
    NotificationLog,
    NotificationPreference,
    NotificationRecipient,
    NotificationSchedule,
)


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="notify-admin", email="admin@example.com", password="test-pass-123"
        )

    def test_daily_schedule_requires_time(self):
        schedule = NotificationSchedule(name="Daily", scheduled_time=None)
        with self.assertRaises(ValidationError):
            schedule.full_clean()

    def test_weekly_schedule_requires_valid_days(self):
        schedule = NotificationSchedule(
            name="Weekdays", frequency=NotificationSchedule.Frequency.WEEKLY,
            scheduled_time="08:00", weekdays=[1, 2, 8],
        )
        with self.assertRaises(ValidationError):
            schedule.full_clean()

    def test_manual_schedule_can_omit_time(self):
        schedule = NotificationSchedule(
            name="Manual", frequency=NotificationSchedule.Frequency.MANUAL,
            scheduled_time=None, weekdays=[],
        )
        schedule.full_clean()

    def test_recipient_requires_at_least_one_destination(self):
        recipient = NotificationRecipient(name="Store Manager")
        with self.assertRaises(ValidationError):
            recipient.full_clean()

    def test_recipient_normalizes_email_and_phone(self):
        recipient = NotificationRecipient(
            name="Store Manager", email=" MANAGER@EXAMPLE.COM ",
            phone_number="+91 9876543210",
        )
        recipient.save()
        self.assertEqual(recipient.email, "manager@example.com")
        self.assertEqual(recipient.phone_number, "+919876543210")

    def test_preference_rejects_channel_without_destination(self):
        recipient = NotificationRecipient.objects.create(
            name="Email only", email="manager@example.com"
        )
        preference = NotificationPreference(
            recipient=recipient, receive_whatsapp=True, receive_email=True
        )
        with self.assertRaises(ValidationError):
            preference.full_clean()

    def test_batch_and_delivery_log_can_be_recorded(self):
        recipient = NotificationRecipient.objects.create(
            name="Store Manager", email="manager@example.com"
        )
        batch = NotificationBatch.objects.create(
            trigger_type=NotificationBatch.TriggerType.MANUAL,
            triggered_by=self.user,
        )
        log = NotificationLog.objects.create(
            batch=batch, recipient=recipient, recipient_name=recipient.name,
            destination=recipient.email, channel=NotificationLog.Channel.EMAIL,
        )
        self.assertEqual(log.status, NotificationLog.Status.PENDING)
        self.assertEqual(batch.delivery_logs.count(), 1)
