"""
MESH Grid Visualization Export

Demonstrates the MESH grid calculation and exports visualization data
for use in GeoJSON viewers (geojson.io, QGIS, etc.)
"""

import os
import sys
import json
import math

sys.path.insert(0, '.')

from src.radar.mesh_algorithm import MESHAlgorithm, MESHGrid, get_freezing_levels_by_region
from src.radar.swath_generator import SwathGenerator, HailDetection


def create_simulated_storm_data(
    center_lat: float,
    center_lon: float,
    storm_dir: float = 45,  # Northeast
    storm_length_miles: float = 25
) -> list:
    """
    Create simulated storm radar data for MESH grid calculation

    Simulates a supercell storm moving in specified direction with:
    - High reflectivity core (65-75 dBZ)
    - Surrounding moderate reflectivity (50-60 dBZ)
    - Gradient from core outward

    Args:
        center_lat: Storm center latitude
        center_lon: Storm center longitude
        storm_dir: Storm motion direction (degrees from north)
        storm_length_miles: Length of storm track (miles)

    Returns:
        List of {lat, lon, reflectivity, storm_top} dicts
    """
    data_points = []

    # Convert direction to radians (meteorological to mathematical)
    bearing_rad = math.radians(90 - storm_dir)

    # Convert miles to degrees
    miles_per_deg = 69.0

    # Create storm core and gradient
    # Storm moves from southwest to northeast if dir=45

    # Generate points along storm track
    num_track_points = 20
    track_half_length = storm_length_miles / 2

    for i in range(num_track_points):
        # Position along track (relative to center)
        track_pos = -track_half_length + (i / (num_track_points - 1)) * storm_length_miles

        # Calculate lat/lon offset
        track_lat_offset = (track_pos / miles_per_deg) * math.sin(bearing_rad + math.pi/2)
        track_lon_offset = (track_pos / miles_per_deg) * math.cos(bearing_rad + math.pi/2) / math.cos(math.radians(center_lat))

        track_lat = center_lat + track_lat_offset
        track_lon = center_lon + track_lon_offset

        # Generate radial points around this track position
        # Reflectivity decreases with distance from track

        # Core point (highest reflectivity)
        # Peak in center, diminishing at ends
        center_factor = 1 - abs(track_pos / track_half_length) * 0.3
        core_ref = 65 + (10 * center_factor)  # 65-75 dBZ

        data_points.append({
            'lat': track_lat,
            'lon': track_lon,
            'reflectivity': core_ref,
            'storm_top': 12 + (2 * center_factor)  # 12-14 km
        })

        # Surrounding points (moderate reflectivity)
        for radius_miles in [1, 2, 3, 4, 5]:
            for angle_offset in [0, 60, 120, 180, 240, 300]:
                angle_rad = math.radians(angle_offset) + bearing_rad

                lat_offset = (radius_miles / miles_per_deg) * math.cos(angle_rad)
                lon_offset = (radius_miles / miles_per_deg) * math.sin(angle_rad) / math.cos(math.radians(track_lat))

                # Reflectivity decreases with distance
                ref = max(40, core_ref - (radius_miles * 5))  # -5 dBZ per mile

                data_points.append({
                    'lat': track_lat + lat_offset,
                    'lon': track_lon + lon_offset,
                    'reflectivity': ref,
                    'storm_top': max(8, 12 - radius_miles * 0.5)
                })

    return data_points


