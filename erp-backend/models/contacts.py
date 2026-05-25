from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, field_validator


class CustomerAddressSchema(BaseModel):
    address_type: str = Field(..., pattern="^(billing|shipping)$")
    attention: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str = "India"
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerContactSchema(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    mobile: Optional[str] = None
    designation: Optional[str] = None
    is_primary: bool = False

    class Config:
        from_attributes = True


class CustomerCustomFieldSchema(BaseModel):
    field_key: str
    field_value: str

    class Config:
        from_attributes = True


class ContactCreateRequest(BaseModel):
    contact_type: str = Field("customer", pattern="^(customer)$")  # Force to customer only
    customer_code: Optional[str] = None
    customer_name: str
    customer_type: str = Field(..., pattern="^(individual|business)$")
    display_name: str
    currency: str = "INR"
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    gst_registration_type: str = Field("unregistered", pattern="^(regular|composition|unregistered|sez|consumer)$")
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: Decimal = Decimal("0")
    opening_balance: Decimal = Decimal("0")
    opening_balance_type: str = Field("debit", pattern="^(debit|credit)$")
    msme_status: bool = False
    msme_registration_no: Optional[str] = None
    cin: Optional[str] = None
    invoice_delivery_preference: str = Field("email", pattern="^(email|portal|both)$")
    addresses: List[CustomerAddressSchema] = []
    contacts: List[CustomerContactSchema] = []
    custom_fields: List[CustomerCustomFieldSchema] = []
    tags: List[str] = []


class ContactUpdateRequest(BaseModel):
    contact_type: Optional[str] = Field(None, pattern="^(customer)$")
    customer_name: Optional[str] = None
    customer_type: Optional[str] = None
    display_name: Optional[str] = None
    currency: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    gst_registration_type: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    opening_balance: Optional[Decimal] = None
    opening_balance_type: Optional[str] = None
    msme_status: Optional[bool] = None
    msme_registration_no: Optional[str] = None
    cin: Optional[str] = None
    invoice_delivery_preference: Optional[str] = None
    is_active: Optional[bool] = None
    addresses: Optional[List[CustomerAddressSchema]] = None
    contacts: Optional[List[CustomerContactSchema]] = None
    custom_fields: Optional[List[CustomerCustomFieldSchema]] = None
    tags: Optional[List[str]] = None


class CustomerAddressResponse(BaseModel):
    address_id: UUID
    address_type: str
    attention: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerContactResponse(BaseModel):
    contact_id: UUID
    first_name: str
    last_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    mobile: Optional[str] = None
    designation: Optional[str] = None
    is_primary: bool

    class Config:
        from_attributes = True


class CustomerCustomFieldResponse(BaseModel):
    field_id: UUID
    field_key: str
    field_value: str

    class Config:
        from_attributes = True


class ContactResponse(BaseModel):
    contact_id: UUID
    contact_type: str = "customer"
    company_id: UUID
    customer_code: str
    customer_name: str
    customer_type: str
    display_name: str
    name: str
    currency: str
    email: Optional[str] = None
    mobile: Optional[str] = None
    phone: Optional[str] = None
    gst_registration_type: str
    gstin: Optional[str] = None
    pan: Optional[str] = None  # Decrypted in service layer
    payment_terms: Optional[str] = None
    credit_limit: float
    opening_balance: float
    opening_balance_type: str
    msme_status: bool
    msme_registration_no: Optional[str] = None
    cin: Optional[str] = None
    invoice_delivery_preference: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    addresses: List[CustomerAddressResponse] = []
    contacts: List[CustomerContactResponse] = []
    custom_fields: List[CustomerCustomFieldResponse] = []
    tags: List[str] = []

    @field_validator("tags", mode="before")
    @classmethod
    def convert_tags(cls, v):
        if isinstance(v, list):
            return [t.tag_name if hasattr(t, "tag_name") else str(t) for t in v]
        return v

    class Config:
        from_attributes = True
