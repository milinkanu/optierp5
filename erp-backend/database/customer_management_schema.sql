-- Database schema upgrades for Zoho Books-style Customer Onboarding and Management Module.
-- Normalized tables representing core customer profile, addresses, secondary contact persons,
-- custom fields, tag strings, and document metadata. All protected by PostgreSQL RLS.

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
    cin TEXT CHECK (cin IS NULL OR cin ~ '^[LUlu][0-9]{5}[A-Za-z]{2}[0-9]{4}[A-Za-z]{3}[0-9]{6}$'), -- Standard Indian CIN regex pattern
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
