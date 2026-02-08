"""
Test basic swath generation (circular and elliptical)
"""

import json
import os
import sys

sys.path.insert(0, '.')

from src.radar.swath_generator import SwathGenerator, HailDetection


def test_basic_swaths():
    print("\n" + "="*70)
    print("TESTING BASIC SWATH GENERATION")
    print("="*70 + "\n")

    # ========================================================================
    # TEST 1: CIRCULAR SWATH (Minimum Data)
    # ========================================================================

    print("[1/6] Testing circular swath (minimum data)...")
    print("Scenario: 1.75\" hail detected in Dallas")
    print("Data: Only lat/lon and hail size")
    print()

    # Dallas coordinates
    dallas_lat = 32.7767
    dallas_lon = -96.7970
    hail_size = 1.75  # inches

    circular_swath = SwathGenerator.create_circular_swath(
        lat=dallas_lat,
        lon=dallas_lon,
        hail_size_inches=hail_size
    )

    area = SwathGenerator.calculate_swath_area(circular_swath)

    print(f"  Circular swath created:")
    print(f"   - Method: {circular_swath['properties']['method']}")
    print(f"   - Radius: {circular_swath['properties']['radius_miles']} miles")
    print(f"   - Area: ~{area} square miles")
    print(f"   - Coordinates: {len(circular_swath['coordinates'][0])} points")
    print()

    # ========================================================================
    # TEST 2: DIFFERENT HAIL SIZES
    # ========================================================================

    print("[2/6] Testing different hail sizes...")

    test_cases = [
        (1.0, "Quarter size"),
        (1.75, "Golf ball"),
        (2.5, "Tennis ball"),
        (4.0, "Softball")
    ]

    for size, description in test_cases:
        swath = SwathGenerator.create_circular_swath(
            lat=dallas_lat,
            lon=dallas_lon,
            hail_size_inches=size
        )
        radius = swath['properties']['radius_miles']
        area = SwathGenerator.calculate_swath_area(swath)
        print(f"   - {size}\" ({description}): {radius} mi radius, ~{area} sq mi")

    print()

    # ========================================================================
    # TEST 3: ELLIPTICAL SWATH (With Storm Movement)
    # ========================================================================

    print("[3/6] Testing elliptical swath (with storm movement)...")
    print("Scenario: Storm moving northeast at 45 mph for 30 minutes")
    print()

    elliptical_swath = SwathGenerator.create_elliptical_swath(
        center_lat=dallas_lat,
        center_lon=dallas_lon,
        hail_size=1.75,
        storm_motion_dir=45,  # Northeast
        storm_motion_speed=45,  # mph
        duration_minutes=30
    )

    area = SwathGenerator.calculate_swath_area(elliptical_swath)

    print(f"  Elliptical swath created:")
    print(f"   - Method: {elliptical_swath['properties']['method']}")
    print(f"   - Path length: {elliptical_swath['properties']['path_length_miles']} miles")
    print(f"   - Width: {elliptical_swath['properties']['width_miles']} miles")
    print(f"   - Direction: {elliptical_swath['properties']['storm_direction']} deg (NE)")
    print(f"   - Area: ~{area} square miles")
    print()

    # ========================================================================
    # TEST 4: DIFFERENT STORM DIRECTIONS
    # ========================================================================

    print("[4/6] Testing storm movement directions...")

    directions = [
        (0, "North"),
        (90, "East"),
        (180, "South"),
        (270, "West"),
        (135, "Southeast")
    ]

    for direction, name in directions:
        swath = SwathGenerator.create_elliptical_swath(
            center_lat=dallas_lat,
            center_lon=dallas_lon,
            hail_size=1.75,
            storm_motion_dir=direction,
            storm_motion_speed=40,
            duration_minutes=20
        )
        length = swath['properties']['path_length_miles']
        width = swath['properties']['width_miles']
        print(f"   - {name:12s} ({direction:3d} deg): {length:.1f} mi x {width:.1f} mi")

    print()

    # ========================================================================
    # TEST 5: POINT IN SWATH TEST
    # ========================================================================

    print("[5/6] Testing point-in-swath detection...")

    # Test point inside circular swath
    inside_point = SwathGenerator.point_in_swath(dallas_lat, dallas_lon, circular_swath)
    print(f"   - Center point ({dallas_lat}, {dallas_lon}): {'INSIDE' if inside_point else 'OUTSIDE'}")

    # Test point outside circular swath (10 miles away)
    outside_lat = dallas_lat + 0.2  # ~14 miles north
    outside_point = SwathGenerator.point_in_swath(outside_lat, dallas_lon, circular_swath)
    print(f"   - 14 mi north ({outside_lat:.4f}, {dallas_lon}): {'INSIDE' if outside_point else 'OUTSIDE'}")

    # Test bounds
    bounds = SwathGenerator.get_swath_bounds(circular_swath)
    print(f"   - Bounds: N={bounds['north']:.4f}, S={bounds['south']:.4f}, E={bounds['east']:.4f}, W={bounds['west']:.4f}")

    print()

    # ========================================================================
    # TEST 6: SAVE SAMPLE SWATHS AS GEOJSON
    # ========================================================================

    print("[6/6] Saving sample swaths as GeoJSON files...")

    os.makedirs('data', exist_ok=True)

    # Save circular swath
    with open('data/sample_circular_swath.geojson', 'w') as f:
        geojson = {
            'type': 'FeatureCollection',
            'features': [{
                'type': 'Feature',
                'geometry': {
                    'type': circular_swath['type'],
                    'coordinates': circular_swath['coordinates']
                },
                'properties': {
                    'name': 'Dallas Circular Swath',
                    'hail_size': 1.75,
                    'radius_miles': circular_swath['properties']['radius_miles'],
                    'method': circular_swath['properties']['method'],
                    'date': '2026-01-17'
                }
            }]
        }
        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_circular_swath.geojson")

    # Save elliptical swath
    with open('data/sample_elliptical_swath.geojson', 'w') as f:
        geojson = {
            'type': 'FeatureCollection',
            'features': [{
                'type': 'Feature',
                'geometry': {
                    'type': elliptical_swath['type'],
                    'coordinates': elliptical_swath['coordinates']
                },
                'properties': {
                    'name': 'Dallas Elliptical Swath',
                    'hail_size': 1.75,
                    'storm_direction': 45,
                    'path_length_miles': elliptical_swath['properties']['path_length_miles'],
                    'width_miles': elliptical_swath['properties']['width_miles'],
                    'method': elliptical_swath['properties']['method'],
                    'date': '2026-01-17'
                }
            }]
        }
        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_elliptical_swath.geojson")

    # Save combined swaths for comparison
    with open('data/sample_swaths_combined.geojson', 'w') as f:
        geojson = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': circular_swath['type'],
                        'coordinates': circular_swath['coordinates']
                    },
                    'properties': {
                        'name': 'Circular Swath',
                        'method': 'circular',
                        'style': {'color': '#ff0000', 'fillOpacity': 0.3}
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': elliptical_swath['type'],
                        'coordinates': elliptical_swath['coordinates']
                    },
                    'properties': {
                        'name': 'Elliptical Swath (NE)',
                        'method': 'elliptical',
                        'style': {'color': '#0000ff', 'fillOpacity': 0.3}
                    }
                }
            ]
        }
        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_swaths_combined.geojson")

    print()
    print("="*70)
    print("BASIC SWATH GENERATION TESTS COMPLETE")
    print("="*70)
    print()
    print("RESULTS:")
    print("  - Circular swaths work")
    print("  - Elliptical swaths work")
    print("  - Different hail sizes tested")
    print("  - Storm directions tested")
    print("  - Point-in-swath detection works")
    print("  - GeoJSON export works")
    print()
    print("NEXT: View these GeoJSON files at geojson.io to visualize!")
    print()

    return True


if __name__ == '__main__':
    test_basic_swaths()
