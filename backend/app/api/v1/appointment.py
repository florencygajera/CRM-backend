"""Appointment management routes: availability, create, patch, list."""

import uuid
from datetime import datetime, timedelta, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload, get_branch_id
from app.models.appointment import Appointment, AppointmentStatus
from app.models.appointment_service import AppointmentService
from app.models.customer import Customer
from app.models.service import Service
from app.models.staff import Staff
from app.schemas.appointment import AppointmentCreateIn, AppointmentPatchIn
from app.workers.tasks import send_booking_email

router = APIRouter()  # prefix set by parent router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _calc_total_duration_min(services: list[Service]) -> int:
    return sum(int(s.duration_min) for s in services)


def _overlap_exists(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID,
    staff_user_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(Appointment.id).where(
        Appointment.tenant_id == tenant_id,
        Appointment.branch_id == branch_id,
        Appointment.staff_user_id == staff_user_id,
        Appointment.status != AppointmentStatus.CANCELLED,
        Appointment.start_at < end_at,
        Appointment.end_at > start_at,
    )
    if exclude_id:
        stmt = stmt.where(Appointment.id != exclude_id)
    return db.scalar(stmt) is not None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/availability")
def availability(
    staff_user_id: str = Query(...),
    service_ids: list[str] = Query(...),
    day: str = Query(..., description="YYYY-MM-DD"),
    slot_step_min: int = Query(15, ge=5, le=60),
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    """
    Returns available start times for a staff member on a given day
    (branch-scoped), using their ``work_start_time`` / ``work_end_time``.
    """
    tenant_id = uuid.UUID(payload["tenant_id"])
    staff_uuid = uuid.UUID(staff_user_id)

    try:
        day_date = datetime.fromisoformat(day).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    svc_uuids = [uuid.UUID(s) for s in service_ids]
    services = db.scalars(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.id.in_(svc_uuids),
            Service.is_active.is_(True),
        )
    ).all()
    if len(services) != len(svc_uuids):
        raise HTTPException(status_code=400, detail="One or more services not found")

    duration_min = _calc_total_duration_min(services)

    staff = db.scalar(
        select(Staff).where(
            Staff.tenant_id == tenant_id,
            Staff.id == staff_uuid,
        )
    )
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    start_hour, start_min = map(int, staff.work_start_time.split(":"))
    end_hour, end_min = map(int, staff.work_end_time.split(":"))

    start_work = datetime.combine(day_date, time(start_hour, start_min))
    end_work = datetime.combine(day_date, time(end_hour, end_min))

    day_start = datetime.combine(day_date, time.min)
    day_end = datetime.combine(day_date, time(23, 59, 59))

    existing = db.scalars(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.branch_id == branch_id,
            Appointment.staff_user_id == staff_uuid,
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.start_at >= day_start,
            Appointment.start_at <= day_end,
        )
    ).all()

    busy = [(a.start_at, a.end_at) for a in existing]

    slots: list[str] = []
    cursor = start_work
    while cursor + timedelta(minutes=duration_min) <= end_work:
        cand_end = cursor + timedelta(minutes=duration_min)
        conflict = any(bs < cand_end and be > cursor for bs, be in busy)
        if not conflict:
            slots.append(cursor.isoformat())
        cursor += timedelta(minutes=slot_step_min)

    return {"success": True, "data": {"duration_min": duration_min, "slots": slots}}


@router.post("")
def create_appointment(
    body: AppointmentCreateIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    staff_uuid = uuid.UUID(body.staff_user_id)
    customer_uuid = uuid.UUID(body.customer_id)

    svc_uuids = [uuid.UUID(s) for s in body.service_ids]
    services = db.scalars(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.id.in_(svc_uuids),
            Service.is_active.is_(True),
        )
    ).all()
    if len(services) != len(svc_uuids):
        raise HTTPException(status_code=400, detail="One or more services not found")

    duration_min = _calc_total_duration_min(services)
    end_time = body.start_at + timedelta(minutes=duration_min)

    if _overlap_exists(
        db,
        tenant_id=tenant_id,
        branch_id=branch_id,
        staff_user_id=staff_uuid,
        start_at=body.start_at,
        end_at=end_time,
    ):
        raise HTTPException(status_code=400, detail="Time slot already booked")

    appt = Appointment(
        tenant_id=tenant_id,
        branch_id=branch_id,
        customer_id=customer_uuid,
        staff_user_id=staff_uuid,
        start_at=body.start_at,
        end_at=end_time,
        status=AppointmentStatus.CONFIRMED,
        notes=body.notes,
    )
    db.add(appt)
    db.flush()

    for svc in services:
        db.add(
            AppointmentService(
                tenant_id=tenant_id,
                appointment_id=appt.id,
                service_id=svc.id,
                price_snapshot=float(svc.price),
                duration_snapshot_min=int(svc.duration_min),
            )
        )

    db.commit()
    db.refresh(appt)

    # Async emails (after commit so data is persisted)
    customer = db.scalar(
        select(Customer).where(
            Customer.tenant_id == tenant_id, Customer.id == customer_uuid,
        )
    )
    if customer and customer.email:
        subject = "Booking Confirmed ✅"
        email_body = (
            "Your appointment is confirmed.\n"
            f"Start: {appt.start_at}\n"
            f"End: {appt.end_at}\n"
            f"Status: {appt.status}"
        )
        send_booking_email.delay(customer.email, subject, email_body)

        # 24h reminder (only if in the future)
        reminder_time = appt.start_at - timedelta(hours=24)
        if reminder_time > datetime.now(timezone.utc):
            send_booking_email.apply_async(
                args=[customer.email, "Appointment Reminder ⏰", email_body],
                eta=reminder_time,
            )

    return {
        "success": True,
        "data": {
            "id": str(appt.id),
            "start_at": appt.start_at,
            "end_at": appt.end_at,
            "status": appt.status,
        },
    }


@router.patch("/{appointment_id}")
def patch_appointment(
    appointment_id: str,
    body: AppointmentPatchIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    appt_id = uuid.UUID(appointment_id)

    appt = db.scalar(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.branch_id == branch_id,
            Appointment.id == appt_id,
        )
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if body.status == AppointmentStatus.CANCELLED:
        appt.status = AppointmentStatus.CANCELLED

    if body.start_at is not None:
        new_start = body.start_at
        duration = int((appt.end_at - appt.start_at).total_seconds() // 60)
        new_end = new_start + timedelta(minutes=duration)

        if _overlap_exists(
            db,
            tenant_id=tenant_id,
            branch_id=branch_id,
            staff_user_id=appt.staff_user_id,
            start_at=new_start,
            end_at=new_end,
            exclude_id=appt.id,
        ):
            raise HTTPException(status_code=400, detail="Time slot already booked")

        appt.start_at = new_start
        appt.end_at = new_end

    if body.notes is not None:
        appt.notes = body.notes

    db.commit()
    db.refresh(appt)

    return {
        "success": True,
        "data": {
            "id": str(appt.id),
            "start_at": appt.start_at,
            "end_at": appt.end_at,
            "status": appt.status,
        },
    }


@router.get("")
def list_appointments(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    q = (
        select(Appointment)
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.branch_id == branch_id,
        )
        .order_by(Appointment.start_at.desc())
    )
    return db.scalars(q).all()
