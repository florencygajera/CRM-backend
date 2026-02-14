from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional

class AppointmentCreateIn(BaseModel):
    customer_id: str
    staff_user_id: str
    service_ids: List[str]
    start_at: datetime
    notes: str = Field(default="", max_length=500)

class AppointmentPatchIn(BaseModel):
    status: Optional[str] = None  # CANCELLED/CONFIRMED
    start_at: Optional[datetime] = None  # reschedule
    notes: Optional[str] = Field(default=None, max_length=500)

class AvailabilityQuery(BaseModel):
    branch_id: str | None = None
    staff_user_id: str
    service_ids: List[str]
    day: date
    slot_step_min: int = 15
