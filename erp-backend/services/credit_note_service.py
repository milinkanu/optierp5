from __future__ import annotations

import io
import os
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text

from models.credit_notes import (
    CreditNoteItemCreate,
    CreditNoteItemResponse,
    CreditNoteCreateRequest,
    CreditNoteUpdateRequest,
    CreditNoteResponse,
    CreditNoteApplyRequest,
    CreditNoteInvoiceMappingResponse,
    CreditNoteActivityLogResponse,
)
from utils.db_invoice import engine

# ----------------------------------------------------
# STATUS MAPPER
# ----------------------------------------------------
def map_cn_status_to_txn_status(cn_status: str) -> str:
    mapping = {
        'draft': 'draft',
        'open': 'posted',
        'partially_applied': 'partial',
        'applied': 'paid',
        'cancelled': 'cancelled'
    }
    return mapping.get(cn_status, 'draft')


# ----------------------------------------------------
# IN-MEMORY DEMO STORAGE FOR MOCK BYPASS MODE
# ----------------------------------------------------
MOCK_CREDIT_NOTES: dict[UUID, dict] = {}
MOCK_ACTIVITY_LOGS: list[dict] = []
MOCK_MAPPINGS: list[dict] = []


def _get_mock_coa_account_id(code: str) -> UUID:
    # Stable deterministic UUIDs for mock Chart of Accounts
    return UUID(f"c0ac0ac0-0000-0000-0000-00000000{code}")


def _get_mock_party_id() -> UUID:
    return UUID("ce3ba27e-128a-45bd-b65d-9c7f1db8816c")


def get_next_credit_note_number(company_id: UUID) -> str:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        count = len(MOCK_CREDIT_NOTES) + 1
        return f"CN-2026-{count:05d}"

    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COALESCE(COUNT(*), 0) + 1 FROM credit_notes WHERE company_id = :company_id"),
            {"company_id": str(company_id)}
        ).scalar_one()
        return f"CN-2026-{count:05d}"


