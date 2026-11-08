from datetime import datetime

from pydantic import BaseModel, Field


class SmsCreate(BaseModel):
    """What the agent sends to send_sms. The phone number comes from the customer record."""

    customer_id: int
    body: str = Field(..., min_length=1, max_length=320,
                      description="Message text; keep under 160 characters for a single SMS")


class SmsMessage(BaseModel):
    id: int
    customer_id: int
    to_phone: str
    body: str
    status: str                       # sent | failed | simulated
    provider_sid: str | None
    created_at: datetime
    error: str | None = None          # why it failed, so the agent can tell the customer
