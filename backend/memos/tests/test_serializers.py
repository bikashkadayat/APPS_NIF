import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from memos.models import Memo, MemoApprovalStep
from memos.serializers import (
    MemoActionSerializer,
    MemoCreateSerializer,
    MemoDetailSerializer,
    MAX_ATTACHMENT_SIZE,
)


@pytest.mark.django_db
def test_create_serializer_accepts_valid_payload():
    serializer = MemoCreateSerializer(data={
        "title": "Test memo",
        "subject": "Subject",
        "body": "Body text",
        "memo_type": Memo.MemoType.INTERNAL,
        "priority": Memo.Priority.NORMAL,
    })
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_create_serializer_rejects_oversized_attachment():
    big = SimpleUploadedFile(
        "big.pdf", b"x" * (MAX_ATTACHMENT_SIZE + 1), content_type="application/pdf"
    )
    serializer = MemoCreateSerializer(data={
        "title": "Test", "subject": "S", "body": "B",
        "memo_type": Memo.MemoType.GENERAL, "attachment": big,
    })
    assert not serializer.is_valid()
    assert "attachment" in serializer.errors


@pytest.mark.django_db
def test_create_serializer_rejects_disallowed_extension():
    bad = SimpleUploadedFile("virus.exe", b"data", content_type="application/octet-stream")
    serializer = MemoCreateSerializer(data={
        "title": "Test", "subject": "S", "body": "B",
        "memo_type": Memo.MemoType.GENERAL, "attachment": bad,
    })
    assert not serializer.is_valid()
    assert "attachment" in serializer.errors


@pytest.mark.django_db
def test_create_serializer_accepts_allowed_extension():
    ok = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 data", content_type="application/pdf")
    serializer = MemoCreateSerializer(data={
        "title": "Test", "subject": "S", "body": "B",
        "memo_type": Memo.MemoType.GENERAL, "attachment": ok,
    })
    assert serializer.is_valid(), serializer.errors


def test_action_serializer_requires_comment_for_reject():
    serializer = MemoActionSerializer(data={"action": MemoApprovalStep.Action.REJECTED, "comment": "short"})
    assert not serializer.is_valid()
    assert "comment" in serializer.errors


def test_action_serializer_requires_comment_for_return():
    serializer = MemoActionSerializer(data={"action": MemoApprovalStep.Action.RETURNED, "comment": ""})
    assert not serializer.is_valid()
    assert "comment" in serializer.errors


def test_action_serializer_allows_reject_with_long_comment():
    serializer = MemoActionSerializer(data={
        "action": MemoApprovalStep.Action.REJECTED,
        "comment": "This does not meet policy requirements.",
    })
    assert serializer.is_valid(), serializer.errors


def test_action_serializer_allows_review_without_comment():
    serializer = MemoActionSerializer(data={"action": MemoApprovalStep.Action.REVIEWED})
    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_detail_serializer_capability_flags_for_author(draft_memo, maker):
    class _Req:
        user = None

    req = _Req()
    req.user = maker
    data = MemoDetailSerializer(draft_memo, context={"request": req}).data
    assert data["can_edit"] is True
    assert data["can_submit"] is True
    assert data["can_review"] is False
    assert data["created_by"]["email"] == maker.email
    # list-style nested user should not leak password or full model
    # (employee_id added for the detailed-review panel: "Created By ... + employee ID").
    assert set(data["created_by"].keys()) == {"id", "full_name", "email", "role", "department", "employee_id"}
