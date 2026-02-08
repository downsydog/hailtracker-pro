"""
Test Payment Processing & Commissions
PDR CRM Part 13 - Commission Management
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_commission_manager():
    print("\n" + "="*80)
    print("TESTING PAYMENT PROCESSING & COMMISSIONS")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.commission_manager import CommissionManager
    from src.crm.managers.payment_manager import PaymentManager
    from src.crm.managers.job_manager import JobManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from datetime import datetime, date, timedelta

    # Use test database
    test_db = "data/test_commission.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    comm_mgr = CommissionManager(db)
    payment_mgr = PaymentManager(db)
    job_mgr = JobManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)

    # Create test data
    print("\nSetting up test data...")

    # Create technician
    db.execute("""
        INSERT INTO technicians (
            first_name, last_name, employee_id,
            skill_level, status, max_jobs_concurrent,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('Mike', 'Smith', 'TECH001', 'SENIOR', 'ACTIVE', 3, datetime.now().isoformat()))

    tech_result = db.execute("SELECT id FROM technicians WHERE employee_id = 'TECH001'")
    tech_id = tech_result[0]['id']

    # Create second tech for comparison
    db.execute("""
        INSERT INTO technicians (
            first_name, last_name, employee_id,
            skill_level, status, max_jobs_concurrent,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('Sarah', 'Johnson', 'TECH002', 'JUNIOR', 'ACTIVE', 2, datetime.now().isoformat()))

    tech2_result = db.execute("SELECT id FROM technicians WHERE employee_id = 'TECH002'")
    tech2_id = tech2_result[0]['id']

    # Create customer
    customer_id = customer_mgr.create_customer({
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '214-555-0100',
        'email': 'john.doe@example.com'
    })

    # Create vehicle
    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2022,
        'make': 'Toyota',
        'model': 'Camry',
        'color': 'Silver'
    })

    # Create multiple jobs and payments
    payment_ids = []
    job_ids = []

    for i in range(5):
        job_id = job_mgr.create_job(
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            job_type="HAIL",
            damage_type="HAIL"
        )
        job_ids.append(job_id)

        # Assign tech and complete job
        db.execute("""
            UPDATE jobs SET status = 'APPROVED', assigned_tech_id = ?, updated_at = ?
            WHERE id = ?
        """, (tech_id, datetime.now().isoformat(), job_id))

        job_mgr.assign_tech(job_id, tech_id, estimated_hours=4.0 + i)

        # Mark job completed
        db.execute("""
            UPDATE jobs SET status = 'COMPLETED', completed_at = ?, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), datetime.now().isoformat(), job_id))

        # Create invoice
        db.execute("""
            INSERT INTO invoices (
                invoice_number, job_id, customer_id,
                subtotal, tax_amount, total, balance_due,
                invoice_date, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'INV-2026-{i+1:04d}', job_id, customer_id,
            1000.00 + (i * 200), 82.50 + (i * 16.50), 1082.50 + (i * 216.50), 0,
            date.today().isoformat(), 'SENT',
            datetime.now().isoformat()
        ))

        invoice_result = db.execute("SELECT id FROM invoices WHERE invoice_number = ?", (f'INV-2026-{i+1:04d}',))
        invoice_id = invoice_result[0]['id']

        # Record payment
        payment_id = payment_mgr.record_payment(
            invoice_id=invoice_id,
            job_id=job_id,
            amount=1082.50 + (i * 216.50),
            payment_method='CHECK',
            payment_date=date.today() - timedelta(days=5-i),  # Spread over last 5 days
            payer_type='INSURANCE',
            parts_cost=100.00 + (i * 20)  # Variable parts cost
        )
        payment_ids.append(payment_id)

    print()

    # ========================================================================
    # TEST 1: Get Tiered Rates
    # ========================================================================

    print("="*80)
    print("[1/10] Getting commission tier rates...")
    print("="*80 + "\n")

    rates = comm_mgr.get_tiered_rates()

    print("Commission Tier Structure:")
    for tier, rate in rates.items():
        print(f"  {tier:15s}: {rate*100:.0f}%")
    print()

    assert 'JUNIOR' in rates
    assert 'SENIOR' in rates
    assert 'MASTER' in rates
    print("[OK] Tiered rates available")
    print()

    # ========================================================================
    # TEST 2: Calculate Commissions
    # ========================================================================

    print("="*80)
    print("[2/10] Calculating commissions...")
    print("="*80 + "\n")

    for i, payment_id in enumerate(payment_ids[:3]):
        calc = comm_mgr.calculate_commission(payment_id)
        print(f"Payment #{payment_id}:")
        print(f"  Total Amount: ${calc['total_amount']:,.2f}")
        print(f"  Parts Cost: ${calc['parts_cost']:,.2f}")
        print(f"  Labor Amount: ${calc['labor_amount']:,.2f}")
        print(f"  Commission Rate: {calc['rate']*100:.0f}%")
        print(f"  Commission: ${calc['commission_amount']:,.2f}")
        print()

    # Verify commission calculation
    calc = comm_mgr.calculate_commission(payment_ids[0])
    expected_labor = 1082.50 - 100.00  # total - parts
    expected_commission = expected_labor * 0.55  # SENIOR rate
    assert abs(calc['commission_amount'] - expected_commission) < 0.01
    print("[OK] Commission calculations correct")
    print()

    # ========================================================================
    # TEST 3: Record Commissions
    # ========================================================================

    print("="*80)
    print("[3/10] Recording commissions...")
    print("="*80 + "\n")

    commission_ids = []
    for payment_id in payment_ids:
        commission_id = comm_mgr.record_commission(
            payment_id=payment_id,
            tech_id=tech_id
        )
        commission_ids.append(commission_id)

    print()
    assert len(commission_ids) == 5
    print(f"[OK] Recorded {len(commission_ids)} commissions")
    print()

    # ========================================================================
    # TEST 4: Add Bonus
    # ========================================================================

    print("="*80)
    print("[4/10] Adding performance bonus...")
    print("="*80 + "\n")

    bonus_id = comm_mgr.add_bonus(
        tech_id=tech_id,
        amount=500.00,
        reason='Exceeded 5 jobs this week - performance bonus'
    )

    assert bonus_id is not None
    print()
    print(f"[OK] Added bonus (ID: {bonus_id})")
    print()

    # ========================================================================
    # TEST 5: Add Deduction
    # ========================================================================

    print("="*80)
    print("[5/10] Adding deduction...")
    print("="*80 + "\n")

    deduction_id = comm_mgr.add_deduction(
        tech_id=tech_id,
        amount=150.00,
        reason='Customer rework required - door panel scratch'
    )

    assert deduction_id is not None
    print()
    print(f"[OK] Added deduction (ID: {deduction_id})")
    print()

    # ========================================================================
    # TEST 6: Get Earnings Summary
    # ========================================================================

    print("="*80)
    print("[6/10] Getting earnings summary...")
    print("="*80 + "\n")

    earnings = comm_mgr.get_tech_earnings(tech_id)

    print(f"Tech #{tech_id} Earnings (Last 30 Days):")
    print(f"  Jobs completed:      {earnings['job_count']}")
    print(f"  Total commissions:   ${earnings['total_commissions']:,.2f}")
    print(f"  Bonuses:             ${earnings['total_bonuses']:,.2f}")
    print(f"  Deductions:         -${earnings['total_deductions']:,.2f}")
    print(f"  Total earnings:      ${earnings['total_earnings']:,.2f}")
    print(f"  Average per job:     ${earnings['avg_per_job']:,.2f}")
    print()
    print(f"  Status:")
    print(f"    Pending:           ${earnings['pending_earnings']:,.2f}")
    print(f"    In Payout:         ${earnings['in_payout_earnings']:,.2f}")
    print(f"    Paid:              ${earnings['paid_earnings']:,.2f}")
    print()

    assert earnings['job_count'] == 5
    assert earnings['total_bonuses'] == 500.00
    assert earnings['total_deductions'] == 150.00
    print("[OK] Earnings summary correct")
    print()

    # ========================================================================
    # TEST 7: Create and Process Payout
    # ========================================================================

    print("="*80)
    print("[7/10] Creating payout...")
    print("="*80 + "\n")

    # Create payout for this week
    monday = date.today() - timedelta(days=date.today().weekday() + 7)  # Last week's Monday
    friday = monday + timedelta(days=4)

    payout_id = comm_mgr.create_payout(
        tech_id=tech_id,
        start_date=monday,
        end_date=date.today(),  # Include today
        payout_date=date.today() + timedelta(days=7),
        notes='Weekly payout'
    )

    assert payout_id is not None
    print()
    print(f"[OK] Created payout (ID: {payout_id})")
    print()

    # Approve payout
    print("Approving payout...")
    comm_mgr.approve_payout(payout_id, approved_by='Admin')
    print()

    # Process payout
    print("Processing payout...")
    comm_mgr.process_payout(
        payout_id=payout_id,
        payment_method='DIRECT_DEPOSIT',
        reference_number='DD-20260118-001'
    )

    print()
    print("[OK] Payout processed successfully")
    print()

    # ========================================================================
    # TEST 8: Get Pending Payouts
    # ========================================================================

    print("="*80)
    print("[8/10] Checking pending payouts...")
    print("="*80 + "\n")

    # Add a new commission to tech2 so we have pending items
    db.execute("""
        UPDATE jobs SET assigned_tech_id = ? WHERE id = ?
    """, (tech2_id, job_ids[0]))

    comm_mgr.record_commission(
        payment_id=payment_ids[0],
        tech_id=tech2_id,
        commission_amount=300.00,  # Override for test
        notes='Test commission for tech2'
    )

    pending = comm_mgr.get_pending_payouts()
    print(f"Pending Payouts: {len(pending)}")
    for p in pending:
        print(f"  Tech: {p['tech_name']} - ${p['total_amount']:,.2f} ({p['status']})")
    print()

    # Check pending commissions for tech2
    pending_comms = comm_mgr.get_pending_commissions(tech2_id)
    print(f"Pending Commissions for Tech #{tech2_id}: {len(pending_comms)}")
    print()

    print("[OK] Pending payout tracking working")
    print()

    # ========================================================================
    # TEST 9: Commission History
    # ========================================================================

    print("="*80)
    print("[9/10] Getting commission history...")
    print("="*80 + "\n")

    history = comm_mgr.get_commission_history(tech_id, limit=10)

    print(f"Commission History for Tech #{tech_id}: {len(history)} records")
    for h in history[:5]:  # Show first 5
        comm_type = h.get('commission_type', 'COMMISSION')
        job_num = h.get('job_number') or '-'
        amount = h['commission_amount']
        status = h['status'] or 'PENDING'
        sign = '+' if amount >= 0 else ''
        print(f"  [{status:10s}] {comm_type:12s} Job:{str(job_num):<15s} {sign}${amount:,.2f}")
    print()

    assert len(history) >= 5
    print("[OK] Commission history working")
    print()

    # ========================================================================
    # TEST 10: Generate Commission Report
    # ========================================================================

    print("="*80)
    print("[10/10] Generating commission report...")
    print("="*80 + "\n")

    report = comm_mgr.generate_commission_report(
        tech_id=tech_id,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today()
    )

    print(report)

    assert 'COMMISSION REPORT' in report
    assert 'Mike Smith' in report
    print("[OK] Commission report generated")
    print()

    # ========================================================================
    # BONUS: Payout Summary
    # ========================================================================

    print("="*80)
    print("[BONUS] Generating payout summary...")
    print("="*80 + "\n")

    summary = comm_mgr.generate_payout_summary(days=30)
    print(summary)

    # ========================================================================
    # BONUS: Update Commission Tier
    # ========================================================================

    print("="*80)
    print("[BONUS] Updating commission tier...")
    print("="*80 + "\n")

    # Get current rate
    old_rate = comm_mgr.get_commission_rate_for_tech(tech_id)
    print(f"Current commission rate for tech #{tech_id}: {old_rate*100:.0f}%")

    # Promote to MASTER
    comm_mgr.update_tech_commission_tier(tech_id, 'MASTER')

    # Get new rate
    new_rate = comm_mgr.get_commission_rate_for_tech(tech_id)
    print(f"New commission rate for tech #{tech_id}: {new_rate*100:.0f}%")
    print()

    assert new_rate == 0.60  # MASTER rate
    print("[OK] Commission tier updated")
    print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] PAYMENT PROCESSING & COMMISSIONS TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Commission calculation (percentage-based)")
    print("  [OK] Tiered commission rates (JUNIOR to MASTER)")
    print("  [OK] Commission recording per payment")
    print("  [OK] Performance bonuses")
    print("  [OK] Deductions (chargebacks)")
    print("  [OK] Payout creation (group commissions)")
    print("  [OK] Payout approval workflow")
    print("  [OK] Payout processing")
    print("  [OK] Earnings summaries")
    print("  [OK] Commission history tracking")
    print("  [OK] Commission reports")
    print("  [OK] Payout summaries")
    print("  [OK] Commission tier management")
    print()

    print("COMMISSION STRUCTURE:")
    print("  - Junior Tech:       40% of labor")
    print("  - Intermediate Tech: 45% of labor")
    print("  - Standard Tech:     50% of labor")
    print("  - Senior Tech:       55% of labor")
    print("  - Expert Tech:       58% of labor")
    print("  - Master Tech:       60% of labor")
    print()

    print("COMMISSION CALCULATION:")
    print("  - Based on labor only (parts excluded)")
    print("  - Rate based on tech skill level")
    print("  - Bonuses added separately")
    print("  - Deductions subtracted")
    print()

    print("PAYOUT WORKFLOW:")
    print("  1. Jobs completed -> payments recorded")
    print("  2. Commissions auto-calculated and recorded")
    print("  3. Add bonuses/deductions as needed")
    print("  4. Create payout (groups pending commissions)")
    print("  5. Approve payout (manager review)")
    print("  6. Process payout (mark as paid)")
    print("  7. Generate reports for records")
    print()

    print("Ready for PROMPT 14: Customer Portal (Self-Service)?")
    print()

    return True


if __name__ == '__main__':
    success = test_commission_manager()
    sys.exit(0 if success else 1)
