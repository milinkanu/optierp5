import os
import io
import json
from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import text
from decimal import Decimal

from utils.db_invoice import engine
from models.payments import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentAllocationResponse,
    PaymentAllocationCreate
)
from routes.invoices import MOCK_INVOICES, get_or_create_mock_invoice

# In-memory database for mock mode
MOCK_PAYMENTS: dict[UUID, dict] = {}

def get_next_payment_number(company_id: UUID) -> str:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        count = len(MOCK_PAYMENTS) + 1
        return f"PAY-{count:05d}"
    
    with engine.begin() as conn:
        conn.execute(
            text("SET LOCAL app.current_company = :company_id"),
            {'company_id': str(company_id)}
        )
        count = conn.execute(
            text("SELECT COALESCE(COUNT(*), 0) + 1 FROM transactions WHERE company_id = :company_id AND txn_type = 'payment_inbound'"),
            {'company_id': str(company_id)}
        ).scalar_one()
        return f"PAY-{count:05d}"

def create_payment(payload: PaymentCreateRequest, company_id: UUID, user_id: UUID) -> PaymentResponse:
    payment_id = uuid4()
    payment_number = get_next_payment_number(company_id)
    
    total_allocated = sum(Decimal(str(x.amount)) for x in payload.allocations)
    unused_balance = Decimal(str(payload.amount)) - total_allocated
    if unused_balance < 0:
        raise ValueError("Allocated amount cannot exceed the payment amount")
        
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        # Mock mode
        allocations_response = []
        for alloc in payload.allocations:
            inv = get_or_create_mock_invoice(alloc.invoice_id)
            inv.paid_amount = float(Decimal(str(inv.paid_amount)) + Decimal(str(alloc.amount)))
            inv.balance_due = float(Decimal(str(inv.invoice_grand_total)) - Decimal(str(inv.paid_amount)))
            
            if inv.balance_due <= 0.01:
                inv.status = 'paid'
                inv.balance_due = 0.0
            elif inv.paid_amount > 0:
                inv.status = 'partial'
                
            MOCK_INVOICES[alloc.invoice_id] = inv
            
            allocations_response.append(PaymentAllocationResponse(
                allocation_id=uuid4(),
                invoice_id=alloc.invoice_id,
                invoice_number=inv.invoice_number,
                allocated_amount=float(alloc.amount),
                allocated_at=datetime.utcnow()
            ))
            
        payment = {
            'payment_id': payment_id,
            'company_id': company_id,
            'payment_number': payment_number,
            'party_id': payload.party_id,
            'amount': float(payload.amount),
            'unused_balance': float(unused_balance),
            'payment_date': payload.payment_date,
            'payment_mode': payload.payment_mode,
            'settlement_bank_account_id': payload.settlement_bank_account_id or uuid4(),
            'reference_number': payload.reference_number,
            'bank_charges': float(payload.bank_charges),
            'notes': payload.notes,
            'status': 'posted',
            'created_at': datetime.utcnow(),
            'allocations': allocations_response
        }
        MOCK_PAYMENTS[payment_id] = payment
        return PaymentResponse(**payment)

    # Database Mode
    with engine.begin() as conn:
        # Set the session tenant context for Row Level Security
        conn.execute(
            text("SET LOCAL app.current_company = :company_id"),
            {'company_id': str(company_id)}
        )

        # Resolve settlement bank account if not provided
        settlement_bank_account_id = payload.settlement_bank_account_id
        if not settlement_bank_account_id:
            # Let's check payment mode to decide default account: Cash (1110) vs Bank (1100)
            code = '1110' if payload.payment_mode and payload.payment_mode.lower() == 'cash' else '1100'
            row = conn.execute(
                text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = :code"),
                {'company_id': str(company_id), 'code': code}
            ).fetchone()
            if row is not None:
                settlement_bank_account_id = row[0]
            else:
                # Fallback to any asset account
                settlement_bank_account_id = conn.execute(
                    text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_type = 'asset' LIMIT 1"),
                    {'company_id': str(company_id)}
                ).scalar()
                if not settlement_bank_account_id:
                    # ultimate fallback
                    settlement_bank_account_id = uuid4()

        # Create payment transaction
        meta_data = {
            'payment_mode': payload.payment_mode,
            'settlement_bank_account_id': str(settlement_bank_account_id),
            'reference_number': payload.reference_number,
            'bank_charges': float(payload.bank_charges),
            'notes': payload.notes,
            'unused_balance': float(unused_balance)
        }
        
        conn.execute(
            text(
                "INSERT INTO transactions (transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, party_id, subtotal, gst_breakdown, grand_total, status, meta, created_by, updated_by, created_at, updated_at) "
                "VALUES (:transaction_id, :company_id, 'payment_inbound', :txn_number, :txn_date, :fiscal_year, :period, :party_id, :subtotal, '{}'::jsonb, :grand_total, 'posted', :meta, :created_by, :updated_by, now(), now())"
            ),
            {
                'transaction_id': str(payment_id),
                'company_id': str(company_id),
                'txn_number': payment_number,
                'txn_date': payload.payment_date,
                'fiscal_year': payload.payment_date.strftime('%Y'),
                'period': payload.payment_date.strftime('%Y-%m'),
                'party_id': str(payload.party_id),
                'subtotal': float(payload.amount),
                'grand_total': float(payload.amount),
                'meta': json.dumps(meta_data),
                'created_by': str(user_id),
                'updated_by': str(user_id)
            }
        )
        
        # Create allocations
        for alloc in payload.allocations:
            conn.execute(
                text(
                    "INSERT INTO invoice_payment_allocations (allocation_id, company_id, payment_transaction_id, invoice_id, allocated_amount, currency, exchange_rate, allocated_at) "
                    "VALUES (gen_random_uuid(), :company_id, :payment_transaction_id, :invoice_id, :allocated_amount, 'INR', 1, now())"
                ),
                {
                    'company_id': str(company_id),
                    'payment_transaction_id': str(payment_id),
                    'invoice_id': str(alloc.invoice_id),
                    'allocated_amount': float(alloc.amount)
                }
            )
            
        # Get Accounts Receivable Account Code '1200'
        ar_account = conn.execute(
            text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '1200'"),
            {'company_id': str(company_id)}
        ).fetchone()
        
        if ar_account is None:
            # Seed default if somehow missing or fallback to any asset
            ar_account_id = conn.execute(
                text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_type = 'asset' LIMIT 1"),
                {'company_id': str(company_id)}
            ).scalar()
        else:
            ar_account_id = ar_account[0]
            
        if ar_account_id:
            # Balanced Journal Posting: Debit Cash/Bank Asset, Credit Accounts Receivable Asset
            # We first insert the journal entry with 'draft' status to avoid the BEFORE INSERT trigger checking lines
            journal_id = uuid4()
            journal_number = f"JRN-PAY-{str(uuid4())[:8].upper()}"
            conn.execute(
                text(
                    "INSERT INTO journal_entries (journal_id, company_id, journal_number, journal_type, journal_date, description, reference, transaction_id, status, created_by, updated_by, created_at, updated_at) "
                    "VALUES (:journal_id, :company_id, :journal_number, 'receipt', :journal_date, :description, :reference, :transaction_id, 'draft', :created_by, :updated_by, now(), now())"
                ),
                {
                    'journal_id': str(journal_id),
                    'company_id': str(company_id),
                    'journal_number': journal_number,
                    'journal_date': payload.payment_date,
                    'description': f"Payment Received - {payload.payment_mode} - Ref: {payload.reference_number or ''}",
                    'reference': payload.reference_number,
                    'transaction_id': str(payment_id),
                    'created_by': str(user_id),
                    'updated_by': str(user_id)
                }
            )
            
            # Debit Line: Bank/Cash account
            conn.execute(
                text(
                    "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                    "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'debit', :amount, :description, :party_id, now())"
                ),
                {
                    'journal_id': str(journal_id),
                    'company_id': str(company_id),
                    'account_id': str(settlement_bank_account_id),
                    'amount': float(payload.amount),
                    'description': f"Debit Bank/Cash for Payment {payment_number}",
                    'party_id': str(payload.party_id)
                }
            )
            
            # Credit Line: Accounts Receivable
            conn.execute(
                text(
                    "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at) "
                    "VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, 'credit', :amount, :description, :party_id, now())"
                ),
                {
                    'journal_id': str(journal_id),
                    'company_id': str(company_id),
                    'account_id': str(ar_account_id),
                    'amount': float(payload.amount),
                    'description': f"Credit Accounts Receivable for Payment {payment_number}",
                    'party_id': str(payload.party_id)
                }
            )

            # Update status to 'posted' (now the lines exist and balance, so the app.ensure_journal_balance trigger will succeed)
            conn.execute(
                text(
                    "UPDATE journal_entries SET status = 'posted', updated_at = now() WHERE journal_id = :journal_id"
                ),
                {'journal_id': str(journal_id)}
            )
            
    return get_payment(payment_id, company_id)

