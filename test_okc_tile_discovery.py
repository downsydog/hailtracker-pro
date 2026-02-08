"""
Test tile-based discovery on October 23, 2025 OKC storm
Target: ~3,539 businesses (Kyle's proven result)

Uses:
- 0.25 sq mile tiles
- All 6 APIs: OSM, Yelp, Foursquare, HERE, TomTom, Google
"""

import sys
import os
import sqlite3
import json
import time

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.business.tile_discovery import TileBasedDiscovery

def main():
    print("=" * 70)
    print("OCTOBER 23, 2025 OKC STORM - TILE-BASED DISCOVERY TEST")
    print("=" * 70)
    print()

    # Get event IDs from database
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
    print()

    # Build swaths list
    swaths = []
    total_area = 0
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
            print(f"  [{event['id']}] {event['event_name'][:50]} - {event['max_hail_size']}\"")
        except Exception as e:
            print(f"  [SKIP] {event['id']}: {e}")

    conn.close()

    if not swaths:
        print("ERROR: No valid swaths found!")
        return

    print()
    print(f"Total swaths to search: {len(swaths)}")
    print()

    # Initialize tile-based discovery with 0.25 sq mile tiles
    print("Initializing TileBasedDiscovery with 0.25 sq mile tiles...")
    discovery = TileBasedDiscovery(tile_size_miles=0.25)
    print(f"Configured APIs: {discovery.configured_apis}")
    print()

    # Use all 6 APIs
    sources = ['osm', 'yelp', 'foursquare', 'here', 'tomtom', 'google']
    print(f"Sources to search: {sources}")
    print()

    # Progress callback
    start_time = time.time()
    last_update = [0]

    def progress(current, total, tile):
        now = time.time()
        if now - last_update[0] >= 5:  # Update every 5 seconds
            elapsed = now - start_time
            rate = current / elapsed if elapsed > 0 else 0
            eta = (total - current) / rate if rate > 0 else 0
            print(f"  Progress: {current}/{total} tiles ({current*100/total:.1f}%) - {rate:.1f} tiles/sec - ETA: {eta/60:.1f} min")
            last_update[0] = now

    print("Starting discovery...")
    print("-" * 70)

    # Run discovery
    result = discovery.discover_for_swaths(
        swaths=swaths,
        sources=sources,
        progress_callback=progress,
        use_cache=True  # Use cache for faster testing
    )

    elapsed = time.time() - start_time

    print("-" * 70)
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    stats = result.get('stats', {})
    tile_stats = result.get('tile_stats', {})
    businesses = result.get('businesses', [])

    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print()
    print(f"TILES:")
    print(f"  Total tiles: {tile_stats.get('count', 0)}")
    print(f"  Tile size: {tile_stats.get('tile_size_miles', 0.25)} sq miles")
    print(f"  Estimated area: {tile_stats.get('estimated_area_sq_miles', 0):.1f} sq miles")
    print()
    print(f"SEARCH RESULTS:")
    print(f"  Tiles searched: {stats.get('tiles_searched', 0)}")
    print(f"  Tiles from cache: {stats.get('tiles_from_cache', 0)}")
    print()
    print(f"BY SOURCE:")
    by_source = stats.get('by_source', {})
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")
    print()
    print(f"DEDUPLICATION:")
    print(f"  Duplicates removed: {stats.get('duplicates_removed', 0)}")
    print()
    print(f"FINAL RESULTS:")
    print(f"  Total businesses: {len(businesses)}")
    print(f"  Total vehicles: {stats.get('total_vehicles', 0)}")
    print()

    # Kyle's target categories
    print("KYLE'S TARGET CATEGORIES:")
    kyle_targets = {
        'towing': 0,
        'landscaping': 0,
        'roofing': 0,
        'plumbing': 0,
        'pest_control': 0,
        'electrical': 0,
        'hvac': 0,
        'contractor': 0,
    }

    by_category = stats.get('by_category', {})
    for cat, count in by_category.items():
        cat_lower = cat.lower()
        if 'tow' in cat_lower:
            kyle_targets['towing'] += count
        elif 'landscape' in cat_lower or 'lawn' in cat_lower:
            kyle_targets['landscaping'] += count
        elif 'roof' in cat_lower:
            kyle_targets['roofing'] += count
        elif 'plumb' in cat_lower:
            kyle_targets['plumbing'] += count
        elif 'pest' in cat_lower or 'exterminator' in cat_lower:
            kyle_targets['pest_control'] += count
        elif 'electric' in cat_lower:
            kyle_targets['electrical'] += count
        elif 'hvac' in cat_lower or 'air condition' in cat_lower or 'heating' in cat_lower:
            kyle_targets['hvac'] += count
        elif 'contractor' in cat_lower or 'construction' in cat_lower:
            kyle_targets['contractor'] += count

    print(f"  Towing: {kyle_targets['towing']} (Kyle: 193)")
    print(f"  Landscaping: {kyle_targets['landscaping']} (Kyle: 173)")
    print(f"  Roofing: {kyle_targets['roofing']} (Kyle: 172)")
    print(f"  Plumbing: {kyle_targets['plumbing']} (Kyle: 143)")
    print(f"  Pest Control: {kyle_targets['pest_control']} (Kyle: 113)")
    print(f"  Electrical: {kyle_targets['electrical']} (Kyle: 98)")
    print(f"  HVAC: {kyle_targets['hvac']}")
    print(f"  Contractor: {kyle_targets['contractor']}")
    print()

    print("ALL CATEGORIES:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1])[:20]:
        print(f"  {cat}: {count}")

    print()
    print("=" * 70)
    print(f"FINAL: {len(businesses)} BUSINESSES")
    print(f"TARGET: 3,539 (Kyle's result)")
    print(f"MATCH: {len(businesses)*100/3539:.1f}%")
    print("=" * 70)

if __name__ == '__main__':
    main()
