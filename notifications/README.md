# Gromaster notifications – Stage 1

Stage 1 adds the PostgreSQL data model and Django Admin management for stock-alert schedules, custom recipients, per-recipient preferences, notification batches, and per-channel delivery logs.

No email, WhatsApp, Celery, or Redis messages are sent in Stage 1. Those integrations are added in later stages.

## Models

- `NotificationSchedule`: daily, selected-weekday, or manual schedule; timezone; channel and alert-type switches.
- `NotificationRecipient`: an external contact or Gromaster user contact, with email and/or E.164 phone number.
- `NotificationPreference`: per-recipient channel and alert-type choices.
- `NotificationBatch`: one manual or scheduled run, with idempotency key and summary counts.
- `NotificationLog`: one delivery record per recipient and channel, retaining destination snapshots for audit history.

## Setup

From the folder containing `manage.py`:

```powershell
python manage.py check
python manage.py makemigrations catalog notifications
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `/django-admin/` and create a `NotificationSchedule`, then add `NotificationRecipient` records. Add each recipient's `NotificationPreference` inline. Stage 1 only stores these settings; it does not dispatch notifications.

The `makemigrations catalog notifications` command is intentional: the current project source contains catalog models (including `Category.sku_prefix`) but the catalog migrations folder is empty. Django must create the catalog initial migration along with the new notifications migration before applying migrations to a fresh database.

Use `+919876543210` format for WhatsApp numbers. A recipient must have at least one destination (email or phone). Do not enter a Gmail account password into Gromaster; SMTP app passwords or a transactional email provider credential will be configured securely in a later stage.
