import os
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy import text
from utils.db_invoice import engine
from models.recurring_invoices import RecurringInvoiceProfileCreateRequest, RecurringInvoiceProfileResponse, RecurringInvoiceItemResponse, RecurringInvoiceLogResponse
from models.invoices import InvoiceItemResponse
from routes.invoices import MOCK_INVOICES, get_or_create_mock_invoice
from decimal import Decimal

# In-memory database for mock mode
MOCK_RECURRING_PROFILES: dict[UUID, dict] = {}
MOCK_RECURRING_LOGS: list[dict] = []

def calculate_next_run_date(start_date: date, frequency: str) -> date:
    if frequency == 'daily':
        return start_date + timedelta(days=1)
    elif frequency == 'weekly':
        return start_date + timedelta(weeks=1)
    elif frequency == 'monthly':
        month = start_date.month + 1
        year = start_date.year
        if month > 12:
            month = 1
            year += 1
        day = min(start_date.day, 28)
        return date(year, month, day)
    elif frequency == 'quarterly':
        month = start_date.month + 3
        year = start_date.year
        if month > 12:
            month = month - 12
            year += 1
        day = min(start_date.day, 28)
        return date(year, month, day)
    elif frequency == 'yearly':
        year = start_date.year + 1
        month = start_date.month
        day = start_date.day
        if month == 2 and day == 29:
            day = 28
        return date(year, month, day)
    return start_date

