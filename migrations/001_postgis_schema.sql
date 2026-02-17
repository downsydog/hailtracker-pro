-- ============================================================================
-- MIGRATION 001: PostGIS Schema for HailTracker Radar Pipeline
-- ============================================================================
-- Target: PostgreSQL 16 + PostGIS 3.4+
-- Run:    psql -U hailtracker -d hailtracker -f migrations/001_postgis_schema.sql
--
-- This migration covers the radar pipeline hot-path tables:
--   hail_events, hail_detections, hail_swaths, affected_locations
--
-- CRM/auth/fleet tables are migrated separately in 002_crm_schema.sql
-- ============================================================================

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- HAIL EVENTS — Master table for hail events
-- ============================================================================

CREATE TABLE IF NOT EXISTS hail_events (
    id BIGSERIAL PRIMARY KEY,

    -- Event identification
    event_name TEXT,
    event_date DATE,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,

    -- Geographic info (PostGIS geometry + legacy scalar columns)
    center_lat DOUBLE PRECISION,
    center_lon DOUBLE PRECISION,
    center_geom geometry(Point, 4326)
        GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)) STORED,

    -- Swath polygon: stored as native PostGIS geometry AND as TEXT for backward compat
    swath_polygon TEXT,                        -- GeoJSON text (kept for API responses)
    swath_geom geometry(Geometry, 4326),      -- PostGIS native (populated by trigger)

    swath_area_sqmi DOUBLE PRECISION,

    -- Storm characteristics
    max_hail_size DOUBLE PRECISION,           -- inches
    avg_hail_size DOUBLE PRECISION,           -- inches
    max_reflectivity DOUBLE PRECISION,        -- dBZ
    avg_reflectivity DOUBLE PRECISION,        -- dBZ

    -- Storm movement
    storm_motion_dir DOUBLE PRECISION,        -- degrees (0=North)
    storm_motion_speed DOUBLE PRECISION,      -- mph

    -- Metadata
    swath_method TEXT,
    num_detections INTEGER DEFAULT 1,
    data_source TEXT DEFAULT 'NEXRAD',
    confidence_score DOUBLE PRECISION,

    -- Evidence flags
    evidence_mrms INTEGER DEFAULT 0,
    evidence_dualpol INTEGER DEFAULT 0,
    evidence_multi_radar INTEGER DEFAULT 0,
    evidence_spc INTEGER DEFAULT 0,
    evidence_lsr INTEGER DEFAULT 0,
    evidence_persistence INTEGER DEFAULT 0,

    -- Bounding box (computed; redundant with swath_geom envelope but kept for compat)
    bbox_min_lat DOUBLE PRECISION,
    bbox_max_lat DOUBLE PRECISION,
    bbox_min_lon DOUBLE PRECISION,
    bbox_max_lon DOUBLE PRECISION,

    -- Severity classification
    severity TEXT DEFAULT 'MINOR',

    -- Event lifecycle
    status TEXT DEFAULT 'CANDIDATE',

    -- Related data
    affected_locations INTEGER DEFAULT 0,
    estimated_vehicles INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Partial unique index: enforce uniqueness for realtime tracker events only
CREATE UNIQUE INDEX IF NOT EXISTS idx_hail_events_rt_upsert
    ON hail_events(event_name) WHERE data_source = 'NEXRAD_REALTIME';

-- Standard B-tree indexes
CREATE INDEX IF NOT EXISTS idx_hail_events_date ON hail_events(event_date);
CREATE INDEX IF NOT EXISTS idx_hail_events_method ON hail_events(swath_method);
CREATE INDEX IF NOT EXISTS idx_hail_events_hail_size ON hail_events(max_hail_size);
CREATE INDEX IF NOT EXISTS idx_hail_events_status ON hail_events(status);
CREATE INDEX IF NOT EXISTS idx_hail_events_data_source ON hail_events(data_source);

-- PostGIS spatial indexes (GiST)
CREATE INDEX IF NOT EXISTS idx_hail_events_center_geom ON hail_events USING GIST(center_geom);
CREATE INDEX IF NOT EXISTS idx_hail_events_swath_geom ON hail_events USING GIST(swath_geom);

-- Legacy (center_lat, center_lon) B-tree for non-spatial queries
CREATE INDEX IF NOT EXISTS idx_hail_events_location ON hail_events(center_lat, center_lon);

-- Trigger: auto-populate swath_geom from swath_polygon TEXT on INSERT/UPDATE
CREATE OR REPLACE FUNCTION hail_events_sync_geom() RETURNS trigger AS $$
BEGIN
    IF NEW.swath_polygon IS NOT NULL AND NEW.swath_polygon != '' THEN
        BEGIN
            NEW.swath_geom := ST_SetSRID(ST_GeomFromGeoJSON(NEW.swath_polygon), 4326);
        EXCEPTION WHEN OTHERS THEN
            -- Invalid GeoJSON: leave swath_geom as NULL
            NEW.swath_geom := NULL;
        END;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_hail_events_sync_geom
    BEFORE INSERT OR UPDATE ON hail_events
    FOR EACH ROW EXECUTE FUNCTION hail_events_sync_geom();


-- ============================================================================
-- HAIL DETECTIONS — Individual radar observations
-- ============================================================================

