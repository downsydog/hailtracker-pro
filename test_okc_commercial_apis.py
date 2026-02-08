"""
Test October 23 OKC storm using COMMERCIAL APIs only (skip OSM rate limits)
"""

import sys
import os
import sqlite3
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file FIRST before importing APIs
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("OCTOBER 23, 2025 OKC STORM - COMMERCIAL APIs TEST")
print("=" * 70)
print()

# Check which APIs are configured
from src.fleet.apis.yelp_api import YelpAPI
from src.fleet.apis.here_api import HereAPI
from src.fleet.apis.tomtom_api import TomTomAPI
from src.fleet.apis.google_places_api import GooglePlacesAPI
from src.fleet.scrapers.foursquare_api import FoursquareAPI

apis = {
    'yelp': YelpAPI(),
    'foursquare': FoursquareAPI(),
    'here': HereAPI(),
    'tomtom': TomTomAPI(),
    'google': GooglePlacesAPI(),
}

print("API STATUS:")
configured = []
for name, api in apis.items():
    is_conf = api.is_configured()
    print(f"  {name}: {'[Y]' if is_conf else '[N]'}")
    if is_conf:
        configured.append(name)

print()
print(f"Will use: {configured if configured else ['osm (fallback)']}")
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

print(f"Swaths: {len(swaths)} events")
print()

# Tile calculation
from src.business.tile_system import SwathTileSystem

ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)
tile_stats = ts.get_tile_stats(tiles)

print(f"Tiles (0.25 sq mi): {tile_stats['count']}")
print(f"Estimated area: {tile_stats.get('estimated_area_sq_miles', 0):.1f} sq miles")
print()

# If no APIs configured, show how to configure
if not configured:
    print("=" * 70)
    print("NO APIs CONFIGURED - Need API keys to run full test")
    print("=" * 70)
    print()
    print("Set environment variables:")
    print("  YELP_API_KEY - Get from https://www.yelp.com/developers")
    print("  HERE_API_KEY - Get from https://developer.here.com/")
    print("  TOMTOM_API_KEY - Get from https://developer.tomtom.com/")
    print("  GOOGLE_PLACES_API_KEY - Get from Google Cloud Console")
    print("  FOURSQUARE_API_KEY - Get from https://location.foursquare.com/")
    print()
    print("Falling back to OSM-only test (rate limited)...")
    configured = ['osm']

# Run discovery
print("=" * 70)
print(f"RUNNING DISCOVERY ({len(tiles)} tiles x {len(configured)} APIs)")
print("=" * 70)
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
        print(f"  {current}/{total} tiles ({current*100/total:.1f}%) - {rate:.2f}/sec - ETA: {eta/60:.1f}m")
        last_update[0] = now

result = discovery.discover_for_swaths(
    swaths=swaths,
    sources=configured,
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
for src, cnt in stats.get('by_source', {}).items():
    print(f"  {src}: {cnt}")
print()
print(f"Duplicates removed: {stats.get('duplicates_removed', 0)}")
print()
print(f"TOTAL BUSINESSES: {len(businesses)}")
print(f"TOTAL VEHICLES: {stats.get('total_vehicles', 0)}")
print()

# Categories
print("TOP CATEGORIES:")
by_cat = stats.get('by_category', {})
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

print(f"  towing: {targets['towing']} (Kyle: 193)")
print(f"  landscaping: {targets['landscaping']} (Kyle: 173)")
print(f"  roofing: {targets['roofing']} (Kyle: 172)")
print(f"  plumbing: {targets['plumbing']} (Kyle: 143)")
print(f"  pest: {targets['pest']} (Kyle: 113)")
print(f"  electric: {targets['electric']} (Kyle: 98)")
print(f"  hvac: {targets['hvac']}")
print(f"  contractor: {targets['contractor']}")
print()

print("=" * 70)
print(f"FINAL: {len(businesses)} businesses")
print(f"TARGET: 3,539")
print(f"MATCH: {len(businesses)*100/3539:.1f}%")
print("=" * 70)
