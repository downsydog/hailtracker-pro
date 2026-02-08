"""
Test authentication system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auth.auth_manager import AuthManager


def test_auth_system():
    print("\n" + "="*60)
    print("TESTING AUTH SYSTEM")
    print("="*60 + "\n")

    auth = AuthManager()

    # Test 1: Create user
    print("[1/8] Creating test user...")
    user_id = auth.create_user(
        email='kyle@example.com',
        username='kyle',
        password='testpassword123',
        full_name='Kyle Test User',
        role='sales',
        company_id=1
    )
    if user_id:
        print(f"  User created with ID: {user_id}")
    else:
        print("  User creation failed (may already exist)")

    # Test 2: Authenticate user
    print("\n[2/8] Testing authentication...")
    user = auth.authenticate_user('kyle', 'testpassword123', '127.0.0.1')
    if user:
        print(f"  Authentication successful: {user['username']}")
    else:
        print("  Authentication failed")

    # Test 3: Test wrong password
    print("\n[3/8] Testing wrong password...")
    bad_user = auth.authenticate_user('kyle', 'wrongpassword', '127.0.0.1')
    if not bad_user:
        print("  Correctly rejected wrong password")
    else:
        print("  Security issue: accepted wrong password!")

    # Test 4: Check permissions
    print("\n[4/8] Testing permissions...")
    if user:
        can_create_deal = auth.check_permission(user['id'], 'deals', 'create')
        can_delete_user = auth.check_permission(user['id'], 'users', 'delete')
        print(f"  Can create deal: {can_create_deal} (should be True)")
        print(f"  Can delete user: {can_delete_user} (should be False)")

    # Test 5: Get user permissions
    print("\n[5/8] Getting user permissions...")
    if user:
        permissions = auth.get_user_permissions(user['id'])
        print(f"  User has {len(permissions)} permissions")
        for perm in permissions[:5]:
            print(f"    - {perm['resource']}:{perm['action']} = {perm['allowed']}")

    # Test 6: Change password
    print("\n[6/8] Testing password change...")
    if user:
        changed = auth.change_password(user['id'], 'testpassword123', 'newpassword456')
        if changed:
            print("  Password changed successfully")
            # Try logging in with new password
            user2 = auth.authenticate_user('kyle', 'newpassword456')
            if user2:
                print("  Login with new password works")
            else:
                print("  Login with new password failed")
        else:
            print("  Password change failed")

    # Test 7: Password reset token
    print("\n[7/8] Testing password reset token...")
    token = auth.generate_reset_token('kyle@example.com')
    if token:
        print(f"  Reset token generated: {token[:20]}...")
        # Test reset
        reset_success = auth.reset_password(token, 'resetpassword789')
        if reset_success:
            print("  Password reset successful")
        else:
            print("  Password reset failed")
    else:
        print("  Token generation failed")

    # Test 8: Audit log
    print("\n[8/8] Checking audit log...")
    logs = auth.get_audit_log(limit=10)
    print(f"  Found {len(logs)} audit log entries")
    for log in logs[:3]:
        print(f"    - {log['action']} at {log['timestamp']}")

    # Test admin user
    print("\n[BONUS] Testing default admin user...")
    admin = auth.authenticate_user('admin', 'admin123')
    if admin:
        print(f"  Admin user works: {admin['username']}")
        print(f"    Role: {admin['role']}")
        print(f"    Email: {admin['email']}")
    else:
        print("  Admin user not working")

    print("\n" + "="*60)
    print("AUTH SYSTEM TESTS COMPLETE")
    print("="*60 + "\n")

    print("Default Login Credentials:")
    print("  Username: admin")
    print("  Password: admin123")
    print("  (CHANGE THIS IN PRODUCTION!)")
    print()


if __name__ == '__main__':
    test_auth_system()
