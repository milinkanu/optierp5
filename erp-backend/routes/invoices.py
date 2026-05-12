from datetime import datetime
from uuid import UUID, uuid4
import json
import os
import io

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import text
from decimal import Decimal

from models.invoices import InvoiceCreateRequest, InvoiceResponse, PaymentAllocationRequest
from utils.auth import TenantContext, get_current_context
from utils.db_invoice import engine

router = APIRouter(prefix="/invoices", tags=["invoices"])


def build_invoice_response(payload: InvoiceCreateRequest) -> InvoiceResponse:
    invoice_id = uuid4()
    invoice_number = f"{payload.invoice_type[:3].upper()}-{payload.invoice_date.year}-{str(uuid4())[:8]}"
    grand_total = Decimal('0')

    for item in payload.items:
        taxable_amount = item.quantity * item.unit_price - item.discount_amount
        gst_amount = taxable_amount * item.gst_rate / Decimal('100')
        tds_amount = taxable_amount * item.tds_rate / Decimal('100')
        tcs_amount = taxable_amount * item.tcs_rate / Decimal('100')
        grand_total += taxable_amount + gst_amount + tcs_amount - tds_amount

    return InvoiceResponse(
        invoice_id=invoice_id,
        invoice_number=invoice_number,
        invoice_type=payload.invoice_type,
        status='draft',
        invoice_grand_total=float(grand_total),
        paid_amount=0.0,
        balance_due=float(grand_total),
        created_at=datetime.utcnow()
    )


