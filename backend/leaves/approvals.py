"""Single source of truth for 'who must act' on a PENDING leave.

Both the notification layer (who is told "awaiting your review") and the pending
queue / count (what an approver can act on) derive from this module, so they can
never disagree.

Routing order — the employee's choice comes FIRST:
  1. The reporting manager the employee SELECTED on the application (Leave.approver)
     is the primary approver. Honoured whenever that person can still act
     (active + an approving role + not the applicant themselves).
  2. Fallback, when no manager was selected or the selected one can no longer act:
     the active Dept Head(s) of the applicant's department.
  3. Final fallback, when that department has no active Dept Head: HR.
  Admin is an oversight role and may act on any pending leave, but is never the
  *routing target* — a request is never silently handed to Admin alone.

Department is resolved by the structured `department_ref` when set, else by the
legacy free-text `department` string (backward compatible with old data).
"""
from django.db.models import Exists, OuterRef, Q

from users.models import User
from .models import Leave

# Roles an employee may legitimately pick as their reporting manager. Mirrors the
# validation in views.LeaveViewSet.perform_create.
SELECTABLE_APPROVER_ROLES = (User.Roles.CHECKER, User.Roles.APPROVER, User.Roles.ADMIN)


def _heads_for_applicant(applicant):
    """Active Dept Heads (checkers) for the applicant's department — by structured
    ref if present, else the legacy string. Empty if the department has no head."""
    heads = User.objects.filter(role=User.Roles.CHECKER, is_active=True).exclude(id=applicant.id)
    if applicant.department_ref_id:
        return heads.filter(department_ref_id=applicant.department_ref_id)
    if applicant.department:
        return heads.filter(department__iexact=applicant.department)
    return heads.none()


def selection_is_actionable(leave):
    """True when the manager the employee picked can actually act on this leave."""
    a = leave.approver
    return bool(
        a
        and a.is_active
        and a.role in SELECTABLE_APPROVER_ROLES
        and a.id != leave.user_id
    )


def _selection_ok_subquery():
    """Queryset mirror of selection_is_actionable().

    Expressed as EXISTS rather than a join + negated Q: a negated multi-table Q
    over a nullable FK is where Django/SQL three-valued logic silently drops rows.
    """
    return Exists(
        User.objects.filter(
            pk=OuterRef("approver_id"),
            is_active=True,
            role__in=SELECTABLE_APPROVER_ROLES,
        ).exclude(pk=OuterRef("user_id"))
    )


def _hr_ids(leave_user_id):
    return set(User.objects.filter(role=User.Roles.APPROVER, is_active=True)
               .exclude(id=leave_user_id).values_list("id", flat=True))


def actionable_approver_ids(leave):
    """User ids who must ACT on this PENDING leave — the exact set notified as
    'awaiting your review'. The employee's selected reporting manager wins; the
    department head / HR chain is only a fallback."""
    if leave.status != Leave.Status.PENDING or getattr(leave, "is_deleted", False):
        return set()
    # 1. The manager the employee chose is the primary approver.
    if selection_is_actionable(leave):
        return {leave.approver_id}
    # 2. No usable selection -> Dept Head(s) of the applicant's department.
    heads = _heads_for_applicant(leave.user)
    if heads.exists():
        return set(heads.values_list("id", flat=True))
    # 3. Department has no active Dept Head -> HR are the fallback grantors.
    return _hr_ids(leave.user_id)


def pending_actionable_leaves(user):
    """PENDING leaves `user` can act on — the queryset mirror of
    actionable_approver_ids (drives the pending list + count). A superset is
    acceptable (Admin oversight); the invariant is: anyone notified 'awaiting your
    review' for a leave finds that leave here."""
    base = (Leave.objects.filter(status=Leave.Status.PENDING, is_deleted=False)
            .exclude(user=user)
            .annotate(_selection_ok=_selection_ok_subquery()))
    role = user.role

    if role == User.Roles.ADMIN:
        return base  # oversight: may act on any pending leave

    # Leaves this user was explicitly PICKED for (step 1) — applies to every
    # approving role, so a Dept Head chosen from another department still gets it.
    chosen = Q(approver_id=user.id) & Q(_selection_ok=True)
    # Fallback rules only apply when the selection cannot be honoured.
    unrouted = Q(_selection_ok=False)

    if role == User.Roles.CHECKER:
        # Dept Head: their own department's pending leaves (step 2).
        if user.department_ref_id:
            dept = Q(user__department_ref_id=user.department_ref_id)
        elif user.department:
            dept = Q(user__department__iexact=user.department)
        else:
            # No department -> no departmental claim at all. (Filtering on a None
            # department_ref would match every unscoped applicant.)
            return base.filter(chosen)
        return base.filter(chosen | (unrouted & dept))

    if role == User.Roles.APPROVER:
        # HR: leaves picked for them, plus (step 3) leaves whose department has NO
        # active Dept Head and which nobody was picked for.
        head_ref = User.objects.filter(
            role=User.Roles.CHECKER, is_active=True,
            department_ref_id=OuterRef("user__department_ref_id"))
        head_str = User.objects.filter(
            role=User.Roles.CHECKER, is_active=True,
            department__iexact=OuterRef("user__department"))
        base = base.annotate(_has_ref=Exists(head_ref), _has_str=Exists(head_str))
        covered = (Q(user__department_ref_id__isnull=False) & Q(_has_ref=True)) | \
                  (Q(user__department_ref_id__isnull=True) & Q(_has_str=True))
        return base.filter(chosen | (unrouted & ~covered))

    return base.none()
