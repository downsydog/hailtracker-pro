"""
Health, Readiness, and SLA Checks
=================================

Provides:
  GET /api/system/health  — Liveness probe (always 200 if process is alive)
  GET /api/system/ready   — Readiness probe (checks DB, Redis, radar pipeline,
                            MRMS, returns SLA state)
  GET /api/system/metrics — Lightweight application metrics

SLA States (dependency-aware):
  ok       — tick < 5 min AND MRMS < 10 min
  degraded — tick 5-15 min, OR MRMS stale (>= 10 min) with tick ok
  down     — tick >= 15 min (MRMS alone never causes DOWN)
"""

import os
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)

# Process start time (for uptime)
_start_time = time.monotonic()
_start_utc = datetime.now(timezone.utc).isoformat()

# SLA thresholds (seconds)
_SLA_OK_TICK_AGE = 300          # 5 minutes
_SLA_OK_MRMS_AGE = 600          # 10 minutes
_SLA_DEGRADED_TICK_AGE = 900    # 15 minutes
_SLA_DEGRADED_MRMS_AGE = 1800   # 30 minutes


class HealthCheck:
    """
    Aggregates readiness checks from subsystems.

    Usage:
        hc = HealthCheck()
        hc.register('database', check_db_func)
        hc.register('mrms_cache', check_mrms_func)

        status = hc.check_all()
        # {'healthy': True, 'checks': {'database': {'ok': True, 'ms': 2}, ...}}
    """

    def __init__(self):
        self._checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._lock = threading.Lock()
        # Counters
        self._request_count = 0
        self._error_count = 0

    def register(self, name: str, check_fn: Callable[[], Dict[str, Any]]):
        """Register a readiness check.

        check_fn should return {'ok': bool, ...extra_info}.
        It must not block for more than 5 seconds.
        """
        with self._lock:
            self._checks[name] = check_fn

    def increment_requests(self):
        self._request_count += 1

    def increment_errors(self):
        self._error_count += 1

    def check_all(self) -> Dict[str, Any]:
        """Run all readiness checks and return aggregated result."""
        results = {}
        all_ok = True

        with self._lock:
            checks = dict(self._checks)

        for name, fn in checks.items():
            t0 = time.monotonic()
            try:
                result = fn()
                result['ms'] = round((time.monotonic() - t0) * 1000, 1)
                results[name] = result
                if not result.get('ok', False):
                    all_ok = False
            except Exception as e:
                results[name] = {
                    'ok': False,
                    'error': str(e),
                    'ms': round((time.monotonic() - t0) * 1000, 1),
                }
                all_ok = False

        # Compute SLA state from radar_pipeline check if present
        sla = _compute_sla_state(results.get('radar_pipeline'))

        return {
            'healthy': all_ok,
            'sla_state': sla,
            'checks': results,
        }

    def get_health(self) -> Dict[str, Any]:
        """Liveness probe — always returns OK if process is alive."""
        return {
            'status': 'ok',
            'uptime_seconds': round(time.monotonic() - _start_time, 1),
            'started_at': _start_utc,
            'pid': os.getpid(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Lightweight application metrics."""
        import sys
        return {
            'uptime_seconds': round(time.monotonic() - _start_time, 1),
            'started_at': _start_utc,
            'requests_total': self._request_count,
            'errors_total': self._error_count,
            'python_version': sys.version.split()[0],
            'pid': os.getpid(),
            'thread_count': threading.active_count(),
        }


# ---------------------------------------------------------------------------
# SLA state computation
# ---------------------------------------------------------------------------

def _compute_sla_state(radar_check: Optional[Dict[str, Any]]) -> str:
    """
    Derive SLA state from the radar_pipeline check result.

    Returns 'ok', 'degraded', or 'down'.

    Rules (dependency-aware):
      - Tick stale (>= 15 min)  → DOWN  (radar pipeline is the critical path)
      - MRMS stale alone        → DEGRADED  (never DOWN from MRMS alone)
      - Tick ok + MRMS ok       → OK
      - Tick slightly stale     → DEGRADED
    """
    if radar_check is None:
        return 'unknown'

    tick_age = radar_check.get('tick_age_seconds')
    mrms_age = radar_check.get('mrms_age_seconds')

    # No tick data at all → down
    if tick_age is None:
        return 'down'

    # Tick hard-down: >= 15 min stale → DOWN regardless of MRMS
    if tick_age >= _SLA_DEGRADED_TICK_AGE:
        return 'down'

    # Tick in ok range (< 5 min)
    if tick_age < _SLA_OK_TICK_AGE:
        # MRMS stale → DEGRADED (not DOWN — MRMS is an auxiliary input)
        if mrms_age is not None and mrms_age >= _SLA_OK_MRMS_AGE:
            return 'degraded'
        return 'ok'

    # Tick in warning range (5-15 min) → DEGRADED
    return 'degraded'


def compute_sla_state_from_redis(redis_client) -> Dict[str, Any]:
    """
    Compute SLA state directly from Redis keys.

    Useful for watchdog (Celery worker context, no Flask).
    Returns:
        {
            'state': str,            # ok | degraded | down
            'tick_age_seconds': float,
            'mrms_age_seconds': float,
            'mrms_source_time': str,  # ISO timestamp of last MRMS grid
        }
    """
    now = datetime.now(timezone.utc)
    result: Dict[str, Any] = {
        'state': 'down',
        'tick_age_seconds': None,
        'mrms_age_seconds': None,
        'mrms_source_time': None,
    }

    try:
        last_tick_utc = redis_client.get('radar:last_tick_utc')
        last_tick_status = redis_client.get('radar:last_tick_status')

        if last_tick_utc:
            dt = datetime.fromisoformat(last_tick_utc.replace('Z', '+00:00'))
            result['tick_age_seconds'] = round((now - dt).total_seconds(), 1)

        mrms_source_time = redis_client.get('mrms:source_time')
        if mrms_source_time:
            result['mrms_source_time'] = mrms_source_time
            dt = datetime.fromisoformat(mrms_source_time.replace('Z', '+00:00'))
            result['mrms_age_seconds'] = round((now - dt).total_seconds(), 1)

        # Only consider SLA ok/degraded if last tick was actually ok
        if last_tick_status != 'ok':
            if result['tick_age_seconds'] is None or result['tick_age_seconds'] >= _SLA_DEGRADED_TICK_AGE:
                result['state'] = 'down'
            else:
                result['state'] = 'degraded'
            return result

        # Reuse the same dependency-aware logic
        radar_check = {
            'tick_age_seconds': result['tick_age_seconds'],
            'mrms_age_seconds': result['mrms_age_seconds'],
        }
        result['state'] = _compute_sla_state(radar_check)
    except Exception as e:
        result['state'] = 'down'
        result['error'] = str(e)

    return result


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[HealthCheck] = None
_instance_lock = threading.Lock()


def get_health_check() -> HealthCheck:
    """Get the singleton HealthCheck instance."""
    global _instance
    if _instance is not None:
        return _instance
    with _instance_lock:
        if _instance is not None:
            return _instance
        _instance = HealthCheck()
        return _instance


# ---------------------------------------------------------------------------
# Radar pipeline health check (expanded)
# ---------------------------------------------------------------------------

def check_radar_pipeline(redis_url: str = 'redis://localhost:6379/0') -> Dict[str, Any]:
    """
    Check radar pipeline health by reading Redis state keys.

    Returns expanded info including tick duration, processed radars count,
    events upserted, MRMS age, and Redis reachability.
    """
    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(redis_url, decode_responses=True, socket_timeout=3)

        # Verify Redis is reachable
        r.ping()

        last_tick_utc = r.get('radar:last_tick_utc')
        last_tick_status = r.get('radar:last_tick_status')
        last_tick_error = r.get('radar:last_tick_error')
        error_count = r.get('radar:error_count_10m')
        mrms_source_time = r.get('mrms:source_time')

        # Extended keys (written by instrumented radar_tick)
        last_tick_duration = r.get('radar:last_tick_duration')
        last_tick_radars = r.get('radar:last_tick_radars_processed')
        last_tick_events = r.get('radar:last_tick_events_upserted')

        # Tick age
        tick_age_seconds = None
        if last_tick_utc:
            try:
                last_dt = datetime.fromisoformat(last_tick_utc.replace('Z', '+00:00'))
                tick_age_seconds = round(
                    (datetime.now(timezone.utc) - last_dt).total_seconds(), 1
                )
            except (ValueError, TypeError):
                pass

        # MRMS age
        mrms_age_seconds = None
        if mrms_source_time:
            try:
                mrms_dt = datetime.fromisoformat(mrms_source_time.replace('Z', '+00:00'))
                mrms_age_seconds = round(
                    (datetime.now(timezone.utc) - mrms_dt).total_seconds(), 1
                )
            except (ValueError, TypeError):
                pass

        # ok = tick fresh AND status ok
        fresh = tick_age_seconds is not None and tick_age_seconds < _SLA_OK_TICK_AGE
        pipeline_ok = fresh and (last_tick_status == 'ok')

        result: Dict[str, Any] = {
            'ok': pipeline_ok,
            'last_tick_utc': last_tick_utc,
            'last_tick_status': last_tick_status or 'unknown',
            'tick_age_seconds': tick_age_seconds,
            'fresh': fresh,
            'error_count_10m': int(error_count) if error_count else 0,
            'mrms_source_time': mrms_source_time,
            'mrms_age_seconds': mrms_age_seconds,
            'redis_reachable': True,
        }

        if last_tick_duration:
            result['last_tick_duration_seconds'] = float(last_tick_duration)
        if last_tick_radars:
            result['last_tick_radars_processed'] = int(last_tick_radars)
        if last_tick_events:
            result['last_tick_events_upserted'] = int(last_tick_events)
        if last_tick_error:
            result['last_tick_error'] = last_tick_error

        return result

    except Exception as e:
        return {
            'ok': False,
            'redis_reachable': False,
            'error': f'Redis unavailable: {e}',
        }


def check_redis(redis_url: str = 'redis://localhost:6379/0') -> Dict[str, Any]:
    """Simple Redis reachability check."""
    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(redis_url, decode_responses=True, socket_timeout=3)
        r.ping()
        info = r.info('memory')
        return {
            'ok': True,
            'used_memory_human': info.get('used_memory_human', 'unknown'),
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def check_database() -> Dict[str, Any]:
    """Database connectivity, PostGIS verification, schema version."""
    try:
        from src.db.engine import get_connection, get_engine_info, get_schema_version
        info = get_engine_info()
        backend = info.get('backend', 'unknown')

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT 1')

            result: Dict[str, Any] = {'ok': True, 'backend': backend}

            if backend == 'postgresql':
                # Verify PostGIS extension is installed
                cur.execute(
                    "SELECT extversion FROM pg_extension WHERE extname = 'postgis'"
                )
                row = cur.fetchone()
                if row:
                    ver = row[0] if not isinstance(row, dict) else row.get('extversion')
                    result['postgis_version'] = ver
                else:
                    result['postgis_version'] = None
                    result['warning'] = 'PostGIS extension not installed'

                # Schema migration version
                schema_ver = get_schema_version()
                result['schema_version'] = schema_ver

                # Table existence spot-check
                cur.execute("""
                    SELECT COUNT(*) as cnt FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name IN ('hail_events', 'fleet_locations', 'deals')
                """)
                tbl_row = cur.fetchone()
                tbl_count = tbl_row[0] if not isinstance(tbl_row, dict) else tbl_row.get('cnt', 0)
                result['core_tables_found'] = tbl_count

            return result
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def register_radar_pipeline_check(redis_url: str = 'redis://localhost:6379/0') -> None:
    """Register the radar pipeline health check with the HealthCheck singleton."""
    hc = get_health_check()
    hc.register('radar_pipeline', lambda: check_radar_pipeline(redis_url))


def register_all_checks(redis_url: str = 'redis://localhost:6379/0') -> None:
    """
    Register all production health checks: database, Redis, radar pipeline.

    Call once at app startup.
    """
    hc = get_health_check()
    hc.register('database', check_database)
    hc.register('redis', lambda: check_redis(redis_url))
    hc.register('radar_pipeline', lambda: check_radar_pipeline(redis_url))
