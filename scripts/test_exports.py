"""
Test script for Phase 12 Part 1 exports

Tests:
1. Excel Export (7-sheet workbook)
2. Mailing Labels (Avery 5160)
3. Cold Calling List (PDF with tracking)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.business.exports import FleetExcelExporter, MailingLabelsExporter, CallingListExporter


def generate_test_data():
    """Generate realistic test data from the database"""

    # Sample hail event
    hail_event = {
        'location': 'Dallas-Fort Worth, TX',
        'date': '2024-11-15',
        'hail_size_inches': 1.75,
        'affected_area_sqmi': 125.5
    }

    # Generate test locations
    test_locations = [
        {
            'name': 'AutoNation Chevrolet North',
            'category': 'car_dealership',
            'priority_score': 92,
            'estimated_vehicles': 245,
            'hail_size_inches': 1.75,
            'estimated_revenue': 91875,
            'manager_name': 'Robert Martinez',
            'phone': '(214) 555-1234',
            'email': 'rmartinez@autonation.com',
            'address': '12500 N Central Expressway',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75243',
            'best_approach_time': 'Weekday mornings 9-11am',
            'accessibility': 'public',
            'notes': 'Large lot, easy access. Previous PDR customer.',
            'lat': 32.9167,
            'lon': -96.7700
        },
        {
            'name': 'Enterprise Rent-A-Car DFW Airport',
            'category': 'rental_car',
            'priority_score': 89,
            'estimated_vehicles': 380,
            'hail_size_inches': 1.75,
            'estimated_revenue': 142500,
            'manager_name': 'Sarah Williams',
            'phone': '(972) 555-5678',
            'email': 'swilliams@enterprise.com',
            'address': '2424 E 38th St',
            'city': 'Irving',
            'state': 'TX',
            'zip_code': '75261',
            'best_approach_time': 'Any time - 24/7 operation',
            'accessibility': 'gated_accessible',
            'notes': 'Fleet must be repaired ASAP for rental availability.',
            'lat': 32.8468,
            'lon': -96.8513
        },
        {
            'name': 'Park Place Lexus Plano',
            'category': 'car_dealership',
            'priority_score': 87,
            'estimated_vehicles': 175,
            'hail_size_inches': 1.5,
            'estimated_revenue': 87500,
            'manager_name': 'Michael Chang',
            'phone': '(972) 555-9012',
            'email': 'mchang@parkplace.com',
            'address': '6100 W Plano Pkwy',
            'city': 'Plano',
            'state': 'TX',
            'zip_code': '75093',
            'best_approach_time': 'Tuesday-Thursday afternoons',
            'accessibility': 'public',
            'notes': 'Luxury vehicles - premium pricing opportunity.',
            'luxury_vehicles': True,
            'lat': 33.0198,
            'lon': -96.7997
        },
        {
            'name': 'City of Dallas Municipal Fleet',
            'category': 'municipal',
            'priority_score': 85,
            'estimated_vehicles': 520,
            'hail_size_inches': 1.75,
            'estimated_revenue': 156000,
            'manager_name': 'James Thompson',
            'phone': '(214) 555-3456',
            'email': 'jthompson@dallas.gov',
            'address': '320 E Jefferson Blvd',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75203',
            'best_approach_time': 'Mon-Fri 8am-4pm',
            'accessibility': 'gated_restricted',
            'notes': 'Municipal contract required. Long approval process.',
            'lat': 32.7447,
            'lon': -96.7970
        },
        {
            'name': 'Hertz Car Rental Love Field',
            'category': 'rental_car',
            'priority_score': 84,
            'estimated_vehicles': 290,
            'hail_size_inches': 1.75,
            'estimated_revenue': 108750,
            'manager_name': 'Jennifer Lopez',
            'phone': '(214) 555-7890',
            'email': 'jlopez@hertz.com',
            'address': '5845 Denton Dr',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75235',
            'best_approach_time': 'Weekday mornings',
            'accessibility': 'gated_accessible',
            'notes': 'Regional fleet manager. Can authorize multi-location work.',
            'lat': 32.8438,
            'lon': -96.8578
        },
        {
            'name': 'Sewell Automotive BMW',
            'category': 'car_dealership',
            'priority_score': 82,
            'estimated_vehicles': 135,
            'hail_size_inches': 1.5,
            'estimated_revenue': 67500,
            'manager_name': 'David Kim',
            'phone': '(214) 555-2345',
            'email': 'dkim@sewell.com',
            'address': '5001 Lemmon Ave',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75209',
            'best_approach_time': 'Afternoons 2-5pm',
            'accessibility': 'public',
            'notes': 'High-end dealership. Quality over speed.',
            'luxury_vehicles': True,
            'lat': 32.8173,
            'lon': -96.8217
        },
        {
            'name': 'FedEx Ground Distribution Center',
            'category': 'delivery',
            'priority_score': 79,
            'estimated_vehicles': 185,
            'hail_size_inches': 1.75,
            'estimated_revenue': 55500,
            'manager_name': 'Patricia Brown',
            'phone': '(972) 555-4567',
            'email': 'pbrown@fedex.com',
            'address': '951 W Bethel Rd',
            'city': 'Coppell',
            'state': 'TX',
            'zip_code': '75019',
            'best_approach_time': 'Overnight shifts (10pm-6am)',
            'accessibility': 'gated_restricted',
            'notes': 'Must work overnight when trucks are parked.',
            'lat': 32.9615,
            'lon': -96.9905
        },
        {
            'name': 'The Oaks at Preston Apartments',
            'category': 'apartment',
            'priority_score': 75,
            'estimated_vehicles': 420,
            'hail_size_inches': 1.75,
            'estimated_revenue': 126000,
            'manager_name': 'Lisa Anderson',
            'phone': '(972) 555-6789',
            'email': 'landerson@greystar.com',
            'address': '5750 Preston Oaks Rd',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75254',
            'best_approach_time': 'Weekdays during business hours',
            'accessibility': 'public',
            'notes': 'Resident outreach opportunity. Can set up in parking lot.',
            'lat': 32.9332,
            'lon': -96.7984
        },
        {
            'name': 'Dallas Country Club',
            'category': 'golf_course',
            'priority_score': 73,
            'estimated_vehicles': 85,
            'hail_size_inches': 1.5,
            'estimated_revenue': 42500,
            'manager_name': 'William Davis',
            'phone': '(214) 555-8901',
            'email': 'wdavis@dallascc.com',
            'address': '4100 Beverly Dr',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75205',
            'best_approach_time': 'Tuesday mornings (slow day)',
            'accessibility': 'gated_restricted',
            'notes': 'Members only. Premium vehicles. Need referral.',
            'luxury_vehicles': True,
            'lat': 32.8350,
            'lon': -96.7800
        },
        {
            'name': 'Caliber Collision North Dallas',
            'category': 'body_shop',
            'priority_score': 71,
            'estimated_vehicles': 45,
            'hail_size_inches': 1.75,
            'estimated_revenue': 16875,
            'manager_name': 'Tony Gonzalez',
            'phone': '(214) 555-0123',
            'email': 'tgonzalez@caliber.com',
            'address': '13740 N Central Expy',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75243',
            'best_approach_time': 'Anytime',
            'accessibility': 'public',
            'notes': 'Potential subcontractor relationship. High volume.',
            'lat': 32.9267,
            'lon': -96.7700
        },
        {
            'name': 'Plano ISD Transportation',
            'category': 'school',
            'priority_score': 68,
            'estimated_vehicles': 310,
            'hail_size_inches': 1.75,
            'estimated_revenue': 93000,
            'manager_name': 'Sandra White',
            'phone': '(469) 555-2345',
            'email': 'swhite@pisd.edu',
            'address': '2700 W 15th St',
            'city': 'Plano',
            'state': 'TX',
            'zip_code': '75075',
            'best_approach_time': 'Summer break ideal',
            'accessibility': 'gated_restricted',
            'notes': 'School district contract. Best timing is summer.',
            'lat': 33.0150,
            'lon': -96.7320
        },
        {
            'name': 'Medical City Dallas Parking',
            'category': 'hospital',
            'priority_score': 65,
            'estimated_vehicles': 850,
            'hail_size_inches': 1.5,
            'estimated_revenue': 255000,
            'manager_name': 'Karen Miller',
            'phone': '(972) 555-3456',
            'email': 'kmiller@medicalcity.com',
            'address': '7777 Forest Ln',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75230',
            'best_approach_time': 'Coordinate with facilities',
            'accessibility': 'public',
            'notes': 'Employee vehicles in garage. Need hospital approval.',
            'lat': 32.9182,
            'lon': -96.7686
        },
        {
            'name': 'Marriott Dallas Downtown',
            'category': 'hotel',
            'priority_score': 62,
            'estimated_vehicles': 125,
            'hail_size_inches': 1.75,
            'estimated_revenue': 37500,
            'manager_name': 'Richard Lee',
            'phone': '(214) 555-4567',
            'email': 'rlee@marriott.com',
            'address': '650 N Pearl St',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75201',
            'best_approach_time': 'Midweek',
            'accessibility': 'public',
            'notes': 'Guest vehicles. Can set up in valet area.',
            'lat': 32.7873,
            'lon': -96.8003
        },
        {
            'name': 'State Farm Regional Office',
            'category': 'insurance',
            'priority_score': 58,
            'estimated_vehicles': 220,
            'hail_size_inches': 1.5,
            'estimated_revenue': 66000,
            'manager_name': 'Nancy Wilson',
            'phone': '(972) 555-5678',
            'email': '',  # No email
            'address': '8333 Douglas Ave',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75225',
            'best_approach_time': 'Lunch hours',
            'accessibility': 'gated_accessible',
            'notes': 'Corporate office. Need HR approval for employee outreach.',
            'lat': 32.8653,
            'lon': -96.8011
        },
        {
            'name': 'Oncor Electric Delivery',
            'category': 'utility',
            'priority_score': 55,
            'estimated_vehicles': 195,
            'hail_size_inches': 1.75,
            'estimated_revenue': 58500,
            'manager_name': '',  # No contact name
            'phone': '(214) 555-6789',
            'email': 'fleet@oncor.com',
            'address': '1601 Bryan St',
            'city': 'Dallas',
            'state': 'TX',
            'zip_code': '75201',
            'best_approach_time': 'After hours',
            'accessibility': 'gated_restricted',
            'notes': 'Utility fleet. Specialized vehicles. Need specific approach.',
            'lat': 32.7857,
            'lon': -96.7969
        }
    ]

    return hail_event, test_locations


def test_excel_export(locations, hail_event):
    """Test Excel export"""
    print("\n" + "="*60)
    print("TEST 1: EXCEL EXPORT")
    print("="*60)

    exporter = FleetExcelExporter(output_dir=str(PROJECT_ROOT / 'exports'))
    filename = exporter.export_to_excel(locations, hail_event)

    # Verify file exists
    if Path(filename).exists():
        file_size = Path(filename).stat().st_size
        print(f"\n[PASS] Excel file created: {filename}")
        print(f"       File size: {file_size:,} bytes")
        return filename
    else:
        print(f"\n[FAIL] Excel file not created!")
        return None


def test_mailing_labels(locations):
    """Test mailing labels export"""
    print("\n" + "="*60)
    print("TEST 2: MAILING LABELS")
    print("="*60)

    exporter = MailingLabelsExporter(output_dir=str(PROJECT_ROOT / 'exports'))
    filename = exporter.export_mailing_labels(locations)

    if Path(filename).exists():
        file_size = Path(filename).stat().st_size
        print(f"\n[PASS] Mailing labels created: {filename}")
        print(f"       File size: {file_size:,} bytes")
        return filename
    else:
        print(f"\n[FAIL] Mailing labels not created!")
        return None


def test_calling_list(locations):
    """Test calling list export"""
    print("\n" + "="*60)
    print("TEST 3: CALLING LIST")
    print("="*60)

    exporter = CallingListExporter(output_dir=str(PROJECT_ROOT / 'exports'))
    filename = exporter.export_calling_list(locations)

    if Path(filename).exists():
        file_size = Path(filename).stat().st_size
        print(f"\n[PASS] Calling list created: {filename}")
        print(f"       File size: {file_size:,} bytes")
        return filename
    else:
        print(f"\n[FAIL] Calling list not created!")
        return None


def test_quick_dial_list(locations):
    """Test quick dial list export"""
    print("\n" + "="*60)
    print("TEST 4: QUICK DIAL LIST (BONUS)")
    print("="*60)

    exporter = CallingListExporter(output_dir=str(PROJECT_ROOT / 'exports'))
    filename = exporter.export_quick_dial_list(locations)

    if Path(filename).exists():
        file_size = Path(filename).stat().st_size
        print(f"\n[PASS] Quick dial list created: {filename}")
        print(f"       File size: {file_size:,} bytes")
        return filename
    else:
        print(f"\n[FAIL] Quick dial list not created!")
        return None


def main():
    """Run all export tests"""

    print("\n" + "="*70)
    print("         PHASE 12 PART 1 - EXPORT SYSTEM TESTS")
    print("="*70)
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"Export Directory: {PROJECT_ROOT / 'exports'}")

    # Generate test data
    print("\nGenerating test data...")
    hail_event, locations = generate_test_data()
    print(f"  Test locations: {len(locations)}")
    print(f"  Event: {hail_event['location']}")

    # Calculate totals
    total_vehicles = sum(loc.get('estimated_vehicles', 0) for loc in locations)
    total_revenue = sum(loc.get('estimated_revenue', 0) for loc in locations)
    with_phone = sum(1 for loc in locations if loc.get('phone'))
    with_email = sum(1 for loc in locations if loc.get('email'))

    print(f"  Total vehicles: {total_vehicles:,}")
    print(f"  Total revenue: ${total_revenue:,.0f}")
    print(f"  With phone: {with_phone}")
    print(f"  With email: {with_email}")

    # Run tests
    results = []

    try:
        excel_file = test_excel_export(locations, hail_event)
        results.append(('Excel Export', excel_file))
    except Exception as e:
        print(f"\n[ERROR] Excel export failed: {e}")
        results.append(('Excel Export', None))

    try:
        labels_file = test_mailing_labels(locations)
        results.append(('Mailing Labels', labels_file))
    except Exception as e:
        print(f"\n[ERROR] Mailing labels failed: {e}")
        results.append(('Mailing Labels', None))

    try:
        calling_file = test_calling_list(locations)
        results.append(('Calling List', calling_file))
    except Exception as e:
        print(f"\n[ERROR] Calling list failed: {e}")
        results.append(('Calling List', None))

    try:
        quick_dial_file = test_quick_dial_list(locations)
        results.append(('Quick Dial List', quick_dial_file))
    except Exception as e:
        print(f"\n[ERROR] Quick dial list failed: {e}")
        results.append(('Quick Dial List', None))

    # Summary
    print("\n" + "="*70)
    print("                    TEST SUMMARY")
    print("="*70)

    passed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        if result:
            passed += 1
        print(f"  [{status}] {name}")

    print(f"\n  Results: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n  ALL TESTS PASSED!")
        print("\n  Generated files in exports/ directory:")
        for name, filepath in results:
            if filepath:
                print(f"    - {Path(filepath).name}")
    else:
        print("\n  Some tests failed. Check errors above.")

    print("\n" + "="*70 + "\n")

    return passed == len(results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
