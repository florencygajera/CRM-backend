from sqlalchemy.orm import Session
from app.models.tenant import Tenant

def create_tenant(db: Session, name: str) -> Tenant:
    t = Tenant(name=name)
    db.add(t)
    db.flush()  # get id
    return t
