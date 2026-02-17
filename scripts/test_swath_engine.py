#!/usr/bin/env python3
"""
Swath Intelligence Engine v2 unit tests.

Validates clustering, impact scoring, lifecycle transitions, area fallback,
motion coherence, geometry quality damping, and ID stability.

Run: python scripts/test_swath_engine.py
"""

import json
import math
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.swath.intelligence_engine import (
    _angular_diff,
    _cluster_events,
    _compute_area_km2,
    _compute_impact_score,
    _compute_lifecycle,
    _compute_motion_score,
    _forward_position,
    _generate_stable_swath_id,
    _generate_swath_id,
    _geometry_quality,
    _get_tier,
    _haversine_km,
    _time_gap_minutes,
    update_swaths,
)


def _make_event(
    name: str,
    lat: float,
    lon: float,
    start_offset_min: int = 0,
    duration_min: int = 10,
    max_hail: float = 1.0,
    confidence: float = 50.0,
    swath_area_sqmi: float = 5.0,
    swath_polygon: str = None,
    swath_area_method: str = 'centroid_buffer',
    swath_area_km2: float = 0.0,
) -> dict:
    """Create a synthetic event dict for testing."""
    base = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    start = base + timedelta(minutes=start_offset_min)
    end = start + timedelta(minutes=duration_min)
    return {
        'event_name': name,
        'center_lat': lat,
        'center_lon': lon,
        'start_time': start.isoformat(),
        'end_time': end.isoformat(),
        'max_hail_size': max_hail,
        'confidence_score': confidence,
        'swath_polygon': swath_polygon,
        'swath_area_sqmi': swath_area_sqmi,
        'swath_area_method': swath_area_method,
        'swath_area_km2': swath_area_km2,
    }


# -----------------------------------------------------------------------
# Test: Clustering (legacy, still validates v1 compat)
# -----------------------------------------------------------------------

def test_clustering():
    print("Category: Clustering")
    all_pass = True

    ev1 = _make_event("A", 35.0, -97.0, start_offset_min=0)
    ev2 = _make_event("B", 35.1, -97.1, start_offset_min=10)
    ev3 = _make_event("C", 35.2, -97.0, start_offset_min=20)
    clusters = _cluster_events([ev1, ev2, ev3])
    ok = len(clusters) == 1 and len(clusters[0]) == 3
    print(f"  [{'PASS' if ok else 'FAIL'}] 3 nearby events -> 1 cluster of 3")
    all_pass &= ok

    ev_far = _make_event("D", 35.8, -97.0, start_offset_min=5)
    clusters = _cluster_events([ev1, ev2, ev3, ev_far])
    cluster_sizes = [len(c) for c in clusters]
    ok = 3 in cluster_sizes and 1 not in cluster_sizes
    print(f"  [{'PASS' if ok else 'FAIL'}] Far event -> excluded (single-event filtered)")
    all_pass &= ok

    ev_late = _make_event("E", 35.05, -97.05, start_offset_min=80)
    ev_late2 = _make_event("F", 35.06, -97.06, start_offset_min=85)
    clusters = _cluster_events([ev1, ev2, ev3, ev_late, ev_late2])
    ok = len(clusters) == 2
    print(f"  [{'PASS' if ok else 'FAIL'}] 60min gap -> 2 separate clusters")
    all_pass &= ok

    ev_solo = _make_event("SOLO", 40.0, -100.0, max_hail=0.5)
    clusters = _cluster_events([ev_solo])
    ok = len(clusters) == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] Single event below threshold -> filtered out")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Impact Scoring
# -----------------------------------------------------------------------

