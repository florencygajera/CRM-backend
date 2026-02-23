from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.security import (
    hash_password,
    verify_password,            # ✅ use the imported one
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.models.user import UserRole
from app.repositiories.tenant_repo import create_tenant
from app.repositiories.user_repo import create_user, get_user_any_tenant_by_email


class AuthError(Exception):
    pass


def register_tenant(db: Session, tenant_name: str, owner_email: str, owner_password: str):
    existing = get_user_any_tenant_by_email(db, owner_email)
    if existing:
        raise AuthError("Email already exists")

    tenant = create_tenant(db, tenant_name)

    owner = create_user(
        db,
        tenant_id=tenant.id,
        email=owner_email,
        password_hash=hash_password(owner_password),
        role=UserRole.OWNER,
    )

    access = create_access_token(sub=str(owner.id), tenant_id=str(tenant.id), role=owner.role)
    refresh = create_refresh_token(sub=str(owner.id), tenant_id=str(tenant.id), role=owner.role)

    owner.refresh_token_hash = hash_refresh_token(refresh)
    db.add(owner)
    db.commit()
    db.refresh(owner)

    return tenant, owner, access, refresh


def login(db: Session, email: str, password: str):
    user = get_user_any_tenant_by_email(db, email)

    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Invalid credentials")

    if hasattr(user, "is_active") and not user.is_active:
        raise AuthError("User disabled")

    access = create_access_token(sub=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
    refresh = create_refresh_token(sub=str(user.id), tenant_id=str(user.tenant_id), role=user.role)

    user.refresh_token_hash = hash_refresh_token(refresh)
    db.add(user)
    db.commit()

    return access, refresh