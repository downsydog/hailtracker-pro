"""
Example: Real storm with multiple radar detections over time
"""

import json
from datetime import datetime, timedelta
from src.radar.swath_generator import SwathGenerator, HailDetection

def create_realistic_multi_detection():
    print("\n" + "="*70)
    print("REALISTIC MULTI-DETECTION SCENARIO")
    print("="*70 + "\n")

    print("Scenario: Supercell tracking northeast across DFW")
    print("Duration: 45 minutes")
    print("Path: Southwest to northeast")
    print()

    # Simulate radar detections every 5 minutes
    # Storm moving NE at ~40 mph
    base_time = datetime(2024, 11, 15, 14, 30, 0)

    detections = []

    # Storm track (SW to NE) - intensifies then weakens
    positions = [
        (32.65, -97.00, 1.25),  # Start (SW) - developing
        (32.70, -96.95, 1.50),  # Intensifying
        (32.75, -96.90, 1.75),  # Intensifying
        (32.80, -96.85, 2.00),  # Peak intensity
        (32.85, -96.80, 2.25),  # Peak intensity
        (32.90, -96.75, 1.75),  # Weakening
        (32.95, -96.70, 1.50),  # Weakening
        (33.00, -96.65, 1.25),  # Weakening
        (33.05, -96.60, 1.00)   # End (NE) - dissipating
    ]

    print("Radar Detections:")
    print("-" * 55)
    for i, (lat, lon, hail_size) in enumerate(positions):
        timestamp = (base_time + timedelta(minutes=i*5)).isoformat()
        det = HailDetection(lat=lat, lon=lon, hail_size=hail_size, timestamp=timestamp)
        detections.append(det)

        # Determine storm phase
        if i < 2:
            phase = "Developing"
        elif i < 5:
            phase = "Mature"
        else:
            phase = "Weakening"

        print(f"  T+{i*5:2d} min: ({lat:.2f}, {lon:.2f}) - {hail_size:.2f}\" hail [{phase}]")

    print("-" * 55)
    print()

    # Create composite swath
    print("Creating composite swath from all detections...")
    composite = SwathGenerator.create_composite_swath(detections)
    area = SwathGenerator.calculate_swath_area(composite)

    print(f"\n  Composite swath:")
    print(f"   Detections: {composite['properties']['detection_count']}")
    print(f"   Max hail: {composite['properties']['max_hail_size']}\"")
    print(f"   Track length: {composite['properties']['track_length_miles']:.1f} mi")
    print(f"   Swath width: {composite['properties']['width_miles']:.1f} mi")
    print(f"   Total area: ~{area:.1f} sq mi")
    print(f"   Duration: {composite['properties']['start_time']} to {composite['properties']['end_time']}")
    print()

    # Calculate estimated storm speed
    track_miles = composite['properties']['track_length_miles']
    duration_min = 40  # 9 detections * 5 min = 45 min, but 40 min between first and last
    storm_speed = track_miles / (duration_min / 60)
    print(f"   Estimated storm speed: ~{storm_speed:.0f} mph")
    print()

    # Create visualization
    features = []

    # Add composite swath
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': composite['type'],
            'coordinates': composite['coordinates']
        },
        'properties': {
            'name': 'Hail Swath',
            'description': 'Composite swath from 45-minute supercell',
            'fill': '#FF4500',
            'fill-opacity': 0.4,
            'stroke': '#FF0000',
            'stroke-width': 3
        }
    })

    # Add storm track line
    track_coords = [[det.lon, det.lat] for det in detections]
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': track_coords
        },
        'properties': {
            'name': 'Storm Track',
            'stroke': '#000000',
            'stroke-width': 2
        }
    })

    # Add detection points with color coding by intensity
    for i, det in enumerate(detections):
        # Color code by hail size
        if det.hail_size >= 2.0:
            color = '#DC143C'  # Crimson - severe
        elif det.hail_size >= 1.5:
            color = '#FFA500'  # Orange - significant
        else:
            color = '#FFD700'  # Gold - moderate

        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [det.lon, det.lat]
            },
            'properties': {
                'name': f'T+{i*5} min ({det.hail_size}")',
                'hail_size': det.hail_size,
                'timestamp': det.timestamp,
                'marker-color': color,
                'marker-size': 'small'
            }
        })

    # Add start and end markers
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [detections[0].lon, detections[0].lat]
        },
        'properties': {
            'name': 'STORM START',
            'marker-color': '#00FF00',
            'marker-size': 'large',
            'marker-symbol': 'star'
        }
    })

    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [detections[-1].lon, detections[-1].lat]
        },
        'properties': {
            'name': 'STORM END',
            'marker-color': '#0000FF',
            'marker-size': 'large',
            'marker-symbol': 'square'
        }
    })

    # Create GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save
    with open('data/realistic_supercell_track.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)

    print("  Saved: data/realistic_supercell_track.geojson")
    print()
    print("VISUALIZATION:")
    print("  -> Open at geojson.io")
    print("  -> Orange shaded area = hail damage swath")
    print("  -> Black line = storm track")
    print("  -> Colored dots = radar detections (gold=moderate, orange=significant, red=severe)")
    print("  -> Green star = storm start, Blue square = storm end")
    print("  -> Shows complete storm path and damage area!")
    print()

    # Summary statistics
    print("="*70)
    print("STORM SUMMARY")
    print("="*70)
    print(f"  Total track: {track_miles:.1f} miles")
    print(f"  Duration: 45 minutes")
    print(f"  Avg speed: ~{storm_speed:.0f} mph")
    print(f"  Max hail: {max(d.hail_size for d in detections):.2f}\"")
    print(f"  Min hail: {min(d.hail_size for d in detections):.2f}\"")
    print(f"  Damage area: ~{area:.1f} sq mi")
    print()

if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)
    create_realistic_multi_detection()
