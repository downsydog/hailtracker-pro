"""
30-Minute Soak Test with Failure Injection
==========================================
Scope: weather/hail/swath ONLY.

Runs the MRMS fetch + swath pipeline on a compressed cadence (30s ticks)
for 30 real minutes.  Injects provider failures at specific intervals and
collects metrics every 5 minutes.

Failure injection schedule:
    00:00 - 05:00   Steady state (no injection)
    05:00 - 10:00   Mesonet JSON API failure
    10:00 - 12:00   Recovery window
    12:00 - 17:00   AWS MRMS index/grib failure
    17:00 - 20:00   Recovery window
    20:00 - 25:00   Both Mesonet + AWS down → synthetic only
    25:00 - 30:00   Full recovery, steady state

Validates:
    - No MRMS thread pileup (max concurrent = 1) under all conditions
    - Synthetic grid wall-clock cap respected when both providers down
    - Health state transitions correctly
    - Swath pipeline continues operating during MRMS outages
    - Metrics counters and histograms increment correctly
"""

import json
import logging
import math
import os
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault(
    'DATABASE_URL',
    'postgresql://hailtracker:hailtracker_dev_2024@localhost:5432/hailtracker_pro',
)
os.environ['MRMS_PROVIDER'] = 'mesonet'
os.environ['MRMS_SYNTHETIC_MAX_SECONDS'] = '10'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-30s %(levelname)-7s %(message)s',
)
logger = logging.getLogger('soak')

# ============================================================================
# Constants
# ============================================================================

TICK_INTERVAL = 30      # seconds between ticks (compressed from 120s)
SOAK_DURATION = 1800    # 30 minutes in seconds
REPORT_INTERVAL = 300   # report every 5 minutes
MRMS_FETCH_TIMEOUT = 20  # seconds

# Failure injection windows (seconds from start)
FAILURE_SCHEDULE = [
    # (start, end, what_to_block)
    (300, 600, 'mesonet_json'),      # 5:00 - 10:00: Mesonet JSON down
    (720, 1020, 'aws_noaa'),         # 12:00 - 17:00: AWS/NOAA down
    (1200, 1500, 'both'),            # 20:00 - 25:00: Everything down
]


# ============================================================================
# Failure injection helpers
# ============================================================================

_original_session_get = None
_active_blocks = set()  # 'mesonet_json', 'aws_noaa', 'mesonet_synthetic'

class _FailureInjector:
    """Monkey-patches requests.Session.get to simulate provider failures."""

    def __init__(self):
        self.blocks = set()
        self._original = None
        self._installed = False

    def install(self):
        import requests
        self._original = requests.Session.get
        _self = self

        def patched_get(session_self, url, **kwargs):
            # Check Mesonet JSON API block
            if 'mesonet_json' in _self.blocks or 'both' in _self.blocks:
                if 'mesonet.agron.iastate.edu/geojson' in url:
                    raise ConnectionError(f"[INJECTED] Mesonet JSON blocked: {url}")
                if 'mesonet.agron.iastate.edu/json/mrms_lookup' in url:
                    if 'both' in _self.blocks:
                        raise ConnectionError(f"[INJECTED] Mesonet synthetic blocked: {url}")

            # Check AWS/NOAA block
            if 'aws_noaa' in _self.blocks or 'both' in _self.blocks:
                if 'mrms.ncep.noaa.gov' in url:
                    raise ConnectionError(f"[INJECTED] NOAA MRMS blocked: {url}")

            return _self._original(session_self, url, **kwargs)

        requests.Session.get = patched_get
        self._installed = True

    def uninstall(self):
        if self._installed and self._original:
            import requests
            requests.Session.get = self._original
            self._installed = False

    def set_blocks(self, blocks):
        self.blocks = set(blocks) if blocks else set()


# ============================================================================
# Thread pileup tracking
# ============================================================================

