import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload, require_roles
from app.models.customer import Customer
from app.schemas.customer import CustomerCreateIn
from app.models.user import UserRole

router = APIRouter(prefix="/customers")

@router.get("")
def list_customers(db: Session = Depends(get_db), payload: dict = Depends(get_token_payload)):
    tenant_id = uuid.UUID(payload["tenant_id"])
    rows = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    return {"success": True, "data": {"items": [
        {"id": str(c.id), "full_name": c.full_name, "phone": c.phone, "email": c.email} for c in rows
    ]}}

@router.post("")
def create_customer(
    body: CustomerCreateIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_roles(UserRole.OWNER, UserRole.MANAGER, UserRole.STAFF)),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    c = Customer(tenant_id=tenant_id, full_name=body.full_name, phone=body.phone, email=body.email)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"success": True, "data": {"id": str(c.id)}}
