#!/usr/bin/env python3
"""
Dev validation script for the hail tracking pipeline.

Exercises:
  a) Reset tracker
  b) Simulate a storm
  c) Verify /active and /swaths return data
  d) Verify miss-tolerance (cell survives missed scans)

Can run standalone (direct imports) or against a live server (HTTP).

Usage:
    python scripts/dev_run_hail_pipeline.py           # direct mode
    python scripts/dev_run_hail_pipeline.py --http     # HTTP mode (server must be running)
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_direct():
    """Run pipeline using direct Python imports (no server needed)."""
    from src.radar.storm_cell_tracker import StormCellTracker

    print("=" * 60)
    print("HAIL PIPELINE VALIDATION (direct mode)")
    print("=" * 60)

    # --- Step a: Reset tracker ---
    print("\n[a] Creating fresh tracker...")
    tracker = StormCellTracker(simulation_mode=True)
    assert len(tracker.active_cells) == 0
    print("    OK: Tracker reset, 0 active cells")

    # --- Step b: Simulate a storm (seeded for determinism) ---
    SEED = 42
    print(f"\n[b] Simulating storm (Dallas -> NE, 60 min, 65 dBZ peak, seed={SEED})...")
    cells = tracker.process_simulated_storm(
        start_lat=32.7,
        start_lon=-96.8,
        direction_deg=45,
        speed_kmh=50,
        duration_minutes=60,
        peak_reflectivity=65,
        seed=SEED,
    )
    print(f"    Created {len(cells)} cell observations")
    assert len(cells) > 0, "Expected at least 1 cell"

    # --- Step c: Verify active cells ---
    print("\n[c] Checking active cells...")
    active = tracker.active_cells
    print(f"    Active cells: {len(active)}")
    for cid, cell in active.items():
        print(f"      Cell #{cid}: ({cell.centroid_lat:.3f}, {cell.centroid_lon:.3f}) "
              f"ref={cell.max_reflectivity:.1f} dBZ, MESH={cell.mesh_inches:.2f}\", "
              f"stage={cell.stage}, missed={tracker.missed_scans.get(cid, 0)}, "
              f"radar_id={cell.radar_id}")
        assert cell.radar_id == 'SIM', f"Expected radar_id='SIM', got {cell.radar_id!r}"
    assert len(active) > 0, "Expected at least 1 active cell"

    # --- Step c2: Verify swaths ---
    print("\n    Checking swaths...")
    swaths = tracker.create_all_track_swaths(min_duration_minutes=5)
    print(f"    Swaths generated: {len(swaths)}")
    for s in swaths:
        props = s['properties']
        print(f"      Cell #{props['cell_id']}: {props['track_length_km']:.1f} km, "
              f"MESH max={props['max_mesh_inches']:.2f}\", "
              f"width={props.get('width_min_km', '?')}-{props.get('width_max_km', '?')} km, "
              f"area={props['area_sq_miles']:.1f} sq mi, "
              f"radar_id={props.get('radar_id')}, "
              f"swath_quality={props.get('swath_quality_score')}")
        assert props.get('radar_id') == 'SIM', f"Expected swath radar_id='SIM', got {props.get('radar_id')!r}"
        assert 0 <= props['swath_quality_score'] <= 100, f"Bad swath quality: {props['swath_quality_score']}"
        assert isinstance(props['swath_quality_reasons'], list)
    assert len(swaths) > 0, "Expected at least 1 swath"

    # --- Step c3: Verify storm events ---
    print("\n    Checking events...")
    events = tracker.get_events(lookback_minutes=180, join_distance_km=25.0)
    print(f"    Events: {len(events)}")
    assert len(events) > 0, "Expected at least 1 event"
    for ev in events:
        print(f"      Event {ev.event_id}: cells={ev.cell_ids}, "
              f"severity={ev.severity}, confidence={ev.confidence}, "
              f"MESH={ev.max_mesh_inches}\", ref={ev.max_reflectivity} dBZ, "
              f"radar_ids={ev.radar_ids}, "
              f"status={ev.status}, phase={ev.phase}, "
              f"impact_window={ev.impact_window_minutes}min, "
              f"quality={ev.event_quality_score}")
        print(f"        reasons: {ev.event_quality_reasons}")
        assert ev.severity in ('light', 'moderate', 'severe'), f"Bad severity: {ev.severity}"
        assert 0.4 <= ev.confidence <= 0.95, f"Bad confidence: {ev.confidence}"
        assert 1 in ev.cell_ids, "Simulated cell #1 should be in event"
        assert ev.status in ('ACTIVE', 'DISSIPATING', 'EXPIRED'), f"Bad status: {ev.status}"
        assert ev.phase in ('DEVELOPING', 'IMPACTING', 'WEAKENING', 'NONE'), f"Bad phase: {ev.phase}"
        assert isinstance(ev.impact_window_minutes, int) and ev.impact_window_minutes >= 0
        assert 0 <= ev.event_quality_score <= 100, f"Bad quality: {ev.event_quality_score}"
        assert isinstance(ev.event_quality_reasons, list) and len(ev.event_quality_reasons) > 0
    has_active = any(ev.status == 'ACTIVE' for ev in events)
    assert has_active, "Expected at least 1 ACTIVE event from seeded simulation"

    # --- Step c4: Verify merged event swath ---
    print("\n    Checking merged event swath...")
    ev0 = events[0]
    merged = tracker.create_event_merged_swath(ev0.event_id, buffer_km=3.0)
    assert merged is not None, "Expected merged swath for event"
    assert merged['type'] == 'Polygon', f"Expected Polygon, got {merged['type']}"
    assert len(merged['coordinates']) > 0, "Expected coordinates"
    assert len(merged['coordinates'][0]) >= 4, "Polygon ring too short"
    props = merged['properties']
    assert props['event_id'] == ev0.event_id
    assert props['swaths_merged'] >= 1
    assert props['method'] in ('shapely_union', 'convex_hull_fallback')
    assert sorted(props['cell_ids']) == sorted(ev0.cell_ids)
    assert 0 <= props['swath_quality_score'] <= 100
    assert isinstance(props['swath_quality_reasons'], list)
    assert 0 <= props['event_quality_score'] <= 100
    print(f"      Event {ev0.event_id}: method={props['method']}, "
          f"swaths_merged={props['swaths_merged']}, "
          f"vertices={len(merged['coordinates'][0])}, "
          f"swath_quality={props['swath_quality_score']}, "
          f"event_quality={props['event_quality_score']}")
    print("    OK: Merged swath verified")

    # --- Step c5: Verify active event feed ---
    print("\n    Checking active event feed...")
    feed = tracker.get_active_event_features(lookback_minutes=180, join_distance_km=25.0, limit=10, buffer_km=3.0)
    print(f"    Active event features: {len(feed)}")
    assert len(feed) >= 1, "Expected at least 1 active event feature"
    for i, feat in enumerate(feed):
        assert feat['type'] == 'Feature', f"Expected Feature, got {feat['type']}"
        assert feat['geometry']['type'] == 'Polygon', "Expected Polygon geometry"
        ring = feat['geometry']['coordinates'][0]
        assert len(ring) >= 4, f"Polygon ring too short: {len(ring)}"
        assert ring[0] == ring[-1] or (abs(ring[0][0]-ring[-1][0])<1e-9 and abs(ring[0][1]-ring[-1][1])<1e-9), "Ring not closed"
        p = feat['properties']
        assert 'event_id' in p
        assert p['status'] in ('ACTIVE', 'DISSIPATING'), f"Feed should exclude EXPIRED, got {p['status']}"
        assert p['phase'] in ('DEVELOPING', 'IMPACTING', 'WEAKENING', 'NONE')
        assert 0 <= p['event_quality_score'] <= 100
        assert 0 <= p['swath_quality_score'] <= 100
        assert isinstance(p['swath_quality_reasons'], list)
        assert p['method'] in ('shapely_union', 'convex_hull_fallback', 'cell_fallback')
        print(f"      #{i+1}: event_id={p['event_id']}, "
              f"eq={p['event_quality_score']}, sq={p['swath_quality_score']}, "
              f"status={p['status']}, phase={p['phase']}, "
              f"method={p['method']}, "
              f"MESH={p['max_mesh_inches']}\", track={p['track_length_km']}km")
    # Verify sorted by quality desc
    if len(feed) >= 2:
        for i in range(len(feed) - 1):
            assert feed[i]['properties']['event_quality_score'] >= feed[i+1]['properties']['event_quality_score'], \
                "Feed should be sorted by event_quality_score desc"
    print("    OK: Active event feed verified")

    # --- Step d: Miss-tolerance test ---
    print("\n[d] Testing miss-tolerance...")
    tracker2 = StormCellTracker(simulation_mode=True)
    base_time = datetime(2025, 6, 15, 18, 0, 0)

    # Scan 1: introduce a cell
    det1 = [{'lat': 35.0, 'lon': -97.0, 'reflectivity': 60, 'mesh_mm': 30, 'area_km2': 80}]
    cells1 = tracker2.process_radar_scan(det1, base_time)
    assert len(cells1) == 1
    cell_id = cells1[0].id
    print(f"    Scan 1: Cell #{cell_id} created, stage={cells1[0].stage}")

    # Scan 2: same cell, moved slightly
    det2 = [{'lat': 35.02, 'lon': -96.98, 'reflectivity': 62, 'mesh_mm': 35, 'area_km2': 85}]
    cells2 = tracker2.process_radar_scan(det2, base_time + timedelta(minutes=5))
    matched_ids = {c.id for c in cells2}
    assert cell_id in matched_ids, f"Cell #{cell_id} should still be tracked"
    print(f"    Scan 2: Cell #{cell_id} matched, missed_scans={tracker2.missed_scans.get(cell_id, 0)}")

    # Scan 3: EMPTY (cell missed)
    cells3 = tracker2.process_radar_scan([], base_time + timedelta(minutes=10))
    assert cell_id in tracker2.active_cells, "Cell should survive 1 missed scan"
    assert tracker2.missed_scans.get(cell_id, 0) == 1
    assert tracker2.active_cells[cell_id].stage == 'DISSIPATION'
    print(f"    Scan 3: EMPTY — Cell #{cell_id} survived, "
          f"missed_scans={tracker2.missed_scans[cell_id]}, stage=DISSIPATION")

    # Scan 4: EMPTY again (cell missed 2nd time)
    cells4 = tracker2.process_radar_scan([], base_time + timedelta(minutes=15))
    assert cell_id in tracker2.active_cells, "Cell should survive 2 missed scans"
    assert tracker2.missed_scans.get(cell_id, 0) == 2
    print(f"    Scan 4: EMPTY — Cell #{cell_id} survived, "
          f"missed_scans={tracker2.missed_scans[cell_id]}")

    # Scan 5: Cell reappears!
    det5 = [{'lat': 35.06, 'lon': -96.94, 'reflectivity': 58, 'mesh_mm': 28, 'area_km2': 75}]
    cells5 = tracker2.process_radar_scan(det5, base_time + timedelta(minutes=20))
    rematched_ids = {c.id for c in cells5}
    assert cell_id in rematched_ids, f"Cell #{cell_id} should re-match after missed scans"
    assert tracker2.missed_scans.get(cell_id, 0) == 0, "missed_scans should reset to 0"
    print(f"    Scan 5: Cell #{cell_id} RE-MATCHED, missed_scans reset to 0, "
          f"stage={tracker2.active_cells[cell_id].stage}")

    # Scan 6-8: Three consecutive misses → cell should be terminated
    for i in range(3):
        tracker2.process_radar_scan([], base_time + timedelta(minutes=25 + i * 5))
    assert cell_id not in tracker2.active_cells, "Cell should be terminated after 3 misses"
    assert cell_id in tracker2.terminated_cells, "Cell should be in terminated_cells"
    print(f"    Scan 6-8: 3 consecutive misses — Cell #{cell_id} TERMINATED")

    # --- Step e: Persistence round-trip ---
    print("\n[e] Testing state persistence...")
    import tempfile
    tmp_path = os.path.join(tempfile.gettempdir(), 'tracker_state_test.json')

    # Use the first tracker (has 1 active cell from simulation)
    tracker.save_state(tmp_path)
    print(f"    Saved state to {tmp_path}")

    loaded = StormCellTracker.load_state(tmp_path, simulation_mode=True)
    assert loaded.next_cell_id == tracker.next_cell_id, "next_cell_id mismatch"
    assert set(loaded.active_cells.keys()) == set(tracker.active_cells.keys()), "active_cells keys mismatch"
    for cid in tracker.active_cells:
        orig = tracker.active_cells[cid]
        rest = loaded.active_cells[cid]
        assert rest.id == orig.id
        assert rest.radar_id == orig.radar_id, f"radar_id mismatch: {rest.radar_id} != {orig.radar_id}"
        assert rest.stage == orig.stage
        assert abs(rest.centroid_lat - orig.centroid_lat) < 1e-6
    assert loaded.missed_scans == tracker.missed_scans, "missed_scans mismatch"
    assert len(loaded.cells_history) == len(tracker.cells_history), "cells_history length mismatch"
    print(f"    Loaded state: {len(loaded.active_cells)} active, "
          f"next_id={loaded.next_cell_id}, history={len(loaded.cells_history)}")
    print("    OK: Round-trip persistence verified")

    # Cleanup
    os.remove(tmp_path)

    # --- Step f: Determinism proof ---
    print("\n[f] Testing determinism (same seed -> same output)...")
    from datetime import datetime as dt
    fixed_start = datetime(2025, 6, 15, 18, 0, 0)
    sim_kwargs = dict(
        start_lat=32.7, start_lon=-96.8, direction_deg=45,
        speed_kmh=50, duration_minutes=60, peak_reflectivity=65,
        start_time=fixed_start, seed=SEED,
    )

    t1 = StormCellTracker(simulation_mode=True)
    cells1 = t1.process_simulated_storm(**sim_kwargs)

    t2 = StormCellTracker(simulation_mode=True)
    cells2 = t2.process_simulated_storm(**sim_kwargs)

    assert len(cells1) == len(cells2), f"Cell count mismatch: {len(cells1)} vs {len(cells2)}"
    for c1, c2 in zip(cells1, cells2):
        assert c1.centroid_lat == c2.centroid_lat, f"Lat mismatch: {c1.centroid_lat} vs {c2.centroid_lat}"
        assert c1.centroid_lon == c2.centroid_lon, f"Lon mismatch"
        assert c1.max_reflectivity == c2.max_reflectivity, f"Ref mismatch"
        assert c1.mesh_mm == c2.mesh_mm, f"MESH mismatch"

    ev1 = t1.get_events()
    ev2 = t2.get_events()
    assert len(ev1) == len(ev2), "Event count mismatch"
    assert ev1[0].event_id == ev2[0].event_id, f"Event ID flap: {ev1[0].event_id} vs {ev2[0].event_id}"
    assert ev1[0].severity == ev2[0].severity, f"Severity flap: {ev1[0].severity} vs {ev2[0].severity}"
    assert ev1[0].confidence == ev2[0].confidence, f"Confidence flap"
    assert ev1[0].cell_ids == ev2[0].cell_ids, f"Cell IDs flap"
    print(f"    Run 1: {len(cells1)} cells, event_id={ev1[0].event_id}, severity={ev1[0].severity}, conf={ev1[0].confidence}")
    print(f"    Run 2: {len(cells2)} cells, event_id={ev2[0].event_id}, severity={ev2[0].severity}, conf={ev2[0].confidence}")
    print("    OK: Deterministic -- both runs identical (including event_id)")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED")
    print("=" * 60)


def run_http(base_url: str):
    """Run pipeline against a live server via HTTP."""
    import urllib.request

    def api(method, path, data=None):
        url = f"{base_url}{path}"
        body = json.dumps(data).encode() if data else None
        headers = {'Content-Type': 'application/json'} if data else {}
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
            return None

    print("=" * 60)
    print(f"HAIL PIPELINE VALIDATION (HTTP mode: {base_url})")
    print("=" * 60)

    # a) Reset
    print("\n[a] Resetting tracker...")
    r = api('POST', '/api/storm-cells/reset')
    print(f"    {r}")

    # b) Simulate
    print("\n[b] Simulating storm...")
    r = api('POST', '/api/storm-cells/simulate', {
        'start_lat': 32.7, 'start_lon': -96.8,
        'direction': 45, 'speed': 50,
        'duration': 60, 'peak_reflectivity': 65,
    })
    if r:
        print(f"    cells_created={r.get('cells_created')}, "
              f"tracks={r.get('tracks')}, "
              f"swath_count={len(r.get('swaths', {}).get('features', []))}")

    # c) Fetch active
    print("\n[c] Fetching /active...")
    r = api('GET', '/api/storm-cells/active')
    if r:
        print(f"    active_cells: {r.get('count', 0)}")
        for c in r.get('active_cells', [])[:5]:
            print(f"      Cell #{c.get('cell_id')}: "
                  f"({c.get('lat'):.3f}, {c.get('lon'):.3f}) "
                  f"ref={c.get('max_reflectivity')} dBZ, "
                  f"MESH={c.get('mesh_inches')}\"")

    # c2) Fetch swaths
    print("\n    Fetching /swaths...")
    r = api('GET', '/api/storm-cells/swaths?min_duration=5')
    if r:
        features = r.get('features', [])
        print(f"    swaths: {len(features)}")
        for f in features[:5]:
            p = f.get('properties', {})
            print(f"      Cell #{p.get('cell_id')}: {p.get('track_length_km')} km, "
                  f"MESH max={p.get('max_mesh_inches')}\", "
                  f"area={p.get('area_sq_miles')} sq mi")

    print("\n" + "=" * 60)
    print("DONE (check output above for errors)")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Dev hail pipeline validation')
    parser.add_argument('--http', action='store_true', help='Use HTTP mode (server must be running)')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL for HTTP mode')
    args = parser.parse_args()

    if args.http:
        run_http(args.url)
    else:
        run_direct()
