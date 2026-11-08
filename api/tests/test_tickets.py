import pytest
from fastapi.testclient import TestClient

from app.helpers import db
from app.helpers.auth import service_headers
from app.main import app

client = TestClient(app, headers=service_headers())

KAVITA_ID = 1  # first seeded customer


@pytest.fixture
def created_ids():
    """Collects ids of tickets a test creates and deletes them afterwards."""
    ids: list[int] = []
    yield ids
    if ids:
        with db() as conn:
            conn.execute("DELETE FROM tickets WHERE id = ANY(%s)", (ids,))


def post_ticket(created_ids, **overrides):
    payload = {
        "customer_id": KAVITA_ID,
        "category": "no_service",
        "summary": "Fibre internet down since this morning; no known outage in Port of Spain.",
        **overrides,
    }
    r = client.post("/tickets", json=payload)
    if r.status_code == 201:
        created_ids.append(r.json()["id"])
    return r


def test_creates_open_ticket_with_defaults(created_ids):
    r = post_ticket(created_ids)
    assert r.status_code == 201
    body = r.json()
    assert body["customer_id"] == KAVITA_ID
    assert body["category"] == "no_service"
    assert body["priority"] == "normal"
    assert body["status"] == "open"
    assert body["conversation_id"] is None

    with db() as conn:
        row = conn.execute("SELECT summary FROM tickets WHERE id = %s", (body["id"],)).fetchone()
    assert row["summary"].startswith("Fibre internet down")


def test_accepts_priority_and_conversation(created_ids):
    with db() as conn:
        conv_id = conn.execute(
            "INSERT INTO conversations (customer_id) VALUES (%s) RETURNING id", (KAVITA_ID,)
        ).fetchone()["id"]
    try:
        r = post_ticket(created_ids, priority="high", category="escalation", conversation_id=conv_id)
        assert r.status_code == 201
        assert r.json()["priority"] == "high"
        assert r.json()["conversation_id"] == conv_id
    finally:
        with db() as conn:
            conn.execute("DELETE FROM tickets WHERE conversation_id = %s", (conv_id,))
            conn.execute("DELETE FROM conversations WHERE id = %s", (conv_id,))


def test_unknown_customer_returns_404(created_ids):
    assert post_ticket(created_ids, customer_id=99999).status_code == 404


def test_unknown_conversation_returns_404(created_ids):
    assert post_ticket(created_ids, conversation_id=99999).status_code == 404


@pytest.mark.parametrize("bad", [
    {"category": "billing"},       # not a valid category
    {"priority": "urgent"},        # not a valid priority
    {"summary": "down"},           # too short to be useful to the field team
    {"customer_id": None},         # required
])
def test_rejects_invalid_input(created_ids, bad):
    assert post_ticket(created_ids, **bad).status_code == 422
