"""Each caller's token only opens its own routes; public endpoints stay open."""
import pytest
from fastapi.testclient import TestClient

from app.helpers.auth import dashboard_headers, service_headers
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


# --- dashboard endpoints: dashboard token only ------------------------------------------------

DASHBOARD_CALLS = [
    ("get", "/conversations", {}),
    ("get", "/conversations/1", {}),
    ("get", "/tickets", {}),
    ("patch", "/tickets/1", {"json": {"status": "open"}}),
    ("get", "/sms", {}),
]


@pytest.mark.parametrize("method,path,kwargs", DASHBOARD_CALLS)
def test_dashboard_endpoints_require_token(method, path, kwargs):
    assert getattr(anon, method)(path, **kwargs).status_code == 401


@pytest.mark.parametrize("method,path,kwargs", DASHBOARD_CALLS)
def test_agent_token_cannot_read_dashboard(method, path, kwargs):
    assert getattr(anon, method)(path, headers=service_headers(), **kwargs).status_code == 401


@pytest.mark.parametrize("method,path,kwargs", TOOL_CALLS)
def test_dashboard_token_cannot_call_tools(method, path, kwargs):
    assert getattr(anon, method)(path, headers=dashboard_headers(), **kwargs).status_code == 401


def test_dashboard_token_reads_dashboard():
    assert anon.get("/tickets", headers=dashboard_headers()).status_code == 200
