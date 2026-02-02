"""
Test Tech App - Complete workflow test

Tests:
1. Link demo user to technician record
2. Create test job assigned to tech
3. Test tech API endpoints:
   - Dashboard
   - Jobs list
   - Start job
   - Update progress
   - Upload photo (simulated)
   - Time tracking (clock in/out)
   - Complete job
   - Gas station mode (create lead)

Usage:
    python scripts/test_tech_app.py
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crm.models.database import Database
from src.crm.managers.tech_manager import TechManager
from src.crm.managers.time_tracking_manager import TimeTrackingManager


def print_header(text):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)


def print_test(name, passed, details=""):
    """Print test result"""
    status = "PASS" if passed else "FAIL"
    symbol = "+" if passed else "x"
    print(f"  [{symbol}] {name}: {status} {details}")
    return passed


def test_tech_app(db_path: str = "data/hailtracker_crm.db"):
    """
    Test the complete Tech App workflow.
    """
    print_header("TECH APP WORKFLOW TEST")
    print(f"Database: {db_path}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    total_tests = 0
    passed_tests = 0

    db = Database(db_path)
    tech_manager = TechManager(db)
    time_manager = TimeTrackingManager(db)

    # ========================================================================
    # 1. Setup - Find or create technician for john@demo.com
    # ========================================================================
    print_header("1. Setup - Link Demo User to Technician")

    tech_id = None
    user_id = None
    org_id = None

    try:
        # Find the demo tech user
        users = db.execute("""
            SELECT u.id, u.email, u.organization_id, r.name as role
            FROM users_new u
            JOIN roles r ON r.id = u.role_id
            WHERE u.email = 'john@demo.com'
        """)

        if users:
            user = users[0]
            user_id = user['id']
            org_id = user['organization_id']
            total_tests += 1
            passed_tests += print_test("Find demo tech user", True, f"ID: {user_id}, Role: {user['role']}")
        else:
            print("  [!] Demo user john@demo.com not found - creating...")
            # We'll continue without user linkage

        # Find or create technician record
        tech = tech_manager.get_tech_by_email('john@demo.com')

        if tech:
            tech_id = tech['id']
            total_tests += 1
            passed_tests += print_test("Find existing technician", True, f"ID: {tech_id}")
        else:
            # Try to find any existing tech we can use
            existing_techs = db.execute("""
                SELECT * FROM technicians WHERE deleted_at IS NULL AND status = 'ACTIVE' LIMIT 1
            """)
            if existing_techs:
                tech_id = existing_techs[0]['id']
                # Update email to match demo user
                db.execute("UPDATE technicians SET email = 'john@demo.com' WHERE id = ?", (tech_id,))
                total_tests += 1
                passed_tests += print_test("Use existing technician", True, f"ID: {tech_id}")
            else:
                # Create technician record
                if not org_id:
                    org_id = 2  # Default demo org

                import uuid
                unique_emp_id = f"TECH-{uuid.uuid4().hex[:8].upper()}"

                tech_id = db.insert('technicians', {
                    'organization_id': org_id,
                    'first_name': 'John',
                    'last_name': 'Tech',
                    'email': 'john@demo.com',
                    'phone': '555-0104',
                    'employee_id': unique_emp_id,
                    'skill_level': 'EXPERT',
                    'status': 'ACTIVE',
                    'max_jobs_concurrent': 3,
                    'current_job_count': 0,
                    'pay_type': 'HOURLY',
                    'pay_rate': 35.00
                })
                total_tests += 1
                passed_tests += print_test("Create technician record", True, f"ID: {tech_id}")

        # Link user to technician if both exist
        if user_id and tech_id:
            tech_manager.link_user_to_technician(user_id, tech_id)
            total_tests += 1
            passed_tests += print_test("Link user to technician", True)

    except Exception as e:
        total_tests += 3
        print_test("Setup", False, str(e))
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # 2. Create Test Job Assigned to Tech
    # ========================================================================
    print_header("2. Create Test Job for Tech")

    job_id = None
    customer_id = None
    vehicle_id = None

    try:
        # Get or create org_id
        if not org_id:
            tech_data = db.execute("SELECT organization_id FROM technicians WHERE id = ?", (tech_id,))
            org_id = tech_data[0]['organization_id'] if tech_data else 2

        # Create a test customer
        customer_id = db.insert('customers', {
            'organization_id': org_id,
            'first_name': 'Test',
            'last_name': 'Customer',
            'phone': '555-9999',
            'email': 'test@example.com'
        })
        total_tests += 1
        passed_tests += print_test("Create test customer", True, f"ID: {customer_id}")

        # Create a test vehicle
        vehicle_id = db.insert('vehicles', {
            'organization_id': org_id,
            'customer_id': customer_id,
            'year': 2023,
            'make': 'Toyota',
            'model': 'Camry',
            'color': 'Silver',
            'vin': 'TEST123456789'
        })
        total_tests += 1
        passed_tests += print_test("Create test vehicle", True, f"ID: {vehicle_id}")

        # Create a test job assigned to tech
        job_number = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        job_id = db.insert('jobs', {
            'organization_id': org_id,
            'job_number': job_number,
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'assigned_tech_id': tech_id,
            'status': 'ASSIGNED_TO_TECH',
            'priority': 'NORMAL',
            'estimated_hours': 4.0,
            'internal_notes': 'Test job created by test script'
        })
        total_tests += 1
        passed_tests += print_test("Create test job", True, f"ID: {job_id}, Number: {job_number}")

    except Exception as e:
        total_tests += 3
        print_test("Create test data", False, str(e))
        import traceback
        traceback.print_exc()

    # ========================================================================
    # 3. Test TechManager - Get Dashboard
    # ========================================================================
    print_header("3. Test TechManager - Dashboard")

    try:
        dashboard = tech_manager.get_tech_dashboard(tech_id)
        total_tests += 1
        has_dashboard = dashboard is not None and 'tech' in dashboard
        passed_tests += print_test("Get tech dashboard", has_dashboard)

        if has_dashboard:
            print(f"      Tech: {dashboard['tech'].get('first_name')} {dashboard['tech'].get('last_name')}")
            print(f"      Active jobs: {dashboard['stats'].get('jobs_active', 0)}")
            print(f"      Current jobs: {len(dashboard.get('current_jobs', []))}")
            print(f"      Upcoming jobs: {len(dashboard.get('upcoming_jobs', []))}")

    except Exception as e:
        total_tests += 1
        print_test("Get dashboard", False, str(e))

    # ========================================================================
    # 4. Test TechManager - Get Jobs
    # ========================================================================
    print_header("4. Test TechManager - Get Jobs")

    try:
        # Get upcoming jobs (should include our test job)
        upcoming = tech_manager.get_tech_jobs(tech_id, 'UPCOMING')
        total_tests += 1
        has_upcoming = any(j['id'] == job_id for j in upcoming)
        passed_tests += print_test("Get upcoming jobs", has_upcoming, f"{len(upcoming)} jobs")

        # Get job details
        job_details = tech_manager.get_job_details(job_id, tech_id)
        total_tests += 1
        has_details = job_details is not None
        passed_tests += print_test("Get job details", has_details)

        if has_details:
            print(f"      Job: {job_details.get('job_number')}")
            print(f"      Vehicle: {job_details.get('vehicle_description')}")
            print(f"      Customer: {job_details.get('customer_name')}")

    except Exception as e:
        total_tests += 2
        print_test("Get jobs", False, str(e))

    # ========================================================================
    # 5. Test Time Tracking - Clock In
    # ========================================================================
    print_header("5. Test Time Tracking - Clock In")

    try:
        # Clock in
        clock_in_result = time_manager.clock_in(tech_id, notes="Starting test day")
        total_tests += 1
        passed_tests += print_test("Clock in", clock_in_result.get('success', False),
                                  clock_in_result.get('message', ''))

        # Check status
        status = time_manager.get_current_status(tech_id)
        total_tests += 1
        passed_tests += print_test("Status is clocked_in", status == 'clocked_in', f"Status: {status}")

        # Get today's time
        today = time_manager.get_today(tech_id)
        total_tests += 1
        passed_tests += print_test("Get today's time", today.get('clock_in_time') is not None)

    except Exception as e:
        total_tests += 3
        print_test("Time tracking", False, str(e))

    # ========================================================================
    # 6. Test TechManager - Start Job
    # ========================================================================
    print_header("6. Test TechManager - Start Job")

    try:
        result = tech_manager.start_job(job_id, tech_id)
        total_tests += 1
        passed_tests += print_test("Start job", result)

        # Verify status changed
        job_details = tech_manager.get_job_details(job_id, tech_id)
        total_tests += 1
        job_in_progress = job_details and job_details.get('status') == 'IN_PROGRESS'
        passed_tests += print_test("Job status is IN_PROGRESS", job_in_progress)

        # Check current jobs
        current = tech_manager.get_tech_jobs(tech_id, 'CURRENT')
        total_tests += 1
        in_current = any(j['id'] == job_id for j in current)
        passed_tests += print_test("Job in current list", in_current, f"{len(current)} current jobs")

    except Exception as e:
        total_tests += 3
        print_test("Start job", False, str(e))

    # ========================================================================
    # 7. Test TechManager - Update Progress
    # ========================================================================
    print_header("7. Test TechManager - Update Progress")

    try:
        result = tech_manager.update_progress(
            job_id, tech_id,
            progress_note="Completed hood and roof. Working on doors.",
            hours_remaining=2.5
        )
        total_tests += 1
        passed_tests += print_test("Update progress", result)

        # Verify notes saved
        job_details = tech_manager.get_job_details(job_id, tech_id)
        total_tests += 1
        has_notes = job_details and 'Completed hood' in (job_details.get('tech_notes') or '')
        passed_tests += print_test("Progress notes saved", has_notes)

    except Exception as e:
        total_tests += 2
        print_test("Update progress", False, str(e))

    # ========================================================================
    # 8. Test Time Tracking - Log Job Time
    # ========================================================================
    print_header("8. Test Time Tracking - Log Job Time")

    try:
        result = time_manager.log_job_time(
            tech_id, job_id,
            hours=1.5,
            description="Hood and roof work"
        )
        total_tests += 1
        passed_tests += print_test("Log job time", result.get('success', False))

        # Get time for job
        job_time = time_manager.get_time_for_job(job_id)
        total_tests += 1
        has_time = job_time.get('total_hours', 0) > 0
        passed_tests += print_test("Job has logged time", has_time, f"{job_time.get('total_hours', 0)}h")

    except Exception as e:
        total_tests += 2
        print_test("Log job time", False, str(e))

    # ========================================================================
    # 9. Test Time Tracking - Break
    # ========================================================================
    print_header("9. Test Time Tracking - Break")

    try:
        # Start break
        break_start = time_manager.start_break(tech_id)
        total_tests += 1
        passed_tests += print_test("Start break", break_start.get('success', False))

        # Check status
        status = time_manager.get_current_status(tech_id)
        total_tests += 1
        passed_tests += print_test("Status is on_break", status == 'on_break', f"Status: {status}")

        # End break
        break_end = time_manager.end_break(tech_id)
        total_tests += 1
        passed_tests += print_test("End break", break_end.get('success', False))

    except Exception as e:
        total_tests += 3
        print_test("Break management", False, str(e))

    # ========================================================================
    # 10. Test TechManager - Complete Job
    # ========================================================================
    print_header("10. Test TechManager - Complete Job")

    try:
        result = tech_manager.mark_complete(
            job_id, tech_id,
            completion_notes="All panels repaired. Ready for QC."
        )
        total_tests += 1
        passed_tests += print_test("Mark job complete", result)

        # Verify status
        job_details = tech_manager.get_job_details(job_id, tech_id)
        total_tests += 1
        job_complete = job_details and job_details.get('status') == 'TECH_COMPLETE'
        passed_tests += print_test("Job status is TECH_COMPLETE", job_complete)

        # Check completed jobs list
        completed = tech_manager.get_tech_jobs(tech_id, 'COMPLETED')
        total_tests += 1
        in_completed = any(j['id'] == job_id for j in completed)
        passed_tests += print_test("Job in completed list", in_completed)

    except Exception as e:
        total_tests += 3
        print_test("Complete job", False, str(e))

    # ========================================================================
    # 11. Test Time Tracking - Clock Out
    # ========================================================================
    print_header("11. Test Time Tracking - Clock Out")

    try:
        result = time_manager.clock_out(tech_id, notes="End of test day")
        total_tests += 1
        passed_tests += print_test("Clock out", result.get('success', False),
                                  f"Total: {result.get('total_hours', 0)}h")

        # Check status
        status = time_manager.get_current_status(tech_id)
        total_tests += 1
        passed_tests += print_test("Status is clocked_out", status == 'clocked_out')

        # Get week summary
        week = time_manager.get_week_summary(tech_id)
        total_tests += 1
        passed_tests += print_test("Get week summary", week.get('total_hours', 0) >= 0,
                                  f"Week total: {week.get('total_hours', 0)}h")

    except Exception as e:
        total_tests += 3
        print_test("Clock out", False, str(e))

    # ========================================================================
    # 12. Test Gas Station Mode - Create Lead
    # ========================================================================
    print_header("12. Test Gas Station Mode - Create Lead")

    try:
        lead_id = db.insert('leads', {
            'organization_id': org_id,
            'source': 'TECH_WALKIN',
            'first_name': 'Walk',
            'last_name': 'Up',
            'phone': '555-LEAD',
            'vehicle_year': 2022,
            'vehicle_make': 'Ford',
            'vehicle_model': 'F-150',
            'notes': f'Met at gas station, hail damage on hood. Created by tech #{tech_id}',
            'status': 'NEW'
        })
        total_tests += 1
        passed_tests += print_test("Create walk-up lead", lead_id is not None, f"ID: {lead_id}")

        # Verify lead created
        lead = db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
        total_tests += 1
        lead_exists = lead and lead[0]['source'] == 'TECH_WALKIN'
        passed_tests += print_test("Lead has correct source", lead_exists)

    except Exception as e:
        total_tests += 2
        print_test("Gas station mode", False, str(e))

    # ========================================================================
    # 13. Test Tech Stats
    # ========================================================================
    print_header("13. Test Tech Stats")

    try:
        stats = tech_manager.get_tech_stats(tech_id, period_days=30)
        total_tests += 1
        passed_tests += print_test("Get tech stats", stats is not None)

        if stats:
            print(f"      Jobs completed (30d): {stats.get('jobs_completed', 0)}")
            print(f"      Jobs active: {stats.get('jobs_active', 0)}")
            print(f"      Week completed: {stats.get('week_completed', 0)}")
            print(f"      Total hours: {stats.get('total_hours', 0)}")

    except Exception as e:
        total_tests += 1
        print_test("Get stats", False, str(e))

    # ========================================================================
    # Summary
    # ========================================================================
    print_header("TEST SUMMARY")

    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Pass Rate: {(passed_tests/total_tests*100):.1f}%")

    if passed_tests == total_tests:
        print("\n[OK] ALL TESTS PASSED!")
        return True
    else:
        print(f"\n[WARN] {total_tests - passed_tests} test(s) failed")
        return False


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/hailtracker_crm.db"
    success = test_tech_app(db_path)
    sys.exit(0 if success else 1)
