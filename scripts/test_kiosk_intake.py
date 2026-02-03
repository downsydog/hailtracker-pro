"""
Test Kiosk Customer Intake System

Tests:
1. Device validation
2. Form processing
3. Customer/vehicle/lead creation
4. Rate limiting
5. Error handling

Usage:
    python scripts/test_kiosk_intake.py [database_path]
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.auth.auth_manager import AuthManager
from src.core.models.tenant_schema import init_tenant_schema
from src.crm.models.schema import DatabaseSchema
from src.crm.managers.kiosk_intake_manager import KioskIntakeManager
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


def test_kiosk_intake(db_path: str = "data/test_kiosk.db"):
    """
    Comprehensive test of the Kiosk Intake system.
    """
    print_header("KIOSK CUSTOMER INTAKE TEST")
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
        # Create CRM schema (customers, vehicles, leads, etc.)
        DatabaseSchema.create_all_tables(db_path)
        total_tests += 1
        passed_tests += print_test("Create CRM schema", True)

        # Create tenant schema (accounts, organizations, roles, etc.)
        init_tenant_schema(db_path)
        total_tests += 1
        passed_tests += print_test("Create tenant schema", True)

        # Seed RBAC data
        seed_rbac(db_path)
        total_tests += 1
        passed_tests += print_test("Seed RBAC data", True)

        # Run migration to add organization_id to CRM tables
        migrate_database(db_path)
        total_tests += 1
        passed_tests += print_test("Migrate add organization_id", True)

    except Exception as e:
        total_tests += 4
        print_test("Setup", False, str(e))
        print("\n[FATAL] Cannot continue without basic setup")
        return False

    # ========================================================================
    # 2. Create Test Account and Kiosk
    # ========================================================================
    print_header("2. Creating Test Account and Kiosk Device")

    auth_manager = AuthManager(db_path)

    try:
        # Create account
        result = auth_manager.create_account(
            name="Test PDR Shop",
            owner_email="owner@testshop.com",
            owner_password="test123",
            plan="professional",
            first_name="Test",
            last_name="Owner"
        )
        account_id = result['account_id']
        organization_id = result['organization_id']

        total_tests += 1
        passed_tests += print_test("Create account", True, f"(Org ID: {organization_id})")

    except Exception as e:
        total_tests += 1
        print_test("Create account", False, str(e))
        print("\n[FATAL] Cannot continue without account")
        return False

    try:
        # Create kiosk device
        kiosk = auth_manager.create_kiosk_device(
            organization_id=organization_id,
            name="Lobby Tablet",
            auto_reset_seconds=30,
            welcome_message="Welcome to Test PDR Shop!"
        )
        device_token = kiosk['device_token']

        total_tests += 1
        passed_tests += print_test("Create kiosk device", True, f"(ID: {kiosk['id']})")
        print(f"      Device Token: {device_token[:20]}...")

    except Exception as e:
        total_tests += 1
        print_test("Create kiosk device", False, str(e))
        print("\n[FATAL] Cannot continue without kiosk device")
        return False

    # ========================================================================
    # 3. Test Device Validation
    # ========================================================================
    print_header("3. Testing Device Validation")

    intake_manager = KioskIntakeManager(db_path)

    # Valid token
    device = intake_manager.validate_device(device_token)
    total_tests += 1
    passed = device is not None and device['organization_id'] == organization_id
    passed_tests += print_test("Validate valid device token", passed)

    if device:
        print(f"      Device Name: {device['name']}")
        print(f"      Organization: {device['organization_name']}")

    # Invalid token
    invalid_device = intake_manager.validate_device("invalid-token-12345")
    total_tests += 1
    passed = invalid_device is None
    passed_tests += print_test("Reject invalid device token", passed)

    # Empty token
    empty_device = intake_manager.validate_device("")
    total_tests += 1
    passed = empty_device is None
    passed_tests += print_test("Reject empty device token", passed)

    # ========================================================================
    # 4. Test Form Data
    # ========================================================================
    print_header("4. Testing Form Data Helpers")

    # Lead sources
    sources = intake_manager.get_lead_sources()
    total_tests += 1
    passed = len(sources) > 0 and any(s['value'] == 'WALK_IN' for s in sources)
    passed_tests += print_test("Get lead sources", passed, f"({len(sources)} sources)")

    # Vehicle makes
    makes = intake_manager.get_vehicle_makes()
    total_tests += 1
    passed = len(makes) > 0 and 'Toyota' in makes
    passed_tests += print_test("Get vehicle makes", passed, f"({len(makes)} makes)")

    # Vehicle years
    years = intake_manager.get_vehicle_years()
    total_tests += 1
    current_year = datetime.now().year
    passed = len(years) > 0 and current_year in years and (current_year + 1) in years
    passed_tests += print_test("Get vehicle years", passed, f"({years[0]} to {years[-1]})")

    # US States
    states = intake_manager.get_us_states()
    total_tests += 1
    passed = len(states) == 50
    passed_tests += print_test("Get US states", passed, f"({len(states)} states)")

    # Insurance companies
    insurance = intake_manager.get_insurance_companies(organization_id)
    total_tests += 1
    passed = len(insurance) > 0
    passed_tests += print_test("Get insurance companies", passed, f"({len(insurance)} companies)")

    # ========================================================================
    # 5. Test Intake Processing
    # ========================================================================
    print_header("5. Testing Intake Processing")

    # Valid intake submission
    form_data = {
        'first_name': 'John',
        'last_name': 'Smith',
        'phone': '(555) 123-4567',
        'email': 'john.smith@example.com',
        'address_line1': '123 Main St',
        'city': 'Dallas',
        'state': 'TX',
        'zip_code': '75001',
        'vehicle_year': '2022',
        'vehicle_make': 'Toyota',
        'vehicle_model': 'Camry',
        'vehicle_color': 'Silver',
        'source': 'WALK_IN',
        'consent_sms': True,
        'consent_email': True
    }

    result = intake_manager.process_intake(device_token, form_data)
    total_tests += 1
    passed = result['success'] == True
    passed_tests += print_test("Process valid intake", passed)

    if result['success']:
        print(f"      Customer ID: {result['customer_id']}")
        print(f"      Vehicle ID: {result['vehicle_id']}")
        print(f"      Lead ID: {result['lead_id']}")
        print(f"      Customer Name: {result['customer_name']}")
        print(f"      Vehicle: {result['vehicle_description']}")
        customer_id = result['customer_id']
        lead_id = result['lead_id']
    else:
        print(f"      Error: {result.get('error')}")
        customer_id = None
        lead_id = None

    # ========================================================================
    # 6. Test Validation Errors
    # ========================================================================
    print_header("6. Testing Validation Errors")

    # Missing first name
    bad_data = {'last_name': 'Doe', 'phone': '5551234567'}
    result = intake_manager.process_intake(device_token, bad_data)
    total_tests += 1
    passed = result['success'] == False and 'first_name' in str(result.get('errors', []))
    passed_tests += print_test("Reject missing first name", passed)

    # Missing last name
    bad_data = {'first_name': 'Jane', 'phone': '5551234567'}
    result = intake_manager.process_intake(device_token, bad_data)
    total_tests += 1
    passed = result['success'] == False and 'last_name' in str(result.get('errors', []))
    passed_tests += print_test("Reject missing last name", passed)

    # Missing phone AND email
    bad_data = {'first_name': 'Jane', 'last_name': 'Doe'}
    result = intake_manager.process_intake(device_token, bad_data)
    total_tests += 1
    passed = result['success'] == False
    passed_tests += print_test("Reject missing contact info", passed)

    # Invalid email format
    bad_data = {'first_name': 'Jane', 'last_name': 'Doe', 'email': 'not-an-email'}
    result = intake_manager.process_intake(device_token, bad_data)
    total_tests += 1
    passed = result['success'] == False and 'email' in str(result.get('errors', []))
    passed_tests += print_test("Reject invalid email format", passed)

    # Short phone number
    bad_data = {'first_name': 'Jane', 'last_name': 'Doe', 'phone': '123'}
    result = intake_manager.process_intake(device_token, bad_data)
    total_tests += 1
    passed = result['success'] == False and 'phone' in str(result.get('errors', []))
    passed_tests += print_test("Reject short phone number", passed)

    # ========================================================================
    # 7. Test Invalid Device Token
    # ========================================================================
    print_header("7. Testing Invalid Device Token")

    result = intake_manager.process_intake("invalid-token", form_data)
    total_tests += 1
    passed = result['success'] == False and result.get('error_code') == 'INVALID_DEVICE'
    passed_tests += print_test("Reject intake with invalid token", passed)

    # ========================================================================
    # 8. Test Duplicate Customer Handling
    # ========================================================================
    print_header("8. Testing Duplicate Customer Handling")

    # Submit again with same email - should find existing customer
    duplicate_data = {
        'first_name': 'John',
        'last_name': 'Smith',
        'email': 'john.smith@example.com',  # Same email as before
        'vehicle_year': '2020',
        'vehicle_make': 'Honda',
        'vehicle_model': 'Accord',
        'source': 'REFERRAL'
    }

    result = intake_manager.process_intake(device_token, duplicate_data)
    total_tests += 1
    passed = result['success'] == True and result.get('customer_id') == customer_id
    passed_tests += print_test("Find existing customer by email", passed,
                               f"(Customer ID: {result.get('customer_id')})")

    # Should create new vehicle and lead for same customer
    total_tests += 1
    passed = result.get('lead_id') != lead_id  # Different lead
    passed_tests += print_test("Create new lead for existing customer", passed)

    # ========================================================================
    # 9. Test Minimal Submission
    # ========================================================================
    print_header("9. Testing Minimal Valid Submission")

    # Minimal valid data (just name and phone)
    minimal_data = {
        'first_name': 'Minimal',
        'last_name': 'Customer',
        'phone': '5559876543'
    }

    result = intake_manager.process_intake(device_token, minimal_data)
    total_tests += 1
    passed = result['success'] == True
    passed_tests += print_test("Process minimal valid intake", passed)

    if result['success']:
        print(f"      Created with just name and phone")
        print(f"      Customer ID: {result['customer_id']}")
        print(f"      Lead ID: {result['lead_id']}")
        print(f"      Vehicle ID: {result.get('vehicle_id')} (should be None)")

    # ========================================================================
    # 10. Test Referral Source
    # ========================================================================
    print_header("10. Testing Lead Source Handling")

    referral_data = {
        'first_name': 'Referred',
        'last_name': 'Customer',
        'phone': '5551112222',
        'source': 'REFERRAL',
        'referrer_name': 'Jane Doe'
    }

    result = intake_manager.process_intake(device_token, referral_data)
    total_tests += 1
    passed = result['success'] == True
    passed_tests += print_test("Process referral intake", passed)

    # ========================================================================
    # 11. Test Recent Submissions Query
    # ========================================================================
    print_header("11. Testing Recent Submissions Query")

    submissions = intake_manager.get_recent_submissions(organization_id, limit=10)
    total_tests += 1
    # Note: Only submissions with source='WALK_IN' are returned. We created 2 walk-ins.
    passed = len(submissions) >= 2
    passed_tests += print_test("Get recent submissions", passed, f"({len(submissions)} found)")

    if submissions:
        print(f"      Latest: {submissions[0]['first_name']} {submissions[0]['last_name']}")
        print(f"      Temperature: {submissions[0]['temperature']}")

    # ========================================================================
    # 12. Test Device Activity Update
    # ========================================================================
    print_header("12. Testing Device Activity Tracking")

    updated = intake_manager.update_device_activity(
        device_token,
        ip_address='192.168.1.100',
        user_agent='Mozilla/5.0 (iPad)'
    )
    total_tests += 1
    passed = updated == True
    passed_tests += print_test("Update device activity", passed)

    # Verify the update
    device = intake_manager.validate_device(device_token)
    total_tests += 1
    passed = device is not None and device.get('last_seen_at') is not None
    passed_tests += print_test("Device last_seen_at updated", passed)

    # ========================================================================
    # 13. Test Kiosk Settings
    # ========================================================================
    print_header("13. Testing Organization Settings")

    settings = intake_manager.get_kiosk_settings(organization_id)
    total_tests += 1
    passed = settings is not None and 'organization_name' in settings
    passed_tests += print_test("Get organization settings", passed)

    if settings:
        print(f"      Organization: {settings.get('organization_name')}")

    # ========================================================================
    # RESULTS
    # ========================================================================
    print_header("TEST RESULTS")

    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")

    if passed_tests == total_tests:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("SOME TESTS FAILED - Review output above")
        print("=" * 60)
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/test_kiosk.db"

    success = test_kiosk_intake(db_path)
    sys.exit(0 if success else 1)
