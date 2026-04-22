import json
import uuid
from datetime import date, datetime, timedelta

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db_session
from app.models import FollowUp, HCP, Interaction


def _llm(model_name: str) -> ChatGroq:
    return ChatGroq(api_key=settings.groq_api_key, model=model_name, temperature=0)


def _safe_json_parse(text: str, fallback: dict | list | None = None) -> dict | list:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return fallback if fallback is not None else {}


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value).date()


def _draft_from_interaction(interaction: Interaction, hcp: HCP | None = None) -> dict:
    latest_follow_up = None
    if interaction.follow_ups:
        latest_follow_up = sorted(
            interaction.follow_ups,
            key=lambda f: f.created_at or datetime.min,
            reverse=True,
        )[0]
    return {
        "hcp_id": str(interaction.hcp_id) if interaction.hcp_id else None,
        "hcp_name": hcp.name if hcp else (interaction.hcp.name if interaction.hcp else None),
        "interaction_type": interaction.interaction_type,
        "date": interaction.date.isoformat() if interaction.date else None,
        "duration_minutes": interaction.duration_minutes,
        "products_discussed": interaction.products_discussed or [],
        "sentiment": interaction.sentiment,
        "next_action": interaction.next_action,
        "ai_summary": interaction.ai_summary,
        "entities_json": interaction.entities_json or {},
        "follow_up_date": latest_follow_up.due_date.isoformat() if latest_follow_up and latest_follow_up.due_date else None,
        "follow_up_task": latest_follow_up.task if latest_follow_up else None,
    }


