"""
Subscription Plans for HailTracker Pro
Defines plan limits and enforcement middleware
"""

from functools import wraps
from flask import g, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

# Database connection
DATABASE_URL = os.environ.get('MASTER_DATABASE_URL', 'postgresql://hailtracker:hailtracker_dev_2024@localhost:5432/hailtracker_master')

DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'

# Plan definitions
PLANS = {
    'free': {
        'name': 'Free',
        'max_users': 2,
        'max_storms_per_month': 3,
        'max_leads_per_month': 50,
        'max_jobs_per_month': 10,
        'features': ['storm_tracking', 'basic_leads', 'basic_jobs'],
        'price_monthly': 0,
        'price_yearly': 0,
    },
    'pro': {
        'name': 'Pro',
        'max_users': 8,
        'max_storms_per_month': 50,
        'max_leads_per_month': 500,
        'max_jobs_per_month': 100,
        'features': ['storm_tracking', 'advanced_leads', 'advanced_jobs', 'estimates', 'reports', 'api_access'],
        'price_monthly': 99,
        'price_yearly': 990,  # 2 months free
    },
    'enterprise': {
        'name': 'Enterprise',
        'max_users': 100,
        'max_storms_per_month': None,  # Unlimited
        'max_leads_per_month': None,   # Unlimited
        'max_jobs_per_month': None,    # Unlimited
        'features': ['storm_tracking', 'advanced_leads', 'advanced_jobs', 'estimates', 'reports', 'api_access', 'white_label', 'priority_support', 'custom_integrations'],
        'price_monthly': 299,
        'price_yearly': 2990,  # 2 months free
    }
}


def get_db():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_plan_limits(plan_name: str) -> dict:
    """Get the limits for a specific plan."""
    return PLANS.get(plan_name, PLANS['free'])


def get_tenant_plan(tenant_id: int) -> str:
    """Get the current plan for a tenant."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT plan FROM tenants WHERE id = %s", (tenant_id,))
        result = cur.fetchone()
        conn.close()
        return result['plan'] if result else 'free'
    except Exception:
        return 'free'


def get_tenant_usage(tenant_id: int) -> dict:
    """Get the current month's usage for a tenant."""
    try:
        conn = get_db()
        cur = conn.cursor()

        # Get current month start
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Count users
        cur.execute("SELECT COUNT(*) as count FROM users WHERE tenant_id = %s", (tenant_id,))
        user_count = cur.fetchone()['count']

        # Count leads this month
        cur.execute("""
            SELECT COUNT(*) as count FROM leads
            WHERE tenant_id = %s AND created_at >= %s
        """, (tenant_id, month_start))
        leads_this_month = cur.fetchone()['count']

        # Count jobs this month
        cur.execute("""
            SELECT COUNT(*) as count FROM jobs
            WHERE tenant_id = %s AND created_at >= %s
        """, (tenant_id, month_start))
        jobs_this_month = cur.fetchone()['count']

        # Count storm queries this month (from api_usage)
        cur.execute("""
            SELECT COALESCE(SUM(calls_count), 0) as count FROM api_usage
            WHERE tenant_id = %s AND api_name = 'storm_query' AND date >= %s
        """, (tenant_id, month_start.date()))
        storms_this_month = cur.fetchone()['count']

        conn.close()

        return {
            'users': user_count,
            'leads_this_month': leads_this_month,
            'jobs_this_month': jobs_this_month,
            'storms_this_month': storms_this_month,
            'month_start': month_start.isoformat()
        }
    except Exception as e:
        return {
            'users': 0,
            'leads_this_month': 0,
            'jobs_this_month': 0,
            'storms_this_month': 0,
            'error': str(e)
        }


