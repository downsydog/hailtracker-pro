"""
Visualize radar coverage for a location
Creates GeoJSON files showing radar coverage areas
"""

import os
import json
import math
from src.radar.radar_network import RadarNetwork


def create_coverage_circle(lat: float, lon: float, radius_km: float, points: int = 36) -> list:
    """Create a circle polygon as a list of coordinates"""
    circle_points = []

    for i in range(points + 1):
        angle = (i / points) * 360
        angle_rad = math.radians(angle)

        # Calculate offset in degrees
        d_lat = (radius_km / 111.0) * math.cos(angle_rad)
        d_lon = (radius_km / (111.0 * math.cos(math.radians(lat)))) * math.sin(angle_rad)

        circle_points.append([
            round(lon + d_lon, 6),
            round(lat + d_lat, 6)
        ])

    return circle_points


def visualize_coverage(lat: float, lon: float, location_name: str):
    """Create GeoJSON showing radar coverage for a location"""

    print(f"\nCreating coverage map for {location_name}")
    print(f"   Location: {lat:.4f}, {lon:.4f}")
    print()

    network = RadarNetwork()

    # Find covering radars
    radars = network.find_covering_radars(lat, lon, max_radars=5)

    features = []

    # Add location marker
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [lon, lat]
        },
        'properties': {
            'name': location_name,
            'type': 'target',
            'marker-color': '#FF0000',
            'marker-size': 'large',
            'marker-symbol': 'star'
        }
    })

    # Colors for different radars
    colors = ['#0066FF', '#00CC00', '#FF00FF', '#FF9900', '#00CCCC']

    # Add radar coverage for each radar
    for i, radar_info in enumerate(radars):
        site = radar_info['site']
        distance = radar_info['distance_km']
        quality = radar_info['quality']
        color = colors[i % len(colors)]

        # Create 100km coverage circle (excellent coverage)
        excellent_circle = create_coverage_circle(site.lat, site.lon, 100)
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [excellent_circle]
            },
            'properties': {
                'name': f'{site.name} - Excellent Coverage',
                'radar': site.id,
                'coverage': 'excellent',
                'range_km': 100,
                'stroke': color,
                'stroke-width': 2,
                'fill': color,
                'fill-opacity': 0.15
            }
        })

        # Create 150km coverage circle (good coverage)
        good_circle = create_coverage_circle(site.lat, site.lon, 150)
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [good_circle]
            },
            'properties': {
                'name': f'{site.name} - Good Coverage',
                'radar': site.id,
                'coverage': 'good',
                'range_km': 150,
                'stroke': color,
                'stroke-width': 1,
                'stroke-dasharray': '5,5',
                'fill': color,
                'fill-opacity': 0.08
            }
        })

        # Add radar location marker
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [site.lon, site.lat]
            },
            'properties': {
                'name': f'{site.name} ({site.id})',
                'type': 'radar',
                'distance_km': round(distance, 1),
                'quality': quality,
                'marker-color': color,
                'marker-size': 'medium',
                'marker-symbol': 'communications-tower'
            }
        })

        # Add line from radar to target
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': [
                    [site.lon, site.lat],
                    [lon, lat]
                ]
            },
            'properties': {
                'name': f'Path from {site.id}',
                'distance_km': round(distance, 1),
                'stroke': color,
                'stroke-width': 1,
                'stroke-opacity': 0.5
            }
        })

    # Create GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save
    safe_name = location_name.replace(" ", "_").replace(",", "").replace(".", "")
    filename = f'data/radar_coverage_{safe_name}.geojson'
    with open(filename, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"Saved to {filename}")
    print()
    print("RADARS COVERING THIS LOCATION:")
    for radar_info in radars:
        site = radar_info['site']
        print(f"  {site.name} ({site.id}): {radar_info['distance_km']:.1f} km - {radar_info['quality']}")
    print()

    return filename


def visualize_all_radars_in_region(
    center_lat: float,
    center_lon: float,
    region_name: str,
    radius_km: float = 300
):
    """Create GeoJSON showing all radars in a region"""

    print(f"\nCreating regional radar map for {region_name}")
    print(f"   Center: {center_lat:.4f}, {center_lon:.4f}")
    print(f"   Radius: {radius_km} km")
    print()

    network = RadarNetwork()

    # Find all radars in region
    all_radars = network.find_covering_radars(
        center_lat, center_lon,
        max_radars=20,
        max_distance_km=radius_km
    )

    features = []

    # Add each radar with coverage
    for radar_info in all_radars:
        site = radar_info['site']

        # Add 100km coverage circle
        coverage_circle = create_coverage_circle(site.lat, site.lon, 100)
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [coverage_circle]
            },
            'properties': {
                'name': f'{site.name} Coverage',
                'radar': site.id,
                'stroke': '#0066FF',
                'stroke-width': 1,
                'fill': '#0066FF',
                'fill-opacity': 0.1
            }
        })

        # Add radar marker
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [site.lon, site.lat]
            },
            'properties': {
                'name': f'{site.name} ({site.id})',
                'marker-color': '#0066FF',
                'marker-size': 'small'
            }
        })

    # Add center marker
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [center_lon, center_lat]
        },
        'properties': {
            'name': f'{region_name} Center',
            'marker-color': '#FF0000',
            'marker-size': 'large'
        }
    })

    # Create GeoJSON
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save
    safe_name = region_name.replace(" ", "_").replace(",", "")
    filename = f'data/radar_network_{safe_name}.geojson'
    with open(filename, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"Saved to {filename}")
    print(f"Found {len(all_radars)} radars in region")
    print()

    return filename


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)

    print("="*70)
    print("RADAR COVERAGE VISUALIZATION")
    print("="*70)

    # Create coverage maps for major cities
    visualize_coverage(32.7767, -96.7970, "Dallas TX")
    visualize_coverage(35.4676, -97.5164, "Oklahoma City OK")
    visualize_coverage(39.7392, -104.9903, "Denver CO")

    # Create regional map of Central US (Tornado Alley)
    visualize_all_radars_in_region(
        35.0, -98.0,
        "Central_US_Tornado_Alley",
        radius_km=500
    )

    print("="*70)
    print("VISUALIZATION COMPLETE")
    print("="*70)
    print()
    print("OUTPUT FILES:")
    print("  data/radar_coverage_Dallas_TX.geojson")
    print("  data/radar_coverage_Oklahoma_City_OK.geojson")
    print("  data/radar_coverage_Denver_CO.geojson")
    print("  data/radar_network_Central_US_Tornado_Alley.geojson")
    print()
    print("View at geojson.io to see radar coverage!")
    print()