@tool
def log_interaction(
    hcp_id: str,
    raw_input: str,
    interaction_type: str = "visit",
    date: str = None,
    duration_minutes: int = None,
    products_discussed: list = None,
    sentiment: str = "neutral",
    next_action: str = None,
) -> dict:
    """
    Log a new HCP interaction to the CRM and enrich it with LLM-generated intelligence.

    This tool stores a fresh interaction record for a known HCP. Before writing to the
    database, it uses Groq with the configured primary model to generate:
    1) a concise 2-3 sentence `ai_summary`, and
    2) structured `entities_json` containing `drugs_mentioned`, `objections`,
       `competitors`, and `action_items`.

    Use this whenever a rep submits a fresh free-text visit/call/email note and you
    need a persisted interaction plus normalized structured fields for downstream
    analysis and UI form-state hydration.

    Returns:
    - `interaction_id`
    - `ai_summary`
    - `entities_json`
    - `interaction_draft` (full draft payload used to update live form state)
    """
    parsed_hcp_id = uuid.UUID(hcp_id)
    interaction_date = _to_date(date) or datetime.utcnow().date()
    products = products_discussed or []

    with get_db_session() as db:
        hcp = db.get(HCP, parsed_hcp_id)
        if not hcp:
            raise ValueError(f"HCP not found for id: {hcp_id}")

        summary_prompt = (
            "You are a pharma CRM assistant. Summarize the following rep note in 2-3 concise "
            "sentences focused on clinical interest, concerns, and next step.\n\n"
            f"Note:\n{raw_input}"
        )
        summary_text = _llm(settings.groq_primary_model).invoke(summary_prompt).content

        extraction_prompt = (
            "You are a pharma CRM assistant. Extract structured data from the rep's visit note.\n"
            "Return ONLY valid JSON with keys: drugs_mentioned, objections, competitors, action_items.\n"
            "No explanation, just JSON.\n\n"
            f"Note:\n{raw_input}"
        )
        entities_raw = _llm(settings.groq_primary_model).invoke(extraction_prompt).content
        entities_json = _safe_json_parse(
            entities_raw,
            fallback={
                "drugs_mentioned": [],
                "objections": [],
                "competitors": [],
                "action_items": [],
            },
        )

        interaction = Interaction(
            hcp_id=parsed_hcp_id,
            interaction_type=interaction_type,
            date=interaction_date,
            duration_minutes=duration_minutes,
            products_discussed=products,
            sentiment=sentiment,
            raw_input=raw_input,
            ai_summary=summary_text.strip(),
            entities_json=entities_json,
            next_action=next_action,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        draft = _draft_from_interaction(interaction, hcp)
        return {
            "interaction_id": str(interaction.id),
            "ai_summary": interaction.ai_summary,
            "entities_json": interaction.entities_json,
            "interaction_draft": draft,
        }


@tool
def edit_interaction(
    interaction_id: str,
    edit_instruction: str,
) -> dict:
    """
    Edit an existing interaction record using a natural-language instruction.

    This tool fetches the current interaction, asks the Groq primary model to interpret
    the instruction, and expects a strict JSON delta containing only fields to update.
    It then applies those changes transactionally and returns a refreshed
    `interaction_draft` for form-state synchronization.

    Use when the user says things like:
    - "change sentiment to positive"
    - "add Metformin to products discussed"
    - "update next action to schedule demo next week"

    Returns:
    - `interaction_id`
    - `updated_fields`
    - `interaction_draft`
    """
    parsed_interaction_id = uuid.UUID(interaction_id)

    with get_db_session() as db:
        interaction = db.get(Interaction, parsed_interaction_id)
        if not interaction:
            raise ValueError(f"Interaction not found for id: {interaction_id}")

        current_record_json = json.dumps(
            {
                "interaction_type": interaction.interaction_type,
                "date": interaction.date.isoformat() if interaction.date else None,
                "duration_minutes": interaction.duration_minutes,
                "products_discussed": interaction.products_discussed or [],
                "sentiment": interaction.sentiment,
                "next_action": interaction.next_action,
                "ai_summary": interaction.ai_summary,
            }
        )
        prompt = (
            "You are editing a pharma CRM interaction record.\n"
            f"Current record: {current_record_json}\n"
            f"Edit instruction: {edit_instruction}\n"
            "Return ONLY a JSON object with the fields to update. Valid fields: "
            "interaction_type, date, duration_minutes, products_discussed (list), "
            "sentiment (positive/neutral/negative), next_action, ai_summary.\n"
            "No explanation, just JSON."
        )
        delta_raw = _llm(settings.groq_primary_model).invoke(prompt).content
        delta = _safe_json_parse(delta_raw, fallback={})

        allowed_fields = {
            "interaction_type",
            "date",
            "duration_minutes",
            "products_discussed",
            "sentiment",
            "next_action",
            "ai_summary",
        }
        updates = {k: v for k, v in delta.items() if k in allowed_fields}
        if "date" in updates and updates["date"]:
            updates["date"] = _to_date(updates["date"])

        for field, value in updates.items():
            setattr(interaction, field, value)

        db.commit()
        db.refresh(interaction)
        hcp = db.get(HCP, interaction.hcp_id)
        return {
            "interaction_id": str(interaction.id),
            "updated_fields": updates,
            "interaction_draft": _draft_from_interaction(interaction, hcp),
        }


@tool
def get_hcp_profile(hcp_id: str) -> dict:
    """
    Fetch an HCP profile with recent engagement and a narrated LLM briefing.

    This tool returns complete profile details for the target HCP plus their latest
    5 interactions. It also asks the Groq primary model to produce a compact narrative
    useful for field reps before a call/visit, covering specialization, sentiment trend,
    most recent visit, and product responsiveness.

    Use this when asked "who is this HCP?" or "brief me before my meeting."

    Returns:
    - `hcp`: profile attributes
    - `recent_interactions`: last 5 interactions (newest first)
    - `llm_narrative`: concise engagement summary for rep prep
    """
    parsed_hcp_id = uuid.UUID(hcp_id)

    with get_db_session() as db:
        hcp = db.get(HCP, parsed_hcp_id)
        if not hcp:
            raise ValueError(f"HCP not found for id: {hcp_id}")

        interactions = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == parsed_hcp_id)
            .order_by(desc(Interaction.date), desc(Interaction.created_at))
            .limit(5)
            .all()
        )

        recent_payload = [
            {
                "interaction_id": str(i.id),
                "interaction_type": i.interaction_type,
                "date": i.date.isoformat() if i.date else None,
                "sentiment": i.sentiment,
                "products_discussed": i.products_discussed or [],
                "next_action": i.next_action,
            }
            for i in interactions
        ]
        hcp_payload = {
            "id": str(hcp.id),
            "name": hcp.name,
            "specialty": hcp.specialty,
            "hospital": hcp.hospital,
            "city": hcp.city,
            "tier": hcp.tier,
            "email": hcp.email,
            "phone": hcp.phone,
        }

        prompt = (
            "You are a pharma CRM assistant. Create a concise rep briefing for this HCP.\n"
            "Cover: specialization, sentiment trend, last visit date, and top products they respond to.\n\n"
            f"HCP: {json.dumps(hcp_payload)}\n"
            f"Recent interactions: {json.dumps(recent_payload)}"
        )
        narrative = _llm(settings.groq_primary_model).invoke(prompt).content.strip()

        return {
            "hcp": hcp_payload,
            "recent_interactions": recent_payload,
            "llm_narrative": narrative,
        }


