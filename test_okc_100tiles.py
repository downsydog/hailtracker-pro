"""
Test 100 dense tiles with proper search radius
"""

import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("OKC TEST - 100 DENSE TILES")
print("=" * 70)
print()

# Get swaths
db_path = os.path.join(os.path.dirname(__file__), 'data', 'hailtracker_crm.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cursor = conn.execute('''
    SELECT id, swath_polygon FROM hail_events
    WHERE event_date = '2025-10-23'
    AND event_name LIKE '%Oklahoma%'
    AND swath_polygon IS NOT NULL
''')

swaths = []
for row in cursor.fetchall():
    try:
        polygon = json.loads(row['swath_polygon'])
        swaths.append({'event_id': row['id'], 'polygon': polygon, **polygon})
    except:
        pass
conn.close()

# Generate tiles
from src.business.tile_system import SwathTileSystem
ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)

# Find dense tiles near OKC center
okc_lat, okc_lon = 35.47, -97.52
dense_tiles = sorted(tiles, key=lambda t: ((t.center_lat - okc_lat)**2 + (t.center_lon - okc_lon)**2)**0.5)
test_tiles = dense_tiles[:100]

print(f"Total tiles: {len(tiles)}")
print(f"Testing 100 tiles nearest OKC center")
print(f"Search radius per tile: {test_tiles[0].search_radius_miles:.2f} miles ({int(test_tiles[0].search_radius_miles * 1609):.0f}m)")
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
        all_businesses.extend(results)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/100 - {len(all_businesses)} raw")
    except Exception as e:
        print(f"  ERROR: {e}")

print()
print(f"RAW: {len(all_businesses)}")

# Deduplicate
from src.business.deduplication import deduplicate_businesses, analyze_duplicates

analysis = analyze_duplicates(all_businesses)
print(f"Unique phones: {analysis['unique_phones']}")
print(f"Phone dupes: {analysis['phone_duplicates']}")
print()

deduped = deduplicate_businesses(all_businesses, merge_data=True)

print("=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Raw: {len(all_businesses)}")
print(f"Unique: {len(deduped)}")
print(f"Dedup rate: {(len(all_businesses) - len(deduped))*100/max(len(all_businesses),1):.1f}%")
print()

# Categories
categories = {}
for biz in deduped:
    cat = biz.get('category', 'other')
    categories[cat] = categories.get(cat, 0) + 1

print("CATEGORIES:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:15]:
    print(f"  {cat}: {count}")

# Kyle targets
kyle = {'Roofing': 172, 'Plumbing': 143, 'Towing': 193, 'Landscaping': 173, 'Pest Control': 113, 'Electricians': 98}
print()
print("vs KYLE'S TARGETS (from 100 tiles, extrapolated to full):")
ratio = len(tiles) / 100
for cat, kyle_count in kyle.items():
    actual = categories.get(cat, 0)
    extrap = int(actual * ratio * 0.4)  # With overlap, reduce by 60%
    print(f"  {cat}: {actual} -> ~{extrap} (Kyle: {kyle_count})")

print()
print(f"EXTRAPOLATION to {len(tiles)} tiles:")
unique_per_tile = len(deduped) / 100
# With more tiles, dedup rate increases (diminishing returns)
estimated = int(unique_per_tile * len(tiles) * 0.35)
print(f"  Unique per tile: {unique_per_tile:.1f}")
print(f"  Estimated total unique: ~{estimated}")
print(f"  Kyle's target: 3,539")
