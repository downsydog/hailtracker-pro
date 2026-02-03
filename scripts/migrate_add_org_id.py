"""
Migration Script: Add organization_id to All Data Tables
Adds multi-tenant support to existing tables by adding organization_id column.

This script:
1. Adds organization_id column to tables that need it
2. Creates indexes for performance
3. Does NOT drop any existing data
4. Is idempotent (safe to run multiple times)

Usage:
    python scripts/migrate_add_org_id.py [database_path]
"""

import sqlite3
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Tables that need organization_id
TABLES_TO_MIGRATE = [
    'customers',
    'vehicles',
    'leads',
    'jobs',
    'job_status_history',
    'technicians',
    'insurance_claims',
    'email_tracking',
    'parts',
    'part_orders',
    'part_quotes',
    'estimates',
    'invoices',
    'payments',
    'communications',
    'documents',
    'hail_events',
    # Onboarding tables
    'enrollment_sessions',
    'enrollment_photos',
    'customer_insurance',
    'customer_signatures',
    # Portal tables
    'portal_credentials',
    'customer_portal_access',
    'customer_portal_logins',
    'customer_referrals',
    'referral_link_clicks',
    'referral_commission_payments',
    'customer_documents',
    'customer_communications',
    # Notification tables
    'customer_notification_preferences',
    'customer_notifications',
    'notification_templates',
    'template_usage_log',
    # Push/SMS tables
    'push_subscriptions',
    'sms_messages',
    # Marketing tables
    'digital_flyers',
    'personalized_flyers',
    'flyer_views',
    'flyer_campaigns',
    # Estimating tables
    'estimate_templates',
    'estimate_line_items',
    'insurance_matrix',
    'comparable_estimates',
    'estimate_alerts',
    'ri_items',
]


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col[1] == column_name for col in columns)


def table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def index_exists(cursor, index_name):
    """Check if an index exists"""
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name=?
    """, (index_name,))
    return cursor.fetchone() is not None


def add_organization_id_column(cursor, table_name):
    """Add organization_id column to a table"""
    if not table_exists(cursor, table_name):
        print(f"  [SKIP] Table {table_name} does not exist")
        return False

    if column_exists(cursor, table_name, 'organization_id'):
        print(f"  [OK] {table_name} already has organization_id")
        return True

    try:
        # Add the column with a default of NULL initially
        # (We'll set a default org later during data migration)
        cursor.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN organization_id INTEGER REFERENCES organizations(id)
        """)
        print(f"  [+] Added organization_id to {table_name}")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to add organization_id to {table_name}: {e}")
        return False


def create_org_index(cursor, table_name):
    """Create index on organization_id for a table"""
    index_name = f"idx_{table_name}_org"

    if not table_exists(cursor, table_name):
        return False

    if not column_exists(cursor, table_name, 'organization_id'):
        return False

    if index_exists(cursor, index_name):
        print(f"  [OK] Index {index_name} already exists")
        return True

    try:
        cursor.execute(f"""
            CREATE INDEX {index_name} ON {table_name}(organization_id)
        """)
        print(f"  [+] Created index {index_name}")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to create index {index_name}: {e}")
        return False


def set_default_organization(cursor, table_name, default_org_id):
    """Set default organization_id for existing records"""
    if not table_exists(cursor, table_name):
        return 0

    if not column_exists(cursor, table_name, 'organization_id'):
        return 0

    try:
        cursor.execute(f"""
            UPDATE {table_name}
            SET organization_id = ?
            WHERE organization_id IS NULL
        """, (default_org_id,))
        affected = cursor.rowcount
        if affected > 0:
            print(f"  [+] Set organization_id={default_org_id} for {affected} rows in {table_name}")
        return affected
    except Exception as e:
        print(f"  [ERROR] Failed to set organization_id in {table_name}: {e}")
        return 0


def get_or_create_default_organization(cursor):
    """Get or create a default organization for existing data"""
    # Check if any organization exists
    cursor.execute("SELECT id FROM organizations ORDER BY id LIMIT 1")
    row = cursor.fetchone()

    if row:
        return row[0]

    # Check if any account exists
    cursor.execute("SELECT id FROM accounts ORDER BY id LIMIT 1")
    account_row = cursor.fetchone()

    if account_row:
        account_id = account_row[0]
    else:
        # Create a default account for migration
        cursor.execute("""
            INSERT INTO accounts (name, slug, owner_email, plan, max_user_seats, status)
            VALUES ('Default Account', 'default', 'admin@localhost', 'professional', 15, 'active')
        """)
        account_id = cursor.lastrowid
        print(f"  [+] Created default account (ID: {account_id})")

    # Create default organization
    cursor.execute("""
        INSERT INTO organizations (account_id, name, slug)
        VALUES (?, 'Main Location', 'main')
    """, (account_id,))
    org_id = cursor.lastrowid
    print(f"  [+] Created default organization (ID: {org_id})")

    return org_id


def migrate_database(db_path: str = "data/hailtracker_crm.db"):
    """
    Main migration function.
    Adds organization_id to all relevant tables.
    """
    print("=" * 60)
    print("MIGRATION: Add organization_id to Data Tables")
    print("=" * 60)
    print(f"\nDatabase: {db_path}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Ensure tenant schema exists
        print("Step 1: Ensuring tenant schema exists...")
        from src.core.models.tenant_schema import init_tenant_schema
        init_tenant_schema(db_path)
        print()

        # Get or create default organization
        print("Step 2: Getting default organization...")
        default_org_id = get_or_create_default_organization(cursor)
        print(f"  Default organization ID: {default_org_id}")
        conn.commit()
        print()

        # Add organization_id columns
        print("Step 3: Adding organization_id columns...")
        added = 0
        for table in TABLES_TO_MIGRATE:
            if add_organization_id_column(cursor, table):
                added += 1
        conn.commit()
        print(f"  Added columns to {added} tables")
        print()

        # Create indexes
        print("Step 4: Creating organization_id indexes...")
        indexed = 0
        for table in TABLES_TO_MIGRATE:
            if create_org_index(cursor, table):
                indexed += 1
        conn.commit()
        print(f"  Created {indexed} indexes")
        print()

        # Set default organization for existing data
        print("Step 5: Setting organization_id for existing data...")
        total_updated = 0
        for table in TABLES_TO_MIGRATE:
            total_updated += set_default_organization(cursor, table, default_org_id)
        conn.commit()
        print(f"  Updated {total_updated} total rows")
        print()

        print("=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Tables migrated: {added}")
        print(f"  - Indexes created: {indexed}")
        print(f"  - Rows updated: {total_updated}")
        print(f"  - Default organization ID: {default_org_id}")
        print()
        print("All existing data has been assigned to the default organization.")
        print("New records will require organization_id to be set explicitly.")
        print()

        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()


def verify_migration(db_path: str = "data/hailtracker_crm.db"):
    """Verify the migration was successful"""
    print("\n" + "=" * 60)
    print("VERIFYING MIGRATION")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    success = True
    for table in TABLES_TO_MIGRATE:
        if table_exists(cursor, table):
            has_col = column_exists(cursor, table, 'organization_id')
            status = "OK" if has_col else "MISSING"
            if not has_col:
                success = False
            print(f"  {table}: {status}")
        else:
            print(f"  {table}: [table doesn't exist]")

    conn.close()

    print()
    if success:
        print("All tables have organization_id column.")
    else:
        print("WARNING: Some tables are missing organization_id!")

    return success


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/hailtracker_crm.db"

    migrate_database(db_path)
    verify_migration(db_path)
