"""
Integration tests for Quotes and Sales Orders endpoints in DB-bypass/mock mode
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import date, timedelta

from main import app


class TestQuotesSalesOrdersService:
    """Test quotes and sales orders endpoints"""

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
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

    def test_create_quote(self, client, valid_headers):
        """Test creating a quote"""
        billing_party_id = uuid4()
        payload = {
            'quote_number': 'QT-2026-00001',
            'quote_date': str(date.today()),
            'expiry_date': str(date.today() + timedelta(days=15)),
            'billing_party_id': str(billing_party_id),
            'currency': 'INR',
            'exchange_rate': 1.0,
            'discount_percentage': 5.0,
            'discount_amount': 0.0,
            'adjustment': 0.0,
            'items': [
                {
                    'description': 'Consulting Services',
                    'quantity': 10.0,
                    'unit_price': 100.0,
                    'discount_amount': 0.0,
                    'gst_rate': 18.0,
                    'tds_rate': 0.0,
                    'tcs_rate': 0.0
                }
            ]
        }

        response = client.post(
            '/quotes',
            json=payload,
            headers=valid_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert 'quote_id' in data
        assert data['quote_number'] == 'QT-2026-00001'
        assert data['subtotal'] == 1000.0
        assert data['total_gst'] == 180.0
        assert data['grand_total'] == 1180.0
        assert len(data['items']) == 1

    def test_list_quotes(self, client, valid_headers):
        """Test listing quotes"""
        response = client.get(
            '/quotes',
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'quote_id' in data[0]

    def test_get_quote(self, client, valid_headers):
        """Test getting a quote"""
        quote_id = uuid4()
        response = client.get(
            f'/quotes/{quote_id}',
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['quote_id'] == str(quote_id)

    def test_update_quote(self, client, valid_headers):
        """Test updating a quote"""
        quote_id = uuid4()
        payload = {
            'quote_number': 'QT-2026-UPDATED',
            'status': 'sent'
        }

        response = client.patch(
            f'/quotes/{quote_id}',
            json=payload,
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['quote_id'] == str(quote_id)
        assert data['quote_number'] == 'QT-2026-UPDATED'
        assert data['status'] == 'sent'

    def test_delete_quote(self, client, valid_headers):
        """Test deleting a quote"""
        quote_id = uuid4()
        response = client.delete(
            f'/quotes/{quote_id}',
            headers=valid_headers
        )

        assert response.status_code == 204

    def test_convert_quote_to_so(self, client, valid_headers):
        """Test converting quote to sales order"""
        quote_id = uuid4()
        response = client.post(
            f'/quotes/{quote_id}/convert-so',
            headers=valid_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert 'sales_order_id' in data
        assert 'sales_order_number' in data

    def test_convert_quote_to_invoice(self, client, valid_headers):
        """Test converting quote to invoice"""
        quote_id = uuid4()
        response = client.post(
            f'/quotes/{quote_id}/convert-invoice',
            headers=valid_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert 'invoice_id' in data

    def test_create_sales_order(self, client, valid_headers):
        """Test creating a sales order"""
        billing_party_id = uuid4()
        payload = {
            'sales_order_number': 'SO-2026-00001',
            'sales_order_date': str(date.today()),
            'expected_shipment_date': str(date.today() + timedelta(days=30)),
            'billing_party_id': str(billing_party_id),
            'currency': 'INR',
            'exchange_rate': 1.0,
            'discount_percentage': 0.0,
            'discount_amount': 0.0,
            'adjustment': 10.0,
            'items': [
                {
                    'description': 'Product Widget A',
                    'quantity': 5.0,
                    'unit_price': 200.0,
                    'discount_amount': 50.0,
                    'gst_rate': 18.0,
                    'tds_rate': 0.0,
                    'tcs_rate': 0.0
                }
            ]
        }

        response = client.post(
            '/sales-orders',
            json=payload,
            headers=valid_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert 'sales_order_id' in data
        assert data['sales_order_number'] == 'SO-2026-00001'
        assert data['subtotal'] == 950.0 # (5 * 200) - 50 = 950
        assert data['total_gst'] == 171.0 # 950 * 0.18 = 171.0
        assert data['grand_total'] == 1131.0 # 950 + 171.0 + 10 = 1131.0
        assert len(data['items']) == 1

    def test_list_sales_orders(self, client, valid_headers):
        """Test listing sales orders"""
        response = client.get(
            '/sales-orders',
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert 'sales_order_id' in data[0]

    def test_get_sales_order(self, client, valid_headers):
        """Test getting a sales order"""
        sales_order_id = uuid4()
        response = client.get(
            f'/sales-orders/{sales_order_id}',
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['sales_order_id'] == str(sales_order_id)

    def test_update_sales_order(self, client, valid_headers):
        """Test updating a sales order"""
        sales_order_id = uuid4()
        payload = {
            'sales_order_number': 'SO-2026-UPDATED',
            'status': 'confirmed'
        }

        response = client.patch(
            f'/sales-orders/{sales_order_id}',
            json=payload,
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['sales_order_id'] == str(sales_order_id)
        assert data['sales_order_number'] == 'SO-2026-UPDATED'
        assert data['status'] == 'confirmed'

    def test_delete_sales_order(self, client, valid_headers):
        """Test deleting a sales order"""
        sales_order_id = uuid4()
        response = client.delete(
            f'/sales-orders/{sales_order_id}',
            headers=valid_headers
        )

        assert response.status_code == 204

    def test_convert_so_to_invoice(self, client, valid_headers):
        """Test converting sales order to invoice"""
        sales_order_id = uuid4()
        response = client.post(
            f'/sales-orders/{sales_order_id}/convert-invoice',
            headers=valid_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert 'invoice_id' in data
