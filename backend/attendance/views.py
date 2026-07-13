from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from audit.services import log_action
from config.nepali_dates import to_bs
from users.models import User

from . import services
from .models import Attendance
from .serializers import AttendanceSerializer, ManualAttendanceSerializer


class IsHROrAdmin(BasePermission):
    """HR (approver) or Admin may manage all attendance."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            User.Roles.APPROVER, User.Roles.ADMIN,
        )


def _fmt(dt):
    return timezone.localtime(dt).strftime("%H:%M") if dt else None


class CheckInView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        emp = request.user
        today = services.now_local().date()
        if services.is_holiday(today):
            return Response({"detail": f"Today is a holiday ({services.holiday_name(today)}). No check-in required."},
                            status=status.HTTP_400_BAD_REQUEST)
        rec, _ = Attendance.objects.get_or_create(
            employee=emp, date=today, defaults={"marked_by": Attendance.MarkedBy.SELF})
        if rec.check_in:
            return Response({"detail": f"You already checked in today at {_fmt(rec.check_in)}."},
                            status=status.HTTP_400_BAD_REQUEST)
        rec.check_in = timezone.now()
        rec.marked_by = Attendance.MarkedBy.SELF
        services.recompute_status(rec)
        rec.save()
        log_action(emp, AuditLog.Action.CREATE, instance=rec,
                   changes={"event": "ATTENDANCE_CHECK_IN", "at": _fmt(rec.check_in)}, request=request)
        return Response(AttendanceSerializer(rec).data, status=status.HTTP_201_CREATED)


class CheckOutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        emp = request.user
        today = services.now_local().date()
        rec = Attendance.objects.filter(employee=emp, date=today).first()
        if not rec or not rec.check_in:
            return Response({"detail": "You must check in before checking out."},
                            status=status.HTTP_400_BAD_REQUEST)
        if rec.check_out:
            return Response({"detail": f"You already checked out today at {_fmt(rec.check_out)}."},
                            status=status.HTTP_400_BAD_REQUEST)
        rec.check_out = timezone.now()
        services.recompute_status(rec)
        rec.save()
        log_action(emp, AuditLog.Action.UPDATE, instance=rec,
                   changes={"event": "ATTENDANCE_CHECK_OUT", "at": _fmt(rec.check_out),
                            "hours": str(rec.working_hours)}, request=request)
        return Response(AttendanceSerializer(rec).data)


class TodayView(APIView):
    """Today's status + this-month summary — powers the dashboard widget."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        emp = request.user
        now = services.now_local()
        today = now.date()
        rec = Attendance.objects.filter(employee=emp, date=today).first()
        eff = services.effective_status(emp, today, rec)
        month = services.build_calendar(emp, now.year, now.month)
        return Response({
            "date": today.isoformat(),
            "date_bs": to_bs(today),
            "status": eff,
            "check_in": rec.check_in.isoformat() if rec and rec.check_in else None,
            "check_out": rec.check_out.isoformat() if rec and rec.check_out else None,
            "check_in_local": _fmt(rec.check_in) if rec and rec.check_in else None,
            "check_out_local": _fmt(rec.check_out) if rec and rec.check_out else None,
            "working_hours": str(rec.working_hours) if rec else "0.00",
            "can_check_in": bool(not (rec and rec.check_in) and not services.is_holiday(today)),
            "can_check_out": bool(rec and rec.check_in and not rec.check_out),
            "office_start": getattr(settings, "ATTENDANCE_OFFICE_START", "10:00"),
            "month_summary": month["summary"],
        })


class MyCalendarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = services.now_local()
        year = int(request.query_params.get("year") or now.year)
        month = int(request.query_params.get("month") or now.month)
        return Response(services.build_calendar(request.user, year, month))


class AttendanceListView(APIView):
    """Role-scoped attendance list with filters (Employee=own, Dept Head=dept, HR/Admin=all)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.user.role
        qs = Attendance.objects.select_related("employee", "employee__department_ref")
        if role in (User.Roles.APPROVER, User.Roles.ADMIN):
            pass  # all
        elif role == User.Roles.CHECKER:
            qs = qs.filter(employee__department_ref_id=request.user.department_ref_id)
        else:
            qs = qs.filter(employee=request.user)

        p = request.query_params
        if p.get("date_from"):
            qs = qs.filter(date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(date__lte=p["date_to"])
        if p.get("department"):
            qs = qs.filter(employee__department_ref_id=p["department"])
        if p.get("employee"):
            qs = qs.filter(employee_id=p["employee"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        qs = qs.order_by("-date", "employee__first_name")[:500]
        return Response(AttendanceSerializer(qs, many=True).data)


class ManualAttendanceView(APIView):
    """HR/Admin manual add/edit (marked_by = HR), with remarks."""
    permission_classes = [IsAuthenticated, IsHROrAdmin]

    def post(self, request):
        ser = ManualAttendanceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            emp = User.objects.get(id=d["employee"])
        except User.DoesNotExist:
            return Response({"detail": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        rec, _ = Attendance.objects.get_or_create(employee=emp, date=d["date"])
        rec.status = d["status"]
        rec.check_in = d.get("check_in") or rec.check_in
        rec.check_out = d.get("check_out") or rec.check_out
        rec.remarks = d.get("remarks", "")
        rec.marked_by = Attendance.MarkedBy.HR
        if rec.check_in and rec.check_out:
            rec.working_hours = services.compute_working_hours(rec.check_in, rec.check_out)
        rec.save()
        log_action(request.user, AuditLog.Action.UPDATE, instance=rec,
                   changes={"event": "ATTENDANCE_MANUAL", "status": rec.status,
                            "employee": str(emp.id)}, request=request)
        return Response(AttendanceSerializer(rec).data, status=status.HTTP_200_OK)