def check_limit(tenant_id: int, resource: str) -> dict:
    """
    Check if a tenant has exceeded their plan limit for a resource.

    Args:
        tenant_id: Tenant ID
        resource: 'users', 'leads', 'jobs', or 'storms'

    Returns:
        dict with 'allowed' (bool), 'current', 'limit', and 'message'
    """
    # DEV_MODE = no limits (enterprise)
    if DEV_MODE:
        return {
            'allowed': True,
            'current': 0,
            'limit': None,
            'plan': 'enterprise',
            'dev_mode': True
        }

    plan_name = get_tenant_plan(tenant_id)
    plan = get_plan_limits(plan_name)
    usage = get_tenant_usage(tenant_id)

    if resource == 'users':
        current = usage['users']
        limit = plan['max_users']
        limit_key = 'max_users'
    elif resource == 'leads':
        current = usage['leads_this_month']
        limit = plan['max_leads_per_month']
        limit_key = 'max_leads_per_month'
    elif resource == 'jobs':
        current = usage['jobs_this_month']
        limit = plan['max_jobs_per_month']
        limit_key = 'max_jobs_per_month'
    elif resource == 'storms':
        current = usage['storms_this_month']
        limit = plan['max_storms_per_month']
        limit_key = 'max_storms_per_month'
    else:
        return {'allowed': True, 'current': 0, 'limit': None}

    # None = unlimited
    if limit is None:
        return {
            'allowed': True,
            'current': current,
            'limit': None,
            'plan': plan_name
        }

    allowed = current < limit

    return {
        'allowed': allowed,
        'current': current,
        'limit': limit,
        'plan': plan_name,
        'limit_key': limit_key,
        'message': f"You have reached your {plan_name} plan limit of {limit} {resource}. Please upgrade to continue." if not allowed else None
    }


def track_usage(tenant_id: int, api_name: str, count: int = 1):
    """Track API usage for a tenant."""
    try:
        conn = get_db()
        cur = conn.cursor()

        today = datetime.utcnow().date()

        # Upsert usage record
        cur.execute("""
            INSERT INTO api_usage (tenant_id, api_name, calls_count, date, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (tenant_id, api_name, date)
            DO UPDATE SET calls_count = api_usage.calls_count + %s
        """, (tenant_id, api_name, count, today, count))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error tracking usage: {e}")


def require_plan_limit(resource: str):
    """
    Decorator to enforce plan limits on a route.

    Usage:
        @app.route('/api/leads', methods=['POST'])
        @login_required
        @require_plan_limit('leads')
        def create_lead():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # DEV_MODE bypass
            if DEV_MODE:
                return f(*args, **kwargs)

            # Get tenant from current user
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'error': 'Authentication required'}), 401

            tenant_id = g.current_user.get('tenant_id')
            if not tenant_id:
                return jsonify({'error': 'No tenant associated with user'}), 400

            # Check limit
            result = check_limit(tenant_id, resource)

            if not result['allowed']:
                return jsonify({
                    'error': 'Plan limit exceeded',
                    'message': result['message'],
                    'current': result['current'],
                    'limit': result['limit'],
                    'plan': result['plan'],
                    'upgrade_url': '/settings/billing',
                    'resource': resource
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def get_plan_info(tenant_id: int) -> dict:
    """
    Get complete plan information for a tenant including usage.

    Args:
        tenant_id: Tenant ID

    Returns:
        Dict with plan details and current usage
    """
    plan_name = get_tenant_plan(tenant_id)
    plan = get_plan_limits(plan_name)
    usage = get_tenant_usage(tenant_id)

    # Calculate percentages
    def calc_percent(current, limit):
        if limit is None:
            return 0
        return min(100, (current / limit) * 100) if limit > 0 else 100

    return {
        'plan': plan_name,
        'plan_details': plan,
        'usage': {
            'users': {
                'current': usage['users'],
                'limit': plan['max_users'],
                'percent': calc_percent(usage['users'], plan['max_users'])
            },
            'leads_this_month': {
                'current': usage['leads_this_month'],
                'limit': plan['max_leads_per_month'],
                'percent': calc_percent(usage['leads_this_month'], plan['max_leads_per_month'])
            },
            'jobs_this_month': {
                'current': usage['jobs_this_month'],
                'limit': plan['max_jobs_per_month'],
                'percent': calc_percent(usage['jobs_this_month'], plan['max_jobs_per_month'])
            },
            'storms_this_month': {
                'current': usage['storms_this_month'],
                'limit': plan['max_storms_per_month'],
                'percent': calc_percent(usage['storms_this_month'], plan['max_storms_per_month'])
            }
        },
        'month_start': usage.get('month_start'),
        'dev_mode': DEV_MODE
    }


def can_add_user(tenant_id: int) -> dict:
    """Check if tenant can add another user."""
    return check_limit(tenant_id, 'users')


def can_create_lead(tenant_id: int) -> dict:
    """Check if tenant can create another lead this month."""
    return check_limit(tenant_id, 'leads')


def can_create_job(tenant_id: int) -> dict:
    """Check if tenant can create another job this month."""
    return check_limit(tenant_id, 'jobs')


def can_query_storms(tenant_id: int) -> dict:
    """Check if tenant can make another storm query this month."""
    return check_limit(tenant_id, 'storms')
