from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User
from leaves.models import Department
from inventory.models import InventoryItem


def _user(username, role, department_ref=None, **extra):
    defaults = dict(
        employment_type=User.EmploymentType.PERMANENT,
        date_of_joining=date(2018, 1, 1),
    )
    defaults.update(extra)
    return User.objects.create_user(
        username=username, email=f"{username}@nif.test", password="pass12345",
        first_name=username.capitalize(), last_name="T", role=role,
        department_ref=department_ref, **defaults,
    )


@pytest.fixture
def today():
    # settings.TIME_ZONE is Asia/Kathmandu, so this is "today" in Nepal.
    return timezone.localtime(timezone.now()).date()


@pytest.fixture
def soon(today):
    return today + timedelta(days=2)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def eng(db):
    return Department.objects.create(name="Engineering", code="INV-ENG")


@pytest.fixture
def ops(db):
    return Department.objects.create(name="Operations", code="INV-OPS")


@pytest.fixture
def employee(db, eng):
    """Plain employee (maker) — can request take-outs, not a manager."""
    return _user("inv_emp", User.Roles.MAKER, eng)


@pytest.fixture
def head(db, eng):
    """Department Head (checker) — manager, scoped to their own department."""
    return _user("inv_head", User.Roles.CHECKER, eng)


@pytest.fixture
def hr(db, eng):
    """HR (approver) — manager, org-wide."""
    return _user("inv_hr", User.Roles.APPROVER, eng)


@pytest.fixture
def admin(db, eng):
    return _user("inv_admin", User.Roles.ADMIN, eng)


@pytest.fixture
def item(db, eng):
    return InventoryItem.objects.create(
        asset_code="NIF-INV-T001", name="Test Laptop", department=eng)


@pytest.fixture
def auth(api):
    def _login(user):
        api.force_authenticate(user=user)
        return api
    return _login
