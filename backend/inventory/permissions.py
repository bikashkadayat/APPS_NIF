from rest_framework.permissions import BasePermission, SAFE_METHODS

from users.models import User

# Managers who may add/edit items, assign/return, and approve/reject take-outs.
MANAGER_ROLES = (User.Roles.ADMIN, User.Roles.APPROVER, User.Roles.CHECKER)  # Admin / HR / Dept Head


def is_manager(user):
    return bool(user and user.is_authenticated and user.role in MANAGER_ROLES)


class InventoryItemPermission(BasePermission):
    """Allowlist: only asset managers (Admin / HR / Dept Head) get full inventory
    access. A non-manager gets NO list and NO writes — they may only *retrieve* a
    single item, and even then the viewset queryset restricts them to items
    actively assigned to them (so a non-assigned id/URL 404s). Any role not in the
    manager allowlist defaults to this restricted path."""
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if is_manager(u):
            return True
        # Non-managers: single-item retrieve only (queryset-scoped to their assets);
        # list / create / update / delete / manager-actions are all denied (403).
        return getattr(view, "action", None) == "retrieve" and request.method in SAFE_METHODS


class IsManager(BasePermission):
    """Manager-only endpoints (assign/return/approve/reject/mark_returned)."""
    def has_permission(self, request, view):
        return is_manager(request.user)
