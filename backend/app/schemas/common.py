from pydantic import BaseModel

class APIResponse(BaseModel):
    success: bool = True
    message: str | None = None
    data: dict | None = None
