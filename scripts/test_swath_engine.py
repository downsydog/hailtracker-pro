#!/usr/bin/env python3
"""
Swath Intelligence Engine unit tests.

Validates clustering, impact scoring, lifecycle transitions, and
end-to-end DB integration.

Run: python scripts/test_swath_engine.py
"""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.swath.intelligence_engine import (
    _cluster_events,
    _compute_area_km2,
    _compute_impact_score,
    _compute_lifecycle,
    _generate_swath_id,
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
    }


# -----------------------------------------------------------------------
# Test: Clustering
# -----------------------------------------------------------------------

def test_clustering():
    print("Category: Clustering")
    all_pass = True

    # 3 events within 40km and 45min -> 1 cluster
    ev1 = _make_event("A", 35.0, -97.0, start_offset_min=0)
    ev2 = _make_event("B", 35.1, -97.1, start_offset_min=10)
    ev3 = _make_event("C", 35.2, -97.0, start_offset_min=20)
    clusters = _cluster_events([ev1, ev2, ev3])
    ok = len(clusters) == 1 and len(clusters[0]) == 3
    print(f"  [{'PASS' if ok else 'FAIL'}] 3 nearby events -> 1 cluster of 3")
    all_pass &= ok

    # 1 event >40km from all others -> separate cluster (filtered by min threshold)
    ev_far = _make_event("D", 35.8, -97.0, start_offset_min=5)  # ~89km from A, ~67km from C
    dist_from_nearest = _haversine_km(35.2, -97.0, 35.8, -97.0)
    clusters = _cluster_events([ev1, ev2, ev3, ev_far])
    # ev_far should be in its own cluster, but single-event clusters are filtered
    cluster_sizes = [len(c) for c in clusters]
    ok = 3 in cluster_sizes and 1 not in cluster_sizes
    print(f"  [{'PASS' if ok else 'FAIL'}] Far event ({dist_from_nearest:.0f}km from nearest) -> excluded (single-event filtered)")
    all_pass &= ok

    # 1 event 60min gap -> separate cluster
    ev_late = _make_event("E", 35.05, -97.05, start_offset_min=80)
    ev_late2 = _make_event("F", 35.06, -97.06, start_offset_min=85)
    clusters = _cluster_events([ev1, ev2, ev3, ev_late, ev_late2])
    ok = len(clusters) == 2
    print(f"  [{'PASS' if ok else 'FAIL'}] 60min gap -> 2 separate clusters")
    all_pass &= ok

    # Single event filtered out
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

    # All events >= 2.0" hail
    cluster_severe = [
        _make_event("S1", 35.0, -97.0, max_hail=2.5),
        _make_event("S2", 35.1, -97.1, max_hail=3.0),
        _make_event("S3", 35.2, -97.0, max_hail=2.0),
    ]
    score = _compute_impact_score(cluster_severe, severe_core_km2=50.0, duration_min=45.0)
    # 30 pts (100% >= 2.0") + 20 pts (100% >= 1.5") + 10 pts (50/100 core)
    # + 7.5 pts (45/60 dur) + 10 pts (urban 0.5) = ~77-78
    ok = score >= 70
    print(f"  [{'PASS' if ok else 'FAIL'}] All severe hail -> score={score} (expected >=70)")
    all_pass &= ok

    # Mixed hail sizes
    cluster_mixed = [
        _make_event("M1", 35.0, -97.0, max_hail=2.5),
        _make_event("M2", 35.1, -97.1, max_hail=1.0),
        _make_event("M3", 35.2, -97.0, max_hail=0.5),
    ]
    score = _compute_impact_score(cluster_mixed, severe_core_km2=10.0, duration_min=30.0)
    ok = 20 <= score <= 50
    print(f"  [{'PASS' if ok else 'FAIL'}] Mixed hail -> score={score} (expected 20-50)")
    all_pass &= ok

    # No severe hail, small core
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

    # Single event -> FORMING
    state, dc = _compute_lifecycle(1, 0.0, 0.0, 20, now_str, None, 0)
    ok = state == 'FORMING'
    print(f"  [{'PASS' if ok else 'FAIL'}] Single event -> {state} (expected FORMING)")
    all_pass &= ok

    # 2 events + positive growth -> ORGANIZING
    state, dc = _compute_lifecycle(2, 0.5, 5.0, 40, now_str, 'FORMING', 0)
    ok = state == 'ORGANIZING'
    print(f"  [{'PASS' if ok else 'FAIL'}] 2 events + growth -> {state} (expected ORGANIZING)")
    all_pass &= ok

    # Large core + high impact -> MATURE
    state, dc = _compute_lifecycle(5, 1.0, 15.0, 65, now_str, 'ORGANIZING', 0)
    ok = state == 'MATURE'
    print(f"  [{'PASS' if ok else 'FAIL'}] Core>=10 + impact>=60 -> {state} (expected MATURE)")
    all_pass &= ok

    # MATURE + 2 consecutive negative growth -> DECAYING
    state, dc = _compute_lifecycle(5, -0.5, 12.0, 55, now_str, 'MATURE', 1)
    ok = state == 'DECAYING' and dc == 2
    print(f"  [{'PASS' if ok else 'FAIL'}] MATURE + 2nd neg growth -> {state} dc={dc} (expected DECAYING, 2)")
    all_pass &= ok

    # Old last_seen -> EXPIRED
    state, dc = _compute_lifecycle(3, 0.0, 10.0, 50, old_str, 'ORGANIZING', 0)
    ok = state == 'EXPIRED'
    print(f"  [{'PASS' if ok else 'FAIL'}] 60min old -> {state} (expected EXPIRED)")
    all_pass &= ok

    # EXPIRED is terminal
    state, dc = _compute_lifecycle(5, 1.0, 20.0, 80, now_str, 'EXPIRED', 0)
    ok = state == 'EXPIRED'
    print(f"  [{'PASS' if ok else 'FAIL'}] EXPIRED stays EXPIRED -> {state}")
    all_pass &= ok

    # MATURE never downgrades to ORGANIZING (even with low impact/core)
    state, dc = _compute_lifecycle(3, 0.1, 5.0, 30, now_str, 'MATURE', 0)
    ok = state == 'MATURE'
    print(f"  [{'PASS' if ok else 'FAIL'}] MATURE stays MATURE (no downgrade) -> {state}")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Swath ID determinism
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

    # No polygons, but swath_area_sqmi present -> sum_sqmi method
    cluster_sqmi = [
        _make_event("A1", 35.0, -97.0, swath_area_sqmi=10.0, swath_polygon=None),
        _make_event("A2", 35.1, -97.1, swath_area_sqmi=8.0, swath_polygon=None),
    ]
    geojsons = [ev['swath_polygon'] for ev in cluster_sqmi]
    area, geom, method = _compute_area_km2(geojsons, 35.05, cluster=cluster_sqmi)
    ok = method == 'sum_sqmi' and abs(area - (18.0 * 2.59)) < 0.01 and geom is None
    print(f"  [{'PASS' if ok else 'FAIL'}] No polygons + sqmi -> method={method} area={area:.2f} (expected sum_sqmi, {18.0*2.59:.2f})")
    all_pass &= ok

    # No polygons, no swath_area_sqmi -> radius_proxy method
    cluster_noarea = [
        _make_event("B1", 35.0, -97.0, swath_area_sqmi=0.0, swath_polygon=None),
        _make_event("B2", 35.2, -97.0, swath_area_sqmi=0.0, swath_polygon=None),
    ]
    geojsons = [ev['swath_polygon'] for ev in cluster_noarea]
    area, geom, method = _compute_area_km2(geojsons, 35.1, cluster=cluster_noarea)
    # radius_proxy: centroid of (35.0,-97.0) and (35.2,-97.0) is (35.1,-97.0)
    # max_r = haversine(35.1,-97.0, 35.2,-97.0) ~= 11.1km
    # area = pi * 11.1^2 ~= 387
    ok = method == 'radius_proxy' and area > 100 and geom is None
    print(f"  [{'PASS' if ok else 'FAIL'}] No polygons + no sqmi -> method={method} area={area:.1f} (expected radius_proxy, >100)")
    all_pass &= ok

    # Radius proxy minimum radius is 3km
    cluster_tight = [
        _make_event("C1", 35.0, -97.0, swath_area_sqmi=0.0, swath_polygon=None),
        _make_event("C2", 35.001, -97.001, swath_area_sqmi=0.0, swath_polygon=None),
    ]
    geojsons = [ev['swath_polygon'] for ev in cluster_tight]
    area, geom, method = _compute_area_km2(geojsons, 35.0, cluster=cluster_tight)
    # Very close events -> radius_proxy with min r=3km -> pi*9 ~= 28.3
    import math
    expected_min = math.pi * 3.0 ** 2
    ok = method == 'radius_proxy' and abs(area - expected_min) < 1.0
    print(f"  [{'PASS' if ok else 'FAIL'}] Tight cluster -> radius_proxy min radius: area={area:.1f} (expected ~{expected_min:.1f})")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: DB integration