def create_credit_note(payload: CreditNoteCreateRequest, company_id: UUID, user_id: UUID) -> CreditNoteResponse:
    credit_note_id = uuid4()
    transaction_id = uuid4()
    cn_number = payload.credit_note_number or get_next_credit_note_number(company_id)

    # In-Memory Mock Mode
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        subtotal = Decimal('0')
        total_gst = Decimal('0')
        total_tds = Decimal('0')
        total_tcs = Decimal('0')
        grand_total = Decimal('0')
        items = []

        for idx, item in enumerate(payload.items):
            taxable = item.quantity * item.rate - item.discount_amount
            gst = round(taxable * item.tax_percentage / Decimal('100'), 2)
            tds = round(taxable * item.tds_rate / Decimal('100'), 2)
            tcs = round(taxable * item.tcs_rate / Decimal('100'), 2)
            total = taxable + gst + tcs - tds

            subtotal += taxable
            total_gst += gst
            total_tds += tds
            total_tcs += tcs
            grand_total += total

            items.append({
                "credit_note_item_id": uuid4(),
                "credit_note_id": credit_note_id,
                "company_id": company_id,
                "line_number": idx + 1,
                "description": item.description,
                "hsn_sac": item.hsn_sac,
                "inventory_item_id": item.inventory_item_id,
                "account_id": item.account_id,
                "quantity": float(item.quantity),
                "unit": item.unit,
                "rate": float(item.rate),
                "discount_amount": float(item.discount_amount),
                "taxable_amount": float(taxable),
                "tax_id": item.tax_id,
                "tax_percentage": float(item.tax_percentage),
                "tax_amount": float(gst),
                "tds_rate": float(item.tds_rate),
                "tds_amount": float(tds),
                "tcs_rate": float(item.tcs_rate),
                "tcs_amount": float(tcs),
                "line_total": float(total),
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })

        cn_dict = {
            "credit_note_id": credit_note_id,
            "transaction_id": transaction_id,
            "credit_note_number": cn_number,
            "reference_number": payload.reference_number,
            "credit_note_date": payload.credit_note_date,
            "billing_party_id": payload.billing_party_id,
            "shipping_party_id": payload.shipping_party_id,
            "status": payload.status,
            "currency": payload.currency,
            "exchange_rate": float(payload.exchange_rate),
            "accounts_receivable_id": _get_mock_coa_account_id("1200"),
            "salesperson_id": payload.salesperson_id,
            "subtotal": float(subtotal),
            "total_gst": float(total_gst),
            "total_tds": float(total_tds),
            "total_tcs": float(total_tcs),
            "grand_total": float(grand_total),
            "remaining_balance": float(grand_total) if payload.status != "draft" else 0.0,
            "customer_notes": payload.customer_notes,
            "terms_and_conditions": payload.terms_and_conditions,
            "created_by": user_id,
            "updated_by": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "items": items
        }
        MOCK_CREDIT_NOTES[credit_note_id] = cn_dict

        MOCK_ACTIVITY_LOGS.append({
            "log_id": uuid4(),
            "credit_note_id": credit_note_id,
            "company_id": company_id,
            "activity_type": "created",
            "description": f"Credit Note {cn_number} created with grand total {grand_total}",
            "metadata": {"grand_total": float(grand_total)},
            "created_by": user_id,
            "created_at": datetime.utcnow()
        })

        return CreditNoteResponse(
            **cn_dict,
            items=[CreditNoteItemResponse(**x) for x in items]
        )

    # Database Mode
    with engine.begin() as conn:
        # Check duplicates
        dup = conn.execute(
            text("SELECT credit_note_id FROM credit_notes WHERE company_id = :company_id AND credit_note_number = :num AND is_deleted = FALSE"),
            {"company_id": str(company_id), "num": cn_number}
        ).fetchone()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Credit Note number {cn_number} already exists"
            )

        # 1. Insert into transactions table
        subtotal = Decimal('0')
        total_gst = Decimal('0')
        total_tds = Decimal('0')
        total_tcs = Decimal('0')
        grand_total = Decimal('0')

        for item in payload.items:
            taxable = item.quantity * item.rate - item.discount_amount
            gst = round(taxable * item.tax_percentage / Decimal('100'), 2)
            tds = round(taxable * item.tds_rate / Decimal('100'), 2)
            tcs = round(taxable * item.tcs_rate / Decimal('100'), 2)
            total = taxable + gst + tcs - tds

            subtotal += taxable
            total_gst += gst
            total_tds += tds
            total_tcs += tcs
            grand_total += total

        conn.execute(
            text(
                "INSERT INTO transactions (transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, subtotal, gst_breakdown, grand_total, status, currency, exchange_rate, created_by, updated_by, created_at, updated_at) "
                "VALUES (:transaction_id, :company_id, 'credit_note', :txn_number, :txn_date, :fiscal_year, :period, :subtotal, :gst_breakdown, :grand_total, :status, :currency, :exchange_rate, :created_by, :updated_by, now(), now())"
            ),
            {
                'transaction_id': str(transaction_id),
                'company_id': str(company_id),
                'txn_number': cn_number,
                'txn_date': payload.credit_note_date,
                'fiscal_year': payload.credit_note_date.strftime('%Y-%m'),
                'period': payload.credit_note_date.strftime('%Y-%m'),
                'subtotal': float(subtotal),
                'gst_breakdown': json_dumps({"gst_total": float(total_gst), "tds_total": float(total_tds), "tcs_total": float(total_tcs)}),
                'grand_total': float(grand_total),
                'status': map_cn_status_to_txn_status(payload.status),
                'currency': payload.currency,
                'exchange_rate': float(payload.exchange_rate),
                'created_by': str(user_id),
                'updated_by': str(user_id)
            }
        )

        # 2. Resolve Accounts Receivable Account (1200)
        ar_account = conn.execute(
            text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '1200' AND is_active = TRUE"),
            {"company_id": str(company_id)}
        ).fetchone()
        ar_account_id = ar_account[0] if ar_account else None

        # 3. Insert Credit Note Header
        conn.execute(
            text(
                "INSERT INTO credit_notes (credit_note_id, company_id, transaction_id, credit_note_number, reference_number, credit_note_date, billing_party_id, shipping_party_id, status, currency, exchange_rate, accounts_receivable_id, salesperson_id, subtotal, total_gst, total_tds, total_tcs, grand_total, remaining_balance, customer_notes, terms_and_conditions, created_by, updated_by) "
                "VALUES (:credit_note_id, :company_id, :transaction_id, :credit_note_number, :reference_number, :credit_note_date, :billing_party_id, :shipping_party_id, :status, :currency, :exchange_rate, :accounts_receivable_id, :salesperson_id, :subtotal, :total_gst, :total_tds, :total_tcs, :grand_total, :remaining_balance, :customer_notes, :terms_and_conditions, :created_by, :updated_by)"
            ),
            {
                'credit_note_id': str(credit_note_id),
                'company_id': str(company_id),
                'transaction_id': str(transaction_id),
                'credit_note_number': cn_number,
                'reference_number': payload.reference_number,
                'credit_note_date': payload.credit_note_date,
                'billing_party_id': str(payload.billing_party_id),
                'shipping_party_id': str(payload.shipping_party_id) if payload.shipping_party_id else None,
                'status': payload.status,
                'currency': payload.currency,
                'exchange_rate': float(payload.exchange_rate),
                'accounts_receivable_id': str(ar_account_id) if ar_account_id else None,
                'salesperson_id': str(payload.salesperson_id) if payload.salesperson_id else None,
                'subtotal': float(subtotal),
                'total_gst': float(total_gst),
                'total_tds': float(total_tds),
                'total_tcs': float(total_tcs),
                'grand_total': float(grand_total),
                'remaining_balance': float(grand_total) if payload.status != 'draft' else 0.0,
                'customer_notes': payload.customer_notes,
                'terms_and_conditions': payload.terms_and_conditions,
                'created_by': str(user_id),
                'updated_by': str(user_id)
            }
        )

        # 4. Insert Items
        for idx, item in enumerate(payload.items):
            taxable = item.quantity * item.rate - item.discount_amount
            gst = round(taxable * item.tax_percentage / Decimal('100'), 2)
            tds = round(taxable * item.tds_rate / Decimal('100'), 2)
            tcs = round(taxable * item.tcs_rate / Decimal('100'), 2)
            total = taxable + gst + tcs - tds

            conn.execute(
                text(
                    "INSERT INTO credit_note_items (credit_note_item_id, credit_note_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit, rate, discount_amount, taxable_amount, tax_id, tax_percentage, tax_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, line_total) "
                    "VALUES (gen_random_uuid(), :credit_note_id, :company_id, :line_number, :description, :hsn_sac, :inventory_item_id, :account_id, :quantity, :unit, :rate, :discount_amount, :taxable_amount, :tax_id, :tax_percentage, :tax_amount, :tds_rate, :tds_amount, :tcs_rate, :tcs_amount, :line_total)"
                ),
                {
                    'credit_note_id': str(credit_note_id),
                    'company_id': str(company_id),
                    'line_number': idx + 1,
                    'description': item.description,
                    'hsn_sac': item.hsn_sac,
                    'inventory_item_id': str(item.inventory_item_id) if item.inventory_item_id else None,
                    'account_id': str(item.account_id),
                    'quantity': float(item.quantity),
                    'unit': item.unit,
                    'rate': float(item.rate),
                    'discount_amount': float(item.discount_amount),
                    'taxable_amount': float(taxable),
                    'tax_id': str(item.tax_id) if item.tax_id else None,
                    'tax_percentage': float(item.tax_percentage),
                    'tax_amount': float(gst),
                    'tds_rate': float(item.tds_rate),
                    'tds_amount': float(tds),
                    'tcs_rate': float(item.tcs_rate),
                    'tcs_amount': float(tcs),
                    'line_total': float(total)
                }
            )

        # 5. balanced Ledger Posting if immediately open
        if payload.status == 'open':
            _post_ledger_entries_conn(conn, credit_note_id, company_id, user_id)

        # 6. Log Activity
        conn.execute(
            text(
                "INSERT INTO credit_note_activity_logs (credit_note_id, company_id, activity_type, description, metadata, created_by) "
                "VALUES (:credit_note_id, :company_id, 'created', :description, :metadata, :created_by)"
            ),
            {
                'credit_note_id': str(credit_note_id),
                'company_id': str(company_id),
                'description': f"Credit Note {cn_number} created in '{payload.status}' status.",
                'metadata': json_dumps({"grand_total": float(grand_total)}),
                'created_by': str(user_id)
            }
        )

        return _get_credit_note_conn(conn, credit_note_id, company_id)


