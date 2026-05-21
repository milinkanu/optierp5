import os
import io
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy import text
from utils.db_invoice import engine
from models.delivery_challans import DeliveryChallanCreateRequest, DeliveryChallanResponse, DeliveryChallanItemResponse
from models.invoices import InvoiceResponse, InvoiceItemResponse
from routes.invoices import MOCK_INVOICES, get_or_create_mock_invoice
from decimal import Decimal

# In-memory database for mock mode
MOCK_DELIVERY_CHALLANS: dict[UUID, dict] = {}

def get_next_challan_number(company_id: UUID) -> str:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        count = len(MOCK_DELIVERY_CHALLANS) + 1
        return f"DC-{count:05d}"
    
    with engine.begin() as conn:
        count = conn.execute(
            text('SELECT COALESCE(COUNT(*), 0) + 1 FROM delivery_challans WHERE company_id = :company_id'),
            {'company_id': str(company_id)}
        ).scalar_one()
        return f"DC-{count:05d}"

def create_delivery_challan(payload: DeliveryChallanCreateRequest, company_id: UUID, user_id: UUID) -> DeliveryChallanResponse:
    challan_id = uuid4()
    challan_number = get_next_challan_number(company_id)
    
    subtotal = Decimal('0')
    total_gst = Decimal('0')
    grand_total = Decimal('0')
    items = []
    
    for idx, item in enumerate(payload.items):
        taxable_amount = item.quantity * item.unit_price - item.discount_amount
        gst_amount = taxable_amount * item.gst_rate / Decimal('100')
        total_amount = taxable_amount + gst_amount
        
        subtotal += taxable_amount
        total_gst += gst_amount
        grand_total += total_amount
        
        items.append({
            'challan_item_id': uuid4(),
            'delivery_challan_id': challan_id,
            'company_id': company_id,
            'line_number': idx + 1,
            'description': item.description,
            'hsn_sac': item.hsn_sac,
            'inventory_item_id': item.inventory_item_id,
            'account_id': item.account_id,
            'quantity': float(item.quantity),
            'unit_price': float(item.unit_price),
            'discount_amount': float(item.discount_amount),
            'taxable_amount': float(taxable_amount),
            'gst_rate': float(item.gst_rate),
            'gst_amount': float(gst_amount),
            'total_amount': float(total_amount)
        })

    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        challan = {
            'delivery_challan_id': challan_id,
            'company_id': company_id,
            'challan_number': challan_number,
            'challan_type': payload.challan_type,
            'challan_date': payload.challan_date,
            'billing_party_id': payload.billing_party_id,
            'shipping_party_id': payload.shipping_party_id,
            'reference_number': payload.reference_number,
            'status': 'open',
            'currency': payload.currency,
            'exchange_rate': float(payload.exchange_rate),
            'subtotal': float(subtotal),
            'total_gst': float(total_gst),
            'grand_total': float(grand_total),
            'transport_mode': payload.transport_mode,
            'vehicle_number': payload.vehicle_number,
            'place_of_supply': payload.place_of_supply,
            'customer_notes': payload.customer_notes,
            'terms_and_conditions': payload.terms_and_conditions,
            'created_by': user_id,
            'updated_by': user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'items': [DeliveryChallanItemResponse(**x) for x in items]
        }
        MOCK_DELIVERY_CHALLANS[challan_id] = challan
        return DeliveryChallanResponse(**challan)

    # Database Mode
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO delivery_challans (delivery_challan_id, company_id, challan_number, challan_type, challan_date, billing_party_id, shipping_party_id, reference_number, status, currency, exchange_rate, subtotal, total_gst, grand_total, transport_mode, vehicle_number, place_of_supply, customer_notes, terms_and_conditions, created_by, updated_by) '
                'VALUES (:challan_id, :company_id, :challan_number, :challan_type, :challan_date, :billing_party_id, :shipping_party_id, :reference_number, \'open\', :currency, :exchange_rate, :subtotal, :total_gst, :grand_total, :transport_mode, :vehicle_number, :place_of_supply, :customer_notes, :terms_and_conditions, :created_by, :updated_by)'
            ),
            {
                'challan_id': str(challan_id),
                'company_id': str(company_id),
                'challan_number': challan_number,
                'challan_type': payload.challan_type,
                'challan_date': payload.challan_date,
                'billing_party_id': str(payload.billing_party_id),
                'shipping_party_id': str(payload.shipping_party_id) if payload.shipping_party_id else None,
                'reference_number': payload.reference_number,
                'currency': payload.currency,
                'exchange_rate': payload.exchange_rate,
                'subtotal': float(subtotal),
                'total_gst': float(total_gst),
                'grand_total': float(grand_total),
                'transport_mode': payload.transport_mode,
                'vehicle_number': payload.vehicle_number,
                'place_of_supply': payload.place_of_supply,
                'customer_notes': payload.customer_notes,
                'terms_and_conditions': payload.terms_and_conditions,
                'created_by': str(user_id),
                'updated_by': str(user_id)
            }
        )

        for item in items:
            item_account_id = item['account_id'] or uuid4()
            item_hsn_sac = item['hsn_sac'] or "0000"
            conn.execute(
                text(
                    'INSERT INTO delivery_challan_items (challan_item_id, delivery_challan_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, total_amount) '
                    'VALUES (:challan_item_id, :delivery_challan_id, :company_id, :line_number, :description, :hsn_sac, :inventory_item_id, :account_id, :quantity, :unit_price, :discount_amount, :taxable_amount, :gst_rate, :gst_amount, :total_amount)'
                ),
                {
                    'challan_item_id': str(item['challan_item_id']),
                    'delivery_challan_id': str(item['delivery_challan_id']),
                    'company_id': str(company_id),
                    'line_number': item['line_number'],
                    'description': item['description'],
                    'hsn_sac': item_hsn_sac,
                    'inventory_item_id': str(item['inventory_item_id']) if item['inventory_item_id'] else None,
                    'account_id': str(item_account_id),
                    'quantity': item['quantity'],
                    'unit_price': item['unit_price'],
                    'discount_amount': item['discount_amount'],
                    'taxable_amount': item['taxable_amount'],
                    'gst_rate': item['gst_rate'],
                    'gst_amount': item['gst_amount'],
                    'total_amount': item['total_amount']
                }
            )

    return get_delivery_challan(challan_id, company_id)

