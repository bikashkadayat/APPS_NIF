"""
Business logic for the memo approval workflow.

Views stay thin and delegate every state transition to the functions here.
Design rules (enterprise conventions):
  * Each mutating transition runs inside a single @transaction.atomic block.
  * The memo row is re-read with select_for_update() so two concurrent actors
    cannot both act on the same memo and corrupt its state.
  * A guard failure raises rest_framework ValidationError with a clear message.
  * State is never mutated without also writing a MemoApprovalStep and an
    AuditLog entry - the two together give a complete, immutable history.
"""
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from audit.models import AuditLog
from audit.services import log_action
from .models import Memo, MemoApprovalStep

logger = logging.getLogger("memos")
User = get_user_model()

MIN_COMMENT_LENGTH = 10

# Short codes embedded in generated memo numbers, per memo type.
MEMO_TYPE_CODES = {
    Memo.MemoType.INTERNAL: "INT",
    Memo.MemoType.EXTERNAL: "EXT",
    Memo.MemoType.FINANCIAL: "FIN",
    Memo.MemoType.HR: "HR",
    Memo.MemoType.GENERAL: "GEN",
}

# Memo types / priorities that must be escalated to a senior approver.
ESCALATION_MEMO_TYPES = {Memo.MemoType.FINANCIAL}
ESCALATION_PRIORITIES = {Memo.Priority.URGENT}


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------
def create_audit_log(actor, action, instance=None, metadata=None, request=None):
    """
    Central audit helper for the memo module.

    The AuditLog table already exists (audit app), so rather than the Phase-3
    logger stub we write a real immutable row via audit.services.log_action -
    a strict superset of the spec. We also emit a logger line for local trace.
    """
    logger.info("audit action=%s actor=%s target=%s", action, getattr(actor, "id", None), instance)
    log_action(actor, action, instance=instance, changes=metadata or {}, request=request)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _next_step_order(memo):
    last = memo.approval_steps.order_by("-step_order").first()
    return (last.step_order + 1) if last else 1


def _record_step(memo, actor, action, comment=""):
    return MemoApprovalStep.objects.create(
        memo=memo,
        step_order=_next_step_order(memo),
        actor=actor,
        action=action,
        comment=comment or "",
    )


def _require_comment(comment):
    comment = (comment or "").strip()
    if len(comment) < MIN_COMMENT_LENGTH:
        raise ValidationError(
            f"A comment of at least {MIN_COMMENT_LENGTH} characters is required."
        )
    return comment


def _lock(memo):
    """Re-read the memo under a row lock to serialize concurrent transitions."""
    return Memo.objects.select_for_update().get(pk=memo.pk)


def _notify_memo(recipient, category, title, body, memo):
    """Send a memo notification (best-effort; never breaks the transition)."""
    if recipient is None:
        return
    try:
        from notifications.dispatcher import notify
        notify(recipient, category, title, body, action_url=f"/memos/{memo.id}")
    except Exception:  # noqa: BLE001 - notifications must not fail the workflow
        logger.warning("memo notification failed", exc_info=True)


# ---------------------------------------------------------------------------
# Numbering
# ---------------------------------------------------------------------------
@transaction.atomic
def generate_memo_number(memo_type):
    """
    Return the next memo number in the form NIFN-{TYPE_CODE}-{YYYY}-{XXXX}
    (e.g. NIFN-HR-2026-0042). The sequence resets each calendar year and is
    scoped per type code.

    Numbers are handed out by an authoritative per-(type, year) counter row
    (MemoNumberSequence). We ensure the row exists, then lock it with
    select_for_update() and increment - so concurrent creations serialize on
    the lock instead of racing on a "max existing number" read (H4). The
    integer counter also removes the previous lexical-sort bug beyond 9999.
    """
    from .models import MemoNumberSequence

    type_code = MEMO_TYPE_CODES.get(memo_type, "GEN")
    year = timezone.now().year

    # get_or_create is safe under the unique constraint if two creators race to
    # create the first row of the year; the loser retries the get.
    MemoNumberSequence.objects.get_or_create(type_code=type_code, year=year)
    seq = MemoNumberSequence.objects.select_for_update().get(
        type_code=type_code, year=year
    )
    seq.last_value += 1
    seq.save(update_fields=["last_value"])
    return f"NIFN-{type_code}-{year}-{seq.last_value:04d}"


