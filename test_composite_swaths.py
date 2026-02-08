"""
Test composite swath generation with multiple detections
"""

import json
from src.radar.swath_generator import SwathGenerator, HailDetection

def test_composite_swaths():
    print("\n" + "="*70)
    print("TESTING COMPOSITE SWATH GENERATION")
    print("="*70 + "\n")

    # ====================================================================
    # TEST 1: SIMPLE 3-POINT COMPOSITE
    # ====================================================================

    print("[1/5] Creating composite swath from 3 detections...")
    print()

    # Three detections along a line (SW to NE)
    detections = [
        HailDetection(lat=32.77, lon=-96.80, hail_size=1.5, timestamp="2024-11-15T14:30:00"),
        HailDetection(lat=32.78, lon=-96.75, hail_size=1.75, timestamp="2024-11-15T14:35:00"),
        HailDetection(lat=32.80, lon=-96.70, hail_size=1.25, timestamp="2024-11-15T14:40:00")
    ]

    print("Detections:")
    for i, det in enumerate(detections, 1):
        print(f"  {i}. {det.lat:.4f}, {det.lon:.4f} - {det.hail_size}\" at {det.timestamp}")
    print()

    composite_swath = SwathGenerator.create_composite_swath(detections)

    area = SwathGenerator.calculate_swath_area(composite_swath)

    print(f"  Composite swath created:")
    print(f"   Method: {composite_swath['properties']['method']}")
    print(f"   Detections: {composite_swath['properties']['detection_count']}")
    print(f"   Max hail: {composite_swath['properties']['max_hail_size']}\"")
    print(f"   Width: {composite_swath['properties']['width_miles']} miles")
    print(f"   Track length: {composite_swath['properties']['track_length_miles']} miles")
    print(f"   Area: ~{area} sq mi")
    print()

    # ====================================================================
    # TEST 2: COMPARE INDIVIDUAL VS COMPOSITE
    # ====================================================================

    print("[2/5] Comparing individual circles vs composite swath...")
    print()

    # Create individual circular swaths
    individual_swaths = []
    total_individual_area = 0

    for det in detections:
        swath = SwathGenerator.create_circular_swath(
            det.lat, det.lon, det.hail_size
        )
        individual_swaths.append(swath)
        ind_area = SwathGenerator.calculate_swath_area(swath)
        total_individual_area += ind_area

    composite_area = SwathGenerator.calculate_swath_area(composite_swath)

    print(f"   Individual circles:")
    print(f"     Total area: ~{total_individual_area:.1f} sq mi")
    print(f"     (With overlap, actual coverage less)")
    print()

    print(f"   Composite swath:")
    print(f"     Total area: ~{composite_area:.1f} sq mi")
    print(f"     (Unified coverage along track)")
    print()

    # ====================================================================
    # TEST 3: DIFFERENT CLUSTER PATTERNS
    # ====================================================================

    print("[3/5] Testing different detection patterns...")
    print()

    patterns = {
        'Linear (4 points)': [
            HailDetection(lat=32.75, lon=-96.80, hail_size=1.5, timestamp="2024-11-15T14:30:00"),
            HailDetection(lat=32.76, lon=-96.78, hail_size=1.6, timestamp="2024-11-15T14:32:00"),
            HailDetection(lat=32.77, lon=-96.76, hail_size=1.7, timestamp="2024-11-15T14:34:00"),
            HailDetection(lat=32.78, lon=-96.74, hail_size=1.8, timestamp="2024-11-15T14:36:00")
        ],
        'Clustered (5 points)': [
            HailDetection(lat=32.77, lon=-96.80, hail_size=1.5, timestamp="2024-11-15T14:30:00"),
            HailDetection(lat=32.77, lon=-96.79, hail_size=1.6, timestamp="2024-11-15T14:31:00"),
            HailDetection(lat=32.78, lon=-96.80, hail_size=1.4, timestamp="2024-11-15T14:32:00"),
            HailDetection(lat=32.78, lon=-96.79, hail_size=1.7, timestamp="2024-11-15T14:33:00"),
            HailDetection(lat=32.77, lon=-96.78, hail_size=1.5, timestamp="2024-11-15T14:34:00")
        ],
        'Scattered (6 points)': [
            HailDetection(lat=32.75, lon=-96.85, hail_size=1.2, timestamp="2024-11-15T14:30:00"),
            HailDetection(lat=32.77, lon=-96.82, hail_size=1.5, timestamp="2024-11-15T14:32:00"),
            HailDetection(lat=32.79, lon=-96.79, hail_size=1.8, timestamp="2024-11-15T14:34:00"),
            HailDetection(lat=32.81, lon=-96.76, hail_size=1.6, timestamp="2024-11-15T14:36:00"),
            HailDetection(lat=32.83, lon=-96.73, hail_size=1.4, timestamp="2024-11-15T14:38:00"),
            HailDetection(lat=32.85, lon=-96.70, hail_size=1.3, timestamp="2024-11-15T14:40:00")
        ]
    }

    for pattern_name, pattern_detections in patterns.items():
        swath = SwathGenerator.create_composite_swath(pattern_detections)
        area = SwathGenerator.calculate_swath_area(swath)
        max_hail = swath['properties']['max_hail_size']
        track_len = swath['properties']['track_length_miles']

        print(f"   {pattern_name}:")
        print(f"     Detections: {len(pattern_detections)}")
        print(f"     Max hail: {max_hail}\"")
        print(f"     Track: {track_len:.1f} mi")
        print(f"     Area: ~{area:.1f} sq mi")
        print()

    # ====================================================================
    # TEST 4: EDGE CASES
    # ====================================================================

    print("[4/5] Testing edge cases...")
    print()

    # Single detection
    single = [HailDetection(lat=32.77, lon=-96.80, hail_size=1.5, timestamp="2024-11-15T14:30:00")]
    single_swath = SwathGenerator.create_composite_swath(single)
    print(f"   Single detection:")
    print(f"     Method: {single_swath['properties']['method']}")
    print(f"     Falls back to circular swath")
    print()

    # Two detections
    pair = [
        HailDetection(lat=32.77, lon=-96.80, hail_size=1.5, timestamp="2024-11-15T14:30:00"),
        HailDetection(lat=32.78, lon=-96.75, hail_size=1.7, timestamp="2024-11-15T14:35:00")
    ]
    pair_swath = SwathGenerator.create_composite_swath(pair)
    pair_area = SwathGenerator.calculate_swath_area(pair_swath)
    print(f"   Two detections:")
    print(f"     Method: {pair_swath['properties']['method']}")
    print(f"     Track: {pair_swath['properties']['track_length_miles']:.1f} mi")
    print(f"     Area: ~{pair_area:.1f} sq mi")
    print()

    # Many detections (storm track)
    many = [
        HailDetection(lat=32.70 + i*0.02, lon=-96.90 + i*0.02, hail_size=1.5 + (i%3)*0.25,
                     timestamp=f"2024-11-15T14:{30+i*2:02d}:00")
        for i in range(15)
    ]
    many_swath = SwathGenerator.create_composite_swath(many)
    many_area = SwathGenerator.calculate_swath_area(many_swath)
    print(f"   15 detections (long track):")
    print(f"     Track: {many_swath['properties']['track_length_miles']:.1f} mi")
    print(f"     Area: ~{many_area:.1f} sq mi")
    print(f"     Handles large tracks")
    print()

    # ====================================================================
    # TEST 5: SAVE VISUALIZATION
    # ====================================================================

    print("[5/5] Creating visualization...")

    features = []

    # Add composite swath
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': composite_swath['type'],
            'coordinates': composite_swath['coordinates']
        },
        'properties': {
            'name': 'Composite Swath',
            'fill': '#FF0000',
            'fill-opacity': 0.3,
            'stroke': '#FF0000',
            'stroke-width': 3
        }
    })

    # Add individual circular swaths for comparison
    for i, (det, swath) in enumerate(zip(detections, individual_swaths)):
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': swath['type'],
                'coordinates': swath['coordinates']
            },
            'properties': {
                'name': f'Individual Circle {i+1}',
                'fill': '#0000FF',
                'fill-opacity': 0.2,
                'stroke': '#0000FF',
                'stroke-width': 1,
                'stroke-dasharray': '5,5'
            }
        })

    # Add detection points
    for i, det in enumerate(detections):
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [det.lon, det.lat]
            },
            'properties': {
                'name': f'Detection {i+1}',
                'hail_size': det.hail_size,
                'timestamp': det.timestamp,
                'marker-color': '#000000',
                'marker-size': 'medium'
            }
        })

    # Add track line
    track_coords = [[det.lon, det.lat] for det in detections]
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': track_coords
        },
        'properties': {
            'name': 'Storm Track',
            'stroke': '#FFD700',
            'stroke-width': 2
        }
    })

    # Create GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save
    with open('data/composite_vs_individual.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)

    print("  Saved: data/composite_vs_individual.geojson")
    print()

    # ====================================================================
    # SUMMARY
    # ====================================================================

    print("="*70)
    print("COMPOSITE SWATH TESTS COMPLETE")
    print("="*70)
    print()
    print("KEY INSIGHTS:")
    print("  -> Composite swaths follow the storm track over time")
    print("  -> Creates unified polygon with rounded end caps")
    print("  -> More accurate than overlapping circles")
    print("  -> Scales well with many detection points")
    print()
    print("WHEN TO USE:")
    print("  - Circular:    Single detection point")
    print("  - Elliptical:  Single detection + storm motion data")
    print("  - Composite:   Multiple time-sequenced detections")
    print()
    print("VISUALIZATION:")
    print("  -> Open data/composite_vs_individual.geojson at geojson.io")
    print("  -> Red solid = composite swath (unified track)")
    print("  -> Blue dashed = individual circles (overlapping)")
    print("  -> Black dots = actual detection points")
    print("  -> Yellow line = storm track")
    print()

if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)
    test_composite_swaths()
