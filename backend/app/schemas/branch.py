from pydantic import BaseModel, Field

class BranchCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    address: str = Field(default="", max_length=500)
