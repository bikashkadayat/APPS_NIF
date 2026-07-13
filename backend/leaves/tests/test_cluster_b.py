"""
Cluster B — security / integrity verification.

M7: a Dept Head (checker) is scoped to their own department across
    LeaveDayRecord / summaries / calendar / TeamAttendance; cross-department
    ?user_id is denied (no data leak). HR/Admin keep org-wide access.
M4: concurrent applications on the same balance are race-safe (no over-spend,
    never negative, capped at allocation) via select_for_update.
M5: logout blacklists the refresh token server-side; the old token is rejected.
"""
import threading
from datetime import timedelta

import pytest
from django.db import connection
from rest_framework.test import APIClient

from users.models import User
from leaves.models import Leave, LeaveBalance
from .conftest import _user, MONDAY


def _emp(username, role, dept):
    return _user(username, role, department=dept)


def _make_leave(emp, start, end, status=Leave.Status.APPROVED, approver=None):
    return Leave.objects.create(
        user=emp, leave_type="annual", reason="x",
        start_date=start, end_date=end, status=status, approver=approver,
    )


# ---------------------------------------------------------------------------
# M7 — cross-department scoping
# ---------------------------------------------------------------------------
@pytest.fixture
def two_depts(db):
    head_a = _emp("cb_head_a", User.Roles.CHECKER, "DEPTA")
    emp_a = _emp("cb_emp_a", User.Roles.MAKER, "DEPTA")
    emp_b = _emp("cb_emp_b", User.Roles.MAKER, "DEPTB")
    hr = _emp("cb_hr", User.Roles.APPROVER, "DEPTA")
    _make_leave(emp_a, MONDAY, MONDAY + timedelta(days=1))
    _make_leave(emp_b, MONDAY, MONDAY + timedelta(days=1))
    return head_a, emp_a, emp_b, hr


@pytest.mark.django_db
def test_checker_cannot_read_other_department_day_records(two_depts):
    head_a, emp_a, emp_b, hr = two_depts
    c = APIClient(); c.force_authenticate(head_a)

    # Own-department employee: allowed.
    r_own = c.get(f"/api/v1/leave-day-records/?user_id={emp_a.id}")
    assert r_own.status_code == 200
    # Cross-department employee: denied, no data leak.
    r_other = c.get(f"/api/v1/leave-day-records/?user_id={emp_b.id}")
    assert r_other.status_code == 403

    # Unfiltered list is scoped to the checker's own department: it returns the
    # same records as the own-department employee (emp_a is DEPTA's only maker),
    # i.e. emp_b's records are excluded.
    def _count(resp):
        return resp.data["count"] if isinstance(resp.data, dict) and "count" in resp.data else len(resp.data)
    all_count = _count(c.get("/api/v1/leave-day-records/"))
    assert all_count == _count(r_own) == 2


@pytest.mark.django_db
def test_checker_cannot_read_other_department_calendar(two_depts):
    head_a, emp_a, emp_b, hr = two_depts
    c = APIClient(); c.force_authenticate(head_a)
    assert c.get(f"/api/v1/leaves/calendar/?user_id={emp_a.id}").status_code == 200
    assert c.get(f"/api/v1/leaves/calendar/?user_id={emp_b.id}").status_code == 403


@pytest.mark.django_db
def test_checker_summaries_scoped(two_depts):
    head_a, emp_a, emp_b, hr = two_depts
    c = APIClient(); c.force_authenticate(head_a)
    assert c.get(f"/api/v1/monthly-summaries/?user_id={emp_b.id}").status_code == 403
    assert c.get(f"/api/v1/weekly-summaries/?user_id={emp_b.id}").status_code == 403


@pytest.mark.django_db
def test_team_attendance_scoped_to_own_department(two_depts):
    head_a, emp_a, emp_b, hr = two_depts
    month = f"{MONDAY.year}-{MONDAY.month:02d}"
    c = APIClient(); c.force_authenticate(head_a)
    data = c.get(f"/api/v1/leaves/team-attendance/?month={month}").data
    depts = {row["user"]["department"] for row in data["team"]}
    names = {row["user"]["full_name"] for row in data["team"]}
    assert "DEPTB" not in depts                          # other department excluded
    assert any("Cb_emp_a" in n for n in names)           # own department present


@pytest.mark.django_db
def test_hr_keeps_org_wide_access(two_depts):
    head_a, emp_a, emp_b, hr = two_depts
    c = APIClient(); c.force_authenticate(hr)
    # HR may read across departments.
    assert c.get(f"/api/v1/leave-day-records/?user_id={emp_b.id}").status_code == 200
    assert c.get(f"/api/v1/leaves/calendar/?user_id={emp_b.id}").status_code == 200


# ---------------------------------------------------------------------------
# M4 — concurrency / race-safety
# ---------------------------------------------------------------------------
@pytest.mark.django_db(transaction=True)
def test_concurrent_apply_cannot_exceed_allocation():
    """Two threads apply the SAME 8-working-day annual leave (Category A = 12)
    simultaneously. Locking must let only one through; used_so_far must never
    exceed the allocation or go negative."""
    emp = _emp("cb_race", User.Roles.MAKER, "RACE")
    hr = _emp("cb_race_hr", User.Roles.APPROVER, "RACE")
    start, end = MONDAY, MONDAY + timedelta(days=8)  # 8 working days (one Saturday)

    results = {}
    barrier = threading.Barrier(2)

    def worker(idx):
        try:
            barrier.wait()
            c = APIClient(); c.force_authenticate(emp)
            r = c.post("/api/v1/leaves/", {
                "leave_type": "annual", "start_date": str(start), "end_date": str(end),
                "reason": "race", "approver": str(hr.id),
            }, format="json")
            results[idx] = r.status_code
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    bal = LeaveBalance.objects.get(user=emp, leave_type="annual", year=start.year)
    # Invariants: never negative, never over allocation. 8+8=16 would breach 12.
    assert 0 <= bal.used_so_far <= bal.total_allocated
    assert bal.used_so_far == 8            # exactly one application committed
    assert sum(1 for v in results.values() if v == 201) == 1

    # cleanup rows created in this transaction=True test
    Leave.objects.filter(user=emp).delete()
    LeaveBalance.objects.filter(user=emp).delete()
    User.objects.filter(username__in=["cb_race", "cb_race_hr"]).delete()


# ---------------------------------------------------------------------------
# M5 — logout blacklists the refresh token
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_logout_blacklists_refresh_token():
    user = _emp("cb_logout", User.Roles.MAKER, "DEPTA")
    user.set_password("pass12345"); user.save()

    c = APIClient()
    login = c.post("/api/v1/auth/login/", {"email": user.email, "password": "pass12345"}, format="json")
    assert login.status_code == 200, login.content
    access, refresh = login.data["access"], login.data["refresh"]

    # The refresh token works before logout.
    ok = APIClient().post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
    assert ok.status_code == 200

    c.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    out = c.post("/api/v1/auth/logout/", {"refresh": ok.data["refresh"]}, format="json")
    assert out.status_code == 205

    # The (rotated) refresh token is rejected after logout.
    rejected = APIClient().post("/api/v1/auth/refresh/", {"refresh": ok.data["refresh"]}, format="json")
    assert rejected.status_code == 401
