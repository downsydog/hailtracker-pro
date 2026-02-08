"""
Test October 23 OKC storm with Yelp + Foursquare only (fastest APIs)
"""

import sys
import os
import sqlite3
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("OCTOBER 23, 2025 OKC STORM - YELP + FOURSQUARE TEST")
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
    ORDER BY max_hail_size DESC
''')

events = list(cursor.fetchall())
conn.close()

swaths = []
for event in events:
    try:
        polygon = json.loads(event['swath_polygon'])
        swaths.append({
            'event_id': event['id'],
            'event_name': event['event_name'],
            'max_hail_size': event['max_hail_size'],
            'polygon': polygon,
            **polygon
        })
    except:
        pass

print(f"Swaths: {len(swaths)}")

# Tile stats
from src.business.tile_system import SwathTileSystem
ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)
tile_stats = ts.get_tile_stats(tiles)
print(f"Tiles (0.25 sq mi): {tile_stats['count']}")
print(f"Estimated area: {tile_stats.get('estimated_area_sq_miles', 0):.1f} sq miles")
print()

# Use only fast APIs
sources = ['yelp', 'foursquare']
print(f"APIs: {sources}")
print(f"Estimated time: {tile_stats['count'] * 12 / 60:.0f} minutes")
print()

from src.business.tile_discovery import TileBasedDiscovery
discovery = TileBasedDiscovery(tile_size_miles=0.25)

start = time.time()
last_update = [0]

def progress(current, total, tile):
    now = time.time()
    if now - last_update[0] >= 10:
        elapsed = now - start
        rate = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / rate if rate > 0 else 0
        print(f"  {current}/{total} ({current*100/total:.1f}%) - ETA: {eta/60:.1f}m")
        last_update[0] = now

print("Starting...")
result = discovery.discover_for_swaths(
    swaths=swaths,
    sources=sources,
    progress_callback=progress,
    use_cache=True
)

elapsed = time.time() - start

print()
print("=" * 70)
print("RESULTS")
print("=" * 70)
print()

stats = result.get('stats', {})
businesses = result.get('businesses', [])

print(f"Time: {elapsed/60:.1f} minutes")
print()
print(f"BY SOURCE:")
for src, cnt in sorted(stats.get('by_source', {}).items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt}")
print()
print(f"Duplicates removed: {stats.get('duplicates_removed', 0)}")
print(f"Dedup rate: {stats.get('duplicates_removed', 0)*100/(stats.get('duplicates_removed', 0) + len(businesses) + 0.001):.1f}%")
print()
print(f"BUSINESSES: {len(businesses)}")
print(f"VEHICLES: {stats.get('total_vehicles', 0)}")
print()

# Categories
by_cat = stats.get('by_category', {})
print("TOP 15 CATEGORIES:")
for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1])[:15]:
    print(f"  {cat}: {cnt}")
print()

# Kyle targets
print("KYLE'S TARGETS:")
targets = {'towing': 0, 'landscaping': 0, 'roofing': 0, 'plumbing': 0,
           'pest': 0, 'electric': 0, 'hvac': 0, 'contractor': 0}
for cat, cnt in by_cat.items():
    cl = cat.lower()
    if 'tow' in cl: targets['towing'] += cnt
    if 'landscape' in cl or 'lawn' in cl: targets['landscaping'] += cnt
    if 'roof' in cl: targets['roofing'] += cnt
    if 'plumb' in cl: targets['plumbing'] += cnt
    if 'pest' in cl: targets['pest'] += cnt
    if 'electric' in cl: targets['electric'] += cnt
    if 'hvac' in cl or 'heat' in cl or 'air' in cl: targets['hvac'] += cnt
    if 'contractor' in cl: targets['contractor'] += cnt

for k, v in sorted(targets.items(), key=lambda x: -x[1]):
    kyle = {'towing': 193, 'landscaping': 173, 'roofing': 172, 'plumbing': 143,
            'pest': 113, 'electric': 98, 'hvac': 0, 'contractor': 0}.get(k, 0)
    suffix = f" (Kyle: {kyle})" if kyle else ""
    print(f"  {k}: {v}{suffix}")

print()
print("=" * 70)
print(f"TOTAL: {len(businesses)} businesses")
print(f"TARGET: 3,539")
print(f"MATCH: {len(businesses)*100/3539:.1f}%")
print("=" * 70)
