"""
Admin API Routes
================
REST API for admin functionality: team management, settings, and billing.
"""

from flask import Blueprint, request, jsonify, current_app, session, g
from functools import wraps
import sqlite3
from datetime import datetime, timedelta
import json
import secrets
import hashlib
from src.core.auth.decorators import login_required

admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')


def admin_required(f):
    """Require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_role = g.current_user.get('role', '')
        if user_role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_db():
    """Get database connection using CRM database."""
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables_exist(conn):
    """Ensure admin tables exist."""
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'pending',
            avatar_url TEXT,
            invite_token TEXT,
            invite_sent_at TEXT,
            password_reset_token TEXT,
            password_reset_expires TEXT,
            last_login_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT
        )
    ''')

    # Company settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT,
            setting_type TEXT DEFAULT 'string',
            category TEXT DEFAULT 'general',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER
        )
    ''')

    # User activity log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Billing/subscription table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT DEFAULT 'free',
            plan_name TEXT DEFAULT 'Free',
            status TEXT DEFAULT 'active',
            billing_email TEXT,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            current_period_start TEXT,
            current_period_end TEXT,
            seats_included INTEGER DEFAULT 5,
            seats_used INTEGER DEFAULT 1,
            monthly_price REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Initialize default settings if empty
    cursor.execute('SELECT COUNT(*) as count FROM company_settings')
    if cursor.fetchone()['count'] == 0:
        default_settings = [
            ('company_name', 'My PDR Company', 'string', 'company'),
            ('company_email', '', 'string', 'company'),
            ('company_phone', '', 'string', 'company'),
            ('company_address', '', 'string', 'company'),
            ('company_city', '', 'string', 'company'),
            ('company_state', '', 'string', 'company'),
            ('company_zip', '', 'string', 'company'),
            ('company_logo_url', '', 'string', 'branding'),
            ('primary_color', '#2563eb', 'string', 'branding'),
            ('default_tax_rate', '0', 'number', 'defaults'),
            ('default_estimate_terms', 'Estimate valid for 30 days. Subject to change upon inspection.', 'text', 'defaults'),
            ('business_hours_start', '08:00', 'string', 'company'),
            ('business_hours_end', '17:00', 'string', 'company'),
            ('notify_new_lead', 'true', 'boolean', 'notifications'),
            ('notify_job_complete', 'true', 'boolean', 'notifications'),
            ('notify_estimate_approved', 'true', 'boolean', 'notifications'),
            ('sms_notifications_enabled', 'false', 'boolean', 'notifications'),
        ]
        cursor.executemany('''
            INSERT INTO company_settings (setting_key, setting_value, setting_type, category)
            VALUES (?, ?, ?, ?)
        ''', default_settings)

    # Initialize billing if empty
    cursor.execute('SELECT COUNT(*) as count FROM billing')
    if cursor.fetchone()['count'] == 0:
        cursor.execute('''
            INSERT INTO billing (plan_id, plan_name, status, seats_included, seats_used)
            VALUES ('free', 'Free Plan', 'active', 5, 1)
        ''')

    conn.commit()


def log_activity(conn, user_id, action, details=None):
    """Log user activity."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_activity_log (user_id, action, details, ip_address, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user_id,
        action,
        json.dumps(details) if details else None,
        request.remote_addr,
        datetime.now().isoformat()
    ))
    conn.commit()


# ===================
# USER MANAGEMENT
# ===================