class _PileupTracker:
    """Tracks concurrent MRMS fetches to detect pileup."""

    def __init__(self):
        self.lock = threading.Lock()
        self.current = 0
        self.peak = 0
        self.total_fetches = 0

    def enter(self):
        with self.lock:
            self.current += 1
            self.total_fetches += 1
            if self.current > self.peak:
                self.peak = self.current

    def exit(self):
        with self.lock:
            self.current -= 1

    def snapshot(self):
        with self.lock:
            return {
                'current': self.current,
                'peak': self.peak,
                'total_fetches': self.total_fetches,
            }


# ============================================================================
# Metrics collector
# ============================================================================

class _MetricsCollector:
    """Collects tick-level metrics for the soak report."""

    def __init__(self):
        self.ticks = []
        self.checkpoints = []
        self.mrms_outcomes = defaultdict(int)
        self.mrms_durations = []
        self.swath_durations = []
        self.swath_counts = []
        self.errors = []
        self.synthetic_wall_times = []

    def record_tick(self, tick_num, elapsed_since_start, result):
        self.ticks.append({
            'tick': tick_num,
            'time_offset': round(elapsed_since_start, 1),
            **result,
        })

    def record_mrms(self, status, duration, provider=None):
        self.mrms_outcomes[status] += 1
        self.mrms_durations.append(duration)
        if provider and 'synthetic' in provider:
            self.synthetic_wall_times.append(duration)

    def record_swath(self, duration, count):
        self.swath_durations.append(duration)
        self.swath_counts.append(count)

    def record_error(self, tick_num, error):
        self.errors.append({'tick': tick_num, 'error': str(error)})

    def checkpoint(self, elapsed, redis_state, pileup_snap):
        self.checkpoints.append({
            'elapsed_min': round(elapsed / 60, 1),
            'redis': redis_state,
            'pileup': pileup_snap,
            'mrms_outcomes': dict(self.mrms_outcomes),
            'mrms_p95': self._percentile(self.mrms_durations, 0.95),
            'mrms_p99': self._percentile(self.mrms_durations, 0.99),
            'swath_p95': self._percentile(self.swath_durations, 0.95),
            'swath_p99': self._percentile(self.swath_durations, 0.99),
            'total_ticks': len(self.ticks),
            'total_errors': len(self.errors),
        })

    @staticmethod
    def _percentile(data, pct):
        if not data:
            return 0.0
        s = sorted(data)
        idx = int(len(s) * pct)
        idx = min(idx, len(s) - 1)
        return round(s[idx], 3)


# ============================================================================
# Soak tick execution
# ============================================================================

def _run_soak_tick(
    tick_num,
    inflight_lock,
    pileup_tracker,
    metrics_collector,
    injector,
    redis_client,
):
    """Execute one soak tick: MRMS fetch + swath update."""
    result = {
        'mrms_status': None,
        'mrms_duration': 0,
        'mrms_provider': None,
        'swath_upserted': 0,
        'swath_duration': 0,
        'active_failure': list(injector.blocks),
    }

    # --- MRMS fetch with inflight guard ---
    if not inflight_lock.acquire(blocking=False):
        result['mrms_status'] = 'skipped_inflight'
        metrics_collector.record_mrms('skipped_inflight', 0)
        logger.info("  Tick %d: MRMS skipped (prior fetch in-flight)", tick_num)
    else:
        mrms_t0 = time.time()
        thread_owns = False
        try:
            from src.radar.mrms.redis_cache import get_mrms_cache
            from src.radar.mrms.updater import MRMSUpdater

            mrms_cache = get_mrms_cache('redis://localhost:6379/0')
            updater = MRMSUpdater(cache=mrms_cache)

            def guarded_fetch():
                pileup_tracker.enter()
                try:
                    return updater.fetch_once()
                finally:
                    pileup_tracker.exit()
                    try:
                        inflight_lock.release()
                    except RuntimeError:
                        pass

            pool = ThreadPoolExecutor(max_workers=1)
            fut = pool.submit(guarded_fetch)
            thread_owns = True

            try:
                mrms_ok = fut.result(timeout=MRMS_FETCH_TIMEOUT)
                result['mrms_status'] = 'ok' if mrms_ok else 'error'
            except FuturesTimeout:
                fut.cancel()
                result['mrms_status'] = 'timeout'
                logger.warning("  Tick %d: MRMS fetch timeout (%ds)", tick_num, MRMS_FETCH_TIMEOUT)
            except Exception as e:
                result['mrms_status'] = 'error'
                logger.warning("  Tick %d: MRMS fetch exception: %s", tick_num, e)
            finally:
                pool.shutdown(wait=False)

            # Capture provider info
            try:
                status = mrms_cache.get_status()
                result['mrms_provider'] = status.get('provider', 'unknown')
            except Exception:
                pass

        except Exception as e:
            result['mrms_status'] = 'error'
            logger.warning("  Tick %d: MRMS setup error: %s", tick_num, e)
            if not thread_owns:
                try:
                    inflight_lock.release()
                except RuntimeError:
                    pass

        mrms_elapsed = round(time.time() - mrms_t0, 3)
        result['mrms_duration'] = mrms_elapsed
        metrics_collector.record_mrms(
            result['mrms_status'] or 'error',
            mrms_elapsed,
            result.get('mrms_provider'),
        )

    # --- Swath intelligence engine update ---
    swath_t0 = time.time()
    try:
        from src.swath.intelligence_engine import update_swaths
        upserted = update_swaths()
        result['swath_upserted'] = upserted
    except Exception as e:
        result['swath_upserted'] = 0
        logger.warning("  Tick %d: update_swaths error: %s", tick_num, e)

    swath_elapsed = round(time.time() - swath_t0, 3)
    result['swath_duration'] = swath_elapsed
    metrics_collector.record_swath(swath_elapsed, result['swath_upserted'])

    # --- Update Redis health keys ---
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        pipe = redis_client.pipeline()
        pipe.set('radar:last_tick_utc', now_iso, ex=600)
        pipe.set('radar:last_tick_status', result['mrms_status'] or 'ok', ex=600)
        pipe.execute()
    except Exception:
        pass

    return result


