"""
Analyze tile generation - are we tiling bounding boxes or actual polygons?
"""

import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("TILE GENERATION ANALYSIS")
print("=" * 70)
print()

# Get all OKC swaths
db_path = os.path.join(os.path.dirname(__file__), 'data', 'hailtracker_crm.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cursor = conn.execute('''
    SELECT id, event_name, max_hail_size, swath_polygon
    FROM hail_events
    WHERE event_date = '2025-10-23'
    AND event_name LIKE '%Oklahoma%'
    AND swath_polygon IS NOT NULL
''')

swaths = []
for row in cursor.fetchall():
    try:
        polygon = json.loads(row['swath_polygon'])
        swaths.append({
            'event_id': row['id'],
            'event_name': row['event_name'],
            'polygon': polygon,
            **polygon
        })
    except:
        pass
conn.close()

print(f"Total swaths: {len(swaths)}")
print()

# Calculate actual polygon area using shoelace formula
def polygon_area_sq_miles(coords):
    """Calculate area of polygon in square miles using shoelace formula."""
    if not coords or len(coords) < 3:
        return 0

    # Coords are [lon, lat] pairs
    n = len(coords)
    area = 0
    for i in range(n):
        j = (i + 1) % n
        # lat/lon to approximate sq miles (rough: 1 deg lat = 69 mi, 1 deg lon = 54 mi at 35N)
        area += coords[i][0] * coords[j][1]
        area -= coords[j][0] * coords[i][1]

    area = abs(area) / 2
    # Convert from deg^2 to sq miles (very rough approximation)
    area_sq_miles = area * 69 * 54  # lat_miles_per_deg * lon_miles_per_deg
    return area_sq_miles

# Calculate total swath area
total_area = 0
for swath in swaths:
    coords = None
    if swath.get('type') == 'Polygon':
        coords = swath['coordinates'][0]
    elif swath.get('type') == 'Feature':
        coords = swath['geometry']['coordinates'][0]

    if coords:
        area = polygon_area_sq_miles(coords)
        total_area += area

print(f"Total swath polygon area: {total_area:.1f} sq miles")
print()

# Generate tiles and analyze
from src.business.tile_system import SwathTileSystem

ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)

print(f"Tiles generated: {len(tiles)}")
print(f"Tile size: 0.25 sq miles")
print(f"Total tile area: {len(tiles) * 0.25:.1f} sq miles")
print()

# Check if tiles are inside polygons
def point_in_polygon(lat, lon, coords):
    """Ray casting algorithm to check if point is inside polygon."""
    n = len(coords)
    inside = False

    p1_lon, p1_lat = coords[0]
    for i in range(1, n + 1):
        p2_lon, p2_lat = coords[i % n]
        if lat > min(p1_lat, p2_lat):
            if lat <= max(p1_lat, p2_lat):
                if lon <= max(p1_lon, p2_lon):
                    if p1_lat != p2_lat:
                        xinters = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                    if p1_lon == p2_lon or lon <= xinters:
                        inside = not inside
        p1_lon, p1_lat = p2_lon, p2_lat

    return inside

# Check each tile
tiles_inside = 0
tiles_outside = 0

for tile in tiles:
    is_inside = False
    for swath in swaths:
        coords = None
        if swath.get('type') == 'Polygon':
            coords = swath['coordinates'][0]
        elif swath.get('type') == 'Feature':
            coords = swath['geometry']['coordinates'][0]

        if coords and point_in_polygon(tile.center_lat, tile.center_lon, coords):
            is_inside = True
            break

    if is_inside:
        tiles_inside += 1
    else:
        tiles_outside += 1

print(f"Tiles INSIDE swath polygons: {tiles_inside}")
print(f"Tiles OUTSIDE swath polygons: {tiles_outside}")
print(f"Percentage outside: {tiles_outside*100/len(tiles):.1f}%")
print()

# Expected vs actual
expected_tiles = int(total_area / 0.25)
print("=" * 70)
print("ANALYSIS")
print("=" * 70)
print(f"Expected tiles (area/tile_size): {expected_tiles}")
print(f"Actual tiles generated: {len(tiles)}")
print(f"Tiles inside polygons: {tiles_inside}")
print(f"Ratio (actual/expected): {len(tiles)/max(expected_tiles,1):.1f}x")
print()

if tiles_outside > tiles_inside:
    print("WARNING: More tiles OUTSIDE than INSIDE!")
    print("The tile system is using bounding boxes, not actual polygons.")
    print("This wastes API calls on areas with NO hail damage.")
elif tiles_outside > len(tiles) * 0.2:
    print("WARNING: >20% of tiles are outside swath polygons.")
    print("Consider filtering tiles to only those inside polygons.")
else:
    print("OK: Most tiles are inside swath polygons.")
