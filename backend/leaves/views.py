from datetime import date
from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsApproverOrAdmin
from audit.models import AuditLog
from audit.services import log_action
from .models import Leave, LeaveBalance
from .serializers import LeaveSerializer, LeaveBalanceSerializer


def update_leave_balance(user, leave_type, year, delta):
    balance, created = LeaveBalance.objects.get_or_create(
        user=user,
        leave_type=leave_type,
        year=year,
        defaults={'total_allocated': 0, 'used_so_far': 0}
    )
    balance.used_so_far = max(0, balance.used_so_far + delta)
    balance.save()


def get_leave_days(start_date, end_date):
    return (end_date - start_date).days + 1


class LeaveViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        from users.models import User

        # Soft-deleted leaves are hidden from all listings/detail (Phase 5).
        base = Leave.objects.filter(is_deleted=False).order_by("-created_at")

        if user.role == User.Roles.MAKER:
            return base.filter(user=user)

        if user.role == User.Roles.CHECKER:
            return base.filter(status=Leave.Status.PENDING)

        if user.role in [User.Roles.APPROVER, User.Roles.ADMIN]:
            return base

        return Leave.objects.none()

    def perform_create(self, serializer):
        from users.models import User
        if self.request.user.role not in [User.Roles.MAKER, User.Roles.ADMIN]:
            raise PermissionDenied("Only makers can apply for leave.")
        approver = serializer.validated_data.get('approver') if hasattr(serializer, 'validated_data') else None
        if approver and approver.role not in [User.Roles.APPROVER, User.Roles.ADMIN]:
            raise PermissionDenied("Invalid approver selected.")
        serializer.save(user=self.request.user, status=Leave.Status.PENDING)
        log_action(self.request.user, AuditLog.Action.SUBMIT, instance=serializer.instance, request=self.request)

    def perform_destroy(self, instance):
        # Leaves with approved day records are soft-deleted to preserve history;
        # everything else is hard-deleted as before.
        from .models import LeaveDayRecord
        from . import services

        has_approved = instance.day_records.filter(
            status=LeaveDayRecord.Status.APPROVED
        ).exists()
        log_action(self.request.user, AuditLog.Action.DELETE, instance=instance, request=self.request)
        if has_approved:
            services.soft_delete_leave(instance)
        else:
            instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[IsApproverOrAdmin])
    def set_status(self, request, pk=None):
        leave = self.get_object()
        status_value = request.data.get('status')
        valid_statuses = [choice[0] for choice in Leave.Status.choices]
        if status_value not in valid_statuses:
            return Response({"error": "Invalid leave status."}, status=status.HTTP_400_BAD_REQUEST)

        old_status = leave.status
        leave.status = status_value
        leave.approver = request.user
        leave.save()

        if old_status != status_value:
            days = get_leave_days(leave.start_date, leave.end_date)
            year = leave.start_date.year
            if status_value == Leave.Status.APPROVED:
                update_leave_balance(leave.user, leave.leave_type, year, days)
            elif status_value == Leave.Status.REJECTED and old_status == Leave.Status.APPROVED:
                update_leave_balance(leave.user, leave.leave_type, year, -days)

        audit_action = AuditLog.Action.APPROVE if status_value == Leave.Status.APPROVED else AuditLog.Action.REJECT if status_value == Leave.Status.REJECTED else AuditLog.Action.UPDATE
        log_action(request.user, audit_action, instance=leave, changes={'from': old_status, 'to': status_value}, request=request)

        return Response(self.get_serializer(leave).data)

    def _leave_pdf_context(self, leave, document_number):
        from documents.pdf import common_context
        from . import services as leave_services
        from .models import EnterpriseLeaveBalance, LeaveType

        user = leave.user
        employee_name = user.get_full_name() or user.username
        approver_name = (leave.approver.get_full_name() or leave.approver.username) if leave.approver else "—"
        working_days = leave_services.calculate_working_days(leave.start_date, leave.end_date)

        leave_type = LeaveType.objects.filter(code__iexact=leave.leave_type).first()
        year = leave.start_date.year
        statement = "Balance details are available in your leave history."
        if leave_type:
            bal = EnterpriseLeaveBalance.objects.filter(user=user, leave_type=leave_type, year=year).first()
            if bal:
                statement = (
                    f"This {working_days}-working-day {leave_type.name} leave is reflected in your {year} balance. "
                    f"Remaining available: {bal.available_days} of {bal.entitled_days} day(s)."
                )

        ctx = common_context(document_number)
        ctx.update({
            "leave": leave,
            "employee_name": employee_name,
            "department": getattr(user, "department", "") or "",
            "approver_name": approver_name,
            "working_days": working_days,
            "balance_statement": statement,
        })
        return ctx

    def _render_leave_pdf(self, request, template_name, doc_type):
        from django.http import HttpResponse
        from documents.models import IssuedDocument
        from documents.pdf import render_pdf
        from documents.services import issue_document

        leave = self.get_object()
        if leave.status != Leave.Status.APPROVED:
            return Response({"detail": "Available only for approved leave."}, status=status.HTTP_409_CONFLICT)

        actors = [leave.user.get_full_name() or leave.user.username]
        if leave.approver:
            actors.append(leave.approver.get_full_name() or leave.approver.username)
        doc = issue_document(
            doc_type, "leave", leave,
            subject=f"{leave.get_leave_type_display()} {leave.start_date}..{leave.end_date}",
            issued_by=request.user, actors=actors,
        )
        ctx = self._leave_pdf_context(leave, doc.document_number)
        pdf_bytes = render_pdf(template_name, ctx)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{doc.document_number}.pdf"'
        return response

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        from documents.models import IssuedDocument
        return self._render_leave_pdf(request, "pdf/leave_application.html", IssuedDocument.DocType.LEAVE_APPLICATION)

    @action(detail=True, methods=["get"], url_path="certificate")
    def certificate(self, request, pk=None):
        from documents.models import IssuedDocument
        return self._render_leave_pdf(request, "pdf/leave_certificate.html", IssuedDocument.DocType.LEAVE_CERTIFICATE)


