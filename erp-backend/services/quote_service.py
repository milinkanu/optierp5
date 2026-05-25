from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update, and_, desc, text
from sqlalchemy.orm import Session

from models.db_models import (
    Quote, QuoteItem, QuoteActivityLog, QuoteStatus,
    SalesOrder, SalesOrderItem, SalesOrderActivityLog, SalesOrderStatus,
    Party, InventoryItem, ChartOfAccount
)
from models.quotes import QuoteCreateRequest, QuoteUpdateRequest


def generate_next_quote_number(db: Session, company_id: UUID) -> str:
    year = datetime.utcnow().year
    prefix = f"QT-{year}-"
    stmt = (
        select(Quote.quote_number)
        .where(and_(Quote.company_id == company_id, Quote.quote_number.like(f"{prefix}%")))
        .order_by(desc(Quote.quote_number))
        .limit(1)
    )
    latest = db.scalar(stmt)
    if latest:
        try:
            seq_part = latest.split("-")[-1]
            seq = int(seq_part) + 1
        except Exception:
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


def create_quote(db: Session, company_id: UUID, user_id: UUID, payload: QuoteCreateRequest) -> Quote:
    # Verify billing party
    billing_party = db.scalar(select(Party).where(and_(Party.party_id == payload.billing_party_id, Party.company_id == company_id)))
    if not billing_party:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing party not found")

    if payload.shipping_party_id:
        shipping_party = db.scalar(select(Party).where(and_(Party.party_id == payload.shipping_party_id, Party.company_id == company_id)))
        if not shipping_party:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shipping party not found")

    # Generate quote number if not custom, check duplicates
    q_number = payload.quote_number or generate_next_quote_number(db, company_id)
    exists = db.scalar(select(Quote.quote_id).where(and_(Quote.company_id == company_id, Quote.quote_number == q_number, Quote.is_deleted == False)))
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Quote number {q_number} already exists")

    now = datetime.utcnow()
    quote = Quote(
        company_id=company_id,
        quote_number=q_number,
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
        status=QuoteStatus.draft,
        currency=payload.currency,
        exchange_rate=payload.exchange_rate,
        discount_percentage=payload.discount_percentage,
        discount_amount=payload.discount_amount,
        adjustment=payload.adjustment,
        created_by=user_id,
        updated_by=user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(quote)
    db.flush()

    subtotal = Decimal("0")
    total_gst = Decimal("0")
    total_tds = Decimal("0")
    total_tcs = Decimal("0")

    for index, item in enumerate(payload.items):
        taxable_amount = item.quantity * item.unit_price - item.discount_amount
        gst_amount = taxable_amount * item.gst_rate / Decimal("100")
        tds_amount = taxable_amount * item.tds_rate / Decimal("100")
        tcs_amount = taxable_amount * item.tcs_rate / Decimal("100")
        total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount

        subtotal += taxable_amount
        total_gst += gst_amount
        total_tds += tds_amount
        total_tcs += tcs_amount

        db_item = QuoteItem(
            quote_id=quote.quote_id,
            company_id=company_id,
            line_number=index + 1,
            description=item.description,
            inventory_item_id=item.inventory_item_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_amount=item.discount_amount,
            taxable_amount=taxable_amount,
            gst_rate=item.gst_rate,
            gst_amount=gst_amount,
            tds_rate=item.tds_rate,
            tds_amount=tds_amount,
            tcs_rate=item.tcs_rate,
            tcs_amount=tcs_amount,
            total_amount=total_amount,
            created_at=now,
            updated_at=now,
        )
        db.add(db_item)

    # Calculate grand total
    grand_total = subtotal + total_gst + total_tcs - total_tds - payload.discount_amount + payload.adjustment
    quote.subtotal = subtotal
    quote.total_gst = total_gst
    quote.total_tds = total_tds
    quote.total_tcs = total_tcs
    quote.grand_total = grand_total

    # Add activity log
    log = QuoteActivityLog(
        quote_id=quote.quote_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="created",
        new_value={"quote_number": quote.quote_number, "grand_total": float(quote.grand_total)},
        created_at=now,
    )
    db.add(log)
    db.commit()
    db.refresh(quote)
    return quote


def update_quote(db: Session, company_id: UUID, user_id: UUID, quote_id: UUID, payload: QuoteUpdateRequest) -> Quote:
    quote = db.scalar(select(Quote).where(and_(Quote.quote_id == quote_id, Quote.company_id == company_id, Quote.is_deleted == False)))
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    if quote.status == QuoteStatus.converted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit a converted quote")

    now = datetime.utcnow()
    previous_value = {"status": quote.status.value, "grand_total": float(quote.grand_total)}

    updates = payload.model_dump(exclude_unset=True)
    items_payload = updates.pop("items", None)

    for field, value in updates.items():
        if field == "status" and value:
            setattr(quote, field, QuoteStatus(value))
        else:
            setattr(quote, field, value)

    quote.updated_by = user_id
    quote.updated_at = now

    if items_payload is not None:
        # Delete old items
        for old_item in quote.items:
            db.delete(old_item)
        db.flush()

        subtotal = Decimal("0")
        total_gst = Decimal("0")
        total_tds = Decimal("0")
        total_tcs = Decimal("0")

        # Create new items
        for index, item in enumerate(items_payload):
            taxable_amount = item.quantity * item.unit_price - item.discount_amount
            gst_amount = taxable_amount * item.gst_rate / Decimal("100")
            tds_amount = taxable_amount * item.tds_rate / Decimal("100")
            tcs_amount = taxable_amount * item.tcs_rate / Decimal("100")
            total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount

            subtotal += taxable_amount
            total_gst += gst_amount
            total_tds += tds_amount
            total_tcs += tcs_amount

            db_item = QuoteItem(
                quote_id=quote.quote_id,
                company_id=company_id,
                line_number=index + 1,
                description=item.description,
                inventory_item_id=item.inventory_item_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_amount=item.discount_amount,
                taxable_amount=taxable_amount,
                gst_rate=item.gst_rate,
                gst_amount=gst_amount,
                tds_rate=item.tds_rate,
                tds_amount=tds_amount,
                tcs_rate=item.tcs_rate,
                tcs_amount=tcs_amount,
                total_amount=total_amount,
                created_at=now,
                updated_at=now,
            )
            db.add(db_item)

        # Recalculate
        quote.subtotal = subtotal
        quote.total_gst = total_gst
        quote.total_tds = total_tds
        quote.total_tcs = total_tcs
        quote.grand_total = subtotal + total_gst + total_tcs - total_tds - quote.discount_amount + quote.adjustment

    # Add activity log
    log = QuoteActivityLog(
        quote_id=quote.quote_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="updated",
        previous_value=previous_value,
        new_value={"status": quote.status.value, "grand_total": float(quote.grand_total)},
        created_at=now,
    )
    db.add(log)
    db.commit()
    db.refresh(quote)
    return quote


def get_quote(db: Session, company_id: UUID, quote_id: UUID) -> Quote:
    quote = db.scalar(select(Quote).where(and_(Quote.quote_id == quote_id, Quote.company_id == company_id, Quote.is_deleted == False)))
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return quote


def list_quotes(db: Session, company_id: UUID, page: int = 1, limit: int = 25, q: str | None = None, status_filter: str | None = None) -> List[Quote]:
    stmt = select(Quote).where(and_(Quote.company_id == company_id, Quote.is_deleted == False))
    if q:
        stmt = stmt.where(Quote.quote_number.ilike(f"%{q}%") | Quote.subject.ilike(f"%{q}%") | Quote.project_name.ilike(f"%{q}%"))
    if status_filter:
        stmt = stmt.where(Quote.status == QuoteStatus(status_filter))

    stmt = stmt.order_by(desc(Quote.created_at)).offset((page - 1) * limit).limit(limit)
    return list(db.scalars(stmt).all())


def delete_quote(db: Session, company_id: UUID, quote_id: UUID) -> bool:
    quote = db.scalar(select(Quote).where(and_(Quote.quote_id == quote_id, Quote.company_id == company_id, Quote.is_deleted == False)))
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    quote.is_deleted = True
    quote.updated_at = datetime.utcnow()
    db.commit()
    return True


def convert_to_sales_order(db: Session, company_id: UUID, user_id: UUID, quote_id: UUID) -> SalesOrder:
    quote = get_quote(db, company_id, quote_id)
    if quote.status == QuoteStatus.converted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quote is already converted")

    now = datetime.utcnow()
    from services.sales_order_service import generate_next_so_number

    so_number = generate_next_so_number(db, company_id)

    sales_order = SalesOrder(
        company_id=company_id,
        sales_order_number=so_number,
        sales_order_date=date.today(),
        expected_shipment_date=quote.expiry_date,
        billing_party_id=quote.billing_party_id,
        shipping_party_id=quote.shipping_party_id,
        reference_number=quote.quote_number,
        payment_terms="Due on Receipt",
        salesperson_id=quote.salesperson_id,
        subject=quote.subject,
        customer_notes=quote.customer_notes,
        terms_and_conditions=quote.terms_and_conditions,
        status=SalesOrderStatus.draft,
        currency=quote.currency,
        exchange_rate=quote.exchange_rate,
        discount_percentage=quote.discount_percentage,
        discount_amount=quote.discount_amount,
        adjustment=quote.adjustment,
        created_by=user_id,
        updated_by=user_id,
        created_at=now,
        updated_at=now,
        quote_id=quote_id,
    )
    db.add(sales_order)
    db.flush()

    for item in quote.items:
        db_item = SalesOrderItem(
            sales_order_id=sales_order.sales_order_id,
            company_id=company_id,
            line_number=item.line_number,
            description=item.description,
            inventory_item_id=item.inventory_item_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_amount=item.discount_amount,
            taxable_amount=item.taxable_amount,
            gst_rate=item.gst_rate,
            gst_amount=item.gst_amount,
            tds_rate=item.tds_rate,
            tds_amount=item.tds_amount,
            tcs_rate=item.tcs_rate,
            tcs_amount=item.tcs_amount,
            total_amount=item.total_amount,
            created_at=now,
            updated_at=now,
        )
        db.add(db_item)

    # Force database recalculated fields
    sales_order.subtotal = quote.subtotal
    sales_order.total_gst = quote.total_gst
    sales_order.total_tds = quote.total_tds
    sales_order.total_tcs = quote.total_tcs
    sales_order.grand_total = quote.grand_total

    # Update quote status
    quote.status = QuoteStatus.converted
    quote.updated_by = user_id
    quote.updated_at = now

    # Log Quote conversion activity
    quote_log = QuoteActivityLog(
        quote_id=quote_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="converted_to_so",
        new_value={"sales_order_number": so_number, "sales_order_id": str(sales_order.sales_order_id)},
        created_at=now,
    )
    db.add(quote_log)

    # Log Sales Order creation activity
    so_log = SalesOrderActivityLog(
        sales_order_id=sales_order.sales_order_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="created_from_quote",
        new_value={"quote_number": quote.quote_number, "quote_id": str(quote_id)},
        created_at=now,
    )
    db.add(so_log)

    db.commit()
    db.refresh(sales_order)
    return sales_order


def convert_to_invoice(db: Session, company_id: UUID, user_id: UUID, quote_id: UUID) -> UUID:
    quote = get_quote(db, company_id, quote_id)
    if quote.status == QuoteStatus.converted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quote is already converted")

    # Fetch default income/sales account (with code 4100 or type income)
    account = db.scalar(
        select(ChartOfAccount)
        .where(and_(ChartOfAccount.company_id == company_id, ChartOfAccount.account_code == "4100"))
    )
    if not account:
        account = db.scalar(
            select(ChartOfAccount)
            .where(and_(ChartOfAccount.company_id == company_id, ChartOfAccount.account_type == "income"))
        )
    if not account:
        from services.coa_seed import seed_default_chart_of_accounts
        seed_default_chart_of_accounts(db, company_id)
        db.commit()
        account = db.scalar(
            select(ChartOfAccount)
            .where(and_(ChartOfAccount.company_id == company_id, ChartOfAccount.account_code == "4100"))
        )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Default Sales Account (code 4100 or type income) not found. Please create it first.",
        )

    # Build raw transaction and invoice using SQL to match routes/invoices.py logic
    # and link quote_id.
    now = datetime.utcnow()
    transaction_id = uuid4()
    invoice_id = uuid4()

    # Get next invoice number using active db session
    invoice_number = db.execute(
        text("SELECT app.next_invoice_number(:company_id, :invoice_type)"),
        {"company_id": str(company_id), "invoice_type": "sales_invoice"}
    ).scalar_one()

    db.execute(
        text(
            "INSERT INTO transactions (transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, party_id, subtotal, gst_breakdown, grand_total, status, created_by, updated_by, created_at, updated_at) "
            "VALUES (:transaction_id, :company_id, 'sales_invoice', :txn_number, :txn_date, :fiscal_year, :period, :cust_id, :subtotal, :gst_breakdown, :grand_total, 'posted', :created_by, :updated_by, :created_at, :updated_at)"
        ),
        {
            "transaction_id": str(transaction_id),
            "company_id": str(company_id),
            "txn_number": invoice_number,
            "txn_date": date.today(),
            "fiscal_year": date.today().strftime("%Y"),
            "period": date.today().strftime("%Y-%m"),
            "cust_id": str(quote.billing_party_id),
            "subtotal": float(quote.subtotal),
            "gst_breakdown": json.dumps({"gst_total": float(quote.total_gst), "tds_total": float(quote.total_tds), "tcs_total": float(quote.total_tcs)}),
            "grand_total": float(quote.grand_total),
            "created_by": str(user_id),
            "updated_by": str(user_id),
            "created_at": now,
            "updated_at": now,
        }
    )

    db.execute(
        text(
            "INSERT INTO invoices (invoice_id, company_id, transaction_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, order_number, salesperson_id, subject, customer_notes, terms_and_conditions, currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_total_tds, invoice_total_tcs, invoice_grand_total, status, created_by, updated_by, created_at, updated_at, quote_id) "
            "VALUES (:invoice_id, :company_id, :transaction_id, :invoice_number, :invoice_type, :invoice_date, :due_date, :billing_party_id, :shipping_party_id, :order_number, :salesperson_id, :subject, :customer_notes, :terms_and_conditions, :currency, :exchange_rate, :invoice_subtotal, :invoice_total_gst, :invoice_total_tds, :invoice_total_tcs, :invoice_grand_total, :status, :created_by, :updated_by, :created_at, :updated_at, :quote_id)"
        ),
        {
            "invoice_id": str(invoice_id),
            "company_id": str(company_id),
            "transaction_id": str(transaction_id),
            "invoice_number": invoice_number,
            "invoice_type": "sales_invoice",
            "invoice_date": date.today(),
            "due_date": quote.expiry_date,
            "billing_party_id": str(quote.billing_party_id),
            "shipping_party_id": str(quote.shipping_party_id) if quote.shipping_party_id else None,
            "order_number": quote.quote_number,
            "salesperson_id": str(quote.salesperson_id) if quote.salesperson_id else None,
            "subject": quote.subject,
            "customer_notes": quote.customer_notes,
            "terms_and_conditions": quote.terms_and_conditions,
            "currency": quote.currency,
            "exchange_rate": float(quote.exchange_rate),
            "invoice_subtotal": float(quote.subtotal),
            "invoice_total_gst": float(quote.total_gst),
            "invoice_total_tds": float(quote.total_tds),
            "invoice_total_tcs": float(quote.total_tcs),
            "invoice_grand_total": float(quote.grand_total),
            "status": "draft",
            "created_by": str(user_id),
            "updated_by": str(user_id),
            "created_at": now,
            "updated_at": now,
            "quote_id": str(quote_id),
        }
    )

    for item in quote.items:
        # Query item sales_account if inventory_item exists
        item_sales_acc_id = None
        if item.inventory_item_id:
            inv_item = db.scalar(
                select(InventoryItem)
                .where(and_(InventoryItem.inventory_item_id == item.inventory_item_id, InventoryItem.company_id == company_id))
            )
            if inv_item:
                item_sales_acc_id = inv_item.sales_account_id

        final_acc_id = item_sales_acc_id or account.account_id

        db.execute(
            text(
                "INSERT INTO invoice_items (invoice_item_id, invoice_id, company_id, line_number, description, hsn_sac, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, total_amount, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :invoice_id, :company_id, :line_number, :description, :hsn_sac, :account_id, :quantity, :unit_price, :discount_amount, :taxable_amount, :gst_rate, :gst_amount, :tds_rate, :tds_amount, :tcs_rate, :tcs_amount, :total_amount, :created_at, :updated_at)"
            ),
            {
                "invoice_id": str(invoice_id),
                "company_id": str(company_id),
                    "account_id": str(final_acc_id),
                    "quantity": float(item.quantity),
                    "unit_price": float(item.unit_price),
                    "discount_amount": float(item.discount_amount),
                    "taxable_amount": float(item.taxable_amount),
                    "gst_rate": float(item.gst_rate),
                    "gst_amount": float(item.gst_amount),
                    "tds_rate": float(item.tds_rate),
                    "tds_amount": float(item.tds_amount),
                    "tcs_rate": float(item.tcs_rate),
                    "tcs_amount": float(item.tcs_amount),
                    "total_amount": float(item.total_amount),
                    "created_at": now,
                    "updated_at": now,
                }
            )

    # Set quote converted status
    quote.status = QuoteStatus.converted
    quote.updated_by = user_id
    quote.updated_at = now

    quote_log = QuoteActivityLog(
        quote_id=quote_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="converted_to_invoice",
        new_value={"invoice_number": invoice_number, "invoice_id": str(invoice_id)},
        created_at=now,
    )
    db.add(quote_log)
    db.commit()

    return invoice_id
