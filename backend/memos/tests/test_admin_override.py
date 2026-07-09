"""H1: admin may act on any memo (override), and the override is audited."""
import pytest

from audit.models import AuditLog
from memos.models import Memo
from memos.services import generate_memo_number
from users.models import User


def _memo(created_by, status, reviewer=None, approver=None):
    return Memo.objects.create(
        title="T", subject="S", body="<p>b</p>",
        memo_type=Memo.MemoType.GENERAL, status=status, created_by=created_by,
        memo_number=generate_memo_number(Memo.MemoType.GENERAL),
        current_reviewer=reviewer, current_approver=approver,
    )


@pytest.mark.django_db
def test_admin_can_review_any_memo(api, maker, checker, other_checker, approver, admin):
    # Memo assigned to `checker`, but `admin` (not the assignee) reviews it.
    memo = _memo(maker, Memo.Status.SUBMITTED, reviewer=checker)
    api.force_authenticate(admin)
    resp = api.post(f"/api/v1/memos/{memo.id}/review/",
                    {"action": "reviewed", "comment": "admin steps in"}, format="json")
    assert resp.status_code == 200, resp.data
    memo.refresh_from_db()
    assert memo.status == Memo.Status.UNDER_REVIEW


@pytest.mark.django_db
def test_admin_can_approve_any_memo(api, maker, approver, admin):
    memo = _memo(maker, Memo.Status.UNDER_REVIEW, approver=approver)
    api.force_authenticate(admin)
    resp = api.post(f"/api/v1/memos/{memo.id}/approve/",
                    {"action": "approved", "comment": "admin approves"}, format="json")
    assert resp.status_code == 200, resp.data
    memo.refresh_from_db()
    assert memo.status == Memo.Status.APPROVED


@pytest.mark.django_db
def test_admin_can_reject_any_memo(api, maker, approver, admin):
    memo = _memo(maker, Memo.Status.UNDER_REVIEW, approver=approver)
    api.force_authenticate(admin)
    resp = api.post(f"/api/v1/memos/{memo.id}/reject/",
                    {"action": "rejected", "comment": "not acceptable at all"}, format="json")
    assert resp.status_code == 200, resp.data
    memo.refresh_from_db()
    assert memo.status == Memo.Status.REJECTED


@pytest.mark.django_db
def test_admin_override_writes_audit_log(api, maker, approver, admin):
    memo = _memo(maker, Memo.Status.UNDER_REVIEW, approver=approver)
    api.force_authenticate(admin)
    api.post(f"/api/v1/memos/{memo.id}/approve/",
             {"action": "approved", "comment": "admin approves"}, format="json")
    log = AuditLog.objects.filter(object_id=str(memo.id), actor=admin,
                                  action=AuditLog.Action.APPROVE).first()
    assert log is not None
    assert log.changes.get("admin_override") is True
    assert log.changes.get("transition") == "approved_admin_override"


@pytest.mark.django_db
def test_assigned_approver_is_not_flagged_as_override(api, maker, approver):
    # Sanity: the normal (assigned) path is NOT marked as an override.
    memo = _memo(maker, Memo.Status.UNDER_REVIEW, approver=approver)
    api.force_authenticate(approver)
    api.post(f"/api/v1/memos/{memo.id}/approve/",
             {"action": "approved", "comment": "ok"}, format="json")
    log = AuditLog.objects.filter(object_id=str(memo.id), actor=approver,
                                  action=AuditLog.Action.APPROVE).first()
    assert log.changes.get("admin_override") is None
    assert log.changes.get("transition") == "approved"
