from datetime import date as date_type
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import HCP, Interaction
from app.schemas import InteractionCreate, InteractionResponse, InteractionUpdate

router = APIRouter(tags=["interactions"])


@router.post("/api/interactions", response_model=InteractionResponse)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)) -> Interaction:
    hcp = db.query(HCP).filter(HCP.id == payload.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")

    interaction = Interaction(
        hcp_id=payload.hcp_id,
        interaction_type=payload.interaction_type,
        date=payload.date or date_type.today(),
        duration_minutes=payload.duration_minutes,
        products_discussed=payload.products_discussed,
        sentiment=payload.sentiment,
        raw_input=payload.raw_input,
        next_action=payload.next_action,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    interaction.hcp = hcp
    return interaction


@router.get("/api/interactions", response_model=list[InteractionResponse])
def list_interactions(hcp_id: UUID | None = Query(default=None), db: Session = Depends(get_db)) -> list[Interaction]:
    query = db.query(Interaction).options(selectinload(Interaction.hcp))
    if hcp_id:
        query = query.filter(Interaction.hcp_id == hcp_id)
    return query.order_by(Interaction.date.desc(), Interaction.created_at.desc()).all()


@router.get("/api/interactions/{interaction_id}", response_model=InteractionResponse)
def get_interaction(interaction_id: UUID, db: Session = Depends(get_db)) -> Interaction:
    interaction = (
        db.query(Interaction)
        .options(selectinload(Interaction.hcp))
        .filter(Interaction.id == interaction_id)
        .first()
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.put("/api/interactions/{interaction_id}", response_model=InteractionResponse)
def update_interaction(
    interaction_id: UUID,
    payload: InteractionUpdate,
    db: Session = Depends(get_db),
) -> Interaction:
    interaction = (
        db.query(Interaction)
        .options(selectinload(Interaction.hcp))
        .filter(Interaction.id == interaction_id)
        .first()
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(interaction, field, value)

    db.commit()
    db.refresh(interaction)
    return interaction
