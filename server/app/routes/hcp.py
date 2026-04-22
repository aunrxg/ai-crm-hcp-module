from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import HCP, Interaction
from app.schemas import HCPCreate, HCPResponse, InteractionResponse

router = APIRouter(tags=["hcp"])


@router.get("/api/hcp", response_model=list[HCPResponse])
def list_hcps(db: Session = Depends(get_db)) -> list[HCP]:
    return db.query(HCP).order_by(HCP.name.asc()).all()


@router.get("/api/hcp/search", response_model=list[HCPResponse])
def search_hcp(q: str = Query(..., min_length=1), db: Session = Depends(get_db)) -> list[HCP]:
    pattern = f"%{q.strip()}%"
    return (
        db.query(HCP)
        .filter(or_(HCP.name.ilike(pattern), HCP.hospital.ilike(pattern)))
        .order_by(HCP.name.asc())
        .limit(20)
        .all()
    )


@router.get("/api/hcp/{hcp_id}")
def get_hcp(hcp_id: UUID, db: Session = Depends(get_db)) -> dict:
    hcp = db.query(HCP).filter(HCP.id == hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail="HCP not found")

    interactions = (
        db.query(Interaction)
        .options(selectinload(Interaction.hcp))
        .filter(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.date.desc(), Interaction.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "hcp": HCPResponse.model_validate(hcp),
        "interactions": [InteractionResponse.model_validate(item) for item in interactions],
    }


@router.post("/api/hcp", response_model=HCPResponse)
def create_hcp(payload: HCPCreate, db: Session = Depends(get_db)) -> HCP:
    hcp = HCP(
        name=payload.name,
        specialty=payload.specialty,
        hospital=payload.hospital,
        city=payload.city,
        tier=payload.tier,
        email=payload.email,
        phone=payload.phone,
    )
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    return hcp


