"""Phase 2: universal memo creation + hybrid checker/approver assignment."""
import pytest

from memos.models import Memo
from users.models import User


def _payload():
    return {"title": "T", "subject": "S", "body": "B", "memo_type": "general", "priority": "normal"}


def _draft_by(api, user):
    api.force_authenticate(user)
    resp = api.post("/api/v1/memos/", _payload(), format="json")
    assert resp.status_code == 201, resp.data
    return resp.data["id"]


# --- STEP 2.2: universal creation ------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("role_fixture", ["maker", "checker", "approver"])
def test_non_admin_users_can_create_memo(api, request, role_fixture):
    # Employee / Department Head / HR may author memos. Admin is excluded below.
    user = request.getfixturevalue(role_fixture)
    api.force_authenticate(user)
    resp = api.post("/api/v1/memos/", _payload(), format="json")
    assert resp.status_code == 201, resp.data
    assert Memo.objects.get(id=resp.data["id"]).created_by_id == user.id


@pytest.mark.django_db
def test_admin_cannot_create_memo(api, admin):
    # Admin is an oversight/approval role and does not author memo requests.
    api.force_authenticate(admin)
    resp = api.post("/api/v1/memos/", _payload(), format="json")
    assert resp.status_code == 403, resp.data


@pytest.mark.django_db
def test_unauthenticated_cannot_create_memo(api):
    assert api.post("/api/v1/memos/", _payload(), format="json").status_code == 401


# --- STEP 2.3: hybrid checker assignment -----------------------------------
@pytest.mark.django_db
def test_submit_with_manual_checker_uses_specified_user(api, maker, checker, other_checker, approver):
    mid = _draft_by(api, maker)
    api.force_authenticate(maker)
    resp = api.post(f"/api/v1/memos/{mid}/submit/", {"override_reviewer_id": str(other_checker.id)}, format="json")
    assert resp.status_code == 200, resp.data
    assert str(resp.data["current_reviewer"]["id"]) == str(other_checker.id)


@pytest.mark.django_db
def test_submit_without_manual_checker_uses_auto_resolve(api, maker, checker, approver):
    mid = _draft_by(api, maker)
    api.force_authenticate(maker)
    resp = api.post(f"/api/v1/memos/{mid}/submit/", {}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["current_reviewer"] is not None  # auto-resolved to a checker


@pytest.mark.django_db
def test_submit_with_invalid_checker_role_returns_400(api, maker, approver, checker, django_user_model):
    # Memo-approval-eligible roles (Dept Head / HR / Admin) are all valid checkers
    # now; a plain Maker is NOT. Use a second maker as the invalid assignee.
    other_maker = django_user_model.objects.create_user(
        username="maker2", email="maker2@nif.test", password="pass12345",
        role="maker", first_name="Second", last_name="Maker",
    )
    api.force_authenticate(maker)
    mid = _draft_by(api, maker)
    resp = api.post(f"/api/v1/memos/{mid}/submit/", {"override_reviewer_id": str(other_maker.id)}, format="json")
    assert resp.status_code == 400

    # An HR (approver) IS now accepted as the checker (memo-approval-eligible).
    mid2 = _draft_by(api, maker)
    ok = api.post(f"/api/v1/memos/{mid2}/submit/", {"override_reviewer_id": str(approver.id)}, format="json")
    assert ok.status_code == 200


@pytest.mark.django_db
def test_submit_with_self_as_checker_returns_400(api, checker, approver):
    # A checker authors a memo and tries to assign themselves as its checker.
    mid = _draft_by(api, checker)
    api.force_authenticate(checker)
    resp = api.post(f"/api/v1/memos/{mid}/submit/", {"override_reviewer_id": str(checker.id)}, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_submit_with_inactive_checker_returns_400(api, maker, checker):
    inactive = User.objects.create_user(
        username="inactive_chk", email="ic@nif.test", password="pass12345",
        role=User.Roles.CHECKER, is_active=False,
    )
    mid = _draft_by(api, maker)
    api.force_authenticate(maker)
    resp = api.post(f"/api/v1/memos/{mid}/submit/", {"override_reviewer_id": str(inactive.id)}, format="json")
    assert resp.status_code == 400


# --- available-* dropdown endpoints (H5: search-gated) ----------------------
@pytest.mark.django_db
def test_available_checkers_endpoint_returns_only_checkers(api, maker, checker, other_checker, approver):
    api.force_authenticate(maker)
    # Fixtures name checkers "Checker1"/"Checker2"; search hits both, not approver.
    resp = api.get("/api/v1/memos/available-checkers/", {"search": "checker"})
    assert resp.status_code == 200
    ids = {str(u["id"]) for u in resp.data}
    assert str(checker.id) in ids and str(other_checker.id) in ids
    assert str(approver.id) not in ids


@pytest.mark.django_db
def test_available_approvers_endpoint_returns_only_approvers(api, maker, approver, checker):
    api.force_authenticate(maker)
    resp = api.get("/api/v1/memos/available-approvers/", {"search": "approver"})
    assert resp.status_code == 200
    ids = {str(u["id"]) for u in resp.data}
    assert str(approver.id) in ids
    assert str(checker.id) not in ids
