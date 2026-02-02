#!/usr/bin/env python3
"""
Test script for Part 2 Marketing Automation Exports

Tests:
1. Direct Mail Letters (Word documents)
2. Email Campaign CSVs (MailChimp, Constant Contact, Generic)
3. SMS Campaign CSVs (Twilio, EZTexting, SimpleTexting, Generic)
4. Google Maps Routes (Shareable links)
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.business.exports import (
    DirectMailExporter,
    EmailCampaignExporter,
    SMSCampaignExporter,
    MapsRoutesExporter
)


def create_sample_locations():
    """Create sample fleet locations for testing"""

    return [
        {
            'id': 1,
            'name': 'Enterprise Rent-A-Car - Downtown Dallas',
            'address': '1234 Main Street',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75201',
            'lat': 32.7767,
            'lon': -96.7970,
            'phone': '(214) 555-1234',
            'email': 'manager@enterprise-dallas.com',
            'manager_name': 'John Smith',
            'manager_title': 'Fleet Manager',
            'category': 'car_rental',
            'estimated_vehicles': 250,
            'estimated_revenue': 62500,
            'priority_score': 92,
            'hail_size_inches': 1.75,
            'best_approach_time': 'Morning (8am-10am)',
            'notes': 'High-value client, insurance ready'
        },
        {
            'id': 2,
            'name': 'Hertz Car Rental - DFW Airport',
            'address': '2424 Airport Blvd',
            'city': 'Irving',
            'state': 'TX',
            'zip_code': '75062',
            'lat': 32.8998,
            'lon': -97.0403,
            'phone': '972-555-9876',
            'email': 'dfw.fleet@hertz.com',
            'manager_name': 'Sarah Johnson',
            'manager_title': 'Regional Fleet Director',
            'category': 'car_rental',
            'estimated_vehicles': 500,
            'estimated_revenue': 125000,
            'priority_score': 95,
            'hail_size_inches': 2.0,
            'best_approach_time': 'Afternoon (2pm-4pm)',
            'notes': 'Largest account in region'
        },
        {
            'id': 3,
            'name': 'AutoNation Ford - Fort Worth',
            'address': '5000 Highway 121',
            'city': 'Fort Worth',
            'state': 'TX',
            'zip_code': '76109',
            'lat': 32.7357,
            'lon': -97.3342,
            'phone': '817.555.4567',
            'email': 'service@autonationford.com',
            'manager_name': 'Mike Davis',
            'manager_title': 'Service Manager',
            'category': 'car_dealership',
            'estimated_vehicles': 180,
            'estimated_revenue': 45000,
            'priority_score': 78,
            'hail_size_inches': 1.5,
            'best_approach_time': 'Morning (9am-11am)',
            'notes': ''
        },
        {
            'id': 4,
            'name': 'ABC Logistics Inc',
            'address': '789 Industrial Way',
            'city': 'Garland',
            'state': 'TX',
            'zip_code': '75040',
            'lat': 32.9126,
            'lon': -96.6389,
            'phone': '2145557890',
            'email': 'ops@abclogistics.com',
            'manager_name': 'Robert Williams',
            'manager_title': 'Operations Manager',
            'category': 'logistics',
            'estimated_vehicles': 75,
            'estimated_revenue': 18750,
            'priority_score': 65,
            'hail_size_inches': 1.25,
            'best_approach_time': 'Any time',
            'notes': 'Fleet trucks only'
        },
        {
            'id': 5,
            'name': 'City of Plano - Municipal Fleet',
            'address': '1520 K Avenue',
            'city': 'Plano',
            'state': 'TX',
            'zip_code': '75074',
            'lat': 33.0198,
            'lon': -96.6989,
            'phone': '(972) 555-0001',
            'email': 'fleet@plano.gov',
            'manager_name': 'Jennifer Martinez',
            'manager_title': 'Fleet Superintendent',
            'category': 'municipal',
            'estimated_vehicles': 320,
            'estimated_revenue': 80000,
            'priority_score': 88,
            'hail_size_inches': 1.75,
            'best_approach_time': 'Business hours',
            'notes': 'Government procurement process required'
        },
        {
            'id': 6,
            'name': 'Marriott Hotel - Downtown Dallas',
            'address': '650 N Pearl St',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75201',
            'lat': 32.7876,
            'lon': -96.8002,
            'phone': '214-555-8888',
            'email': None,  # No email - should be filtered in email exports
            'manager_name': 'Thomas Brown',
            'manager_title': 'Facilities Manager',
            'category': 'hotel',
            'estimated_vehicles': 25,
            'estimated_revenue': 6250,
            'priority_score': 45,
            'hail_size_inches': 1.5,
            'best_approach_time': 'Morning',
            'notes': 'Shuttle vans only'
        },
        {
            'id': 7,
            'name': 'Test Company Without Phone',
            'address': '100 Test Road',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75201',
            'lat': 32.7767,
            'lon': -96.7970,
            'phone': None,  # No phone - should be filtered in SMS exports
            'email': 'test@example.com',
            'manager_name': 'Test Manager',
            'category': 'logistics',
            'estimated_vehicles': 10,
            'estimated_revenue': 2500,
            'priority_score': 30,
            'hail_size_inches': 1.0,
            'best_approach_time': 'Afternoon',
            'notes': ''
        }
    ]


def test_direct_mail():
    """Test Direct Mail Letter generation"""

    print("\n" + "="*70)
    print("TEST 1: DIRECT MAIL LETTERS")
    print("="*70)

    locations = create_sample_locations()
    exporter = DirectMailExporter(output_dir='exports/test_part2')

    company_info = {
        'name': 'Texas Hail Repair Pros',
        'phone': '(972) 555-HAIL',
        'email': 'service@texashailrepair.com',
        'website': 'www.texashailrepair.com',
        'address': '5555 Commerce St, Dallas, TX 75201'
    }

    hail_event = {
        'date': 'January 15, 2026',
        'location': 'Dallas-Fort Worth Metroplex',
        'hail_size_inches': 1.75
    }

    # Test full export
    result = exporter.export_direct_mail(locations, company_info, hail_event)

    assert os.path.exists(result), f"File not created: {result}"
    file_size = os.path.getsize(result)
    assert file_size > 1000, f"File too small: {file_size} bytes"

    # Test single letter export
    single_result = exporter.export_single_letter(
        locations[0],
        company_info,
        hail_event,
        filename='exports/test_part2/single_letter_test.docx'
    )
    assert os.path.exists(single_result), f"Single letter not created: {single_result}"

    print(f"\n[PASS] Direct Mail Test PASSED")
    print(f"  - Generated {len(locations)} personalized letters")
    print(f"  - File size: {file_size:,} bytes")
    print(f"  - Output: {result}")

    return True


def test_email_campaign():
    """Test Email Campaign CSV generation"""

    print("\n" + "="*70)
    print("TEST 2: EMAIL CAMPAIGN EXPORTS")
    print("="*70)

    locations = create_sample_locations()
    exporter = EmailCampaignExporter(output_dir='exports/test_part2')

    # Test individual platforms
    platforms = ['mailchimp', 'constant_contact', 'generic']
    results = {}

    for platform in platforms:
        result = exporter.export_email_campaign(locations, platform=platform)
        results[platform] = result

        assert os.path.exists(result), f"File not created: {result}"

        # Verify CSV content
        with open(result, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Should have header + locations with email (exclude those without email)
            locations_with_email = sum(1 for loc in locations if loc.get('email'))
            expected_rows = locations_with_email + 1  # +1 for header
            assert len(lines) == expected_rows, f"Expected {expected_rows} rows, got {len(lines)}"

    # Test export all formats
    all_results = exporter.export_all_formats(locations)
    assert len(all_results) == 3, "Should have 3 platform exports"

    # Test stats
    stats = exporter.get_email_stats(locations)
    print(f"\n  Email Stats:")
    print(f"    - Total: {stats['total_locations']}")
    print(f"    - With email: {stats['with_email']}")
    print(f"    - Email rate: {stats['email_rate']}%")

    print(f"\n[PASS] Email Campaign Test PASSED")
    print(f"  - Generated exports for: {', '.join(platforms)}")

    return True


def test_sms_campaign():
    """Test SMS Campaign CSV generation"""

    print("\n" + "="*70)
    print("TEST 3: SMS CAMPAIGN EXPORTS")
    print("="*70)

    locations = create_sample_locations()
    exporter = SMSCampaignExporter(output_dir='exports/test_part2')

    # Test individual platforms
    platforms = ['twilio', 'eztexting', 'simpletexting', 'generic']
    results = {}

    for platform in platforms:
        result = exporter.export_sms_campaign(locations, platform=platform)
        results[platform] = result

        assert os.path.exists(result), f"File not created: {result}"

    # Test custom message template
    custom_template = "Hi {manager}! {name} may need hail repair for {vehicles} vehicles. Reply YES for FREE inspection!"
    custom_result = exporter.export_sms_campaign(
        locations,
        platform='generic',
        message_template=custom_template,
        filename='exports/test_part2/sms_custom_template.csv'
    )
    assert os.path.exists(custom_result), "Custom template export failed"

    # Test stats
    stats = exporter.get_sms_stats(locations)
    print(f"\n  SMS Stats:")
    print(f"    - Total: {stats['total_locations']}")
    print(f"    - Valid phones: {stats['valid_phones']}")
    print(f"    - Invalid phones: {stats['invalid_phones']}")
    print(f"    - Valid rate: {stats['valid_rate']}%")

    # Test message preview
    previews = exporter.generate_message_preview(locations, count=3)
    print(f"\n  Message Previews:")
    for preview in previews:
        print(f"    - {preview['company'][:30]}: {preview['char_count']} chars")

    print(f"\n[PASS] SMS Campaign Test PASSED")
    print(f"  - Generated exports for: {', '.join(platforms)}")
    print(f"  - Custom template export working")

    return True


def test_maps_routes():
    """Test Google Maps Routes generation"""

    print("\n" + "="*70)
    print("TEST 4: GOOGLE MAPS ROUTES")
    print("="*70)

    locations = create_sample_locations()
    exporter = MapsRoutesExporter(output_dir='exports/test_part2')

    # Test single route URL generation
    single_url = exporter.generate_maps_url(locations[:5], optimize=True)
    assert single_url is not None, "URL generation failed"
    assert 'google.com/maps' in single_url, "Invalid Maps URL"
    print(f"\n  Sample URL (5 stops):")
    print(f"    {single_url[:100]}...")

    # Test route export
    result = exporter.export_routes(locations, routes_per_day=3, optimize=True)
    assert os.path.exists(result), f"File not created: {result}"

    # Verify CSV content
    with open(result, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Should have header + routes
        assert len(lines) > 1, "No routes generated"

        # Check header
        header = lines[0].strip()
        assert 'Route' in header, "Missing Route column"
        assert 'Google Maps Link' in header, "Missing Maps Link column"

    # Test route sheets
    sheets_result = exporter.export_route_sheets(locations, routes_per_day=3)
    assert os.path.exists(sheets_result), "Route sheets not created"

    # Test single route details
    route_details = exporter.export_single_route(locations[:5], route_name="Test Route")
    assert route_details['stops'] == 5, "Wrong stop count"
    assert route_details['maps_url'] is not None, "No URL generated"
    print(f"\n  Single Route Details:")
    print(f"    - Name: {route_details['name']}")
    print(f"    - Stops: {route_details['stops']}")
    print(f"    - Total Vehicles: {route_details['total_vehicles']}")
    print(f"    - Est. Distance: {route_details['estimated_distance_miles']} miles")

    # Test stats
    stats = exporter.get_route_stats(locations)
    print(f"\n  Route Stats:")
    print(f"    - Total: {stats['total_locations']}")
    print(f"    - With address: {stats['with_address']}")
    print(f"    - With coordinates: {stats['with_coordinates']}")
    print(f"    - Cities: {stats['cities']}")

    print(f"\n[PASS] Google Maps Routes Test PASSED")
    print(f"  - Route export working")
    print(f"  - Route optimization working")
    print(f"  - Output: {result}")

    return True


def main():
    """Run all Part 2 export tests"""

    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#" + "  HAILTRACKER PRO - PART 2 EXPORT SYSTEM TESTS".center(68) + "#")
    print("#" + " "*68 + "#")
    print("#"*70)

    # Create test output directory
    os.makedirs('exports/test_part2', exist_ok=True)

    tests = [
        ('Direct Mail Letters', test_direct_mail),
        ('Email Campaign CSVs', test_email_campaign),
        ('SMS Campaign CSVs', test_sms_campaign),
        ('Google Maps Routes', test_maps_routes),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n[FAIL] {name} FAILED: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, error in results:
        status = "[PASS] PASS" if success else f"[FAIL] FAIL: {error}"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")
    print("="*70)

    if passed == total:
        print("\n[SUCCESS] ALL PART 2 EXPORT TESTS PASSED!\n")
        return 0
    else:
        print(f"\n[WARNING]  {total - passed} test(s) failed\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
