"""
Sample test - 100 random tiles to estimate total
"""

import sys
import os
import sqlite3
import json
import time
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("OCTOBER 23 OKC - SAMPLING TEST (100 tiles)")
print("=" * 70)
print()

# Get all swaths
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
        swaths.append({'event_id': row['id'], 'polygon': polygon, **polygon})
    except:
        pass
conn.close()

print(f"Swaths: {len(swaths)}")

# Generate all tiles
from src.business.tile_system import SwathTileSystem
ts = SwathTileSystem(tile_size_miles=0.25)
all_tiles = ts.generate_tiles_for_multiple_swaths(swaths)
print(f"Total tiles: {len(all_tiles)}")

# Sample 100 tiles randomly
sample_size = min(100, len(all_tiles))
sample_tiles = random.sample(all_tiles, sample_size)
print(f"Sample: {sample_size} tiles")
print()

# Search just these tiles manually with Yelp + Foursquare
from src.fleet.apis.yelp_api import YelpAPI
from src.fleet.scrapers.foursquare_api import FoursquareAPI

yelp = YelpAPI()
fs = FoursquareAPI()

all_businesses = []
start = time.time()

print("Searching sample tiles...")
for i, tile in enumerate(sample_tiles):
    if (i + 1) % 10 == 0:
        elapsed = time.time() - start
        rate = (i + 1) / elapsed
        eta = (sample_size - i - 1) / rate
        print(f"  {i+1}/{sample_size} - {rate:.1f}/sec - ETA: {eta:.0f}s")

    # Yelp
    try:
        radius = int(tile.search_radius_miles * 1609.34)
        results = yelp.search_all_categories(tile.center_lat, tile.center_lon, radius)
        for r in results:
            r['source'] = 'yelp'
        all_businesses.extend(results)
    except Exception as e:
        pass

    # Foursquare
    try:
        radius = int(tile.search_radius_miles * 1609.34)
        results = fs.search_all_fleet_categories(tile.center_lat, tile.center_lon, radius)
        for r in results:
            r['source'] = 'foursquare'
        all_businesses.extend(results)
    except Exception as e:
        pass

    time.sleep(0.1)

elapsed = time.time() - start
print()
print(f"Sample search time: {elapsed:.1f}s")
print(f"Raw businesses from sample: {len(all_businesses)}")

# Deduplicate
from src.business.deduplication import deduplicate_businesses
unique = deduplicate_businesses(all_businesses, merge_data=True)
print(f"After dedup: {len(unique)}")
print(f"Dedup rate: {(len(all_businesses) - len(unique))*100/max(len(all_businesses), 1):.1f}%")
print()

# Estimate for full
ratio = len(all_tiles) / sample_size
estimated_raw = len(all_businesses) * ratio
estimated_unique = len(unique) * ratio * 0.6  # Lower because full has more overlap

print("=" * 70)
print("ESTIMATES FOR FULL 3570 TILES:")
print(f"  Estimated raw: ~{estimated_raw:.0f}")
print(f"  Estimated unique: ~{estimated_unique:.0f}")
print(f"  Target: 3,539")
print("=" * 70)

# Categories
by_cat = {}
for biz in unique:
    cat = biz.get('category', 'other')
    by_cat[cat] = by_cat.get(cat, 0) + 1

print()
print("SAMPLE CATEGORIES (scaled to full):")
for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1])[:10]:
    print(f"  {cat}: ~{int(cnt * ratio)}")
