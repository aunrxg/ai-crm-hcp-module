import json
import uuid
from datetime import datetime

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState
from app.agent.tools import TOOLS
from app.config import settings
from app.database import get_db_session
from app.models import AgentSession

SYSTEM_PROMPT = """You are an AI assistant embedded inside a pharma CRM system.
You help field medical representatives log and manage their interactions with Healthcare Professionals (HCPs).

You have access to 5 tools:
1. log_interaction — use when the rep describes a visit/call/meeting
2. edit_interaction — use when the rep wants to change something already logged
3. get_hcp_profile — use when the rep asks about an HCP before or during a visit
4. schedule_follow_up — use when the rep mentions a follow-up task or date
5. summarize_and_analyze_visit — use when the rep asks for analytics or a summary

IMPORTANT RULES:
- Always extract as much information as possible from the rep's message before calling a tool
- If hcp_id is not known, ask for the HCP name first
- After every tool call, confirm what was saved/updated in a brief, friendly message
- Keep responses concise — reps are on the field, not at a desk
- The form on the right side of the screen is automatically updated via the interaction_draft in your state
"""


def llm_node(state: AgentState) -> AgentState:
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_primary_model,
        temperature=0,
    ).bind_tools(TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    ai_response = llm.invoke(messages)
    return {"messages": [ai_response]}


tool_node = ToolNode(TOOLS)


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "end"


builder = StateGraph(AgentState)
builder.add_node("llm", llm_node)
builder.add_node("tools", tool_node)
builder.set_entry_point("llm")
builder.add_conditional_edges("llm", should_continue, {"tools": "tools", "end": END})
builder.add_edge("tools", "llm")
graph = builder.compile()


def _serialize_message(message: BaseMessage) -> dict:
    payload = {
        "type": message.type,
        "content": message.content,
    }
    if isinstance(message, AIMessage):
        payload["tool_calls"] = message.tool_calls
    if isinstance(message, HumanMessage):
        payload["name"] = message.name
    return payload


def _extract_last_tool_called(messages: list[BaseMessage]) -> str | None:
    for message in reversed(messages):
        if message.type == "ai" and getattr(message, "tool_calls", None):
            tool_calls = getattr(message, "tool_calls", [])
            if tool_calls:
                return tool_calls[-1].get("name")
    return None


def _extract_interaction_draft(messages: list[BaseMessage], fallback: dict) -> dict:
    for message in reversed(messages):
        if message.type != "tool":
            continue
        try:
            parsed = json.loads(message.content)
        except (TypeError, json.JSONDecodeError):
            continue

        if isinstance(parsed, dict):
            if "interaction_draft" in parsed and isinstance(parsed["interaction_draft"], dict):
                return parsed["interaction_draft"]
            if "interaction_draft_updates" in parsed and isinstance(parsed["interaction_draft_updates"], dict):
                merged = dict(fallback or {})
                merged.update(parsed["interaction_draft_updates"])
                return merged
    return fallback or {}


async def run_agent(
    user_message: str,
    session_id: str,
    hcp_id: str = None,
    interaction_draft: dict = None,
    history: list = None,
) -> dict:
    history_messages = [msg for msg in (history or []) if isinstance(msg, BaseMessage)]
    state: AgentState = {
        "messages": history_messages + [HumanMessage(content=user_message)],
        "session_id": session_id,
        "hcp_id": hcp_id,
        "interaction_draft": interaction_draft or {},
        "last_tool_called": None,
        "interaction_id": None,
        "error": None,
        "final_response": None,
    }

    final_state = graph.invoke(state)
    messages = final_state["messages"]

    last_ai_message = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    response_text = last_ai_message.content if last_ai_message else ""
    last_tool_called = _extract_last_tool_called(messages)
    updated_draft = _extract_interaction_draft(messages, final_state.get("interaction_draft", {}))

    with get_db_session() as db:
        parsed_hcp_id = uuid.UUID(hcp_id) if hcp_id else None
        existing = db.query(AgentSession).filter(AgentSession.session_id == session_id).first()
        serialized_messages = [_serialize_message(msg) for msg in messages]

        if existing:
            existing.hcp_id = parsed_hcp_id
            existing.messages_json = serialized_messages
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                AgentSession(
                    session_id=session_id,
                    hcp_id=parsed_hcp_id,
                    messages_json=serialized_messages,
                )
            )
        db.commit()

    return {
        "response": response_text,
        "interaction_draft": updated_draft,
        "session_id": session_id,
        "tool_called": last_tool_called,
    }
