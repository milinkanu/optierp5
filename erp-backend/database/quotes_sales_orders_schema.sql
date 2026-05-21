-- PostgreSQL schema for Quotes and Sales Orders
-- Requires database/schema.sql and database/transaction_invoice_schema.sql to be present.

DROP TABLE IF EXISTS sales_order_attachments CASCADE;
DROP TABLE IF EXISTS sales_order_activity_logs CASCADE;
DROP TABLE IF EXISTS sales_order_items CASCADE;
DROP TABLE IF EXISTS sales_orders CASCADE;
DROP TABLE IF EXISTS quote_attachments CASCADE;
DROP TABLE IF EXISTS quote_activity_logs CASCADE;
DROP TABLE IF EXISTS quote_items CASCADE;
DROP TABLE IF EXISTS quotes CASCADE;
DROP TYPE IF EXISTS quote_status_enum CASCADE;
DROP TYPE IF EXISTS sales_order_status_enum CASCADE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'quote_status_enum') THEN
        CREATE TYPE quote_status_enum AS ENUM ('draft', 'sent', 'accepted', 'rejected', 'expired', 'converted');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sales_order_status_enum') THEN
        CREATE TYPE sales_order_status_enum AS ENUM ('draft', 'confirmed', 'partially_invoiced', 'invoiced', 'cancelled');
    END IF;
END$$;

-- Quotes Table
CREATE TABLE quotes (
    quote_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    quote_number TEXT NOT NULL,
    quote_date DATE NOT NULL,
    expiry_date DATE,
    billing_party_id UUID NOT NULL REFERENCES parties(party_id),
    shipping_party_id UUID REFERENCES parties(party_id),
    reference_number TEXT,
    salesperson_id UUID REFERENCES users(user_id),
    project_name TEXT,
    subject TEXT,
    customer_notes TEXT,
    terms_and_conditions TEXT,
    status quote_status_enum NOT NULL DEFAULT 'draft',
    currency TEXT NOT NULL DEFAULT 'INR',
    exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    subtotal NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    total_gst NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_gst >= 0),
    total_tds NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_tds >= 0),
    total_tcs NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_tcs >= 0),
    adjustment NUMERIC(18,2) NOT NULL DEFAULT 0,
    discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (discount_percentage >= 0 AND discount_percentage <= 100),
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    grand_total NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (grand_total >= 0),
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, quote_number)
);