# -----------------------------------------------------------------------

def test_db_integration():
    print("\nCategory: DB Integration")
    all_pass = True

    # Create temp DB
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    db_path = tmp.name

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")

        # Create hail_events table (minimal for swath engine)
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
                status TEXT,
                data_source TEXT
            )
        """)

        # Empty DB -> 0 swaths
        n = update_swaths(db_path)
        ok = n == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] Empty DB -> {n} swaths (expected 0)")
        all_pass &= ok

        # Seed 3 nearby CONFIRMED events (recent timestamps to avoid EXPIRED)
        base = datetime.now(timezone.utc) - timedelta(minutes=15)
        for i, (name, lat, lon, offset) in enumerate([
            ("ev1", 35.0, -97.0, 0),
            ("ev2", 35.05, -97.05, 10),
            ("ev3", 35.1, -97.1, 20),
        ]):
            start = (base + timedelta(minutes=offset)).isoformat()
            end = (base + timedelta(minutes=offset + 10)).isoformat()
            conn.execute(
                "INSERT INTO hail_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (name, lat, lon, start, end, 1.5, 50.0, None, 5.0,
                 'CONFIRMED', 'NEXRAD_REALTIME'),
            )
        conn.commit()
        conn.close()

        # Run swath engine
        n = update_swaths(db_path)
        ok = n == 1
        print(f"  [{'PASS' if ok else 'FAIL'}] 3 nearby CONFIRMED -> {n} swath (expected 1)")
        all_pass &= ok

        # Verify swath contents
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM hail_swaths LIMIT 1").fetchone()
        if row:
            ok_id = row['swath_id'].startswith('SWATH_')
            ok_count = row['confirmed_event_count'] == 3
            ok_tier = row['impact_tier'] in ('LOW', 'MODERATE', 'HIGH', 'EXTREME')
            ok_state = row['lifecycle_state'] in ('FORMING', 'ORGANIZING', 'MATURE')
            ok_area_method = row['area_method'] in ('polygon_union', 'sum_sqmi', 'radius_proxy')
            ok_area = row['area_km2'] > 0
            ok_all = ok_id and ok_count and ok_tier and ok_state and ok_area_method and ok_area
            print(f"  [{'PASS' if ok_all else 'FAIL'}] Swath row: id={row['swath_id'][:30]}... "
                  f"events={row['confirmed_event_count']} tier={row['impact_tier']} "
                  f"state={row['lifecycle_state']} impact={row['impact_score']} "
                  f"area={row['area_km2']:.1f} method={row['area_method']}")
            all_pass &= ok_all
        else:
            print(f"  [FAIL] No swath row found in DB")
            all_pass = False

        conn.close()

    finally:
        os.unlink(db_path)

    return all_pass


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("=== SWATH INTELLIGENCE ENGINE TESTS ===\n")
    all_pass = True

    all_pass &= test_clustering()
    all_pass &= test_impact_scoring()
    all_pass &= test_tiers()
    all_pass &= test_lifecycle()
    all_pass &= test_swath_id()
    all_pass &= test_area_fallback()
    all_pass &= test_db_integration()

    print()
    if all_pass:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