def create_recurring_profile(payload: RecurringInvoiceProfileCreateRequest, company_id: UUID, user_id: UUID) -> RecurringInvoiceProfileResponse:
    profile_id = uuid4()
    next_run = payload.start_date
    
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        # Mock Mode
        items = []
        for idx, item in enumerate(payload.items):
            taxable_amount = item.quantity * item.unit_price - item.discount_amount
            gst_amount = taxable_amount * item.gst_rate / Decimal('100')
            tds_amount = taxable_amount * item.tds_rate / Decimal('100')
            tcs_amount = taxable_amount * item.tcs_rate / Decimal('100')
            total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount
            
            items.append(RecurringInvoiceItemResponse(
                profile_item_id=uuid4(),
                profile_id=profile_id,
                company_id=company_id,
                line_number=idx + 1,
                description=item.description,
                hsn_sac=item.hsn_sac,
                inventory_item_id=item.inventory_item_id,
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
            
        profile = {
            'profile_id': profile_id,
            'company_id': company_id,
            'profile_name': payload.profile_name,
            'billing_party_id': payload.billing_party_id,
            'shipping_party_id': payload.shipping_party_id,
            'frequency': payload.frequency,
            'status': 'active',
            'start_date': payload.start_date,
            'end_date': payload.end_date,
            'next_run_date': next_run,
            'last_run_date': None,
            'auto_email': payload.auto_email,
            'currency': payload.currency,
            'exchange_rate': float(payload.exchange_rate),
            'order_number': payload.order_number,
            'salesperson_id': payload.salesperson_id,
            'subject': payload.subject,
            'customer_notes': payload.customer_notes,
            'terms_and_conditions': payload.terms_and_conditions,
            'created_by': user_id,
            'updated_by': user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'items': items
        }
        MOCK_RECURRING_PROFILES[profile_id] = profile
        return RecurringInvoiceProfileResponse(**profile)

    # Database Mode
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO recurring_invoice_profiles (profile_id, company_id, profile_name, billing_party_id, shipping_party_id, frequency, status, start_date, end_date, next_run_date, auto_email, currency, exchange_rate, order_number, salesperson_id, subject, customer_notes, terms_and_conditions, created_by, updated_by) '
                'VALUES (:profile_id, :company_id, :profile_name, :billing_party_id, :shipping_party_id, :frequency, :status, :start_date, :end_date, :next_run_date, :auto_email, :currency, :exchange_rate, :order_number, :salesperson_id, :subject, :customer_notes, :terms_and_conditions, :created_by, :updated_by)'
            ),
            {
                'profile_id': str(profile_id),
                'company_id': str(company_id),
                'profile_name': payload.profile_name,
                'billing_party_id': str(payload.billing_party_id),
                'shipping_party_id': str(payload.shipping_party_id) if payload.shipping_party_id else None,
                'frequency': payload.frequency,
                'status': 'active',
                'start_date': payload.start_date,
                'end_date': payload.end_date,
                'next_run_date': next_run,
                'auto_email': payload.auto_email,
                'currency': payload.currency,
                'exchange_rate': payload.exchange_rate,
                'order_number': payload.order_number,
                'salesperson_id': str(payload.salesperson_id) if payload.salesperson_id else None,
                'subject': payload.subject,
                'customer_notes': payload.customer_notes,
                'terms_and_conditions': payload.terms_and_conditions,
                'created_by': str(user_id),
                'updated_by': str(user_id)
            }
        )

        for idx, item in enumerate(payload.items):
            taxable_amount = float(item.quantity) * float(item.unit_price) - float(item.discount_amount)
            gst_amount = round(taxable_amount * float(item.gst_rate) / 100, 2)
            tds_amount = round(taxable_amount * float(item.tds_rate) / 100, 2)
            tcs_amount = round(taxable_amount * float(item.tcs_rate) / 100, 2)
            total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount
            item_account_id = item.account_id or uuid4()
            item_hsn_sac = item.hsn_sac or "0000"

            conn.execute(
                text(
                    'INSERT INTO recurring_invoice_items (profile_item_id, profile_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, total_amount) '
                    'VALUES (gen_random_uuid(), :profile_id, :company_id, :line_number, :description, :hsn_sac, :inventory_item_id, :account_id, :quantity, :unit_price, :discount_amount, :taxable_amount, :gst_rate, :gst_amount, :tds_rate, :tds_amount, :tcs_rate, :tcs_amount, :total_amount)'
                ),
                {
                    'profile_id': str(profile_id),
                    'company_id': str(company_id),
                    'line_number': idx + 1,
                    'description': item.description,
                    'hsn_sac': item_hsn_sac,
                    'inventory_item_id': str(item.inventory_item_id) if item.inventory_item_id else None,
                    'account_id': str(item_account_id),
                    'quantity': float(item.quantity),
                    'unit_price': float(item.unit_price),
                    'discount_amount': float(item.discount_amount),
                    'taxable_amount': taxable_amount,
                    'gst_rate': float(item.gst_rate),
                    'gst_amount': gst_amount,
                    'tds_rate': float(item.tds_rate),
                    'tds_amount': tds_amount,
                    'tcs_rate': float(item.tcs_rate),
                    'tcs_amount': tcs_amount,
                    'total_amount': total_amount
                }
            )

    return get_recurring_profile(profile_id, company_id)

def get_recurring_profile(profile_id: UUID, company_id: UUID) -> RecurringInvoiceProfileResponse:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if profile_id not in MOCK_RECURRING_PROFILES:
            raise ValueError("Profile not found")
        return RecurringInvoiceProfileResponse(**MOCK_RECURRING_PROFILES[profile_id])

    with engine.begin() as conn:
        profile = conn.execute(
            text('SELECT * FROM recurring_invoice_profiles WHERE profile_id = :profile_id AND company_id = :company_id'),
            {'profile_id': str(profile_id), 'company_id': str(company_id)}
        ).fetchone()
        if profile is None:
            raise ValueError("Profile not found")
        
        profile_dict = dict(profile._mapping) if hasattr(profile, '_mapping') else dict(profile)
        
        items = conn.execute(
            text('SELECT * FROM recurring_invoice_items WHERE profile_id = :profile_id AND company_id = :company_id ORDER BY line_number'),
            {'profile_id': str(profile_id), 'company_id': str(company_id)}
        ).fetchall()
        
        profile_dict['items'] = [dict(x._mapping) if hasattr(x, '_mapping') else dict(x) for x in items]
        return RecurringInvoiceProfileResponse(**profile_dict)