def get_payment(payment_id: UUID, company_id: UUID) -> PaymentResponse:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if payment_id not in MOCK_PAYMENTS:
            raise ValueError("Payment not found")
        return PaymentResponse(**MOCK_PAYMENTS[payment_id])
        
    with engine.begin() as conn:
        conn.execute(
            text("SET LOCAL app.current_company = :company_id"),
            {'company_id': str(company_id)}
        )
        txn = conn.execute(
            text("SELECT * FROM transactions WHERE transaction_id = :payment_id AND company_id = :company_id AND txn_type = 'payment_inbound'"),
            {'payment_id': str(payment_id), 'company_id': str(company_id)}
        ).fetchone()
        
        if txn is None:
            raise ValueError("Payment not found")
            
        txn_dict = dict(txn._mapping) if hasattr(txn, '_mapping') else dict(txn)
        meta = txn_dict.get('meta') or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
            
        allocations = conn.execute(
            text(
                "SELECT a.allocation_id, a.invoice_id, i.invoice_number, a.allocated_amount, a.allocated_at "
                "FROM invoice_payment_allocations a "
                "JOIN invoices i ON a.invoice_id = i.invoice_id "
                "WHERE a.payment_transaction_id = :payment_id AND a.company_id = :company_id"
            ),
            {'payment_id': str(payment_id), 'company_id': str(company_id)}
        ).fetchall()
        
        alloc_list = []
        for a in allocations:
            a_dict = dict(a._mapping) if hasattr(a, '_mapping') else dict(a)
            alloc_list.append(PaymentAllocationResponse(
                allocation_id=a_dict['allocation_id'],
                invoice_id=a_dict['invoice_id'],
                invoice_number=a_dict['invoice_number'],
                allocated_amount=float(a_dict['allocated_amount']),
                allocated_at=a_dict['allocated_at']
            ))
            
        return PaymentResponse(
            payment_id=txn_dict['transaction_id'],
            company_id=txn_dict['company_id'],
            payment_number=txn_dict['txn_number'],
            party_id=txn_dict['party_id'],
            amount=float(txn_dict['grand_total']),
            unused_balance=float(meta.get('unused_balance', 0.0)),
            payment_date=txn_dict['txn_date'],
            payment_mode=meta.get('payment_mode', 'Cash'),
            settlement_bank_account_id=UUID(meta['settlement_bank_account_id']) if meta.get('settlement_bank_account_id') else uuid4(),
            reference_number=meta.get('reference_number'),
            bank_charges=float(meta.get('bank_charges', 0.0)),
            notes=meta.get('notes'),
            status=txn_dict['status'],
            created_at=txn_dict['created_at'],
            allocations=alloc_list
        )

