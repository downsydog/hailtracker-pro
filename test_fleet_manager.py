"""
Test Fleet & Batch Processing
PDR CRM Part 24 - Fleet customer management and batch operations
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_fleet_manager():
    print("\n" + "="*80)
    print("TESTING FLEET & BATCH PROCESSING")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.fleet_manager import FleetManager

    # Use test database
    test_db = "data/test_fleet_manager.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mgr = FleetManager(db)

    print()

    # ========================================================================
    # TEST 1: Create Fleet Customer
    # ========================================================================

    print("="*80)
    print("[1/10] Creating fleet customer...")
    print("="*80 + "\n")

    fleet_id = mgr.create_fleet_customer(
        company_name="Metro Auto Dealership",
        fleet_type="DEALERSHIP",
        primary_contact_name="John Smith",
        primary_contact_email="john@metrodealer.com",
        primary_contact_phone="555-1234",
        billing_address="100 Auto Row",
        city="Dallas",
        state="TX",
        zip_code="75001",
        tax_id="12-3456789",
        pricing_tier="SILVER",
        payment_terms="NET_30",
        notes="Large dealership, high volume potential"
    )
    print()

    assert fleet_id > 0
    print("[OK] Fleet customer created")
    print()

    # ========================================================================
    # TEST 2: Create Batch Job
    # ========================================================================

    print("="*80)
    print("[2/10] Creating batch job...")
    print("="*80 + "\n")

    vehicles = [
        {
            'stock_number': 'A001',
            'year': 2023,
            'make': 'Toyota',
            'model': 'Camry',
            'vin': 'VIN001',
            'color': 'Silver',
            'damage_type': 'HAIL',
            'estimated_cost': 850.00
        },
        {
            'stock_number': 'A002',
            'year': 2023,
            'make': 'Honda',
            'model': 'Accord',
            'vin': 'VIN002',
            'color': 'White',
            'damage_type': 'HAIL',
            'estimated_cost': 1200.00
        },
        {
            'stock_number': 'A003',
            'year': 2022,
            'make': 'Ford',
            'model': 'F-150',
            'vin': 'VIN003',
            'color': 'Blue',
            'damage_type': 'HAIL',
            'estimated_cost': 1500.00
        },
        {
            'stock_number': 'A004',
            'year': 2024,
            'make': 'Chevrolet',
            'model': 'Silverado',
            'vin': 'VIN004',
            'color': 'Black',
            'damage_type': 'HAIL',
            'estimated_cost': 1800.00
        },
        {
            'stock_number': 'A005',
            'year': 2023,
            'make': 'Nissan',
            'model': 'Altima',
            'vin': 'VIN005',
            'color': 'Red',
            'damage_type': 'HAIL',
            'estimated_cost': 950.00
        }
    ]

    batch_id = mgr.create_batch_job(
        fleet_id=fleet_id,
        batch_name="Weekly Hail Repair - Jan 2026",
        vehicles=vehicles,
        created_by="tech_manager",
        notes="Storm damage from Jan 15 hail event"
    )
    print()

    assert batch_id > 0
    print("[OK] Batch job created")
    print()

    # ========================================================================
    # TEST 3: Add Vehicle to Existing Batch
    # ========================================================================

    print("="*80)
    print("[3/10] Adding vehicle to existing batch...")
    print("="*80 + "\n")

    new_vehicle_id = mgr.add_vehicle_to_batch(
        batch_id=batch_id,
        vehicle={
            'stock_number': 'A006',
            'year': 2023,
            'make': 'BMW',
            'model': 'X3',
            'vin': 'VIN006',
            'color': 'Gray',
            'damage_type': 'HAIL',
            'estimated_cost': 2200.00
        }
    )
    print()

    assert new_vehicle_id > 0

    # Verify batch updated
    batch_details = mgr.get_batch_details(batch_id)
    assert batch_details['vehicle_count'] == 6
    print(f"Batch now has {batch_details['vehicle_count']} vehicles")
    print(f"Total estimated: ${batch_details['batch']['total_estimated_cost']:,.2f}")
    print()

    print("[OK] Vehicle added to batch")
    print()

    # ========================================================================
    # TEST 4: Update Batch Vehicle Status
    # ========================================================================

    print("="*80)
    print("[4/10] Updating batch vehicle status...")
    print("="*80 + "\n")

    # Get first vehicle
    first_vehicle = batch_details['vehicles'][0]

    # Start work
    mgr.update_batch_vehicle_status(
        batch_vehicle_id=first_vehicle['id'],
        new_status='IN_PROGRESS',
        assigned_tech='tech_mike'
    )
    print()

    # Complete work
    mgr.update_batch_vehicle_status(
        batch_vehicle_id=first_vehicle['id'],
        new_status='COMPLETED',
        actual_cost=800.00,
        completed_at=datetime.now(),
        notes='Completed ahead of schedule'
    )
    print()

    # Verify
    updated_details = mgr.get_batch_details(batch_id)
    print(f"Batch Status:")
    print(f"  Completed: {updated_details['completed_count']}")
    print(f"  In Progress: {updated_details['in_progress_count']}")
    print(f"  Pending: {updated_details['pending_count']}")
    print()

    assert updated_details['completed_count'] == 1
    print("[OK] Batch vehicle status updated")
    print()

    # ========================================================================
    # TEST 5: Calculate Fleet Pricing
    # ========================================================================

    print("="*80)
    print("[5/10] Calculating fleet pricing...")
    print("="*80 + "\n")

    pricing = mgr.calculate_fleet_pricing(
        fleet_id=fleet_id,
        base_cost=1000.00
    )

    print(f"Fleet Pricing Calculation:")
    print(f"  Base cost: ${pricing['base_cost']:,.2f}")
    print(f"  Tier: {pricing['tier_name']}")
    print(f"  Discount: {pricing['discount_percent']}%")
    print(f"  Discount amount: ${pricing['discount_amount']:,.2f}")
    print(f"  Final cost: ${pricing['final_cost']:,.2f}")
    print(f"  Savings: ${pricing['savings']:,.2f}")
    print()

    assert pricing['discount_percent'] == 15  # Silver tier
    assert pricing['final_cost'] == 850.00
    print("[OK] Fleet pricing calculated correctly")
    print()

    # ========================================================================
    # TEST 6: Calculate Batch Pricing
    # ========================================================================

    print("="*80)
    print("[6/10] Calculating batch pricing...")
    print("="*80 + "\n")

    batch_pricing = mgr.calculate_batch_pricing(batch_id)

    print(f"Batch Pricing:")
    print(f"  Vehicles: {batch_pricing['vehicle_count']}")
    print(f"  Subtotal: ${batch_pricing['base_cost']:,.2f}")
    print(f"  Fleet Discount ({batch_pricing['discount_percent']}%): -${batch_pricing['discount_amount']:,.2f}")
    print(f"  Total: ${batch_pricing['final_cost']:,.2f}")
    print()

    assert batch_pricing['vehicle_count'] == 6
    print("[OK] Batch pricing calculated")
    print()

    # ========================================================================
    # TEST 7: Get Recommended Tier
    # ========================================================================

    print("="*80)
    print("[7/10] Getting recommended pricing tier...")
    print("="*80 + "\n")

    recommendation = mgr.get_recommended_tier(fleet_id, months_to_analyze=1)

    print(f"Tier Recommendation:")
    print(f"  Vehicles analyzed: {recommendation['vehicles_analyzed']}")
    print(f"  Months analyzed: {recommendation['months_analyzed']}")
    print(f"  Avg vehicles/month: {recommendation['avg_vehicles_per_month']}")
    print(f"  Current tier: {recommendation['current_tier']} ({recommendation['current_discount']}%)")
    print(f"  Recommended tier: {recommendation['recommended_tier']} ({recommendation['recommended_discount']}%)")
    print(f"  Should upgrade: {recommendation['should_upgrade']}")
    print(f"  Should downgrade: {recommendation['should_downgrade']}")
    print()

    print("[OK] Tier recommendation working")
    print()

    # ========================================================================
    # TEST 8: Create Bulk Invoice
    # ========================================================================

    print("="*80)
    print("[8/10] Creating bulk invoice...")
    print("="*80 + "\n")

    invoice_id = mgr.create_bulk_invoice(
        batch_id=batch_id,
        notes="Invoice for weekly hail repair batch"
    )
    print()

    assert invoice_id > 0

    # Record partial payment
    mgr.record_invoice_payment(
        invoice_id=invoice_id,
        amount=3000.00,
        payment_method='CHECK',
        reference='CHK-12345'
    )
    print()

    # Check invoice status
    invoices = mgr.get_fleet_invoices(fleet_id)
    invoice = invoices[0]
    print(f"Invoice Status:")
    print(f"  Invoice #: {invoice['invoice_number']}")
    print(f"  Total: ${invoice['total']:,.2f}")
    print(f"  Paid: ${invoice['amount_paid']:,.2f}")
    print(f"  Balance: ${invoice['balance_due']:,.2f}")
    print(f"  Status: {invoice['status']}")
    print()

    assert invoice['status'] == 'PARTIAL'
    print("[OK] Bulk invoice created and payment recorded")
    print()

    # ========================================================================
    # TEST 9: Create Fleet Contract
    # ========================================================================

    print("="*80)
    print("[9/10] Creating fleet contract...")
    print("="*80 + "\n")

    contract_id = mgr.create_fleet_contract(
        fleet_id=fleet_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        pricing_tier='GOLD',
        min_monthly_volume=50,
        discount_percent=20,
        terms="Guaranteed 50+ vehicles per month for Gold tier pricing",
        notes="Annual service contract - 2026"
    )
    print()

    assert contract_id > 0
    print("[OK] Fleet contract created")
    print()

    # ========================================================================
    # TEST 10: Fleet Performance Report
    # ========================================================================

    print("="*80)
    print("[10/10] Generating fleet performance report...")
    print("="*80 + "\n")

    performance = mgr.get_fleet_performance(fleet_id)

    print(f"Fleet Performance Metrics:")
    print(f"  Company: {performance['company_name']}")
    print(f"  Type: {performance['fleet_type']}")
    print(f"  Tier: {performance['pricing_tier']}")
    print(f"  Period: {performance['period']['start_date']} to {performance['period']['end_date']}")
    print()
    print(f"  Activity:")
    print(f"    Total batches: {performance['activity']['total_batches']}")
    print(f"    Total vehicles: {performance['activity']['total_vehicles']}")
    print(f"    Avg vehicles/month: {performance['activity']['avg_vehicles_per_month']}")
    print()
    print(f"  Revenue:")
    print(f"    Total: ${performance['revenue']['total_revenue']:,.2f}")
    print(f"    Discounts given: ${performance['revenue']['total_discounts_given']:,.2f}")
    print(f"    Avg per vehicle: ${performance['revenue']['avg_revenue_per_vehicle']:,.2f}")
    print()

    assert performance['activity']['total_vehicles'] == 6
    print("[OK] Fleet performance report generated")
    print()

    # ========================================================================
    # BONUS: Generate Summary Report
    # ========================================================================

    print("="*80)
    print("[BONUS] Generating fleet summary report...")
    print("="*80 + "\n")

    report = mgr.generate_fleet_summary_report(fleet_id)
    print(report)
    print()

    assert "FLEET CUSTOMER SUMMARY" in report
    assert "Metro Auto Dealership" in report
    print("[OK] Fleet summary report generated")
    print()

    # ========================================================================
    # BONUS 2: Create Second Fleet Customer (Different Type)
    # ========================================================================

    print("="*80)
    print("[BONUS] Creating rental company fleet...")
    print("="*80 + "\n")

    rental_id = mgr.create_fleet_customer(
        company_name="Quick Rent Car Rental",
        fleet_type="RENTAL_COMPANY",
        primary_contact_name="Sarah Jones",
        primary_contact_email="sarah@quickrent.com",
        primary_contact_phone="555-5678",
        billing_address="200 Airport Blvd",
        city="Dallas",
        state="TX",
        zip_code="75261",
        pricing_tier="GOLD",
        payment_terms="NET_15",
        notes="Airport location, high turnover"
    )
    print()

    # Get all fleet customers
    all_fleets = mgr.get_all_fleet_customers()
    print(f"\nAll Fleet Customers: {len(all_fleets)}")
    for fleet in all_fleets:
        tier = mgr.PRICING_TIERS[fleet['pricing_tier']]
        print(f"  - {fleet['company_name']} ({fleet['fleet_type']})")
        print(f"    Tier: {tier['name']} ({tier['discount_percent']}% discount)")
    print()

    assert len(all_fleets) == 2
    print("[OK] Multiple fleet customers managed")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] FLEET & BATCH PROCESSING TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Fleet customer creation")
    print("  [OK] Multiple fleet types (Dealership, Rental, etc.)")
    print("  [OK] Batch job creation")
    print("  [OK] Add vehicles to batch")
    print("  [OK] Batch vehicle status tracking")
    print("  [OK] Volume pricing tiers")
    print("  [OK] Fleet discount calculation")
    print("  [OK] Batch pricing with discounts")
    print("  [OK] Tier recommendation engine")
    print("  [OK] Bulk invoicing")
    print("  [OK] Payment recording")
    print("  [OK] Fleet contracts")
    print("  [OK] Performance reporting")
    print("  [OK] Summary report generation")
    print()

    print("FLEET TYPES SUPPORTED:")
    for fleet_type in mgr.FLEET_TYPES:
        print(f"  - {fleet_type}")
    print()

    print("VOLUME PRICING TIERS:")
    for tier, info in mgr.PRICING_TIERS.items():
        print(f"  {tier}: {info['discount_percent']}% discount ({info['min_vehicles_per_month']}+ vehicles/month)")
    print()

    print("TYPICAL FLEET WORKFLOW:")
    print("  1. Create fleet customer account")
    print("  2. Set pricing tier based on expected volume")
    print("  3. Create batch job for group of vehicles")
    print("  4. Track individual vehicle status")
    print("  5. Generate bulk invoice with fleet discount")
    print("  6. Record payments")
    print("  7. Review performance metrics")
    print("  8. Adjust tier based on actual volume")
    print()

    print("BATCH PROCESSING BENEFITS:")
    print("  - Single invoice for multiple vehicles")
    print("  - Automatic fleet discounts applied")
    print("  - Track progress across all vehicles")
    print("  - Efficient scheduling for groups")
    print("  - Volume-based tier recommendations")
    print()

    print("Ready for PROMPT 25?")
    print()

    return True


if __name__ == '__main__':
    success = test_fleet_manager()
    sys.exit(0 if success else 1)
