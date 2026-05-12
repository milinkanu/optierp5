from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from utils.db import Base


class Company(Base):
    __tablename__ = "companies"

    company_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_name = Column(String, nullable=False)
    trade_name = Column(String)
    company_type = Column(String, nullable=False)
    pan = Column(String, nullable=False)
    gstin = Column(String)
    tan = Column(String)
    udyam_no = Column(String)
    gst_type = Column(String, nullable=False)
    primary_state = Column(String, nullable=False)
    address = Column(JSON)
    logo_url = Column(Text)
    fiscal_year_start = Column(Date)
    currency = Column(String, nullable=False, default="INR")
    timezone = Column(String, nullable=False, default="Asia/Kolkata")
    extra_states = Column(ARRAY(String))
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="company")
    roles = relationship("Role", back_populates="company")


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    email = Column(String, nullable=False)
    password_hash = Column(Text, nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    user_version = Column(Integer, default=1, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token_hash = Column(Text)
    verification_token_expires_at = Column(DateTime)
    reset_token_hash = Column(Text)
    reset_token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="users")
    roles = relationship("UserRole", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="roles")
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.role_id", ondelete="CASCADE"), primary_key=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="user_roles")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    token_hash = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime)

    user = relationship("User", back_populates="refresh_tokens")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    entity_name = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    operation = Column(String, nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    before_state = Column(JSON)
    after_state = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    record_hash = Column(Text, nullable=False)
    previous_hash = Column(Text)


class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"

    account_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    account_code = Column(Text, nullable=False)
    account_name = Column(Text, nullable=False)
    account_type = Column(String, nullable=False)
    description = Column(Text)
    parent_account_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.account_id"))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Party(Base):
    __tablename__ = "parties"

    party_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    party_name = Column(Text, nullable=False)
    party_type = Column(String, nullable=False)
    gstin = Column(Text)
    pan = Column(Text)
    email = Column(Text)
    phone = Column(Text)
    payment_terms = Column(Text)
    currency = Column(String, nullable=False, default="INR")
    billing_address = Column(JSON)
    shipping_address = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class InventoryItem(Base):
    """
    Item master used across sales invoices, sales orders, delivery challans, credit notes, etc.

    We reuse the existing `inventory_items` table (already present in `database/schema.sql`) and
    extend it via `database/dev_upgrades.sql` with pricing, SKU, default accounts, and inventory flags.
    """

    __tablename__ = "inventory_items"

    inventory_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)

    item_name = Column(Text, nullable=False)
    item_type = Column(Text, nullable=False)  # goods|service (string for compatibility with existing schema)
    sku = Column(Text)
    hsn_sac = Column(Text)
    unit = Column(Text, nullable=False)

    description = Column(Text)
    image_url = Column(Text)

    is_active = Column(Boolean, default=True, nullable=False)
    is_track_inventory = Column(Boolean, default=False, nullable=False)
    opening_stock = Column(Numeric(18, 4))
    opening_value = Column(Numeric(18, 2))
    reorder_point = Column(Numeric(18, 4))

    gst_rate = Column(Numeric(5, 2))

    selling_price = Column(Numeric(18, 2))
    purchase_price = Column(Numeric(18, 2))
    sales_account_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.account_id"))
    purchase_account_id = Column(UUID(as_uuid=True), ForeignKey("chart_of_accounts.account_id"))
    preferred_vendor_id = Column(UUID(as_uuid=True), ForeignKey("parties.party_id"))

    valuation_method = Column(Text, nullable=False, default="fifo")
    godown_id = Column(UUID(as_uuid=True))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
