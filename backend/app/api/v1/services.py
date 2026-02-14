import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload, require_roles
from app.models.service import Service
from app.schemas.service import ServiceCreateIn
from app.models.user import UserRole

router = APIRouter(prefix="/services")

@router.get("")
def list_services(db: Session = Depends(get_db), payload: dict = Depends(get_token_payload)):
    tenant_id = uuid.UUID(payload["tenant_id"])
    rows = db.scalars(select(Service).where(Service.tenant_id == tenant_id, Service.is_active == True)).all()
    return {"success": True, "data": {"items": [
        {"id": str(s.id), "name": s.name, "category": s.category, "duration_min": s.duration_min,
         "price": float(s.price), "is_active": s.is_active} for s in rows
    ]}}

@router.post("")
def create_service(
    body: ServiceCreateIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    s = Service(
        tenant_id=tenant_id,
        name=body.name,
        category=body.category,
        duration_min=body.duration_min,
        price=body.price
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"success": True, "data": {"id": str(s.id)}}
