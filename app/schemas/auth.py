from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class APIKeyCreate(BaseModel):
    name: str
    permissions: Optional[list] = []
    expires_days: Optional[int] = 365

class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key: str  # Only returned on creation
    permissions: list
    created_at: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ValidationRequest(BaseModel):
    token: str

class ValidationResponse(BaseModel):
    is_valid: bool
    user_id: Optional[uuid.UUID] = None
    expires_at: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str = None 