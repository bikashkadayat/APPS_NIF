"""
Leave-workflow notification triggers (in-app + email).

Recipients are resolved dynamically from the applicant's department (Dept Head)
and the HR pool — never hardcoded — and every address is the user's account
(login) email. Every send is best-effort and idempotency-keyed: a notification
failure can NEVER break apply / approve / reject, and a transition can't send the
same email twice.

Trigger map (see the four public functions):
  1. leave_submitted   - new request  -> Dept Head(s) [+ HR CC]
  2. leave_l1_approved - Dept Head OK  -> HR [+ employee "stage 1 passed"]
  3. leave_finalized   - HR decision   -> employee [+ audit copy]
  4. leave_rejected_l1 - Dept Head NO  -> employee (reason mandatory)
"""
import logging

from django.conf import settings

from config.nepali_dates import to_bs
from notifications.dispatcher import notify
from notifications.models import Category
from users.models import User
from . import services
from .models import Leave

logger = logging.getLogger("leaves.notifications")

# status_key -> (accent color, badge label)
_STATUS_META = {
    "submitted": ("#F59E0B", "Awaiting Review"),
    "pending_hr": ("#F59E0B", "Awaiting HR"),
    "approved": ("#10B981", "Approved"),
    "rejected": ("#DC2626", "Rejected"),
}


def _safe(label, fn):
    try:
        fn()
    except Exception:  # noqa: BLE001 - notifications must never break the workflow
        logger.exception("leave notification failed (%s)", label)


def _bs(value):
    return to_bs(value) or "—"


def _dept_heads(applicant):
    """Active Department Heads (checkers) in the applicant's department; falls
    back to all Dept Heads if none are assigned to that department."""
    qs = User.objects.filter(role=User.Roles.CHECKER, is_active=True).exclude(id=applicant.id)
    if applicant.department_ref_id:
        scoped = qs.filter(department_ref_id=applicant.department_ref_id)
        if scoped.exists():
            return list(scoped)
    elif applicant.department:
        scoped = qs.filter(department__iexact=applicant.department)
        if scoped.exists():
            return list(scoped)
    return list(qs)


def _hr_users(exclude=None):
    qs = User.objects.filter(role=User.Roles.APPROVER, is_active=True)
    if exclude is not None:
        qs = qs.exclude(id=exclude.id)
    return list(qs)


def _actor_line(actor, when):
    if not actor:
        return ""
    name = actor.get_full_name() or actor.username
    if when:
        return f"{name} on {_bs(when)} BS / {when.date()}"
    return name


def _detail_ctx(leave, status_key, actor_line="", remarks=""):
    color, label = _STATUS_META.get(status_key, ("#2563EB", ""))
    days = services.working_leave_days(leave)
    ctx = {
        "status_color": color, "status_label": label,
        "employee_name": leave.user.get_full_name() or leave.user.username,
        "department": leave.user.department_name or "",
        "leave_type": leave.get_leave_type_display(),
        "start_ad": str(leave.start_date), "start_bs": _bs(leave.start_date),
        "end_ad": str(leave.end_date), "end_bs": _bs(leave.end_date),
        "working_days": days,
        "reason": leave.reason or "",
        "actor_line": actor_line, "remarks": remarks or "",
    }
    return ctx, days


# ---------------------------------------------------------------------------
# Trigger 1 — new request submitted
# ---------------------------------------------------------------------------
def leave_submitted(leave):
    ctx, days = _detail_ctx(leave, "submitted")
    emp, ltype = ctx["employee_name"], ctx["leave_type"]
    title = f"New Leave Request — {emp} ({ltype})"
    body = f"{emp} submitted a {ltype} request for {days} working day(s), awaiting your review."

    for head in _dept_heads(leave.user):
        _safe(f"submitted->head:{head.id}", lambda head=head: notify(
            head, Category.LEAVE_SUBMITTED, title, body, action_url="/leave/pending",
            idempotency_key=f"leave-{leave.id}-submitted-head-{head.id}",
            email_context=ctx, object_id=leave.id,
        ))

    if getattr(settings, "NOTIFY_CC_HR_ON_SUBMIT", True):
        for hr in _hr_users():
            _safe(f"submitted->hrcc:{hr.id}", lambda hr=hr: notify(
                hr, Category.LEAVE_SUBMITTED, f"{title} (CC)",
                body + " You are copied for visibility.", action_url="/leave/pending",
                idempotency_key=f"leave-{leave.id}-submitted-hrcc-{hr.id}",
                email_context=ctx, object_id=leave.id,
            ))


