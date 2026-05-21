from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceItemCreate(BaseModel):
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


class InvoiceCreateRequest(BaseModel):
    invoice_type: str
    invoice_date: date
    due_date: Optional[date] = None
    billing_party_id: Optional[UUID] = None
    shipping_party_id: Optional[UUID] = None
    order_number: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")
    items: List[InvoiceItemCreate]
    meta: Optional[dict] = None


class InvoiceItemResponse(BaseModel):
    invoice_item_id: UUID
    invoice_id: UUID
    company_id: UUID
    line_number: int
    description: str
    hsn_sac: Optional[str] = None
    account_id: Optional[UUID] = None
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


class InvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_number: str
    invoice_type: str
    invoice_date: date
    due_date: Optional[date] = None
    billing_party_id: Optional[UUID] = None
    shipping_party_id: Optional[UUID] = None
    order_number: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    status: str
    invoice_subtotal: float = 0
    invoice_total_gst: float = 0
    invoice_total_tds: float = 0
    invoice_total_tcs: float = 0
    invoice_grand_total: float
    paid_amount: float
    balance_due: float
    currency: str = "INR"
    created_at: datetime
    items: Optional[List[InvoiceItemResponse]] = []


class PaymentAllocationRequest(BaseModel):
    payment_transaction_id: UUID
    allocated_amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")

