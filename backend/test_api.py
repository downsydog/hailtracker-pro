"""
HailTracker API Test Script
===========================
Tests the API endpoints for registration, authentication, storms, and leads.
"""

import sys
import requests

BASE_URL = 'http://localhost:5000/api'


def test_api():
    """Run API tests."""
    print("=== Testing HailTracker API ===\n")

    token = None

    # 1. Register a new company
    print("1. Registering new company...")
    response = requests.post(f'{BASE_URL}/auth/register', json={
        'company_name': 'Demo PDR Company',
        'owner_name': 'Demo Owner',
        'email': 'demo@demopdr.com',
        'password': 'demopass123'
    })

    if response.status_code == 201:
        data = response.json()
        token = data['data']['access_token']
        print(f"   Registered: {data['data']['tenant']['company_name']}")
        print(f"   Token: {token[:50]}...")
    else:
        print(f"   Registration error (may already exist): {response.json().get('error', 'Unknown')}")
        # Try login instead
        print("\n   Trying login...")
        response = requests.post(f'{BASE_URL}/auth/login', json={
            'email': 'demo@demopdr.com',
            'password': 'demopass123'
        })
        if response.status_code == 200:
            data = response.json()
            token = data['access_token']
            print(f"   Logged in, token: {token[:50]}...")
        else:
            print(f"   Login failed: {response.json()}")
            return

    headers = {'Authorization': f'Bearer {token}'}

    # 2. Get current user
    print("\n2. Getting current user...")
    response = requests.get(f'{BASE_URL}/auth/me', headers=headers)
    if response.status_code == 200:
        user = response.json()['user']
        print(f"   User: {user['name']} ({user['role']})")
    else:
        print(f"   Error: {response.json()}")

    # 3. Get storms
    print("\n3. Getting recent storms...")
    response = requests.get(f'{BASE_URL}/storms', headers=headers)
    if response.status_code == 200:
        storms = response.json()['storms']
        print(f"   Found {len(storms)} storms")
        if storms:
            storm = storms[0]
            print(f"   First storm: ID={storm['id']}, State={storm.get('state')}, Businesses={storm.get('business_count')}")
    else:
        print(f"   Error: {response.json()}")

    # 4. Get leads
    print("\n4. Getting leads...")
    response = requests.get(f'{BASE_URL}/leads', headers=headers)
    if response.status_code == 200:
        leads = response.json()['leads']
        print(f"   Found {len(leads)} leads")
    else:
        print(f"   Error: {response.json()}")

    # 5. Get lead stats
    print("\n5. Getting lead stats...")
    response = requests.get(f'{BASE_URL}/leads/stats', headers=headers)
    if response.status_code == 200:
        stats = response.json()
        print(f"   Total leads: {stats['total']}")
        print(f"   By status: {stats['by_status']}")
    else:
        print(f"   Error: {response.json()}")

    # 6. Customer dashboard
    print("\n6. Getting customer dashboard...")
    response = requests.get(f'{BASE_URL}/dashboard', headers=headers)
    if response.status_code == 200:
        dashboard = response.json()
        print(f"   Company: {dashboard['company']}")
        print(f"   Active storms: {dashboard['stats']['active_storms']}")
        print(f"   Total leads: {dashboard['stats']['total_leads']}")
    else:
        print(f"   Error: {response.json()}")

    # 7. Admin dashboard (owner only)
    print("\n7. Getting admin dashboard...")
    response = requests.get(f'{BASE_URL}/admin/dashboard', headers=headers)
    if response.status_code == 200:
        dashboard = response.json()
        print(f"   Tenant: {dashboard['tenant']['company_name']}")
        print(f"   Users: {dashboard['users']['active']}/{dashboard['users']['max_allowed']}")
        print(f"   Plan: {dashboard['tenant']['plan']}")
    else:
        print(f"   Error: {response.json()}")

    # 8. API usage
    print("\n8. Getting API usage...")
    response = requests.get(f'{BASE_URL}/admin/usage', headers=headers)
    if response.status_code == 200:
        usage = response.json()
        print(f"   Today: {usage['today']}")
        print(f"   This month: {list(usage['month'].keys())}")
    else:
        print(f"   Error: {response.json()}")

    # 9. Get team members
    print("\n9. Getting team members...")
    response = requests.get(f'{BASE_URL}/auth/team', headers=headers)
    if response.status_code == 200:
        team = response.json()
        print(f"   Team size: {team['count']}")
        for member in team['team']:
            print(f"     - {member['name']} ({member['role']})")
    else:
        print(f"   Error: {response.json()}")

    # 10. Health check
    print("\n10. Health check...")
    response = requests.get('http://localhost:5000/api/health')
    if response.status_code == 200:
        health = response.json()
        print(f"   Status: {health['status']}")
        print(f"   Database: {health['database']}")
    else:
        print(f"   Error: {response.status_code}")

    print("\n=== API Tests Complete ===")


if __name__ == '__main__':
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Make sure the Flask server is running: python run.py")
        sys.exit(1)
