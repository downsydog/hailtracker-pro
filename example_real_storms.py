"""
Examples of real storm scenarios using elliptical swaths
"""

import json
from src.radar.swath_generator import SwathGenerator

def create_realistic_examples():
    print("\n" + "="*70)
    print("REALISTIC STORM SCENARIOS")
    print("="*70 + "\n")

    scenarios = [
        {
            'name': 'Slow-Moving Supercell',
            'lat': 32.7767,
            'lon': -96.7970,
            'hail_size': 2.5,
            'direction': 30,  # NNE
            'speed': 25,  # mph (slow)
            'duration': 45,  # minutes
            'description': 'Slow-moving supercell, large hail core',
            'color': '#DC143C'  # Crimson
        },
        {
            'name': 'Fast-Moving Squall Line',
            'lat': 35.4676,
            'lon': -97.5164,
            'hail_size': 1.0,
            'direction': 90,  # East
            'speed': 55,  # mph (fast)
            'duration': 20,  # minutes
            'description': 'Fast squall line, brief but intense',
            'color': '#FFA500'  # Orange
        },
        {
            'name': 'Severe Supercell',
            'lat': 33.0,
            'lon': -97.0,
            'hail_size': 3.0,
            'direction': 45,  # NE
            'speed': 40,  # mph
            'duration': 60,  # minutes
            'description': 'Long-lived severe supercell, giant hail',
            'color': '#8B0000'  # Dark red
        },
        {
            'name': 'Multicell Cluster',
            'lat': 30.2672,
            'lon': -97.7431,
            'hail_size': 1.5,
            'direction': 135,  # SE
            'speed': 35,  # mph
            'duration': 30,  # minutes
            'description': 'Multicell cluster moving southeast',
            'color': '#FFD700'  # Gold
        }
    ]

    features = []

    for scenario in scenarios:
        print(f"Creating: {scenario['name']}")

        swath = SwathGenerator.create_elliptical_swath(
            center_lat=scenario['lat'],
            center_lon=scenario['lon'],
            hail_size=scenario['hail_size'],
            storm_motion_dir=scenario['direction'],
            storm_motion_speed=scenario['speed'],
            duration_minutes=scenario['duration']
        )

        area = SwathGenerator.calculate_swath_area(swath)

        print(f"  Path: {swath['properties']['path_length_miles']} mi")
        print(f"  Width: {swath['properties']['width_miles']} mi")
        print(f"  Area: ~{area} sq mi")
        print(f"  {scenario['description']}")
        print()

        # Add to features
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': swath['type'],
                'coordinates': swath['coordinates']
            },
            'properties': {
                'name': scenario['name'],
                'description': scenario['description'],
                'hail_size': scenario['hail_size'],
                'storm_speed': scenario['speed'],
                'duration': scenario['duration'],
                'fill': scenario['color'],
                'fill-opacity': 0.4,
                'stroke': scenario['color'],
                'stroke-width': 2
            }
        })

        # Add center marker for each storm
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [scenario['lon'], scenario['lat']]
            },
            'properties': {
                'name': f"{scenario['name']} Center",
                'marker-color': scenario['color'],
                'marker-size': 'medium'
            }
        })

    # Create GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save
    with open('data/realistic_storm_scenarios.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)

    print("  Saved: data/realistic_storm_scenarios.geojson")
    print()
    print("VISUALIZATION:")
    print("  -> Open at geojson.io to see 4 different storm types")
    print("  -> Notice how speed and duration affect swath shape")
    print("  -> Each swath shows realistic damage pattern")
    print()
    print("STORM TYPE SUMMARY:")
    print("  1. Slow-Moving Supercell: Short but wide damage path")
    print("  2. Fast-Moving Squall Line: Long, narrow damage path")
    print("  3. Severe Supercell: Long-track, wide damage path")
    print("  4. Multicell Cluster: Moderate damage path")
    print()

if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)
    create_realistic_examples()
