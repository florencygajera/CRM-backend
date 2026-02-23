"""
Security utilities: password hashing, JWT creation / decoding,
and refresh-token hashing.
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from app.core.config import settings
from passlib.context import CryptContext

_pwd_ctx = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto"
)
# ---------------------------------------------------------------------------
# Password hashing (bcrypt)
# ---------------------------------------------------------------------------
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
print("JWT_SECRET loaded? len =", len(settings.JWT_SECRET or ""))
print("JWT_ALGO =", getattr(settings, "JWT_ALG", "HS256"))

from fastapi import HTTPException

def hash_password(password: str) -> str:
    if password is None:
        raise HTTPException(status_code=400, detail="Password is required")

    # bcrypt limit: 72 bytes
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password too long. Must be 72 bytes or less."
        )

    return _pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return ``True`` when *password* matches *password_hash*."""
    if not password or not password_hash:
        return False
    return _pwd_ctx.verify(password, password_hash)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
def create_access_token(*, sub: str, tenant_id: str, role: str) -> str:
    """Create a short-lived access JWT."""
    now = datetime.now(timezone.utc)
    payload = {
        "type": "access",
        "sub": sub,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(*, sub: str, tenant_id: str, role: str) -> str:
    """Create a long-lived refresh JWT."""
    now = datetime.now(timezone.utc)
    payload = {
        "type": "refresh",
        "sub": sub,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": now + timedelta(days=settings.JWT_REFRESH_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises:
        ValueError: If the token is invalid or expired.
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise ValueError("Token has expired") from None
    except JWTError:
        raise ValueError("Invalid token") from None


# ---------------------------------------------------------------------------
# Refresh-token storage helpers
# ---------------------------------------------------------------------------
def hash_refresh_token(token: str) -> str:
    """
    HMAC-SHA256 the refresh token before storing in the database.
    Uses JWT_SECRET as pepper to prevent rainbow-table attacks.
    """
    if not token:
        raise ValueError("Missing refresh token")
    return hmac.new(
        key=settings.JWT_SECRET.encode("utf-8"),
        msg=token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_refresh_token_hash(token: str, token_hash: str) -> bool:
    """Constant-time comparison of the presented token against the DB hash."""
    if not token or not token_hash:
        return False
    return hmac.compare_digest(hash_refresh_token(token), token_hash)