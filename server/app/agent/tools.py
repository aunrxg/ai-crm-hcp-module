import pstats
import json
import uuid
from datetime import date, datetime, timedelta

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db_session, SessionLocal
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


def _to_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    v = str(value).strip().lower()
    if v in ("today", "now", "current", ""):
        return datetime.utcnow().date()
    if v == "yesterday":
        return (datetime.utcnow() - timedelta(days=1)).date()

    try:
        return datetime.fromisoformat(value).date()
    except (ValueError, TypeError):
        pass
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
        return datetime.utcnow().date()


def _draft_from_interaction(interaction: Interaction, hcp: HCP | None = None) -> dict:
    latest_follow_up = None
    if interaction.follow_ups:
        latest_follow_up = sorted(
            interaction.follow_ups,
            key=lambda f: f.created_at or datetime.min,
            reverse=True,
        )[0]
    return {
        "interaction_id": str(interaction.id),
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
            return {
                "error": f"HCP not found for id: {hcp_id}. Please select a valid HCP.",
                "success": False,
            }

        summary_prompt = (
            "You are a pharma CRM assistant. Summarize the following rep note in 2-3 concise "
            "sentences focused on clinical interest, concerns, and next step.\n\n"
            f"Note:\n{raw_input}"
        )
        try:
            summary_text = _llm(settings.groq_primary_model).invoke(summary_prompt).content
            
            extraction_prompt = (
                "You are a pharma CRM assistant. Extract structured data from the rep's visit note.\n"
                "Return ONLY valid JSON with keys: drugs_mentioned, objections, competitors, action_items.\n"
                "No explanation, just JSON.\n\n"
                f"Note:\n{raw_input}"
            )
            entities_raw = _llm(settings.groq_primary_model).invoke(extraction_prompt).content
        except Exception as e:
            return {"error": f"Groq API error while logging interaction. Please try again later.", "success": False}

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
            "products_discussed": entities_json.get("drugs_mentioned", []),
            "sentiment": sentiment,
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
        try:
            delta_raw = _llm(settings.groq_primary_model).invoke(prompt).content
        except Exception as e:
            return {"error": f"Groq API error while editing interaction. Please try again later.", "success": False}

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
            return {
                "error": f"HCP not found for id: {hcp_id}. Please select a valid HCP.",
                "success": False,
            }

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
        
        days_since = None
        if interactions and interactions[0].date:
            days_since = (datetime.utcnow().date() - interactions[0].date).days

        prompt = f"""You are a pharma CRM assistant briefing a field rep before a visit.
        Write a SHORT, SPECIFIC briefing using ONLY the data below. 
        Do NOT give generic advice. Every sentence must reference actual data from the profile.

        HCP DATA:
        Name: {hcp.name}
        Specialty: {hcp.specialty}
        Hospital: {hcp.hospital}, {hcp.city}
        Tier: {hcp.tier}
        Days since last visit: {days_since if days_since is not None else 'No previous visits'}

        RECENT INTERACTIONS ({len(interactions)} total):
        {json.dumps(recent_payload, indent=2)}

        Write 3-4 sentences covering:
        1. Who they are (specialty + hospital)
        2. Last interaction date and sentiment (or note if no visits yet)
        3. Products they responded to (or note if none yet)  
        4. One specific recommended next step based on actual data

        Be direct and factual. Do not say 'remember to', 'don't forget to', or give generic sales advice."""

        try:
            narrative = _llm(settings.groq_primary_model).invoke(prompt).content.strip()
        except Exception as e:
            return {"error": f"Groq API error while generating profile briefing. Please try again later.", "success": False}


        return {
            "hcp": hcp_payload,
            "recent_interactions": recent_payload,
            "llm_narrative": narrative,
            "day_since_last_visit": days_since,
        }


@tool
def schedule_follow_up(
    interaction_id: str,
    hcp_id: str,
    task: str,
    due_date: str = None,
) -> dict:
    """
    Schedule a specific follow-up task for a FUTURE action after an interaction.
    Use ONLY when the rep explicitly mentions scheduling, booking, or planning
    something - e.g. 'Schedule a follow-up', 'I will meet him next week', 'remind me to send samples',
    'i will call him tomorrow', 'book a demo next week', 'plan a call on friday' etc.

    Do NOT use this tool for logging past interactions or general conversation.
    Do NOT use this for analysis, summaries, or reviewing past visits.
    Do NOT call this unless the rep has explicitly asked to schedule something.

    Requires a real interaction_id from a previously logged interaction in this
    session. If no interaction has been logged yet, ask the rep to log one first.

    If `due_date` is provided, it is used directly. Otherwise this tool asks the Groq
    large model to suggest an optimal date based on HCP tier.
    - tier1: 7 days
    - tier2: 14 days
    - tier3: 21 days

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
    parsed_interaction_id = None
    if interaction_id and interaction_id != "None" and interaction_id != "null":
        try:
            parsed_interaction_id = uuid.UUID(interaction_id)
        except ValueError:
            pass
            
    parsed_hcp_id = None
    if hcp_id and hcp_id != "None" and hcp_id != "null":
        try:
            parsed_hcp_id = uuid.UUID(hcp_id)
        except ValueError:
            pass

    with get_db_session() as db:
        interaction = db.get(Interaction, parsed_interaction_id)
        hcp = db.get(HCP, parsed_hcp_id)
        if not interaction:
            return {
                "error": f"Could not find interaction with id '{interaction_id}'"
                    "please ensure an interaction has been logged first.",
                "success": False,
            }
        if not hcp:
            return {
                "error": f"HCP not found for id: {hcp_id}. Please select a valid HCP.",
                "success": False,
            }

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
            try:
                llm_raw = _llm(settings.groq_large_model).invoke(prompt).content
            except Exception as e:
                return {"error": f"Groq API error while scheduling follow-up. Please try again later.", "success": False}

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
    Analyze and summarize ALL past interactions with an HCP.
    Use when the rep asks for analysis, insights, patterns, or a review of their relationship with the HCP.
    - e.g. 'analyze my visits', 'how have my visits with Dr. X gone?', 'give me a summary of my interactions', 'what's the sentiment tend?', 'how is my engagemnet with this doctor?'.

    Do NOT require an interaction_id. Only needs hcp_id.
    Do NOT use this for scheduling or logging - only for analysis of exisiting data.

    Returns:
    - `analysis`: structured analysis dict
    - `summary`: human-readable recap string
    """
    parsed_hcp_id = uuid.UUID(hcp_id)

    with get_db_session() as db:
        hcp = db.get(HCP, parsed_hcp_id)
        if not hcp:
            return {
                "error": f"HCP not found for id: {hcp_id}. Please select a valid HCP.",
                "success": False,
            }

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
        try:
            analysis_raw = _llm(settings.groq_large_model).invoke(prompt).content
        except Exception as e:
            return {"error": f"Groq API error while analyzing visits. Please try again later.", "success": False}

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
