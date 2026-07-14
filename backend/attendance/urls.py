from django.urls import path

from .report_views import (
    AllReportView,
    EmployeeMonthlyReportView,
    EmployeeWeeklyReportView,
    ReportOptionsView,
)
from .views import (
    AttendanceListView,
    CheckInView,
    CheckOutView,
    ManualAttendanceView,
    MyCalendarView,
    TodayView,
)

urlpatterns = [
    path("attendance/check-in/", CheckInView.as_view(), name="attendance-check-in"),
    path("attendance/check-out/", CheckOutView.as_view(), name="attendance-check-out"),
    path("attendance/today/", TodayView.as_view(), name="attendance-today"),
    path("attendance/me/", MyCalendarView.as_view(), name="attendance-me"),
    # Reports (Admin/HR only)
    path("attendance/report/employee/<uuid:pk>/weekly", EmployeeWeeklyReportView.as_view(), name="attendance-report-weekly"),
    path("attendance/report/employee/<uuid:pk>/monthly", EmployeeMonthlyReportView.as_view(), name="attendance-report-monthly"),
    path("attendance/report/options/", ReportOptionsView.as_view(), name="attendance-report-options"),
    path("attendance/report/all", AllReportView.as_view(), name="attendance-report-all"),
    path("attendance/manual/", ManualAttendanceView.as_view(), name="attendance-manual"),
    path("attendance/", AttendanceListView.as_view(), name="attendance-list"),
]