def test_impact_scoring():
    print("\nCategory: Impact Scoring")
    all_pass = True

    cluster_severe = [
        _make_event("S1", 35.0, -97.0, max_hail=2.5),
        _make_event("S2", 35.1, -97.1, max_hail=3.0),
        _make_event("S3", 35.2, -97.0, max_hail=2.0),
    ]
    score = _compute_impact_score(cluster_severe, severe_core_km2=50.0, duration_min=45.0)
    ok = score >= 70
    print(f"  [{'PASS' if ok else 'FAIL'}] All severe hail -> score={score} (expected >=70)")
    all_pass &= ok

    cluster_mixed = [
        _make_event("M1", 35.0, -97.0, max_hail=2.5),
        _make_event("M2", 35.1, -97.1, max_hail=1.0),
        _make_event("M3", 35.2, -97.0, max_hail=0.5),
    ]
    score = _compute_impact_score(cluster_mixed, severe_core_km2=10.0, duration_min=30.0)
    ok = 20 <= score <= 50
    print(f"  [{'PASS' if ok else 'FAIL'}] Mixed hail -> score={score} (expected 20-50)")
    all_pass &= ok

    cluster_weak = [
        _make_event("W1", 35.0, -97.0, max_hail=0.5),
        _make_event("W2", 35.1, -97.1, max_hail=0.3),
    ]
    score = _compute_impact_score(cluster_weak, severe_core_km2=0.0, duration_min=5.0)
    ok = score <= 15
    print(f"  [{'PASS' if ok else 'FAIL'}] No severe hail -> score={score} (expected <=15)")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Tier mapping
# -----------------------------------------------------------------------

def test_tiers():
    print("\nCategory: Impact Tiers")
    all_pass = True

    tests = [(90, 'EXTREME'), (80, 'EXTREME'), (79, 'HIGH'), (60, 'HIGH'),
             (59, 'MODERATE'), (30, 'MODERATE'), (29, 'LOW'), (0, 'LOW')]
    for score, expected in tests:
        tier = _get_tier(score)
        ok = tier == expected
        if not ok:
            print(f"  [FAIL] score={score} -> {tier} (expected {expected})")
            all_pass = False
    if all_pass:
        print(f"  [PASS] All 8 tier boundaries correct")

    return all_pass


# -----------------------------------------------------------------------
# Test: Lifecycle transitions
# -----------------------------------------------------------------------

def test_lifecycle():
    print("\nCategory: Lifecycle Transitions")
    all_pass = True

    now_str = datetime.now(timezone.utc).isoformat()
    old_str = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()

    state, dc = _compute_lifecycle(1, 0.0, 0.0, 20, now_str, None, 0)
    ok = state == 'FORMING'
    print(f"  [{'PASS' if ok else 'FAIL'}] Single event -> {state} (expected FORMING)")
    all_pass &= ok

    state, dc = _compute_lifecycle(2, 0.5, 5.0, 40, now_str, 'FORMING', 0)
    ok = state == 'ORGANIZING'
    print(f"  [{'PASS' if ok else 'FAIL'}] 2 events + growth -> {state} (expected ORGANIZING)")
    all_pass &= ok

    state, dc = _compute_lifecycle(5, 1.0, 15.0, 65, now_str, 'ORGANIZING', 0,
                                    geo_quality='MED', has_mrms_core=False)
    ok = state == 'MATURE'
    print(f"  [{'PASS' if ok else 'FAIL'}] Core>=10 + impact>=60 + MED quality -> {state} (expected MATURE)")
    all_pass &= ok

    state, dc = _compute_lifecycle(5, -0.5, 12.0, 55, now_str, 'MATURE', 1)
    ok = state == 'DECAYING' and dc == 2
    print(f"  [{'PASS' if ok else 'FAIL'}] MATURE + 2nd neg growth -> {state} dc={dc} (expected DECAYING, 2)")
    all_pass &= ok

    state, dc = _compute_lifecycle(3, 0.0, 10.0, 50, old_str, 'ORGANIZING', 0)
    ok = state == 'EXPIRED'
    print(f"  [{'PASS' if ok else 'FAIL'}] 60min old -> {state} (expected EXPIRED)")
    all_pass &= ok

    state, dc = _compute_lifecycle(5, 1.0, 20.0, 80, now_str, 'EXPIRED', 0)
    ok = state == 'EXPIRED'
    print(f"  [{'PASS' if ok else 'FAIL'}] EXPIRED stays EXPIRED -> {state}")
    all_pass &= ok

    state, dc = _compute_lifecycle(3, 0.1, 5.0, 30, now_str, 'MATURE', 0)
    ok = state == 'MATURE'
    print(f"  [{'PASS' if ok else 'FAIL'}] MATURE stays MATURE (no downgrade) -> {state}")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Swath ID determinism (legacy)
# -----------------------------------------------------------------------

def test_swath_id():
    print("\nCategory: Swath ID")
    all_pass = True

    cluster = [
        _make_event("B", 35.1, -97.1, start_offset_min=10),
        _make_event("A", 35.0, -97.0, start_offset_min=0),
    ]
    id1 = _generate_swath_id(cluster)
    id2 = _generate_swath_id(list(reversed(cluster)))
    ok = id1 == id2 and id1.startswith("SWATH_")
    print(f"  [{'PASS' if ok else 'FAIL'}] Same events in different order -> same ID: {id1}")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Area fallback methods
