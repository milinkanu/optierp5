import os
import sys
import json
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from decimal import Decimal

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from utils.security import hash_password
from services.coa_seed import seed_default_chart_of_accounts
from services.customer_service import encrypt_pan

# Initialize connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/finops")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("Connecting to DB...")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Global Fixed UUIDs for ease of linking and verification
COMPANY_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")

# Fixed Item IDs
ITEM_IDS = [
    UUID("a1111111-1111-1111-1111-111111111111"),
    UUID("a2222222-2222-2222-2222-222222222222"),
    UUID("a3333333-3333-3333-3333-333333333333"),
    UUID("a4444444-4444-4444-4444-444444444444"),
    UUID("a5555555-5555-5555-5555-555555555555")
]

# Fixed Customer IDs
CUSTOMER_IDS = [
    UUID("b1111111-1111-1111-1111-111111111111"),
    UUID("b2222222-2222-2222-2222-222222222222"),
    UUID("b3333333-3333-3333-3333-333333333333"),
    UUID("b4444444-4444-4444-4444-444444444444"),
    UUID("b5555555-5555-5555-5555-555555555555")
]

# Fixed Quote IDs
QUOTE_IDS = [
    UUID("c1111111-1111-1111-1111-111111111111"),
    UUID("c2222222-2222-2222-2222-222222222222"),
    UUID("c3333333-3333-3333-3333-333333333333"),
    UUID("c4444444-4444-4444-4444-444444444444"),
    UUID("c5555555-5555-5555-5555-555555555555")
]

# Fixed Sales Order IDs
SO_IDS = [
    UUID("d1111111-1111-1111-1111-111111111111"),
    UUID("d2222222-2222-2222-2222-222222222222"),
    UUID("d3333333-3333-3333-3333-333333333333"),
    UUID("d4444444-4444-4444-4444-444444444444"),
    UUID("d5555555-5555-5555-5555-555555555555")
]

# Fixed Invoice IDs
INV_IDS = [
    UUID("e1111111-1111-1111-1111-111111111111"),
    UUID("e2222222-2222-2222-2222-222222222222"),
    UUID("e3333333-3333-3333-3333-333333333333"),
    UUID("e4444444-4444-4444-4444-444444444444"),
    UUID("e5555555-5555-5555-5555-555555555555")
]

# Fixed Recurring Profile IDs
REC_IDS = [
    UUID("f1111111-1111-1111-1111-111111111111"),
    UUID("f2222222-2222-2222-2222-222222222222"),
    UUID("f3333333-3333-3333-3333-333333333333"),
    UUID("f4444444-4444-4444-4444-444444444444"),
    UUID("f5555555-5555-5555-5555-555555555555")
]

# Fixed Challan IDs
DC_IDS = [
    UUID("71111111-1111-1111-1111-111111111111"),
    UUID("72222222-2222-2222-2222-222222222222"),
    UUID("73333333-3333-3333-3333-333333333333"),
    UUID("74444444-4444-4444-4444-444444444444"),
    UUID("75555555-5555-5555-5555-555555555555")
]

# Fixed Payment IDs
PAY_IDS = [
    UUID("81111111-1111-1111-1111-111111111111"),
    UUID("82222222-2222-2222-2222-222222222222"),
    UUID("83333333-3333-3333-3333-333333333333"),
    UUID("84444444-4444-4444-4444-444444444444"),
    UUID("85555555-5555-5555-5555-555555555555")
]

# Fixed Credit Note IDs
CN_IDS = [
    UUID("91111111-1111-1111-1111-111111111111"),
    UUID("92222222-2222-2222-2222-222222222222"),
    UUID("93333333-3333-3333-3333-333333333333"),
    UUID("94444444-4444-4444-4444-444444444444"),
    UUID("95555555-5555-5555-5555-555555555555")
]

