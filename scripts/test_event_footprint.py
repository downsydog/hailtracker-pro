#!/usr/bin/env python3
"""
Event Footprint unit tests.

Validates polygon construction, MRMS core extraction, DB enrichment,
and performance guardrails.

Run: python scripts/test_event_footprint.py
"""

import json
import math
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.radar.event_footprint import (
    build_event_polygon,
    extract_mrms_cores,
    update_event_footprints,
    _haversine_km,
    _create_circle_coords,
    _polygon_area_km2,
)


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _make_cell(
    lat: float, lon: float,
    area_km2: float = 10.0,
    mesh_mm: float = 25.0,
    prev_positions: list = None,
) -> dict:
    """Create a synthetic cell dict for testing."""
    return {
        'centroid_lat': lat,
        'centroid_lon': lon,
        'area_km2': area_km2,
        'mesh_mm': mesh_mm,
        'previous_positions': prev_positions or [],
    }


class FakeMRMSCache:
    """Synthetic MRMS cache with a gaussian-like MESH blob for testing."""

    def __init__(self, center_lat=35.0, center_lon=-97.0, peak_mm=50.0,
                 grid_size=20, step=0.1):
        import numpy as np
        self.is_loaded = True

        lats = np.linspace(center_lat - step * grid_size / 2,
                           center_lat + step * grid_size / 2,
                           grid_size)
        lons = np.linspace(center_lon - step * grid_size / 2,
                           center_lon + step * grid_size / 2,
                           grid_size)

        mesh = np.zeros((grid_size, grid_size), dtype=np.float32)
        cx, cy = grid_size // 2, grid_size // 2
        for i in range(grid_size):
            for j in range(grid_size):
                dist = math.sqrt((i - cx) ** 2 + (j - cy) ** 2)
                mesh[i, j] = peak_mm * math.exp(-0.5 * (dist / 3) ** 2)

        self._grid = {
            'lats': lats,
            'lons': lons,
            'mesh_mm': mesh,
            'source_time': datetime.now(timezone.utc).isoformat(),
            'provider': 'test_synthetic',
        }


# -----------------------------------------------------------------------
# Test: Multi-cell union
# -----------------------------------------------------------------------

def test_multi_cell_union():
    print("Category: Multi-cell Union")
    all_pass = True

    cells = [
        _make_cell(35.0, -97.0, area_km2=15.0, mesh_mm=30.0,
                   prev_positions=[(35.01, -97.01), (35.02, -97.02)]),
        _make_cell(35.05, -97.05, area_km2=12.0, mesh_mm=25.0,
                   prev_positions=[(35.06, -97.06)]),
        _make_cell(35.1, -97.0, area_km2=10.0, mesh_mm=20.0,
                   prev_positions=[(35.11, -97.01), (35.12, -97.0)]),
    ]

    geojson_str, area_km2, method = build_event_polygon(cells)

    ok = geojson_str is not None
    print(f"  [{'PASS' if ok else 'FAIL'}] GeoJSON not None")
    all_pass &= ok

    if geojson_str:
        geoj = json.loads(geojson_str)
        ok = geoj.get('type') in ('Polygon', 'MultiPolygon')
        print(f"  [{'PASS' if ok else 'FAIL'}] Type is Polygon: {geoj.get('type')}")
        all_pass &= ok

    ok = area_km2 > 0
    print(f"  [{'PASS' if ok else 'FAIL'}] Area > 0: {area_km2:.1f} km2")
    all_pass &= ok

    ok = method in ('cell_union', 'convex_hull')
    print(f"  [{'PASS' if ok else 'FAIL'}] Method: {method}")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Single-cell centroid buffer
# -----------------------------------------------------------------------

def test_single_cell_buffer():
    print("\nCategory: Single-cell Centroid Buffer")
    all_pass = True

    cells = [_make_cell(35.0, -97.0, area_km2=20.0, mesh_mm=10.0)]

    geojson_str, area_km2, method = build_event_polygon(cells)

    ok = geojson_str is not None
    print(f"  [{'PASS' if ok else 'FAIL'}] GeoJSON not None")
    all_pass &= ok

    # area_km2 = 20 -> radius = sqrt(20/pi) ~ 2.52 km
    # buffer area = pi * 2.52^2 ~ 20 km2
    min_area = math.pi * 2.0 ** 2  # minimum radius is 2km
    ok = area_km2 >= min_area
    print(f"  [{'PASS' if ok else 'FAIL'}] Area >= pi*2^2 ({min_area:.1f}): {area_km2:.1f} km2")
    all_pass &= ok

    ok = method == 'centroid_buffer'
    print(f"  [{'PASS' if ok else 'FAIL'}] Method: {method} (expected centroid_buffer)")
    all_pass &= ok

    if geojson_str:
        geoj = json.loads(geojson_str)
        ok = geoj.get('type') == 'Polygon'
        print(f"  [{'PASS' if ok else 'FAIL'}] Type is Polygon")
        all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: MRMS core nesting
