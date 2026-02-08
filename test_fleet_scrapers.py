"""
Test Fleet Business Scrapers
============================

Tests the complete fleet prospecting system:
- BBB scraper (working)
- Manta scraper (new)
- Yellow Pages (with anti-detection)
- Geocoding service
- Unified discovery

Run: python test_fleet_scrapers.py
"""

import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_bbb_scraper():
    """Test BBB scraper on a real city."""
    print("\n" + "="*70)
    print("TESTING BBB SCRAPER")
    print("="*70)

    from src.fleet.scrapers import BBBScraper

    scraper = BBBScraper()

    # Test search for landscaping in Oklahoma City
    print("\nSearching BBB for landscaping in Oklahoma City, OK...")
    businesses = scraper.search("Oklahoma City", "OK", "landscape-contractors", max_pages=1)

    print(f"\nFound {len(businesses)} businesses")

    if businesses:
        print("\nFirst 5 results:")
        for i, biz in enumerate(businesses[:5]):
            print(f"  {i+1}. {biz.get('name', 'N/A')}")
            print(f"     Category: {biz.get('category')}")
            print(f"     BBB Accredited: {biz.get('bbb_accredited')}")

    return len(businesses)


def test_manta_scraper():
    """Test Manta scraper on a real city."""
    print("\n" + "="*70)
    print("TESTING MANTA SCRAPER")
    print("="*70)

    from src.fleet.scrapers import MantaScraper

    scraper = MantaScraper()

    # Test search for pest control in Denver
    print("\nSearching Manta for pest control in Denver, CO...")
    businesses = scraper.search("Denver", "CO", "pest control", max_pages=1)

    print(f"\nFound {len(businesses)} businesses")

    if businesses:
        print("\nFirst 5 results:")
        for i, biz in enumerate(businesses[:5]):
            print(f"  {i+1}. {biz.get('name', 'N/A')}")
            print(f"     Category: {biz.get('category')}")
            if biz.get('employee_count'):
                print(f"     Employees: {biz.get('employee_count')}")

    return len(businesses)


def test_yellowpages_scraper():
    """Test Yellow Pages scraper with anti-detection."""
    print("\n" + "="*70)
    print("TESTING YELLOW PAGES SCRAPER (with anti-detection)")
    print("="*70)

    from src.fleet.scrapers import YellowPagesScraper

    scraper = YellowPagesScraper()

    # Test search for HVAC in Kansas City
    print("\nSearching Yellow Pages for HVAC in Kansas City, MO...")
    businesses = scraper.search("Kansas City", "MO", "hvac", max_pages=1)

    print(f"\nFound {len(businesses)} businesses")

    if businesses:
        print("\nFirst 5 results:")
        for i, biz in enumerate(businesses[:5]):
            print(f"  {i+1}. {biz.get('name', 'N/A')}")
            print(f"     Category: {biz.get('category')}")
            print(f"     Phone: {biz.get('phone', 'N/A')}")

    return len(businesses)


def test_geocoding():
    """Test the geocoding service."""
    print("\n" + "="*70)
    print("TESTING GEOCODING SERVICE")
    print("="*70)

    from src.fleet.scrapers.geocoding import GeocodingService

    geocoder = GeocodingService()

    # Test a few addresses
    test_addresses = [
        ("123 Main St", "Dallas", "TX", None),
        (None, "Denver", "CO", None),  # City center
        ("1600 Pennsylvania Ave", "Washington", "DC", None),
    ]

    for address, city, state, zip_code in test_addresses:
        print(f"\nGeocoding: {address or ''}, {city}, {state}")
        coords = geocoder.geocode(address, city, state, zip_code)

        if coords:
            print(f"  Result: ({coords[0]:.4f}, {coords[1]:.4f})")
        else:
            print("  Result: Not found")

    # Get cache stats
    stats = geocoder.get_cache_stats()
    print(f"\nCache stats: {stats}")

    return stats.get('successful', 0)


