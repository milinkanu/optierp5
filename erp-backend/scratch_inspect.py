import os
import sys
from uuid import UUID, uuid4
from datetime import date

# Set environment variables for testing database mode
os.environ["FINOPS_USE_DATABASE"] = "true"
os.environ["DATABASE_URL"] = "postgresql://finops:finops_password@localhost:5432/finops"

from sqlalchemy import text
from utils.db_invoice import engine
from models.payments import PaymentCreateRequest, PaymentAllocationCreate
from services.payment_service import create_payment

def inspect_db_and_test_payment():
    print("--- STARTING DB INSPECTION AND PAYMENT TEST ---")
    
    with engine.begin() as conn:
        # Get a user and company
        user_row = conn.execute(text("SELECT user_id, email, company_id FROM users WHERE email = 'admin@test.com'")).fetchone()
        if not user_row:
            print("admin@test.com user not found in database!")
            return
        
        user_id = user_row[0]
        email = user_row[1]
        company_id = user_row[2]
        print(f"Found User: {email} | ID: {user_id} | Company ID: {company_id}")
        
        # Set tenant session parameter
        conn.execute(text("SET LOCAL app.current_company = :company_id"), {'company_id': str(company_id)})
        
        # Let's see if there is an invoice in the DB
        invoice_row = conn.execute(text("SELECT invoice_id, invoice_number, invoice_grand_total, paid_amount, balance_due FROM invoices WHERE company_id = :company_id LIMIT 1"), {'company_id': str(company_id)}).fetchone()
        if not invoice_row:
            print("No invoices found in database! Let's find any invoice in the DB regardless of tenant RLS (just to test).")
            # Clear RLS or query directly as postgres superuser if possible, but let's query invoices first
            invoice_row = conn.execute(text("SELECT invoice_id, invoice_number, invoice_grand_total, paid_amount, balance_due, company_id FROM invoices LIMIT 1")).fetchone()
            if not invoice_row:
                print("No invoices exist at all in database. We will need to create one first.")
                return
            else:
                # Use the company_id from that invoice to satisfy RLS
                company_id = invoice_row[5]
                conn.execute(text("SET LOCAL app.current_company = :company_id"), {'company_id': str(company_id)})
                
        invoice_id = invoice_row[0]
        invoice_number = invoice_row[1]
        grand_total = invoice_row[2]
        paid_amount = invoice_row[3]
        balance_due = invoice_row[4]
        print(f"Found Invoice: {invoice_number} | ID: {invoice_id} | Grand Total: {grand_total} | Paid: {paid_amount} | Balance: {balance_due}")
        
        # Let's find a valid party (customer) for the payment
        party_row = conn.execute(text("SELECT party_id FROM parties WHERE company_id = :company_id LIMIT 1"), {'company_id': str(company_id)}).fetchone()
        if not party_row:
            party_id = uuid4()
            print(f"No party found, generated random party_id: {party_id}")
        else:
            party_id = party_row[0]
            print(f"Found Party: {party_id}")

    # Now let's try creating a payment for this invoice using the service!
    # Amount is 10.00
    payload = PaymentCreateRequest(
        amount=10.00,
        payment_date=date.today(),
        payment_mode="Cash",
        reference_number="REF-TEST-DB-1",
        notes="DB test payment",
        party_id=party_id,
        allocations=[
            PaymentAllocationCreate(
                invoice_id=invoice_id,
                amount=10.00
            )
        ]
    )
    
    print("\nAttempting to call create_payment...")
    try:
        payment_resp = create_payment(payload, company_id=company_id, user_id=user_id)
        print("SUCCESS! Payment recorded successfully in DB mode!")
        print(f"Payment ID: {payment_resp.payment_id}")
        print(f"Payment Number: {payment_resp.payment_number}")
        print(f"Unused Balance: {payment_resp.unused_balance}")
        print(f"Allocations Count: {len(payment_resp.allocations)}")
        for alloc in payment_resp.allocations:
            print(f"  - Allocated {alloc.allocated_amount} to invoice {alloc.invoice_number}")
            
        # Verify updated invoice details from DB
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL app.current_company = :company_id"), {'company_id': str(company_id)})
            updated_inv = conn.execute(text("SELECT status, paid_amount, balance_due FROM invoices WHERE invoice_id = :invoice_id"), {'invoice_id': str(invoice_id)}).fetchone()
            print(f"\nUpdated Invoice Status in DB: {updated_inv[0]} | Paid: {updated_inv[1]} | Balance Due: {updated_inv[2]}")
            
            # Let's inspect generated journal entry lines
            journal = conn.execute(text("SELECT journal_id, journal_number, status, description FROM journal_entries WHERE transaction_id = :payment_id"), {'payment_id': str(payment_resp.payment_id)}).fetchone()
            if journal:
                print(f"Generated Journal Entry: {journal[1]} | Status: {journal[2]} | Description: {journal[3]}")
                lines = conn.execute(text("SELECT entry_type, amount, account_id, description FROM journal_entry_lines WHERE journal_id = :journal_id"), {'journal_id': str(journal[0])}).fetchall()
                for line in lines:
                    print(f"  - Line Type: {line[0]} | Amount: {line[1]} | Account ID: {line[2]} | Desc: {line[3]}")
            else:
                print("No journal entry was generated!")
                
    except Exception as e:
        print("\nERROR ENCOUNTERED during payment creation:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_db_and_test_payment()
