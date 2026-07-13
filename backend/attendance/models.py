import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Attendance(models.Model):
    """One attendance record per employee per day (check-in/out based).

    Holiday / On-Leave statuses are derived at read time from the existing
    Holiday + Leave models, so those days need no pre-created rows; a stored row
    exists only when there is a real check-in or a manual HR entry.
    """

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        HALF_DAY = "half_day", "Half Day"
        ON_LEAVE = "on_leave", "On Leave"
        HOLIDAY = "holiday", "Holiday"

    class MarkedBy(models.TextChoices):
        SELF = "self", "Self"
        HR = "hr", "HR"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField(db_index=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABSENT)
    working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    remarks = models.TextField(blank=True, default="")
    marked_by = models.CharField(max_length=10, choices=MarkedBy.choices, default=MarkedBy.SELF)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["-date"]
        indexes = [models.Index(fields=["employee", "date"])]

    def __str__(self):
        return f"{self.employee} · {self.date} · {self.status}"