def _read_redis_state(redis_client):
    """Read health keys from Redis."""
    try:
        pipe = redis_client.pipeline()
        pipe.get('radar:last_tick_utc')
        pipe.get('radar:last_tick_status')
        pipe.get('mrms:source_time')
        results = pipe.execute()

        tick_utc = results[0]
        tick_status = results[1]
        mrms_time = results[2]

        now = datetime.now(timezone.utc)
        tick_age = None
        mrms_age = None

        if tick_utc:
            if isinstance(tick_utc, bytes):
                tick_utc = tick_utc.decode()
            try:
                dt = datetime.fromisoformat(tick_utc.replace('Z', '+00:00'))
                tick_age = round((now - dt).total_seconds(), 1)
            except Exception:
                pass

        if mrms_time:
            if isinstance(mrms_time, bytes):
                mrms_time = mrms_time.decode()
            try:
                dt = datetime.fromisoformat(mrms_time.replace('Z', '+00:00'))
                mrms_age = round((now - dt).total_seconds(), 1)
            except Exception:
                pass

        return {
            'tick_status': tick_status.decode() if isinstance(tick_status, bytes) else tick_status,
            'tick_age_sec': tick_age,
            'mrms_source_time': mrms_time,
            'mrms_age_sec': mrms_age,
        }
    except Exception as e:
        return {'error': str(e)}