# -----------------------------------------------------------------------

def test_area_fallback():
    print("\nCategory: Area Fallback")
    all_pass = True

    cluster_sqmi = [
        _make_event("A1", 35.0, -97.0, swath_area_sqmi=10.0, swath_polygon=None),
        _make_event("A2", 35.1, -97.1, swath_area_sqmi=8.0, swath_polygon=None),
    ]
    geojsons = [ev['swath_polygon'] for ev in cluster_sqmi]
    area, geom, method = _compute_area_km2(geojsons, 35.05, cluster=cluster_sqmi)
    ok = method == 'sum_sqmi' and abs(area - (18.0 * 2.59)) < 0.01 and geom is None
    print(f"  [{'PASS' if ok else 'FAIL'}] No polygons + sqmi -> method={method} area={area:.2f}")
    all_pass &= ok

    cluster_noarea = [
        _make_event("B1", 35.0, -97.0, swath_area_sqmi=0.0, swath_polygon=None),
        _make_event("B2", 35.2, -97.0, swath_area_sqmi=0.0, swath_polygon=None),
    ]
    geojsons = [ev['swath_polygon'] for ev in cluster_noarea]
    area, geom, method = _compute_area_km2(geojsons, 35.1, cluster=cluster_noarea)
    ok = method == 'radius_proxy' and area > 100 and geom is None
    print(f"  [{'PASS' if ok else 'FAIL'}] No polygons + no sqmi -> method={method} area={area:.1f}")
    all_pass &= ok

    cluster_tight = [
        _make_event("C1", 35.0, -97.0, swath_area_sqmi=0.0, swath_polygon=None),
        _make_event("C2", 35.001, -97.001, swath_area_sqmi=0.0, swath_polygon=None),
    ]
    geojsons = [ev['swath_polygon'] for ev in cluster_tight]
    area, geom, method = _compute_area_km2(geojsons, 35.0, cluster=cluster_tight)
    expected_min = math.pi * 3.0 ** 2
    ok = method == 'radius_proxy' and abs(area - expected_min) < 1.0
    print(f"  [{'PASS' if ok else 'FAIL'}] Tight cluster -> radius_proxy min radius: area={area:.1f}")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Motion Coherence
# -----------------------------------------------------------------------

