from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, UUID4


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    company_id: UUID4 | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    company_id: UUID4 | None = None


class ResetPasswordRequest(BaseModel):
    reset_token: str
    password: str


class VerifyEmailRequest(BaseModel):
    verification_token: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


AuthResponse = LoginResponse


class CompanyCreateRequest(BaseModel):
    company_name: str
    trade_name: str | None = None
    company_type: str
    pan: str
    gstin: str | None = None
    tan: str | None = None
    udyam_no: str | None = None
    gst_type: str
    primary_state: str
    extra_states: list[str] | None = []


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    roles: list[str] = []


class SignUpRequest(BaseModel):
    company: CompanyCreateRequest
    user: UserCreateRequest


class UserResponse(BaseModel):
    user_id: UUID4
    company_id: UUID4
    email: EmailStr
    name: str
    roles: list[str]
    email_verified: bool
    is_active: bool


class DelegationCreateRequest(BaseModel):
    delegate_email: EmailStr
    role_name: str
    start_date: date
    end_date: date


class DelegationResponse(BaseModel):
    delegation_id: UUID
    delegate_user_id: UUID
    role_name: str
    start_date: date
    end_date: date
    is_active: bool

