import uuid

from django.conf import settings
from django.db import models


class Category(models.TextChoices):
    MEMO_ASSIGNED_TO_REVIEW = "MEMO_ASSIGNED_TO_REVIEW", "Memo assigned to review"
    MEMO_APPROVED = "MEMO_APPROVED", "Memo approved"
    MEMO_REJECTED = "MEMO_REJECTED", "Memo rejected"
    MEMO_RETURNED = "MEMO_RETURNED", "Memo returned"
    LEAVE_SUBMITTED = "LEAVE_SUBMITTED", "Leave submitted"
    LEAVE_APPROVED = "LEAVE_APPROVED", "Leave approved"
    LEAVE_REJECTED = "LEAVE_REJECTED", "Leave rejected"
    LEAVE_BALANCE_LOW = "LEAVE_BALANCE_LOW", "Leave balance low"
    POLICY_UPDATED = "POLICY_UPDATED", "Policy updated"
    SYSTEM_ANNOUNCEMENT = "SYSTEM_ANNOUNCEMENT", "System announcement"
    WEEKLY_DIGEST = "WEEKLY_DIGEST", "Weekly digest"
    INVENTORY_TAKEOUT_REQUESTED = "INVENTORY_TAKEOUT_REQUESTED", "Inventory take-out requested"
    INVENTORY_TAKEOUT_APPROVED = "INVENTORY_TAKEOUT_APPROVED", "Inventory take-out approved"
    INVENTORY_TAKEOUT_REJECTED = "INVENTORY_TAKEOUT_REJECTED", "Inventory take-out rejected"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications", db_index=True,
    )
    category = models.CharField(max_length=40, choices=Category.choices, db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    action_url = models.CharField(max_length=500, blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    is_email_sent = models.BooleanField(default=False)
    # Optional dedup key; two notifications with the same (recipient, key) collapse.
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="uniq_notification_idempotency",
            ),
        ]

    def __str__(self):
        return f"{self.category} -> {self.recipient} ({'read' if self.is_read else 'unread'})"


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences",
    )
    category = models.CharField(max_length=40, choices=Category.choices)
    in_app_enabled = models.BooleanField(default=True)
    # Weekly digest is opt-in; everything else defaults on (see get_preference).
    email_enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "category"], name="uniq_user_category_pref"),
        ]

    def __str__(self):
        return f"{self.user} / {self.category}: in_app={self.in_app_enabled} email={self.email_enabled}"


class NotificationLog(models.Model):
    """
    Audit + retry log for outbound emails. One row per send attempt (sent or
    failed with the error), so failures are visible and retryable rather than
    swallowed silently. Written by the email worker; failures to write here are
    themselves swallowed so logging can never break the workflow.
    """
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notification_logs",
    )
    recipient_email = models.EmailField(blank=True, default="")
    category = models.CharField(max_length=40)
    # Free-form reference to the source object (e.g. the leave UUID) for auditing.
    object_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    subject = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.recipient_email} {self.category} [{self.status}]"
