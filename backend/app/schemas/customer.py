from pydantic import BaseModel, Field

class CustomerCreateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=7, max_length=30)
    email: str = Field(default="", max_length=255)