class LeaveBalanceView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balances = LeaveBalance.objects.filter(user=request.user)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class LeaveCalendarView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leaves = Leave.objects.filter(status=Leave.Status.APPROVED)
        serializer = LeaveSerializer(leaves, many=True)
        return Response(serializer.data)


# ===========================================================================
# Phase 4 - Enterprise Leave Records views
# ===========================================================================
from django.db.models import Q
from rest_framework import viewsets as drf_viewsets
from rest_framework.views import APIView
from users.models import User
from users.admin_views import IsAdminOrSuperuser
from . import services
from .filters import LeaveDayRecordFilter
from .models import (
    EnterpriseLeaveBalance,
    Holiday,
    LeaveDayRecord,
    LeaveType,
    MonthlyLeaveSummary,
    WeeklyLeaveSummary,
)
from .serializers import (
    EnterpriseLeaveBalanceSerializer,
    HolidaySerializer,
    LeaveDayRecordSerializer,
    LeaveHistorySerializer,
    LeaveTypeSerializer,
    MonthlyLeaveSummarySerializer,
    UserMiniSerializer,
    WeeklyLeaveSummarySerializer,
)


def _is_privileged(user):
    """Admin/checker/approver may view records beyond their own."""
    return user.role in [User.Roles.ADMIN, User.Roles.CHECKER, User.Roles.APPROVER]


class LeaveTypeViewSet(drf_viewsets.ReadOnlyModelViewSet):
    """Active leave types for all authenticated users (admin CRUD lives in admin_views)."""
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveTypeSerializer
    queryset = LeaveType.objects.filter(is_active=True)