@admin_api_bp.route('/users')
@login_required
@admin_required
def list_users():
    """List all users with filtering."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Build query
    where_clauses = ['1=1']
    params = []

    # Role filter
    role = request.args.get('role')
    if role:
        where_clauses.append('role = ?')
        params.append(role)

    # Status filter (map to 'active' boolean)
    status = request.args.get('status')
    if status:
        if status == 'active':
            where_clauses.append('active = 1')
        elif status == 'inactive':
            where_clauses.append('active = 0')

    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        where_clauses.append('(email LIKE ? OR full_name LIKE ? OR username LIKE ?)')
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param])

    where_sql = ' AND '.join(where_clauses)

    # Get users
    cursor.execute(f'''
        SELECT
            id, email, username, full_name, phone, role,
            CASE WHEN active = 1 THEN 'active' ELSE 'inactive' END as status,
            last_login, created_at
        FROM users
        WHERE {where_sql}
        ORDER BY created_at DESC
    ''', params)

    users = [dict(row) for row in cursor.fetchall()]

    # Get stats
    cursor.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN active = 0 THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admins
        FROM users
        WHERE 1=1
    ''')
    stats = dict(cursor.fetchone())

    conn.close()

    return jsonify({
        'users': users,
        'stats': stats
    })


@admin_api_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def get_user(user_id):
    """Get user details with activity."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            id, email, first_name, last_name, phone, role, status,
            avatar_url, last_login_at, created_at, updated_at
        FROM users
        WHERE id = ? AND deleted_at IS NULL
    ''', (user_id,))

    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    user = dict(user)

    # Get recent activity
    cursor.execute('''
        SELECT action, details, ip_address, created_at
        FROM user_activity_log
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    ''', (user_id,))

    user['activity'] = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify(user)


@admin_api_bp.route('/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create/invite a new user."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    data = request.get_json()

    if not data.get('email'):
        conn.close()
        return jsonify({'error': 'Email is required'}), 422

    # Check if email exists
    cursor.execute('SELECT id FROM users WHERE email = ? AND deleted_at IS NULL', (data['email'].lower(),))
    if cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Email already exists'}), 422

    # Check seat limit
    cursor.execute('SELECT seats_included, seats_used FROM billing LIMIT 1')
    billing = cursor.fetchone()
    if billing and billing['seats_used'] >= billing['seats_included']:
        conn.close()
        return jsonify({'error': 'User limit reached. Please upgrade your plan.'}), 422

    # Generate invite token
    invite_token = secrets.token_urlsafe(32)
    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO users (
            email, first_name, last_name, role, status,
            invite_token, invite_sent_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
    ''', (
        data['email'].lower(),
        data.get('first_name', ''),
        data.get('last_name', ''),
        data.get('role', 'user'),
        invite_token,
        now if data.get('send_invite', True) else None,
        now, now
    ))

    user_id = cursor.lastrowid

    # Update seats used
    cursor.execute('UPDATE billing SET seats_used = seats_used + 1, updated_at = ?', (now,))

    conn.commit()

    # Log activity
    log_activity(conn, g.current_user.get('id'), 'user_created', {'user_id': user_id, 'email': data['email']})

    # TODO: Send invite email if send_invite is true

    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = dict(cursor.fetchone())

    conn.close()

    return jsonify(user), 201


