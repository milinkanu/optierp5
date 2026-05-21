from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeliveryChallanItemCreate(BaseModel):
    inventory_item_id: Optional[UUID] = None
    description: str
    hsn_sac: Optional[str] = None
    account_id: Optional[UUID] = None
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    gst_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]


class DeliveryChallanCreateRequest(BaseModel):
    challan_type: str = Field(..., pattern="^(supply_on_approval|job_work|transport|others)$")
    challan_date: date
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")
    transport_mode: Optional[str] = None
    vehicle_number: Optional[str] = None
    place_of_supply: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    items: List[DeliveryChallanItemCreate]


class DeliveryChallanItemResponse(BaseModel):
    challan_item_id: UUID
    delivery_challan_id: UUID
    company_id: UUID
    line_number: int
    description: str
    hsn_sac: Optional[str] = None
    inventory_item_id: Optional[UUID] = None
    account_id: Optional[UUID] = None
    quantity: float
    unit_price: float
    discount_amount: float
    taxable_amount: float
    gst_rate: float
    gst_amount: float
    total_amount: float


class DeliveryChallanResponse(BaseModel):
    delivery_challan_id: UUID
    company_id: UUID
    challan_number: str
    challan_type: str
    challan_date: date
    billing_party_id: UUID
    shipping_party_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    status: str
    currency: str
    exchange_rate: float
    subtotal: float
    total_gst: float
    grand_total: float
    transport_mode: Optional[str] = None
    vehicle_number: Optional[str] = None
    place_of_supply: Optional[str] = None
    customer_notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
    items: Optional[List[DeliveryChallanItemResponse]] = []
