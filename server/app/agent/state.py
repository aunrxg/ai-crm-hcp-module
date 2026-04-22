from typing import Annotated, List, Optional, TypedDict
import operator

from langchain_core.messages import BaseMessage


class InteractionDraft(TypedDict):
    hcp_id: Optional[str]
    hcp_name: Optional[str]
    interaction_type: Optional[str]  # visit | call | email | conference
    date: Optional[str]  # ISO date string
    duration_minutes: Optional[int]
    products_discussed: Optional[List[str]]
    sentiment: Optional[str]  # positive | neutral | negative
    next_action: Optional[str]
    ai_summary: Optional[str]
    entities_json: Optional[dict]
    follow_up_date: Optional[str]
    follow_up_task: Optional[str]


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]  # append-only
    session_id: str
    hcp_id: Optional[str]
    interaction_draft: InteractionDraft  # live form state — updated by tools
    last_tool_called: Optional[str]
    interaction_id: Optional[str]  # set after a log or edit is done
    error: Optional[str]
    final_response: Optional[str]


# Field labels for the UI — maps draft keys to display names
FORM_FIELD_LABELS = {
    "hcp_name": "HCP Name",
    "interaction_type": "Interaction Type",
    "date": "Date",
    "duration_minutes": "Duration (min)",
    "products_discussed": "Products Discussed",
    "sentiment": "Sentiment",
    "next_action": "Next Action",
    "ai_summary": "AI Summary",
    "follow_up_date": "Follow-up Date",
    "follow_up_task": "Follow-up Task",
}