def update_profile_status(profile_id: UUID, company_id: UUID, status: str) -> RecurringInvoiceProfileResponse:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        if profile_id not in MOCK_RECURRING_PROFILES:
            raise ValueError("Profile not found")
        MOCK_RECURRING_PROFILES[profile_id]['status'] = status
        MOCK_RECURRING_PROFILES[profile_id]['updated_at'] = datetime.utcnow()
        return RecurringInvoiceProfileResponse(**MOCK_RECURRING_PROFILES[profile_id])

    with engine.begin() as conn:
        conn.execute(
            text('UPDATE recurring_invoice_profiles SET status = :status, updated_at = now() WHERE profile_id = :profile_id AND company_id = :company_id'),
            {'status': status, 'profile_id': str(profile_id), 'company_id': str(company_id)}
        )
    return get_recurring_profile(profile_id, company_id)

def trigger_invoice_generation(profile_id: UUID, company_id: UUID, user_id: UUID, run_date: date) -> UUID:
    """Generates an invoice from the recurring profile and shifts next run date."""
    profile = get_recurring_profile(profile_id, company_id)
    if profile.status == 'stopped':
        raise ValueError("Cannot generate invoice for a stopped profile")
        
    invoice_id = uuid4()
    
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        # Generate mock invoice
        subtotal = 0.0
        gst_total = 0.0
        tds_total = 0.0
        tcs_total = 0.0
        grand_total = 0.0
        items = []
        
        for item in profile.items or []:
            items.append(InvoiceItemResponse(
                invoice_item_id=uuid4(),
                invoice_id=invoice_id,
                company_id=company_id,
                line_number=item.line_number,
                description=item.description,
                hsn_sac=item.hsn_sac,
                account_id=item.account_id,
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
                total_amount=item.total_amount
            ))
            subtotal += item.taxable_amount
            gst_total += item.gst_amount
            tds_total += item.tds_amount
            tcs_total += item.tcs_amount
            grand_total += item.total_amount

        invoice_number = f"INV-REC-{str(uuid4())[:8].upper()}"
        inv_payload = {
            'invoice_id': invoice_id,
            'invoice_number': invoice_number,
            'invoice_type': 'sales_invoice',
            'invoice_date': run_date,
            'due_date': run_date + timedelta(days=15),
            'billing_party_id': profile.billing_party_id,
            'shipping_party_id': profile.shipping_party_id,
            'order_number': profile.order_number,
            'salesperson_id': profile.salesperson_id,
            'subject': profile.subject,
            'customer_notes': profile.customer_notes,
            'terms_and_conditions': profile.terms_and_conditions,
            'status': 'draft',
            'invoice_subtotal': subtotal,
            'invoice_total_gst': gst_total,
            'invoice_total_tds': tds_total,
            'invoice_total_tcs': tcs_total,
            'invoice_grand_total': grand_total,
            'paid_amount': 0.0,
            'balance_due': grand_total,
            'currency': profile.currency,
            'created_at': datetime.utcnow(),
            'items': items
        }
        MOCK_INVOICES[invoice_id] = get_or_create_mock_invoice(invoice_id)
        # Overwrite with correct profile data
        for k, v in inv_payload.items():
            setattr(MOCK_INVOICES[invoice_id], k, v)

        # Update profile
        MOCK_RECURRING_PROFILES[profile_id]['last_run_date'] = run_date
        MOCK_RECURRING_PROFILES[profile_id]['next_run_date'] = calculate_next_run_date(run_date, profile.frequency)
        
        # Log successful run
        MOCK_RECURRING_LOGS.append({
            'log_id': uuid4(),
            'profile_id': profile_id,
            'company_id': company_id,
            'run_date': datetime.utcnow(),
            'status': 'success',
            'generated_invoice_id': invoice_id,
            'error_message': None,
            'created_at': datetime.utcnow()
        })
        return invoice_id

    # Database Mode
    try:
        with engine.begin() as conn:
            transaction_id = uuid4()
            invoice_number = conn.execute(
                text('SELECT app.next_invoice_number(:company_id, :invoice_type)'),
                {'company_id': str(company_id), 'invoice_type': 'sales_invoice'}
            ).scalar_one()

            subtotal = 0.0
            gst_total = 0.0
            tds_total = 0.0
            tcs_total = 0.0
            grand_total = 0.0

            for item in profile.items or []:
                taxable_amount = float(item.quantity) * float(item.unit_price) - float(item.discount_amount)
                gst_amount = round(taxable_amount * float(item.gst_rate) / 100, 2)
                tds_amount = round(taxable_amount * float(item.tds_rate) / 100, 2)
                tcs_amount = round(taxable_amount * float(item.tcs_rate) / 100, 2)
                total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount

                subtotal += taxable_amount
                gst_total += gst_amount
                tds_total += tds_amount
                tcs_total += tcs_amount
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
                    'txn_date': run_date,
                    'fiscal_year': run_date.strftime('%Y-%m'),
                    'period': run_date.strftime('%Y-%m'),
                    'subtotal': subtotal,
                    'gst_breakdown': {'gst_total': gst_total, 'tds_total': tds_total, 'tcs_total': tcs_total},
                    'grand_total': grand_total,
                    'status': 'draft',
                    'currency': profile.currency,
                    'exchange_rate': profile.exchange_rate,
                    'created_by': str(user_id),
                    'updated_by': str(user_id)
                }
            )

            conn.execute(
                text(
                    'INSERT INTO invoices (invoice_id, company_id, transaction_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_total_tds, invoice_total_tcs, invoice_grand_total, status, created_by, updated_by, created_at, updated_at, recurring_profile_id) '
                    'VALUES (:invoice_id, :company_id, :transaction_id, :invoice_number, :invoice_type, :invoice_date, :due_date, :billing_party_id, :shipping_party_id, :currency, :exchange_rate, :invoice_subtotal, :invoice_total_gst, :invoice_total_tds, :invoice_total_tcs, :invoice_grand_total, :status, :created_by, :updated_by, now(), now(), :recurring_profile_id)'
                ),
                {
                    'invoice_id': str(invoice_id),
                    'company_id': str(company_id),
                    'transaction_id': str(transaction_id),
                    'invoice_number': invoice_number,
                    'invoice_type': 'sales_invoice',
                    'invoice_date': run_date,
                    'due_date': run_date + timedelta(days=15),
                    'billing_party_id': str(profile.billing_party_id),
                    'shipping_party_id': str(profile.shipping_party_id) if profile.shipping_party_id else None,
                    'currency': profile.currency,
                    'exchange_rate': profile.exchange_rate,
                    'invoice_subtotal': subtotal,
                    'invoice_total_gst': gst_total,
                    'invoice_total_tds': tds_total,
                    'invoice_total_tcs': tcs_total,
                    'invoice_grand_total': grand_total,
                    'status': 'draft',
                    'created_by': str(user_id),
                    'updated_by': str(user_id),
                    'recurring_profile_id': str(profile_id)
                }
            )

            for item in profile.items or []:
                taxable_amount = float(item.quantity) * float(item.unit_price) - float(item.discount_amount)
                gst_amount = round(taxable_amount * float(item.gst_rate) / 100, 2)
                tds_amount = round(taxable_amount * float(item.tds_rate) / 100, 2)
                tcs_amount = round(taxable_amount * float(item.tcs_rate) / 100, 2)
                total_amount = taxable_amount + gst_amount + tcs_amount - tds_amount

                conn.execute(
                    text(
                        'INSERT INTO invoice_items (invoice_item_id, invoice_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, tds_rate, tds_amount, tcs_rate, tcs_amount, total_amount) '
                        'VALUES (gen_random_uuid(), :invoice_id, :company_id, :line_number, :description, :hsn_sac, :inventory_item_id, :account_id, :quantity, :unit_price, :discount_amount, :taxable_amount, :gst_rate, :gst_amount, :tds_rate, :tds_amount, :tcs_rate, :tcs_amount, :total_amount)'
                    ),
                    {
                        'invoice_id': str(invoice_id),
                        'company_id': str(company_id),
                        'line_number': item.line_number,
                        'description': item.description,
                        'hsn_sac': item.hsn_sac or "0000",
                        'inventory_item_id': str(item.inventory_item_id) if item.inventory_item_id else None,
                        'account_id': str(item.account_id),
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
                        'total_amount': total_amount
                    }
                )

            # Shift profile dates
            next_date = calculate_next_run_date(run_date, profile.frequency)
            conn.execute(
                text('UPDATE recurring_invoice_profiles SET last_run_date = :run_date, next_run_date = :next_date, updated_at = now() WHERE profile_id = :profile_id'),
                {'run_date': run_date, 'next_date': next_date, 'profile_id': str(profile_id)}
            )

            # Create success log
            conn.execute(
                text('INSERT INTO recurring_invoice_logs (log_id, profile_id, company_id, run_date, status, generated_invoice_id) VALUES (gen_random_uuid(), :profile_id, :company_id, now(), \'success\', :generated_invoice_id)'),
                {'profile_id': str(profile_id), 'company_id': str(company_id), 'generated_invoice_id': str(invoice_id)}
            )
            return invoice_id
    except Exception as e:
        with engine.begin() as conn_log:
            conn_log.execute(
                text('INSERT INTO recurring_invoice_logs (log_id, profile_id, company_id, run_date, status, error_message) VALUES (gen_random_uuid(), :profile_id, :company_id, now(), \'failure\', :error)'),
                {'profile_id': str(profile_id), 'company_id': str(company_id), 'error': str(e)}
            )
        raise e

