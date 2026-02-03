"""
Test the RBAC system end-to-end.
Creates accounts, users, tests permissions, sessions, and kiosks.

Usage:
    python scripts/test_rbac.py [database_path]
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.auth.auth_manager import AuthManager, SeatLimitExceeded
from src.core.models.tenant_schema import init_tenant_schema
from scripts.seed_rbac import seed_rbac


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


def test_rbac_system(db_path: str = "data/test_rbac.db"):
    """
    Comprehensive test of the RBAC system.
    Uses a separate test database to avoid affecting production data.
    """
    print_header("RBAC SYSTEM TEST")
    print(f"Database: {db_path}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Remove test database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing test database")

    total_tests = 0
    passed_tests = 0

    # ========================================================================
    # 1. Create Schema
    # ========================================================================
    print_header("1. Creating Schema")

    try:
        init_tenant_schema(db_path)
        total_tests += 1
        passed_tests += print_test("Create tenant schema", True)
    except Exception as e:
        total_tests += 1
        print_test("Create tenant schema", False, str(e))

    # ========================================================================
    # 2. Seed Roles and Permissions
    # ========================================================================
    print_header("2. Seeding Roles and Permissions")

    try:
        seed_rbac(db_path)
        total_tests += 1
        passed_tests += print_test("Seed RBAC data", True)
    except Exception as e:
        total_tests += 1
        print_test("Seed RBAC data", False, str(e))

    # ========================================================================
    # 3. Create Test Account
    # ========================================================================
    print_header("3. Creating Test Account")

    auth_manager = AuthManager(db_path)

    try:
        result = auth_manager.create_account(
            name="Test PDR Shop",
            owner_email="owner@testshop.com",
            owner_password="test123",
            plan="starter",
            first_name="John",
            last_name="Owner"
        )
        account_id = result['account_id']
        organization_id = result['organization_id']
        owner_user_id = result['user_id']

        total_tests += 1
        passed_tests += print_test("Create account", True, f"(ID: {account_id})")
        print(f"      Account ID: {account_id}")
        print(f"      Organization ID: {organization_id}")
        print(f"      Owner User ID: {owner_user_id}")

    except Exception as e:
        total_tests += 1
        print_test("Create account", False, str(e))
        print("\n[FATAL] Cannot continue without account")
        return

    # ========================================================================
    # 4. Check Seat Usage
    # ========================================================================
    print_header("4. Checking Seat Usage")

    seats = auth_manager.get_seat_usage(account_id)
    total_tests += 1
    passed = seats['max'] == 5 and seats['used'] == 1
    passed_tests += print_test("Initial seat usage", passed,
                               f"({seats['used']}/{seats['max']} used)")

    # ========================================================================
    # 5. Create Users with Different Roles
    # ========================================================================
    print_header("5. Creating Users with Different Roles")

    # Note: Starter plan has 5 seats. Owner takes 1, so we can create 4 more.
    roles_to_test = ['admin', 'office', 'sales', 'tech']  # 4 roles = 5 total with owner
    created_users = {}

    for role in roles_to_test:
        try:
            user_id = auth_manager.create_user(
                account_id=account_id,
                organization_id=organization_id,
                email=f"{role}@testshop.com",
                password="test123",
                role_name=role,
                first_name=role.capitalize(),
                last_name="User"
            )
            created_users[role] = user_id
            total_tests += 1
            passed_tests += print_test(f"Create {role} user", True, f"(ID: {user_id})")
        except Exception as e:
            total_tests += 1
            print_test(f"Create {role} user", False, str(e))

    # ========================================================================
    # 6. Check Seat Usage After Creating Users
    # ========================================================================
    print_header("6. Checking Seat Usage After User Creation")

    seats = auth_manager.get_seat_usage(account_id)
    expected_used = 5  # owner + 4 users = 5
    total_tests += 1
    passed = seats['used'] == expected_used
    passed_tests += print_test("Seat usage after users", passed,
                               f"({seats['used']}/{seats['max']} used)")

    # Check at_limit flag (5/5 = at limit)
    total_tests += 1
    passed = seats['at_limit'] == True
    passed_tests += print_test("At limit flag", passed)

    # ========================================================================
    # 7. Test Authentication
    # ========================================================================
    print_header("7. Testing Authentication")

    # Successful auth
    user = auth_manager.authenticate("office@testshop.com", "test123")
    total_tests += 1
    passed = user is not None and user['email'] == "office@testshop.com"
    passed_tests += print_test("Authenticate valid user", passed)

    if user:
        print(f"      Email: {user['email']}")
        print(f"      Role: {user['role']}")
        print(f"      Permissions: {len(user.get('permissions', []))} total")

    # Failed auth - wrong password
    user = auth_manager.authenticate("office@testshop.com", "wrongpassword")
    total_tests += 1
    passed = user is None
    passed_tests += print_test("Reject wrong password", passed)

    # Failed auth - non-existent user
    user = auth_manager.authenticate("nobody@testshop.com", "test123")
    total_tests += 1
    passed = user is None
    passed_tests += print_test("Reject non-existent user", passed)

    # ========================================================================
    # 8. Test Permissions
    # ========================================================================
    print_header("8. Testing Permissions")

    test_cases = [
        # (email, permission, expected_result)
        ("owner@testshop.com", "billing.manage", True),
        ("admin@testshop.com", "billing.manage", False),
        ("admin@testshop.com", "users.create", True),
        ("office@testshop.com", "users.create", False),
        ("office@testshop.com", "customers.create", True),
        ("sales@testshop.com", "customers.view_all", False),
        ("sales@testshop.com", "customers.view_own", True),
        ("sales@testshop.com", "hail.view_map", True),
        ("tech@testshop.com", "jobs.view_all", False),
        ("tech@testshop.com", "jobs.view_assigned", True),
        ("tech@testshop.com", "jobs.update_status", True),
        # Note: estimator not created in this test (at seat limit)
    ]

    for email, permission, expected in test_cases:
        user = auth_manager.authenticate(email, "test123")
        if user:
            has_perm = auth_manager.has_permission(user['id'], permission)
            total_tests += 1
            passed = has_perm == expected
            passed_tests += print_test(
                f"{email.split('@')[0]}: {permission}",
                passed,
                f"(got={has_perm}, expected={expected})"
            )
        else:
            total_tests += 1
            print_test(f"{email.split('@')[0]}: {permission}", False, "auth failed")

    # ========================================================================
    # 9. Create Kiosk Device
    # ========================================================================
    print_header("9. Creating Kiosk Device")

    try:
        kiosk = auth_manager.create_kiosk_device(
            organization_id=organization_id,
            name="Lobby Tablet",
            auto_reset_seconds=60,
            welcome_message="Welcome to Test PDR Shop!"
        )
        total_tests += 1
        passed_tests += print_test("Create kiosk", True, f"(ID: {kiosk['id']})")
        print(f"      Device Token: {kiosk['device_token'][:20]}...")
    except Exception as e:
        total_tests += 1
        print_test("Create kiosk", False, str(e))

    # ========================================================================
    # 10. Verify Kiosk Doesn't Count as Seat
    # ========================================================================
    print_header("10. Verifying Kiosk Seat Counting")

    seats = auth_manager.get_seat_usage(account_id)
    total_tests += 1
    passed = seats['used'] == 5  # Still 5, kiosk doesn't count as seat
    passed_tests += print_test("Kiosk doesn't count as seat", passed,
                               f"({seats['used']} seats used)")

    # ========================================================================
    # 11. Test Session Management
    # ========================================================================
    print_header("11. Testing Session Management")

    # Create session
    user = auth_manager.authenticate("office@testshop.com", "test123")
    if user:
        session_token = auth_manager.create_session(
            user_id=user['id'],
            context={'ip_address': '127.0.0.1', 'device_type': 'desktop'}
        )
        total_tests += 1
        passed = len(session_token) > 0
        passed_tests += print_test("Create session", passed)

        # Validate session
        session_data = auth_manager.validate_session(session_token)
        total_tests += 1
        passed = session_data is not None and session_data['user_id'] == user['id']
        passed_tests += print_test("Validate session", passed)

        # Revoke session
        revoked = auth_manager.revoke_session(session_token)
        total_tests += 1
        passed_tests += print_test("Revoke session", revoked)

        # Verify revoked session is invalid
        session_data = auth_manager.validate_session(session_token)
        total_tests += 1
        passed = session_data is None
        passed_tests += print_test("Revoked session rejected", passed)

    # ========================================================================
    # 12. Test Seat Limit Enforcement
    # ========================================================================
    print_header("12. Testing Seat Limit Enforcement")

    # Try to create user when at limit (should fail)
    try:
        auth_manager.create_user(
            account_id=account_id,
            organization_id=organization_id,
            email="extra@testshop.com",
            password="test123",
            role_name="office"
        )
        total_tests += 1
        print_test("Seat limit enforced", False, "User created when at limit")
    except SeatLimitExceeded as e:
        total_tests += 1
        passed_tests += print_test("Seat limit enforced", True)
        print(f"      Error: {str(e)[:50]}...")

    # Create kiosk (should succeed - doesn't count)
    try:
        kiosk2 = auth_manager.create_kiosk_device(
            organization_id=organization_id,
            name="Lobby Tablet 2"
        )
        total_tests += 1
        passed_tests += print_test("Kiosk creation allowed at limit", True)
    except Exception as e:
        total_tests += 1
        print_test("Kiosk creation allowed at limit", False, str(e))

    # ========================================================================
    # 13. Test User Deactivation and Reactivation
    # ========================================================================
    print_header("13. Testing User Deactivation")

    # Deactivate a user
    if 'sales' in created_users:
        sales_id = created_users['sales']
        auth_manager.deactivate_user(sales_id)

        # Check seat was freed (5 users - 1 deactivated = 4)
        seats = auth_manager.get_seat_usage(account_id)
        total_tests += 1
        passed = seats['used'] == 4 and not seats['at_limit']
        passed_tests += print_test("Deactivate frees seat", passed,
                                   f"({seats['used']}/{seats['max']} used)")

        # Now we can create a new user
        try:
            new_user_id = auth_manager.create_user(
                account_id=account_id,
                organization_id=organization_id,
                email="newsales@testshop.com",
                password="test123",
                role_name="sales"
            )
            total_tests += 1
            passed_tests += print_test("Create user after deactivation", True)

            # Deactivate new user to make room
            auth_manager.deactivate_user(new_user_id)
        except Exception as e:
            total_tests += 1
            print_test("Create user after deactivation", False, str(e))

        # Reactivate original sales user
        try:
            auth_manager.reactivate_user(sales_id)
            total_tests += 1
            passed_tests += print_test("Reactivate user", True)
        except Exception as e:
            total_tests += 1
            print_test("Reactivate user", False, str(e))

    # ========================================================================
    # 14. Test Audit Log
    # ========================================================================
    print_header("14. Testing Audit Log")

    logs = auth_manager.get_audit_log(organization_id=organization_id, limit=10)
    total_tests += 1
    passed = len(logs) > 0
    passed_tests += print_test("Audit log has entries", passed, f"({len(logs)} entries)")

    # Check for expected actions
    actions = [log['action'] for log in logs]
    total_tests += 1
    passed = 'account.created' in actions or 'user.created' in actions
    passed_tests += print_test("Audit log has expected actions", passed)

    # ========================================================================
    # 15. Test Role and Permission Queries
    # ========================================================================
    print_header("15. Testing Role and Permission Queries")

    roles = auth_manager.get_all_roles()
    total_tests += 1
    passed = len(roles) == 7  # owner, admin, office, sales, tech, estimator, kiosk
    passed_tests += print_test("Get all roles", passed, f"({len(roles)} roles)")

    owner_role = auth_manager.get_role_by_name('owner')
    total_tests += 1
    passed = owner_role is not None and owner_role['name'] == 'owner'
    passed_tests += print_test("Get role by name", passed)

    owner_perms = auth_manager.get_permissions_for_role(owner_role['id'])
    total_tests += 1
    passed = len(owner_perms) > 50  # Owner should have all permissions
    passed_tests += print_test("Get permissions for role", passed,
                               f"({len(owner_perms)} permissions)")

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
        db_path = "data/test_rbac.db"

    success = test_rbac_system(db_path)
    sys.exit(0 if success else 1)
