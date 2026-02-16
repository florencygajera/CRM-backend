from pydantic import BaseModel, Field

class CreateRazorpayOrderIn(BaseModel):
    appointment_id: str
    amount: float = Field(ge=1)
    currency: str = "INR"

class CreateOrderOut(BaseModel):
    payment_id: str
    provider: str
    provider_order_id: str
    amount: float
    currency: str
