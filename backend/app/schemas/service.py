from pydantic import BaseModel, Field

class ServiceCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(default="", max_length=120)
    duration_min: int = Field(ge=5, le=600)
    price: float = Field(ge=0)

class ServiceOut(BaseModel):
    id: str
    name: str
    category: str
    duration_min: int
    price: float
    is_active: bool
