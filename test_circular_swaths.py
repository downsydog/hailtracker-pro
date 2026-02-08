"""
Test circular swath generation
"""

import json
from src.radar.swath_generator import SwathGenerator
from src.radar.swath_generator import HailDetection

def test_circular_swaths():
    print("\n" + "="*70)
    print("TESTING CIRCULAR SWATH GENERATION")
    print("="*70 + "\n")

    # ====================================================================
    # TEST 1: SINGLE CIRCULAR SWATH
    # ====================================================================

    print("[1/5] Creating circular swath for Dallas hail...")
    print("Scenario: 1.75\" hail (golf ball size)")
    print()

    # Dallas coordinates
    dallas_lat = 32.7767
    dallas_lon = -96.7970
    hail_size = 1.75  # inches

    swath = SwathGenerator.create_circular_swath(
        lat=dallas_lat,
        lon=dallas_lon,
        hail_size_inches=hail_size
    )

    area = SwathGenerator.calculate_swath_area(swath)

    print(f"  Circular swath created:")
    print(f"   Method: {swath['properties']['method']}")
    print(f"   Radius: {swath['properties']['radius_miles']} miles")
    print(f"   Area: ~{area} square miles")
    print(f"   Coordinates: {len(swath['coordinates'][0])} points")
    print()

    # ====================================================================
    # TEST 2: DIFFERENT HAIL SIZES
    # ====================================================================

    print("[2/5] Testing different hail sizes...")
    print()

    test_cases = [
        (0.75, "Penny"),
        (1.00, "Quarter"),
        (1.75, "Golf ball"),
        (2.50, "Tennis ball"),
        (4.00, "Softball")
    ]

    for size, description in test_cases:
        swath = SwathGenerator.create_circular_swath(
            lat=dallas_lat,
            lon=dallas_lon,
            hail_size_inches=size
        )
        radius = swath['properties']['radius_miles']
        area = SwathGenerator.calculate_swath_area(swath)
        print(f"   {size:4.2f}\" ({description:12s}): {radius:5.2f} mi radius, ~{area:6.1f} sq mi")

    print()

    # ====================================================================
    # TEST 3: MINIMUM RADIUS ENFORCEMENT
    # ====================================================================

    print("[3/5] Testing minimum radius enforcement...")

    # Very small hail should still create minimum radius
    tiny_swath = SwathGenerator.create_circular_swath(
        lat=dallas_lat,
        lon=dallas_lon,
        hail_size_inches=0.25  # Pea size
    )

    print(f"   0.25\" hail (pea):")
    print(f"   Expected: {0.25 * 3} mi radius")
    print(f"   Actual: {tiny_swath['properties']['radius_miles']} mi radius")
    print(f"   Enforced minimum of {SwathGenerator.MIN_SWATH_RADIUS} miles")
    print()

    # ====================================================================
    # TEST 4: CUSTOM RADIUS MULTIPLIER
    # ====================================================================

    print("[4/5] Testing custom radius multiplier...")

    # Conservative estimate (wider swaths)
    conservative_swath = SwathGenerator.create_circular_swath(
        lat=dallas_lat,
        lon=dallas_lon,
        hail_size_inches=1.75,
        radius_multiplier=4.0  # More conservative
    )

    # Aggressive estimate (narrower swaths)
    aggressive_swath = SwathGenerator.create_circular_swath(
        lat=dallas_lat,
        lon=dallas_lon,
        hail_size_inches=1.75,
        radius_multiplier=2.0  # More aggressive
    )

    # Standard swath for comparison
    standard_swath = SwathGenerator.create_circular_swath(
        lat=dallas_lat,
        lon=dallas_lon,
        hail_size_inches=1.75
    )

    print(f"   1.75\" hail with different multipliers:")
    print(f"   Conservative (4x): {conservative_swath['properties']['radius_miles']} mi radius")
    print(f"   Standard (3x):     {standard_swath['properties']['radius_miles']} mi radius")
    print(f"   Aggressive (2x):   {aggressive_swath['properties']['radius_miles']} mi radius")
    print()

    # ====================================================================
    # TEST 5: SAVE AS GEOJSON
    # ====================================================================

    print("[5/5] Saving swath as GeoJSON...")

    # Create feature collection
    features = []

    # Add swath polygon
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': swath['type'],
            'coordinates': swath['coordinates']
        },
        'properties': {
            'name': 'Dallas Hail Swath',
            'date': '2024-11-15',
            'hail_size': hail_size,
            'location': 'Dallas, TX',
            **swath['properties']
        }
    })

    # Add center point
    center_point = {
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [dallas_lon, dallas_lat]
        },
        'properties': {
            'name': 'Detection Point',
            'hail_size': hail_size
        }
    }
    features.append(center_point)

    # Create feature collection
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save to file
    with open('data/circular_swath_dallas.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)

    print("  Saved: data/circular_swath_dallas.geojson")
    print()

    # ====================================================================
    # SUMMARY
    # ====================================================================

    print("="*70)
    print("CIRCULAR SWATH TESTS COMPLETE")
    print("="*70)
    print()
    print("CAPABILITIES:")
    print("  - Create circular swaths around detection points")
    print("  - Radius scales with hail size")
    print("  - Minimum radius enforcement")
    print("  - Custom radius multipliers")
    print("  - Area calculation")
    print("  - GeoJSON export")
    print()
    print("NEXT STEPS:")
    print("  -> View data/circular_swath_dallas.geojson at geojson.io")
    print("  -> See the circular swath on a map!")
    print()
    print("FORMULA:")
    print("  Radius (miles) = hail_size (inches) x multiplier")
    print("  Default multiplier: 3.0")
    print("  Example: 1.75\" hail = 5.25 mile radius")
    print()

if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)
    test_circular_swaths()