CREATE TABLE IF NOT EXISTS hail_detections (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL,

    -- Detection info
    detection_time TIMESTAMPTZ NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    geom geometry(Point, 4326)
        GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED,

    -- Hail characteristics
    hail_size DOUBLE PRECISION NOT NULL,      -- inches
    reflectivity DOUBLE PRECISION,            -- dBZ

    -- Storm motion at this detection point
    storm_motion_dir DOUBLE PRECISION,        -- degrees
    storm_motion_speed DOUBLE PRECISION,      -- mph

    -- Radar info
    radar_site TEXT,
    elevation_angle DOUBLE PRECISION,
    range_miles DOUBLE PRECISION,

    -- Quality metrics
    confidence_score DOUBLE PRECISION,
    data_source TEXT DEFAULT 'NEXRAD',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_detections_event
        FOREIGN KEY (event_id) REFERENCES hail_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_hail_detections_event ON hail_detections(event_id);
CREATE INDEX IF NOT EXISTS idx_hail_detections_time ON hail_detections(detection_time);
CREATE INDEX IF NOT EXISTS idx_hail_detections_geom ON hail_detections USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_hail_detections_location ON hail_detections(lat, lon);


-- ============================================================================
-- HAIL SWATHS — Intelligence engine swath tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS hail_swaths (
    swath_id TEXT PRIMARY KEY,
    first_seen_utc TEXT NOT NULL,
    last_seen_utc TEXT NOT NULL,

    centroid_lat DOUBLE PRECISION NOT NULL,
    centroid_lon DOUBLE PRECISION NOT NULL,
    centroid_geom geometry(Point, 4326)
        GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(centroid_lon, centroid_lat), 4326)) STORED,

    area_km2 DOUBLE PRECISION DEFAULT 0,
    severe_core_km2 DOUBLE PRECISION DEFAULT 0,
    mean_hail_size DOUBLE PRECISION DEFAULT 0,
    max_hail_size DOUBLE PRECISION DEFAULT 0,
    impact_score INTEGER DEFAULT 0,
    impact_tier TEXT DEFAULT 'LOW',
    lifecycle_state TEXT DEFAULT 'FORMING',
    confidence_avg DOUBLE PRECISION DEFAULT 0,
    confirmed_event_count INTEGER DEFAULT 0,
    candidate_event_count INTEGER DEFAULT 0,
    directional_vector_deg DOUBLE PRECISION,
    velocity_kmh DOUBLE PRECISION,
    growth_rate_km2_per_min DOUBLE PRECISION DEFAULT 0,
    decay_cycles INTEGER DEFAULT 0,

    -- Geometry: stored as TEXT + native PostGIS
    geometry_geojson TEXT,
    swath_geom geometry(Geometry, 4326),

    member_event_names TEXT,
    area_method TEXT DEFAULT 'unknown',
    geometry_quality TEXT DEFAULT 'LOW',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_swaths_time ON hail_swaths(last_seen_utc);
CREATE INDEX IF NOT EXISTS idx_swaths_state ON hail_swaths(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_swaths_impact ON hail_swaths(impact_score);
CREATE INDEX IF NOT EXISTS idx_swaths_centroid_geom ON hail_swaths USING GIST(centroid_geom);
CREATE INDEX IF NOT EXISTS idx_swaths_swath_geom ON hail_swaths USING GIST(swath_geom);
CREATE INDEX IF NOT EXISTS idx_swaths_loc ON hail_swaths(centroid_lat, centroid_lon);

-- Trigger: sync geometry_geojson → swath_geom
CREATE OR REPLACE FUNCTION hail_swaths_sync_geom() RETURNS trigger AS $$
BEGIN
    IF NEW.geometry_geojson IS NOT NULL AND NEW.geometry_geojson != '' THEN
        BEGIN
            NEW.swath_geom := ST_SetSRID(ST_GeomFromGeoJSON(NEW.geometry_geojson), 4326);
        EXCEPTION WHEN OTHERS THEN
            NEW.swath_geom := NULL;
        END;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_hail_swaths_sync_geom
    BEFORE INSERT OR UPDATE ON hail_swaths
    FOR EACH ROW EXECUTE FUNCTION hail_swaths_sync_geom();


-- ============================================================================
-- AFFECTED LOCATIONS — Junction table linking events to fleet locations
-- ============================================================================

CREATE TABLE IF NOT EXISTS affected_locations (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL,
    location_id BIGINT NOT NULL,

    -- Impact assessment
    distance_from_center_miles DOUBLE PRECISION,
    estimated_hail_size DOUBLE PRECISION,
    confidence DOUBLE PRECISION,

    -- Marketing status
    contacted BOOLEAN DEFAULT FALSE,
    deal_created BOOLEAN DEFAULT FALSE,
    deal_id BIGINT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_affected_event
        FOREIGN KEY (event_id) REFERENCES hail_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_affected_locations_event ON affected_locations(event_id);
CREATE INDEX IF NOT EXISTS idx_affected_locations_location ON affected_locations(location_id);


-- ============================================================================
-- HELPER FUNCTION: UPSERT for intelligence engine
-- ============================================================================
-- The intelligence engine's _UPSERT_SQL uses SQLite's ON CONFLICT syntax.
-- PostgreSQL supports ON CONFLICT natively with the same semantics.
-- The UPSERT SQL in Python code will be migrated to use %s placeholders
-- and GREATEST() instead of MAX() for the max_hail_size merge.
-- ============================================================================
