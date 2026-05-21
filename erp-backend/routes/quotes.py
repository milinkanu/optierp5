from __future__ import annotations

import os
from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from models.quotes import QuoteCreateRequest, QuoteResponse, QuoteUpdateRequest, QuoteItemResponse
from services import quote_service
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session

router = APIRouter(prefix="/quotes", tags=["quotes"])


def build_quote_response(payload: QuoteCreateRequest, quote_id: UUID | None = None, status: str = "draft") -> QuoteResponse:
    q_id = quote_id or uuid4()
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

        items.append(QuoteItemResponse(
            quote_item_id=uuid4(),
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

    return QuoteResponse(
        quote_id=q_id,
        quote_number=payload.quote_number,
        quote_date=payload.quote_date,
        expiry_date=payload.expiry_date,
        billing_party_id=payload.billing_party_id,
        shipping_party_id=payload.shipping_party_id,
        reference_number=payload.reference_number,
        salesperson_id=payload.salesperson_id,
        project_name=payload.project_name,
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
        items=items,
    )


@router.post("", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: QuoteCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return build_quote_response(payload)
    return quote_service.create_quote(db, current_context.company_id, current_context.user_id, payload)


@router.get("", response_model=list[QuoteResponse])
def list_quotes(
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    q: str | None = Query(None),
    status: str | None = Query(None),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from models.quotes import QuoteItemCreate
        payload = QuoteCreateRequest(
            quote_number="QT-2026-00001",
            quote_date=datetime.utcnow().date(),
            billing_party_id=uuid4(),
            items=[QuoteItemCreate(description="Mock Item", quantity=1.0, unit_price=100.0, gst_rate=18.0)]
        )
        return [build_quote_response(payload)]
    quotes = quote_service.list_quotes(db, current_context.company_id, page, limit, q, status)
    return quotes


@router.get("/{quote_id}", response_model=QuoteResponse)
def get_quote(
    quote_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from models.quotes import QuoteItemCreate
        payload = QuoteCreateRequest(
            quote_number="QT-2026-00001",
            quote_date=datetime.utcnow().date(),
            billing_party_id=quote_id,
            items=[QuoteItemCreate(description="Mock Item", quantity=1.0, unit_price=100.0, gst_rate=18.0)]
        )
        return build_quote_response(payload, quote_id=quote_id)
    return quote_service.get_quote(db, current_context.company_id, quote_id)


@router.patch("/{quote_id}", response_model=QuoteResponse)
def update_quote(
    quote_id: UUID,
    payload: QuoteUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from models.quotes import QuoteItemCreate
        req_payload = QuoteCreateRequest(
            quote_number=payload.quote_number or "QT-2026-00001",
            quote_date=payload.quote_date or datetime.utcnow().date(),
            billing_party_id=payload.billing_party_id or uuid4(),
            items=[QuoteItemCreate(description="Mock Item", quantity=1.0, unit_price=100.0, gst_rate=18.0)]
        )
        return build_quote_response(req_payload, quote_id=quote_id, status=payload.status or "draft")
    return quote_service.update_quote(db, current_context.company_id, current_context.user_id, quote_id, payload)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote(
    quote_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return
    quote_service.delete_quote(db, current_context.company_id, quote_id)
    return


@router.post("/{quote_id}/convert-so", status_code=status.HTTP_201_CREATED)
def convert_to_so(
    quote_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return {"sales_order_id": uuid4(), "sales_order_number": "SO-2026-00001"}
    so = quote_service.convert_to_sales_order(db, current_context.company_id, current_context.user_id, quote_id)
    return {"sales_order_id": so.sales_order_id, "sales_order_number": so.sales_order_number}


@router.post("/{quote_id}/convert-invoice", status_code=status.HTTP_201_CREATED)
def convert_to_invoice(
    quote_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        from routes.invoices import MOCK_INVOICES
        from models.invoices import InvoiceResponse, InvoiceItemResponse
        
        quote = get_quote(quote_id, current_context, db)
        invoice_id = uuid4()
        invoice_number = f"INV-2026-{str(uuid4())[:8].upper()}"
        
        invoice_items = []
        for it in quote.items:
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
            billing_party_id=quote.billing_party_id,
            shipping_party_id=quote.shipping_party_id,
            order_number=quote.quote_number,
            salesperson_id=quote.salesperson_id,
            subject=quote.subject,
            customer_notes=quote.customer_notes,
            terms_and_conditions=quote.terms_and_conditions,
            status="draft",
            invoice_subtotal=quote.subtotal,
            invoice_total_gst=quote.total_gst,
            invoice_total_tds=quote.total_tds,
            invoice_total_tcs=quote.total_tcs,
            invoice_grand_total=quote.grand_total,
            paid_amount=0.0,
            balance_due=quote.grand_total,
            currency=quote.currency,
            created_at=datetime.utcnow(),
            items=invoice_items
        )
        MOCK_INVOICES[invoice_id] = inv
        return {"invoice_id": invoice_id}
        
    invoice_id = quote_service.convert_to_invoice(db, current_context.company_id, current_context.user_id, quote_id)
    return {"invoice_id": invoice_id}


