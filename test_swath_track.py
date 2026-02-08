"""
Test storm track swath generation
"""

import json
import os
import sys

sys.path.insert(0, '.')

from src.radar.swath_generator import SwathGenerator, StormTrack


def test_track_swaths():
    print("\n" + "="*70)
    print("TESTING STORM TRACK SWATH GENERATION")
    print("="*70 + "\n")

    os.makedirs('data', exist_ok=True)

    # ========================================================================
    # TEST 1: SIMPLE NORTH-SOUTH TRACK
    # ========================================================================

    print("[1/4] Testing north-south storm track...")
    print("Scenario: Storm moving from north Dallas to south Dallas")
    print()

    track_ns = StormTrack(
        start_lat=32.9,
        start_lon=-96.8,
        end_lat=32.6,
        end_lon=-96.8,
        start_time='2024-11-15T14:00:00',
        end_time='2024-11-15T14:30:00',
        motion_dir=180,  # South
        motion_speed=40,
        max_hail=1.75
    )

    swath_ns = SwathGenerator.create_track_swath(track_ns)
    area_ns = SwathGenerator.calculate_swath_area(swath_ns)

    print(f"  North-South track created:")
    print(f"   - Track length: {swath_ns['properties']['track_length_miles']} miles")
    print(f"   - Swath width: {swath_ns['properties']['width_miles']} miles")
    print(f"   - Duration: {swath_ns['properties']['duration_minutes']} minutes")
    print(f"   - Area: ~{area_ns} square miles")
    print()

    # ========================================================================
    # TEST 2: DIAGONAL TRACK (More Realistic)
    # ========================================================================

    print("[2/4] Testing diagonal storm track...")
    print("Scenario: Storm moving southwest to northeast (typical pattern)")
    print()

    track_diag = StormTrack(
        start_lat=32.6,
        start_lon=-97.1,
        end_lat=33.0,
        end_lon=-96.6,
        start_time='2024-11-15T14:00:00',
        end_time='2024-11-15T15:00:00',
        motion_dir=45,  # Northeast
        motion_speed=45,
        max_hail=2.0
    )

    swath_diag = SwathGenerator.create_track_swath(track_diag)
    area_diag = SwathGenerator.calculate_swath_area(swath_diag)

    print(f"  Diagonal track created:")
    print(f"   - Track length: {swath_diag['properties']['track_length_miles']} miles")
    print(f"   - Swath width: {swath_diag['properties']['width_miles']} miles")
    print(f"   - Duration: {swath_diag['properties']['duration_minutes']} minutes")
    print(f"   - Storm speed: {swath_diag['properties']['storm_speed_mph']} mph")
    print(f"   - Area: ~{area_diag} square miles")
    print()

    # ========================================================================
    # TEST 3: DIFFERENT HAIL SIZES
    # ========================================================================

    print("[3/4] Testing different hail sizes on same track...")

    hail_sizes = [1.0, 1.75, 2.5, 4.0]

    for hail_size in hail_sizes:
        track = StormTrack(
            start_lat=32.7,
            start_lon=-97.0,
            end_lat=32.9,
            end_lon=-96.7,
            start_time='2024-11-15T14:00:00',
            end_time='2024-11-15T14:30:00',
            motion_dir=45,
            motion_speed=40,
            max_hail=hail_size
        )

        swath = SwathGenerator.create_track_swath(track)
        width = swath['properties']['width_miles']
        area = SwathGenerator.calculate_swath_area(swath)

        print(f"   - {hail_size}\" hail: {width} mi wide, ~{area} sq mi")

    print()

    # ========================================================================
    # TEST 4: SAVE REALISTIC EXAMPLE
    # ========================================================================

    print("[4/4] Creating realistic Dallas-Fort Worth track...")
    print("Scenario: Supercell crossing DFW metro area")
    print()

    # Realistic DFW supercell track
    track_dfw = StormTrack(
        start_lat=32.55,  # Southwest of Fort Worth
        start_lon=-97.50,
        end_lat=33.05,    # Northeast of Dallas
        end_lon=-96.50,
        start_time='2024-11-15T15:00:00',
        end_time='2024-11-15T16:30:00',  # 90 minute event
        motion_dir=55,    # ENE movement
        motion_speed=50,  # Fast-moving supercell
        max_hail=2.75     # Large hail
    )

    swath_dfw = SwathGenerator.create_track_swath(track_dfw)
    area_dfw = SwathGenerator.calculate_swath_area(swath_dfw)

    print(f"  DFW supercell track:")
    print(f"   - Path: Southwest Fort Worth -> Northeast Dallas")
    print(f"   - Track length: {swath_dfw['properties']['track_length_miles']} miles")
    print(f"   - Swath width: {swath_dfw['properties']['width_miles']} miles")
    print(f"   - Duration: {swath_dfw['properties']['duration_minutes']} minutes")
    print(f"   - Max hail: {track_dfw.max_hail}\"")
    print(f"   - Affected area: ~{area_dfw} square miles")
    print()

    # Save as GeoJSON
    with open('data/sample_track_swath_dfw.geojson', 'w') as f:
        geojson = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': swath_dfw['type'],
                        'coordinates': swath_dfw['coordinates']
                    },
                    'properties': {
                        'name': 'DFW Supercell Track',
                        'event_date': '2024-11-15',
                        'max_hail': track_dfw.max_hail,
                        'storm_type': 'Supercell',
                        'track_length_miles': swath_dfw['properties']['track_length_miles'],
                        'width_miles': swath_dfw['properties']['width_miles']
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [track_dfw.start_lon, track_dfw.start_lat]
                    },
                    'properties': {
                        'name': 'Storm Start',
                        'time': track_dfw.start_time,
                        'marker-color': '#00ff00'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [track_dfw.end_lon, track_dfw.end_lat]
                    },
                    'properties': {
                        'name': 'Storm End',
                        'time': track_dfw.end_time,
                        'marker-color': '#ff0000'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': [
                            [track_dfw.start_lon, track_dfw.start_lat],
                            [track_dfw.end_lon, track_dfw.end_lat]
                        ]
                    },
                    'properties': {
                        'name': 'Storm Track Centerline',
                        'stroke': '#ff6600',
                        'stroke-width': 3
                    }
                }
            ]
        }
        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_track_swath_dfw.geojson")

    # Save comparison with all three methods
    print("\n  Creating method comparison...")

    # Circular swath at center of track
    center_lat = (track_dfw.start_lat + track_dfw.end_lat) / 2
    center_lon = (track_dfw.start_lon + track_dfw.end_lon) / 2

    circular = SwathGenerator.create_circular_swath(
        lat=center_lat,
        lon=center_lon,
        hail_size_inches=track_dfw.max_hail
    )

    elliptical = SwathGenerator.create_elliptical_swath(
        center_lat=center_lat,
        center_lon=center_lon,
        hail_size=track_dfw.max_hail,
        storm_motion_dir=track_dfw.motion_dir,
        storm_motion_speed=track_dfw.motion_speed,
        duration_minutes=90
    )

    with open('data/sample_swath_methods_comparison.geojson', 'w') as f:
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
                        'fill-opacity': 0.2,
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
                        'fill-opacity': 0.2,
                        'stroke': '#00ff00'
                    }
                },
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': swath_dfw['type'],
                        'coordinates': swath_dfw['coordinates']
                    },
                    'properties': {
                        'name': 'Method 3: Track',
                        'method': 'track',
                        'fill': '#0000ff',
                        'fill-opacity': 0.2,
                        'stroke': '#0000ff'
                    }
                }
            ]
        }
        json.dump(geojson, f, indent=2)

    print("  Saved: data/sample_swath_methods_comparison.geojson")

    print()
    print("="*70)
    print("STORM TRACK SWATH TESTS COMPLETE")
    print("="*70)
    print()
    print("KEY FEATURES:")
    print("  - Realistic storm tracks")
    print("  - Rounded end caps")
    print("  - Variable hail sizes")
    print("  - Duration calculations")
    print("  - Method comparison exported")
    print()
    print("View at geojson.io to see the DFW supercell path!")
    print()


if __name__ == '__main__':
    test_track_swaths()
