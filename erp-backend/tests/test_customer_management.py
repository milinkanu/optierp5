"""
Integration and Unit Tests for the Customer Onboarding & Management Module
"""
import pytest
import json
from uuid import uuid4, UUID
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text

from main import app
from utils.db import engine, SessionLocal
from services import customer_service
from models.customers import (
    CustomerCreateRequest,
    CustomerAddressSchema,
    CustomerContactSchema,
    CustomerCustomFieldSchema,
    CustomerUpdateRequest
)

class TestCustomerManagement:
    """Test suite for Customer Onboarding and Management Module"""

    @pytest.fixture(scope="class", autouse=True)
    def seeded_tenant(self):
        """Fetch or create a seeded tenant/company and user"""
        with engine.begin() as conn:
            user_row = conn.execute(text("SELECT user_id, company_id FROM users WHERE email = 'admin@test.com'")).fetchone()
            if user_row:
                user_id, company_id = user_row
            else:
                # Try to fetch ANY existing user
                any_user = conn.execute(text("SELECT user_id, company_id FROM users LIMIT 1")).fetchone()
                if any_user:
                    user_id, company_id = any_user
                else:
                    # Database is completely empty, insert a company and then insert a user
                    company_id = uuid4()
                    user_id = uuid4()
                    conn.execute(
                        text("INSERT INTO companies (company_id, company_name, company_type, pan, gst_type, primary_state, onboarding_completed, created_at, updated_at) "
                             "VALUES (:company_id, 'Test Company', 'pvt_ltd', 'ABCDE1234F', 'regular', 'Maharashtra', true, now(), now())"),
                        {"company_id": str(company_id)}
                    )
                    conn.execute(
                        text("INSERT INTO users (user_id, company_id, email, password_hash, name, created_at, updated_at) "
                             "VALUES (:user_id, :company_id, 'admin@test.com', 'dummy', 'Admin User', now(), now())"),
                        {"user_id": str(user_id), "company_id": str(company_id)}
                    )
            
            return {
                'user_id': user_id,
                'company_id': company_id
            }

    @pytest.fixture
    def db(self):
        """Get a database session"""
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    @pytest.fixture
    def valid_headers(self, seeded_tenant):
        """Create valid headers for requests"""
        from services.common import create_access_token
        
        company_id = seeded_tenant['company_id']
        user_id = seeded_tenant['user_id']
        token = create_access_token(
            subject=str(user_id),
            company_id=company_id,
            user_version=1,
            roles=['owner'],
            delegations=[]
        )
        
        return {
            'Authorization': f'Bearer {token}',
            'X-Tenant-ID': str(company_id),
            'X-User-ID': str(user_id),
            'X-User-Roles': 'owner'
        }

    def clean_all_test_data(self, db, company_id):
        """Clean all test data from prior or current runs to avoid duplicates"""
        # Set status of all test journal entries to draft first to bypass ensure_journal_balance triggers
        db.execute(text("""
            UPDATE journal_entries 
            SET status = 'draft' 
            WHERE company_id = :company_id AND (
                reference LIKE 'CUST-TEST-%' 
                OR reference LIKE 'CUST-API-%'
                OR reference IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003')
            )
        """), {"company_id": str(company_id)})
        
        customer_ids = db.scalars(text("""
            SELECT customer_id FROM customers 
            WHERE company_id = :company_id AND (
                customer_code LIKE 'CUST-TEST-%' 
                OR customer_code LIKE 'CUST-API-%'
                OR customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003')
                OR email IN ('info@alphatech.com', 'imported_a@test.com', 'imported_b@test.com', 'api_contact@apitech.com')
            )
        """), {"company_id": str(company_id)}).all()

        for cid in customer_ids:
            try:
                # Also try to update status to draft using customer_code/customer_id reference to be completely safe
                code_row = db.execute(text("SELECT customer_code FROM customers WHERE customer_id = :cid"), {"cid": str(cid)}).fetchone()
                if code_row and code_row[0]:
                    db.execute(
                        text("UPDATE journal_entries SET status = 'draft' WHERE company_id = :company_id AND reference = :code"),
                        {"company_id": str(company_id), "code": code_row[0]}
                    )
                db.execute(
                    text("UPDATE journal_entries SET status = 'draft' WHERE company_id = :company_id AND (reference = :cid OR description LIKE :desc)"),
                    {"company_id": str(company_id), "cid": str(cid), "desc": f"%{cid}%"}
                )

                db.execute(text("DELETE FROM journal_entry_lines WHERE party_id = :cid"), {"cid": str(cid)})
                db.execute(text("DELETE FROM customer_addresses WHERE customer_id = :cid"), {"cid": str(cid)})
                db.execute(text("DELETE FROM customer_contacts WHERE customer_id = :cid"), {"cid": str(cid)})
                db.execute(text("DELETE FROM customer_custom_fields WHERE customer_id = :cid"), {"cid": str(cid)})
                db.execute(text("DELETE FROM customer_tags WHERE customer_id = :cid"), {"cid": str(cid)})
                db.execute(text("DELETE FROM customers WHERE customer_id = :cid"), {"cid": str(cid)})
                db.execute(text("DELETE FROM parties WHERE party_id = :cid"), {"cid": str(cid)})
            except Exception as e:
                print(f"Error in clean_all_test_data for {cid}: {e}")

        # Delete any orphan test journal entries
        db.execute(text("""
            DELETE FROM journal_entries 
            WHERE company_id = :company_id AND (
                reference LIKE 'CUST-TEST-%'
                OR reference LIKE 'CUST-API-%'
                OR reference IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003')
            )
        """), {"company_id": str(company_id)})
        
        # Clean any orphan parties with test emails just in case
        db.execute(text("""
            DELETE FROM parties 
            WHERE company_id = :company_id 
            AND party_type = 'customer'
            AND email IN ('info@alphatech.com', 'imported_a@test.com', 'imported_b@test.com', 'api_contact@apitech.com')
        """), {"company_id": str(company_id)})
        
        db.commit()

    @pytest.fixture(autouse=True)
    def cleanup_customers(self, db, seeded_tenant):
        """Automatically clean up any customers created during the test runs"""
        # Pre-cleanup: ensure clean database slate before executing test
        self.clean_all_test_data(db, seeded_tenant['company_id'])
        
        created_ids = []
        yield created_ids
        
        # Post-cleanup: clean any customers created in this test
        if created_ids:
            # Expunge all objects from session so SQLAlchemy doesn't try to update deleted objects
            db.expunge_all()
            # RLS needs tenant context
            customer_service.set_tenant_context(db, seeded_tenant['company_id'])
            for cid in created_ids:
                try:
                    # 1. Update status to draft first to bypass triggers
                    code_row = db.execute(text("SELECT customer_code FROM customers WHERE customer_id = :cid"), {"cid": str(cid)}).fetchone()
                    if code_row and code_row[0]:
                        db.execute(
                            text("UPDATE journal_entries SET status = 'draft' WHERE company_id = :company_id AND reference = :code"),
                            {"company_id": str(seeded_tenant['company_id']), "code": code_row[0]}
                        )
                    
                    db.execute(
                        text("UPDATE journal_entries SET status = 'draft' WHERE company_id = :company_id AND (reference = :cid OR description LIKE :desc)"),
                        {"company_id": str(seeded_tenant['company_id']), "cid": str(cid), "desc": f"%{cid}%"}
                    )

                    # 2. Delete journal entry lines referencing this customer's party_id
                    db.execute(text("DELETE FROM journal_entry_lines WHERE party_id = :cid"), {"cid": str(cid)})
                    
                    # 3. Delete opening balance journal entries themselves (linked via reference = customer_code or company_id/reference = cid)
                    if code_row and code_row[0]:
                        db.execute(
                            text("DELETE FROM journal_entries WHERE company_id = :company_id AND reference = :code"),
                            {"company_id": str(seeded_tenant['company_id']), "code": code_row[0]}
                        )
                    
                    db.execute(
                        text("DELETE FROM journal_entries WHERE company_id = :company_id AND (reference = :cid OR description LIKE :desc)"),
                        {"company_id": str(seeded_tenant['company_id']), "cid": str(cid), "desc": f"%{cid}%"}
                    )
                    
                    # 4. Delete child tables
                    db.execute(text("DELETE FROM customer_addresses WHERE customer_id = :cid"), {"cid": str(cid)})
                    db.execute(text("DELETE FROM customer_contacts WHERE customer_id = :cid"), {"cid": str(cid)})
                    db.execute(text("DELETE FROM customer_custom_fields WHERE customer_id = :cid"), {"cid": str(cid)})
                    db.execute(text("DELETE FROM customer_tags WHERE customer_id = :cid"), {"cid": str(cid)})
                    
                    # 5. Delete master customer
                    db.execute(text("DELETE FROM customers WHERE customer_id = :cid"), {"cid": str(cid)})
                    
                    # 6. Delete companion party
                    db.execute(text("DELETE FROM parties WHERE party_id = :cid"), {"cid": str(cid)})
                except Exception as e:
                    print(f"Error during cleanup of {cid}: {e}")
            db.commit()

    # ====================================================
    # GSTIN VALIDATION & PAN EXTRACTION TESTS
    # ====================================================

    def test_gstin_checksum_validation(self):
        """Test validation of GSTIN format and checksum digits"""
        # Valid state-coded GSTINs (checksum correct)
        assert customer_service.validate_gstin_checksum("27AADCB8374D1Z3") is True
        assert customer_service.validate_gstin_checksum("27AAJFU9603R1Z9") is True
        
        # Invalid GSTINs
        assert customer_service.validate_gstin_checksum("27AAJFU9603R1Z0") is False # Invalid check digit
        assert customer_service.validate_gstin_checksum("INVALIDGSTIN") is False
        assert customer_service.validate_gstin_checksum("") is False

    def test_pan_extraction_from_gstin(self):
        """Test correct extraction of 10-digit PAN from GSTIN"""
        gstin = "27AAJFU9603R1Z9"
        pan = customer_service.extract_pan_from_gstin(gstin)
        assert pan == "AAJFU9603R"

    # ====================================================
    # PAN ENCRYPTION & DECRYPTION TESTS
    # ====================================================

    def test_pan_encryption_decryption(self):
        """Test symmetric encryption of PAN at rest and decryption on load"""
        original_pan = "ABCDE1234F"
        
        encrypted_pan = customer_service.encrypt_pan(original_pan)
        assert encrypted_pan is not None
        assert encrypted_pan != original_pan
        
        decrypted_pan = customer_service.decrypt_pan(encrypted_pan)
        assert decrypted_pan == original_pan

    # ====================================================
    # CUSTOMER SERVICE BUSINESS LOGIC TESTS
    # ====================================================

    def test_create_customer_logic(self, db, seeded_tenant, cleanup_customers):
        """Test full create customer flow with addresses, contacts, fields, tags, and ledger opening balance"""
        company_id = seeded_tenant['company_id']
        user_id = seeded_tenant['user_id']
        
        # Ensure default chart of accounts is seeded
        customer_service.seed_default_chart_of_accounts(db, company_id)

        custom_code = f"CUST-TEST-{uuid4().hex[:8].upper()}"
        
        payload = CustomerCreateRequest(
            customer_code=custom_code,
            customer_name="Alpha Tech Corp",
            customer_type="business",
            display_name=f"Alpha Tech - {uuid4().hex[:4]}",
            currency="INR",
            email="info@alphatech.com",
            mobile="+919876543210",
            phone="+912224567890",
            gst_registration_type="regular",
            gstin="27AADCB8374D1Z3", # Valid GSTIN
            payment_terms="Net 30",
            credit_limit=Decimal("50000.00"),
            opening_balance=Decimal("12500.00"),
            opening_balance_type="debit",
            msme_status=True,
            msme_registration_no="MSME123456",
            cin="U72200MH2020PTC335544",
            invoice_delivery_preference="email",
            addresses=[
                CustomerAddressSchema(
                    address_type="billing",
                    attention="Finance Dept",
                    address_line1="123 Financial Expressway",
                    address_line2="Tech Park",
                    city="Mumbai",
                    state="Maharashtra",
                    zip_code="400001",
                    country="India",
                    phone="+912224567891"
                ),
                CustomerAddressSchema(
                    address_type="shipping",
                    attention="Warehouse Manager",
                    address_line1="Plot 45, Sector 2",
                    address_line2="MIDC Industrial Area",
                    city="Thane",
                    state="Maharashtra",
                    zip_code="400604",
                    country="India",
                    phone="+912225678912"
                )
            ],
            contacts=[
                CustomerContactSchema(
                    first_name="Rohan",
                    last_name="Sharma",
                    email="rohan@alphatech.com",
                    phone="+912224567892",
                    mobile="+919811122233",
                    designation="Accounts Lead",
                    is_primary=True
                )
            ],
            custom_fields=[
                CustomerCustomFieldSchema(
                    field_key="industry_vertical",
                    field_value="Logistics"
                )
            ],
            tags=["Enterprise", "Premium"]
        )

        # Call service to create customer
        customer = customer_service.create_customer(
            db=db,
            payload=payload,
            company_id=company_id,
            user_id=user_id
        )

        assert customer.customer_code == custom_code
        assert customer.gstin == "27AADCB8374D1Z3"
        # Verify PAN is encrypted in customer object (or decrypted on get)
        assert customer_service.decrypt_pan(customer.pan) == "AADCB8374D"
        
        # Add to cleanup queue
        cleanup_customers.append(str(customer.customer_id))

        # 1. Verify master customer and companion party exist
        customer_db = customer_service.get_customer(db, customer.customer_id, company_id)
        assert customer_db is not None
        assert customer_db.customer_name == "Alpha Tech Corp"
        assert customer_db.msme_status is True
        
        # 2. Verify addresses are present
        assert len(customer_db.addresses) == 2
        billing_addr = next(a for a in customer_db.addresses if a.address_type == "billing")
        assert billing_addr.city == "Mumbai"
        assert billing_addr.zip_code == "400001"

        # 3. Verify contacts & custom fields
        assert len(customer_db.contacts) == 1
        assert customer_db.contacts[0].first_name == "Rohan"
        assert len(customer_db.custom_fields) == 1
        assert customer_db.custom_fields[0].field_key == "industry_vertical"
        assert customer_db.custom_fields[0].field_value == "Logistics"

        # 4. Verify opening balance ledger double-entry
        # debit to A/R (1200), credit to Capital (3100)
        journal_row = db.execute(
            text("SELECT journal_id, status FROM journal_entries WHERE company_id = :company_id AND reference = :ref"),
            {"company_id": str(company_id), "ref": custom_code}
        ).fetchone()
        
        assert journal_row is not None
        journal_id, status = journal_row
        assert status == "posted"

        lines = db.execute(
            text("SELECT account_id, entry_type, amount FROM journal_entry_lines WHERE journal_id = :jid ORDER BY entry_type"),
            {"jid": str(journal_id)}
        ).fetchall()

        assert len(lines) == 2
        # Lines ordered by entry_type enum order: debit, credit
        debit_line = lines[0]
        credit_line = lines[1]

        assert debit_line.entry_type == "debit"
        assert float(debit_line.amount) == 12500.00
        
        assert credit_line.entry_type == "credit"
        assert float(credit_line.amount) == 12500.00

    def test_duplicate_customer_detection(self, db, seeded_tenant, cleanup_customers):
        """Test that duplicate Display Names, Customer Codes, or GSTINs raise ValueError"""
        company_id = seeded_tenant['company_id']
        user_id = seeded_tenant['user_id']
        
        code = f"CUST-TEST-{uuid4().hex[:8].upper()}"
        display_name = f"Duplicate Corp - {uuid4().hex[:4]}"
        gstin = "27AAJFU9603R1Z9"

        payload = CustomerCreateRequest(
            customer_code=code,
            customer_name="Duplicate Corp Ltd",
            customer_type="business",
            display_name=display_name,
            gstin=gstin,
            addresses=[]
        )

        c = customer_service.create_customer(db, payload, company_id, user_id)
        cleanup_customers.append(str(c.customer_id))

        # Try inserting with same code
        with pytest.raises(ValueError) as exc:
            payload_same_code = CustomerCreateRequest(
                customer_code=code,
                customer_name="Different Name",
                customer_type="business",
                display_name=f"Different Display - {uuid4().hex[:4]}",
                addresses=[]
            )
            customer_service.create_customer(db, payload_same_code, company_id, user_id)
        assert "already exists" in str(exc.value)

        # Try inserting with same display name
        with pytest.raises(ValueError) as exc:
            payload_same_name = CustomerCreateRequest(
                customer_name="Different Name Too",
                customer_type="business",
                display_name=display_name,
                addresses=[]
            )
            customer_service.create_customer(db, payload_same_name, company_id, user_id)
        assert "already exists" in str(exc.value)

        # Try inserting with same GSTIN
        with pytest.raises(ValueError) as exc:
            payload_same_gstin = CustomerCreateRequest(
                customer_name="Other Corp",
                customer_type="business",
                display_name=f"Other Corp - {uuid4().hex[:4]}",
                gstin=gstin,
                addresses=[]
            )
            customer_service.create_customer(db, payload_same_gstin, company_id, user_id)
        assert "already exists" in str(exc.value)

    # ====================================================
    # CSV IMPORT WIZARD TESTING
    # ====================================================

    def test_csv_import_wizard_logic(self, db, seeded_tenant, cleanup_customers):
        """Test bulk import of customers via mapped CSV with duplicate detection"""
        company_id = seeded_tenant['company_id']
        user_id = seeded_tenant['user_id']

        # Clean up any leftover customers/parties from previous test executions to guarantee a clean slate
        db.execute(text("""
            DELETE FROM customer_addresses WHERE customer_id IN (
                SELECT customer_id FROM customers WHERE customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
                OR email IN ('imported_a@test.com', 'imported_b@test.com')
                OR display_name = 'Invalid Row Cust'
            )
        """))
        db.execute(text("""
            DELETE FROM customer_contacts WHERE customer_id IN (
                SELECT customer_id FROM customers WHERE customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
                OR email IN ('imported_a@test.com', 'imported_b@test.com')
                OR display_name = 'Invalid Row Cust'
            )
        """))
        db.execute(text("""
            DELETE FROM customer_custom_fields WHERE customer_id IN (
                SELECT customer_id FROM customers WHERE customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
                OR email IN ('imported_a@test.com', 'imported_b@test.com')
                OR display_name = 'Invalid Row Cust'
            )
        """))
        db.execute(text("""
            DELETE FROM customer_tags WHERE customer_id IN (
                SELECT customer_id FROM customers WHERE customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
                OR email IN ('imported_a@test.com', 'imported_b@test.com')
                OR display_name = 'Invalid Row Cust'
            )
        """))
        # Set status to draft first to bypass ensure_journal_balance triggers on delete
        db.execute(text("""
            UPDATE journal_entries SET status = 'draft' WHERE reference IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
        """))
        db.execute(text("""
            DELETE FROM journal_entry_lines WHERE party_id IN (
                SELECT customer_id FROM customers WHERE customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
                OR email IN ('imported_a@test.com', 'imported_b@test.com')
                OR display_name = 'Invalid Row Cust'
            )
        """))
        db.execute(text("""
            DELETE FROM journal_entries WHERE reference IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
        """))
        
        # Capture customer IDs before deletion so we can delete their corresponding parties safely
        imp_customer_ids = db.scalars(text("""
            SELECT customer_id FROM customers WHERE customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
            OR email IN ('imported_a@test.com', 'imported_b@test.com')
            OR display_name = 'Invalid Row Cust'
        """)).all()
        
        db.execute(text("""
            DELETE FROM customers WHERE customer_code IN ('CUST-IMP-001', 'CUST-IMP-002', 'CUST-IMP-003', 'CUST-IMP-004')
            OR email IN ('imported_a@test.com', 'imported_b@test.com')
            OR display_name = 'Invalid Row Cust'
        """))
        
        if imp_customer_ids:
            db.execute(
                text("""
                    DELETE FROM parties WHERE party_type = 'customer' AND (
                        email IN ('imported_a@test.com', 'imported_b@test.com')
                        OR party_id IN :ids
                    )
                """),
                {"ids": tuple(str(cid) for cid in imp_customer_ids)}
            )
        else:
            db.execute(text("""
                DELETE FROM parties WHERE party_type = 'customer' AND email IN ('imported_a@test.com', 'imported_b@test.com')
            """))
        db.commit()
 
        csv_text = (
            "Name,Code,Type,GSTIN,Email,Mobile,OpeningBal,BalType\n"
            "Imported Customer A,CUST-IMP-001,business,27AADCB8374D1Z3,imported_a@test.com,+919999888877,1000,debit\n"
            "Imported Customer B,CUST-IMP-002,business,,imported_b@test.com,+919999888878,0,debit\n"
            "Duplicate Email Cust,CUST-IMP-003,business,,imported_a@test.com,+919999888879,0,debit\n"
            ",CUST-IMP-004,business,,,,,debit\n" # Missing Name
        )

        column_mapping = {
            "customer_name": "Name",
            "customer_code": "Code",
            "customer_type": "Type",
            "gstin": "GSTIN",
            "email": "Email",
            "mobile": "Mobile",
            "opening_balance": "OpeningBal",
            "opening_balance_type": "BalType"
        }

        report = customer_service.bulk_import_customers_csv(
            db=db,
            csv_text=csv_text,
            column_mapping=column_mapping,
            company_id=company_id,
            user_id=user_id
        )

        assert report["imported"] == 2
        assert report["duplicates"] == 1 # Duplicate Email (imported_a@test.com)
        assert report["failed"] == 1 # Missing name

        # Add imported customer IDs to cleanup queue
        imported_customers = db.scalars(
            text("SELECT customer_id FROM customers WHERE company_id = :cid AND customer_code IN ('CUST-IMP-001', 'CUST-IMP-002')"),
            {"cid": str(company_id)}
        ).all()
        for cid in imported_customers:
            cleanup_customers.append(str(cid))

    # ====================================================
    # FASTAPI ROUTER INTEGRATION TESTS
    # ====================================================

    def test_api_validate_gstin(self, client):
        """Test API endpoint POST /contacts/validate-gstin"""
        # Valid GSTIN
        response = client.post("/contacts/validate-gstin", json={"gstin": "27AADCB8374D1Z3"})
        assert response.status_code == 200
        assert response.json()["valid"] is True
        assert response.json()["pan"] == "AADCB8374D"

        # Invalid GSTIN
        response = client.post("/contacts/validate-gstin", json={"gstin": "27AAJFU9603R1Z0"})
        assert response.status_code == 200
        assert response.json()["valid"] is False

    def test_api_prefill_gstin(self, client):
        """Test API endpoint POST /contacts/prefill-gstin"""
        # Valid GSTIN
        response = client.post("/contacts/prefill-gstin", json={"gstin": "27AAJFU9603R1Z9"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["legal_name"] == "OptiReach Enterprise Solutions Private Limited"
        assert data["data"]["gst_status"] == "Active"

        # Invalid GSTIN
        response = client.post("/contacts/prefill-gstin", json={"gstin": "INVALIDGSTIN"})
        assert response.status_code == 400

    def test_api_crud_flow(self, client, valid_headers, db, seeded_tenant, cleanup_customers):
        """Test complete API CRUD flow through HTTP client endpoints"""
        company_id = seeded_tenant['company_id']
        code = f"CUST-API-{uuid4().hex[:8].upper()}"

        # 1. POST Create Customer
        create_payload = {
            "customer_code": code,
            "customer_name": "API Tech Corp",
            "customer_type": "business",
            "display_name": f"API Tech - {uuid4().hex[:4]}",
            "currency": "INR",
            "email": "api_contact@apitech.com",
            "mobile": "+918888777766",
            "gst_registration_type": "unregistered",
            "addresses": [
                {
                    "address_type": "billing",
                    "attention": "API Finance Dept",
                    "address_line1": "456 Endpoint Lane",
                    "city": "Pune",
                    "state": "Maharashtra",
                    "zip_code": "411001",
                    "country": "India",
                    "phone": "+912012345678"
                }
            ],
            "contacts": [],
            "custom_fields": [],
            "tags": ["API-Client"]
        }

        response = client.post(
            "/contacts",
            json=create_payload,
            headers=valid_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["customer_code"] == code
        assert data["customer_name"] == "API Tech Corp"
        assert len(data["addresses"]) == 1
        
        contact_id = data["contact_id"]
        cleanup_customers.append(contact_id)

        # 2. GET List Customers
        response = client.get(
            "/contacts",
            params={"q": "API Tech Corp"},
            headers=valid_headers
        )
        assert response.status_code == 200
        list_data = response.json()
        assert len(list_data) >= 1
        assert any(c["contact_id"] == contact_id for c in list_data)

        # 3. GET Customer Details
        response = client.get(
            f"/contacts/{contact_id}",
            headers=valid_headers
        )
        assert response.status_code == 200
        details_data = response.json()
        assert details_data["contact_id"] == contact_id
        assert details_data["addresses"][0]["attention"] == "API Finance Dept"

        # 4. PATCH Update Customer
        update_payload = {
            "customer_name": "API Tech Corp Updated",
            "display_name": f"API Tech Updated - {uuid4().hex[:4]}",
            "addresses": [
                {
                    "address_type": "billing",
                    "attention": "API Accounts Dept",
                    "address_line1": "456 Endpoint Lane",
                    "city": "Pune",
                    "state": "Maharashtra",
                    "zip_code": "411001",
                    "country": "India",
                    "phone": "+912012345678"
                }
            ]
        }
        response = client.patch(
            f"/contacts/{contact_id}",
            json=update_payload,
            headers=valid_headers
        )
        assert response.status_code == 200
        updated_data = response.json()
        assert updated_data["customer_name"] == "API Tech Corp Updated"
        assert updated_data["addresses"][0]["attention"] == "API Accounts Dept"

        # 5. DELETE Soft Delete Customer
        response = client.delete(
            f"/contacts/{contact_id}",
            headers=valid_headers
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Check soft delete hides it from lists and details
        response = client.get(
            f"/contacts/{contact_id}",
            headers=valid_headers
        )
        assert response.status_code == 404
