"""Inventory Management models.

Tracks office assets, WHO currently holds each one (ItemAssignment), and an
approval workflow for taking an item home/outside (TakeOutRequest) — mirroring the
leave module's maker→checker/approver→approved pattern.

Design notes:
  * User FKs are SET_NULL + name snapshots so historical records survive account
    deletion (the DB was designed to be wiped/re-onboarded).
  * asset_code / reference are handed out by a race-safe per-key counter
    (InventorySequence) — see services.py.
"""
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class InventorySequence(models.Model):
    """Gap-free, race-safe counter for asset codes / take-out references.
    ``year`` = 0 means not year-scoped (asset codes); a BS year for references."""
    key = models.CharField(max_length=8)
    year = models.PositiveIntegerField(default=0)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("key", "year")

    def __str__(self):
        return f"{self.key}-{self.year}: {self.last_value}"


class InventoryCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Inventory categories"

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        ASSIGNED = "assigned", "Assigned"
        OUT = "out", "Taken Out"            # approved take-out, currently outside
        MAINTENANCE = "maintenance", "Under Maintenance"
        RETIRED = "retired", "Retired"

    class Condition(models.TextChoices):
        NEW = "new", "New"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        DAMAGED = "damaged", "Damaged"

    class AssetType(models.TextChoices):
        IT = "it", "IT / Computing"
        PERIPHERAL = "peripheral", "Peripheral"
        FURNITURE = "furniture", "Furniture"
        VEHICLE = "vehicle", "Vehicle"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_code = models.CharField(max_length=32, unique=True, editable=False)
    name = models.CharField(max_length=150)
    asset_type = models.CharField(max_length=20, choices=AssetType.choices, default=AssetType.OTHER)
    category = models.ForeignKey(
        InventoryCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")
    serial_number = models.CharField(max_length=120, blank=True, default="")
    department = models.ForeignKey(
        "leaves.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_items")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)
    purchase_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    # --- Device specifications (mainly IT/electronic assets; all optional) ---
    brand = models.CharField(max_length=80, blank=True, default="")
    model = models.CharField(max_length=120, blank=True, default="")
    cpu = models.CharField(max_length=120, blank=True, default="")
    ram = models.CharField(max_length=60, blank=True, default="")
    storage_type = models.CharField(max_length=40, blank=True, default="")   # SSD/HDD/NVMe
    storage_size = models.CharField(max_length=40, blank=True, default="")   # e.g. 512GB
    gpu = models.CharField(max_length=120, blank=True, default="")
    screen_size = models.CharField(max_length=40, blank=True, default="")
    os = models.CharField(max_length=80, blank=True, default="")
    mac_address = models.CharField(max_length=64, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendor = models.CharField(max_length=150, blank=True, default="")
    accessories = models.CharField(max_length=255, blank=True, default="")   # charger/bag/mouse
    # Flexible, category-appropriate specs for non-IT items (furniture, camera…).
    specifications = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["asset_code"]

    def __str__(self):
        return f"{self.asset_code} · {self.name}"

    @property
    def is_it_asset(self):
        return self.asset_type in (self.AssetType.IT, self.AssetType.PERIPHERAL)

    @property
    def active_assignment(self):
        return self.assignments.filter(is_active=True).first()


class ItemAssignment(models.Model):
    """WHO is currently using an item. At most one active row per item."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="assignments")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_assignments")
    assigned_to_name = models.CharField(max_length=150, blank=True, default="")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_assigned_by")
    assigned_by_name = models.CharField(max_length=150, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")
    # Business handover date (BS+AD), distinct from the created timestamp.
    assigned_date = models.DateField(null=True, blank=True)
    handover_condition = models.CharField(max_length=20, choices=InventoryItem.Condition.choices, blank=True, default="")
    accessories = models.CharField(max_length=255, blank=True, default="")
    # A handover is a transfer from a previous active holder to a new one.
    is_handover = models.BooleanField(default=False)
    # Captured when the item is returned / the assignment is closed.
    return_condition = models.CharField(max_length=20, choices=InventoryItem.Condition.choices, blank=True, default="")
    return_remarks = models.CharField(max_length=255, blank=True, default="")
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            # Integrity: only one active holder per item at any time (race-safe).
            models.UniqueConstraint(
                fields=["item"], condition=Q(is_active=True),
                name="uniq_active_assignment_per_item"),
        ]

    def __str__(self):
        return f"{self.item.asset_code} → {self.assigned_to_name} ({'active' if self.is_active else 'closed'})"


class TakeOutRequest(models.Model):
    class Purpose(models.TextChoices):
        HOME = "home", "Take Home"
        OUTSIDE = "outside", "Use Outside Office"
        REPAIR = "repair", "Repair / Servicing"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RETURNED = "returned", "Returned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=32, unique=True, editable=False)
    # Item FK is SET_NULL + snapshot so a retired/deleted item keeps its history.
    item = models.ForeignKey(
        InventoryItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="takeout_requests")
    item_code = models.CharField(max_length=32, blank=True, default="")
    item_name = models.CharField(max_length=150, blank=True, default="")

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="takeout_requests")
    requested_by_name = models.CharField(max_length=150, blank=True, default="")
    department = models.ForeignKey(
        "leaves.Department", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_takeouts")

    purpose = models.CharField(max_length=12, choices=Purpose.choices, default=Purpose.HOME)
    reason = models.TextField()
    expected_out_date = models.DateField()
    expected_return_date = models.DateField()

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="takeout_reviewed")
    approver_name = models.CharField(max_length=150, blank=True, default="")
    approver_remarks = models.TextField(blank=True, default="")
    action_date = models.DateTimeField(null=True, blank=True)
    actual_return_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["requested_by", "status"]),
        ]

    def __str__(self):
        return f"{self.reference} · {self.item_code} ({self.status})"