def export_mesh_grid_geojson(output_dir: str = 'data'):
    """
    Export MESH grid as GeoJSON heatmap

    Creates:
    1. Point layer with MESH values at each grid cell
    2. Polygon layer with MESH contours
    3. Storm track detections as points
    """
    print("=" * 70)
    print("MESH GRID VISUALIZATION EXPORT")
    print("=" * 70)
    print()

    os.makedirs(output_dir, exist_ok=True)

    # ========================================================================
    # 1. CREATE SIMULATED STORM DATA
    # ========================================================================

    print("[1/5] Creating simulated storm data...")

    # DFW area supercell
    storm_center_lat = 32.78
    storm_center_lon = -96.85

    storm_data = create_simulated_storm_data(
        center_lat=storm_center_lat,
        center_lon=storm_center_lon,
        storm_dir=45,  # Moving NE
        storm_length_miles=20
    )

    print(f"  Created {len(storm_data)} simulated radar points")
    print()

    # ========================================================================
    # 2. CALCULATE MESH GRID
    # ========================================================================

    print("[2/5] Calculating MESH grid...")

    # Get seasonal freezing levels for Texas (spring storm season)
    h0, h20 = get_freezing_levels_by_region('texas', month=4)  # April
    print(f"  Freezing levels: H0={h0}km, H-20={h20}km")

    mesh_grid = MESHGrid(freezing_level_km=h0, minus20_level_km=h20)

    # Calculate grid (use smaller range for faster demo)
    grid = mesh_grid.calculate_mesh_grid(
        radar_lat=storm_center_lat,
        radar_lon=storm_center_lon,
        reflectivity_data=storm_data,
        grid_resolution=0.005,  # ~0.5 km resolution
        range_km=50  # 50 km range for demo
    )

    print(f"  Grid size: {grid['grid_size'][0]} x {grid['grid_size'][1]}")
    print(f"  Max MESH: {grid['max_mesh']}\"")
    print(f"  Severe pixels (2\"+): {grid['severe_pixels']}")
    print(f"  Significant pixels (1-2\"): {grid['significant_pixels']}")
    print()

    # ========================================================================
    # 3. EXPORT MESH GRID AS POINTS (HEATMAP)
    # ========================================================================

    print("[3/5] Exporting MESH grid points...")

    features = []
    bounds = grid['bounds']
    resolution = grid['resolution']

    for row_idx, row in enumerate(grid['mesh_values']):
        for col_idx, mesh_value in enumerate(row):
            if mesh_value > 0:  # Only include non-zero values
                lat = bounds['north'] - (row_idx + 0.5) * resolution
                lon = bounds['west'] + (col_idx + 0.5) * resolution

                # Color based on MESH value
                if mesh_value >= 2.0:
                    color = '#ff0000'  # Red - severe
                    size = 'large'
                elif mesh_value >= 1.0:
                    color = '#ff6600'  # Orange - significant
                    size = 'medium'
                elif mesh_value >= 0.5:
                    color = '#ffcc00'  # Yellow - moderate
                    size = 'small'
                else:
                    color = '#00cc00'  # Green - marginal
                    size = 'small'

                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [lon, lat]
                    },
                    'properties': {
                        'mesh_inches': round(mesh_value, 2),
                        'marker-color': color,
                        'marker-size': size
                    }
                })

    grid_geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    grid_file = os.path.join(output_dir, 'mesh_grid_points.geojson')
    with open(grid_file, 'w') as f:
        json.dump(grid_geojson, f, indent=2)

    print(f"  Exported {len(features)} points to {grid_file}")
    print()

    # ========================================================================
    # 4. EXPORT MESH CONTOURS
    # ========================================================================

    print("[4/5] Extracting MESH contours...")

    # Extract contours at different thresholds
    contour_features = []

    thresholds = [
        (2.0, '#ff0000', 'Severe (2\"+)'),
        (1.5, '#ff6600', 'Large (1.5\"+)'),
        (1.0, '#ffcc00', 'Significant (1\"+)'),
        (0.75, '#00cc00', 'Moderate (0.75\"+)')
    ]

    for threshold, color, label in thresholds:
        contours = mesh_grid.extract_mesh_contours(grid, threshold)
        print(f"  {label}: {len(contours)} regions")

        for contour in contours:
            contour['properties']['stroke'] = color
            contour['properties']['stroke-width'] = 2
            contour['properties']['fill'] = color
            contour['properties']['fill-opacity'] = 0.3
            contour['properties']['label'] = label
            contour_features.append(contour)

    contour_geojson = {
        'type': 'FeatureCollection',
        'features': contour_features
    }

    contour_file = os.path.join(output_dir, 'mesh_contours.geojson')
    with open(contour_file, 'w') as f:
        json.dump(contour_geojson, f, indent=2)

    print(f"  Exported to {contour_file}")
    print()

    # ========================================================================
    # 5. CREATE MESH-ENHANCED SWATH
    # ========================================================================

    print("[5/5] Creating MESH-enhanced swath...")

    # Create detections from storm data (sample high-reflectivity points)
    detections = []
    high_ref_points = sorted(
        [p for p in storm_data if p['reflectivity'] >= 55],
        key=lambda p: p['reflectivity'],
        reverse=True
    )[:10]  # Top 10 points

    for i, p in enumerate(high_ref_points):
        det = HailDetection(
            lat=p['lat'],
            lon=p['lon'],
            hail_size=1.0,  # Will be overridden by MESH
            timestamp=f'2024-11-15T14:{i*5:02d}:00',
            reflectivity=p['reflectivity']
        )
        detections.append(det)

    # Generate MESH-enhanced swath
    swath = SwathGenerator.create_mesh_enhanced_swath(
        detections,
        freezing_level_km=h0,
        storm_top_km=12.0
    )

    # Add styling for visualization
    swath['properties']['stroke'] = swath['properties']['threat_color']
    swath['properties']['stroke-width'] = 3
    swath['properties']['fill'] = swath['properties']['threat_color']
    swath['properties']['fill-opacity'] = 0.4

    swath_geojson = {
        'type': 'FeatureCollection',
        'features': [{
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': swath['coordinates']
            },
            'properties': swath['properties']
        }]
    }

    swath_file = os.path.join(output_dir, 'mesh_swath.geojson')
    with open(swath_file, 'w') as f:
        json.dump(swath_geojson, f, indent=2)

    print(f"  Max MESH: {swath['properties']['mesh_max_inches']}\"")
    print(f"  Threat level: {swath['properties']['threat_level']}")
    print(f"  Area: {swath['properties']['area_sq_miles']} sq mi")
    print(f"  Exported to {swath_file}")
    print()

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("=" * 70)
    print("MESH VISUALIZATION EXPORT COMPLETE")
    print("=" * 70)
    print()
    print("Files created:")
    print(f"  1. {grid_file}")
    print("     - Point layer showing MESH values across grid")
    print("     - Color-coded by hail size category")
    print()
    print(f"  2. {contour_file}")
    print("     - Polygon contours at 0.75\", 1.0\", 1.5\", 2.0\" thresholds")
    print("     - Shows hail intensity zones")
    print()
    print(f"  3. {swath_file}")
    print("     - MESH-enhanced swath polygon")
    print("     - Includes threat classification")
    print()
    print("View files at: https://geojson.io")
    print()

    return {
        'grid_file': grid_file,
        'contour_file': contour_file,
        'swath_file': swath_file,
        'statistics': {
            'max_mesh': grid['max_mesh'],
            'severe_pixels': grid['severe_pixels'],
            'significant_pixels': grid['significant_pixels'],
            'grid_points': len(features)
        }
    }


def print_mesh_legend():
    """Print MESH interpretation legend"""
    print()
    print("MESH INTERPRETATION GUIDE")
    print("=" * 50)
    print()
    print("  MESH Size     Category        Expected Damage")
    print("  " + "-" * 46)
    print("  < 0.50\"       Marginal        Minimal/None")
    print("  0.50-0.75\"    Small           Possible minor")
    print("  0.75-1.00\"    Moderate        Dents, bruised vegetation")
    print("  1.00-1.50\"    Significant     Vehicle dents, shingles")
    print("  1.50-2.00\"    Large           Broken windows, roof damage")
    print("  2.00-2.50\"    Severe          Major vehicle damage")
    print("  2.50-3.00\"    Very Severe     Structural damage")
    print("  > 3.00\"       Giant           Catastrophic damage")
    print()
    print("  POSH (Probability of Severe Hail):")
    print("  " + "-" * 46)
    print("  < 30%         Low probability of 1\"+ hail")
    print("  30-60%        Moderate probability")
    print("  60-80%        High probability")
    print("  > 80%         Very high probability")
    print()


if __name__ == '__main__':
    print_mesh_legend()
    export_mesh_grid_geojson()