-- Quote Line Items Table
CREATE TABLE quote_items (
    quote_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES quotes(quote_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    line_number INT NOT NULL,
    description TEXT NOT NULL,
    inventory_item_id UUID REFERENCES inventory_items(inventory_item_id),
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
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(quote_id, line_number)
);

-- Quote Activity Logs Table
CREATE TABLE quote_activity_logs (
    activity_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES quotes(quote_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    actor_user_id UUID NOT NULL REFERENCES users(user_id),
    action TEXT NOT NULL,
    previous_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Quote Attachments Table
CREATE TABLE quote_attachments (
    attachment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES quotes(quote_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INT NOT NULL,
    mime_type TEXT,
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sales Orders Table
CREATE TABLE sales_orders (
    sales_order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    sales_order_number TEXT NOT NULL,
    sales_order_date DATE NOT NULL,
    expected_shipment_date DATE,
    billing_party_id UUID NOT NULL REFERENCES parties(party_id),
    shipping_party_id UUID REFERENCES parties(party_id),
    reference_number TEXT,
    payment_terms TEXT,
    salesperson_id UUID REFERENCES users(user_id),
    subject TEXT,
    customer_notes TEXT,
    terms_and_conditions TEXT,
    status sales_order_status_enum NOT NULL DEFAULT 'draft',
    currency TEXT NOT NULL DEFAULT 'INR',
    exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    subtotal NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
    total_gst NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_gst >= 0),
    total_tds NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_tds >= 0),
    total_tcs NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (total_tcs >= 0),
    adjustment NUMERIC(18,2) NOT NULL DEFAULT 0,
    discount_percentage NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (discount_percentage >= 0 AND discount_percentage <= 100),
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    grand_total NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (grand_total >= 0),
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    quote_id UUID REFERENCES quotes(quote_id) ON DELETE SET NULL,
    UNIQUE(company_id, sales_order_number)
);

-- Sales Order Line Items Table
CREATE TABLE sales_order_items (
    sales_order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID NOT NULL REFERENCES sales_orders(sales_order_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    line_number INT NOT NULL,
    description TEXT NOT NULL,
    inventory_item_id UUID REFERENCES inventory_items(inventory_item_id),
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
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(sales_order_id, line_number)
);

-- Sales Order Activity Logs Table
CREATE TABLE sales_order_activity_logs (
    activity_log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID NOT NULL REFERENCES sales_orders(sales_order_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    actor_user_id UUID NOT NULL REFERENCES users(user_id),
    action TEXT NOT NULL,
    previous_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sales Order Attachments Table
CREATE TABLE sales_order_attachments (
    attachment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sales_order_id UUID NOT NULL REFERENCES sales_orders(sales_order_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INT NOT NULL,
    mime_type TEXT,
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_quotes_company_status ON quotes(company_id, status);
CREATE INDEX idx_quote_items_company_quote ON quote_items(company_id, quote_id);
CREATE INDEX idx_sales_orders_company_status ON sales_orders(company_id, status);
CREATE INDEX idx_sales_order_items_company_so ON sales_order_items(company_id, sales_order_id);

-- Link from invoices back to quote/sales order for conversion audit
ALTER TABLE invoices 
ADD COLUMN IF NOT EXISTS quote_id UUID REFERENCES quotes(quote_id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS sales_order_id UUID REFERENCES sales_orders(sales_order_id) ON DELETE SET NULL;

-- Enable Row Level Security (RLS)
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_attachments ENABLE ROW LEVEL SECURITY;

ALTER TABLE sales_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_order_activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_order_attachments ENABLE ROW LEVEL SECURITY;

-- Add Tenant Isolation policies
CREATE POLICY tenant_isolation_quotes ON quotes USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_quote_items ON quote_items USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_quote_activity_logs ON quote_activity_logs USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_quote_attachments ON quote_attachments USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_sales_orders ON sales_orders USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_sales_order_items ON sales_order_items USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_sales_order_activity_logs ON sales_order_activity_logs USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_sales_order_attachments ON sales_order_attachments USING (company_id = app.current_tenant());

-- Trigger for quote recalculation
CREATE OR REPLACE FUNCTION app.recalculate_quote_totals() RETURNS trigger AS $$
DECLARE
    totals RECORD;
    target_quote_id UUID := COALESCE(NEW.quote_id, OLD.quote_id);
BEGIN
    SELECT
        COALESCE(SUM(taxable_amount), 0) AS subtotal,
        COALESCE(SUM(gst_amount), 0) AS gst_total,
        COALESCE(SUM(tds_amount), 0) AS tds_total,
        COALESCE(SUM(tcs_amount), 0) AS tcs_total,
        COALESCE(SUM(total_amount), 0) AS grand_total
      INTO totals
      FROM quote_items
     WHERE quote_id = target_quote_id AND is_deleted = FALSE;

    UPDATE quotes
       SET subtotal = totals.subtotal,
           total_gst = totals.gst_total,
           total_tds = totals.tds_total,
           total_tcs = totals.tcs_total,
           grand_total = totals.grand_total - COALESCE(discount_amount, 0) + COALESCE(adjustment, 0),
           updated_at = now()
     WHERE quote_id = target_quote_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_quote_items_recalculate
AFTER INSERT OR UPDATE OR DELETE ON quote_items
FOR EACH ROW EXECUTE FUNCTION app.recalculate_quote_totals();

-- Trigger for sales order recalculation
CREATE OR REPLACE FUNCTION app.recalculate_sales_order_totals() RETURNS trigger AS $$
DECLARE
    totals RECORD;
    target_so_id UUID := COALESCE(NEW.sales_order_id, OLD.sales_order_id);
BEGIN
    SELECT
        COALESCE(SUM(taxable_amount), 0) AS subtotal,
        COALESCE(SUM(gst_amount), 0) AS gst_total,
        COALESCE(SUM(tds_amount), 0) AS tds_total,
        COALESCE(SUM(tcs_amount), 0) AS tcs_total,
        COALESCE(SUM(total_amount), 0) AS grand_total
      INTO totals
      FROM sales_order_items
     WHERE sales_order_id = target_so_id AND is_deleted = FALSE;

    UPDATE sales_orders
       SET subtotal = totals.subtotal,
           total_gst = totals.gst_total,
           total_tds = totals.tds_total,
           total_tcs = totals.tcs_total,
           grand_total = totals.grand_total - COALESCE(discount_amount, 0) + COALESCE(adjustment, 0),
           updated_at = now()
     WHERE sales_order_id = target_so_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sales_order_items_recalculate
AFTER INSERT OR UPDATE OR DELETE ON sales_order_items
FOR EACH ROW EXECUTE FUNCTION app.recalculate_sales_order_totals();
