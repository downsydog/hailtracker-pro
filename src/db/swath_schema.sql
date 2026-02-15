-- ============================================================================
-- HAIL SWATH DATABASE SCHEMA
-- ============================================================================

-- HAIL EVENTS - Master table for hail events
CREATE TABLE IF NOT EXISTS hail_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Event identification
    event_name TEXT NOT NULL,  -- e.g. "Dallas-Fort Worth Nov 15 2024"
    event_date DATE NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,

    -- Geographic info
    center_lat REAL NOT NULL,
    center_lon REAL NOT NULL,
    swath_polygon TEXT NOT NULL,  -- GeoJSON polygon
    swath_area_sqmi REAL,

    -- Storm characteristics
    max_hail_size REAL,  -- inches
    avg_hail_size REAL,  -- inches
    max_reflectivity REAL,  -- dBZ
    avg_reflectivity REAL,  -- dBZ

    -- Storm movement
    storm_motion_dir REAL,  -- degrees (0=North)
    storm_motion_speed REAL,  -- mph

    -- Metadata
    swath_method TEXT NOT NULL,  -- 'circular', 'elliptical', 'track', 'composite', 'reflectivity'
    num_detections INTEGER DEFAULT 1,
    data_source TEXT DEFAULT 'NEXRAD',  -- 'NEXRAD', 'Social Media', 'Manual', 'Combined'
    confidence_score REAL,  -- 0-100

    -- Related data
    affected_locations INTEGER DEFAULT 0,  -- Count of fleet locations hit
    estimated_vehicles INTEGER DEFAULT 0,  -- Total vehicles affected

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_hail_events_date ON hail_events(event_date);
CREATE INDEX IF NOT EXISTS idx_hail_events_location ON hail_events(center_lat, center_lon);
CREATE INDEX IF NOT EXISTS idx_hail_events_method ON hail_events(swath_method);
CREATE INDEX IF NOT EXISTS idx_hail_events_hail_size ON hail_events(max_hail_size);

-- Partial unique index: enforce uniqueness for realtime tracker events only
-- (historical NOAA data may have duplicate event_names, so this is scoped)
CREATE UNIQUE INDEX IF NOT EXISTS idx_hail_events_rt_upsert
    ON hail_events(event_name) WHERE data_source = 'NEXRAD_REALTIME';

-- HAIL DETECTIONS - Individual radar observations
CREATE TABLE IF NOT EXISTS hail_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,

    -- Detection info
    detection_time TIMESTAMP NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,

    -- Hail characteristics
    hail_size REAL NOT NULL,  -- inches
    reflectivity REAL,  -- dBZ

    -- Storm motion at this detection point
    storm_motion_dir REAL,  -- degrees
    storm_motion_speed REAL,  -- mph

    -- Radar info
    radar_site TEXT,  -- e.g. 'KFWS' (Fort Worth)
    elevation_angle REAL,  -- radar beam elevation
    range_miles REAL,  -- distance from radar

    -- Quality metrics
    confidence_score REAL,  -- 0-100
    data_source TEXT DEFAULT 'NEXRAD',

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (event_id) REFERENCES hail_events(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_hail_detections_event ON hail_detections(event_id);
CREATE INDEX IF NOT EXISTS idx_hail_detections_time ON hail_detections(detection_time);
CREATE INDEX IF NOT EXISTS idx_hail_detections_location ON hail_detections(lat, lon);

-- AFFECTED LOCATIONS - Junction table linking events to fleet locations
CREATE TABLE IF NOT EXISTS affected_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,  -- References fleet_locations table (from Phase 1-9)

    -- Impact assessment
    distance_from_center_miles REAL,
    estimated_hail_size REAL,  -- Interpolated hail size at this location
    confidence REAL,  -- 0-100

    -- Marketing status
    contacted BOOLEAN DEFAULT 0,
    deal_created BOOLEAN DEFAULT 0,
    deal_id INTEGER,  -- References deals table if deal created

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (event_id) REFERENCES hail_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_affected_locations_event ON affected_locations(event_id);
CREATE INDEX IF NOT EXISTS idx_affected_locations_location ON affected_locations(location_id);