@router.post("", response_model=InvoiceResponse)
async def create_invoice(
    payload: InvoiceCreateRequest,
    idempotency_key: UUID = Header(..., alias='Idempotency-Key'),
    current_context: TenantContext = Depends(get_current_context)
):
    if payload.invoice_type not in ('sales_invoice', 'purchase_invoice'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid invoice type')
    if len(payload.items) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invoice must contain at least one line item')

    if os.getenv('FINOPS_USE_DATABASE', '').lower() != 'true':
        return build_invoice_response(payload)

    with engine.begin() as conn:
        existing = conn.execute(
            text('SELECT response_payload FROM api_idempotency_keys WHERE idempotency_key = :key AND company_id = :company_id'),
            {'key': str(idempotency_key), 'company_id': str(current_context.company_id)}
        ).fetchone()
        if existing is not None:
            cached_response = dict(existing._mapping) if hasattr(existing, '_mapping') else dict(existing)
            response_payload = cached_response.get('response_payload', {})
            response_payload['created_at'] = datetime.fromisoformat(response_payload['created_at']) if isinstance(response_payload.get('created_at'), str) else response_payload.get('created_at')
            return InvoiceResponse(**response_payload)

        transaction_id = uuid4()
        invoice_id = uuid4()
        invoice_number = conn.execute(
            text('SELECT app.next_invoice_number(:company_id, :invoice_type)'),
            {'company_id': str(current_context.company_id), 'invoice_type': payload.invoice_type}
        ).scalar_one()

        subtotal = 0
        total_gst = 0
        total_tds = 0
        total_tcs = 0
        grand_total = 0

        for item in payload.items:
            taxable_amount = float(item.quantity) * float(item.unit_price) - float(item.discount_amount)
            gst_amount = round(taxable_amount * float(item.gst_rate) / 100, 2)
            tds_amount = round(taxable_amount * float(item.tds_rate) / 100, 2)
            tcs_amount = round(taxable_amount * float(item.tcs_rate) / 100, 2)
            total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount
            subtotal += taxable_amount
            total_gst += gst_amount
            total_tds += tds_amount
            total_tcs += tcs_amount
            grand_total += total_amount

        conn.execute(
            text(
                'INSERT INTO transactions (transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, subtotal, gst_breakdown, grand_total, status, currency, exchange_rate, created_by, updated_by, created_at, updated_at, idempotency_key) '
                'VALUES (:transaction_id, :company_id, :txn_type, :txn_number, :txn_date, :fiscal_year, :period, :subtotal, :gst_breakdown, :grand_total, :status, :currency, :exchange_rate, :created_by, :updated_by, :created_at, :updated_at, :idempotency_key)'
            ),
            {
                'transaction_id': str(transaction_id),
                'company_id': str(current_context.company_id),
                'txn_type': payload.invoice_type,
                'txn_number': invoice_number,
                'txn_date': payload.invoice_date,
                'fiscal_year': payload.invoice_date.strftime('%Y-%m'),
                'period': payload.invoice_date.strftime('%Y-%m'),
                'subtotal': subtotal,
                'gst_breakdown': {'gst_total': total_gst, 'tds_total': total_tds, 'tcs_total': total_tcs},
                'grand_total': grand_total,
                'status': 'draft',
                'currency': payload.currency,
                'exchange_rate': payload.exchange_rate,
                'created_by': str(current_context.user_id),
                'updated_by': str(current_context.user_id),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'idempotency_key': str(idempotency_key)
            }
        )

        conn.execute(
            text(
                'INSERT INTO invoices (invoice_id, company_id, transaction_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_total_tds, invoice_total_tcs, invoice_grand_total, status, created_by, updated_by, created_at, updated_at, meta) '
                'VALUES (:invoice_id, :company_id, :transaction_id, :invoice_number, :invoice_type, :invoice_date, :due_date, :billing_party_id, :shipping_party_id, :currency, :exchange_rate, :invoice_subtotal, :invoice_total_gst, :invoice_total_tds, :invoice_total_tcs, :invoice_grand_total, :status, :created_by, :updated_by, :created_at, :updated_at, :meta)'
            ),
            {
                'invoice_id': str(invoice_id),
                'company_id': str(current_context.company_id),
                'transaction_id': str(transaction_id),
                'invoice_number': invoice_number,
                'invoice_type': payload.invoice_type,
                'invoice_date': payload.invoice_date,
                'due_date': payload.due_date,
                'billing_party_id': str(payload.billing_party_id) if payload.billing_party_id else None,
                'shipping_party_id': str(payload.shipping_party_id) if payload.shipping_party_id else None,
                'currency': payload.currency,
                'exchange_rate': payload.exchange_rate,
                'invoice_subtotal': subtotal,
                'invoice_total_gst': total_gst,
                'invoice_total_tds': total_tds,
                'invoice_total_tcs': total_tcs,
                'invoice_grand_total': grand_total,
                'status': 'draft',
                'created_by': str(current_context.user_id),
                'updated_by': str(current_context.user_id),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'meta': payload.meta
            }
        )

        line_number = 1
        for item in payload.items:
            taxable_amount = float(item.quantity) * float(item.unit_price) - float(item.discount_amount)
            gst_amount = round(taxable_amount * float(item.gst_rate) / 100, 2)
            tds_amount = round(taxable_amount * float(item.tds_rate) / 100, 2)
            tcs_amount = round(taxable_amount * float(item.tcs_rate) / 100, 2)
            total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount
            item_account_id = item.account_id or uuid4()
            item_hsn_sac = item.hsn_sac or "0000"

            conn.execute(
                text(
                    'INSERT INTO invoice_items (invoice_item_id, invoice_id, company_id, line_number, description, hsn_sac, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, total_amount, created_at, updated_at) '
                    'VALUES (gen_random_uuid(), :invoice_id, :company_id, :line_number, :description, :hsn_sac, :account_id, :quantity, :unit_price, :discount_amount, :taxable_amount, :gst_rate, :gst_amount, :tds_rate, :tds_amount, :tcs_rate, :tcs_amount, :total_amount, :created_at, :updated_at)'
                ),
                {
                    'invoice_id': str(invoice_id),
                    'company_id': str(current_context.company_id),
                    'line_number': line_number,
                    'description': item.description,
                    'hsn_sac': item_hsn_sac,
                    'account_id': str(item_account_id),
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'discount_amount': item.discount_amount,
                    'taxable_amount': taxable_amount,
                    'gst_rate': item.gst_rate,
                    'gst_amount': gst_amount,
                    'tds_rate': item.tds_rate,
                    'tds_amount': tds_amount,
                    'tcs_rate': item.tcs_rate,
                    'tcs_amount': tcs_amount,
                    'total_amount': total_amount,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            )
            line_number += 1

        created_at_dt = datetime.utcnow()
        response = {
            'invoice_id': str(invoice_id),
            'invoice_number': invoice_number,
            'invoice_type': payload.invoice_type,
            'status': 'draft',
            'invoice_grand_total': float(grand_total),
            'paid_amount': 0.0,
            'balance_due': float(grand_total),
            'created_at': created_at_dt.isoformat()
        }

        conn.execute(
            text(
                'INSERT INTO api_idempotency_keys (idempotency_key, company_id, user_id, endpoint, request_hash, response_payload, created_at, last_used_at) '
                'VALUES (:key, :company_id, :user_id, :endpoint, :request_hash, :response_payload, :created_at, :last_used_at)'
            ),
            {
                'key': str(idempotency_key),
                'company_id': str(current_context.company_id),
                'user_id': str(current_context.user_id),
                'endpoint': '/invoices',
                'request_hash': str(idempotency_key),
                'response_payload': json.loads(json.dumps(response, default=str)),
                'created_at': created_at_dt,
                'last_used_at': created_at_dt
            }
        )

        return InvoiceResponse(
            invoice_id=invoice_id,
            invoice_number=invoice_number,
            invoice_type=payload.invoice_type,
            status='draft',
            invoice_grand_total=grand_total,
            paid_amount=0,
            balance_due=grand_total,
            created_at=created_at_dt
        )


@router.post("/{invoice_id}/post", response_model=InvoiceResponse)
async def post_invoice(
    invoice_id: UUID,
    idempotency_key: UUID = Header(..., alias='Idempotency-Key'),
    current_context: TenantContext = Depends(get_current_context)
):
    with engine.begin() as conn:
        invoice = conn.execute(
            text('SELECT invoice_id, invoice_number, invoice_type, invoice_grand_total, paid_amount, balance_due, status FROM invoices WHERE invoice_id = :invoice_id AND company_id = :company_id AND is_deleted = FALSE'),
            {'invoice_id': str(invoice_id), 'company_id': str(current_context.company_id)}
        ).fetchone()
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invoice not found')
        invoice_dict = dict(invoice._mapping) if hasattr(invoice, '_mapping') else dict(invoice)
        if invoice_dict.get('status') != 'draft':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Only draft invoices can be posted')

        conn.execute(
            text('UPDATE invoices SET status = :status, updated_at = :updated_at WHERE invoice_id = :invoice_id'),
            {'status': 'posted', 'updated_at': datetime.utcnow(), 'invoice_id': str(invoice_id)}
        )

        updated_invoice = conn.execute(
            text('SELECT invoice_id, invoice_number, invoice_type, invoice_grand_total, paid_amount, balance_due, status, created_at FROM invoices WHERE invoice_id = :invoice_id AND is_deleted = FALSE'),
            {'invoice_id': str(invoice_id)}
        ).fetchone()
        if updated_invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invoice not found after posting')
        invoice_dict = dict(updated_invoice._mapping) if hasattr(updated_invoice, '_mapping') else dict(updated_invoice)
        return InvoiceResponse(**invoice_dict)


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    current_context: TenantContext = Depends(get_current_context),
    page: int = 1,
    limit: int = 25,
    invoice_type: str | None = None,
):
    offset = (page - 1) * limit
    with engine.begin() as conn:
        params: dict = {"company_id": str(current_context.company_id), "limit": limit, "offset": offset}
        where = "company_id = :company_id AND is_deleted = FALSE"
        if invoice_type:
            where += " AND invoice_type = :invoice_type"
            params["invoice_type"] = invoice_type

        rows = conn.execute(
            text(
                f"SELECT invoice_id, invoice_number, invoice_type, status, invoice_grand_total, paid_amount, balance_due, created_at "
                f"FROM invoices WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r._mapping) if hasattr(r, "_mapping") else dict(r)
            result.append(InvoiceResponse(**d))
        return result


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT invoice_id, invoice_number, invoice_type, status, invoice_grand_total, paid_amount, balance_due, created_at "
                "FROM invoices WHERE invoice_id = :invoice_id AND company_id = :company_id AND is_deleted = FALSE"
            ),
            {"invoice_id": str(invoice_id), "company_id": str(current_context.company_id)},
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
        return InvoiceResponse(**d)


@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    with engine.begin() as conn:
        updated = conn.execute(
            text(
                "UPDATE invoices SET is_deleted = TRUE, updated_at = :updated_at "
                "WHERE invoice_id = :invoice_id AND company_id = :company_id AND is_deleted = FALSE"
            ),
            {"invoice_id": str(invoice_id), "company_id": str(current_context.company_id), "updated_at": datetime.utcnow()},
        ).rowcount
        if updated == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return {"success": True}


def _minimal_invoice_pdf(invoice_number: str) -> bytes:
    # Minimal valid PDF with a single line of text. No external dependencies.
    text_line = f"Invoice {invoice_number}"
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


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT invoice_number FROM invoices "
                "WHERE invoice_id = :invoice_id AND company_id = :company_id AND is_deleted = FALSE"
            ),
            {"invoice_id": str(invoice_id), "company_id": str(current_context.company_id)},
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        invoice_number = (dict(row._mapping) if hasattr(row, "_mapping") else dict(row))["invoice_number"]

    pdf_bytes = _minimal_invoice_pdf(invoice_number)
    headers = {"Content-Disposition": f'inline; filename="{invoice_number}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/{invoice_id}/payments", response_model=InvoiceResponse)
async def allocate_payment(
    invoice_id: UUID,
    payload: PaymentAllocationRequest,
    idempotency_key: UUID = Header(..., alias='Idempotency-Key'),
    current_context: TenantContext = Depends(get_current_context)
):
    with engine.begin() as conn:
        invoice = conn.execute(
            text('SELECT invoice_grand_total, paid_amount, status FROM invoices WHERE invoice_id = :invoice_id AND company_id = :company_id'),
            {'invoice_id': str(invoice_id), 'company_id': str(current_context.company_id)}
        ).fetchone()
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invoice not found')
        invoice_dict = dict(invoice._mapping) if hasattr(invoice, '_mapping') else dict(invoice)
        if invoice_dict.get('status') not in ('posted', 'partial'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invoice must be posted before payment allocation')

        conn.execute(
            text('INSERT INTO invoice_payment_allocations (allocation_id, company_id, payment_transaction_id, invoice_id, allocated_amount, currency, exchange_rate, allocated_at) VALUES (gen_random_uuid(), :company_id, :payment_transaction_id, :invoice_id, :allocated_amount, :currency, :exchange_rate, :allocated_at)'),
            {
                'company_id': str(current_context.company_id),
                'payment_transaction_id': str(payload.payment_transaction_id),
                'invoice_id': str(invoice_id),
                'allocated_amount': payload.allocated_amount,
                'currency': payload.currency,
                'exchange_rate': payload.exchange_rate,
                'allocated_at': datetime.utcnow()
            }
        )

        updated = conn.execute(
            text('SELECT invoice_id, invoice_number, invoice_type, invoice_grand_total, paid_amount, balance_due, status, created_at FROM invoices WHERE invoice_id = :invoice_id'),
            {'invoice_id': str(invoice_id)}
        ).fetchone()
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invoice not found after payment allocation')
        invoice_dict = dict(updated._mapping) if hasattr(updated, '_mapping') else dict(updated)
        return InvoiceResponse(**invoice_dict)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    with engine.connect() as conn:
        invoice = conn.execute(
            text('SELECT invoice_id, invoice_number, invoice_type, invoice_grand_total, paid_amount, balance_due, status, created_at FROM invoices WHERE invoice_id = :invoice_id AND company_id = :company_id'),
            {'invoice_id': str(invoice_id), 'company_id': str(current_context.company_id)}
        ).fetchone()
        if invoice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invoice not found')
        return InvoiceResponse(**dict(invoice._mapping) if hasattr(invoice, '_mapping') else dict(invoice))
