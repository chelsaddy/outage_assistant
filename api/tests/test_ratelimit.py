"""Rate limits on POST /chat, and the limiter itself."""
import pytest
from fastapi.testclient import TestClient

from app.helpers import ratelimit
from app.helpers.auth import dashboard_headers
from app.helpers.ratelimit import RateLimiter, check_and_record
from app.main import app

customer = TestClient(app)
staff = TestClient(app, headers=dashboard_headers())

# A message to a conversation that doesn't exist: counted, then 404, and no model call.
NO_SUCH_CONVERSATION = {"message": "hi", "conversation_id": 999999}


@pytest.fixture
def limits(monkeypatch):
    """Small limits so tests hit them quickly."""
    def set_limits(per_minute=3, per_day=100, global_per_day=1000):
        monkeypatch.setattr(ratelimit.CHAT_PER_MINUTE, "limit", per_minute)
        monkeypatch.setattr(ratelimit.CHAT_PER_DAY, "limit", per_day)
        monkeypatch.setattr(ratelimit.CHAT_GLOBAL_PER_DAY, "limit", global_per_day)
    return set_limits


def test_limiter_allows_up_to_limit_then_waits_for_window():
    rl = RateLimiter(limit=2, window=60)
    rl.record("a", now=0)
    rl.record("a", now=10)
    assert rl.retry_after("a", now=20) == 40           # oldest hit expires at t=60
    assert rl.retry_after("b", now=20) == 0            # other keys are separate
    assert rl.retry_after("a", now=60) == 0            # window slid past the first hit


def test_check_and_record_records_nothing_when_any_limit_is_hit():
    roomy, full = RateLimiter(10, 60), RateLimiter(1, 60)
    full.record("k")
    assert check_and_record([(roomy, "k"), (full, "k")]) > 0
    assert roomy.retry_after("k") == 0 and len(roomy._hits["k"]) == 0


def test_customer_is_limited_per_minute_with_retry_after(limits):
    limits(per_minute=3)
    codes = [customer.post("/chat", json=NO_SUCH_CONVERSATION).status_code for _ in range(4)]
    assert codes == [404, 404, 404, 429]
    r = customer.post("/chat", json=NO_SUCH_CONVERSATION)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1


def test_customer_is_limited_per_day(limits):
    limits(per_minute=100, per_day=2)
    codes = [customer.post("/chat", json=NO_SUCH_CONVERSATION).status_code for _ in range(3)]
    assert codes == [404, 404, 429]


def test_staff_skip_per_client_limits(limits):
    limits(per_minute=1)
    codes = [staff.post("/chat", json=NO_SUCH_CONVERSATION).status_code for _ in range(5)]
    assert codes == [404] * 5


def test_global_cap_applies_to_everyone(limits):
    limits(per_minute=100, global_per_day=2)
    assert staff.post("/chat", json=NO_SUCH_CONVERSATION).status_code == 404
    assert customer.post("/chat", json=NO_SUCH_CONVERSATION).status_code == 404
    assert staff.post("/chat", json=NO_SUCH_CONVERSATION).status_code == 429
    assert customer.post("/chat", json=NO_SUCH_CONVERSATION).status_code == 429
