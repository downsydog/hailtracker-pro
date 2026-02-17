-- ============================================================================
-- MIGRATION 002: CRM + Fleet Locations PostGIS Schema
-- ============================================================================
-- Target: PostgreSQL 16 + PostGIS 3.4+
-- Run:    psql -U hailtracker -d hailtracker -f migrations/002_crm_fleet_schema.sql
--
-- Covers:
--   Fleet locations (with PostGIS geom), fleet_categories,
--   hail_event_locations, watch_list, planned_routes, route_stops,
--   CRM tables: interactions, deals, tasks, users, notes,
--   email_campaigns, email_sends, sms_campaigns, sms_sends,
--   performance_metrics, alerts, alert_stats
-- ============================================================================

-- ============================================================================
-- FLEET LOCATIONS — Main table with PostGIS geometry
-- ============================================================================

CREATE TABLE IF NOT EXISTS fleet_locations (
    id BIGSERIAL PRIMARY KEY,

    -- Basic info
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    brand TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    country TEXT DEFAULT 'US',
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,

    -- PostGIS geometry (auto-populated from lat/lon)
    geom geometry(Point, 4326)
        GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED,

    -- Contact details
    phone TEXT,
    email TEXT,
    website TEXT,
    manager_name TEXT,
    manager_title TEXT,
    fleet_manager_name TEXT,
    fleet_manager_phone TEXT,
    decision_maker TEXT,
    best_contact_method TEXT,
    contact_notes TEXT,

    -- Vehicle data
    estimated_vehicles INTEGER DEFAULT 50,
    vehicle_confidence TEXT DEFAULT 'medium',
    lot_size_sqm INTEGER,
    parking_type TEXT DEFAULT 'outdoor_uncovered',
    vehicle_types TEXT,
    luxury_vehicles BOOLEAN DEFAULT FALSE,
    average_vehicle_value INTEGER DEFAULT 35000,

    -- Accessibility
    accessibility TEXT DEFAULT 'public',
    requires_appointment BOOLEAN DEFAULT FALSE,
    has_security_gate BOOLEAN DEFAULT FALSE,
    gate_code TEXT,
    security_guard BOOLEAN DEFAULT FALSE,
    can_canvas_lot BOOLEAN DEFAULT TRUE,
    operating_hours TEXT,
    best_approach_time TEXT,
    access_restrictions TEXT,
    parking_fee BOOLEAN DEFAULT FALSE,

    -- Business intelligence (CRM)
    worked_before BOOLEAN DEFAULT FALSE,
    last_visit_date DATE,
    num_previous_visits INTEGER DEFAULT 0,
    conversion_rate DOUBLE PRECISION,
    avg_revenue_per_vehicle DOUBLE PRECISION DEFAULT 1500,
    total_revenue_historical DOUBLE PRECISION DEFAULT 0,
    customer_satisfaction TEXT,
    payment_speed TEXT,
    notes TEXT,
    internal_champion TEXT,

    -- Competition
    competitors_present TEXT,
    competitor_last_seen DATE,
    market_saturation TEXT DEFAULT 'low',

    -- OSM data
    osm_id TEXT,
    osm_type TEXT,

    -- Metadata
    data_source TEXT DEFAULT 'osm',
    verified BOOLEAN DEFAULT FALSE,
    verified_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spatial index (GiST)
CREATE INDEX IF NOT EXISTS idx_fleet_locations_geom ON fleet_locations USING GIST(geom);
-- B-tree indexes
CREATE INDEX IF NOT EXISTS idx_fleet_locations_category ON fleet_locations(category);
CREATE INDEX IF NOT EXISTS idx_fleet_locations_lat_lon ON fleet_locations(lat, lon);
CREATE INDEX IF NOT EXISTS idx_fleet_locations_city ON fleet_locations(city);
CREATE INDEX IF NOT EXISTS idx_fleet_locations_state ON fleet_locations(state);
CREATE INDEX IF NOT EXISTS idx_fleet_locations_vehicles ON fleet_locations(estimated_vehicles);
CREATE UNIQUE INDEX IF NOT EXISTS idx_fleet_locations_osm ON fleet_locations(osm_id, osm_type)
    WHERE osm_id IS NOT NULL;

-- ============================================================================
-- FLEET CATEGORIES — Category definitions
-- ============================================================================

CREATE TABLE IF NOT EXISTS fleet_categories (
    id BIGSERIAL PRIMARY KEY,
    category TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    tier INTEGER DEFAULT 2,
    avg_vehicles INTEGER DEFAULT 50,
    avg_revenue_per_vehicle DOUBLE PRECISION DEFAULT 1500,
    description TEXT,
    osm_tags TEXT
);

INSERT INTO fleet_categories (category, display_name, icon, color, tier, avg_vehicles, avg_revenue_per_vehicle, description, osm_tags) VALUES
('car_dealership', 'Car Dealerships', '🚗', '#4CAF50', 1, 200, 2000, 'New and used car dealerships', '{}'),
('rental_car', 'Rental Car Locations', '🚙', '#2196F3', 1, 100, 1800, 'Enterprise, Hertz, Budget, etc.', '{}'),
('parking_structure', 'Parking Structures', '🅿️', '#9C27B0', 1, 500, 1500, 'Multi-story garages, open lots', '{}'),
('municipal', 'Municipal Fleets', '🏛️', '#F44336', 1, 100, 1600, 'City, county, government vehicles', '{}'),
('utility', 'Utility Companies', '⚡', '#FFEB3B', 1, 150, 1700, 'Electric, gas, water, telecom fleets', '{}'),
('service_company', 'Service Companies', '🔨', '#795548', 2, 25, 1400, 'HVAC, plumbing, electrical contractors', '{}'),
('delivery', 'Delivery/Logistics', '📦', '#607D8B', 2, 200, 1500, 'UPS, FedEx, Amazon, USPS', '{}'),
('body_shop', 'Body Shops', '🔧', '#FF9800', 2, 30, 1200, 'Auto body and collision repair', '{}'),
('golf_course', 'Golf Courses', '⛳', '#8BC34A', 2, 150, 2200, 'Country clubs with wealthy clientele', '{}'),
('apartment', 'Large Apartments', '🏘️', '#00BCD4', 2, 200, 1300, '200+ unit complexes with outdoor parking', '{}'),
('school', 'Schools/Universities', '🏫', '#673AB7', 3, 150, 1400, 'School parking lots and bus yards', '{}'),
('hospital', 'Hospitals', '🏥', '#E91E63', 3, 300, 1500, 'Hospital and medical center parking', '{}'),
('hotel', 'Hotels', '🏨', '#009688', 3, 80, 1400, 'Hotels with outdoor parking', '{}'),
('event_venue', 'Event Venues', '🎪', '#FF5722', 3, 2000, 1500, 'Stadiums, arenas, fairgrounds', '{}'),
('insurance', 'Insurance Offices', '💼', '#3F51B5', 3, 10, 0, 'Partnership opportunities', '{}')
ON CONFLICT (category) DO NOTHING;

-- ============================================================================
-- HAIL EVENT LOCATIONS — Link events to fleet locations
-- ============================================================================

CREATE TABLE IF NOT EXISTS hail_event_locations (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL,
    location_id BIGINT NOT NULL,

    in_swath BOOLEAN DEFAULT TRUE,
    hail_size_inches DOUBLE PRECISION,
    hail_duration_minutes INTEGER,
    confidence_score DOUBLE PRECISION DEFAULT 0.8,
    social_media_confirmations INTEGER DEFAULT 0,
    damage_severity_estimate TEXT,

    estimated_damaged_vehicles INTEGER,
    estimated_total_revenue DOUBLE PRECISION,
    priority_score INTEGER,
    opportunity_grade TEXT,

    time_since_hail_hours INTEGER,
    estimated_unclaimed_percentage DOUBLE PRECISION DEFAULT 1.0,

    status TEXT DEFAULT 'new',
    contacted_date TIMESTAMPTZ,
    visited_date TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_event_location UNIQUE (event_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_hel_event ON hail_event_locations(event_id);
CREATE INDEX IF NOT EXISTS idx_hel_location ON hail_event_locations(location_id);
CREATE INDEX IF NOT EXISTS idx_hel_priority ON hail_event_locations(priority_score DESC);

-- ============================================================================
-- WATCH LIST
-- ============================================================================

CREATE TABLE IF NOT EXISTS watch_list (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER DEFAULT 1,
    location_id BIGINT NOT NULL,
    notes TEXT,
    alert_on_hail BOOLEAN DEFAULT TRUE,
    priority_override INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_watch UNIQUE (user_id, location_id)
);

-- ============================================================================
-- PLANNED ROUTES + STOPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS planned_routes (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER DEFAULT 1,
    event_id BIGINT,
    route_name TEXT,
    locations TEXT NOT NULL,
    total_distance_km DOUBLE PRECISION,
    total_distance_miles DOUBLE PRECISION,
    estimated_time_hours DOUBLE PRECISION,
    estimated_fuel_cost DOUBLE PRECISION,
    total_vehicles INTEGER,
    estimated_revenue DOUBLE PRECISION,
    status TEXT DEFAULT 'planned',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS route_stops (
    id BIGSERIAL PRIMARY KEY,
    route_id BIGINT NOT NULL REFERENCES planned_routes(id),
    location_id BIGINT NOT NULL,
    stop_order INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    arrived_at TIMESTAMPTZ,
    departed_at TIMESTAMPTZ,
    vehicles_contacted INTEGER,
    vehicles_converted INTEGER,
    revenue_actual DOUBLE PRECISION,
    notes TEXT
);

-- ============================================================================
-- CRM TABLES
-- ============================================================================

-- Users (CRM + auth combined)
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE,
    password_hash TEXT,
    full_name TEXT NOT NULL,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'sales',
    phone TEXT,
    company_id INTEGER,
    active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    login_count INTEGER DEFAULT 0,
    reset_token TEXT,
    reset_token_expires TIMESTAMPTZ
);

-- Interactions
CREATE TABLE IF NOT EXISTS interactions (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL,
    user_id BIGINT,
    interaction_type TEXT NOT NULL,
    interaction_date TIMESTAMPTZ DEFAULT NOW(),
    outcome TEXT,
    notes TEXT,
    duration_seconds INTEGER,
    next_followup_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interactions_location ON interactions(location_id);
CREATE INDEX IF NOT EXISTS idx_interactions_date ON interactions(interaction_date);

-- Deals
CREATE TABLE IF NOT EXISTS deals (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL,
    event_id BIGINT,
    stage TEXT NOT NULL,
    estimated_value DOUBLE PRECISION,
    actual_value DOUBLE PRECISION,
    probability INTEGER DEFAULT 0,
    expected_close_date DATE,
    actual_close_date DATE,
    lost_reason TEXT,
    assigned_to BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
CREATE INDEX IF NOT EXISTS idx_deals_location ON deals(location_id);

-- Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT,
    deal_id BIGINT,
    assigned_to BIGINT,
    task_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date TIMESTAMPTZ,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date);

-- Notes
CREATE TABLE IF NOT EXISTS notes (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT,
    deal_id BIGINT,
    user_id BIGINT,
    note_text TEXT NOT NULL,
    attachment_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email campaigns
CREATE TABLE IF NOT EXISTS email_campaigns (
    id BIGSERIAL PRIMARY KEY,
    campaign_name TEXT NOT NULL,
    subject_line TEXT,
    body_template TEXT,
    sent_count INTEGER DEFAULT 0,
    opened_count INTEGER DEFAULT 0,
    clicked_count INTEGER DEFAULT 0,
    replied_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS email_sends (
    id BIGSERIAL PRIMARY KEY,
    campaign_id BIGINT NOT NULL REFERENCES email_campaigns(id),
    location_id BIGINT NOT NULL,
    email_address TEXT NOT NULL,
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    bounced BOOLEAN DEFAULT FALSE
);

-- SMS campaigns
CREATE TABLE IF NOT EXISTS sms_campaigns (
    id BIGSERIAL PRIMARY KEY,
    campaign_name TEXT NOT NULL,
    message_template TEXT NOT NULL,
    sent_count INTEGER DEFAULT 0,
    replied_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sms_sends (
    id BIGSERIAL PRIMARY KEY,
    campaign_id BIGINT NOT NULL REFERENCES sms_campaigns(id),
    location_id BIGINT NOT NULL,
    phone_number TEXT NOT NULL,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    reply_message TEXT
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    event_id BIGINT,
    metric_date DATE NOT NULL,
    calls_made INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    visits_completed INTEGER DEFAULT 0,
    quotes_generated INTEGER DEFAULT 0,
    deals_won INTEGER DEFAULT 0,
    revenue_generated DOUBLE PRECISION DEFAULT 0
);

-- ============================================================================
-- ALERTS TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    level TEXT NOT NULL,
    event_name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    radar_id TEXT NOT NULL,
    hail_detected BOOLEAN NOT NULL,
    hail_probability DOUBLE PRECISION NOT NULL,
    hail_size_mm DOUBLE PRECISION NOT NULL,
    severity TEXT NOT NULL,
    pdr_score DOUBLE PRECISION NOT NULL,
    max_reflectivity DOUBLE PRECISION NOT NULL,
    mesh_mm DOUBLE PRECISION NOT NULL,
    posh DOUBLE PRECISION NOT NULL,
    message TEXT,
    recommendations JSONB,
    expires TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level);
CREATE INDEX IF NOT EXISTS idx_alerts_radar ON alerts(radar_id);
CREATE INDEX IF NOT EXISTS idx_alerts_pdr ON alerts(pdr_score);

CREATE TABLE IF NOT EXISTS alert_stats (
    date DATE PRIMARY KEY,
    total_alerts INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    watch_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,
    avg_pdr_score DOUBLE PRECISION DEFAULT 0,
    max_hail_size DOUBLE PRECISION DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
