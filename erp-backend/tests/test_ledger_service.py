"""
Integration tests for ledger_service.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import date

from services.ledger_service import app


class TestLedgerService:
    """Test ledger service endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    @pytest.fixture
    def seeded_tenant(self):
        """Fetch seeded company_id, user_id, two account_ids, and a party_id from db"""
        from utils.db_ledger import engine
        from sqlalchemy import text
        
        with engine.begin() as conn:
            user_row = conn.execute(text("SELECT user_id, company_id FROM users WHERE email = 'admin@test.com'")).fetchone()
            if not user_row:
                pytest.skip("No seeded admin@test.com user found in database")
            
            user_id, company_id = user_row
            
            # Fetch two accounts
            accounts = conn.execute(
                text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id LIMIT 2"),
                {'company_id': str(company_id)}
            ).fetchall()
            
            if len(accounts) < 2:
                pytest.skip("Not enough seeded accounts in chart_of_accounts")
                
            # Fetch a party
            party_row = conn.execute(
                text("SELECT party_id FROM parties WHERE company_id = :company_id LIMIT 1"),
                {'company_id': str(company_id)}
            ).fetchone()
            party_id = party_row[0] if party_row else None
            
            # Seed a transaction to prevent FK violation
            transaction_id = uuid4()
            txn_number = f"TXN-{uuid4().hex[:8].upper()}"
            conn.execute(text("SET LOCAL app.current_company = :company_id"), {'company_id': str(company_id)})
            conn.execute(
                text("""
                    INSERT INTO transactions (
                        transaction_id, company_id, txn_type, txn_number, txn_date, 
                        fiscal_year, period, subtotal, gst_breakdown, grand_total, 
                        status, created_by, updated_by
                    ) VALUES (
                        :transaction_id, :company_id, 'payment', :txn_number, :txn_date, 
                        '2026-2027', 'May 2026', 1000.0, '{}'::jsonb, 1000.0, 
                        'draft', :created_by, :updated_by
                    )
                """),
                {
                    'transaction_id': str(transaction_id),
                    'company_id': str(company_id),
                    'txn_number': txn_number,
                    'txn_date': date.today(),
                    'created_by': str(user_id),
                    'updated_by': str(user_id)
                }
            )
            
            return {
                'user_id': user_id,
                'company_id': company_id,
                'account_id_1': accounts[0][0],
                'account_id_2': accounts[1][0],
                'party_id': party_id,
                'transaction_id': transaction_id
            }

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

    def test_create_journal_entry_valid(self, client, valid_headers, seeded_tenant):
        """Test creating a valid journal entry"""
        account_id = seeded_tenant['account_id_1']
        account_id_2 = seeded_tenant['account_id_2']

        payload = {
            'journal_type': 'opening',
            'journal_date': str(date.today()),
            'reference': 'JNL-001',
            'description': 'Opening Balances',
            'lines': [
                {
                    'account_id': str(account_id),
                    'entry_type': 'debit',
                    'amount': 1000.0,
                    'description': 'Opening balance'
                },
                {
                    'account_id': str(account_id_2),
                    'entry_type': 'credit',
                    'amount': 1000.0,
                    'description': 'Opening balance offset'
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'journal_id' in data
        assert 'journal_number' in data
        assert data['status'] == 'posted'

    def test_create_journal_with_multiple_lines(self, client, valid_headers, seeded_tenant):
        """Test creating journal with multiple lines"""
        account_id_1 = seeded_tenant['account_id_1']
        account_id_2 = seeded_tenant['account_id_2']

        payload = {
            'journal_type': 'misc',
            'journal_date': str(date.today()),
            'description': 'Multi-line entry',
            'lines': [
                {
                    'account_id': str(account_id_1),
                    'entry_type': 'debit',
                    'amount': 500.0,
                    'description': 'Debit entry'
                },
                {
                    'account_id': str(account_id_2),
                    'entry_type': 'credit',
                    'amount': 500.0,
                    'description': 'Credit entry'
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200

    def test_create_journal_with_party_and_transaction(self, client, valid_headers, seeded_tenant):
        """Test creating journal with party and transaction references"""
        account_id = seeded_tenant['account_id_1']
        account_id_2 = seeded_tenant['account_id_2']
        party_id = seeded_tenant['party_id']
        transaction_id = seeded_tenant['transaction_id']

        payload = {
            'journal_type': 'payment',
            'journal_date': str(date.today()),
            'reference': 'PAY-001',
            'transaction_id': str(transaction_id),
            'lines': [
                {
                    'account_id': str(account_id),
                    'entry_type': 'credit',
                    'amount': 1000.0,
                    'party_id': str(party_id) if party_id else None,
                    'description': 'Payment to vendor'
                },
                {
                    'account_id': str(account_id_2),
                    'entry_type': 'debit',
                    'amount': 1000.0,
                    'description': 'Debit account offset'
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'journal_id' in data

    def test_create_journal_missing_idempotency_key(self, client, valid_headers):
        """Test creating journal without idempotency key"""
        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': 1000.0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers=valid_headers
        )

        # Should fail because idempotency key is required
        assert response.status_code == 422

    def test_create_journal_invalid_amount(self, client, valid_headers):
        """Test creating journal with invalid amount"""
        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': 0.0  # Should be > 0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        # Should fail validation
        assert response.status_code == 422

    def test_create_journal_negative_amount(self, client, valid_headers):
        """Test creating journal with negative amount"""
        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': -100.0  # Should be > 0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 422

    def test_journal_response_has_required_fields(self, client, valid_headers, seeded_tenant):
        """Test that journal response has all required fields"""
        payload = {
            'journal_type': 'misc',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(seeded_tenant['account_id_1']),
                    'entry_type': 'debit',
                    'amount': 100.0
                },
                {
                    'account_id': str(seeded_tenant['account_id_2']),
                    'entry_type': 'credit',
                    'amount': 100.0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        data = response.json()
        assert 'journal_id' in data
        assert 'company_id' in data
        assert 'journal_number' in data
        assert 'status' in data
        assert 'created_at' in data
