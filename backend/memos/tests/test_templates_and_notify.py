"""L1: template admin CRUD.  L3: notification failures logged at ERROR."""
import logging

import pytest

from memos.models import Memo, MemoTemplate
from memos.services import generate_memo_number, submit_memo


def _template_payload():
    return {"name": "Ops Notice", "memo_type": "general",
            "subject_template": "Ops: Topic", "body_template": "<p>Body</p>"}


# --- L1: template CRUD ------------------------------------------------------
@pytest.mark.django_db
def test_admin_can_create_template(api, admin):
    api.force_authenticate(admin)
    resp = api.post("/api/v1/memo-templates/", _template_payload(), format="json")
    assert resp.status_code == 201, resp.data
    assert MemoTemplate.objects.filter(name="Ops Notice").exists()


@pytest.mark.django_db
def test_non_admin_cannot_write_template(api, maker):
    api.force_authenticate(maker)
    assert api.post("/api/v1/memo-templates/", _template_payload(), format="json").status_code == 403


@pytest.mark.django_db
def test_authenticated_can_read_active_templates(api, maker):
    MemoTemplate.objects.create(name="A", memo_type="general",
                                subject_template="s", body_template="b", is_active=True)
    api.force_authenticate(maker)
    resp = api.get("/api/v1/memo-templates/")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.data["results"]}
    assert "A" in names  # (plus the 3 seeded defaults)


@pytest.mark.django_db
def test_admin_can_update_and_delete_template(api, admin):
    t = MemoTemplate.objects.create(name="Old", memo_type="general",
                                    subject_template="s", body_template="b")
    api.force_authenticate(admin)
    up = api.patch(f"/api/v1/memo-templates/{t.id}/", {"name": "New"}, format="json")
    assert up.status_code == 200 and up.data["name"] == "New"
    assert api.delete(f"/api/v1/memo-templates/{t.id}/").status_code == 204


# --- L3: notification failure logging ---------------------------------------
@pytest.mark.django_db
def test_notification_failure_logged_at_error(maker, checker, monkeypatch, caplog):
    memo = Memo.objects.create(
        title="T", subject="S", body="<p>b</p>", memo_type=Memo.MemoType.GENERAL,
        status=Memo.Status.DRAFT, created_by=maker,
        memo_number=generate_memo_number(Memo.MemoType.GENERAL),
    )

    def _boom(*a, **k):
        raise RuntimeError("dispatcher down")

    monkeypatch.setattr("notifications.dispatcher.notify", _boom)
    with caplog.at_level(logging.ERROR, logger="memos"):
        # The transition must still succeed despite the notify failure.
        result = submit_memo(memo, maker)
    assert result.status == Memo.Status.SUBMITTED
    assert any("memo notification failed" in r.message and r.levelno == logging.ERROR
               for r in caplog.records)
