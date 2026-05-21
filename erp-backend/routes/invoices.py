from datetime import datetime, date
from uuid import UUID, uuid4
import json
import os
import io

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import text
from decimal import Decimal

from models.invoices import InvoiceCreateRequest, InvoiceResponse, PaymentAllocationRequest, InvoiceItemResponse
from utils.auth import TenantContext, get_current_context
from utils.db_invoice import engine

router = APIRouter(prefix="/invoices", tags=["invoices"])

# Shared in-memory mock invoices database for DB-bypass mode
MOCK_INVOICES: dict[UUID, InvoiceResponse] = {}


def get_or_create_mock_invoice(invoice_id: UUID) -> InvoiceResponse:
    if invoice_id in MOCK_INVOICES:
        return MOCK_INVOICES[invoice_id]

    # Prepopulate default or generate a beautiful realistic mock invoice on-the-fly
    items = [
        InvoiceItemResponse(
            invoice_item_id=uuid4(),
            invoice_id=invoice_id,
            company_id=UUID("00000000-0000-0000-0000-000000000000"),
            line_number=1,
            description="Pens",
            hsn_sac="9608",
            account_id=uuid4(),
            quantity=1.0,
            unit_price=100.0,
            discount_amount=20.0,
            taxable_amount=80.0,
            gst_rate=0.0,
            gst_amount=0.0,
            tds_rate=10.0,
            tds_amount=8.0,
            tcs_rate=0.0,
            tcs_amount=0.0,
            total_amount=72.0
        )
    ]

    # Matching standard default INV-000001
    inv = InvoiceResponse(
        invoice_id=invoice_id,
        invoice_number="INV-000001" if str(invoice_id).startswith("00000000") else f"INV-2026-{str(uuid4())[:8].upper()}",
        invoice_type="sales_invoice",
        invoice_date=datetime(2026, 5, 11).date(),
        due_date=datetime(2026, 5, 11).date(),
        billing_party_id=UUID("ce3ba27e-128a-45bd-b65d-9c7f1db8816c"),  # Milin Kanu in mock contacts
        shipping_party_id=UUID("ce3ba27e-128a-45bd-b65d-9c7f1db8816c"),
        order_number="SO-00001",
        salesperson_id=None,
        subject="Office supplies delivery",
        customer_notes="Thanks for your business.",
        terms_and_conditions="Due on Receipt",
        status="overdue",
        invoice_subtotal=100.0,
        invoice_total_gst=0.0,
        invoice_total_tds=8.0,
        invoice_total_tcs=0.0,
        invoice_grand_total=72.0,
        paid_amount=0.0,
        balance_due=72.0,
        currency="INR",
        created_at=datetime(2026, 5, 11, 10, 0, 0),
        items=items
    )
    MOCK_INVOICES[invoice_id] = inv
    return inv


