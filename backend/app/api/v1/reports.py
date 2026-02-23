"""Reporting routes: revenue, top services, staff performance, cancellation rate."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.core.deps import get_db, get_token_payload
from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_service import AppointmentService

router = APIRouter()  # prefix set by parent router


@router.get("/revenue")
def revenue_report(
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    start = datetime.fromisoformat(from_date)
    end = datetime.fromisoformat(to_date)

    total = db.scalar(
        select(func.sum(AppointmentService.price_snapshot))
        .join(Appointment, Appointment.id == AppointmentService.appointment_id)
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.CONFIRMED,
            Appointment.start_at >= start,
            Appointment.start_at <= end,
        )
    ) or 0

    return {
        "success": True,
        "data": {
            "from": from_date,
            "to": to_date,
            "total_revenue": float(total),
        },
    }


@router.get("/services/top")
def top_services(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])

    rows = db.execute(
        select(
            AppointmentService.service_id,
            func.count(AppointmentService.id).label("count"),
        )
        .join(Appointment, Appointment.id == AppointmentService.appointment_id)
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.CONFIRMED,
        )
        .group_by(AppointmentService.service_id)
        .order_by(func.count(AppointmentService.id).desc())
    ).all()

    return {
        "success": True,
        "data": [
            {"service_id": str(r.service_id), "bookings": r.count}
            for r in rows
        ],
    }


@router.get("/staff/performance")
def staff_performance(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])

    rows = db.execute(
        select(
            Appointment.staff_user_id,
            func.count(Appointment.id).label("appointments"),
        )
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.CONFIRMED,
        )
        .group_by(Appointment.staff_user_id)
        .order_by(func.count(Appointment.id).desc())
    ).all()

    return {
        "success": True,
        "data": [
            {"staff_user_id": str(r.staff_user_id), "appointments": r.appointments}
            for r in rows
        ],
    }


@router.get("/cancellation-rate")
def cancellation_rate(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])

    total = db.scalar(
        select(func.count(Appointment.id)).where(Appointment.tenant_id == tenant_id)
    ) or 0

    cancelled = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == AppointmentStatus.CANCELLED,
        )
    ) or 0

    rate = (cancelled / total * 100) if total > 0 else 0.0

    return {
        "success": True,
        "data": {
            "total": total,
            "cancelled": cancelled,
            "cancellation_rate_percent": round(rate, 2),
        },
    }