# -----------------------------------------------------------------------

def test_mrms_core_nesting():
    print("\nCategory: MRMS Core Nesting")
    all_pass = True

    try:
        import numpy as np
    except ImportError:
        print("  [SKIP] numpy not available")
        return True

    cache = FakeMRMSCache(center_lat=35.0, center_lon=-97.0, peak_mm=50.0,
                         grid_size=40, step=0.05)

    bbox = {
        'bbox_min_lat': 34.0,
        'bbox_max_lat': 36.0,
        'bbox_min_lon': -98.0,
        'bbox_max_lon': -96.0,
    }

    result = extract_mrms_cores(cache, bbox, thresholds_mm=[15, 25, 40])

    ok = result.get('method') == 'mrms_contour'
    print(f"  [{'PASS' if ok else 'FAIL'}] Method: {result.get('method')} (expected mrms_contour)")
    all_pass &= ok

    a15 = result.get('core_15', {}).get('area_km2', 0)
    a25 = result.get('core_25', {}).get('area_km2', 0)
    a40 = result.get('core_40', {}).get('area_km2', 0)

    print(f"  Core areas: 15mm={a15:.1f} 25mm={a25:.1f} 40mm={a40:.1f} km2")

    # All should have some area (gaussian peaks at 50mm)
    ok = a15 > 0
    print(f"  [{'PASS' if ok else 'FAIL'}] 15mm core area > 0")
    all_pass &= ok

    ok = a25 > 0
    print(f"  [{'PASS' if ok else 'FAIL'}] 25mm core area > 0")
    all_pass &= ok

    # Nesting: 40mm <= 25mm <= 15mm
    ok = a40 <= a25 + 0.1  # small epsilon for rounding
    print(f"  [{'PASS' if ok else 'FAIL'}] Nesting: area_40 ({a40:.1f}) <= area_25 ({a25:.1f})")
    all_pass &= ok

    ok = a25 <= a15 + 0.1
    print(f"  [{'PASS' if ok else 'FAIL'}] Nesting: area_25 ({a25:.1f}) <= area_15 ({a15:.1f})")
    all_pass &= ok

    # Check GeoJSON is valid
    for t in [15, 25, 40]:
        key = f'core_{t}'
        gj = result.get(key, {}).get('geojson')
        if gj:
            parsed = json.loads(gj)
            ok = parsed.get('type') in ('Polygon', 'MultiPolygon')
            print(f"  [{'PASS' if ok else 'FAIL'}] core_{t} GeoJSON type: {parsed.get('type')}")
            all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: MRMS unavailable
# -----------------------------------------------------------------------

def test_mrms_unavailable():
    print("\nCategory: MRMS Unavailable")
    all_pass = True

    bbox = {
        'bbox_min_lat': 34.0, 'bbox_max_lat': 36.0,
        'bbox_min_lon': -98.0, 'bbox_max_lon': -96.0,
    }

    # None cache
    result = extract_mrms_cores(None, bbox)
    ok = result.get('method') == 'unavailable'
    print(f"  [{'PASS' if ok else 'FAIL'}] None cache -> method={result.get('method')}")
    all_pass &= ok

    # Unloaded cache
    class EmptyCache:
        is_loaded = False
        _grid = None

    result = extract_mrms_cores(EmptyCache(), bbox)
    ok = result.get('method') == 'unavailable'
    print(f"  [{'PASS' if ok else 'FAIL'}] Unloaded cache -> method={result.get('method')}")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: DB enrichment
# -----------------------------------------------------------------------

