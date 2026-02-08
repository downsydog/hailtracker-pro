"""
Visualize different hail sizes as circular swaths
Creates multiple swaths for comparison
"""

import json
from src.radar.swath_generator import SwathGenerator

def create_comparison_visualization():
    print("\n" + "="*70)
    print("CREATING SWATH SIZE COMPARISON")
    print("="*70 + "\n")

    # Dallas location
    dallas_lat = 32.7767
    dallas_lon = -96.7970

    # Different hail sizes to compare
    hail_sizes = [
        (0.75, "Penny", "#90EE90"),      # Light green
        (1.00, "Quarter", "#FFD700"),    # Gold
        (1.75, "Golf Ball", "#FFA500"),  # Orange
        (2.50, "Tennis Ball", "#FF6347"), # Tomato red
        (4.00, "Softball", "#DC143C")    # Crimson
    ]

    features = []

    print("Creating swaths for comparison:")
    print()

    for size, name, color in hail_sizes:
        swath = SwathGenerator.create_circular_swath(
            lat=dallas_lat,
            lon=dallas_lon,
            hail_size_inches=size
        )

        area = SwathGenerator.calculate_swath_area(swath)
        radius = swath['properties']['radius_miles']

        # Add to features
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': swath['type'],
                'coordinates': swath['coordinates']
            },
            'properties': {
                'name': f'{size}" - {name}',
                'hail_size': size,
                'radius_miles': radius,
                'area_sq_miles': area,
                'fill': color,
                'fill-opacity': 0.3,
                'stroke': color,
                'stroke-width': 2
            }
        })

        print(f"  {size:4.2f}\" ({name:12s}): {radius:5.2f} mi radius, ~{area:6.1f} sq mi")

    # Add center marker
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [dallas_lon, dallas_lat]
        },
        'properties': {
            'name': 'Dallas Detection Point',
            'marker-color': '#000000',
            'marker-size': 'large'
        }
    })

    # Create GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save
    with open('data/swath_comparison.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)

    print()
    print("  Saved: data/swath_comparison.geojson")
    print()
    print("VISUALIZATION:")
    print("  -> Open data/swath_comparison.geojson at geojson.io")
    print("  -> See all 5 hail sizes overlaid")
    print("  -> Notice how swath radius scales with hail size")
    print()

if __name__ == '__main__':
    import os
    os.makedirs('data', exist_ok=True)
    create_comparison_visualization()
