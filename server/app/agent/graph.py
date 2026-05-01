import json
import uuid
from datetime import datetime

from langchain_core.messages import (
    AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
)
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState
from app.agent.tools import TOOLS
from app.config import settings
from app.database import get_db_session, SessionLocal
from app.models import AgentSession

SYSTEM_PROMPT_TEMPLATE = """You are an AI assistant embedded inside a pharma CRM system.
You help field medical representatives log and manage their interactions with Healthcare Professionals (HCPs).

=== CURRENT SESSION CONTEXT ===
Selected HCP ID      : {hcp_id}
Selected HCP Name    : {hcp_name}
Session ID           : {session_id}
Current Date         : {current_date}
Last Interaction ID  : {interaction_id}

CRITICAL RULES:
- When calling any tool requiring hcp_id, use EXACTLY: {hcp_id}
- When calling any tool requiring interaction_id, use EXACTLY: {interaction_id}
- If Last Interaction ID is "None", no interaction has been logged yet this session
- If interaction_id is "None", DO NOT call schedule_follow_up or edit_interaction
- NEVER invent, guess, or substitute IDs — use only the values shown above

=== TOOL SELECTION — FOLLOW EXACTLY ===
Use get_hcp_profile when:
  - Rep asks "tell me about", "who is", "profile", "brief me", "info about"
  - Rep asks anything about the HCP before a visit
  → ONLY pass hcp_id. No other parameters needed.

Use log_interaction when:
  - Rep describes a completed visit, call, or meeting
  - Keywords: "met", "visited", "called", "discussed", "just had"

Use edit_interaction when:
  - Rep wants to change something already logged
  - Keywords: "change", "update", "edit", "actually", "correct"
  - ONLY call if Last Interaction ID is NOT "None"

Use schedule_follow_up when:
  - Rep EXPLICITLY asks to schedule or book something future
  - Keywords: "schedule", "book", "remind me", "follow up on"
  - ONLY call if Last Interaction ID is NOT "None"
  - NEVER call this just because a follow-up is mentioned in a profile or summary

Use summarize_and_analyze_visit when:
  - Rep asks for analysis, trends, history, patterns
  - Keywords: "analyze", "summary", "how have", "trend", "review"


RULES:
- Always use the hcp_id from the session context above — never make one up
- For the 'date' parameter, always pass today's ISO date ({current_date}) unless the rep says otherwise
- After every tool call, confirm what was saved/updated in a brief, friendly message
- Keep responses concise — reps are on the field
"""


def llm_node(state: AgentState) -> AgentState:

    # 1. build context aware system prompt with real id injected
    hcp_id = state.get('hcp_id') or "None (Ask user to select an HCP)"
    hcp_name = state["interaction_draft"].get("hcp_name", "Unknown HCP")
    current_date = datetime.utcnow().date().isoformat()

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        hcp_id = hcp_id,
        hcp_name = hcp_name,
        session_id = state.get("session_id", ""),
        current_date = current_date, #always send real iso date
        interaction_id = state.get("interaction_id") or None
    )

    # 2. Initialize chat groq with tools bound to it
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_primary_model,
        temperature=0,
    ).bind_tools(TOOLS)
    
    # 3. build full msg list the llm will see
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    # 4. call llm
    ai_response = llm.invoke(messages)

    # 5. return new state
    return {**state, "messages": [ai_response]}


_tool_node = ToolNode(TOOLS)


def sanitized_tool_node(state: AgentState) -> AgentState:
    """
    Before passing to ToolNode, rewrite any hcp_id in tool call arguments with the real hcp_id from AgentState if they don't match.
    """
    real_hcp_id = state.get("hcp_id")
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None

    if real_hcp_id and last_message and hasattr(last_message, "tool_calls"):
        fixed_tool_calls = []
        for tc in last_message.tool_calls:
            args = dict(tc.get("args", {}))

            # force the hcp id if the llm used something else or left blank
            if "hcp_id" in args and args["hcp_id"] != real_hcp_id:
                print(f"[sanitizer] LLM passed hcp_id={args['hcp_id']!r}, overriding with real={real_hcp_id!r}")
                args["hcp_id"] = real_hcp_id
            elif "hcp_id" not in args:
                args["hcp_id"] = real_hcp_id

            # fix interaction_id halluccination
            if "interaction_id" in args: 
                real_interaction_id = state.get("interaction_id")
                passed_id = args["interaction_id"]

                # fake placeholders
                is_fake = (
                    not passed_id
                    or passed_id.lower() in (
                        "last logged interaction id",
                        "last_logged_interaction_id", 
                        "interaction_id",
                        "none",
                        "null",
                        "unknown",
                        "placeholder",
                    )
                    or len(passed_id) < 10
                )

                if is_fake and real_interaction_id:
                    print(f"[sanitizer] LLM hallucinated interaction_id={passed_id!r}, overriding with real={real_interaction_id!r}")
                    args["interaction_id"] = real_interaction_id
                elif is_fake and not real_interaction_id:
                    # no real id tracked yet - this tool will fail
                    # return graceful error message
                    print(f"[sanitizer] No real interaction_id in state, cannot call tool")
                    error_msg = ToolMessage(
                        content=json.dumps({
                            "error": "No interaction has been logged yet in this session."
                            "Please log an interaction first before scheduling a follow-up."
                        }),
                        tool_call_id=tc.get("id", ""),
                    )
                    return {**state, "messages": messages[:-1] + [last_message, error_msg]}
            
            fixed_tool_calls.append({**tc, "args": args})
        
        # rebuild the AIMessage with corrected tool calls
        fixed_message = AIMessage(
            content=last_message.content,
            tool_calls=fixed_tool_calls,
        )
        state = {**state, "messages": messages[:-1] + [fixed_message]}

    # run the real tool
    result_state = _tool_node.invoke(state)

    # KEY: extract interaction_id from tool results and store in state
    result_state = _update_state_from_results(result_state)

    return result_state;


