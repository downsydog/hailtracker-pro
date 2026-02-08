"""
Test Customer Portal & Self-Service
PDR CRM Part 27 - Customer self-service portal
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_customer_portal():
    print("\n" + "="*80)
    print("TESTING CUSTOMER PORTAL & SELF-SERVICE")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.customer_portal_manager import CustomerPortalManager

    # Use test database
    test_db = "data/test_customer_portal.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mgr = CustomerPortalManager(db)

    # Setup: Create customer
    print("Creating test customer...")
    db.execute("""
        INSERT INTO customers (first_name, last_name, email, phone, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, ('John', 'Doe', 'john@example.com', '555-1234', datetime.now().isoformat()))

    customer_id = 1
    print()

    # ========================================================================
    # TEST 1: Create Portal Access
    # ========================================================================

    print("="*80)
    print("[1/12] Creating portal access...")
    print("="*80 + "\n")

    access = mgr.create_portal_access(
        customer_id=customer_id,
        email='john@example.com',
        phone='555-1234'
    )
    print()

    assert access['customer_id'] == customer_id
    assert 'access_token' in access
    assert 'portal_url' in access
    print("[OK] Portal access created")
    print()

    # ========================================================================
    # TEST 2: Send Portal Invite
    # ========================================================================

    print("="*80)
    print("[2/12] Sending portal invite...")
    print("="*80 + "\n")

    result = mgr.send_portal_invite(
        customer_id=customer_id,
        email='john@example.com'
    )
    print()

    assert result == True
    print("[OK] Portal invite sent")
    print()

    # ========================================================================
    # TEST 3: Get Available Slots
    # ========================================================================

    print("="*80)
    print("[3/12] Getting available appointment slots...")
    print("="*80 + "\n")

    service_date = date.today() + timedelta(days=3)

    slots = mgr.get_available_slots(
        service_date=service_date,
        service_type='PDR'
    )

    print(f"Available slots for {service_date.strftime('%B %d, %Y')}:")
    for i, slot in enumerate(slots[:5]):
        status = 'Available' if slot['available'] else 'Booked'
        print(f"  {slot['time']} - {status}")
    print(f"  ... and {len(slots) - 5} more slots")
    print()

    assert len(slots) == 9  # 8 AM to 4 PM = 9 slots
    print("[OK] Appointment slots retrieved")
    print()

    # ========================================================================
    # TEST 4: Book Appointment
    # ========================================================================

    print("="*80)
    print("[4/12] Booking appointment...")
    print("="*80 + "\n")

    appointment_id = mgr.book_appointment(
        customer_id=customer_id,
        service_date=service_date,
        service_time='10:00',
        service_type='PDR',
        vehicle_info={
            'year': 2023,
            'make': 'Toyota',
            'model': 'Camry',
            'color': 'Silver',
            'vin': '1HGBH41JXMN109186'
        },
        damage_description='Hail damage on hood and roof from recent storm',
        contact_preference='EMAIL',
        notes='Prefer morning appointment'
    )
    print()

    assert appointment_id > 0

    # Verify appointment
    appointments = mgr.get_customer_appointments(customer_id)
    assert len(appointments) == 1
    print("[OK] Appointment booked successfully")
    print()

    # ========================================================================
    # TEST 5: Request Online Estimate
    # ========================================================================

    print("="*80)
    print("[5/12] Requesting online estimate...")
    print("="*80 + "\n")

    estimate_request_id = mgr.request_estimate(
        customer_id=customer_id,
        vehicle_info={
            'year': 2021,
            'make': 'Honda',
            'model': 'Accord',
            'color': 'Black'
        },
        damage_description='Door ding on driver side door',
        photo_urls=[
            'https://storage.example.com/photos/photo1.jpg',
            'https://storage.example.com/photos/photo2.jpg',
            'https://storage.example.com/photos/photo3.jpg'
        ],
        preferred_contact='EMAIL',
        urgency='NORMAL'
    )
    print()

    assert estimate_request_id > 0
    print("[OK] Estimate request submitted")
    print()

    # ========================================================================
    # TEST 6: Upload Estimate Photos
    # ========================================================================

    print("="*80)
    print("[6/12] Uploading estimate photos...")
    print("="*80 + "\n")

    photos = [
        {
            'url': 'https://storage.example.com/photos/photo1.jpg',
            'type': 'overview',
            'description': 'Driver side overview'
        },
        {
            'url': 'https://storage.example.com/photos/photo2.jpg',
            'type': 'damage',
            'description': 'Door ding closeup'
        },
        {
            'url': 'https://storage.example.com/photos/photo3.jpg',
            'type': 'damage',
            'description': 'Damage from different angle'
        }
    ]

    photo_count = mgr.upload_estimate_photos(
        request_id=estimate_request_id,
        photos=photos
    )
    print()

    assert photo_count == 3

    # Verify photos
    request = mgr.get_estimate_request(estimate_request_id)
    assert len(request['photos']) == 3
    print("[OK] Photos uploaded successfully")
    print()

    # ========================================================================
    # TEST 7: Track Job Status
    # ========================================================================

    print("="*80)
    print("[7/12] Tracking job status...")
    print("="*80 + "\n")

    # Create a test vehicle
    db.execute("""
        INSERT INTO vehicles (customer_id, year, make, model, vin, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (customer_id, 2023, 'Toyota', 'Camry', '1HGBH41JXMN109186', datetime.now().isoformat()))

    vehicle_id = 1

    # Create a test job
    db.execute("""
        INSERT INTO jobs (
            job_number, customer_id, vehicle_id, status,
            tech_notes, estimated_completion_date,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'JOB-2026-0001',
        customer_id,
        vehicle_id,
        'IN_PROGRESS',
        'Hail damage repair - hood and roof',
        (date.today() + timedelta(days=2)).isoformat(),
        datetime.now().isoformat()
    ))

    job_statuses = mgr.get_job_status(customer_id)

    print(f"Active jobs for customer ({len(job_statuses)}):")
    for job_status in job_statuses:
        print(f"  Job #{job_status['job_id']}")
        print(f"    Status: {job_status['status']}")
        print(f"    Progress: {job_status['progress_percent']}%")
        if job_status['estimated_completion']:
            print(f"    Est. completion: {job_status['estimated_completion']}")
        print()

    assert len(job_statuses) == 1
    assert job_statuses[0]['progress_percent'] == 50  # IN_PROGRESS = 50%
    print("[OK] Job status tracking working")
    print()

    # ========================================================================
    # TEST 8: Get Service History
    # ========================================================================

    print("="*80)
    print("[8/12] Getting service history...")
    print("="*80 + "\n")

    # Create completed job
    db.execute("""
        INSERT INTO jobs (
            job_number, customer_id, vehicle_id, status,
            tech_notes, completed_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'JOB-2026-0002',
        customer_id,
        vehicle_id,
        'COMPLETED',
        'Door ding removal',
        (date.today() - timedelta(days=30)).isoformat(),
        (date.today() - timedelta(days=35)).isoformat()
    ))

    completed_job_id = 2

    # Create invoice for completed job
    db.execute("""
        INSERT INTO invoices (
            invoice_number, job_id, customer_id, invoice_date,
            subtotal, tax_amount, total, balance_due, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'INV-2026-0001',
        completed_job_id,
        customer_id,
        (date.today() - timedelta(days=30)).isoformat(),
        425.00,
        35.06,
        460.06,
        0.00,  # Paid
        'PAID'
    ))

    history = mgr.get_service_history(customer_id, limit=10)

    print(f"Service history ({len(history)} services):")
    for item in history:
        print(f"  Job #{item['job_id']}")
        print(f"    Date: {item['service_date']}")
        print(f"    Service: {item['description']}")
        if item['total_cost']:
            print(f"    Cost: ${item['total_cost']:,.2f}")
        print()

    assert len(history) == 1
    print("[OK] Service history retrieved")
    print()

    # ========================================================================
    # TEST 9: Get Customer Invoices
    # ========================================================================

    print("="*80)
    print("[9/12] Getting customer invoices...")
    print("="*80 + "\n")

    # Create unpaid invoice
    db.execute("""
        INSERT INTO jobs (
            job_number, customer_id, vehicle_id, status,
            tech_notes, completed_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'JOB-2026-0003',
        customer_id,
        vehicle_id,
        'COMPLETED',
        'Hail damage repair',
        date.today().isoformat(),
        (date.today() - timedelta(days=3)).isoformat()
    ))

    new_job_id = 3

    db.execute("""
        INSERT INTO invoices (
            invoice_number, job_id, customer_id, invoice_date,
            subtotal, tax_amount, total, balance_due, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'INV-2026-0002',
        new_job_id,
        customer_id,
        date.today().isoformat(),
        850.00,
        70.13,
        920.13,
        920.13,  # Unpaid
        'SENT'
    ))

    unpaid_invoice_id = 2

    invoices = mgr.get_customer_invoices(customer_id, unpaid_only=True)

    print(f"Unpaid invoices ({len(invoices)}):")
    for invoice in invoices:
        print(f"  Invoice #{invoice['id']}")
        print(f"    Date: {invoice['invoice_date']}")
        print(f"    Total: ${invoice['total']:,.2f}")
        print(f"    Balance due: ${invoice['balance_due']:,.2f}")
        print()

    assert len(invoices) == 1
    assert invoices[0]['balance_due'] == 920.13
    print("[OK] Invoices retrieved successfully")
    print()

    # ========================================================================
    # TEST 10: Create Payment Link
    # ========================================================================

    print("="*80)
    print("[10/12] Creating payment link...")
    print("="*80 + "\n")

    payment_link = mgr.create_payment_link(
        invoice_id=unpaid_invoice_id,
        amount=920.13
    )
    print()

    assert 'payment_token' in payment_link
    assert 'payment_url' in payment_link
    assert payment_link['amount'] == 920.13
    print("[OK] Payment link created")
    print()

    # ========================================================================
    # TEST 11: Submit Customer Review
    # ========================================================================

    print("="*80)
    print("[11/12] Submitting customer review...")
    print("="*80 + "\n")

    review_id = mgr.submit_review(
        customer_id=customer_id,
        job_id=completed_job_id,
        rating=5,
        review_text='Excellent service! Fast, professional, and the repair looks perfect. Highly recommend!',
        would_recommend=True,
        review_categories={
            'quality': 5,
            'service': 5,
            'value': 5,
            'timeliness': 5
        }
    )
    print()

    assert review_id > 0

    # Verify review
    reviews = mgr.get_customer_reviews(customer_id)
    assert len(reviews) == 1
    assert reviews[0]['rating'] == 5
    print("[OK] Review submitted successfully")
    print()

    # ========================================================================
    # TEST 12: Get Loyalty Points
    # ========================================================================

    print("="*80)
    print("[12/12] Getting loyalty points...")
    print("="*80 + "\n")

    # Create loyalty transactions
    db.execute("""
        INSERT INTO loyalty_transactions (
            customer_id, transaction_type, points_earned,
            description, created_at
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        customer_id,
        'EARNED',
        850,
        'Points earned from invoice #1',
        (date.today() - timedelta(days=30)).isoformat()
    ))

    db.execute("""
        INSERT INTO loyalty_transactions (
            customer_id, transaction_type, points_earned,
            description, created_at
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        customer_id,
        'EARNED',
        400,
        'Points earned from invoice #2',
        date.today().isoformat()
    ))

    loyalty = mgr.get_loyalty_points(customer_id)

    print(f"Loyalty Program Summary:")
    print(f"  Customer ID: {loyalty['customer_id']}")
    print(f"  Current balance: {loyalty['points_balance']} points")
    print(f"  Total earned: {loyalty['total_earned']} points")
    print(f"  Total redeemed: {loyalty['total_redeemed']} points")
    print(f"  Current tier: {loyalty['tier']}")
    print()
    print(f"  Tier benefits:")
    for benefit in loyalty['tier_benefits']:
        print(f"    - {benefit}")
    print()

    assert loyalty['points_balance'] == 1250
    assert loyalty['tier'] == 'SILVER'  # 1000-2499 points
    print("[OK] Loyalty points retrieved")
    print()

    # ========================================================================
    # BONUS: Send Message
    # ========================================================================

    print("="*80)
    print("[BONUS] Sending message through portal...")
    print("="*80 + "\n")

    message_id = mgr.send_message(
        customer_id=customer_id,
        subject='Question about my repair',
        message='When will my car be ready for pickup?',
        related_job_id=1
    )
    print()

    assert message_id > 0

    messages = mgr.get_messages(customer_id)
    assert len(messages) == 1
    print("[OK] Message sent successfully")
    print()

    # ========================================================================
    # BONUS: Portal Dashboard
    # ========================================================================

    print("="*80)
    print("[BONUS] Getting portal dashboard...")
    print("="*80 + "\n")

    dashboard = mgr.get_portal_dashboard(customer_id)

    print(f"Portal Dashboard:")
    print(f"  Customer: {dashboard['customer']['first_name']} {dashboard['customer']['last_name']}")
    print(f"  Active jobs: {len(dashboard['active_jobs'])}")
    print(f"  Upcoming appointments: {len(dashboard['upcoming_appointments'])}")
    print(f"  Unpaid invoices: {len(dashboard['unpaid_invoices'])}")
    print(f"  Loyalty tier: {dashboard['loyalty']['tier']}")
    print(f"  Points balance: {dashboard['loyalty']['points_balance']}")
    print(f"  Unread messages: {dashboard['unread_messages']}")
    print()

    assert dashboard['customer']['first_name'] == 'John'
    print("[OK] Portal dashboard working")
    print()

    # ========================================================================
    # Cleanup
    # ========================================================================

    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] CUSTOMER PORTAL & SELF-SERVICE TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Portal access creation")
    print("  [OK] Portal invite emails")
    print("  [OK] Appointment availability check")
    print("  [OK] Self-service booking")
    print("  [OK] Online estimate requests")
    print("  [OK] Photo uploads")
    print("  [OK] Real-time job tracking")
    print("  [OK] Service history")
    print("  [OK] Invoice viewing")
    print("  [OK] Payment link generation")
    print("  [OK] Customer reviews")
    print("  [OK] Loyalty points tracking")
    print("  [OK] Messaging system")
    print("  [OK] Portal dashboard")
    print()

    print("CUSTOMER PORTAL FEATURES:")
    print("  - Self-service appointment booking")
    print("  - Real-time job status tracking")
    print("  - Online estimate requests with photos")
    print("  - Complete service history")
    print("  - Invoice viewing & online payment")
    print("  - Review & feedback system")
    print("  - Communication center")
    print("  - Loyalty rewards program")
    print()

    print("SELF-SERVICE WORKFLOW:")
    print("  1. Customer receives portal invite email")
    print("  2. Click link to access personal portal")
    print("  3. View dashboard (active jobs, invoices, points)")
    print("  4. Book appointments online")
    print("  5. Upload photos for remote estimates")
    print("  6. Track job progress in real-time")
    print("  7. Pay invoices securely online")
    print("  8. Leave reviews after service")
    print("  9. Redeem loyalty points")
    print()

    print("LOYALTY PROGRAM TIERS:")
    print("  Bronze:   0-999 points    (1 pt/$1)")
    print("  Silver:   1,000-2,499 pts (1.5 pt/$1)")
    print("  Gold:     2,500-4,999 pts (2 pt/$1)")
    print("  Platinum: 5,000+ pts      (2.5 pt/$1)")
    print()

    print("Ready for PROMPT 28?")
    print()

    return True


if __name__ == '__main__':
    success = test_customer_portal()
    sys.exit(0 if success else 1)
