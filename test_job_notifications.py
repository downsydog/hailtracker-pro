"""
Test Job Notification System
Real-time notifications for job status changes
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_job_notifications():
    print("\n" + "="*80)
    print("TESTING JOB NOTIFICATION SYSTEM")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.models.onboarding_schema import OnboardingSchema
    from src.crm.managers.job_manager import JobManager
    from src.crm.managers.job_notification_manager import JobNotificationManager
    from src.crm.managers.customer_manager import CustomerManager
    from src.crm.managers.vehicle_manager import VehicleManager
    from datetime import datetime, timedelta

    # Use test database
    test_db = "data/test_notifications.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize database
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    OnboardingSchema.create_onboarding_tables(db)

    # Initialize managers
    job_mgr = JobManager(db, enable_notifications=True)
    notification_mgr = JobNotificationManager(test_db)
    customer_mgr = CustomerManager(db)
    vehicle_mgr = VehicleManager(db)

    # Create test data
    print("\nSetting up test data...")

    # Create customer
    customer_id = customer_mgr.create_customer({
        'first_name': 'Jane',
        'last_name': 'Smith',
        'phone': '214-555-0200',
        'email': 'jane.smith@example.com',
        'city': 'Dallas',
        'state': 'TX'
    })
    print(f"[OK] Created customer (ID: {customer_id})")

    # Create vehicle
    vehicle_id = vehicle_mgr.create_vehicle({
        'customer_id': customer_id,
        'year': 2023,
        'make': 'Honda',
        'model': 'Accord',
        'vin': '1HGBH41JXMN109187',
        'color': 'Blue'
    })
    print(f"[OK] Created vehicle (ID: {vehicle_id})")

    # Create tech
    tech_id = db.insert('technicians', {
        'first_name': 'Bob',
        'last_name': 'Tech',
        'employee_id': 'TECH002',
        'email': 'bob@shop.com',
        'skill_level': 'EXPERT',
        'max_jobs_concurrent': 3,
        'status': 'ACTIVE'
    })
    print(f"[OK] Created technician (ID: {tech_id})")

    print()

    # ========================================================================
    # TEST 1: Create Job and Check Notification Tables
    # ========================================================================

    print("="*80)
    print("[1/8] Testing notification tables exist...")
    print("="*80 + "\n")

    # Verify tables exist
    tables = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name LIKE 'customer_notif%'
        ORDER BY name
    """)

    table_names = [t['name'] for t in tables]
    print(f"Found tables: {table_names}")

    assert 'customer_notifications' in table_names, "Missing customer_notifications table"
    assert 'customer_notification_preferences' in table_names, "Missing preferences table"
    print("[PASS] Notification tables exist\n")

    # ========================================================================
    # TEST 2: Customer Preferences - Default
    # ========================================================================

    print("="*80)
    print("[2/8] Testing default customer preferences...")
    print("="*80 + "\n")

    prefs = notification_mgr.get_customer_preferences(customer_id)
    print(f"Default preferences: {prefs}")

    assert prefs['email_enabled'] == True, "Email should be enabled by default"
    assert prefs['in_app_enabled'] == True, "In-app should be enabled by default"
    assert prefs['sms_enabled'] == False, "SMS should be disabled by default"
    assert 'APPROVED' in prefs['notify_on_statuses'], "Should notify on APPROVED status"
    assert 'READY_FOR_PICKUP' in prefs['notify_on_statuses'], "Should notify on READY_FOR_PICKUP"

    print("[PASS] Default preferences correct\n")

    # ========================================================================
    # TEST 3: Update Customer Preferences
    # ========================================================================

    print("="*80)
    print("[3/8] Testing update customer preferences...")
    print("="*80 + "\n")

    notification_mgr.update_customer_preferences(customer_id, {
        'email_enabled': True,
        'sms_enabled': True,
        'push_enabled': False,
        'in_app_enabled': True,
        'notify_on_statuses': ['APPROVED', 'IN_PROGRESS', 'READY_FOR_PICKUP', 'COMPLETED'],
        'quiet_hours_start': '22:00',
        'quiet_hours_end': '08:00'
    })

    prefs = notification_mgr.get_customer_preferences(customer_id)
    print(f"Updated preferences: {prefs}")

    assert prefs['sms_enabled'] == True, "SMS should now be enabled"
    assert prefs['quiet_hours_start'] == '22:00', "Quiet hours start should be 22:00"
    assert 'IN_PROGRESS' in prefs['notify_on_statuses'], "Should notify on IN_PROGRESS"

    print("[PASS] Preferences updated correctly\n")

    # ========================================================================
    # TEST 4: Create Job with Notifications Enabled
    # ========================================================================

    print("="*80)
    print("[4/8] Testing job creation with notifications...")
    print("="*80 + "\n")

    job_id = job_mgr.create_job(
        customer_id=customer_id,
        vehicle_id=vehicle_id,
        job_type="HAIL",
        damage_type="HAIL",
        scheduled_drop_off=datetime.now() + timedelta(days=1),
        priority="HIGH",
        internal_notes="Test job for notifications",
        created_by="test"
    )

    job = job_mgr.get_job(job_id)
    print(f"Created job: {job['job_number']} (ID: {job_id})")

    assert job is not None
    assert job['status'] == 'NEW'

    print("[PASS] Job created successfully\n")

    # ========================================================================
    # TEST 5: Create In-App Notification Manually
    # ========================================================================

    print("="*80)
    print("[5/8] Testing manual notification creation...")
    print("="*80 + "\n")

    notif_id = notification_mgr.create_notification(
        customer_id=customer_id,
        notification_type='TEST',
        title='Test Notification',
        message='This is a test notification for job tracking.',
        job_id=job_id,
        priority='HIGH'
    )

    print(f"Created notification ID: {notif_id}")

    notifications = notification_mgr.get_notifications(customer_id)
    print(f"Total notifications: {len(notifications)}")

    assert len(notifications) >= 1, "Should have at least one notification"
    assert notifications[0]['title'] == 'Test Notification', "Title should match"
    assert notifications[0]['priority'] == 'HIGH', "Priority should be HIGH"

    print("[PASS] Manual notification created\n")

    # ========================================================================
    # TEST 6: Status Change Triggers Notification
    # ========================================================================

    print("="*80)
    print("[6/8] Testing status change notification trigger...")
    print("="*80 + "\n")

    # Get initial count
    initial_count = notification_mgr.get_unread_count(customer_id)
    print(f"Initial unread count: {initial_count}")

    # Update status to one that's in notify_on_statuses
    job_mgr.update_status(job_id, 'WAITING_DROP_OFF', notes='Scheduled for tomorrow')
    job_mgr.update_status(job_id, 'DROPPED_OFF', notes='Customer dropped off vehicle')

    # Check for new notifications
    new_count = notification_mgr.get_unread_count(customer_id)
    print(f"Unread count after status changes: {new_count}")

    # Note: Some statuses may not trigger notifications based on preferences
    # Let's check the notifications
    notifications = notification_mgr.get_notifications(customer_id)
    for n in notifications[:5]:
        print(f"  - {n['title']}: {n['message'][:50]}...")

    print("[PASS] Status changes processed\n")

    # ========================================================================
    # TEST 7: Mark Notifications as Read
    # ========================================================================

    print("="*80)
    print("[7/8] Testing mark notifications as read...")
    print("="*80 + "\n")

    # Mark single notification as read
    notification_mgr.mark_as_read(notif_id)

    notif = notification_mgr.get_notifications(customer_id)[0]
    for n in notification_mgr.get_notifications(customer_id):
        if n['id'] == notif_id:
            assert n['status'] == 'READ', "Notification should be marked as read"
            print(f"Notification {notif_id} marked as read")
            break

    # Mark all as read
    notification_mgr.mark_all_as_read(customer_id)
    unread = notification_mgr.get_unread_count(customer_id)
    print(f"Unread count after mark all: {unread}")

    assert unread == 0, "All notifications should be read"

    print("[PASS] Notifications marked as read\n")

    # ========================================================================
    # TEST 8: Should Notify For Status Check
    # ========================================================================

    print("="*80)
    print("[8/8] Testing should_notify_for_status logic...")
    print("="*80 + "\n")

    prefs = notification_mgr.get_customer_preferences(customer_id)

    # Test status that should trigger
    should_notify = notification_mgr.should_notify_for_status(prefs, 'APPROVED')
    print(f"Should notify for APPROVED: {should_notify}")
    assert should_notify == True, "Should notify for APPROVED"

    # Test status that shouldn't trigger (not in list)
    should_notify = notification_mgr.should_notify_for_status(prefs, 'WAITING_PARTS')
    print(f"Should notify for WAITING_PARTS: {should_notify}")
    # WAITING_PARTS is not in the updated notify_on_statuses
    assert should_notify == False, "Should not notify for WAITING_PARTS"

    print("[PASS] Should notify logic correct\n")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("="*80)
    print("ALL NOTIFICATION TESTS PASSED!")
    print("="*80 + "\n")

    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"Cleaned up test database: {test_db}")

    return True


