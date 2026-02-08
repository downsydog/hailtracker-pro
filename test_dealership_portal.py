"""
Test Dealership Portal & Volume Pricing
PDR CRM Part 25 - Self-service portal for fleet customers
"""

import sys
import os
from datetime import date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_dealership_portal():
    print("\n" + "="*80)
    print("TESTING DEALERSHIP PORTAL & VOLUME PRICING")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.dealership_portal_manager import DealershipPortalManager
    from src.crm.managers.fleet_manager import FleetManager

    # Use test database
    test_db = "data/test_dealer_portal.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    portal_mgr = DealershipPortalManager(db)
    fleet_mgr = FleetManager(db)

    print()

    # ========================================================================
    # Setup: Create fleet customer
    # ========================================================================

    print("Setting up test fleet customer...")
    print()

    fleet_id = fleet_mgr.create_fleet_customer(
        company_name='Dallas Auto Group',
        fleet_type='DEALERSHIP',
        primary_contact_name='Mike Johnson',
        primary_contact_email='mike@dallasauto.com',
        primary_contact_phone='555-1234',
        billing_address='123 Auto Plaza Drive',
        city='Dallas',
        state='TX',
        zip_code='75201',
        tax_id='12-3456789',
        pricing_tier='SILVER',
        payment_terms='NET_30'
    )

    print()

    # ========================================================================
    # TEST 1: Create Portal Access
    # ========================================================================

    print("="*80)
    print("[1/10] Creating portal access...")
    print("="*80 + "\n")

    user_id = portal_mgr.create_portal_access(
        fleet_id=fleet_id,
        username='mike.johnson',
        email='mike@dallasauto.com',
        access_level='ADMIN'
    )

    print()

    assert user_id > 0
    print("[OK] Portal access created")
    print()

    # ========================================================================
    # TEST 2: Get Portal Dashboard
    # ========================================================================

    print("="*80)
    print("[2/10] Getting portal dashboard...")
    print("="*80 + "\n")

    dashboard = portal_mgr.get_portal_dashboard(fleet_id)

    print(f"Portal Dashboard:")
    print(f"  Company: {dashboard['fleet_info']['company_name']}")
    print(f"  Pricing Tier: {dashboard['fleet_info']['tier_name']}")
    print(f"  Discount: {dashboard['fleet_info']['discount_percent']}%")
    print(f"  Payment Terms: {dashboard['fleet_info']['payment_terms']}")
    print()
    print(f"  This Month:")
    print(f"    Vehicles processed: {dashboard['this_month']['vehicles_processed']}")
    print(f"    Revenue: ${dashboard['this_month']['revenue']:,.2f}")
    print()
    print(f"  Active batches: {len(dashboard['active_batches'])}")
    print(f"  Recent invoices: {len(dashboard['recent_invoices'])}")
    print(f"  Unpaid balance: ${dashboard['unpaid_balance']:,.2f}")
    print()

    assert dashboard['fleet_info']['company_name'] == 'Dallas Auto Group'
    assert dashboard['fleet_info']['discount_percent'] == 15  # Silver tier
    print("[OK] Portal dashboard working")
    print()

    # ========================================================================
    # TEST 3: Submit Batch via CSV
    # ========================================================================

    print("="*80)
    print("[3/10] Submitting batch via CSV...")
    print("="*80 + "\n")

    csv_data = """stock_number,year,make,model,vin,damage_type,estimated_cost
A12345,2023,Toyota,Camry,1HGBH41JXMN109186,HAIL,850.00
A12346,2023,Honda,Accord,1HGBH41JXMN109187,DOOR_DING,350.00
A12347,2024,Ford,F-150,1HGBH41JXMN109188,HAIL,1200.00
A12348,2023,Chevrolet,Silverado,1HGBH41JXMN109189,DOOR_DING,275.00
A12349,2024,Nissan,Altima,1HGBH41JXMN109190,HAIL,950.00"""

    csv_result = portal_mgr.submit_batch_via_csv(
        fleet_id=fleet_id,
        csv_data=csv_data,
        batch_name='Weekly Service - January 2026',
        submitted_by='mike.johnson'
    )

    print(f"CSV Upload Result:")
    print(f"  Success: {csv_result['success']}")
    print(f"  Batch ID: {csv_result['batch_id']}")
    print(f"  Batch name: {csv_result['batch_name']}")
    print(f"  Vehicles uploaded: {csv_result['vehicles_uploaded']}")
    print(f"  Total estimated: ${csv_result['total_estimated_cost']:,.2f}")
    print()

    batch_id = csv_result['batch_id']

    assert csv_result['success'] == True
    assert csv_result['vehicles_uploaded'] == 5
    print("[OK] CSV batch upload working")
    print()

    # ========================================================================
    # TEST 4: Generate API Key
    # ========================================================================

    print("="*80)
    print("[4/10] Generating API key...")
    print("="*80 + "\n")

    api_key = portal_mgr.generate_api_key(
        fleet_id=fleet_id,
        key_name='DMS Integration - Production',
        permissions=['batch.submit', 'batch.view', 'invoice.view']
    )

    print()

    assert api_key.startswith('fleet_')
    print("[OK] API key generated")
    print()

    # ========================================================================
    # TEST 5: Submit Batch via API
    # ========================================================================

    print("="*80)
    print("[5/10] Submitting batch via API...")
    print("="*80 + "\n")

    api_vehicles = [
        {
            'stock_number': 'B54321',
            'year': 2024,
            'make': 'Tesla',
            'model': 'Model 3',
            'vin': '5YJ3E1EA1LF000001',
            'damage_type': 'DOOR_DING',
            'estimated_cost': 425.00
        },
        {
            'stock_number': 'B54322',
            'year': 2023,
            'make': 'BMW',
            'model': '330i',
            'vin': 'WBA5A5C50ED000001',
            'damage_type': 'HAIL',
            'estimated_cost': 1150.00
        }
    ]

    api_result = portal_mgr.submit_batch_via_api(
        fleet_id=fleet_id,
        api_key=api_key,
        vehicles=api_vehicles
    )

    print(f"API Submission Result:")
    print(f"  Success: {api_result['success']}")
    print(f"  Batch ID: {api_result['batch_id']}")
    print(f"  Vehicles submitted: {api_result['vehicles_submitted']}")
    print()

    assert api_result['success'] == True
    assert api_result['vehicles_submitted'] == 2
    print("[OK] API batch submission working")
    print()

    # ========================================================================
    # TEST 6: Get Batch Status
    # ========================================================================

    print("="*80)
    print("[6/10] Getting batch status...")
    print("="*80 + "\n")

    batch_status = portal_mgr.get_batch_status(fleet_id, batch_id)

    print(f"Batch Status:")
    print(f"  Batch: {batch_status['batch_name']}")
    print(f"  Created: {batch_status['created_at']}")
    print(f"  Status: {batch_status['status']}")
    print(f"  Total vehicles: {batch_status['total_vehicles']}")
    print(f"  Progress: {batch_status['progress_percent']:.0f}%")
    print()
    print(f"  Status breakdown:")
    for status, count in batch_status['status_breakdown'].items():
        if count > 0:
            print(f"    {status}: {count}")
    print()

    assert batch_status['total_vehicles'] == 5
    print("[OK] Batch status tracking working")
    print()

    # ========================================================================
    # TEST 7: Track Vehicle by Stock Number
    # ========================================================================

    print("="*80)
    print("[7/10] Tracking vehicle by stock number...")
    print("="*80 + "\n")

    vehicle_status = portal_mgr.get_vehicle_status(fleet_id, 'A12345')

    if vehicle_status:
        print(f"Vehicle Status:")
        print(f"  Stock #: {vehicle_status['stock_number']}")
        print(f"  Vehicle: {vehicle_status['year']} {vehicle_status['make']} {vehicle_status['model']}")
        print(f"  Batch: {vehicle_status['batch_name']}")
        print(f"  Status: {vehicle_status['status']}")
        print(f"  Estimated cost: ${vehicle_status['estimated_cost']:,.2f}")
        print()

    assert vehicle_status is not None
    assert vehicle_status['stock_number'] == 'A12345'
    assert vehicle_status['make'] == 'Toyota'
    print("[OK] Vehicle tracking working")
    print()

    # ========================================================================
    # TEST 8: Create Bulk Invoice
    # ========================================================================

    print("="*80)
    print("[8/10] Creating bulk invoice...")
    print("="*80 + "\n")

    # Mark vehicles complete first
    batch_vehicles = db.execute("SELECT * FROM batch_vehicles WHERE batch_job_id = ?", (batch_id,))

    for bv in batch_vehicles:
        fleet_mgr.update_batch_vehicle_status(
            batch_vehicle_id=bv['id'],
            new_status='COMPLETED',
            actual_cost=bv['estimated_cost']
        )
    print()

    invoice_id = fleet_mgr.create_bulk_invoice(
        batch_id=batch_id,
        invoice_date=date.today(),
        notes='Batch completed - all vehicles ready for pickup'
    )
    print()

    assert invoice_id > 0
    print("[OK] Bulk invoice created")
    print()

    # ========================================================================
    # TEST 9: Get Invoice Details
    # ========================================================================

    print("="*80)
    print("[9/10] Getting invoice details...")
    print("="*80 + "\n")

    invoice_details = portal_mgr.get_invoice_details(fleet_id, invoice_id)

    if invoice_details:
        inv = invoice_details['invoice']
        print(f"Invoice Details:")
        print(f"  Invoice #: {inv['invoice_number']}")
        print(f"  Date: {inv['invoice_date']}")
        print(f"  Due: {inv['due_date']}")
        print(f"  Vehicles: {invoice_details['line_item_count']}")
        print()
        print(f"  Subtotal: ${inv['subtotal']:,.2f}")
        print(f"  Discount ({inv['discount_percent']}%): -${inv['discount_amount']:,.2f}")
        print(f"  Total: ${inv['total']:,.2f}")
        print(f"  Balance due: ${inv['balance_due']:,.2f}")
        print()

    assert invoice_details is not None
    assert invoice_details['line_item_count'] == 5
    assert invoice_details['invoice']['discount_percent'] == 15
    print("[OK] Invoice details working")
    print()

    # ========================================================================
    # TEST 10: Generate Monthly Report
    # ========================================================================

    print("="*80)
    print("[10/10] Generating monthly report...")
    print("="*80 + "\n")

    monthly_report = portal_mgr.generate_monthly_report(
        fleet_id=fleet_id,
        year=2026,
        month=1
    )

    print(f"Monthly Report - {monthly_report['report_period']['month_name']} {monthly_report['report_period']['year']}")
    print(f"Company: {monthly_report['company_name']}")
    print()
    print(f"Activity:")
    print(f"  Batches submitted: {monthly_report['activity']['batches_submitted']}")
    print(f"  Vehicles processed: {monthly_report['activity']['vehicles_processed']}")
    print(f"  Avg per batch: {monthly_report['activity']['avg_vehicles_per_batch']:.1f}")
    print()
    print(f"Financial:")
    print(f"  Total revenue: ${monthly_report['financial']['total_revenue']:,.2f}")
    print(f"  Total discounts: ${monthly_report['financial']['total_discounts']:,.2f}")
    print(f"  Avg per vehicle: ${monthly_report['financial']['avg_revenue_per_vehicle']:,.2f}")
    print()
    print(f"Pricing:")
    print(f"  Current tier: {monthly_report['pricing']['current_tier']}")
    print(f"  Discount: {monthly_report['pricing']['discount_percent']}%")
    print()

    assert monthly_report['company_name'] == 'Dallas Auto Group'
    print("[OK] Monthly report generated")
    print()

    # ========================================================================
    # BONUS: Activity Log
    # ========================================================================

    print("="*80)
    print("[BONUS] Checking activity log...")
    print("="*80 + "\n")

    activity_log = portal_mgr.get_activity_log(fleet_id)

    print(f"Recent Activity ({len(activity_log)} entries):")
    for entry in activity_log[:5]:
        print(f"  {entry['created_at']}: {entry['action']}")
        if entry.get('details'):
            print(f"    {entry['details']}")
    print()

    assert len(activity_log) >= 3
    print("[OK] Activity logging working")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] DEALERSHIP PORTAL & VOLUME PRICING TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Portal access creation")
    print("  [OK] Dashboard data aggregation")
    print("  [OK] CSV batch upload")
    print("  [OK] API key generation")
    print("  [OK] API batch submission")
    print("  [OK] Real-time batch status")
    print("  [OK] Vehicle tracking by stock #")
    print("  [OK] Bulk invoice creation")
    print("  [OK] Invoice details & download")
    print("  [OK] Monthly reporting")
    print("  [OK] Activity logging")
    print()

    print("PORTAL FEATURES:")
    print("  - Self-service batch submission")
    print("  - CSV/Excel upload (unlimited vehicles)")
    print("  - Real-time status tracking")
    print("  - Automated volume pricing")
    print("  - Invoice history & downloads")
    print("  - Performance dashboards")
    print("  - Monthly activity reports")
    print("  - API for DMS integration")
    print()

    print("API INTEGRATION:")
    print("  Endpoint: POST /api/v1/fleet/batch/submit")
    print("  Authentication: API Key in header")
    print("  Permissions: batch.submit, batch.view, invoice.view")
    print()
    print("  Example Request:")
    print("  {")
    print('    "vehicles": [')
    print("      {")
    print('        "stock_number": "A12345",')
    print('        "year": 2023,')
    print('        "make": "Toyota",')
    print('        "model": "Camry",')
    print('        "vin": "1HGBH41JXMN109186",')
    print('        "damage_type": "HAIL",')
    print('        "estimated_cost": 850.00')
    print("      }")
    print("    ]")
    print("  }")
    print()

    print("CSV FORMAT:")
    print("  stock_number,year,make,model,vin,damage_type,estimated_cost")
    print("  A12345,2023,Toyota,Camry,1HGBH41JXMN109186,HAIL,850.00")
    print("  A12346,2023,Honda,Accord,1HGBH41JXMN109187,DOOR_DING,350.00")
    print()

    print("VOLUME PRICING TIERS:")
    print("  Standard:  0+ vehicles/month  - 0% discount")
    print("  Bronze:   10+ vehicles/month  - 10% discount")
    print("  Silver:   25+ vehicles/month  - 15% discount")
    print("  Gold:     50+ vehicles/month  - 20% discount")
    print("  Platinum: 100+ vehicles/month - 25% discount")
    print()

    print("DEALERSHIP BENEFITS:")
    print("  - Automatic tier upgrades based on volume")
    print("  - Single invoice for entire batch")
    print("  - Extended payment terms (NET 30)")
    print("  - Priority scheduling")
    print("  - Dedicated account manager")
    print("  - Real-time status updates")
    print("  - API integration with DMS")
    print("  - Monthly performance reports")
    print()

    print("Ready for PROMPT 26?")
    print()

    return True


if __name__ == '__main__':
    success = test_dealership_portal()
    sys.exit(0 if success else 1)
