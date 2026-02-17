"""
Celery task: radar backfill / gap repair.

Replays a historical time range through the same detection pipeline
used by radar_tick, allowing missed storms to be recovered.

Design:
    * Steps through [start_utc, end_utc) in ``step_seconds`` increments.
    * For each window, sets StormMonitor._override_end_time and runs
      _check_radar for every radar in the region (or all radars).
    * Scans already in the processed_scans ZSET are skipped automatically.
    * DB writes are UPSERT-safe — safe to re-run the same range.
    * Alerts are suppressed by default (allow_alerts=False).

Redis checkpoint keys (per job):
    radar:backfill:checkpoint:{job_id}   STRING  current_time ISO
    radar:backfill:status:{job_id}       STRING  running|done|error
    radar:backfill:meta:{job_id}         HASH    start/end/region/step
    radar:backfill:windows:{job_id}      STRING  int count processed
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis as redis_lib
from celery import shared_task

from src.workers.radar_shared import (
    check_alert_dedupe,
    mark_alert_sent,
    process_radar_batch,
    run_post_processing,
)
from src.observability.metrics import BACKFILL_WINDOWS, RADARS_PROCESSED
from src.observability.log_context import (
    set_log_context, clear_log_context, new_trace_id, install_context_filter,
)

logger = logging.getLogger(__name__)

install_context_filter()

# Redis key templates
_CK_PREFIX = 'radar:backfill:checkpoint:'
_ST_PREFIX = 'radar:backfill:status:'
_META_PREFIX = 'radar:backfill:meta:'
_WIN_PREFIX = 'radar:backfill:windows:'

# Checkpoint TTL: 7 days (so stale jobs eventually clean up)
_CHECKPOINT_TTL = 7 * 86400

# Defaults (env-overridable)
_DEFAULT_MAX_RUNTIME = 3600     # 1 hour
_DEFAULT_MAX_WINDOWS = 1800     # 1800 * 2min = 60 hours of history

# Processed scans ZSET (shared with radar_tick)
_PROCESSED_SCANS_KEY = 'radar:state:processed_scans'


def _get_redis() -> redis_lib.Redis:
    url = os.environ.get(
        'REDIS_URL',
        os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    )
    return redis_lib.Redis.from_url(url, decode_responses=True)


def _parse_iso(s: str) -> datetime:
    """Parse ISO 8601 string to timezone-aware datetime."""
    s = s.replace('Z', '+00:00')
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@shared_task(
    name='src.workers.radar_backfill.radar_backfill',
    bind=True,
    max_retries=1,
    acks_late=True,
    time_limit=7200,       # 2 hour hard limit
    soft_time_limit=7000,
)
def radar_backfill(
    self,
    start_utc: str,
    end_utc: str,
    region: Optional[str] = None,
    step_seconds: int = 120,
    allow_alerts: bool = False,
    max_runtime_seconds: Optional[int] = None,
    max_windows_per_run: Optional[int] = None,
    job_id: Optional[str] = None,
):
    """
    Replay a time range through the radar detection pipeline.

    Args:
        start_utc: ISO 8601 start time (inclusive).
        end_utc:   ISO 8601 end time (exclusive).
        region:    Optional named region to filter radars (e.g. "texas").
        step_seconds: Window step size in seconds (default 120).
        allow_alerts: If True, allow alert dispatch (with dedupe).
                      If False (default), suppress all alerts.
        max_runtime_seconds: Max wall-clock time for this task invocation.
        max_windows_per_run: Max windows to process before yielding.
        job_id: Resume an existing job.  If None, a new job_id is generated.

    Returns:
        dict with job_id, status, windows_processed, checkpoint.
    """
    r = _get_redis()

    max_runtime = max_runtime_seconds or int(
        os.environ.get('BACKFILL_MAX_RUNTIME', str(_DEFAULT_MAX_RUNTIME)))
    max_windows = max_windows_per_run or int(
        os.environ.get('BACKFILL_MAX_WINDOWS', str(_DEFAULT_MAX_WINDOWS)))

    start_dt = _parse_iso(start_utc)
    end_dt = _parse_iso(end_utc)

    if end_dt <= start_dt:
        return {'error': 'end_utc must be after start_utc'}

    # --- Job ID + checkpoint ---
    if not job_id:
        job_id = uuid.uuid4().hex[:12]

    trace_id = new_trace_id()
    set_log_context(trace_id=trace_id, job_id=job_id)

    ck_key = f'{_CK_PREFIX}{job_id}'
    st_key = f'{_ST_PREFIX}{job_id}'
    meta_key = f'{_META_PREFIX}{job_id}'
    win_key = f'{_WIN_PREFIX}{job_id}'

    # Check for existing checkpoint (resume)
    existing_ck = r.get(ck_key)
    if existing_ck:
        try:
            resume_dt = _parse_iso(existing_ck)
            if resume_dt > start_dt:
                logger.info("Resuming backfill %s from checkpoint %s", job_id, existing_ck)
                start_dt = resume_dt
        except (ValueError, TypeError):
            pass

    # Store job metadata
    r.hset(meta_key, mapping={
        'start_utc': start_utc,
        'end_utc': end_utc,
        'region': region or '',
        'step_seconds': str(step_seconds),
        'allow_alerts': '1' if allow_alerts else '0',
    })
    r.expire(meta_key, _CHECKPOINT_TTL)
    r.set(st_key, 'running', ex=_CHECKPOINT_TTL)

    try:
        result = _run_backfill(
            r, job_id, start_dt, end_dt, region, step_seconds,
            allow_alerts, max_runtime, max_windows,
        )
        return result
    except Exception as exc:
        r.set(st_key, 'error', ex=_CHECKPOINT_TTL)
        logger.exception("Backfill %s failed: %s", job_id, exc)
        raise
    finally:
        clear_log_context()


def _run_backfill(
    r: redis_lib.Redis,
    job_id: str,
    start_dt: datetime,
    end_dt: datetime,
    region: Optional[str],
    step_seconds: int,
    allow_alerts: bool,
    max_runtime: int,
    max_windows: int,
) -> dict:
    """Core backfill loop."""
    from src.alerts.storm_monitor import StormMonitor, MonitorConfig
    from src.alerts.monitor_defaults import national_monitor_defaults

    ck_key = f'{_CK_PREFIX}{job_id}'
    st_key = f'{_ST_PREFIX}{job_id}'
    win_key = f'{_WIN_PREFIX}{job_id}'

    run_start = time.time()

    # --- Build monitor ---
    defaults = national_monitor_defaults()
    config = MonitorConfig(**defaults)
    config.enable_console = False
    config.enable_sound = False
    config.enable_file_log = False
    # Disable discovery/focus — backfill checks all radars per window
    config.enable_discovery_focus = False
    monitor = StormMonitor(config)

    # --- Region filtering ---
    if region:
        try:
            from src.alerts.geo_filter import GeoFilter, get_suggested_radars
            geo_filter = GeoFilter.from_named_region(region)
            suggested = get_suggested_radars(geo_filter)
            if suggested:
                config.radar_ids = suggested
                monitor.config.radar_ids = suggested
                logger.info("Backfill region=%s → %d radars", region, len(suggested))
        except Exception as e:
            logger.warning("Region filter failed, using all radars: %s", e)

    radar_ids = list(monitor.config.radar_ids)

    # --- Alert handling ---
    if not allow_alerts:
        # Suppress all alerts: dedupe check always returns True
        monitor._alert_dedupe_check = lambda _key: True
    else:
        monitor._alert_dedupe_check = lambda key: check_alert_dedupe(r, key)
        monitor._alert_dedupe_mark = lambda key: mark_alert_sent(r, key)

    # --- Load processed_scans from ZSET ---
    members = r.zrange('radar:state:processed_scans', 0, -1)
    monitor.processed_scans = set(members) if members else set()

    # --- Step through windows ---
    current = start_dt
    step = timedelta(seconds=step_seconds)
    windows_processed = 0
    total_ok = 0
    total_err = 0

    while current < end_dt:
        # Budget checks
        elapsed = time.time() - run_start
        if elapsed >= max_runtime:
            logger.info("Backfill %s: max_runtime %ds reached after %d windows",
                        job_id, max_runtime, windows_processed)
            break

        if windows_processed >= max_windows:
            logger.info("Backfill %s: max_windows %d reached", job_id, max_windows)
            break

        # Set time override (naive UTC, matching StormMonitor convention)
        window_end = current + step
        monitor._override_end_time = current.replace(tzinfo=None)

        # Process all radars for this window
        window_deadline = time.time() + float(config.per_radar_timeout_seconds) * 2.0
        processed, ok, err = process_radar_batch(
            monitor, radar_ids, config, deadline=window_deadline,
        )
        total_ok += ok
        total_err += err

        # Merge newly processed scans into ZSET
        if monitor.processed_scans:
            now = time.time()
            new_entries = {k: now for k in monitor.processed_scans}
            r.zadd(_PROCESSED_SCANS_KEY, new_entries, nx=True)

        windows_processed += 1
        BACKFILL_WINDOWS.inc()
        RADARS_PROCESSED.labels(result='ok').inc(ok)
        RADARS_PROCESSED.labels(result='error').inc(err)

        # Update checkpoint
        checkpoint_iso = current.isoformat()
        r.set(ck_key, checkpoint_iso, ex=_CHECKPOINT_TTL)
        r.set(win_key, str(windows_processed), ex=_CHECKPOINT_TTL)

        current = window_end

    # --- Post-processing (once, at the end) ---
    monitor._override_end_time = None
    run_post_processing(monitor)

    # --- Final status ---
    done = current >= end_dt
    status = 'done' if done else 'paused'
    r.set(st_key, status, ex=_CHECKPOINT_TTL)

    wall_seconds = round(time.time() - run_start, 1)

    result = {
        'job_id': job_id,
        'status': status,
        'windows_processed': windows_processed,
        'ok': total_ok,
        'errors': total_err,
        'checkpoint': current.isoformat(),
        'wall_seconds': wall_seconds,
        'region': region,
    }

    logger.info(
        "Backfill %s %s: windows=%d ok=%d err=%d wall=%.1fs checkpoint=%s",
        job_id, status, windows_processed, total_ok, total_err,
        wall_seconds, current.isoformat(),
    )

    return result