# ---------------------------------------------------------------------------
# Routing resolution
# ---------------------------------------------------------------------------
def _department_config(department):
    """
    Look up the per-department approval config added in Phase 4.
    Returns None gracefully until that model exists.
    """
    try:
        from .models import DepartmentApprovalConfig  # noqa: WPS433 (Phase 4)
    except ImportError:
        return None
    if not department:
        return None
    return DepartmentApprovalConfig.objects.filter(department=department).first()


def resolve_next_reviewer(memo):
    """
    Pick the Checker who should review this memo:
      1. the department's configured checker (Phase 4 DepartmentApprovalConfig),
      2. else any active checker in the maker's department,
      3. else any active checker.
    Returns a User or None.
    """
    department = getattr(memo.created_by, "department", None)

    config = _department_config(department)
    if config is not None and getattr(config, "checker_id", None):
        return config.checker

    checkers = User.objects.filter(
        role=User.Roles.CHECKER, is_active=True
    ).order_by("date_joined", "id")
    if department:
        dept_checker = checkers.filter(department=department).first()
        if dept_checker:
            return dept_checker
    return checkers.first()


def resolve_next_approver(memo):
    """
    Pick the Approver for this memo. Financial memos and urgent-priority memos
    are escalated to a senior approver (an admin acting as approver) when one is
    available. Returns a User or None.
    """
    department = getattr(memo.created_by, "department", None)

    config = _department_config(department)
    if config is not None and getattr(config, "approver_id", None):
        return config.approver

    escalate = (
        memo.memo_type in ESCALATION_MEMO_TYPES
        or memo.priority in ESCALATION_PRIORITIES
    )
    if escalate:
        # M4: deterministic pick (oldest admin, id tie-break) so escalation
        # routing is reproducible rather than depending on default ordering.
        senior = User.objects.filter(
            role=User.Roles.ADMIN, is_active=True
        ).order_by("date_joined", "id").first()
        if senior:
            return senior

    approvers = User.objects.filter(
        role=User.Roles.APPROVER, is_active=True
    ).order_by("date_joined", "id")
    if department:
        dept_approver = approvers.filter(department=department).first()
        if dept_approver:
            return dept_approver
    return approvers.first()


# ---------------------------------------------------------------------------
# Workflow transitions
# ---------------------------------------------------------------------------
def _resolve_manual_assignee(user_id, allowed_roles, actor, kind):
    """
    Validate a manually-picked checker/approver for hybrid assignment.
    Rules: must exist, be active, hold an allowed role, and not be the actor.
    Raises ValidationError (-> HTTP 400) on any violation.
    """
    target = User.objects.filter(pk=user_id).first()
    if target is None:
        raise ValidationError({f"{kind}_id": f"Selected {kind} does not exist."})
    if not target.is_active:
        raise ValidationError({f"{kind}_id": f"Selected {kind} is inactive."})
    if target.role not in allowed_roles:
        raise ValidationError({f"{kind}_id": f"Selected user is not a valid {kind}."})
    if target.id == actor.id:
        raise ValidationError({f"{kind}_id": f"You cannot assign yourself as the {kind}."})
    return target


