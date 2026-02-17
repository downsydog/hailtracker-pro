"""
Prometheus Metrics for HailTracker Radar Pipeline.

Exports counters, gauges, and histograms for:
  - radar_tick lifecycle (ok / error / skipped)
  - per-radar processing outcomes
  - scan / event / swath throughput
  - MRMS freshness
  - backfill progress
  - storage / retention

Usage (instrument code):
    from src.observability.metrics import TICK_TOTAL, TICK_DURATION, ...
    TICK_TOTAL.labels(status='ok').inc()
    TICK_DURATION.observe(wall_seconds)

Endpoint:
    GET /metrics  (or /api/metrics)  — Prometheus scrape target
"""

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import: prometheus_client may not be installed
# ---------------------------------------------------------------------------
_PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.info("prometheus_client not installed — metrics disabled")


def is_available() -> bool:
    """Return True if prometheus_client is importable."""
    return _PROMETHEUS_AVAILABLE


# ---------------------------------------------------------------------------
# Metric definitions (module-level singletons)
# ---------------------------------------------------------------------------
if _PROMETHEUS_AVAILABLE:

    # --- Radar Tick ---
    TICK_TOTAL = Counter(
        'hailtracker_radar_tick_total',
        'Total radar ticks by outcome',
        ['status'],  # ok | error | skipped_lock
    )

    TICK_DURATION = Histogram(
        'hailtracker_radar_tick_duration_seconds',
        'Wall-clock duration of each radar tick',
        buckets=(1, 5, 10, 30, 60, 120, 240, 600),
    )

    TICK_LAST_SUCCESS = Gauge(
        'hailtracker_radar_tick_last_success_unixtime',
        'Unix timestamp of last successful tick',
    )

    # --- Per-radar processing ---
    RADARS_PROCESSED = Counter(
        'hailtracker_radar_radars_processed_total',
        'Radars processed by result',
        ['result'],  # ok | timeout | error
    )

    RADAR_CHECKS_OK = Counter(
        'hailtracker_radar_checks_ok_total',
        'Successful radar checks (one per radar per tick/backfill window)',
    )

    # --- Persist batches ---
    EVENT_PERSIST_BATCHES = Counter(
        'hailtracker_radar_event_persist_batches_total',
        'Successful event persistence batches (one per post-processing call)',
    )

    SWATH_PERSIST_BATCHES = Counter(
        'hailtracker_radar_swath_persist_batches_total',
        'Successful swath persistence batches (one per post-processing call)',
    )

    # --- MRMS ---
    MRMS_UPDATE = Counter(
        'hailtracker_mrms_update_total',
        'MRMS grid fetch attempts by outcome (legacy, prefer MRMS_FETCH_RESULT)',
        ['status'],  # ok | error
    )

    MRMS_GRID_AGE = Gauge(
        'hailtracker_mrms_grid_age_seconds',
        'Seconds since the MRMS grid was last updated',
    )

    MRMS_FETCH_DURATION = Histogram(
        'hailtracker_mrms_fetch_duration_seconds',
        'Wall-clock duration of each MRMS fetch attempt',
        buckets=(0.5, 1, 2, 5, 10, 15, 20, 30, 60),
    )

    MRMS_FETCH_RESULT = Counter(
        'hailtracker_mrms_fetch_result_total',
        'MRMS fetch outcomes',
        ['status'],  # ok_data | ok_empty | error | timeout | skipped_inflight | synthetic
    )

    # --- Swath ---
    SWATH_BUILD_DURATION = Histogram(
        'hailtracker_swath_build_duration_seconds',
        'Wall-clock duration of swath intelligence engine update_swaths()',
        buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
    )

    SWATH_GEOMETRY_REPAIRED = Counter(
        'hailtracker_swath_geometry_repaired_total',
        'Swath geometries repaired by ST_MakeValid or Shapely buffer(0)',
    )

    # --- Backfill ---
    BACKFILL_WINDOWS = Counter(
        'hailtracker_backfill_windows_processed_total',
        'Backfill windows processed',
    )

    # --- Storage ---
    MRMS_ARCHIVE_FILES = Gauge(
        'hailtracker_mrms_archive_file_count',
        'Number of MRMS .npz archive files on disk',
    )

    MRMS_ARCHIVE_BYTES = Gauge(
        'hailtracker_mrms_archive_bytes_total',
        'Total bytes of MRMS .npz archive files on disk',
    )

    # --- DB table row counts ---
    DB_TABLE_ROWS = Gauge(
        'hailtracker_db_table_rows',
        'Approximate row count for key tables',
        ['table'],
    )

    # --- Watchdog ---
    WATCHDOG_SLA_STATE = Gauge(
        'hailtracker_watchdog_sla_state',
        'SLA state: 0=down, 1=degraded, 2=ok',
    )

