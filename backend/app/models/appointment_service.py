import uuid
from sqlalchemy import Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AppointmentService(Base):
    __tablename__ = "appointment_services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    appointment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    price_snapshot: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duration_snapshot_min: Mapped[int] = mapped_column(Integer, nullable=False)
