from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: int | None = Field(None, description="Omit to start a new conversation")


class AgentStep(BaseModel):
    step_no: int
    kind: str          # user_message | assistant_message | tool_call | tool_result | escalation
    tool_name: str | None
    payload: dict
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    status: str                 # open | escalated
    tools_called: list[str]     # in order, for this message only
    steps: list[AgentStep]      # the trace for this message only
