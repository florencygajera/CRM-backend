"""Authentication routes: register, login, refresh, logout."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload
from app.core.security import (
    decode_token, create_access_token, create_refresh_token,
    verify_refresh_token_hash, hash_refresh_token,
)
from app.models.user import User
from app.schemas.auth import RegisterTenantIn, LoginIn, TokenOut
from app.services.auth_service import register_tenant, login, AuthError

router = APIRouter()  # prefix set by parent router


@router.post("/register-tenant", response_model=TokenOut)
def register_tenant_route(body: RegisterTenantIn, db: Session = Depends(get_db)):
    try:
        _, _, access, refresh = register_tenant(
            db, body.tenant_name, body.owner_email, body.owner_password,
        )
        db.commit()
        return TokenOut(access_token=access, refresh_token=refresh)
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/login", response_model=TokenOut)
def login_route(body: LoginIn, db: Session = Depends(get_db)):
    try:
        access, refresh = login(db, body.email, body.password)
        return TokenOut(access_token=access, refresh_token=refresh)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.post("/refresh", response_model=TokenOut)
def refresh_route(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token required")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if not user.refresh_token_hash or not verify_refresh_token_hash(
        refresh_token, user.refresh_token_hash,
    ):
        raise HTTPException(status_code=401, detail="Refresh token revoked or rotated")

    # Rotate refresh token
    new_access = create_access_token(
        sub=str(user.id), tenant_id=str(user.tenant_id), role=user.role,
    )
    new_refresh = create_refresh_token(
        sub=str(user.id), tenant_id=str(user.tenant_id), role=user.role,
    )
    user.refresh_token_hash = hash_refresh_token(new_refresh)
    db.add(user)
    db.commit()

    return TokenOut(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    user = db.scalar(select(User).where(User.id == payload["sub"]))
    if user:
        user.refresh_token_hash = None
        db.add(user)
        db.commit()
    return {"success": True}