"""
Import all models so that Base.metadata is fully populated before
create_all() or Alembic autogenerate runs.
"""

from app.db.base_class import Base  # noqa: F401 – re-export

# Register every model with the shared Base.metadata
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.branch import Branch  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.staff import Staff  # noqa: F401
from app.models.appointment import Appointment  # noqa: F401
from app.models.appointment_service import AppointmentService  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.payment_event import PaymentEvent  # noqa: F401
