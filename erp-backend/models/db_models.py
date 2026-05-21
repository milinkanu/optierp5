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


import enum
from sqlalchemy import Enum as SQLEnum

class QuoteStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    converted = "converted"

class SalesOrderStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    partially_invoiced = "partially_invoiced"
    invoiced = "invoiced"
    cancelled = "cancelled"


class Quote(Base):
    __tablename__ = "quotes"

    quote_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    quote_number = Column(String, nullable=False)
    quote_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    billing_party_id = Column(UUID(as_uuid=True), ForeignKey("parties.party_id"), nullable=False)
    shipping_party_id = Column(UUID(as_uuid=True), ForeignKey("parties.party_id"))
    reference_number = Column(String)
    salesperson_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    project_name = Column(String)
    subject = Column(String)
    customer_notes = Column(Text)
    terms_and_conditions = Column(Text)
    status = Column(SQLEnum(QuoteStatus, name="quote_status_enum", create_type=False), nullable=False, default=QuoteStatus.draft)
    currency = Column(String, nullable=False, default="INR")
    exchange_rate = Column(Numeric(18, 8), nullable=False, default=1.0)
    is_deleted = Column(Boolean, nullable=False, default=False)
    subtotal = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_gst = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_tds = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_tcs = Column(Numeric(18, 2), nullable=False, default=0.0)
    adjustment = Column(Numeric(18, 2), nullable=False, default=0.0)
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=0.0)
    discount_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    grand_total = Column(Numeric(18, 2), nullable=False, default=0.0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company")
    billing_party = relationship("Party", foreign_keys=[billing_party_id])
    shipping_party = relationship("Party", foreign_keys=[shipping_party_id])
    salesperson = relationship("User", foreign_keys=[salesperson_id])
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")


class QuoteItem(Base):
    __tablename__ = "quote_items"

    quote_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.quote_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.inventory_item_id"))
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=False)
    discount_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    taxable_amount = Column(Numeric(18, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False)
    gst_amount = Column(Numeric(18, 2), nullable=False)
    tds_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    tds_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    tcs_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    tcs_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(18, 2), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    quote = relationship("Quote", back_populates="items")
    inventory_item = relationship("InventoryItem")


class QuoteActivityLog(Base):
    __tablename__ = "quote_activity_logs"

    activity_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.quote_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    action = Column(String, nullable=False)
    previous_value = Column(JSON)
    new_value = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("User")


class QuoteAttachment(Base):
    __tablename__ = "quote_attachments"

    attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.quote_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    sales_order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    sales_order_number = Column(String, nullable=False)
    sales_order_date = Column(Date, nullable=False)
    expected_shipment_date = Column(Date)
    billing_party_id = Column(UUID(as_uuid=True), ForeignKey("parties.party_id"), nullable=False)
    shipping_party_id = Column(UUID(as_uuid=True), ForeignKey("parties.party_id"))
    reference_number = Column(String)
    payment_terms = Column(String)
    salesperson_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    subject = Column(String)
    customer_notes = Column(Text)
    terms_and_conditions = Column(Text)
    status = Column(SQLEnum(SalesOrderStatus, name="sales_order_status_enum", create_type=False), nullable=False, default=SalesOrderStatus.draft)
    currency = Column(String, nullable=False, default="INR")
    exchange_rate = Column(Numeric(18, 8), nullable=False, default=1.0)
    is_deleted = Column(Boolean, nullable=False, default=False)
    subtotal = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_gst = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_tds = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_tcs = Column(Numeric(18, 2), nullable=False, default=0.0)
    adjustment = Column(Numeric(18, 2), nullable=False, default=0.0)
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=0.0)
    discount_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    grand_total = Column(Numeric(18, 2), nullable=False, default=0.0)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.quote_id"))

    # Relationships
    company = relationship("Company")
    billing_party = relationship("Party", foreign_keys=[billing_party_id])
    shipping_party = relationship("Party", foreign_keys=[shipping_party_id])
    salesperson = relationship("User", foreign_keys=[salesperson_id])
    quote = relationship("Quote")
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    sales_order_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.sales_order_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    inventory_item_id = Column(UUID(as_uuid=True), ForeignKey("inventory_items.inventory_item_id"))
    quantity = Column(Numeric(18, 4), nullable=False)
    unit_price = Column(Numeric(18, 4), nullable=False)
    discount_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    taxable_amount = Column(Numeric(18, 2), nullable=False)
    gst_rate = Column(Numeric(5, 2), nullable=False)
    gst_amount = Column(Numeric(18, 2), nullable=False)
    tds_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    tds_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    tcs_rate = Column(Numeric(5, 2), nullable=False, default=0.0)
    tcs_amount = Column(Numeric(18, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(18, 2), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sales_order = relationship("SalesOrder", back_populates="items")
    inventory_item = relationship("InventoryItem")


class SalesOrderActivityLog(Base):
    __tablename__ = "sales_order_activity_logs"

    activity_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.sales_order_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    action = Column(String, nullable=False)
    previous_value = Column(JSON)
    new_value = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("User")


class SalesOrderAttachment(Base):
    __tablename__ = "sales_order_attachments"

    attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    sales_order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.sales_order_id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.company_id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

