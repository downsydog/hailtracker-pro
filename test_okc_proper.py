"""
Proper test with contiguous tiles to verify deduplication
"""

import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("PROPER OKC TEST - CONTIGUOUS TILES")
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

print(f"Total swaths: {len(swaths)}")

# Generate tiles
from src.business.tile_system import SwathTileSystem
ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)
print(f"Total tiles: {len(tiles)}")

# Use CONTIGUOUS tiles (first 50)
test_tiles = tiles[:50]
print(f"Testing with first {len(test_tiles)} contiguous tiles")
print()

# Search with Yelp only (fast, reliable)
from src.fleet.apis.yelp_api import YelpAPI
yelp = YelpAPI()

all_businesses = []
print("Searching tiles...")
for i, tile in enumerate(test_tiles):
    try:
        radius = int(tile.search_radius_miles * 1609.34)
        results = yelp.search_all_categories(tile.center_lat, tile.center_lon, radius)
        for r in results:
            r['source'] = 'yelp'
            r['tile_id'] = tile.tile_id
        all_businesses.extend(results)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(test_tiles)} tiles - {len(all_businesses)} raw businesses")
    except Exception as e:
        print(f"  Tile {i+1} ERROR: {e}")

print()
print(f"RAW TOTAL: {len(all_businesses)}")
print()

# Analyze before dedup
from src.business.deduplication import deduplicate_businesses, analyze_duplicates

analysis = analyze_duplicates(all_businesses)
print("PRE-DEDUP ANALYSIS:")
print(f"  Total businesses: {analysis['total']}")
print(f"  Unique phone numbers: {analysis['unique_phones']}")
print(f"  Phone duplicates: {analysis['phone_duplicates']}")
print(f"  Estimated unique: {analysis['estimated_unique']}")
print()

# Run deduplication
print("Running deduplication...")
deduped = deduplicate_businesses(all_businesses, merge_data=True)
print()

print("=" * 70)
print("RESULTS")
print("=" * 70)
print()
print(f"Raw businesses: {len(all_businesses)}")
print(f"After dedup: {len(deduped)}")
print(f"Duplicates removed: {len(all_businesses) - len(deduped)}")
print(f"DEDUP RATE: {(len(all_businesses) - len(deduped))*100/len(all_businesses):.1f}%")
print()

# Count categories
categories = {}
for biz in deduped:
    cat = biz.get('category', 'other')
    categories[cat] = categories.get(cat, 0) + 1

print("CATEGORIES (unique businesses):")
for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:15]:
    print(f"  {cat}: {count}")

print()
print("Expected dedup rate: 60-70% (GOOD)")
print("Actual dedup rate: {:.1f}%".format((len(all_businesses) - len(deduped))*100/len(all_businesses)))
