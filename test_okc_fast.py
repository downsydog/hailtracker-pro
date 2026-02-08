"""
Fast test of October 23 OKC storm - run 3 swaths with 4 working APIs
"""

import sys
import os
import sqlite3
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env FIRST
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("OCTOBER 23, 2025 OKC STORM - FAST TEST (3 swaths)")
print("=" * 70)
print()

# Get largest swaths
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
    LIMIT 3
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
        print(f"  [{event['id']}] {event['max_hail_size']}\" - {event['event_name'][:50]}")
    except:
        pass

print()
print(f"Testing {len(swaths)} swaths")
print()

# Calculate tiles
from src.business.tile_system import SwathTileSystem
ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)
print(f"Tiles for these swaths: {len(tiles)}")
print()

# Use working APIs (skip TomTom - 404 errors)
sources = ['yelp', 'foursquare', 'here', 'google']
print(f"Using APIs: {sources}")
print()

# Run discovery
from src.business.tile_discovery import TileBasedDiscovery

discovery = TileBasedDiscovery(tile_size_miles=0.25)

start = time.time()
last_update = [0]

def progress(current, total, tile):
    now = time.time()
    if now - last_update[0] >= 5:
        elapsed = now - start
        rate = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / rate if rate > 0 else 0
        print(f"  {current}/{total} ({current*100/total:.0f}%) - {rate:.1f}/sec - ETA: {eta:.0f}s")
        last_update[0] = now

print("Starting discovery...")
print("-" * 50)

result = discovery.discover_for_swaths(
    swaths=swaths,
    sources=sources,
    progress_callback=progress,
    use_cache=True
)

elapsed = time.time() - start

print("-" * 50)
print()
print("=" * 70)
print("RESULTS")
print("=" * 70)
print()

stats = result.get('stats', {})
businesses = result.get('businesses', [])

print(f"Time: {elapsed:.1f}s ({elapsed/60:.1f}m)")
print()
print(f"BY SOURCE:")
for src, cnt in sorted(stats.get('by_source', {}).items(), key=lambda x: -x[1]):
    print(f"  {src}: {cnt}")
print()
print(f"Duplicates removed: {stats.get('duplicates_removed', 0)}")
print()

# Categories
print("TOP CATEGORIES:")
by_cat = stats.get('by_category', {})
for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1])[:10]:
    print(f"  {cat}: {cnt}")
print()

print(f"BUSINESSES FOUND: {len(businesses)}")
print(f"TOTAL VEHICLES: {stats.get('total_vehicles', 0)}")
print()

# Full test estimate
total_swaths = 18
extrapolated = len(businesses) * (total_swaths / len(swaths))
print(f"EXTRAPOLATION (for all {total_swaths} swaths): ~{extrapolated:.0f} businesses")
print(f"TARGET: 3,539")
print()
print("=" * 70)
