"""Service management routes."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload, require_roles
from app.models.service import Service
from app.models.user import UserRole
from app.schemas.service import ServiceCreateIn

router = APIRouter()  # prefix set by parent router


@router.get("")
def list_services(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    rows = db.scalars(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.is_active.is_(True),
        )
    ).all()
    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "category": s.category,
                    "duration_min": s.duration_min,
                    "price": float(s.price),
                    "is_active": s.is_active,
                }
                for s in rows
            ]
        },
    }


@router.post("")
def create_service(
    body: ServiceCreateIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    service = Service(
        tenant_id=tenant_id,
        name=body.name,
        category=body.category,
        duration_min=body.duration_min,
        price=body.price,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return {"success": True, "data": {"id": str(service.id)}}
