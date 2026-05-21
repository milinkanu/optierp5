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
    SalesOrder, SalesOrderItem, SalesOrderActivityLog, SalesOrderStatus,
    Party, InventoryItem, ChartOfAccount
)
from models.sales_orders import SalesOrderCreateRequest, SalesOrderUpdateRequest


def generate_next_so_number(db: Session, company_id: UUID) -> str:
    year = datetime.utcnow().year
    prefix = f"SO-{year}-"
    stmt = (
        select(SalesOrder.sales_order_number)
        .where(and_(SalesOrder.company_id == company_id, SalesOrder.sales_order_number.like(f"{prefix}%")))
        .order_by(desc(SalesOrder.sales_order_number))
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


def create_sales_order(db: Session, company_id: UUID, user_id: UUID, payload: SalesOrderCreateRequest) -> SalesOrder:
    # Verify billing party
    billing_party = db.scalar(select(Party).where(and_(Party.party_id == payload.billing_party_id, Party.company_id == company_id)))
    if not billing_party:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing party not found")

    if payload.shipping_party_id:
        shipping_party = db.scalar(select(Party).where(and_(Party.party_id == payload.shipping_party_id, Party.company_id == company_id)))
        if not shipping_party:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shipping party not found")

    # Generate so number if not custom, check duplicates
    so_number = payload.sales_order_number or generate_next_so_number(db, company_id)
    exists = db.scalar(
        select(SalesOrder.sales_order_id)
        .where(and_(SalesOrder.company_id == company_id, SalesOrder.sales_order_number == so_number, SalesOrder.is_deleted == False))
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Sales order number {so_number} already exists")

    now = datetime.utcnow()
    sales_order = SalesOrder(
        company_id=company_id,
        sales_order_number=so_number,
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
        status=SalesOrderStatus.draft,
        currency=payload.currency,
        exchange_rate=payload.exchange_rate,
        discount_percentage=payload.discount_percentage,
        discount_amount=payload.discount_amount,
        adjustment=payload.adjustment,
        created_by=user_id,
        updated_by=user_id,
        created_at=now,
        updated_at=now,
        quote_id=payload.quote_id,
    )
    db.add(sales_order)
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

        db_item = SalesOrderItem(
            sales_order_id=sales_order.sales_order_id,
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
    sales_order.subtotal = subtotal
    sales_order.total_gst = total_gst
    sales_order.total_tds = total_tds
    sales_order.total_tcs = total_tcs
    sales_order.grand_total = grand_total

    # Add activity log
    log = SalesOrderActivityLog(
        sales_order_id=sales_order.sales_order_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="created",
        new_value={"sales_order_number": sales_order.sales_order_number, "grand_total": float(sales_order.grand_total)},
        created_at=now,
    )
    db.add(log)
    db.commit()
    db.refresh(sales_order)
    return sales_order


def update_sales_order(db: Session, company_id: UUID, user_id: UUID, sales_order_id: UUID, payload: SalesOrderUpdateRequest) -> SalesOrder:
    sales_order = db.scalar(
        select(SalesOrder)
        .where(and_(SalesOrder.sales_order_id == sales_order_id, SalesOrder.company_id == company_id, SalesOrder.is_deleted == False))
    )
    if not sales_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")

    if sales_order.status in (SalesOrderStatus.invoiced, SalesOrderStatus.cancelled):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot edit sales order in {sales_order.status.value} status")

    now = datetime.utcnow()
    previous_value = {"status": sales_order.status.value, "grand_total": float(sales_order.grand_total)}

    updates = payload.model_dump(exclude_unset=True)
    items_payload = updates.pop("items", None)

    for field, value in updates.items():
        if field == "status" and value:
            setattr(sales_order, field, SalesOrderStatus(value))
        else:
            setattr(sales_order, field, value)

    sales_order.updated_by = user_id
    sales_order.updated_at = now

    if items_payload is not None:
        # Delete old items
        for old_item in sales_order.items:
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

            db_item = SalesOrderItem(
                sales_order_id=sales_order.sales_order_id,
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
        sales_order.subtotal = subtotal
        sales_order.total_gst = total_gst
        sales_order.total_tds = total_tds
        sales_order.total_tcs = total_tcs
        sales_order.grand_total = subtotal + total_gst + total_tcs - total_tds - sales_order.discount_amount + sales_order.adjustment

    # Add activity log
    log = SalesOrderActivityLog(
        sales_order_id=sales_order.sales_order_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="updated",
        previous_value=previous_value,
        new_value={"status": sales_order.status.value, "grand_total": float(sales_order.grand_total)},
        created_at=now,
    )
    db.add(log)
    db.commit()
    db.refresh(sales_order)
    return sales_order


def get_sales_order(db: Session, company_id: UUID, sales_order_id: UUID) -> SalesOrder:
    sales_order = db.scalar(
        select(SalesOrder)
        .where(and_(SalesOrder.sales_order_id == sales_order_id, SalesOrder.company_id == company_id, SalesOrder.is_deleted == False))
    )
    if not sales_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")
    return sales_order


def list_sales_orders(
    db: Session, company_id: UUID, page: int = 1, limit: int = 25, q: str | None = None, status_filter: str | None = None
) -> List[SalesOrder]:
    stmt = select(SalesOrder).where(and_(SalesOrder.company_id == company_id, SalesOrder.is_deleted == False))
    if q:
        stmt = stmt.where(SalesOrder.sales_order_number.ilike(f"%{q}%") | SalesOrder.subject.ilike(f"%{q}%") | SalesOrder.reference_number.ilike(f"%{q}%"))
    if status_filter:
        stmt = stmt.where(SalesOrder.status == SalesOrderStatus(status_filter))

    stmt = stmt.order_by(desc(SalesOrder.created_at)).offset((page - 1) * limit).limit(limit)
    return list(db.scalars(stmt).all())


def delete_sales_order(db: Session, company_id: UUID, sales_order_id: UUID) -> bool:
    sales_order = db.scalar(
        select(SalesOrder)
        .where(and_(SalesOrder.sales_order_id == sales_order_id, SalesOrder.company_id == company_id, SalesOrder.is_deleted == False))
    )
    if not sales_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales order not found")
    sales_order.is_deleted = True
    sales_order.updated_at = datetime.utcnow()
    db.commit()
    return True


def convert_to_invoice(db: Session, company_id: UUID, user_id: UUID, sales_order_id: UUID) -> UUID:
    sales_order = get_sales_order(db, company_id, sales_order_id)
    if sales_order.status in (SalesOrderStatus.invoiced, SalesOrderStatus.cancelled):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot invoice a sales order in status {sales_order.status.value}")

    # Fetch default income/sales account
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
    # and link sales_order_id.
    from utils.db_invoice import engine
    now = datetime.utcnow()
    transaction_id = uuid4()
    invoice_id = uuid4()

    with engine.begin() as conn:
        # Get next invoice number
        invoice_number = conn.execute(
            text("SELECT app.next_invoice_number(:company_id, :invoice_type)"),
            {"company_id": str(company_id), "invoice_type": "sales_invoice"}
        ).scalar_one()

        conn.execute(
            text(
                "INSERT INTO transactions (transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, subtotal, gst_breakdown, grand_total, status, currency, exchange_rate, created_by, updated_by, created_at, updated_at) "
                "VALUES (:transaction_id, :company_id, :txn_type, :txn_number, :txn_date, :fiscal_year, :period, :subtotal, :gst_breakdown, :grand_total, :status, :currency, :exchange_rate, :created_by, :updated_by, :created_at, :updated_at)"
            ),
            {
                "transaction_id": str(transaction_id),
                "company_id": str(company_id),
                "txn_type": "sales_invoice",
                "txn_number": invoice_number,
                "txn_date": date.today(),
                "fiscal_year": date.today().strftime("%Y-%m"),
                "period": date.today().strftime("%Y-%m"),
                "subtotal": float(sales_order.subtotal),
                "gst_breakdown": json.dumps({"gst_total": float(sales_order.total_gst), "tds_total": float(sales_order.total_tds), "tcs_total": float(sales_order.total_tcs)}),
                "grand_total": float(sales_order.grand_total),
                "status": "draft",
                "currency": sales_order.currency,
                "exchange_rate": float(sales_order.exchange_rate),
                "created_by": str(user_id),
                "updated_by": str(user_id),
                "created_at": now,
                "updated_at": now,
            }
        )

        conn.execute(
            text(
                "INSERT INTO invoices (invoice_id, company_id, transaction_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, order_number, salesperson_id, subject, customer_notes, terms_and_conditions, currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_total_tds, invoice_total_tcs, invoice_grand_total, status, created_by, updated_by, created_at, updated_at, sales_order_id) "
                "VALUES (:invoice_id, :company_id, :transaction_id, :invoice_number, :invoice_type, :invoice_date, :due_date, :billing_party_id, :shipping_party_id, :order_number, :salesperson_id, :subject, :customer_notes, :terms_and_conditions, :currency, :exchange_rate, :invoice_subtotal, :invoice_total_gst, :invoice_total_tds, :invoice_total_tcs, :invoice_grand_total, :status, :created_by, :updated_by, :created_at, :updated_at, :sales_order_id)"
            ),
            {
                "invoice_id": str(invoice_id),
                "company_id": str(company_id),
                "transaction_id": str(transaction_id),
                "invoice_number": invoice_number,
                "invoice_type": "sales_invoice",
                "invoice_date": date.today(),
                "due_date": sales_order.expected_shipment_date,
                "billing_party_id": str(sales_order.billing_party_id),
                "shipping_party_id": str(sales_order.shipping_party_id) if sales_order.shipping_party_id else None,
                "order_number": sales_order.sales_order_number,
                "salesperson_id": str(sales_order.salesperson_id) if sales_order.salesperson_id else None,
                "subject": sales_order.subject,
                "customer_notes": sales_order.customer_notes,
                "terms_and_conditions": sales_order.terms_and_conditions,
                "currency": sales_order.currency,
                "exchange_rate": float(sales_order.exchange_rate),
                "invoice_subtotal": float(sales_order.subtotal),
                "invoice_total_gst": float(sales_order.total_gst),
                "invoice_total_tds": float(sales_order.total_tds),
                "invoice_total_tcs": float(sales_order.total_tcs),
                "invoice_grand_total": float(sales_order.grand_total),
                "status": "draft",
                "created_by": str(user_id),
                "updated_by": str(user_id),
                "created_at": now,
                "updated_at": now,
                "sales_order_id": str(sales_order_id),
            }
        )

        for item in sales_order.items:
            item_sales_acc_id = None
            if item.inventory_item_id:
                inv_item = db.scalar(
                    select(InventoryItem)
                    .where(and_(InventoryItem.inventory_item_id == item.inventory_item_id, InventoryItem.company_id == company_id))
                )
                if inv_item:
                    item_sales_acc_id = inv_item.sales_account_id

            final_acc_id = item_sales_acc_id or account.account_id

            conn.execute(
                text(
                    "INSERT INTO invoice_items (invoice_item_id, invoice_id, company_id, line_number, description, hsn_sac, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, total_amount, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :invoice_id, :company_id, :line_number, :description, :hsn_sac, :account_id, :quantity, :unit_price, :discount_amount, :taxable_amount, :gst_rate, :gst_amount, :tds_rate, :tds_amount, :tcs_rate, :tcs_amount, :total_amount, :created_at, :updated_at)"
                ),
                {
                    "invoice_id": str(invoice_id),
                    "company_id": str(company_id),
                    "line_number": item.line_number,
                    "description": item.description,
                    "hsn_sac": "0000",
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

    # Set Sales Order to invoiced
    sales_order.status = SalesOrderStatus.invoiced
    sales_order.updated_by = user_id
    sales_order.updated_at = now

    so_log = SalesOrderActivityLog(
        sales_order_id=sales_order_id,
        company_id=company_id,
        actor_user_id=user_id,
        action="converted_to_invoice",
        new_value={"invoice_number": invoice_number, "invoice_id": str(invoice_id)},
        created_at=now,
    )
    db.add(so_log)
    db.commit()

    return invoice_id
