"""
Test elliptical swath generation with storm movement
"""

import json
from src.radar.swath_generator import SwathGenerator
from src.radar.geo_utils import GeoUtils

def test_elliptical_swaths():
    print("\n" + "="*70)
    print("TESTING ELLIPTICAL SWATH GENERATION")
    print("="*70 + "\n")

    # Dallas location
    dallas_lat = 32.7767
    dallas_lon = -96.7970

    # ====================================================================
    # TEST 1: BASIC ELLIPTICAL SWATH
    # ====================================================================

    print("[1/6] Creating elliptical swath...")
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
    print(f"   Method: {elliptical_swath['properties']['method']}")
    print(f"   Path length: {elliptical_swath['properties']['path_length_miles']} miles")
    print(f"   Width: {elliptical_swath['properties']['width_miles']} miles")
    print(f"   Direction: {elliptical_swath['properties']['storm_direction']} deg (NE)")
    print(f"   Area: ~{area} square miles")
    print()

    # ====================================================================
    # TEST 2: COMPARE CIRCULAR VS ELLIPTICAL
    # ====================================================================

    print("[2/6] Comparing circular vs elliptical for same event...")
    print()

    # Same hail size, same location
    circular_swath = SwathGenerator.create_circular_swath(
        lat=dallas_lat,
        lon=dallas_lon,
        hail_size_inches=1.75
    )

    circular_area = SwathGenerator.calculate_swath_area(circular_swath)
    elliptical_area = SwathGenerator.calculate_swath_area(elliptical_swath)

    print(f"   Circular swath:")
    print(f"     Radius: {circular_swath['properties']['radius_miles']} miles")
    print(f"     Area: ~{circular_area} sq mi")
    print()

    print(f"   Elliptical swath (moving storm):")
    print(f"     Length: {elliptical_swath['properties']['path_length_miles']} miles")
    print(f"     Width: {elliptical_swath['properties']['width_miles']} miles")
    print(f"     Area: ~{elliptical_area} sq mi")
    print()

    print(f"   Elliptical is {elliptical_area/circular_area:.1f}x larger")
    print(f"      (More realistic for moving storms)")
    print()

    # ====================================================================
    # TEST 3: DIFFERENT STORM DIRECTIONS
    # ====================================================================

    print("[3/6] Testing different storm directions...")
    print()

    directions = [
        (0, "North"),
        (45, "Northeast"),
        (90, "East"),
        (135, "Southeast"),
        (180, "South"),
        (225, "Southwest"),
        (270, "West"),
        (315, "Northwest")
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
        print(f"   {name:12s} ({direction:3d} deg): {length:.1f} mi x {width:.1f} mi")

    print()

    # ====================================================================
    # TEST 4: DIFFERENT STORM SPEEDS
    # ====================================================================

    print("[4/6] Testing different storm speeds (30 min duration)...")
    print()

    speeds = [20, 30, 40, 50, 60]  # mph

    for speed in speeds:
        swath = SwathGenerator.create_elliptical_swath(
            center_lat=dallas_lat,
            center_lon=dallas_lon,
            hail_size=1.75,
            storm_motion_dir=45,  # NE
            storm_motion_speed=speed,
            duration_minutes=30
        )
        length = swath['properties']['path_length_miles']
        width = swath['properties']['width_miles']
        area = SwathGenerator.calculate_swath_area(swath)
        print(f"   {speed:2d} mph: {length:5.1f} mi long x {width:4.1f} mi wide = ~{area:6.1f} sq mi")

    print()

    # ====================================================================
    # TEST 5: DIFFERENT DURATIONS
    # ====================================================================

    print("[5/6] Testing different storm durations (45 mph)...")
    print()

    durations = [10, 20, 30, 45, 60]  # minutes

    for duration in durations:
        swath = SwathGenerator.create_elliptical_swath(
            center_lat=dallas_lat,
            center_lon=dallas_lon,
            hail_size=1.75,
            storm_motion_dir=45,
            storm_motion_speed=45,
            duration_minutes=duration
        )
        length = swath['properties']['path_length_miles']
        width = swath['properties']['width_miles']
        area = SwathGenerator.calculate_swath_area(swath)
        print(f"   {duration:2d} min: {length:5.1f} mi long x {width:4.1f} mi wide = ~{area:6.1f} sq mi")

    print()

    # ====================================================================
    # TEST 6: SAVE COMPARISON VISUALIZATION
    # ====================================================================

    print("[6/6] Creating comparison visualization...")

    features = []

    # Add circular swath (for comparison)
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': circular_swath['type'],
            'coordinates': circular_swath['coordinates']
        },
        'properties': {
            'name': 'Circular Swath (no movement)',
            'fill': '#0000FF',
            'fill-opacity': 0.3,
            'stroke': '#0000FF',
            'stroke-width': 2
        }
    })

    # Add elliptical swath
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': elliptical_swath['type'],
            'coordinates': elliptical_swath['coordinates']
        },
        'properties': {
            'name': 'Elliptical Swath (moving storm)',
            'fill': '#FF0000',
            'fill-opacity': 0.3,
            'stroke': '#FF0000',
            'stroke-width': 2
        }
    })

    # Add center point
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [dallas_lon, dallas_lat]
        },
        'properties': {
            'name': 'Storm Center',
            'marker-color': '#000000',
            'marker-size': 'large'
        }
    })

    # Add direction arrow (line showing storm motion)
    arrow_end_lat, arrow_end_lon = GeoUtils.offset_position(
        dallas_lat, dallas_lon,
        distance_miles=15,
        bearing_deg=45  # NE direction
    )

    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': [
                [dallas_lon, dallas_lat],
                [arrow_end_lon, arrow_end_lat]
            ]
        },
        'properties': {
            'name': 'Storm Motion (NE at 45 mph)',
            'stroke': '#000000',
            'stroke-width': 3
        }
    })

    # Create GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save
    with open('data/elliptical_vs_circular.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)

    print("  Saved: data/elliptical_vs_circular.geojson")
    print()

    # ====================================================================
    # SUMMARY
    # ====================================================================

    print("="*70)
    print("ELLIPTICAL SWATH TESTS COMPLETE")
    print("="*70)
    print()
    print("KEY INSIGHTS:")
    print("  -> Moving storms create elongated damage paths")
    print("  -> Elliptical swaths are more realistic than circles")
    print("  -> Faster storms = longer swaths")
    print("  -> Longer duration = longer swaths")
    print("  -> Direction matters for accurate swath placement")
    print()
    print("WHEN TO USE:")
    print("  - Circular:    Single radar detection, no storm motion data")
    print("  - Elliptical:  Storm motion known (direction + speed + duration)")
    print()
    print("VISUALIZATION:")
    print("  -> Open data/elliptical_vs_circular.geojson at geojson.io")
    print("  -> Blue circle = no movement assumption")
    print("  -> Red ellipse = accounts for storm movement")
    print("  -> Notice how ellipse follows storm direction!")
    print()


if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)
    test_elliptical_swaths()
