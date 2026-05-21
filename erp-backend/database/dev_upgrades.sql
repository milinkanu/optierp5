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

-- Additional invoice fields for complete form support.
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS order_number TEXT,
    ADD COLUMN IF NOT EXISTS salesperson_id UUID REFERENCES parties(party_id),
    ADD COLUMN IF NOT EXISTS subject TEXT,
    ADD COLUMN IF NOT EXISTS customer_notes TEXT,
    ADD COLUMN IF NOT EXISTS terms_and_conditions TEXT,
    ADD COLUMN IF NOT EXISTS reference_document_url TEXT;

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

-- ====================================================
-- MODULE 1: RECURRING INVOICES
-- ====================================================

CREATE TABLE IF NOT EXISTS recurring_invoice_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    profile_name TEXT NOT NULL,
    billing_party_id UUID NOT NULL REFERENCES parties(party_id),
    shipping_party_id UUID REFERENCES parties(party_id),
    frequency TEXT NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'stopped')),
    start_date DATE NOT NULL,
    end_date DATE,
    next_run_date DATE NOT NULL,
    last_run_date DATE,
    auto_email BOOLEAN NOT NULL DEFAULT FALSE,
    currency TEXT NOT NULL DEFAULT 'INR',
    exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    order_number TEXT,
    salesperson_id UUID REFERENCES parties(party_id),
    subject TEXT,
    customer_notes TEXT,
    terms_and_conditions TEXT,
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recurring_invoice_items (
    profile_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES recurring_invoice_profiles(profile_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    line_number INT NOT NULL,
    description TEXT NOT NULL,
    hsn_sac TEXT CHECK (hsn_sac IS NULL OR hsn_sac ~ '^[0-9A-Z]{4,8}$'),
    inventory_item_id UUID REFERENCES inventory_items(inventory_item_id),
    account_id UUID NOT NULL REFERENCES chart_of_accounts(account_id),
    quantity NUMERIC(18,4) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    taxable_amount NUMERIC(18,2) NOT NULL CHECK (taxable_amount >= 0),
    gst_rate NUMERIC(5,2) NOT NULL CHECK (gst_rate >= 0 AND gst_rate <= 100),
    gst_amount NUMERIC(18,2) NOT NULL CHECK (gst_amount >= 0),
    tds_rate NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tds_rate >= 0 AND tds_rate <= 100),
    tds_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (tds_amount >= 0),
    tcs_rate NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tcs_rate >= 0 AND tcs_rate <= 100),
    tcs_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (tcs_amount >= 0),
    total_amount NUMERIC(18,2) NOT NULL CHECK (total_amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(profile_id, line_number)
);

CREATE TABLE IF NOT EXISTS recurring_invoice_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES recurring_invoice_profiles(profile_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    run_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL CHECK (status IN ('success', 'failure')),
    generated_invoice_id UUID REFERENCES invoices(invoice_id),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ====================================================
-- MODULE 2: DELIVERY CHALLANS
-- ====================================================

CREATE TABLE IF NOT EXISTS delivery_challans (
    delivery_challan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    challan_number TEXT NOT NULL,
    challan_type TEXT NOT NULL CHECK (challan_type IN ('supply_on_approval', 'job_work', 'transport', 'others')),
    challan_date DATE NOT NULL,
    billing_party_id UUID NOT NULL REFERENCES parties(party_id),
    shipping_party_id UUID REFERENCES parties(party_id),
    reference_number TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'open', 'converted', 'cancelled', 'closed')),
    currency TEXT NOT NULL DEFAULT 'INR',
    exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    subtotal NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    total_gst NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_gst >= 0),
    grand_total NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (grand_total >= 0),
    transport_mode TEXT,
    vehicle_number TEXT,
    place_of_supply TEXT,
    customer_notes TEXT,
    terms_and_conditions TEXT,
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, challan_number)
);

CREATE TABLE IF NOT EXISTS delivery_challan_items (
    challan_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_challan_id UUID NOT NULL REFERENCES delivery_challans(delivery_challan_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    line_number INT NOT NULL,
    description TEXT NOT NULL,
    hsn_sac TEXT CHECK (hsn_sac IS NULL OR hsn_sac ~ '^[0-9A-Z]{4,8}$'),
    inventory_item_id UUID REFERENCES inventory_items(inventory_item_id),
    account_id UUID REFERENCES chart_of_accounts(account_id),
    quantity NUMERIC(18,4) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    taxable_amount NUMERIC(18,2) NOT NULL CHECK (taxable_amount >= 0),
    gst_rate NUMERIC(5,2) NOT NULL CHECK (gst_rate >= 0 AND gst_rate <= 100),
    gst_amount NUMERIC(18,2) NOT NULL CHECK (gst_amount >= 0),
    total_amount NUMERIC(18,2) NOT NULL CHECK (total_amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(delivery_challan_id, line_number)
);

-- Add foreign keys / references to existing invoices table
ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS recurring_profile_id UUID REFERENCES recurring_invoice_profiles(profile_id),
    ADD COLUMN IF NOT EXISTS delivery_challan_id UUID REFERENCES delivery_challans(delivery_challan_id);

-- ====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ====================================================

ALTER TABLE recurring_invoice_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE recurring_invoice_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_challans ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_challan_items ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_recurring_invoice_profiles') THEN
        CREATE POLICY tenant_isolation_recurring_invoice_profiles ON recurring_invoice_profiles USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_recurring_invoice_items') THEN
        CREATE POLICY tenant_isolation_recurring_invoice_items ON recurring_invoice_items USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_recurring_invoice_logs') THEN
        CREATE POLICY tenant_isolation_recurring_invoice_logs ON recurring_invoice_logs USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_delivery_challans') THEN
        CREATE POLICY tenant_isolation_delivery_challans ON delivery_challans USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_delivery_challan_items') THEN
        CREATE POLICY tenant_isolation_delivery_challan_items ON delivery_challan_items USING (company_id = app.current_tenant());
    END IF;
END$$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_recurring_profiles_company ON recurring_invoice_profiles(company_id, status);
CREATE INDEX IF NOT EXISTS idx_recurring_items_profile ON recurring_invoice_items(company_id, profile_id);
CREATE INDEX IF NOT EXISTS idx_delivery_challans_company ON delivery_challans(company_id, status);
CREATE INDEX IF NOT EXISTS idx_delivery_challan_items ON delivery_challan_items(company_id, delivery_challan_id);

