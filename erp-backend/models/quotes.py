from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class QuoteItemCreate(BaseModel):
    inventory_item_id: Optional[UUID] = None
    description: str
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    gst_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]
    tds_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    tcs_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")


class QuoteCreateRequest(BaseModel):
    quote_number: str
    quote_date: date
    expiry_date: Optional[date] = None
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    project_name: Optional[str] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")
    discount_percentage: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    adjustment: Annotated[Decimal, Field(max_digits=18, decimal_places=2)] = Decimal("0")
    items: List[QuoteItemCreate]


class QuoteUpdateRequest(BaseModel):
    quote_number: Optional[str] = None
    quote_date: Optional[date] = None
    expiry_date: Optional[date] = None
    billing_party_id: Optional[UUID] = None
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    project_name: Optional[str] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    currency: Optional[str] = None
    exchange_rate: Optional[Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)]] = None
    status: Optional[str] = None
    discount_percentage: Optional[Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]] = None
    discount_amount: Optional[Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]] = None
    adjustment: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=2)]] = None
    items: Optional[List[QuoteItemCreate]] = None


class QuoteItemResponse(BaseModel):
    quote_item_id: UUID
    line_number: int
    description: str
    inventory_item_id: Optional[UUID] = None
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

    class Config:
        from_attributes = True


class QuoteResponse(BaseModel):
    quote_id: UUID
    quote_number: str
    quote_date: date
    expiry_date: Optional[date] = None
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    project_name: Optional[str] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    status: str
    subtotal: float
    total_gst: float
    total_tds: float
    total_tcs: float
    adjustment: float
    discount_percentage: float
    discount_amount: float
    grand_total: float
    currency: str
    exchange_rate: float
    created_at: datetime
    updated_at: datetime
    items: List[QuoteItemResponse]

    class Config:
        from_attributes = True
