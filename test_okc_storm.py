"""
Test Fleet Intelligence for Oklahoma City Storm
Date: October 23, 2025
Location: Oklahoma City, OK
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.business.fleet_locations import FleetLocationManager, OSMQueryBuilder

# Oklahoma City coordinates and bounding box
OKC_LAT = 35.4676
OKC_LON = -97.5164
OKC_BBOX = (35.25, -97.75, 35.65, -97.30)  # south, west, north, east

def test_okc_storm():
    print("=" * 80)
    print("TESTING FLEET INTELLIGENCE FOR OKLAHOMA CITY STORM")
    print("Date: October 23, 2025")
    print(f"Location: Oklahoma City, OK")
    print(f"Coordinates: {OKC_LAT}, {OKC_LON}")
    print(f"Bounding Box: {OKC_BBOX}")
    print("=" * 80)
    print()

    # Initialize manager with database path
    db_path = os.path.join(os.path.dirname(__file__), "data", "fleet_locations.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    manager = FleetLocationManager(db_path)

    # Check existing data for OKC area
    print("[1] Checking existing fleet locations in OKC area...")
    south, west, north, east = OKC_BBOX
    existing = manager.get_locations_in_bbox(south, west, north, east)
    print(f"    Found {len(existing)} existing locations in bbox")

    if existing:
        categories = {}
        for loc in existing:
            cat = loc.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        print("    Categories:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
            print(f"      - {cat}: {count}")
    print()

    # Discover fleet locations using seed_city
    print("[2] Discovering fleet locations from OSM...")
    print(f"    Seeding Oklahoma City, OK")
    print(f"    Categories: {len(OSMQueryBuilder.CATEGORY_QUERIES)}")
    print()

    results = manager.seed_city(
        city="Oklahoma City",
        state="OK",
        bbox=OKC_BBOX
    )

    print()
    print("[3] Discovery Results by Category:")
    total_new = 0
    for category, count in sorted(results.items(), key=lambda x: -x[1] if x[0] != 'total' else 0):
        if category != 'total':
            print(f"    - {category}: {count} locations")
            total_new += count
    print()
    print(f"    Total new locations discovered: {results.get('total', total_new)}")
    print()

    # Get updated count using bbox instead to avoid sorting error
    all_locations = manager.get_locations_in_bbox(south, west, north, east)
    print(f"[4] Total fleet locations in OKC area: {len(all_locations)}")
    print()

    if all_locations:
        # Analyze by category
        cat_counts = {}
        total_vehicles = 0
        total_revenue = 0
        grade_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'Unknown': 0}

        for loc in all_locations:
            cat = loc.get('category', 'unknown')
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            total_vehicles += loc.get('estimated_fleet_size', 0) or 0
            total_revenue += loc.get('estimated_revenue', 0) or 0
            grade = loc.get('grade', 'Unknown')
            if grade in grade_counts:
                grade_counts[grade] += 1
            else:
                grade_counts['Unknown'] += 1

        print("    By Category:")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"      - {cat}: {count}")
        print()

        print("    By Grade:")
        for grade in ['A', 'B', 'C', 'D', 'Unknown']:
            if grade_counts[grade] > 0:
                print(f"      - Grade {grade}: {grade_counts[grade]}")
        print()

        print("    Revenue Potential:")
        print(f"      - Total estimated vehicles: {total_vehicles:,}")
        print(f"      - Total potential revenue: ${total_revenue:,.0f}")
        print()

        # Top prospects
        print("[5] Top 10 Fleet Prospects:")
        sorted_locs = sorted(all_locations, key=lambda x: x.get('estimated_revenue', 0) or 0, reverse=True)[:10]
        for i, loc in enumerate(sorted_locs, 1):
            name = (loc.get('name') or 'Unknown')[:40]
            cat = loc.get('category') or 'unknown'
            vehicles = loc.get('estimated_fleet_size') or 0
            revenue = loc.get('estimated_revenue') or 0
            grade = loc.get('grade') or '?'
            print(f"    {i:2}. [{grade}] {name:<40} | {cat:<20} | {vehicles:>4} vehicles | ${revenue:>10,.0f}")
        print()

        # Show category summary from database
        print("[6] Category Summary from Database:")
        for cat in manager.get_category_summary():
            cat_name = cat.get('display_name') or cat.get('category') or 'Unknown'
            loc_count = cat.get('location_count', 0)
            vehicles = cat.get('total_vehicles', 0) or 0
            revenue = cat.get('potential_revenue', 0) or 0
            print(f"    {cat_name}: {loc_count} locations, ~{vehicles:,} vehicles, ${revenue:,.0f} potential")
        print()

        # Sample location details
        print("[7] Sample Location Details:")
        for i, loc in enumerate(sorted_locs[:5], 1):
            print(f"\n    --- {i}. {loc.get('name', 'Unknown')} ---")
            print(f"    Category: {loc.get('category', 'N/A')}")
            print(f"    Address: {loc.get('address') or 'N/A'}")
            print(f"    City: {loc.get('city') or 'N/A'}, {loc.get('state') or 'N/A'}")
            print(f"    Coordinates: {loc.get('latitude')}, {loc.get('longitude')}")
            print(f"    Est. Fleet Size: {loc.get('estimated_fleet_size') or 0} vehicles")
            print(f"    Est. Revenue: ${loc.get('estimated_revenue') or 0:,.0f}")
            print(f"    Grade: {loc.get('grade') or 'N/A'}")
            if loc.get('phone'):
                print(f"    Phone: {loc.get('phone')}")
            if loc.get('website'):
                print(f"    Website: {loc.get('website')}")
        print()

        # Final summary
        print("=" * 80)
        print("OKLAHOMA CITY STORM FLEET INTELLIGENCE SUMMARY")
        print("=" * 80)
        print(f"  Storm Date: October 23, 2025")
        print(f"  Location: Oklahoma City, OK")
        print(f"  Total Fleet Locations: {len(all_locations)}")
        print(f"  Estimated Vehicles at Risk: {total_vehicles:,}")
        print(f"  Potential PDR Revenue: ${total_revenue:,.0f}")
        if cat_counts:
            top_cat = max(cat_counts, key=cat_counts.get)
            print(f"  Top Category: {top_cat} ({cat_counts[top_cat]} locations)")
        print()
        print("  Recommended Actions:")
        print("    1. Contact Grade A prospects immediately")
        print("    2. Prepare route for high-value dealerships")
        print("    3. Deploy fleet inspection teams to affected areas")
        print("=" * 80)

        return len(all_locations)
    else:
        print("  No fleet locations found")
        return 0


if __name__ == '__main__':
    count = test_okc_storm()
    print(f"\nTest complete. Found {count} fleet locations in Oklahoma City.")
    sys.exit(0 if count >= 0 else 1)
