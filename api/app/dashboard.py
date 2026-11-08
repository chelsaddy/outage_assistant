"""Read endpoints for the dashboard: conversations with their trace, the ticket queue, the SMS outbox.

These are for people watching the agent, not for the agent itself, so none of them are tools.
Every route requires the dashboard token (see app/helpers/auth.py).
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.helpers import db
from app.helpers.auth import require_dashboard_token
from app.models import (ConversationDetail, ConversationSummary, ConversationStatus, SmsOutboxItem,
                        TicketQueueItem, TicketStatus, TicketStatusUpdate)

router = APIRouter(tags=["dashboard"], dependencies=[Depends(require_dashboard_token)])

_CUSTOMER_COLUMNS = """
    cu.id AS customer_id, cu.full_name AS customer_name, cu.account_no, cu.phone,
    cu.service_type, a.name AS area_name
"""


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    status: ConversationStatus | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Most recently active conversations first."""
    with db() as conn:
        return conn.execute(
            f"""
            SELECT c.id, c.status, c.channel, c.created_at,
                   {_CUSTOMER_COLUMNS},
                   coalesce(s.last_activity, c.created_at) AS last_activity,
                   coalesce(s.step_count, 0) AS step_count,
                   coalesce(s.tool_calls, 0) AS tool_calls,
                   m.text AS last_message
            FROM conversations c
            LEFT JOIN customers cu ON cu.id = c.customer_id
            LEFT JOIN service_areas a ON a.id = cu.area_id
            LEFT JOIN LATERAL (
                SELECT max(created_at) AS last_activity, count(*) AS step_count,
                       count(*) FILTER (WHERE kind = 'tool_call') AS tool_calls
                FROM agent_steps WHERE conversation_id = c.id
            ) s ON true
            LEFT JOIN LATERAL (
                SELECT payload->>'text' AS text FROM agent_steps
                WHERE conversation_id = c.id AND kind IN ('user_message', 'assistant_message')
                  AND coalesce(payload->>'text', '') <> ''
                ORDER BY step_no DESC LIMIT 1
            ) m ON true
            WHERE (%(status)s::text IS NULL OR c.status = %(status)s)
            ORDER BY last_activity DESC, c.id DESC
            LIMIT %(limit)s
            """,
            {"status": status, "limit": limit},
        ).fetchall()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int):
    """One conversation: the customer, every agent step in order, and the tickets it opened."""
    with db() as conn:
        conversation = conn.execute(
            f"""
            SELECT c.id, c.status, c.channel, c.created_at, {_CUSTOMER_COLUMNS}
            FROM conversations c
            LEFT JOIN customers cu ON cu.id = c.customer_id
            LEFT JOIN service_areas a ON a.id = cu.area_id
            WHERE c.id = %s
            """,
            (conversation_id,),
        ).fetchone()
        if conversation is None:
            raise HTTPException(404, f"No conversation with id {conversation_id}.")

        steps = conn.execute(
            """
            SELECT step_no, kind, tool_name, payload, created_at FROM agent_steps
            WHERE conversation_id = %s ORDER BY step_no
            """,
            (conversation_id,),
        ).fetchall()
        tickets = conn.execute(
            """
            SELECT id, customer_id, conversation_id, category, priority, summary, status, created_at
            FROM tickets WHERE conversation_id = %s ORDER BY id
            """,
            (conversation_id,),
        ).fetchall()

    return {**conversation, "steps": steps, "tickets": tickets}


@router.get("/tickets", response_model=list[TicketQueueItem])
def list_tickets(
    status: TicketStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """The ticket queue: high priority first, then oldest first."""
    with db() as conn:
        return conn.execute(
            f"""
            SELECT t.id, t.conversation_id, t.category, t.priority, t.summary, t.status, t.created_at,
                   {_CUSTOMER_COLUMNS}
            FROM tickets t
            JOIN customers cu ON cu.id = t.customer_id
            JOIN service_areas a ON a.id = cu.area_id
            WHERE (%(status)s::text IS NULL OR t.status = %(status)s)
            ORDER BY CASE t.priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
                     t.created_at, t.id
            LIMIT %(limit)s
            """,
            {"status": status, "limit": limit},
        ).fetchall()


@router.patch("/tickets/{ticket_id}", response_model=TicketQueueItem)
def update_ticket(ticket_id: int, update: TicketStatusUpdate):
    """Move a ticket through the queue (open -> in_progress -> closed)."""
    with db() as conn:
        updated = conn.execute(
            "UPDATE tickets SET status = %s WHERE id = %s RETURNING id",
            (update.status, ticket_id),
        ).fetchone()
        if updated is None:
            raise HTTPException(404, f"No ticket with id {ticket_id}.")
        return conn.execute(
            f"""
            SELECT t.id, t.conversation_id, t.category, t.priority, t.summary, t.status, t.created_at,
                   {_CUSTOMER_COLUMNS}
            FROM tickets t
            JOIN customers cu ON cu.id = t.customer_id
            JOIN service_areas a ON a.id = cu.area_id
            WHERE t.id = %s
            """,
            (ticket_id,),
        ).fetchone()


@router.get("/sms", response_model=list[SmsOutboxItem])
def list_sms(limit: int = Query(50, ge=1, le=200)):
    """Every SMS attempt, newest first, including simulated ones."""
    with db() as conn:
        return conn.execute(
            """
            SELECT s.id, s.customer_id, cu.full_name AS customer_name, s.to_phone, s.body,
                   s.status, s.provider_sid, s.created_at
            FROM sms_messages s
            LEFT JOIN customers cu ON cu.id = s.customer_id
            ORDER BY s.created_at DESC, s.id DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
