from __future__ import annotations

"""
Items API
---------
CRUD endpoints for the Item Master (`inventory_items` table).

Design notes:
- Tenant isolation is enforced by scoping every query with `company_id` from JWT (`TenantContext`).
- We keep this module intentionally simple now; future modules (Sales Orders, DC, Credit Notes)
  will reference `inventory_item_id` to pull default prices/accounts/tax.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.db_models import InventoryItem
from models.items import ItemCreateRequest, ItemResponse, ItemUpdateRequest
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session

router = APIRouter(prefix="/items", tags=["items"])

ALLOWED_ITEM_TYPES = {"goods", "service"}


def _to_response(row: InventoryItem) -> ItemResponse:
    return ItemResponse(**row.__dict__)


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if payload.item_type not in ALLOWED_ITEM_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item_type (goods|service)")

    now = datetime.utcnow()
    row = InventoryItem(
        company_id=current_context.company_id,
        item_name=payload.item_name,
        item_type=payload.item_type,
        unit=payload.unit,
        sku=payload.sku,
        hsn_sac=payload.hsn_sac,
        description=payload.description,
        image_url=payload.image_url,
        is_active=payload.is_active,
        is_track_inventory=payload.is_track_inventory,
        opening_stock=payload.opening_stock,
        opening_value=payload.opening_value,
        reorder_point=payload.reorder_point,
        gst_rate=payload.gst_rate,
        selling_price=payload.selling_price,
        purchase_price=payload.purchase_price,
        sales_account_id=payload.sales_account_id,
        purchase_account_id=payload.purchase_account_id,
        preferred_vendor_id=payload.preferred_vendor_id,
        created_at=now,
        updated_at=now,
        valuation_method="fifo",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.get("", response_model=list[ItemResponse])
def list_items(
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    q: str | None = Query(None),
    is_active: bool | None = Query(None),
    item_type: str | None = Query(None),
):
    stmt = select(InventoryItem).where(InventoryItem.company_id == current_context.company_id)
    if q:
        stmt = stmt.where(InventoryItem.item_name.ilike(f"%{q}%") | InventoryItem.sku.ilike(f"%{q}%"))
    if is_active is not None:
        stmt = stmt.where(InventoryItem.is_active == is_active)
    if item_type:
        stmt = stmt.where(InventoryItem.item_type == item_type)
    stmt = stmt.order_by(InventoryItem.item_name).offset((page - 1) * limit).limit(limit)
    rows = db.scalars(stmt).all()
    return [_to_response(r) for r in rows]


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    row = db.scalar(
        select(InventoryItem)
        .where(InventoryItem.company_id == current_context.company_id)
        .where(InventoryItem.inventory_item_id == item_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return _to_response(row)


@router.patch("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: UUID,
    payload: ItemUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    values = payload.model_dump(exclude_unset=True)
    if "item_type" in values and values["item_type"] not in ALLOWED_ITEM_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid item_type (goods|service)")
    if not values:
        return get_item(item_id, current_context, db)

    values["updated_at"] = datetime.utcnow()
    row = db.execute(
        update(InventoryItem)
        .where(InventoryItem.company_id == current_context.company_id)
        .where(InventoryItem.inventory_item_id == item_id)
        .values(**values)
        .returning(InventoryItem)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.commit()
    return _to_response(row[0])


@router.delete("/{item_id}")
def deactivate_item(
    item_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    row = db.scalar(
        select(InventoryItem)
        .where(InventoryItem.company_id == current_context.company_id)
        .where(InventoryItem.inventory_item_id == item_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    row.is_active = False
    row.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}

