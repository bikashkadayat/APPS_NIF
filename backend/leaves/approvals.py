"""Single source of truth for 'who must act' on a PENDING leave.

Both the notification layer (who is told "awaiting your review") and the pending
queue / count (what an approver can act on) derive from this module, so they can
never disagree. Mirrors the grant permission in views.dept_head_review:
  - Dept Head(s) of the applicant's department are the actionable approvers.
  - If that department has no active Dept Head, HR are the fallback grantors.
  - Admin is an oversight role and may act on any pending leave.

Department is resolved by the structured `department_ref` when set, else by the
legacy free-text `department` string (backward compatible with old data).
"""
from django.db.models import Exists, OuterRef, Q

from users.models import User
from .models import Leave


def _heads_for_applicant(applicant):
    """Active Dept Heads (checkers) for the applicant's department — by structured
    ref if present, else the legacy string. Empty if the department has no head."""
    heads = User.objects.filter(role=User.Roles.CHECKER, is_active=True).exclude(id=applicant.id)
    if applicant.department_ref_id:
        return heads.filter(department_ref_id=applicant.department_ref_id)
    if applicant.department:
        return heads.filter(department__iexact=applicant.department)
    return heads.none()


def actionable_approver_ids(leave):
    """User ids who must ACT on this PENDING leave — the exact set notified as
    'awaiting your review'. Dept Head(s) of the applicant's department, or HR when
    the department has no active Dept Head."""
    if leave.status != Leave.Status.PENDING or getattr(leave, "is_deleted", False):
        return set()
    heads = _heads_for_applicant(leave.user)
    if heads.exists():
        return set(heads.values_list("id", flat=True))
    # No Dept Head for this department (or no department) -> HR fallback grantors.
    return set(User.objects.filter(role=User.Roles.APPROVER, is_active=True)
               .exclude(id=leave.user_id).values_list("id", flat=True))


def pending_actionable_leaves(user):
    """PENDING leaves `user` can act on — the queryset mirror of
    actionable_approver_ids (drives the pending list + count). A superset is
    acceptable (Admin oversight); the invariant is: anyone notified 'awaiting your
    review' for a leave finds that leave here."""
    base = Leave.objects.filter(status=Leave.Status.PENDING, is_deleted=False).exclude(user=user)
    role = user.role
    if role == User.Roles.ADMIN:
        return base  # oversight: may act on any pending leave
    if role == User.Roles.CHECKER:
        # Dept Head: pending leaves from their own department (ref, else string).
        if user.department_ref_id:
            return base.filter(user__department_ref_id=user.department_ref_id)
        if user.department:
            return base.filter(user__department__iexact=user.department)
        return base.none()
    if role == User.Roles.APPROVER:
        # HR: only leaves whose department has NO active Dept Head (fallback path).
        head_ref = User.objects.filter(
            role=User.Roles.CHECKER, is_active=True,
            department_ref_id=OuterRef("user__department_ref_id"))
        head_str = User.objects.filter(
            role=User.Roles.CHECKER, is_active=True,
            department__iexact=OuterRef("user__department"))
        base = base.annotate(_has_ref=Exists(head_ref), _has_str=Exists(head_str))
        covered = (Q(user__department_ref_id__isnull=False) & Q(_has_ref=True)) | \
                  (Q(user__department_ref_id__isnull=True) & Q(_has_str=True))
        return base.exclude(covered)
    return base.none()