def get_credit_note(credit_note_id: UUID, company_id: UUID) -> CreditNoteResponse:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if credit_note_id not in MOCK_CREDIT_NOTES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found")
        data = MOCK_CREDIT_NOTES[credit_note_id]
        return CreditNoteResponse(
            **data,
            items=[CreditNoteItemResponse(**x) for x in data.get('items', [])]
        )

    with engine.begin() as conn:
        return _get_credit_note_conn(conn, credit_note_id, company_id)


def update_credit_note(credit_note_id: UUID, payload: CreditNoteUpdateRequest, company_id: UUID, user_id: UUID) -> CreditNoteResponse:
    # Mock update
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if credit_note_id not in MOCK_CREDIT_NOTES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found")
        
        data = MOCK_CREDIT_NOTES[credit_note_id]
        if data['status'] in ('open', 'partially_applied', 'applied') and payload.status != 'cancelled' and payload.items is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify line items on posted/active credit notes"
            )

        updates = payload.model_dump(exclude_unset=True)
        items_payload = updates.pop("items", None)

        for field, value in updates.items():
            if value is not None:
                data[field] = value

        if payload.items is not None:
            subtotal = Decimal('0')
            total_gst = Decimal('0')
            total_tds = Decimal('0')
            total_tcs = Decimal('0')
            grand_total = Decimal('0')
            items = []

            for idx, item in enumerate(payload.items):
                taxable = item.quantity * item.rate - item.discount_amount
                gst = round(taxable * item.tax_percentage / Decimal('100'), 2)
                tds = round(taxable * item.tds_rate / Decimal('100'), 2)
                tcs = round(taxable * item.tcs_rate / Decimal('100'), 2)
                total = taxable + gst + tcs - tds

                subtotal += taxable
                total_gst += gst
                total_tds += tds
                total_tcs += tcs
                grand_total += total

                items.append({
                    "credit_note_item_id": uuid4(),
                    "credit_note_id": credit_note_id,
                    "company_id": company_id,
                    "line_number": idx + 1,
                    "description": item.description,
                    "hsn_sac": item.hsn_sac,
                    "inventory_item_id": item.inventory_item_id,
                    "account_id": item.account_id,
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "rate": float(item.rate),
                    "discount_amount": float(item.discount_amount),
                    "taxable_amount": float(taxable),
                    "tax_id": item.tax_id,
                    "tax_percentage": float(item.tax_percentage),
                    "tax_amount": float(gst),
                    "tds_rate": float(item.tds_rate),
                    "tds_amount": float(tds),
                    "tcs_rate": float(item.tcs_rate),
                    "tcs_amount": float(tcs),
                    "line_total": float(total),
                    "is_deleted": False,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })

            data['subtotal'] = float(subtotal)
            data['total_gst'] = float(total_gst)
            data['total_tds'] = float(total_tds)
            data['total_tcs'] = float(total_tcs)
            data['grand_total'] = float(grand_total)
            data['remaining_balance'] = float(grand_total) if data['status'] != 'draft' else 0.0
            data['items'] = items

        MOCK_ACTIVITY_LOGS.append({
            "log_id": uuid4(),
            "credit_note_id": credit_note_id,
            "company_id": company_id,
            "activity_type": "updated",
            "description": f"Credit Note {data['credit_note_number']} updated.",
            "metadata": {},
            "created_by": user_id,
            "created_at": datetime.utcnow()
        })
        return get_credit_note(credit_note_id, company_id)

    # Database Mode
    with engine.begin() as conn:
        current = conn.execute(
            text("SELECT status, transaction_id, credit_note_number, grand_total FROM credit_notes WHERE credit_note_id = :id AND company_id = :cid AND is_deleted = FALSE"),
            {"id": str(credit_note_id), "cid": str(company_id)}
        ).fetchone()
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found")

        curr_status = current[0]
        txn_id = current[1]
        cn_number = current[2]

        if curr_status in ('open', 'partially_applied', 'applied') and payload.status != 'cancelled' and payload.items is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify line items on open or applied credit notes"
            )

        updates = payload.model_dump(exclude_unset=True)
        items_payload = updates.pop("items", None)

        # Build dynamic update statement
        set_clauses = []
        params = {"id": str(credit_note_id), "cid": str(company_id)}
        for field, val in updates.items():
            if val is not None:
                set_clauses.append(f"{field} = :{field}")
                if isinstance(val, (date, datetime)):
                    params[field] = val
                elif isinstance(val, Decimal):
                    params[field] = float(val)
                elif isinstance(val, UUID):
                    params[field] = str(val)
                else:
                    params[field] = val

        if set_clauses:
            conn.execute(
                text(f"UPDATE credit_notes SET {', '.join(set_clauses)}, updated_at = now() WHERE credit_note_id = :id AND company_id = :cid"),
                params
            )

        if payload.items is not None:
            # Delete old items and insert new ones
            conn.execute(
                text("DELETE FROM credit_note_items WHERE credit_note_id = :id"),
                {"id": str(credit_note_id)}
            )

            for idx, item in enumerate(payload.items):
                taxable = item.quantity * item.rate - item.discount_amount
                gst = round(taxable * item.tax_percentage / Decimal('100'), 2)
                tds = round(taxable * item.tds_rate / Decimal('100'), 2)
                tcs = round(taxable * item.tcs_rate / Decimal('100'), 2)
                total = taxable + gst + tcs - tds

                conn.execute(
                    text(
                        "INSERT INTO credit_note_items (credit_note_item_id, credit_note_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit, rate, discount_amount, taxable_amount, tax_id, tax_percentage, tax_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, line_total) "
                        "VALUES (gen_random_uuid(), :credit_note_id, :company_id, :line_number, :description, :hsn_sac, :inventory_item_id, :account_id, :quantity, :unit, :rate, :discount_amount, :taxable_amount, :tax_id, :tax_percentage, :tax_amount, :tds_rate, :tds_amount, :tcs_rate, :tcs_amount, :line_total)"
                    ),
                    {
                        'credit_note_id': str(credit_note_id),
                        'company_id': str(company_id),
                        'line_number': idx + 1,
                        'description': item.description,
                        'hsn_sac': item.hsn_sac,
                        'inventory_item_id': str(item.inventory_item_id) if item.inventory_item_id else None,
                        'account_id': str(item.account_id),
                        'quantity': float(item.quantity),
                        'unit': item.unit,
                        'rate': float(item.rate),
                        'discount_amount': float(item.discount_amount),
                        'taxable_amount': float(taxable),
                        'tax_id': str(item.tax_id) if item.tax_id else None,
                        'tax_percentage': float(item.tax_percentage),
                        'tax_amount': float(gst),
                        'tds_rate': float(item.tds_rate),
                        'tds_amount': float(tds),
                        'tcs_rate': float(item.tcs_rate),
                        'tcs_amount': float(tcs),
                        'line_total': float(total)
                    }
                )

        # Trigger DB update recalculation (even if items weren't changed, we flush to update grand total)
        updated_cn = conn.execute(
            text("SELECT grand_total, status FROM credit_notes WHERE credit_note_id = :id"),
            {"id": str(credit_note_id)}
        ).fetchone()
        new_total = updated_cn[0]
        new_status = updated_cn[1]

        # Update core transaction
        conn.execute(
            text("UPDATE transactions SET grand_total = :gt, status = :status, updated_at = now() WHERE transaction_id = :txn_id"),
            {"gt": float(new_total), "status": map_cn_status_to_txn_status(new_status), "txn_id": str(txn_id)}
        )

        # Balanced Ledger Posting if transitioned to open
        if curr_status == 'draft' and new_status == 'open':
            _post_ledger_entries_conn(conn, credit_note_id, company_id, user_id)

        # Log Activity
        conn.execute(
            text(
                "INSERT INTO credit_note_activity_logs (credit_note_id, company_id, activity_type, description, created_by) "
                "VALUES (:credit_note_id, :company_id, 'updated', :description, :created_by)"
            ),
            {
                'credit_note_id': str(credit_note_id),
                'company_id': str(company_id),
                'description': f"Credit Note {cn_number} updated by user.",
                'created_by': str(user_id)
            }
        )

        return _get_credit_note_conn(conn, credit_note_id, company_id)