@transaction.atomic
def submit_memo(memo, actor, override_reviewer_id=None, request=None):
    memo = _lock(memo)
    if memo.status != Memo.Status.DRAFT:
        raise ValidationError("Only draft memos can be submitted.")
    if memo.created_by_id != actor.id:
        raise ValidationError("Only the author can submit this memo.")

    # Hybrid assignment: use the maker's chosen checker when provided, else
    # auto-resolve by department config (existing default behavior).
    if override_reviewer_id:
        reviewer = _resolve_manual_assignee(
            override_reviewer_id, [User.Roles.CHECKER, User.Roles.ADMIN], actor, "checker")
    else:
        reviewer = resolve_next_reviewer(memo)
    if reviewer is None:
        raise ValidationError("No active checker is available to review this memo.")

    memo.status = Memo.Status.SUBMITTED
    memo.submitted_at = timezone.now()
    memo.current_reviewer = reviewer
    memo.save(update_fields=["status", "submitted_at", "current_reviewer", "updated_at"])

    _record_step(memo, actor, MemoApprovalStep.Action.SUBMITTED)
    create_audit_log(
        actor, AuditLog.Action.SUBMIT, instance=memo,
        metadata={"reviewer": str(reviewer.id)}, request=request,
    )
    _notify_memo(reviewer, "MEMO_ASSIGNED_TO_REVIEW",
                 f"Memo {memo.memo_number} needs your review", memo.title, memo)
    return memo


def _is_admin(actor):
    return getattr(actor, "role", None) == User.Roles.ADMIN


def _override_meta(is_override, transition):
    """Audit metadata that records when an admin acted outside their assignment."""
    if is_override:
        return {"transition": f"{transition}_admin_override", "admin_override": True}
    return {"transition": transition}


@transaction.atomic
def review_memo(memo, actor, comment="", override_approver_id=None, request=None):
    memo = _lock(memo)
    if memo.status != Memo.Status.SUBMITTED:
        raise ValidationError("Only submitted memos can be reviewed.")
    # H1: the assigned reviewer OR an admin may act; admin acting on a memo not
    # assigned to them is an override and is flagged in the audit trail.
    admin_override = _is_admin(actor) and memo.current_reviewer_id != actor.id
    if memo.current_reviewer_id != actor.id and not _is_admin(actor):
        raise ValidationError("Only the assigned reviewer can review this memo.")

    # Hybrid assignment: checker may pick the approver, else auto-resolve.
    if override_approver_id:
        approver = _resolve_manual_assignee(
            override_approver_id, [User.Roles.APPROVER, User.Roles.ADMIN], actor, "approver")
    else:
        approver = resolve_next_approver(memo)
    if approver is None:
        raise ValidationError("No active approver is available for this memo.")

    memo.status = Memo.Status.UNDER_REVIEW
    memo.current_approver = approver
    memo.save(update_fields=["status", "current_approver", "updated_at"])

    _record_step(memo, actor, MemoApprovalStep.Action.REVIEWED, comment=comment)
    create_audit_log(
        actor, AuditLog.Action.UPDATE, instance=memo,
        metadata={**_override_meta(admin_override, "reviewed"), "approver": str(approver.id)},
        request=request,
    )
    _notify_memo(approver, "MEMO_ASSIGNED_TO_REVIEW",
                 f"Memo {memo.memo_number} needs your approval", memo.title, memo)
    _notify_memo(memo.created_by, "MEMO_ASSIGNED_TO_REVIEW",
                 f"Memo {memo.memo_number} advanced to approval", memo.title, memo)
    return memo


@transaction.atomic
def approve_memo(memo, actor, comment="", request=None):
    memo = _lock(memo)
    if memo.status != Memo.Status.UNDER_REVIEW:
        raise ValidationError("Only memos under review can be approved.")
    # H1: the assigned approver OR an admin may act (admin acts = override).
    admin_override = _is_admin(actor) and memo.current_approver_id != actor.id
    if memo.current_approver_id != actor.id and not _is_admin(actor):
        raise ValidationError("Only the assigned approver can approve this memo.")

    memo.status = Memo.Status.APPROVED
    memo.finalized_at = timezone.now()
    memo.save(update_fields=["status", "finalized_at", "updated_at"])

    _record_step(memo, actor, MemoApprovalStep.Action.APPROVED, comment=comment)
    create_audit_log(
        actor, AuditLog.Action.APPROVE, instance=memo,
        metadata=_override_meta(admin_override, "approved"), request=request,
    )
    _notify_memo(memo.created_by, "MEMO_APPROVED",
                 f"Memo {memo.memo_number} was approved", memo.title, memo)
    return memo