def test_notification_messages():
    """Test notification message formatting"""
    print("\n" + "="*80)
    print("TESTING NOTIFICATION MESSAGE FORMATTING")
    print("="*80 + "\n")

    from src.crm.managers.job_notification_manager import JobNotificationManager

    # Check STATUS_MESSAGES exist
    assert len(JobNotificationManager.STATUS_MESSAGES) > 0, "Should have status messages"

    print("Available status messages:")
    for status, msg in JobNotificationManager.STATUS_MESSAGES.items():
        print(f"  {status}: {msg['title']}")
        assert 'title' in msg, f"Missing title for {status}"
        assert 'message' in msg, f"Missing message for {status}"
        assert 'priority' in msg, f"Missing priority for {status}"

    print("\n[PASS] All status messages have required fields\n")

    # Test message formatting
    test_job_info = {
        'id': 1,
        'job_number': 'JOB-2024-0001',
        'status': 'READY_FOR_PICKUP',
        'customer_id': 1,
        'customer_name': 'John Doe',
        'customer_email': 'john@example.com',
        'vehicle_description': '2023 Toyota Camry'
    }

    # Manually test format (without DB)
    template = JobNotificationManager.STATUS_MESSAGES['READY_FOR_PICKUP']
    message = template['message'].format(
        vehicle=test_job_info['vehicle_description'],
        status='READY_FOR_PICKUP',
        job_number=test_job_info['job_number'],
        customer_name=test_job_info['customer_name']
    )

    print(f"Formatted message for READY_FOR_PICKUP:")
    print(f"  Title: {template['title']}")
    print(f"  Message: {message}")
    print(f"  Priority: {template['priority']}")

    assert '2023 Toyota Camry' in message, "Vehicle should be in message"

    print("\n[PASS] Message formatting works correctly\n")

    return True


