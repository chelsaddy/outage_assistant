import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app.helpers import db
from app.helpers.auth import dashboard_headers
from app.main import app

client = TestClient(app, headers=dashboard_headers())

KAVITA_ID = 1  # first seeded customer


@pytest.fixture
def conversation():
    """A conversation with a short trace and one linked ticket, removed afterwards."""
    with db() as conn:
        cid = conn.execute(
            "INSERT INTO conversations (customer_id) VALUES (%s) RETURNING id", (KAVITA_ID,)
        ).fetchone()["id"]
        steps = [
            ("user_message", None, {"text": "My internet is down"}),
            ("tool_call", "get_customer", {"tool_use_id": "t1", "input": {"phone": "555-1000"}}),
            ("tool_result", "get_customer", {"tool_use_id": "t1", "content": "{}", "is_error": False}),
            ("assistant_message", None, {"content": [], "text": "Sorry to hear that, checking now."}),
        ]
        for n, (kind, tool, payload) in enumerate(steps, start=1):
            conn.execute(
                "INSERT INTO agent_steps (conversation_id, step_no, kind, tool_name, payload) VALUES (%s, %s, %s, %s, %s)",
                (cid, n, kind, tool, Jsonb(payload)),
            )
        tid = conn.execute(
            """INSERT INTO tickets (customer_id, conversation_id, category, priority, summary)
               VALUES (%s, %s, 'no_service', 'high', 'Fibre down, no known outage in the area.') RETURNING id""",
            (KAVITA_ID, cid),
        ).fetchone()["id"]
    yield {"id": cid, "ticket_id": tid}
    with db() as conn:
        conn.execute("DELETE FROM tickets WHERE conversation_id = %s", (cid,))
        conn.execute("DELETE FROM agent_steps WHERE conversation_id = %s", (cid,))
        conn.execute("DELETE FROM conversations WHERE id = %s", (cid,))


def test_lists_conversations_with_summary(conversation):
    r = client.get("/conversations")
    assert r.status_code == 200
    row = next(c for c in r.json() if c["id"] == conversation["id"])
    assert row["customer_name"] is not None
    assert row["step_count"] == 4
    assert row["tool_calls"] == 1
    assert row["last_message"] == "Sorry to hear that, checking now."


def test_filters_conversations_by_status(conversation):
    ids = [c["id"] for c in client.get("/conversations", params={"status": "escalated"}).json()]
    assert conversation["id"] not in ids
    assert client.get("/conversations", params={"status": "bogus"}).status_code == 422


def test_conversation_detail_has_steps_and_tickets(conversation):
    r = client.get(f"/conversations/{conversation['id']}")
    assert r.status_code == 200
    body = r.json()
    assert [s["kind"] for s in body["steps"]] == ["user_message", "tool_call", "tool_result", "assistant_message"]
    assert [t["id"] for t in body["tickets"]] == [conversation["ticket_id"]]
    assert body["customer_id"] == KAVITA_ID


def test_unknown_conversation_is_404():
    assert client.get("/conversations/999999").status_code == 404


def test_ticket_queue_puts_high_priority_first(conversation):
    queue = client.get("/tickets", params={"status": "open"}).json()
    priorities = [t["priority"] for t in queue]
    assert priorities == sorted(priorities, key=["high", "normal", "low"].index)
    assert conversation["ticket_id"] in [t["id"] for t in queue]


def test_updates_ticket_status(conversation):
    tid = conversation["ticket_id"]
    r = client.patch(f"/tickets/{tid}", json={"status": "in_progress"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert tid not in [t["id"] for t in client.get("/tickets", params={"status": "open"}).json()]


def test_rejects_bad_ticket_updates(conversation):
    assert client.patch(f"/tickets/{conversation['ticket_id']}", json={"status": "done"}).status_code == 422
    assert client.patch("/tickets/999999", json={"status": "closed"}).status_code == 404


def test_sms_outbox_newest_first():
    with db() as conn:
        ids = [conn.execute(
            "INSERT INTO sms_messages (customer_id, to_phone, body, status) VALUES (%s, '+18685551000', %s, 'simulated') RETURNING id",
            (KAVITA_ID, f"test {i}"),
        ).fetchone()["id"] for i in range(2)]
    try:
        outbox = client.get("/sms", params={"limit": 2}).json()
        assert [m["id"] for m in outbox] == ids[::-1]
        assert outbox[0]["customer_name"] is not None
    finally:
        with db() as conn:
            conn.execute("DELETE FROM sms_messages WHERE id = ANY(%s)", (ids,))