@tool
def schedule_follow_up(
    interaction_id: str,
    hcp_id: str,
    task: str,
    due_date: str = None,
) -> dict:
    """
    Schedule and persist a follow-up task for a specific HCP interaction.

    If `due_date` is provided, it is used directly. Otherwise this tool asks the Groq
    large model to suggest an optimal date using business policy signals:
    - tier1: 7 days
    - tier2: 14 days
    - tier3: 21 days
    and recent interaction gap context.

    It writes the follow-up record and returns both a confirmation payload and form-state
    updates (`follow_up_date`, `follow_up_task`) for the interaction draft.

    Returns:
    - `follow_up_id`
    - `due_date`
    - `task`
    - `hcp_name`
    - `confirmation_message`
    - `interaction_draft_updates`
    """
    parsed_interaction_id = uuid.UUID(interaction_id)
    parsed_hcp_id = uuid.UUID(hcp_id)

    with get_db_session() as db:
        interaction = db.get(Interaction, parsed_interaction_id)
        hcp = db.get(HCP, parsed_hcp_id)
        if not interaction:
            raise ValueError(f"Interaction not found for id: {interaction_id}")
        if not hcp:
            raise ValueError(f"HCP not found for id: {hcp_id}")

        computed_due_date = _to_date(due_date)
        if not computed_due_date:
            last_interaction = (
                db.query(Interaction)
                .filter(Interaction.hcp_id == parsed_hcp_id)
                .order_by(desc(Interaction.date))
                .first()
            )
            gap_days = 0
            if last_interaction and last_interaction.date:
                gap_days = (datetime.utcnow().date() - last_interaction.date).days
            prompt = (
                "You are helping schedule pharma follow-ups.\n"
                "Choose an ISO date (YYYY-MM-DD) for next follow-up based on:\n"
                "- tier1 -> 7 days\n- tier2 -> 14 days\n- tier3 -> 21 days\n"
                "Also factor the last visit gap. Return ONLY JSON: {\"due_date\":\"YYYY-MM-DD\"}.\n\n"
                f"today={datetime.utcnow().date().isoformat()}, tier={hcp.tier}, last_visit_gap_days={gap_days}"
            )
            llm_raw = _llm(settings.groq_large_model).invoke(prompt).content
            parsed = _safe_json_parse(llm_raw, fallback={})
            computed_due_date = _to_date(parsed.get("due_date")) if isinstance(parsed, dict) else None

            if not computed_due_date:
                baseline = {"tier1": 7, "tier2": 14, "tier3": 21}.get(hcp.tier, 14)
                computed_due_date = datetime.utcnow().date() + timedelta(days=baseline)

        follow_up = FollowUp(
            interaction_id=parsed_interaction_id,
            hcp_id=parsed_hcp_id,
            task=task,
            due_date=computed_due_date,
        )
        db.add(follow_up)
        db.commit()
        db.refresh(follow_up)

        return {
            "follow_up_id": str(follow_up.id),
            "due_date": follow_up.due_date.isoformat() if follow_up.due_date else None,
            "task": follow_up.task,
            "hcp_name": hcp.name,
            "confirmation_message": (
                f"Follow-up scheduled for {hcp.name} on "
                f"{follow_up.due_date.isoformat() if follow_up.due_date else 'TBD'}."
            ),
            "interaction_draft_updates": {
                "follow_up_date": follow_up.due_date.isoformat() if follow_up.due_date else None,
                "follow_up_task": follow_up.task,
            },
        }


