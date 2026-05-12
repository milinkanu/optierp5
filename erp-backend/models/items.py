from __future__ import annotations

"""
Items module (Item Master)
--------------------------
This module defines the Pydantic schemas for the Item Master.

The Item Master is the single source of truth for:
- Sales Invoices
- Sales Orders (future)
- Delivery Challans (future)
- Credit Notes (future)

Backend persistence uses the existing `inventory_items` table, extended via
`database/dev_upgrades.sql` for SKU, prices, default accounts, etc.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ItemCreateRequest(BaseModel):
    item_name: str
    item_type: str  # goods|service
    unit: str

    sku: Optional[str] = None
    hsn_sac: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    is_active: bool = True
    is_track_inventory: bool = False
    opening_stock: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=4)]] = None
    opening_value: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=2)]] = None
    reorder_point: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=4)]] = None

    gst_rate: Optional[Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]] = None

    selling_price: Optional[Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]] = None
    purchase_price: Optional[Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]] = None
    sales_account_id: Optional[UUID] = None
    purchase_account_id: Optional[UUID] = None
    preferred_vendor_id: Optional[UUID] = None


class ItemUpdateRequest(BaseModel):
    item_name: Optional[str] = None
    item_type: Optional[str] = None
    unit: Optional[str] = None

    sku: Optional[str] = None
    hsn_sac: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    is_active: Optional[bool] = None
    is_track_inventory: Optional[bool] = None
    opening_stock: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=4)]] = None
    opening_value: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=2)]] = None
    reorder_point: Optional[Annotated[Decimal, Field(max_digits=18, decimal_places=4)]] = None

    gst_rate: Optional[Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]] = None

    selling_price: Optional[Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]] = None
    purchase_price: Optional[Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]] = None
    sales_account_id: Optional[UUID] = None
    purchase_account_id: Optional[UUID] = None
    preferred_vendor_id: Optional[UUID] = None


class ItemResponse(BaseModel):
    inventory_item_id: UUID
    item_name: str
    item_type: str
    unit: str

    sku: Optional[str] = None
    hsn_sac: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

    is_active: bool
    is_track_inventory: bool
    opening_stock: Optional[Decimal] = None
    opening_value: Optional[Decimal] = None
    reorder_point: Optional[Decimal] = None

    gst_rate: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    purchase_price: Optional[Decimal] = None
    sales_account_id: Optional[UUID] = None
    purchase_account_id: Optional[UUID] = None
    preferred_vendor_id: Optional[UUID] = None

    created_at: datetime
    updated_at: datetime

