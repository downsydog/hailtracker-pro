-- MIGRATION 006: MRMS Backfill — partial unique index + mrms_core columns
--
-- Enables ON CONFLICT(event_name) WHERE data_source = 'MRMS_BACKFILL'
-- for idempotent re-runs of the MRMS MESH historical backfill pipeline.
--
-- Also adds mrms_core polygon columns that were previously only available
-- via inline ALTER TABLE in storm_monitor.py (SQLite path).

CREATE UNIQUE INDEX IF NOT EXISTS idx_hail_events_mrms_backfill_upsert
    ON hail_events(event_name) WHERE data_source = 'MRMS_BACKFILL';

-- MRMS core polygon columns (idempotent via DO/EXCEPTION)
DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN mrms_core_15_geojson TEXT;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN mrms_core_25_geojson TEXT;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN mrms_core_40_geojson TEXT;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN mrms_core_15_km2 REAL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN mrms_core_25_km2 REAL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE hail_events ADD COLUMN mrms_core_40_km2 REAL DEFAULT 0;
EXCEPTION WHEN duplicate_column THEN NULL;
END $$;