def test_motion_coherence():
    print("\nCategory: Motion Coherence")
    all_pass = True

    # --- Test 1: Two storms, same time, within 50km, OPPOSITE bearings -> must NOT merge ---
    # Storm A: moving east (bearing ~90)
    swath_a = {
        'swath_id': 'SA',
        'centroid_lat': 35.0, 'centroid_lon': -97.0,
        'last_seen_utc': datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc).isoformat(),
        'directional_vector_deg': 90.0,  # east
        'velocity_kmh': 50.0,
    }
    # Storm B: moving north (bearing ~0)
    swath_b = {
        'swath_id': 'SB',
        'centroid_lat': 35.3, 'centroid_lon': -97.0,  # ~33km north of A
        'last_seen_utc': datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc).isoformat(),
        'directional_vector_deg': 0.0,  # north
        'velocity_kmh': 50.0,
    }

    # New event: appears to the east of A at t+20min (consistent with A moving east)
    ev_east = _make_event("EV_E", 35.0, -96.8, start_offset_min=20)
    score_a, _ = _compute_motion_score(swath_a, ev_east)
    score_b, _ = _compute_motion_score(swath_b, ev_east)

    ok = score_a > score_b  # A should score higher (motion consistent)
    print(f"  [{'PASS' if ok else 'FAIL'}] East event matches east-moving swath: "
          f"scoreA={score_a:.3f} > scoreB={score_b:.3f}")
    all_pass &= ok

    # New event: appears to the north of B at t+20min (consistent with B moving north)
    ev_north = _make_event("EV_N", 35.5, -97.0, start_offset_min=20)
    score_a2, _ = _compute_motion_score(swath_a, ev_north)
    score_b2, _ = _compute_motion_score(swath_b, ev_north)

    ok = score_b2 > score_a2  # B should score higher
    print(f"  [{'PASS' if ok else 'FAIL'}] North event matches north-moving swath: "
          f"scoreB={score_b2:.3f} > scoreA={score_a2:.3f}")
    all_pass &= ok

    # --- Test 2: Bearing gate - opposite direction should be rejected ---
    swath_east = {
        'swath_id': 'SE',
        'centroid_lat': 35.0, 'centroid_lon': -97.0,
        'last_seen_utc': datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc).isoformat(),
        'directional_vector_deg': 90.0,  # east
        'velocity_kmh': 60.0,
    }
    # Event to the WEST (opposite of swath direction)
    ev_west = _make_event("EV_W", 35.0, -97.2, start_offset_min=20)
    score_opp, _ = _compute_motion_score(swath_east, ev_west)
    ok = score_opp < 0  # should be rejected by bearing gate
    print(f"  [{'PASS' if ok else 'FAIL'}] Opposite-direction event rejected: score={score_opp:.3f}")
    all_pass &= ok

    # --- Test 3: Forward projection allows jump outside 40km if velocity-consistent ---
    swath_fast = {
        'swath_id': 'SF',
        'centroid_lat': 35.0, 'centroid_lon': -97.0,
        'last_seen_utc': datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc).isoformat(),
        'directional_vector_deg': 90.0,  # east
        'velocity_kmh': 80.0,  # fast-moving
    }
    # Event 55km east at dt=45min: projected position ~60km east, so dist to pred ~5km
    # At 80km/h for 0.75h = 60km projected distance
    pred_lat, pred_lon = _forward_position(35.0, -97.0, 90.0, 60.0)
    ev_jump = {
        'event_name': 'EV_J',
        'center_lat': pred_lat,
        'center_lon': pred_lon + 0.05,  # slightly past prediction
        'start_time': (datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=45)).isoformat(),
        'end_time': (datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=55)).isoformat(),
    }
    score_jump, dist_jump = _compute_motion_score(swath_fast, ev_jump)
    # Raw distance from swath centroid:
    raw_dist = _haversine_km(35.0, -97.0, ev_jump['center_lat'], ev_jump['center_lon'])
    ok = score_jump >= 0.45 and raw_dist > 40
    print(f"  [{'PASS' if ok else 'FAIL'}] Forward projection: raw_dist={raw_dist:.1f}km > 40, "
          f"score={score_jump:.3f} >= 0.45 (projected match)")
    all_pass &= ok

    # --- Test 4: Time gate - event too far in future should be rejected ---
    ev_old = {
        'event_name': 'EV_OLD',
        'center_lat': 35.0, 'center_lon': -96.8,
        'start_time': (datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=80)).isoformat(),
        'end_time': (datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=90)).isoformat(),
    }
    score_old, _ = _compute_motion_score(swath_a, ev_old)
    ok = score_old < 0
    print(f"  [{'PASS' if ok else 'FAIL'}] Event >75min future rejected: score={score_old:.3f}")
    all_pass &= ok

    # --- Test 5: Nearby static swath should still match nearby event ---
    swath_static = {
        'swath_id': 'SS',
        'centroid_lat': 35.0, 'centroid_lon': -97.0,
        'last_seen_utc': datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc).isoformat(),
        'directional_vector_deg': 0.0,
        'velocity_kmh': 0.0,  # not moving
    }
    ev_nearby = _make_event("EV_NEAR", 35.1, -97.05, start_offset_min=15)
    score_near, dist_near = _compute_motion_score(swath_static, ev_nearby)
    ok = score_near >= 0.45 and dist_near < 35
    print(f"  [{'PASS' if ok else 'FAIL'}] Static swath matches nearby event: "
          f"score={score_near:.3f}, dist={dist_near:.1f}km")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Geometry Quality
# -----------------------------------------------------------------------