@transaction.atomic
def reject_memo(memo, actor, comment, request=None):
    comment = _require_comment(comment)
    memo = _lock(memo)
    if memo.status not in (Memo.Status.SUBMITTED, Memo.Status.UNDER_REVIEW):
        raise ValidationError("Only submitted or under-review memos can be rejected.")

    is_reviewer = memo.current_reviewer_id == actor.id and memo.status == Memo.Status.SUBMITTED
    is_approver = memo.current_approver_id == actor.id and memo.status == Memo.Status.UNDER_REVIEW
    # H1: an admin may reject any submitted/under-review memo (override).
    admin_override = _is_admin(actor) and not (is_reviewer or is_approver)
    if not (is_reviewer or is_approver or _is_admin(actor)):
        raise ValidationError("Only the assigned reviewer or approver can reject this memo.")

    memo.status = Memo.Status.REJECTED
    memo.finalized_at = timezone.now()
    memo.save(update_fields=["status", "finalized_at", "updated_at"])

    _record_step(memo, actor, MemoApprovalStep.Action.REJECTED, comment=comment)
    create_audit_log(
        actor, AuditLog.Action.REJECT, instance=memo,
        metadata={**_override_meta(admin_override, "rejected"), "comment": comment}, request=request,
    )
    _notify_memo(memo.created_by, "MEMO_REJECTED",
                 f"Memo {memo.memo_number} was rejected", comment or memo.title, memo)
    return memo


@transaction.atomic
def return_memo(memo, actor, comment, request=None):
    """Checker sends the memo back to the maker for revision."""
    comment = _require_comment(comment)
    memo = _lock(memo)
    if memo.status != Memo.Status.SUBMITTED:
        raise ValidationError("Only submitted memos can be returned.")
    if memo.current_reviewer_id != actor.id:
        raise ValidationError("Only the assigned reviewer can return this memo.")

    memo.status = Memo.Status.DRAFT
    memo.current_reviewer = None
    memo.submitted_at = None
    memo.save(update_fields=["status", "current_reviewer", "submitted_at", "updated_at"])

    _record_step(memo, actor, MemoApprovalStep.Action.RETURNED, comment=comment)
    create_audit_log(
        actor, AuditLog.Action.UPDATE, instance=memo,
        metadata={"transition": "returned", "comment": comment}, request=request,
    )
    _notify_memo(memo.created_by, "MEMO_RETURNED",
                 f"Memo {memo.memo_number} was returned for revision", comment or memo.title, memo)
    return memo


@transaction.atomic
def cancel_memo(memo, actor, comment="", request=None):
    """Maker cancels their own memo while it is still draft or submitted."""
    memo = _lock(memo)
    if memo.created_by_id != actor.id:
        raise ValidationError("Only the author can cancel this memo.")
    if memo.status not in (Memo.Status.DRAFT, Memo.Status.SUBMITTED):
        raise ValidationError("Only draft or submitted memos can be cancelled.")

    memo.status = Memo.Status.CANCELLED
    memo.current_reviewer = None
    memo.current_approver = None
    memo.finalized_at = timezone.now()
    memo.save(update_fields=[
        "status", "current_reviewer", "current_approver", "finalized_at", "updated_at",
    ])

    _record_step(memo, actor, MemoApprovalStep.Action.CANCELLED, comment=comment)
    create_audit_log(
        actor, AuditLog.Action.UPDATE, instance=memo,
        metadata={"transition": "cancelled"}, request=request,
    )
    return memo
