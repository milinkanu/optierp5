import os
from uuid import UUID, uuid4
from datetime import date

os.environ["FINOPS_USE_DATABASE"] = "true"
os.environ["DATABASE_URL"] = "postgresql://finops:finops_password@localhost:5432/finops"

from sqlalchemy import text
from utils.db_ledger import engine

def test_ledger_direct_insert():
    print("--- STARTING DIRECT LEDGER INSERT TEST ---")
    
    with engine.begin() as conn:
        # Get a user and company
        user_row = conn.execute(text("SELECT user_id, email, company_id FROM users WHERE email = 'admin@test.com'")).fetchone()
        if not user_row:
            print("admin@test.com user not found!")
            return
        
        user_id = user_row[0]
        company_id = user_row[2]
        print(f"Company ID: {company_id}")
        
        # Set tenant session parameter
        conn.execute(text("SET LOCAL app.current_company = :company_id"), {'company_id': str(company_id)})
        
        # Let's find two asset or expense accounts
        accounts = conn.execute(text("SELECT account_id FROM chart_of_accounts WHERE company_id = :company_id LIMIT 2"), {'company_id': str(company_id)}).fetchall()
        if len(accounts) < 2:
            print("Not enough accounts to test!")
            return
        
        acc1 = accounts[0][0]
        acc2 = accounts[1][0]
        
        journal_id = uuid4()
        journal_number = f"JRN-TEST-{str(uuid4())[:8].upper()}"
        
        print("\nAttempting direct posted INSERT into journal_entries...")
        try:
            conn.execute(
                text(
                    "INSERT INTO journal_entries (journal_id, company_id, journal_number, journal_type, journal_date, description, reference, transaction_id, status, created_by, updated_by, created_at, updated_at)"
                    " VALUES (:journal_id, :company_id, :journal_number, 'misc', :journal_date, :description, :reference, :transaction_id, 'posted', :created_by, :updated_by, now(), now())"
                ),
                {
                    "journal_id": str(journal_id),
                    "company_id": str(company_id),
                    "journal_number": journal_number,
                    "journal_date": date.today(),
                    "description": "Test Ledger Direct Insert",
                    "reference": "REF-LEDGER-1",
                    "transaction_id": None,
                    "created_by": str(user_id),
                    "updated_by": str(user_id)
                }
            )
            print("SUCCESS! Wait, how did it succeed without lines if status is posted?")
        except Exception as e:
            print("EXPECTED FAILURE encountered:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_ledger_direct_insert()
