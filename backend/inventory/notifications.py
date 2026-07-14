"""Take-out workflow notifications — reuses the shared dispatcher + generic email
template. Best-effort: a notification failure can never break the API action."""
import logging

from config.nepali_dates import to_bs
from notifications.dispatcher import notify
from notifications.models import Category
from users.models import User

logger = logging.getLogger("inventory.notifications")


def _safe(label, fn):
    try:
        fn()
    except Exception:  # noqa: BLE001 - notifications must never break the workflow
        logger.exception("inventory notification failed (%s)", label)


def _managers_for(requester):
    """Approvers for a take-out: the requester's Dept Head(s) + all HR + all Admin
    (deduped, excluding the requester)."""
    # Only Dept Head(s) of the requester's OWN department (they can actually approve
    # it — the take-out queue scopes a Dept Head to their department). Do NOT fall
    # back to all Dept Heads: HR + Admin below already cover a headless department,
    # and notifying out-of-department heads who cannot act was the bug.
    heads = User.objects.filter(role=User.Roles.CHECKER, is_active=True)
    dept_id = getattr(requester, "department_ref_id", None)
    heads = heads.filter(department_ref_id=dept_id) if dept_id else heads.none()
    hr = User.objects.filter(role=User.Roles.APPROVER, is_active=True)
    admin = User.objects.filter(role=User.Roles.ADMIN, is_active=True)
    seen, out = set(), []
    for u in list(heads) + list(hr) + list(admin):
        if u.id != getattr(requester, "id", None) and u.id not in seen:
            seen.add(u.id)
            out.append(u)
    return out


def _ctx(req):
    return {
        "reference": req.reference,
        "item": f"{req.item_code} · {req.item_name}",
        "employee_name": req.requested_by_name,
        "purpose": req.get_purpose_display(),
        "out_ad": str(req.expected_out_date), "out_bs": to_bs(req.expected_out_date) or "—",
        "return_ad": str(req.expected_return_date), "return_bs": to_bs(req.expected_return_date) or "—",
        "reason": req.reason or "",
        "remarks": req.approver_remarks or "",
    }


def takeout_submitted(req):
    ctx = _ctx(req)
    title = f"Take-Out Request — {req.item_name} ({req.requested_by_name})"
    body = (f"{req.requested_by_name} requested to take '{req.item_name}' "
            f"({req.get_purpose_display()}) from {ctx['out_ad']} to {ctx['return_ad']}. Awaiting your approval.")
    for m in _managers_for(req.requested_by):
        _safe(f"submitted->{m.id}", lambda m=m: notify(
            m, Category.INVENTORY_TAKEOUT_REQUESTED, title, body,
            action_url="/inventory/approvals",
            idempotency_key=f"takeout-{req.id}-submitted-{m.id}",
            email_context=ctx, object_id=str(req.id)))


def takeout_finalized(req):
    """Approve/reject → notify the requester."""
    approved = req.status == req.Status.APPROVED
    ctx = _ctx(req)
    if approved:
        cat = Category.INVENTORY_TAKEOUT_APPROVED
        title = f"Take-Out Approved — {req.item_name}"
        body = (f"Your request to take '{req.item_name}' was approved by {req.approver_name}. "
                f"Reference {req.reference}. Please collect the gate pass.")
    else:
        cat = Category.INVENTORY_TAKEOUT_REJECTED
        title = f"Take-Out Rejected — {req.item_name}"
        body = f"Your request to take '{req.item_name}' was rejected. Reason: {req.approver_remarks}"
    _safe("finalized->requester", lambda: notify(
        req.requested_by, cat, title, body,
        action_url="/inventory/my-requests",
        idempotency_key=f"takeout-{req.id}-{req.status}",
        email_context=ctx, object_id=str(req.id)))
