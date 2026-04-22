from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HCPBase(BaseModel):
    name: str
    specialty: str | None = None
    hospital: str | None = None
    city: str | None = None
    tier: str = "tier2"


class HCPCreate(HCPBase):
    email: str | None = None
    phone: str | None = None


class HCPResponse(HCPBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class InteractionCreate(BaseModel):
    hcp_id: UUID
    interaction_type: str = "visit"
    date: date | None = None
    products_discussed: list[str] | None = None
    sentiment: str = "neutral"
    raw_input: str | None = None
    next_action: str | None = None
    duration_minutes: int | None = None


class InteractionUpdate(BaseModel):
    interaction_type: str | None = None
    date: date | None = None
    duration_minutes: int | None = None
    products_discussed: list[str] | None = None
    sentiment: str | None = None
    raw_input: str | None = None
    ai_summary: str | None = None
    entities_json: dict | None = None
    next_action: str | None = None


class InteractionResponse(BaseModel):
    id: UUID
    hcp_id: UUID
    interaction_type: str
    date: date
    duration_minutes: int | None = None
    products_discussed: list[str] | None = None
    sentiment: str
    raw_input: str | None = None
    ai_summary: str | None = None
    entities_json: dict | None = None
    next_action: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    hcp: HCPResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str
    session_id: str
    hcp_id: str | None = None
    interaction_draft: dict | None = None
    history: list | None = None


class ChatResponse(BaseModel):
    response: str
    interaction_draft: dict
    session_id: str
    tool_called: str | None = None


class FollowUpCreate(BaseModel):
    interaction_id: UUID | None = None
    hcp_id: UUID | None = None
    due_date: date | None = None
    task: str | None = None
    status: str = "pending"


class FollowUpResponse(BaseModel):
    id: UUID
    interaction_id: UUID | None = None
    hcp_id: UUID | None = None
    due_date: date | None = None
    task: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
