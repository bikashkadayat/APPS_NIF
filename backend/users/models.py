import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model for the NIF Portal.
    Uses UUID as the primary key.
    """
    class Roles(models.TextChoices):
        MAKER = "maker", "Maker"
        CHECKER = "checker", "Checker"
        APPROVER = "approver", "Approver"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.MAKER)
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
