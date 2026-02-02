"""
Seed Fleet Locations for Major Hail-Prone Cities

Tier 1 Cities (Major Hail Zones):
1. Dallas-Fort Worth, Texas
2. Tulsa, Oklahoma
3. Denver, Colorado
4. Kansas City, Missouri/Kansas
5. San Antonio, Texas

Queries OpenStreetMap for all 15 fleet categories in each city.
"""

import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.business.fleet_locations import FleetLocationManager


def calculate_bbox(lat: float, lon: float, radius_miles: float):
    """
    Calculate bounding box from center point and radius.

    Returns: (south, west, north, east)
    """
    # 1 degree latitude = ~69 miles
    # 1 degree longitude = ~69 miles * cos(lat)
    import math

    lat_delta = radius_miles / 69.0
    lon_delta = radius_miles / (69.0 * math.cos(math.radians(lat)))

    south = lat - lat_delta
    north = lat + lat_delta
    west = lon - lon_delta
    east = lon + lon_delta

    return (south, west, north, east)


# City definitions with center coordinates and radius
TIER_1_CITIES = [
    {
        'name': 'Dallas-Fort Worth',
        'state': 'TX',
        'lat': 32.7767,
        'lon': -96.7970,
        'radius_miles': 30,
        'description': 'Largest hail market in US'
    },
    {
        'name': 'Tulsa',
        'state': 'OK',
        'lat': 36.1540,
        'lon': -95.9928,
        'radius_miles': 20,
        'description': 'Major hail corridor'
    },
    {
        'name': 'Denver',
        'state': 'CO',
        'lat': 39.7392,
        'lon': -104.9903,
        'radius_miles': 25,
        'description': 'Front Range hail alley'
    },
    {
        'name': 'Kansas City',
        'state': 'MO',
        'lat': 39.0997,
        'lon': -94.5786,
        'radius_miles': 25,
        'description': 'Frequent severe weather'
    },
    {
        'name': 'San Antonio',
        'state': 'TX',
        'lat': 29.4241,
        'lon': -98.4936,
        'radius_miles': 20,
        'description': 'Texas hail corridor'
    },
]

TIER_2_CITIES = [
    {
        'name': 'Omaha',
        'state': 'NE',
        'lat': 41.2565,
        'lon': -95.9345,
        'radius_miles': 15,
        'description': 'Nebraska hail zone'
    },
    {
        'name': 'Wichita',
        'state': 'KS',
        'lat': 37.6872,
        'lon': -97.3301,
        'radius_miles': 15,
        'description': 'Kansas tornado alley'
    },
    {
        'name': 'Austin',
        'state': 'TX',
        'lat': 30.2672,
        'lon': -97.7431,
        'radius_miles': 20,
        'description': 'Central Texas'
    },
    {
        'name': 'Colorado Springs',
        'state': 'CO',
        'lat': 38.8339,
        'lon': -104.8214,
        'radius_miles': 15,
        'description': 'Front Range south'
    },
    {
        'name': 'Houston',
        'state': 'TX',
        'lat': 29.7604,
        'lon': -95.3698,
        'radius_miles': 30,
        'description': 'Gulf Coast market'
    },
]


def seed_city(manager: FleetLocationManager, city_info: dict) -> dict:
    """
    Seed a single city with fleet locations.

    Returns dict with results.
    """
    name = city_info['name']
    state = city_info['state']
    lat = city_info['lat']
    lon = city_info['lon']
    radius = city_info['radius_miles']

    print(f"\n{'='*60}")
    print(f"SEEDING: {name}, {state}")
    print(f"{'='*60}")
    print(f"Center: {lat}, {lon}")
    print(f"Radius: {radius} miles")
    print(f"Description: {city_info.get('description', '')}")
    print()

    # Calculate bounding box
    bbox = calculate_bbox(lat, lon, radius)
    print(f"Bounding box: S={bbox[0]:.4f}, W={bbox[1]:.4f}, N={bbox[2]:.4f}, E={bbox[3]:.4f}")
    print()

    # Get categories
    categories = list(manager.osm.CATEGORY_QUERIES.keys())

    results = {'city': name, 'state': state, 'categories': {}, 'total': 0}

    for i, category in enumerate(categories, 1):
        print(f"[{i:2d}/15] Querying {category}...", end=' ', flush=True)

        try:
            # Query OSM
            locations = manager.query_osm_for_category(category, name, state, bbox)

            # Save to database
            saved = manager.save_locations(locations)

            results['categories'][category] = {
                'found': len(locations),
                'saved': saved
            }
            results['total'] += saved

            print(f"Found {len(locations):3d}, Saved {saved:3d} new")

            # Rate limit - be nice to OSM
            time.sleep(2)

        except Exception as e:
            print(f"ERROR: {e}")
            results['categories'][category] = {'found': 0, 'saved': 0, 'error': str(e)}
            time.sleep(5)  # Longer wait on error

    print()
    print(f"{'='*60}")
    print(f"COMPLETED: {name}, {state}")
    print(f"Total new locations saved: {results['total']}")
    print(f"{'='*60}")

    return results


