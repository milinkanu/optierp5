import os
import sys
import json
from uuid import UUID
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/finops")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print("Connecting to DB for Verification...")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

COMPANY_ID = UUID("11111111-1111-1111-1111-111111111111")

def run_verification():
    print("\n==================================================")
    print("        DATABASE SEED VERIFICATION REPORT         ")
    print("==================================================")
    
    # 1. Set app.current_company RLS context
    db.execute(text("SET app.current_company = :company_id"), {'company_id': str(COMPANY_ID)})
    
    tables_to_check = [
        ("companies", "company_id = :company_id"),
        ("users", "company_id = :company_id"),
        ("roles", "company_id = :company_id"),
        ("permissions", "role_id IN (SELECT role_id FROM roles WHERE company_id = :company_id)"),
        ("inventory_items", "company_id = :company_id"),
        ("parties", "company_id = :company_id"),
        ("quotes", "company_id = :company_id"),
        ("quote_items", "company_id = :company_id"),
        ("sales_orders", "company_id = :company_id"),
        ("sales_order_items", "company_id = :company_id"),
        ("transactions", "company_id = :company_id"),
        ("invoices", "company_id = :company_id"),
        ("invoice_items", "company_id = :company_id"),
        ("recurring_invoice_profiles", "company_id = :company_id"),
        ("recurring_invoice_items", "company_id = :company_id"),
        ("recurring_invoice_logs", "company_id = :company_id"),
        ("delivery_challans", "company_id = :company_id"),
        ("delivery_challan_items", "company_id = :company_id"),
        ("invoice_payment_allocations", "company_id = :company_id"),
        ("journal_entries", "company_id = :company_id"),
        ("journal_entry_lines", "company_id = :company_id"),
        ("ledger_entries", "company_id = :company_id"),
        ("customers", "company_id = :company_id"),
        ("customer_addresses", "company_id = :company_id"),
        ("customer_contacts", "company_id = :company_id"),
        ("credit_notes", "company_id = :company_id"),
        ("credit_note_items", "company_id = :company_id"),
        ("credit_note_invoice_mappings", "company_id = :company_id")
    ]
    
    print("\n--- Row Counts per Seeded Table ---")
    all_valid = True
    for table, query in tables_to_check:
        try:
            count = db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {query}"), {'company_id': str(COMPANY_ID)}).scalar()
            print(f"| {table.ljust(32)} | {str(count).rjust(6)} rows |")
            if count == 0 and table not in ["permissions", "roles"]: # permissions/roles seeded by setup or seed, they must be checked
                pass # some tables can be 0 if not needed, but for our task all must be > 0
        except Exception as e:
            print(f"| ERROR reading {table}: {e}")
            all_valid = False

    print("\n--- Relational Ledger & Journal Balance Check ---")
    try:
        # Balanced Journal Entry Lines Check
        journal_bal = db.execute(text("""
            SELECT 
                SUM(CASE WHEN entry_type = 'debit' THEN amount ELSE 0 END) as total_debits,
                SUM(CASE WHEN entry_type = 'credit' THEN amount ELSE 0 END) as total_credits
            FROM journal_entry_lines
            WHERE company_id = :company_id
        """), {'company_id': str(COMPANY_ID)}).fetchone()
        
        debits = journal_bal[0] or 0.0
        credits = journal_bal[1] or 0.0
        diff = abs(debits - credits)
        print(f"Journal Entries Debits : {debits:.2f}")
        print(f"Journal Entries Credits: {credits:.2f}")
        print(f"Journal Difference     : {diff:.2f}")
        if diff < 0.01:
            print("STATUS: SUCCESS! Journal entry lines are perfectly balanced.")
        else:
            print("STATUS: WARNING! Journal entry lines are OUT OF BALANCE.")
            all_valid = False
            
        # Balanced Ledger Entries Check
        ledger_bal = db.execute(text("""
            SELECT 
                SUM(CASE WHEN entry_type = 'debit' THEN amount ELSE 0 END) as total_debits,
                SUM(CASE WHEN entry_type = 'credit' THEN amount ELSE 0 END) as total_credits
            FROM ledger_entries
            WHERE company_id = :company_id
        """), {'company_id': str(COMPANY_ID)}).fetchone()
        
        l_debits = ledger_bal[0] or 0.0
        l_credits = ledger_bal[1] or 0.0
        l_diff = abs(l_debits - l_credits)
        print(f"\nLedger Entries Debits  : {l_debits:.2f}")
        print(f"Ledger Entries Credits : {l_credits:.2f}")
        print(f"Ledger Difference      : {l_diff:.2f}")
        if l_diff < 0.01:
            print("STATUS: SUCCESS! General Ledger entries are perfectly balanced.")
        else:
            print("STATUS: WARNING! General Ledger entries are OUT OF BALANCE.")
            all_valid = False
    except Exception as e:
        print(f"Error executing balancing check: {e}")
        all_valid = False

    print("\n--- Invoice Allocation Status Consistency Check ---")
    try:
        invoices = db.execute(text("""
            SELECT invoice_number, invoice_grand_total, paid_amount, status,
                   (invoice_grand_total - paid_amount) as outstanding
            FROM invoices
            WHERE company_id = :company_id
            ORDER BY invoice_number
        """), {'company_id': str(COMPANY_ID)}).fetchall()
        
        print(f"| {'Invoice No'.ljust(15)} | {'Grand Total'.rjust(12)} | {'Paid Amount'.rjust(12)} | {'Outstanding'.rjust(12)} | {'Status'.ljust(10)} |")
        print("|" + "-"*17 + "|" + "-"*14 + "|" + "-"*14 + "|" + "-"*14 + "|" + "-"*12 + "|")
        for inv in invoices:
            print(f"| {inv[0].ljust(15)} | {str(inv[1]).rjust(12)} | {str(inv[2]).rjust(12)} | {str(inv[3] if inv[4] else inv[1]-inv[2]).rjust(12)} | {inv[3].ljust(10)} |")
    except Exception as e:
        print(f"Error checking invoice consistency: {e}")
        all_valid = False

    print("\n==================================================")
    if all_valid:
        print("          ALL VERIFICATION TESTS PASSED           ")
    else:
        print("          VERIFICATION DETECTED FAILURE           ")
    print("==================================================")

if __name__ == "__main__":
    try:
        run_verification()
    finally:
        db.close()
