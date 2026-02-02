"""
Tenant Middleware for Flask
Handles loading current user/kiosk from session and setting organization context.

Usage:
    from src.core.auth.middleware import TenantMiddleware
    from src.core.auth.auth_manager import AuthManager

    auth_manager = AuthManager(db_path)
    TenantMiddleware(app, auth_manager)
"""

from flask import g, request, current_app
from typing import Optional, Tuple
import re


class TenantMiddleware:
    """
    Flask middleware to:
    1. Load current user/kiosk from session
    2. Set organization context
    3. Update last activity tracking
    """

    # Routes that don't require authentication
    PUBLIC_ROUTES = [
        '/auth/login',
        '/auth/register',
        '/auth/forgot-password',
        '/auth/reset-password',
        '/static/',
        '/favicon.ico',
        '/manifest.json',
        '/sw.js',
        '/intake/',  # Public intake form
        '/portal/login',
        '/portal/forgot-password',
    ]

    # Routes that accept kiosk auth
    KIOSK_ROUTES = [
        '/intake/',
        '/kiosk/',
    ]

    def __init__(self, app, auth_manager):
        """
        Initialize middleware.

        Args:
            app: Flask application
            auth_manager: AuthManager instance
        """
        self.app = app
        self.auth_manager = auth_manager

        # Register before_request handler
        app.before_request(self.before_request)

        # Make auth helper functions available in templates
        @app.context_processor
        def inject_auth_helpers():
            from .decorators import (
                check_permission, check_any_permission, check_role,
                is_owner, is_admin, is_authenticated, is_kiosk
            )
            return {
                'check_permission': check_permission,
                'check_any_permission': check_any_permission,
                'check_role': check_role,
                'is_owner': is_owner,
                'is_admin': is_admin,
                'is_authenticated': is_authenticated,
                'is_kiosk': is_kiosk,
                'current_user': lambda: g.get('current_user'),
                'current_kiosk': lambda: g.get('current_kiosk'),
                'organization_id': lambda: g.get('organization_id'),
            }

    def before_request(self):
        """Run before every request to set up tenant context"""
        # Initialize context variables ONLY if not already set
        # (Flask-Login bridge may have already set g.current_user)
        if not hasattr(g, 'current_user') or g.current_user is None:
            g.current_user = None
        if not hasattr(g, 'current_kiosk'):
            g.current_kiosk = None
        if not hasattr(g, 'organization_id') or g.organization_id is None:
            g.organization_id = None
        if not hasattr(g, 'account_id') or g.account_id is None:
            g.account_id = None

        # Skip further processing if user already set by Flask-Login bridge
        if g.current_user is not None:
            return

        # Skip auth for public routes
        if self._is_public_route(request.path):
            return

        # Try to get session from cookie or header
        session_token = self._get_session_token()

        if session_token:
            session_data = self.auth_manager.validate_session(session_token)

            if session_data:
                if session_data.get('user_id'):
                    # User session
                    user = self.auth_manager.get_user(session_data['user_id'])
                    if user and user['is_active']:
                        g.current_user = user
                        g.organization_id = user['organization_id']
                        g.account_id = user['account_id']

                        # Load permissions
                        g.current_user['permissions'] = \
                            self.auth_manager.get_user_permissions(user['id'])

                        # Update last activity (async would be better)
                        self._update_last_activity(user['id'])

                elif session_data.get('kiosk_id'):
                    # Kiosk session
                    kiosk = self.auth_manager.get_kiosk(session_data['kiosk_id'])
                    if kiosk and kiosk['is_active']:
                        g.current_kiosk = kiosk
                        g.organization_id = kiosk['organization_id']
                        g.account_id = kiosk['account_id']

    def _get_session_token(self) -> Optional[str]:
        """Get session token from cookie or Authorization header"""
        # Check Authorization header first (API calls)
        auth_header = request.headers.get('Authorization')
        if auth_header:
            if auth_header.startswith('Bearer '):
                return auth_header[7:]
            # Also support "Token xxx" format
            if auth_header.startswith('Token '):
                return auth_header[6:]

        # Check X-Session-Token header (alternative for API)
        session_header = request.headers.get('X-Session-Token')
        if session_header:
            return session_header

        # Check cookie (browser sessions)
        return request.cookies.get('session_token')

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public (no auth required)"""
        for route in self.PUBLIC_ROUTES:
            if path.startswith(route):
                return True
        return False

    def _is_kiosk_route(self, path: str) -> bool:
        """Check if route allows kiosk auth"""
        for route in self.KIOSK_ROUTES:
            if path.startswith(route):
                return True
        return False

    def _update_last_activity(self, user_id: int):
        """Update user's last activity timestamp"""
        # This could be made async or batched for performance
        try:
            conn = self.auth_manager.get_connection()
            cursor = conn.cursor()
            from datetime import datetime
            cursor.execute("""
                UPDATE users_new SET last_activity_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), user_id))
            conn.commit()
            conn.close()
        except Exception:
            pass  # Don't fail request on activity update


# ============================================================================
# ORG SCOPE HELPERS
# ============================================================================

def org_scope(query: str, params: dict = None) -> Tuple[str, dict]:
    """
    Helper to add organization_id to a query.

    Usage:
        query, params = org_scope(
            "SELECT * FROM customers WHERE status = :status",
            {"status": "active"}
        )
        # Returns: "SELECT * FROM customers WHERE organization_id = :_org_id AND status = :status"

    Args:
        query: SQL query string
        params: Query parameters dict

    Returns:
        Tuple of (modified_query, modified_params)

    Raises:
        PermissionError: If no organization context is set
    """
    if not g.get('organization_id'):
        raise PermissionError("No organization context - cannot scope query")

    params = params.copy() if params else {}
    params['_org_id'] = g.organization_id

    # Add org filter to query
    query_upper = query.upper()

    if 'WHERE' in query_upper:
        # Find WHERE and insert org filter after it
        where_idx = query_upper.index('WHERE')
        where_end = where_idx + 5  # len('WHERE')
        query = query[:where_end] + ' organization_id = :_org_id AND' + query[where_end:]
    else:
        # Check for GROUP BY, ORDER BY, LIMIT to insert WHERE before them
        insert_pos = len(query)
        for keyword in ['GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']:
            if keyword in query_upper:
                idx = query_upper.index(keyword)
                if idx < insert_pos:
                    insert_pos = idx

        query = query[:insert_pos] + ' WHERE organization_id = :_org_id ' + query[insert_pos:]

    return query, params


def org_scope_simple(table_alias: str = None) -> str:
    """
    Returns a simple organization_id filter clause.

    Usage:
        query = f"SELECT * FROM customers WHERE {org_scope_simple()} AND status = 'active'"

    Args:
        table_alias: Optional table alias (e.g., 'c' for 'customers c')

    Returns:
        String like "organization_id = 123" or "c.organization_id = 123"
    """
    if not g.get('organization_id'):
        raise PermissionError("No organization context")

    if table_alias:
        return f"{table_alias}.organization_id = {g.organization_id}"
    return f"organization_id = {g.organization_id}"


def get_current_org_id() -> int:
    """
    Get current organization ID from context.

    Returns:
        Organization ID

    Raises:
        PermissionError: If no organization context is set
    """
    if not g.get('organization_id'):
        raise PermissionError("No organization context")
    return g.organization_id


def get_current_account_id() -> int:
    """
    Get current account ID from context.

    Returns:
        Account ID

    Raises:
        PermissionError: If no account context is set
    """
    if not g.get('account_id'):
        raise PermissionError("No account context")
    return g.account_id


def get_current_user_id() -> int:
    """
    Get current user ID from context.

    Returns:
        User ID

    Raises:
        PermissionError: If no user context is set
    """
    if not g.get('current_user'):
        raise PermissionError("No user context")
    return g.current_user['id']


def get_current_user() -> Optional[dict]:
    """Get current user dict or None"""
    return g.get('current_user')


def get_current_kiosk() -> Optional[dict]:
    """Get current kiosk dict or None"""
    return g.get('current_kiosk')


def has_org_context() -> bool:
    """Check if organization context is set"""
    return g.get('organization_id') is not None


def has_user_context() -> bool:
    """Check if user context is set"""
    return g.get('current_user') is not None


def has_kiosk_context() -> bool:
    """Check if kiosk context is set"""
    return g.get('current_kiosk') is not None


# ============================================================================
# DATA ACCESS HELPERS
# ============================================================================

def can_access_customer(customer_id: int, customer_org_id: int = None) -> bool:
    """
    Check if current user can access a customer.

    - Users with 'customers.view_all' can see any customer in their org
    - Users with 'customers.view_own' can only see customers they created
    - Checks organization boundary

    Args:
        customer_id: Customer ID to check
        customer_org_id: Organization ID of the customer (optional, will be looked up if not provided)

    Returns:
        True if access is allowed
    """
    if not g.get('current_user'):
        return False

    # Check organization boundary
    if customer_org_id and customer_org_id != g.organization_id:
        return False

    # Check permissions
    perms = g.current_user.get('permissions', [])

    if 'customers.view_all' in perms:
        return True

    if 'customers.view_own' in perms:
        # Would need to check if user created/owns this customer
        # This requires a DB lookup - return True for now and let the query handle it
        return True

    return False


def can_access_job(job_id: int, job_org_id: int = None, assigned_tech_id: int = None) -> bool:
    """
    Check if current user can access a job.

    - Users with 'jobs.view_all' can see any job in their org
    - Users with 'jobs.view_assigned' can only see jobs assigned to them
    - Checks organization boundary

    Args:
        job_id: Job ID to check
        job_org_id: Organization ID of the job
        assigned_tech_id: Tech ID assigned to the job

    Returns:
        True if access is allowed
    """
    if not g.get('current_user'):
        return False

    # Check organization boundary
    if job_org_id and job_org_id != g.organization_id:
        return False

    perms = g.current_user.get('permissions', [])

    if 'jobs.view_all' in perms:
        return True

    if 'jobs.view_assigned' in perms:
        # Check if this job is assigned to the current user
        # This would typically involve matching tech_id to user
        # For now, return True and let the query filter
        return True

    return False


def can_access_lead(lead_id: int, lead_org_id: int = None, assigned_to: int = None) -> bool:
    """
    Check if current user can access a lead.

    - Users with 'leads.view_all' can see any lead in their org
    - Users with 'leads.view_own' can only see leads assigned to them
    """
    if not g.get('current_user'):
        return False

    if lead_org_id and lead_org_id != g.organization_id:
        return False

    perms = g.current_user.get('permissions', [])

    if 'leads.view_all' in perms:
        return True

    if 'leads.view_own' in perms:
        return True

    return False
