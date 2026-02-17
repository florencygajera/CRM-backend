from __future__ import annotations

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


# ---------- Common ----------
class CustomerInfoOut(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""


# ---------- Razorpay: Create Order ----------
class CreateRazorpayOrderIn(BaseModel):
    appointment_id: UUID
    amount: float = Field(..., gt=0)
    currency: str = "INR"


class CreateRazorpayOrderDataOut(BaseModel):
    payment_id: str
    provider: str
    provider_order_id: str
    amount: float
    currency: str
    razorpay_key_id: str
    customer: CustomerInfoOut


class CreateRazorpayOrderOut(BaseModel):
    success: bool
    data: CreateRazorpayOrderDataOut


# ---------- Razorpay: Verify Checkout ----------
class RazorpayVerifyIn(BaseModel):
    payment_id: UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class RazorpayVerifyOut(BaseModel):
    success: bool
    payment_status: str


# ---------- Refund ----------
class RefundIn(BaseModel):
    payment_id: UUID
    amount: Optional[float] = Field(default=None, gt=0)


class RefundOut(BaseModel):
    success: bool
    payment_status: str
    refund_status: Optional[str] = None
    refund: dict
