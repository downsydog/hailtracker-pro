-- ============================================================================
-- CRM DATABASE SCHEMA
-- ============================================================================

-- INTERACTIONS TABLE - Track all customer touchpoints
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    user_id INTEGER,
    interaction_type TEXT NOT NULL,  -- 'call', 'email', 'visit', 'sms', 'note'
    interaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    outcome TEXT,  -- 'answered', 'voicemail', 'no_answer', 'meeting_scheduled', 'quoted', 'declined'
    notes TEXT,
    duration_seconds INTEGER,  -- For calls
    next_followup_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES fleet_locations(id)
);

CREATE INDEX IF NOT EXISTS idx_interactions_location ON interactions(location_id);
CREATE INDEX IF NOT EXISTS idx_interactions_date ON interactions(interaction_date);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(interaction_type);

-- DEALS TABLE - Sales pipeline management
CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    event_id INTEGER,
    stage TEXT NOT NULL,  -- 'lead', 'contacted', 'qualified', 'quoted', 'negotiating', 'won', 'lost'
    estimated_value REAL,
    actual_value REAL,
    probability INTEGER DEFAULT 0,  -- 0-100%
    expected_close_date DATE,
    actual_close_date DATE,
    lost_reason TEXT,
    assigned_to INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES fleet_locations(id)
);

CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
CREATE INDEX IF NOT EXISTS idx_deals_assigned ON deals(assigned_to);
CREATE INDEX IF NOT EXISTS idx_deals_location ON deals(location_id);

-- TASKS TABLE - Follow-ups and to-dos
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER,
    deal_id INTEGER,
    assigned_to INTEGER,
    task_type TEXT NOT NULL,  -- 'call', 'email', 'visit', 'quote', 'follow_up'
    title TEXT NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    priority TEXT DEFAULT 'medium',  -- 'low', 'medium', 'high', 'urgent'
    status TEXT DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'cancelled'
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES fleet_locations(id),
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- EMAIL CAMPAIGNS TABLE
CREATE TABLE IF NOT EXISTS email_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_name TEXT NOT NULL,
    subject_line TEXT,
    body_template TEXT,
    sent_count INTEGER DEFAULT 0,
    opened_count INTEGER DEFAULT 0,
    clicked_count INTEGER DEFAULT 0,
    replied_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

-- EMAIL SENDS TABLE - Track individual emails
CREATE TABLE IF NOT EXISTS email_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    email_address TEXT NOT NULL,
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    replied_at TIMESTAMP,
    bounced BOOLEAN DEFAULT 0,
    FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id),
    FOREIGN KEY (location_id) REFERENCES fleet_locations(id)
);

CREATE INDEX IF NOT EXISTS idx_email_sends_campaign ON email_sends(campaign_id);
CREATE INDEX IF NOT EXISTS idx_email_sends_location ON email_sends(location_id);

-- SMS CAMPAIGNS TABLE
CREATE TABLE IF NOT EXISTS sms_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_name TEXT NOT NULL,
    message_template TEXT NOT NULL,
    sent_count INTEGER DEFAULT 0,
    replied_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

-- SMS SENDS TABLE
CREATE TABLE IF NOT EXISTS sms_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    phone_number TEXT NOT NULL,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    replied_at TIMESTAMP,
    reply_message TEXT,
    FOREIGN KEY (campaign_id) REFERENCES sms_campaigns(id),
    FOREIGN KEY (location_id) REFERENCES fleet_locations(id)
);

CREATE INDEX IF NOT EXISTS idx_sms_sends_campaign ON sms_sends(campaign_id);
CREATE INDEX IF NOT EXISTS idx_sms_sends_location ON sms_sends(location_id);

-- USERS TABLE - Team members
-- Note: This table is also defined in auth_schema.sql with additional auth fields
-- Using IF NOT EXISTS to avoid conflicts - auth_schema should be loaded first
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE,
    password_hash TEXT,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'sales',  -- 'admin', 'sales', 'technician', 'manager'
    phone TEXT,
    company_id INTEGER,
    active BOOLEAN DEFAULT 1,
    email_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    reset_token TEXT,
    reset_token_expires TIMESTAMP
);

-- PERFORMANCE METRICS TABLE
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_id INTEGER,
    metric_date DATE NOT NULL,
    calls_made INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    visits_completed INTEGER DEFAULT 0,
    quotes_generated INTEGER DEFAULT 0,
    deals_won INTEGER DEFAULT 0,
    revenue_generated REAL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_performance_user ON performance_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_performance_date ON performance_metrics(metric_date);

-- NOTES TABLE - General notes/attachments
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER,
    deal_id INTEGER,
    user_id INTEGER,
    note_text TEXT NOT NULL,
    attachment_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES fleet_locations(id),
    FOREIGN KEY (deal_id) REFERENCES deals(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_notes_location ON notes(location_id);
CREATE INDEX IF NOT EXISTS idx_notes_deal ON notes(deal_id);
