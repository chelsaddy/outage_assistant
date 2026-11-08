"""Tools API for the Telecom Outage Assistant.

The agent calls these endpoints as tools:
  GET  /customers/lookup   -> get_customer
  GET  /outages?area_id=   -> check_outages
  POST /tickets            -> create_ticket
  POST /sms                -> send_sms

and the care agent is exposed at:
  POST /chat               -> one customer message in, the agent's reply (and its trace) out

and the dashboard reads from app/dashboard.py (conversations, ticket queue, SMS outbox).
"""
import anthropic
from fastapi import Depends, FastAPI, HTTPException, Query

from app.agent import ConversationNotFound, run_turn
from app.dashboard import router as dashboard_router
from app.helpers import db, normalize_phone, send_sms_message
from app.helpers.auth import require_service_token
from app.models import ChatRequest, ChatResponse, Customer, OutageCheck, ServiceType, SmsCreate, SmsMessage, Ticket, TicketCreate

app = FastAPI(title="Telecom Outage Assistant: Tools API")
app.include_router(dashboard_router)

# Tool endpoints are for the agent only: they require the service token.
AGENT_ONLY = [Depends(require_service_token)]


@app.get("/health")
def health():
    with db() as conn:
        customers = conn.execute("SELECT count(*) AS n FROM customers").fetchone()["n"]
        active = conn.execute("SELECT count(*) AS n FROM outages WHERE status = 'active'").fetchone()["n"]
    return {"status": "ok", "customers": customers, "active_outages": active}


@app.get("/customers/lookup", response_model=Customer, dependencies=AGENT_ONLY)
def get_customer(
    phone: str | None = Query(None, description="Customer phone number, any common format"),
    account_no: str | None = Query(None, description="Account number, e.g. ACC-100001"),
):
    """Find one customer by phone number or account number."""
    if bool(phone) == bool(account_no):
        raise HTTPException(422, "Provide exactly one of 'phone' or 'account_no'.")

    if phone:
        where, value = "c.phone = %s", normalize_phone(phone)
    else:
        where, value = "c.account_no = %s", account_no.strip().upper()

    with db() as conn:
        row = conn.execute(
            f"""
            SELECT c.id, c.account_no, c.full_name, c.phone, c.service_type, c.status,
                   c.area_id, a.name AS area_name, a.region
            FROM customers c JOIN service_areas a ON a.id = c.area_id
            WHERE {where}
            """,
            (value,),
        ).fetchone()

    if row is None:
        raise HTTPException(404, "No customer found with those details.")
    return row


@app.get("/outages", response_model=OutageCheck, dependencies=AGENT_ONLY)
def check_outages(
    area_id: int = Query(..., description="Service area id, from get_customer"),
    service_type: ServiceType | None = Query(None, description="Only outages affecting this service"),
):
    """List active outages in an area, optionally for one service type."""
    with db() as conn:
        area = conn.execute("SELECT id, name FROM service_areas WHERE id = %s", (area_id,)).fetchone()
        if area is None:
            raise HTTPException(404, f"No service area with id {area_id}.")

        outages = conn.execute(
            """
            SELECT id, service_type, cause, started_at, eta,
                   floor(extract(epoch FROM eta - now()) / 60)::int AS minutes_until_eta,
                   coalesce(eta < now(), false) AS eta_overdue
            FROM outages
            WHERE area_id = %(area_id)s
              AND status = 'active'
              AND (%(service_type)s::text IS NULL OR service_type = %(service_type)s)
            ORDER BY started_at
            """,
            {"area_id": area_id, "service_type": service_type},
        ).fetchall()

    return {
        "area_id": area["id"],
        "area_name": area["name"],
        "service_type": service_type,
        "has_active_outage": bool(outages),
        "outages": outages,
    }


@app.post("/tickets", response_model=Ticket, status_code=201, dependencies=AGENT_ONLY)
def create_ticket(ticket: TicketCreate):
    """Open a fault ticket for a customer (used when no known outage explains the problem)."""
    with db() as conn:
        if conn.execute("SELECT 1 FROM customers WHERE id = %s", (ticket.customer_id,)).fetchone() is None:
            raise HTTPException(404, f"No customer with id {ticket.customer_id}.")
        if ticket.conversation_id is not None and conn.execute(
            "SELECT 1 FROM conversations WHERE id = %s", (ticket.conversation_id,)
        ).fetchone() is None:
            raise HTTPException(404, f"No conversation with id {ticket.conversation_id}.")

        return conn.execute(
            """
            INSERT INTO tickets (customer_id, conversation_id, category, priority, summary)
            VALUES (%(customer_id)s, %(conversation_id)s, %(category)s, %(priority)s, %(summary)s)
            RETURNING id, customer_id, conversation_id, category, priority, summary, status, created_at
            """,
            {**ticket.model_dump(), "summary": ticket.summary.strip()},
        ).fetchone()


@app.post("/sms", response_model=SmsMessage, status_code=201, dependencies=AGENT_ONLY)
def send_sms(sms: SmsCreate):
    """Text a customer an update. Every attempt is recorded, including failures."""
    body = sms.body.strip()
    with db() as conn:
        customer = conn.execute("SELECT phone FROM customers WHERE id = %s", (sms.customer_id,)).fetchone()
        if customer is None:
            raise HTTPException(404, f"No customer with id {sms.customer_id}.")

    result = send_sms_message(customer["phone"], body)

    with db() as conn:
        row = conn.execute(
            """
            INSERT INTO sms_messages (customer_id, to_phone, body, status, provider_sid)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, customer_id, to_phone, body, status, provider_sid, created_at
            """,
            (sms.customer_id, result.sent_to, body, result.status, result.provider_sid),
        ).fetchone()
    return {**row, "error": result.error}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Send a customer message to the agent. Omit conversation_id to start a new conversation."""
    try:
        return run_turn(req.conversation_id, req.message)
    except ConversationNotFound:
        raise HTTPException(404, f"No conversation with id {req.conversation_id}.")
    except anthropic.APIConnectionError:
        raise HTTPException(503, "Could not reach the model API. Try again shortly.")
    except anthropic.RateLimitError:
        raise HTTPException(503, "The model API is rate limited. Try again shortly.")
    except anthropic.APIStatusError as exc:
        raise HTTPException(502, f"Model API error ({exc.status_code}).")