def _update_state_from_results(state: AgentState) -> AgentState:
    """
    After a tool runs, scan the new ToolMessage for any interaction_id
    and write it back into AgentState so future tools can use it.
    """

    messages = state.get("messages", [])

    # find the most recent tool
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue

        try:
            content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(content, dict):
            continue

        updates = {}

        # Track interaction_id from log_interaction or edit_interaction
        if "interaction_id" in content:
            updates["interaction_id"] = content["interaction_id"]

        # also update interaction_draft if tool returned one
        if "interaction_draft" in content:
            exisiting_draft = state.get("interaction_draft", {})
            updates["interaction_draft"] = {**exisiting_draft, **content["interaction_draft"]}

        if updates:
            return {**state, **updates}

        break # only the most recent

    return state

# the conditional edge function
def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]

    # if the llm's last response has tool_calls -> go to tools
    if getattr(last_message, "tool_calls", None):
        return "tools"
    # otherwise end, we are done here
    return "end"


builder = StateGraph(AgentState)

# register nodes
builder.add_node("llm", llm_node)
builder.add_node("tools", sanitized_tool_node)

# entry point (always start from llm node)
builder.set_entry_point("llm")

# conditional routing - (source node, routing function, { if tools go to tools node, if end terminate graph })
builder.add_conditional_edges("llm", should_continue, {"tools": "tools", "end": END})

# after tool call always to back to llm
builder.add_edge("tools", "llm")

# compile the graph
graph = builder.compile()


def _serialize_message(messages: BaseMessage) -> dict:
    """Convert BaseMessage objects to plain dicts for JSON storage."""
    result = []
    for msg in messages:
        if isinstance(msg, dict):
            result.append(msg) # already a dict - pass through 
            continue

        if isinstance(msg, HumanMessage):
            result.append({"type": "human", "content": msg.content})

        elif isinstance(msg, AIMessage):
            d = {"type": "ai", "content": msg.content}
            if getattr(msg, "tool_calls", None):
                d["tool_calls"] = msg.tool_calls
            result.append(d)

        elif isinstance(msg, ToolMessage):
            result.append({
                "type": "tool",
                "content": msg.content,
                "tool_call_id": getattr(msg, "tool_call_id", "")
            })

        elif isinstance(msg, SystemMessage):
            # skip - system prompt is rebuilt fresh each turn
            continue

    return result

def _deserialize_message(raw: list) -> list[BaseMessage]:
    """
    Convert plain dict (load from JSON in DB) back into Langchain BaseMessage objects. Passes through objects that are already BaseMessage instance unchanged.
    """
    if not raw:
        return []
    
    result = []
    for item in raw:
        # already a proper object - leave it alone
        if isinstance(item, BaseMessage):
            result.append(item)
            continue

        if not isinstance(item, dict):
            continue

        # normalize the type object - DB might store "human", "ai", "tool" or the full class name
        msg_type = (item.get("type") or item.get("role") or "").lower()
        content = item.get("content", "")

        if msg_type in ("human", "user", "humanmessage", "user_message"):
            result.append(HumanMessage(content=content))
        
        elif msg_type in ("ai", "assistant", "aimessage", "ai_message"):
            # preserve tool_calls if present
            tool_calls = item.get("tool_calls") or item.get("additional_kwargs", {}).get("tool_calls")
            if tool_calls:
                result.append(AIMessage(content=content, tool_calls=tool_calls))
            else:
                result.append(AIMessage(content=content))
        
        elif msg_type in ("tool", "toolmessage", "tool_message"):
            result.append(ToolMessage(
                content = content,
                tool_call_id = item.get("tool_call_id", ""),
            ))
        
        elif msg_type in ("system", "system_message", "systemmessage"):
            continue


    return result


