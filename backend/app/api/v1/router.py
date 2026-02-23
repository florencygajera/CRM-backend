from fastapi import APIRouter
from app.api.v1 import auth, branches, services, customers, appointments, staff, payments, reports
from app.ai_models.router import router as ai_router

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(branches.router, prefix="/branches", tags=["branches"])
router.include_router(services.router, prefix="/services", tags=["services"])
router.include_router(customers.router, prefix="/customers", tags=["customers"])
router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
router.include_router(staff.router, prefix="/staff", tags=["staff"])
router.include_router(payments.router, prefix="/payments", tags=["payments"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(ai_router, prefix="/ai", tags=["ai"])