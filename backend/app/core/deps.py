from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_token_payload(token: str = Depends(oauth2)) -> dict:
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Access token required")
    return payload

def require_roles(*allowed: str):
    def _guard(payload: dict = Depends(get_token_payload)) -> dict:
        role = payload.get("role")
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        return payload
    return _guard
