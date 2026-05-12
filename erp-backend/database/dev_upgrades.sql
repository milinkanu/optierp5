-- Non-destructive schema upgrades for an existing database.
-- Safe to run repeatedly.

-- Add enum value for unified contacts.
ALTER TYPE party_type_enum ADD VALUE IF NOT EXISTS 'both';

-- Company profile fields.
ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS address JSONB,
    ADD COLUMN IF NOT EXISTS logo_url TEXT,
    ADD COLUMN IF NOT EXISTS fiscal_year_start DATE,
    ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'INR',
    ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata';

-- Contacts fields.
ALTER TABLE parties
    ADD COLUMN IF NOT EXISTS pan TEXT,
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS phone TEXT,
    ADD COLUMN IF NOT EXISTS payment_terms TEXT,
    ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'INR';

-- Chart of Accounts fields.
ALTER TABLE chart_of_accounts
    ADD COLUMN IF NOT EXISTS description TEXT;

-- Invoicing soft-delete fields (if invoice schema already applied).
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE invoice_items
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;

-- Items (inventory_items) upgrades to support Zoho-Books-like item master.
ALTER TABLE inventory_items
    ADD COLUMN IF NOT EXISTS sku TEXT,
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS image_url TEXT,
    ADD COLUMN IF NOT EXISTS is_track_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reorder_point NUMERIC(18,4),
    ADD COLUMN IF NOT EXISTS selling_price NUMERIC(18,2),
    ADD COLUMN IF NOT EXISTS purchase_price NUMERIC(18,2),
    ADD COLUMN IF NOT EXISTS sales_account_id UUID REFERENCES chart_of_accounts(account_id),
    ADD COLUMN IF NOT EXISTS purchase_account_id UUID REFERENCES chart_of_accounts(account_id),
    ADD COLUMN IF NOT EXISTS preferred_vendor_id UUID REFERENCES parties(party_id);

CREATE INDEX IF NOT EXISTS idx_inventory_items_company_name ON inventory_items(company_id, item_name);
