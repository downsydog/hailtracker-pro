-- ============================================================================
-- MIGRATION 005: Add event_date index for /api/events query performance
-- ============================================================================
-- The /api/events endpoint filters by event_date DESC with LIMIT.
-- Without this index, the query does a full table scan on 10k+ rows.
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_hail_events_event_date ON hail_events (event_date DESC);
CREATE INDEX IF NOT EXISTS idx_hail_events_status_date ON hail_events (status, event_date DESC);
