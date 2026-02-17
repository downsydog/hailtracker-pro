-- ============================================================================
-- MIGRATION 003: CRM Core Tables
-- ============================================================================
-- Target: PostgreSQL 16+
-- Depends on: 001 (hail_events), 002 (users, fleet_locations, etc.)
--
-- These tables were previously created at runtime by schema.py,
-- estimates_api.py, admin_api.py, and admin_manager.py.
-- Moving them to a migration makes PG mode fully migration-driven.
-- ============================================================================

-- ============================================================================
-- ALTER users TABLE — Add columns that admin_api.py relied on
-- (users table was created in migration 002 with a minimal column set)
-- ============================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_token TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS invite_sent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- ============================================================================
-- LOCATIONS — Multi-shop support (parent of customers, technicians, jobs)
-- ============================================================================

CREATE TABLE IF NOT EXISTS locations (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    location_code TEXT UNIQUE,
    street_address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    phone TEXT,
    email TEXT,
    max_concurrent_jobs INTEGER,
    tech_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- CUSTOMERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS customers (
    id BIGSERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    company_name TEXT,
    customer_type TEXT DEFAULT 'INDIVIDUAL',
    email TEXT,
    phone TEXT,
    phone_secondary TEXT,
    preferred_contact TEXT DEFAULT 'PHONE',
    street_address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    status TEXT DEFAULT 'ACTIVE',
    customer_since DATE,
    last_contact_date DATE,
    source TEXT,
    referral_source TEXT,
    marketing_consent INTEGER DEFAULT 1,
    preferred_location_id BIGINT REFERENCES locations(id),
    notes TEXT,
    tags TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    updated_by TEXT,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);

-- ============================================================================
-- VEHICLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS vehicles (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    vin TEXT,
    year INTEGER,
    make TEXT,
    model TEXT,
    color TEXT,
    license_plate TEXT,
    insurance_company TEXT,
    policy_number TEXT,
    claim_number TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_vehicles_customer ON vehicles(customer_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_vin ON vehicles(vin);

-- ============================================================================
-- TECHNICIANS
-- ============================================================================

CREATE TABLE IF NOT EXISTS technicians (
    id BIGSERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    employee_id TEXT UNIQUE,
    location_id BIGINT REFERENCES locations(id),
    status TEXT DEFAULT 'ACTIVE',
    hire_date DATE,
    skill_level TEXT DEFAULT 'INTERMEDIATE',
    certifications TEXT,
    specialties TEXT,
    max_jobs_concurrent INTEGER DEFAULT 3,
    current_job_count INTEGER DEFAULT 0,
    avg_job_hours DOUBLE PRECISION,
    quality_score DOUBLE PRECISION,
    pay_type TEXT DEFAULT 'PERCENTAGE',
    pay_rate DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- INSURANCE CLAIMS
-- ============================================================================

CREATE TABLE IF NOT EXISTS insurance_claims (
    id BIGSERIAL PRIMARY KEY,
    claim_number TEXT UNIQUE NOT NULL,
    insurance_company TEXT NOT NULL,
    policy_number TEXT,
    adjuster_name TEXT,
    adjuster_email TEXT,
    adjuster_phone TEXT,
    adjuster_extension TEXT,
    status TEXT DEFAULT 'SUBMITTED',
    claim_date DATE,
    submitted_date DATE,
    adjuster_scheduled_date TIMESTAMPTZ,
    adjuster_inspection_date DATE,
    approval_date DATE,
    payment_received_date DATE,
    last_contact_date DATE,
    last_contact_method TEXT,
    next_follow_up_date DATE,
    follow_up_count INTEGER DEFAULT 0,
    auto_follow_up_enabled INTEGER DEFAULT 1,
    days_since_last_response INTEGER,
    claimed_amount DOUBLE PRECISION,
    approved_amount DOUBLE PRECISION,
    supplement_amount DOUBLE PRECISION,
    deductible DOUBLE PRECISION,
    payment_received DOUBLE PRECISION,
    estimate_sent INTEGER DEFAULT 0,
    supplement_sent INTEGER DEFAULT 0,
    notes TEXT,
    adjuster_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_claims_number ON insurance_claims(claim_number);
CREATE INDEX IF NOT EXISTS idx_claims_status ON insurance_claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_follow_up ON insurance_claims(next_follow_up_date);

-- ============================================================================
-- LEADS
-- ============================================================================

CREATE TABLE IF NOT EXISTS leads (
    id BIGSERIAL PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    company_name TEXT,
    email TEXT,
    phone TEXT,
    source TEXT NOT NULL,
    hail_event_id BIGINT,
    score INTEGER DEFAULT 0,
    temperature TEXT DEFAULT 'WARM',
    status TEXT DEFAULT 'NEW',
    converted_to_customer_id BIGINT REFERENCES customers(id),
    lost_reason TEXT,
    assigned_to TEXT,
    assigned_at TIMESTAMPTZ,
    next_follow_up_date DATE,
    follow_up_count INTEGER DEFAULT 0,
    last_contact_date DATE,
    vehicle_year INTEGER,
    vehicle_make TEXT,
    vehicle_model TEXT,
    damage_type TEXT,
    damage_description TEXT,
    estimated_repair_cost DOUBLE PRECISION,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_hail_event ON leads(hail_event_id);
CREATE INDEX IF NOT EXISTS idx_leads_follow_up ON leads(next_follow_up_date);

-- ============================================================================
-- JOBS — Core workflow engine
-- ============================================================================

CREATE TABLE IF NOT EXISTS jobs (
    id BIGSERIAL PRIMARY KEY,
    job_number TEXT UNIQUE NOT NULL,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    vehicle_id BIGINT NOT NULL REFERENCES vehicles(id),
    location_id BIGINT REFERENCES locations(id),
    job_type TEXT DEFAULT 'PDR',
    damage_type TEXT,
    status TEXT DEFAULT 'NEW',
    status_changed_at TIMESTAMPTZ,
    status_changed_by TEXT,
    scheduled_drop_off TIMESTAMPTZ,
    actual_drop_off TIMESTAMPTZ,
    scheduled_pickup TIMESTAMPTZ,
    actual_pickup TIMESTAMPTZ,
    assigned_tech_id BIGINT,
    assigned_at TIMESTAMPTZ,
    estimated_hours DOUBLE PRECISION,
    estimated_completion_date DATE,
    tech_notes TEXT,
    tech_daily_update TEXT,
    last_tech_update TIMESTAMPTZ,
    insurance_claim_id BIGINT REFERENCES insurance_claims(id),
    parts_needed TEXT,
    parts_status TEXT,
    estimate_id BIGINT,
    invoice_id BIGINT,
    total_estimate DOUBLE PRECISION,
    total_actual DOUBLE PRECISION,
    priority TEXT DEFAULT 'NORMAL',
    internal_notes TEXT,
    customer_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_customer ON jobs(customer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_tech ON jobs(assigned_tech_id);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON jobs(scheduled_drop_off);
CREATE INDEX IF NOT EXISTS idx_jobs_number ON jobs(job_number);

-- ============================================================================
-- JOB STATUS HISTORY — Audit trail
-- ============================================================================

CREATE TABLE IF NOT EXISTS job_status_history (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    from_status TEXT,
    to_status TEXT,
    changed_by TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

-- ============================================================================
-- ESTIMATES — Superset of schema.py + estimates_api.py columns
-- ============================================================================

CREATE TABLE IF NOT EXISTS estimates (
    id BIGSERIAL PRIMARY KEY,
    estimate_number TEXT UNIQUE,
    customer_id BIGINT REFERENCES customers(id),
    vehicle_id BIGINT REFERENCES vehicles(id),
    job_id BIGINT REFERENCES jobs(id),
    status TEXT DEFAULT 'DRAFT',
    labor_hours DOUBLE PRECISION,
    labor_rate DOUBLE PRECISION,
    labor_total DOUBLE PRECISION,
    parts_total DOUBLE PRECISION,
    subtotal DOUBLE PRECISION DEFAULT 0,
    tax_rate DOUBLE PRECISION DEFAULT 0,
    tax_amount DOUBLE PRECISION DEFAULT 0,
    total DOUBLE PRECISION DEFAULT 0,
    line_items TEXT,
    notes TEXT,
    terms TEXT,
    valid_until TEXT,
    sent_at TEXT,
    approved_date TEXT,
    declined_at TEXT,
    converted_at TEXT,
    converted_job_id BIGINT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- ESTIMATE ITEMS — Line items for estimates (from estimates_api.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS estimate_items (
    id BIGSERIAL PRIMARY KEY,
    estimate_id BIGINT NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    service_type TEXT,
    description TEXT NOT NULL,
    quantity DOUBLE PRECISION DEFAULT 1,
    unit_price DOUBLE PRECISION DEFAULT 0,
    line_total DOUBLE PRECISION DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INVOICES
-- ============================================================================

CREATE TABLE IF NOT EXISTS invoices (
    id BIGSERIAL PRIMARY KEY,
    invoice_number TEXT UNIQUE NOT NULL,
    job_id BIGINT NOT NULL REFERENCES jobs(id),
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    status TEXT DEFAULT 'DRAFT',
    subtotal DOUBLE PRECISION,
    tax_amount DOUBLE PRECISION,
    total DOUBLE PRECISION NOT NULL,
    amount_paid DOUBLE PRECISION DEFAULT 0,
    balance_due DOUBLE PRECISION,
    line_items TEXT,
    invoice_date DATE NOT NULL,
    due_date DATE,
    sent_date DATE,
    paid_date DATE,
    payment_method TEXT,
    payment_reference TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PAYMENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES invoices(id),
    job_id BIGINT NOT NULL REFERENCES jobs(id),
    amount DOUBLE PRECISION NOT NULL,
    payment_method TEXT,
    payment_reference TEXT,
    payment_date DATE NOT NULL,
    payer_type TEXT,
    payer_name TEXT,
    total_amount DOUBLE PRECISION NOT NULL,
    insurance_portion DOUBLE PRECISION DEFAULT 0,
    parts_cost DOUBLE PRECISION DEFAULT 0,
    sales_team_cut DOUBLE PRECISION DEFAULT 0,
    tech_cut DOUBLE PRECISION DEFAULT 0,
    office_cut DOUBLE PRECISION DEFAULT 0,
    shop_profit DOUBLE PRECISION DEFAULT 0,
    sales_percentage DOUBLE PRECISION,
    tech_percentage DOUBLE PRECISION,
    office_percentage DOUBLE PRECISION,
    status TEXT DEFAULT 'RECEIVED',
    cleared_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT
);

-- ============================================================================
-- EMAIL TRACKING — Insurance correspondence audit trail
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_tracking (
    id BIGSERIAL PRIMARY KEY,
    insurance_claim_id BIGINT NOT NULL REFERENCES insurance_claims(id),
    job_id BIGINT REFERENCES jobs(id),
    direction TEXT NOT NULL,
    from_address TEXT,
    to_address TEXT,
    cc_addresses TEXT,
    subject TEXT,
    body TEXT,
    contains_approval INTEGER DEFAULT 0,
    contains_denial INTEGER DEFAULT 0,
    contains_question INTEGER DEFAULT 0,
    sentiment TEXT,
    response_received INTEGER DEFAULT 0,
    response_to_email_id BIGINT REFERENCES email_tracking(id),
    requires_response INTEGER DEFAULT 0,
    response_deadline DATE,
    sent_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_claim ON email_tracking(insurance_claim_id);
CREATE INDEX IF NOT EXISTS idx_email_direction ON email_tracking(direction);
CREATE INDEX IF NOT EXISTS idx_email_response ON email_tracking(requires_response);

-- ============================================================================
-- PARTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS parts (
    id BIGSERIAL PRIMARY KEY,
    part_number TEXT,
    description TEXT NOT NULL,
    category TEXT,
    preferred_supplier TEXT,
    supplier_part_number TEXT,
    cost DOUBLE PRECISION,
    retail_price DOUBLE PRECISION,
    in_stock INTEGER DEFAULT 0,
    reorder_level INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- PART ORDERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS part_orders (
    id BIGSERIAL PRIMARY KEY,
    order_number TEXT UNIQUE,
    job_id BIGINT REFERENCES jobs(id),
    supplier_name TEXT NOT NULL,
    supplier_email TEXT,
    supplier_phone TEXT,
    status TEXT DEFAULT 'QUOTED',
    quote_requested_date DATE,
    quote_received_date DATE,
    ordered_date DATE,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    quote_amount DOUBLE PRECISION,
    actual_amount DOUBLE PRECISION,
    return_cost DOUBLE PRECISION,
    parts_json TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PART QUOTES
-- ============================================================================

CREATE TABLE IF NOT EXISTS part_quotes (
    id BIGSERIAL PRIMARY KEY,
    part_order_id BIGINT NOT NULL REFERENCES part_orders(id),
    supplier_name TEXT NOT NULL,
    quoted_price DOUBLE PRECISION,
    quoted_delivery_days INTEGER,
    return_policy TEXT,
    core_charge DOUBLE PRECISION,
    selected INTEGER DEFAULT 0,
    quote_received_at TIMESTAMPTZ,
    quote_expires_at DATE
);

-- ============================================================================
-- COMMUNICATIONS LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS communications (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(id),
    lead_id BIGINT REFERENCES leads(id),
    job_id BIGINT REFERENCES jobs(id),
    insurance_claim_id BIGINT REFERENCES insurance_claims(id),
    type TEXT NOT NULL,
    direction TEXT NOT NULL,
    subject TEXT,
    message TEXT,
    from_person TEXT,
    to_person TEXT,
    status TEXT DEFAULT 'COMPLETED',
    outcome TEXT,
    follow_up_required INTEGER DEFAULT 0,
    follow_up_date DATE,
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT
);

-- ============================================================================
-- DOCUMENTS — Photos, PDFs, claim docs
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT REFERENCES jobs(id),
    customer_id BIGINT REFERENCES customers(id),
    vehicle_id BIGINT REFERENCES vehicles(id),
    insurance_claim_id BIGINT REFERENCES insurance_claims(id),
    document_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    photo_location TEXT,
    photo_angle TEXT,
    status TEXT DEFAULT 'ACTIVE',
    description TEXT,
    tags TEXT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    uploaded_by TEXT,
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- COMPANY SETTINGS (from admin_api.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_settings (
    id BIGSERIAL PRIMARY KEY,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type TEXT DEFAULT 'string',
    category TEXT DEFAULT 'general',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by INTEGER
);

-- ============================================================================
-- USER ACTIVITY LOG (from admin_api.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_activity_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- BILLING (from admin_api.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS billing (
    id BIGSERIAL PRIMARY KEY,
    plan_id TEXT UNIQUE DEFAULT 'free',
    plan_name TEXT DEFAULT 'Free',
    status TEXT DEFAULT 'active',
    billing_email TEXT,
    stripe_customer_id TEXT UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    seats_included INTEGER DEFAULT 5,
    seats_used INTEGER DEFAULT 1,
    monthly_price DOUBLE PRECISION DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SETTINGS (from admin_manager.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS settings (
    id BIGSERIAL PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    value_type TEXT DEFAULT 'STRING',
    category TEXT,
    description TEXT,
    updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- BACKUPS (from admin_manager.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS backups (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMPTZ,
    created_by TEXT,
    notes TEXT
);

-- ============================================================================
-- AUDIT LOGS (from admin_manager.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action TEXT NOT NULL,
    description TEXT,
    metadata TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SEED DATA — Default company settings (moved from admin_api.py per-request DDL)
-- ============================================================================

INSERT INTO company_settings (setting_key, setting_value, setting_type, category)
VALUES
    ('company_name', 'My PDR Company', 'string', 'company'),
    ('company_email', '', 'string', 'company'),
    ('company_phone', '', 'string', 'company'),
    ('company_address', '', 'string', 'company'),
    ('company_city', '', 'string', 'company'),
    ('company_state', '', 'string', 'company'),
    ('company_zip', '', 'string', 'company'),
    ('company_logo_url', '', 'string', 'branding'),
    ('primary_color', '#2563eb', 'string', 'branding'),
    ('default_tax_rate', '0', 'number', 'defaults'),
    ('default_estimate_terms', 'Estimate valid for 30 days. Subject to change upon inspection.', 'text', 'defaults'),
    ('business_hours_start', '08:00', 'string', 'company'),
    ('business_hours_end', '17:00', 'string', 'company'),
    ('notify_new_lead', 'true', 'boolean', 'notifications'),
    ('notify_job_complete', 'true', 'boolean', 'notifications'),
    ('notify_estimate_approved', 'true', 'boolean', 'notifications'),
    ('sms_notifications_enabled', 'false', 'boolean', 'notifications')
ON CONFLICT (setting_key) DO NOTHING;

-- Default billing row
INSERT INTO billing (plan_id, plan_name, status, seats_included, seats_used)
VALUES ('free', 'Free Plan', 'active', 5, 1)
ON CONFLICT (plan_id) DO NOTHING;
