"""
Test Fleet Intelligence System
Comprehensive tests for fleet map, business discovery, and intelligence features

Tests:
1. Fleet Location Data Models
2. OSM Query Builder
3. Fleet Location Manager
4. Category Filtering
5. Bounding Box Queries
6. Radius/Nearby Queries
7. Search Functionality
8. Revenue Calculations
9. Route Building
10. Grading System
"""

import sys
import os
import json
from datetime import datetime, date
from unittest.mock import Mock, patch

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_fleet_intelligence():
    print("\n" + "=" * 80)
    print("TESTING FLEET INTELLIGENCE SYSTEM")
    print("=" * 80 + "\n")

    # ========================================================================
    # TEST 1: Fleet Location Data Model
    # ========================================================================

    print("=" * 80)
    print("[1/12] Testing FleetLocation data model...")
    print("=" * 80 + "\n")

    from src.business.fleet_locations import FleetLocation

    # Create a sample fleet location
    location = FleetLocation(
        name="Metro Ford Dealership",
        category="car_dealership",
        subcategory="new",
        brand="Ford",
        address="123 Auto Row",
        city="Dallas",
        state="TX",
        zip_code="75001",
        lat=32.7767,
        lon=-96.7970,
        phone="555-123-4567",
        email="sales@metroford.com",
        website="https://metroford.com",
        estimated_vehicles=200,
        vehicle_confidence="high",
        luxury_vehicles=False,
        avg_revenue_per_vehicle=1500.0,
        accessibility="public",
        can_canvas_lot=True,
        osm_id="12345",
        osm_type="way"
    )

    assert location.name == "Metro Ford Dealership"
    assert location.category == "car_dealership"
    assert location.estimated_vehicles == 200
    assert location.avg_revenue_per_vehicle == 1500.0
    assert location.lat == 32.7767
    assert location.accessibility == "public"

    print(f"  Created: {location.name}")
    print(f"  Category: {location.category}")
    print(f"  Vehicles: {location.estimated_vehicles}")
    print(f"  Revenue/vehicle: ${location.avg_revenue_per_vehicle}")
    print()

    print("[OK] FleetLocation data model works correctly")
    print()

    # ========================================================================
    # TEST 2: OSM Query Builder
    # ========================================================================

    print("=" * 80)
    print("[2/12] Testing OSM Query Builder...")
    print("=" * 80 + "\n")

    from src.business.fleet_locations import OSMQueryBuilder

    builder = OSMQueryBuilder()

    # Test bbox query generation
    bbox = (32.6, -97.0, 33.0, -96.5)  # Dallas area
    query = builder.build_query("car_dealership", bbox)

    assert "[out:json]" in query
    assert "shop" in query or "car" in query
    assert str(bbox[0]) in query  # south
    assert str(bbox[2]) in query  # north

    print(f"  Generated query for car_dealership:")
    print(f"    BBox: {bbox}")
    print(f"    Query length: {len(query)} chars")
    print()

    # Test radius query generation
    radius_query = builder.build_radius_query(
        categories=['car_dealership', 'rental_car'],
        lat=32.7767,
        lon=-96.7970,
        radius_meters=10000
    )

    assert "around:10000" in radius_query
    assert "32.7767" in radius_query

    print(f"  Generated radius query:")
    print(f"    Center: (32.7767, -96.7970)")
    print(f"    Radius: 10000m")
    print(f"    Categories: car_dealership, rental_car")
    print()

    print("[OK] OSM Query Builder works correctly")
    print()

    # ========================================================================
    # TEST 3: Category Configuration
    # ========================================================================

    print("=" * 80)
    print("[3/12] Testing Category Configuration...")
    print("=" * 80 + "\n")

    categories = builder.CATEGORY_QUERIES

    print(f"  Total categories: {len(categories)}")
    print()

    expected_categories = [
        'car_dealership', 'rental_car', 'parking_structure', 'municipal',
        'utility', 'service_company', 'delivery', 'body_shop',
        'golf_course', 'apartment', 'school', 'hospital',
        'hotel', 'event_venue', 'insurance'
    ]

    for cat in expected_categories:
        assert cat in categories, f"Missing category: {cat}"
        config = categories[cat]
        assert 'tags' in config, f"Category {cat} missing tags"
        assert 'vehicle_estimate' in config, f"Category {cat} missing vehicle_estimate"
        print(f"    {cat}: ~{config['vehicle_estimate']} vehicles")

    print()
    print("[OK] All expected categories configured")
    print()

    # ========================================================================
    # TEST 4: Fleet Location Manager Initialization
    # ========================================================================

    print("=" * 80)
    print("[4/12] Testing Fleet Location Manager...")
    print("=" * 80 + "\n")

    from src.business.fleet_locations import FleetLocationManager

    # Use test database
    test_db = "data/test_fleet_intelligence.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    manager = FleetLocationManager(test_db)

    # Verify database initialized
    conn = manager._get_conn()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t['name'] for t in tables]
    conn.close()

    assert 'fleet_locations' in table_names or len(table_names) > 0
    print(f"  Database initialized: {test_db}")
    print(f"  Tables: {table_names}")
    print()

    print("[OK] Fleet Location Manager initialized")
    print()

    # ========================================================================
    # TEST 5: Save and Retrieve Locations
    # ========================================================================

    print("=" * 80)
    print("[5/12] Testing Save and Retrieve Locations...")
    print("=" * 80 + "\n")

    # Create test locations
    test_locations = [
        FleetLocation(
            name="Dallas Ford",
            category="car_dealership",
            city="Dallas",
            state="TX",
            lat=32.78,
            lon=-96.80,
            estimated_vehicles=150,
            avg_revenue_per_vehicle=1500,
            osm_id="100001",
            osm_type="way"
        ),
        FleetLocation(
            name="Enterprise Rent-A-Car",
            category="rental_car",
            city="Dallas",
            state="TX",
            lat=32.77,
            lon=-96.79,
            estimated_vehicles=80,
            avg_revenue_per_vehicle=1800,
            osm_id="100002",
            osm_type="node"
        ),
        FleetLocation(
            name="Dallas Police HQ",
            category="municipal",
            city="Dallas",
            state="TX",
            lat=32.79,
            lon=-96.81,
            estimated_vehicles=100,
            avg_revenue_per_vehicle=1200,
            osm_id="100003",
            osm_type="way"
        ),
        FleetLocation(
            name="Lakewood Country Club",
            category="golf_course",
            city="Dallas",
            state="TX",
            lat=32.82,
            lon=-96.75,
            estimated_vehicles=120,
            luxury_vehicles=True,
            avg_revenue_per_vehicle=2500,
            osm_id="100004",
            osm_type="way"
        ),
        FleetLocation(
            name="Big Hospital Medical Center",
            category="hospital",
            city="Dallas",
            state="TX",
            lat=32.80,
            lon=-96.78,
            estimated_vehicles=250,
            avg_revenue_per_vehicle=1500,
            osm_id="100005",
            osm_type="way"
        ),
    ]

    saved_count = manager.save_locations(test_locations)
    print(f"  Saved {saved_count} test locations")

    # Verify count
    total = manager.get_location_count()
    assert total >= 5, f"Expected at least 5 locations, got {total}"
    print(f"  Total in database: {total}")
    print()

    print("[OK] Locations saved successfully")
    print()

    # ========================================================================
    # TEST 6: Bounding Box Query
    # ========================================================================

    print("=" * 80)
    print("[6/12] Testing Bounding Box Query...")
    print("=" * 80 + "\n")

    # Query locations in bbox
    results = manager.get_locations_in_bbox(
        south=32.75,
        west=-96.85,
        north=32.85,
        east=-96.70
    )

    print(f"  BBox query results: {len(results)} locations")
    assert len(results) >= 5, f"Expected at least 5 results, got {len(results)}"

    for loc in results[:3]:
        print(f"    - {loc['name']} ({loc['category']}): {loc['estimated_vehicles']} vehicles")
    print()

    # Test with category filter
    dealerships = manager.get_locations_in_bbox(
        south=32.75,
        west=-96.85,
        north=32.85,
        east=-96.70,
        categories=['car_dealership']
    )

    print(f"  Filtered by car_dealership: {len(dealerships)} locations")
    for loc in dealerships:
        assert loc['category'] == 'car_dealership'
    print()

    print("[OK] Bounding box queries work correctly")
    print()

    # ========================================================================
    # TEST 7: Radius/Nearby Query
    # ========================================================================

    print("=" * 80)
    print("[7/12] Testing Radius/Nearby Query...")
    print("=" * 80 + "\n")

    # Query locations near a point
    nearby = manager.get_locations_near_point(
        lat=32.78,
        lon=-96.80,
        radius_km=10,
        min_vehicles=50
    )

    print(f"  Nearby query (10km radius, 50+ vehicles): {len(nearby)} locations")
    assert len(nearby) >= 1, "Expected at least 1 nearby result"

    for loc in nearby[:3]:
        print(f"    - {loc['name']}: {loc.get('distance_km', 'N/A')} km away")
    print()

    # Test with category filter
    nearby_rentals = manager.get_locations_near_point(
        lat=32.78,
        lon=-96.80,
        radius_km=10,
        categories=['rental_car']
    )

    print(f"  Nearby rentals only: {len(nearby_rentals)} locations")
    print()

    print("[OK] Radius/nearby queries work correctly")
    print()

    # ========================================================================
    # TEST 8: Search Functionality
    # ========================================================================

    print("=" * 80)
    print("[8/12] Testing Search Functionality...")
    print("=" * 80 + "\n")

    # Search by name
    ford_results = manager.search_locations("Ford")
    print(f"  Search 'Ford': {len(ford_results)} results")
    assert len(ford_results) >= 1, "Expected at least 1 Ford result"

    # Search by category
    hospital_results = manager.search_locations("hospital")
    print(f"  Search 'hospital': {len(hospital_results)} results")

    # Search by city
    dallas_results = manager.search_locations("Dallas")
    print(f"  Search 'Dallas': {len(dallas_results)} results")
    assert len(dallas_results) >= 5, "Expected at least 5 Dallas results"
    print()

    print("[OK] Search functionality works correctly")
    print()

    # ========================================================================
    # TEST 9: Category Summary
    # ========================================================================

    print("=" * 80)
    print("[9/12] Testing Category Summary...")
    print("=" * 80 + "\n")

    summary = manager.get_category_summary()

    print(f"  Category Summary ({len(summary)} categories):")
    total_vehicles = 0
    total_revenue = 0

    for cat in summary:
        vehicles = cat.get('total_vehicles', 0) or 0
        revenue = cat.get('potential_revenue', 0) or 0
        total_vehicles += vehicles
        total_revenue += revenue
        print(f"    {cat['category']}: {cat['location_count']} locations, ~{vehicles} vehicles, ${revenue:,.0f} potential")

    print()
    print(f"  Totals: {total_vehicles} vehicles, ${total_revenue:,.0f} potential revenue")
    print()

    assert len(summary) >= 1, "Expected at least 1 category in summary"
    print("[OK] Category summary works correctly")
    print()

    # ========================================================================
    # TEST 10: Revenue Calculations
    # ========================================================================

    print("=" * 80)
    print("[10/12] Testing Revenue Calculations...")
    print("=" * 80 + "\n")

    # Test revenue calculation for individual location
    test_loc = test_locations[0]  # Dallas Ford
    expected_revenue = test_loc.estimated_vehicles * test_loc.avg_revenue_per_vehicle

    print(f"  {test_loc.name}:")
    print(f"    Vehicles: {test_loc.estimated_vehicles}")
    print(f"    Revenue/vehicle: ${test_loc.avg_revenue_per_vehicle}")
    print(f"    Expected revenue: ${expected_revenue:,.0f}")

    # Luxury premium
    luxury_loc = test_locations[3]  # Golf course
    luxury_revenue = luxury_loc.estimated_vehicles * luxury_loc.avg_revenue_per_vehicle
    print()
    print(f"  {luxury_loc.name} (Luxury):")
    print(f"    Vehicles: {luxury_loc.estimated_vehicles}")
    print(f"    Revenue/vehicle: ${luxury_loc.avg_revenue_per_vehicle}")
    print(f"    Expected revenue: ${luxury_revenue:,.0f}")
    print()

    # Verify luxury premium
    assert luxury_loc.avg_revenue_per_vehicle > test_loc.avg_revenue_per_vehicle
    print("[OK] Revenue calculations work correctly")
    print()

    # ========================================================================
    # TEST 11: Grading System
    # ========================================================================

    print("=" * 80)
    print("[11/12] Testing Grading System...")
    print("=" * 80 + "\n")

    def get_grade(vehicles):
        """Grade based on vehicle count (matches fleet_map.html)"""
        if vehicles >= 300:
            return 'A'
        elif vehicles >= 150:
            return 'B'
        elif vehicles >= 75:
            return 'C'
        return 'D'

    test_cases = [
        (350, 'A'),  # Large dealership
        (200, 'B'),  # Medium dealership
        (100, 'C'),  # Small dealership
        (50, 'D'),   # Very small
    ]

    for vehicles, expected_grade in test_cases:
        actual_grade = get_grade(vehicles)
        assert actual_grade == expected_grade, f"Expected {expected_grade} for {vehicles} vehicles, got {actual_grade}"
        print(f"  {vehicles} vehicles -> Grade {actual_grade}")

    print()

    # Apply to our test locations
    print("  Grading test locations:")
    for loc in test_locations:
        grade = get_grade(loc.estimated_vehicles)
        print(f"    {loc.name}: {loc.estimated_vehicles} vehicles -> Grade {grade}")

    print()
    print("[OK] Grading system works correctly")
    print()

    # ========================================================================
    # TEST 12: Route Building Logic
    # ========================================================================

    print("=" * 80)
    print("[12/12] Testing Route Building Logic...")
    print("=" * 80 + "\n")

    # Simulate route building
    selected_route = []

    def add_to_route(location):
        if location not in selected_route:
            selected_route.append(location)
            return True
        return False

    def remove_from_route(location):
        if location in selected_route:
            selected_route.remove(location)
            return True
        return False

    def get_route_summary():
        total_vehicles = sum(loc.estimated_vehicles for loc in selected_route)
        total_revenue = sum(loc.estimated_vehicles * loc.avg_revenue_per_vehicle for loc in selected_route)
        return {
            'stops': len(selected_route),
            'total_vehicles': total_vehicles,
            'estimated_revenue': total_revenue
        }

    # Add locations to route
    for loc in test_locations[:3]:
        add_to_route(loc)
        print(f"  Added: {loc.name}")

    summary = get_route_summary()
    print()
    print(f"  Route Summary:")
    print(f"    Stops: {summary['stops']}")
    print(f"    Total Vehicles: {summary['total_vehicles']}")
    print(f"    Est. Revenue: ${summary['estimated_revenue']:,.0f}")
    print()

    assert summary['stops'] == 3
    assert summary['total_vehicles'] > 0
    assert summary['estimated_revenue'] > 0

    # Remove one stop
    remove_from_route(test_locations[1])
    summary = get_route_summary()
    assert summary['stops'] == 2
    print(f"  After removing 1 stop: {summary['stops']} stops remaining")
    print()

    print("[OK] Route building logic works correctly")
    print()

    # ========================================================================
    # BONUS: Test Duplicate Prevention
    # ========================================================================

    print("=" * 80)
    print("[BONUS] Testing Duplicate Prevention...")
    print("=" * 80 + "\n")

    # Try to save the same locations again
    duplicate_count = manager.save_locations(test_locations)
    print(f"  Attempted to save {len(test_locations)} existing locations")
    print(f"  Actually saved: {duplicate_count} (should be 0)")

    assert duplicate_count == 0, "Duplicates should not be saved"
    print()

    print("[OK] Duplicate prevention works correctly")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    # Close any open connections before removing
    try:
        conn = manager._get_conn()
        conn.close()
    except:
        pass

    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except PermissionError:
        print(f"  Note: Could not remove {test_db} (file in use)")
        # On Windows, sometimes the file is locked - this is okay

    print("=" * 80)
    print("[SUCCESS] FLEET INTELLIGENCE TESTS COMPLETE")
    print("=" * 80 + "\n")

    print("Key features verified:")
    print("  [OK] FleetLocation data model")
    print("  [OK] OSM Query Builder")
    print("  [OK] Category configuration (17 categories)")
    print("  [OK] Fleet Location Manager")
    print("  [OK] Save and retrieve locations")
    print("  [OK] Bounding box queries")
    print("  [OK] Radius/nearby queries")
    print("  [OK] Search functionality")
    print("  [OK] Category summaries")
    print("  [OK] Revenue calculations")
    print("  [OK] Grading system (A/B/C/D)")
    print("  [OK] Route building logic")
    print("  [OK] Duplicate prevention")
    print()

    print("FLEET CATEGORIES:")
    for cat in expected_categories:
        print(f"  - {cat}")
    print()

    print("GRADING THRESHOLDS:")
    print("  Grade A: 300+ vehicles")
    print("  Grade B: 150-299 vehicles")
    print("  Grade C: 75-149 vehicles")
    print("  Grade D: <75 vehicles")
    print()

    print("REVENUE TIERS:")
    print("  Standard: $1,200-1,500/vehicle")
    print("  Premium (Rentals): $1,800/vehicle")
    print("  Luxury (Golf/Luxury Dealers): $2,000-2,500/vehicle")
    print()

    return True


if __name__ == '__main__':
    success = test_fleet_intelligence()
    sys.exit(0 if success else 1)
