"""
Test advanced swath generation (composite and reflectivity methods)
"""

import json
import os
import sys

sys.path.insert(0, '.')

from src.radar.swath_generator import SwathGenerator, HailDetection, StormTrack


def test_advanced_swaths():
    print("\n" + "="*70)
    print("TESTING ADVANCED SWATH GENERATION")
    print("="*70 + "\n")

    os.makedirs('data', exist_ok=True)

    # ========================================================================
    # TEST 1: COMPOSITE SWATH (Multiple Detections)
    # ========================================================================

    print("[1/6] Testing composite swath from multiple detections...")
    print("Scenario: Storm producing hail over 30 minutes across DFW")
    print()

    # Create detections moving from southwest to northeast
    detections_composite = [
        HailDetection(
            lat=32.65, lon=-97.10,
            hail_size=1.25, timestamp='2024-11-15T14:00:00'
        ),
        HailDetection(
            lat=32.70, lon=-97.00,
            hail_size=1.50, timestamp='2024-11-15T14:10:00'
        ),
        HailDetection(
            lat=32.75, lon=-96.90,
            hail_size=1.75, timestamp='2024-11-15T14:20:00'
        ),
        HailDetection(
            lat=32.82, lon=-96.80,
            hail_size=2.00, timestamp='2024-11-15T14:30:00'
        ),
        HailDetection(
            lat=32.88, lon=-96.70,
            hail_size=1.75, timestamp='2024-11-15T14:40:00'
        ),
    ]

    composite_swath = SwathGenerator.create_composite_swath(detections_composite)
    area_composite = SwathGenerator.calculate_swath_area(composite_swath)

    print(f"  Composite swath created:")
    print(f"   - Method: {composite_swath['properties']['method']}")
    print(f"   - Detections: {composite_swath['properties']['detection_count']}")
    print(f"   - Track length: {composite_swath['properties']['track_length_miles']} miles")
    print(f"   - Width: {composite_swath['properties']['width_miles']} miles")
    print(f"   - Max hail: {composite_swath['properties']['max_hail_size']}\"")
    print(f"   - Area: ~{area_composite} sq miles")
    print()

    # ========================================================================
    # TEST 2: REFLECTIVITY-WEIGHTED SWATH
    # ========================================================================

    print("[2/6] Testing reflectivity-weighted swath...")
    print("Scenario: Storm with varying intensity (radar reflectivity)")
    print()

    # Create detections with reflectivity data
    detections_reflectivity = [
        HailDetection(
            lat=32.65, lon=-97.10,
            hail_size=1.25, timestamp='2024-11-15T14:00:00',
            reflectivity=52
        ),
        HailDetection(
            lat=32.70, lon=-97.00,
            hail_size=1.50, timestamp='2024-11-15T14:10:00',
            reflectivity=58
        ),
        HailDetection(
            lat=32.75, lon=-96.90,
            hail_size=2.00, timestamp='2024-11-15T14:20:00',
            reflectivity=65  # Peak intensity
        ),
        HailDetection(
            lat=32.82, lon=-96.80,
            hail_size=1.75, timestamp='2024-11-15T14:30:00',
            reflectivity=60
        ),
        HailDetection(
            lat=32.88, lon=-96.70,
            hail_size=1.50, timestamp='2024-11-15T14:40:00',
            reflectivity=55
        ),
    ]

    reflectivity_swath = SwathGenerator.create_reflectivity_swath(detections_reflectivity)
    area_reflectivity = SwathGenerator.calculate_swath_area(reflectivity_swath)

    print(f"  Reflectivity swath created:")
    print(f"   - Method: {reflectivity_swath['properties']['method']}")
    print(f"   - Detections: {reflectivity_swath['properties']['detection_count']}")
    print(f"   - Track length: {reflectivity_swath['properties']['track_length_miles']} miles")
    print(f"   - Max hail: {reflectivity_swath['properties']['max_hail_size']}\"")
    print(f"   - Max reflectivity: {reflectivity_swath['properties']['max_reflectivity_dbz']} dBZ")
    print(f"   - Avg reflectivity: {reflectivity_swath['properties']['avg_reflectivity_dbz']} dBZ")
    print(f"   - Area: ~{area_reflectivity} sq miles")
    print()

    # ========================================================================
    # TEST 3: AUTO-SELECTION WITH REFLECTIVITY DATA
    # ========================================================================

    print("[3/6] Testing auto-selection with reflectivity data...")
    print()

    auto_swath_1 = SwathGenerator.auto_generate_swath(detections=detections_reflectivity)
    print(f"  Auto-selected method: {auto_swath_1['properties']['method']}")
    print(f"  (Expected: reflectivity - has dBZ values)")
    print()

    # ========================================================================
    # TEST 4: AUTO-SELECTION WITHOUT REFLECTIVITY DATA
    # ========================================================================

    print("[4/6] Testing auto-selection without reflectivity data...")
    print()

    auto_swath_2 = SwathGenerator.auto_generate_swath(detections=detections_composite)
    print(f"  Auto-selected method: {auto_swath_2['properties']['method']}")
    print(f"  (Expected: composite - no dBZ values)")
    print()

    # ========================================================================
    # TEST 5: AUTO-SELECTION WITH SINGLE POINT + MOVEMENT
    # ========================================================================

    print("[5/6] Testing auto-selection with single point + movement data...")
    print()

    auto_swath_3 = SwathGenerator.auto_generate_swath(
        center_lat=32.7767,
        center_lon=-96.7970,
        hail_size=1.75,
        storm_motion_dir=45,
        storm_motion_speed=40,
        duration_minutes=30
    )
    print(f"  Auto-selected method: {auto_swath_3['properties']['method']}")
    print(f"  (Expected: elliptical - has movement data)")
    print()

    # ========================================================================
    # TEST 6: SAVE ADVANCED SWATHS AS GEOJSON
    # ========================================================================

    print("[6/6] Saving advanced swaths as GeoJSON files...")

    # Save composite swath
    with open('data/sample_composite_swath.geojson', 'w') as f:
        geojson = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': composite_swath['type'],
                        'coordinates': composite_swath['coordinates']
                    },
                    'properties': {
                        'name': 'DFW Composite Swath',
                        'method': 'composite',
                        'detection_count': composite_swath['properties']['detection_count'],
                        'track_length_miles': composite_swath['properties']['track_length_miles'],
                        'fill': '#ff6600',
                        'fill-opacity': 0.3
                    }
                }
            ]
        }

        # Add detection points
        for i, d in enumerate(detections_composite):
            geojson['features'].append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [d.lon, d.lat]
                },
                'properties': {
                    'name': f'Detection {i+1}',
                    'hail_size': d.hail_size,
                    'timestamp': d.timestamp,
                    'marker-color': '#ff0000',
                    'marker-size': 'small'
                }
            })

        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_composite_swath.geojson")

    # Save reflectivity swath
    with open('data/sample_reflectivity_swath.geojson', 'w') as f:
        geojson = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': reflectivity_swath['type'],
                        'coordinates': reflectivity_swath['coordinates']
                    },
                    'properties': {
                        'name': 'DFW Reflectivity Swath',
                        'method': 'reflectivity',
                        'max_reflectivity': reflectivity_swath['properties']['max_reflectivity_dbz'],
                        'avg_reflectivity': reflectivity_swath['properties']['avg_reflectivity_dbz'],
                        'fill': '#9900ff',
                        'fill-opacity': 0.3
                    }
                }
            ]
        }

        # Add detection points with reflectivity labels
        for i, d in enumerate(detections_reflectivity):
            geojson['features'].append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [d.lon, d.lat]
                },
                'properties': {
                    'name': f'Detection {i+1}',
                    'hail_size': d.hail_size,
                    'reflectivity': d.reflectivity,
                    'timestamp': d.timestamp,
                    'marker-color': '#9900ff',
                    'marker-size': 'small'
                }
            })

        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_reflectivity_swath.geojson")

    # Save all methods comparison
    with open('data/sample_all_methods_comparison.geojson', 'w') as f:
        # Create circular at center
        center_lat = 32.75
        center_lon = -96.90

        circular = SwathGenerator.create_circular_swath(center_lat, center_lon, 2.0)

        elliptical = SwathGenerator.create_elliptical_swath(
            center_lat=center_lat,
            center_lon=center_lon,
            hail_size=2.0,
            storm_motion_dir=45,
            storm_motion_speed=40,
            duration_minutes=30
        )

        track = StormTrack(
            start_lat=32.65, start_lon=-97.10,
            end_lat=32.88, end_lon=-96.70,
            start_time='2024-11-15T14:00:00',
            end_time='2024-11-15T14:40:00',
            motion_dir=45, motion_speed=40, max_hail=2.0
        )
        track_swath = SwathGenerator.create_track_swath(track)

        geojson = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': circular['type'],
                        'coordinates': circular['coordinates']
                    },
                    'properties': {
                        'name': 'Method 1: Circular',
                        'method': 'circular',
                        'fill': '#ff0000',
                        'fill-opacity': 0.15,
                        'stroke': '#ff0000'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': elliptical['type'],
                        'coordinates': elliptical['coordinates']
                    },
                    'properties': {
                        'name': 'Method 2: Elliptical',
                        'method': 'elliptical',
                        'fill': '#00ff00',
                        'fill-opacity': 0.15,
                        'stroke': '#00ff00'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': track_swath['type'],
                        'coordinates': track_swath['coordinates']
                    },
                    'properties': {
                        'name': 'Method 3: Track',
                        'method': 'track',
                        'fill': '#0000ff',
                        'fill-opacity': 0.15,
                        'stroke': '#0000ff'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': composite_swath['type'],
                        'coordinates': composite_swath['coordinates']
                    },
                    'properties': {
                        'name': 'Method 4: Composite',
                        'method': 'composite',
                        'fill': '#ff6600',
                        'fill-opacity': 0.15,
                        'stroke': '#ff6600'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': reflectivity_swath['type'],
                        'coordinates': reflectivity_swath['coordinates']
                    },
                    'properties': {
                        'name': 'Method 5: Reflectivity',
                        'method': 'reflectivity',
                        'fill': '#9900ff',
                        'fill-opacity': 0.15,
                        'stroke': '#9900ff'
                    }
                }
            ]
        }
        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_all_methods_comparison.geojson")

    print()
    print("="*70)
    print("ADVANCED SWATH GENERATION TESTS COMPLETE")
    print("="*70)
    print()
    print("KEY FEATURES:")
    print("  - Composite swaths from multiple detections")
    print("  - Reflectivity-weighted variable-width swaths")
    print("  - Auto-selection based on available data")
    print("  - All 5 methods compared in one file")
    print()
    print("METHOD COMPARISON:")
    print("  1. Circular    - Minimum data (point + hail size)")
    print("  2. Elliptical  - With storm movement")
    print("  3. Track       - Start/end points known")
    print("  4. Composite   - Multiple time-sequenced detections")
    print("  5. Reflectivity - With radar intensity data")
    print()
    print("View at geojson.io to compare all methods!")
    print()