class HolidayViewSet(drf_viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HolidaySerializer

    def get_queryset(self):
        qs = Holiday.objects.filter(is_active=True)
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(date__year=year)
        return qs


class LeaveDayRecordViewSet(drf_viewsets.ReadOnlyModelViewSet):
    """Per-day records, filterable by user_id / start / end."""
    permission_classes = [IsAuthenticated]
    serializer_class = LeaveDayRecordSerializer
    filterset_class = LeaveDayRecordFilter
    ordering_fields = ['date', 'status', 'year', 'month', 'week_number']

    def get_queryset(self):
        user = self.request.user
        qs = LeaveDayRecord.objects.select_related("leave_type", "user")
        if not _is_privileged(user):
            qs = qs.filter(user=user)
        elif self.request.query_params.get("user_id"):
            qs = qs.filter(user_id=self.request.query_params["user_id"])
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs


class EnterpriseLeaveBalanceViewSet(drf_viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EnterpriseLeaveBalanceSerializer

    def get_queryset(self):
        user = self.request.user
        qs = EnterpriseLeaveBalance.objects.select_related("leave_type", "user")
        if user.role != User.Roles.ADMIN:
            qs = qs.filter(user=user)
        elif self.request.query_params.get("user_id"):
            qs = qs.filter(user_id=self.request.query_params["user_id"])
        year = self.request.query_params.get("year")
        if year:
            qs = qs.filter(year=year)
        return qs


class WeeklyLeaveSummaryViewSet(drf_viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = WeeklyLeaveSummarySerializer

    def get_queryset(self):
        user = self.request.user
        qs = WeeklyLeaveSummary.objects.all()
        if not _is_privileged(user):
            qs = qs.filter(user=user)
        elif self.request.query_params.get("user_id"):
            qs = qs.filter(user_id=self.request.query_params["user_id"])
        for field in ("year", "week_number"):
            value = self.request.query_params.get(field)
            if value:
                qs = qs.filter(**{field: value})
        return qs


class MonthlyLeaveSummaryViewSet(drf_viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MonthlyLeaveSummarySerializer

    def get_queryset(self):
        user = self.request.user
        qs = MonthlyLeaveSummary.objects.all()
        if not _is_privileged(user):
            qs = qs.filter(user=user)
        elif self.request.query_params.get("user_id"):
            qs = qs.filter(user_id=self.request.query_params["user_id"])
        for field in ("year", "month"):
            value = self.request.query_params.get(field)
            if value:
                qs = qs.filter(**{field: value})
        return qs


class MyLeaveHistoryView(APIView):
    """GET /api/v1/leaves/my-history/?year=2026 - rich per-year history."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        year = int(request.query_params.get("year", date.today().year))
        user = request.user
        payload = {
            "user": user,
            "year": year,
            "balances": EnterpriseLeaveBalance.objects.filter(
                user=user, year=year
            ).select_related("leave_type"),
            "recent_leaves": Leave.objects.filter(
                user=user, start_date__year=year
            ).order_by("-start_date")[:20],
            "monthly_summaries": MonthlyLeaveSummary.objects.filter(
                user=user, year=year
            ).order_by("month"),
        }
        return Response(LeaveHistorySerializer(payload, context={"request": request}).data)


class LeaveCalendarRecordsView(APIView):
    """
    GET /api/v1/leaves/calendar/?start=YYYY-MM-DD&end=YYYY-MM-DD&user_id=optional
    Returns LeaveDayRecords for calendar rendering (color-coded by leave type).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = LeaveDayRecord.objects.select_related("leave_type", "user")
        target = request.query_params.get("user_id")
        if _is_privileged(user) and target:
            qs = qs.filter(user_id=target)
        else:
            qs = qs.filter(user=user)
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return Response(LeaveDayRecordSerializer(qs, many=True).data)


class TeamAttendanceView(APIView):
    """
    GET /api/v1/leaves/team-attendance/?department=CODE&month=YYYY-MM
    Team attendance heatmap for managers / HR (privileged roles only).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_privileged(request.user):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)

        dept_code = request.query_params.get("department")
        month_param = request.query_params.get("month")
        if not month_param:
            return Response({"detail": "month=YYYY-MM is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            year, month = (int(x) for x in month_param.split("-"))
        except ValueError:
            return Response({"detail": "month must be YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)

        members = User.objects.filter(is_active=True)
        if dept_code:
            members = members.filter(
                Q(department_ref__code__iexact=dept_code) | Q(department__iexact=dept_code)
            )

        rows = []
        for member in members:
            summary = services.recompute_monthly_summary(member, year, month)
            rows.append({
                "user": UserMiniSerializer(member).data,
                "working_days": summary.working_days,
                "approved_days": summary.approved_days,
                "pending_days": summary.pending_days,
                "attendance_percentage": summary.attendance_percentage,
                "by_type": summary.by_type,
            })
        return Response({"department": dept_code, "year": year, "month": month, "team": rows})


class RecomputeBalanceView(APIView):
    """POST /api/v1/leaves/recompute-balance/  body: {user_id, year}  (admin only)."""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request):
        user_id = request.data.get("user_id")
        year = int(request.data.get("year", date.today().year))
        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        balances = [
            services.recompute_leave_balance(target, lt, year)
            for lt in LeaveType.objects.filter(is_active=True)
        ]
        services.audit_log(
            request.user, "LEAVE_BALANCE_ADJUSTED", target=target,
            metadata={"year": year, "trigger": "manual_recompute"}, request=request,
        )
        return Response(EnterpriseLeaveBalanceSerializer(balances, many=True).data)


class YearEndCarryForwardView(APIView):
    """POST /api/v1/leaves/year-end-carry-forward/  body: {year}  (admin only)."""
    permission_classes = [IsAdminOrSuperuser]

    def post(self, request):
        year = int(request.data.get("year", date.today().year))
        processed = 0
        for member in User.objects.filter(is_active=True):
            services.process_year_end_carry_forward(member, year, actor=request.user)
            processed += 1
        return Response({"year": year, "users_processed": processed})
