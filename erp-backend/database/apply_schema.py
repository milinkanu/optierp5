import os
import sys
from pathlib import Path

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    # Look for .env in the parent directories
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

import psycopg2

SQL_FILES = [
    "schema.sql",
    "compliance_schema.sql",
    "compliance_setup.sql",
    "ocr_credit_schema.sql",
    "transaction_invoice_schema.sql",
    "quotes_sales_orders_schema.sql",
    "dev_upgrades.sql"
]

def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable is not set.", file=sys.stderr)
        print("Please set DATABASE_URL or create a .env file in the backend root directory.", file=sys.stderr)
        sys.exit(1)

    print("Connecting to database...")
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False  # Use transaction block
    except Exception as e:
        print(f"Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    db_dir = Path(__file__).parent
    
    try:
        with conn.cursor() as cur:
            for sql_file in SQL_FILES:
                file_path = db_dir / sql_file
                if not file_path.exists():
                    print(f"Warning: File {sql_file} not found in {db_dir}. Skipping.", file=sys.stderr)
                    continue
                
                print(f"Applying {sql_file}...")
                with open(file_path, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                
                cur.execute(sql_content)
                print(f"Successfully applied {sql_file}.")
        
        conn.commit()
        print("\nAll database schema files applied successfully!")
    except Exception as e:
        conn.rollback()
        print(f"\nError applying schema: {e}", file=sys.stderr)
        print("Transaction rolled back.", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
