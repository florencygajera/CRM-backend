"""
SmartServeAI — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.db.base import Base  # noqa: F401 – registers all models
from app.api.v1.router import api_router
from app.middlewares.rate_limit import RateLimitMiddleware, RateLimitRule
from app.middlewares.security_headers import SecurityHeadersMiddleware
from app.middlewares.request_context import RequestContextMiddleware


print("JWT_SECRET len =", len(settings.JWT_SECRET or ""))
print("JWT_SECRET preview =", (settings.JWT_SECRET or "")[:6])

# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    In development, auto-create tables for convenience.
    In staging / production, prefer Alembic migrations (``alembic upgrade head``).
    """
    if settings.ENV.lower() in {"dev", "development", "local"}:
        Base.metadata.create_all(bind=engine)
    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


# ── Routes ────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Middleware (outermost first) ──────────────────────────────────────────
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    RateLimitMiddleware,
    rule=RateLimitRule(window_sec=60, max_requests=120),
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Branch-Id"],
)


# ── Health-check endpoints ───────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/health/live")
def liveness():
    return {"ok": True}


@app.get("/health/ready")
def readiness():
    """Deep health check — verifies DB and Redis connectivity."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {"db": True, "redis": redis_ok}