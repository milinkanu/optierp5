from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SalesOrderItemCreate(BaseModel):
    inventory_item_id: Optional[UUID] = None
    description: str
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    gst_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]
    tds_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    tcs_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")


class SalesOrderCreateRequest(BaseModel):
    sales_order_number: str
    sales_order_date: date
    expected_shipment_date: Optional[date] = None
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    payment_terms: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")
    discount_percentage: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    adjustment: Annotated[Decimal, Field(max_digits=18, decimal_places=2)] = Decimal("0")
    quote_id: Optional[UUID] = None
    items: List[SalesOrderItemCreate]


class SalesOrderUpdateRequest(BaseModel):
    sales_order_number: Optional[str] = None
    sales_order_date: Optional[date] = None
    expected_shipment_date: Optional[date] = None
    billing_party_id: Optional[UUID] = None
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    payment_terms: Optional[str] = None
    salesperson_id: Optional[UUID] = None
    subject: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    currency: Optional[str] = None
    exchange_rate: Optional[Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)]] = None
    status: Optional[str] = None
    discount_percentage: Optional[Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]] = None
    discount_amount: Optional[Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]] = None
    adjustment: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=2)]] = None
    quote_id: Optional[UUID] = None
    items: Optional[List[SalesOrderItemCreate]] = None


class SalesOrderItemResponse(BaseModel):
    sales_order_item_id: UUID
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


class SalesOrderResponse(BaseModel):
    sales_order_id: UUID
    sales_order_number: str
    sales_order_date: date
    expected_shipment_date: Optional[date] = None
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    payment_terms: Optional[str] = None
    salesperson_id: Optional[UUID] = None
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
    quote_id: Optional[UUID] = None
    items: List[SalesOrderItemResponse]

    class Config:
        from_attributes = True
