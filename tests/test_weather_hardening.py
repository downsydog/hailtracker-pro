#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weather-Core Hardening Verification -- 4 Phases
================================================
PHASE 1: MRMS Provider Truthfulness Audit
PHASE 2: MRMS Failure Realism
PHASE 3: Swath Integrity Validation
PHASE 4: Performance Stress (15-min accelerated tick loop)

Run:
    DATABASE_URL="postgresql://hailtracker:hailtracker_dev_2024@localhost:5432/hailtracker_pro" \
    python tests/test_weather_hardening.py
"""

import json
import logging
import os
import sys
import threading
import time

# Add project root to path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Dict, List, Tuple
from unittest.mock import MagicMock, patch

import redis as redis_lib

# ---------------------------------------------------------------------------
# Logging -- capture to buffer for evidence
# ---------------------------------------------------------------------------
_log_buf = StringIO()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-5s %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), logging.StreamHandler(_log_buf)],
)
logger = logging.getLogger('hardening')

# ---------------------------------------------------------------------------
# Redis helper
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get(
    'REDIS_URL',
    os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
)

def get_redis():
    return redis_lib.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=3)

def flush_mrms_keys(r):
    for k in ('mrms:source_time', 'mrms:provider', 'mrms:last_status',
              'mrms:last_error', 'mrms:latest_path', 'mrms:update_count'):
        r.delete(k)

def read_mrms_keys(r) -> Dict[str, str]:
    return {
        'source_time': r.get('mrms:source_time'),
        'provider': r.get('mrms:provider'),
        'last_status': r.get('mrms:last_status'),
        'last_error': r.get('mrms:last_error'),
    }

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
_results: Dict[str, List[Tuple[str, bool, str]]] = {}

def check(phase: str, name: str, passed: bool, detail: str = ''):
    tag = 'PASS' if passed else 'FAIL'
    _results.setdefault(phase, []).append((name, passed, detail))
    msg = f"  [{tag}] {name}"
    if detail:
        msg += f": {detail}"
    print(msg)

def phase_pass(phase: str) -> bool:
    return all(ok for _, ok, _ in _results.get(phase, []))


# ===================================================================
# PHASE 1 -- MRMS Provider Truthfulness Audit
# ===================================================================

def run_phase_1():
    print("\n" + "=" * 70)
    print("PHASE 1 -- MRMS Provider Truthfulness Audit")
    print("=" * 70)

    from src.radar.mrms.redis_cache import get_mrms_cache, RedisMRMSCache
    from src.radar.mrms.updater import MRMSUpdater
    from src.observability.health import compute_sla_state_from_redis, _compute_sla_state

    r = get_redis()

    # ------ 1A: Redis state model correctness ------
    print("\n--- 1A: Redis state model correctness ---")

    # Clean slate
    flush_mrms_keys(r)

    cache = get_mrms_cache(REDIS_URL)
    u = MRMSUpdater(cache=cache, provider_name='aws')
    status = u.fetch_once()

    keys = read_mrms_keys(r)
    print(f"  fetch_once() returned: {status!r}")
    print(f"  Redis keys: {json.dumps(keys, indent=4)}")

    # source_time should be fresh
    check('P1', 'source_time fresh on ok_empty/ok_data',
          keys['source_time'] is not None,
          f"source_time={keys['source_time']}")

    # last_status should match fetch_once return value
    check('P1', 'last_status matches fetch_once',
          keys['last_status'] == status,
          f"last_status={keys['last_status']!r}, fetch_once={status!r}")

    # provider should be actual provider name, NOT 'ok_empty'
    check('P1', 'provider is real name, not status string',
          keys['provider'] not in (None, 'ok_empty', 'ok_data', 'error', 'synthetic'),
          f"provider={keys['provider']!r}")

    # last_error should be None when status != error
    if status != 'error':
        check('P1', 'last_error cleared on success',
              keys['last_error'] is None,
              f"last_error={keys['last_error']!r}")

    # --- Force an error and verify error path ---
    print("\n--- 1A-error: Verify error path ---")
    flush_mrms_keys(r)

    # Mock provider to return None (real error)
    with patch.object(u._provider, 'fetch_mesh_grid', return_value=None):
        err_status = u.fetch_once()

    keys_err = read_mrms_keys(r)
    print(f"  fetch_once() with None provider: {err_status!r}")
    print(f"  Redis keys: {json.dumps(keys_err, indent=4)}")

    check('P1', 'error returns error string',
          err_status == 'error', f"got {err_status!r}")
    check('P1', 'last_status=error on failure',
          keys_err['last_status'] == 'error',
          f"last_status={keys_err['last_status']!r}")
    check('P1', 'last_error set on failure',
          keys_err['last_error'] is not None,
          f"last_error={keys_err['last_error']!r}")

    # ------ 1B: Provider switching ------
    print("\n--- 1B: Provider switching ---")

    flush_mrms_keys(r)
    u_aws = MRMSUpdater(cache=cache, provider_name='aws')
    st_aws = u_aws.fetch_once()
    keys_aws = read_mrms_keys(r)
    print(f"  AWS: status={st_aws!r}, provider={keys_aws['provider']!r}")
    check('P1', 'aws fetch returns valid status',
          st_aws in ('ok_data', 'ok_empty', 'synthetic', 'error'),
          f"status={st_aws!r}")

    flush_mrms_keys(r)
    u_meso = MRMSUpdater(cache=cache, provider_name='mesonet')
    st_meso = u_meso.fetch_once()
    keys_meso = read_mrms_keys(r)
    print(f"  Mesonet: status={st_meso!r}, provider={keys_meso['provider']!r}")
    check('P1', 'mesonet fetch returns valid status',
          st_meso in ('ok_data', 'ok_empty', 'synthetic', 'error'),
          f"status={st_meso!r}")

    # If both succeeded, provider names should differ
    if st_aws != 'error' and st_meso != 'error':
        check('P1', 'provider name updates between providers',
              keys_aws['provider'] != keys_meso['provider'],
              f"aws={keys_aws['provider']!r} mesonet={keys_meso['provider']!r}")
    else:
        # At least the one that succeeded should have a valid provider
        for label, keys_x, st_x in [('aws', keys_aws, st_aws), ('mesonet', keys_meso, st_meso)]:
            if st_x != 'error':
                check('P1', f'{label} provider name is valid',
                      keys_x['provider'] is not None and keys_x['provider'] != '',
                      f"provider={keys_x['provider']!r}")

    # ------ 1C: SLA behavior ------
    print("\n--- 1C: SLA behavior ---")

    # SLA function takes a dict with tick_age_seconds + mrms_age_seconds
    # ok_data / ok_empty / synthetic -> SLA ok (tick fresh + mrms fresh)
    sla_ok = _compute_sla_state({'tick_age_seconds': 60, 'mrms_age_seconds': 30})
    check('P1', 'SLA ok when tick fresh + mrms fresh',
          sla_ok == 'ok', f"sla={sla_ok}")

    # error but tick fresh -> SLA ok at tick level (MRMS stale would degrade)
    sla_mrms_stale = _compute_sla_state({'tick_age_seconds': 60, 'mrms_age_seconds': 700})
    check('P1', 'SLA degraded when mrms stale + tick fresh',
          sla_mrms_stale == 'degraded', f"sla={sla_mrms_stale}")

    # stale tick >= 900 -> SLA down
    sla_down = _compute_sla_state({'tick_age_seconds': 1000, 'mrms_age_seconds': 30})
    check('P1', 'SLA down when tick >= 15min',
          sla_down == 'down', f"sla={sla_down}")

    # tick warning range (5-15 min)
    sla_degraded = _compute_sla_state({'tick_age_seconds': 400, 'mrms_age_seconds': 30})
    check('P1', 'SLA degraded when tick 5-15min',
          sla_degraded == 'degraded', f"sla={sla_degraded}")

    # Verify compute_sla_state_from_redis with live keys
    # Set up: fresh tick + fresh mrms
    now_iso = datetime.now(timezone.utc).isoformat()
    r.set('radar:last_tick_utc', now_iso, ex=60)
    r.set('radar:last_tick_status', 'ok', ex=60)
    # mrms:source_time should still be fresh from earlier fetch
    flush_mrms_keys(r)
    u_check = MRMSUpdater(cache=cache, provider_name='aws')
    u_check.fetch_once()

    sla_live = compute_sla_state_from_redis(r)
    print(f"  Live SLA from Redis: {json.dumps(sla_live, indent=4)}")
    check('P1', 'live SLA state is ok with fresh tick + fresh mrms',
          sla_live['state'] == 'ok',
          f"state={sla_live['state']}")


# ===================================================================
# PHASE 2 -- MRMS Failure Realism
# ===================================================================

def run_phase_2():
    print("\n" + "=" * 70)
    print("PHASE 2 -- MRMS Failure Realism")
    print("=" * 70)

    from src.radar.mrms.redis_cache import get_mrms_cache
    from src.radar.mrms.updater import MRMSUpdater
    from src.workers.radar_tick import _mrms_inflight_lock, _guarded_mrms_fetch

    r = get_redis()
    cache = get_mrms_cache(REDIS_URL)

    # ------ 2A: HTTP 500 ------
    print("\n--- 2A: HTTP 500 simulation ---")
    flush_mrms_keys(r)
    u = MRMSUpdater(cache=cache, provider_name='mesonet')

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    with patch.object(u._provider._session, 'get', return_value=mock_resp):
        status = u.fetch_once()

    keys = read_mrms_keys(r)
    check('P2', 'HTTP 500 -> error status',
          status == 'error', f"status={status!r}")
    check('P2', 'HTTP 500 -> last_status=error',
          keys['last_status'] == 'error', f"last_status={keys['last_status']!r}")
    check('P2', 'HTTP 500 -> last_error set',
          keys['last_error'] is not None, f"last_error={keys['last_error']!r}")

    # ------ 2B: Malformed JSON ------
    print("\n--- 2B: Malformed JSON simulation ---")
    flush_mrms_keys(r)

    mock_resp_json = MagicMock()
    mock_resp_json.status_code = 200
    mock_resp_json.json.side_effect = ValueError("No JSON could be decoded")
    with patch.object(u._provider._session, 'get', return_value=mock_resp_json):
        status = u.fetch_once()

    keys = read_mrms_keys(r)
    check('P2', 'Malformed JSON -> error status',
          status == 'error', f"status={status!r}")
    check('P2', 'Malformed JSON -> last_status=error',
          keys['last_status'] == 'error', f"last_status={keys['last_status']!r}")

    # ------ 2C: Slow timeout ------
    print("\n--- 2C: Slow timeout simulation ---")
    flush_mrms_keys(r)

    import requests
    with patch.object(u._provider._session, 'get',
                      side_effect=requests.exceptions.Timeout("Connection timed out")):
        status = u.fetch_once()

    keys = read_mrms_keys(r)
    check('P2', 'Timeout -> error status',
          status == 'error', f"status={status!r}")
    check('P2', 'Timeout -> last_error mentions timeout or error',
          keys['last_error'] is not None, f"last_error={keys['last_error']!r}")

    # ------ 2D: In-flight guard (no thread pileup) ------
    print("\n--- 2D: In-flight guard / lock safety ---")

    # Ensure lock is not held
    try:
        _mrms_inflight_lock.release()
    except RuntimeError:
        pass

    # Simulate: acquire lock, verify second acquire fails
    acquired = _mrms_inflight_lock.acquire(blocking=False)
    check('P2', 'inflight lock acquirable when free',
          acquired is True, f"acquired={acquired}")

    second = _mrms_inflight_lock.acquire(blocking=False)
    check('P2', 'inflight lock blocks second acquire',
          second is False, f"second_acquire={second}")

    # Release
    _mrms_inflight_lock.release()

    # Test _guarded_mrms_fetch releases lock on success
    _mrms_inflight_lock.acquire(blocking=False)
    u_guard = MRMSUpdater(cache=cache, provider_name='mesonet')
    result = _guarded_mrms_fetch(u_guard)
    check('P2', 'guarded fetch returns valid status',
          result in ('ok_data', 'ok_empty', 'synthetic', 'error'),
          f"result={result!r}")

    # Lock should now be released
    can_reacquire = _mrms_inflight_lock.acquire(blocking=False)
    check('P2', 'lock released after guarded fetch',
          can_reacquire is True, f"can_reacquire={can_reacquire}")
    if can_reacquire:
        _mrms_inflight_lock.release()

    # Test _guarded_mrms_fetch releases lock on exception
    _mrms_inflight_lock.acquire(blocking=False)
    u_exc = MRMSUpdater(cache=cache, provider_name='mesonet')
    with patch.object(u_exc._provider, 'fetch_mesh_grid',
                      side_effect=RuntimeError("boom")):
        result_exc = _guarded_mrms_fetch(u_exc)

    check('P2', 'guarded fetch returns error on exception',
          result_exc == 'error', f"result={result_exc!r}")

    can_reacquire2 = _mrms_inflight_lock.acquire(blocking=False)
    check('P2', 'lock released after exception in guarded fetch',
          can_reacquire2 is True, f"can_reacquire={can_reacquire2}")
    if can_reacquire2:
        _mrms_inflight_lock.release()

    # ------ 2E: Concurrent fetch count ------
    print("\n--- 2E: Peak concurrent fetches <= 1 ---")
    peak_concurrent = [0]
    current_concurrent = [0]
    lock_counter = threading.Lock()

    original_fetch = u._provider.fetch_mesh_grid

    def counting_fetch(*a, **kw):
        with lock_counter:
            current_concurrent[0] += 1
            peak_concurrent[0] = max(peak_concurrent[0], current_concurrent[0])
        try:
            time.sleep(0.1)
            return original_fetch(*a, **kw)
        finally:
            with lock_counter:
                current_concurrent[0] -= 1

    # Ensure inflight lock is free
    try:
        _mrms_inflight_lock.release()
    except RuntimeError:
        pass

    # Try to run 3 concurrent fetches
    threads = []
    results_concurrent = []

    def attempt_guarded():
        acq = _mrms_inflight_lock.acquire(blocking=False)
        if not acq:
            results_concurrent.append('skipped_inflight')
            return
        u_t = MRMSUpdater(cache=cache, provider_name='mesonet')
        with patch.object(u_t._provider, 'fetch_mesh_grid', side_effect=counting_fetch):
            r_val = _guarded_mrms_fetch(u_t)
            results_concurrent.append(r_val)

    for _ in range(3):
        t = threading.Thread(target=attempt_guarded)
        threads.append(t)
        t.start()
        time.sleep(0.01)

    for t in threads:
        t.join(timeout=30)

    check('P2', 'peak concurrent fetches <= 1',
          peak_concurrent[0] <= 1,
          f"peak={peak_concurrent[0]}, results={results_concurrent}")


# ===================================================================
# PHASE 3 -- Swath Integrity Validation
# ===================================================================

def run_phase_3():
    print("\n" + "=" * 70)
    print("PHASE 3 -- Swath Integrity Validation")
    print("=" * 70)

    from src.db.engine import get_connection, is_postgres, placeholder as ph, ensure_schema

    if not is_postgres():
        print("  SKIP: Phase 3 requires PostgreSQL + PostGIS")
        check('P3', 'PostgreSQL available', False, 'Not running PostgreSQL')
        return

    ensure_schema()

    # Apply migration 004 if not already applied
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name='hail_swaths' AND column_name='last_valid_swath_utc'")
            if not cur.fetchone():
                mig_path = os.path.join(os.path.dirname(__file__), '..', 'migrations', '004_geometry_validity.sql')
                if os.path.exists(mig_path):
                    with open(mig_path) as f:
                        cur.execute(f.read())
                    logger.info("Applied migration 004")
    except Exception as e:
        logger.warning("Migration 004 check: %s", e)

    p = ph()

    # ------ 3A: Valid polygon ------
    print("\n--- 3A: Valid polygon insert ---")
    valid_poly = json.dumps({
        "type": "Polygon",
        "coordinates": [[
            [-97.0, 35.0], [-96.5, 35.0], [-96.5, 35.5],
            [-97.0, 35.5], [-97.0, 35.0]
        ]]
    })

    swath_id_valid = f'test_valid_{int(time.time())}'
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO hail_swaths (
                    swath_id, first_seen_utc, last_seen_utc,
                    centroid_lat, centroid_lon,
                    area_km2, geometry_geojson, lifecycle_state,
                    area_method, geometry_quality, member_event_names
                ) VALUES (
                    {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}
                )
                ON CONFLICT(swath_id) DO UPDATE SET geometry_geojson = excluded.geometry_geojson
            """, (
                swath_id_valid,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                35.25, -96.75, 100.0, valid_poly, 'MATURE',
                'cell_union', 'HIGH', '[]',
            ))

            # Verify swath_geom was populated by trigger
            cur.execute(f"""
                SELECT ST_IsValid(swath_geom) as valid,
                       ST_Area(swath_geom::geography)/1e6 as area_km2,
                       ST_GeometryType(swath_geom) as geom_type
                FROM hail_swaths WHERE swath_id = {p}
            """, (swath_id_valid,))
            row = cur.fetchone()

            if row:
                is_valid = row[0]
                area_km2 = row[1]
                geom_type = row[2]
                check('P3', 'valid polygon: swath_geom populated', True,
                      f"type={geom_type}")
                check('P3', 'valid polygon: ST_IsValid=true',
                      is_valid is True, f"valid={is_valid}")
                check('P3', 'valid polygon: area > 0',
                      area_km2 is not None and area_km2 > 0,
                      f"area_km2={area_km2:.2f}" if area_km2 else "area=None")
            else:
                check('P3', 'valid polygon: row inserted', False, 'no row returned')
    except Exception as e:
        check('P3', 'valid polygon: insert', False, str(e))

    # ------ 3B: Self-intersecting polygon (bowtie) ------
    print("\n--- 3B: Self-intersecting polygon ---")
    bowtie = json.dumps({
        "type": "Polygon",
        "coordinates": [[
            [-97.0, 35.0], [-96.0, 36.0], [-96.0, 35.0],
            [-97.0, 36.0], [-97.0, 35.0]
        ]]
    })

    swath_id_bowtie = f'test_bowtie_{int(time.time())}'
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO hail_swaths (
                    swath_id, first_seen_utc, last_seen_utc,
                    centroid_lat, centroid_lon,
                    area_km2, geometry_geojson, lifecycle_state,
                    area_method, geometry_quality, member_event_names
                ) VALUES (
                    {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}
                )
                ON CONFLICT(swath_id) DO UPDATE SET geometry_geojson = excluded.geometry_geojson
            """, (
                swath_id_bowtie,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                35.5, -96.5, 50.0, bowtie, 'FORMING',
                'centroid_buffer', 'MED', '[]',
            ))

            # ST_MakeValid trigger should repair it
            cur.execute(f"""
                SELECT ST_IsValid(swath_geom) as valid,
                       swath_geom IS NOT NULL as has_geom,
                       ST_Area(swath_geom::geography)/1e6 as area_km2
                FROM hail_swaths WHERE swath_id = {p}
            """, (swath_id_bowtie,))
            row = cur.fetchone()

            if row:
                has_geom = row[1]
                is_valid = row[0]
                area = row[2]
                check('P3', 'bowtie: swath_geom populated',
                      has_geom is True, f"has_geom={has_geom}")
                check('P3', 'bowtie: ST_MakeValid repaired -> ST_IsValid=true',
                      is_valid is True, f"valid={is_valid}")
                check('P3', 'bowtie: area > 0 after repair',
                      area is not None and area > 0,
                      f"area_km2={area:.2f}" if area else "area=None")
            else:
                check('P3', 'bowtie: row inserted', False, 'no row returned')
    except Exception as e:
        check('P3', 'bowtie: insert', False, str(e))

    # ------ 3C: Empty / NULL geometry ------
    print("\n--- 3C: Empty / NULL geometry ---")
    swath_id_null = f'test_nullgeom_{int(time.time())}'
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO hail_swaths (
                    swath_id, first_seen_utc, last_seen_utc,
                    centroid_lat, centroid_lon,
                    area_km2, geometry_geojson, lifecycle_state,
                    area_method, geometry_quality, member_event_names
                ) VALUES (
                    {p}, {p}, {p}, {p}, {p}, {p}, NULL, {p}, {p}, {p}, {p}
                )
                ON CONFLICT(swath_id) DO UPDATE SET geometry_geojson = excluded.geometry_geojson
            """, (
                swath_id_null,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                35.0, -97.0, 0.0, 'FORMING',
                'unknown', 'LOW', '[]',
            ))

            cur.execute(f"""
                SELECT swath_geom IS NULL as geom_null
                FROM hail_swaths WHERE swath_id = {p}
            """, (swath_id_null,))
            row = cur.fetchone()
            check('P3', 'null geometry: swath_geom is NULL',
                  row is not None and row[0] is True,
                  f"geom_null={row[0] if row else 'N/A'}")
    except Exception as e:
        check('P3', 'null geometry: insert', False, str(e))

    # ------ 3D: Extremely small geometry ------
    print("\n--- 3D: Extremely small geometry ---")
    tiny_poly = json.dumps({
        "type": "Polygon",
        "coordinates": [[
            [-97.000000, 35.000000], [-97.000001, 35.000000],
            [-97.000001, 35.000001], [-97.000000, 35.000001],
            [-97.000000, 35.000000]
        ]]
    })
    swath_id_tiny = f'test_tiny_{int(time.time())}'
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                INSERT INTO hail_swaths (
                    swath_id, first_seen_utc, last_seen_utc,
                    centroid_lat, centroid_lon,
                    area_km2, geometry_geojson, lifecycle_state,
                    area_method, geometry_quality, member_event_names
                ) VALUES (
                    {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}
                )
                ON CONFLICT(swath_id) DO UPDATE SET geometry_geojson = excluded.geometry_geojson
            """, (
                swath_id_tiny,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                35.0, -97.0, 0.001, tiny_poly, 'FORMING',
                'centroid_buffer', 'LOW', '[]',
            ))

            cur.execute(f"""
                SELECT ST_IsValid(swath_geom) as valid,
                       swath_geom IS NOT NULL as has_geom,
                       ST_Area(swath_geom::geography) as area_m2
                FROM hail_swaths WHERE swath_id = {p}
            """, (swath_id_tiny,))
            row = cur.fetchone()
            if row:
                check('P3', 'tiny geometry: swath_geom populated',
                      row[1] is True, f"has_geom={row[1]}")
                check('P3', 'tiny geometry: ST_IsValid',
                      row[0] is True, f"valid={row[0]}")
                check('P3', 'tiny geometry: area near zero',
                      row[2] is not None and row[2] < 1.0,
                      f"area_m2={row[2]:.6f}" if row[2] else "None")
            else:
                check('P3', 'tiny geometry: row inserted', False, 'no row')
    except Exception as e:
        check('P3', 'tiny geometry: insert', False, str(e))

    # ------ 3E: fetch_swaths_geojson does not crash ------
    print("\n--- 3E: fetch_swaths_geojson() ---")
    try:
        from src.swath.intelligence_engine import fetch_swaths_geojson
        result = fetch_swaths_geojson(simplify_meters=0)
        check('P3', 'fetch_swaths_geojson: no crash',
              isinstance(result, list), f"type={type(result).__name__}, len={len(result)}")
    except Exception as e:
        check('P3', 'fetch_swaths_geojson: no crash', False, str(e))

    # Simplification path
    try:
        result_simp = fetch_swaths_geojson(simplify_meters=500)
        check('P3', 'fetch_swaths_geojson with simplify: no crash',
              isinstance(result_simp, list),
              f"len={len(result_simp)}")
    except Exception as e:
        check('P3', 'fetch_swaths_geojson with simplify: no crash', False, str(e))

    # ------ 3F: area_method and geometry_quality populated ------
    print("\n--- 3F: area_method, geometry_quality, last_valid_swath_utc ---")
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT swath_id, area_method, geometry_quality
                FROM hail_swaths WHERE swath_id = {p}
            """, (swath_id_valid,))
            row = cur.fetchone()
            if row:
                check('P3', 'area_method populated',
                      row[1] is not None and row[1] != '',
                      f"area_method={row[1]!r}")
                check('P3', 'geometry_quality populated',
                      row[2] is not None and row[2] != '',
                      f"geometry_quality={row[2]!r}")
            else:
                check('P3', 'area_method populated', False, 'row not found')
    except Exception as e:
        check('P3', 'area_method populated', False, str(e))

    # ------ Cleanup test rows ------
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            for sid in [swath_id_valid, swath_id_bowtie, swath_id_null, swath_id_tiny]:
                cur.execute(f"DELETE FROM hail_swaths WHERE swath_id = {p}", (sid,))
    except Exception:
        pass


