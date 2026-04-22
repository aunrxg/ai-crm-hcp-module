from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.graph import run_agent
from app.database import get_db
from app.models import AgentSession
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> dict:
    result = await run_agent(
        user_message=payload.message,
        session_id=payload.session_id,
        hcp_id=payload.hcp_id,
        interaction_draft=payload.interaction_draft or {},
        history=payload.history or [],
    )
    return result


@router.get("/api/chat/session/{session_id}")
def get_chat_session(session_id: str, db: Session = Depends(get_db)) -> dict:
    session = db.query(AgentSession).filter(AgentSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "hcp_id": str(session.hcp_id) if session.hcp_id else None,
        "messages": session.messages_json or [],
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