@admin_api_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """Update user details."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = ? AND deleted_at IS NULL', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    now = datetime.now().isoformat()

    updates = ['updated_at = ?']
    params = [now]

    if 'first_name' in data:
        updates.append('first_name = ?')
        params.append(data['first_name'])

    if 'last_name' in data:
        updates.append('last_name = ?')
        params.append(data['last_name'])

    if 'phone' in data:
        updates.append('phone = ?')
        params.append(data['phone'])

    if 'role' in data:
        updates.append('role = ?')
        params.append(data['role'])

    if 'status' in data:
        updates.append('status = ?')
        params.append(data['status'])

    params.append(user_id)

    cursor.execute(f'''
        UPDATE users SET {', '.join(updates)} WHERE id = ?
    ''', params)

    conn.commit()

    log_activity(conn, g.current_user.get('id'), 'user_updated', {'user_id': user_id})

    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    updated = dict(cursor.fetchone())

    conn.close()

    return jsonify(updated)


@admin_api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def deactivate_user(user_id):
    """Deactivate (soft delete) user."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Can't delete yourself
    if user_id == g.current_user.get('id'):
        conn.close()
        return jsonify({'error': 'Cannot deactivate your own account'}), 422

    cursor.execute('SELECT * FROM users WHERE id = ? AND deleted_at IS NULL', (user_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    now = datetime.now().isoformat()

    cursor.execute('''
        UPDATE users SET status = 'inactive', deleted_at = ?, updated_at = ?
        WHERE id = ?
    ''', (now, now, user_id))

    # Update seats used
    cursor.execute('UPDATE billing SET seats_used = seats_used - 1, updated_at = ?', (now,))

    conn.commit()

    log_activity(conn, g.current_user.get('id'), 'user_deactivated', {'user_id': user_id})

    conn.close()

    return jsonify({'message': 'User deactivated'})


@admin_api_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Send password reset email to user."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = ? AND deleted_at IS NULL', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(hours=24)).isoformat()
    now = datetime.now().isoformat()

    cursor.execute('''
        UPDATE users SET
            password_reset_token = ?,
            password_reset_expires = ?,
            updated_at = ?
        WHERE id = ?
    ''', (reset_token, expires, now, user_id))

    conn.commit()

    # TODO: Send password reset email

    log_activity(conn, g.current_user.get('id'), 'password_reset_sent', {'user_id': user_id})

    conn.close()

    return jsonify({'message': f'Password reset email sent to {user["email"]}'})


@admin_api_bp.route('/users/<int:user_id>/resend-invite', methods=['POST'])
@login_required
@admin_required
def resend_invite(user_id):
    """Resend invitation email to pending user."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE id = ? AND status = "pending" AND deleted_at IS NULL', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found or not pending'}), 404

    # Generate new invite token
    invite_token = secrets.token_urlsafe(32)
    now = datetime.now().isoformat()

    cursor.execute('''
        UPDATE users SET invite_token = ?, invite_sent_at = ?, updated_at = ?
        WHERE id = ?
    ''', (invite_token, now, now, user_id))

    conn.commit()

    # TODO: Send invite email

    log_activity(conn, g.current_user.get('id'), 'invite_resent', {'user_id': user_id})

    conn.close()

    return jsonify({'message': f'Invitation resent to {user["email"]}'})


@admin_api_bp.route('/roles')
@login_required
@admin_required
def list_roles():
    """List available roles."""
    roles = [
        {
            'id': 'admin',
            'name': 'Administrator',
            'description': 'Full access to all features',
            'permissions': ['all']
        },
        {
            'id': 'office_manager',
            'name': 'Office Manager',
            'description': 'Manage leads, customers, jobs, and scheduling',
            'permissions': ['leads.*', 'customers.*', 'jobs.*', 'estimates.*', 'scheduling.*']
        },
        {
            'id': 'sales',
            'name': 'Sales Representative',
            'description': 'Handle leads, create estimates, manage customers',
            'permissions': ['leads.*', 'customers.view', 'customers.create', 'estimates.*']
        },
        {
            'id': 'technician',
            'name': 'Technician',
            'description': 'View assigned jobs, update status, clock in/out',
            'permissions': ['jobs.view_own', 'jobs.update_status', 'time_tracking.*']
        },
        {
            'id': 'user',
            'name': 'Basic User',
            'description': 'Limited read-only access',
            'permissions': ['dashboard.view']
        }
    ]

    return jsonify({'roles': roles})


# ===================
# COMPANY SETTINGS
# ===================

@admin_api_bp.route('/settings')
@login_required
@admin_required
def get_settings():
    """Get all company settings."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM company_settings ORDER BY category, setting_key')
    rows = cursor.fetchall()

    # Group by category
    settings = {}
    for row in rows:
        category = row['category']
        if category not in settings:
            settings[category] = {}

        # Parse value based on type
        value = row['setting_value']
        if row['setting_type'] == 'boolean':
            value = value == 'true'
        elif row['setting_type'] == 'number':
            try:
                value = float(value) if '.' in str(value) else int(value)
            except:
                value = 0
        elif row['setting_type'] == 'json':
            try:
                value = json.loads(value)
            except:
                value = {}

        settings[category][row['setting_key']] = value

    conn.close()

    return jsonify(settings)


@admin_api_bp.route('/settings', methods=['PUT'])
@login_required
@admin_required
def update_settings():
    """Update company settings."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    data = request.get_json()
    now = datetime.now().isoformat()
    user_id = g.current_user.get('id')

    for key, value in data.items():
        # Convert value to string
        if isinstance(value, bool):
            str_value = 'true' if value else 'false'
        elif isinstance(value, (dict, list)):
            str_value = json.dumps(value)
        else:
            str_value = str(value)

        cursor.execute('''
            UPDATE company_settings
            SET setting_value = ?, updated_at = ?, updated_by = ?
            WHERE setting_key = ?
        ''', (str_value, now, user_id, key))

        # Insert if not exists
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO company_settings (setting_key, setting_value, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
            ''', (key, str_value, now, user_id))

    conn.commit()

    log_activity(conn, user_id, 'settings_updated', {'keys': list(data.keys())})

    conn.close()

    return jsonify({'message': 'Settings updated'})


@admin_api_bp.route('/settings/branding', methods=['PUT'])
@login_required
@admin_required
def update_branding():
    """Update branding settings (logo, colors)."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    data = request.get_json()
    now = datetime.now().isoformat()
    user_id = g.current_user.get('id')

    branding_keys = ['company_logo_url', 'primary_color', 'secondary_color', 'accent_color']

    for key in branding_keys:
        if key in data:
            cursor.execute('''
                UPDATE company_settings
                SET setting_value = ?, updated_at = ?, updated_by = ?
                WHERE setting_key = ?
            ''', (str(data[key]), now, user_id, key))

    conn.commit()

    log_activity(conn, user_id, 'branding_updated', {'keys': [k for k in branding_keys if k in data]})

    conn.close()

    return jsonify({'message': 'Branding updated'})


@admin_api_bp.route('/settings/integrations')
@login_required
@admin_required
def get_integrations():
    """Get integrations status."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Check for integration settings
    cursor.execute('''
        SELECT setting_key, setting_value FROM company_settings
        WHERE category = 'integrations'
    ''')

    integration_settings = {row['setting_key']: row['setting_value'] for row in cursor.fetchall()}

    integrations = [
        {
            'id': 'twilio',
            'name': 'Twilio SMS',
            'description': 'Send SMS notifications to customers',
            'status': 'connected' if integration_settings.get('twilio_account_sid') else 'not_configured',
            'icon': 'message-square'
        },
        {
            'id': 'stripe',
            'name': 'Stripe Payments',
            'description': 'Process customer payments',
            'status': 'connected' if integration_settings.get('stripe_secret_key') else 'not_configured',
            'icon': 'credit-card'
        },
        {
            'id': 'google_calendar',
            'name': 'Google Calendar',
            'description': 'Sync jobs to calendar',
            'status': 'connected' if integration_settings.get('google_calendar_token') else 'not_configured',
            'icon': 'calendar'
        },
        {
            'id': 'quickbooks',
            'name': 'QuickBooks',
            'description': 'Sync invoices and payments',
            'status': 'not_configured',
            'icon': 'file-text'
        }
    ]

    conn.close()

    return jsonify({'integrations': integrations})


# ===================
# BILLING
# ===================

@admin_api_bp.route('/billing')
@login_required
@admin_required
def get_billing():
    """Get billing information."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM billing LIMIT 1')
    billing = cursor.fetchone()

    if billing:
        billing = dict(billing)
    else:
        billing = {
            'plan_id': 'free',
            'plan_name': 'Free Plan',
            'status': 'active',
            'seats_included': 5,
            'seats_used': 1,
            'monthly_price': 0
        }

    # Available plans
    plans = [
        {
            'id': 'free',
            'name': 'Free',
            'price': 0,
            'seats': 5,
            'features': ['Up to 5 users', 'Basic CRM', 'Email support']
        },
        {
            'id': 'starter',
            'name': 'Starter',
            'price': 49,
            'seats': 10,
            'features': ['Up to 10 users', 'Full CRM', 'Customer portal', 'Priority support']
        },
        {
            'id': 'professional',
            'name': 'Professional',
            'price': 99,
            'seats': 25,
            'features': ['Up to 25 users', 'Full CRM', 'Customer portal', 'API access', 'Phone support']
        },
        {
            'id': 'enterprise',
            'name': 'Enterprise',
            'price': 199,
            'seats': -1,  # Unlimited
            'features': ['Unlimited users', 'Full CRM', 'Customer portal', 'API access', 'Custom integrations', 'Dedicated support']
        }
    ]

    # Payment history
    cursor.execute('''
        SELECT * FROM (
            SELECT
                'invoice' as type,
                id,
                monthly_price as amount,
                current_period_start as date,
                status,
                plan_name as description
            FROM billing
            WHERE monthly_price > 0
        ) ORDER BY date DESC LIMIT 10
    ''')

    # This would normally come from Stripe
    invoices = []

    conn.close()

    return jsonify({
        'billing': billing,
        'plans': plans,
        'invoices': invoices
    })


@admin_api_bp.route('/billing/upgrade', methods=['POST'])
@login_required
@admin_required
def upgrade_plan():
    """Upgrade billing plan."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    data = request.get_json()
    plan_id = data.get('plan_id')

    if not plan_id:
        conn.close()
        return jsonify({'error': 'Plan ID required'}), 422

    # Plan details (would normally come from Stripe)
    plans = {
        'free': {'name': 'Free Plan', 'price': 0, 'seats': 5},
        'starter': {'name': 'Starter Plan', 'price': 49, 'seats': 10},
        'professional': {'name': 'Professional Plan', 'price': 99, 'seats': 25},
        'enterprise': {'name': 'Enterprise Plan', 'price': 199, 'seats': 999}
    }

    if plan_id not in plans:
        conn.close()
        return jsonify({'error': 'Invalid plan'}), 422

    plan = plans[plan_id]
    now = datetime.now().isoformat()

    # In production, this would create a Stripe checkout session
    # For now, just update the local record

    cursor.execute('''
        UPDATE billing SET
            plan_id = ?,
            plan_name = ?,
            seats_included = ?,
            monthly_price = ?,
            updated_at = ?
    ''', (plan_id, plan['name'], plan['seats'], plan['price'], now))

    conn.commit()

    log_activity(conn, g.current_user.get('id'), 'plan_upgraded', {'plan_id': plan_id})

    conn.close()

    return jsonify({
        'message': f'Upgraded to {plan["name"]}',
        'checkout_url': None  # Would be Stripe checkout URL
    })


@admin_api_bp.route('/billing/portal', methods=['POST'])
@login_required
@admin_required
def create_billing_portal():
    """Create Stripe billing portal session."""
    # In production, this would create a Stripe billing portal session
    # For now, return a placeholder

    return jsonify({
        'url': None,
        'message': 'Billing portal not configured. Set up Stripe to manage billing.'
    })


# ===================
# ACTIVITY LOG
# ===================

@admin_api_bp.route('/activity')
@login_required
@admin_required
def get_activity():
    """Get recent activity log."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 200)

    cursor.execute('''
        SELECT
            al.*,
            u.email as user_email,
            u.first_name || ' ' || u.last_name as user_name
        FROM user_activity_log al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC
        LIMIT ?
    ''', (limit,))

    activity = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({'activity': activity})
