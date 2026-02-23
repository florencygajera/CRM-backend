"""Payment routes: Razorpay order, webhook, verify, refund, list."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_branch_id, get_db, get_token_payload, require_roles
from app.integration.razorpay import (
    verify_razorpay_checkout_signature,
    verify_razorpay_webhook_signature,
)
from app.integration.razorpay_client import client
from app.models.appointment import Appointment, ApptPayStatus
from app.models.customer import Customer
from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.models.payment_event import PaymentEvent
from app.models.user import UserRole
from app.schemas.payment import (
    CreateRazorpayOrderIn,
    CreateRazorpayOrderOut,
    RazorpayVerifyIn,
    RazorpayVerifyOut,
    RefundIn,
    RefundOut,
)

router = APIRouter()  # prefix set by parent router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_STATUS_MAP = {
    "authorized": PaymentStatus.AUTHORIZED,
    "captured": PaymentStatus.CAPTURED,
    "failed": PaymentStatus.FAILED,
    "refunded": PaymentStatus.REFUNDED,
}

_APPT_STATUS_MAP = {
    PaymentStatus.CAPTURED: ApptPayStatus.PAID,
    PaymentStatus.FAILED: ApptPayStatus.FAILED,
    PaymentStatus.REFUNDED: ApptPayStatus.REFUNDED,
}


def _sync_appointment_payment_status(
    db: Session,
    tenant_id: uuid.UUID,
    appointment_id: uuid.UUID,
    pay_status: str,
    *,
    branch_id: uuid.UUID | None = None,
) -> None:
    """Update the appointment's payment_status to match the payment."""
    filters = [
        Appointment.tenant_id == tenant_id,
        Appointment.id == appointment_id,
    ]
    if branch_id is not None:
        filters.append(Appointment.branch_id == branch_id)

    appt = db.scalar(select(Appointment).where(*filters))
    if appt and pay_status in _APPT_STATUS_MAP:
        appt.payment_status = _APPT_STATUS_MAP[pay_status]


# ---------------------------------------------------------------------------
# Razorpay: Create Order
# ---------------------------------------------------------------------------
@router.post("/razorpay/order", response_model=CreateRazorpayOrderOut)
def create_razorpay_order(
    body: CreateRazorpayOrderIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    appt_id = body.appointment_id

    appt = db.scalar(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.branch_id == branch_id,
            Appointment.id == appt_id,
        )
    )
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found for this branch")

    appt.amount_due = body.amount
    appt.currency = body.currency
    appt.payment_status = ApptPayStatus.UNPAID

    order = client.order.create(
        {
            "amount": int(round(float(body.amount) * 100)),
            "currency": body.currency,
            "receipt": f"appt_{appt_id}",
            "notes": {
                "tenant_id": str(tenant_id),
                "branch_id": str(branch_id),
                "appointment_id": str(appt_id),
            },
        }
    )
    provider_order_id = order["id"]

    customer = db.scalar(
        select(Customer).where(
            Customer.tenant_id == tenant_id, Customer.id == appt.customer_id,
        )
    )

    pay = Payment(
        tenant_id=tenant_id,
        branch_id=branch_id,
        appointment_id=appt.id,
        customer_id=appt.customer_id,
        status=PaymentStatus.CREATED,
        amount=body.amount,
        currency=body.currency,
        provider=PaymentProvider.RAZORPAY,
        provider_order_id=provider_order_id,
    )
    db.add(pay)
    db.flush()

    db.add(
        PaymentEvent(
            tenant_id=tenant_id,
            provider=PaymentProvider.RAZORPAY,
            event_type="order.created",
            provider_event_id=provider_order_id,
            provider_payment_id=None,
            provider_order_id=provider_order_id,
            payload=order,
        )
    )

    db.commit()
    db.refresh(pay)

    return {
        "success": True,
        "data": {
            "payment_id": str(pay.id),
            "provider": pay.provider,
            "provider_order_id": pay.provider_order_id,
            "amount": float(pay.amount),
            "currency": pay.currency,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "customer": {
                "name": customer.full_name if customer else "",
                "email": customer.email if customer else "",
                "phone": customer.phone if customer else "",
            },
        },
    }


