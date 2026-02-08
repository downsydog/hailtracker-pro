"""
Full Discovery - Oklahoma City Storm
October 23, 2025

Run ALL APIs: OSM, Yelp, HERE, TomTom, Foursquare, Google
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Oklahoma City coordinates
OKC_LAT = 35.4676
OKC_LON = -97.5164
RADIUS_METERS = 25000  # 25km radius to cover metro area


def categorize_by_service_type(businesses):
    """Categorize businesses by service type."""

    categories = {
        'HVAC': ['hvac', 'heating', 'cooling', 'air conditioning', 'furnace', 'ac repair', 'heat pump'],
        'Plumbing': ['plumb', 'plumber', 'pipe', 'drain', 'sewer', 'water heater'],
        'Electrical': ['electric', 'electrician', 'wiring', 'power'],
        'Pest Control': ['pest', 'exterminator', 'termite', 'bug', 'rodent', 'mosquito'],
        'Landscaping': ['landscap', 'lawn care', 'lawn service', 'yard', 'garden', 'mowing'],
        'Tree Service': ['tree service', 'tree trim', 'tree removal', 'arborist', 'stump'],
        'Roofing': ['roof', 'roofing', 'shingle', 'gutter'],
        'Siding': ['siding', 'fascia', 'soffit'],
        'Fence': ['fence', 'fencing', 'gate'],
        'Pool Service': ['pool', 'spa', 'hot tub'],
        'Garage Door': ['garage door', 'overhead door'],
        'Locksmith': ['locksmith', 'lock ', 'key '],
        'Painting': ['paint', 'painter', 'coating'],
        'Flooring': ['floor', 'flooring', 'carpet', 'tile', 'hardwood'],
        'Concrete/Paving': ['concrete', 'paving', 'asphalt', 'driveway', 'masonry'],
        'Pressure Washing': ['pressure wash', 'power wash'],
        'Window Cleaning': ['window clean', 'glass clean'],
        'Restoration': ['restoration', 'water damage', 'fire damage', 'mold', 'remediation'],
        'Septic': ['septic', 'porta potty', 'portable toilet'],
        'General Contractor': ['general contractor', 'remodel', 'renovation', 'builder', 'construction co'],
        'Excavation': ['excavat', 'grading', 'earthwork', 'dirt work'],
        'Towing': ['tow', 'towing', 'wrecker', 'roadside'],
        'Auto Glass': ['auto glass', 'windshield', 'safelite'],
        'Auto Body': ['body shop', 'collision', 'auto body', 'dent'],
        'Beverage Distributor': ['beverage', 'coca-cola', 'pepsi', 'beer dist', 'wine dist'],
        'Linen/Uniform': ['linen', 'uniform', 'cintas', 'aramark'],
        'Property Management': ['property manage', 'apartment manage', 'hoa', 'real estate manage'],
        'Janitorial': ['janitor', 'cleaning service', 'commercial clean', 'office clean'],
        'Sign Company': ['sign company', 'sign shop', 'signage', 'banner'],
        'Courier/Delivery': ['courier', 'messenger', 'express delivery'],
        'Home Health': ['home health', 'hospice', 'home care'],
        'Medical Transport': ['medical transport', 'ambulance', 'patient transport'],
        'Cable/Telecom': ['cable', 'satellite', 'dish', 'directv', 'cox', 'att ', 'verizon'],
        'Security': ['security', 'alarm', 'adt', 'monitoring'],
        'Waste/Junk': ['waste', 'garbage', 'trash', 'junk removal', 'hauling', 'dumpster'],
        'Equipment Rental': ['equipment rental', 'tool rental', 'rent-all'],
        'Moving': ['moving', 'movers', 'relocation'],
        'Carpet Cleaning': ['carpet clean', 'rug clean', 'upholstery clean'],
        'Appliance Repair': ['appliance repair', 'appliance service'],
        'Car Dealer': ['car dealer', 'auto dealer', 'motors', 'dealership', 'chevrolet', 'ford', 'toyota', 'honda'],
        'Other Service': [],
    }

    results = {cat: [] for cat in categories}

    for biz in businesses:
        name = (biz.get('name') or '').lower()
        category = (biz.get('category') or '').lower()
        combined = f"{name} {category}"

        matched = False
        for cat, keywords in categories.items():
            if cat == 'Other Service':
                continue
            for kw in keywords:
                if kw in combined:
                    results[cat].append(biz)
                    matched = True
                    break
            if matched:
                break

        if not matched:
            results['Other Service'].append(biz)

    return results


def run_full_discovery():
    print("=" * 80)
    print("FULL DISCOVERY - OKLAHOMA CITY STORM")
    print("October 23, 2025")
    print("=" * 80)
    print()
    print(f"Location: {OKC_LAT}, {OKC_LON}")
    print(f"Radius: {RADIUS_METERS/1000:.0f} km")
    print()

    all_businesses = []
    seen_names = set()  # For deduplication
    api_results = {}

    # ========================================================================
    # 1. YELP API
    # ========================================================================
    print("-" * 80)
    print("[1/6] YELP API")
    print("-" * 80)

    try:
        from src.fleet.apis.yelp_api import YelpAPI
        yelp = YelpAPI()

        if yelp.is_configured():
            print("  Status: CONFIGURED")
            print("  Searching all categories...")
            results = yelp.search_all_categories(OKC_LAT, OKC_LON, RADIUS_METERS)

            # Dedupe
            new_count = 0
            for biz in results:
                name_key = (biz.get('name', '').lower(), biz.get('address', '').lower()[:30])
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_businesses.append(biz)
                    new_count += 1

            api_results['Yelp'] = len(results)
            print(f"  Found: {len(results)} businesses ({new_count} unique)")
        else:
            print("  Status: NOT CONFIGURED")
            api_results['Yelp'] = 0
    except Exception as e:
        print(f"  Error: {e}")
        api_results['Yelp'] = 0
    print()

    # ========================================================================
    # 2. HERE API
    # ========================================================================
    print("-" * 80)
    print("[2/6] HERE API")
    print("-" * 80)

    try:
        from src.fleet.apis.here_api import HereAPI
        here = HereAPI()

        if here.is_configured():
            print("  Status: CONFIGURED")
            print("  Searching priority terms...")
            results = here.search_priority_categories(OKC_LAT, OKC_LON, RADIUS_METERS)

            new_count = 0
            for biz in results:
                name_key = (biz.get('name', '').lower(), biz.get('address', '').lower()[:30])
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_businesses.append(biz)
                    new_count += 1

            api_results['HERE'] = len(results)
            print(f"  Found: {len(results)} businesses ({new_count} unique)")
        else:
            print("  Status: NOT CONFIGURED")
            api_results['HERE'] = 0
    except Exception as e:
        print(f"  Error: {e}")
        api_results['HERE'] = 0
    print()

    # ========================================================================
    # 3. TOMTOM API
    # ========================================================================
    print("-" * 80)
    print("[3/6] TOMTOM API")
    print("-" * 80)

    try:
        from src.fleet.apis.tomtom_api import TomTomAPI
        tomtom = TomTomAPI()

        if tomtom.is_configured():
            print("  Status: CONFIGURED")
            print("  Searching priority terms...")
            results = tomtom.search_priority_categories(OKC_LAT, OKC_LON, RADIUS_METERS)

            new_count = 0
            for biz in results:
                name_key = (biz.get('name', '').lower(), biz.get('address', '').lower()[:30])
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_businesses.append(biz)
                    new_count += 1

            api_results['TomTom'] = len(results)
            print(f"  Found: {len(results)} businesses ({new_count} unique)")
        else:
            print("  Status: NOT CONFIGURED")
            api_results['TomTom'] = 0
    except Exception as e:
        print(f"  Error: {e}")
        api_results['TomTom'] = 0
    print()

    # ========================================================================
    # 4. FOURSQUARE API
    # ========================================================================
    print("-" * 80)
    print("[4/6] FOURSQUARE API")
    print("-" * 80)

    try:
        from src.fleet.scrapers.foursquare_api import FoursquareAPI
        foursquare = FoursquareAPI()

        if foursquare.is_configured():
            print("  Status: CONFIGURED")
            print("  Searching all fleet categories...")
            results = foursquare.search_all_fleet_categories(OKC_LAT, OKC_LON, RADIUS_METERS)

            new_count = 0
            for biz in results:
                name_key = (biz.get('name', '').lower(), biz.get('address', '').lower()[:30])
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_businesses.append(biz)
                    new_count += 1

            api_results['Foursquare'] = len(results)
            print(f"  Found: {len(results)} businesses ({new_count} unique)")
        else:
            print("  Status: NOT CONFIGURED")
            api_results['Foursquare'] = 0
    except Exception as e:
        print(f"  Error: {e}")
        api_results['Foursquare'] = 0
    print()

    # ========================================================================
    # 5. GOOGLE PLACES API
    # ========================================================================
    print("-" * 80)
    print("[5/6] GOOGLE PLACES API")
    print("-" * 80)

    try:
        from src.fleet.apis.google_places_api import GooglePlacesAPI
        google = GooglePlacesAPI()

        if google.is_configured():
            print("  Status: CONFIGURED")
            print("  Searching priority keywords...")
            results = google.search_priority_categories(OKC_LAT, OKC_LON, RADIUS_METERS)

            new_count = 0
            for biz in results:
                name_key = (biz.get('name', '').lower(), biz.get('address', '').lower()[:30])
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_businesses.append(biz)
                    new_count += 1

            api_results['Google'] = len(results)
            print(f"  Found: {len(results)} businesses ({new_count} unique)")
        else:
            print("  Status: NOT CONFIGURED")
            api_results['Google'] = 0
    except Exception as e:
        print(f"  Error: {e}")
        api_results['Google'] = 0
    print()

    # ========================================================================
    # 6. OSM (Existing Database)
    # ========================================================================
    print("-" * 80)
    print("[6/6] OSM DATABASE")
    print("-" * 80)

    try:
        from src.business.fleet_locations import FleetLocationManager
        db_path = os.path.join(os.path.dirname(__file__), "data", "fleet_locations.db")

        if os.path.exists(db_path):
            manager = FleetLocationManager(db_path)
            # Get existing locations from bbox
            results = manager.get_locations_in_bbox(35.25, -97.75, 35.65, -97.30)

            new_count = 0
            for biz in results:
                name_key = (biz.get('name', '').lower(), biz.get('address', '').lower()[:30])
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_businesses.append(biz)
                    new_count += 1

            api_results['OSM'] = len(results)
            print(f"  Found: {len(results)} locations ({new_count} unique)")
        else:
            print("  Database not found")
            api_results['OSM'] = 0
    except Exception as e:
        print(f"  Error: {e}")
        api_results['OSM'] = 0
    print()

    # ========================================================================
    # RESULTS SUMMARY
    # ========================================================================
    print("=" * 80)
    print("API RESULTS SUMMARY")
    print("=" * 80)
    print()

    for api, count in api_results.items():
        status = "OK" if count > 0 else "NO DATA"
        print(f"  {api:15} : {count:5} businesses  [{status}]")

    print()
    print(f"  TOTAL (with dedup): {len(all_businesses)} unique businesses")
    print()

    # ========================================================================
    # SERVICE TYPE BREAKDOWN
    # ========================================================================
    print("=" * 80)
    print("SERVICE TYPE BREAKDOWN")
    print("=" * 80)
    print()

    breakdown = categorize_by_service_type(all_businesses)

    # Sort by count
    sorted_breakdown = sorted(breakdown.items(), key=lambda x: -len(x[1]))

    total_categorized = 0
    for service_type, businesses in sorted_breakdown:
        count = len(businesses)
        if count > 0:
            total_categorized += count
            print(f"  {service_type:25} : {count:4}")
            # Show top 3 examples
            for biz in businesses[:3]:
                name = biz.get('name', 'Unknown')[:45]
                source = biz.get('source', 'unknown')
                print(f"      - {name} [{source}]")
            if count > 3:
                print(f"      ... and {count - 3} more")

    print()
    print("=" * 80)
    print("FINAL SUMMARY - OKLAHOMA CITY STORM")
    print("=" * 80)
    print()
    print(f"  Storm Date: October 23, 2025")
    print(f"  Search Radius: {RADIUS_METERS/1000:.0f} km")
    print()
    print("  APIs Used:")
    for api, count in api_results.items():
        if count > 0:
            print(f"    - {api}: {count} results")
    print()
    print(f"  TOTAL UNIQUE BUSINESSES: {len(all_businesses)}")
    print()

    # Count service companies specifically (excluding car dealers, auto body)
    service_types = ['HVAC', 'Plumbing', 'Electrical', 'Pest Control', 'Landscaping',
                     'Tree Service', 'Roofing', 'Fence', 'Pool Service', 'Garage Door',
                     'Locksmith', 'Painting', 'Flooring', 'Concrete/Paving', 'Restoration',
                     'General Contractor', 'Towing', 'Property Management', 'Janitorial',
                     'Sign Company', 'Septic', 'Pressure Washing', 'Carpet Cleaning',
                     'Moving', 'Security', 'Waste/Junk']

    service_count = sum(len(breakdown.get(st, [])) for st in service_types)

    print("  BEFORE (OSM only): 31 service companies")
    print(f"  AFTER (all APIs):  {service_count} service companies")
    if service_count > 31:
        print(f"  IMPROVEMENT:       +{service_count - 31} ({service_count/31:.1f}x more)")
    print()
    print("=" * 80)

    return len(all_businesses)


if __name__ == '__main__':
    count = run_full_discovery()
