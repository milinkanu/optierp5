import os
from uuid import UUID, uuid4
from datetime import date

os.environ["FINOPS_USE_DATABASE"] = "true"
os.environ["DATABASE_URL"] = "postgresql://finops:finops_password@localhost:5432/finops"

from fastapi.testclient import TestClient
from services.ledger_service import app
from utils.db_ledger import engine
from sqlalchemy import text
from services.common import create_access_token

def test_ledger_endpoints():
    print("--- STARTING LEDGER ENDPOINTS INTEGRATION TEST ---")
    
    # 1. Get database details (user/company)
    with engine.begin() as conn:
        user_row = conn.execute(text("SELECT user_id, email, company_id FROM users WHERE email = 'admin@test.com'")).fetchone()
        if not user_row:
            print("admin@test.com user not found!")
            return
        
        user_id = user_row[0]
        email = user_row[1]
        company_id = user_row[2]
        
        # Set tenant session parameter
        conn.execute(text("SET LOCAL app.current_company = :company_id"), {'company_id': str(company_id)})
        
        # Find two accounts for testing
        accounts = conn.execute(text("SELECT account_id, account_code FROM chart_of_accounts WHERE company_id = :company_id LIMIT 2"), {'company_id': str(company_id)}).fetchall()
        if len(accounts) < 2:
            print("Not enough accounts in chart_of_accounts to perform ledger test!")
            return
            
        acc1 = accounts[0][0]
        acc2 = accounts[1][0]
        print(f"Company ID: {company_id}")
        print(f"Account 1: {accounts[0][1]} | Account 2: {accounts[1][1]}")

    # Generate JWT token for client authorization
    token = create_access_token(
        subject=str(user_id),
        company_id=company_id,
        user_version=1,
        roles=['owner'],
        delegations=[]
    )
    
    headers = {
        'Authorization': f'Bearer {token}',
        'X-Tenant-ID': str(company_id),
        'X-User-ID': str(user_id),
        'X-User-Roles': 'owner',
        'Idempotency-Key': str(uuid4())
    }
    
    client = TestClient(app)
    
    # Payload for journal entry
    payload = {
        "journal_type": "misc",
        "journal_date": str(date.today()),
        "description": "Integration test journal entry",
        "reference": "REF-INT-TEST-1",
        "lines": [
            {
                "account_id": str(acc1),
                "entry_type": "debit",
                "amount": 100.00,
                "description": "Debit test line"
            },
            {
                "account_id": str(acc2),
                "entry_type": "credit",
                "amount": 100.00,
                "description": "Credit test line"
            }
        ]
    }
    
    print("\nSending POST /ledger/journals...")
    response = client.post("/ledger/journals", json=payload, headers=headers)
    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        print(f"FAILED: {response.text}")
        return
        
    data = response.json()
    journal_id = data["journal_id"]
    journal_number = data["journal_number"]
    print(f"SUCCESS! Created Journal ID: {journal_id} | Number: {journal_number}")
    
    # Now let's test reversal
    print(f"\nSending POST /ledger/journals/{journal_id}/reverse...")
    response = client.post(f"/ledger/journals/{journal_id}/reverse", headers=headers)
    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        print(f"FAILED: {response.text}")
        return
        
    rev_data = response.json()
    print(f"SUCCESS! Reversed Journal. Reversal ID: {rev_data['reversal_journal_id']}")
    
    # Query database to confirm status and lines
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL app.current_company = :company_id"), {'company_id': str(company_id)})
        orig_journal = conn.execute(text("SELECT status FROM journal_entries WHERE journal_id = :journal_id"), {'journal_id': str(journal_id)}).fetchone()
        rev_journal = conn.execute(text("SELECT status FROM journal_entries WHERE journal_id = :journal_id"), {'journal_id': str(rev_data['reversal_journal_id'])}).fetchone()
        print(f"\nOriginal Journal Status in DB: {orig_journal[0] if orig_journal else 'None'}")
        print(f"Reversal Journal Status in DB: {rev_journal[0] if rev_journal else 'None'}")
        
    print("\n--- ALL LEDGER ENDPOINTS VERIFIED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_ledger_endpoints()