# ---------------------------------------------------------------------------
# Trigger 2 — Dept Head approved (L1) -> pending HR
# ---------------------------------------------------------------------------
def leave_l1_approved(leave):
    actor_line = _actor_line(leave.department_head_reviewer, leave.department_head_action_date)
    ctx, days = _detail_ctx(leave, "pending_hr", actor_line=actor_line, remarks=leave.remarks or "")
    emp, ltype = ctx["employee_name"], ctx["leave_type"]

    title = "Action Required — Leave Request Awaiting Your Approval"
    body = f"{emp}'s {ltype} request ({days} working day(s)) was approved by the Department Head and awaits your final approval."
    for hr in _hr_users():
        _safe(f"l1->hr:{hr.id}", lambda hr=hr: notify(
            hr, Category.LEAVE_SUBMITTED, title, body, action_url="/leave/pending",
            idempotency_key=f"leave-{leave.id}-l1-hr-{hr.id}",
            email_context=ctx, object_id=leave.id,
        ))

    if getattr(settings, "NOTIFY_EMPLOYEE_ON_L1", True):
        _safe("l1->emp", lambda: notify(
            leave.user, Category.LEAVE_SUBMITTED, "Leave Update — Stage 1 Approved",
            "Your leave request passed Stage 1 (Department Head) and now awaits HR's final decision.",
            action_url="/leave/my-applications",
            idempotency_key=f"leave-{leave.id}-l1-emp",
            email_context=ctx, object_id=leave.id,
        ))


# ---------------------------------------------------------------------------
# Trigger 3 — HR final decision (approved / rejected)
# ---------------------------------------------------------------------------
def leave_finalized(leave):
    approved = leave.status == Leave.Status.APPROVED
    status_key = "approved" if approved else "rejected"
    actor = leave.hr_reviewer or leave.approver
    actor_line = _actor_line(actor, leave.hr_action_date)
    ctx, days = _detail_ctx(leave, status_key, actor_line=actor_line, remarks=leave.remarks or "")
    dates = f"{ctx['start_ad']} to {ctx['end_ad']}"

    if approved:
        title, cat = f"Leave Approved — {dates}", Category.LEAVE_APPROVED
        body = f"Your {ctx['leave_type']} ({days} working day(s)) has been approved."
    else:
        title, cat = f"Leave Rejected — {dates}", Category.LEAVE_REJECTED
        body = f"Your {ctx['leave_type']} request has been rejected."

    _safe("final->emp", lambda: notify(
        leave.user, cat, title, body, action_url="/leave/my-applications",
        idempotency_key=f"leave-{leave.id}-final-{status_key}",
        email_context=ctx, object_id=leave.id,
    ))

    if getattr(settings, "NOTIFY_AUDIT_COPY_ON_FINAL", False):
        audience = _dept_heads(leave.user) + _hr_users()
        for u in audience:
            _safe(f"final->audit:{u.id}", lambda u=u: notify(
                u, cat, f"{title} (audit copy)",
                f"{ctx['employee_name']}'s {ctx['leave_type']} was {status_key}.",
                action_url="/leave/pending",
                idempotency_key=f"leave-{leave.id}-final-{status_key}-audit-{u.id}",
                email_context=ctx, object_id=leave.id,
            ))


# ---------------------------------------------------------------------------
# Trigger 4 — Dept Head rejected at L1
# ---------------------------------------------------------------------------
def leave_rejected_l1(leave):
    actor_line = _actor_line(leave.department_head_reviewer, leave.department_head_action_date)
    ctx, days = _detail_ctx(leave, "rejected", actor_line=actor_line, remarks=leave.remarks or "")
    dates = f"{ctx['start_ad']} to {ctx['end_ad']}"
    _safe("l1reject->emp", lambda: notify(
        leave.user, Category.LEAVE_REJECTED, f"Leave Rejected — {dates}",
        "Your leave request was rejected by the Department Head. See the remarks for details.",
        action_url="/leave/my-applications",
        # Shares the 'final-rejected' key so a rejection is only ever emailed once.
        idempotency_key=f"leave-{leave.id}-final-rejected",
        email_context=ctx, object_id=leave.id,
    ))
