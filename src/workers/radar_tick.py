"""
Celery periodic task: radar pipeline tick.

Runs the full StormMonitor detection pipeline every 120s, backed by
Redis state persistence so the pipeline survives restarts and scales
independently of Flask.

Phase-1 hardened:
    * Token-based distributed lock with background renewal
    * ZSET for processed_scans with 24h prune + 5000-entry cap
    * MRMS grids on disk, Redis metadata only
    * Alert dedupe key independent of processed_scans
    * All DB writes are idempotent (UPSERT)

Redis keys:
    radar:tick:lock              STRING uuid token, NX, EX 300s
    radar:state:hot_radars       HASH {radar_id: epoch}, TTL 7200s
    radar:state:next_due         HASH {radar_id: epoch}, TTL 7200s
    radar:state:processed_scans  ZSET {scan_key: epoch}, pruned per tick
    radar:state:swath_cache      HASH {event_id: epoch}, TTL 7200s
    radar:last_tick_utc          STRING ISO, TTL 600s
    radar:last_tick_status       STRING 'ok'|'error', TTL 600s
    radar:last_tick_error        STRING, TTL 600s
    radar:error_count_10m        STRING int, TTL 600s
    radar:alert_sent:{scan_key}  STRING '1', TTL 86400s
"""

import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import redis as redis_lib
from celery import shared_task

from src.workers.radar_shared import (
    check_alert_dedupe,
    mark_alert_sent,
    prune_mrms_archive,
    prune_radar_raw_data,
    process_radar_batch,
    run_post_processing,
)
from src.observability.metrics import (
    TICK_TOTAL, TICK_DURATION, TICK_LAST_SUCCESS,
    RADARS_PROCESSED, MRMS_UPDATE, refresh_mrms_age_gauge,
    MRMS_FETCH_DURATION, MRMS_FETCH_RESULT,
)
from src.observability.log_context import (
    set_log_context, clear_log_context, new_trace_id, install_context_filter,
)

logger = logging.getLogger(__name__)

# Install context filter once at module load (idempotent)
install_context_filter()

# ---------------------------------------------------------------------------
# Redis key constants
# ---------------------------------------------------------------------------
_LOCK_KEY = 'radar:tick:lock'
_LOCK_TTL = 300          # seconds
_LOCK_RENEW_INTERVAL = 30  # seconds

_HOT_RADARS_KEY = 'radar:state:hot_radars'
_NEXT_DUE_KEY = 'radar:state:next_due'
_PROCESSED_SCANS_KEY = 'radar:state:processed_scans'
_SWATH_CACHE_KEY = 'radar:state:swath_cache'

_STATE_TTL_HOT = 7200      # 2 hours
_STATE_TTL_SWATH = 7200    # 2 hours
_SCANS_MAX_AGE = 86400     # 24 hours
_SCANS_CAP = 5000

_TICK_UTC_KEY = 'radar:last_tick_utc'
_TICK_STATUS_KEY = 'radar:last_tick_status'
_TICK_ERROR_KEY = 'radar:last_tick_error'
_ERROR_COUNT_KEY = 'radar:error_count_10m'
_HEALTH_TTL = 600

# MRMS fetch budget: hard ceiling so MRMS cannot starve radar processing.
# Must leave headroom for radar batch + post-processing within soft_time_limit.
_MRMS_FETCH_TIMEOUT = int(os.environ.get('MRMS_FETCH_TIMEOUT', '20'))

# ---------------------------------------------------------------------------
# MRMS in-flight guard: process-global lock prevents orphan thread pileup.
#
# The lock is acquired (non-blocking) by the tick BEFORE submitting the
# fetch, and released by the worker thread AFTER fetch completes.  If a
# prior fetch is still running (orphan from a timed-out tick), the next
# tick sees the lock held and skips MRMS entirely.
# ---------------------------------------------------------------------------
_mrms_inflight_lock = threading.Lock()


def _guarded_mrms_fetch(updater) -> str:
    """Run updater.fetch_once() under the inflight lock.

    Returns one of: 'ok_data', 'ok_empty', 'synthetic', 'error'.
    The lock is already acquired by the caller; this function is
    responsible for releasing it when the fetch completes (success,
    failure, or exception).
    """
    try:
        return updater.fetch_once()
    finally:
        try:
            _mrms_inflight_lock.release()
        except RuntimeError:
            pass  # already released (shouldn't happen)

# Lua: compare-and-delete (only owner can release)
_LUA_RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""

# Lua: compare-and-extend TTL (only owner can renew)
_LUA_EXTEND = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('pexpire', KEYS[1], ARGV[2])
else
    return 0