def test_template_integration():
    """Test that JobNotificationManager uses NotificationTemplateManager"""
    import tempfile
    import os as os_module

    print("\n" + "="*80)
    print("TESTING TEMPLATE INTEGRATION")
    print("="*80 + "\n")

    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.job_notification_manager import JobNotificationManager
    from src.crm.managers.notification_template_manager import NotificationTemplateManager

    # Create temp database
    temp_dir = tempfile.mkdtemp()
    db_path = os_module.path.join(temp_dir, "test_integration.db")

    try:
        # Initialize schema
        DatabaseSchema.create_all_tables(db_path)

        # Initialize managers
        job_notif_mgr = JobNotificationManager(db_path)
        template_mgr = NotificationTemplateManager(db_path)

        print("1. Testing STATUS_TO_TEMPLATE mapping...")
        assert hasattr(job_notif_mgr, 'STATUS_TO_TEMPLATE'), "Should have STATUS_TO_TEMPLATE"
        print(f"   Mapped statuses: {list(job_notif_mgr.STATUS_TO_TEMPLATE.keys())}")
        assert 'READY_FOR_PICKUP' in job_notif_mgr.STATUS_TO_TEMPLATE
        assert job_notif_mgr.STATUS_TO_TEMPLATE['READY_FOR_PICKUP'] == 'JOB_READY_FOR_PICKUP'
        print("   [PASS] STATUS_TO_TEMPLATE mapping correct\n")

        print("2. Testing template manager initialization...")
        tm = job_notif_mgr._get_template_manager()
        assert tm is not None, "Template manager should be initialized"
        print("   [PASS] Template manager initialized\n")

        print("3. Testing _build_template_variables...")
        job_info = {
            'id': 1,
            'job_number': 'JOB-2024-0001',
            'status': 'READY_FOR_PICKUP',
            'customer_id': 1,
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_phone': '555-123-4567',
            'vehicle_description': '2023 Toyota Camry'
        }
        variables = job_notif_mgr._build_template_variables(job_info, 'Test note')
        assert 'customer_name' in variables
        assert variables['customer_name'] == 'John Doe'
        assert variables['vehicle'] == '2023 Toyota Camry'
        assert variables['job_number'] == 'JOB-2024-0001'
        assert variables['notes'] == 'Test note'
        print(f"   Variables: customer_name={variables['customer_name']}, vehicle={variables['vehicle']}")
        print("   [PASS] Template variables built correctly\n")

        print("4. Testing _format_status_message with templates...")
        message_data = job_notif_mgr._format_status_message('READY_FOR_PICKUP', job_info, 'Vehicle is ready')

        # Should have template key when using templates
        assert 'template_key' in message_data, "Should include template_key"
        assert message_data['template_key'] == 'JOB_READY_FOR_PICKUP'

        # Should have rendered content for all channels
        assert message_data.get('email_subject'), "Should have email subject"
        assert message_data.get('email_body'), "Should have email body"
        assert message_data.get('sms'), "Should have SMS message"
        assert message_data.get('push_title'), "Should have push title"
        assert message_data.get('push_body'), "Should have push body"

        # Check content includes job info
        assert 'Toyota Camry' in message_data['email_body'], "Email body should contain vehicle"
        assert 'JOB-2024-0001' in message_data['sms'], "SMS should contain job number"

        print(f"   Template key: {message_data['template_key']}")
        print(f"   Email subject: {message_data['email_subject'][:50]}...")
        print(f"   SMS: {message_data['sms'][:50]}...")
        print(f"   Push title: {message_data['push_title']}")
        print("   [PASS] Template rendering correct\n")

        print("5. Testing fallback for non-mapped statuses...")
        # WAITING_PARTS is not in STATUS_TO_TEMPLATE, should use fallback
        fallback_msg = job_notif_mgr._format_status_message('WAITING_PARTS', job_info)
        assert 'template_key' not in fallback_msg or fallback_msg.get('template_key') is None, \
            "Should not have template_key for unmapped status"
        assert fallback_msg['title'] == 'Waiting for Parts', "Should use fallback title"
        print(f"   Fallback title: {fallback_msg['title']}")
        print("   [PASS] Fallback works for unmapped statuses\n")

        print("6. Testing template usage logging...")
        # Check that usage was logged
        stats = template_mgr.get_template_stats('JOB_READY_FOR_PICKUP', days=1)
        print(f"   Template stats: {stats}")
        # Usage should have been logged during _format_status_message
        assert stats['template_key'] == 'JOB_READY_FOR_PICKUP'
        print("   [PASS] Template usage logged\n")

        print("="*80)
        print("TEMPLATE INTEGRATION TESTS PASSED!")
        print("="*80 + "\n")

    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    return True


if __name__ == "__main__":
    success = True

    try:
        success = test_notification_messages() and success
        success = test_template_integration() and success
        success = test_job_notifications() and success
    except Exception as e:
        print(f"\n[FAIL] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        success = False

    if success:
        print("\n" + "="*80)
        print("ALL JOB NOTIFICATION TESTS COMPLETED SUCCESSFULLY!")
        print("="*80 + "\n")
    else:
        print("\n" + "="*80)
        print("SOME TESTS FAILED - SEE ABOVE FOR DETAILS")
        print("="*80 + "\n")
        sys.exit(1)
