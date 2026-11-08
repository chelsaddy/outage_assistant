from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TicketCategory = Literal["no_service", "slow_speed", "intermittent", "escalation", "other"]
TicketPriority = Literal["low", "normal", "high"]


class TicketCreate(BaseModel):
    """What the agent sends to create_ticket."""

    customer_id: int
    category: TicketCategory
    summary: str = Field(..., min_length=10, max_length=1000,
                         description="Short description of the problem for the field team")
    priority: TicketPriority = "normal"
    conversation_id: int | None = None


class Ticket(BaseModel):
    id: int
    customer_id: int
    conversation_id: int | None
    category: str
    priority: str
    summary: str
    status: str
    created_at: datetime
