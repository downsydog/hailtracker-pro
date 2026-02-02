"""
Test Scheduling System

Tests:
1. Scheduling settings management
2. Technician schedule management
3. Time-off management
4. Self-scheduling tokens
5. Appointment booking via token
6. Availability calculation
7. Reminder tracking

Usage:
    python scripts/test_scheduling.py [database_path]
"""

import os
import sys
from datetime import datetime, timedelta
import json
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.auth.auth_manager import AuthManager
from src.core.models.tenant_schema import init_tenant_schema
from src.crm.models.schema import DatabaseSchema
from src.crm.models.scheduling_schema import SchedulingSchema
from src.crm.models.database import Database
from src.crm.managers.scheduling_manager import SchedulingManager
from scripts.seed_rbac import seed_rbac
from scripts.migrate_add_org_id import migrate_database


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


def print_subtest(name, passed, details=""):
    """Print sub-test result"""
    status = "PASS" if passed else "FAIL"
    symbol = "+" if passed else "x"
    print(f"      [{symbol}] {name}: {status} {details}")
    return passed


def test_scheduling(db_path: str = "data/test_scheduling.db"):
    """
    Comprehensive test of the Scheduling System.
    """
    print_header("SCHEDULING SYSTEM TEST")
    print(f"Database: {db_path}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Remove test database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing test database")

    total_tests = 0
    passed_tests = 0

    # ========================================================================
    # 1. Setup - Create Schema and Seed Data
    # ========================================================================
    print_header("1. Setting Up Test Environment")

    try:
        # Create CRM schema
        DatabaseSchema.create_all_tables(db_path)
        total_tests += 1
        passed_tests += print_test("Create CRM schema", True)

        # Create tenant schema
        init_tenant_schema(db_path)
        total_tests += 1
        passed_tests += print_test("Create tenant schema", True)

        # Create scheduling schema
        import sqlite3
        conn = sqlite3.connect(db_path)
        SchedulingSchema.create_scheduling_tables(conn)
        conn.close()
        total_tests += 1
        passed_tests += print_test("Create scheduling schema", True)

        # Seed RBAC data
        seed_rbac(db_path)
        total_tests += 1
        passed_tests += print_test("Seed RBAC data", True)

        # Run migration
        migrate_database(db_path)
        total_tests += 1
        passed_tests += print_test("Migrate add organization_id", True)

    except Exception as e:
        total_tests += 5
        print_test("Setup", False, str(e))
        print("\n[FATAL] Cannot continue without basic setup")
        return False

    # ========================================================================
    # 2. Create Test Account, Organization, and Technician
    # ========================================================================
    print_header("2. Creating Test Data")

    auth_manager = AuthManager(db_path)
    org_id = None
    tech_id = None
    customer_id = None

    try:
        # Create account (returns account_id, organization_id, user_id)
        result = auth_manager.create_account(
            name="Test PDR Shop",
            owner_email="owner@testpdr.com",
            owner_password="TestPassword123!"
        )
        account_id = result['account_id']
        org_id = result['organization_id']
        total_tests += 1
        passed_tests += print_test("Create account", True, f"Account: {account_id}, Org: {org_id}")

        # Create a technician
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO technicians (organization_id, first_name, last_name, email, phone, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (org_id, "John", "Tech", "john@test.com", "555-1234", "ACTIVE"))
        tech_id = cursor.lastrowid
        conn.commit()
        total_tests += 1
        passed_tests += print_test("Create technician", True, f"ID: {tech_id}")

        # Create a customer
        cursor.execute("""
            INSERT INTO customers (organization_id, first_name, last_name, email, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (org_id, "Jane", "Customer", "jane@test.com", "555-5678"))
        customer_id = cursor.lastrowid
        conn.commit()
        total_tests += 1
        passed_tests += print_test("Create customer", True, f"ID: {customer_id}")

        conn.close()

    except Exception as e:
        total_tests += 3
        print_test("Create test data", False, str(e))
        import traceback
        traceback.print_exc()
        return False

    # ========================================================================
    # 3. Test Scheduling Settings
    # ========================================================================
    print_header("3. Testing Scheduling Settings")

    # SchedulingManager takes a Database wrapper instance
    db = Database(db_path)
    manager = SchedulingManager(db)

    try:
        # Create default settings
        conn = sqlite3.connect(db_path)
        SchedulingSchema.create_default_settings(conn, org_id)
        conn.commit()
        conn.close()
        total_tests += 1
        passed_tests += print_test("Create default settings", True)

        # Get settings
        settings = manager.get_scheduling_settings(org_id)
        total_tests += 1
        has_settings = settings is not None and 'business_hours' in settings
        passed_tests += print_test("Get scheduling settings", has_settings)

        if has_settings:
            print(f"      Business hours: {type(settings['business_hours'])}")
            print(f"      Default slot duration: {settings.get('default_slot_duration')} min")

        # Update settings
        update_result = manager.update_scheduling_settings(org_id, {
            'default_slot_duration': 90,
            'min_notice_hours': 48,
            'max_advance_days': 14
        })
        total_tests += 1
        passed_tests += print_test("Update scheduling settings", update_result)

        # Verify update
        settings = manager.get_scheduling_settings(org_id)
        total_tests += 1
        update_verified = settings.get('default_slot_duration') == 90
        passed_tests += print_test("Verify settings update", update_verified)

    except Exception as e:
        total_tests += 4
        print_test("Scheduling settings", False, str(e))

    # ========================================================================
    # 4. Test Technician Schedule Management
    # ========================================================================
    print_header("4. Testing Technician Schedule Management")

    try:
        # Create default schedule for technician
        conn = sqlite3.connect(db_path)
        SchedulingSchema.create_default_tech_schedule(conn, org_id, tech_id)
        conn.commit()
        conn.close()
        total_tests += 1
        passed_tests += print_test("Create default tech schedule", True)

        # Get technician schedule
        tech_schedule = manager.get_technician_schedule(tech_id)
        total_tests += 1
        has_schedule = len(tech_schedule) == 7  # 7 days
        passed_tests += print_test("Get technician schedule", has_schedule, f"{len(tech_schedule)} days")

        # Update technician schedule (make Friday shorter)
        new_schedule = [
            {"day_of_week": 5, "is_available": True, "start_time": "08:00", "end_time": "14:00"}
        ]
        update_result = manager.set_technician_schedule(org_id, tech_id, new_schedule)
        total_tests += 1
        passed_tests += print_test("Update technician schedule", update_result)

        # Verify schedule update
        tech_schedule = manager.get_technician_schedule(tech_id)
        friday = next((d for d in tech_schedule if d['day_of_week'] == 5), None)
        total_tests += 1
        friday_updated = friday and friday.get('end_time') == '14:00'
        passed_tests += print_test("Verify schedule update", friday_updated)

    except Exception as e:
        total_tests += 4
        print_test("Technician schedule", False, str(e))

    # ========================================================================
    # 5. Test Time Off Management
    # ========================================================================
    print_header("5. Testing Time Off Management")

    time_off_id = None

    try:
        # Add time off
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        time_off_id = manager.add_time_off(
            organization_id=org_id,
            technician_id=tech_id,
            start_date=next_week,
            end_date=next_week,
            reason="vacation",
            notes="Family trip"
        )
        total_tests += 1
        passed_tests += print_test("Add time off", time_off_id is not None, f"ID: {time_off_id}")

        # Get technician time off
        time_off_list = manager.get_technician_time_off(tech_id)
        total_tests += 1
        has_time_off = len(time_off_list) > 0
        passed_tests += print_test("Get time off list", has_time_off, f"{len(time_off_list)} entries")

        # Check if tech is on time off
        is_off = manager.is_tech_on_time_off(tech_id, next_week)
        total_tests += 1
        passed_tests += print_test("Check is_tech_on_time_off", is_off)

        # Remove time off
        if time_off_id:
            remove_result = manager.remove_time_off(time_off_id)
            total_tests += 1
            passed_tests += print_test("Remove time off", remove_result)

    except Exception as e:
        total_tests += 4
        print_test("Time off management", False, str(e))

    # ========================================================================
    # 6. Test Self-Scheduling Tokens
    # ========================================================================
    print_header("6. Testing Self-Scheduling Tokens")

    token = None

    try:
        # Create scheduling token
        token = manager.create_scheduling_token(
            organization_id=org_id,
            customer_id=customer_id,
            appointment_type="DROP_OFF",
            expires_days=7,
            max_uses=1,
            created_by=1
        )
        total_tests += 1
        passed_tests += print_test("Create scheduling token", token is not None, f"Token: {token[:20]}...")

        # Validate token
        token_info = manager.validate_token(token)
        total_tests += 1
        token_valid = token_info is not None and token_info.get('customer_id') == customer_id
        passed_tests += print_test("Validate token", token_valid)

        if token_info:
            print(f"      Customer ID: {token_info.get('customer_id')}")
            print(f"      Appointment type: {token_info.get('appointment_type')}")
            print(f"      Expires: {token_info.get('expires_at')}")

        # Test invalid token
        invalid_info = manager.validate_token("invalid-token-12345")
        total_tests += 1
        passed_tests += print_test("Reject invalid token", invalid_info is None)

    except Exception as e:
        total_tests += 3
        print_test("Self-scheduling tokens", False, str(e))

    # ========================================================================
    # 7. Test Available Dates/Slots
    # ========================================================================
    print_header("7. Testing Availability Calculation")

    try:
        # Get available dates for self-scheduling
        available_dates = manager.get_available_dates_for_self_scheduling(
            organization_id=org_id,
            days=14,
            appointment_type='DROP_OFF'
        )
        total_tests += 1
        has_dates = isinstance(available_dates, list)
        passed_tests += print_test("Get available dates", has_dates, f"{len(available_dates)} dates")

        if available_dates:
            print(f"      First available: {available_dates[0].get('date') if available_dates else 'None'}")

        # Get available slots for a specific date
        tomorrow = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        available_slots = manager.get_available_slots_for_self_scheduling(
            organization_id=org_id,
            target_date=tomorrow,
            appointment_type='DROP_OFF'
        )
        total_tests += 1
        has_slots = isinstance(available_slots, list)
        passed_tests += print_test("Get available slots", has_slots, f"{len(available_slots)} slots")

        if available_slots:
            print(f"      First slot: {available_slots[0].get('time') if available_slots else 'None'}")

    except Exception as e:
        total_tests += 2
        print_test("Availability calculation", False, str(e))

    # ========================================================================
    # 8. Test Booking via Token
    # ========================================================================
    print_header("8. Testing Booking via Token")

    try:
        if token:
            # Book appointment via token
            tomorrow = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
            booking_result = manager.book_via_token(
                token=token,
                appointment_date=tomorrow,
                start_time="09:00",
                customer_info=None  # Already linked to customer
            )
            total_tests += 1
            booking_success = booking_result.get('success', False)
            passed_tests += print_test("Book via token", booking_success)

            if booking_success:
                print(f"      Appointment ID: {booking_result.get('appointment_id')}")

            # Try to reuse token (should fail - max_uses=1)
            second_booking = manager.book_via_token(
                token=token,
                appointment_date=tomorrow,
                start_time="10:00"
            )
            total_tests += 1
            reuse_blocked = not second_booking.get('success', True)
            passed_tests += print_test("Block token reuse", reuse_blocked)
        else:
            total_tests += 2
            print_test("Book via token", False, "No token available")

    except Exception as e:
        total_tests += 2
        print_test("Booking via token", False, str(e))

    # ========================================================================
    # 9. Test Schedule Overview
    # ========================================================================
    print_header("9. Testing Schedule Overview")

    try:
        overview = manager.get_schedule_overview(org_id)
        total_tests += 1
        has_overview = overview is not None
        passed_tests += print_test("Get schedule overview", has_overview)

        if has_overview:
            print(f"      Today's count: {overview.get('today_count', 0)}")
            print(f"      Week count: {overview.get('week_count', 0)}")
            print(f"      Date: {overview.get('date')}")

    except Exception as e:
        total_tests += 1
        print_test("Schedule overview", False, str(e))

    # ========================================================================
    # 10. Test Appointment Reminders
    # ========================================================================
    print_header("10. Testing Reminder Management")

    try:
        # Get appointments needing 24h reminder
        appointments_24h = manager.get_appointments_needing_reminder('24h')
        total_tests += 1
        passed_tests += print_test("Get 24h reminders", isinstance(appointments_24h, list))

        # Get appointments needing 2h reminder
        appointments_2h = manager.get_appointments_needing_reminder('2h')
        total_tests += 1
        passed_tests += print_test("Get 2h reminders", isinstance(appointments_2h, list))

    except Exception as e:
        total_tests += 2
        print_test("Reminder management", False, str(e))

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
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/test_scheduling.db"
    success = test_scheduling(db_path)
    sys.exit(0 if success else 1)
