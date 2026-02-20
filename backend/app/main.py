from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from app.models.service import Service  
from app.models.customer import Customer  
from app.models.tenant import Tenant 
from app.models.user import User      
from app.models.branch import Branch  
from app.models.appointment import Appointment  
from app.models.appointment_service import AppointmentService 
from app.models.staff import Staff  
from app.models.payment import Payment  # noqa: F401
from app.models.payment_event import PaymentEvent  # noqa: F401
from app.api.v1.router import api_router
from app.middlewares.rate_limit import RateLimitMiddleware, RateLimitRule
from app.middlewares.security_headers import SecurityHeadersMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.middlewares.request_context import RequestContextMiddleware
from sqlalchemy import text
from app.ai_models.router import router as ai_router

app = FastAPI(title=settings.APP_NAME)

# Include AI router
app.include_router(ai_router)

@app.get("/")
def root():
    return {"status": "ok"}

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Branch-Id"],
)

# ✅ Security headers
app.add_middleware(SecurityHeadersMiddleware)
# ✅ Rate limit (example global; better: auth/payment routes stricter)
app.add_middleware(RateLimitMiddleware, rule=RateLimitRule(window_sec=60, max_requests=120))
app.include_router(api_router, prefix="/api/v1")
app.add_middleware(RequestContextMiddleware)

@app.on_event("startup")
def startup():
    """
    In development, we auto-create tables for convenience.
    In staging/production, prefer Alembic migrations (alembic upgrade head).
    """
    if settings.ENV.lower() in {"dev", "development", "local"}:
        Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/health/live")
def live():
    return {"ok": True}

@app.get("/health/ready")
def ready():
    # DB check
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # Redis check (optional)
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {"db": True, "redis": redis_ok}