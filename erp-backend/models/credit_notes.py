from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreditNoteItemCreate(BaseModel):
    inventory_item_id: Optional[UUID] = None
    account_id: UUID
    description: str
    hsn_sac: Optional[str] = None
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
    unit: Optional[str] = None
    rate: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    tax_id: Optional[UUID] = None
    tax_percentage: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    tds_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    tcs_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")


class CreditNoteCreateRequest(BaseModel):
    credit_note_number: Optional[str] = None
    reference_number: Optional[str] = None
    credit_note_date: date
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")
    salesperson_id: Optional[UUID] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    items: List[CreditNoteItemCreate]
    status: str = "draft"


class CreditNoteUpdateRequest(BaseModel):
    reference_number: Optional[str] = None
    credit_note_date: Optional[date] = None
    billing_party_id: Optional[UUID] = None
    shipping_party_id: Optional[UUID] = None
    currency: Optional[str] = None
    exchange_rate: Optional[Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)]] = None
    salesperson_id: Optional[UUID] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    items: Optional[List[CreditNoteItemCreate]] = None
    status: Optional[str] = None


class CreditNoteItemResponse(BaseModel):
    credit_note_item_id: UUID
    credit_note_id: UUID
    company_id: UUID
    line_number: int
    description: str
    hsn_sac: Optional[str] = None
    inventory_item_id: Optional[UUID] = None
    account_id: UUID
    quantity: float
    unit: Optional[str] = None
    rate: float
    discount_amount: float
    taxable_amount: float
    tax_id: Optional[UUID] = None
    tax_percentage: float
    tax_amount: float
    tds_rate: float
    tds_amount: float
    tcs_rate: float
    tcs_amount: float
    line_total: float
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class CreditNoteResponse(BaseModel):
    credit_note_id: UUID
    transaction_id: UUID
    credit_note_number: str
    reference_number: Optional[str] = None
    credit_note_date: date
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    status: str
    currency: str
    exchange_rate: float
    accounts_receivable_id: Optional[UUID] = None
    salesperson_id: Optional[UUID] = None
    subtotal: float
    total_gst: float
    total_tds: float
    total_tcs: float
    grand_total: float
    remaining_balance: float
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
    items: List[CreditNoteItemResponse] = []


class CreditNoteApplyRequest(BaseModel):
    invoice_id: UUID
    applied_amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


class CreditNoteInvoiceMappingResponse(BaseModel):
    mapping_id: UUID
    company_id: UUID
    credit_note_id: UUID
    invoice_id: UUID
    applied_amount: float
    applied_at: datetime
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    invoice_grand_total: Optional[float] = None
    invoice_balance_due: Optional[float] = None


class CreditNoteActivityLogResponse(BaseModel):
    log_id: UUID
    credit_note_id: UUID
    company_id: UUID
    activity_type: str
    description: str
    metadata: Optional[dict] = None
    created_by: UUID
    created_at: datetime