def build_invoice_response(payload: InvoiceCreateRequest, invoice_id: UUID | None = None, status_val: str = 'draft') -> InvoiceResponse:
    inv_id = invoice_id or uuid4()
    invoice_number = f"INV-2026-{str(uuid4())[:8].upper()}"
    
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

        items.append(InvoiceItemResponse(
            invoice_item_id=uuid4(),
            invoice_id=inv_id,
            company_id=UUID("00000000-0000-0000-0000-000000000000"),
            line_number=idx + 1,
            description=item.description,
            hsn_sac=item.hsn_sac or "0000",
            account_id=item.account_id or uuid4(),
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
            total_amount=float(total_amount)
        ))

    inv = InvoiceResponse(
        invoice_id=inv_id,
        invoice_number=invoice_number,
        invoice_type=payload.invoice_type,
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        billing_party_id=payload.billing_party_id,
        shipping_party_id=payload.shipping_party_id,
        order_number=payload.order_number,
        salesperson_id=payload.salesperson_id,
        subject=payload.subject,
        customer_notes=payload.customer_notes,
        terms_and_conditions=payload.terms_and_conditions,
        status=status_val,
        invoice_subtotal=float(subtotal),
        invoice_total_gst=float(total_gst),
        invoice_total_tds=float(total_tds),
        invoice_total_tcs=float(total_tcs),
        invoice_grand_total=float(grand_total),
        paid_amount=0.0,
        balance_due=float(grand_total),
        currency=payload.currency,
        created_at=datetime.utcnow(),
        items=items
    )
    MOCK_INVOICES[inv_id] = inv
    return inv


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

    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
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
            invoice_date=payload.invoice_date,
            due_date=payload.due_date,
            billing_party_id=payload.billing_party_id,
            shipping_party_id=payload.shipping_party_id,
            status='draft',
            invoice_subtotal=subtotal,
            invoice_total_gst=total_gst,
            invoice_total_tds=total_tds,
            invoice_total_tcs=total_tcs,
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
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        inv = get_or_create_mock_invoice(invoice_id)
        if inv.status != 'draft':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Only draft invoices can be posted')
        inv.status = 'posted'
        return inv

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

        return await get_invoice(invoice_id=invoice_id, current_context=current_context)


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    current_context: TenantContext = Depends(get_current_context),
    page: int = 1,
    limit: int = 25,
    invoice_type: str | None = None,
):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if not MOCK_INVOICES:
            get_or_create_mock_invoice(UUID("00000000-0000-0000-0000-000000000001"))
        
        results = list(MOCK_INVOICES.values())
        if invoice_type:
            results = [x for x in results if x.invoice_type == invoice_type]
        results.sort(key=lambda x: x.created_at, reverse=True)
        offset = (page - 1) * limit
        return results[offset : offset + limit]

    offset = (page - 1) * limit
    with engine.begin() as conn:
        params: dict = {"company_id": str(current_context.company_id), "limit": limit, "offset": offset}
        where = "company_id = :company_id AND is_deleted = FALSE"
        if invoice_type:
            where += " AND invoice_type = :invoice_type"
            params["invoice_type"] = invoice_type

        rows = conn.execute(
            text(
                f"SELECT invoice_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, "
                f"currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_total_tds, invoice_total_tcs, "
                f"invoice_grand_total, paid_amount, balance_due, status, created_at, meta "
                f"FROM invoices WHERE {where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            ),
            params,
        ).fetchall()
        
        result = []
        for r in rows:
            d = dict(r._mapping) if hasattr(r, "_mapping") else dict(r)
            meta = d.get("meta") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            
            d["order_number"] = meta.get("order_number")
            d["salesperson_id"] = meta.get("salesperson_id")
            d["subject"] = meta.get("subject")
            d["customer_notes"] = meta.get("customer_notes")
            d["terms_and_conditions"] = meta.get("terms_and_conditions")
            d["invoice_subtotal"] = float(d["invoice_subtotal"])
            d["invoice_total_gst"] = float(d["invoice_total_gst"])
            d["invoice_total_tds"] = float(d["invoice_total_tds"])
            d["invoice_total_tcs"] = float(d["invoice_total_tcs"])
            d["invoice_grand_total"] = float(d["invoice_grand_total"])
            d["paid_amount"] = float(d["paid_amount"])
            d["balance_due"] = float(d["balance_due"])
            d["exchange_rate"] = float(d["exchange_rate"])
            result.append(InvoiceResponse(**d))
        return result


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return get_or_create_mock_invoice(invoice_id)

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT invoice_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, "
                "currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_total_tds, invoice_total_tcs, "
                "invoice_grand_total, paid_amount, balance_due, status, created_at, meta "
                "FROM invoices WHERE invoice_id = :invoice_id AND company_id = :company_id AND is_deleted = FALSE"
            ),
            {"invoice_id": str(invoice_id), "company_id": str(current_context.company_id)},
        ).fetchone()
        
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        
        d = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
        meta = d.get("meta") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        
        d["order_number"] = meta.get("order_number")
        d["salesperson_id"] = meta.get("salesperson_id")
        d["subject"] = meta.get("subject")
        d["customer_notes"] = meta.get("customer_notes")
        d["terms_and_conditions"] = meta.get("terms_and_conditions")
        d["invoice_subtotal"] = float(d["invoice_subtotal"])
        d["invoice_total_gst"] = float(d["invoice_total_gst"])
        d["invoice_total_tds"] = float(d["invoice_total_tds"])
        d["invoice_total_tcs"] = float(d["invoice_total_tcs"])
        d["invoice_grand_total"] = float(d["invoice_grand_total"])
        d["paid_amount"] = float(d["paid_amount"])
        d["balance_due"] = float(d["balance_due"])
        d["exchange_rate"] = float(d["exchange_rate"])

        # Query all items
        item_rows = conn.execute(
            text(
                "SELECT invoice_item_id, invoice_id, company_id, line_number, description, hsn_sac, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, total_amount "
                "FROM invoice_items WHERE invoice_id = :invoice_id AND company_id = :company_id ORDER BY line_number"
            ),
            {"invoice_id": str(invoice_id), "company_id": str(current_context.company_id)},
        ).fetchall()
        
        items = []
        for r in item_rows:
            idict = dict(r._mapping) if hasattr(r, "_mapping") else dict(r)
            idict["quantity"] = float(idict["quantity"])
            idict["unit_price"] = float(idict["unit_price"])
            idict["discount_amount"] = float(idict["discount_amount"])
            idict["taxable_amount"] = float(idict["taxable_amount"])
            idict["gst_rate"] = float(idict["gst_rate"])
            idict["gst_amount"] = float(idict["gst_amount"])
            idict["tds_rate"] = float(idict["tds_rate"])
            idict["tds_amount"] = float(idict["tds_amount"])
            idict["tcs_rate"] = float(idict["tcs_rate"])
            idict["tcs_amount"] = float(idict["tcs_amount"])
            idict["total_amount"] = float(idict["total_amount"])
            items.append(idict)
            
        d["items"] = items
        return InvoiceResponse(**d)


@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if invoice_id in MOCK_INVOICES:
            del MOCK_INVOICES[invoice_id]
            return {"success": True}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

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
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        inv = get_or_create_mock_invoice(invoice_id)
        pdf_bytes = _minimal_invoice_pdf(inv.invoice_number)
        headers = {"Content-Disposition": f'inline; filename="{inv.invoice_number}.pdf"'}
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

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
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        inv = get_or_create_mock_invoice(invoice_id)
        if inv.status not in ('posted', 'partial'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invoice must be posted before payment allocation')
        
        allocated = float(payload.allocated_amount)
        inv.paid_amount = round(inv.paid_amount + allocated, 2)
        inv.balance_due = round(max(0.0, inv.invoice_grand_total - inv.paid_amount), 2)
        inv.status = 'paid' if inv.balance_due <= 0 else 'partial'
        return inv

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

        return await get_invoice(invoice_id=invoice_id, current_context=current_context)