def test_method_recommendations():
    """Test the get_recommended_method function"""
    print("\n" + "="*70)
    print("TESTING METHOD RECOMMENDATIONS")
    print("="*70 + "\n")

    # Test 1: Multiple detections with reflectivity
    detections_dbz = [
        HailDetection(32.7, -96.8, 1.5, '2024-11-15T14:00:00', reflectivity=55),
        HailDetection(32.75, -96.7, 1.75, '2024-11-15T14:10:00', reflectivity=60),
        HailDetection(32.8, -96.6, 2.0, '2024-11-15T14:20:00', reflectivity=58),
    ]

    rec = SwathGenerator.get_recommended_method(detections=detections_dbz)
    print(f"  Multiple detections with dBZ:")
    print(f"    Recommendation: {rec}")
    print()

    # Test 2: Multiple detections without reflectivity
    detections_no_dbz = [
        HailDetection(32.7, -96.8, 1.5, '2024-11-15T14:00:00'),
        HailDetection(32.75, -96.7, 1.75, '2024-11-15T14:10:00'),
        HailDetection(32.8, -96.6, 2.0, '2024-11-15T14:20:00'),
    ]

    rec = SwathGenerator.get_recommended_method(detections=detections_no_dbz)
    print(f"  Multiple detections without dBZ:")
    print(f"    Recommendation: {rec}")
    print()

    # Test 3: Storm track
    track = StormTrack(
        start_lat=32.7, start_lon=-97.0,
        end_lat=32.9, end_lon=-96.8,
        start_time='2024-11-15T14:00:00',
        end_time='2024-11-15T14:30:00',
        motion_dir=45, motion_speed=40, max_hail=1.75
    )

    rec = SwathGenerator.get_recommended_method(track=track)
    print(f"  Storm track provided:")
    print(f"    Recommendation: {rec}")
    print()

    # Test 4: Movement data only
    rec = SwathGenerator.get_recommended_method(has_movement_data=True)
    print(f"  Movement data only:")
    print(f"    Recommendation: {rec}")
    print()

    # Test 5: Minimum data
    rec = SwathGenerator.get_recommended_method()
    print(f"  Minimum data:")
    print(f"    Recommendation: {rec}")
    print()

    print("="*70)
    print("METHOD RECOMMENDATIONS TESTS COMPLETE")
    print("="*70 + "\n")