else:
    # Stub classes so instrumentation code doesn't need if-guards
    class _StubLabels:
        def inc(self, amount=1): pass
        def dec(self, amount=1): pass
        def set(self, value): pass

    class _StubMetric:
        def labels(self, **kw): return _StubLabels()
        def inc(self, amount=1): pass
        def dec(self, amount=1): pass
        def set(self, value): pass
        def observe(self, value): pass

    TICK_TOTAL = _StubMetric()
    TICK_DURATION = _StubMetric()
    TICK_LAST_SUCCESS = _StubMetric()
    RADARS_PROCESSED = _StubMetric()
    RADAR_CHECKS_OK = _StubMetric()
    EVENT_PERSIST_BATCHES = _StubMetric()
    SWATH_PERSIST_BATCHES = _StubMetric()
    MRMS_UPDATE = _StubMetric()
    MRMS_GRID_AGE = _StubMetric()
    MRMS_FETCH_DURATION = _StubMetric()
    MRMS_FETCH_RESULT = _StubMetric()
    SWATH_BUILD_DURATION = _StubMetric()
    SWATH_GEOMETRY_REPAIRED = _StubMetric()
    BACKFILL_WINDOWS = _StubMetric()
    MRMS_ARCHIVE_FILES = _StubMetric()
    MRMS_ARCHIVE_BYTES = _StubMetric()
    DB_TABLE_ROWS = _StubMetric()
    WATCHDOG_SLA_STATE = _StubMetric()


# ---------------------------------------------------------------------------
# Flask endpoint helpers
# ---------------------------------------------------------------------------

def metrics_response():
    """
    Generate Prometheus text-format response body + content type.

    Returns (body_bytes, content_type_str).
    If prometheus_client is unavailable, returns a plain-text fallback.
    """
    if not _PROMETHEUS_AVAILABLE:
        return (b'# prometheus_client not installed\n', 'text/plain; charset=utf-8')

    body = generate_latest(REGISTRY)
    return (body, CONTENT_TYPE_LATEST)


def register_metrics_endpoint(app):
    """
    Register GET /metrics on the Flask app.

    Access is controlled by METRICS_ENABLED env (default true)
    and optionally restricted by METRICS_TOKEN.
    """
    from flask import Response, request as flask_request

    @app.route('/metrics', methods=['GET'])
    def prometheus_metrics():
        # Gate: disabled entirely
        if os.environ.get('METRICS_ENABLED', 'true').lower() not in ('true', '1', 'yes'):
            return Response('metrics disabled', status=404)

        # Optional bearer-token auth
        token = os.environ.get('METRICS_TOKEN', '')
        if token:
            auth = flask_request.headers.get('Authorization', '')
            if auth != f'Bearer {token}':
                return Response('unauthorized', status=401)

        body, content_type = metrics_response()
        return Response(body, content_type=content_type)


# ---------------------------------------------------------------------------
# Convenience: update MRMS age gauge from Redis
# ---------------------------------------------------------------------------

def refresh_mrms_age_gauge(redis_client) -> None:
    """Read mrms:source_time from Redis and update the age gauge."""
    if not _PROMETHEUS_AVAILABLE:
        return
    try:
        from datetime import datetime, timezone
        st = redis_client.get('mrms:source_time')
        if st:
            if isinstance(st, bytes):
                st = st.decode()
            dt = datetime.fromisoformat(st.replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            MRMS_GRID_AGE.set(max(0, age))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Convenience: update storage gauges
# ---------------------------------------------------------------------------

def refresh_storage_gauges(mrms_dir: str = 'data/mrms') -> None:
    """Count MRMS archive files and total bytes on disk."""
    if not _PROMETHEUS_AVAILABLE:
        return
    try:
        import glob as glob_mod
        files = glob_mod.glob(os.path.join(mrms_dir, '*.npz'))
        MRMS_ARCHIVE_FILES.set(len(files))
        total_bytes = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
        MRMS_ARCHIVE_BYTES.set(total_bytes)
    except Exception:
        pass


def refresh_db_table_gauges() -> None:
    """Sample row counts for key tables and update gauges."""
    if not _PROMETHEUS_AVAILABLE:
        return
    try:
        from src.db.engine import get_connection
        tables = ['hail_detections', 'hail_events', 'hail_swaths']
        with get_connection() as conn:
            cur = conn.cursor()
            for table in tables:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM {table}')  # noqa: S608
                    count = cur.fetchone()[0]
                    DB_TABLE_ROWS.labels(table=table).set(count)
                except Exception:
                    pass
    except Exception:
        pass
