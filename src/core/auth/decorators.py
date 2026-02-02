"""
Permission Decorators for Flask Routes
Provides decorators to protect routes based on authentication and permissions.

Usage:
    @login_required
    def my_view():
        ...

    @require_permission('customers.create')
    def create_customer():
        ...

    @require_role('admin', 'owner')
    def admin_action():
        ...
"""

from functools import wraps
from flask import g, request, jsonify, redirect, url_for, flash
from typing import Union, List


def login_required(f):
    """
    Require authenticated user (any role).

    Redirects to login page for browser requests, returns 401 for API requests.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.get('current_user'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def require_permission(permission: str):
    """
    Require specific permission.

    Usage:
        @require_permission('customers.create')
        def create_customer():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not g.get('current_user'):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Authentication required',
                        'code': 'AUTH_REQUIRED'
                    }), 401
                return redirect(url_for('auth.login', next=request.url))

            user_perms = g.current_user.get('permissions', [])
            if permission not in user_perms:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Permission denied',
                        'code': 'PERMISSION_DENIED',
                        'required': permission
                    }), 403
                flash('You do not have permission to access this resource.', 'error')
                return redirect(url_for('home.index'))

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_any_permission(*permissions):
    """
    Require at least one of the permissions.

    Usage:
        @require_any_permission('customers.view_all', 'customers.view_own')
        def view_customers():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not g.get('current_user'):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Authentication required',
                        'code': 'AUTH_REQUIRED'
                    }), 401
                return redirect(url_for('auth.login', next=request.url))

            user_perms = set(g.current_user.get('permissions', []))
            if not user_perms.intersection(set(permissions)):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Permission denied',
                        'code': 'PERMISSION_DENIED',
                        'required_any': list(permissions)
                    }), 403
                flash('You do not have permission to access this resource.', 'error')
                return redirect(url_for('home.index'))

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_all_permissions(*permissions):
    """
    Require all of the specified permissions.

    Usage:
        @require_all_permissions('estimates.create', 'estimates.send')
        def create_and_send_estimate():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not g.get('current_user'):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Authentication required',
                        'code': 'AUTH_REQUIRED'
                    }), 401
                return redirect(url_for('auth.login', next=request.url))

            user_perms = set(g.current_user.get('permissions', []))
            missing = set(permissions) - user_perms
            if missing:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Permission denied',
                        'code': 'PERMISSION_DENIED',
                        'required_all': list(permissions),
                        'missing': list(missing)
                    }), 403
                flash('You do not have permission to access this resource.', 'error')
                return redirect(url_for('home.index'))

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_role(*roles):
    """
    Require one of the specified roles.

    Usage:
        @require_role('admin', 'owner')
        def admin_action():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not g.get('current_user'):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Authentication required',
                        'code': 'AUTH_REQUIRED'
                    }), 401
                return redirect(url_for('auth.login', next=request.url))

            user_role = g.current_user.get('role')
            if user_role not in roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': 'Role not authorized',
                        'code': 'ROLE_DENIED',
                        'required_role': list(roles)
                    }), 403
                flash('You do not have the required role to access this resource.', 'error')
                return redirect(url_for('home.index'))

            return f(*args, **kwargs)
        return decorated
    return decorator


def owner_only(f):
    """Require owner role (shortcut for @require_role('owner'))"""
    return require_role('owner')(f)


def admin_only(f):
    """Require owner or admin role (shortcut for @require_role('owner', 'admin'))"""
    return require_role('owner', 'admin')(f)


def office_or_above(f):
    """Require office, admin, or owner role"""
    return require_role('owner', 'admin', 'office')(f)


def kiosk_allowed(f):
    """
    Allow kiosk devices OR authenticated users.

    Used for routes that can be accessed by both kiosks and regular users,
    like the customer intake form.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.get('current_user') and not g.get('current_kiosk'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated


def kiosk_only(f):
    """
    Require kiosk device authentication only.

    Used for routes that should only be accessed by kiosk devices.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.get('current_kiosk'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Kiosk authentication required',
                    'code': 'KIOSK_REQUIRED'
                }), 401
            flash('This resource requires kiosk access.', 'error')
            return redirect(url_for('home.index'))
        return f(*args, **kwargs)
    return decorated


def same_organization(f):
    """
    Ensure user can only access resources in their organization.

    This decorator checks that a resource's organization_id matches
    the current user's organization. Should be used with other decorators.

    Note: This assumes the route has an 'organization_id' parameter or
    the view function returns data that can be organization-scoped.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.get('current_user') and not g.get('current_kiosk'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'code': 'AUTH_REQUIRED'
                }), 401
            return redirect(url_for('auth.login', next=request.url))

        # Check if org_id is in kwargs
        resource_org_id = kwargs.get('organization_id')
        if resource_org_id and resource_org_id != g.organization_id:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Access denied to this organization',
                    'code': 'ORG_DENIED'
                }), 403
            flash('You do not have access to this organization.', 'error')
            return redirect(url_for('home.index'))

        return f(*args, **kwargs)
    return decorated


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_permission(permission: str) -> bool:
    """
    Check if current user has a permission without raising an error.

    Useful in templates or conditional logic:
        {% if check_permission('estimates.approve') %}
            <button>Approve</button>
        {% endif %}
    """
    if not g.get('current_user'):
        return False
    return permission in g.current_user.get('permissions', [])


def check_any_permission(*permissions) -> bool:
    """Check if current user has any of the permissions"""
    if not g.get('current_user'):
        return False
    user_perms = set(g.current_user.get('permissions', []))
    return bool(user_perms.intersection(set(permissions)))


def check_role(*roles) -> bool:
    """Check if current user has one of the roles"""
    if not g.get('current_user'):
        return False
    return g.current_user.get('role') in roles


def is_owner() -> bool:
    """Check if current user is an owner"""
    return check_role('owner')


def is_admin() -> bool:
    """Check if current user is an admin or owner"""
    return check_role('owner', 'admin')


def is_authenticated() -> bool:
    """Check if there is a current user"""
    return g.get('current_user') is not None


def is_kiosk() -> bool:
    """Check if current session is a kiosk"""
    return g.get('current_kiosk') is not None