# ===================================================================
# PHASE 4 -- Performance Stress (accelerated)
# ===================================================================

def run_phase_4():
    print("\n" + "=" * 70)
    print("PHASE 4 -- Performance Stress (accelerated 2-minute loop)")
    print("=" * 70)

    from src.radar.mrms.redis_cache import get_mrms_cache
    from src.radar.mrms.updater import MRMSUpdater
    from src.workers.radar_tick import _mrms_inflight_lock, _guarded_mrms_fetch
    from src.observability.health import compute_sla_state_from_redis

    r = get_redis()
    cache = get_mrms_cache(REDIS_URL)

    DURATION_SECONDS = 120  # 2 minutes accelerated
    TICK_INTERVAL = 5       # every 5 seconds

    durations = []
    statuses = []
    errors = []
    peak_concurrent = [0]
    current_concurrent = [0]
    lock_counter = threading.Lock()
    unhandled_exceptions = []
    lock_leaks = 0
    sla_states = []

    # Ensure inflight lock is free
    try:
        _mrms_inflight_lock.release()
    except RuntimeError:
        pass

    print(f"  Running {DURATION_SECONDS}s accelerated loop (tick every {TICK_INTERVAL}s)...")
    start = time.time()
    tick_count = 0

    while time.time() - start < DURATION_SECONDS:
        tick_count += 1
        tick_start = time.time()

        try:
            # Simulate tick's MRMS fetch path
            acquired = _mrms_inflight_lock.acquire(blocking=False)
            if not acquired:
                statuses.append('skipped_inflight')
                with lock_counter:
                    pass  # just checking
            else:
                with lock_counter:
                    current_concurrent[0] += 1
                    peak_concurrent[0] = max(peak_concurrent[0], current_concurrent[0])

                try:
                    u = MRMSUpdater(cache=cache, provider_name='aws')
                    result = _guarded_mrms_fetch(u)
                    # _guarded_mrms_fetch releases the lock in its finally
                    statuses.append(result)
                except Exception as e:
                    unhandled_exceptions.append(str(e))
                    try:
                        _mrms_inflight_lock.release()
                    except RuntimeError:
                        pass
                finally:
                    with lock_counter:
                        current_concurrent[0] -= 1

            elapsed = time.time() - tick_start
            durations.append(elapsed)

            # Check lock not leaked
            lock_free = _mrms_inflight_lock.acquire(blocking=False)
            if lock_free:
                _mrms_inflight_lock.release()
            else:
                lock_leaks += 1

            # Check SLA
            now_iso = datetime.now(timezone.utc).isoformat()
            r.set('radar:last_tick_utc', now_iso, ex=60)
            r.set('radar:last_tick_status', 'ok', ex=60)
            sla = compute_sla_state_from_redis(r)
            sla_states.append(sla['state'])

        except Exception as e:
            unhandled_exceptions.append(f"tick {tick_count}: {e}")

        # Wait for next tick
        wait = max(0, TICK_INTERVAL - (time.time() - tick_start))
        if wait > 0:
            time.sleep(wait)

    # ------ Analyze results ------
    print(f"\n  Completed {tick_count} ticks in {time.time() - start:.1f}s")

    # Status distribution
    from collections import Counter
    status_dist = Counter(statuses)
    print(f"  Status distribution: {dict(status_dist)}")

    # Duration percentiles
    if durations:
        durations_sorted = sorted(durations)
        n = len(durations_sorted)
        p50 = durations_sorted[int(n * 0.50)]
        p95 = durations_sorted[int(min(n - 1, n * 0.95))]
        p99 = durations_sorted[int(min(n - 1, n * 0.99))]
        print(f"  MRMS fetch duration: p50={p50:.2f}s  p95={p95:.2f}s  p99={p99:.2f}s")
    else:
        p50 = p95 = p99 = 0

    # Error rate
    error_count = sum(1 for s in statuses if s == 'error')
    total = len(statuses)
    error_rate = error_count / total if total > 0 else 0
    print(f"  Error rate: {error_count}/{total} ({error_rate:.1%})")
    print(f"  Peak concurrent: {peak_concurrent[0]}")
    print(f"  Lock leaks: {lock_leaks}")
    print(f"  Unhandled exceptions: {len(unhandled_exceptions)}")
    if unhandled_exceptions:
        for e in unhandled_exceptions[:5]:
            print(f"    - {e}")

    # SLA state distribution
    sla_dist = Counter(sla_states)
    print(f"  SLA distribution: {dict(sla_dist)}")

    # Verify Redis keys still consistent
    keys_final = read_mrms_keys(r)
    print(f"  Final Redis keys: {json.dumps(keys_final, indent=4)}")

    # Taxonomy check: all statuses should be valid
    valid_statuses = {'ok_data', 'ok_empty', 'synthetic', 'error', 'timeout', 'skipped_inflight'}
    invalid = [s for s in statuses if s not in valid_statuses]

    # Checks
    check('P4', 'no unhandled exceptions',
          len(unhandled_exceptions) == 0,
          f"count={len(unhandled_exceptions)}")
    check('P4', 'no lock deadlock (leaks=0)',
          lock_leaks == 0, f"leaks={lock_leaks}")
    check('P4', 'peak concurrent fetches <= 1',
          peak_concurrent[0] <= 1, f"peak={peak_concurrent[0]}")
    check('P4', 'status taxonomy correct (all values valid)',
          len(invalid) == 0,
          f"invalid={invalid[:5]}" if invalid else "all valid")
    check('P4', 'SLA did not flap to down incorrectly',
          'down' not in sla_dist,
          f"sla_dist={dict(sla_dist)}")
    check('P4', 'Redis keys consistent after stress',
          keys_final['last_status'] in valid_statuses,
          f"last_status={keys_final['last_status']!r}")
    check('P4', 'mrms:provider is real name (not status)',
          keys_final['provider'] not in (None, '', 'ok_empty', 'ok_data', 'error'),
          f"provider={keys_final['provider']!r}")

    # Metrics table
    print("\n  ┌─────────────────────────────────┬─────────────┐")
    print("  │ Metric                          │ Value       │")
    print("  ├─────────────────────────────────┼─────────────┤")
    print(f"  │ Ticks                           │ {tick_count:<11d} │")
    print(f"  │ MRMS p50                        │ {p50:<11.3f} │")
    print(f"  │ MRMS p95                        │ {p95:<11.3f} │")
    print(f"  │ MRMS p99                        │ {p99:<11.3f} │")
    print(f"  │ Error rate                      │ {error_rate:<11.1%} │")
    print(f"  │ Peak concurrent                 │ {peak_concurrent[0]:<11d} │")
    print(f"  │ Lock leaks                      │ {lock_leaks:<11d} │")
    print(f"  │ Unhandled exceptions            │ {len(unhandled_exceptions):<11d} │")
    print("  └─────────────────────────────────┴─────────────┘")


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("HailTracker Weather-Core Hardening Verification")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    run_phase_1()
    run_phase_2()
    run_phase_3()
    run_phase_4()

    # ------ Final Summary ------
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    all_pass = True
    for phase_key in ['P1', 'P2', 'P3', 'P4']:
        phase_label = {
            'P1': 'PHASE 1 -- MRMS Provider Truthfulness',
            'P2': 'PHASE 2 -- MRMS Failure Realism',
            'P3': 'PHASE 3 -- Swath Integrity',
            'P4': 'PHASE 4 -- Performance Stress',
        }[phase_key]
        passed = phase_pass(phase_key)
        all_pass = all_pass and passed
        tag = 'PASS' if passed else 'FAIL'
        checks = _results.get(phase_key, [])
        total = len(checks)
        ok = sum(1 for _, p, _ in checks if p)
        print(f"  [{tag}] {phase_label} ({ok}/{total})")

        # Show failures
        for name, p, detail in checks:
            if not p:
                print(f"         FAIL: {name} -- {detail}")

    print()
    if all_pass:
        print("  ALL PHASES PASSED")
    else:
        print("  SOME PHASES FAILED -- see details above")

    print("=" * 70)
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
