"""H5: the assignee directory is search-gated, PII-free and throttled."""
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_available_checkers_requires_search(api, maker, checker, other_checker):
    api.force_authenticate(maker)
    # No search term -> empty, so the endpoint cannot dump the whole roster.
    assert api.get("/api/v1/memos/available-checkers/").data == []
    # A single char is still below the minimum.
    assert api.get("/api/v1/memos/available-checkers/", {"search": "c"}).data == []
    # Two chars -> results.
    resp = api.get("/api/v1/memos/available-checkers/", {"search": "ch"})
    assert len(resp.data) >= 1


@pytest.mark.django_db
def test_email_not_exposed_in_directory(api, maker, checker):
    api.force_authenticate(maker)
    resp = api.get("/api/v1/memos/available-checkers/", {"search": "checker"})
    assert resp.status_code == 200 and resp.data
    row = resp.data[0]
    assert set(row.keys()) == {"id", "full_name", "department"}
    assert "email" not in row and "role" not in row


@pytest.mark.django_db
def test_directory_search_does_not_match_email(api, maker, checker):
    # checker email is checker1@nif.test; searching the email must not leak them.
    api.force_authenticate(maker)
    resp = api.get("/api/v1/memos/available-checkers/", {"search": "nif.test"})
    assert resp.data == []


@pytest.mark.django_db
def test_available_checkers_throttled(api, maker, checker, monkeypatch):
    # Pin a tiny rate deterministically (independent of DRF settings caching).
    from memos.views import MemoDirectoryThrottle
    monkeypatch.setattr(MemoDirectoryThrottle, "get_rate", lambda self: "3/min")
    api.force_authenticate(maker)
    codes = [api.get("/api/v1/memos/available-checkers/", {"search": "ch"}).status_code
             for _ in range(5)]
    assert codes.count(200) == 3  # first 3 allowed
    assert 429 in codes  # then rate-limited within the window
