"""M4: escalation of financial/urgent memos picks a deterministic approver."""
import pytest
from django.utils import timezone

from memos.models import Memo
from memos.services import generate_memo_number, resolve_next_approver
from users.models import User


def _admin(username, joined):
    u = User.objects.create_user(username=username, email=f"{username}@nif.test",
                                 password="pass12345", role=User.Roles.ADMIN)
    User.objects.filter(pk=u.pk).update(date_joined=joined)
    return User.objects.get(pk=u.pk)


@pytest.mark.django_db
def test_escalation_is_deterministic(maker):
    now = timezone.now()
    younger = _admin("admin_new", now)
    older = _admin("admin_old", now - timezone.timedelta(days=100))
    memo = Memo.objects.create(
        title="Big spend", subject="S", body="<p>b</p>",
        memo_type=Memo.MemoType.FINANCIAL, status=Memo.Status.SUBMITTED,
        created_by=maker, memo_number=generate_memo_number(Memo.MemoType.FINANCIAL),
    )
    # Always the oldest admin, regardless of insertion order / repeated calls.
    assert resolve_next_approver(memo).id == older.id
    assert resolve_next_approver(memo).id == older.id
    assert older.id != younger.id
