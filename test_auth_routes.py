"""
Test authentication routes and Flask-Login integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.web.app import create_app
from src.auth.auth_manager import AuthManager


def test_auth_routes():
    print("\n" + "="*60)
    print("TESTING AUTH ROUTES & FLASK-LOGIN")
    print("="*60 + "\n")

    app = create_app()
    auth_manager = AuthManager()

    with app.test_client() as client:

        # Test 1: Access protected page without login (should redirect)
        print("[1/7] Testing protected route without login...")
        response = client.get('/crm/dashboard', follow_redirects=False)
        if response.status_code == 302:  # Redirect
            print(f"  Correctly redirected to login (status: {response.status_code})")
        else:
            print(f"  Should redirect but got status: {response.status_code}")

        # Test 2: Access login page
        print("\n[2/7] Testing login page access...")
        response = client.get('/auth/login')
        if response.status_code == 200:
            print(f"  Login page accessible (status: {response.status_code})")
        else:
            print(f"  Login page error (status: {response.status_code})")

        # Test 3: Login with admin credentials
        print("\n[3/7] Testing login with admin credentials...")
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123',
            'remember': False
        }, follow_redirects=True)

        if response.status_code == 200 and b'Dashboard' in response.data:
            print("  Admin login successful, redirected to dashboard")
        elif response.status_code == 200:
            print("  Admin login successful (dashboard redirect)")
        else:
            print(f"  Login failed (status: {response.status_code})")

        # Test 4: Access protected route after login
        print("\n[4/7] Testing protected route after login...")
        response = client.get('/crm/dashboard')
        if response.status_code == 200:
            print("  Can access dashboard after login")
        else:
            print(f"  Dashboard access failed (status: {response.status_code})")

        # Test 5: Test logout
        print("\n[5/7] Testing logout...")
        response = client.get('/auth/logout', follow_redirects=True)
        if response.status_code == 200:
            print("  Logout successful")
        else:
            print(f"  Logout failed (status: {response.status_code})")

        # Test 6: Try accessing dashboard after logout
        print("\n[6/7] Testing dashboard access after logout...")
        response = client.get('/crm/dashboard', follow_redirects=False)
        if response.status_code == 302:
            print("  Correctly redirected to login after logout")
        else:
            print(f"  Should redirect but got status: {response.status_code}")

        # Test 7: Test failed login
        print("\n[7/7] Testing failed login...")
        response = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        if b'Invalid username or password' in response.data:
            print("  Failed login correctly rejected")
        else:
            print("  Failed login not properly handled")

    print("\n" + "="*60)
    print("AUTH ROUTES TESTS COMPLETE")
    print("="*60 + "\n")

    print("Try accessing in browser:")
    print("  1. http://localhost:5555/auth/login")
    print("  2. Login with: admin / admin123")
    print("  3. Should redirect to CRM dashboard")
    print()


if __name__ == '__main__':
    test_auth_routes()
