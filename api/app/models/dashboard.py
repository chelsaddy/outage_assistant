from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .chat import AgentStep
from .ticket import Ticket

ConversationStatus = Literal["open", "escalated", "closed"]
TicketStatus = Literal["open", "in_progress", "closed"]


class CustomerRef(BaseModel):
    """The customer behind a conversation or ticket. All null until the agent identifies them."""

    customer_id: int | None
    customer_name: str | None
    account_no: str | None
    phone: str | None
    service_type: str | None
    area_name: str | None


class ConversationSummary(CustomerRef):
    id: int
    status: str
    channel: str
    created_at: datetime
    last_activity: datetime
    step_count: int
    tool_calls: int
    last_message: str | None


class ConversationDetail(CustomerRef):
    id: int
    status: str
    channel: str
    created_at: datetime
    steps: list[AgentStep]
    tickets: list[Ticket]


class TicketQueueItem(CustomerRef):
    id: int
    conversation_id: int | None
    category: str
    priority: str
    summary: str
    status: str
    created_at: datetime


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class SmsOutboxItem(BaseModel):
    id: int
    customer_id: int | None
    customer_name: str | None
    to_phone: str
    body: str
    status: str
    provider_sid: str | None
    created_at: datetime