def test_geometry_quality():
    print("\nCategory: Geometry Quality")
    all_pass = True

    # HIGH quality from cell_union
    q = _geometry_quality(['centroid_buffer', 'cell_union', 'radius_proxy'])
    ok = q == 'HIGH'
    print(f"  [{'PASS' if ok else 'FAIL'}] cell_union present -> {q} (expected HIGH)")
    all_pass &= ok

    # MED quality from centroid_buffer
    q = _geometry_quality(['centroid_buffer', 'sum_sqmi'])
    ok = q == 'MED'
    print(f"  [{'PASS' if ok else 'FAIL'}] centroid_buffer/sum_sqmi -> {q} (expected MED)")
    all_pass &= ok

    # LOW quality from radius_proxy only
    q = _geometry_quality(['radius_proxy', 'unknown'])
    ok = q == 'LOW'
    print(f"  [{'PASS' if ok else 'FAIL'}] radius_proxy only -> {q} (expected LOW)")
    all_pass &= ok

    # --- Impact damping: LOW quality should damp core component ---
    cluster_low = [
        _make_event("L1", 35.0, -97.0, max_hail=2.5, swath_area_method='radius_proxy'),
        _make_event("L2", 35.1, -97.1, max_hail=2.5, swath_area_method='radius_proxy'),
    ]
    score_low = _compute_impact_score(cluster_low, severe_core_km2=80.0, duration_min=45.0,
                                      geo_quality='LOW')
    score_med = _compute_impact_score(cluster_low, severe_core_km2=80.0, duration_min=45.0,
                                      geo_quality='MED')
    ok = score_low < score_med
    print(f"  [{'PASS' if ok else 'FAIL'}] LOW quality damps impact: low={score_low} < med={score_med}")
    all_pass &= ok

    # --- MATURE gate: LOW quality + no MRMS should block MATURE ---
    now_str = datetime.now(timezone.utc).isoformat()
    state_low, _ = _compute_lifecycle(5, 1.0, 15.0, 65, now_str, 'ORGANIZING', 0,
                                      geo_quality='LOW', has_mrms_core=False)
    state_med, _ = _compute_lifecycle(5, 1.0, 15.0, 65, now_str, 'ORGANIZING', 0,
                                      geo_quality='MED', has_mrms_core=False)
    ok = state_low != 'MATURE' and state_med == 'MATURE'
    print(f"  [{'PASS' if ok else 'FAIL'}] LOW quality blocks MATURE: low={state_low}, med={state_med}")
    all_pass &= ok

    # --- MATURE gate: LOW quality but has_mrms_core=True should still allow MATURE ---
    state_mrms, _ = _compute_lifecycle(5, 1.0, 15.0, 65, now_str, 'ORGANIZING', 0,
                                       geo_quality='LOW', has_mrms_core=True)
    ok = state_mrms == 'MATURE'
    print(f"  [{'PASS' if ok else 'FAIL'}] LOW quality + MRMS core allows MATURE: {state_mrms}")
    all_pass &= ok

    # --- LOW quality + no MRMS should NOT reach MATURE ---
    state_block, _ = _compute_lifecycle(5, 1.0, 15.0, 65, now_str, 'ORGANIZING', 0,
                                        geo_quality='LOW', has_mrms_core=False)
    ok = state_block != 'MATURE'
    print(f"  [{'PASS' if ok else 'FAIL'}] LOW quality + no MRMS blocks MATURE: {state_block}")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Stable ID
# -----------------------------------------------------------------------

def test_stable_id():
    print("\nCategory: Stable Swath ID")
    all_pass = True

    ev1 = _make_event("EV1", 35.0, -97.0, start_offset_min=0)
    id1 = _generate_stable_swath_id(ev1)
    id2 = _generate_stable_swath_id(ev1)
    ok = id1 == id2 and id1.startswith("SWATH_")
    print(f"  [{'PASS' if ok else 'FAIL'}] Same event -> same stable ID: {id1}")
    all_pass &= ok

    ev2 = _make_event("EV2", 35.1, -97.0, start_offset_min=10)
    id3 = _generate_stable_swath_id(ev2)
    ok = id3 != id1  # Different first event -> different ID
    print(f"  [{'PASS' if ok else 'FAIL'}] Different first event -> different stable ID")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: DB integration with motion coherence
# -----------------------------------------------------------------------

