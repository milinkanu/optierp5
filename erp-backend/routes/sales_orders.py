from __future__ import annotations

import os
from uuid import UUID, uuid4
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from models.sales_orders import (
    SalesOrderCreateRequest,
    SalesOrderResponse,
    SalesOrderUpdateRequest,
    SalesOrderItemResponse,
)
from services import sales_order_service
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session

router = APIRouter(prefix="/sales-orders", tags=["sales-orders"])


def build_sales_order_response(payload: SalesOrderCreateRequest, sales_order_id: UUID | None = None, status: str = "draft") -> SalesOrderResponse:
    so_id = sales_order_id or uuid4()
    subtotal = Decimal('0')
    total_gst = Decimal('0')
    total_tds = Decimal('0')
    total_tcs = Decimal('0')
    grand_total = Decimal('0')
    items = []

    for idx, item in enumerate(payload.items):
        taxable_amount = item.quantity * item.unit_price - item.discount_amount
        gst_amount = taxable_amount * item.gst_rate / Decimal('100')
        tds_amount = taxable_amount * item.tds_rate / Decimal('100')
        tcs_amount = taxable_amount * item.tcs_rate / Decimal('100')
        total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount
        
        subtotal += taxable_amount
        total_gst += gst_amount
        total_tds += tds_amount
        total_tcs += tcs_amount
        grand_total += total_amount

        items.append(SalesOrderItemResponse(
            sales_order_item_id=uuid4(),
            line_number=idx + 1,
            description=item.description,
            inventory_item_id=item.inventory_item_id,
            quantity=float(item.quantity),
            unit_price=float(item.unit_price),
            discount_amount=float(item.discount_amount),
            taxable_amount=float(taxable_amount),
            gst_rate=float(item.gst_rate),
            gst_amount=float(gst_amount),
            tds_rate=float(item.tds_rate),
            tds_amount=float(tds_amount),
            tcs_rate=float(item.tcs_rate),
            tcs_amount=float(tcs_amount),
            total_amount=float(total_amount),
        ))

    return SalesOrderResponse(
        sales_order_id=so_id,
        sales_order_number=payload.sales_order_number,
        sales_order_date=payload.sales_order_date,
        expected_shipment_date=payload.expected_shipment_date,
        billing_party_id=payload.billing_party_id,
        shipping_party_id=payload.shipping_party_id,
        reference_number=payload.reference_number,
        payment_terms=payload.payment_terms,
        salesperson_id=payload.salesperson_id,
        subject=payload.subject,
        customer_notes=payload.customer_notes,
        terms_and_conditions=payload.terms_and_conditions,
        status=status,
        subtotal=float(subtotal),
        total_gst=float(total_gst),
        total_tds=float(total_tds),
        total_tcs=float(total_tcs),
        adjustment=float(payload.adjustment),
        discount_percentage=float(payload.discount_percentage),
        discount_amount=float(payload.discount_amount),
        grand_total=float(grand_total + payload.adjustment),
        currency=payload.currency,
        exchange_rate=float(payload.exchange_rate),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        quote_id=payload.quote_id,
        items=items,
    )


