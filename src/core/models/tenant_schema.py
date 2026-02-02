"""
Multi-Tenant RBAC Database Schema
Account -> Organization -> User hierarchy with granular permissions

Tables:
- accounts: The paying customer (a PDR company)
- organizations: Locations under an account
- roles: System-defined roles
- permissions: Granular capabilities
- role_permissions: Which permissions each role has
- users_new: Rebuilt user table for multi-tenant support
- kiosk_devices: Customer walk-in tablets
- user_sessions: Session management
- audit_log: Track important actions
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional


TENANT_SCHEMA = """
-- =====================================================
-- ACCOUNTS (the paying customer - a PDR company)
-- =====================================================
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "ABC Dent Repair LLC"
    slug TEXT UNIQUE NOT NULL,             -- "abc-dent" (URL-safe identifier)

    -- Contact
    owner_email TEXT NOT NULL,
    phone TEXT,

    -- Address
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,

    -- Subscription (manual for now)
    plan TEXT DEFAULT 'starter',           -- starter, professional, enterprise
    max_user_seats INTEGER DEFAULT 5,

    -- Status
    status TEXT DEFAULT 'active',          -- active, suspended, cancelled, trial
    trial_ends_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- =====================================================
-- ORGANIZATIONS (locations under an account)
-- For V1: 1 account = 1 org, but schema supports multiple
-- =====================================================
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    name TEXT NOT NULL,                    -- "Main Shop"
    slug TEXT NOT NULL,                    -- "main"

    -- Location
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    phone TEXT,
    email TEXT,
    timezone TEXT DEFAULT 'America/Chicago',

    -- Business Settings (JSON for flexibility)
    settings TEXT,                         -- {"labor_rates": {...}, "tax_rate": 0.0825}

    -- Branding
    logo_path TEXT,

    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,

    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    UNIQUE(account_id, slug)
);

-- =====================================================
-- ROLES (system-defined, not customizable)
-- =====================================================
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,             -- 'owner', 'admin', 'office', 'sales', 'tech', 'estimator', 'kiosk'
    display_name TEXT NOT NULL,            -- 'Owner', 'Office Staff', etc.
    description TEXT,
    counts_as_seat BOOLEAN DEFAULT 1,      -- kiosk = false
    is_system BOOLEAN DEFAULT 1,           -- can't be deleted
    sort_order INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PERMISSIONS (granular capabilities)
-- =====================================================
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,             -- 'customers.view', 'estimates.create'
    display_name TEXT NOT NULL,            -- 'View Customers'
    category TEXT NOT NULL,                -- 'customers', 'estimates', 'jobs'
    description TEXT,
    sort_order INTEGER DEFAULT 100
);

-- =====================================================
-- ROLE_PERMISSIONS (which permissions each role has)
-- =====================================================
CREATE TABLE IF NOT EXISTS role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- =====================================================
-- USERS (rebuilt to support multi-tenant)
-- =====================================================
CREATE TABLE IF NOT EXISTS users_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    organization_id INTEGER NOT NULL,      -- their primary org (V1: only org)
    role_id INTEGER NOT NULL,

    -- Identity
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,

    -- Profile
    avatar_path TEXT,
    job_title TEXT,

    -- For sales/tech: compensation
    commission_rate REAL DEFAULT 0,
    hourly_rate REAL DEFAULT 0,
    hire_date DATE,

    -- Status
    is_active BOOLEAN DEFAULT 1,
    email_verified BOOLEAN DEFAULT 0,
    must_change_password BOOLEAN DEFAULT 0,

    -- Tracking
    last_login_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    created_by INTEGER,

    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- =====================================================
-- KIOSK DEVICES (for customer walk-in tablets)
-- =====================================================
CREATE TABLE IF NOT EXISTS kiosk_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,

    -- Device identity
    device_token TEXT UNIQUE NOT NULL,     -- UUID, used for auth
    name TEXT,                             -- "Lobby Tablet 1"

    -- Settings
    auto_reset_seconds INTEGER DEFAULT 30, -- reset form after submission
    welcome_message TEXT,                  -- "Welcome to ABC Dent Repair!"

    -- Tracking
    last_seen_at TIMESTAMP,
    last_ip TEXT,
    user_agent TEXT,

    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- =====================================================
-- SESSION MANAGEMENT (replace Flask-Login's default)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    kiosk_id INTEGER,                      -- either user_id OR kiosk_id

    session_token TEXT UNIQUE NOT NULL,

    -- Context
    ip_address TEXT,
    user_agent TEXT,
    device_type TEXT,                      -- 'desktop', 'mobile', 'tablet'

    -- Validity
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users_new(id) ON DELETE CASCADE,
    FOREIGN KEY (kiosk_id) REFERENCES kiosk_devices(id) ON DELETE CASCADE
);

