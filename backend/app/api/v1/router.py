"""V1 API aggregation router — mounts every domain sub-router."""

from fastapi import APIRouter

from app.api.v1 import (
    auth, branches, services, customers,
    appointment, staff, payments, reports,
)
from app.ai_models.router import router as ai_router

api_router = APIRouter()

api_router.include_router(auth.router,        prefix="/auth",         tags=["auth"])
api_router.include_router(branches.router,     prefix="/branches",     tags=["branches"])
api_router.include_router(services.router,     prefix="/services",     tags=["services"])
api_router.include_router(customers.router,    prefix="/customers",    tags=["customers"])
api_router.include_router(appointment.router,  prefix="/appointments", tags=["appointments"])
api_router.include_router(staff.router,        prefix="/staff",        tags=["staff"])
api_router.include_router(payments.router,     prefix="/payments",     tags=["payments"])
api_router.include_router(reports.router,      prefix="/reports",      tags=["reports"])
api_router.include_router(ai_router,           prefix="/ai",           tags=["ai"])