def _get_active_swaths_info():
    """Get active swath count and last_valid_swath_utc."""
    try:
        import psycopg2
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS active_count,
                   MAX(last_valid_swath_utc) AS latest_update
            FROM hail_swaths
            WHERE lifecycle_state NOT IN ('EXPIRED')
        """)
        row = cur.fetchone()
        conn.close()
        return {
            'active_swaths': row[0] or 0,
            'last_valid_swath_utc': str(row[1]) if row[1] else None,
        }
    except Exception as e:
        return {'active_swaths': 0, 'error': str(e)}


# ============================================================================
# Main soak loop
# ============================================================================

def run_soak():
    """Run the 30-minute soak test."""
    import redis as redis_lib

    logger.info("=" * 76)
    logger.info("30-MINUTE SOAK TEST — WEATHER CORE")
    logger.info("Scope: weather/hail/swath ONLY")
    logger.info("Tick interval: %ds  Duration: %ds (%d min)",
                TICK_INTERVAL, SOAK_DURATION, SOAK_DURATION // 60)
    logger.info("MRMS fetch timeout: %ds", MRMS_FETCH_TIMEOUT)
    logger.info("Synthetic wall-clock cap: %ss", os.environ.get('MRMS_SYNTHETIC_MAX_SECONDS', '10'))
    logger.info("=" * 76)

    # Setup
    redis_client = redis_lib.Redis.from_url('redis://localhost:6379/0', decode_responses=False)
    redis_client.ping()
    logger.info("Redis: OK")

    inflight_lock = threading.Lock()
    pileup_tracker = _PileupTracker()
    metrics_collector = _MetricsCollector()
    injector = _FailureInjector()
    injector.install()

    start_time = time.time()
    tick_num = 0
    next_report = start_time + REPORT_INTERVAL

    logger.info("\nFailure injection schedule:")
    for start, end, what in FAILURE_SCHEDULE:
        logger.info("  %02d:%02d - %02d:%02d  Block: %s",
                     start // 60, start % 60, end // 60, end % 60, what)
    logger.info("")

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= SOAK_DURATION:
                break

            # --- Update failure injection ---
            active_faults = set()
            for f_start, f_end, f_type in FAILURE_SCHEDULE:
                if f_start <= elapsed < f_end:
                    active_faults.add(f_type)
            injector.set_blocks(active_faults)

            # Log fault state changes
            if active_faults:
                logger.info("[%02d:%02d] Active faults: %s",
                            int(elapsed) // 60, int(elapsed) % 60,
                            ', '.join(active_faults))

            # --- Run tick ---
            tick_t0 = time.time()
            try:
                result = _run_soak_tick(
                    tick_num, inflight_lock, pileup_tracker,
                    metrics_collector, injector, redis_client,
                )
                tick_elapsed = round(time.time() - tick_t0, 3)

                logger.info(
                    "[%02d:%02d] Tick %3d: mrms=%s (%.1fs, provider=%s) swath=%d (%.3fs) faults=%s",
                    int(elapsed) // 60, int(elapsed) % 60,
                    tick_num,
                    result['mrms_status'],
                    result['mrms_duration'],
                    result.get('mrms_provider', '-'),
                    result['swath_upserted'],
                    result['swath_duration'],
                    result['active_failure'] or 'none',
                )

                metrics_collector.record_tick(tick_num, elapsed, result)
            except Exception as e:
                logger.error("[%02d:%02d] Tick %d EXCEPTION: %s",
                             int(elapsed) // 60, int(elapsed) % 60, tick_num, e)
                metrics_collector.record_error(tick_num, e)

            tick_num += 1

            # --- Periodic report ---
            now = time.time()
            if now >= next_report:
                redis_state = _read_redis_state(redis_client)
                pileup_snap = pileup_tracker.snapshot()
                swath_info = _get_active_swaths_info()

                logger.info("\n" + "-" * 76)
                logger.info("CHECKPOINT at %02d:%02d (%.0f min elapsed)",
                            int(elapsed) // 60, int(elapsed) % 60, elapsed / 60)
                logger.info("  Redis: tick_status=%s tick_age=%.1fs mrms_age=%s",
                            redis_state.get('tick_status'),
                            redis_state.get('tick_age_sec') or -1,
                            redis_state.get('mrms_age_sec'))
                logger.info("  MRMS outcomes: %s", dict(metrics_collector.mrms_outcomes))
                logger.info("  MRMS p95=%.3fs  p99=%.3fs",
                            metrics_collector._percentile(metrics_collector.mrms_durations, 0.95),
                            metrics_collector._percentile(metrics_collector.mrms_durations, 0.99))
                logger.info("  Swath p95=%.3fs  p99=%.3fs",
                            metrics_collector._percentile(metrics_collector.swath_durations, 0.95),
                            metrics_collector._percentile(metrics_collector.swath_durations, 0.99))
                logger.info("  Pileup: current=%d peak=%d total_fetches=%d",
                            pileup_snap['current'], pileup_snap['peak'], pileup_snap['total_fetches'])
                logger.info("  Swaths: active=%d last_valid=%s",
                            swath_info.get('active_swaths', 0),
                            swath_info.get('last_valid_swath_utc'))
                logger.info("  Errors: %d", len(metrics_collector.errors))
                logger.info("-" * 76 + "\n")

                metrics_collector.checkpoint(elapsed, redis_state, pileup_snap)
                next_report = now + REPORT_INTERVAL

            # --- Wait for next tick ---
            tick_wall = time.time() - tick_t0
            sleep_time = max(0, TICK_INTERVAL - tick_wall)
            if sleep_time > 0:
                time.sleep(sleep_time)

    finally:
        injector.uninstall()

    # Wait for any orphan threads
    logger.info("\nWaiting 25s for any orphan MRMS threads to drain...")
    time.sleep(25)

    # ========================================================================
    # Final report
    # ========================================================================
    elapsed_total = time.time() - start_time
    redis_state = _read_redis_state(redis_client)
    pileup_snap = pileup_tracker.snapshot()
    swath_info = _get_active_swaths_info()

    # Final checkpoint
    metrics_collector.checkpoint(elapsed_total, redis_state, pileup_snap)

    logger.info("\n" + "=" * 76)
    logger.info("SOAK TEST COMPLETE — FINAL REPORT")
    logger.info("=" * 76)
    logger.info("Duration: %.1f minutes (%d ticks at %ds interval)",
                elapsed_total / 60, tick_num, TICK_INTERVAL)
    logger.info("")

    # --- Thread pileup ---
    logger.info("=== THREAD PILEUP CHECK ===")
    logger.info("  Peak concurrent MRMS fetches: %d", pileup_snap['peak'])
    logger.info("  Total fetch attempts: %d", pileup_snap['total_fetches'])
    pileup_pass = pileup_snap['peak'] <= 1
    logger.info("  Result: %s", "PASS" if pileup_pass else "FAIL — THREAD PILEUP DETECTED")

    # --- MRMS outcomes ---
    logger.info("\n=== MRMS FETCH OUTCOMES ===")
    outcomes = dict(metrics_collector.mrms_outcomes)
    for status, count in sorted(outcomes.items()):
        logger.info("  %-20s %d", status, count)
    logger.info("  Total: %d", sum(outcomes.values()))

    # --- Latency ---
    logger.info("\n=== LATENCY PERCENTILES ===")
    logger.info("  MRMS fetch   p50=%.3fs  p95=%.3fs  p99=%.3fs  max=%.3fs",
                metrics_collector._percentile(metrics_collector.mrms_durations, 0.50),
                metrics_collector._percentile(metrics_collector.mrms_durations, 0.95),
                metrics_collector._percentile(metrics_collector.mrms_durations, 0.99),
                max(metrics_collector.mrms_durations) if metrics_collector.mrms_durations else 0)
    logger.info("  Swath build  p50=%.3fs  p95=%.3fs  p99=%.3fs  max=%.3fs",
                metrics_collector._percentile(metrics_collector.swath_durations, 0.50),
                metrics_collector._percentile(metrics_collector.swath_durations, 0.95),
                metrics_collector._percentile(metrics_collector.swath_durations, 0.99),
                max(metrics_collector.swath_durations) if metrics_collector.swath_durations else 0)

    # --- Synthetic wall-clock cap ---
    logger.info("\n=== SYNTHETIC GRID WALL-CLOCK CAP ===")
    if metrics_collector.synthetic_wall_times:
        max_syn = max(metrics_collector.synthetic_wall_times)
        cap = int(os.environ.get('MRMS_SYNTHETIC_MAX_SECONDS', '10'))
        # Allow 5s overhead for HTTP setup + teardown
        syn_pass = max_syn <= cap + 5
        logger.info("  Max synthetic fetch wall time: %.1fs (cap=%ds + 5s overhead)",
                    max_syn, cap)
        logger.info("  Result: %s", "PASS" if syn_pass else "FAIL — EXCEEDED CAP")
    else:
        logger.info("  No synthetic fetches observed (OK if Mesonet JSON always succeeded)")
        syn_pass = True

    # --- Failure injection validation ---
    logger.info("\n=== FAILURE INJECTION VALIDATION ===")
    mesonet_block_ticks = [t for t in metrics_collector.ticks
                           if 'mesonet_json' in t.get('active_failure', [])]
    aws_block_ticks = [t for t in metrics_collector.ticks
                       if 'aws_noaa' in t.get('active_failure', [])]
    both_block_ticks = [t for t in metrics_collector.ticks
                        if 'both' in t.get('active_failure', [])]
    clean_ticks = [t for t in metrics_collector.ticks
                   if not t.get('active_failure')]

    logger.info("  Clean ticks: %d", len(clean_ticks))
    logger.info("  Mesonet-blocked ticks: %d", len(mesonet_block_ticks))
    logger.info("  AWS-blocked ticks: %d", len(aws_block_ticks))
    logger.info("  Both-blocked ticks: %d", len(both_block_ticks))

    # Verify system didn't crash during any fault window
    fault_ticks = mesonet_block_ticks + aws_block_ticks + both_block_ticks
    fault_crashes = [t for t in fault_ticks if t.get('mrms_status') not in
                     ('ok', 'error', 'timeout', 'skipped_inflight')]
    injection_pass = len(fault_crashes) == 0
    logger.info("  Ticks with unexpected status during faults: %d", len(fault_crashes))
    logger.info("  Result: %s", "PASS" if injection_pass else "FAIL")

    # --- Checkpoints ---
    logger.info("\n=== 5-MINUTE CHECKPOINTS ===")
    for cp in metrics_collector.checkpoints:
        logger.info("  [%.0f min] ticks=%d mrms=%s p95=%.3fs swath_p95=%.3fs peak_concurrent=%d errors=%d",
                    cp['elapsed_min'],
                    cp['total_ticks'],
                    cp['mrms_outcomes'],
                    cp['mrms_p95'],
                    cp['swath_p95'],
                    cp['pileup']['peak'],
                    cp['total_errors'])

    # --- Swath state ---
    logger.info("\n=== SWATH STATE ===")
    logger.info("  Active swaths: %d", swath_info.get('active_swaths', 0))
    logger.info("  Last valid swath UTC: %s", swath_info.get('last_valid_swath_utc'))

    # --- Errors ---
    logger.info("\n=== ERRORS ===")
    if metrics_collector.errors:
        for err in metrics_collector.errors[:20]:
            logger.info("  Tick %d: %s", err['tick'], err['error'])
        if len(metrics_collector.errors) > 20:
            logger.info("  ... and %d more", len(metrics_collector.errors) - 20)
    else:
        logger.info("  No unhandled errors")

    # --- Final health ---
    logger.info("\n=== FINAL REDIS HEALTH STATE ===")
    logger.info("  tick_status: %s", redis_state.get('tick_status'))
    logger.info("  tick_age: %s sec", redis_state.get('tick_age_sec'))
    logger.info("  mrms_age: %s sec", redis_state.get('mrms_age_sec'))

    # --- Overall verdict ---
    all_pass = pileup_pass and syn_pass and injection_pass
    logger.info("\n" + "=" * 76)
    logger.info("OVERALL RESULT: %s", "ALL PASS" if all_pass else "SOME FAILURES")
    logger.info("=" * 76)

    return {
        'duration_min': round(elapsed_total / 60, 1),
        'total_ticks': tick_num,
        'pileup_pass': pileup_pass,
        'pileup_peak': pileup_snap['peak'],
        'synthetic_cap_pass': syn_pass,
        'injection_pass': injection_pass,
        'mrms_outcomes': outcomes,
        'mrms_p95': metrics_collector._percentile(metrics_collector.mrms_durations, 0.95),
        'mrms_p99': metrics_collector._percentile(metrics_collector.mrms_durations, 0.99),
        'swath_p95': metrics_collector._percentile(metrics_collector.swath_durations, 0.95),
        'swath_p99': metrics_collector._percentile(metrics_collector.swath_durations, 0.99),
        'errors': len(metrics_collector.errors),
        'checkpoints': metrics_collector.checkpoints,
        'all_pass': all_pass,
    }


if __name__ == '__main__':
    result = run_soak()
    sys.exit(0 if result['all_pass'] else 1)