@tool
def summarize_and_analyze_visit(hcp_id: str) -> dict:
    """
    Generate a structured analytics snapshot over all interactions for one HCP.

    This tool gathers complete interaction history, then uses the Groq large model to
    produce JSON analytics with sentiment trend, top products, days since last visit,
    top objections, recommended action, and a risk flag (true when no visit in 30+ days).
    It also returns a concise human-readable summary string for direct display.

    Use when a rep asks for strategic guidance, risk review, or progression analysis
    across historical interactions for a specific HCP.

    Returns:
    - `analysis`: structured analysis dict
    - `summary`: human-readable recap string
    """
    parsed_hcp_id = uuid.UUID(hcp_id)

    with get_db_session() as db:
        hcp = db.get(HCP, parsed_hcp_id)
        if not hcp:
            raise ValueError(f"HCP not found for id: {hcp_id}")

        interactions = (
            db.query(Interaction)
            .filter(Interaction.hcp_id == parsed_hcp_id)
            .order_by(desc(Interaction.date), desc(Interaction.created_at))
            .all()
        )
        if not interactions:
            return {
                "analysis": {
                    "sentiment_trend": "stable",
                    "top_products": [],
                    "days_since_last_visit": None,
                    "top_objections": [],
                    "recommended_action": "Schedule an introductory visit.",
                    "risk_flag": True,
                },
                "summary": f"No interactions yet for {hcp.name}. Schedule a first visit.",
            }

        records_json = json.dumps(
            [
                {
                    "interaction_type": i.interaction_type,
                    "date": i.date.isoformat() if i.date else None,
                    "products_discussed": i.products_discussed or [],
                    "sentiment": i.sentiment,
                    "entities_json": i.entities_json or {},
                    "next_action": i.next_action,
                }
                for i in interactions
            ]
        )
        prompt = (
            "You are a pharma sales analytics assistant. Analyze these HCP interaction "
            "records and return a JSON with: sentiment_trend, top_products (list), "
            "days_since_last_visit (int), top_objections (list), recommended_action (str), "
            "risk_flag (bool, true if no visit in 30+ days).\n"
            f"Records: {records_json}"
        )
        analysis_raw = _llm(settings.groq_large_model).invoke(prompt).content
        analysis = _safe_json_parse(
            analysis_raw,
            fallback={
                "sentiment_trend": "stable",
                "top_products": [],
                "days_since_last_visit": (datetime.utcnow().date() - interactions[0].date).days if interactions[0].date else None,
                "top_objections": [],
                "recommended_action": "Review recent notes and plan next engagement.",
                "risk_flag": False,
            },
        )

        if isinstance(analysis, list):
            analysis = {}
        summary = (
            f"{hcp.name} ({hcp.specialty}) shows {analysis.get('sentiment_trend', 'stable')} sentiment trend. "
            f"Top products: {', '.join(analysis.get('top_products', [])[:3]) or 'none yet'}. "
            f"Recommended action: {analysis.get('recommended_action', 'follow up soon')}."
        )
        return {"analysis": analysis, "summary": summary}


TOOLS = [log_interaction, edit_interaction, get_hcp_profile, schedule_follow_up, summarize_and_analyze_visit]
