from pydantic import BaseModel, EmailStr, Field

class RegisterTenantIn(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=200)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=72)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