def test_edge_cases():
    """Test edge cases for swath generation"""
    print("\n" + "="*70)
    print("TESTING EDGE CASES")
    print("="*70 + "\n")

    # Test 1: Single detection falls back to circular
    print("[1/3] Single detection -> circular fallback...")
    single = [HailDetection(32.7, -96.8, 1.5, '2024-11-15T14:00:00')]
    swath = SwathGenerator.create_composite_swath(single)
    print(f"  Method: {swath['properties']['method']}")
    print(f"  (Expected: circular)")
    print()

    # Test 2: Mixed reflectivity data
    print("[2/3] Mixed reflectivity data (some None)...")
    mixed = [
        HailDetection(32.7, -96.8, 1.5, '2024-11-15T14:00:00', reflectivity=55),
        HailDetection(32.75, -96.7, 1.75, '2024-11-15T14:10:00'),  # No dBZ
        HailDetection(32.8, -96.6, 2.0, '2024-11-15T14:20:00', reflectivity=60),
    ]
    swath = SwathGenerator.create_reflectivity_swath(mixed)
    print(f"  Method: {swath['properties']['method']}")
    print(f"  Detections used: {swath['properties']['detection_count']}")
    print()

    # Test 3: Auto-generate with insufficient data
    print("[3/3] Auto-generate with insufficient data...")
    try:
        SwathGenerator.auto_generate_swath()
        print("  ERROR: Should have raised ValueError")
    except ValueError as e:
        print(f"  Correctly raised ValueError: {str(e)[:50]}...")
    print()

    print("="*70)
    print("EDGE CASE TESTS COMPLETE")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_advanced_swaths()
    test_method_recommendations()
    test_edge_cases()
