"""Agent loop tests with a scripted model: no API key or network needed.

Each test scripts the model's responses (tool calls, then a reply) and checks what the loop
does with them: tools run through the tools API, every step is logged, history is replayed,
and escalation hands the conversation to a person.
"""
import itertools

import pytest
from anthropic.types.beta import BetaMessage
from fastapi.testclient import TestClient

from app.agent import run_turn
from app.agent.prompt import MAX_ITERATIONS
from app.helpers import db
from app.helpers.auth import service_headers
from app.main import app

api = TestClient(app, headers=service_headers())

KAVITA = {"id": 1, "phone": "+18685551000", "area_id": 1}  # Port of Spain, fibre: active outage
ANDRE = {"id": 2, "phone": "+18685551001", "area_id": 2}   # Diego Martin, fibre: no outage

_ids = itertools.count(1)


def tool_use(name, **args):
    return {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": args}


def reply(text, stop_reason="end_turn"):
    return msg([{"type": "text", "text": text}], stop_reason)


def calls(*blocks):
    return msg(list(blocks), "tool_use")


def msg(content, stop_reason):
    return BetaMessage.model_validate({
        "id": f"msg_{next(_ids)}", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    })


class ScriptedLLM:
    """Stands in for anthropic.Anthropic(): returns scripted responses, records each request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.beta = self
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.responses.pop(0)


def turn(llm, message="My internet is down", conversation_id=None):
    return run_turn(conversation_id, message, llm=llm, api=api)


@pytest.fixture(autouse=True)
def cleanup():
    tables = ["conversations", "tickets", "sms_messages"]
    with db() as conn:
        before = {t: conn.execute(f"SELECT coalesce(max(id), 0) AS n FROM {t}").fetchone()["n"] for t in tables}
    yield
    with db() as conn:
        conn.execute("DELETE FROM agent_steps WHERE conversation_id > %s", (before["conversations"],))
        conn.execute("DELETE FROM tickets WHERE id > %s", (before["tickets"],))
        conn.execute("DELETE FROM sms_messages WHERE id > %s", (before["sms_messages"],))
        conn.execute("DELETE FROM conversations WHERE id > %s", (before["conversations"],))


def test_outage_path_looks_up_checks_and_texts():
    llm = ScriptedLLM(
        calls(tool_use("get_customer", phone="868-555-1000")),
        calls(tool_use("check_outages", area_id=1, service_type="fibre")),
        calls(tool_use("send_sms", customer_id=1, body="Fibre outage in Port of Spain, back in ~2 hrs.")),
        reply("There's a fibre cut in Port of Spain; service should be back in about 2 hours."),
    )
    out = turn(llm, "Hi, my internet is down. My number is 868-555-1000")

    assert out["tools_called"] == ["get_customer", "check_outages", "send_sms"]
    assert out["reply"].startswith("There's a fibre cut")
    assert out["status"] == "open"
    assert [s["kind"] for s in out["steps"]] == [
        "user_message",
        "assistant_message", "tool_call", "tool_result",
        "assistant_message", "tool_call", "tool_result",
        "assistant_message", "tool_call", "tool_result",
        "assistant_message",
    ]
    assert not any(s["payload"].get("is_error") for s in out["steps"] if s["kind"] == "tool_result")

    # The second model call saw the first tool's result, paired with its tool_use id.
    second = llm.requests[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "user"]
    result = second[2]["content"][0]
    assert result["type"] == "tool_result" and result["tool_use_id"] == second[1]["content"][0]["id"]
    assert "Kavita Joseph" in result["content"]

    with db() as conn:
        conv = conn.execute("SELECT customer_id FROM conversations WHERE id = %s",
                            (out["conversation_id"],)).fetchone()
        sms = conn.execute("SELECT status FROM sms_messages ORDER BY id DESC LIMIT 1").fetchone()
    assert conv["customer_id"] == KAVITA["id"]
    assert sms["status"] == "simulated"


def test_no_outage_opens_ticket_linked_to_conversation():
    llm = ScriptedLLM(
        calls(tool_use("get_customer", account_no="ACC-100002")),
        calls(tool_use("check_outages", area_id=2, service_type="fibre")),
        calls(tool_use("create_ticket", customer_id=2, category="no_service", priority="normal",
                       summary="Fibre down since 8am in Diego Martin; router restarted, no change.")),
        reply("I've opened ticket for you."),
    )
    out = turn(llm)
    assert out["tools_called"] == ["get_customer", "check_outages", "create_ticket"]

    with db() as conn:
        ticket = conn.execute("SELECT customer_id, conversation_id, category FROM tickets ORDER BY id DESC LIMIT 1").fetchone()
    assert ticket == {"customer_id": 2, "conversation_id": out["conversation_id"], "category": "no_service"}


def test_tool_errors_go_back_to_the_model():
    llm = ScriptedLLM(
        calls(tool_use("get_customer", account_no="ACC-999999")),
        reply("I couldn't find that account. Could you check the number?"),
    )
    out = turn(llm)
    [result] = [s for s in out["steps"] if s["kind"] == "tool_result"]
    assert result["payload"]["is_error"] is True
    assert "404" in result["payload"]["content"]
    assert llm.requests[1]["messages"][-1]["content"][0]["is_error"] is True


def test_escalation_hands_off_and_stops_acting():
    llm = ScriptedLLM(
        calls(tool_use("get_customer", phone="5551000")),
        calls(tool_use("escalate_to_human", reason="upset_customer",
                       summary="Customer is very angry about repeated outages and wants a call back.")),
        reply("I'm sorry. A member of our team will call you shortly."),
    )
    out = turn(llm, "This is the THIRD time this month!! I want to speak to a manager")
    assert out["status"] == "escalated"
    assert "escalation" in [s["kind"] for s in out["steps"]]

    with db() as conn:
        ticket = conn.execute("SELECT category, priority, conversation_id FROM tickets ORDER BY id DESC LIMIT 1").fetchone()
    assert ticket == {"category": "escalation", "priority": "high", "conversation_id": out["conversation_id"]}

    # Follow-up messages are recorded but the model is not called again.
    idle = ScriptedLLM()
    follow = turn(idle, "Hello??", conversation_id=out["conversation_id"])
    assert idle.requests == []
    assert follow["status"] == "escalated"
    assert "care team" in follow["reply"]


def test_multi_turn_replays_history():
    first = turn(ScriptedLLM(reply("Sure, what's your phone or account number?")))
    llm = ScriptedLLM(reply("Thanks!"))
    turn(llm, "It's 868-555-1000", conversation_id=first["conversation_id"])
    sent = llm.requests[0]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
    assert sent[0]["content"] == "My internet is down"
    assert sent[2]["content"] == "It's 868-555-1000"


def test_refusal_escalates():
    out = turn(ScriptedLLM(msg([], "refusal")))
    assert out["status"] == "escalated"
    assert out["tools_called"] == []


def test_runaway_loop_escalates():
    llm = ScriptedLLM(*[calls(tool_use("check_outages", area_id=1, service_type="fibre"))
                        for _ in range(MAX_ITERATIONS)])
    out = turn(llm)
    assert len(llm.requests) == MAX_ITERATIONS
    assert out["status"] == "escalated"


def test_request_uses_tools_and_fallbacks():
    llm = ScriptedLLM(reply("Hi!"))
    turn(llm)
    req = llm.requests[0]
    assert {t["name"] for t in req["tools"]} == {
        "get_customer", "check_outages", "create_ticket", "send_sms", "escalate_to_human"}
    assert all(t["strict"] for t in req["tools"])
    assert req["fallbacks"] == "default"


def test_chat_endpoint_unknown_conversation():
    r = api.post("/chat", json={"message": "hi", "conversation_id": 999999})
    assert r.status_code == 404
