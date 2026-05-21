from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RecurringInvoiceItemCreate(BaseModel):
    inventory_item_id: Optional[UUID] = None
    description: str
    hsn_sac: Optional[str] = None
    account_id: Optional[UUID] = None
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    gst_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]
    tds_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    tcs_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")


class RecurringInvoiceProfileCreateRequest(BaseModel):
    profile_name: str
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    frequency: str = Field(..., pattern="^(daily|weekly|monthly|quarterly|yearly)$")
    start_date: date
    end_date: Optional[date] = None
    auto_email: bool = False
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")
    order_number: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    items: List[RecurringInvoiceItemCreate]


class RecurringInvoiceItemResponse(BaseModel):
    profile_item_id: UUID
    profile_id: UUID
    company_id: UUID
    line_number: int
    description: str
    hsn_sac: Optional[str] = None
    inventory_item_id: Optional[UUID] = None
    account_id: UUID
    quantity: float
    unit_price: float
    discount_amount: float
    taxable_amount: float
    gst_rate: float
    gst_amount: float
    tds_rate: float
    tds_amount: float
    tcs_rate: float
    tcs_amount: float
    total_amount: float


class RecurringInvoiceProfileResponse(BaseModel):
    profile_id: UUID
    company_id: UUID
    profile_name: str
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    frequency: str
    status: str
    start_date: date
    end_date: Optional[date] = None
    next_run_date: date
    last_run_date: Optional[date] = None
    auto_email: bool
    currency: str
    exchange_rate: float
    order_number: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
    items: Optional[List[RecurringInvoiceItemResponse]] = []


class RecurringInvoiceLogResponse(BaseModel):
    log_id: UUID
    profile_id: UUID
    company_id: UUID
    run_date: datetime
    status: str
    generated_invoice_id: Optional[UUID] = None
    error_message: Optional[str] = None
    created_at: datetime
