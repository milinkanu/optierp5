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


-- ====================================================
-- MODULE 3: CREDIT NOTES
-- ====================================================

CREATE TABLE IF NOT EXISTS credit_notes (
    credit_note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    credit_note_number TEXT NOT NULL,
    reference_number TEXT,
    credit_note_date DATE NOT NULL,
    billing_party_id UUID NOT NULL REFERENCES parties(party_id),
    shipping_party_id UUID REFERENCES parties(party_id),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'open', 'partially_applied', 'applied', 'cancelled')),
    currency TEXT NOT NULL DEFAULT 'INR',
    exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    accounts_receivable_id UUID REFERENCES chart_of_accounts(account_id),
    salesperson_id UUID REFERENCES parties(party_id),
    subtotal NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    total_gst NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_gst >= 0),
    total_tds NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_tds >= 0),
    total_tcs NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_tcs >= 0),
    grand_total NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (grand_total >= 0),
    remaining_balance NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (remaining_balance >= 0),
    customer_notes TEXT,
    terms_and_conditions TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, credit_note_number)
);

CREATE TABLE IF NOT EXISTS credit_note_items (
    credit_note_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credit_note_id UUID NOT NULL REFERENCES credit_notes(credit_note_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    line_number INT NOT NULL,
    description TEXT NOT NULL,
    hsn_sac TEXT CHECK (hsn_sac IS NULL OR hsn_sac ~ '^[0-9A-Z]{4,8}$'),
    inventory_item_id UUID REFERENCES inventory_items(inventory_item_id),
    account_id UUID NOT NULL REFERENCES chart_of_accounts(account_id),
    quantity NUMERIC(18,4) NOT NULL CHECK (quantity > 0),
    unit TEXT,
    rate NUMERIC(18,4) NOT NULL CHECK (rate >= 0),
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    taxable_amount NUMERIC(18,2) NOT NULL CHECK (taxable_amount >= 0),
    tax_id UUID,
    tax_percentage NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tax_percentage >= 0 AND tax_percentage <= 100),
    tax_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (tax_amount >= 0),
    tds_rate NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tds_rate >= 0 AND tds_rate <= 100),
    tds_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (tds_amount >= 0),
    tcs_rate NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tcs_rate >= 0 AND tcs_rate <= 100),
    tcs_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (tcs_amount >= 0),
    line_total NUMERIC(18,2) NOT NULL CHECK (line_total >= 0),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(credit_note_id, line_number)
);

