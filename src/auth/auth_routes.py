"""
JWT Authentication Routes for HailTracker Pro
Handles login, register, refresh, and user info endpoints
"""

from flask import Blueprint, request, jsonify, g
import bcrypt
import psycopg2
import psycopg2.extras
from datetime import datetime
import os

from .jwt_utils import (
    generate_token, generate_refresh_token, verify_token,
    get_dev_user, DEV_MODE
)
from .auth_middleware import login_required

# Create blueprint for auth routes
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# PostgreSQL configuration (matches test_api_server.py)
PG_CONFIG = {
    "host": os.environ.get('PG_HOST', 'localhost'),
    "port": int(os.environ.get('PG_PORT', 5432)),
    "database": os.environ.get('PG_DATABASE', 'hailtracker_master'),
    "user": os.environ.get('PG_USER', 'hailtracker'),
    "password": os.environ.get('PG_PASSWORD', 'hailtracker_dev_2024')
}


def get_db():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(**PG_CONFIG)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT tokens.

    Request Body:
        {
            "email": "user@example.com",
            "password": "password123"
        }

    Returns:
        {
            "success": true,
            "token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
            "user": { user info }
        }
    """
    data = request.get_json() or {}

    # DEV_MODE: Accept any credentials
    if DEV_MODE:
        dev_user = get_dev_user()
        return jsonify({
            'success': True,
            'token': dev_user['token'],
            'refresh_token': dev_user['refresh_token'],
            'user': {
                'id': dev_user['user_id'],
                'email': dev_user['email'],
                'name': dev_user['name'],
                'role': dev_user['role'],
                'role_name': dev_user['role'].title(),
                'tenant_id': dev_user['tenant_id'],
                'permissions': get_permissions_for_role('admin')
            },
            'dev_mode': True
        })

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password required'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Find user by email
        cur.execute("""
            SELECT id, tenant_id, email, password_hash, name, phone, role, is_active
            FROM users
            WHERE email = %s
        """, (email,))

        user = cur.fetchone()

        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        if not user['is_active']:
            conn.close()
            return jsonify({'success': False, 'error': 'Account is disabled'}), 401

        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        # Update last login
        cur.execute("""
            UPDATE users SET last_login = %s WHERE id = %s
        """, (datetime.utcnow(), user['id']))
        conn.commit()
        conn.close()

        # Generate tokens
        token = generate_token(
            user_id=user['id'],
            tenant_id=user['tenant_id'],
            email=user['email'],
            role=user['role'],
            name=user['name']
        )
        refresh = generate_refresh_token(user['id'], user['tenant_id'])

        return jsonify({
            'success': True,
            'token': token,
            'refresh_token': refresh,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'role_name': user['role'].title(),
                'tenant_id': user['tenant_id'],
                'permissions': get_permissions_for_role(user['role'])
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request Body:
        {
            "email": "user@example.com",
            "password": "password123",
            "name": "John Doe",
            "phone": "555-1234"  (optional)
        }

    Returns:
        {
            "success": true,
            "token": "jwt_access_token",
            "refresh_token": "jwt_refresh_token",
            "user": { user info }
        }
    """
    data = request.get_json() or {}

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    phone = data.get('phone')

    if not email or not password or not name:
        return jsonify({'success': False, 'error': 'Email, password, and name are required'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if email exists
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Email already registered'}), 400

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Create new tenant for this user (each registration gets their own tenant)
        # Generate a unique slug from name
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        slug = f"{slug}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        cur.execute("""
            INSERT INTO tenants (company_name, slug, owner_email, plan, status, max_users, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (f"{name}'s Company", slug, email, 'free', 'active', 8, datetime.utcnow()))
        tenant_id = cur.fetchone()['id']

        # Create user with 'owner' role for their tenant
        cur.execute("""
            INSERT INTO users (tenant_id, email, password_hash, name, phone, role, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, tenant_id, email, name, phone, role, is_active
        """, (tenant_id, email, password_hash, name, phone, 'owner', True, datetime.utcnow()))

        user = cur.fetchone()
        conn.commit()
        conn.close()

        # Generate tokens
        token = generate_token(
            user_id=user['id'],
            tenant_id=user['tenant_id'],
            email=user['email'],
            role=user['role'],
            name=user['name']
        )
        refresh = generate_refresh_token(user['id'], user['tenant_id'])

        return jsonify({
            'success': True,
            'token': token,
            'refresh_token': refresh,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'role_name': user['role'].title(),
                'tenant_id': user['tenant_id'],
                'permissions': get_permissions_for_role(user['role'])
            }
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'error': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Get a new access token using a refresh token.

    Request Body:
        {
            "refresh_token": "jwt_refresh_token"
        }

    Returns:
        {
            "success": true,
            "token": "new_jwt_access_token",
            "refresh_token": "new_jwt_refresh_token"
        }
    """
    data = request.get_json() or {}
    refresh_token_str = data.get('refresh_token')

    if not refresh_token_str:
        return jsonify({'success': False, 'error': 'Refresh token required'}), 400

    # Verify refresh token
    payload = verify_token(refresh_token_str)

    if not payload or payload.get('type') != 'refresh':
        return jsonify({'success': False, 'error': 'Invalid or expired refresh token'}), 401

    user_id = payload.get('user_id')  # Use numeric user_id, not string sub
    tenant_id = payload.get('tenant_id')

    try:
        # Look up user to get current info
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT id, tenant_id, email, name, role, is_active
            FROM users
            WHERE id = %s AND tenant_id = %s
        """, (user_id, tenant_id))

        user = cur.fetchone()
        conn.close()

        if not user or not user['is_active']:
            return jsonify({'success': False, 'error': 'User not found or disabled'}), 401

        # Generate new tokens
        token = generate_token(
            user_id=user['id'],
            tenant_id=user['tenant_id'],
            email=user['email'],
            role=user['role'],
            name=user['name']
        )
        new_refresh = generate_refresh_token(user['id'], user['tenant_id'])

        return jsonify({
            'success': True,
            'token': token,
            'refresh_token': new_refresh
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Refresh failed: {str(e)}'}), 500


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_me():
    """
    Get current authenticated user's information.

    Headers:
        Authorization: Bearer <token>

    Returns:
        {
            "id": 1,
            "email": "user@example.com",
            "name": "John Doe",
            "role": "owner",
            "tenant_id": 1,
            "permissions": [...]
        }
    """
    user = g.current_user

    return jsonify({
        'id': user['user_id'],
        'email': user['email'],
        'name': user['name'],
        'role': user['role'],
        'role_name': user['role'].title(),
        'tenant_id': user['tenant_id'],
        'permissions': get_permissions_for_role(user['role'])
    })


def get_permissions_for_role(role: str) -> list:
    """
    Get permissions list for a given role.
    This defines what each role can do in the application.
    """
    # Base permissions everyone has
    base_permissions = [
        'dashboard:view',
        'hail:view',
        'storms:view'
    ]

    # Role-specific permissions
    role_permissions = {
        'admin': [
            'dashboard:manage',
            'jobs:view', 'jobs:create', 'jobs:edit', 'jobs:delete', 'jobs:assign', 'jobs:status', 'jobs:complete',
            'customers:view', 'customers:create', 'customers:edit', 'customers:delete', 'customers:import',
            'vehicles:view', 'vehicles:create', 'vehicles:edit',
            'estimates:view', 'estimates:create', 'estimates:edit', 'estimates:delete', 'estimates:send', 'estimates:approve', 'estimates:convert',
            'invoices:view', 'invoices:create', 'invoices:edit', 'invoices:send',
            'leads:view', 'leads:create', 'leads:edit', 'leads:delete', 'leads:convert', 'leads:assign',
            'claims:view', 'claims:create', 'claims:edit',
            'schedule:view', 'schedule:manage',
            'technicians:view', 'technicians:manage',
            'reports:view', 'reports:export',
            'hail:create', 'hail:manage',
            'communications:view', 'communications:send',
            'documents:view', 'documents:upload', 'documents:delete',
            'admin:users', 'admin:settings', 'admin:billing', 'admin:roles', 'admin:logs', 'admin:backup', 'admin:tenants',
            'billing:view', 'billing:manage'
        ],
        'owner': [
            'dashboard:manage',
            'jobs:view', 'jobs:create', 'jobs:edit', 'jobs:delete', 'jobs:assign', 'jobs:status', 'jobs:complete',
            'customers:view', 'customers:create', 'customers:edit', 'customers:delete', 'customers:import',
            'vehicles:view', 'vehicles:create', 'vehicles:edit',
            'estimates:view', 'estimates:create', 'estimates:edit', 'estimates:delete', 'estimates:send', 'estimates:approve', 'estimates:convert',
            'invoices:view', 'invoices:create', 'invoices:edit', 'invoices:send',
            'leads:view', 'leads:create', 'leads:edit', 'leads:delete', 'leads:convert', 'leads:assign',
            'claims:view', 'claims:create', 'claims:edit',
            'schedule:view', 'schedule:manage',
            'technicians:view', 'technicians:manage',
            'reports:view', 'reports:export',
            'hail:create', 'hail:manage',
            'communications:view', 'communications:send',
            'documents:view', 'documents:upload', 'documents:delete',
            'admin:users', 'admin:settings', 'admin:billing',
            'billing:view', 'billing:manage'
        ],
        'manager': [
            'jobs:view', 'jobs:create', 'jobs:edit', 'jobs:assign', 'jobs:status', 'jobs:complete',
            'customers:view', 'customers:create', 'customers:edit',
            'vehicles:view', 'vehicles:create', 'vehicles:edit',
            'estimates:view', 'estimates:create', 'estimates:edit', 'estimates:send', 'estimates:approve',
            'invoices:view', 'invoices:create', 'invoices:edit',
            'leads:view', 'leads:create', 'leads:edit', 'leads:convert', 'leads:assign',
            'claims:view', 'claims:create', 'claims:edit',
            'schedule:view', 'schedule:manage',
            'technicians:view',
            'reports:view',
            'communications:view', 'communications:send',
            'documents:view', 'documents:upload'
        ],
        'technician': [
            'jobs:view', 'jobs:status', 'jobs:complete',
            'customers:view',
            'vehicles:view',
            'estimates:view',
            'schedule:view',
            'documents:view', 'documents:upload'
        ],
        'viewer': [
            'jobs:view',
            'customers:view',
            'vehicles:view',
            'estimates:view',
            'reports:view',
            'schedule:view'
        ]
    }

    return base_permissions + role_permissions.get(role, [])
