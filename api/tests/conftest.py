import pytest

from app.helpers import ratelimit


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Every test starts with empty rate-limit counters."""
    for limiter in (ratelimit.CHAT_PER_MINUTE, ratelimit.CHAT_PER_DAY, ratelimit.CHAT_GLOBAL_PER_DAY):
        limiter.reset()
    yield
