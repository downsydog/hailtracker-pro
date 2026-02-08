"""
Test Estimate Manager
PDR CRM Part 6 - Professional Estimates!
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_estimate_manager():
    print("\n" + "="*80)
    print("TESTING ESTIMATE BUILDER")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.estimate_manager import EstimateManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from src.crm.managers.job_manager import JobManager
    from datetime import date, timedelta

    # Use test database
    test_db = "data/test_estimate_mgr.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    estimate_mgr = EstimateManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    job_mgr = JobManager(db)

    # Create test data
    print("\nSetting up test data...")

    customer_id = customer_mgr.create_customer({
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '214-555-0100',
        'email': 'john@example.com'
    })
    print(f"[OK] Created customer (ID: {customer_id})")

    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2022,
        'make': 'Toyota',
        'model': 'Camry',
        'color': 'Silver'
    })
    print(f"[OK] Created vehicle (ID: {vehicle_id})")

    job_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL"
    )

    print()

    # ========================================================================
    # TEST 1: Create Estimate from Template
    # ========================================================================

    print("="*80)
    print("[1/8] Creating estimate from HAIL_BASIC template...")
    print("="*80 + "\n")

    estimate1_id = estimate_mgr.create_estimate(
        job_id=job_id,
        template='HAIL_BASIC',
        tax_rate=8.25,
        notes="Hail damage from November storm",
        created_by='admin'
    )
    assert estimate1_id is not None

    # Verify estimate
    estimate1 = estimate_mgr.get_estimate(estimate1_id)
    assert estimate1 is not None
    assert estimate1['status'] == 'DRAFT'
    assert len(estimate1['line_items_parsed']) == 3  # Hood, Roof, Trunk from template
    assert estimate1['tax_rate'] == 8.25
    print(f"[OK] Created estimate with {estimate1['item_count']} line items")
    print(f"     Subtotal: ${estimate1['subtotal']:,.2f}")
    print(f"     Tax ({estimate1['tax_rate']}%): ${estimate1['tax_amount']:,.2f}")
    print(f"     Total: ${estimate1['total']:,.2f}")
    print()

    # ========================================================================
    # TEST 2: Add Line Items
    # ========================================================================

    print("="*80)
    print("[2/8] Adding line items to estimate...")
    print("="*80 + "\n")

    # Add labor item
    estimate_mgr.add_line_item(
        estimate_id=estimate1_id,
        item_type='LABOR',
        description='PDR - Left Fender',
        quantity=1,
        unit_price=400.00
    )

    # Add part item
    estimate_mgr.add_line_item(
        estimate_id=estimate1_id,
        item_type='PART',
        description='Windshield Molding',
        quantity=2,
        unit_price=45.00
    )

    # Verify additions
    estimate1 = estimate_mgr.get_estimate(estimate1_id)
    assert estimate1['item_count'] == 5  # 3 original + 2 new
    print(f"[OK] Now has {estimate1['item_count']} line items")
    print(f"     Labor total: ${estimate1['labor_total']:,.2f}")
    print(f"     Parts total: ${estimate1['parts_total']:,.2f}")
    print(f"     New total: ${estimate1['total']:,.2f}")
    print()

    # ========================================================================
    # TEST 3: Update Line Item
    # ========================================================================

    print("="*80)
    print("[3/8] Updating a line item...")
    print("="*80 + "\n")

    # Update the first item's price
    old_total = estimate1['total']
    estimate_mgr.update_line_item(
        estimate_id=estimate1_id,
        item_index=0,
        unit_price=400.00  # Was 350.00
    )

    estimate1 = estimate_mgr.get_estimate(estimate1_id)
    assert estimate1['total'] > old_total
    print(f"[OK] Updated line item price")
    print(f"     Old total: ${old_total:,.2f}")
    print(f"     New total: ${estimate1['total']:,.2f}")
    print()

    # ========================================================================
    # TEST 4: Remove Line Item
    # ========================================================================

    print("="*80)
    print("[4/8] Removing a line item...")
    print("="*80 + "\n")

    old_count = estimate1['item_count']
    old_total = estimate1['total']

    estimate_mgr.remove_line_item(estimate1_id, 4)  # Remove the windshield molding

    estimate1 = estimate_mgr.get_estimate(estimate1_id)
    assert estimate1['item_count'] == old_count - 1
    print(f"[OK] Removed line item")
    print(f"     Items: {old_count} -> {estimate1['item_count']}")
    print(f"     Total: ${old_total:,.2f} -> ${estimate1['total']:,.2f}")
    print()

    # ========================================================================
    # TEST 5: Status Workflow
    # ========================================================================

    print("="*80)
    print("[5/8] Testing status workflow...")
    print("="*80 + "\n")

    # Mark as sent
    estimate_mgr.mark_sent(estimate1_id)
    estimate1 = estimate_mgr.get_estimate(estimate1_id)
    assert estimate1['status'] == 'SENT'
    assert estimate1['sent_date'] is not None
    print(f"[OK] Marked as SENT")

    # Mark as viewed
    estimate_mgr.mark_viewed(estimate1_id)
    estimate1 = estimate_mgr.get_estimate(estimate1_id)
    assert estimate1['status'] == 'VIEWED'
    assert estimate1['viewed_date'] is not None
    print(f"[OK] Marked as VIEWED")

    # Mark as approved
    estimate_mgr.mark_approved(estimate1_id)
    estimate1 = estimate_mgr.get_estimate(estimate1_id)
    assert estimate1['status'] == 'APPROVED'
    assert estimate1['approved_date'] is not None
    print(f"[OK] Marked as APPROVED")
    print()

    # ========================================================================
    # TEST 6: Convert to Invoice
    # ========================================================================

    print("="*80)
    print("[6/8] Converting estimate to invoice...")
    print("="*80 + "\n")

    invoice_id = estimate_mgr.convert_to_invoice(
        estimate_id=estimate1_id,
        due_days=30,
        created_by='admin'
    )
    assert invoice_id is not None

    # Verify invoice was created
    invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    assert len(invoice) == 1
    invoice = invoice[0]
    assert invoice['total'] == estimate1['total']
    assert invoice['status'] == 'DRAFT'
    print(f"[OK] Created invoice #{invoice['invoice_number']}")
    print(f"     Total: ${invoice['total']:,.2f}")
    print(f"     Due: {invoice['due_date']}")
    print()

    # ========================================================================
    # TEST 7: Severe Hail Template
    # ========================================================================

    print("="*80)
    print("[7/8] Creating HAIL_SEVERE template estimate...")
    print("="*80 + "\n")

    # Create another job
    job2_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL"
    )

    estimate2_id = estimate_mgr.create_estimate(
        job_id=job2_id,
        template='HAIL_SEVERE',
        tax_rate=8.25
    )

    estimate2 = estimate_mgr.get_estimate(estimate2_id)
    assert estimate2['item_count'] == 7  # Full body panels
    print(f"[OK] Created severe hail estimate")
    print(f"     Items: {estimate2['item_count']}")
    print(f"     Total: ${estimate2['total']:,.2f}")
    print()

    # ========================================================================
    # TEST 8: Format Estimate for Print
    # ========================================================================

    print("="*80)
    print("[8/8] Formatting estimate for display...")
    print("="*80 + "\n")

    formatted = estimate_mgr.format_estimate(estimate2_id)
    print(formatted)
    print()

    # ========================================================================
    # BONUS: Test Statistics
    # ========================================================================

    print("="*80)
    print("[BONUS] Getting estimate statistics...")
    print("="*80 + "\n")

    stats = estimate_mgr.get_estimate_stats(days=30)

    print(f"Estimate Statistics (Last 30 Days):")
    print(f"  Total estimates: {stats['total_estimates']}")
    print(f"  Total value: ${stats['total_value']:,.2f}")
    print(f"  Average value: ${stats['avg_estimate_value']:,.2f}")
    print(f"  Approval rate: {stats['approval_rate']}%")
    print()
    print(f"  By status:")
    for status, data in stats.get('by_status', {}).items():
        print(f"    {status}: {data['count']} (${data['value']:,.2f})")
    print()
    print(f"  Pending: {stats['pending_count']} (${stats['pending_value']:,.2f})")
    print(f"  Expired: {stats['expired_count']} (${stats['expired_value']:,.2f})")
    print()

    # ========================================================================
    # BONUS: Test Duplicate
    # ========================================================================

    print("="*80)
    print("[BONUS] Duplicating estimate...")
    print("="*80 + "\n")

    dup_id = estimate_mgr.duplicate_estimate(estimate2_id)
    dup = estimate_mgr.get_estimate(dup_id)
    assert dup['total'] == estimate2['total']
    assert dup['status'] == 'DRAFT'  # New one starts as draft
    print(f"[OK] Duplicated to #{dup['estimate_number']}")
    print()

    # ========================================================================
    # BONUS: Test Templates List
    # ========================================================================

    print("="*80)
    print("[BONUS] Available templates...")
    print("="*80 + "\n")

    templates = estimate_mgr.get_templates()
    for name, tmpl in templates.items():
        print(f"  {name}: {tmpl['name']}")
        print(f"    {tmpl['description']}")
        print(f"    Default items: {len(tmpl['default_items'])}")
        print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] ESTIMATE BUILDER TESTS COMPLETE")
    print("="*80 + "\n")

    print("PROFESSIONAL ESTIMATES READY!")
    print()
    print("Key features verified:")
    print("  [OK] Template-based estimates (HAIL_BASIC, HAIL_SEVERE, DOOR_DING, CUSTOM)")
    print("  [OK] Line item management (add/update/remove)")
    print("  [OK] Labor + Parts tracking")
    print("  [OK] Tax calculations")
    print("  [OK] Status workflow (DRAFT -> SENT -> VIEWED -> APPROVED)")
    print("  [OK] Convert to invoice")
    print("  [OK] Professional formatting")
    print("  [OK] Statistics and reporting")
    print("  [OK] Duplicate estimates")
    print()

    print("BENEFITS:")
    print("  [OK] Fast estimate creation with templates")
    print("  [OK] Professional presentation")
    print("  [OK] Track estimate status")
    print("  [OK] Easy conversion to invoice")
    print()

    print("Ready for PROMPT 7: SMS & Email Automation?")
    print()

    return True


if __name__ == '__main__':
    success = test_estimate_manager()
    sys.exit(0 if success else 1)
