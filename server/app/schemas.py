import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict


class HCPBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    city: Optional[str] = None
    tier: str = "tier2"


class HCPCreate(HCPBase):
    email: Optional[str] = None
    phone: Optional[str] = None


class HCPResponse(HCPBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class InteractionCreate(BaseModel):
    hcp_id: UUID
    interaction_type: str = "visit"
    date: Optional[datetime.date] = None
    products_discussed: Optional[list[str]] = None
    sentiment: str = "neutral"
    raw_input: Optional[str] = None
    next_action: Optional[str] = None
    duration_minutes: Optional[int] = None


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    date: Optional[datetime.date] = None
    duration_minutes: Optional[int] = None
    products_discussed: Optional[list[str]] = None
    sentiment: Optional[str] = None
    raw_input: Optional[str] = None
    ai_summary: Optional[str] = None
    entities_json: Optional[dict] = None
    next_action: Optional[str] = None


class InteractionResponse(BaseModel):
    id: UUID
    hcp_id: UUID
    interaction_type: str
    date: datetime.date
    duration_minutes: Optional[int] = None
    products_discussed: Optional[list[str]] = None
    sentiment: str
    raw_input: Optional[str] = None
    ai_summary: Optional[str] = None
    entities_json: Optional[dict] = None
    next_action: Optional[str] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    hcp: Optional[HCPResponse] = None

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
    interaction_id: Optional[UUID] = None
    hcp_id: Optional[UUID] = None
    due_date: Optional[datetime.date] = None
    task: Optional[str] = None
    status: str = "pending"


class FollowUpResponse(BaseModel):
    id: UUID
    interaction_id: Optional[UUID] = None
    hcp_id: Optional[UUID] = None
    due_date: Optional[datetime.date] = None
    task: Optional[str] = None
    status: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