-- =====================================================
-- AUDIT LOG (track important actions)
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_log_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    user_id INTEGER,
    kiosk_id INTEGER,

    -- What happened
    action TEXT NOT NULL,                  -- 'user.created', 'estimate.approved', 'job.status_changed'
    resource_type TEXT,                    -- 'user', 'estimate', 'job'
    resource_id INTEGER,

    -- Details
    details TEXT,                          -- JSON with before/after or context
    ip_address TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users_new(id)
);

-- =====================================================
-- INDEXES
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_users_new_account ON users_new(account_id);
CREATE INDEX IF NOT EXISTS idx_users_new_org ON users_new(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_new_email ON users_new(email);
CREATE INDEX IF NOT EXISTS idx_users_new_role ON users_new(role_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_new_org ON audit_log_new(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_new_user ON audit_log_new(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_new_action ON audit_log_new(action);
CREATE INDEX IF NOT EXISTS idx_kiosk_token ON kiosk_devices(device_token);
CREATE INDEX IF NOT EXISTS idx_orgs_account ON organizations(account_id);
CREATE INDEX IF NOT EXISTS idx_accounts_slug ON accounts(slug);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
"""

# Views are created separately due to SQLite limitations
TENANT_VIEWS = """
-- =====================================================
-- VIEWS
-- =====================================================

-- Seat usage per account
CREATE VIEW IF NOT EXISTS v_seat_usage AS
SELECT
    a.id as account_id,
    a.name as account_name,
    a.max_user_seats,
    COUNT(CASE WHEN r.counts_as_seat = 1 THEN u.id END) as used_seats,
    (a.max_user_seats - COUNT(CASE WHEN r.counts_as_seat = 1 THEN u.id END)) as available_seats,
    CASE WHEN COUNT(CASE WHEN r.counts_as_seat = 1 THEN u.id END) >= a.max_user_seats THEN 1 ELSE 0 END as at_limit
FROM accounts a
LEFT JOIN users_new u ON u.account_id = a.id AND u.is_active = 1
LEFT JOIN roles r ON u.role_id = r.id
GROUP BY a.id;

-- User with role and permissions (for easy lookup)
CREATE VIEW IF NOT EXISTS v_user_permissions AS
SELECT
    u.id as user_id,
    u.email,
    u.first_name,
    u.last_name,
    u.account_id,
    u.organization_id,
    r.name as role_name,
    r.display_name as role_display_name,
    GROUP_CONCAT(p.name) as permissions
FROM users_new u
JOIN roles r ON u.role_id = r.id
LEFT JOIN role_permissions rp ON rp.role_id = r.id
LEFT JOIN permissions p ON rp.permission_id = p.id
GROUP BY u.id;

-- Active sessions with user/kiosk info
CREATE VIEW IF NOT EXISTS v_active_sessions AS
SELECT
    s.id as session_id,
    s.session_token,
    s.user_id,
    s.kiosk_id,
    CASE
        WHEN s.user_id IS NOT NULL THEN u.email
        WHEN s.kiosk_id IS NOT NULL THEN k.name
    END as identity,
    CASE
        WHEN s.user_id IS NOT NULL THEN 'user'
        WHEN s.kiosk_id IS NOT NULL THEN 'kiosk'
    END as session_type,
    s.device_type,
    s.ip_address,
    s.created_at,
    s.expires_at
FROM user_sessions s
LEFT JOIN users_new u ON s.user_id = u.id
LEFT JOIN kiosk_devices k ON s.kiosk_id = k.id
WHERE s.revoked_at IS NULL
  AND s.expires_at > CURRENT_TIMESTAMP;
"""


class TenantSchema:
    """Create and manage multi-tenant RBAC schema"""

    @staticmethod
    def create_all_tables(db_path: str = "data/hailtracker_crm.db") -> bool:
        """
        Create complete multi-tenant RBAC schema.

        This adds the tenant structure without modifying existing tables.
        """
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("=" * 60)
        print("Creating Multi-Tenant RBAC Schema")
        print("=" * 60)
        print()

        try:
            # Create main schema tables
            cursor.executescript(TENANT_SCHEMA)
            print("[OK] Created tenant tables (accounts, organizations, roles, permissions, users_new, etc.)")

            # Create views separately - each view as individual statement
            views = [
                """
                CREATE VIEW IF NOT EXISTS v_seat_usage AS
                SELECT
                    a.id as account_id,
                    a.name as account_name,
                    a.max_user_seats,
                    COUNT(CASE WHEN r.counts_as_seat = 1 THEN u.id END) as used_seats,
                    (a.max_user_seats - COUNT(CASE WHEN r.counts_as_seat = 1 THEN u.id END)) as available_seats,
                    CASE WHEN COUNT(CASE WHEN r.counts_as_seat = 1 THEN u.id END) >= a.max_user_seats THEN 1 ELSE 0 END as at_limit
                FROM accounts a
                LEFT JOIN users_new u ON u.account_id = a.id AND u.is_active = 1
                LEFT JOIN roles r ON u.role_id = r.id
                GROUP BY a.id
                """,
                """
                CREATE VIEW IF NOT EXISTS v_user_permissions AS
                SELECT
                    u.id as user_id,
                    u.email,
                    u.first_name,
                    u.last_name,
                    u.account_id,
                    u.organization_id,
                    r.name as role_name,
                    r.display_name as role_display_name,
                    GROUP_CONCAT(p.name) as permissions
                FROM users_new u
                JOIN roles r ON u.role_id = r.id
                LEFT JOIN role_permissions rp ON rp.role_id = r.id
                LEFT JOIN permissions p ON rp.permission_id = p.id
                GROUP BY u.id
                """,
                """
                CREATE VIEW IF NOT EXISTS v_active_sessions AS
                SELECT
                    s.id as session_id,
                    s.session_token,
                    s.user_id,
                    s.kiosk_id,
                    CASE
                        WHEN s.user_id IS NOT NULL THEN u.email
                        WHEN s.kiosk_id IS NOT NULL THEN k.name
                    END as identity,
                    CASE
                        WHEN s.user_id IS NOT NULL THEN 'user'
                        WHEN s.kiosk_id IS NOT NULL THEN 'kiosk'
                    END as session_type,
                    s.device_type,
                    s.ip_address,
                    s.created_at,
                    s.expires_at
                FROM user_sessions s
                LEFT JOIN users_new u ON s.user_id = u.id
                LEFT JOIN kiosk_devices k ON s.kiosk_id = k.id
                WHERE s.revoked_at IS NULL
                  AND s.expires_at > CURRENT_TIMESTAMP
                """
            ]
            for view_sql in views:
                try:
                    cursor.execute(view_sql)
                except sqlite3.OperationalError as e:
                    if 'already exists' not in str(e):
                        raise
            print("[OK] Created views (v_seat_usage, v_user_permissions, v_active_sessions)")

            conn.commit()
            print()
            print("=" * 60)
            print("TENANT SCHEMA CREATED SUCCESSFULLY")
            print("=" * 60)
            print()
            print("Tables created:")
            print("  - accounts (paying customers)")
            print("  - organizations (locations under accounts)")
            print("  - roles (owner, admin, office, sales, tech, estimator, kiosk)")
            print("  - permissions (granular capabilities)")
            print("  - role_permissions (role -> permission mapping)")
            print("  - users_new (multi-tenant user table)")
            print("  - kiosk_devices (lobby tablets)")
            print("  - user_sessions (session management)")
            print("  - audit_log_new (action tracking)")
            print()
            print("Views created:")
            print("  - v_seat_usage (seat counting per account)")
            print("  - v_user_permissions (user with all permissions)")
            print("  - v_active_sessions (current active sessions)")
            print()

            return True

        except Exception as e:
            print(f"[ERROR] Failed to create tenant schema: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    @staticmethod
    def drop_tenant_tables(db_path: str = "data/hailtracker_crm.db") -> bool:
        """
        Drop all tenant tables (for clean rebuild during development).
        WARNING: Destructive operation!
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        tables = [
            'v_active_sessions',
            'v_user_permissions',
            'v_seat_usage',
            'audit_log_new',
            'user_sessions',
            'kiosk_devices',
            'users_new',
            'role_permissions',
            'permissions',
            'roles',
            'organizations',
            'accounts'
        ]

        print("Dropping tenant tables...")

        for table in tables:
            try:
                if table.startswith('v_'):
                    cursor.execute(f"DROP VIEW IF EXISTS {table}")
                else:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  Dropped {table}")
            except Exception as e:
                print(f"  Error dropping {table}: {e}")

        conn.commit()
        conn.close()

        print("Done.")
        return True


# Convenience function
def init_tenant_schema(db_path: str = "data/hailtracker_crm.db") -> bool:
    """Initialize the tenant schema"""
    return TenantSchema.create_all_tables(db_path)


if __name__ == "__main__":
    # Run directly to create schema
    import sys

    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/hailtracker_crm.db"

    init_tenant_schema(db_path)
