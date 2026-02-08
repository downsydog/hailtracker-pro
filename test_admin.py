"""
Test admin panel functionality
"""

import sys
sys.path.insert(0, '.')

from src.auth.auth_manager import AuthManager

def test_admin_features():
    print("\n" + "="*60)
    print("TESTING ADMIN PANEL")
    print("="*60 + "\n")

    auth = AuthManager()

    # Test 1: Create test users with different roles
    print("[1/5] Creating test users...")

    users_to_create = [
        ('sarah', 'sarah@example.com', 'Sarah Manager', 'manager'),
        ('john', 'john@example.com', 'John Sales', 'sales'),
        ('mike', 'mike@example.com', 'Mike Tech', 'technician'),
    ]

    for username, email, full_name, role in users_to_create:
        user_id = auth.create_user(
            email=email,
            username=username,
            password='testpass123',
            full_name=full_name,
            role=role,
            company_id=1
        )
        if user_id:
            print(f"  Created {role}: {username}")
        else:
            print(f"  {username} already exists")

    # Test 2: Get company users
    print("\n[2/5] Getting company users...")
    company_users = auth.get_company_users(1)
    print(f"  Found {len(company_users)} users in company")

    # Test 3: Count by role
    print("\n[3/5] Counting users by role...")
    from collections import Counter
    role_counts = Counter(user['role'] for user in company_users)
    for role, count in role_counts.items():
        print(f"  - {role}: {count}")

    # Test 4: Get audit log
    print("\n[4/5] Checking audit log...")
    logs = auth.get_audit_log(limit=20)
    print(f"  Found {len(logs)} recent audit entries")
    for log in logs[:5]:
        print(f"    - {log['action']} at {log['timestamp'][:16] if log['timestamp'] else 'N/A'}")

    # Test 5: Permission check for different roles
    print("\n[5/5] Testing role permissions...")

    # Get a sales user
    sales_user = next((u for u in company_users if u['role'] == 'sales'), None)
    if sales_user:
        can_create_deal = auth.check_permission(sales_user['id'], 'deals', 'create')
        can_delete_user = auth.check_permission(sales_user['id'], 'users', 'delete')
        print(f"  Sales user '{sales_user['username']}':")
        print(f"    - Can create deal: {can_create_deal}")
        print(f"    - Can delete user: {can_delete_user}")

    # Get admin user
    admin_user = next((u for u in company_users if u['role'] == 'admin'), None)
    if admin_user:
        can_delete_user = auth.check_permission(admin_user['id'], 'users', 'delete')
        print(f"  Admin user '{admin_user['username']}':")
        print(f"    - Can delete user: {can_delete_user}")

    print("\n" + "="*60)
    print("ADMIN PANEL TESTS COMPLETE")
    print("="*60 + "\n")

    print("Try accessing admin panel:")
    print("  1. Login as admin@hailtracker.com / admin123")
    print("  2. Go to /admin/team or /admin/users")
    print("  3. Try creating/editing users")
    print()

    return True


def test_admin_routes():
    """Test admin routes via HTTP requests"""
    print("\n" + "="*60)
    print("TESTING ADMIN ROUTES")
    print("="*60 + "\n")

    from src.web.app import create_app

    app = create_app()
    app.config['TESTING'] = True

    with app.test_client() as client:

        # Test 1: Admin routes require login
        print("[1/4] Testing admin routes require login...")
        response = client.get('/admin/users')
        if response.status_code == 302:
            print("  Correctly redirected to login (status: 302)")
        else:
            print(f"  Unexpected status: {response.status_code}")

        # Test 2: Login as admin
        print("\n[2/4] Logging in as admin...")
        response = client.post('/auth/login', data={
            'username': 'admin@hailtracker.com',
            'password': 'admin123'
        }, follow_redirects=False)

        if response.status_code == 302:
            print("  Login successful, redirected")
        else:
            print(f"  Login status: {response.status_code}")

        # Test 3: Access admin users page
        print("\n[3/4] Accessing admin users page...")
        response = client.get('/admin/users')
        if response.status_code == 200:
            print("  Admin users page accessible (status: 200)")
            if b'User Management' in response.data:
                print("  Page contains 'User Management' header")
        else:
            print(f"  Status: {response.status_code}")

        # Test 4: Access admin team page
        print("\n[4/4] Accessing admin team page...")
        response = client.get('/admin/team')
        if response.status_code == 200:
            print("  Admin team page accessible (status: 200)")
            if b'Team Overview' in response.data:
                print("  Page contains 'Team Overview' header")
        else:
            print(f"  Status: {response.status_code}")

    print("\n" + "="*60)
    print("ADMIN ROUTES TESTS COMPLETE")
    print("="*60 + "\n")

    return True


if __name__ == '__main__':
    test_admin_features()
    test_admin_routes()
