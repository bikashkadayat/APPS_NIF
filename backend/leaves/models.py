import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings

class LeaveBalance(models.Model):
    """
    Tracks the total and used leave balances per user per year.
    """
    class LeaveType(models.TextChoices):
        ANNUAL = "annual", "Annual Leave"
        SICK = "sick", "Sick Leave"
        CASUAL = "casual", "Casual Leave"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    year = models.IntegerField()
    total_allocated = models.IntegerField()
    used_so_far = models.FloatField(default=0)

    class Meta:
        unique_together = ('user', 'leave_type', 'year')

    @property
    def remaining(self):
        return self.total_allocated - self.used_so_far

    def __str__(self):
        return f"{self.user} - {self.leave_type} ({self.year})"


class Leave(models.Model):
    """
    Leave Application tracking model.
    """
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leaves_applied")
    leave_type = models.CharField(max_length=20, choices=LeaveBalance.LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    handover_notes = models.TextField(blank=True, default='')
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="leaves_to_approve")

    # Phase 5: soft-delete. Leaves with approved day records are never hard
    # deleted (integrity); they are flagged here instead.
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.leave_type} ({self.status})"


# ===========================================================================
# Phase 4 - Enterprise Leave Records
#
# These models EXTEND the Level 1 leaves app; the original Leave / LeaveBalance
# above are intentionally left untouched. New enterprise fields live on new
# tables so existing endpoints keep working.
# ===========================================================================

# Roles are duplicated as plain choices here (rather than importing users.User)
# to avoid an import cycle at module load; they mirror users.User.Roles.
ROLE_CHOICES = [
    ("maker", "Maker"),
    ("checker", "Checker"),
    ("approver", "Approver"),
    ("admin", "Admin"),
]


class Department(models.Model):
    """Organizational unit, optionally nested (parent) for reporting hierarchy."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="departments_headed",
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveType(models.Model):
    """
    CMS-driven leave type. Replaces the hardcoded LeaveBalance.LeaveType enum
    for all Phase 4 features; admins manage these from the dashboard.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    default_days_per_year = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(default=True)
    allow_half_day = models.BooleanField(default=True)
    allow_carry_forward = models.BooleanField(default=False)
    max_carry_forward_days = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    requires_document = models.BooleanField(default=False)
    min_notice_days = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    display_color = models.CharField(max_length=7, default="#6B7280")  # hex for calendar UI
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeavePolicy(models.Model):
    """
    Overrides a LeaveType's default entitlement for a department and/or role,
    effective over a date range. Null department => org-wide; null role => all
    roles. Resolution prefers the most specific match (see services).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="policies")
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True, related_name="leave_policies",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    days_per_year = models.DecimalField(max_digits=6, decimal_places=2)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leave_policies_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["leave_type", "department", "role", "effective_from"],
                name="uniq_policy_scope_effective",
            ),
        ]

    def __str__(self):
        scope = self.department.code if self.department else "ORG"
        return f"{self.leave_type.code}/{scope}/{self.role or 'ALL'} = {self.days_per_year}d"


class Holiday(models.Model):
    """CMS-driven public holiday; excluded from working-day calculations."""
    class HolidayType(models.TextChoices):
        PUBLIC = "public", "Public"
        OPTIONAL = "optional", "Optional"
        RELIGIOUS = "religious", "Religious"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(unique=True)
    name = models.CharField(max_length=150)
    holiday_type = models.CharField(max_length=20, choices=HolidayType.choices, default=HolidayType.PUBLIC)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} - {self.name}"


class LeaveDayRecord(models.Model):
    """
    ATOMIC per-day source of truth. One row per calendar day covered by a leave
    request. Every weekly/monthly summary and balance is derived from this
    table, which makes reporting fast and fully auditable.
    """
    class DayPortion(models.TextChoices):
        FULL = "full", "Full Day"
        FIRST_HALF = "first_half", "First Half"
        SECOND_HALF = "second_half", "Second Half"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    PORTION_WEIGHTS = {
        DayPortion.FULL: Decimal("1.0"),
        DayPortion.FIRST_HALF: Decimal("0.5"),
        DayPortion.SECOND_HALF: Decimal("0.5"),
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    leave_request = models.ForeignKey(Leave, on_delete=models.CASCADE, related_name="day_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_day_records")
    date = models.DateField()
    day_portion = models.CharField(max_length=20, choices=DayPortion.choices, default=DayPortion.FULL)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="day_records")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_holiday = models.BooleanField(default=False)
    is_weekend = models.BooleanField(default=False)
    week_number = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]
        indexes = [
            models.Index(fields=["user", "year", "month"]),
            models.Index(fields=["user", "year", "week_number"]),
            models.Index(fields=["date", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date", "day_portion", "leave_request"],
                name="uniq_leave_day_booking",
            ),
        ]

    @property
    def portion_days(self):
        """Decimal weight this record contributes to a day count (1.0 or 0.5)."""
        return self.PORTION_WEIGHTS.get(self.day_portion, Decimal("1.0"))

    @property
    def is_working_day(self):
        return not (self.is_holiday or self.is_weekend)

    def __str__(self):
        return f"{self.user} {self.date} {self.day_portion} ({self.status})"


class EnterpriseLeaveBalance(models.Model):
    """
    Phase 4 balance, recomputed idempotently from LeaveDayRecord + LeavePolicy.
    (The Level 1 LeaveBalance above is kept for backward compatibility.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enterprise_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="balances")
    year = models.PositiveIntegerField()
    entitled_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    carried_forward_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    used_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    pending_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    encashed_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    forfeited_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    # Phase 7: manual HR adjustment (bonus/deduction). Preserved by recompute
    # (never derived from records); every change is audit-logged with a reason.
    adjustment_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    last_recomputed_at = models.DateTimeField(null=True, blank=True)
    # Phase 5: set by process_year_end to freeze a closed year's balance.
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "leave_type"]
        constraints = [
            models.UniqueConstraint(fields=["user", "leave_type", "year"], name="uniq_enterprise_balance"),
        ]

    @property
    def available_days(self):
        """entitled + carried_forward + adjustment - used - pending."""
        return (
            self.entitled_days + self.carried_forward_days + self.adjustment_days
            - self.used_days - self.pending_days
        )

    def __str__(self):
        return f"{self.user} {self.leave_type.code} {self.year}: {self.available_days} avail"


class WeeklyLeaveSummary(models.Model):
    """Materialized weekly aggregate, recomputed from LeaveDayRecord."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_summaries")
    year = models.PositiveIntegerField()
    week_number = models.PositiveSmallIntegerField()
    week_start_date = models.DateField()
    week_end_date = models.DateField()
    total_leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    by_type = models.JSONField(default=dict, blank=True)
    approved_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    pending_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    rejected_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    working_days = models.PositiveSmallIntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("100.00"))
    last_recomputed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "-week_number"]
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "week_number"], name="uniq_weekly_summary"),
        ]

    def __str__(self):
        return f"{self.user} {self.year}-W{self.week_number}"


class MonthlyLeaveSummary(models.Model):
    """Materialized monthly aggregate, recomputed from LeaveDayRecord."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="monthly_summaries")
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    total_leave_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    by_type = models.JSONField(default=dict, blank=True)
    approved_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    pending_days = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    working_days = models.PositiveSmallIntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("100.00"))
    carry_forward_earned = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    last_recomputed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "month"], name="uniq_monthly_summary"),
        ]

    def __str__(self):
        return f"{self.user} {self.year}-{self.month:02d}"
