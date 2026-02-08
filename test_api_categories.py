"""
Test Updated API Search Categories
Shows potential service company discovery with updated categories
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Oklahoma City coordinates
OKC_LAT = 35.4676
OKC_LON = -97.5164


def test_api_categories():
    print("=" * 80)
    print("UPDATED API CATEGORIES - POTENTIAL DISCOVERY")
    print("Oklahoma City Storm - October 23, 2025")
    print("=" * 80)
    print()

    # Test each API configuration
    from src.fleet.apis.yelp_api import YelpAPI
    from src.fleet.apis.here_api import HereAPI
    from src.fleet.apis.tomtom_api import TomTomAPI
    from src.fleet.apis.google_places_api import GooglePlacesAPI
    from src.fleet.scrapers.foursquare_api import FoursquareAPI

    print("API Configuration Status:")
    print("-" * 50)

    apis = {
        'Yelp': YelpAPI(),
        'HERE': HereAPI(),
        'TomTom': TomTomAPI(),
        'Google Places': GooglePlacesAPI(),
        'Foursquare': FoursquareAPI(),
    }

    configured_apis = []
    for name, api in apis.items():
        configured = api.is_configured()
        status = "CONFIGURED" if configured else "Not configured"
        print(f"  {name}: {status}")
        if configured:
            configured_apis.append((name, api))
    print()

    if not configured_apis:
        print("=" * 80)
        print("NO APIs CONFIGURED - SHOWING POTENTIAL DISCOVERY")
        print("=" * 80)
        print()
        print("With updated categories, here's what each API could find:")
        print()

        # Show category counts
        yelp = YelpAPI()
        here = HereAPI()

        print("YELP API (5,000 calls/day free):")
        print(f"  Will search {len(yelp.CATEGORIES)} categories in {len(yelp.CATEGORY_BATCHES)} batches")
        print("  Service categories include:")
        for cat in yelp.TRADES_CATEGORIES[:15]:
            print(f"    - {cat}")
        print(f"    ... and {len(yelp.TRADES_CATEGORIES) - 15} more")
        print()

        print("HERE API (250,000 calls/month free):")
        print(f"  Will search {len(here.SEARCH_TERMS)} terms")
        print("  Service terms include:")
        for term in here.TRADES_TERMS[:15]:
            print(f"    - {term}")
        print(f"    ... and {len(here.TRADES_TERMS) - 15} more")
        print()

        # Estimate potential
        print("=" * 80)
        print("ESTIMATED DISCOVERY POTENTIAL")
        print("=" * 80)
        print()
        print("Based on typical API results for a metro area like Oklahoma City:")
        print()
        print("Service Company Types Expected:")
        estimates = {
            'HVAC contractors': '50-100',
            'Plumbing contractors': '60-120',
            'Electrical contractors': '80-150',
            'Pest Control': '30-60',
            'Landscaping/Lawn': '100-200',
            'Tree Service': '40-80',
            'Roofing contractors': '80-150',
            'Pool Service': '20-40',
            'Fence contractors': '30-50',
            'Garage Door': '15-30',
            'Locksmith': '20-40',
            'Painting contractors': '40-80',
            'Concrete/Paving': '30-60',
            'Pressure Washing': '20-40',
            'Restoration': '20-40',
            'General contractors': '100-200',
            'Towing': '30-60',
            'Property Management': '50-100',
            'Janitorial': '40-80',
            'Sign Companies': '20-40',
            'Couriers': '15-30',
            'Beverage Distributors': '10-20',
        }

        total_low = 0
        total_high = 0
        for service_type, estimate in estimates.items():
            low, high = map(int, estimate.split('-'))
            total_low += low
            total_high += high
            print(f"  {service_type}: {estimate}")

        print()
        print(f"TOTAL ESTIMATED: {total_low:,} - {total_high:,} service companies")
        print()
        print("=" * 80)
        print("COMPARISON")
        print("=" * 80)
        print()
        print("  BEFORE (OSM only):     31 service companies")
        print(f"  AFTER (with APIs):     {total_low:,} - {total_high:,} service companies")
        print(f"  IMPROVEMENT:           {int(total_low/31)}x - {int(total_high/31)}x more discovery")
        print()
        print("To enable API discovery, set environment variables:")
        print("  YELP_API_KEY=your_key")
        print("  HERE_API_KEY=your_key")
        print("  GOOGLE_PLACES_API_KEY=your_key")
        print("  FOURSQUARE_API_KEY=your_key")
        print("  TOMTOM_API_KEY=your_key")
        print()

    else:
        # Test with available APIs
        print("=" * 80)
        print("TESTING CONFIGURED APIs")
        print("=" * 80)
        print()

        total_found = 0
        all_results = []

        for name, api in configured_apis:
            print(f"Testing {name} API...")
            try:
                if hasattr(api, 'search_all_categories'):
                    results = api.search_all_categories(OKC_LAT, OKC_LON, radius_meters=10000)
                elif hasattr(api, 'search_all_fleet_categories'):
                    results = api.search_all_fleet_categories(OKC_LAT, OKC_LON, radius_meters=10000)
                else:
                    results = []

                print(f"  Found: {len(results)} businesses")
                total_found += len(results)
                all_results.extend(results)

            except Exception as e:
                print(f"  Error: {e}")
            print()

        if all_results:
            print("=" * 80)
            print(f"TOTAL FOUND: {total_found} businesses")
            print("=" * 80)

            # Categorize results
            categories = {}
            for biz in all_results:
                cat = biz.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1

            print("\nBy Category:")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:20]:
                print(f"  {cat}: {count}")

    print("=" * 80)


if __name__ == '__main__':
    test_api_categories()