end
"""


# ---------------------------------------------------------------------------
# Token-based distributed lock with background renewal
# ---------------------------------------------------------------------------

class _LockRenewer:
    """
    Daemon thread that renews a Redis lock every ``interval`` seconds.

    Renewal uses a Lua compare-and-extend script: only the holder of
    the matching token can extend the TTL.  If the lock is lost (stolen
    or expired), the renewer stops silently.
    """

    def __init__(self, r: redis_lib.Redis, key: str, token: str,
                 ttl: int, interval: int = _LOCK_RENEW_INTERVAL):
        self._r = r
        self._key = key
        self._token = token
        self._ttl_ms = ttl * 1000
        self._interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(
            target=self._run, daemon=True, name='lock-renewer',
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        while not self._stop.wait(self._interval):
            try:
                ok = self._r.eval(_LUA_EXTEND, 1,
                                  self._key, self._token, str(self._ttl_ms))
                if not ok:
                    logger.warning("Lock renewal failed — lock lost")
                    break
            except Exception as e:
                logger.warning("Lock renewal error: %s", e)


def _acquire_lock(r: redis_lib.Redis) -> Tuple[Optional[str], Optional[_LockRenewer]]:
    """
    Try to acquire the distributed lock.

    Returns (token, renewer) on success, (None, None) on failure.
    The caller MUST call ``_release_lock`` in a finally block.
    """
    token = uuid.uuid4().hex
    acquired = r.set(_LOCK_KEY, token, nx=True, ex=_LOCK_TTL)
    if not acquired:
        return None, None

    renewer = _LockRenewer(r, _LOCK_KEY, token, _LOCK_TTL)
    renewer.start()
    return token, renewer


def _release_lock(r: redis_lib.Redis, token: Optional[str],
                  renewer: Optional[_LockRenewer]) -> None:
    """Release the distributed lock (compare-and-delete via Lua)."""
    if renewer:
        renewer.stop()
    if token:
        try:
            r.eval(_LUA_RELEASE, 1, _LOCK_KEY, token)
        except Exception:
            pass  # lock will expire via TTL


# ---------------------------------------------------------------------------
# Processed-scans helpers (ZSET, score = epoch seconds)
# ---------------------------------------------------------------------------

def was_processed(r: redis_lib.Redis, scan_key: str) -> bool:
    """Check whether a scan key has already been processed."""
    return r.zscore(_PROCESSED_SCANS_KEY, scan_key) is not None


def mark_processed(r: redis_lib.Redis, scan_key: str) -> None:
    """Mark a scan key as processed (add to ZSET with current epoch)."""
    r.zadd(_PROCESSED_SCANS_KEY, {scan_key: time.time()})


def _prune_processed_scans(r: redis_lib.Redis) -> None:
    """
    Prune the processed-scans ZSET:
      1. Remove entries older than 24h  (ZREMRANGEBYSCORE)
      2. Cap to 5000 newest entries     (ZREMRANGEBYRANK)
    """
    cutoff = time.time() - _SCANS_MAX_AGE
    r.zremrangebyscore(_PROCESSED_SCANS_KEY, '-inf', cutoff)

    total = r.zcard(_PROCESSED_SCANS_KEY)
    if total > _SCANS_CAP:
        r.zremrangebyrank(_PROCESSED_SCANS_KEY, 0, total - _SCANS_CAP - 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_redis() -> redis_lib.Redis:
    """Get a Redis client from REDIS_URL or CELERY_BROKER_URL."""
    url = os.environ.get(
        'REDIS_URL',
        os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    )
    return redis_lib.Redis.from_url(url, decode_responses=True)


def _load_state(r: redis_lib.Redis, monitor) -> None:
    """Load scheduler state from Redis into the StormMonitor instance."""
    hot = r.hgetall(_HOT_RADARS_KEY)
    monitor._hot_radars = {k: float(v) for k, v in hot.items()} if hot else {}

    due = r.hgetall(_NEXT_DUE_KEY)
    monitor._next_due = {k: float(v) for k, v in due.items()} if due else {}

    members = r.zrange(_PROCESSED_SCANS_KEY, 0, -1)
    monitor.processed_scans = set(members) if members else set()

    sc = r.hgetall(_SWATH_CACHE_KEY)
    monitor._swath_cache = {k: float(v) for k, v in sc.items()} if sc else {}


def _save_state(r: redis_lib.Redis, monitor) -> None:
    """Save scheduler state from StormMonitor back to Redis."""
    pipe = r.pipeline()

    pipe.delete(_HOT_RADARS_KEY)
    if monitor._hot_radars:
        pipe.hset(_HOT_RADARS_KEY, mapping={
            k: str(v) for k, v in monitor._hot_radars.items()
        })
    pipe.expire(_HOT_RADARS_KEY, _STATE_TTL_HOT)

    pipe.delete(_NEXT_DUE_KEY)
    if monitor._next_due:
        pipe.hset(_NEXT_DUE_KEY, mapping={
            k: str(v) for k, v in monitor._next_due.items()
        })
    pipe.expire(_NEXT_DUE_KEY, _STATE_TTL_HOT)

    now = time.time()
    new_scans = monitor.processed_scans
    if new_scans:
        mapping = {k: now for k in new_scans}
        pipe.zadd(_PROCESSED_SCANS_KEY, mapping, nx=True)

    pipe.delete(_SWATH_CACHE_KEY)
    if monitor._swath_cache:
        pipe.hset(_SWATH_CACHE_KEY, mapping={
            k: str(v) for k, v in monitor._swath_cache.items()
        })
    pipe.expire(_SWATH_CACHE_KEY, _STATE_TTL_SWATH)

    pipe.execute()

    _prune_processed_scans(r)


def _update_health(r: redis_lib.Redis, status: str, error: str = '') -> None:
    """Write health keys to Redis."""
    now_iso = datetime.now(timezone.utc).isoformat()
    pipe = r.pipeline()
    pipe.set(_TICK_UTC_KEY, now_iso, ex=_HEALTH_TTL)
    pipe.set(_TICK_STATUS_KEY, status, ex=_HEALTH_TTL)
    if error:
        pipe.set(_TICK_ERROR_KEY, error, ex=_HEALTH_TTL)
        pipe.incr(_ERROR_COUNT_KEY)
        pipe.expire(_ERROR_COUNT_KEY, _HEALTH_TTL)
    else:
        pipe.delete(_TICK_ERROR_KEY)
    pipe.execute()


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@shared_task(
    name='src.workers.radar_tick.radar_tick',
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(redis_lib.ConnectionError, redis_lib.TimeoutError),
    retry_backoff=True,
    retry_backoff_max=120,
    acks_late=True,
    time_limit=280,
    soft_time_limit=260,
)
def radar_tick(self):
    """
    Run one tick of the radar detection pipeline.

    Acquires a token-based distributed lock with background renewal,
    loads state from Redis, runs StormMonitor scheduling + radar checks,
    then saves state back.
    """
    trace_id = new_trace_id()
    set_log_context(trace_id=trace_id, tick_id=trace_id)

    r = _get_redis()

    token, renewer = _acquire_lock(r)
    if token is None:
        TICK_TOTAL.labels(status='skipped_lock').inc()
        logger.info("radar_tick: lock not acquired, another tick is running")
        clear_log_context()
        return {'skipped': True, 'reason': 'lock_held'}

    try:
        result = _run_tick(r)
        return result
    except Exception as exc:
        TICK_TOTAL.labels(status='error').inc()
        _update_health(r, 'error', str(exc))
        logger.exception("radar_tick failed: %s", exc)
        raise
    finally:
        _release_lock(r, token, renewer)
        clear_log_context()


def _run_tick(r: redis_lib.Redis) -> dict:
    """Core tick logic, called while holding the distributed lock."""
    from src.alerts.storm_monitor import StormMonitor, MonitorConfig
    from src.alerts.monitor_defaults import national_monitor_defaults

    tick_start = time.time()

    # --- Build monitor with national defaults ---
    defaults = national_monitor_defaults()
    config = MonitorConfig(**defaults)
    config.enable_console = False
    config.enable_sound = False
    config.enable_file_log = False
    monitor = StormMonitor(config)

    # --- Wire alert dedupe callbacks ---
    monitor._alert_dedupe_check = lambda key: check_alert_dedupe(r, key)
    monitor._alert_dedupe_mark = lambda key: mark_alert_sent(r, key)

    # --- Load state from Redis ---
    try:
        _load_state(r, monitor)
    except Exception as e:
        logger.warning("State load failed, starting fresh: %s", e)

    # --- MRMS refresh (optional, with in-flight guard + hard timeout) ---
    mrms_refreshed = False
    mrms_status = None  # tracks outcome for metrics
    if os.environ.get('ENABLE_MRMS', '').lower() in ('true', '1', 'yes'):
        # Try to acquire the in-flight lock (non-blocking).
        # If a prior orphan fetch is still running, skip entirely.
        if not _mrms_inflight_lock.acquire(blocking=False):
            logger.warning("MRMS fetch skipped: prior fetch still in-flight")
            mrms_status = 'skipped_inflight'
            MRMS_FETCH_RESULT.labels(status='skipped_inflight').inc()
        else:
            # Lock acquired — we own it.  Ownership transfers to the
            # worker thread at pool.submit(); after that point ONLY the
            # thread's finally block in _guarded_mrms_fetch may release.
            mrms_t0 = time.time()
            _thread_owns_lock = False
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
                from src.radar.mrms.redis_cache import get_mrms_cache
                from src.radar.mrms.updater import MRMSUpdater

                redis_url = os.environ.get(
                    'REDIS_URL',
                    os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
                )
                mrms_cache = get_mrms_cache(redis_url)
                updater = MRMSUpdater(cache=mrms_cache)

                # Submit guarded fetch — lock ownership transfers to thread.
                pool = ThreadPoolExecutor(max_workers=1)
                fut = pool.submit(_guarded_mrms_fetch, updater)
                _thread_owns_lock = True  # thread will release in its finally

                try:
                    mrms_result = fut.result(timeout=_MRMS_FETCH_TIMEOUT)
                    mrms_status = mrms_result  # 'ok_data' | 'ok_empty' | 'synthetic' | 'error'
                except FuturesTimeout:
                    logger.warning(
                        "MRMS fetch exceeded %ds budget; orphan thread will "
                        "release lock when done", _MRMS_FETCH_TIMEOUT,
                    )
                    fut.cancel()
                    mrms_status = 'timeout'
                finally:
                    pool.shutdown(wait=False)

                monitor._mrms_cache = mrms_cache
            except Exception as e:
                logger.warning("MRMS refresh failed: %s", e)
                mrms_status = 'error'
                if not _thread_owns_lock:
                    # Setup failed before pool.submit — thread never
                    # started, so we must release the lock ourselves.
                    try:
                        _mrms_inflight_lock.release()
                    except RuntimeError:
                        pass

            mrms_elapsed = time.time() - mrms_t0
            MRMS_FETCH_DURATION.observe(mrms_elapsed)
            MRMS_FETCH_RESULT.labels(status=mrms_status or 'error').inc()
            # Legacy metric compat: any non-error is "ok"
            mrms_refreshed = mrms_status in ('ok_data', 'synthetic')
            MRMS_UPDATE.labels(
                status='ok' if mrms_status in ('ok_data', 'ok_empty', 'synthetic') else 'error',
            ).inc()
            logger.info(
                "MRMS fetch: status=%s elapsed=%.1fs",
                mrms_status, mrms_elapsed,
            )

    # --- Run one scheduler tick ---
    now_ts = time.time()
    discovery_radars, focus_radars = monitor._schedule_tick(now_ts)
    scheduled = focus_radars + discovery_radars

    if not scheduled:
        logger.info("radar_tick: no radars due this tick")
        _save_state(r, monitor)
        _update_health(r, 'ok')
        return {
            'skipped': False,
            'discovery': 0,
            'focus': 0,
            'processed': 0,
            'wall_seconds': round(time.time() - tick_start, 1),
        }

    # --- Process radars (shared helper) ---
    tick_wall_seconds = min(
        float(config.per_radar_timeout_seconds) * 3.0,
        float(os.environ.get('STORM_TICK_WALL_SECONDS', '240')),
    )
    tick_deadline = tick_start + tick_wall_seconds

    processed, ok_count, err_count = process_radar_batch(
        monitor, scheduled, config, deadline=tick_deadline,
    )

    # --- Post-processing (shared helper) ---
    run_post_processing(monitor)

    # --- Save state back to Redis ---
    _save_state(r, monitor)

    # --- MRMS archive pruning (Phase-1 red-team fix A) ---
    try:
        prune_mrms_archive()
    except Exception as e:
        logger.debug("MRMS prune: %s", e)

    # --- Radar raw data pruning ---
    try:
        prune_radar_raw_data()
    except Exception as e:
        logger.debug("Radar raw prune: %s", e)

    wall_seconds = round(time.time() - tick_start, 1)
    _update_health(r, 'ok')

    # --- Prometheus metrics ---
    TICK_TOTAL.labels(status='ok').inc()
    TICK_DURATION.observe(wall_seconds)
    TICK_LAST_SUCCESS.set(time.time())
    RADARS_PROCESSED.labels(result='ok').inc(ok_count)
    RADARS_PROCESSED.labels(result='error').inc(err_count)
    refresh_mrms_age_gauge(r)

    # --- Extended health keys for /api/system/ready ---
    try:
        pipe = r.pipeline()
        pipe.set('radar:last_tick_duration', str(wall_seconds), ex=_HEALTH_TTL)
        pipe.set('radar:last_tick_radars_processed', str(processed), ex=_HEALTH_TTL)
        pipe.execute()
    except Exception:
        pass

    result = {
        'skipped': False,
        'discovery': len(discovery_radars),
        'focus': len(focus_radars),
        'processed': processed,
        'ok': ok_count,
        'errors': err_count,
        'hot_radars': len(monitor._hot_radars),
        'mrms_refreshed': mrms_refreshed,
        'wall_seconds': wall_seconds,
    }

    logger.info(
        "radar_tick completed: discovery=%d focus=%d processed=%d ok=%d err=%d wall=%.1fs",
        len(discovery_radars), len(focus_radars), processed, ok_count, err_count, wall_seconds,
    )

    return result
