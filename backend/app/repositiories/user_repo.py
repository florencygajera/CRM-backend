from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User

def get_user_by_email(db: Session, tenant_id, email: str) -> User | None:
    stmt = select(User).where(User.tenant_id == tenant_id, User.email == email)
    return db.scalar(stmt)

def get_user_any_tenant_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return db.scalar(stmt)

def create_user(db: Session, *, tenant_id, email: str, password_hash: str, role: str) -> User:
    u = User(tenant_id=tenant_id, email=email, password_hash=password_hash, role=role)
    db.add(u)
    db.flush()
    return u