@router.post("", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
def create_sales_order(
    payload: SalesOrderCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return build_sales_order_response(payload)
    return sales_order_service.create_sales_order(db, current_context.company_id, current_context.user_id, payload)


@router.get("", response_model=list[SalesOrderResponse])
def list_sales_orders(
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    q: str | None = Query(None),
    status: str | None = Query(None),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from models.sales_orders import SalesOrderItemCreate
        payload = SalesOrderCreateRequest(
            sales_order_number="SO-2026-00001",
            sales_order_date=date.today(),
            billing_party_id=uuid4(),
            items=[SalesOrderItemCreate(description="Mock SO Item", quantity=1.0, unit_price=100.0, gst_rate=18.0)]
        )
        return [build_sales_order_response(payload)]
    sales_orders = sales_order_service.list_sales_orders(db, current_context.company_id, page, limit, q, status)
    return sales_orders


@router.get("/{sales_order_id}", response_model=SalesOrderResponse)
def get_sales_order(
    sales_order_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from models.sales_orders import SalesOrderItemCreate
        payload = SalesOrderCreateRequest(
            sales_order_number="SO-2026-00001",
            sales_order_date=date.today(),
            billing_party_id=sales_order_id,
            items=[SalesOrderItemCreate(description="Mock SO Item", quantity=1.0, unit_price=100.0, gst_rate=18.0)]
        )
        return build_sales_order_response(payload, sales_order_id=sales_order_id)
    return sales_order_service.get_sales_order(db, current_context.company_id, sales_order_id)


@router.patch("/{sales_order_id}", response_model=SalesOrderResponse)
def update_sales_order(
    sales_order_id: UUID,
    payload: SalesOrderUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from models.sales_orders import SalesOrderItemCreate
        req_payload = SalesOrderCreateRequest(
            sales_order_number=payload.sales_order_number or "SO-2026-00001",
            sales_order_date=payload.sales_order_date or date.today(),
            billing_party_id=payload.billing_party_id or uuid4(),
            items=[SalesOrderItemCreate(description="Mock SO Item", quantity=1.0, unit_price=100.0, gst_rate=18.0)]
        )
        return build_sales_order_response(req_payload, sales_order_id=sales_order_id, status=payload.status or "draft")
    return sales_order_service.update_sales_order(db, current_context.company_id, current_context.user_id, sales_order_id, payload)


@router.delete("/{sales_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sales_order(
    sales_order_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return
    sales_order_service.delete_sales_order(db, current_context.company_id, sales_order_id)
    return


@router.post("/{sales_order_id}/convert-invoice", status_code=status.HTTP_201_CREATED)
def convert_to_invoice(
    sales_order_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from routes.invoices import MOCK_INVOICES
        from models.invoices import InvoiceResponse, InvoiceItemResponse
        
        so = get_sales_order(sales_order_id, current_context, db)
        invoice_id = uuid4()
        invoice_number = f"INV-2026-{str(uuid4())[:8].upper()}"
        
        invoice_items = []
        for it in so.items:
            invoice_items.append(InvoiceItemResponse(
                invoice_item_id=uuid4(),
                invoice_id=invoice_id,
                company_id=UUID("00000000-0000-0000-0000-000000000000"),
                line_number=it.line_number,
                description=it.description,
                hsn_sac="0000",
                account_id=uuid4(),
                quantity=float(it.quantity),
                unit_price=float(it.unit_price),
                discount_amount=float(it.discount_amount),
                taxable_amount=float(it.taxable_amount),
                gst_rate=float(it.gst_rate),
                gst_amount=float(it.gst_amount),
                tds_rate=float(it.tds_rate),
                tds_amount=float(it.tds_amount),
                tcs_rate=float(it.tcs_rate),
                tcs_amount=float(it.tcs_amount),
                total_amount=float(it.total_amount)
            ))
            
        inv = InvoiceResponse(
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            invoice_type="sales_invoice",
            invoice_date=datetime.utcnow().date(),
            due_date=datetime.utcnow().date(),
            billing_party_id=so.billing_party_id,
            shipping_party_id=so.shipping_party_id,
            order_number=so.sales_order_number,
            salesperson_id=so.salesperson_id,
            subject=so.subject,
            customer_notes=so.customer_notes,
            terms_and_conditions=so.terms_and_conditions,
            status="draft",
            invoice_subtotal=so.subtotal,
            invoice_total_gst=so.total_gst,
            invoice_total_tds=so.total_tds,
            invoice_total_tcs=so.total_tcs,
            invoice_grand_total=so.grand_total,
            paid_amount=0.0,
            balance_due=so.grand_total,
            currency=so.currency,
            created_at=datetime.utcnow(),
            items=invoice_items
        )
        MOCK_INVOICES[invoice_id] = inv
        return {"invoice_id": invoice_id}
        
    invoice_id = sales_order_service.convert_to_invoice(db, current_context.company_id, current_context.user_id, sales_order_id)
    return {"invoice_id": invoice_id}


