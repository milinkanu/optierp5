from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr, field_validator
from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from utils.db import Base

# ====================================================
# SQLALCHEMY DATABASE MODELS
# ====================================================

class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("parties.party_id", ondelete="CASCADE"), primary_key=True)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    customer_code = Column(Text, nullable=False)
    customer_name = Column(Text, nullable=False)
    customer_type = Column(Text, nullable=False)
    display_name = Column(Text, nullable=False)
    currency = Column(Text, nullable=False, default="INR")
    email = Column(Text)
    mobile = Column(Text)
    phone = Column(Text)
    gst_registration_type = Column(Text, nullable=False, default="unregistered")
    gstin = Column(Text)
    pan = Column(Text)  # Fernet encrypted PAN string
    payment_terms = Column(Text)
    credit_limit = Column(Numeric(18, 2), nullable=False, default=0.0)
    opening_balance = Column(Numeric(18, 2), nullable=False, default=0.0)
    opening_balance_type = Column(Text, nullable=False, default="debit")
    msme_status = Column(Boolean, nullable=False, default=False)
    msme_registration_no = Column(Text)
    cin = Column(Text)
    invoice_delivery_preference = Column(Text, nullable=False, default="email")
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    updated_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    contacts = relationship("CustomerContact", back_populates="customer", cascade="all, delete-orphan")
    custom_fields = relationship("CustomerCustomField", back_populates="customer", cascade="all, delete-orphan")
    documents = relationship("CustomerDocument", back_populates="customer", cascade="all, delete-orphan")
    tags = relationship("CustomerTag", back_populates="customer", cascade="all, delete-orphan")


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    address_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    address_type = Column(Text, nullable=False)  # billing | shipping
    attention = Column(Text)
    address_line1 = Column(Text, nullable=False)
    address_line2 = Column(Text)
    city = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    zip_code = Column(Text, nullable=False)
    country = Column(Text, nullable=False, default="India")
    phone = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="addresses")


class CustomerContact(Base):
    __tablename__ = "customer_contacts"

    contact_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    first_name = Column(Text, nullable=False)
    last_name = Column(Text)
    email = Column(Text, nullable=False)
    phone = Column(Text)
    mobile = Column(Text)
    designation = Column(Text)
    is_primary = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="contacts")


class CustomerCustomField(Base):
    __tablename__ = "customer_custom_fields"

    field_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    field_key = Column(Text, nullable=False)
    field_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="custom_fields")


class CustomerDocument(Base):
    __tablename__ = "customer_documents"

    document_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    file_name = Column(Text, nullable=False)
    file_url = Column(Text, nullable=False)
    file_size = Column(Integer)
    mime_type = Column(Text)
    notes = Column(Text)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="documents")


class CustomerTag(Base):
    __tablename__ = "customer_tags"

    tag_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(PG_UUID(as_uuid=True), ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    tag_name = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="tags")


# ====================================================
# PYDANTIC SCHEMAS
# ====================================================

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


class CustomerCreateRequest(BaseModel):
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


class CustomerUpdateRequest(BaseModel):
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


class CustomerResponse(BaseModel):
    customer_id: UUID
    company_id: UUID
    customer_code: str
    customer_name: str
    customer_type: str
    display_name: str
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