def test_db_integration():
    print("\nCategory: DB Integration")
    all_pass = True

    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    db_path = tmp.name

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE hail_events (
                event_name TEXT,
                center_lat REAL,
                center_lon REAL,
                start_time TEXT,
                end_time TEXT,
                max_hail_size REAL,
                confidence_score REAL,
                swath_polygon TEXT,
                swath_area_sqmi REAL,
                swath_area_km2 REAL,
                swath_area_method TEXT,
                mrms_core_25_km2 REAL DEFAULT 0,
                mrms_core_40_km2 REAL DEFAULT 0,
                status TEXT,
                data_source TEXT
            )
        """)

        n = update_swaths(db_path)
        ok = n == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] Empty DB -> {n} swaths (expected 0)")
        all_pass &= ok

        # Seed 3 nearby CONFIRMED events (use CURRENT_TIMESTAMP format)
        now = datetime.now(timezone.utc)
        for i, (name, lat, lon, offset) in enumerate([
            ("ev1", 35.0, -97.0, 0),
            ("ev2", 35.05, -97.05, 10),
            ("ev3", 35.1, -97.1, 20),
        ]):
            start = (now - timedelta(minutes=30) + timedelta(minutes=offset))
            end = start + timedelta(minutes=10)
            # Use space-separated format to match SQLite CURRENT_TIMESTAMP
            start_str = start.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end.strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                """INSERT INTO hail_events VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, lat, lon, start_str, end_str, 1.5, 50.0, None, 5.0,
                 12.95, 'centroid_buffer', 0, 0, 'CONFIRMED', 'NEXRAD_REALTIME'),
            )
        conn.commit()
        conn.close()

        n = update_swaths(db_path)
        ok = n >= 1
        print(f"  [{'PASS' if ok else 'FAIL'}] 3 nearby CONFIRMED -> {n} swath(s) (expected >=1)")
        all_pass &= ok

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM hail_swaths LIMIT 1").fetchone()
        if row:
            ok_id = row['swath_id'].startswith('SWATH_')
            ok_count = row['confirmed_event_count'] >= 2
            ok_tier = row['impact_tier'] in ('LOW', 'MODERATE', 'HIGH', 'EXTREME')
            ok_state = row['lifecycle_state'] in ('FORMING', 'ORGANIZING', 'MATURE')
            ok_quality = row['geometry_quality'] in ('LOW', 'MED', 'HIGH')
            ok_all = ok_id and ok_count and ok_tier and ok_state and ok_quality
            print(f"  [{'PASS' if ok_all else 'FAIL'}] Swath row: id={row['swath_id'][:30]}... "
                  f"events={row['confirmed_event_count']} tier={row['impact_tier']} "
                  f"state={row['lifecycle_state']} quality={row['geometry_quality']} "
                  f"area_method={row['area_method']}")
            all_pass &= ok_all
        else:
            print(f"  [FAIL] No swath row found in DB")
            all_pass = False
        conn.close()

    finally:
        os.unlink(db_path)

    return all_pass


# -----------------------------------------------------------------------
# Test: ID stability across cycles
# -----------------------------------------------------------------------