def print_summary(all_results: list, manager: FleetLocationManager):
    """Print final summary"""
    print("\n")
    print("=" * 70)
    print("                    SEEDING COMPLETE - SUMMARY")
    print("=" * 70)

    grand_total = 0

    print(f"\n{'City':<25} {'State':<6} {'New Locations':<15}")
    print("-" * 50)

    for result in all_results:
        city = result['city']
        state = result['state']
        total = result['total']
        grand_total += total
        print(f"{city:<25} {state:<6} {total:>10,}")

    print("-" * 50)
    print(f"{'TOTAL':<25} {'':<6} {grand_total:>10,}")

    # Get database totals
    print("\n")
    print("=" * 70)
    print("                    DATABASE TOTALS")
    print("=" * 70)

    summary = manager.get_category_summary()
    total_locations = 0
    total_vehicles = 0
    total_revenue = 0

    print(f"\n{'Category':<25} {'Locations':>12} {'Vehicles':>12} {'Revenue':>15}")
    print("-" * 70)

    for cat in summary:
        name = cat.get('display_name', cat['category'])
        locs = cat['location_count']
        vehicles = cat['total_vehicles'] or 0
        revenue = cat['potential_revenue'] or 0

        total_locations += locs
        total_vehicles += vehicles
        total_revenue += revenue

        print(f"{name:<25} {locs:>12,} {vehicles:>12,} ${revenue:>14,.0f}")

    print("-" * 70)
    print(f"{'TOTAL':<25} {total_locations:>12,} {total_vehicles:>12,} ${total_revenue:>14,.0f}")
    print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Seed fleet locations for cities')
    parser.add_argument('--tier', type=int, choices=[1, 2], default=1,
                       help='Which tier of cities to seed (1=major, 2=secondary)')
    parser.add_argument('--city', type=str, help='Seed only a specific city by name')
    parser.add_argument('--all', action='store_true', help='Seed all cities (Tier 1 and 2)')
    args = parser.parse_args()

    # Initialize database
    db_path = PROJECT_ROOT / 'database' / 'fleet_locations.db'
    manager = FleetLocationManager(str(db_path))

    print("\n" + "=" * 70)
    print("           FLEET LOCATION SEEDING - HAIL TRACKER PRO")
    print("=" * 70)
    print(f"\nDatabase: {db_path}")
    print(f"Current locations: {manager.get_location_count():,}")

    # Determine which cities to seed
    if args.city:
        # Find specific city
        all_cities = TIER_1_CITIES + TIER_2_CITIES
        cities = [c for c in all_cities if args.city.lower() in c['name'].lower()]
        if not cities:
            print(f"\nCity '{args.city}' not found. Available cities:")
            for c in all_cities:
                print(f"  - {c['name']}, {c['state']}")
            return
    elif args.all:
        cities = TIER_1_CITIES + TIER_2_CITIES
    elif args.tier == 1:
        cities = TIER_1_CITIES
    else:
        cities = TIER_2_CITIES

    print(f"\nCities to seed: {len(cities)}")
    for c in cities:
        print(f"  - {c['name']}, {c['state']} ({c['radius_miles']} mile radius)")

    # Seed each city
    all_results = []

    for i, city_info in enumerate(cities):
        result = seed_city(manager, city_info)
        all_results.append(result)

        # Wait between cities to avoid rate limiting
        if i < len(cities) - 1:
            wait_time = 30
            print(f"\nWaiting {wait_time} seconds before next city...")
            time.sleep(wait_time)

    # Print summary
    print_summary(all_results, manager)

    print("\nSeeding complete!")
    print(f"View the map at: http://127.0.0.1:5556/fleet")


if __name__ == '__main__':
    main()
