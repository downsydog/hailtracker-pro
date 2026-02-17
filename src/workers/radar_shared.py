"""
Shared helpers for radar pipeline (live tick + backfill).

Centralizes:
    * scan_key generation
    * alert dedupe (Redis-backed, independent of processed_scans)
    * MRMS archive pruning
    * radar batch processing (thread pool)
    * post-processing (swaths, persistence, intelligence engine)
"""

import glob
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Alert dedupe constants
# ---------------------------------------------------------------------------
_ALERT_DEDUPE_PREFIX = 'radar:alert_sent:'
_ALERT_DEDUPE_TTL = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Canonical scan key
# ---------------------------------------------------------------------------

def make_scan_key(radar_id: str, filename: str) -> str:
    """
    Build the canonical scan-key used across live tick, backfill,
    and the processed_scans ZSET.

    Format:  ``{RADAR_ID}_{filename}``

    Must stay in sync with StormMonitor._check_radar() usage.
    """
    return f"{radar_id}_{filename}"


# ---------------------------------------------------------------------------
# Alert dedupe (independent of processed_scans ZSET)
# ---------------------------------------------------------------------------

def check_alert_dedupe(r, scan_key: str) -> bool:
    """Return True if an alert was already dispatched for this scan_key."""
    return r.exists(f'{_ALERT_DEDUPE_PREFIX}{scan_key}') > 0


def mark_alert_sent(r, scan_key: str) -> None:
    """Record that an alert was dispatched for this scan_key (24h TTL)."""
    r.set(f'{_ALERT_DEDUPE_PREFIX}{scan_key}', '1', ex=_ALERT_DEDUPE_TTL)


# ---------------------------------------------------------------------------
# MRMS archive pruning
# ---------------------------------------------------------------------------

def prune_mrms_archive(mrms_dir: str = 'data/mrms',
                       max_age_hours: Optional[int] = None) -> int:
    """
    Delete timestamped ``*.npz`` files older than *max_age_hours*.

    Skips ``latest.npz`` (the active symlink).
    Returns the number of files deleted.

    Default max age is read from ``MRMS_ARCHIVE_MAX_HOURS`` (default 24).
    """
    if max_age_hours is None:
        max_age_hours = int(os.environ.get('MRMS_ARCHIVE_MAX_HOURS', '24'))

    if not os.path.isdir(mrms_dir):
        return 0

    cutoff = time.time() - (max_age_hours * 3600)
    deleted = 0

    for path in glob.glob(os.path.join(mrms_dir, '*.npz')):
        basename = os.path.basename(path)
        if basename == 'latest.npz':
            continue
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                deleted += 1
        except Exception as e:
            logger.debug("Failed to prune %s: %s", path, e)

    if deleted:
        logger.info("Pruned %d MRMS archive files older than %dh", deleted, max_age_hours)

    return deleted


# ---------------------------------------------------------------------------
# Radar raw data pruning
# ---------------------------------------------------------------------------

def prune_radar_raw_data(data_dir: str = 'data/radar_raw',
                         max_age_hours: Optional[int] = None) -> int:
    """
    Delete raw radar scan files older than *max_age_hours*.

    Scans older files in ``data_dir`` and removes them.
    Default max age is read from ``RADAR_RAW_RETENTION_HOURS`` (default 24).
    Returns the number of files deleted.
    """
    if max_age_hours is None:
        max_age_hours = int(os.environ.get('RADAR_RAW_RETENTION_HOURS', '24'))

    if not os.path.isdir(data_dir):
        return 0

    cutoff = time.time() - (max_age_hours * 3600)
    deleted = 0

    for root, _dirs, files in os.walk(data_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    deleted += 1
            except Exception as e:
                logger.debug("Failed to prune %s: %s", fpath, e)

    if deleted:
        logger.info("Pruned %d raw radar files older than %dh", deleted, max_age_hours)

    return deleted


# ---------------------------------------------------------------------------
# Shared radar batch processing
# ---------------------------------------------------------------------------

def process_radar_batch(
    monitor,
    radars: List[str],
    config,
    deadline: Optional[float] = None,
) -> Tuple[int, int, int]:
    """
    Process a list of radars using a thread pool.

    Returns ``(processed, ok_count, err_count)``.
    Handles hot-radar promotion and next_due updates.
    """
    max_workers = int(config.max_workers)
    processed = 0
    ok_count = 0
    err_count = 0

    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        futures: Dict = {}
        for rid in radars:
            futures[executor.submit(monitor._check_radar_with_result, rid)] = rid

        try:
            timeout = max(1, deadline - time.time()) if deadline else None
            for fut in as_completed(futures, timeout=timeout):
                rid = futures[fut]
                processed += 1

                try:
                    res = fut.result(timeout=0)
                except Exception:
                    err_count += 1
                    monitor._update_next_due(rid, time.time(), monitor._is_hot(rid))
                    continue

                result_ts = time.time()

                if not res.get('ok'):
                    err_count += 1
                    monitor._update_next_due(rid, result_ts, monitor._is_hot(rid))
                    continue

                ok_count += 1

                # Promote to HOT based on evidence
                max_ref = res.get('max_reflectivity')
                hail_peak = res.get('hail_score_peak')

                if (max_ref is not None and float(max_ref) >= float(config.hot_promote_dbz)) or \
                   (hail_peak is not None and float(hail_peak) >= float(config.hot_promote_hail_score)):
                    monitor._mark_radar_hot(rid, result_ts)

                monitor._update_next_due(rid, result_ts, monitor._is_hot(rid))

                if deadline and time.time() >= deadline:
                    break
        except TimeoutError:
            pass
        finally:
            for f in futures:
                if not f.done():
                    f.cancel()
    finally:
        executor.shutdown(wait=False)

    try:
        from src.observability.metrics import RADAR_CHECKS_OK
        RADAR_CHECKS_OK.inc(ok_count)
    except Exception:
        pass

    return processed, ok_count, err_count


# ---------------------------------------------------------------------------
# Shared post-processing
# ---------------------------------------------------------------------------

def run_post_processing(monitor) -> None:
    """
    Run swath generation, event persistence, and intelligence-engine
    swath roll-up.  All DB writes are idempotent (UPSERT).
    """
    try:
        monitor._auto_generate_swaths()
    except Exception as e:
        logger.warning("auto_generate_swaths failed: %s", e)

    try:
        monitor._persist_tracker_events()
        from src.observability.metrics import EVENT_PERSIST_BATCHES
        EVENT_PERSIST_BATCHES.inc()
    except Exception as e:
        logger.warning("persist_tracker_events failed: %s", e)

    try:
        from src.swath.intelligence_engine import update_swaths
        from src.observability.metrics import SWATH_PERSIST_BATCHES, SWATH_BUILD_DURATION
        swath_t0 = time.time()
        upserted = update_swaths()
        swath_elapsed = time.time() - swath_t0
        SWATH_BUILD_DURATION.observe(swath_elapsed)
        SWATH_PERSIST_BATCHES.inc()
        if upserted:
            logger.info("update_swaths: upserted=%d elapsed=%.2fs", upserted, swath_elapsed)
    except Exception as e:
        logger.warning("update_swaths failed: %s", e)