def test_id_stability():
    print("\nCategory: ID Stability")
    all_pass = True

    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    db_path = tmp.name

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE hail_events (
                event_name TEXT,
                center_lat REAL,
                center_lon REAL,
                start_time TEXT,
                end_time TEXT,
                max_hail_size REAL,
                confidence_score REAL,
                swath_polygon TEXT,
                swath_area_sqmi REAL,
                swath_area_km2 REAL,
                swath_area_method TEXT,
                mrms_core_25_km2 REAL DEFAULT 0,
                mrms_core_40_km2 REAL DEFAULT 0,
                status TEXT,
                data_source TEXT
            )
        """)

        now = datetime.now(timezone.utc)
        for name, lat, lon, offset in [
            ("S1", 35.0, -97.0, 0),
            ("S2", 35.05, -97.05, 10),
            ("S3", 35.1, -97.1, 20),
        ]:
            start = (now - timedelta(minutes=30) + timedelta(minutes=offset))
            end = start + timedelta(minutes=10)
            start_str = start.strftime('%Y-%m-%d %H:%M:%S')
            end_str = end.strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                """INSERT INTO hail_events VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, lat, lon, start_str, end_str, 1.5, 50.0, None, 5.0,
                 12.95, 'centroid_buffer', 0, 0, 'CONFIRMED', 'NEXRAD_REALTIME'),
            )
        conn.commit()
        conn.close()

        # Run cycle 1
        n1 = update_swaths(db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows1 = conn.execute("SELECT swath_id FROM hail_swaths").fetchall()
        ids1 = set(r['swath_id'] for r in rows1)
        conn.close()

        # Run cycle 2 (same data)
        n2 = update_swaths(db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows2 = conn.execute("SELECT swath_id FROM hail_swaths").fetchall()
        ids2 = set(r['swath_id'] for r in rows2)
        count2 = conn.execute("SELECT COUNT(*) c FROM hail_swaths").fetchone()['c']
        conn.close()

        ok = ids1 == ids2 and count2 == len(ids1)
        print(f"  [{'PASS' if ok else 'FAIL'}] Same data, 2 cycles -> same IDs: "
              f"cycle1={len(ids1)} cycle2={len(ids2)} total_rows={count2}")
        all_pass &= ok

    finally:
        os.unlink(db_path)

    return all_pass


# -----------------------------------------------------------------------
# Test: Motion separation in DB (two storms, opposite directions)
# -----------------------------------------------------------------------

def test_motion_separation_db():
    print("\nCategory: Motion Separation (DB)")
    all_pass = True

    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    db_path = tmp.name

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE hail_events (
                event_name TEXT,
                center_lat REAL,
                center_lon REAL,
                start_time TEXT,
                end_time TEXT,
                max_hail_size REAL,
                confidence_score REAL,
                swath_polygon TEXT,
                swath_area_sqmi REAL,
                swath_area_km2 REAL,
                swath_area_method TEXT,
                mrms_core_25_km2 REAL DEFAULT 0,
                mrms_core_40_km2 REAL DEFAULT 0,
                status TEXT,
                data_source TEXT
            )
        """)

        now = datetime.now(timezone.utc)

        # Storm A: moving east (events A1, A2 spaced eastward)
        # A1: initial position
        a1_start = (now - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        a1_end = (now - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """INSERT INTO hail_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("A1", 35.0, -97.0, a1_start, a1_end, 2.0, 60.0, None, 5.0,
             12.95, 'centroid_buffer', 0, 0, 'CONFIRMED', 'NEXRAD_REALTIME'),
        )
        # A2: ~20km east of A1
        a2_start = (now - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
        a2_end = (now - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """INSERT INTO hail_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("A2", 35.0, -96.8, a2_start, a2_end, 2.0, 60.0, None, 5.0,
             12.95, 'centroid_buffer', 0, 0, 'CONFIRMED', 'NEXRAD_REALTIME'),
        )

        # Storm B: moving north (events B1, B2 spaced northward)
        # B1: same area as A1 but offset north
        b1_start = (now - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        b1_end = (now - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """INSERT INTO hail_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("B1", 35.3, -97.0, b1_start, b1_end, 2.0, 60.0, None, 5.0,
             12.95, 'centroid_buffer', 0, 0, 'CONFIRMED', 'NEXRAD_REALTIME'),
        )
        # B2: ~20km north of B1
        b2_start = (now - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
        b2_end = (now - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """INSERT INTO hail_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("B2", 35.5, -97.0, b2_start, b2_end, 2.0, 60.0, None, 5.0,
             12.95, 'centroid_buffer', 0, 0, 'CONFIRMED', 'NEXRAD_REALTIME'),
        )

        conn.commit()
        conn.close()

        n = update_swaths(db_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        swaths = conn.execute("SELECT * FROM hail_swaths").fetchall()
        n_swaths = len(swaths)

        # Verify: should be 2 swaths (A and B separated by motion)
        ok = n_swaths == 2
        if ok:
            members = []
            for s in swaths:
                m = json.loads(s['member_event_names'])
                members.append(set(m))
            # Check that A events and B events are in different swaths
            a_set = {'A1', 'A2'}
            b_set = {'B1', 'B2'}
            ok = (a_set in members and b_set in members)
            print(f"  [{'PASS' if ok else 'FAIL'}] Two storms, opposite motion -> {n_swaths} swaths, "
                  f"members: {[sorted(m) for m in members]}")
        else:
            print(f"  [{'PASS' if ok else 'FAIL'}] Two storms, opposite motion -> {n_swaths} swaths "
                  f"(expected 2)")
        all_pass &= ok

        conn.close()

    finally:
        os.unlink(db_path)

    return all_pass


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("=== SWATH INTELLIGENCE ENGINE v2 TESTS ===\n")
    all_pass = True

    all_pass &= test_clustering()
    all_pass &= test_impact_scoring()
    all_pass &= test_tiers()
    all_pass &= test_lifecycle()
    all_pass &= test_swath_id()
    all_pass &= test_area_fallback()
    all_pass &= test_motion_coherence()
    all_pass &= test_geometry_quality()
    all_pass &= test_stable_id()
    all_pass &= test_db_integration()
    all_pass &= test_id_stability()
    all_pass &= test_motion_separation_db()

    print()
    if all_pass:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
