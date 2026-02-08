"""
Quick test of October 23 OKC storm - check API configuration and run smaller test
"""

import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("OCTOBER 23, 2025 OKC STORM - API STATUS CHECK")
print("=" * 70)
print()

# Check API configuration
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

print("API CONFIGURATION STATUS:")
print("-" * 40)
configured_apis = []
for name, api in apis.items():
    status = "CONFIGURED" if api.is_configured() else "NOT CONFIGURED"
    print(f"  {name}: {status}")
    if api.is_configured():
        configured_apis.append(name)

print()
print(f"Configured APIs: {configured_apis}")
print()

# Get event info
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

events = cursor.fetchall()
print(f"Found {len(events)} events for October 23, 2025 OKC storm")

# Calculate total area
total_area = 0
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

conn.close()

print(f"Valid swaths: {len(swaths)}")
print()

# Calculate tiles for 0.25 sq mile
from src.business.tile_system import SwathTileSystem

ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)
tile_stats = ts.get_tile_stats(tiles)

print("TILE CALCULATION (0.25 sq mile tiles):")
print(f"  Total tiles: {tile_stats['count']}")
print(f"  Estimated area: {tile_stats.get('estimated_area_sq_miles', 0):.1f} sq miles")
print()

# Estimate API calls
num_apis = len(configured_apis) + 1  # +1 for OSM
total_calls = tile_stats['count'] * num_apis
print(f"ESTIMATED API CALLS:")
print(f"  Tiles x APIs = {tile_stats['count']} x {num_apis} = {total_calls} calls")
print()

# Run a SMALL test - just first 10 tiles with configured APIs only
print("=" * 70)
print("RUNNING SMALL TEST (first 20 tiles, configured APIs only)")
print("=" * 70)
print()

from src.business.tile_discovery import TileBasedDiscovery
import time

discovery = TileBasedDiscovery(tile_size_miles=0.25)

# Use only first swath for quick test
test_swaths = swaths[:2]  # First 2 swaths only

# Only use configured APIs (skip OSM to avoid rate limits)
test_sources = configured_apis if configured_apis else ['osm']
print(f"Testing with sources: {test_sources}")
print()

start = time.time()
result = discovery.discover_for_swaths(
    swaths=test_swaths,
    sources=test_sources,
    use_cache=True
)
elapsed = time.time() - start

print()
print("SMALL TEST RESULTS:")
print("-" * 40)
print(f"Time: {elapsed:.1f} seconds")
print(f"Businesses found: {len(result.get('businesses', []))}")
print(f"By source: {result.get('stats', {}).get('by_source', {})}")
print(f"Duplicates removed: {result.get('stats', {}).get('duplicates_removed', 0)}")
print()

# Show categories
by_cat = result.get('stats', {}).get('by_category', {})
print("BY CATEGORY (top 10):")
for cat, count in sorted(by_cat.items(), key=lambda x: -x[1])[:10]:
    print(f"  {cat}: {count}")

print()
print("=" * 70)
print("To run full test, APIs need to be configured with keys.")
print("Set environment variables: YELP_API_KEY, HERE_API_KEY, etc.")
print("=" * 70)