# ---------------------------------------------------------------------------
# Razorpay: Webhook
# ---------------------------------------------------------------------------
@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Unauthenticated webhook receiver — verifies signature, stores the event
    idempotently, and updates payment / appointment status.
    """
    raw = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if not sig:
        raise HTTPException(status_code=400, detail="Missing signature")

    if not verify_razorpay_webhook_signature(raw, sig, settings.RAZORPAY_WEBHOOK_SECRET):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload_json = await request.json()
    event_type = payload_json.get("event", "")

    nested = payload_json.get("payload") or {}
    payment_entity = (nested.get("payment") or {}).get("entity") or {}
    order_entity = (nested.get("order") or {}).get("entity") or {}
    refund_entity = (nested.get("refund") or {}).get("entity") or {}

    event_id = (
        payment_entity.get("id")
        or order_entity.get("id")
        or refund_entity.get("id")
    )
    provider_order_id = (
        payment_entity.get("order_id")
        or order_entity.get("id")
        or refund_entity.get("order_id")
        or ""
    )
    provider_payment_id = payment_entity.get("id") or refund_entity.get("payment_id") or ""
    status = (
        payment_entity.get("status")
        or order_entity.get("status")
        or refund_entity.get("status")
        or ""
    )

    notes = payment_entity.get("notes") or order_entity.get("notes") or {}
    tenant_id_str = notes.get("tenant_id")

    # Resolve payment row (tenant-scoped first, fallback to global)
    pay = None
    if tenant_id_str and provider_order_id:
        try:
            pay = db.scalar(
                select(Payment).where(
                    Payment.tenant_id == uuid.UUID(tenant_id_str),
                    Payment.provider_order_id == provider_order_id,
                )
            )
        except Exception:
            pass

    if not pay and provider_order_id:
        pay = db.scalar(
            select(Payment).where(Payment.provider_order_id == provider_order_id)
        )

    if not pay:
        return {"success": True}

    # Idempotency
    if event_id:
        existing = db.scalar(
            select(PaymentEvent).where(
                PaymentEvent.tenant_id == pay.tenant_id,
                PaymentEvent.provider_event_id == event_id,
            )
        )
        if existing:
            return {"success": True}

    db.add(
        PaymentEvent(
            tenant_id=pay.tenant_id,
            provider=PaymentProvider.RAZORPAY,
            event_type=event_type or "unknown",
            provider_event_id=event_id,
            provider_order_id=provider_order_id or None,
            provider_payment_id=provider_payment_id or None,
            payload=payload_json,
        )
    )

    if status in _STATUS_MAP:
        pay.status = _STATUS_MAP[status]

    if provider_payment_id:
        pay.provider_payment_id = provider_payment_id

    _sync_appointment_payment_status(db, pay.tenant_id, pay.appointment_id, pay.status)

    db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# Razorpay: Verify Checkout
# ---------------------------------------------------------------------------
@router.post("/razorpay/verify", response_model=RazorpayVerifyOut)
def razorpay_verify(
    body: RazorpayVerifyIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    tenant_id = uuid.UUID(payload["tenant_id"])

    pay = db.scalar(
        select(Payment).where(
            Payment.id == body.payment_id,
            Payment.tenant_id == tenant_id,
            Payment.branch_id == branch_id,
        )
    )
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found for this branch")

    if pay.status == PaymentStatus.CAPTURED:
        return {"success": True, "payment_status": pay.status}

    if pay.provider_order_id != body.razorpay_order_id:
        raise HTTPException(status_code=400, detail="Order ID mismatch")

    if not verify_razorpay_checkout_signature(
        order_id=body.razorpay_order_id,
        payment_id=body.razorpay_payment_id,
        signature=body.razorpay_signature,
        key_secret=settings.RAZORPAY_KEY_SECRET,
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    rp_payment = client.payment.fetch(body.razorpay_payment_id)
    rp_status = rp_payment.get("status", "")
    rp_amount_paisa = int(rp_payment.get("amount", 0))
    rp_currency = rp_payment.get("currency", "")

    expected_paisa = int(Decimal(str(pay.amount)) * 100)
    if rp_currency != pay.currency:
        raise HTTPException(status_code=400, detail="Currency mismatch")
    if rp_amount_paisa != expected_paisa:
        raise HTTPException(status_code=400, detail="Amount mismatch")

    pay.provider_payment_id = body.razorpay_payment_id
    pay.status = _STATUS_MAP.get(rp_status, PaymentStatus.FAILED)

    _sync_appointment_payment_status(
        db, tenant_id, pay.appointment_id, pay.status, branch_id=branch_id,
    )

    db.add(
        PaymentEvent(
            tenant_id=tenant_id,
            provider=PaymentProvider.RAZORPAY,
            event_type="checkout.verified",
            provider_event_id=body.razorpay_payment_id,
            provider_order_id=body.razorpay_order_id,
            provider_payment_id=body.razorpay_payment_id,
            payload={"razorpay_payment": rp_payment},
        )
    )

    # Receipt + email (idempotent)
    if pay.status == PaymentStatus.CAPTURED and pay.receipt_sent_at is None:
        appt = db.scalar(
            select(Appointment).where(
                Appointment.tenant_id == tenant_id,
                Appointment.id == pay.appointment_id,
            )
        )
        customer = None
        if appt:
            customer = db.scalar(
                select(Customer).where(
                    Customer.tenant_id == tenant_id, Customer.id == appt.customer_id,
                )
            )

        from app.services.receipt_service import generate_receipt_pdf
        from app.workers.tasks import send_email

        pdf_bytes = generate_receipt_pdf(
            receipt_no=str(pay.id),
            customer_name=customer.full_name if customer else "Customer",
            amount=float(pay.amount),
            currency=pay.currency,
        )
        send_email.delay(
            to_email=(customer.email if customer and customer.email else "fallback@email.com"),
            subject="Payment Receipt",
            body="Your payment was successful. Receipt attached.",
            attachment_bytes=pdf_bytes,
            attachment_name=f"receipt_{pay.id}.pdf",
        )
        pay.receipt_sent_at = datetime.now(timezone.utc)

    db.commit()
    return {"success": True, "payment_status": pay.status}


# ---------------------------------------------------------------------------
# Razorpay: Refund
# ---------------------------------------------------------------------------
@router.post(
    "/razorpay/refund",
    response_model=RefundOut,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.MANAGER))],
)
def razorpay_refund(
    body: RefundIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    tenant_id = uuid.UUID(payload["tenant_id"])

    pay = db.scalar(
        select(Payment).where(
            Payment.id == body.payment_id,
            Payment.tenant_id == tenant_id,
            Payment.branch_id == branch_id,
        )
    )
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found for this branch")
    if pay.provider != PaymentProvider.RAZORPAY:
        raise HTTPException(status_code=400, detail="Not a Razorpay payment")
    if not pay.provider_payment_id:
        raise HTTPException(status_code=400, detail="Missing provider_payment_id")
    if pay.status != PaymentStatus.CAPTURED:
        raise HTTPException(status_code=400, detail="Only CAPTURED payments can be refunded")
    if pay.refund_id and pay.refund_status == "processed":
        raise HTTPException(status_code=400, detail="Payment already refunded")

    refund_payload = {}
    if body.amount is not None:
        if body.amount <= 0:
            raise HTTPException(status_code=400, detail="Refund amount must be > 0")
        refund_payload["amount"] = int(round(float(body.amount) * 100))

    refund = client.payment.refund(pay.provider_payment_id, refund_payload)

    pay.refund_id = refund.get("id")
    pay.refund_status = refund.get("status")

    if pay.refund_status == "processed":
        pay.status = PaymentStatus.REFUNDED
        _sync_appointment_payment_status(
            db, tenant_id, pay.appointment_id, pay.status, branch_id=branch_id,
        )

    db.add(
        PaymentEvent(
            tenant_id=tenant_id,
            provider=PaymentProvider.RAZORPAY,
            event_type="refund.created",
            provider_event_id=refund.get("id"),
            provider_order_id=pay.provider_order_id,
            provider_payment_id=pay.provider_payment_id,
            payload=refund,
        )
    )

    db.commit()
    return {
        "success": True,
        "refund": refund,
        "payment_status": pay.status,
        "refund_status": pay.refund_status,
    }


# ---------------------------------------------------------------------------
# List payments
# ---------------------------------------------------------------------------
@router.get("/")
def list_payments(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
    branch_id: uuid.UUID = Depends(get_branch_id),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    q = (
        select(Payment)
        .where(Payment.tenant_id == tenant_id, Payment.branch_id == branch_id)
        .order_by(Payment.created_at.desc())
    )
    return db.scalars(q).all()
