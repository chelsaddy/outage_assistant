import httpx
import pytest
from fastapi.testclient import TestClient

from app.helpers import db, sms as sms_helper
from app.main import app

client = TestClient(app)

KAVITA_ID, KAVITA_PHONE = 1, "+18685551000"
TWILIO_ENV = {"TWILIO_ACCOUNT_SID": "ACtest", "TWILIO_AUTH_TOKEN": "secret", "TWILIO_FROM_NUMBER": "+15005550006"}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    """Start every test with Twilio unconfigured, and delete any SMS rows it writes."""
    for key in [*TWILIO_ENV, "SMS_REDIRECT_TO"]:
        monkeypatch.delenv(key, raising=False)
    with db() as conn:
        before = conn.execute("SELECT coalesce(max(id), 0) AS n FROM sms_messages").fetchone()["n"]
    yield
    with db() as conn:
        conn.execute("DELETE FROM sms_messages WHERE id > %s", (before,))


@pytest.fixture
def twilio(monkeypatch):
    """Configure Twilio and capture outgoing requests instead of hitting the network."""
    for k, v in TWILIO_ENV.items():
        monkeypatch.setenv(k, v)
    calls = []

    def respond(status=201, json=None):
        def fake_post(to, body):
            calls.append({"to": to, "body": body})
            return httpx.Response(status, json=json or {"sid": "SM123", "status": "queued"})
        monkeypatch.setattr(sms_helper, "_twilio_post", fake_post)

    respond()
    return calls, respond


def send(**overrides):
    return client.post("/sms", json={"customer_id": KAVITA_ID, "body": "Your service is restored.", **overrides})


def test_simulated_when_twilio_not_configured():
    r = send()
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "simulated"
    assert body["to_phone"] == KAVITA_PHONE
    assert body["provider_sid"] is None

    with db() as conn:
        row = conn.execute("SELECT status, body FROM sms_messages WHERE id = %s", (body["id"],)).fetchone()
    assert row == {"status": "simulated", "body": "Your service is restored."}


def test_sends_via_twilio_when_configured(twilio):
    calls, _ = twilio
    body = send().json()
    assert body["status"] == "sent"
    assert body["provider_sid"] == "SM123"
    assert calls == [{"to": KAVITA_PHONE, "body": "Your service is restored."}]


def test_redirects_real_sms(twilio, monkeypatch):
    calls, _ = twilio
    monkeypatch.setenv("SMS_REDIRECT_TO", "+18680000000")
    body = send().json()
    assert calls[0]["to"] == "+18680000000"
    assert body["to_phone"] == "+18680000000"


def test_twilio_error_is_recorded_and_explained(twilio):
    _, respond = twilio
    respond(status=400, json={"message": "The 'To' number is not a valid phone number."})
    r = send()
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "failed"
    assert "not a valid phone number" in body["error"]


def test_unknown_customer_returns_404():
    assert send(customer_id=99999).status_code == 404


@pytest.mark.parametrize("bad", [{"body": ""}, {"body": "x" * 321}, {"customer_id": None}])
def test_rejects_invalid_input(bad):
    assert send(**bad).status_code == 422
