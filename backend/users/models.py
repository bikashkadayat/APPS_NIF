import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model for the NIF Portal.
    Uses UUID as the primary key.
    """
    class Roles(models.TextChoices):
        # Business-facing labels (Phase 2.6). The stored VALUES are unchanged
        # (maker/checker/approver/admin) so the leave/memo workflow engine,
        # permissions, policies and existing data keep working untouched; only
        # the display names become the clear business roles.
        MAKER = "maker", "Employee"
        CHECKER = "checker", "Department Head"
        APPROVER = "approver", "HR"
        ADMIN = "admin", "Admin"

    class EmployeeType(models.TextChoices):
        # Org-hierarchy / seniority label - independent of `role` (permissions).
        EMPLOYEE = "employee", "Employee"
        SUPERVISOR = "supervisor", "Supervisor"
        MANAGER = "manager", "Manager"
        DEPARTMENT_HEAD = "department_head", "Department Head"
        HR_OFFICER = "hr_officer", "HR Officer"
        SYSTEM_ADMIN = "system_admin", "System Admin"

    class EmploymentType(models.TextChoices):
        # Contract/engagement basis. Drives the leave *category* engine together
        # with continuous service (date_of_joining). Distinct from both `role`
        # (permissions) and `employee_type` (org rank).
        PERMANENT = "permanent", "Permanent"
        POST_PROBATION = "post_probation", "Post-Probation"
        PROBATION = "probation", "Probation"
        INTERN = "intern", "Intern"
        VOLUNTEER = "volunteer", "Volunteer"

    class LeaveCategory(models.TextChoices):
        # Cached result of the category engine (leaves.category_engine). Never
        # NULL after resolution; PROBATION is the sub-1-quarter floor tier.
        A = "A", "Category A — Permanent (>3 yrs)"
        B = "B", "Category B — Permanent (1–3 yrs)"
        C = "C", "Category C — Post-Probation / Permanent (<1 yr)"
        D = "D", "Category D — Intern / Volunteer"
        PROBATION = "PROBATION", "Probation (<3 mo)"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        UNDISCLOSED = "undisclosed", "Prefer not to say"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.MAKER)
    # Phase 2.6: org-rank label, separate from the permission `role` above.
    employee_type = models.CharField(
        max_length=20, choices=EmployeeType.choices, default=EmployeeType.EMPLOYEE,
    )
    # Leave-category engine inputs/outputs (all additive; existing rows default to
    # PERMANENT and are re-resolved + flagged by the backfill migration).
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.PERMANENT,
    )
    gender = models.CharField(
        max_length=12, choices=Gender.choices, default=Gender.UNDISCLOSED, blank=True,
    )
    # Eligibility is a separate, HR-overridable flag rather than a hard gender
    # gate (inclusive of adoption / same-sex parents / legal edge cases). Saving
    # the user auto-defaults these from gender unless HR has set them explicitly;
    # both are always suppressed for Category D (Intern/Volunteer) at read time.
    maternity_eligible = models.BooleanField(default=False)
    paternity_eligible = models.BooleanField(default=False)
    # Cached category (leaves.category_engine.resolve_category). Recomputed on
    # save/login/rollover; kept on the row so reads don't recompute every time.
    leave_category = models.CharField(
        max_length=12, choices=LeaveCategory.choices, null=True, blank=True,
    )
    # Human-readable note when a fallback/auto-transition rule fired; surfaced to
    # HR in the review list. Null = clean resolution, nothing to review.
    category_flag = models.TextField(null=True, blank=True)
    # Legacy free-text department (Level 1). Kept for backward compatibility.
    department = models.CharField(max_length=100, blank=True, null=True)
    # Phase 4: structured department reference used by leave-policy resolution.
    # NOTE (Phase 2.5): this IS the "department FK" the corrected spec asks for -
    # it already existed, so we reuse it rather than add a duplicate.
    department_ref = models.ForeignKey(
        "leaves.Department", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="members",
    )

    # Phase 2.5: HR profile fields (all additive/nullable so existing rows are safe).
    employee_id = models.CharField(max_length=32, unique=True, null=True, blank=True, editable=False)
    designation = models.CharField(max_length=120, blank=True, null=True)
    date_of_joining = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    profile_photo = models.ImageField(upload_to="profiles/%Y/%m/", null=True, blank=True)
    # Employee self-service personal fields (Profile module; all additive/nullable
    # so existing rows are unaffected). Editable by the employee themselves.
    address = models.CharField(max_length=255, blank=True, default="")
    emergency_contact_name = models.CharField(max_length=120, blank=True, default="")
    emergency_contact_number = models.CharField(max_length=32, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True, default="")
    # Admin-created accounts must change their password on first login.
    must_change_password = models.BooleanField(default=True)
    last_password_change = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="users_created",
    )

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    @property
    def department_name(self):
        if self.department_ref_id:
            return self.department_ref.name
        return self.department or None

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"
