from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from audit.services import log_action
from users.models import User

from . import services, notifications as inv_notify
from .models import InventoryCategory, InventoryItem, TakeOutRequest
from .permissions import InventoryItemPermission, IsManager, is_manager
from .serializers import (
    InventoryCategorySerializer, InventoryItemSerializer, TakeOutRequestSerializer)


def _clear_takeout_notices(req_id):
    """Mark managers' 'awaiting your review' notices for a take-out read once it is
    decided, so their bell reconciles with the (now-empty) pending queue."""
    from notifications.dispatcher import resolve_source_notifications
    resolve_source_notifications(f"takeout-{req_id}-submitted")


class ManagerEmployeeListView(APIView):
    """Active users an asset can be assigned to — with the name + department the
    assignment UI needs. Managers only (Admin / HR / Dept Head); the shared
    /users/ endpoint is intentionally left minimal, so this is purpose-built."""
    permission_classes = [IsManager]

    def get(self, request):
        out = []
        qs = User.objects.filter(is_active=True).select_related("department_ref").order_by(
            "first_name", "last_name", "username")
        for u in qs:
            dep = getattr(u, "department_ref", None)
            out.append({
                "id": str(u.id),
                "full_name": u.get_full_name() or u.username,
                "employee_id": u.employee_id or "",
                "role": u.role,
                "department_ref": str(dep.id) if dep else None,
                "department_name": dep.name if dep else (getattr(u, "department", None) or None),
            })
        return Response(out)


class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [InventoryItemPermission]


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [InventoryItemPermission]

    def get_queryset(self):
        qs = InventoryItem.objects.select_related("category", "department").all()
        user = self.request.user
        if not is_manager(user):
            # Non-managers see ONLY items actively assigned to them (self-scoped).
            qs = qs.filter(assignments__assigned_to=user, assignments__is_active=True).distinct()
        elif user.role == User.Roles.CHECKER:
            # Dept Head: manager access scoped to items in their own department.
            qs = qs.filter(department_id=user.department_ref_id)
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("category"):
            qs = qs.filter(category_id=p["category"])
        if p.get("department"):
            qs = qs.filter(department_id=p["department"])
        if p.get("search"):
            s = p["search"]
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=s) | Q(asset_code__icontains=s) | Q(serial_number__icontains=s))
        return qs

    def perform_create(self, serializer):
        item = serializer.save(asset_code=services.generate_asset_code())
        log_action(self.request.user, AuditLog.Action.CREATE, instance=item,
                   changes={"event": "INVENTORY_ITEM_CREATED", "asset_code": item.asset_code},
                   request=self.request)

    def perform_update(self, serializer):
        item = serializer.save()
        log_action(self.request.user, AuditLog.Action.UPDATE, instance=item, request=self.request)

    def _employee(self, request):
        emp_id = request.data.get("assigned_to")
        if not emp_id:
            return None, Response({"detail": "assigned_to (employee id) is required."},
                                  status=status.HTTP_400_BAD_REQUEST)
        try:
            return User.objects.get(id=emp_id), None
        except User.DoesNotExist:
            return None, Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

    def _parse_date(self, request, field):
        raw = request.data.get(field)
        if not raw:
            return None
        from datetime import date
        try:
            y, m, d = (int(x) for x in str(raw).split("-"))
            return date(y, m, d)
        except (ValueError, TypeError):
            return None

    @action(detail=True, methods=["post"], permission_classes=[IsManager])
    def assign(self, request, pk=None):
        item = self.get_object()
        employee, err = self._employee(request)
        if err:
            return err
        services.assign_item(
            item.id, employee, request.user,
            note=request.data.get("note", ""),
            assigned_date=self._parse_date(request, "assigned_date"),
            handover_condition=request.data.get("handover_condition", ""),
            accessories=request.data.get("accessories", ""))
        item.refresh_from_db()
        log_action(request.user, AuditLog.Action.UPDATE, instance=item,
                   changes={"event": "INVENTORY_ASSIGNED", "to": str(employee.id)}, request=request)
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"], permission_classes=[IsManager])
    def handover(self, request, pk=None):
        item = self.get_object()
        employee, err = self._employee(request)
        if err:
            return err
        services.handover_item(
            item.id, employee, request.user,
            note=request.data.get("note", ""),
            assigned_date=self._parse_date(request, "assigned_date"),
            handover_condition=request.data.get("handover_condition", ""),
            accessories=request.data.get("accessories", ""))
        item.refresh_from_db()
        log_action(request.user, AuditLog.Action.UPDATE, instance=item,
                   changes={"event": "INVENTORY_HANDOVER", "to": str(employee.id)}, request=request)
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"], url_path="return", permission_classes=[IsManager])
    def return_item(self, request, pk=None):
        item = self.get_object()
        services.return_item(
            item.id, request.user,
            return_condition=request.data.get("return_condition", ""),
            return_remarks=request.data.get("return_remarks", ""))
        item.refresh_from_db()
        log_action(request.user, AuditLog.Action.UPDATE, instance=item,
                   changes={"event": "INVENTORY_RETURNED"}, request=request)
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["get"], permission_classes=[IsManager])
    def assignments(self, request, pk=None):
        """Assignment history for an item (managers only; Dept Head dept-scoped via
        get_object)."""
        from .serializers import ItemAssignmentSerializer
        item = self.get_object()  # enforces manager scope (404 outside Dept Head's dept)
        qs = item.assignments.order_by("-assigned_at")
        return Response(ItemAssignmentSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="assignment-receipt")
    def assignment_receipt(self, request, pk=None):
        item = self.get_object()
        active = item.active_assignment
        if not active:
            return Response({"detail": "No active assignment to generate a receipt for."},
                            status=status.HTTP_409_CONFLICT)
        from .pdf import render_assignment_receipt
        pdf = render_assignment_receipt(item, active)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="handover-{item.asset_code}.pdf"'
        return resp


class AssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Cross-item assignment board ('who has what') + employee 'My Assigned Assets'.

    - list: managers only (Dept Head scoped to their own department); active
      assignments by default, filterable by employee / department / category / status.
    - mine: any authenticated user's own active assignments (read-only).
    """
    from .serializers import AssignmentBoardSerializer
    serializer_class = AssignmentBoardSerializer
    permission_classes = [IsManager]

    def get_permissions(self):
        if self.action == "mine":
            return [IsAuthenticated()]
        return [IsManager()]

    def _base_qs(self):
        from .models import ItemAssignment
        return ItemAssignment.objects.select_related(
            "item", "item__category", "assigned_to", "assigned_to__department_ref")

    def get_queryset(self):
        qs = self._base_qs()
        # Active-only unless explicitly asked for history.
        if self.request.query_params.get("all") != "1":
            qs = qs.filter(is_active=True)
        # Dept Head is scoped to holders in their own department.
        user = self.request.user
        if user.role == User.Roles.CHECKER:
            qs = qs.filter(assigned_to__department_ref_id=user.department_ref_id)
        p = self.request.query_params
        if p.get("employee"):
            qs = qs.filter(assigned_to_id=p["employee"])
        if p.get("department"):
            qs = qs.filter(assigned_to__department_ref_id=p["department"])
        if p.get("category"):
            qs = qs.filter(item__category_id=p["category"])
        if p.get("status"):
            qs = qs.filter(item__status=p["status"])
        if p.get("search"):
            from django.db.models import Q
            s = p["search"]
            qs = qs.filter(Q(item__name__icontains=s) | Q(item__asset_code__icontains=s) | Q(assigned_to_name__icontains=s))
        return qs.order_by("assigned_to_name", "item__asset_code")

    @action(detail=False, methods=["get"])
    def mine(self, request):
        qs = self._base_qs().filter(is_active=True, assigned_to=request.user).order_by("item__asset_code")
        return Response(self.get_serializer(qs, many=True).data)


class TakeOutRequestViewSet(viewsets.ModelViewSet):
    serializer_class = TakeOutRequestSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]  # no PUT/PATCH/DELETE

    def get_queryset(self):
        user = self.request.user
        qs = TakeOutRequest.objects.select_related("item", "requested_by", "department").all()
        if user.role in (User.Roles.ADMIN, User.Roles.APPROVER):
            pass  # HR / Admin: org-wide
        elif user.role == User.Roles.CHECKER:
            # Dept Head: own department's requests + own requests.
            from django.db.models import Q
            qs = qs.filter(Q(department_id=user.department_ref_id) | Q(requested_by=user))
        else:
            qs = qs.filter(requested_by=user)  # Employee: own only
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("mine") == "1":
            qs = qs.filter(requested_by=user)
        return qs

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item = ser.validated_data.get("item")
        req = services.create_takeout(
            item=item, requester=request.user,
            purpose=ser.validated_data.get("purpose"),
            reason=ser.validated_data.get("reason"),
            expected_out_date=ser.validated_data.get("expected_out_date"),
            expected_return_date=ser.validated_data.get("expected_return_date"),
        )
        log_action(request.user, AuditLog.Action.SUBMIT, instance=req,
                   changes={"event": "TAKEOUT_REQUESTED", "reference": req.reference}, request=request)
        inv_notify.takeout_submitted(req)
        return Response(self.get_serializer(req).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsManager])
    def approve(self, request, pk=None):
        req = self.get_object()
        req = services.approve_takeout(req.id, request.user, remarks=request.data.get("remarks", ""))
        log_action(request.user, AuditLog.Action.APPROVE, instance=req,
                   changes={"event": "TAKEOUT_APPROVED", "reference": req.reference}, request=request)
        _clear_takeout_notices(req.id)  # reconcile approvers' bells with their queue
        inv_notify.takeout_finalized(req)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"], permission_classes=[IsManager])
    def reject(self, request, pk=None):
        req = self.get_object()
        req = services.reject_takeout(req.id, request.user, remarks=request.data.get("remarks", ""))
        log_action(request.user, AuditLog.Action.REJECT, instance=req,
                   changes={"event": "TAKEOUT_REJECTED", "reference": req.reference}, request=request)
        _clear_takeout_notices(req.id)
        inv_notify.takeout_finalized(req)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"], url_path="mark_returned", permission_classes=[IsManager])
    def mark_returned(self, request, pk=None):
        req = self.get_object()
        req = services.mark_returned(req.id, request.user)
        log_action(request.user, AuditLog.Action.UPDATE, instance=req,
                   changes={"event": "TAKEOUT_RETURNED", "reference": req.reference}, request=request)
        _clear_takeout_notices(req.id)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["get"], url_path="gate-pass")
    def gate_pass(self, request, pk=None):
        req = self.get_object()
        if req.status not in (TakeOutRequest.Status.APPROVED, TakeOutRequest.Status.RETURNED):
            return Response({"detail": "Gate pass is available only for approved requests."},
                            status=status.HTTP_409_CONFLICT)
        # Requester or any manager may download.
        if not (is_manager(request.user) or req.requested_by_id == request.user.id):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        from .pdf import render_gate_pass
        pdf = render_gate_pass(req)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="gate-pass-{req.reference}.pdf"'
        return resp
