"""Branch management routes."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload, require_roles
from app.models.branch import Branch
from app.models.user import UserRole
from app.schemas.branch import BranchCreateIn

router = APIRouter()  # prefix set by parent router


@router.get("")
def list_branches(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    rows = db.scalars(select(Branch).where(Branch.tenant_id == tenant_id)).all()
    return {
        "success": True,
        "data": {
            "items": [
                {"id": str(b.id), "name": b.name, "address": b.address}
                for b in rows
            ]
        },
    }


@router.post("")
def create_branch(
    body: BranchCreateIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER)),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    branch = Branch(tenant_id=tenant_id, name=body.name, address=body.address)
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return {
        "success": True,
        "data": {"id": str(branch.id), "name": branch.name, "address": branch.address},
    }
