"""
Integration and flow tests for the new FinOps modules:
- Recurring Invoices
- Delivery Challans
- Payments Received (including Invoice integration)
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import date, timedelta
from decimal import Decimal

from main import app


class TestFinOpsNewModules:
    """Test suite for Recurring Invoices, Delivery Challans, and Payments Received"""

    @pytest.fixture(autouse=True)
    def force_mock_mode(self, monkeypatch):
        """Force FINOPS_USE_DATABASE=false for these tests"""
        monkeypatch.setenv("FINOPS_USE_DATABASE", "false")

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    @pytest.fixture
    def valid_headers(self):
        """Create valid headers for requests"""
        from services.common import create_access_token
        
        company_id = uuid4()
        user_id = uuid4()
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

    # ====================================================
    # RECURRING INVOICES TESTS
    # ====================================================

    def test_recurring_invoices_flow(self, client, valid_headers):
        """Test the CRUD and life-cycle flow for Recurring Invoices"""
        billing_party_id = uuid4()
        account_id = uuid4()

        # 1. Create recurring profile
        payload = {
            "profile_name": "Monthly SaaS Plan",
            "billing_party_id": str(billing_party_id),
            "frequency": "monthly",
            "start_date": str(date.today()),
            "currency": "INR",
            "exchange_rate": 1.0,
            "items": [
                {
                    "description": "Premium subscription tier",
                    "quantity": 1.0000,
                    "unit_price": 999.0000,
                    "discount_amount": 0.00,
                    "gst_rate": 18.00,
                    "account_id": str(account_id)
                }
            ]
        }

        response = client.post(
            "/recurring-invoices",
            json=payload,
            headers=valid_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "profile_id" in data
        assert data["profile_name"] == "Monthly SaaS Plan"
        assert data["status"] == "active"
        assert len(data["items"]) == 1
        
        profile_id = data["profile_id"]

        # 2. List recurring profiles
        response = client.get(
            "/recurring-invoices",
            headers=valid_headers
        )
        assert response.status_code == 200
        profiles = response.json()
        assert any(p["profile_id"] == profile_id for p in profiles)

        # 3. Get recurring profile by ID
        response = client.get(
            f"/recurring-invoices/{profile_id}",
            headers=valid_headers
        )
        assert response.status_code == 200
        assert response.json()["profile_id"] == profile_id

        # 4. Update status to paused
        response = client.put(
            f"/recurring-invoices/{profile_id}/status?status_val=paused",
            headers=valid_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

        # 5. Trigger manual invoice generation
        response = client.post(
            f"/recurring-invoices/{profile_id}/trigger?run_date={date.today()}",
            headers=valid_headers
        )
        assert response.status_code == 200
        gen_data = response.json()
        assert gen_data["success"] is True
        assert "generated_invoice_id" in gen_data

        # 6. Retrieve execution logs
        response = client.get(
            f"/recurring-invoices/{profile_id}/logs",
            headers=valid_headers
        )
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) >= 1
        assert logs[0]["status"] == "success"

    # ====================================================
    # DELIVERY CHALLANS TESTS
    # ====================================================

    def test_delivery_challans_flow(self, client, valid_headers):
        """Test the CRUD and convert-to-invoice flow for Delivery Challans"""
        billing_party_id = uuid4()
        account_id = uuid4()

        # 1. Create Delivery Challan
        payload = {
            "challan_type": "supply_on_approval",
            "challan_date": str(date.today()),
            "billing_party_id": str(billing_party_id),
            "reference_number": "REF-CH-777",
            "currency": "INR",
            "exchange_rate": 1.0,
            "transport_mode": "road",
            "vehicle_number": "KA-01-MJ-1234",
            "place_of_supply": "Karnataka",
            "customer_notes": "Sample delivery on approval",
            "items": [
                {
                    "description": "Industrial Pump Alpha",
                    "quantity": 2.0000,
                    "unit_price": 5000.0000,
                    "discount_amount": 500.00,
                    "gst_rate": 18.00,
                    "account_id": str(account_id)
                }
            ]
        }

        response = client.post(
            "/delivery-challans",
            json=payload,
            headers=valid_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "delivery_challan_id" in data
        assert data["challan_type"] == "supply_on_approval"
        assert data["status"] == "open"
        assert data["grand_total"] == float((2 * 5000 - 500) * 1.18)
        
        challan_id = data["delivery_challan_id"]

        # 2. List Delivery Challans
        response = client.get(
            "/delivery-challans",
            headers=valid_headers
        )
        assert response.status_code == 200
        challans = response.json()
        assert any(c["delivery_challan_id"] == challan_id for c in challans)

        # 3. Get Delivery Challan by ID
        response = client.get(
            f"/delivery-challans/{challan_id}",
            headers=valid_headers
        )
        assert response.status_code == 200
        assert response.json()["delivery_challan_id"] == challan_id

        # 4. Fetch Delivery Challan PDF Receipt
        response = client.get(
            f"/delivery-challans/{challan_id}/pdf",
            headers=valid_headers
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/pdf"
        assert len(response.content) > 0

        # 5. Convert Delivery Challan to Invoice
        response = client.post(
            f"/delivery-challans/{challan_id}/convert",
            headers=valid_headers
        )
        assert response.status_code == 200
        inv_data = response.json()
        assert "invoice_id" in inv_data
        assert inv_data["status"] == "draft"
        assert inv_data["invoice_grand_total"] == float((2 * 5000 - 500) * 1.18)

    # ====================================================
    # PAYMENTS RECEIVED & RECORD PAYMENT TESTS
    # ====================================================

    def test_payments_and_invoice_integration_flow(self, client, valid_headers):
        """Test recording payments received, allocations, and status updates on invoices"""
        billing_party_id = uuid4()
        account_id = uuid4()
        settlement_bank_account_id = uuid4()

        # 1. Create a draft invoice to pay
        payload_inv = {
            "invoice_type": "sales_invoice",
            "invoice_date": str(date.today()),
            "due_date": str(date.today() + timedelta(days=15)),
            "billing_party_id": str(billing_party_id),
            "currency": "INR",
            "exchange_rate": 1.0,
            "items": [
                {
                    "description": "Consulting retainer fee",
                    "hsn_sac": "998311",
                    "account_id": str(account_id),
                    "quantity": 1.0,
                    "unit_price": 1000.00,
                    "discount_amount": 0.0,
                    "gst_rate": 18.00
                }
            ]
        }

        response = client.post(
            "/invoices",
            json=payload_inv,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )
        assert response.status_code == 200
        inv_data = response.json()
        invoice_id = inv_data["invoice_id"]
        assert inv_data["balance_due"] == 1180.0
        assert inv_data["status"] == "draft"

        # 2. Record a partial payment directly on the invoice
        partial_payment_payload = {
            "amount": 500.00,
            "payment_date": str(date.today()),
            "payment_mode": "UPI",
            "reference_number": "UPI-888-2993",
            "notes": "Partial invoice prepayment"
        }

        response = client.post(
            f"/invoices/{invoice_id}/record-payment",
            json=partial_payment_payload,
            headers=valid_headers
        )
        assert response.status_code == 200
        updated_inv = response.json()
        assert updated_inv["paid_amount"] == 500.0
        assert updated_inv["balance_due"] == 680.0
        assert updated_inv["status"] == "partial"

        # 3. Fetch payment allocation history for this invoice
        response = client.get(
            f"/invoices/{invoice_id}/payments",
            headers=valid_headers
        )
        assert response.status_code == 200
        allocations = response.json()
        assert len(allocations) == 1
        assert allocations[0]["allocated_amount"] == 500.0

        # 4. Record a full payment to pay off the remaining balance
        full_payment_payload = {
            "amount": 680.00,
            "payment_date": str(date.today()),
            "payment_mode": "Bank Transfer",
            "settlement_bank_account_id": str(settlement_bank_account_id),
            "reference_number": "FT-9911-3004",
            "notes": "Full balance settlement"
        }

        response = client.post(
            f"/invoices/{invoice_id}/record-payment",
            json=full_payment_payload,
            headers=valid_headers
        )
        assert response.status_code == 200
        updated_inv_full = response.json()
        assert updated_inv_full["paid_amount"] == 1180.0
        assert updated_inv_full["balance_due"] == 0.0
        assert updated_inv_full["status"] == "paid"

        # 5. List all payments received under the company
        response = client.get(
            "/payments",
            headers=valid_headers
        )
        assert response.status_code == 200
        payments = response.json()
        assert len(payments) >= 2
        
        # Verify one of the payments has allocations matching the invoice
        payment_id = payments[0]["payment_id"]

        # 6. Retrieve a specific payment receipt details
        response = client.get(
            f"/payments/{payment_id}",
            headers=valid_headers
        )
        assert response.status_code == 200
        single_payment = response.json()
        assert single_payment["payment_id"] == payment_id

        # 7. Fetch payment receipt PDF
        response = client.get(
            f"/payments/{payment_id}/pdf",
            headers=valid_headers
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/pdf"
        assert len(response.content) > 0