def get_delivery_challan(delivery_challan_id: UUID, company_id: UUID) -> DeliveryChallanResponse:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if delivery_challan_id not in MOCK_DELIVERY_CHALLANS:
            raise ValueError("Challan not found")
        return DeliveryChallanResponse(**MOCK_DELIVERY_CHALLANS[delivery_challan_id])

    with engine.begin() as conn:
        challan = conn.execute(
            text('SELECT * FROM delivery_challans WHERE delivery_challan_id = :challan_id AND company_id = :company_id'),
            {'challan_id': str(delivery_challan_id), 'company_id': str(company_id)}
        ).fetchone()
        if challan is None:
            raise ValueError("Challan not found")
        
        challan_dict = dict(challan._mapping) if hasattr(challan, '_mapping') else dict(challan)
        
        items = conn.execute(
            text('SELECT * FROM delivery_challan_items WHERE delivery_challan_id = :challan_id AND company_id = :company_id ORDER BY line_number'),
            {'challan_id': str(delivery_challan_id), 'company_id': str(company_id)}
        ).fetchall()
        
        challan_dict['items'] = [dict(x._mapping) if hasattr(x, '_mapping') else dict(x) for x in items]
        return DeliveryChallanResponse(**challan_dict)

def list_delivery_challans(company_id: UUID) -> list[DeliveryChallanResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return [DeliveryChallanResponse(**x) for x in MOCK_DELIVERY_CHALLANS.values() if x['company_id'] == company_id]
        
    with engine.begin() as conn:
        challans = conn.execute(
            text('SELECT * FROM delivery_challans WHERE company_id = :company_id ORDER BY created_at DESC'),
            {'company_id': str(company_id)}
        ).fetchall()
        
        results = []
        for c in challans:
            c_dict = dict(c._mapping) if hasattr(c, '_mapping') else dict(c)
            items = conn.execute(
                text('SELECT * FROM delivery_challan_items WHERE delivery_challan_id = :challan_id ORDER BY line_number'),
                {'challan_id': str(c_dict['delivery_challan_id'])}
            ).fetchall()
            c_dict['items'] = [dict(x._mapping) if hasattr(x, '_mapping') else dict(x) for x in items]
            results.append(DeliveryChallanResponse(**c_dict))
        return results

def convert_challan_to_invoice(delivery_challan_id: UUID, company_id: UUID, user_id: UUID) -> InvoiceResponse:
    challan = get_delivery_challan(delivery_challan_id, company_id)
    if challan.status == 'converted':
        raise ValueError("Delivery Challan is already converted to an invoice")
        
    invoice_id = uuid4()
    
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        # Convert in mock
        subtotal = 0.0
        gst_total = 0.0
        grand_total = 0.0
        items = []
        
        for idx, item in enumerate(challan.items or []):
            items.append(InvoiceItemResponse(
                invoice_item_id=uuid4(),
                invoice_id=invoice_id,
                company_id=company_id,
                line_number=idx + 1,
                description=item.description,
                hsn_sac=item.hsn_sac,
                account_id=item.account_id or uuid4(),
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_amount=item.discount_amount,
                taxable_amount=item.taxable_amount,
                gst_rate=item.gst_rate,
                gst_amount=item.gst_amount,
                tds_rate=0.0,
                tds_amount=0.0,
                tcs_rate=0.0,
                tcs_amount=0.0,
                total_amount=item.total_amount
            ))
            subtotal += item.taxable_amount
            gst_total += item.gst_amount
            grand_total += item.total_amount

        invoice_number = f"INV-DC-{str(uuid4())[:8].upper()}"
        inv_payload = {
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'invoice_type': 'sales_invoice',
            'invoice_date': date.today(),
            'due_date': date.today() + timedelta(days=15),
            'billing_party_id': challan.billing_party_id,
            'shipping_party_id': challan.shipping_party_id,
            'order_number': challan.challan_number,
            'salesperson_id': None,
            'subject': f"Invoice converted from Challan {challan.challan_number}",
            'customer_notes': challan.customer_notes,
            'terms_and_conditions': challan.terms_and_conditions,
            'status': 'draft',
            'invoice_subtotal': subtotal,
            'invoice_total_gst': gst_total,
            'invoice_total_tds': 0.0,
            'invoice_total_tcs': 0.0,
            'invoice_grand_total': grand_total,
            'paid_amount': 0.0,
            'balance_due': grand_total,
            'currency': challan.currency,
            'created_at': datetime.utcnow(),
            'items': items,
            'delivery_challan_id': delivery_challan_id
        }
        MOCK_INVOICES[invoice_id] = get_or_create_mock_invoice(invoice_id)
        for k, v in inv_payload.items():
            setattr(MOCK_INVOICES[invoice_id], k, v)

        # Update Challan Status
        MOCK_DELIVERY_CHALLANS[delivery_challan_id]['status'] = 'converted'
        MOCK_DELIVERY_CHALLANS[delivery_challan_id]['updated_at'] = datetime.utcnow()
        return MOCK_INVOICES[invoice_id]

    # Database Mode
    with engine.begin() as conn:
        transaction_id = uuid4()
        invoice_number = conn.execute(
            text('SELECT app.next_invoice_number(:company_id, :invoice_type)'),
            {'company_id': str(company_id), 'invoice_type': 'sales_invoice'}
        ).scalar_one()

        subtotal = 0.0
        gst_total = 0.0
        grand_total = 0.0

        for item in challan.items or []:
            taxable_amount = float(item.quantity) * float(item.unit_price) - float(item.discount_amount)
            gst_amount = round(taxable_amount * float(item.gst_rate) / 100, 2)
            total_amount = taxable_amount + gst_amount

            subtotal += taxable_amount
            gst_total += gst_amount
            grand_total += total_amount

        conn.execute(
            text(
                'INSERT INTO transactions (transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, subtotal, gst_breakdown, grand_total, status, currency, exchange_rate, created_by, updated_by, created_at, updated_at) '
                'VALUES (:transaction_id, :company_id, :txn_type, :txn_number, :txn_date, :fiscal_year, :period, :subtotal, :gst_breakdown, :grand_total, :status, :currency, :exchange_rate, :created_by, :updated_by, now(), now())'
            ),
            {
                'transaction_id': str(transaction_id),
                'company_id': str(company_id),
                'txn_type': 'sales_invoice',
                'txn_number': invoice_number,
                'txn_date': date.today(),
                'fiscal_year': date.today().strftime('%Y-%m'),
                'period': date.today().strftime('%Y-%m'),
                'subtotal': subtotal,
                'gst_breakdown': {'gst_total': gst_total},
                'grand_total': grand_total,
                'status': 'draft',
                'currency': challan.currency,
                'exchange_rate': challan.exchange_rate,
                'created_by': str(user_id),
                'updated_by': str(user_id)
            }
        )

        conn.execute(
            text(
                'INSERT INTO invoices (invoice_id, company_id, transaction_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_grand_total, status, created_by, updated_by, created_at, updated_at, delivery_challan_id) '
                'VALUES (:invoice_id, :company_id, :transaction_id, :invoice_number, :invoice_type, :invoice_date, :due_date, :billing_party_id, :shipping_party_id, :currency, :exchange_rate, :invoice_subtotal, :invoice_total_gst, :invoice_grand_total, :status, :created_by, :updated_by, now(), now(), :delivery_challan_id)'
            ),
            {
                'invoice_id': str(invoice_id),
                'company_id': str(company_id),
                'transaction_id': str(transaction_id),
                'invoice_number': invoice_number,
                'invoice_type': 'sales_invoice',
                'invoice_date': date.today(),
                'due_date': date.today() + timedelta(days=15),
                'billing_party_id': str(challan.billing_party_id),
                'shipping_party_id': str(challan.shipping_party_id) if challan.shipping_party_id else None,
                'currency': challan.currency,
                'exchange_rate': challan.exchange_rate,
                'invoice_subtotal': subtotal,
                'invoice_total_gst': gst_total,
                'invoice_grand_total': grand_total,
                'status': 'draft',
                'created_by': str(user_id),
                'updated_by': str(user_id),
                'delivery_challan_id': str(delivery_challan_id)
            }
        )

        for idx, item in enumerate(challan.items or []):
            taxable_amount = float(item.quantity) * float(item.unit_price) - float(item.discount_amount)
            gst_amount = round(taxable_amount * float(item.gst_rate) / 100, 2)
            total_amount = taxable_amount + gst_amount
            item_account_id = item.account_id or uuid4()
            item_hsn_sac = item.hsn_sac or "0000"

            conn.execute(
                text(
                    'INSERT INTO invoice_items (invoice_item_id, invoice_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, total_amount) '
                    'VALUES (gen_random_uuid(), :invoice_id, :company_id, :line_number, :description, :hsn_sac, :inventory_item_id, :account_id, :quantity, :unit_price, :discount_amount, :taxable_amount, :gst_rate, :gst_amount, :total_amount)'
                ),
                {
                    'invoice_id': str(invoice_id),
                    'company_id': str(company_id),
                    'line_number': idx + 1,
                    'description': item.description,
                    'hsn_sac': item_hsn_sac,
                    'inventory_item_id': str(item.inventory_item_id) if item.inventory_item_id else None,
                    'account_id': str(item_account_id),
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'discount_amount': item.discount_amount,
                    'taxable_amount': taxable_amount,
                    'gst_rate': item.gst_rate,
                    'gst_amount': gst_amount,
                    'total_amount': total_amount
                }
            )

        # Update Challan Status
        conn.execute(
            text('UPDATE delivery_challans SET status = \'converted\', updated_at = now() WHERE delivery_challan_id = :challan_id'),
            {'challan_id': str(delivery_challan_id)}
        )

    # Fetch and return the converted invoice
    from routes.invoices import get_invoice
    from utils.auth import TenantContext
    return get_delivery_challan_invoice(invoice_id, company_id)

def get_delivery_challan_invoice(invoice_id: UUID, company_id: UUID) -> InvoiceResponse:
    with engine.begin() as conn:
        inv = conn.execute(
            text('SELECT * FROM invoices WHERE invoice_id = :invoice_id AND company_id = :company_id'),
            {'invoice_id': str(invoice_id), 'company_id': str(company_id)}
        ).fetchone()
        
        inv_dict = dict(inv._mapping) if hasattr(inv, '_mapping') else dict(inv)
        
        items = conn.execute(
            text('SELECT * FROM invoice_items WHERE invoice_id = :invoice_id AND company_id = :company_id ORDER BY line_number'),
            {'invoice_id': str(invoice_id), 'company_id': str(company_id)}
        ).fetchall()
        
        inv_dict['items'] = [dict(x._mapping) if hasattr(x, '_mapping') else dict(x) for x in items]
        return InvoiceResponse(**inv_dict)

def get_delivery_challan_pdf(challan_number: str) -> bytes:
    """Renders a standard-compliant minimal pure-Python PDF for Challans."""
    text_line = f"Delivery Challan {challan_number}"
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
