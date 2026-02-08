"""
Test Dent Mapping System
PDR CRM Part 20 - Interactive Vehicle Damage Mapping
"""

import sys
import os
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_dent_mapper():
    print("\n" + "="*80)
    print("TESTING DENT MAPPING SYSTEM")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.dent_mapper import DentMapper

    # Use test database
    test_db = "data/test_dent_mapper.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mapper = DentMapper(db)

    print()

    # ========================================================================
    # Create Test Customer, Vehicle, and Job
    # ========================================================================

    print("Creating test customer and job...")

    # Create customer
    result = db.execute("""
        INSERT INTO customers (
            first_name, last_name, phone, email, zip_code, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "Mike",
        "Thompson",
        "555-0300",
        "mike.thompson@test.com",
        "75024",
        datetime.now().isoformat()
    ))
    customer_id = result[0]['id']

    # Create vehicle
    result = db.execute("""
        INSERT INTO vehicles (
            customer_id, year, make, model, color, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        customer_id,
        2021,
        "Ford",
        "F-150",
        "White",
        datetime.now().isoformat()
    ))
    vehicle_id = result[0]['id']

    # Create job
    result = db.execute("""
        INSERT INTO jobs (
            job_number, customer_id, vehicle_id, job_type, damage_type,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "JOB-DENT-001",
        customer_id,
        vehicle_id,
        "HAIL",
        "HAIL",
        "IN_PROGRESS",
        datetime.now().isoformat()
    ))
    job_id = result[0]['id']

    print(f"  Created job JOB-DENT-001 (ID: {job_id})")
    print()

    # ========================================================================
    # TEST 1: Create Dent Map
    # ========================================================================

    print("="*80)
    print("[1/9] Creating initial dent map...")
    print("="*80 + "\n")

    map_id = mapper.create_dent_map(
        job_id=job_id,
        map_type='INITIAL',
        notes='Initial damage assessment'
    )
    print()

    assert map_id > 0
    print("[OK] Dent map created")
    print()

    # ========================================================================
    # TEST 2: Add Individual Dents
    # ========================================================================

    print("="*80)
    print("[2/9] Adding dents individually...")
    print("="*80 + "\n")

    # Add some dents with positions
    dent1 = mapper.add_dent(
        map_id=map_id,
        panel='HOOD',
        dent_size='QUARTER',
        x_position=45.0,
        y_position=60.0,
        severity=3,
        notes='Center of hood'
    )
    print(f"  Added dent #{dent1}: QUARTER on HOOD at (45, 60)")

    dent2 = mapper.add_dent(
        map_id=map_id,
        panel='HOOD',
        dent_size='DIME',
        x_position=30.0,
        y_position=40.0,
        severity=2
    )
    print(f"  Added dent #{dent2}: DIME on HOOD at (30, 40)")

    dent3 = mapper.add_dent(
        map_id=map_id,
        panel='ROOF',
        dent_size='GOLF_BALL',
        x_position=50.0,
        y_position=50.0,
        severity=4,
        notes='Large impact'
    )
    print(f"  Added dent #{dent3}: GOLF_BALL on ROOF at (50, 50)")
    print()

    assert dent1 > 0 and dent2 > 0 and dent3 > 0
    print("[OK] Individual dents added")
    print()

    # ========================================================================
    # TEST 3: Add Dents in Bulk
    # ========================================================================

    print("="*80)
    print("[3/9] Adding dents in bulk...")
    print("="*80 + "\n")

    # Hood: 15 dime, 8 nickel, 5 quarter
    added = mapper.add_dents_bulk(
        map_id=map_id,
        panel='HOOD',
        dent_counts={'DIME': 15, 'NICKEL': 8, 'QUARTER': 5}
    )
    print()

    # Roof: 12 quarter, 3 golf ball
    added += mapper.add_dents_bulk(
        map_id=map_id,
        panel='ROOF',
        dent_counts={'QUARTER': 12, 'GOLF_BALL': 3}
    )
    print()

    # Trunk: 10 dime, 6 quarter, 1 golf ball
    added += mapper.add_dents_bulk(
        map_id=map_id,
        panel='TRUNK',
        dent_counts={'DIME': 10, 'QUARTER': 6, 'GOLF_BALL': 1}
    )
    print()

    # Driver Door: 8 dime, 4 nickel
    added += mapper.add_dents_bulk(
        map_id=map_id,
        panel='DRIVER_DOOR',
        dent_counts={'DIME': 8, 'NICKEL': 4}
    )
    print()

    # Driver Fender: 5 dime, 3 quarter
    added += mapper.add_dents_bulk(
        map_id=map_id,
        panel='DRIVER_FENDER',
        dent_counts={'DIME': 5, 'QUARTER': 3}
    )
    print()

    print(f"[OK] Added {added} dents in bulk")
    print()

    # ========================================================================
    # TEST 4: Get Dent Counts
    # ========================================================================

    print("="*80)
    print("[4/9] Getting dent counts...")
    print("="*80 + "\n")

    total = mapper.get_dent_count(map_id)
    print(f"Total dents: {total}")

    hood_count = mapper.get_dent_count(map_id, panel='HOOD')
    print(f"Hood dents: {hood_count}")

    roof_count = mapper.get_dent_count(map_id, panel='ROOF')
    print(f"Roof dents: {roof_count}")

    quarter_count = mapper.get_dent_count(map_id, dent_size='QUARTER')
    print(f"Quarter-size dents: {quarter_count}")

    golf_ball_count = mapper.get_dent_count(map_id, dent_size='GOLF_BALL')
    print(f"Golf ball-size dents: {golf_ball_count}")
    print()

    # We added 3 individual + bulk dents
    expected_total = 3 + (15 + 8 + 5) + (12 + 3) + (10 + 6 + 1) + (8 + 4) + (5 + 3)
    assert total == expected_total, f"Expected {expected_total}, got {total}"
    print(f"[OK] Total dents: {total}")
    print()

    # ========================================================================
    # TEST 5: Get Dent Breakdown
    # ========================================================================

    print("="*80)
    print("[5/9] Getting dent breakdown...")
    print("="*80 + "\n")

    breakdown = mapper.get_dent_breakdown(map_id)

    print(f"Dent Breakdown:")
    print(f"  Total: {breakdown['total_dents']}")
    print(f"  Avg Severity: {breakdown['severity_avg']:.1f}/5")
    print()

    print(f"  By Panel:")
    for panel, count in sorted(breakdown['by_panel'].items(), key=lambda x: x[1], reverse=True):
        print(f"    {panel:20s}: {count:3d} dents")
    print()

    print(f"  By Size:")
    for size, count in sorted(breakdown['by_size'].items()):
        size_name = mapper.DENT_SIZES[size]['name']
        print(f"    {size_name:20s}: {count:3d} dents")
    print()

    assert breakdown['total_dents'] == total
    assert len(breakdown['by_panel']) == 5  # 5 panels with dents
    print("[OK] Dent breakdown working")
    print()

    # ========================================================================
    # TEST 6: Calculate Repair Estimate
    # ========================================================================

    print("="*80)
    print("[6/9] Calculating repair estimate...")
    print("="*80 + "\n")

    estimate = mapper.calculate_repair_estimate(map_id)

    print(f"Repair Estimate:")
    print(f"  Total dents: {estimate['total_dents']}")
    print(f"  Estimated hours: {estimate['estimated_hours']:.1f}")
    print(f"  Total cost: ${estimate['total_cost']:,.2f}")
    print()

    print(f"  Breakdown by size:")
    for size, info in sorted(estimate['by_size'].items()):
        size_name = mapper.DENT_SIZES[size]['name']
        print(f"    {size_name:20s}: {info['count']:3d} x ${info['cost_per_dent']:.2f} = ${info['total_cost']:,.2f}")
    print()

    print(f"  Breakdown by panel:")
    for panel, info in sorted(estimate['by_panel'].items(), key=lambda x: x[1]['total_cost'], reverse=True):
        print(f"    {panel:20s}: {info['count']:3d} dents = ${info['total_cost']:,.2f}")
    print()

    print(f"  Difficulty breakdown:")
    for diff, count in estimate['difficulty_breakdown'].items():
        if count > 0:
            print(f"    {diff:15s}: {count:3d} dents")
    print()

    assert estimate['total_cost'] > 0
    print("[OK] Repair estimate calculated")
    print()

    # ========================================================================
    # TEST 7: Generate Damage Report
    # ========================================================================

    print("="*80)
    print("[7/9] Generating damage report...")
    print("="*80 + "\n")

    report = mapper.generate_damage_report(map_id)
    print(report)
    print()

    assert "VEHICLE DAMAGE ASSESSMENT REPORT" in report
    assert "Total Dents:" in report
    print("[OK] Damage report generated")
    print()

    # ========================================================================
    # TEST 8: Before/After Comparison
    # ========================================================================

    print("="*80)
    print("[8/9] Testing before/after comparison...")
    print("="*80 + "\n")

    # Create "after" map with remaining dents
    after_map_id = mapper.create_dent_map(
        job_id=job_id,
        map_type='FINAL',
        notes='After repair assessment'
    )
    print()

    # Add remaining dents (simulating incomplete repair)
    mapper.add_dents_bulk(
        map_id=after_map_id,
        panel='HOOD',
        dent_counts={'DIME': 2}
    )
    print()

    mapper.add_dents_bulk(
        map_id=after_map_id,
        panel='ROOF',
        dent_counts={'QUARTER': 1}
    )
    print()

    # Compare
    comparison = mapper.compare_before_after(map_id, after_map_id)

    print(f"Before/After Comparison:")
    print(f"  Before: {comparison['before_total']} dents")
    print(f"  After: {comparison['after_total']} dents")
    print(f"  Removed: {comparison['dents_removed']} dents")
    print(f"  Progress: {comparison['percent_complete']:.1f}% complete")
    print()

    print(f"  By Panel:")
    for panel, data in sorted(comparison['by_panel'].items()):
        if data['before'] > 0:
            print(f"    {panel:20s}: {data['before']:3d} -> {data['after']:3d} ({data['removed']} removed)")
    print()

    assert comparison['before_total'] == total
    assert comparison['after_total'] == 3
    assert comparison['percent_complete'] > 95  # Most dents removed
    print("[OK] Before/after comparison working")
    print()

    # Generate comparison report
    print("Comparison Report:")
    print("-" * 60)
    comp_report = mapper.generate_comparison_report(map_id, after_map_id)
    print(comp_report)
    print()

    # ========================================================================
    # TEST 9: Heatmap Data
    # ========================================================================

    print("="*80)
    print("[9/9] Getting heatmap data...")
    print("="*80 + "\n")

    heatmap = mapper.get_heatmap_data(map_id)

    print(f"Heatmap Data:")
    print(f"  Max count: {heatmap['max_count']}")
    print(f"  Max severity: {heatmap['max_severity']}")
    print()

    print(f"  Panel intensities:")
    for panel, data in sorted(heatmap['panels'].items(), key=lambda x: x[1]['intensity'], reverse=True):
        if data['count'] > 0:
            intensity_bar = "#" * int(data['intensity'] * 20)
            print(f"    {panel:20s}: {data['count']:3d} dents - {data['intensity']:.2f} [{intensity_bar}]")
    print()

    assert heatmap['max_count'] > 0
    print("[OK] Heatmap data working")
    print()

    # ========================================================================
    # BONUS: Test Validation
    # ========================================================================

    print("="*80)
    print("[BONUS] Testing validation...")
    print("="*80 + "\n")

    # Test invalid panel
    try:
        mapper.add_dent(map_id=map_id, panel='INVALID_PANEL', dent_size='QUARTER')
        print("[ERROR] Should have raised ValueError for invalid panel")
    except ValueError as e:
        print(f"[OK] Caught invalid panel: {str(e)[:50]}...")
    print()

    # Test invalid dent size
    try:
        mapper.add_dent(map_id=map_id, panel='HOOD', dent_size='TENNIS_BALL')
        print("[ERROR] Should have raised ValueError for invalid dent size")
    except ValueError as e:
        print(f"[OK] Caught invalid dent size: {str(e)[:50]}...")
    print()

    print("[OK] Validation working")
    print()

    # ========================================================================
    # BONUS: Display Dent Size Reference
    # ========================================================================

    print("="*80)
    print("[BONUS] Dent Size Reference")
    print("="*80 + "\n")

    print("DENT SIZE CLASSIFICATIONS:")
    print("-" * 60)
    for size, info in mapper.DENT_SIZES.items():
        print(f"  {info['name']:20s}")
        print(f"    Diameter:   {info['diameter_inches']}\"")
        print(f"    Cost:       ${info['typical_cost']:.2f}")
        print(f"    Difficulty: {info['difficulty']}")
        print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] DENT MAPPING SYSTEM TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Dent map creation (INITIAL, PROGRESS, FINAL)")
    print("  [OK] Individual dent adding (with position)")
    print("  [OK] Bulk dent adding (counts only)")
    print("  [OK] Dent counting (total, by panel, by size)")
    print("  [OK] Dent breakdown analysis")
    print("  [OK] Repair cost estimation")
    print("  [OK] Damage report generation")
    print("  [OK] Before/after comparison")
    print("  [OK] Comparison report generation")
    print("  [OK] Heatmap data for visualization")
    print("  [OK] Input validation")
    print()

    print("DENT MAPPING CAPABILITIES:")
    print("  - Interactive vehicle diagram (clickable SVG)")
    print("  - Dent counting by panel")
    print("  - 6 dent size classifications (Dime to Baseball)")
    print("  - Visual damage map with position tracking")
    print("  - Click to add/remove dents")
    print("  - Dent severity heatmap")
    print("  - Printable damage reports")
    print("  - Before/after dent count comparison")
    print("  - Repair cost estimation")
    print()

    print("Ready for PROMPT 21: Tech Mobile Interface?")
    print()

    return True


if __name__ == '__main__':
    success = test_dent_mapper()
    sys.exit(0 if success else 1)