CREATE TABLE IF NOT EXISTS credit_note_attachments (
    attachment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credit_note_id UUID NOT NULL REFERENCES credit_notes(credit_note_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size INT,
    mime_type TEXT,
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_note_activity_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credit_note_id UUID NOT NULL REFERENCES credit_notes(credit_note_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    activity_type TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB,
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_note_invoice_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    credit_note_id UUID NOT NULL REFERENCES credit_notes(credit_note_id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    applied_amount NUMERIC(18,2) NOT NULL CHECK (applied_amount > 0),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(credit_note_id, invoice_id)
);

-- ====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ====================================================

ALTER TABLE credit_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_note_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_note_attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_note_activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_note_invoice_mappings ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_credit_notes') THEN
        CREATE POLICY tenant_isolation_credit_notes ON credit_notes USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_credit_note_items') THEN
        CREATE POLICY tenant_isolation_credit_note_items ON credit_note_items USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_credit_note_attachments') THEN
        CREATE POLICY tenant_isolation_credit_note_attachments ON credit_note_attachments USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_credit_note_activity_logs') THEN
        CREATE POLICY tenant_isolation_credit_note_activity_logs ON credit_note_activity_logs USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_credit_note_invoice_mappings') THEN
        CREATE POLICY tenant_isolation_credit_note_invoice_mappings ON credit_note_invoice_mappings USING (company_id = app.current_tenant());
    END IF;
END$$;

-- Recalculation Triggers
CREATE OR REPLACE FUNCTION app.recalculate_credit_note_totals() RETURNS trigger AS $$
DECLARE
    totals RECORD;
    target_cn_id UUID := COALESCE(NEW.credit_note_id, OLD.credit_note_id);
BEGIN
    SELECT
        COALESCE(SUM(taxable_amount), 0) AS subtotal,
        COALESCE(SUM(tax_amount), 0) AS gst_total,
        COALESCE(SUM(tds_amount), 0) AS tds_total,
        COALESCE(SUM(tcs_amount), 0) AS tcs_total,
        COALESCE(SUM(line_total), 0) AS grand_total
      INTO totals
      FROM credit_note_items
     WHERE credit_note_id = target_cn_id AND is_deleted = FALSE;

    UPDATE credit_notes
       SET subtotal = totals.subtotal,
           total_gst = totals.gst_total,
           total_tds = totals.tds_total,
           total_tcs = totals.tcs_total,
           grand_total = totals.grand_total,
           remaining_balance = totals.grand_total - COALESCE((
               SELECT SUM(applied_amount)
                 FROM credit_note_invoice_mappings
                WHERE credit_note_id = target_cn_id
           ), 0),
           updated_at = now()
     WHERE credit_note_id = target_cn_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_credit_note_items_recalculate
AFTER INSERT OR UPDATE OR DELETE ON credit_note_items
FOR EACH ROW EXECUTE FUNCTION app.recalculate_credit_note_totals();

CREATE OR REPLACE FUNCTION app.update_credit_note_remaining_balance() RETURNS trigger AS $$
DECLARE
    total_applied NUMERIC(18,2);
    target_cn_id UUID := COALESCE(NEW.credit_note_id, OLD.credit_note_id);
BEGIN
    SELECT COALESCE(SUM(applied_amount), 0) INTO total_applied
      FROM credit_note_invoice_mappings
     WHERE credit_note_id = target_cn_id;

    UPDATE credit_notes
       SET remaining_balance = grand_total - total_applied,
           status = CASE
               WHEN total_applied >= grand_total AND grand_total > 0 THEN 'applied'
               WHEN total_applied > 0 AND total_applied < grand_total THEN 'partially_applied'
               ELSE status
           END,
           updated_at = now()
     WHERE credit_note_id = target_cn_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_credit_note_mappings_update
AFTER INSERT OR UPDATE OR DELETE ON credit_note_invoice_mappings
FOR EACH ROW EXECUTE FUNCTION app.update_credit_note_remaining_balance();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credit_notes_company ON credit_notes(company_id, status);
CREATE INDEX IF NOT EXISTS idx_credit_note_items ON credit_note_items(company_id, credit_note_id);
CREATE INDEX IF NOT EXISTS idx_credit_note_mappings_cn ON credit_note_invoice_mappings(company_id, credit_note_id);
CREATE INDEX IF NOT EXISTS idx_credit_note_mappings_inv ON credit_note_invoice_mappings(company_id, invoice_id);


-- ====================================================
-- MODULE 4: CUSTOMER MANAGEMENT
-- ====================================================

-- 1. Core customer master table
CREATE TABLE IF NOT EXISTS customers (
    customer_id UUID PRIMARY KEY REFERENCES parties(party_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    customer_code TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_type TEXT NOT NULL CHECK (customer_type IN ('individual', 'business')),
    display_name TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    email TEXT,
    mobile TEXT,
    phone TEXT,
    gst_registration_type TEXT NOT NULL DEFAULT 'unregistered' CHECK (gst_registration_type IN ('regular', 'composition', 'unregistered', 'sez', 'consumer')),
    gstin TEXT CHECK (gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    pan TEXT, -- Encrypted PAN at rest (Fernet token string)
    payment_terms TEXT, -- e.g., 'Due on Receipt', 'Net 15', 'Net 30'
    credit_limit NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (credit_limit >= 0),
    opening_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
    opening_balance_type TEXT NOT NULL DEFAULT 'debit' CHECK (opening_balance_type IN ('debit', 'credit')),
    msme_status BOOLEAN NOT NULL DEFAULT FALSE,
    msme_registration_no TEXT,
    cin TEXT CHECK (cin IS NULL OR cin ~ '^[LUlu][0-9]{5}[A-Za-z]{2}[0-9]{4}[A-Za-z]{3}[0-9]{6}$'),
    invoice_delivery_preference TEXT NOT NULL DEFAULT 'email' CHECK (invoice_delivery_preference IN ('email', 'portal', 'both')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, customer_code),
    UNIQUE(company_id, display_name)
);

-- 2. Customer address table (supports billing and shipping)
CREATE TABLE IF NOT EXISTS customer_addresses (
    address_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    address_type TEXT NOT NULL CHECK (address_type IN ('billing', 'shipping')),
    attention TEXT,
    address_line1 TEXT NOT NULL,
    address_line2 TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Customer secondary contact persons grid
CREATE TABLE IF NOT EXISTS customer_contacts (
    contact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    first_name TEXT NOT NULL,
    last_name TEXT,
    email TEXT NOT NULL,
    phone TEXT,
    mobile TEXT,
    designation TEXT,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Customer custom fields
CREATE TABLE IF NOT EXISTS customer_custom_fields (
    field_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    field_key TEXT NOT NULL,
    field_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, field_key)
);

-- 5. Customer notes & attachment document metadata
CREATE TABLE IF NOT EXISTS customer_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    notes TEXT,
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. Customer tags
CREATE TABLE IF NOT EXISTS customer_tags (
    tag_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    tag_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, tag_name)
);

-- ====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ====================================================

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_custom_fields ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_tags ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_customers') THEN
        CREATE POLICY tenant_isolation_customers ON customers USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_customer_addresses') THEN
        CREATE POLICY tenant_isolation_customer_addresses ON customer_addresses USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_customer_contacts') THEN
        CREATE POLICY tenant_isolation_customer_contacts ON customer_contacts USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_customer_custom_fields') THEN
        CREATE POLICY tenant_isolation_customer_custom_fields ON customer_custom_fields USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_customer_documents') THEN
        CREATE POLICY tenant_isolation_customer_documents ON customer_documents USING (company_id = app.current_tenant());
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polname = 'tenant_isolation_customer_tags') THEN
        CREATE POLICY tenant_isolation_customer_tags ON customer_tags USING (company_id = app.current_tenant());
    END IF;
END$$;

-- ====================================================
-- INDEXES FOR HIGH-PERFORMANCE SEARCH
-- ====================================================

CREATE INDEX IF NOT EXISTS idx_customers_company_active ON customers(company_id, is_active, is_deleted);
CREATE INDEX IF NOT EXISTS idx_customers_gstin ON customers(company_id, gstin) WHERE gstin IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(company_id, email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_customers_mobile ON customers(company_id, mobile) WHERE mobile IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_customer_addresses_lookup ON customer_addresses(company_id, customer_id, address_type);
CREATE INDEX IF NOT EXISTS idx_customer_contacts_lookup ON customer_contacts(company_id, customer_id, is_primary);



