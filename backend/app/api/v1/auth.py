from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.schemas.auth import RegisterTenantIn, LoginIn, TokenOut
from app.services.auth_service import register_tenant, login, AuthError
from app.core.security import decode_token, create_access_token, create_refresh_token

router = APIRouter(prefix="/auth")

@router.post("/register-tenant", response_model=TokenOut)
def register_tenant_route(body: RegisterTenantIn, db: Session = Depends(get_db)):
    try:
        _, _, access, refresh = register_tenant(db, body.tenant_name, body.owner_email, body.owner_password)
        db.commit()
        return TokenOut(access_token=access, refresh_token=refresh)
    except AuthError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=TokenOut)
def login_route(body: LoginIn, db: Session = Depends(get_db)):
    try:
        access, refresh = login(db, body.email, body.password)
        return TokenOut(access_token=access, refresh_token=refresh)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/refresh", response_model=TokenOut)
def refresh_route(refresh_token: str):
    # Simple refresh endpoint (MVP). Later: store refresh tokens + revoke.
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token required")

    access = create_access_token(sub=payload["sub"], tenant_id=payload["tenant_id"], role=payload["role"])
    new_refresh = create_refresh_token(sub=payload["sub"], tenant_id=payload["tenant_id"], role=payload["role"])
    return TokenOut(access_token=access, refresh_token=new_refresh)
