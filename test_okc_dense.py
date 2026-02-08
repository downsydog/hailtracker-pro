"""
Test dense urban area tiles
"""

import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("OKC TEST - DENSE URBAN AREA")
print("=" * 70)
print()

# Get swaths
db_path = os.path.join(os.path.dirname(__file__), 'data', 'hailtracker_crm.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cursor = conn.execute('''
    SELECT id, event_name, max_hail_size, swath_polygon
    FROM hail_events
    WHERE event_date = '2025-10-23'
    AND event_name LIKE '%Oklahoma%'
    AND swath_polygon IS NOT NULL
    ORDER BY max_hail_size DESC
''')

swaths = []
for row in cursor.fetchall():
    try:
        polygon = json.loads(row['swath_polygon'])
        swaths.append({'event_id': row['id'], 'polygon': polygon, **polygon})
    except:
        pass
conn.close()

print(f"Swaths: {len(swaths)}")

# Generate tiles
from src.business.tile_system import SwathTileSystem
ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)
print(f"Total tiles: {len(tiles)}")

# Find dense tiles - middle of the list, near OKC center
# OKC center is ~35.47, -97.52
# Find tiles near that location
okc_lat, okc_lon = 35.47, -97.52
dense_tiles = []
for tile in tiles:
    dist = ((tile.center_lat - okc_lat)**2 + (tile.center_lon - okc_lon)**2)**0.5
    if dist < 0.15:  # Within ~10 miles
        dense_tiles.append(tile)

print(f"Tiles near OKC center: {len(dense_tiles)}")

# Use first 30 of these
test_tiles = dense_tiles[:30]
print(f"Testing {len(test_tiles)} tiles near urban center")
print()

# Search with Yelp
from src.fleet.apis.yelp_api import YelpAPI
yelp = YelpAPI()

all_businesses = []
print("Searching...")
for i, tile in enumerate(test_tiles):
    try:
        radius = int(tile.search_radius_miles * 1609.34)
        results = yelp.search_all_categories(tile.center_lat, tile.center_lon, radius)
        for r in results:
            r['source'] = 'yelp'
            r['tile_id'] = tile.tile_id
        all_businesses.extend(results)
        if (i + 1) % 5 == 0:
            print(f"  {i+1}/{len(test_tiles)} - {len(all_businesses)} raw")
    except Exception as e:
        print(f"  ERROR: {e}")

print()
print(f"RAW: {len(all_businesses)}")
print()

# Dedup
from src.business.deduplication import deduplicate_businesses, analyze_duplicates

analysis = analyze_duplicates(all_businesses)
print("ANALYSIS:")
print(f"  Unique phones: {analysis['unique_phones']}")
print(f"  Phone dupes: {analysis['phone_duplicates']}")
print()

deduped = deduplicate_businesses(all_businesses, merge_data=True)

print("=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Raw: {len(all_businesses)}")
print(f"After dedup: {len(deduped)}")
print(f"Removed: {len(all_businesses) - len(deduped)}")
print(f"DEDUP RATE: {(len(all_businesses) - len(deduped))*100/max(len(all_businesses),1):.1f}%")
print()

# Categories
categories = {}
for biz in deduped:
    cat = biz.get('category', 'other')
    categories[cat] = categories.get(cat, 0) + 1

print("CATEGORIES:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
    print(f"  {cat}: {count}")

# Extrapolate to full
if len(deduped) > 0:
    ratio = len(tiles) / len(test_tiles)
    print()
    print(f"EXTRAPOLATION to {len(tiles)} tiles:")
    print(f"  Estimated unique: ~{int(len(deduped) * ratio * 0.3)} (accounting for more overlap)")
    print(f"  Kyle's target: 3,539")
