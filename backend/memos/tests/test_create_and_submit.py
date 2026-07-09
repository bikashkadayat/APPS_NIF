"""M2: create-and-submit is atomic - a failed submit leaves no orphaned draft."""
import pytest

from memos.models import Memo


def _payload():
    return {"title": "Atomic", "subject": "S", "body": "<p>b</p>",
            "memo_type": "general", "priority": "normal"}


@pytest.mark.django_db
def test_create_and_submit_rolls_back_on_failure(api, maker):
    # No checker exists, so submit fails; the draft must NOT be persisted.
    api.force_authenticate(maker)
    before = Memo.objects.count()
    resp = api.post("/api/v1/memos/create-and-submit/", _payload(), format="json")
    assert resp.status_code == 400
    assert Memo.objects.count() == before  # rolled back, no orphan draft


@pytest.mark.django_db
def test_create_and_submit_succeeds_with_checker(api, maker, checker):
    api.force_authenticate(maker)
    resp = api.post("/api/v1/memos/create-and-submit/", _payload(), format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["status"] == "submitted"
    assert resp.data["current_reviewer"]["id"] == str(checker.id)


@pytest.mark.django_db
def test_create_and_submit_honours_override(api, maker, checker, other_checker):
    api.force_authenticate(maker)
    payload = {**_payload(), "override_reviewer_id": str(other_checker.id)}
    resp = api.post("/api/v1/memos/create-and-submit/", payload, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["current_reviewer"]["id"] == str(other_checker.id)
