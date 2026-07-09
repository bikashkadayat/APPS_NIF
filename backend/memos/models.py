import uuid
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


def memo_attachment_path(instance, filename):
    """
    Store uploads under an unguessable per-file UUID directory
    (memos/attachments/YYYY/MM/<uuid>/<original-name>). Even if MEDIA were ever
    served directly, the path cannot be guessed; downloads still go through the
    authenticated MemoViewSet.attachment endpoint which enforces CanViewMemo.
    """
    return f"memos/attachments/{timezone.now():%Y/%m}/{uuid.uuid4().hex}/{filename}"


class Memo(models.Model):
    """
    A memo document routed through a maker -> reviewer -> approver workflow.
    """
    class MemoType(models.TextChoices):
        INTERNAL = "internal", "Internal"
        EXTERNAL = "external", "External"
        FINANCIAL = "financial", "Financial"
        HR = "hr", "HR"
        GENERAL = "general", "General"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    memo_number = models.CharField(max_length=30, unique=True, editable=False)
    subject = models.CharField(max_length=500)
    body = models.TextField()

    memo_type = models.CharField(max_length=20, choices=MemoType.choices, default=MemoType.GENERAL)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memos_created", db_index=True)
    current_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="memos_to_review",
        help_text="The user assigned as CHECKER for this memo. Displayed as "
                  "'Checker' in the UI. Field kept as 'current_reviewer' to "
                  "avoid a rename migration.",
    )
    current_approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="memos_to_approve", db_index=True)

    attachment = models.FileField(upload_to=memo_attachment_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.memo_number:
            with transaction.atomic():
                year = timezone.now().year
                prefix = f"NIFN-MEMO-{year}-"
                last = (
                    Memo.objects.select_for_update()
                    .filter(memo_number__startswith=prefix)
                    .order_by("-memo_number")
                    .first()
                )
                last_seq = int(last.memo_number.rsplit("-", 1)[-1]) if last else 0
                self.memo_number = f"{prefix}{last_seq + 1:04d}"
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.memo_number} - {self.title}"


class MemoApprovalStep(models.Model):
    """
    Audit trail entry for a single action taken on a memo's workflow.
    """
    class Action(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RETURNED = "returned", "Returned"
        CANCELLED = "cancelled", "Cancelled"
        COMMENTED = "commented", "Commented"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    memo = models.ForeignKey(Memo, on_delete=models.CASCADE, related_name="approval_steps")
    step_order = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memo_actions")
    action = models.CharField(max_length=20, choices=Action.choices)
    comment = models.TextField(blank=True, default="")
    acted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["memo", "step_order"]

    def __str__(self):
        return f"{self.memo.memo_number} - step {self.step_order} - {self.action}"


class MemoTemplate(models.Model):
    """
    Admin-editable content template used to prefill new memos of a given type.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)
    memo_type = models.CharField(max_length=20, choices=Memo.MemoType.choices)
    subject_template = models.CharField(max_length=500)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.memo_type})"
