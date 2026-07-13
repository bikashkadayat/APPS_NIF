"""Attendance business logic — reuses the existing Holiday / Leave / BS-date
systems so nothing is duplicated."""
from datetime import date as _date, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone

from .models import Attendance

ZERO = Decimal("0.00")


def office_start_time():
    raw = getattr(settings, "ATTENDANCE_OFFICE_START", "10:00")
    h, m = (int(x) for x in str(raw).split(":"))
    return time(h, m)


def full_day_hours():
    return Decimal(str(getattr(settings, "ATTENDANCE_FULL_DAY_HOURS", 8)))


def half_day_hours():
    return Decimal(str(getattr(settings, "ATTENDANCE_HALF_DAY_HOURS", 5)))


def now_local():
    """Current time in the configured (Asia/Kathmandu) timezone."""
    return timezone.localtime(timezone.now())


def is_holiday(d):
    """Saturday (Nepal weekly holiday) or an active public holiday."""
    from leaves.models import Holiday

    if d.weekday() == 5:
        return True
    return Holiday.objects.filter(is_active=True, date=d).exists()


def holiday_name(d):
    from leaves.models import Holiday

    if d.weekday() == 5:
        return "Saturday (Weekly Holiday)"
    h = Holiday.objects.filter(is_active=True, date=d).values_list("name", flat=True).first()
    return h


def has_approved_leave(employee, d):
    from leaves.models import Leave

    return Leave.objects.filter(
        user=employee, status=Leave.Status.APPROVED, is_deleted=False,
        start_date__lte=d, end_date__gte=d,
    ).exists()


def compute_working_hours(check_in, check_out):
    if not check_in or not check_out or check_out <= check_in:
        return ZERO
    hours = Decimal((check_out - check_in).total_seconds()) / Decimal(3600)
    return hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_late(check_in_local):
    return check_in_local.timetz().replace(tzinfo=None) > office_start_time()


def recompute_status(record):
    """Set status + working_hours on a record from its check-in/out times."""
    ci, co = record.check_in, record.check_out
    if ci and co:
        wh = compute_working_hours(ci, co)
        record.working_hours = wh
        if wh < half_day_hours():
            record.status = Attendance.Status.HALF_DAY
        else:
            record.status = Attendance.Status.LATE if is_late(timezone.localtime(ci)) else Attendance.Status.PRESENT
    elif ci:
        record.working_hours = ZERO
        record.status = Attendance.Status.LATE if is_late(timezone.localtime(ci)) else Attendance.Status.PRESENT
    else:
        record.working_hours = ZERO
        record.status = Attendance.Status.ABSENT
    return record


def effective_status(employee, d, record=None):
    """Status for a single day, layering auto-integration over any stored row.

    Priority: real check-in > Holiday > Approved Leave > Absent (past) / none (future).
    """
    if record and record.check_in:
        return record.status
    if is_holiday(d):
        return Attendance.Status.HOLIDAY
    if has_approved_leave(employee, d):
        return Attendance.Status.ON_LEAVE
    if record:  # manual HR row without check-in
        return record.status
    if d < now_local().date():
        return Attendance.Status.ABSENT
    return None  # today/future with no record yet


def month_days(year, month):
    d = _date(year, month, 1)
    while d.month == month:
        yield d
        d += timedelta(days=1)


def build_calendar(employee, year, month):
    """Per-day status for an employee's month, plus summary counts."""
    from config.nepali_dates import to_bs

    records = {a.date: a for a in Attendance.objects.filter(
        employee=employee, date__year=year, date__month=month)}
    days, counts = [], {s.value: 0 for s in Attendance.Status}
    for d in month_days(year, month):
        rec = records.get(d)
        status = effective_status(employee, d, rec)
        if status is None:
            continue
        counts[status] = counts.get(status, 0) + 1
        days.append({
            "date": d.isoformat(),
            "date_bs": to_bs(d),
            "status": status,
            "check_in": rec.check_in.isoformat() if rec and rec.check_in else None,
            "check_out": rec.check_out.isoformat() if rec and rec.check_out else None,
            "working_hours": str(rec.working_hours) if rec else "0.00",
            "holiday_name": holiday_name(d) if status == Attendance.Status.HOLIDAY else None,
        })
    return {"year": year, "month": month, "days": days, "summary": counts}