def test_db_enrichment():
    print("\nCategory: DB Enrichment")
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
                swath_method TEXT,
                status TEXT,
                data_source TEXT,
                bbox_min_lat REAL,
                bbox_max_lat REAL,
                bbox_min_lon REAL,
                bbox_max_lon REAL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed 5 centroid_point events
        base = datetime.now(timezone.utc) - timedelta(minutes=10)
        for i in range(5):
            lat = 35.0 + i * 0.05
            lon = -97.0 - i * 0.05
            start = (base + timedelta(minutes=i * 5)).isoformat()
            end = (base + timedelta(minutes=i * 5 + 10)).isoformat()
            point_json = json.dumps({
                'type': 'Point',
                'coordinates': [lon, lat],
            })
            conn.execute("""
                INSERT INTO hail_events (
                    event_name, center_lat, center_lon,
                    start_time, end_time,
                    max_hail_size, confidence_score,
                    swath_polygon, swath_area_sqmi,
                    swath_method, status, data_source,
                    bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?)
            """, (
                f'test_ev_{i}', lat, lon, start, end,
                1.5, 50.0,
                point_json, 5.0,
                'centroid_point', 'CONFIRMED', 'NEXRAD_REALTIME',
                lat - 0.2, lat + 0.2, lon - 0.2, lon + 0.2,
            ))
        conn.commit()
        conn.close()

        # Run enrichment (no MRMS cache)
        n = update_event_footprints(db_path, mrms_cache=None)
        ok = n == 5
        print(f"  [{'PASS' if ok else 'FAIL'}] Enriched {n} events (expected 5)")
        all_pass &= ok

        # Verify updates
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT swath_method, swath_area_method, swath_area_km2
            FROM hail_events
        """).fetchall()

        upgraded = sum(1 for r in rows if r['swath_method'] == 'deferred_buffer')
        ok = upgraded == 5
        print(f"  [{'PASS' if ok else 'FAIL'}] {upgraded}/5 upgraded to deferred_buffer")
        all_pass &= ok

        has_area_method = sum(1 for r in rows if r['swath_area_method'] is not None)
        ok = has_area_method == 5
        print(f"  [{'PASS' if ok else 'FAIL'}] {has_area_method}/5 have swath_area_method")
        all_pass &= ok

        has_area_km2 = sum(1 for r in rows if (r['swath_area_km2'] or 0) > 0)
        ok = has_area_km2 == 5
        print(f"  [{'PASS' if ok else 'FAIL'}] {has_area_km2}/5 have swath_area_km2 > 0")
        all_pass &= ok

        # Verify polygon is now a Polygon, not Point
        row = conn.execute(
            "SELECT swath_polygon FROM hail_events LIMIT 1"
        ).fetchone()
        if row and row['swath_polygon']:
            geoj = json.loads(row['swath_polygon'])
            ok = geoj.get('type') == 'Polygon'
            print(f"  [{'PASS' if ok else 'FAIL'}] swath_polygon type: {geoj.get('type')} (expected Polygon)")
            all_pass &= ok

        conn.close()

    finally:
        os.unlink(db_path)

    return all_pass


# -----------------------------------------------------------------------
# Test: Performance
# -----------------------------------------------------------------------

def test_performance():
    print("\nCategory: Performance")
    all_pass = True

    # 100 single-cell events
    t0 = time.time()
    for i in range(100):
        cells = [_make_cell(35.0 + i * 0.01, -97.0 + i * 0.01,
                            area_km2=10.0, mesh_mm=20.0)]
        build_event_polygon(cells)
    elapsed = time.time() - t0
    ok = elapsed < 5.0
    print(f"  [{'PASS' if ok else 'FAIL'}] 100 single-cell polygons in {elapsed:.2f}s (limit 5s)")
    all_pass &= ok

    # 100 multi-cell events
    t0 = time.time()
    for i in range(100):
        cells = [
            _make_cell(35.0, -97.0, prev_positions=[(35.01, -97.01), (35.02, -97.02)]),
            _make_cell(35.05, -97.05, prev_positions=[(35.06, -97.06)]),
        ]
        build_event_polygon(cells)
    elapsed = time.time() - t0
    ok = elapsed < 10.0
    print(f"  [{'PASS' if ok else 'FAIL'}] 100 multi-cell polygons in {elapsed:.2f}s (limit 10s)")
    all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Test: Empty cells graceful
# -----------------------------------------------------------------------

def test_empty_cells():
    print("\nCategory: Edge Cases")
    all_pass = True

    # Empty list
    geojson_str, area_km2, method = build_event_polygon([])
    ok = geojson_str is None and area_km2 == 0.0 and method == 'none'
    print(f"  [{'PASS' if ok else 'FAIL'}] Empty cells -> (None, 0.0, 'none')")
    all_pass &= ok

    # Cell with zero area
    cells = [_make_cell(35.0, -97.0, area_km2=0.0, mesh_mm=0.0)]
    geojson_str, area_km2, method = build_event_polygon(cells)
    ok = geojson_str is not None  # Should still produce a 2km buffer
    print(f"  [{'PASS' if ok else 'FAIL'}] Zero-area cell -> still produces polygon (method={method})")
    all_pass &= ok

    if geojson_str:
        # min buffer = 2km radius -> area ~= pi*4 = 12.6 km2
        ok = area_km2 >= 10.0
        print(f"  [{'PASS' if ok else 'FAIL'}] Min buffer area >= 10: {area_km2:.1f} km2")
        all_pass &= ok

    return all_pass


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("=== EVENT FOOTPRINT TESTS ===\n")
    all_pass = True

    all_pass &= test_multi_cell_union()
    all_pass &= test_single_cell_buffer()
    all_pass &= test_mrms_core_nesting()
    all_pass &= test_mrms_unavailable()
    all_pass &= test_db_enrichment()
    all_pass &= test_performance()
    all_pass &= test_empty_cells()

    print()
    if all_pass:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
