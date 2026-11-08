"""Tool definitions the model sees, and the executor that runs them through the tools API.

The agent never touches the database or Twilio directly: every action is an HTTP call to the
tools API, so it is validated, logged and testable in one place.
"""
import json
from dataclasses import dataclass

import httpx

from app.agent.store import ConversationStore


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOL_DEFINITIONS = [
    _tool(
        "get_customer",
        "Look up a customer by phone number or account number. Provide exactly one. "
        "Returns their customer id, name, service type, and service area (area_id, area_name).",
        {
            "phone": {"type": "string", "description": "Phone number in any format, e.g. 868-555-1000"},
            "account_no": {"type": "string", "description": "Account number, e.g. ACC-100001"},
        },
        [],
    ),
    _tool(
        "check_outages",
        "Check for active outages in a service area. has_active_outage says whether a known outage "
        "covers it; each outage has a cause, minutes_until_eta and eta_overdue.",
        {
            "area_id": {"type": "integer", "description": "area_id from get_customer"},
            "service_type": {
                "type": "string",
                "enum": ["fibre", "dsl", "mobile", "fixed_wireless"],
                "description": "The customer's service_type from get_customer",
            },
        },
        ["area_id", "service_type"],
    ),
    _tool(
        "create_ticket",
        "Open a fault ticket when no known outage explains the customer's problem. "
        "Returns the ticket, including its id (the ticket number to give the customer).",
        {
            "customer_id": {"type": "integer"},
            "category": {"type": "string", "enum": ["no_service", "slow_speed", "intermittent", "other"]},
            "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            "summary": {
                "type": "string",
                "description": "10-1000 characters, written for a field technician",
            },
        },
        ["customer_id", "category", "priority", "summary"],
    ),
    _tool(
        "send_sms",
        "Text the customer an update at the phone number on their account. Keep it under 160 characters.",
        {
            "customer_id": {"type": "integer"},
            "body": {"type": "string"},
        },
        ["customer_id", "body"],
    ),
    _tool(
        "escalate_to_human",
        "Hand the conversation to a human care agent instead of taking further action. "
        "Use for upset customers, out-of-scope requests, or when you are not confident.",
        {
            "reason": {
                "type": "string",
                "enum": ["upset_customer", "asked_for_human", "out_of_scope", "low_confidence",
                         "safety_or_critical", "tool_failure"],
            },
            "summary": {
                "type": "string",
                "description": "What the human agent needs to know, in two or three sentences",
            },
        },
        ["reason", "summary"],
    ),
]


@dataclass
class ToolResult:
    content: str
    is_error: bool = False


class ToolExecutor:
    """Runs one tool call against the tools API on behalf of a conversation."""

    def __init__(self, api: httpx.Client, store: ConversationStore):
        self.api = api
        self.store = store

    def run(self, name: str, args: dict) -> ToolResult:
        handler = getattr(self, f"_{name}", None)
        if handler is None:
            return ToolResult(f"Unknown tool '{name}'.", is_error=True)
        try:
            return handler(**args)
        except httpx.HTTPError as exc:
            return ToolResult(f"Tools API unreachable: {exc}", is_error=True)
        except TypeError as exc:  # unexpected arguments
            return ToolResult(f"Invalid arguments for {name}: {exc}", is_error=True)

    @staticmethod
    def _result(r: httpx.Response) -> ToolResult:
        if r.is_success:
            return ToolResult(r.text)
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        return ToolResult(f"HTTP {r.status_code}: {json.dumps(detail)}", is_error=True)

    def _get_customer(self, phone: str | None = None, account_no: str | None = None) -> ToolResult:
        params = {k: v for k, v in {"phone": phone, "account_no": account_no}.items() if v}
        result = self._result(self.api.get("/customers/lookup", params=params))
        if not result.is_error:
            self.store.set_customer(json.loads(result.content)["id"])
        return result

    def _check_outages(self, area_id: int, service_type: str) -> ToolResult:
        return self._result(self.api.get("/outages", params={"area_id": area_id, "service_type": service_type}))

    def _create_ticket(self, customer_id: int, category: str, priority: str, summary: str) -> ToolResult:
        return self._result(self.api.post("/tickets", json={
            "customer_id": customer_id, "category": category, "priority": priority,
            "summary": summary, "conversation_id": self.store.conversation_id,
        }))

    def _send_sms(self, customer_id: int, body: str) -> ToolResult:
        return self._result(self.api.post("/sms", json={"customer_id": customer_id, "body": body}))

    def _escalate_to_human(self, reason: str, summary: str) -> ToolResult:
        ticket_id = None
        customer_id = self.store.customer_id()
        if customer_id is not None:
            ticket = self._result(self.api.post("/tickets", json={
                "customer_id": customer_id, "category": "escalation", "priority": "high",
                "summary": f"[{reason}] {summary}", "conversation_id": self.store.conversation_id,
            }))
            if not ticket.is_error:
                ticket_id = json.loads(ticket.content)["id"]
        self.store.escalate(reason=reason, summary=summary, ticket_id=ticket_id)
        return ToolResult(json.dumps({
            "escalated": True, "ticket_id": ticket_id,
            "next": "Tell the customer a member of the team will follow up. Take no further action.",
        }))
