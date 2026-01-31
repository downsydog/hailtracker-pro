#!/usr/bin/env python3
"""
Test all discovery APIs.

Usage:
    python scripts/test_discovery_apis.py

This tests each API individually:
- Foursquare (100k/month)
- Yelp (5k/day)
- HERE (250k/month)
- TomTom (2.5k/day)
- Google Places ($200 credit)

Make sure your .env file has the API keys set:
    FOURSQUARE_API_KEY=your_key_here
    YELP_API_KEY=your_key_here
    HERE_API_KEY=your_key_here
    TOMTOM_API_KEY=your_key_here
    GOOGLE_PLACES_API_KEY=your_key_here
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

# Test location: Oklahoma City (center of Hail Alley)
TEST_LAT = 35.4676
TEST_LON = -97.5164
TEST_RADIUS = 5000  # meters


def test_foursquare():
    """Test Foursquare API."""
    print("\n" + "=" * 60)
    print("FOURSQUARE API")
    print("=" * 60)

    try:
        from src.fleet.scrapers.foursquare_api import FoursquareAPI
        fs = FoursquareAPI()

        print(f"Configured: {fs.is_configured()}")

        if not fs.is_configured():
            print("  Set FOURSQUARE_API_KEY in .env")
            print("  Get free key at: https://foursquare.com/developers")
            return

        # Test connection
        status = fs.test_connection()
        print(f"Connection: {status['message']}")

        if status['success']:
            # Search for businesses
            results = fs.search_all_fleet_categories(TEST_LAT, TEST_LON, TEST_RADIUS)
            print(f"Found: {len(results)} businesses")

            # Show sample results
            for r in results[:5]:
                print(f"  - {r.get('name')} ({r.get('category')}) | {r.get('address', 'No address')}")

    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def test_yelp():
    """Test Yelp API."""
    print("\n" + "=" * 60)
    print("YELP API")
    print("=" * 60)

    try:
        from src.fleet.apis.yelp_api import YelpAPI
        yelp = YelpAPI()

        print(f"Configured: {yelp.is_configured()}")

        if not yelp.is_configured():
            print("  Set YELP_API_KEY in .env")
            print("  Get free key at: https://www.yelp.com/developers")
            return

        # Test connection
        status = yelp.test_connection()
        print(f"Connection: {status['message']}")

        if status['success']:
            # Search for businesses
            results = yelp.search_all_categories(TEST_LAT, TEST_LON, TEST_RADIUS)
            print(f"Found: {len(results)} businesses")

            # Show sample results
            for r in results[:5]:
                print(f"  - {r.get('name')} ({r.get('category')}) | {r.get('city')}")

    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def test_here():
    """Test HERE API."""
    print("\n" + "=" * 60)
    print("HERE API")
    print("=" * 60)

    try:
        from src.fleet.apis.here_api import HereAPI
        here = HereAPI()

        print(f"Configured: {here.is_configured()}")

        if not here.is_configured():
            print("  Set HERE_API_KEY in .env")
            print("  Get free key at: https://developer.here.com")
            return

        # Test connection
        status = here.test_connection()
        print(f"Connection: {status['message']}")

        if status['success']:
            # Search for businesses
            results = here.search_all_categories(TEST_LAT, TEST_LON, TEST_RADIUS)
            print(f"Found: {len(results)} businesses")

            # Show sample results
            for r in results[:5]:
                print(f"  - {r.get('name')} ({r.get('category')}) | {r.get('city')}")

    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def test_tomtom():
    """Test TomTom API."""
    print("\n" + "=" * 60)
    print("TOMTOM API")
    print("=" * 60)

    try:
        from src.fleet.apis.tomtom_api import TomTomAPI
        tt = TomTomAPI()

        print(f"Configured: {tt.is_configured()}")

        if not tt.is_configured():
            print("  Set TOMTOM_API_KEY in .env")
            print("  Get free key at: https://developer.tomtom.com")
            return

        # Test connection
        status = tt.test_connection()
        print(f"Connection: {status['message']}")

        if status['success']:
            # Search for businesses
            results = tt.search_all_categories(TEST_LAT, TEST_LON, TEST_RADIUS)
            print(f"Found: {len(results)} businesses")

            # Show sample results
            for r in results[:5]:
                print(f"  - {r.get('name')} ({r.get('category')}) | {r.get('city')}")

    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def test_google():
    """Test Google Places API."""
    print("\n" + "=" * 60)
    print("GOOGLE PLACES API")
    print("=" * 60)

    try:
        from src.fleet.apis.google_places_api import GooglePlacesAPI
        google = GooglePlacesAPI()

        print(f"Configured: {google.is_configured()}")

        if not google.is_configured():
            print("  Set GOOGLE_PLACES_API_KEY in .env")
            print("  Get key at: https://console.cloud.google.com")
            print("  Note: This API costs money after $200/month credit")
            return

        # Test connection
        status = google.test_connection()
        print(f"Connection: {status['message']}")

        if status['success']:
            # Search for businesses (just one keyword to save API calls)
            results = google.search_radius(TEST_LAT, TEST_LON, TEST_RADIUS, keyword='landscaping')
            print(f"Found: {len(results)} landscaping businesses")

            # Show sample results
            for r in results[:5]:
                print(f"  - {r.get('name')} ({r.get('category')}) | {r.get('address', 'No address')}")

    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def test_swath_discovery():
    """Test the integrated swath discovery service."""
    print("\n" + "=" * 60)
    print("SWATH DISCOVERY SERVICE")
    print("=" * 60)

    try:
        from src.business.swath_discovery import SwathDiscoveryService
        service = SwathDiscoveryService()

        # Get API status
        status = service.get_api_status()
        print("\nAPI Configuration Status:")
        for name, info in status.items():
            configured = "YES" if info['configured'] else "NO"
            print(f"  {name.upper():12} Configured: {configured:3} | Free: {info['free_tier']}")

    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    print("\n" + "=" * 60)
    print("DISCOVERY API TEST SUITE")
    print("=" * 60)
    print(f"Test location: Oklahoma City ({TEST_LAT}, {TEST_LON})")
    print(f"Search radius: {TEST_RADIUS}m")

    # Run all tests
    test_foursquare()
    test_yelp()
    test_here()
    test_tomtom()
    test_google()
    test_swath_discovery()

    print("\n" + "=" * 60)
    print("SETUP INSTRUCTIONS")
    print("=" * 60)
    print("""
Add these to your .env file:

# FREE Business Discovery APIs
FOURSQUARE_API_KEY=your_key_here    # 100k calls/month
YELP_API_KEY=your_key_here          # 5k calls/day (150k/month)
HERE_API_KEY=your_key_here          # 250k calls/month
TOMTOM_API_KEY=your_key_here        # 2.5k calls/day (75k/month)
GOOGLE_PLACES_API_KEY=your_key_here # $200/month credit

Get keys at:
- Foursquare: https://foursquare.com/developers
- Yelp: https://www.yelp.com/developers/v3/manage_app
- HERE: https://developer.here.com
- TomTom: https://developer.tomtom.com
- Google: https://console.cloud.google.com

Recommended sources: OSM (free unlimited), Foursquare, Yelp
""")


if __name__ == '__main__':
    main()