def list_recurring_profiles(company_id: UUID) -> list[RecurringInvoiceProfileResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return [RecurringInvoiceProfileResponse(**x) for x in MOCK_RECURRING_PROFILES.values() if x['company_id'] == company_id]
        
    with engine.begin() as conn:
        profiles = conn.execute(
            text('SELECT * FROM recurring_invoice_profiles WHERE company_id = :company_id ORDER BY created_at DESC'),
            {'company_id': str(company_id)}
        ).fetchall()
        
        results = []
        for p in profiles:
            p_dict = dict(p._mapping) if hasattr(p, '_mapping') else dict(p)
            items = conn.execute(
                text('SELECT * FROM recurring_invoice_items WHERE profile_id = :profile_id ORDER BY line_number'),
                {'profile_id': str(p_dict['profile_id'])}
            ).fetchall()
            p_dict['items'] = [dict(x._mapping) if hasattr(x, '_mapping') else dict(x) for x in items]
            results.append(RecurringInvoiceProfileResponse(**p_dict))
        return results

def get_profile_logs(profile_id: UUID, company_id: UUID) -> list[RecurringInvoiceLogResponse]:
    if os.getenv('FINOPS_USE_DATABASE', 'true').lower() == 'false':
        return [RecurringInvoiceLogResponse(**x) for x in MOCK_RECURRING_LOGS if x['profile_id'] == profile_id and x['company_id'] == company_id]
        
    with engine.begin() as conn:
        logs = conn.execute(
            text('SELECT * FROM recurring_invoice_logs WHERE profile_id = :profile_id AND company_id = :company_id ORDER BY run_date DESC'),
            {'profile_id': str(profile_id), 'company_id': str(company_id)}
        ).fetchall()
        return [RecurringInvoiceLogResponse(**(dict(x._mapping) if hasattr(x, '_mapping') else dict(x))) for x in logs]

