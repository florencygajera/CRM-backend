import uuid
from sqlalchemy import String, DateTime, func, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class PaymentStatus:
    CREATED = "CREATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class PaymentProvider:
    RAZORPAY = "RAZORPAY"
    STRIPE = "STRIPE"

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    appointment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # RAZORPAY/STRIPE
    status: Mapped[str] = mapped_column(String(20), default=PaymentStatus.CREATED, nullable=False)

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    provider_order_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    provider_payment_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
