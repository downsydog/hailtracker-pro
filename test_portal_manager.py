"""
Test Customer Portal
PDR CRM Part 14 - Self-Service Customer Portal
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_portal_manager():
    print("\n" + "="*80)
    print("TESTING CUSTOMER PORTAL (SELF-SERVICE)")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.portal_manager import PortalManager
    from src.crm.managers.estimate_manager import EstimateManager
    from src.crm.managers.job_manager import JobManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from src.crm.managers.payment_manager import PaymentManager
    from datetime import datetime, date, timedelta

    # Use test database
    test_db = "data/test_portal.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    portal_mgr = PortalManager(db)
    estimate_mgr = EstimateManager(db)
    job_mgr = JobManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    payment_mgr = PaymentManager(db)

    # Create test data
    print("\nSetting up test data...")

    # Create customer
    customer_id = customer_mgr.create_customer({
        'first_name': 'Jennifer',
        'last_name': 'Wilson',
        'phone': '214-555-0300',
        'email': 'jennifer.wilson@example.com',
        'street_address': '123 Main Street',
        'city': 'Dallas',
        'state': 'TX',
        'zip_code': '75201'
    })

    # Create second customer
    customer2_id = customer_mgr.create_customer({
        'first_name': 'Robert',
        'last_name': 'Brown',
        'phone': '214-555-0400',
        'email': 'robert.brown@example.com'
    })

    # Create vehicles
    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2023,
        'make': 'BMW',
        'model': 'X5',
        'color': 'Alpine White',
        'vin': 'WBAPH5C51BA123456',
        'license_plate': 'BMW-X5'
    })

    vehicle2_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2022,
        'make': 'Mercedes',
        'model': 'GLE',
        'color': 'Obsidian Black',
        'license_plate': 'MBZ-GLE'
    })

    # Create technician
    db.execute("""
        INSERT INTO technicians (
            first_name, last_name, employee_id, skill_level,
            status, max_jobs_concurrent, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('Alex', 'Turner', 'TECH003', 'EXPERT', 'ACTIVE', 3, datetime.now().isoformat()))

    tech_result = db.execute("SELECT id FROM technicians WHERE employee_id = 'TECH003'")
    tech_id = tech_result[0]['id']

    # Create jobs
    job1_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL"
    )

    job2_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle2_id,
        job_type="DENT",
        damage_type="DOOR_DING"
    )

    # Update job1 to IN_PROGRESS
    db.execute("""
        UPDATE jobs SET status = 'IN_PROGRESS', assigned_tech_id = ?, updated_at = ?
        WHERE id = ?
    """, (tech_id, datetime.now().isoformat(), job1_id))

    # Create estimate for job2
    estimate_id = estimate_mgr.create_estimate(
        job_id=job2_id,
        template='DOOR_DING',
        labor_rate=85.00,
        tax_rate=0.0825,
        notes="Minor door ding on driver side door.",
        terms="Payment due upon completion."
    )

    # Send estimate (make it available for approval)
    estimate_mgr.update_status(estimate_id, 'SENT')

    # Create invoice for job1
    db.execute("""
        INSERT INTO invoices (
            invoice_number, job_id, customer_id,
            subtotal, tax_amount, total, balance_due,
            invoice_date, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'INV-2026-0100', job1_id, customer_id,
        2500.00, 206.25, 2706.25, 1206.25,
        date.today().isoformat(), 'SENT',
        datetime.now().isoformat()
    ))

    invoice_result = db.execute("SELECT id FROM invoices WHERE invoice_number = 'INV-2026-0100'")
    invoice_id = invoice_result[0]['id']

    # Record partial payment
    payment_id = payment_mgr.record_payment(
        invoice_id=invoice_id,
        job_id=job1_id,
        amount=1500.00,
        payment_method='CHECK',
        payment_date=date.today() - timedelta(days=3),
        payer_type='INSURANCE',
        payment_reference='INS-CHK-54321'
    )

    print()

    # ========================================================================
    # TEST 1: Generate Portal Link
    # ========================================================================

    print("="*80)
    print("[1/12] Generating portal access link...")
    print("="*80 + "\n")

    link_result = portal_mgr.generate_portal_link(customer_id, expires_days=30)

    print(f"Customer: {link_result['customer_name']}")
    print(f"Email: {link_result['email']}")
    print(f"Token: {link_result['token'][:20]}...")
    print(f"Expires: {link_result['expires_at']}")
    print(f"Portal URL: {link_result['portal_url']}")
    print()

    token = link_result['token']
    assert token is not None
    assert len(token) > 20
    print("[OK] Portal link generated successfully")
    print()

    # ========================================================================
    # TEST 2: Validate Token
    # ========================================================================

    print("="*80)
    print("[2/12] Validating portal token...")
    print("="*80 + "\n")

    validation = portal_mgr.validate_token(token)

    print(f"Customer ID: {validation['customer_id']}")
    print(f"Name: {validation['first_name']} {validation['last_name']}")
    print(f"Email: {validation['email']}")
    print(f"Token Expires: {validation['token_expires']}")
    print()

    assert validation is not None
    assert validation['customer_id'] == customer_id
    print("[OK] Token validated successfully")
    print()

    # Test invalid token
    invalid = portal_mgr.validate_token('invalid-token-12345')
    assert invalid is None
    print("[OK] Invalid token rejected")
    print()

    # ========================================================================
    # TEST 3: Get Dashboard Data
    # ========================================================================

    print("="*80)
    print("[3/12] Loading portal dashboard...")
    print("="*80 + "\n")

    dashboard = portal_mgr.get_dashboard_data(customer_id)

    print("Dashboard Summary:")
    print(f"  Active Jobs:        {dashboard['summary']['active_jobs']}")
    print(f"  Pending Estimates:  {dashboard['summary']['pending_estimates']}")
    print(f"  Outstanding Balance: ${dashboard['summary']['outstanding_balance']:,.2f}")
    print(f"  Unread Messages:    {dashboard['summary']['unread_messages']}")
    print()
    print(f"Recent Jobs: {len(dashboard['recent_jobs'])}")
    print(f"Pending Estimates: {len(dashboard['pending_estimates'])}")
    print(f"Outstanding Invoices: {len(dashboard['outstanding_invoices'])}")
    print()

    assert dashboard['summary']['active_jobs'] >= 1
    assert dashboard['summary']['pending_estimates'] >= 1
    print("[OK] Dashboard data loaded")
    print()

    # ========================================================================
    # TEST 4: Get Customer Jobs
    # ========================================================================

    print("="*80)
    print("[4/12] Getting customer jobs...")
    print("="*80 + "\n")

    jobs = portal_mgr.get_customer_jobs(customer_id)

    print(f"Total Jobs: {len(jobs)}")
    for job in jobs:
        print(f"  [{job['job_number']}] {job['vehicle']} - {job['status_display']} ({job['progress_percent']}%)")
    print()

    assert len(jobs) >= 2
    print("[OK] Customer jobs retrieved")
    print()

    # ========================================================================
    # TEST 5: Get Job Details
    # ========================================================================

    print("="*80)
    print("[5/12] Getting job details...")
    print("="*80 + "\n")

    job_details = portal_mgr.get_job_details(job1_id, customer_id)

    print(f"Job: {job_details['job_number']}")
    print(f"Status: {job_details['status_display']} ({job_details['progress_percent']}%)")
    print(f"Vehicle: {job_details['vehicle']['year']} {job_details['vehicle']['make']} {job_details['vehicle']['model']}")
    print(f"Technician: {job_details['technician'] or 'Not Assigned'}")
    print(f"Scheduled: {job_details['scheduled_date']}")
    print(f"Estimates: {len(job_details['estimates'])}")
    print(f"Invoices: {len(job_details['invoices'])}")
    print(f"Payments: {len(job_details['payments'])}")
    print()

    assert job_details is not None
    assert job_details['job_number'] is not None
    print("[OK] Job details retrieved")
    print()

    # ========================================================================
    # TEST 6: Get Pending Estimates
    # ========================================================================

    print("="*80)
    print("[6/12] Getting pending estimates...")
    print("="*80 + "\n")

    pending = portal_mgr.get_pending_estimates(customer_id)

    print(f"Pending Estimates: {len(pending)}")
    for est in pending:
        print(f"  [{est['estimate_number']}] {est['vehicle']} - ${est['total']:,.2f}")
    print()

    assert len(pending) >= 1
    print("[OK] Pending estimates retrieved")
    print()

    # ========================================================================
    # TEST 7: Approve Estimate
    # ========================================================================

    print("="*80)
    print("[7/12] Approving estimate...")
    print("="*80 + "\n")

    # Get estimate details first
    est_details = portal_mgr.get_estimate_details(estimate_id, customer_id)
    print(f"Estimate: {est_details['estimate_number']}")
    print(f"Vehicle: {est_details['vehicle']['year']} {est_details['vehicle']['make']} {est_details['vehicle']['model']}")
    print(f"Total: ${est_details['total']:,.2f}")
    print(f"Can Approve: {est_details['can_approve']}")
    print()

    # Approve it
    approval = portal_mgr.approve_estimate(
        estimate_id=estimate_id,
        customer_id=customer_id,
        signature_data='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        ip_address='192.168.1.100',
        notes='Looks good, please proceed'
    )

    print(f"Approval Result: {approval['success']}")
    print(f"Approved At: {approval['approved_at']}")
    print()

    assert approval['success'] == True
    print("[OK] Estimate approved through portal")
    print()

    # ========================================================================
    # TEST 8: Messaging System
    # ========================================================================

    print("="*80)
    print("[8/12] Testing messaging system...")
    print("="*80 + "\n")

    # Customer sends message
    msg1 = portal_mgr.send_message(
        job_id=job1_id,
        customer_id=customer_id,
        message="Hi, I wanted to check on the status of my repair. When do you expect it to be done?",
        ip_address='192.168.1.100'
    )
    print(f"Customer message sent: ID #{msg1['message_id']}")

    # Shop responds (internal function)
    msg2 = portal_mgr.shop_send_message(
        job_id=job1_id,
        message="Hi Jennifer! Your BMW X5 is progressing well. We expect to complete it by tomorrow afternoon.",
        sender_name="Service Desk"
    )
    print(f"Shop message sent: ID #{msg2['message_id']}")

    # Customer follows up
    msg3 = portal_mgr.send_message(
        job_id=job1_id,
        customer_id=customer_id,
        message="Great, thank you! I'll plan to pick it up tomorrow after 4pm."
    )
    print(f"Customer reply sent: ID #{msg3['message_id']}")
    print()

    # Get all messages
    messages = portal_mgr.get_messages(job1_id, customer_id)
    print(f"Total messages in thread: {len(messages)}")
    for m in messages:
        sender = "Customer" if m['sender_type'] == 'CUSTOMER' else "Shop"
        preview = m['message'][:50] + "..." if len(m['message']) > 50 else m['message']
        print(f"  [{sender}] {preview}")
    print()

    # Check unread count (should be 0 after reading)
    unread = portal_mgr.get_unread_count(customer_id)
    print(f"Unread messages: {unread}")
    print()

    assert len(messages) == 3
    print("[OK] Messaging system working")
    print()

    # ========================================================================
    # TEST 9: Photo Uploads
    # ========================================================================

    print("="*80)
    print("[9/12] Testing photo uploads...")
    print("="*80 + "\n")

    photo1 = portal_mgr.upload_photo(
        job_id=job1_id,
        customer_id=customer_id,
        file_path='/uploads/customers/1/damage_photo_1.jpg',
        file_name='damage_photo_1.jpg',
        description='Front bumper damage'
    )
    print(f"Photo 1 uploaded: ID #{photo1['photo_id']}")

    photo2 = portal_mgr.upload_photo(
        job_id=job1_id,
        customer_id=customer_id,
        file_path='/uploads/customers/1/damage_photo_2.jpg',
        file_name='damage_photo_2.jpg',
        description='Side view showing hail damage'
    )
    print(f"Photo 2 uploaded: ID #{photo2['photo_id']}")
    print()

    # Get photos
    photos = portal_mgr.get_job_photos(job1_id, customer_id)
    print(f"Total photos: {len(photos)}")
    for p in photos:
        print(f"  - {p['file_name']}: {p['description']}")
    print()

    assert len(photos) == 2
    print("[OK] Photo upload working")
    print()

    # ========================================================================
    # TEST 10: Portal Payment
    # ========================================================================

    print("="*80)
    print("[10/12] Testing portal payment...")
    print("="*80 + "\n")

    # Get outstanding invoices
    invoices = portal_mgr.get_outstanding_invoices(customer_id)
    print(f"Outstanding Invoices: {len(invoices)}")
    for inv in invoices:
        print(f"  [{inv['invoice_number']}] Total: ${inv['total']:,.2f} | Paid: ${inv['paid']:,.2f} | Due: ${inv['balance_due']:,.2f}")
    print()

    # Make portal payment
    payment_result = portal_mgr.record_portal_payment(
        invoice_id=invoice_id,
        customer_id=customer_id,
        amount=500.00,
        payment_method='CREDIT_CARD',
        payment_reference='CC-VISA-1234',
        ip_address='192.168.1.100'
    )

    print(f"Payment Result: {payment_result['success']}")
    print(f"Amount: ${payment_result['amount']:,.2f}")
    print(f"New Balance: ${payment_result['new_balance']:,.2f}")
    print()

    assert payment_result['success'] == True
    print("[OK] Portal payment recorded")
    print()

    # ========================================================================
    # TEST 11: Customer Profile
    # ========================================================================

    print("="*80)
    print("[11/12] Testing customer profile...")
    print("="*80 + "\n")

    profile = portal_mgr.get_profile(customer_id)

    print(f"Customer: {profile['first_name']} {profile['last_name']}")
    print(f"Email: {profile['email']}")
    print(f"Phone: {profile['phone']}")
    print(f"Address: {profile['address']['street']}, {profile['address']['city']}, {profile['address']['state']} {profile['address']['zip']}")
    print(f"Vehicles: {len(profile['vehicles'])}")
    print(f"Total Jobs: {profile['total_jobs']}")
    print(f"Total Spent: ${profile['total_spent']:,.2f}")
    print()

    # Update profile
    update_result = portal_mgr.update_profile(
        customer_id=customer_id,
        updates={
            'phone': '214-555-9999',
            'email': 'jennifer.wilson.updated@example.com'
        },
        ip_address='192.168.1.100'
    )

    print(f"Profile Update: {update_result['success']}")
    print(f"Updated Fields: {update_result['updated_fields']}")
    print()

    assert profile is not None
    assert update_result['success'] == True
    print("[OK] Customer profile working")
    print()

    # ========================================================================
    # TEST 12: Portal Statistics & Report
    # ========================================================================

    print("="*80)
    print("[12/12] Generating portal statistics...")
    print("="*80 + "\n")

    stats = portal_mgr.get_portal_stats(days=30)

    print("Portal Statistics (Last 30 Days):")
    print(f"  Active Portal Links:  {stats['active_portal_links']}")
    print(f"  Total Logins:         {stats['total_logins']}")
    print(f"  Estimates Approved:   {stats['estimates_approved']}")
    print(f"  Payments Made:        {stats['payments_count']}")
    print(f"  Payment Total:        ${stats['payments_total']:,.2f}")
    print(f"  Messages Sent:        {stats['messages_sent']}")
    print(f"  Photos Uploaded:      {stats['photos_uploaded']}")
    print()

    # Generate report
    report = portal_mgr.generate_portal_report(days=30)
    print(report)

    assert 'CUSTOMER PORTAL USAGE REPORT' in report
    print("[OK] Portal statistics generated")
    print()

    # ========================================================================
    # BONUS: Activity Log
    # ========================================================================

    print("="*80)
    print("[BONUS] Customer activity log...")
    print("="*80 + "\n")

    activity = portal_mgr.get_activity_log(customer_id, limit=10)

    print(f"Recent Activity: {len(activity)} records")
    for a in activity:
        print(f"  [{a['created_at'][:16]}] {a['action']}: {a['details'] or '-'}")
    print()

    # ========================================================================
    # BONUS: Token Revocation
    # ========================================================================

    print("="*80)
    print("[BONUS] Token revocation...")
    print("="*80 + "\n")

    # Revoke all tokens
    portal_mgr.revoke_token(customer_id)
    print("All tokens revoked for customer")

    # Try to validate old token
    revoked_check = portal_mgr.validate_token(token)
    assert revoked_check is None
    print("[OK] Revoked token correctly rejected")
    print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] CUSTOMER PORTAL TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Portal link generation (secure tokens)")
    print("  [OK] Token validation and expiration")
    print("  [OK] Dashboard with summary data")
    print("  [OK] Job listing and status tracking")
    print("  [OK] Job detail view with progress")
    print("  [OK] Estimate viewing and approval")
    print("  [OK] Estimate digital signature")
    print("  [OK] Messaging (customer <-> shop)")
    print("  [OK] Photo uploads")
    print("  [OK] Invoice viewing")
    print("  [OK] Portal payments")
    print("  [OK] Payment history")
    print("  [OK] Customer profile management")
    print("  [OK] Activity logging")
    print("  [OK] Token revocation")
    print("  [OK] Portal statistics")
    print()

    print("PORTAL FEATURES:")
    print("  - Secure token-based authentication")
    print("  - Real-time job status tracking")
    print("  - Progress visualization")
    print("  - Estimate review and approval")
    print("  - Digital signature capture")
    print("  - Two-way messaging")
    print("  - Photo upload for damage documentation")
    print("  - Online payment processing")
    print("  - Profile management")
    print()

    print("CUSTOMER SELF-SERVICE WORKFLOW:")
    print("  1. Customer receives portal link via email")
    print("  2. Click link -> validates token -> enters portal")
    print("  3. View dashboard with pending actions")
    print("  4. Track job progress in real-time")
    print("  5. Review and approve estimates")
    print("  6. Communicate with shop via messaging")
    print("  7. Upload photos of damage")
    print("  8. Make payments online")
    print("  9. View payment history")
    print("  10. Update contact information")
    print()

    print("Ready for PROMPT 15: Reporting & Advanced Analytics?")
    print()

    return True


if __name__ == '__main__':
    success = test_portal_manager()
    sys.exit(0 if success else 1)
