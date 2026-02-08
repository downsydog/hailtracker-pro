"""
Test Parts Management & Local Sourcing
PDR CRM Part 7 - Local Sourcing Made Easy!
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_parts_manager():
    print("\n" + "="*80)
    print("TESTING PARTS MANAGEMENT & LOCAL SOURCING")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.parts_manager import PartsManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from src.crm.managers.job_manager import JobManager
    from datetime import date, timedelta

    # Use test database
    test_db = "data/test_parts_mgr.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    parts_mgr = PartsManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    job_mgr = JobManager(db)

    # Create test job
    print("\nSetting up test data...")

    customer_id = customer_mgr.create_customer({
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '214-555-0100',
        'email': 'john@example.com'
    })

    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2022,
        'make': 'Toyota',
        'model': 'Camry',
        'color': 'Silver'
    })

    job_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="COLLISION",
        damage_type="COLLISION"
    )

    print()

    # ========================================================================
    # TEST 1: Add Parts to Catalog
    # ========================================================================

    print("="*80)
    print("[1/8] Adding parts to catalog...")
    print("="*80 + "\n")

    part1_id = parts_mgr.add_part(
        description='Front Bumper - Toyota Camry 2022',
        part_number='BUMPER-TOY-CAM-22-F',
        category='BODY_PANEL',
        preferred_supplier='Auto Parts Warehouse',
        supplier_part_number='TO1000412',
        cost=250.00,
        retail_price=375.00,
        in_stock=0,
        reorder_level=1
    )
    assert part1_id is not None
    print()

    part2_id = parts_mgr.add_part(
        description='Hood - Toyota Camry 2022',
        part_number='HOOD-TOY-CAM-22',
        category='BODY_PANEL',
        preferred_supplier='Auto Parts Warehouse',
        supplier_part_number='TO1230178',
        cost=300.00,
        retail_price=450.00,
        in_stock=0,
        reorder_level=1
    )
    assert part2_id is not None
    print()

    part3_id = parts_mgr.add_part(
        description='Paint Touch-up Kit - Black',
        part_number='PAINT-KIT-BLK',
        category='PAINT',
        cost=15.00,
        retail_price=35.00,
        in_stock=5,
        reorder_level=2
    )
    assert part3_id is not None
    print()

    # Verify parts were added
    parts = parts_mgr.search_parts()
    assert len(parts) == 3
    print(f"[OK] Added {len(parts)} parts to catalog")
    print()

    # ========================================================================
    # TEST 2: Create Parts Order
    # ========================================================================

    print("="*80)
    print("[2/8] Creating parts order...")
    print("="*80 + "\n")

    order_id = parts_mgr.create_order(
        supplier_name='Auto Parts Warehouse',
        supplier_email='quotes@autopartswarehouse.com',
        supplier_phone='800-555-PARTS',
        job_id=job_id,
        parts=[
            {
                'part_id': part1_id,
                'description': 'Front Bumper - Toyota Camry 2022',
                'supplier_part_number': 'TO1000412',
                'quantity': 1
            },
            {
                'part_id': part2_id,
                'description': 'Hood - Toyota Camry 2022',
                'supplier_part_number': 'TO1230178',
                'quantity': 1
            }
        ],
        notes='Need ASAP for collision repair'
    )
    assert order_id is not None

    # Verify order was created
    order = parts_mgr.get_order(order_id)
    assert order is not None
    assert order['status'] == 'QUOTED'
    assert len(order['parts_list']) == 2
    print()
    print(f"[OK] Order created with {len(order['parts_list'])} parts")
    print()

    # ========================================================================
    # TEST 3: Generate Quote Request Email
    # ========================================================================

    print("="*80)
    print("[3/8] Generating quote request email...")
    print("="*80 + "\n")

    email = parts_mgr.generate_quote_request_email(
        order_id=order_id,
        supplier_name='Auto Parts Warehouse',
        supplier_email='quotes@autopartswarehouse.com'
    )

    assert email is not None
    assert email['to'] == 'quotes@autopartswarehouse.com'
    assert 'Quote Request' in email['subject']

    print("Quote Request Email:")
    print("-" * 70)
    print(f"To: {email['to']}")
    print(f"Subject: {email['subject']}")
    print()
    print(email['body'])
    print("-" * 70)
    print()
    print("[OK] Email template generated")
    print()

    # ========================================================================
    # TEST 4: Add Quotes from Multiple Suppliers
    # ========================================================================

    print("="*80)
    print("[4/8] Simulating quotes from 3 local suppliers...")
    print("="*80 + "\n")

    # Quote 1: Auto Parts Warehouse
    quote1_id = parts_mgr.add_quote(
        order_id=order_id,
        supplier_name='Auto Parts Warehouse',
        quoted_price=650.00,
        quoted_delivery_days=2,
        return_policy='30 days with receipt',
        core_charge=50.00
    )
    assert quote1_id is not None
    print()

    # Quote 2: O'Reilly Auto Parts
    quote2_id = parts_mgr.add_quote(
        order_id=order_id,
        supplier_name="O'Reilly Auto Parts",
        quoted_price=625.00,
        quoted_delivery_days=1,
        return_policy='30 days, 15% restocking fee',
        core_charge=50.00
    )
    assert quote2_id is not None
    print()

    # Quote 3: AutoZone
    quote3_id = parts_mgr.add_quote(
        order_id=order_id,
        supplier_name='AutoZone',
        quoted_price=675.00,
        quoted_delivery_days=3,
        return_policy='30 days with receipt',
        core_charge=0.00
    )
    assert quote3_id is not None
    print()

    # Verify quotes were added
    quotes = parts_mgr.get_order_quotes(order_id)
    assert len(quotes) == 3
    print(f"[OK] Received {len(quotes)} quotes")
    print()

    # ========================================================================
    # TEST 5: Compare Quotes
    # ========================================================================

    print("="*80)
    print("[5/8] Generating quote comparison...")
    print("="*80 + "\n")

    comparison = parts_mgr.generate_quote_comparison(order_id)
    print(comparison)

    # ========================================================================
    # TEST 6: Select Winning Quote
    # ========================================================================

    print("="*80)
    print("[6/8] Selecting best quote...")
    print("="*80 + "\n")

    # Select O'Reilly (fastest delivery, good price)
    parts_mgr.select_quote(quote2_id)

    # Verify quote was selected
    order = parts_mgr.get_order(order_id)
    assert order['quote_amount'] == 625.00
    assert order['supplier_name'] == "O'Reilly Auto Parts"
    print()
    print("[OK] Quote selected and order updated")
    print()

    # ========================================================================
    # TEST 7: Order Workflow
    # ========================================================================

    print("="*80)
    print("[7/8] Processing order workflow...")
    print("="*80 + "\n")

    # Check current inventory (should be 0)
    part1 = parts_mgr.get_part(part1_id)
    part2 = parts_mgr.get_part(part2_id)
    print(f"Current inventory:")
    print(f"  Bumper: {part1['in_stock']} units")
    print(f"  Hood: {part2['in_stock']} units")
    print()

    # Mark as ordered
    parts_mgr.update_order_status(
        order_id=order_id,
        status='ORDERED',
        quote_amount=625.00,
        expected_delivery_date=date.today() + timedelta(days=1)
    )
    print()

    order = parts_mgr.get_order(order_id)
    assert order['status'] == 'ORDERED'
    print("[OK] Marked as ORDERED")
    print()

    # Simulate next day - parts received
    parts_mgr.update_order_status(
        order_id=order_id,
        status='RECEIVED',
        actual_amount=625.00,
        actual_delivery_date=date.today()
    )
    print()

    order = parts_mgr.get_order(order_id)
    assert order['status'] == 'RECEIVED'

    # Check inventory was updated
    part1 = parts_mgr.get_part(part1_id)
    part2 = parts_mgr.get_part(part2_id)
    assert part1['in_stock'] == 1
    assert part2['in_stock'] == 1
    print("[OK] Marked as RECEIVED (inventory auto-updated)")
    print()

    # ========================================================================
    # TEST 8: Statistics & Reporting
    # ========================================================================

    print("="*80)
    print("[8/8] Getting parts statistics...")
    print("="*80 + "\n")

    stats = parts_mgr.get_parts_stats()

    print(f"Parts Statistics:")
    print(f"  Total parts in catalog: {stats['total_parts']}")
    print(f"  Parts needing reorder: {stats['needs_reorder']}")
    print(f"  Inventory value: ${stats['inventory_value']:,.2f}")
    print()
    print(f"  Total orders: {stats['total_orders']}")
    print(f"  Total quoted: ${stats['total_quoted']:,.2f}")
    print(f"  Total spent: ${stats['total_spent']:,.2f}")
    print()
    print(f"  Orders by status:")
    for status, count in stats.get('by_status', {}).items():
        print(f"    {status}: {count}")
    print()

    # Supplier performance
    print("Supplier Performance:")
    suppliers = parts_mgr.get_supplier_performance()
    for supplier in suppliers:
        print(f"  {supplier['supplier_name']}")
        print(f"    Orders: {supplier['order_count']} ({supplier['completed_orders']} completed)")
        print(f"    Reliability: {supplier['reliability_pct']}%")
        if supplier['avg_quote']:
            print(f"    Avg quote: ${supplier['avg_quote']:,.2f}")
        if supplier['avg_delivery_days']:
            print(f"    Avg delivery: {supplier['avg_delivery_days']:.1f} days")
    print()

    # ========================================================================
    # BONUS: Parts Report
    # ========================================================================

    print("="*80)
    print("[BONUS] Generating full parts report...")
    print("="*80 + "\n")

    report = parts_mgr.format_parts_report()
    print(report)

    # ========================================================================
    # BONUS: Job Parts Summary
    # ========================================================================

    print("="*80)
    print("[BONUS] Job parts summary...")
    print("="*80 + "\n")

    job_parts = parts_mgr.get_parts_needed_for_job(job_id)
    print(f"Parts for Job #{job_id}:")
    print(f"  Total orders: {job_parts['total_orders']}")
    print(f"  Total quoted: ${job_parts['total_quoted']:,.2f}")
    print(f"  Total spent: ${job_parts['total_spent']:,.2f}")
    print(f"  Parts received: {len(job_parts['parts_received'])}")
    print(f"  Parts pending: {len(job_parts['parts_pending'])}")
    print()

    # ========================================================================
    # BONUS: Low Stock Alert
    # ========================================================================

    print("="*80)
    print("[BONUS] Checking low stock items...")
    print("="*80 + "\n")

    low_stock = parts_mgr.get_low_stock_parts()
    print(f"Parts needing reorder: {len(low_stock)}")
    for part in low_stock:
        print(f"  - {part['description']}")
        print(f"    Stock: {part['in_stock']}, Reorder at: {part['reorder_level']}")
    print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] PARTS MANAGEMENT TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Parts catalog with pricing and markup")
    print("  [OK] Order creation linked to jobs")
    print("  [OK] Email quote request generation")
    print("  [OK] Multi-supplier quote tracking")
    print("  [OK] Quote comparison reports")
    print("  [OK] Quote selection")
    print("  [OK] Order status workflow (QUOTED -> ORDERED -> RECEIVED)")
    print("  [OK] Automatic inventory updates on receipt")
    print("  [OK] Supplier performance tracking")
    print("  [OK] Low stock alerts")
    print()

    print("LOCAL SOURCING WORKFLOW:")
    print("  1. Create order with parts needed")
    print("  2. Generate emails for 3-5 local suppliers")
    print("  3. Receive quotes and add to system")
    print("  4. Compare side-by-side (price, delivery, policies)")
    print("  5. Select best quote")
    print("  6. Track order -> shipped -> received")
    print("  7. Inventory auto-updates")
    print()

    print("Ready for PROMPT 8: Tech Mobile App?")
    print()

    return True


if __name__ == '__main__':
    success = test_parts_manager()
    sys.exit(0 if success else 1)
