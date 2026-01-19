"""
Demo script to test real-time job status notifications

This script:
1. Creates a test customer with portal access
2. Creates a job for the customer
3. Updates the job status through the workflow
4. Creates notifications that will appear in the customer portal

Run this while the web app is running to see notifications in real-time.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crm.models.database import Database
from src.crm.models.schema import DatabaseSchema
from src.crm.models.onboarding_schema import OnboardingSchema
from src.crm.managers.job_manager import JobManager
from src.crm.managers.job_notification_manager import JobNotificationManager
from src.crm.managers.customer_manager import CustomerManager
from src.crm.managers.vehicle_manager import VehicleManager


def setup_test_data():
    """Set up test data for notification demo"""

    print("\n" + "="*60)
    print("NOTIFICATION DEMO - SETUP")
    print("="*60 + "\n")

    # Use the same database as the customer portal
    db_path = "data/pdr_crm.db"
    os.makedirs("data", exist_ok=True)

    # Create schema
    DatabaseSchema.create_all_tables(db_path)

    db = Database(db_path)
    OnboardingSchema.create_onboarding_tables(db)

    # Initialize managers
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    job_mgr = JobManager(db, enable_notifications=True)
    notification_mgr = JobNotificationManager(db_path)

    # Check if demo customer exists
    existing = db.execute("""
        SELECT id FROM customers WHERE email = 'demo@test.com'
    """)

    if existing:
        customer_id = existing[0]['id']
        print(f"[INFO] Using existing demo customer (ID: {customer_id})")
    else:
        # Create demo customer
        customer_id = customer_mgr.create_customer({
            'first_name': 'Demo',
            'last_name': 'Customer',
            'phone': '555-123-4567',
            'email': 'demo@test.com',
            'city': 'Dallas',
            'state': 'TX'
        })
        print(f"[OK] Created demo customer (ID: {customer_id})")

    # Check/create portal credentials
    portal_creds = db.execute("""
        SELECT id FROM portal_credentials WHERE customer_id = ?
    """, (customer_id,))

    if not portal_creds:
        # Create portal credentials
        from werkzeug.security import generate_password_hash
        db.insert('portal_credentials', {
            'customer_id': customer_id,
            'username': 'demo',
            'password_hash': generate_password_hash('demo123'),
            'created_at': datetime.now().isoformat(),
            'status': 'ACTIVE'
        })
        print("[OK] Created portal credentials: username='demo', password='demo123'")
    else:
        print("[INFO] Portal credentials already exist: username='demo', password='demo123'")

    # Check/create vehicle
    vehicles = db.execute("""
        SELECT id FROM vehicles WHERE customer_id = ?
    """, (customer_id,))

    if vehicles:
        vehicle_id = vehicles[0]['id']
        print(f"[INFO] Using existing vehicle (ID: {vehicle_id})")
    else:
        vehicle_id = vehicle_mgr.create_vehicle({
            'customer_id': customer_id,
            'year': 2024,
            'make': 'Tesla',
            'model': 'Model 3',
            'vin': 'DEMO12345678901',
            'color': 'White'
        })
        print(f"[OK] Created vehicle (ID: {vehicle_id})")

    # Create technician if needed
    tech = db.execute("SELECT id FROM technicians LIMIT 1")
    if not tech:
        tech_id = db.insert('technicians', {
            'first_name': 'John',
            'last_name': 'Tech',
            'employee_id': 'TECH001',
            'email': 'john@pdrshop.com',
            'skill_level': 'EXPERT',
            'max_jobs_concurrent': 3,
            'status': 'ACTIVE'
        })
        print(f"[OK] Created technician (ID: {tech_id})")

    # Set up notification preferences (enable all channels for demo)
    notification_mgr.update_customer_preferences(customer_id, {
        'email_enabled': True,
        'sms_enabled': False,
        'push_enabled': False,
        'in_app_enabled': True,
        'notify_on_statuses': [
            'DROPPED_OFF', 'ESTIMATE_CREATED', 'APPROVED',
            'IN_PROGRESS', 'READY_FOR_PICKUP', 'COMPLETED'
        ]
    })
    print("[OK] Set up notification preferences")

    return db_path, customer_id, vehicle_id


def create_job_and_notify(db_path, customer_id, vehicle_id):
    """Create a new job and progress through statuses"""

    print("\n" + "="*60)
    print("NOTIFICATION DEMO - CREATING JOB")
    print("="*60 + "\n")

    db = Database(db_path)
    job_mgr = JobManager(db, enable_notifications=True)
    notification_mgr = JobNotificationManager(db_path)

    # Create a new job
    job_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL",
        scheduled_drop_off=datetime.now() + timedelta(days=1),
        priority="HIGH",
        internal_notes="Demo job for notification testing",
        created_by="demo_script"
    )

    job = job_mgr.get_job(job_id)
    print(f"[OK] Created job: {job['job_number']} (ID: {job_id})")
    print(f"     Current status: {job['status']}")

    return job_id


def progress_job_status(db_path, job_id):
    """Progress job through various statuses to trigger notifications"""

    print("\n" + "="*60)
    print("NOTIFICATION DEMO - UPDATING STATUS")
    print("="*60 + "\n")

    db = Database(db_path)
    job_mgr = JobManager(db, enable_notifications=True)

    # Status progression sequence (following valid workflow)
    # Using only key statuses that customers care about
    statuses = [
        ('DROPPED_OFF', 'Customer dropped off vehicle'),
        ('ESTIMATE_CREATED', 'Initial estimate completed'),
        ('WAITING_INSURANCE', 'Submitted to insurance'),
        ('APPROVED', 'Insurance approved the claim'),
        ('ASSIGNED_TO_TECH', 'Technician assigned'),
        ('IN_PROGRESS', 'Repair work has begun'),
    ]

    print("Progressing job through statuses...\n")

    import time

    for new_status, notes in statuses:
        print(f">>> Updating to: {new_status}")
        job_mgr.update_status(job_id, new_status, notes=notes)

        # Wait a moment between updates
        time.sleep(2)
        print()

    print("[DONE] Job status progression complete!")
    print("\nCheck the customer portal at http://127.0.0.1:5000/portal/")
    print("Login with: username='demo', password='demo123'")


def show_notifications(db_path, customer_id):
    """Display current notifications for the customer"""

    print("\n" + "="*60)
    print("NOTIFICATION DEMO - CURRENT NOTIFICATIONS")
    print("="*60 + "\n")

    notification_mgr = JobNotificationManager(db_path)

    notifications = notification_mgr.get_notifications(customer_id, limit=10)
    unread = notification_mgr.get_unread_count(customer_id)

    print(f"Total unread: {unread}\n")

    for notif in notifications:
        status_indicator = "[NEW]" if notif['status'] == 'UNREAD' else "[READ]"
        print(f"{status_indicator} {notif['title']}")
        print(f"         {notif['message'][:60]}...")
        print(f"         Created: {notif['created_at']}")
        print()


def main():
    print("""
    ============================================================
    JOB STATUS NOTIFICATION DEMO
    ============================================================

    This script demonstrates the real-time notification system.

    Make sure the web app is running at http://127.0.0.1:5000

    The script will:
    1. Create a demo customer with portal access
    2. Create a job for the customer
    3. Progress the job through various statuses
    4. Each status change will trigger notifications

    You can watch the notifications appear in real-time in the
    customer portal!

    ============================================================
    """)

    # Setup
    db_path, customer_id, vehicle_id = setup_test_data()

    # Create job
    job_id = create_job_and_notify(db_path, customer_id, vehicle_id)

    print("\n" + "-"*60)
    print("JOB CREATED! Now let's progress through statuses...")
    print("-"*60)
    print("\nOpen http://127.0.0.1:5000/portal/ in your browser")
    print("Login: username='demo', password='demo123'")
    print("\nWatch for notifications as we update the job status!")
    print("-"*60)

    # Progress through statuses
    progress_job_status(db_path, job_id)

    # Show final notifications
    show_notifications(db_path, customer_id)

    print("\n" + "="*60)
    print("DEMO COMPLETE!")
    print("="*60)
    print("\nVisit the customer portal to see all notifications:")
    print("  URL: http://127.0.0.1:5000/portal/notifications")
    print("  Login: demo / demo123")
    print()


if __name__ == "__main__":
    main()
