"""Inventory business logic — race-safe sequences + atomic state transitions.

Every state change (assign / return / approve / reject / mark-returned) runs
inside transaction.atomic() and re-reads the row with select_for_update() so
concurrent actors serialize on the row lock (same pattern as memos/leaves).
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import InventoryItem, ItemAssignment, InventorySequence, TakeOutRequest


# --------------------------------------------------------------------------- #
# Reference / asset-code generation (gap-free, race-safe)
# --------------------------------------------------------------------------- #
@transaction.atomic
def _next_seq(key, year=0):
    # Own transaction (or savepoint if already inside one) so select_for_update is
    # always valid — DRF's perform_create is not atomic by default.
    InventorySequence.objects.get_or_create(key=key, year=year)
    seq = InventorySequence.objects.select_for_update().get(key=key, year=year)
    seq.last_value += 1
    seq.save(update_fields=["last_value"])
    return seq.last_value


def current_bs_year():
    from config.nepali_dates import to_bs
    bs = to_bs(timezone.localtime(timezone.now()).date())
    return int(bs.split("-")[0]) if bs else timezone.now().year


def generate_asset_code():
    """NIF-INV-0001 (not year-scoped)."""
    return f"NIF-INV-{_next_seq('INV', 0):04d}"


def generate_takeout_reference():
    """NIF-OUT-2083-0001 (scoped to the current BS year)."""
    y = current_bs_year()
    return f"NIF-OUT-{y}-{_next_seq('OUT', y):04d}"


def _name(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


# --------------------------------------------------------------------------- #
# Direct assignment (who is using what)
# --------------------------------------------------------------------------- #
@transaction.atomic
def assign_item(item_id, assignee, actor, *, note="", assigned_date=None,
                handover_condition="", accessories="", is_handover=False,
                require_current_holder=False):
    item = InventoryItem.objects.select_for_update().get(pk=item_id)
    if item.status in (InventoryItem.Status.RETIRED, InventoryItem.Status.MAINTENANCE):
        raise ValidationError(f"Cannot assign a {item.get_status_display().lower()} item.")
    prior = ItemAssignment.objects.select_for_update().filter(item=item, is_active=True).first()
    if require_current_holder and prior is None:
        raise ValidationError("This item has no current holder to hand over from.")
    if prior and prior.assigned_to_id == getattr(assignee, "id", None):
        raise ValidationError("The item is already assigned to this employee.")
    # Close any prior active assignment first (keeps the one-active constraint).
    if prior:
        prior.is_active = False
        prior.returned_at = timezone.now()
        prior.save(update_fields=["is_active", "returned_at"])
    assignment = ItemAssignment.objects.create(
        item=item, assigned_to=assignee, assigned_to_name=_name(assignee),
        assigned_by=actor, assigned_by_name=_name(actor), note=note,
        assigned_date=assigned_date or timezone.localtime(timezone.now()).date(),
        handover_condition=handover_condition or item.condition,
        accessories=accessories, is_handover=is_handover, is_active=True)
    item.status = InventoryItem.Status.ASSIGNED
    item.save(update_fields=["status", "updated_at"])
    return assignment


@transaction.atomic
def handover_item(item_id, new_assignee, actor, *, note="", assigned_date=None,
                  handover_condition="", accessories=""):
    """Transfer an item from its current holder to a new employee (staff change)."""
    return assign_item(
        item_id, new_assignee, actor, note=note, assigned_date=assigned_date,
        handover_condition=handover_condition, accessories=accessories,
        is_handover=True, require_current_holder=True)


@transaction.atomic
def return_item(item_id, actor, *, return_condition="", return_remarks=""):
    item = InventoryItem.objects.select_for_update().get(pk=item_id)
    active = ItemAssignment.objects.select_for_update().filter(item=item, is_active=True).first()
    if active:
        active.is_active = False
        active.returned_at = timezone.now()
        active.return_condition = return_condition or ""
        active.return_remarks = return_remarks or ""
        active.save(update_fields=["is_active", "returned_at", "return_condition", "return_remarks"])
    if return_condition:
        item.condition = return_condition
    if item.status in (InventoryItem.Status.ASSIGNED, InventoryItem.Status.OUT):
        item.status = InventoryItem.Status.AVAILABLE
    item.save(update_fields=["status", "condition", "updated_at"])
    return item


# --------------------------------------------------------------------------- #
# Take-out workflow
# --------------------------------------------------------------------------- #
def assert_item_takeable(item):
    """Raise if the item cannot be taken out (retired / maintenance / already out
    / an in-flight request exists)."""
    if item is None:
        raise ValidationError("Item is required.")
    blocked = {
        InventoryItem.Status.RETIRED: "retired",
        InventoryItem.Status.MAINTENANCE: "under maintenance",
        InventoryItem.Status.OUT: "already taken out",
    }
    if item.status in blocked:
        raise ValidationError(f"This item is {blocked[item.status]} and cannot be taken out.")
    existing = TakeOutRequest.objects.filter(
        item=item, status__in=[TakeOutRequest.Status.PENDING, TakeOutRequest.Status.APPROVED]
    ).exists()
    if existing:
        raise ValidationError("There is already an active take-out request for this item.")


@transaction.atomic
def create_takeout(*, item, requester, purpose, reason, expected_out_date, expected_return_date):
    item = InventoryItem.objects.select_for_update().get(pk=item.pk)
    assert_item_takeable(item)
    if expected_return_date < expected_out_date:
        raise ValidationError("Expected return date cannot be before the take-out date.")
    dept = getattr(requester, "department_ref", None)
    req = TakeOutRequest.objects.create(
        reference=generate_takeout_reference(),
        item=item, item_code=item.asset_code, item_name=item.name,
        requested_by=requester, requested_by_name=_name(requester), department=dept,
        purpose=purpose, reason=reason,
        expected_out_date=expected_out_date, expected_return_date=expected_return_date,
        status=TakeOutRequest.Status.PENDING,
    )
    return req


@transaction.atomic
def approve_takeout(req_id, actor, remarks=""):
    req = TakeOutRequest.objects.select_for_update().get(pk=req_id)
    if req.status != TakeOutRequest.Status.PENDING:
        raise ValidationError("Only a pending request can be approved.")
    req.status = TakeOutRequest.Status.APPROVED
    req.approver = actor
    req.approver_name = _name(actor)
    req.approver_remarks = remarks
    req.action_date = timezone.now()
    req.save(update_fields=["status", "approver", "approver_name", "approver_remarks",
                            "action_date", "updated_at"])
    if req.item_id:
        item = InventoryItem.objects.select_for_update().get(pk=req.item_id)
        item.status = InventoryItem.Status.OUT
        item.save(update_fields=["status", "updated_at"])
    return req


@transaction.atomic
def reject_takeout(req_id, actor, remarks):
    remarks = (remarks or "").strip()
    if not remarks:
        raise ValidationError("A remark is required when rejecting a request.")
    req = TakeOutRequest.objects.select_for_update().get(pk=req_id)
    if req.status != TakeOutRequest.Status.PENDING:
        raise ValidationError("Only a pending request can be rejected.")
    req.status = TakeOutRequest.Status.REJECTED
    req.approver = actor
    req.approver_name = _name(actor)
    req.approver_remarks = remarks
    req.action_date = timezone.now()
    req.save(update_fields=["status", "approver", "approver_name", "approver_remarks",
                            "action_date", "updated_at"])
    return req


@transaction.atomic
def mark_returned(req_id, actor):
    req = TakeOutRequest.objects.select_for_update().get(pk=req_id)
    if req.status != TakeOutRequest.Status.APPROVED:
        raise ValidationError("Only an approved (currently out) item can be marked returned.")
    req.status = TakeOutRequest.Status.RETURNED
    req.actual_return_date = timezone.localtime(timezone.now()).date()
    req.save(update_fields=["status", "actual_return_date", "updated_at"])
    if req.item_id:
        item = InventoryItem.objects.select_for_update().get(pk=req.item_id)
        # Back to available unless it is still directly assigned to someone.
        if item.status == InventoryItem.Status.OUT:
            item.status = InventoryItem.Status.AVAILABLE
            item.save(update_fields=["status", "updated_at"])
    return req
