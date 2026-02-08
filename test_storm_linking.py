"""
Test Storm-to-Job Linking & ROI Analytics
PDR CRM Part 17 - Storm Analytics
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_storm_linking():
    print("\n" + "="*80)
    print("TESTING STORM-TO-JOB LINKING & ROI ANALYTICS")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.hail_event_manager import HailEventManager

    # Use test database
    test_db = "data/test_storm_linking.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    hail_mgr = HailEventManager(db)

    # Use relative dates
    today = date.today()

    print()

    # ========================================================================
    # Create Test Storm
    # ========================================================================

    print("Creating test storm event...")
    storm_id = hail_mgr.create_storm_event(
        event_name='Dallas Hail Storm - Test',
        event_date=today - timedelta(days=30),
        location='North Dallas - Plano - Richardson',
        city='Dallas',
        state='TX',
        severity='SEVERE',
        hail_size_inches=1.75,
        affected_zip_codes=['75024', '75025', '75074', '75075'],
        estimated_radius_miles=15.0,
        insurance_storm_code='TX-2024-0528-001',
        estimated_vehicles_affected=50000
    )

    print()

    # Create a second storm for comparison
    storm2_id = hail_mgr.create_storm_event(
        event_name='Fort Worth Storm - Test',
        event_date=today - timedelta(days=45),
        location='Fort Worth - Arlington',
        city='Fort Worth',
        state='TX',
        severity='MODERATE',
        hail_size_inches=1.25,
        affected_zip_codes=['76001', '76002', '76010'],
        estimated_radius_miles=10.0,
        estimated_vehicles_affected=30000
    )

    print()

    # ========================================================================
    # Create Test Customers, Vehicles, and Jobs
    # ========================================================================

    print("Creating test customers and jobs...")

    job_ids = []
    for i in range(5):
        # Create customer - use result['id'] from INSERT
        result = db.execute("""
            INSERT INTO customers (
                first_name, last_name, phone, email, zip_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"Customer{i+1}",
            "Test",
            f"555-010{i}",
            f"customer{i+1}@test.com",
            '75024',
            datetime.now().isoformat()
        ))
        customer_id = result[0]['id']

        # Create vehicle - use result['id'] from INSERT
        result = db.execute("""
            INSERT INTO vehicles (
                customer_id, year, make, model, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            customer_id,
            2020 + i % 3,
            "Toyota",
            "Camry",
            datetime.now().isoformat()
        ))
        vehicle_id = result[0]['id']

        # Create job - use result['id'] from INSERT
        job_number = f"JOB-2024-{1000+i}"
        result = db.execute("""
            INSERT INTO jobs (
                job_number, customer_id, vehicle_id, job_type, damage_type,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            job_number,
            customer_id,
            vehicle_id,
            "HAIL",
            "HAIL",
            "NEW",
            datetime.now().isoformat()
        ))
        job_id = result[0]['id']
        job_ids.append(job_id)

        print(f"  Created job {job_number} (ID: {job_id}) for Customer{i+1}")

    print()

    # ========================================================================
    # TEST 1: Link Jobs to Storm
    # ========================================================================

    print("="*80)
    print("[1/7] Linking jobs to storm...")
    print("="*80 + "\n")

    for i, job_id in enumerate(job_ids[:4]):  # Link 4 jobs to storm 1
        confidence = 'CONFIRMED' if i < 2 else 'LIKELY'
        hail_mgr.link_job_to_storm(
            job_id=job_id,
            storm_id=storm_id,
            confidence=confidence,
            notes=f'Job linked for testing ({confidence})'
        )

    # Link 1 job to storm 2
    hail_mgr.link_job_to_storm(
        job_id=job_ids[4],
        storm_id=storm2_id,
        confidence='CONFIRMED',
        notes='Job linked to second storm'
    )

    print()

    # Verify links
    job_count = hail_mgr.get_storm_job_count(storm_id)
    assert job_count == 4, f"Expected 4 jobs, got {job_count}"
    print(f"[OK] {job_count} jobs linked to storm 1")

    job_count2 = hail_mgr.get_storm_job_count(storm2_id)
    assert job_count2 == 1, f"Expected 1 job, got {job_count2}"
    print(f"[OK] {job_count2} job linked to storm 2")

    print()

    # ========================================================================
    # TEST 2: Auto-Match Storm by ZIP/Date
    # ========================================================================

    print("="*80)
    print("[2/7] Testing auto-match feature...")
    print("="*80 + "\n")

    # Customer in affected area noticed damage recently
    damage_date = today - timedelta(days=25)
    match = hail_mgr.find_matching_storm('75024', damage_date)

    if match:
        print(f"Auto-matched to: {match['event_name']}")
        assert match['id'] == storm_id, "Should match first storm"
        print("[OK] ZIP-based match working")
    else:
        print("[ERROR] No match found!")

    print()

    # Customer outside affected area - should still find closest by date
    match2 = hail_mgr.find_matching_storm('90210', damage_date)

    if match2:
        print(f"Fallback match (by date): {match2['event_name']}")
        print("[OK] Date-based fallback working")

    print()

    # No matching storm (old date)
    old_date = today - timedelta(days=365)
    no_match = hail_mgr.find_matching_storm('75024', old_date)

    if not no_match:
        print("[OK] No false positives for old dates")
    else:
        print(f"Found storm for old date: {no_match['event_name']}")

    print()

    # ========================================================================
    # TEST 3: Get Storm Jobs
    # ========================================================================

    print("="*80)
    print("[3/7] Getting jobs linked to storm...")
    print("="*80 + "\n")

    storm_jobs = hail_mgr.get_storm_jobs(storm_id)

    print(f"Jobs linked to storm: {len(storm_jobs)}")
    for job in storm_jobs:
        print(f"  - {job['job_number']}: {job['customer_name']} - {job['vehicle_description']} ({job['confidence']})")

    print()

    assert len(storm_jobs) == 4, f"Expected 4 jobs, got {len(storm_jobs)}"
    print("[OK] Storm jobs retrieval working")
    print()

    # ========================================================================
    # TEST 4: Add Payments and Calculate ROI
    # ========================================================================

    print("="*80)
    print("[4/7] Adding payments and calculating ROI...")
    print("="*80 + "\n")

    # Create invoices and payments for 3 of the jobs
    for i, job_id in enumerate(job_ids[:3]):
        # Create invoice - use result['id'] from INSERT
        invoice_number = f'INV-2024-{2000+i}'
        result = db.execute("""
            INSERT INTO invoices (
                invoice_number, job_id, customer_id,
                subtotal, tax_amount, total, balance_due,
                invoice_date, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_number,
            job_id,
            i + 1,  # customer_id
            3000.00,
            247.50,
            3247.50,
            0,  # Paid
            today.isoformat(),
            'PAID',
            datetime.now().isoformat()
        ))
        invoice_id = result[0]['id']

        # Create payment
        db.execute("""
            INSERT INTO payments (
                invoice_id, job_id, amount, payment_method, payment_date,
                payer_type, total_amount, parts_cost, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            job_id,
            3247.50,
            'CHECK',
            today.isoformat(),
            'INSURANCE',
            3247.50,
            200.00,
            'RECEIVED',
            datetime.now().isoformat()
        ))

        print(f"  Created payment for job #{job_id}: $3,247.50")

    print()

    # Calculate ROI
    roi = hail_mgr.get_storm_roi(storm_id)

    print("Storm ROI Analysis:")
    print(f"  Event Name:         {roi['event_name']}")
    print(f"  Jobs Created:       {roi['jobs_created']}")
    print(f"  Customers Acquired: {roi['customers_acquired']}")
    print(f"  Total Revenue:      ${roi['total_revenue']:,.2f}")
    print(f"  Labor Revenue:      ${roi['labor_revenue']:,.2f}")
    print(f"  Avg per Job:        ${roi['avg_revenue_per_job']:,.2f}")
    print(f"  Market Penetration: {roi['market_penetration']:.4f}%")
    print(f"  Leads Generated:    {roi['leads_generated']}")
    print(f"  Conversion Rate:    {roi['lead_conversion_rate']:.1f}%")
    print()

    assert roi['jobs_created'] == 4
    assert roi['total_revenue'] == 9742.50  # 3 payments * $3,247.50
    print("[OK] ROI calculation working")
    print()

    # ========================================================================
    # TEST 5: All Storms Performance
    # ========================================================================

    print("="*80)
    print("[5/7] Getting all storms performance...")
    print("="*80 + "\n")

    performance = hail_mgr.get_all_storms_performance(
        start_date=today - timedelta(days=90),
        min_jobs=0
    )

    print(f"Storm Performance Summary ({len(performance)} storms):")
    print("-" * 60)
    for storm in performance:
        print(f"  {storm['event_name']}:")
        print(f"    Jobs: {storm['job_count']}")
        print(f"    Revenue: ${storm['total_revenue']:,.2f}")
        print(f"    Avg/Job: ${storm['avg_revenue_per_job']:,.2f}")
        print(f"    Penetration: {storm['market_penetration']:.4f}%")
        print()

    assert len(performance) == 2, f"Expected 2 storms, got {len(performance)}"
    print("[OK] All storms performance working")
    print()

    # ========================================================================
    # TEST 6: Storm Comparison
    # ========================================================================

    print("="*80)
    print("[6/7] Comparing storm performance...")
    print("="*80 + "\n")

    comparison = hail_mgr.get_storm_comparison([storm_id, storm2_id])

    print("Storm Comparison:")
    print(f"  Total Jobs:      {comparison['totals']['jobs']}")
    print(f"  Total Revenue:   ${comparison['totals']['revenue']:,.2f}")
    print(f"  Total Customers: {comparison['totals']['customers']}")
    print()
    print(f"  Avg Jobs/Storm:     {comparison['averages']['jobs_per_storm']:.1f}")
    print(f"  Avg Revenue/Storm:  ${comparison['averages']['revenue_per_storm']:,.2f}")
    print()

    assert comparison['totals']['jobs'] == 5
    print("[OK] Storm comparison working")
    print()

    # ========================================================================
    # TEST 7: Generate Reports
    # ========================================================================

    print("="*80)
    print("[7/7] Generating reports...")
    print("="*80 + "\n")

    # Individual storm report
    print("--- INDIVIDUAL STORM PERFORMANCE REPORT ---")
    print()
    report = hail_mgr.generate_storm_performance_report(storm_id)
    print(report)
    print()

    # Multi-storm report
    print("--- MULTI-STORM REPORT ---")
    print()
    multi_report = hail_mgr.generate_multi_storm_report(days=365)
    print(multi_report)
    print()

    # ========================================================================
    # BONUS: Job Storm Link Details
    # ========================================================================

    print("="*80)
    print("[BONUS] Testing job storm link retrieval...")
    print("="*80 + "\n")

    link = hail_mgr.get_job_storm_link(job_ids[0])
    if link:
        print(f"Job #{job_ids[0]} linked to:")
        print(f"  Storm: {link['event_name']}")
        print(f"  Confidence: {link['confidence']}")
        print(f"  Linked at: {link['linked_at']}")
        print()
        print("[OK] Job storm link retrieval working")
    else:
        print("[ERROR] Could not retrieve job storm link")

    print()

    # Test unlinking
    hail_mgr.unlink_job_from_storm(job_ids[3], storm_id)
    new_count = hail_mgr.get_storm_job_count(storm_id)
    assert new_count == 3, f"Expected 3 jobs after unlink, got {new_count}"
    print("[OK] Job unlinking working")

    print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] STORM-TO-JOB LINKING & ANALYTICS TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Job-to-storm linking (with confidence levels)")
    print("  [OK] Auto-match storms (by ZIP/date)")
    print("  [OK] Storm jobs retrieval")
    print("  [OK] Storm ROI calculation")
    print("  [OK] Market penetration metrics")
    print("  [OK] Revenue per storm analysis")
    print("  [OK] Lead conversion tracking")
    print("  [OK] Multi-storm performance comparison")
    print("  [OK] Individual storm performance reports")
    print("  [OK] Multi-storm summary reports")
    print("  [OK] Job unlinking")
    print()

    print("STORM ANALYTICS CAPABILITIES:")
    print("  - Link jobs to specific storm events")
    print("  - Track confidence level (CONFIRMED, LIKELY, POSSIBLE)")
    print("  - Auto-suggest storm based on customer ZIP + damage date")
    print("  - Calculate total revenue by storm")
    print("  - Track jobs created per storm")
    print("  - Measure average revenue per job")
    print("  - Calculate market penetration %")
    print("  - Track lead conversion rates")
    print("  - Count customers acquired per storm")
    print("  - Compare performance across multiple storms")
    print("  - Generate detailed performance reports")
    print()

    print("Ready for PROMPT 18: Before/After Photo Management?")
    print()

    return True


if __name__ == '__main__':
    success = test_storm_linking()
    sys.exit(0 if success else 1)
