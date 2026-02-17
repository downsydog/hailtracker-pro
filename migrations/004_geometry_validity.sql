-- ============================================================================
-- MIGRATION 004: Geometry Validity + Swath Area Columns
-- ============================================================================
-- Adds ST_MakeValid to geometry sync triggers and new columns for
-- swath area tracking on hail_events.
-- ============================================================================

-- Add swath_area_km2 and swath_area_method to hail_events if missing
DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN swath_area_km2 DOUBLE PRECISION DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN swath_area_method TEXT DEFAULT 'unknown';
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

-- Update hail_events trigger: validate geometry with ST_MakeValid
CREATE OR REPLACE FUNCTION hail_events_sync_geom() RETURNS trigger AS $$
BEGIN
    IF NEW.swath_polygon IS NOT NULL AND NEW.swath_polygon != '' THEN
        BEGIN
            NEW.swath_geom := ST_MakeValid(
                ST_SetSRID(ST_GeomFromGeoJSON(NEW.swath_polygon), 4326)
            );
        EXCEPTION WHEN OTHERS THEN
            NEW.swath_geom := NULL;
        END;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update hail_swaths trigger: validate geometry with ST_MakeValid
CREATE OR REPLACE FUNCTION hail_swaths_sync_geom() RETURNS trigger AS $$
BEGIN
    IF NEW.geometry_geojson IS NOT NULL AND NEW.geometry_geojson != '' THEN
        BEGIN
            NEW.swath_geom := ST_MakeValid(
                ST_SetSRID(ST_GeomFromGeoJSON(NEW.geometry_geojson), 4326)
            );
        EXCEPTION WHEN OTHERS THEN
            NEW.swath_geom := NULL;
        END;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add last_valid_swath_utc for cache staleness tracking (Phase C1)
DO $$ BEGIN
    ALTER TABLE hail_swaths ADD COLUMN last_valid_swath_utc TIMESTAMPTZ;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
