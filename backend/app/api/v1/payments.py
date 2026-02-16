import uuid, json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.deps import get_db, get_token_payload
from app.core.config import settings
from app.models.appointment import Appointment, PaymentStatus as ApptPayStatus
from app.models.customer import Customer
from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.models.payment_event import PaymentEvent
from app.schemas.payment import CreateRazorpayOrderIn
from app.integration.razorpay import verify_razorpay_webhook_signature

import requests  # pip install requests

router = APIRouter(prefix="/payments")

@router.post("/razorpay/order")
def create_razorpay_order(
    body: CreateRazorpayOrderIn,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_token_payload),
):
    tenant_id = uuid.UUID(payload["tenant_id"])
    appt_id = uuid.UUID(body.appointment_id)

    appt = db.scalar(select(Appointment).where(Appointment.tenant_id == tenant_id, Appointment.id == appt_id))
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # set due amount on appointment
    appt.amount_due = body.amount
    appt.currency = body.currency
    appt.payment_status = ApptPayStatus.UNPAID

    # create provider order (Razorpay Orders API)
    # NOTE: This requires internet. If your machine is offline, skip calling Razorpay and just store a "mock" order.
    url = "https://api.razorpay.com/v1/orders"
    auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)

    order_payload = {
        "amount": int(round(float(body.amount) * 100)),  # paisa
        "currency": body.currency,
        "receipt": f"appt_{appt_id}",
        "notes": {"tenant_id": str(tenant_id), "appointment_id": str(appt_id)},
    }

    resp = requests.post(url, auth=auth, json=order_payload, timeout=20)
    if resp.status_code >= 300:
        raise HTTPException(status_code=400, detail=f"Razorpay order create failed: {resp.text}")

    order = resp.json()
    provider_order_id = order["id"]

    customer = db.scalar(select(Customer).where(Customer.tenant_id == tenant_id, Customer.id == appt.customer_id))

    pay = Payment(
        tenant_id=tenant_id,
        appointment_id=appt.id,
        customer_id=appt.customer_id,
        provider=PaymentProvider.RAZORPAY,
        status=PaymentStatus.CREATED,
        amount=body.amount,
        currency=body.currency,
        provider_order_id=provider_order_id,
    )

    db.add(PaymentEvent(
        tenant_id=pay.tenant_id,
        provider=PaymentProvider.RAZORPAY,
        event_type="order.created",
        provider_event_id=provider_order_id,  # Use order ID as event ID (no separate event at order creation)
        provider_payment_id="",  # Payment not yet made
        provider_order_id=provider_order_id,
        payload_json=json.dumps(order),  # Store Razorpay order response, not JWT token payload
    ))


    db.add(pay)
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
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,  # frontend needs this
            "customer": {
                "name": customer.full_name if customer else "",
                "email": customer.email if customer else "",
                "phone": customer.phone if customer else "",
            },
        },
    }

@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if not sig:
        raise HTTPException(status_code=400, detail="Missing signature")

    if not verify_razorpay_webhook_signature(raw, sig, settings.RAZORPAY_WEBHOOK_SECRET):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = json.loads(raw.decode("utf-8"))
    event = payload.get("event", "")
    entity = (payload.get("payload") or {}).get("payment") or {}
    payment_entity = entity.get("entity") or {}

    provider_payment_id = payment_entity.get("id", "")
    provider_order_id = payment_entity.get("order_id", "")
    status = payment_entity.get("status", "")  # created/authorized/captured/failed/refunded

    # store event (tenant_id will be resolved from Payment)
    # find payment by provider order id
    pay = db.scalar(select(Payment).where(Payment.provider_order_id == provider_order_id))
    if not pay:
        # accept webhook but log minimal
        return {"success": True}

    db.add(PaymentEvent(
        tenant_id=pay.tenant_id,
        provider=PaymentProvider.RAZORPAY,
        event_type=event,
        provider_event_id=(payload.get("id") or ""),
        provider_payment_id=provider_payment_id,
        provider_order_id=provider_order_id,
        payload_json=json.dumps(payload),
    ))

    # update payment status
    if status == "authorized":
        pay.status = PaymentStatus.AUTHORIZED
    elif status == "captured":
        pay.status = PaymentStatus.CAPTURED
    elif status == "failed":
        pay.status = PaymentStatus.FAILED
    elif status == "refunded":
        pay.status = PaymentStatus.REFUNDED

    # update appointment payment status
    appt = db.scalar(select(Appointment).where(Appointment.id == pay.appointment_id))
    if appt:
        if pay.status == PaymentStatus.CAPTURED:
            appt.payment_status = ApptPayStatus.PAID
        elif pay.status == PaymentStatus.FAILED:
            appt.payment_status = ApptPayStatus.FAILED
        elif pay.status == PaymentStatus.REFUNDED:
            appt.payment_status = ApptPayStatus.REFUNDED

    pay.provider_payment_id = provider_payment_id

    db.commit()
    return {"success": True}