def clean_database():
    print("--- Cleaning Database of Previous Seeded Data ---")
    db.execute(text("SET app.current_company = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("DELETE FROM credit_note_invoice_mappings WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM credit_note_items WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM credit_notes WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("DELETE FROM invoice_payment_allocations WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM invoice_items WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM recurring_invoice_logs WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM invoices WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("DELETE FROM delivery_challan_items WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM delivery_challans WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("DELETE FROM recurring_invoice_items WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM recurring_invoice_profiles WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("DELETE FROM sales_order_activity_logs WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM sales_order_items WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM sales_orders WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("DELETE FROM quote_activity_logs WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM quote_items WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM quotes WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("ALTER TABLE ledger_entries DISABLE TRIGGER trg_ledger_entries_immutable"))
    db.execute(text("DELETE FROM ledger_entries WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("ALTER TABLE ledger_entries ENABLE TRIGGER trg_ledger_entries_immutable"))
    
    db.execute(text("UPDATE journal_entries SET status = 'draft' WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM journal_entry_lines WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM journal_entries WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.execute(text("DELETE FROM customer_tags WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM customer_custom_fields WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM customer_contacts WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM customer_addresses WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM customers WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM transactions WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM inventory_items WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    db.execute(text("DELETE FROM parties WHERE company_id = :company_id"), {'company_id': str(COMPANY_ID)})
    
    db.commit()
    print("Database cleaned.")

def create_company_and_user():
    print("--- Phase 2: Creating Company & Owner User ---")
    
    # 1. Create Company
    db.execute(text("""
        INSERT INTO companies (
            company_id, company_name, trade_name, company_type, pan, gstin, gst_type, primary_state, onboarding_completed, address, created_at, updated_at
        ) VALUES (
            :company_id, :company_name, :trade_name, :company_type, :pan, :gstin, :gst_type, :primary_state, TRUE, :address, now(), now()
        ) ON CONFLICT (company_id) DO NOTHING
    """), {
        'company_id': str(COMPANY_ID),
        'company_name': 'OptiReach Tech Solutions Pvt Ltd',
        'trade_name': 'OptiReach Tech Solutions',
        'company_type': 'pvt_ltd',
        'pan': 'AADCO1234F',
        'gstin': '27AADCO1234F1Z5',
        'gst_type': 'regular',
        'primary_state': 'Maharashtra',
        'address': json.dumps({
            'line1': '101, Maker Chambers V',
            'line2': 'Nariman Point',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400021',
            'country': 'India'
        })
    })
    db.commit()

    # Set Local app.current_company so RLS behaves during selects
    db.execute(text("SET app.current_company = :company_id"), {'company_id': str(COMPANY_ID)})

    # 2. Seed Default Chart of Accounts
    seed_default_chart_of_accounts(db, COMPANY_ID)
    db.commit()

    # 3. Create Default Roles
    roles = [
        ('owner', 'Company owner with full access'),
        ('accountant', 'Accounting and financial operations'),
        ('auditor', 'Read-only access for auditing'),
        ('employee', 'Basic employee access'),
        ('tax_admin', 'Tax filing and compliance access')
    ]
    
    role_ids = {}
    for role_name, desc in roles:
        role_row = db.execute(text("""
            SELECT role_id FROM roles WHERE company_id = :company_id AND name = :name
        """), {'company_id': str(COMPANY_ID), 'name': role_name}).fetchone()
        
        if role_row:
            role_ids[role_name] = role_row[0]
        else:
            role_id = uuid4()
            db.execute(text("""
                INSERT INTO roles (role_id, company_id, name, description, created_at)
                VALUES (:role_id, :company_id, :name, :description, now())
            """), {
                'role_id': role_id,
                'company_id': str(COMPANY_ID),
                'name': role_name,
                'description': desc
            })
            role_ids[role_name] = role_id
            
    db.commit()

    # 4. Create Owner User
    pass_hash = hash_password("password123")
    user_row = db.execute(text("""
        SELECT user_id FROM users WHERE email = 'admin@test.com'
    """)).fetchone()
    
    if not user_row:
        db.execute(text("""
            INSERT INTO users (user_id, company_id, email, password_hash, name, is_active, email_verified, created_at, updated_at)
            VALUES (:user_id, :company_id, 'admin@test.com', :password_hash, 'Milin Kanu', TRUE, TRUE, now(), now())
        """), {
            'user_id': str(USER_ID),
            'company_id': str(COMPANY_ID),
            'password_hash': pass_hash
        })
        
        # Assign owner role
        db.execute(text("""
            INSERT INTO user_roles (user_id, role_id, assigned_at)
            VALUES (:user_id, :role_id, now())
        """), {
            'user_id': str(USER_ID),
            'role_id': role_ids['owner']
        })
        
    db.commit()

    # Default permissions
    permissions = {
        'owner': ['*'],
        'accountant': ['read:ledger', 'write:transactions', 'read:reports'],
        'auditor': ['read:ledger', 'read:reports'],
        'employee': ['read:basic'],
        'tax_admin': ['read:compliance', 'write:filings']
    }
    
    for role_name, perms in permissions.items():
        role_id = role_ids[role_name]
        for perm in perms:
            db.execute(text("""
                INSERT INTO permissions (permission_id, role_id, permission, created_at)
                VALUES (gen_random_uuid(), :role_id, :permission, now())
                ON CONFLICT DO NOTHING
            """), {
                'role_id': role_id,
                'permission': perm
            })
            
    db.commit()

def seed_relational_data():
    print("--- Phase 3: Populating Relational Dummy Data ---")
    db.execute(text("SET app.current_company = :company_id"), {'company_id': str(COMPANY_ID)})

    # Resolve income & expense accounts
    sales_acc = db.execute(text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '4100'"), {'company_id': str(COMPANY_ID)}).fetchone()
    sales_acc_id = sales_acc[0] if sales_acc else uuid4()
    
    service_acc = db.execute(text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '4200'"), {'company_id': str(COMPANY_ID)}).fetchone()
    service_acc_id = service_acc[0] if service_acc else sales_acc_id
    
    exp_acc = db.execute(text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '5100'"), {'company_id': str(COMPANY_ID)}).fetchone()
    exp_acc_id = exp_acc[0] if exp_acc else uuid4()

    # 1. Seed 5 Realistic Inventory Items
    items_data = [
        (ITEM_IDS[0], "Senior Software Engineering Consulting", "service", "hours", "SRV-CONS-001", "High-end development and architectural advisory services.", Decimal("4500.00"), Decimal("0.00"), service_acc_id, exp_acc_id, Decimal("18.00")),
        (ITEM_IDS[1], "OptiReach ERP Enterprise License", "service", "user/month", "LIC-ERP-001", "Monthly subscription license for enterprise ERP.", Decimal("1500.00"), Decimal("0.00"), service_acc_id, exp_acc_id, Decimal("18.00")),
        (ITEM_IDS[2], "Ergonomic Office Chair Elite", "goods", "pcs", "GDS-CHR-999", "Ergonomic high-back leather executive chair.", Decimal("12000.00"), Decimal("8000.00"), sales_acc_id, exp_acc_id, Decimal("18.00")),
        (ITEM_IDS[3], "Nexus High-Speed Gigabit Router", "goods", "pcs", "GDS-RTR-100", "High-performance enterprise dual-band wifi router.", Decimal("5500.00"), Decimal("3500.00"), sales_acc_id, exp_acc_id, Decimal("18.00")),
        (ITEM_IDS[4], "Premium USB-C Docking Station", "goods", "pcs", "GDS-DCK-200", "Multi-port premium laptop docking hub.", Decimal("4200.00"), Decimal("2500.00"), sales_acc_id, exp_acc_id, Decimal("18.00"))
    ]

    for item in items_data:
        db.execute(text("""
            INSERT INTO inventory_items (
                inventory_item_id, company_id, item_name, item_type, unit, sku, description, selling_price, purchase_price, sales_account_id, purchase_account_id, gst_rate, valuation_method, is_active, is_track_inventory, created_at, updated_at
            ) VALUES (
                :id, :company_id, :name, :type, :unit, :sku, :desc, :sell, :purchase, :sales_acc, :purch_acc, :gst, 'fifo', TRUE, TRUE, now(), now()
            )
        """), {
            'id': str(item[0]), 'company_id': str(COMPANY_ID), 'name': item[1], 'type': item[2], 'unit': item[3],
            'sku': item[4], 'desc': item[5], 'sell': float(item[6]), 'purchase': float(item[7]), 'sales_acc': str(item[8]),
            'purch_acc': str(item[9]), 'gst': float(item[10])
        })
    db.commit()
    print("1. Seeded 5 Realistic Inventory Items.")

    # 2. Seed 5 Realistic Customers
    customers_data = [
        (CUSTOMER_IDS[0], "Nexus Digital Labs Pvt Ltd", "customer", "27AAACN4321A1Z9", "AAACN4321A", "finance@nexuslabs.co", "+919876543210", "15-Days", "INR", {"line1": "402, Trade Centre", "city": "Mumbai", "state": "Maharashtra", "pincode": "400051"}),
        (CUSTOMER_IDS[1], "Apex Global Retailers", "customer", "27BBBCA8888P1Z2", "BBBCA8888P", "billing@apexretail.in", "+919822334455", "Due on Receipt", "INR", {"line1": "Flat 12, West End Mall", "city": "Pune", "state": "Maharashtra", "pincode": "411007"}),
        (CUSTOMER_IDS[2], "Skyline Infra Developers", "customer", "27CCCSD9999M1Z3", "CCCSD9999M", "accounts@skyline.org", "+919922001122", "30-Days", "INR", {"line1": "Bldg 3A, Hiranandani Estate", "city": "Thane", "state": "Maharashtra", "pincode": "400607"}),
        (CUSTOMER_IDS[3], "Alpha FinTech Solutions", "customer", "27DDDFT5555L1Z1", "DDDFT5555L", "procurement@alphafin.com", "+919700889977", "15-Days", "INR", {"line1": "1203, Cyber City", "city": "Navi Mumbai", "state": "Maharashtra", "pincode": "400705"}),
        (CUSTOMER_IDS[4], "Milin Kanu & Associates", "customer", None, None, "milinkanu@test.com", "+919867000111", "Due on Receipt", "INR", {"line1": "Flat 4A, Green Meadows", "city": "Mumbai", "state": "Maharashtra", "pincode": "400093"})
    ]

    for cust in customers_data:
        # Step 1: Insert generic Party record
        db.execute(text("""
            INSERT INTO parties (
                party_id, company_id, party_name, party_type, gstin, pan, email, phone, payment_terms, currency, billing_address, shipping_address, created_at, updated_at
            ) VALUES (
                :id, :company_id, :name, :type, :gstin, :pan, :email, :phone, :terms, :curr, :addr, :addr, now(), now()
            )
        """), {
            'id': str(cust[0]), 'company_id': str(COMPANY_ID), 'name': cust[1], 'type': cust[2], 'gstin': cust[3],
            'pan': cust[4], 'email': cust[5], 'phone': cust[6], 'terms': cust[7], 'curr': cust[8], 'addr': json.dumps(cust[9])
        })

        # Step 2: Insert matching Customer record
        gst_reg = 'regular' if cust[3] else 'unregistered'
        code = f"CUST-2026-{cust[0].hex[:5].upper()}"
        enc_pan = None
        if cust[4]:
            try:
                enc_pan = encrypt_pan(cust[4])
            except Exception:
                enc_pan = cust[4]

        db.execute(text("""
            INSERT INTO customers (
                customer_id, company_id, customer_code, customer_name, customer_type, display_name,
                currency, email, mobile, phone, gst_registration_type, gstin, pan, payment_terms,
                credit_limit, opening_balance, opening_balance_type, msme_status, msme_registration_no,
                cin, invoice_delivery_preference, is_active, is_deleted, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, :code, :name, 'business', :name,
                :curr, :email, :phone, :phone, :gst_reg, :gstin, :pan, :terms,
                0.00, 0.00, 'debit', FALSE, NULL,
                NULL, 'email', TRUE, FALSE, :user_id, :user_id, now(), now()
            )
        """), {
            'id': str(cust[0]),
            'company_id': str(COMPANY_ID),
            'code': code,
            'name': cust[1],
            'curr': cust[8],
            'email': cust[5],
            'phone': cust[6],
            'gst_reg': gst_reg,
            'gstin': cust[3],
            'pan': enc_pan,
            'terms': cust[7],
            'user_id': str(USER_ID)
        })

        # Step 3: Insert Customer Addresses (Billing)
        db.execute(text("""
            INSERT INTO customer_addresses (
                address_id, customer_id, company_id, address_type, attention, address_line1, address_line2,
                city, state, zip_code, country, phone, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :customer_id, :company_id, 'billing', 'Accounts Department', :line1, NULL,
                :city, :state, :zip, 'India', :phone, now(), now()
            )
        """), {
            'customer_id': str(cust[0]),
            'company_id': str(COMPANY_ID),
            'line1': cust[9].get('line1'),
            'city': cust[9].get('city'),
            'state': cust[9].get('state'),
            'zip': cust[9].get('pincode'),
            'phone': cust[6]
        })

        # Step 4: Insert Customer Addresses (Shipping)
        db.execute(text("""
            INSERT INTO customer_addresses (
                address_id, customer_id, company_id, address_type, attention, address_line1, address_line2,
                city, state, zip_code, country, phone, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :customer_id, :company_id, 'shipping', 'Receiving Department', :line1, NULL,
                :city, :state, :zip, 'India', :phone, now(), now()
            )
        """), {
            'customer_id': str(cust[0]),
            'company_id': str(COMPANY_ID),
            'line1': cust[9].get('line1'),
            'city': cust[9].get('city'),
            'state': cust[9].get('state'),
            'zip': cust[9].get('pincode'),
            'phone': cust[6]
        })

        # Step 5: Insert Customer Contacts
        db.execute(text("""
            INSERT INTO customer_contacts (
                contact_id, customer_id, company_id, first_name, last_name, email, phone, mobile, designation, is_primary, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :customer_id, :company_id, :first_name, '', :email, :phone, :phone, 'Primary Contact', TRUE, now(), now()
            )
        """), {
            'customer_id': str(cust[0]),
            'company_id': str(COMPANY_ID),
            'first_name': cust[1],
            'email': cust[5] or "info@test.com",
            'phone': cust[6]
        })
    db.commit()
    print("2. Seeded 5 Realistic Customers.")

    # 3. Seed 5 Quotes spanning last 30 days
    quotes_data = [
        (QUOTE_IDS[0], "QT-2026-00001", CUSTOMER_IDS[0], date.today() - timedelta(days=28), "ERP Implementation Proposal", Decimal("0.00"), Decimal("0.00")),
        (QUOTE_IDS[1], "QT-2026-00002", CUSTOMER_IDS[1], date.today() - timedelta(days=24), "Office Premium Seating Supply", Decimal("5.00"), Decimal("3000.00")), # 5% discount
        (QUOTE_IDS[2], "QT-2026-00003", CUSTOMER_IDS[2], date.today() - timedelta(days=20), "High-Speed Router Installation", Decimal("0.00"), Decimal("0.00")),
        (QUOTE_IDS[3], "QT-2026-00004", CUSTOMER_IDS[3], date.today() - timedelta(days=15), "Docking Station Bulk Proposal", Decimal("10.00"), Decimal("4200.00")), # 10% discount
        (QUOTE_IDS[4], "QT-2026-00005", CUSTOMER_IDS[4], date.today() - timedelta(days=10), "Personal IT Advisory Consultation", Decimal("0.00"), Decimal("0.00"))
    ]

    quote_items_data = [
        # Quote 1: 10 licenses of ERP + 20 hours consulting
        (QUOTE_IDS[0], 1, ITEM_IDS[1], "OptiReach ERP Enterprise License", Decimal("10.00"), Decimal("1500.00"), Decimal("0.00")),
        (QUOTE_IDS[0], 2, ITEM_IDS[0], "Senior Software Engineering Consulting", Decimal("20.00"), Decimal("4500.00"), Decimal("0.00")),
        # Quote 2: 5 Office chairs
        (QUOTE_IDS[1], 1, ITEM_IDS[2], "Ergonomic Office Chair Elite", Decimal("5.00"), Decimal("12000.00"), Decimal("3000.00")),
        # Quote 3: 3 Routers
        (QUOTE_IDS[2], 1, ITEM_IDS[3], "Nexus High-Speed Gigabit Router", Decimal("3.00"), Decimal("5500.00"), Decimal("0.00")),
        # Quote 4: 10 Docking Stations
        (QUOTE_IDS[3], 1, ITEM_IDS[4], "Premium USB-C Docking Station", Decimal("10.00"), Decimal("4200.00"), Decimal("4200.00")),
        # Quote 5: 5 hours consultation
        (QUOTE_IDS[4], 1, ITEM_IDS[0], "Senior Software Engineering Consulting", Decimal("5.00"), Decimal("4500.00"), Decimal("0.00"))
    ]

    for q in quotes_data:
        # We'll compute total on items first
        subtotal = Decimal("0.00")
        total_gst = Decimal("0.00")
        for q_item in [x for x in quote_items_data if x[0] == q[0]]:
            taxable = q_item[4] * q_item[5] - q_item[6]
            gst = taxable * Decimal("0.18")
            subtotal += taxable
            total_gst += gst

        grand_total = subtotal + total_gst
        status = 'converted' if q[1] in ("QT-2026-00001", "QT-2026-00002") else 'sent'
        
        db.execute(text("""
            INSERT INTO quotes (
                quote_id, company_id, quote_number, quote_date, expiry_date, billing_party_id, shipping_party_id, subject, status, subtotal, total_gst, grand_total, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, :num, :date, :exp, :party, :party, :subj, :status, :sub, :gst, :grand, :user, :user, now(), now()
            )
        """), {
            'id': str(q[0]), 'company_id': str(COMPANY_ID), 'num': q[1], 'date': q[3], 'exp': q[3] + timedelta(days=30),
            'party': str(q[2]), 'subj': q[4], 'status': status, 'sub': float(subtotal), 'gst': float(total_gst),
            'grand': float(grand_total), 'user': str(USER_ID)
        })

        # Insert items
        for q_item in [x for x in quote_items_data if x[0] == q[0]]:
            taxable = q_item[4] * q_item[5] - q_item[6]
            gst = taxable * Decimal("0.18")
            total = taxable + gst
            
            db.execute(text("""
                INSERT INTO quote_items (
                    quote_item_id, quote_id, company_id, line_number, description, inventory_item_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, total_amount, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :quote_id, :company_id, :line, :desc, :item, :qty, :price, :disc, :taxable, 18.00, :gst, :total, now(), now()
                )
            """), {
                'quote_id': str(q[0]), 'company_id': str(COMPANY_ID), 'line': q_item[1], 'desc': q_item[3],
                'item': str(q_item[2]), 'qty': float(q_item[4]), 'price': float(q_item[5]), 'disc': float(q_item[6]),
                'taxable': float(taxable), 'gst': float(gst), 'total': float(total)
            })

        # Activity log
        db.execute(text("""
            INSERT INTO quote_activity_logs (activity_log_id, quote_id, company_id, actor_user_id, action, new_value, created_at)
            VALUES (gen_random_uuid(), :quote_id, :company_id, :user, 'created', :val, now())
        """), {
            'quote_id': str(q[0]), 'company_id': str(COMPANY_ID), 'user': str(USER_ID),
            'val': json.dumps({'quote_number': q[1], 'grand_total': float(grand_total)})
        })
        
    db.commit()
    print("3. Seeded 5 Realistic Quotes and Activity Logs.")

    # 4. Seed 5 Sales Orders
    so_data = [
        (SO_IDS[0], "SO-2026-00001", CUSTOMER_IDS[0], date.today() - timedelta(days=26), "ERP System Implementation", QUOTE_IDS[0]), # converted from QT-2026-00001
        (SO_IDS[1], "SO-2026-00002", CUSTOMER_IDS[1], date.today() - timedelta(days=22), "Office Ergonomic Seating Setup", QUOTE_IDS[1]), # converted from QT-2026-00002
        (SO_IDS[2], "SO-2026-00003", CUSTOMER_IDS[2], date.today() - timedelta(days=18), "Router Networking Install", None),
        (SO_IDS[3], "SO-2026-00004", CUSTOMER_IDS[3], date.today() - timedelta(days=12), "USB Docking Stations Supply", None),
        (SO_IDS[4], "SO-2026-00005", CUSTOMER_IDS[4], date.today() - timedelta(days=8), "Expert IT Consultancy Hours", None)
    ]

    so_items_data = [
        # SO 1
        (SO_IDS[0], 1, ITEM_IDS[1], "OptiReach ERP Enterprise License", Decimal("10.00"), Decimal("1500.00"), Decimal("0.00")),
        (SO_IDS[0], 2, ITEM_IDS[0], "Senior Software Engineering Consulting", Decimal("20.00"), Decimal("4500.00"), Decimal("0.00")),
        # SO 2
        (SO_IDS[1], 1, ITEM_IDS[2], "Ergonomic Office Chair Elite", Decimal("5.00"), Decimal("12000.00"), Decimal("3000.00")),
        # SO 3
        (SO_IDS[2], 1, ITEM_IDS[3], "Nexus High-Speed Gigabit Router", Decimal("3.00"), Decimal("5500.00"), Decimal("0.00")),
        # SO 4
        (SO_IDS[3], 1, ITEM_IDS[4], "Premium USB-C Docking Station", Decimal("10.00"), Decimal("4200.00"), Decimal("4200.00")),
        # SO 5
        (SO_IDS[4], 1, ITEM_IDS[0], "Senior Software Engineering Consulting", Decimal("5.00"), Decimal("4500.00"), Decimal("0.00"))
    ]

    for so in so_data:
        subtotal = Decimal("0.00")
        total_gst = Decimal("0.00")
        for so_item in [x for x in so_items_data if x[0] == so[0]]:
            taxable = so_item[4] * so_item[5] - so_item[6]
            gst = taxable * Decimal("0.18")
            subtotal += taxable
            total_gst += gst

        grand_total = subtotal + total_gst
        status = 'invoiced' if so[1] in ("SO-2026-00001", "SO-2026-00002") else 'confirmed'
        
        db.execute(text("""
            INSERT INTO sales_orders (
                sales_order_id, company_id, sales_order_number, sales_order_date, expected_shipment_date, billing_party_id, shipping_party_id, subject, status, subtotal, total_gst, grand_total, created_by, updated_by, created_at, updated_at, quote_id
            ) VALUES (
                :id, :company_id, :num, :date, :ship, :party, :party, :subj, :status, :sub, :gst, :grand, :user, :user, now(), now(), :quote
            )
        """), {
            'id': str(so[0]), 'company_id': str(COMPANY_ID), 'num': so[1], 'date': so[3], 'ship': so[3] + timedelta(days=10),
            'party': str(so[2]), 'subj': so[4], 'status': status, 'sub': float(subtotal), 'gst': float(total_gst),
            'grand': float(grand_total), 'user': str(USER_ID), 'quote': str(so[5]) if so[5] else None
        })

        # Insert items
        for so_item in [x for x in so_items_data if x[0] == so[0]]:
            taxable = so_item[4] * so_item[5] - so_item[6]
            gst = taxable * Decimal("0.18")
            total = taxable + gst
            
            db.execute(text("""
                INSERT INTO sales_order_items (
                    sales_order_item_id, sales_order_id, company_id, line_number, description, inventory_item_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, total_amount, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :so_id, :company_id, :line, :desc, :item, :qty, :price, :disc, :taxable, 18.00, :gst, :total, now(), now()
                )
            """), {
                'so_id': str(so[0]), 'company_id': str(COMPANY_ID), 'line': so_item[1], 'desc': so_item[3],
                'item': str(so_item[2]), 'qty': float(so_item[4]), 'price': float(so_item[5]), 'disc': float(so_item[6]),
                'taxable': float(taxable), 'gst': float(gst), 'total': float(total)
            })

        # Activity log
        db.execute(text("""
            INSERT INTO sales_order_activity_logs (activity_log_id, sales_order_id, company_id, actor_user_id, action, new_value, created_at)
            VALUES (gen_random_uuid(), :so_id, :company_id, :user, 'created', :val, now())
        """), {
            'so_id': str(so[0]), 'company_id': str(COMPANY_ID), 'user': str(USER_ID),
            'val': json.dumps({'sales_order_number': so[1], 'grand_total': float(grand_total)})
        })
        
    db.commit()
    print("4. Seeded 5 Realistic Sales Orders and Activity Logs.")

    # 5. Seed 5 Realistic Sales Invoices
    inv_data = [
        (INV_IDS[0], "INV-2026-00001", CUSTOMER_IDS[0], date.today() - timedelta(days=24), "paid", SO_IDS[0]), # fully paid by payment 1
        (INV_IDS[1], "INV-2026-00002", CUSTOMER_IDS[1], date.today() - timedelta(days=20), "partial", SO_IDS[1]), # partially paid by payment 2
        (INV_IDS[2], "INV-2026-00003", CUSTOMER_IDS[2], date.today() - timedelta(days=16), "posted", None), # posted, outstanding
        (INV_IDS[3], "INV-2026-00004", CUSTOMER_IDS[3], date.today() - timedelta(days=10), "posted", None), # posted, outstanding
        (INV_IDS[4], "INV-2026-00005", CUSTOMER_IDS[4], date.today() - timedelta(days=6), "draft", None) # draft status
    ]

    inv_items_data = [
        # Inv 1
        (INV_IDS[0], 1, ITEM_IDS[1], "OptiReach ERP Enterprise License", Decimal("10.00"), Decimal("1500.00"), Decimal("0.00")),
        (INV_IDS[0], 2, ITEM_IDS[0], "Senior Software Engineering Consulting", Decimal("20.00"), Decimal("4500.00"), Decimal("0.00")),
        # Inv 2
        (INV_IDS[1], 1, ITEM_IDS[2], "Ergonomic Office Chair Elite", Decimal("5.00"), Decimal("12000.00"), Decimal("3000.00")),
        # Inv 3
        (INV_IDS[2], 1, ITEM_IDS[3], "Nexus High-Speed Gigabit Router", Decimal("3.00"), Decimal("5500.00"), Decimal("0.00")),
        # Inv 4
        (INV_IDS[3], 1, ITEM_IDS[4], "Premium USB-C Docking Station", Decimal("10.00"), Decimal("4200.00"), Decimal("4200.00")),
        # Inv 5
        (INV_IDS[4], 1, ITEM_IDS[0], "Senior Software Engineering Consulting", Decimal("5.00"), Decimal("4500.00"), Decimal("0.00"))
    ]

    for inv in inv_data:
        subtotal = Decimal("0.00")
        total_gst = Decimal("0.00")
        for inv_item in [x for x in inv_items_data if x[0] == inv[0]]:
            taxable = inv_item[4] * inv_item[5] - inv_item[6]
            gst = taxable * Decimal("0.18")
            subtotal += taxable
            total_gst += gst

        grand_total = subtotal + total_gst
        
        # Determine RLS session bypassing transaction insert
        txn_id = uuid4()
        
        # Insert raw transaction
        db.execute(text("""
            INSERT INTO transactions (
                transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, subtotal, gst_breakdown, grand_total, status, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :txn_id, :company_id, 'sales_invoice', :num, :date, :year, :period, :sub, :breakdown, :grand, :status, :user, :user, now(), now()
            )
        """), {
            'txn_id': str(txn_id), 'company_id': str(COMPANY_ID), 'num': inv[1], 'date': inv[3],
            'year': inv[3].strftime('%Y'), 'period': inv[3].strftime('%Y-%m'), 'sub': float(subtotal),
            'breakdown': json.dumps({'gst_total': float(total_gst), 'cgst_total': float(total_gst/2), 'sgst_total': float(total_gst/2)}),
            'grand': float(grand_total), 'status': 'posted' if inv[4] != 'draft' else 'draft', 'user': str(USER_ID)
        })

        # Insert Invoice Header
        db.execute(text("""
            INSERT INTO invoices (
                invoice_id, company_id, transaction_id, invoice_number, invoice_type, invoice_date, due_date, billing_party_id, shipping_party_id, currency, exchange_rate, invoice_subtotal, invoice_total_gst, invoice_grand_total, paid_amount, status, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, :txn_id, :num, 'sales_invoice', :date, :due, :party, :party, 'INR', 1, :sub, :gst, :grand, 0.00, :status, :user, :user, now(), now()
            )
        """), {
            'id': str(inv[0]), 'company_id': str(COMPANY_ID), 'txn_id': str(txn_id), 'num': inv[1], 'date': inv[3],
            'due': inv[3] + timedelta(days=15), 'party': str(inv[2]), 'sub': float(subtotal), 'gst': float(total_gst),
            'grand': float(grand_total), 'status': inv[4], 'user': str(USER_ID)
        })

        # Insert Invoice Items
        for inv_item in [x for x in inv_items_data if x[0] == inv[0]]:
            taxable = inv_item[4] * inv_item[5] - inv_item[6]
            gst = taxable * Decimal("0.18")
            total = taxable + gst
            
            db.execute(text("""
                INSERT INTO invoice_items (
                    invoice_item_id, invoice_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, total_amount, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :inv_id, :company_id, :line, :desc, '9983', :item, :sales_acc, :qty, :price, :disc, :taxable, 18.00, :gst, :total, now(), now()
                )
            """), {
                'inv_id': str(inv[0]), 'company_id': str(COMPANY_ID), 'line': inv_item[1], 'desc': inv_item[3],
                'item': str(inv_item[2]), 'sales_acc': str(sales_acc_id), 'qty': float(inv_item[4]),
                'price': float(inv_item[5]), 'disc': float(inv_item[6]), 'taxable': float(taxable), 'gst': float(gst), 'total': float(total)
            })

    db.commit()
    print("5. Seeded 5 Realistic Invoices and Transactions.")

    # 6. Seed 5 Recurring Invoice Profiles and populate success logs
    rec_data = [
        (REC_IDS[0], "Monthly SaaS ERP Sub - Nexus", CUSTOMER_IDS[0], date.today() - timedelta(days=45), 'monthly', ITEM_IDS[1], "OptiReach ERP Enterprise License Subscription", Decimal("10.00"), Decimal("1500.00")),
        (REC_IDS[1], "Weekly Advisory Retainer - Apex", CUSTOMER_IDS[1], date.today() - timedelta(days=28), 'weekly', ITEM_IDS[0], "Weekly Systems Engineering Advisory Hours", Decimal("5.00"), Decimal("4500.00")),
        (REC_IDS[2], "Monthly Server Maintenance - Skyline", CUSTOMER_IDS[2], date.today() - timedelta(days=35), 'monthly', ITEM_IDS[0], "Server Infrastructure Maintenance retainer", Decimal("8.00"), Decimal("4500.00")),
        (REC_IDS[3], "Monthly IT Support retaining - Alpha", CUSTOMER_IDS[3], date.today() - timedelta(days=15), 'monthly', ITEM_IDS[0], "L2/L3 IT Helpdesk Support Retainer", Decimal("12.00"), Decimal("4500.00")),
        (REC_IDS[4], "Weekly Business Consultation - Milin", CUSTOMER_IDS[4], date.today() - timedelta(days=10), 'weekly', ITEM_IDS[0], "Personal Business IT Strategy Consultation", Decimal("2.00"), Decimal("4500.00"))
    ]

    for rec in rec_data:
        db.execute(text("""
            INSERT INTO recurring_invoice_profiles (
                profile_id, company_id, profile_name, billing_party_id, shipping_party_id, frequency, status, start_date, end_date, next_run_date, auto_email, currency, exchange_rate, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, :name, :party, :party, :freq, 'active', :start, :end, :next_run, TRUE, 'INR', 1, :user, :user, now(), now()
            )
        """), {
            'id': str(rec[0]), 'company_id': str(COMPANY_ID), 'name': rec[1], 'party': str(rec[2]), 'freq': rec[4],
            'start': rec[3], 'end': rec[3] + timedelta(days=365), 'next_run': rec[3] + timedelta(days=30), 'user': str(USER_ID)
        })

        # Insert item details
        taxable = rec[7] * rec[8]
        gst = taxable * Decimal("0.18")
        total = taxable + gst

        db.execute(text("""
            INSERT INTO recurring_invoice_items (
                profile_item_id, profile_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, total_amount
            ) VALUES (
                gen_random_uuid(), :profile_id, :company_id, 1, :desc, '9983', :item, :sales_acc, :qty, :price, 0.00, :taxable, 18.00, :gst, :total
            )
        """), {
            'profile_id': str(rec[0]), 'company_id': str(COMPANY_ID), 'desc': rec[6], 'item': str(rec[5]),
            'sales_acc': str(sales_acc_id), 'qty': float(rec[7]), 'price': float(rec[8]), 'taxable': float(taxable), 'gst': float(gst), 'total': float(total)
        })

        # Populate recurring run logs showing successful execution
        db.execute(text("""
            INSERT INTO recurring_invoice_logs (
                log_id, profile_id, company_id, run_date, status, generated_invoice_id, error_message, created_at
            ) VALUES (
                gen_random_uuid(), :profile_id, :company_id, :run, 'success', :inv_id, NULL, now()
            )
        """), {
            'profile_id': str(rec[0]), 'company_id': str(COMPANY_ID), 'run': datetime.utcnow() - timedelta(days=5), 'inv_id': str(INV_IDS[0])
        })
        
    db.commit()
    print("6. Seeded 5 Recurring Invoice Profiles and logs.")

    # 7. Seed 5 delivery challans with real transport details
    dc_data = [
        (DC_IDS[0], "DC-2026-00001", CUSTOMER_IDS[0], date.today() - timedelta(days=25), "Road / Porter", "MH-43-EV-1234", "Mumbai"),
        (DC_IDS[1], "DC-2026-00002", CUSTOMER_IDS[1], date.today() - timedelta(days=21), "Road / Tata Ace", "MH-12-PQ-5678", "Pune"),
        (DC_IDS[2], "DC-2026-00003", CUSTOMER_IDS[2], date.today() - timedelta(days=17), "Road / Porter", "MH-04-AB-9999", "Thane"),
        (DC_IDS[3], "DC-2026-00004", CUSTOMER_IDS[3], date.today() - timedelta(days=11), "Self / Hand Delivery", "N/A", "Navi Mumbai"),
        (DC_IDS[4], "DC-2026-00005", CUSTOMER_IDS[4], date.today() - timedelta(days=7), "Road / Porter", "MH-02-XY-8888", "Mumbai")
    ]

    dc_items_data = [
        # Challan 1
        (DC_IDS[0], 1, ITEM_IDS[2], "Ergonomic Office Chair Elite", Decimal("5.00"), Decimal("12000.00"), Decimal("3000.00")),
        # Challan 2
        (DC_IDS[1], 1, ITEM_IDS[3], "Nexus High-Speed Gigabit Router", Decimal("3.00"), Decimal("5500.00"), Decimal("0.00")),
        # Challan 3
        (DC_IDS[2], 1, ITEM_IDS[4], "Premium USB-C Docking Station", Decimal("10.00"), Decimal("4200.00"), Decimal("4200.00")),
        # Challan 4
        (DC_IDS[3], 1, ITEM_IDS[2], "Ergonomic Office Chair Elite", Decimal("2.00"), Decimal("12000.00"), Decimal("0.00")),
        # Challan 5
        (DC_IDS[4], 1, ITEM_IDS[3], "Nexus High-Speed Gigabit Router", Decimal("1.00"), Decimal("5500.00"), Decimal("0.00"))
    ]

    for dc in dc_data:
        subtotal = Decimal("0.00")
        total_gst = Decimal("0.00")
        for dc_item in [x for x in dc_items_data if x[0] == dc[0]]:
            taxable = dc_item[4] * dc_item[5] - dc_item[6]
            gst = taxable * Decimal("0.18")
            subtotal += taxable
            total_gst += gst

        grand_total = subtotal + total_gst

        db.execute(text("""
            INSERT INTO delivery_challans (
                delivery_challan_id, company_id, challan_number, challan_type, challan_date, billing_party_id, shipping_party_id, status, subtotal, total_gst, grand_total, transport_mode, vehicle_number, place_of_supply, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, :num, 'job_work', :date, :party, :party, 'open', :sub, :gst, :grand, :mode, :vehicle, :supply, :user, :user, now(), now()
            )
        """), {
            'id': str(dc[0]), 'company_id': str(COMPANY_ID), 'num': dc[1], 'date': dc[3], 'party': str(dc[2]),
            'sub': float(subtotal), 'gst': float(total_gst), 'grand': float(grand_total), 'mode': dc[4],
            'vehicle': dc[5], 'supply': dc[6], 'user': str(USER_ID)
        })

        for dc_item in [x for x in dc_items_data if x[0] == dc[0]]:
            taxable = dc_item[4] * dc_item[5] - dc_item[6]
            gst = taxable * Decimal("0.18")
            total = taxable + gst

            db.execute(text("""
                INSERT INTO delivery_challan_items (
                    challan_item_id, delivery_challan_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit_price, discount_amount, taxable_amount, gst_rate, gst_amount, total_amount
                ) VALUES (
                    gen_random_uuid(), :dc_id, :company_id, :line, :desc, '9403', :item, :sales_acc, :qty, :price, :disc, :taxable, 18.00, :gst, :total
                )
            """), {
                'dc_id': str(dc[0]), 'company_id': str(COMPANY_ID), 'line': dc_item[1], 'desc': dc_item[3],
                'item': str(dc_item[2]), 'sales_acc': str(sales_acc_id), 'qty': float(dc_item[4]),
                'price': float(dc_item[5]), 'disc': float(dc_item[6]), 'taxable': float(taxable), 'gst': float(gst), 'total': float(total)
            })

    db.commit()
    print("7. Seeded 5 Delivery Challans.")

    # 8. Seed 5 Inbound Payments
    # Resolve bank and accounts receivable accounts for ledger/journal postings
    bank_acc = db.execute(text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '1100'"), {'company_id': str(COMPANY_ID)}).fetchone()
    bank_acc_id = bank_acc[0] if bank_acc else uuid4()
    
    ar_acc = db.execute(text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id AND account_code = '1200'"), {'company_id': str(COMPANY_ID)}).fetchone()
    ar_acc_id = ar_acc[0] if ar_acc else uuid4()

    # Invoice 1: ERP implementation (INV-2026-00001). Grand Total: subtotal 105000 + GST 18900 = 123900. Fully paid.
    # Invoice 2: Seating setup (INV-2026-00002). Grand Total: subtotal 57000 + GST 10260 = 67260. Part paid 40000.
    # Invoice 3: Router installation (INV-2026-00003). Grand total: subtotal 16500 + GST 2970 = 19470. Fully paid.
    # Invoice 4: Docking Stations (INV-2026-00004). Grand total: subtotal 37800 + GST 6804 = 44604. Fully paid.
    # Invoice 5: Consultation (INV-2026-00005). Grand total: subtotal 22500 + GST 4050 = 26550. Draft, not paid.

    payments_data = [
        (PAY_IDS[0], "PAY-00001", CUSTOMER_IDS[0], date.today() - timedelta(days=22), Decimal("123900.00"), "NEFT", "NEFT-NEXUS-9872", INV_IDS[0], Decimal("123900.00")),
        (PAY_IDS[1], "PAY-00002", CUSTOMER_IDS[1], date.today() - timedelta(days=19), Decimal("40000.00"), "UPI", "UPI-APEX-6721", INV_IDS[1], Decimal("40000.00")),
        (PAY_IDS[2], "PAY-00003", CUSTOMER_IDS[2], date.today() - timedelta(days=15), Decimal("19470.00"), "NEFT", "NEFT-SKYLINE-0034", INV_IDS[2], Decimal("19470.00")),
        (PAY_IDS[3], "PAY-00004", CUSTOMER_IDS[3], date.today() - timedelta(days=9), Decimal("44604.00"), "UPI", "UPI-ALPHA-9911", INV_IDS[3], Decimal("44604.00")),
        (PAY_IDS[4], "PAY-00005", CUSTOMER_IDS[4], date.today() - timedelta(days=5), Decimal("5000.00"), "Cash", "CASH-MILIN-1122", None, Decimal("0.00")) # Unused prepayment balance
    ]

    for pay in payments_data:
        unused = pay[4] - pay[8]
        meta = {
            'payment_mode': pay[5],
            'settlement_bank_account_id': str(bank_acc_id),
            'reference_number': pay[6],
            'bank_charges': 0.0,
            'notes': "Realistic customer payment processed.",
            'unused_balance': float(unused)
        }
        
        # 1. Insert into transactions
        db.execute(text("""
            INSERT INTO transactions (
                transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, party_id, subtotal, gst_breakdown, grand_total, status, meta, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, 'payment_inbound', :num, :date, :year, :period, :party, :amount, '{}'::jsonb, :amount, 'posted', :meta, :user, :user, now(), now()
            )
        """), {
            'id': str(pay[0]), 'company_id': str(COMPANY_ID), 'num': pay[1], 'date': pay[3],
            'year': pay[3].strftime('%Y'), 'period': pay[3].strftime('%Y-%m'), 'party': str(pay[2]),
            'amount': float(pay[4]), 'meta': json.dumps(meta), 'user': str(USER_ID)
        })

        # 2. Insert into allocations
        if pay[7] is not None:
            db.execute(text("""
                INSERT INTO invoice_payment_allocations (
                    allocation_id, company_id, payment_transaction_id, invoice_id, allocated_amount, currency, exchange_rate, allocated_at
                ) VALUES (
                    gen_random_uuid(), :company_id, :pay_id, :inv_id, :amount, 'INR', 1, now()
                )
            """), {
                'company_id': str(COMPANY_ID), 'pay_id': str(pay[0]), 'inv_id': str(pay[7]), 'amount': float(pay[8])
            })

            # Note: invoices.paid_amount and status are automatically updated via trigger trg_invoice_payment_allocations_update on allocation insert.
            pass

        # 3. balanced Ledger & Journal entry lines
        journal_id = uuid4()
        jrn_num = f"JRN-PAY-{str(uuid4())[:8].upper()}"
        
        db.execute(text("""
            INSERT INTO journal_entries (
                journal_id, company_id, journal_number, journal_type, journal_date, description, reference, transaction_id, status, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, :num, 'receipt', :date, :desc, :ref, :txn_id, 'draft', :user, :user, now(), now()
            )
        """), {
            'id': str(journal_id), 'company_id': str(COMPANY_ID), 'num': jrn_num, 'date': pay[3],
            'desc': f"Balanced Payment Receipt {pay[1]}", 'ref': pay[6], 'txn_id': str(pay[0]), 'user': str(USER_ID)
        })

        # Debit: Bank/Cash
        db.execute(text("""
            INSERT INTO journal_entry_lines (
                journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at
            ) VALUES (
                gen_random_uuid(), :j_id, :company_id, :acc, 'debit', :amount, :desc, :party, now()
            )
        """), {
            'j_id': str(journal_id), 'company_id': str(COMPANY_ID), 'acc': str(bank_acc_id),
            'amount': float(pay[4]), 'desc': f"Debit Bank/Cash for Inbound Payment {pay[1]}", 'party': str(pay[2])
        })

        # Credit: Accounts Receivable
        db.execute(text("""
            INSERT INTO journal_entry_lines (
                journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at
            ) VALUES (
                gen_random_uuid(), :j_id, :company_id, :acc, 'credit', :amount, :desc, :party, now()
            )
        """), {
            'j_id': str(journal_id), 'company_id': str(COMPANY_ID), 'acc': str(ar_acc_id),
            'amount': float(pay[4]), 'desc': f"Credit Accounts Receivable for Payment {pay[1]}", 'party': str(pay[2])
        })

        # Also write the actual Ledger Entries!
        # Debit ledger
        db.execute(text("""
            INSERT INTO ledger_entries (
                ledger_entry_id, company_id, transaction_id, journal_id, entry_type, account_id, amount, entry_date, reference, party_id, is_reversal, created_at, created_by
            ) VALUES (
                gen_random_uuid(), :company_id, :txn_id, :j_id, 'debit', :acc, :amount, :date, :ref, :party, FALSE, now(), :user
            )
        """), {
            'company_id': str(COMPANY_ID), 'txn_id': str(pay[0]), 'j_id': str(journal_id), 'acc': str(bank_acc_id),
            'amount': float(pay[4]), 'date': pay[3], 'ref': pay[6], 'party': str(pay[2]), 'user': str(USER_ID)
        })

        # Credit ledger
        db.execute(text("""
            INSERT INTO ledger_entries (
                ledger_entry_id, company_id, transaction_id, journal_id, entry_type, account_id, amount, entry_date, reference, party_id, is_reversal, created_at, created_by
            ) VALUES (
                gen_random_uuid(), :company_id, :txn_id, :j_id, 'credit', :acc, :amount, :date, :ref, :party, FALSE, now(), :user
            )
        """), {
            'company_id': str(COMPANY_ID), 'txn_id': str(pay[0]), 'j_id': str(journal_id), 'acc': str(ar_acc_id),
            'amount': float(pay[4]), 'date': pay[3], 'ref': pay[6], 'party': str(pay[2]), 'user': str(USER_ID)
        })

        # Update status to 'posted' (now the lines exist and balance, so trigger will succeed)
        db.execute(text("""
            UPDATE journal_entries SET status = 'posted', updated_at = now() WHERE journal_id = :journal_id
        """), {'journal_id': str(journal_id)})

    db.commit()
    print("8. Seeded 5 Realistic Inbound Payments, Journal lines, allocations and Ledgers.")

    # 9. Seed 5 Credit Notes and apply some to invoices
    # Credit Note 1: Elite Ergonomic Chair Elite volume return (INV-2026-00002). Grand total: 10000 + 1800 GST = 11800. Applied.
    cn_data = [
        (CN_IDS[0], "CN-2026-00001", CUSTOMER_IDS[1], date.today() - timedelta(days=12), ITEM_IDS[2], "Volume chair price adjustment discount credit", Decimal("1.00"), Decimal("10000.00"), INV_IDS[1], Decimal("11800.00")),
        (CN_IDS[1], "CN-2026-00002", CUSTOMER_IDS[0], date.today() - timedelta(days=10), ITEM_IDS[0], "Expert consulting credit correction", Decimal("2.00"), Decimal("4500.00"), None, Decimal("0.00")),
        (CN_IDS[2], "CN-2026-00003", CUSTOMER_IDS[2], date.today() - timedelta(days=8), ITEM_IDS[3], "Damaged Router hardware credit", Decimal("1.00"), Decimal("5500.00"), INV_IDS[2], Decimal("6490.00")),
        (CN_IDS[3], "CN-2026-00004", CUSTOMER_IDS[3], date.today() - timedelta(days=6), ITEM_IDS[4], "Docking station returned defective", Decimal("1.00"), Decimal("4200.00"), INV_IDS[3], Decimal("4956.00")),
        (CN_IDS[4], "CN-2026-00005", CUSTOMER_IDS[4], date.today() - timedelta(days=4), ITEM_IDS[0], "IT 전략 컨설팅 할인 Credit Note", Decimal("1.00"), Decimal("4500.00"), None, Decimal("0.00"))
    ]

    for cn in cn_data:
        subtotal = cn[6] * cn[7]
        total_gst = subtotal * Decimal("0.18")
        grand_total = subtotal + total_gst

        txn_id = uuid4()
        
        # 1. Insert transaction
        db.execute(text("""
            INSERT INTO transactions (
                transaction_id, company_id, txn_type, txn_number, txn_date, fiscal_year, period, subtotal, gst_breakdown, grand_total, status, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :txn_id, :company_id, 'credit_note', :num, :date, :year, :period, :sub, :breakdown, :grand, 'posted', :user, :user, now(), now()
            )
        """), {
            'txn_id': str(txn_id), 'company_id': str(COMPANY_ID), 'num': cn[1], 'date': cn[3],
            'year': cn[3].strftime('%Y'), 'period': cn[3].strftime('%Y-%m'), 'sub': float(subtotal),
            'breakdown': json.dumps({'gst_total': float(total_gst)}), 'grand': float(grand_total), 'user': str(USER_ID)
        })

        # 2. Insert Credit Note Header
        rem_balance = grand_total - cn[9]
        status = 'applied' if rem_balance <= 0 and cn[9] > 0 else ('partially_applied' if cn[9] > 0 else 'open')
        
        db.execute(text("""
            INSERT INTO credit_notes (
                credit_note_id, company_id, transaction_id, credit_note_number, reference_number, credit_note_date, billing_party_id, shipping_party_id, status, currency, exchange_rate, accounts_receivable_id, subtotal, total_gst, grand_total, remaining_balance, customer_notes, terms_and_conditions, created_by, updated_by, created_at, updated_at
            ) VALUES (
                :id, :company_id, :txn_id, :num, 'REF-CN-12', :date, :party, :party, :status, 'INR', 1, :ar_acc, :sub, :gst, :grand, :rem, 'Credit issued successfully.', 'Terms apply.', :user, :user, now(), now()
            )
        """), {
            'id': str(cn[0]), 'company_id': str(COMPANY_ID), 'txn_id': str(txn_id), 'num': cn[1], 'date': cn[3],
            'party': str(cn[2]), 'status': status, 'ar_acc': str(ar_acc_id), 'sub': float(subtotal), 'gst': float(total_gst),
            'grand': float(grand_total), 'rem': float(rem_balance), 'user': str(USER_ID)
        })

        # 3. Insert Credit Note Item
        db.execute(text("""
            INSERT INTO credit_note_items (
                credit_note_item_id, credit_note_id, company_id, line_number, description, hsn_sac, inventory_item_id, account_id, quantity, unit, rate, discount_amount, taxable_amount, tax_percentage, tax_amount, line_total, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :cn_id, :company_id, 1, :desc, '9983', :item, :sales_acc, :qty, 'pcs', :rate, 0.00, :taxable, 18.00, :gst, :total, now(), now()
            )
        """), {
            'cn_id': str(cn[0]), 'company_id': str(COMPANY_ID), 'desc': cn[5], 'item': str(cn[4]),
            'sales_acc': str(sales_acc_id), 'qty': float(cn[6]), 'price': float(cn[7]), 'rate': float(cn[7]),
            'taxable': float(subtotal), 'gst': float(total_gst), 'total': float(grand_total)
        })

        # 4. Map Credit Note to Invoice if requested
        if cn[8] is not None:
            # Map credit
            db.execute(text("""
                INSERT INTO credit_note_invoice_mappings (
                    mapping_id, company_id, credit_note_id, invoice_id, applied_amount, applied_at
                ) VALUES (
                    gen_random_uuid(), :company_id, :cn_id, :inv_id, :amount, now()
                )
            """), {
                'company_id': str(COMPANY_ID), 'cn_id': str(cn[0]), 'inv_id': str(cn[8]), 'amount': float(cn[9])
            })

            # Allocate in invoice payment allocations (so that invoice balance reduces accordingly!)
            db.execute(text("""
                INSERT INTO invoice_payment_allocations (
                    allocation_id, company_id, payment_transaction_id, invoice_id, allocated_amount, currency, exchange_rate, allocated_at
                ) VALUES (
                    gen_random_uuid(), :company_id, :txn_id, :inv_id, :amount, 'INR', 1, now()
                )
            """), {
                'company_id': str(COMPANY_ID), 'txn_id': str(txn_id), 'inv_id': str(cn[8]), 'amount': float(cn[9])
            })

            # Note: invoices.paid_amount and status are automatically updated via trigger trg_invoice_payment_allocations_update on allocation insert.
            pass

        # Seed activity log for Credit Note creation
        db.execute(text("""
            INSERT INTO credit_note_activity_logs (
                log_id, credit_note_id, company_id, activity_type, description, metadata, created_by, created_at
            ) VALUES (
                gen_random_uuid(), :cn_id, :company_id, 'created', :desc, :meta, :user, now()
            )
        """), {
            'cn_id': str(cn[0]), 'company_id': str(COMPANY_ID), 'desc': f"Credit Note {cn[1]} created.",
            'meta': json.dumps({'grand_total': float(grand_total)}), 'user': str(USER_ID)
        })

    db.commit()
    print("9. Seeded 5 Credit Notes, mapped credits to invoices and updated balances.")

if __name__ == "__main__":
    try:
        clean_database()
        create_company_and_user()
        seed_relational_data()
        print("\nSUCCESS! Relational realistic dummy database seeded completely!")
    except Exception as e:
        db.rollback()
        print(f"\nFATAL SEEDING ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