def delete_credit_note(credit_note_id: UUID, company_id: UUID, user_id: UUID):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if credit_note_id not in MOCK_CREDIT_NOTES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found")
        MOCK_CREDIT_NOTES[credit_note_id]['is_deleted'] = True
        return

    with engine.begin() as conn:
        res = conn.execute(
            text("UPDATE credit_notes SET is_deleted = TRUE, status = 'cancelled', updated_at = now() WHERE credit_note_id = :id AND company_id = :cid AND is_deleted = FALSE RETURNING transaction_id"),
            {"id": str(credit_note_id), "cid": str(company_id)}
        ).fetchone()
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found or already deleted")
        
        # Soft delete items
        conn.execute(
            text("UPDATE credit_note_items SET is_deleted = TRUE, updated_at = now() WHERE credit_note_id = :id"),
            {"id": str(credit_note_id)}
        )

        # Cancel transaction
        conn.execute(
            text("UPDATE transactions SET status = 'cancelled', updated_at = now() WHERE transaction_id = :txn_id"),
            {"txn_id": str(res[0])}
        )


def list_credit_notes(company_id: UUID) -> list[CreditNoteResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        res = []
        for x in MOCK_CREDIT_NOTES.values():
            if x['company_id'] == company_id and not x.get('is_deleted', False):
                res.append(CreditNoteResponse(
                    **x,
                    items=[CreditNoteItemResponse(**item) for item in x.get('items', [])]
                ))
        return res

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT * FROM credit_notes WHERE company_id = :cid AND is_deleted = FALSE ORDER BY credit_note_date DESC, created_at DESC"),
            {"cid": str(company_id)}
        ).fetchall()

        results = []
        for r in rows:
            r_dict = dict(r._mapping) if hasattr(r, '_mapping') else dict(r)
            items = conn.execute(
                text("SELECT * FROM credit_note_items WHERE credit_note_id = :cnid AND is_deleted = FALSE ORDER BY line_number"),
                {"cnid": str(r_dict['credit_note_id'])}
            ).fetchall()
            r_dict['items'] = [dict(x._mapping) if hasattr(x, '_mapping') else dict(x) for x in items]
            results.append(CreditNoteResponse(**r_dict))
        return results


