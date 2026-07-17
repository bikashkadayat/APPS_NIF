"""Cluster 2 regressions — authorization (bugs 4, 5).

  bug 4  any manager could approve their OWN take-out request (no segregation of
         duties, unlike leaves which guards this)
  bug 5  a manager with department_ref=None filtered on `department_id=None`, which
         compiles to IS NULL and matched every unscoped row
"""
import pytest

from inventory.models import InventoryItem, TakeOutRequest
from inventory import services
from users.models import User

pytestmark = pytest.mark.django_db


def _mk_request(item, requester, today, soon):
    return services.create_takeout(
        item=item, requester=requester, purpose=TakeOutRequest.Purpose.HOME,
        reason="need it", expected_out_date=today, expected_return_date=soon)


# --------------------------------------------------------------------------- #
# BUG 4 — no self-approval
# --------------------------------------------------------------------------- #
def test_dept_head_cannot_approve_own_takeout(auth, item, head, today, soon):
    req = _mk_request(item, head, today, soon)

    resp = auth(head).post(f"/api/v1/inventory/takeouts/{req.id}/approve/", {}, format="json")

    assert resp.status_code == 403
    assert "your own" in str(resp.data).lower()
    req.refresh_from_db()
    item.refresh_from_db()
    assert req.status == TakeOutRequest.Status.PENDING
    assert item.status != InventoryItem.Status.OUT


@pytest.mark.parametrize("role_fixture", ["hr", "admin"])
def test_no_manager_role_can_approve_own_takeout(auth, item, today, soon, request, role_fixture):
    actor = request.getfixturevalue(role_fixture)
    req = _mk_request(item, actor, today, soon)

    resp = auth(actor).post(f"/api/v1/inventory/takeouts/{req.id}/approve/", {}, format="json")

    assert resp.status_code == 403
    req.refresh_from_db()
    assert req.status == TakeOutRequest.Status.PENDING


def test_another_manager_can_approve_that_request(auth, item, head, hr, today, soon):
    """The request must still be actionable — by a DIFFERENT authorized approver."""
    req = _mk_request(item, head, today, soon)

    resp = auth(hr).post(f"/api/v1/inventory/takeouts/{req.id}/approve/", {}, format="json")

    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == TakeOutRequest.Status.APPROVED
    assert req.approver_id == hr.id


def test_manager_can_still_approve_someone_elses_request(auth, item, employee, head, today, soon):
    req = _mk_request(item, employee, today, soon)

    resp = auth(head).post(f"/api/v1/inventory/takeouts/{req.id}/approve/", {}, format="json")

    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == TakeOutRequest.Status.APPROVED


# --------------------------------------------------------------------------- #
# BUG 5 — a manager with no department sees nothing department-scoped
# --------------------------------------------------------------------------- #
@pytest.fixture
def headless(db):
    return User.objects.create_user(
        username="inv_headless", email="inv_headless@nif.test", password="pass12345",
        first_name="Headless", last_name="T", role=User.Roles.CHECKER,
        department_ref=None)


def test_departmentless_head_sees_no_unscoped_items(auth, headless, eng):
    unscoped = InventoryItem.objects.create(asset_code="NIF-INV-NULL", name="Unscoped", department=None)
    InventoryItem.objects.create(asset_code="NIF-INV-ENG", name="Eng item", department=eng)

    resp = auth(headless).get("/api/v1/inventory/items/")

    assert resp.status_code == 200
    body = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    codes = [r["asset_code"] for r in body]
    assert unscoped.asset_code not in codes
    assert codes == []


def test_departmentless_head_sees_no_unscoped_assignments(
        auth, headless, admin, eng):
    """The 'who has what' board must be scoped the same way."""
    orphan_item = InventoryItem.objects.create(asset_code="NIF-INV-NULL2", name="Unscoped2")
    nobody = User.objects.create_user(
        username="inv_nodept", email="inv_nodept@nif.test", password="pass12345",
        role=User.Roles.MAKER, department_ref=None)
    services.assign_item(orphan_item.id, nobody, admin)

    resp = auth(headless).get("/api/v1/inventory/assignments/")

    assert resp.status_code == 200
    body = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    assert body == []


def test_departmentless_head_sees_only_own_takeouts(auth, headless, employee, item, today, soon):
    """A None department must fall back to own-requests-only, not every unscoped one."""
    orphan_item = InventoryItem.objects.create(asset_code="NIF-INV-NULL3", name="Unscoped3")
    someone_elses = _mk_request(orphan_item, employee, today, soon)  # department=None
    mine = _mk_request(item, headless, today, soon)

    resp = auth(headless).get("/api/v1/inventory/takeouts/")

    assert resp.status_code == 200
    body = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    refs = {r["reference"] for r in body}
    assert mine.reference in refs
    assert someone_elses.reference not in refs


def test_head_with_department_still_sees_their_own_department(auth, head, eng, ops):
    mine = InventoryItem.objects.create(asset_code="NIF-INV-M1", name="Mine", department=eng)
    theirs = InventoryItem.objects.create(asset_code="NIF-INV-O1", name="Theirs", department=ops)

    resp = auth(head).get("/api/v1/inventory/items/")

    body = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    codes = [r["asset_code"] for r in body]
    assert mine.asset_code in codes
    assert theirs.asset_code not in codes


def test_admin_still_sees_everything(auth, admin, eng, ops):
    InventoryItem.objects.create(asset_code="NIF-INV-A1", name="A", department=eng)
    InventoryItem.objects.create(asset_code="NIF-INV-A2", name="B", department=ops)
    InventoryItem.objects.create(asset_code="NIF-INV-A3", name="C", department=None)

    resp = auth(admin).get("/api/v1/inventory/items/")

    body = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
    codes = [r["asset_code"] for r in body]
    for c in ("NIF-INV-A1", "NIF-INV-A2", "NIF-INV-A3"):
        assert c in codes


def test_employee_cannot_list_items(auth, employee, item):
    resp = auth(employee).get("/api/v1/inventory/items/")
    assert resp.status_code == 403
