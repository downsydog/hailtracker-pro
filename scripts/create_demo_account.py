"""
Create Demo Account
Creates a demo account with sample users for development and testing.

Login credentials:
    Owner:     demo@hailtrackerpro.com / demo123
    Admin:     admin@demo.com / demo123
    Office:    sarah@demo.com / demo123
    Sales:     mike@demo.com / demo123
    Tech:      john@demo.com / demo123
    Estimator: lisa@demo.com / demo123

Usage:
    python scripts/create_demo_account.py [database_path]
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.auth.auth_manager import AuthManager
from src.core.models.tenant_schema import init_tenant_schema
from scripts.seed_rbac import seed_rbac


def create_demo_account(db_path: str = "data/hailtracker_crm.db"):
    """
    Create a demo account with realistic sample users.
    """
    print("=" * 60)
    print("CREATE DEMO ACCOUNT")
    print("=" * 60)
    print(f"\nDatabase: {db_path}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Ensure schema and roles exist
    print("Step 1: Ensuring tenant schema exists...")
    init_tenant_schema(db_path)
    print()

    print("Step 2: Ensuring RBAC data is seeded...")
    seed_rbac(db_path)
    print()

    # Create AuthManager
    auth_manager = AuthManager(db_path)

    # Check if demo account already exists
    existing = auth_manager.get_user_by_email("demo@hailtrackerpro.com")
    if existing:
        print("Demo account already exists!")
        print(f"  Owner: demo@hailtrackerpro.com / demo123")
        print(f"  Account ID: {existing['account_id']}")
        print(f"  Organization ID: {existing['organization_id']}")
        return existing

    # Create account
    print("Step 3: Creating demo account...")
    result = auth_manager.create_account(
        name="Demo PDR Shop",
        owner_email="demo@hailtrackerpro.com",
        owner_password="demo123",
        plan="professional",
        first_name="Demo",
        last_name="Owner",
        phone="(555) 123-4567",
        address="123 Main Street",
        city="Dallas",
        state="TX",
        zip="75001"
    )

    account_id = result['account_id']
    organization_id = result['organization_id']

    print(f"  Account ID: {account_id}")
    print(f"  Organization ID: {organization_id}")
    print(f"  Owner User ID: {result['user_id']}")
    print()

    # Create sample users
    print("Step 4: Creating sample users...")

    users = [
        {
            "email": "admin@demo.com",
            "role": "admin",
            "first_name": "Admin",
            "last_name": "User",
            "job_title": "System Administrator"
        },
        {
            "email": "sarah@demo.com",
            "role": "office",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "job_title": "Office Manager",
            "phone": "(555) 234-5678"
        },
        {
            "email": "mike@demo.com",
            "role": "sales",
            "first_name": "Mike",
            "last_name": "Rodriguez",
            "job_title": "Sales Representative",
            "phone": "(555) 345-6789",
            "commission_rate": 0.10
        },
        {
            "email": "john@demo.com",
            "role": "tech",
            "first_name": "John",
            "last_name": "Smith",
            "job_title": "Master Technician",
            "phone": "(555) 456-7890",
            "hourly_rate": 35.00
        },
        {
            "email": "lisa@demo.com",
            "role": "estimator",
            "first_name": "Lisa",
            "last_name": "Chen",
            "job_title": "Senior Estimator",
            "phone": "(555) 567-8901"
        },
    ]

    for u in users:
        try:
            user_id = auth_manager.create_user(
                account_id=account_id,
                organization_id=organization_id,
                email=u['email'],
                password="demo123",
                role_name=u['role'],
                first_name=u['first_name'],
                last_name=u['last_name'],
                job_title=u.get('job_title'),
                phone=u.get('phone'),
                commission_rate=u.get('commission_rate', 0),
                hourly_rate=u.get('hourly_rate', 0)
            )
            print(f"  [+] Created {u['first_name']} {u['last_name']} ({u['role']}) - ID: {user_id}")
        except Exception as e:
            print(f"  [!] Failed to create {u['email']}: {e}")
    print()

    # Create kiosk
    print("Step 5: Creating demo kiosk device...")
    try:
        kiosk = auth_manager.create_kiosk_device(
            organization_id=organization_id,
            name="Lobby Tablet",
            auto_reset_seconds=60,
            welcome_message="Welcome to Demo PDR Shop! Please sign in."
        )
        print(f"  [+] Created kiosk: {kiosk['name']} (ID: {kiosk['id']})")
        print(f"      Token: {kiosk['device_token'][:20]}...")
    except Exception as e:
        print(f"  [!] Failed to create kiosk: {e}")
    print()

    # Show seat usage
    print("Step 6: Checking seat usage...")
    seats = auth_manager.get_seat_usage(account_id)
    print(f"  Used: {seats['used']} / {seats['max']} seats")
    print(f"  Available: {seats['available']}")
    print()

    # Print login credentials
    print("=" * 60)
    print("DEMO ACCOUNT CREATED SUCCESSFULLY")
    print("=" * 60)
    print()
    print("Login Credentials:")
    print("-" * 40)
    print(f"  Owner:     demo@hailtrackerpro.com / demo123")
    print(f"  Admin:     admin@demo.com / demo123")
    print(f"  Office:    sarah@demo.com / demo123")
    print(f"  Sales:     mike@demo.com / demo123")
    print(f"  Tech:      john@demo.com / demo123")
    print(f"  Estimator: lisa@demo.com / demo123")
    print()
    print("All users have the same password: demo123")
    print()

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/hailtracker_crm.db"

    create_demo_account(db_path)