def _save_session(session_id: str, hcp_id: str, messages: list):
    """Upsert agent session to DB."""
    db = SessionLocal()
    try:
        session = db.query(AgentSession).filter_by(session_id=session_id).first()
        serialized = _serialize_message(messages=messages)

        if session:
            session.messages_json = serialized
            session.updated_at = datetime.utcnow()
            if hcp_id:
                session.hcp_id = hcp_id
            db.add(session)
            db.commit()
        else:
            new_session = AgentSession(
                session_id=session_id,
                hcp_id=hcp_id,
                messages_json=serialized,
            )
            db.add(new_session)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[session save error] {e}")
    finally:
        db.close()


def _extract_last_tool_called(messages: list[BaseMessage]) -> str | None:
    for message in reversed(messages):
        if message.type == "ai" and getattr(message, "tool_calls", None):
            tool_calls = getattr(message, "tool_calls", [])
            if tool_calls:
                return tool_calls[-1].get("name")
    return None

# messages might be langchain message or plain dicts (json)
def _extract_interaction_draft(messages: list, current_draft: dict) -> dict:
    draft = dict(current_draft or {})

    for message in reversed(messages):
        # handle both langchain message objects and plain dicts
        # plain dict appear when history is history is loaded from db json
        if isinstance(message, dict):
            msg_type = message.get("type") or message.get("role", "")
            content = message.get("content", "")
        else:
            # langchain basemsg object
            msg_type = getattr(message, "type", "") or getattr(message, "role", "")
            content = getattr(message, "content", "")
        
        # normalize: ToolMessage.type == "tool", dict from db has type="tool"
        if msg_type not in ("tool", "tool_message"):
            continue

        if not content:
            continue

        try:
            tool_result = json.loads(content) if isinstance(content, str) else content
            if isinstance(tool_result, dict):
                # merge any interactions draft sub-dict the tool returned 
                if "interaction_draft" in tool_result:
                    draft.update(tool_result["interaction_draft"])
                # also pull top level field tools commnly return
                for field in (
                    "ai_summary", "entities_json", "products_discussed", "sentiment", "next_action", "follow_up_date", "follow_up_task", "interaction_id", "hcp_id", "hcp_name", "interaction_type", "date", "duration_minutes",
                ):
                    if field in tool_result:
                        draft[field] = tool_result[field]
        except (TypeError, json.JSONDecodeError):
            continue
    return draft


def _extract_final_response(result: AgentState) -> str:
    """
    Extract the best response string from the final agent state.
    For tools that produce their own narrative (get_hcp_profile, 
    summarize_and_analyze_visit), use that directly instead of the 
    LLM's re-summary which tends to be vague.
    """
    messages = result.get("messages", [])

    # Find the last ToolMessage — check if it has a narrative we should use directly
    NARRATIVE_TOOLS = {"get_hcp_profile", "summarize_and_analyze_visit"}
    
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        try:
            content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(content, dict):
            continue

        # If this tool produced a narrative, use it directly — skip LLM re-summary
        if content.get("llm_narrative"):
            narrative = content["llm_narrative"]
            
            # Optionally append follow-up suggestions if present
            suggestions = content.get("suggested_actions", [])
            if suggestions:
                items = "\n".join(f"• {s}" for s in suggestions)
                narrative += f"\n\n**Suggested next steps:**\n{items}"
            
            return narrative
        
        break  # Only check the most recent ToolMessage

    # Default — find the last AIMessage with no tool_calls (LLM's text response)
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            return msg.content

    return ""


async def run_agent(
    user_message: str,
    session_id: str,
    hcp_id: str = None,
    hcp_name: str = None,
    interaction_draft: dict = None,
    history: list = None,
) -> dict:
    draft = interaction_draft or {}
    if hcp_name:
        draft["hcp_name"] = hcp_name

    # deserialize history from dict -> BaseMessage objects
    clean_history = _deserialize_message(history or [])
    
    initial_state: AgentState = {
        "messages": clean_history + [HumanMessage(content=user_message)],
        "session_id": session_id,
        "hcp_id": hcp_id,
        "interaction_draft": draft,
        "last_tool_called": None,
        "interaction_id": draft.get("interaction_id"),
        "error": None,
        "final_response": None,
    }

    result = await graph.ainvoke(initial_state)

    final_response = _extract_final_response(result)

     # find which tool was called this turn (if any)
    tool_called = None
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            tool_called = msg.tool_calls[0].get("name") if msg.tool_calls else None
            break

    updated_draft = _extract_interaction_draft(
        result["messages"],
        result.get("interaction_draft", {})
    )

    # save session back to db
    _save_session(session_id, hcp_id, result['messages'])

    return {
        "response": final_response,
        "interaction_draft": updated_draft,
        "session_id": session_id,
        "tool_called": tool_called,
    }
