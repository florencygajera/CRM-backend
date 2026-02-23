"""Customer management routes."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload, require_roles
from app.models.customer import Customer
from app.models.user import UserRole
from app.schemas.customer import CustomerCreateIn

router = APIRouter()  # prefix set by parent router


@router.get("")
def list_customers(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    rows = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": str(c.id),
                    "full_name": c.full_name,
                    "phone": c.phone,
                    "email": c.email,
                }
                for c in rows
            ]
        },
    }


@router.post("")
def create_customer(
    body: CustomerCreateIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(
        require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.STAFF)
    ),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    customer = Customer(
        tenant_id=tenant_id,
        full_name=body.full_name,
        phone=body.phone,
        email=body.email,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return {"success": True, "data": {"id": str(customer.id)}}