def apply_credit_note_to_invoice(credit_note_id: UUID, payload: CreditNoteApplyRequest, company_id: UUID, user_id: UUID) -> CreditNoteInvoiceMappingResponse:
    # Mock Apply
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if credit_note_id not in MOCK_CREDIT_NOTES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found")
        
        cn = MOCK_CREDIT_NOTES[credit_note_id]
        if cn['status'] not in ('open', 'partially_applied'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credit Note must be open to apply credits")

        # Import mock invoices from routes
        from routes.invoices import MOCK_INVOICES, get_or_create_mock_invoice
        invoice_id = payload.invoice_id
        
        # Verify invoice exists in mock or load it
        inv = get_or_create_mock_invoice(invoice_id)
        if inv.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice belongs to different company")

        if inv.billing_party_id != cn['billing_party_id']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing party mismatch")

        applied_amount = float(payload.applied_amount)
        if applied_amount > cn['remaining_balance']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Applied amount exceeds remaining credit balance")

        if applied_amount > inv.balance_due:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Applied amount exceeds outstanding invoice balance due")

        # Apply Balances
        cn['remaining_balance'] = round(cn['remaining_balance'] - applied_amount, 2)
        inv.paid_amount = round(inv.paid_amount + applied_amount, 2)
        inv.balance_due = round(inv.invoice_grand_total - inv.paid_amount, 2)

        # Status Adjustments
        if cn['remaining_balance'] <= 0:
            cn['status'] = 'applied'
        else:
            cn['status'] = 'partially_applied'

        if inv.balance_due <= 0:
            inv.status = 'paid'
        else:
            inv.status = 'partial'

        mapping = {
            "mapping_id": uuid4(),
            "company_id": company_id,
            "credit_note_id": credit_note_id,
            "invoice_id": invoice_id,
            "applied_amount": applied_amount,
            "applied_at": datetime.utcnow(),
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date,
            "invoice_grand_total": inv.invoice_grand_total,
            "invoice_balance_due": inv.balance_due
        }
        MOCK_MAPPINGS.append(mapping)

        MOCK_ACTIVITY_LOGS.append({
            "log_id": uuid4(),
            "credit_note_id": credit_note_id,
            "company_id": company_id,
            "activity_type": "applied",
            "description": f"Applied {applied_amount} credit to invoice {inv.invoice_number}.",
            "metadata": {"invoice_id": str(invoice_id)},
            "created_by": user_id,
            "created_at": datetime.utcnow()
        })

        return CreditNoteInvoiceMappingResponse(**mapping)

    # Database Mode
    with engine.begin() as conn:
        cn = conn.execute(
            text("SELECT remaining_balance, status, billing_party_id, transaction_id, credit_note_number FROM credit_notes WHERE credit_note_id = :id AND company_id = :cid AND is_deleted = FALSE"),
            {"id": str(credit_note_id), "cid": str(company_id)}
        ).fetchone()

        if not cn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found")

        cn_rem = cn[0]
        cn_status = cn[1]
        cn_party = cn[2]
        cn_txn_id = cn[3]
        cn_number = cn[4]

        if cn_status not in ('open', 'partially_applied'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credit Note must be open to apply credits")

        inv = conn.execute(
            text("SELECT balance_due, status, billing_party_id, invoice_number, currency, exchange_rate FROM invoices WHERE invoice_id = :id AND company_id = :cid AND is_deleted = FALSE"),
            {"id": str(payload.invoice_id), "cid": str(company_id)}
        ).fetchone()

        if not inv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

        inv_due = inv[0]
        inv_status = inv[1]
        inv_party = inv[2]
        inv_number = inv[3]
        inv_curr = inv[4]
        inv_rate = inv[5]

        if inv_party != cn_party:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing party mismatch between invoice and credit note")

        if payload.applied_amount > cn_rem:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Applied amount exceeds remaining credit balance")

        if payload.applied_amount > inv_due:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Applied amount exceeds invoice balance due")

        mapping_id = uuid4()
        # 1. Insert into credit_note_invoice_mappings
        conn.execute(
            text(
                "INSERT INTO credit_note_invoice_mappings (mapping_id, company_id, credit_note_id, invoice_id, applied_amount) "
                "VALUES (:mapping_id, :company_id, :credit_note_id, :invoice_id, :applied_amount)"
            ),
            {
                'mapping_id': str(mapping_id),
                'company_id': str(company_id),
                'credit_note_id': str(credit_note_id),
                'invoice_id': str(payload.invoice_id),
                'applied_amount': float(payload.applied_amount)
            }
        )

        # 2. Insert into invoice_payment_allocations to trigger auto balance updates on the invoice
        conn.execute(
            text(
                "INSERT INTO invoice_payment_allocations (allocation_id, company_id, payment_transaction_id, invoice_id, allocated_amount, currency, exchange_rate) "
                "VALUES (gen_random_uuid(), :company_id, :payment_transaction_id, :invoice_id, :allocated_amount, :currency, :exchange_rate)"
            ),
            {
                'company_id': str(company_id),
                'payment_transaction_id': str(cn_txn_id),
                'invoice_id': str(payload.invoice_id),
                'allocated_amount': float(payload.applied_amount),
                'currency': inv_curr,
                'exchange_rate': float(inv_rate)
            }
        )

        # 3. Log activity
        conn.execute(
            text(
                "INSERT INTO credit_note_activity_logs (credit_note_id, company_id, activity_type, description, metadata, created_by) "
                "VALUES (:credit_note_id, :company_id, 'applied', :description, :metadata, :created_by)"
            ),
            {
                'credit_note_id': str(credit_note_id),
                'company_id': str(company_id),
                'description': f"Applied {payload.applied_amount} credit from {cn_number} to invoice {inv_number}.",
                'metadata': json_dumps({"invoice_id": str(payload.invoice_id), "applied_amount": float(payload.applied_amount)}),
                'created_by': str(user_id)
            }
        )

        # Fetch the updated balance info for response
        updated_inv = conn.execute(
            text("SELECT balance_due, invoice_grand_total FROM invoices WHERE invoice_id = :id"),
            {"id": str(payload.invoice_id)}
        ).fetchone()

        return CreditNoteInvoiceMappingResponse(
            mapping_id=mapping_id,
            company_id=company_id,
            credit_note_id=credit_note_id,
            invoice_id=payload.invoice_id,
            applied_amount=float(payload.applied_amount),
            applied_at=datetime.utcnow(),
            invoice_number=inv_number,
            invoice_grand_total=float(updated_inv[1]),
            invoice_balance_due=float(updated_inv[0])
        )


def get_credit_note_activities(credit_note_id: UUID, company_id: UUID) -> list[CreditNoteActivityLogResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return [CreditNoteActivityLogResponse(**x) for x in MOCK_ACTIVITY_LOGS if x['credit_note_id'] == credit_note_id]

    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT * FROM credit_note_activity_logs WHERE credit_note_id = :cnid ORDER BY created_at DESC"),
            {"cnid": str(credit_note_id)}
        ).fetchall()
        return [CreditNoteActivityLogResponse(**(dict(r._mapping) if hasattr(r, '_mapping') else dict(r))) for r in rows]


def get_credit_note_mappings(credit_note_id: UUID, company_id: UUID) -> list[CreditNoteInvoiceMappingResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return [CreditNoteInvoiceMappingResponse(**x) for x in MOCK_MAPPINGS if x['credit_note_id'] == credit_note_id]

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT m.*, i.invoice_number, i.invoice_date, i.invoice_grand_total, i.balance_due "
                "FROM credit_note_invoice_mappings m "
                "JOIN invoices i ON m.invoice_id = i.invoice_id "
                "WHERE m.credit_note_id = :cnid"
            ),
            {"cnid": str(credit_note_id)}
        ).fetchall()
        return [CreditNoteInvoiceMappingResponse(**(dict(r._mapping) if hasattr(r, '_mapping') else dict(r))) for r in rows]


def get_credit_note_pdf(credit_note_number: str) -> bytes:
    """Generates standard receipt PDF bytes matching _minimal_invoice_pdf."""
    text_line = f"Credit Note {credit_note_number}"
    content = f"BT /F1 18 Tf 72 720 Td ({text_line}) Tj ET"
    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n")
    stream = content.encode("latin-1", errors="replace")
    objects.append(f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("ascii") + stream + b"\nendstream\nendobj\n")
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    xref_positions = [0]
    for obj in objects:
        xref_positions.append(out.tell())
        out.write(obj)
        out.write(b"\n")

    xref_start = out.tell()
    out.write(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for pos in xref_positions[1:]:
        out.write(f"{pos:010d} 00000 n \n".encode("ascii"))
    out.write(
        f"trailer<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("ascii")
    )
    return out.getvalue()


# ----------------------------------------------------
# PRIVATE DATABASE IMPLEMENTATION DETAILS
# ----------------------------------------------------

def _get_credit_note_conn(conn, credit_note_id: UUID, company_id: UUID) -> CreditNoteResponse:
    row = conn.execute(
        text("SELECT * FROM credit_notes WHERE credit_note_id = :id AND company_id = :cid AND is_deleted = FALSE"),
        {"id": str(credit_note_id), "cid": str(company_id)}
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit Note not found")

    r_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
    items = conn.execute(
        text("SELECT * FROM credit_note_items WHERE credit_note_id = :cnid AND is_deleted = FALSE ORDER BY line_number"),
        {"cnid": str(credit_note_id)}
    ).fetchall()
    r_dict['items'] = [dict(x._mapping) if hasattr(x, '_mapping') else dict(x) for x in items]

    return CreditNoteResponse(**r_dict)


def _post_ledger_entries_conn(conn, credit_note_id: UUID, company_id: UUID, user_id: UUID):
    # Fetch details
    cn = conn.execute(
        text("SELECT transaction_id, credit_note_number, credit_note_date, billing_party_id, subtotal, total_gst, total_tds, total_tcs, grand_total, accounts_receivable_id FROM credit_notes WHERE credit_note_id = :id"),
        {"id": str(credit_note_id)}
    ).fetchone()

    txn_id = cn[0]
    cn_number = cn[1]
    cn_date = cn[2]
    party_id = cn[3]
    subtotal = Decimal(str(cn[4]))
    total_gst = Decimal(str(cn[5]))
    total_tds = Decimal(str(cn[6]))
    total_tcs = Decimal(str(cn[7]))
    grand_total = Decimal(str(cn[8]))
    ar_account_id = cn[9]

    # Resolve AR Account (1200) if not in the header
    if not ar_account_id:
        ar_acc = conn.execute(
            text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '1200' AND is_active = TRUE"),
            {"company_id": str(company_id)}
        ).fetchone()
        ar_account_id = ar_acc[0] if ar_acc else None

    # Resolve GST Payable Account (2200)
    gst_acc = conn.execute(
        text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '2200' AND is_active = TRUE"),
        {"company_id": str(company_id)}
    ).fetchone()
    gst_account_id = gst_acc[0] if gst_acc else None

    # Resolve Sales Returns Account (4110)
    sales_ret_acc = conn.execute(
        text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '4110' AND is_active = TRUE"),
        {"company_id": str(company_id)}
    ).fetchone()

    if sales_ret_acc:
        sales_ret_account_id = sales_ret_acc[0]
    else:
        # Dynamically seed Sales Returns under '4000' (Income)
        income_parent = conn.execute(
            text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '4000'"),
            {"company_id": str(company_id)}
        ).fetchone()
        parent_id = income_parent[0] if income_parent else None

        sales_ret_account_id = uuid4()
        conn.execute(
            text(
                "INSERT INTO chart_of_accounts (account_id, company_id, account_code, account_name, account_type, parent_account_id, is_active, created_at, updated_at) "
                "VALUES (:account_id, :company_id, '4110', 'Sales Returns', 'income', :parent_account_id, TRUE, now(), now())"
            ),
            {
                'account_id': str(sales_ret_account_id),
                'company_id': str(company_id),
                'parent_account_id': str(parent_id) if parent_id else None
            }
        )

    # Balanced Journal Entry posting sequence
    journal_id = uuid4()
    journal_number = f"JRN-CN-{str(uuid4())[:8].upper()}"

    # Insert Draft Journal
    conn.execute(
        text(
            "INSERT INTO journal_entries (journal_id, company_id, journal_number, journal_type, journal_date, description, reference, transaction_id, status, created_by, updated_by, created_at, updated_at) "
            "VALUES (:journal_id, :company_id, :journal_number, 'reversal', :journal_date, :description, :reference, :transaction_id, 'draft', :created_by, :updated_by, now(), now())"
        ),
        {
            'journal_id': str(journal_id),
            'company_id': str(company_id),
            'journal_number': journal_number,
            'journal_date': cn_date,
            'description': f"Credit Note Posting - {cn_number}",
            'reference': cn_number,
            'transaction_id': str(txn_id),
            'created_by': str(user_id),
            'updated_by': str(user_id)
        }
    )

    # Debit: Sales Return Account (subtotal)
    conn.execute(
        text(
            "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
            "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'debit', :amount, :description, :party_id, now())"
        ),
        {
            'journal_id': str(journal_id),
            'company_id': str(company_id),
            'account_id': str(sales_ret_account_id),
            'amount': float(subtotal),
            'description': f"Debit Sales Returns for Credit Note {cn_number}",
            'party_id': str(party_id)
        }
    )

    # Debit: Output GST Reversal (total_gst)
    if total_gst > 0 and gst_account_id:
        conn.execute(
            text(
                "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'debit', :amount, :description, :party_id, now())"
            ),
            {
                'journal_id': str(journal_id),
                'company_id': str(company_id),
                'account_id': str(gst_account_id),
                'amount': float(total_gst),
                'description': f"Debit GST Reversal for Credit Note {cn_number}",
                'party_id': str(party_id)
            }
        )

    # Debit: TCS Reversal (total_tcs)
    if total_tcs > 0:
        # Re-use GST account or search liability
        conn.execute(
            text(
                "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'debit', :amount, :description, :party_id, now())"
            ),
            {
                'journal_id': str(journal_id),
                'company_id': str(company_id),
                'account_id': str(gst_account_id or sales_ret_account_id),
                'amount': float(total_tcs),
                'description': f"Debit TCS Reversal for Credit Note {cn_number}",
                'party_id': str(party_id)
            }
        )

    # Credit: Accounts Receivable (grand_total)
    if ar_account_id:
        conn.execute(
            text(
                "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'credit', :amount, :description, :party_id, now())"
            ),
            {
                'journal_id': str(journal_id),
                'company_id': str(company_id),
                'account_id': str(ar_account_id),
                'amount': float(grand_total),
                'description': f"Credit Accounts Receivable for Credit Note {cn_number}",
                'party_id': str(party_id)
            }
        )

    # Credit: TDS Reversal (total_tds)
    if total_tds > 0:
        conn.execute(
            text(
                "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'credit', :amount, :description, :party_id, now())"
            ),
            {
                'journal_id': str(journal_id),
                'company_id': str(company_id),
                'account_id': str(ar_account_id or gst_account_id),
                'amount': float(total_tds),
                'description': f"Credit TDS Reversal for Credit Note {cn_number}",
                'party_id': str(party_id)
            }
        )

    # Set Journal Status to posted
    conn.execute(
        text("UPDATE journal_entries SET status = 'posted', updated_at = now() WHERE journal_id = :id"),
        {"id": str(journal_id)}
    )


# ----------------------------------------------------
# JSON SERIALIZER HELPER
# ----------------------------------------------------
def json_dumps(data) -> str:
    import json
    return json.dumps(data, default=str)
