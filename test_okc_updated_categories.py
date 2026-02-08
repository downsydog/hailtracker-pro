"""
Test Updated Search Categories - Oklahoma City Storm
October 23, 2025

Compare BEFORE vs AFTER service company discovery
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.business.fleet_locations import FleetLocationManager, OSMQueryBuilder

# Oklahoma City coordinates and bounding box
OKC_LAT = 35.4676
OKC_LON = -97.5164
OKC_BBOX = (35.25, -97.75, 35.65, -97.30)  # south, west, north, east


def categorize_service_companies(locations):
    """Break down service companies by specific type."""

    # Define service company subcategories with keywords
    subcategories = {
        'HVAC': ['hvac', 'heating', 'cooling', 'air conditioning', 'furnace', 'ac ', 'a/c'],
        'Plumbing': ['plumb', 'pipe', 'drain', 'sewer', 'water heater'],
        'Electrical': ['electric', 'wiring', 'power'],
        'Pest Control': ['pest', 'exterminator', 'termite', 'bug', 'rodent'],
        'Landscaping': ['landscap', 'lawn', 'yard', 'garden', 'mow'],
        'Tree Service': ['tree', 'stump', 'arbor'],
        'Roofing': ['roof', 'shingle'],
        'Siding/Gutter': ['siding', 'gutter', 'fascia', 'soffit'],
        'Fence': ['fence', 'fencing', 'gate'],
        'Pool Service': ['pool', 'spa', 'hot tub'],
        'Garage Door': ['garage door', 'overhead door'],
        'Locksmith': ['locksmith', 'lock ', 'key '],
        'Painting': ['paint', 'coating'],
        'Flooring': ['floor', 'carpet', 'tile', 'hardwood'],
        'Concrete/Paving': ['concrete', 'paving', 'asphalt', 'driveway'],
        'Pressure Washing': ['pressure wash', 'power wash'],
        'Window Cleaning': ['window clean', 'glass clean'],
        'Restoration': ['restoration', 'water damage', 'fire damage', 'mold'],
        'Septic': ['septic', 'porta', 'toilet'],
        'General Contractor': ['contractor', 'construction', 'builder', 'remodel'],
        'Excavation': ['excavat', 'grading', 'earth', 'dirt'],
        'Surveying': ['survey', 'land survey'],
        'Towing': ['tow', 'towing', 'wrecker'],
        'Auto Glass': ['auto glass', 'windshield', 'safelite'],
        'Beverage Distributor': ['beverage', 'coca-cola', 'pepsi', 'beer', 'wine', 'distributor'],
        'Linen/Uniform': ['linen', 'uniform', 'cintas', 'laundry'],
        'Vending': ['vending', 'snack'],
        'Property Management': ['property manag', 'apartment manag', 'hoa'],
        'Janitorial': ['janitor', 'cleaning service', 'maid', 'custod'],
        'Sign Company': ['sign ', 'signage', 'banner'],
        'Courier/Delivery': ['courier', 'delivery', 'messenger'],
        'Home Health': ['home health', 'hospice', 'medical transport'],
        'Cable/Satellite': ['cable', 'satellite', 'dish', 'directv', 'spectrum', 'cox'],
        'Security System': ['security', 'alarm', 'adt', 'monitoring'],
        'Waste/Junk': ['waste', 'garbage', 'trash', 'junk', 'haul', 'dumpster'],
        'Equipment Rental': ['rental', 'equipment', 'tool rent'],
        'Funeral': ['funeral', 'mortuary', 'cemetery'],
        'Other Service': [],  # Catch-all
    }

    results = {cat: [] for cat in subcategories}

    for loc in locations:
        name = (loc.get('name') or '').lower()
        category = (loc.get('category') or '').lower()
        combined = f"{name} {category}"

        matched = False
        for subcat, keywords in subcategories.items():
            if subcat == 'Other Service':
                continue
            for kw in keywords:
                if kw in combined:
                    results[subcat].append(loc)
                    matched = True
                    break
            if matched:
                break

        if not matched and 'service' in category:
            results['Other Service'].append(loc)

    return results


def test_updated_categories():
    print("=" * 80)
    print("OKLAHOMA CITY STORM - UPDATED CATEGORY TEST")
    print("Date: October 23, 2025")
    print("=" * 80)
    print()
    print("BEFORE UPDATE: Service Companies = 31")
    print()
    print("Running discovery with updated categories...")
    print("=" * 80)
    print()

    # Initialize manager with database path
    db_path = os.path.join(os.path.dirname(__file__), "data", "fleet_locations.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    manager = FleetLocationManager(db_path)

    # Run discovery
    print("[1] Discovering fleet locations from OSM...")
    results = manager.seed_city(
        city="Oklahoma City",
        state="OK",
        bbox=OKC_BBOX
    )

    print()
    print("[2] Discovery Results by Category:")
    for category, count in sorted(results.items(), key=lambda x: -x[1] if x[0] != 'total' else 0):
        if category != 'total' and count > 0:
            print(f"    {category}: {count}")
    print(f"\n    TOTAL NEW: {results.get('total', 0)}")
    print()

    # Get all locations
    south, west, north, east = OKC_BBOX
    all_locations = manager.get_locations_in_bbox(south, west, north, east)

    print("=" * 80)
    print(f"[3] TOTAL FLEET LOCATIONS IN DATABASE: {len(all_locations)}")
    print("=" * 80)
    print()

    # Category breakdown
    cat_counts = {}
    for loc in all_locations:
        cat = loc.get('category', 'unknown')
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    print("Overall Category Breakdown:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat}: {count}")
    print()

    # Get service companies specifically
    service_locs = [loc for loc in all_locations if loc.get('category') == 'service_company']

    print("=" * 80)
    print(f"[4] SERVICE COMPANY BREAKDOWN")
    print("=" * 80)
    print()
    print(f"BEFORE: 31 service companies")
    print(f"AFTER:  {len(service_locs)} service companies")
    print(f"IMPROVEMENT: +{len(service_locs) - 31} ({((len(service_locs)/31)-1)*100:.0f}% increase)" if len(service_locs) > 31 else "")
    print()

    # Detailed breakdown by service type
    service_breakdown = categorize_service_companies(service_locs)

    print("Service Companies by Type:")
    print("-" * 50)

    total_categorized = 0
    for subcat, locs in sorted(service_breakdown.items(), key=lambda x: -len(x[1])):
        if len(locs) > 0:
            print(f"    {subcat}: {len(locs)}")
            total_categorized += len(locs)
            # Show sample names
            for loc in locs[:3]:
                print(f"        - {loc.get('name', 'Unknown')[:50]}")
    print()

    # Also look at other categories that might contain service vehicles
    print("=" * 80)
    print("[5] OTHER CATEGORIES WITH SERVICE VEHICLES")
    print("=" * 80)
    print()

    # Check body_shop, delivery, utility for service vehicle companies
    other_service_categories = ['body_shop', 'delivery', 'utility', 'municipal']
    for cat in other_service_categories:
        cat_locs = [loc for loc in all_locations if loc.get('category') == cat]
        if cat_locs:
            print(f"{cat.upper()}: {len(cat_locs)}")
            # Get breakdown
            breakdown = categorize_service_companies(cat_locs)
            for subcat, locs in sorted(breakdown.items(), key=lambda x: -len(x[1])):
                if len(locs) > 0 and subcat != 'Other Service':
                    print(f"    {subcat}: {len(locs)}")
            print()

    # Revenue potential
    total_vehicles = 0
    total_revenue = 0
    for loc in all_locations:
        vehicles = loc.get('estimated_fleet_size') or loc.get('estimated_vehicles') or 0
        revenue = loc.get('estimated_revenue') or 0
        total_vehicles += vehicles
        total_revenue += revenue

    print("=" * 80)
    print("OKLAHOMA CITY STORM - FINAL SUMMARY")
    print("=" * 80)
    print(f"  Storm Date: October 23, 2025")
    print(f"  Location: Oklahoma City, OK")
    print()
    print("  BEFORE UPDATE:")
    print(f"    Service Companies: 31")
    print()
    print("  AFTER UPDATE:")
    print(f"    Service Companies: {len(service_locs)}")
    print(f"    Total Fleet Locations: {len(all_locations)}")
    print(f"    Estimated Vehicles: {total_vehicles:,}")
    print(f"    Potential Revenue: ${total_revenue:,.0f}")
    print()

    if len(service_locs) > 31:
        improvement = len(service_locs) - 31
        pct = ((len(service_locs) / 31) - 1) * 100
        print(f"  IMPROVEMENT: +{improvement} service companies ({pct:.0f}% increase)")
    print("=" * 80)

    return len(all_locations)


if __name__ == '__main__':
    count = test_updated_categories()
    print(f"\nTest complete. Found {count} total fleet locations.")
