"""
PostgreSQL Auth Bootstrap

Ensures auth-related tables, seed data, and admin user exist in PostgreSQL.
Called once at app startup when DATABASE_URL points to Postgres.

Safe to call repeatedly (all operations are idempotent).

Usage:
    from src.db.pg_bootstrap import pg_bootstrap
    pg_bootstrap()  # no-op if SQLite
"""

import os
import logging

logger = logging.getLogger(__name__)


def pg_bootstrap() -> None:
    """Run full PG auth bootstrap. No-op when backend is SQLite."""
    from src.db.engine import is_postgres, get_raw_connection

    if not is_postgres():
        return

    conn = get_raw_connection()
    try:
        _ensure_auth_tables(conn)
        _seed_roles_and_permissions(conn)
        _seed_default_company(conn)
        _ensure_admin_user(conn)
        conn.commit()
        logger.info("pg_bootstrap: complete")
    except Exception:
        conn.rollback()
        logger.exception("pg_bootstrap: failed")
        raise
    finally:
        conn.close()


# ------------------------------------------------------------------
# Table creation (CREATE TABLE IF NOT EXISTS)
# ------------------------------------------------------------------

def _ensure_auth_tables(conn) -> None:
    """Create auth tables that may be missing from the PG schema."""
    cur = conn.cursor()

    # roles
    cur.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id   BIGSERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # permissions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id       BIGSERIAL PRIMARY KEY,
            name     TEXT,
            role     TEXT NOT NULL,
            resource TEXT NOT NULL,
            action   TEXT NOT NULL,
            allowed  BOOLEAN DEFAULT TRUE
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_permissions_role
        ON permissions(role)
    """)

    # role_permissions (join table)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            id            BIGSERIAL PRIMARY KEY,
            role_id       BIGINT REFERENCES roles(id),
            permission_id BIGINT REFERENCES permissions(id)
        )
    """)

    # sessions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id            BIGSERIAL PRIMARY KEY,
            user_id       BIGINT NOT NULL REFERENCES users(id),
            session_token TEXT UNIQUE NOT NULL,
            ip_address    TEXT,
            user_agent    TEXT,
            created_at    TIMESTAMPTZ DEFAULT NOW(),
            expires_at    TIMESTAMPTZ,
            last_activity TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user  ON sessions(user_id)")

    # companies
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id                  BIGSERIAL PRIMARY KEY,
            name                TEXT NOT NULL,
            subscription_plan   TEXT DEFAULT 'basic',
            subscription_status TEXT DEFAULT 'trial',
            max_users           INTEGER DEFAULT 5,
            created_at          TIMESTAMPTZ DEFAULT NOW(),
            trial_ends_at       TIMESTAMPTZ,
            billing_email       TEXT,
            phone               TEXT,
            address             TEXT,
            city                TEXT,
            state               TEXT,
            zip_code            TEXT
        )
    """)

    # audit_logs (PG name; SQLite uses audit_log)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          BIGSERIAL PRIMARY KEY,
            user_id     BIGINT REFERENCES users(id),
            action      TEXT NOT NULL,
            description TEXT,
            metadata    TEXT,
            ip_address  TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    logger.info("pg_bootstrap: auth tables ensured")


# ------------------------------------------------------------------
# Seed data (INSERT ... ON CONFLICT DO NOTHING)
# ------------------------------------------------------------------

def _seed_roles_and_permissions(conn) -> None:
    """Insert baseline roles and permissions if not already present."""
    cur = conn.cursor()

    # Roles
    for role in ('admin', 'manager', 'sales', 'technician'):
        cur.execute(
            "INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
            (role,),
        )

    # Permissions — use (role, resource, action) as a logical key.
    # Check count first to avoid duplicating on every restart.
    cur.execute("SELECT COUNT(*) FROM permissions")
    count = cur.fetchone()['count']
    if count == 0:
        perms = [
            # admin
            ('admin', 'deals', 'create'), ('admin', 'deals', 'read'),
            ('admin', 'deals', 'update'), ('admin', 'deals', 'delete'),
            ('admin', 'locations', 'read'), ('admin', 'locations', 'update'),
            ('admin', 'locations', 'export'),
            ('admin', 'users', 'create'), ('admin', 'users', 'read'),
            ('admin', 'users', 'update'), ('admin', 'users', 'delete'),
            # manager
            ('manager', 'deals', 'create'), ('manager', 'deals', 'read'),
            ('manager', 'deals', 'update'), ('manager', 'deals', 'delete'),
            ('manager', 'locations', 'read'), ('manager', 'locations', 'export'),
            ('manager', 'users', 'read'),
            # sales
            ('sales', 'deals', 'create'), ('sales', 'deals', 'read'),
            ('sales', 'deals', 'update'),
            ('sales', 'locations', 'read'), ('sales', 'locations', 'export'),
            # technician
            ('technician', 'deals', 'read'), ('technician', 'locations', 'read'),
        ]
        for role, resource, action in perms:
            cur.execute(
                "INSERT INTO permissions (role, resource, action, allowed) VALUES (%s, %s, %s, TRUE)",
                (role, resource, action),
            )
        logger.info("pg_bootstrap: seeded %d permissions", len(perms))
    else:
        logger.debug("pg_bootstrap: permissions already seeded (%d rows)", count)


def _seed_default_company(conn) -> None:
    """Ensure at least one company exists for the admin user."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM companies LIMIT 1")
    if cur.fetchone() is None:
        cur.execute("""
            INSERT INTO companies (name, subscription_plan, subscription_status, max_users, billing_email)
            VALUES ('Demo PDR Company', 'professional', 'active', 10, 'admin@hailtracker.com')
        """)
        logger.info("pg_bootstrap: seeded default company")


# ------------------------------------------------------------------
# Admin user from environment variables
# ------------------------------------------------------------------

def _ensure_admin_user(conn) -> None:
    """Create admin user from env vars if one doesn't already exist.

    Env vars (all optional — skipped if ADMIN_EMAIL is not set):
        ADMIN_EMAIL    - admin email (default: admin@hailtracker.com)
        ADMIN_USERNAME - admin username (default: admin)
        ADMIN_PASSWORD - admin password (default: admin123)
    """
    email = os.environ.get('ADMIN_EMAIL', '')
    if not email:
        # No env var set — check if any admin exists already
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        if cur.fetchone() is not None:
            logger.debug("pg_bootstrap: admin user already exists, skipping")
            return
        # No admin at all — use defaults
        email = 'admin@hailtracker.com'

    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD', 'admin123')

    cur = conn.cursor()

    # Skip if this email or username already exists
    cur.execute(
        "SELECT id FROM users WHERE email = %s OR username = %s",
        (email, username),
    )
    if cur.fetchone() is not None:
        logger.debug("pg_bootstrap: user %s already exists, skipping", username)
        return

    # Hash password
    import bcrypt
    password_hash = bcrypt.hashpw(
        password.encode('utf-8'), bcrypt.gensalt()
    ).decode('utf-8')

    cur.execute("""
        INSERT INTO users (email, username, password_hash, full_name, role, active, email_verified, login_count)
        VALUES (%s, %s, %s, 'System Administrator', 'admin', TRUE, TRUE, 0)
    """, (email, username, password_hash))

    # Link to default company
    cur.execute("SELECT id FROM companies LIMIT 1")
    company = cur.fetchone()
    if company:
        cur.execute(
            "UPDATE users SET company_id = %s WHERE email = %s",
            (company['id'], email),
        )

    logger.info("pg_bootstrap: created admin user %s <%s>", username, email)
