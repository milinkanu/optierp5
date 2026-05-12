from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class ContactCreateRequest(BaseModel):
    contact_type: str  # customer|vendor|both
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: str = "INR"
    billing_address: Optional[dict[str, Any]] = None
    shipping_address: Optional[dict[str, Any]] = None


class ContactUpdateRequest(BaseModel):
    contact_type: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: Optional[str] = None
    billing_address: Optional[dict[str, Any]] = None
    shipping_address: Optional[dict[str, Any]] = None


class ContactResponse(BaseModel):
    contact_id: UUID
    contact_type: str
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: str
    billing_address: Optional[dict[str, Any]] = None
    shipping_address: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

