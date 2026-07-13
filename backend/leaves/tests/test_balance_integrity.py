"""
Cluster A regression tests — simple LeaveBalance is a derived projection of the
LeaveDayRecord source of truth, kept correct across the two-stage workflow.

Covers:
  H4 — pending leave reserves balance; over-application is blocked.
  M3 — an approved leave is deducted exactly once (no double-deduct, no stage skip).
  H3 — cancelling an approved leave refunds the balance.
"""
from datetime import timedelta

import pytest
from rest_framework.test import APIClient

from users.models import User
from leaves.models import Leave, LeaveBalance
from .conftest import _user, MONDAY, YEAR


FRI = MONDAY + timedelta(days=4)  # Mon..Fri inclusive = 5 working days (no Saturday)


@pytest.fixture
def approver(db):
    return _user("lapprover", User.Roles.APPROVER)


def _apply(client, approver, start, end):
    return client.post("/api/v1/leaves/", {
        "leave_type": "annual",
        "start_date": str(start),
        "end_date": str(end),
        "reason": "Test leave",
        "approver": str(approver.id),
    }, format="json")


def _balance(user):
    bal = LeaveBalance.objects.filter(user=user, leave_type="annual", year=YEAR).first()
    return bal.used_so_far if bal else 0


@pytest.mark.django_db
def test_pending_leave_reserves_balance_and_blocks_overapplication(maker, checker, approver):
    """H4: a pending application immediately consumes balance; a second request
    that would exceed the remainder (18 annual) is rejected."""
    client = APIClient(); client.force_authenticate(maker)

    resp = _apply(client, approver, MONDAY, FRI)
    assert resp.status_code == 201, resp.content
    assert _balance(maker) == 5  # 5 working days reserved while merely PENDING

    # Remaining is 13; ask for a ~3-week span (>13 working days) -> blocked.
    big_start = MONDAY + timedelta(days=7)
    resp2 = _apply(client, approver, big_start, big_start + timedelta(days=20))
    assert resp2.status_code == 400, resp2.content
    assert "exceed" in str(resp2.content).lower()
    assert _balance(maker) == 5  # unchanged — the rejected apply left no trace
    assert Leave.objects.filter(user=maker).count() == 1


@pytest.mark.django_db
def test_two_stage_approval_deducts_exactly_once(maker, checker, approver):
    """M3: pending -> Dept Head -> HR keeps the deduction at 5 (never doubles)."""
    client = APIClient(); client.force_authenticate(maker)
    resp = _apply(client, approver, MONDAY, FRI)
    leave_id = resp.json()["id"]
    assert _balance(maker) == 5

    # Level 1: Department Head approves -> pending_hr. Balance still reserved once.
    dh = APIClient(); dh.force_authenticate(checker)
    r1 = dh.post(f"/api/v1/leaves/{leave_id}/dept-head-review/", {"decision": "approve"}, format="json")
    assert r1.status_code == 200, r1.content
    assert Leave.objects.get(pk=leave_id).status == Leave.Status.PENDING_HR
    assert _balance(maker) == 5

    # Level 2: HR approves -> approved. Still exactly 5 (deducted once, not twice).
    hr = APIClient(); hr.force_authenticate(approver)
    r2 = hr.post(f"/api/v1/leaves/{leave_id}/hr-review/", {"decision": "approve"}, format="json")
    assert r2.status_code == 200, r2.content
    assert Leave.objects.get(pk=leave_id).status == Leave.Status.APPROVED
    assert _balance(maker) == 5


@pytest.mark.django_db
def test_set_status_cannot_skip_department_head(maker, approver):
    """M3: set_status may not jump pending -> approved (Level 1 not done)."""
    client = APIClient(); client.force_authenticate(maker)
    leave_id = _apply(client, approver, MONDAY, FRI).json()["id"]

    hr = APIClient(); hr.force_authenticate(approver)
    r = hr.post(f"/api/v1/leaves/{leave_id}/set_status/", {"status": "approved"}, format="json")
    assert r.status_code == 409, r.content
    assert Leave.objects.get(pk=leave_id).status == Leave.Status.PENDING


@pytest.mark.django_db
def test_cancelling_approved_leave_refunds_balance(maker, checker, approver):
    """H3: deleting an approved leave frees the balance it had consumed."""
    client = APIClient(); client.force_authenticate(maker)
    leave_id = _apply(client, approver, MONDAY, FRI).json()["id"]
    APIClient();
    dh = APIClient(); dh.force_authenticate(checker)
    dh.post(f"/api/v1/leaves/{leave_id}/dept-head-review/", {"decision": "approve"}, format="json")
    hr = APIClient(); hr.force_authenticate(approver)
    hr.post(f"/api/v1/leaves/{leave_id}/hr-review/", {"decision": "approve"}, format="json")
    assert _balance(maker) == 5

    # Employee cancels the approved leave -> soft-deleted, balance refunded.
    r = client.delete(f"/api/v1/leaves/{leave_id}/")
    assert r.status_code in (200, 204), r.content
    assert _balance(maker) == 0
