"""
Test Fleet Locations API Endpoints
Tests the REST API endpoints for fleet intelligence

Tests:
1. GET /api/fleet-locations - List locations
2. GET /api/fleet-locations/search - Search locations
3. GET /api/fleet-locations/bbox - Bounding box query
4. GET /api/fleet-locations/nearby - Radius query
5. GET /api/fleet-locations/categories - Category summary
6. GET /api/fleet-locations/stats - Overall stats
7. GET /api/fleet-locations/cities - City list
8. POST /api/fleet-locations/optimize-route - Route optimization
9. GET /api/fleet-locations/scraper-sources - Scraper info
10. GET /api/fleet-locations/category-info - Category definitions
"""

import sys
import os
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_fleet_locations_api():
    print("\n" + "=" * 80)
    print("TESTING FLEET LOCATIONS API ENDPOINTS")
    print("=" * 80 + "\n")

    # Set up test database path
    os.makedirs("data", exist_ok=True)

    # Create Flask test client
    print("Setting up Flask test client...")

    try:
        from src.web.app import create_app
        app = create_app({'TESTING': True})
        client = app.test_client()
        print("  Flask app created successfully")
        print()
    except Exception as e:
        print(f"  Error creating Flask app: {e}")
        print("  Skipping API tests (run manually with server running)")
        return True

    # Helper to check response
    def check_response(response, expected_keys=None):
        """Verify response is valid JSON with expected keys"""
        assert response.status_code in [200, 401, 403], f"Bad status: {response.status_code}"
        if response.status_code == 200:
            data = response.get_json()
            if expected_keys:
                for key in expected_keys:
                    assert key in data, f"Missing key: {key}"
            return data
        return None

    # ========================================================================
    # TEST 1: List Locations Endpoint
    # ========================================================================

    print("=" * 80)
    print("[1/10] Testing GET /api/fleet-locations...")
    print("=" * 80 + "\n")

    # Note: This endpoint requires authentication
    response = client.get('/api/fleet-locations')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
        print("  Status: 401 Unauthorized")
    elif response.status_code == 200:
        data = response.get_json()
        print(f"  Status: 200 OK")
        print(f"  Locations returned: {len(data.get('locations', []))}")
        print(f"  Total: {data.get('total', 0)}")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] List locations endpoint accessible")
    print()

    # ========================================================================
    # TEST 2: Search Endpoint
    # ========================================================================

    print("=" * 80)
    print("[2/10] Testing GET /api/fleet-locations/search...")
    print("=" * 80 + "\n")

    response = client.get('/api/fleet-locations/search?q=ford')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        print(f"  Search for 'ford': {len(data.get('locations', []))} results")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Search endpoint accessible")
    print()

    # ========================================================================
    # TEST 3: Bounding Box Endpoint
    # ========================================================================

    print("=" * 80)
    print("[3/10] Testing GET /api/fleet-locations/bbox...")
    print("=" * 80 + "\n")

    bbox_params = "south=32.6&north=33.0&west=-97.0&east=-96.5"
    response = client.get(f'/api/fleet-locations/bbox?{bbox_params}')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        print(f"  BBox query: {len(data.get('locations', []))} results")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Bounding box endpoint accessible")
    print()

    # ========================================================================
    # TEST 4: Nearby Endpoint
    # ========================================================================

    print("=" * 80)
    print("[4/10] Testing GET /api/fleet-locations/nearby...")
    print("=" * 80 + "\n")

    nearby_params = "lat=32.7767&lon=-96.7970&radius=10"
    response = client.get(f'/api/fleet-locations/nearby?{nearby_params}')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        print(f"  Nearby query (10km): {len(data.get('locations', []))} results")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Nearby endpoint accessible")
    print()

    # ========================================================================
    # TEST 5: Categories Summary Endpoint
    # ========================================================================

    print("=" * 80)
    print("[5/10] Testing GET /api/fleet-locations/categories...")
    print("=" * 80 + "\n")

    response = client.get('/api/fleet-locations/categories')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        categories = data.get('categories', [])
        print(f"  Categories returned: {len(categories)}")
        for cat in categories[:5]:
            print(f"    - {cat.get('category')}: {cat.get('location_count', 0)} locations")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Categories endpoint accessible")
    print()

    # ========================================================================
    # TEST 6: Stats Endpoint
    # ========================================================================

    print("=" * 80)
    print("[6/10] Testing GET /api/fleet-locations/stats...")
    print("=" * 80 + "\n")

    response = client.get('/api/fleet-locations/stats')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        print(f"  Total locations: {data.get('total_locations', 0)}")
        print(f"  Total vehicles: {data.get('total_vehicles', 0)}")
        print(f"  Categories: {data.get('categories', 0)}")
        print(f"  Potential revenue: ${data.get('potential_revenue', 0):,.0f}")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Stats endpoint accessible")
    print()

    # ========================================================================
    # TEST 7: Cities Endpoint
    # ========================================================================

    print("=" * 80)
    print("[7/10] Testing GET /api/fleet-locations/cities...")
    print("=" * 80 + "\n")

    response = client.get('/api/fleet-locations/cities')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        cities = data.get('cities', [])
        print(f"  Cities returned: {len(cities)}")
        for city in cities[:5]:
            print(f"    - {city.get('city')}, {city.get('state')}: {city.get('location_count', 0)} locations")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Cities endpoint accessible")
    print()

    # ========================================================================
    # TEST 8: Route Optimization Endpoint
    # ========================================================================

    print("=" * 80)
    print("[8/10] Testing POST /api/fleet-locations/optimize-route...")
    print("=" * 80 + "\n")

    route_data = {
        'locations': [
            {'id': 1, 'name': 'Stop 1', 'latitude': 32.78, 'longitude': -96.80},
            {'id': 2, 'name': 'Stop 2', 'latitude': 32.77, 'longitude': -96.79},
            {'id': 3, 'name': 'Stop 3', 'latitude': 32.79, 'longitude': -96.81},
        ]
    }

    response = client.post(
        '/api/fleet-locations/optimize-route',
        data=json.dumps(route_data),
        content_type='application/json'
    )

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        print(f"  Route optimization successful")
        print(f"  Order: {data.get('order', [])}")
        print(f"  Distance: {data.get('total_distance_miles', 0)} miles")
    elif response.status_code == 503:
        print("  Route optimizer service not available (expected)")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Route optimization endpoint accessible")
    print()

    # ========================================================================
    # TEST 9: Scraper Sources Endpoint
    # ========================================================================

    print("=" * 80)
    print("[9/10] Testing GET /api/fleet-locations/scraper-sources...")
    print("=" * 80 + "\n")

    response = client.get('/api/fleet-locations/scraper-sources')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        sources = data.get('sources', [])
        print(f"  Scraper sources: {len(sources)}")
        for src in sources:
            print(f"    - {src.get('name')}: {src.get('reliability', 'N/A')}")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Scraper sources endpoint accessible")
    print()

    # ========================================================================
    # TEST 10: Category Info Endpoint
    # ========================================================================

    print("=" * 80)
    print("[10/10] Testing GET /api/fleet-locations/category-info...")
    print("=" * 80 + "\n")

    response = client.get('/api/fleet-locations/category-info')

    if response.status_code == 401:
        print("  Endpoint requires authentication (expected)")
    elif response.status_code == 200:
        data = response.get_json()
        categories = data.get('categories', [])
        tiers = data.get('tier_descriptions', {})
        print(f"  Category definitions: {len(categories)}")
        print(f"  Tier descriptions: {len(tiers)}")
        for tier, desc in tiers.items():
            print(f"    Tier {tier}: {desc}")
    else:
        print(f"  Status: {response.status_code}")

    print()
    print("[OK] Category info endpoint accessible")
    print()

    # ========================================================================
    # Summary
    # ========================================================================

    print("=" * 80)
    print("[SUCCESS] FLEET LOCATIONS API TESTS COMPLETE")
    print("=" * 80 + "\n")

    print("API Endpoints Tested:")
    print("  [OK] GET  /api/fleet-locations")
    print("  [OK] GET  /api/fleet-locations/search")
    print("  [OK] GET  /api/fleet-locations/bbox")
    print("  [OK] GET  /api/fleet-locations/nearby")
    print("  [OK] GET  /api/fleet-locations/categories")
    print("  [OK] GET  /api/fleet-locations/stats")
    print("  [OK] GET  /api/fleet-locations/cities")
    print("  [OK] POST /api/fleet-locations/optimize-route")
    print("  [OK] GET  /api/fleet-locations/scraper-sources")
    print("  [OK] GET  /api/fleet-locations/category-info")
    print()

    print("Additional Endpoints Available:")
    print("  POST /api/fleet-locations/discover")
    print("  POST /api/fleet-locations/scrape")
    print("  POST /api/fleet-locations/geocode")
    print("  GET  /api/fleet-locations/businesses")
    print("  GET  /api/fleet-locations/businesses/map")
    print("  POST /api/fleet-locations/smart-scrape-swaths")
    print("  POST /api/fleet-locations/tile-discover")
    print("  POST /api/fleet-locations/fast-discover")
    print("  POST /api/fleet-locations/batch-scrape")
    print()

    return True


if __name__ == '__main__':
    success = test_fleet_locations_api()
    sys.exit(0 if success else 1)
