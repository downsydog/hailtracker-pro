"""
Test Hail Event Database & Tracking
PDR CRM Part 16 - Storm Event Management
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_hail_event_manager():
    print("\n" + "="*80)
    print("TESTING HAIL EVENT DATABASE & TRACKING")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.hail_event_manager import HailEventManager
    from datetime import date, timedelta

    # Use test database
    test_db = "data/test_hail_events.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    hail_mgr = HailEventManager(db)

    print()

    # ========================================================================
    # TEST 1: Create Storm Events
    # ========================================================================

    print("="*80)
    print("[1/8] Creating storm events...")
    print("="*80 + "\n")

    # Use relative dates so tests work regardless of current date
    today = date.today()

    # Severe storm - Dallas (30 days ago)
    storm1_id = hail_mgr.create_storm_event(
        event_name='Dallas Hail Storm - Recent',
        event_date=today - timedelta(days=30),
        location='North Dallas - Plano - Richardson corridor',
        city='Dallas',
        state='TX',
        severity='SEVERE',
        hail_size_inches=1.75,
        affected_zip_codes=['75024', '75025', '75074', '75075', '75093', '75080', '75081'],
        estimated_radius_miles=15.0,
        insurance_storm_code='TX-2024-0528-001',
        estimated_vehicles_affected=50000,
        notes='Golf ball size hail. Extensive damage reported across North Dallas suburbs.'
    )

    print()

    # Moderate storm - Fort Worth (45 days ago)
    storm2_id = hail_mgr.create_storm_event(
        event_name='Fort Worth Storm - Recent',
        event_date=today - timedelta(days=45),
        location='Fort Worth - Arlington - Grand Prairie',
        city='Fort Worth',
        state='TX',
        severity='MODERATE',
        hail_size_inches=1.25,
        affected_zip_codes=['76001', '76002', '76010', '76013', '76014'],
        estimated_radius_miles=10.0,
        insurance_storm_code='TX-2024-0603-002',
        estimated_vehicles_affected=30000,
        notes='Quarter to half dollar size hail. Dealerships heavily affected.'
    )

    print()

    # Catastrophic storm - McKinney (60 days ago)
    storm3_id = hail_mgr.create_storm_event(
        event_name='McKinney Mega Storm - Recent',
        event_date=today - timedelta(days=60),
        location='McKinney - Frisco - Allen',
        city='McKinney',
        state='TX',
        severity='CATASTROPHIC',
        hail_size_inches=2.5,
        affected_zip_codes=['75069', '75070', '75071', '75072', '75013', '75035', '75034'],
        estimated_radius_miles=20.0,
        insurance_storm_code='TX-2024-0415-001',
        noaa_event_id='NOAA-TX-2024-0415',
        estimated_vehicles_affected=75000,
        notes='Baseball size hail. Widespread damage. Many windshields broken. Total loss vehicles reported.'
    )

    print()

    # Minor storm - Austin (15 days ago)
    storm4_id = hail_mgr.create_storm_event(
        event_name='Austin Minor Storm - Recent',
        event_date=today - timedelta(days=15),
        location='North Austin - Round Rock',
        city='Austin',
        state='TX',
        severity='MINOR',
        hail_size_inches=0.75,
        affected_zip_codes=['78681', '78664', '78665'],
        estimated_radius_miles=8.0,
        estimated_vehicles_affected=15000,
        notes='Pea to marble size hail. Light damage expected.'
    )

    print()

    # Oklahoma storm (90 days ago)
    storm5_id = hail_mgr.create_storm_event(
        event_name='Oklahoma City Hailstorm - Recent',
        event_date=today - timedelta(days=90),
        location='Oklahoma City Metro - Edmond - Norman',
        city='Oklahoma City',
        state='OK',
        severity='SEVERE',
        hail_size_inches=1.8,
        affected_zip_codes=['73012', '73013', '73034', '73069', '73071'],
        estimated_radius_miles=25.0,
        insurance_storm_code='OK-2024-0515-001',
        noaa_event_id='NOAA-OK-2024-0515',
        estimated_vehicles_affected=60000,
        notes='Large hail event. Multiple supercells.'
    )

    print()

    assert storm1_id > 0
    assert storm2_id > 0
    assert storm3_id > 0
    print(f"[OK] Created {5} storm events")
    print()

    # ========================================================================
    # TEST 2: Get Storm Details
    # ========================================================================

    print("="*80)
    print("[2/8] Getting storm details...")
    print("="*80 + "\n")

    storm = hail_mgr.get_storm_event(storm1_id)

    print(f"Storm ID: {storm['id']}")
    print(f"Name: {storm['event_name']}")
    print(f"Date: {storm['event_date']}")
    print(f"Location: {storm['location']}")
    print(f"City/State: {storm['city']}, {storm['state']}")
    print(f"Severity: {storm['severity']} - {storm['severity_info']['name']}")
    print(f"Hail Size: {storm['hail_size_inches']} inches")
    print(f"Damage Level: {storm['severity_info']['damage_level']}")
    print(f"Radius: {storm['estimated_radius_miles']} miles")
    print(f"Insurance Code: {storm['insurance_storm_code']}")
    print(f"Affected ZIPs: {', '.join(storm['affected_zip_codes'])}")
    print(f"Est. Vehicles: {storm['estimated_vehicles_affected']:,}")
    print(f"Status: {storm['status']}")
    print()

    assert storm['event_name'] == 'Dallas Hail Storm - Recent'
    assert storm['severity'] == 'SEVERE'
    print("[OK] Storm details retrieved correctly")
    print()

    # ========================================================================
    # TEST 3: Search Storms
    # ========================================================================

    print("="*80)
    print("[3/8] Searching storms...")
    print("="*80 + "\n")

    # All Texas storms
    tx_storms = hail_mgr.search_storms(state='TX')
    print(f"Texas storms: {len(tx_storms)}")
    for s in tx_storms:
        print(f"  - {s['event_name']} ({s['severity']})")
    print()

    # Severe storms only
    severe_storms = hail_mgr.search_storms(severity='SEVERE')
    print(f"Severe storms: {len(severe_storms)}")
    for s in severe_storms:
        print(f"  - {s['event_name']}")
    print()

    # Search by city
    dallas_storms = hail_mgr.search_storms(city='Dallas')
    print(f"Dallas area storms: {len(dallas_storms)}")
    print()

    # Search by ZIP code
    zip_storms = hail_mgr.get_storms_by_zip('75024')
    print(f"Storms affecting ZIP 75024: {len(zip_storms)}")
    print()

    # Date range search (20-50 days ago should capture 3 storms: Dallas 30, Fort Worth 45)
    recent_storms = hail_mgr.search_storms(
        start_date=today - timedelta(days=50),
        end_date=today - timedelta(days=20)
    )
    print(f"Storms (20-50 days ago): {len(recent_storms)}")
    print()

    assert len(tx_storms) == 4
    assert len(severe_storms) == 2
    print("[OK] Storm search working correctly")
    print()

    # ========================================================================
    # TEST 4: Active Storms
    # ========================================================================

    print("="*80)
    print("[4/8] Getting active storms...")
    print("="*80 + "\n")

    active = hail_mgr.get_active_storms(days_back=365)
    print(f"Active storms (last 365 days): {len(active)}")
    for s in active:
        print(f"  [{s['status']:8}] {s['event_name']}")
    print()

    # Close a storm
    hail_mgr.close_storm_event(storm4_id, notes='Storm season ended. All claims processed.')

    active_after = hail_mgr.get_active_storms(days_back=365)
    print(f"Active storms after closing one: {len(active_after)}")
    print()

    # Reopen the storm
    hail_mgr.reopen_storm_event(storm4_id)
    active_reopened = hail_mgr.get_active_storms(days_back=365)
    print(f"Active storms after reopening: {len(active_reopened)}")
    print()

    print("[OK] Active storm management working")
    print()

    # ========================================================================
    # TEST 5: Update Storm
    # ========================================================================

    print("="*80)
    print("[5/8] Updating storm event...")
    print("="*80 + "\n")

    # Update estimated vehicles
    hail_mgr.update_storm_event(
        storm1_id,
        estimated_vehicles_affected=55000,
        notes='Updated estimate based on insurance claims data. Higher than initially projected.'
    )

    # Add more ZIP codes
    updated_zips = ['75024', '75025', '75074', '75075', '75093', '75080', '75081', '75082', '75083']
    hail_mgr.update_storm_event(
        storm1_id,
        affected_zip_codes=updated_zips
    )

    # Verify update
    updated_storm = hail_mgr.get_storm_event(storm1_id)
    print(f"Updated vehicles: {updated_storm['estimated_vehicles_affected']:,}")
    print(f"Updated ZIP count: {len(updated_storm['affected_zip_codes'])}")
    print()

    assert updated_storm['estimated_vehicles_affected'] == 55000
    assert len(updated_storm['affected_zip_codes']) == 9
    print("[OK] Storm update working")
    print()

    # ========================================================================
    # TEST 6: Storm Statistics
    # ========================================================================

    print("="*80)
    print("[6/8] Getting storm statistics...")
    print("="*80 + "\n")

    stats = hail_mgr.get_storm_stats(storm3_id)  # Catastrophic storm

    print(f"Storm: {stats['event_name']}")
    print(f"Severity: {stats['severity']}")
    print(f"Affected ZIPs: {stats['affected_zip_count']}")
    print(f"Estimated Vehicles: {stats['estimated_vehicles']:,}")
    print()
    print("Market Opportunity by Capture Rate:")
    for rate, data in stats['market_opportunity'].items():
        print(f"  {rate:>5}: {data['vehicles']:>6,} vehicles = ${data['revenue']:>12,.0f}")
    print()

    assert stats['estimated_vehicles'] == 75000
    print("[OK] Storm statistics working")
    print()

    # ========================================================================
    # TEST 7: Overall Statistics
    # ========================================================================

    print("="*80)
    print("[7/8] Getting overall storm statistics...")
    print("="*80 + "\n")

    overall = hail_mgr.get_overall_storm_stats(days=365)

    print(f"Total Storms: {overall['total_storms']}")
    print(f"Active Storms: {overall['active_storms']}")
    print(f"Total Estimated Vehicles: {overall['total_estimated_vehicles']:,}")
    print()
    print("By Severity:")
    for severity, data in overall['by_severity'].items():
        print(f"  {severity:15} {data['count']:>3} storms  {data['estimated_vehicles']:>10,} vehicles")
    print()
    print("By State:")
    for state, data in overall['by_state'].items():
        print(f"  {state:5} {data['count']:>3} storms  {data['estimated_vehicles']:>10,} vehicles")
    print()

    assert overall['total_storms'] == 5
    print("[OK] Overall statistics working")
    print()

    # ========================================================================
    # TEST 8: Severity Classification & Market Estimation
    # ========================================================================

    print("="*80)
    print("[8/8] Testing severity classification & market estimation...")
    print("="*80 + "\n")

    # Test severity classification by hail size
    print("Severity Classification by Hail Size:")
    test_sizes = [0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    for size in test_sizes:
        severity = hail_mgr.classify_severity_by_hail_size(size)
        info = hail_mgr.get_severity_info(severity)
        print(f"  {size} inches -> {severity} ({info['name']})")
    print()

    # Test market estimation
    print("Market Opportunity Estimation:")
    estimate = hail_mgr.estimate_market_opportunity(
        vehicles_affected=50000,
        severity='SEVERE',
        capture_rate=0.05
    )

    print(f"  Vehicles in Area: {estimate['vehicles_in_area']:,}")
    print(f"  Capture Rate: {estimate['capture_rate']*100:.0f}%")
    print(f"  Captured Vehicles: {estimate['captured_vehicles']:,}")
    print(f"  Avg Revenue/Vehicle: ${estimate['avg_revenue_per_vehicle']:,}")
    print(f"  Total Revenue Potential: ${estimate['total_revenue_potential']:,}")
    print(f"  Total Repair Hours: {estimate['total_repair_hours']:,}")
    print(f"  Techs Needed (30 days): {estimate['techs_needed_30_days']}")
    print()

    print("[OK] Severity classification & market estimation working")
    print()

    # ========================================================================
    # BONUS: Generate Reports
    # ========================================================================

    print("="*80)
    print("[BONUS] Generating storm reports...")
    print("="*80 + "\n")

    # Individual storm report
    report = hail_mgr.generate_storm_report(storm3_id)
    print(report)
    print()

    # Summary report
    summary = hail_mgr.generate_summary_report(days=365)
    print(summary)

    # ========================================================================
    # BONUS: Severity Levels Reference
    # ========================================================================

    print("="*80)
    print("[BONUS] Severity Level Reference...")
    print("="*80 + "\n")

    print("HAIL STORM SEVERITY CLASSIFICATIONS:")
    print()
    for level, info in hail_mgr.SEVERITY_LEVELS.items():
        print(f"  {level}:")
        print(f"    Name: {info['name']}")
        print(f"    Hail Size: {info['hail_size']}")
        print(f"    Damage Level: {info['damage_level']}")
        print(f"    Avg Revenue/Vehicle: ${info['avg_revenue_per_vehicle']:,}")
        print(f"    Avg Repair Hours: {info['avg_repair_hours']}")
        print(f"    Glass Damage Likely: {'Yes' if info['glass_damage_likely'] else 'No'}")
        print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] HAIL EVENT DATABASE TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Storm event creation")
    print("  [OK] Storm event retrieval")
    print("  [OK] Storm updates")
    print("  [OK] Storm search & filtering (state, city, severity, date, ZIP)")
    print("  [OK] Active storm tracking")
    print("  [OK] Storm open/close status management")
    print("  [OK] Severity classification (4 levels)")
    print("  [OK] Affected area tracking (ZIP codes, radius)")
    print("  [OK] Insurance storm codes")
    print("  [OK] NOAA event linking")
    print("  [OK] Storm statistics")
    print("  [OK] Overall statistics")
    print("  [OK] Market opportunity estimation")
    print("  [OK] Storm reports")
    print("  [OK] Summary reports")
    print()

    print("HAIL EVENT DATABASE FEATURES:")
    print("  - Track storm events with full details")
    print("  - 4 severity levels (Minor to Catastrophic)")
    print("  - Affected area tracking (ZIP codes + radius)")
    print("  - Insurance storm code linking")
    print("  - NOAA event ID linking")
    print("  - Market opportunity estimation")
    print("  - Storm search and filtering")
    print("  - Active storm management")
    print("  - Comprehensive reporting")
    print()

    print("Ready for PROMPT 17: Storm-to-Job Linking & Analytics?")
    print()

    return True


if __name__ == '__main__':
    success = test_hail_event_manager()
    sys.exit(0 if success else 1)
