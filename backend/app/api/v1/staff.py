"""Staff management routes."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload, require_roles
from app.models.staff import Staff
from app.models.user import UserRole
from app.schemas.staff import StaffCreateIn

router = APIRouter()  # prefix set by parent router


@router.get("")
def list_staff(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    rows = db.scalars(
        select(Staff).where(
            Staff.tenant_id == tenant_id,
            Staff.is_active.is_(True),
        )
    ).all()
    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": str(s.id),
                    "full_name": s.full_name,
                    "role": s.role,
                    "work_start_time": s.work_start_time,
                    "work_end_time": s.work_end_time,
                }
                for s in rows
            ]
        },
    }


@router.post("")
def create_staff(
    body: StaffCreateIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    member = Staff(
        tenant_id=tenant_id,
        full_name=body.full_name,
        role=body.role,
        work_start_time=body.work_start_time,
        work_end_time=body.work_end_time,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"success": True, "data": {"id": str(member.id)}}
