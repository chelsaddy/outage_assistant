"""Tool endpoints reject callers without the service token; public endpoints stay open."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

anon = TestClient(app)

TOOL_CALLS = [
    ("get", "/customers/lookup", {"params": {"phone": "868-555-1000"}}),
    ("get", "/outages", {"params": {"area_id": 1}}),
    ("post", "/tickets", {"json": {"customer_id": 1, "category": "other", "summary": "Should never be created."}}),
    ("post", "/sms", {"json": {"customer_id": 1, "body": "Should never be sent."}}),
]


@pytest.mark.parametrize("method,path,kwargs", TOOL_CALLS)
def test_tool_endpoints_require_token(method, path, kwargs):
    r = getattr(anon, method)(path, **kwargs)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("method,path,kwargs", TOOL_CALLS)
def test_tool_endpoints_reject_wrong_token(method, path, kwargs):
    r = getattr(anon, method)(path, headers={"Authorization": "Bearer not-the-token"}, **kwargs)
    assert r.status_code == 401


def test_health_stays_public():
    assert anon.get("/health").status_code == 200
