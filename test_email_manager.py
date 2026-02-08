"""
Test Email Integration & Automation
PDR CRM Part 11 - Email Templates and Automation
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_email_manager():
    print("\n" + "="*80)
    print("TESTING EMAIL INTEGRATION & AUTOMATION")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.email_manager import EmailManager
    from src.crm.managers.estimate_manager import EstimateManager
    from src.crm.managers.job_manager import JobManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from src.crm.managers.scheduling_manager import SchedulingManager
    from datetime import datetime, date, timedelta

    # Use test database
    test_db = "data/test_email.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    email_mgr = EmailManager(db)
    estimate_mgr = EstimateManager(db)
    job_mgr = JobManager(db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)
    schedule_mgr = SchedulingManager(db)

    # Create test data
    print("\nSetting up test data...")

    customer_id = customer_mgr.create_customer({
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '214-555-0100',
        'email': 'john.doe@example.com'
    })

    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2022,
        'make': 'Toyota',
        'model': 'Camry',
        'color': 'Silver'
    })

    job_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL"
    )

    # Create estimate
    estimate_id = estimate_mgr.create_estimate(
        job_id=job_id,
        template='HAIL_BASIC',
        labor_rate=85.00,
        tax_rate=0.0825
    )

    print()

    # ========================================================================
    # TEST 1: List Templates
    # ========================================================================

    print("="*80)
    print("[1/9] Listing email templates...")
    print("="*80 + "\n")

    templates = email_mgr.list_templates()

    print(f"Available Email Templates: {len(templates)}")
    for template in templates:
        preview = email_mgr.get_template_preview(template)
        print(f"  - {template}")
        print(f"    Variables: {', '.join(preview['required_variables'][:5])}...")
    print()

    assert len(templates) >= 6
    print(f"[OK] Found {len(templates)} templates")
    print()

    # ========================================================================
    # TEST 2: Render Template
    # ========================================================================

    print("="*80)
    print("[2/9] Rendering email template...")
    print("="*80 + "\n")

    rendered = email_mgr.render_template(
        'ESTIMATE_DELIVERY',
        {
            'customer_name': 'John Doe',
            'vehicle_description': '2022 Toyota Camry',
            'estimate_number': 'EST-2026-0001',
            'estimate_total': '750.00',
            'estimate_expires_days': '30'
        }
    )

    print("Rendered Email:")
    print("-" * 60)
    print(f"Subject: {rendered['subject']}")
    print()
    print(rendered['body'][:500] + "...")
    print("-" * 60)
    print()

    assert 'John Doe' in rendered['body']
    assert '2022 Toyota Camry' in rendered['subject']
    print("[OK] Template rendered correctly")
    print()

    # ========================================================================
    # TEST 3: Send Manual Email
    # ========================================================================

    print("="*80)
    print("[3/9] Sending manual email...")
    print("="*80 + "\n")

    manual_id = email_mgr.send_email(
        to_email='john.doe@example.com',
        to_name='John Doe',
        subject='Custom message about your repair',
        body="""Hello John,

I wanted to personally reach out to let you know we're working on your vehicle.

Everything is going smoothly and we should have it ready by end of day tomorrow.

