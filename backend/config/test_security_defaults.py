"""H6: fail-closed permissions, throttling, and prod-safe settings guards."""
import pytest
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings
from rest_framework.test import APIClient


@pytest.fixture
def api():
    return APIClient()


def test_default_permission_is_authenticated():
    # Fail closed: any view that forgets permission_classes still needs auth.
    assert IsAuthenticated in api_settings.DEFAULT_PERMISSION_CLASSES


def test_global_throttles_configured():
    rates = api_settings.DEFAULT_THROTTLE_RATES
    assert rates.get("anon") and rates.get("user")
    scopes = {t.__name__ for t in api_settings.DEFAULT_THROTTLE_CLASSES}
    assert {"AnonRateThrottle", "UserRateThrottle"} <= scopes


@pytest.mark.django_db
def test_protected_endpoint_rejects_anonymous(api):
    # A representative authenticated endpoint must 401 without a token.
    assert api.get("/api/v1/memos/").status_code == 401


@pytest.mark.django_db
def test_public_endpoints_still_accessible(api):
    # Health is public.
    assert api.get("/api/v1/health/").status_code == 200
    # Login is reachable anonymously (bad creds -> 400/401, not a 403 lockout).
    resp = api.post("/api/v1/auth/login/",
                    {"email": "nobody@nif.test", "password": "wrong"}, format="json")
    assert resp.status_code in (400, 401)
    # Refresh is reachable anonymously (invalid token -> 401, not a permission 403).
    r2 = api.post("/api/v1/auth/refresh/", {"refresh": "not-a-token"}, format="json")
    assert r2.status_code in (400, 401)


@pytest.mark.django_db
def test_anon_throttle_enforced(api, monkeypatch):
    from rest_framework.throttling import AnonRateThrottle
    monkeypatch.setattr(AnonRateThrottle, "get_rate", lambda self: "2/min")
    codes = [api.get("/api/v1/health/").status_code for _ in range(4)]
    assert 429 in codes