def list_payments(company_id: UUID) -> list[PaymentResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return [PaymentResponse(**x) for x in MOCK_PAYMENTS.values() if x['company_id'] == company_id]
        
    with engine.begin() as conn:
        conn.execute(
            text("SET LOCAL app.current_company = :company_id"),
            {'company_id': str(company_id)}
        )
        txns = conn.execute(
            text("SELECT transaction_id FROM transactions WHERE company_id = :company_id AND txn_type = 'payment_inbound' ORDER BY created_at DESC"),
            {'company_id': str(company_id)}
        ).fetchall()
        
        results = []
        for t in txns:
            results.append(get_payment(t[0], company_id))
        return results

def get_invoice_payments(invoice_id: UUID, company_id: UUID) -> list[PaymentAllocationResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        # Gather mock allocations
        alloc_list = []
        for p in MOCK_PAYMENTS.values():
            if p['company_id'] == company_id:
                for a in p.get('allocations', []):
                    if a.invoice_id == invoice_id:
                        alloc_list.append(a)
        return alloc_list
        
    with engine.begin() as conn:
        conn.execute(
            text("SET LOCAL app.current_company = :company_id"),
            {'company_id': str(company_id)}
        )
        allocations = conn.execute(
            text(
                "SELECT a.allocation_id, a.invoice_id, i.invoice_number, a.allocated_amount, a.allocated_at "
                "FROM invoice_payment_allocations a "
                "JOIN invoices i ON a.invoice_id = i.invoice_id "
                "WHERE a.invoice_id = :invoice_id AND a.company_id = :company_id"
            ),
            {'invoice_id': str(invoice_id), 'company_id': str(company_id)}
        ).fetchall()
        
        alloc_list = []
        for a in allocations:
            a_dict = dict(a._mapping) if hasattr(a, '_mapping') else dict(a)
            alloc_list.append(PaymentAllocationResponse(
                allocation_id=a_dict['allocation_id'],
                invoice_id=a_dict['invoice_id'],
                invoice_number=a_dict['invoice_number'],
                allocated_amount=float(a_dict['allocated_amount']),
                allocated_at=a_dict['allocated_at']
            ))
        return alloc_list

def get_payment_receipt_pdf(payment_number: str) -> bytes:
    """Renders a standard-compliant minimal pure-Python PDF for Payment Receipts."""
    text_line = f"Payment Receipt {payment_number}"
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
