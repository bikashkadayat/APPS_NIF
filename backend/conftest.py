import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _notifications_sync(settings):
    """
    Send notification emails synchronously in tests so background threads never
    race the shared mail.outbox (or the sqlite connection). Production keeps the
    async thread behaviour (NOTIFICATIONS_RUN_SYNC defaults False).
    """
    settings.NOTIFICATIONS_RUN_SYNC = True


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    """
    H6 adds global DRF throttling backed by the cache. Reset it around every
    test so accumulated request counts never leak between tests and trip 429s.
    """
    cache.clear()
    yield
    cache.clear()
