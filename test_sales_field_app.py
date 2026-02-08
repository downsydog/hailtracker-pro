"""
Test Sales Territory & Field Sales Managers
PDR CRM Part 31 - Sales Team Field App & Swath Management
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_sales_field_app():
    print("\n" + "="*80)
    print("TESTING SALES TERRITORY & FIELD SALES MANAGERS")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.sales_territory_manager import SalesTerritoryManager
    from src.crm.managers.field_sales_manager import FieldSalesManager

    # Use test database
    test_db = "data/test_sales_field_app.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    territory_mgr = SalesTerritoryManager(db)
    field_mgr = FieldSalesManager(db)

    print("  Tables created for territory and field sales management")
    print()

    # ==================== TEST 1: Create Salesperson ====================
    print("Test 1: Create Salesperson")
    salesperson_id = territory_mgr.create_salesperson(
        first_name="Mike",
        last_name="Johnson",
        email="mike.johnson@pdrpro.com",
        phone="555-0001",
        hire_date=date(2024, 1, 15),
        commission_rate=0.15,
        notes="Top performer"
    )
    assert salesperson_id > 0
    print(f"  - Created salesperson ID: {salesperson_id}")

    # Create second salesperson
    salesperson2_id = territory_mgr.create_salesperson(
        first_name="Sarah",
        last_name="Williams",
        email="sarah.williams@pdrpro.com",
        phone="555-0002",
        commission_rate=0.12
    )
    print(f"  - Created second salesperson ID: {salesperson2_id}")
    print("  PASSED\n")

    # ==================== TEST 2: Get Salesperson ====================
    print("Test 2: Get Salesperson")
    salesperson = territory_mgr.get_salesperson(salesperson_id)
    assert salesperson is not None
    assert salesperson['first_name'] == "Mike"
    assert salesperson['last_name'] == "Johnson"
    print(f"  - Retrieved: {salesperson['first_name']} {salesperson['last_name']}")

    active = territory_mgr.get_active_salespeople()
    assert len(active) == 2
    print(f"  - Active salespeople: {len(active)}")
    print("  PASSED\n")

    # ==================== TEST 3: Create Hail Swath ====================
    print("Test 3: Create Hail Swath")
    swath_id = territory_mgr.create_hail_swath(
        swath_name="Dallas Hail Event - Nov 15 2024",
        center_lat=32.7767,
        center_lon=-96.7970,
        radius_miles=5.0,
        hail_date=date(2024, 11, 15),
        severity="HIGH",
        estimated_homes=12000,
        notes="2-inch hail reported"
    )
    assert swath_id > 0
    print(f"  - Created swath ID: {swath_id}")

    swath = territory_mgr.get_hail_swath(swath_id)
    assert swath is not None
    assert swath['swath_name'] == "Dallas Hail Event - Nov 15 2024"
    print(f"  - Swath name: {swath['swath_name']}")
    print(f"  - Radius: {swath['radius_miles']} miles")
    print(f"  - Estimated homes: {swath['estimated_homes']}")
    print("  PASSED\n")

    # ==================== TEST 4: Generate Sales Grid ====================
    print("Test 4: Generate Sales Grid")
    cells_created = territory_mgr.generate_sales_grid(swath_id, grid_size_miles=0.5)
    assert cells_created > 0
    print(f"  - Grid cells created: {cells_created}")

    cells = territory_mgr.get_grid_cells(swath_id)
    print(f"  - Retrieved {len(cells)} cells")
    print(f"  - First cell: #{cells[0]['cell_number']} at ({cells[0]['center_lat']:.4f}, {cells[0]['center_lon']:.4f})")
    print("  PASSED\n")

    # ==================== TEST 5: Get Available Cells ====================
    print("Test 5: Get Available Cells")
    available = territory_mgr.get_available_cells(swath_id)
    assert len(available) == cells_created
    print(f"  - Available cells: {len(available)}")
    print("  PASSED\n")

    # ==================== TEST 6: Assign Territory ====================
    print("Test 6: Assign Territory")
    # Assign first 10 cells to Mike
    cell_ids = [c['id'] for c in available[:10]]
    assignment_id = territory_mgr.assign_territory(
        salesperson_id=salesperson_id,
        grid_cell_ids=cell_ids,
        assigned_date=date.today()
    )
    assert assignment_id > 0
    print(f"  - Assignment ID: {assignment_id}")
    print(f"  - Assigned {len(cell_ids)} cells to Mike")

    # Verify assignment
    mike_territory = territory_mgr.get_salesperson_territory(salesperson_id)
    assert len(mike_territory) == 10
    print(f"  - Mike's territory: {len(mike_territory)} cells")

    # Check available cells reduced
    available_after = territory_mgr.get_available_cells(swath_id)
    assert len(available_after) == cells_created - 10
    print(f"  - Remaining available: {len(available_after)}")
    print("  PASSED\n")

    # ==================== TEST 7: Mark Cell Canvassed ====================
    print("Test 7: Mark Cell Canvassed")
    cell_to_canvass = mike_territory[0]['id']
    result = territory_mgr.mark_cell_canvassed(
        cell_id=cell_to_canvass,
        salesperson_id=salesperson_id,
        homes_visited=45,
        leads_generated=3,
        notes="Good area, many interested homeowners"
    )
    assert result is True
    print(f"  - Cell {cell_to_canvass} marked as canvassed")

    cell = territory_mgr.get_grid_cell(cell_to_canvass)
    assert cell['status'] == 'CANVASSED'
    assert cell['homes_visited'] == 45
    print(f"  - Homes visited: {cell['homes_visited']}")
    print(f"  - Leads generated: {cell['leads_generated']}")
    print("  PASSED\n")

    # ==================== TEST 8: Coverage Statistics ====================
    print("Test 8: Coverage Statistics")
    coverage = territory_mgr.get_coverage_stats(swath_id)
    assert coverage['total_cells'] == cells_created
    assert coverage['canvassed'] == 1
    print(f"  - Total cells: {coverage['total_cells']}")
    print(f"  - Assigned: {coverage['assigned']}")
    print(f"  - Canvassed: {coverage['canvassed']}")
    print(f"  - Coverage: {coverage['coverage_percent']}%")
    print(f"  - Homes visited: {coverage['homes_visited']}")
    print(f"  - Leads generated: {coverage['leads_generated']}")
    print("  PASSED\n")

    # ==================== TEST 9: Create Field Lead ====================
    print("Test 9: Create Field Lead")
    lead_id = territory_mgr.create_field_lead(
        salesperson_id=salesperson_id,
        customer_info={
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '555-1234',
            'email': 'john.doe@example.com',
            'address': '123 Main St, Dallas, TX 75201'
        },
        location_lat=32.7767,
        location_lon=-96.7970,
        grid_cell_id=cell_to_canvass,
        vehicle_info={
            'year': 2022,
            'make': 'Toyota',
            'model': 'Camry',
            'color': 'Silver'
        },
        insurance_info={
            'company': 'State Farm',
            'policy_number': 'POL123456',
            'deductible': 500.00
        },
        damage_assessment={
            'severity': 'MODERATE',
            'affected_panels': ['hood', 'roof'],
            'estimated_cost': 1500.00,
            'estimated_dents': 30
        },
        lead_quality='HOT',
        notes="Very interested, wants to schedule ASAP"
    )
    assert lead_id > 0
    print(f"  - Created lead ID: {lead_id}")

    lead = territory_mgr.get_field_lead(lead_id)
    assert lead is not None
    assert lead['customer_info']['first_name'] == 'John'
    print(f"  - Customer: {lead['customer_info']['first_name']} {lead['customer_info']['last_name']}")
    print(f"  - Quality: {lead['lead_quality']}")
    print("  PASSED\n")

    # ==================== TEST 10: Update Lead Status ====================
    print("Test 10: Update Lead Status")
    result = territory_mgr.update_lead_status(lead_id, 'CONTACTED', 'Scheduled for estimate')
    assert result is True

    lead = territory_mgr.get_field_lead(lead_id)
    assert lead['status'] == 'CONTACTED'
    print(f"  - Lead status updated to: {lead['status']}")
    print("  PASSED\n")

    # ==================== TEST 11: Check In ====================
    print("Test 11: Check In (Field Sales)")
    session_id = field_mgr.check_in(
        salesperson_id=salesperson_id,
        location_lat=32.7767,
        location_lon=-96.7970,
        notes="Starting morning shift"
    )
    assert session_id > 0
    print(f"  - Session ID: {session_id}")

    session = field_mgr.get_session(session_id)
    assert session is not None
    assert session['status'] == 'ACTIVE'
    print(f"  - Check-in time: {session['check_in_time'][:19]}")
    print("  PASSED\n")

    # ==================== TEST 12: Active Session ====================
    print("Test 12: Get Active Session")
    active_session = field_mgr.get_active_session(salesperson_id)
    assert active_session is not None
    assert active_session['id'] == session_id
    print(f"  - Active session found: {active_session['id']}")
    print("  PASSED\n")

    # ==================== TEST 13: Log Location ====================
    print("Test 13: Log Location")
    location_id = field_mgr.log_location(
        salesperson_id=salesperson_id,
        latitude=32.7800,
        longitude=-96.8000,
        accuracy_meters=5.0,
        activity_type='CANVASSING'
    )
    assert location_id > 0
    print(f"  - Location logged: {location_id}")

    current_loc = field_mgr.get_salesperson_location(salesperson_id)
    assert current_loc is not None
    print(f"  - Current location: ({current_loc['latitude']}, {current_loc['longitude']})")
    print("  PASSED\n")

    # ==================== TEST 14: Log Customer Interaction ====================
    print("Test 14: Log Customer Interaction")
    interaction_id = field_mgr.log_customer_interaction(
        salesperson_id=salesperson_id,
        interaction_type='CONVERSATION',
        location_lat=32.7800,
        location_lon=-96.8000,
        outcome='SUCCESS',
        customer_name='Jane Smith',
        customer_phone='555-5678',
        customer_address='456 Oak Ave, Dallas, TX',
        notes='Interested in estimate'
    )
    assert interaction_id > 0
    print(f"  - Interaction ID: {interaction_id}")

    interactions = field_mgr.get_interactions_today(salesperson_id)
    assert len(interactions) >= 1
    print(f"  - Today's interactions: {len(interactions)}")
    print("  PASSED\n")

    # ==================== TEST 15: Quick Lead Capture ====================
    print("Test 15: Quick Lead Capture")
    quick_lead_id = field_mgr.quick_lead_capture(
        salesperson_id=salesperson_id,
        name="Robert Brown",
        phone="555-9999",
        address="789 Elm St, Dallas, TX",
        latitude=32.7850,
        longitude=-96.7950
    )
    assert quick_lead_id > 0
    print(f"  - Quick lead ID: {quick_lead_id}")
    print("  PASSED\n")

    # ==================== TEST 16: Check Out ====================
    print("Test 16: Check Out")
    result = field_mgr.check_out(
        session_id=session_id,
        location_lat=32.7800,
        location_lon=-96.8000,
        daily_summary={
            'doors_knocked': 45,
            'conversations': 28,
            'leads_generated': 5,
            'appointments_set': 2,
            'miles_driven': 15.2
        },
        notes="Great day in the field!"
    )
    assert result is True

    session = field_mgr.get_session(session_id)
    assert session['status'] == 'COMPLETED'
    assert session['daily_summary']['doors_knocked'] == 45
    print(f"  - Session completed")
    print(f"  - Doors knocked: {session['daily_summary']['doors_knocked']}")
    print(f"  - Leads generated: {session['daily_summary']['leads_generated']}")
    print("  PASSED\n")

    # ==================== TEST 17: Today's Assignment ====================
    print("Test 17: Today's Assignment")
    # Check in again for today's assignment test
    new_session = field_mgr.check_in(salesperson_id, 32.7767, -96.7970)

    assignment = field_mgr.get_today_assignment(salesperson_id)
    assert assignment['checked_in'] is True
    assert assignment['territory_count'] > 0
    print(f"  - Checked in: {assignment['checked_in']}")
    print(f"  - Territory cells: {assignment['territory_count']}")
    print(f"  - Today's leads: {assignment['today_stats']['leads_generated']}")
    print("  PASSED\n")

    # ==================== TEST 18: Salesperson Performance ====================
    print("Test 18: Salesperson Performance")
    start = date.today() - timedelta(days=30)
    end = date.today()

    perf = field_mgr.get_salesperson_performance(salesperson_id, start, end)
    assert perf is not None
    assert perf['name'] == "Mike Johnson"
    print(f"  - Name: {perf['name']}")
    print(f"  - Days worked: {perf['period']['days_worked']}")
    print(f"  - Doors knocked: {perf['activity']['doors_knocked']}")
    print(f"  - Leads generated: {perf['leads']['total_generated']}")
    print("  PASSED\n")

    # ==================== TEST 19: Team Leaderboard ====================
    print("Test 19: Team Leaderboard")
    leaderboard = field_mgr.get_team_leaderboard(start, end, metric='LEADS')
    assert len(leaderboard) >= 1
    print(f"  - Leaderboard entries: {len(leaderboard)}")
    for entry in leaderboard[:3]:
        print(f"    #{entry['rank']} {entry['name']}: {entry['score']} leads")
    print("  PASSED\n")

    # ==================== TEST 20: Calculate Commission ====================
    print("Test 20: Calculate Commission")
    # First need to create a job and invoice for the lead
    # Create customer
    customer_result = db.execute("""
        INSERT INTO customers (first_name, last_name, phone, email, source)
        VALUES ('Test', 'Customer', '555-0000', 'test@test.com', 'FIELD_SALES')
    """)
    customer_id = customer_result[0]['id']

    # Create vehicle
    vehicle_result = db.execute("""
        INSERT INTO vehicles (customer_id, year, make, model)
        VALUES (?, 2022, 'Test', 'Vehicle')
    """, [customer_id])
    vehicle_id = vehicle_result[0]['id']

    # Create job
    job_result = db.execute("""
        INSERT INTO jobs (job_number, customer_id, vehicle_id, status, job_type)
        VALUES ('JOB-TEST-001', ?, ?, 'COMPLETED', 'HAIL')
    """, [customer_id, vehicle_id])
    job_id = job_result[0]['id']

    # Create invoice
    invoice_result = db.execute("""
        INSERT INTO invoices (invoice_number, job_id, customer_id, invoice_date, total, status)
        VALUES ('INV-TEST-001', ?, ?, ?, 1500.00, 'PAID')
    """, [job_id, customer_id, date.today().isoformat()])
    invoice_id = invoice_result[0]['id']

    # Calculate commission
    commission_id = field_mgr.calculate_commission(
        salesperson_id=salesperson_id,
        lead_id=lead_id,
        job_id=job_id,
        invoice_id=invoice_id,
        invoice_total=1500.00
    )
    assert commission_id > 0
    print(f"  - Commission ID: {commission_id}")

    # Get pending commissions
    pending = field_mgr.get_pending_commissions(salesperson_id)
    assert len(pending) >= 1
    print(f"  - Pending commissions: {len(pending)}")
    print(f"  - Commission amount: ${pending[0]['commission_amount']:.2f}")
    print("  PASSED\n")

    # ==================== TEST 21: Mark Commission Paid ====================
    print("Test 21: Mark Commission Paid")
    result = field_mgr.mark_commission_paid(commission_id, "CHK-12345")
    assert result is True

    # Verify no longer pending
    pending = field_mgr.get_pending_commissions(salesperson_id)
    unpaid = [p for p in pending if p['id'] == commission_id]
    assert len(unpaid) == 0
    print(f"  - Commission marked as paid")
    print("  PASSED\n")

    # ==================== TEST 22: Commission Summary ====================
    print("Test 22: Commission Summary")
    summary = field_mgr.get_commission_summary(salesperson_id, start, end)
    assert summary['total_commissions'] >= 1
    print(f"  - Total commissions: {summary['total_commissions']}")
    print(f"  - Total sales: ${summary['total_sales']:.2f}")
    print(f"  - Total commission: ${summary['total_commission']:.2f}")
    print(f"  - Paid: ${summary['paid']:.2f}")
    print("  PASSED\n")

    # ==================== TEST 23: Convert Lead to Customer ====================
    print("Test 23: Convert Lead to Customer")
    # Create a new lead to convert
    convert_lead_id = territory_mgr.create_field_lead(
        salesperson_id=salesperson_id,
        customer_info={
            'first_name': 'Convert',
            'last_name': 'Test',
            'phone': '555-9876',
            'address': '999 Convert St'
        },
        location_lat=32.78,
        location_lon=-96.80,
        vehicle_info={'year': 2023, 'make': 'Honda', 'model': 'Accord'},
        damage_assessment={'estimated_dents': 25, 'estimated_cost': 1200}
    )

    customer_id, job_id = territory_mgr.convert_lead_to_customer(convert_lead_id)
    assert customer_id > 0
    assert job_id > 0
    print(f"  - Created customer ID: {customer_id}")
    print(f"  - Created job ID: {job_id}")

    # Verify lead status updated
    converted_lead = territory_mgr.get_field_lead(convert_lead_id)
    assert converted_lead['status'] == 'CONVERTED'
    print(f"  - Lead status: {converted_lead['status']}")
    print("  PASSED\n")

    # ==================== TEST 24: Swath Summary ====================
    print("Test 24: Swath Summary")
    summary = territory_mgr.get_swath_summary(swath_id)
    assert summary['swath'] is not None
    assert summary['coverage']['total_cells'] > 0
    print(f"  - Swath: {summary['swath']['swath_name']}")
    print(f"  - Total cells: {summary['coverage']['total_cells']}")
    print(f"  - Coverage: {summary['coverage']['coverage_percent']}%")
    print(f"  - Total leads: {summary['leads']['total']}")
    print(f"  - Salespeople assigned: {summary['salesperson_count']}")
    print("  PASSED\n")

    # ==================== TEST 25: Nearby Leads ====================
    print("Test 25: Nearby Leads")
    nearby = field_mgr.get_nearby_leads(32.78, -96.80, radius_miles=1.0)
    print(f"  - Leads found nearby: {len(nearby)}")
    for lead in nearby[:3]:
        customer = lead.get('customer_info', {})
        print(f"    - {customer.get('first_name', 'N/A')} {customer.get('last_name', '')}")
    print("  PASSED\n")

    # ==================== TEST 26: Salesperson Coverage ====================
    print("Test 26: Salesperson Coverage")
    coverage = territory_mgr.get_salesperson_coverage(salesperson_id)
    assert coverage['assigned_cells'] > 0
    print(f"  - Assigned cells: {coverage['assigned_cells']}")
    print(f"  - Completed cells: {coverage['completed_cells']}")
    print(f"  - Remaining: {coverage['remaining_cells']}")
    print(f"  - Completion: {coverage['completion_percent']}%")
    print("  PASSED\n")

    # ==================== TEST 27: All Active Locations ====================
    print("Test 27: All Active Locations")
    # Make sure there's an active session and log location
    field_mgr.log_location(salesperson_id, 32.7800, -96.8000, activity_type='CANVASSING')

    locations = field_mgr.get_all_active_locations()
    print(f"  - Active salespeople with locations: {len(locations)}")
    for loc in locations:
        print(f"    - {loc['name']}: ({loc['latitude']}, {loc['longitude']}) - {loc['activity_type']}")
    print("  PASSED\n")

    # ==================== TEST 28: Interaction Stats ====================
    print("Test 28: Interaction Stats")
    interaction_stats = field_mgr.get_interaction_stats(salesperson_id, start, end)
    print(f"  - Total interactions: {interaction_stats['total_interactions']}")
    print(f"  - Door knocks: {interaction_stats['door_knocks']}")
    print(f"  - Conversations: {interaction_stats['conversations']}")
    print(f"  - Conversation rate: {interaction_stats['conversation_rate']}%")
    print("  PASSED\n")

    # Final summary
    print("="*80)
    print("ALL TESTS PASSED - Sales Territory & Field Sales working correctly!")
    print("="*80)

    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)

    return True


if __name__ == '__main__':
    try:
        success = test_sales_field_app()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
