-- Tenant Database Template
-- This SQL is used to initialize each tenant's database

-- Leads table - potential PDR jobs
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    business_id INTEGER NOT NULL,
    storm_id INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'new',
    priority VARCHAR(20) DEFAULT 'medium',
    assigned_to INTEGER,
    notes TEXT,
    estimated_vehicles INTEGER,
    estimated_value DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Contacts table - people at businesses
CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    name VARCHAR(255),
    title VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(255),
    is_primary BOOLEAN DEFAULT FALSE,
    is_decision_maker BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Calls table - call log
CREATE TABLE IF NOT EXISTS calls (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES contacts(id),
    user_id INTEGER NOT NULL,
    call_type VARCHAR(50),
    duration_seconds INTEGER,
    outcome VARCHAR(50),
    notes TEXT,
    callback_date TIMESTAMP,
    called_at TIMESTAMP DEFAULT NOW()
);

-- Jobs table - scheduled/completed work
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    job_number VARCHAR(50),
    status VARCHAR(50) DEFAULT 'scheduled',
    vehicle_count INTEGER,
    total_amount DECIMAL(12, 2),
    scheduled_date DATE,
    completed_date DATE,
    assigned_tech INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Estimates table - quotes
CREATE TABLE IF NOT EXISTS estimates (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    estimate_number VARCHAR(50),
    status VARCHAR(50) DEFAULT 'draft',
    vehicle_count INTEGER,
    price_per_vehicle DECIMAL(10, 2),
    total_amount DECIMAL(12, 2),
    valid_until DATE,
    sent_at TIMESTAMP,
    accepted_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_assigned_to ON leads(assigned_to);
CREATE INDEX idx_leads_storm_id ON leads(storm_id);
CREATE INDEX idx_leads_business_id ON leads(business_id);
CREATE INDEX idx_leads_created_at ON leads(created_at);
CREATE INDEX idx_calls_lead_id ON calls(lead_id);
CREATE INDEX idx_calls_user_id ON calls(user_id);
CREATE INDEX idx_calls_called_at ON calls(called_at);
CREATE INDEX idx_jobs_lead_id ON jobs(lead_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_scheduled_date ON jobs(scheduled_date);
CREATE INDEX idx_estimates_lead_id ON estimates(lead_id);
CREATE INDEX idx_estimates_status ON estimates(status);
