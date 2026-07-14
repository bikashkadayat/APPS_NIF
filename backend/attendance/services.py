"""Attendance business logic — reuses the existing Holiday / Leave / BS-date
systems so nothing is duplicated."""
from datetime import date as _date, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone

from .models import Attendance

ZERO = Decimal("0.00")


def _parse_time(raw, default_h, default_m):
    try:
        h, m = (int(x) for x in str(raw).split(":"))
        return time(h, m)
    except (ValueError, AttributeError):
        return time(default_h, default_m)


def office_start_time():
    return _parse_time(getattr(settings, "ATTENDANCE_OFFICE_START", "10:00"), 10, 0)


def absent_cutoff_time():
    """Local time after which *today* becomes eligible to be counted Absent."""
    return _parse_time(getattr(settings, "ATTENDANCE_ABSENT_CUTOFF", "18:00"), 18, 0)


def attendance_tracking_start():
    """Global floor date before which no day is ever Absent (feature go-live).
    None when unset."""
    raw = (getattr(settings, "ATTENDANCE_TRACKING_START", "") or "").strip()
    if not raw:
        return None
    try:
        y, m, d = (int(x) for x in raw.split("-"))
        return _date(y, m, d)
    except (ValueError, AttributeError):
        return None


def absent_floor(employee):
    """The earliest date an absence can EVER be counted for this employee.

    Hard lower bound = the ACCOUNT REGISTRATION date (User.date_joined): attendance
    cannot exist before the employee's account existed in the system. A backdated
    ``date_of_joining`` can only push this LATER, never earlier — so we take the
    later of (registration, date_of_joining). The optional global tracking-start
    pushes it later still. A day before this floor is Not Applicable — never Absent.
    """
    dj = getattr(employee, "date_joined", None)
    registration = timezone.localtime(dj).date() if dj else None
    join = getattr(employee, "date_of_joining", None)

    if registration and join:
        floor = max(registration, join)   # never earlier than registration
    else:
        floor = registration or join

    start = attendance_tracking_start()
    if floor and start:
        return max(floor, start)
    return floor or start  # None only if the account has no registration date


def _absent_day_reached(d, today, now=None):
    """True when day `d` is 'past enough' to judge as Absent: any strictly-past
    day, or today only after the check-in window (cut-off) has closed. Future
    days are never reached."""
    if d < today:
        return True
    if d == today:
        now = now or now_local()
        return now.timetz().replace(tzinfo=None) >= absent_cutoff_time()
    return False


def resolve_day_status(*, record, is_holiday_day, is_leave_day, d, floor, today, now=None):
    """Canonical per-day attendance status shared by the dashboard, calendar,
    history and reports/PDFs. Returns an Attendance.Status value, or None when
    the day is Not Applicable (excluded — NOT Absent, NOT counted).

    A day is Absent ONLY when it is a working day with no check-in, on/after the
    employee's tracking floor, and already 'past enough' (see _absent_day_reached).
    """
    if record and record.check_in:
        return record.status  # a real check-in is ground truth, always shown
    # Nothing of ANY kind exists before the account was registered in the system
    # (checked before holiday/leave so pre-registration days render as Not Applicable).
    if floor is None or d < floor:
        return None
    if is_holiday_day:
        return Attendance.Status.HOLIDAY
    if is_leave_day:
        return Attendance.Status.ON_LEAVE
    if record:  # manual HR row without a check-in — respect the stored status
        return record.status
    if not _absent_day_reached(d, today, now):
        return None  # today mid-day, or a future date — Not Applicable
    return Attendance.Status.ABSENT


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

    Priority: real check-in > Holiday > Approved Leave > Absent (only a past-enough
    working day on/after the employee's tracking floor) > Not Applicable (None).
    Delegates to resolve_day_status so every view agrees.
    """
    return resolve_day_status(
        record=record,
        is_holiday_day=is_holiday(d),
        is_leave_day=has_approved_leave(employee, d),
        d=d,
        floor=absent_floor(employee),
        today=now_local().date(),
    )


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