Thanks!
Mike""",
        job_id=job_id,
        customer_id=customer_id
    )

    assert manual_id is not None
    print()
    print(f"[OK] Manual email sent (ID: {manual_id})")
    print()

    # ========================================================================
    # TEST 4: Send from Template
    # ========================================================================

    print("="*80)
    print("[4/9] Sending email from template...")
    print("="*80 + "\n")

    template_email_id = email_mgr.send_from_template(
        template_name='THANK_YOU',
        to_email='john.doe@example.com',
        to_name='John Doe',
        variables={
            'customer_name': 'John Doe',
            'vehicle_description': '2022 Toyota Camry'
        },
        job_id=job_id,
        customer_id=customer_id
    )

    assert template_email_id is not None
    print()
    print(f"[OK] Template email sent (ID: {template_email_id})")
    print()

    # ========================================================================
    # TEST 5: Send Estimate Email
    # ========================================================================

    print("="*80)
    print("[5/9] Sending estimate email...")
    print("="*80 + "\n")

    estimate_email_id = email_mgr.send_estimate_email(estimate_id)

    assert estimate_email_id is not None
    print()

    # Verify estimate was updated
    estimate = estimate_mgr.get_estimate(estimate_id)
    assert estimate['sent_date'] is not None
    print(f"[OK] Estimate email sent (ID: {estimate_email_id})")
    print(f"     Estimate marked as sent: {estimate['sent_date']}")
    print()

    # ========================================================================
    # TEST 6: Schedule Appointment Reminder
    # ========================================================================

    print("="*80)
    print("[6/9] Scheduling appointment reminder...")
    print("="*80 + "\n")

    # First, schedule a drop-off appointment
    tomorrow = date.today() + timedelta(days=1)
    # Skip Sunday
    while tomorrow.weekday() == 6:
        tomorrow += timedelta(days=1)

    apt_id = schedule_mgr.schedule_appointment(
        appointment_type='DROP_OFF',
        appointment_date=tomorrow,
        start_time='09:00',
        job_id=job_id,
        customer_id=customer_id,
        vehicle_id=vehicle_id
    )
    print()

    # Update job with scheduled drop-off
    drop_off_datetime = datetime.combine(tomorrow, datetime.strptime('09:00', '%H:%M').time())
    db.execute("""
        UPDATE jobs SET scheduled_drop_off = ?, updated_at = ? WHERE id = ?
    """, (drop_off_datetime.isoformat(), datetime.now().isoformat(), job_id))

    # Schedule reminder (24 hours before - will send immediately since it's less than 24h away)
    reminder_id = email_mgr.send_appointment_reminder(
        job_id=job_id,
        hours_before=24
    )

    assert reminder_id is not None
    print()
    print(f"[OK] Appointment reminder scheduled (ID: {reminder_id})")
    print()

    # ========================================================================
    # TEST 7: Send Ready for Pickup
    # ========================================================================

    print("="*80)
    print("[7/9] Sending ready for pickup notification...")
    print("="*80 + "\n")

    # Create invoice first
    db.execute("""
        INSERT INTO invoices (
            invoice_number, job_id, customer_id,
            subtotal, tax_amount, total, balance_due,
            invoice_date, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'INV-2026-0001', job_id, customer_id,
        750.00, 61.88, 811.88, 811.88,
        date.today().isoformat(), 'SENT',
        datetime.now().isoformat()
    ))

    pickup_id = email_mgr.send_ready_for_pickup(job_id)

    assert pickup_id is not None
    print()
    print(f"[OK] Ready for pickup notification sent (ID: {pickup_id})")
    print()

    # ========================================================================
    # TEST 8: Email History
    # ========================================================================

    print("="*80)
    print("[8/9] Getting email history...")
    print("="*80 + "\n")

    history = email_mgr.get_email_history(customer_id=customer_id)

    print(f"Email History for Customer #{customer_id}: {len(history)} email(s)")
    print()
    for email in history:
        sent_time = email['sent_at'] or email['created_at']
        print(f"  [{email['status']}] {email['subject'][:50]}...")
        print(f"    To: {email['to_email']}")
        if email['template_name']:
            print(f"    Template: {email['template_name']}")
        print()

    assert len(history) >= 5
    print(f"[OK] Retrieved {len(history)} emails in history")
    print()

    # ========================================================================
    # TEST 9: Email Statistics
    # ========================================================================

    print("="*80)
    print("[9/9] Getting email statistics...")
    print("="*80 + "\n")

    stats = email_mgr.get_email_stats(days=30)

    print(f"Email Statistics (Last 30 Days):")
    print(f"  Total sent: {stats['sent']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Open rate: {stats['open_rate']}%")
    print()
    print(f"  By status:")
    for status, count in stats.get('by_status', {}).items():
        print(f"    {status}: {count}")
    print()
    if stats.get('by_template'):
        print(f"  By template:")
        for template, count in stats['by_template'].items():
            print(f"    {template}: {count}")
    print()

    print("[OK] Statistics retrieved")
    print()

    # ========================================================================
    # BONUS: Email Report
    # ========================================================================

    print("="*80)
    print("[BONUS] Generating email report...")
    print("="*80 + "\n")

    report = email_mgr.generate_email_report(days=30)
    print(report)
    print()

    # ========================================================================
    # BONUS: Process Queue
    # ========================================================================

    print("="*80)
    print("[BONUS] Processing email queue...")
    print("="*80 + "\n")

    # Schedule an email for the future
    future_email_id = email_mgr.send_email(
        to_email='john.doe@example.com',
        subject='Future email test',
        body='This email was scheduled for the future.',
        send_at=datetime.now() + timedelta(hours=1)
    )
    print()

    # Check pending count
    stats = email_mgr.get_email_stats()
    print(f"Pending emails before processing: {stats['pending']}")

    # Process queue (won't send future-scheduled email)
    sent = email_mgr.process_email_queue()
    print()

    print(f"[OK] Queue processing complete")
    print()

    # Cleanup
    os.remove(test_db)

    print("="*80)
    print("[SUCCESS] EMAIL INTEGRATION TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] Email templates (6 templates)")
    print("  [OK] Template rendering (variable substitution)")
    print("  [OK] Manual email sending")
    print("  [OK] Send from template")
    print("  [OK] Automated estimate emails")
    print("  [OK] Appointment reminders (scheduled)")
    print("  [OK] Ready for pickup notifications")
    print("  [OK] Email history tracking")
    print("  [OK] Email statistics")
    print("  [OK] Queue processing")
    print()

    print("EMAIL TEMPLATES:")
    print("  - ESTIMATE_DELIVERY - Send estimates to customers")
    print("  - APPOINTMENT_REMINDER - 24hr before drop-off")
    print("  - READY_FOR_PICKUP - Job complete notification")
    print("  - INSURANCE_CLAIM_UPDATE - Claim status updates")
    print("  - FOLLOW_UP_LEAD - Lead follow-up sequences")
    print("  - THANK_YOU - Post-service thank you")
    print()

    print("AUTOMATION FEATURES:")
    print("  - Auto-send estimates when created")
    print("  - Schedule reminders before appointments")
    print("  - Notify when ready for pickup")
    print("  - Track all email history per customer/job")
    print("  - Queue management (send later)")
    print()

    print("Ready for PROMPT 12: Document Generation (PDF)?")
    print()

    return True


if __name__ == '__main__':
    success = test_email_manager()
    sys.exit(0 if success else 1)