def test_unified_discovery():
    """Test the unified discovery service."""
    print("\n" + "="*70)
    print("TESTING UNIFIED DISCOVERY SERVICE")
    print("="*70)

    from src.fleet.scrapers import BusinessDiscoveryService

    service = BusinessDiscoveryService()

    # Discover businesses in San Antonio using BBB and Manta
    print("\nDiscovering fleet prospects in San Antonio, TX...")
    print("Sources: BBB + Manta")
    print("This will take a few minutes...")

    # Use only priority categories to save time
    priority_categories = [
        'car dealers',
        'landscaping',
        'pest control',
        'hvac',
        'roofing contractors',
    ]

    results = service.discover_city(
        "San Antonio", "TX",
        sources=['bbb', 'manta'],
        categories=priority_categories,
        geocode=False  # Skip geocoding for faster test
    )

    print(f"\n{'='*70}")
    print("DISCOVERY RESULTS")
    print(f"{'='*70}")
    print(f"City: {results['city']}, {results['state']}")
    print(f"New businesses: {results['total_new']}")
    print(f"By source: {results['sources']}")

    if results['stats']:
        print(f"\nDatabase totals for San Antonio:")
        print(f"  Total businesses: {results['stats']['total']}")
        print(f"  Estimated vehicles: {results['stats']['total_vehicles']}")
        print(f"  Geocoded: {results['stats'].get('geocoded', 0)}")

    if results.get('errors'):
        print(f"\nErrors: {results['errors']}")

    return results['total_new']


def test_database_stats():
    """Show overall database statistics."""
    print("\n" + "="*70)
    print("DATABASE STATISTICS")
    print("="*70)

    from src.fleet.scrapers import BusinessDiscoveryService

    service = BusinessDiscoveryService()
    stats = service.get_database_stats()

    print(f"\nTotal businesses: {stats.get('total', 0)}")
    print(f"Total estimated vehicles: {stats.get('total_vehicles', 0)}")

    if stats.get('by_tier'):
        print("\nBy tier:")
        for tier in stats['by_tier']:
            print(f"  Tier {tier['tier']}: {tier['count']} businesses, {tier['vehicles']} vehicles")

    if stats.get('by_source'):
        print("\nBy source:")
        for source in stats['by_source']:
            print(f"  {source['source']}: {source['count']} businesses")

    return stats.get('total', 0)


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("FLEET BUSINESS SCRAPER TEST SUITE")
    print("="*70)
    print("\nThis will test the complete PDR fleet prospecting system.")
    print("Sources: BBB, Manta, Yellow Pages (with anti-detection)")
    print("Plus: Geocoding and unified discovery\n")

    results = {}

    # Test individual scrapers
    try:
        results['bbb'] = test_bbb_scraper()
    except Exception as e:
        print(f"BBB test failed: {e}")
        results['bbb'] = 0

    try:
        results['manta'] = test_manta_scraper()
    except Exception as e:
        print(f"Manta test failed: {e}")
        results['manta'] = 0

    # Yellow Pages may still be blocked, so this is optional
    try:
        results['yellowpages'] = test_yellowpages_scraper()
    except Exception as e:
        print(f"Yellow Pages test failed (expected if blocked): {e}")
        results['yellowpages'] = 0

    # Test geocoding
    try:
        results['geocoding'] = test_geocoding()
    except Exception as e:
        print(f"Geocoding test failed: {e}")
        results['geocoding'] = 0

    # Test unified discovery (full integration test)
    try:
        results['discovery'] = test_unified_discovery()
    except Exception as e:
        print(f"Discovery test failed: {e}")
        results['discovery'] = 0

    # Show database stats
    try:
        results['total_in_db'] = test_database_stats()
    except Exception as e:
        print(f"Stats test failed: {e}")
        results['total_in_db'] = 0

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"\nBBB scraper:         {results.get('bbb', 0)} businesses found")
    print(f"Manta scraper:       {results.get('manta', 0)} businesses found")
    print(f"Yellow Pages:        {results.get('yellowpages', 0)} businesses found")
    print(f"Geocoding tests:     {results.get('geocoding', 0)} successful")
    print(f"Discovery (full):    {results.get('discovery', 0)} new businesses")
    print(f"Total in database:   {results.get('total_in_db', 0)} businesses")

    # Overall assessment
    print("\n" + "-"*70)
    if results.get('bbb', 0) > 0 or results.get('manta', 0) > 0:
        print("SUCCESS: At least one scraper is working!")
        print("The system can discover fleet prospects.")
    else:
        print("WARNING: All scrapers returned 0 results.")
        print("Check network connectivity and anti-bot measures.")
    print("-"*70)


if __name__ == '__main__':
    main()
