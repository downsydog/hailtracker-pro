"""
Admin Portal Routes for HailTracker Pro
All routes require admin role
"""

from flask import Blueprint, jsonify, request, g
from functools import wraps
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

# Database connection
DATABASE_URL = os.environ.get('MASTER_DATABASE_URL', 'postgresql://hailtracker:hailtracker_dev_2024@localhost:5432/hailtracker_master')

DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def get_db():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def require_admin(f):
    """Decorator that requires admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In DEV_MODE, allow all requests
        if DEV_MODE:
            return f(*args, **kwargs)

        # Check if user is authenticated
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({'error': 'Authentication required'}), 401

        user_role = g.current_user.get('role', 'viewer')

        if user_role != 'admin':
            return jsonify({
                'error': 'Access denied',
                'message': 'Admin role required',
                'your_role': user_role
            }), 403

        return f(*args, **kwargs)

    return decorated_function


# ============================================
# TENANT MANAGEMENT
# ============================================

@admin_bp.route('/tenants', methods=['GET'])
@require_admin
def list_tenants():
    """Get all tenants."""
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT t.id, t.company_name, t.slug, t.owner_email, t.plan, t.status,
                   t.max_users, t.created_at,
                   (SELECT COUNT(*) FROM users WHERE tenant_id = t.id) as user_count
            FROM tenants t
            ORDER BY t.created_at DESC
        """)

        tenants = cur.fetchall()
        conn.close()

        # Convert to list of dicts
        result = []
        for t in tenants:
            result.append({
                'id': t['id'],
                'company_name': t['company_name'],
                'slug': t['slug'],
                'owner_email': t['owner_email'],
                'plan': t['plan'],
                'status': t['status'],
                'max_users': t['max_users'],
                'user_count': t['user_count'],
                'created_at': t['created_at'].isoformat() if t['created_at'] else None
            })

        return jsonify({
            'tenants': result,
            'total': len(result)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/tenants', methods=['POST'])
@require_admin
def create_tenant():
    """Create a new tenant."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required = ['company_name', 'owner_email']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        company_name = data['company_name']
        owner_email = data['owner_email']
        plan = data.get('plan', 'free')
        status = data.get('status', 'active')
        max_users = data.get('max_users', 2)

        # Generate slug from company name
        slug = company_name.lower().replace(' ', '-').replace("'", '')

        conn = get_db()
        cur = conn.cursor()

        # Check if slug already exists
        cur.execute("SELECT id FROM tenants WHERE slug = %s", (slug,))
        if cur.fetchone():
            conn.close()
            return jsonify({'error': 'A tenant with this name already exists'}), 409

        cur.execute("""
            INSERT INTO tenants (company_name, slug, owner_email, plan, status, max_users, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (company_name, slug, owner_email, plan, status, max_users, datetime.utcnow()))

        tenant_id = cur.fetchone()['id']
        conn.commit()
        conn.close()

        return jsonify({
            'id': tenant_id,
            'company_name': company_name,
            'slug': slug,
            'owner_email': owner_email,
            'plan': plan,
            'status': status,
            'max_users': max_users,
            'message': 'Tenant created successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['GET'])
@require_admin
def get_tenant(tenant_id):
    """Get a specific tenant."""
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT t.*,
                   (SELECT COUNT(*) FROM users WHERE tenant_id = t.id) as user_count,
                   (SELECT COUNT(*) FROM leads WHERE tenant_id = t.id) as lead_count,
                   (SELECT COUNT(*) FROM jobs WHERE tenant_id = t.id) as job_count
            FROM tenants t
            WHERE t.id = %s
        """, (tenant_id,))

        tenant = cur.fetchone()
        conn.close()

        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        return jsonify({
            'id': tenant['id'],
            'company_name': tenant['company_name'],
            'slug': tenant['slug'],
            'owner_email': tenant['owner_email'],
            'plan': tenant['plan'],
            'status': tenant['status'],
            'max_users': tenant['max_users'],
            'user_count': tenant['user_count'],
            'lead_count': tenant['lead_count'],
            'job_count': tenant['job_count'],
            'created_at': tenant['created_at'].isoformat() if tenant['created_at'] else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/tenants/<int:tenant_id>', methods=['PUT'])
@require_admin
def update_tenant(tenant_id):
    """Update a tenant."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        conn = get_db()
        cur = conn.cursor()

        # Check if tenant exists
        cur.execute("SELECT id FROM tenants WHERE id = %s", (tenant_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({'error': 'Tenant not found'}), 404

        # Build update query dynamically
        allowed_fields = ['company_name', 'plan', 'status', 'max_users', 'owner_email']
        updates = []
        values = []

        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = %s")
                values.append(data[field])

        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        values.append(tenant_id)

        cur.execute(f"""
            UPDATE tenants SET {', '.join(updates)}
            WHERE id = %s
            RETURNING *
        """, values)

        tenant = cur.fetchone()
        conn.commit()
        conn.close()

        return jsonify({
            'id': tenant['id'],
            'company_name': tenant['company_name'],
            'slug': tenant['slug'],
            'owner_email': tenant['owner_email'],
            'plan': tenant['plan'],
            'status': tenant['status'],
            'max_users': tenant['max_users'],
            'message': 'Tenant updated successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# USER MANAGEMENT
# ============================================

@admin_bp.route('/users', methods=['GET'])
@require_admin
def list_users():
    """Get all users across all tenants."""
    try:
        tenant_id = request.args.get('tenant_id', type=int)

        conn = get_db()
        cur = conn.cursor()

        if tenant_id:
            cur.execute("""
                SELECT u.id, u.tenant_id, u.email, u.name, u.phone, u.role,
                       u.is_active, u.last_login, u.created_at,
                       t.company_name as tenant_name
                FROM users u
                LEFT JOIN tenants t ON u.tenant_id = t.id
                WHERE u.tenant_id = %s
                ORDER BY u.created_at DESC
            """, (tenant_id,))
        else:
            cur.execute("""
                SELECT u.id, u.tenant_id, u.email, u.name, u.phone, u.role,
                       u.is_active, u.last_login, u.created_at,
                       t.company_name as tenant_name
                FROM users u
                LEFT JOIN tenants t ON u.tenant_id = t.id
                ORDER BY u.created_at DESC
            """)

        users = cur.fetchall()
        conn.close()

        result = []
        for u in users:
            result.append({
                'id': u['id'],
                'tenant_id': u['tenant_id'],
                'tenant_name': u['tenant_name'],
                'email': u['email'],
                'name': u['name'],
                'phone': u['phone'],
                'role': u['role'],
                'is_active': u['is_active'],
                'last_login': u['last_login'].isoformat() if u['last_login'] else None,
                'created_at': u['created_at'].isoformat() if u['created_at'] else None
            })

        return jsonify({
            'users': result,
            'total': len(result)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users', methods=['POST'])
@require_admin
def create_user():
    """Create a new user (admin only)."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required = ['email', 'password', 'name', 'tenant_id']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        import bcrypt

        email = data['email'].lower().strip()
        password = data['password']
        name = data['name']
        tenant_id = data['tenant_id']
        role = data.get('role', 'viewer')
        phone = data.get('phone')
        is_active = data.get('is_active', True)

        # Validate role
        valid_roles = ['admin', 'owner', 'manager', 'technician', 'viewer']
        if role not in valid_roles:
            return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400

        conn = get_db()
        cur = conn.cursor()

        # Check if email already exists
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            conn.close()
            return jsonify({'error': 'Email already registered'}), 409

        # Check if tenant exists
        cur.execute("SELECT id, max_users FROM tenants WHERE id = %s", (tenant_id,))
        tenant = cur.fetchone()
        if not tenant:
            conn.close()
            return jsonify({'error': 'Tenant not found'}), 404

        # Check max users limit
        cur.execute("SELECT COUNT(*) as count FROM users WHERE tenant_id = %s", (tenant_id,))
        user_count = cur.fetchone()['count']
        if tenant['max_users'] and user_count >= tenant['max_users']:
            conn.close()
            return jsonify({'error': f'Tenant has reached maximum user limit ({tenant["max_users"]})'}), 403

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cur.execute("""
            INSERT INTO users (tenant_id, email, password_hash, name, phone, role, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (tenant_id, email, password_hash, name, phone, role, is_active, datetime.utcnow()))

        user_id = cur.fetchone()['id']
        conn.commit()
        conn.close()

        return jsonify({
            'id': user_id,
            'email': email,
            'name': name,
            'tenant_id': tenant_id,
            'role': role,
            'message': 'User created successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@require_admin
def get_user(user_id):
    """Get a specific user."""
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT u.id, u.tenant_id, u.email, u.name, u.phone, u.role,
                   u.is_active, u.last_login, u.created_at,
                   t.company_name as tenant_name
            FROM users u
            LEFT JOIN tenants t ON u.tenant_id = t.id
            WHERE u.id = %s
        """, (user_id,))

        user = cur.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'id': user['id'],
            'tenant_id': user['tenant_id'],
            'tenant_name': user['tenant_name'],
            'email': user['email'],
            'name': user['name'],
            'phone': user['phone'],
            'role': user['role'],
            'is_active': user['is_active'],
            'last_login': user['last_login'].isoformat() if user['last_login'] else None,
            'created_at': user['created_at'].isoformat() if user['created_at'] else None
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    """Update a user."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        conn = get_db()
        cur = conn.cursor()

        # Check if user exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        # Build update query dynamically
        allowed_fields = ['name', 'phone', 'role', 'is_active', 'tenant_id']
        updates = []
        values = []

        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = %s")
                values.append(data[field])

        # Handle password update separately
        if 'password' in data and data['password']:
            import bcrypt
            password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            updates.append("password_hash = %s")
            values.append(password_hash)

        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        values.append(user_id)

        cur.execute(f"""
            UPDATE users SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, email, name, role, is_active, tenant_id
        """, values)

        user = cur.fetchone()
        conn.commit()
        conn.close()

        return jsonify({
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': user['role'],
            'is_active': user['is_active'],
            'tenant_id': user['tenant_id'],
            'message': 'User updated successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# STATS
# ============================================

@admin_bp.route('/stats', methods=['GET'])
@require_admin
def get_stats():
    """Get system-wide statistics."""
    try:
        conn = get_db()
        cur = conn.cursor()

        # Get counts
        cur.execute("SELECT COUNT(*) as count FROM tenants")
        tenant_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM users")
        user_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM storms")
        storm_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM leads")
        lead_count = cur.fetchone()['count']

        cur.execute("SELECT COUNT(*) as count FROM jobs")
        job_count = cur.fetchone()['count']

        # Get plan distribution
        cur.execute("""
            SELECT plan, COUNT(*) as count
            FROM tenants
            GROUP BY plan
        """)
        plan_distribution = {}
        for row in cur.fetchall():
            plan_distribution[row['plan'] or 'unknown'] = row['count']

        # Get recent signups (last 30 days)
        cur.execute("""
            SELECT COUNT(*) as count
            FROM tenants
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        recent_signups = cur.fetchone()['count']

        # Get active users (logged in last 7 days)
        cur.execute("""
            SELECT COUNT(*) as count
            FROM users
            WHERE last_login > NOW() - INTERVAL '7 days'
        """)
        active_users = cur.fetchone()['count']

        conn.close()

        return jsonify({
            'tenants': {
                'total': tenant_count,
                'recent_signups': recent_signups,
                'plan_distribution': plan_distribution
            },
            'users': {
                'total': user_count,
                'active_last_7_days': active_users
            },
            'storms': storm_count,
            'leads': lead_count,
            'jobs': job_count,
            'system_health': 'ok'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# API USAGE
# ============================================

@admin_bp.route('/api-usage', methods=['GET'])
@require_admin
def get_api_usage():
    """Get API usage statistics."""
    try:
        tenant_id = request.args.get('tenant_id', type=int)
        days = request.args.get('days', 30, type=int)

        conn = get_db()
        cur = conn.cursor()

        if tenant_id:
            cur.execute("""
                SELECT api_name, SUM(calls_count) as total_calls,
                       COUNT(DISTINCT date) as days_used
                FROM api_usage
                WHERE tenant_id = %s AND date > NOW() - INTERVAL '%s days'
                GROUP BY api_name
                ORDER BY total_calls DESC
            """, (tenant_id, days))
        else:
            cur.execute("""
                SELECT api_name, SUM(calls_count) as total_calls,
                       COUNT(DISTINCT date) as days_used,
                       COUNT(DISTINCT tenant_id) as tenants_using
                FROM api_usage
                WHERE date > NOW() - INTERVAL '%s days'
                GROUP BY api_name
                ORDER BY total_calls DESC
            """, (days,))

        usage_by_api = cur.fetchall()

        # Get daily totals
        if tenant_id:
            cur.execute("""
                SELECT date, SUM(calls_count) as total_calls
                FROM api_usage
                WHERE tenant_id = %s AND date > NOW() - INTERVAL '%s days'
                GROUP BY date
                ORDER BY date DESC
            """, (tenant_id, days))
        else:
            cur.execute("""
                SELECT date, SUM(calls_count) as total_calls
                FROM api_usage
                WHERE date > NOW() - INTERVAL '%s days'
                GROUP BY date
                ORDER BY date DESC
            """, (days,))

        daily_usage = cur.fetchall()

        conn.close()

        return jsonify({
            'by_api': [dict(row) for row in usage_by_api],
            'daily': [{
                'date': row['date'].isoformat() if row['date'] else None,
                'total_calls': row['total_calls']
            } for row in daily_usage],
            'period_days': days
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
