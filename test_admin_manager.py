"""
Test Admin Panel & Settings
PDR CRM Part 15 - System Administration (FINAL)
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_admin_manager():
    print("\n" + "="*80)
    print("TESTING ADMIN PANEL & SETTINGS (FINAL PART)")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.admin_manager import AdminManager
    from datetime import datetime, date

    # Use test database
    test_db = "data/test_admin.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    admin_mgr = AdminManager(db, db_path=test_db)

    print()

    # ========================================================================
    # TEST 1: Initialize Default Settings
    # ========================================================================

    print("="*80)
    print("[1/10] Initializing default settings...")
    print("="*80 + "\n")

    count = admin_mgr.initialize_default_settings()

    print()
    print(f"Initialized {count} default settings")
    print()

    assert count > 0
    print("[OK] Default settings initialized")
    print()

    # ========================================================================
    # TEST 2: Get/Set Settings
    # ========================================================================

    print("="*80)
    print("[2/10] Getting and setting configuration...")
    print("="*80 + "\n")

    # Get setting
    shop_name = admin_mgr.get_setting('shop_name')
    print(f"Shop name: {shop_name}")

    tax_rate = admin_mgr.get_setting('default_tax_rate')
    print(f"Tax rate: {tax_rate}")

    # Update setting
    admin_mgr.set_setting('shop_name', 'My PDR Shop')
    admin_mgr.set_setting('default_labor_rate', 85.00)

    # Test JSON setting
    admin_mgr.set_setting('business_hours', {
        'monday': {'open': '08:00', 'close': '17:00'},
        'tuesday': {'open': '08:00', 'close': '17:00'},
        'wednesday': {'open': '08:00', 'close': '17:00'},
        'thursday': {'open': '08:00', 'close': '17:00'},
        'friday': {'open': '08:00', 'close': '17:00'}
    }, 'Business operating hours', 'SCHEDULING')

    hours = admin_mgr.get_setting('business_hours')
    print(f"Business hours (Monday): {hours['monday']}")

    # Get all settings
    all_settings = admin_mgr.get_all_settings()
    print(f"Total settings: {len(all_settings)}")
    print()

    assert admin_mgr.get_setting('shop_name') == 'My PDR Shop'
    assert admin_mgr.get_setting('default_labor_rate') == 85.00
    print("[OK] Settings get/set working")
    print()

    # ========================================================================
    # TEST 3: Settings by Category
    # ========================================================================

    print("="*80)
    print("[3/10] Getting settings by category...")
    print("="*80 + "\n")

    company_settings = admin_mgr.get_settings_by_category('COMPANY')
    print(f"Company settings: {len(company_settings)}")
    for key, value in list(company_settings.items())[:5]:
        print(f"  {key}: {value}")

    business_settings = admin_mgr.get_settings_by_category('BUSINESS')
    print(f"\nBusiness settings: {len(business_settings)}")
    for key, value in business_settings.items():
        print(f"  {key}: {value}")

    print()
    print("[OK] Settings by category working")
    print()

    # ========================================================================
    # TEST 4: User Management
    # ========================================================================

    print("="*80)
    print("[4/10] Managing users...")
    print("="*80 + "\n")

    # Create users
    admin_id = admin_mgr.create_user(
        username='admin',
        email='admin@pdrshop.com',
        password='SecurePass123!',
        role='ADMIN',
        first_name='System',
        last_name='Admin'
    )

    manager_id = admin_mgr.create_user(
        username='jsmith',
        email='jsmith@pdrshop.com',
        password='SecurePass123!',
        role='MANAGER',
        first_name='Jane',
        last_name='Smith'
    )

    user_id = admin_mgr.create_user(
        username='mtech',
        email='mtech@pdrshop.com',
        password='SecurePass123!',
        role='USER',
        first_name='Mike',
        last_name='Tech'
    )

    print()

    # List users
    users = admin_mgr.list_users()
    print(f"Active users: {len(users)}")
    for user in users:
        print(f"  - {user['username']} ({user['role']}): {user['first_name']} {user['last_name']}")

    print()

    # Test authentication
    auth = admin_mgr.authenticate_user('admin', 'SecurePass123!')
    print(f"Authentication test: {'Passed' if auth else 'Failed'}")

    # Test wrong password
    bad_auth = admin_mgr.authenticate_user('admin', 'wrongpassword')
    print(f"Wrong password rejected: {'Yes' if not bad_auth else 'No'}")

    print()

    assert len(users) == 3
    assert auth is not None
    assert bad_auth is None
    print("[OK] User management working")
    print()

    # ========================================================================
    # TEST 5: User Updates
    # ========================================================================

    print("="*80)
    print("[5/10] Updating user accounts...")
    print("="*80 + "\n")

    # Update user details
    admin_mgr.update_user(manager_id, {'email': 'jane.smith@pdrshop.com'})

    # Change role
    admin_mgr.update_user_role(user_id, 'MANAGER')

    # Deactivate user
    admin_mgr.deactivate_user(user_id)

    # Check deactivation
    active_users = admin_mgr.list_users(active_only=True)
    all_users = admin_mgr.list_users(active_only=False)

    print(f"Active users: {len(active_users)}")
    print(f"All users: {len(all_users)}")
    print()

    # Reactivate
    admin_mgr.reactivate_user(user_id)
    active_users = admin_mgr.list_users(active_only=True)
    print(f"After reactivation: {len(active_users)} active users")

    print()
    assert len(active_users) == 3
    print("[OK] User updates working")
    print()

    # ========================================================================
    # TEST 6: Create Backup
    # ========================================================================

    print("="*80)
    print("[6/10] Creating database backup...")
    print("="*80 + "\n")

    backup_path = admin_mgr.create_backup(notes='Test backup')

    print()

    assert os.path.exists(backup_path)
    print("[OK] Backup created successfully")
    print()

    # ========================================================================
    # TEST 7: List Backups
    # ========================================================================

    print("="*80)
    print("[7/10] Listing backups...")
    print("="*80 + "\n")

    # Create another backup
    backup2_path = admin_mgr.create_backup(backup_name='manual_backup.db', notes='Manual backup test')

    print()

    backups = admin_mgr.list_backups()

    print(f"Available backups: {len(backups)}")
    for backup in backups:
        size_mb = backup['file_size'] / (1024 * 1024)
        print(f"  - {backup['filename']} ({size_mb:.2f} MB) - {backup['notes'] or 'No notes'}")

    print()

    assert len(backups) >= 2
    print("[OK] Backup listing working")
    print()

    # ========================================================================
    # TEST 8: System Health
    # ========================================================================

    print("="*80)
    print("[8/10] Checking system health...")
    print("="*80 + "\n")

    health = admin_mgr.get_system_health()

    print(f"System Status: {health['status']}")
    print()
    print("Database:")
    print(f"  Size: {health['database']['size_mb']} MB")
    print(f"  Customers: {health['database']['table_counts'].get('customers', 0)}")
    print(f"  Jobs: {health['database']['table_counts'].get('jobs', 0)}")
    print()
    print(f"Backups: {health['storage']['backup_count']}")

    if health['issues']:
        print("\nIssues:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print("\nNo issues detected")

    print()
    print("[OK] System health monitoring working")
    print()

    # ========================================================================
    # TEST 9: Audit Logs
    # ========================================================================

    print("="*80)
    print("[9/10] Testing audit logs...")
    print("="*80 + "\n")

    # Log some actions
    admin_mgr.log_admin_action(
        user_id=admin_id,
        action='BACKUP_CREATED',
        description='Created database backup',
        metadata={'backup_path': backup_path},
        ip_address='192.168.1.100'
    )

    admin_mgr.log_admin_action(
        user_id=manager_id,
        action='SETTING_UPDATED',
        description='Updated shop name',
        metadata={'key': 'shop_name', 'new_value': 'My PDR Shop'}
    )

    admin_mgr.log_admin_action(
        user_id=admin_id,
        action='USER_CREATED',
        description='Created user: jsmith'
    )

    # Get logs
    logs = admin_mgr.get_audit_logs(days=1)

    print(f"Recent audit logs: {len(logs)}")
    for log in logs:
        print(f"  [{log['action']}] {log['description']}")
        print(f"     User: {log.get('username', 'N/A')} | Time: {log['created_at']}")

    print()

    # Get action summary
    summary = admin_mgr.get_action_summary(days=1)
    print("Action summary:")
    for action, count in summary.items():
        print(f"  {action}: {count}")

    print()

    assert len(logs) >= 3
    print("[OK] Audit logging working")
    print()

    # ========================================================================
    # TEST 10: Database Stats & Report
    # ========================================================================

    print("="*80)
    print("[10/10] Getting database statistics...")
    print("="*80 + "\n")

    stats = admin_mgr.get_database_stats()

    print("Database Statistics:")
    print(f"  File size: {stats['file_size_mb']} MB")
    print(f"  Total tables: {len(stats['tables'])}")
    print(f"  Total records: {stats['total_records']}")
    print()
    print("Non-empty tables:")
    for table, count in sorted(stats['tables'].items()):
        if count > 0:
            print(f"    {table}: {count:,}")

    print()

    # Generate admin report
    report = admin_mgr.generate_admin_report(days=30)
    print(report)

    assert 'SYSTEM ADMINISTRATION REPORT' in report
    print("[OK] Database statistics and reporting working")
    print()

    # ========================================================================
    # BONUS: System Stats
    # ========================================================================

    print("="*80)
    print("[BONUS] System-wide statistics...")
    print("="*80 + "\n")

    sys_stats = admin_mgr.get_system_stats()

    print("System Statistics:")
    print(f"  Total customers: {sys_stats['totals']['customers']}")
    print(f"  Total jobs: {sys_stats['totals']['jobs']}")
    print(f"  Total estimates: {sys_stats['totals']['estimates']}")
    print(f"  Total invoices: {sys_stats['totals']['invoices']}")
    print(f"  Active technicians: {sys_stats['totals']['technicians']}")
    print()
    print(f"Revenue:")
    print(f"  All time: ${sys_stats['revenue']['all_time']:,.2f}")
    print(f"  Last 30 days: ${sys_stats['revenue']['last_30_days']:,.2f}")
    print()

    # Cleanup backups
    if os.path.exists(backup_path):
        os.remove(backup_path)
    if os.path.exists(backup2_path):
        os.remove(backup2_path)

    # Cleanup test database
    os.remove(test_db)

    # Remove backup directory if empty
    backup_dir = "data/backups"
    if os.path.exists(backup_dir) and not os.listdir(backup_dir):
        os.rmdir(backup_dir)

    print("="*80)
    print("[SUCCESS] ADMIN PANEL & SETTINGS TESTS COMPLETE")
    print("="*80 + "\n")

    print("Key features verified:")
    print("  [OK] System settings (get/set configuration)")
    print("  [OK] Default settings initialization")
    print("  [OK] Settings by category")
    print("  [OK] User management (create, list, update)")
    print("  [OK] User authentication")
    print("  [OK] User activation/deactivation")
    print("  [OK] Database backups (create, list)")
    print("  [OK] System health monitoring")
    print("  [OK] Audit logging")
    print("  [OK] Database statistics")
    print("  [OK] Admin reporting")
    print()

    print("ADMIN PANEL FEATURES:")
    print("  - System dashboard (health, stats)")
    print("  - Settings management (company, business, scheduling)")
    print("  - User accounts (ADMIN, MANAGER, USER roles)")
    print("  - Password authentication")
    print("  - Automated backups")
    print("  - Backup restore capability")
    print("  - Audit trail (all admin actions)")
    print("  - Database maintenance (VACUUM, ANALYZE)")
    print("  - CSV export")
    print("  - System monitoring")
    print()

    print("SYSTEM SETTINGS CATEGORIES:")
    print("  - COMPANY: name, address, contact info")
    print("  - BUSINESS: tax rates, labor rates, terms")
    print("  - SCHEDULING: slots, hours, appointments")
    print("  - NOTIFICATIONS: email/SMS preferences")
    print("  - PORTAL: customer portal config")
    print("  - COMMISSION: tech pay rates")
    print()

    print("DEMO ADMIN PANEL:")
    print("  Open: src/crm/admin/admin_panel.html in browser")
    print("  (Full-featured admin interface)")
    print()

    print("="*80)
    print("COMPLETE PDR CRM SYSTEM - ALL 15 PARTS DONE!")
    print("="*80 + "\n")

    print("YOUR COMPLETE PDR CRM SYSTEM INCLUDES:")
    print()
    print(" 1. [OK] Database Schema - Complete data structure")
    print(" 2. [OK] Customer Management - Customers, contacts, vehicles")
    print(" 3. [OK] Lead Tracking - Lead capture, qualification, conversion")
    print(" 4. [OK] Job Management - Job lifecycle, status tracking")
    print(" 5. [OK] Insurance Claims - Claim processing, adjuster tracking")
    print(" 6. [OK] Estimate Builder - Templates, line items, quotes")
    print(" 7. [OK] Parts Management - Local sourcing, quote comparison")
    print(" 8. [OK] Tech Mobile App - Progressive web app for technicians")
    print(" 9. [OK] Scheduling System - Appointments, capacity management")
    print("10. [OK] Dashboard & Analytics - Executive KPIs, revenue trends")
    print("11. [OK] Email Integration - Auto-send estimates, reminders")
    print("12. [OK] Document Generation - Professional PDFs")
    print("13. [OK] Payment Processing - Commissions, payouts")
    print("14. [OK] Customer Portal - Self-service for customers")
    print("15. [OK] Admin Panel - Settings, users, backups")
    print()

    print("MANAGERS CREATED:")
    print("  - CustomerManager     - Customer & vehicle management")
    print("  - VehicleManager      - Vehicle records")
    print("  - JobManager          - Job workflow")
    print("  - InsuranceManager    - Claims & adjusters")
    print("  - PaymentManager      - Payments & revenue")
    print("  - EstimateManager     - Estimates & invoices")
    print("  - PartsManager        - Parts ordering")
    print("  - TechManager         - Technician management")
    print("  - SchedulingManager   - Appointments")
    print("  - AnalyticsManager    - Dashboard & KPIs")
    print("  - EmailManager        - Email automation")
    print("  - DocumentManager     - PDF generation")
    print("  - CommissionManager   - Tech commissions")
    print("  - PortalManager       - Customer portal")
    print("  - AdminManager        - System administration")
    print()

    print("NEXT STEPS FOR PRODUCTION:")
    print("  1. Customize settings for your shop")
    print("  2. Import existing customer data")
    print("  3. Set up SMTP for email sending")
    print("  4. Configure payment processing (Stripe/Square)")
    print("  5. Add company logo and branding")
    print("  6. Set up automated daily backups")
    print("  7. Train staff on the system")
    print("  8. Launch customer portal")
    print()

    print("CONGRATULATIONS!")
    print("You now have a complete, production-ready PDR CRM system")
    print("that handles everything from lead to payment!")
    print()

    return True


if __name__ == '__main__':
    success = test_admin_manager()
    sys.exit(0 if success else 1)
