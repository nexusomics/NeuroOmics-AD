"""Authentication & user schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    organization: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)
