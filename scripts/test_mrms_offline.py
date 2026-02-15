#!/usr/bin/env python3
"""
Lightweight offline sanity test for the MRMS MESH backbone.

Verifies:
  - Import succeeds
  - MRMSCache works with synthetic data
  - MRMSUpdater.fetch_once() does not crash when offline
  - Point queries and bbox queries work correctly
  - GeoJSON export works
  - Cache status reporting works

Does NOT require network access or ENABLE_MRMS=true.

Usage:
    python scripts/test_mrms_offline.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def main():
    print("=" * 60)
    print("MRMS OFFLINE SANITY TEST")
    print("=" * 60)

    # --- 1) Import check ---
    print("\n[1] Import check...")
    from src.radar.mrms import MRMSCache, MRMSUpdater
    from src.radar.mrms.providers import MesonetMRMSProvider, AWSMRMSProvider, get_provider
    print("    OK: All MRMS modules imported")

    # --- 2) Cache with synthetic data ---
    print("\n[2] Cache with synthetic data...")
    cache = MRMSCache()
    assert not cache.is_loaded, "Cache should start empty"
    assert cache.source_time is None
    assert cache.query_point(32.7, -96.8) is None, "Empty cache should return None"

    # Create synthetic grid
    lats = np.arange(30.0, 40.0, 0.5)
    lons = np.arange(-100.0, -90.0, 0.5)
    mesh = np.zeros((len(lats), len(lons)), dtype=np.float32)
    # Put a hail cell at (35.0, -97.0) area
    mesh[10, 6] = 45.0  # 45mm MESH
    mesh[10, 7] = 30.0
    mesh[11, 6] = 25.0

    cache.update({
        'lats': lats,
        'lons': lons,
        'mesh_mm': mesh,
        'source_time': '2025-06-15T18:00:00Z',
        'provider': 'test_synthetic',
    })

    assert cache.is_loaded, "Cache should be loaded after update"
    assert cache.source_time == '2025-06-15T18:00:00Z'
    assert cache.provider == 'test_synthetic'
    assert cache.update_count == 1
    print("    OK: Cache loaded with synthetic data")

    # --- 3) Point queries ---
    print("\n[3] Point queries...")
    val = cache.query_point(35.0, -97.0)
    assert val is not None and val == 45.0, f"Expected 45.0 at (35,-97), got {val}"
    print(f"    OK: query_point(35.0, -97.0) = {val} mm")

    val2 = cache.query_point(30.0, -100.0)
    assert val2 is None, f"Expected None at grid corner (no MESH), got {val2}"
    print(f"    OK: query_point(30.0, -100.0) = None (no MESH)")

    val3 = cache.query_point(0.0, 0.0)
    assert val3 is None, "Point outside grid should return None"
    print(f"    OK: query_point(0.0, 0.0) = None (outside grid)")

    # --- 4) Bbox queries ---
    print("\n[4] Bbox queries...")
    result = cache.query_bbox(-98.0, 34.0, -96.0, 36.0)
    assert result is not None, "Bbox query should return result"
    assert result['peak_mm'] == 45.0, f"Expected peak=45.0, got {result['peak_mm']}"
    assert result['count'] >= 3, f"Expected >=3 nonzero cells, got {result['count']}"
    print(f"    OK: bbox query peak={result['peak_mm']}, avg={result['avg_mm']:.1f}, count={result['count']}")

    empty = cache.query_bbox(-80.0, 40.0, -70.0, 45.0)
    # Outside grid entirely -> returns None; or if partially in grid -> count=0
    if empty is None:
        print(f"    OK: Empty region query returned None (outside grid)")
    else:
        assert empty['count'] == 0, f"Expected 0 count, got {empty['count']}"
        print(f"    OK: Empty region query count=0")

    # --- 5) GeoJSON export ---
    print("\n[5] GeoJSON export...")
    geojson = cache.get_geojson_grid(-100.0, 30.0, -90.0, 40.0, max_points=500)
    assert geojson['type'] == 'FeatureCollection'
    assert len(geojson['features']) >= 3, f"Expected >=3 features, got {len(geojson['features'])}"
    for f in geojson['features']:
        assert f['type'] == 'Feature'
        assert f['geometry']['type'] == 'Point'
        assert f['properties']['mesh_mm'] > 0
        assert 'mesh_inches' in f['properties']
    print(f"    OK: GeoJSON has {len(geojson['features'])} features")

    # --- 6) Cache status ---
    print("\n[6] Cache status...")
    status = cache.get_status()
    assert status['loaded'] is True
    assert status['peak_mm'] == 45.0
    assert status['update_count'] == 1
    assert status['last_error'] is None
    print(f"    OK: Status = {status}")

    # --- 7) Error recording ---
    print("\n[7] Error recording...")
    cache.set_error("test error")
    assert cache.last_error == "test error"
    assert cache.is_loaded, "Error should not clear the cache"
    print("    OK: Error recorded without clearing cache")

    # --- 8) Updater offline resilience ---
    print("\n[8] Updater offline resilience...")
    updater = MRMSUpdater(
        cache=MRMSCache(),
        refresh_seconds=9999,
        provider_name='mesonet',
    )
    # fetch_once should not crash even if network is down
    result = updater.fetch_once()
    # Result may be True or False depending on network, but should not raise
    print(f"    OK: fetch_once returned {result} (no crash)")

    status = updater.get_status()
    assert 'updater_running' in status
    assert 'refresh_seconds' in status
    print(f"    OK: Updater status = running={status['updater_running']}")

    # --- 9) Provider factory ---
    print("\n[9] Provider factory...")
    p1 = get_provider('aws')
    assert isinstance(p1, AWSMRMSProvider)
    p2 = get_provider('mesonet')
    assert isinstance(p2, MesonetMRMSProvider)
    p3 = get_provider('unknown_xyz')
    assert isinstance(p3, MesonetMRMSProvider), "Unknown provider should fallback to mesonet"
    print("    OK: Provider factory works")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("ALL MRMS OFFLINE TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
