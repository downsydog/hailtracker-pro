"""
Role-Based Access Control (RBAC) for HailTracker Pro
Defines what each role can access
"""

from functools import wraps
from flask import g, jsonify
import os

DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'

# Role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    'viewer': 1,
    'technician': 2,
    'manager': 3,
    'owner': 4,
    'admin': 5
}

# Permission definitions by role
ROLE_PERMISSIONS = {
    'admin': {
        # Admin has EVERYTHING
        'storms': ['view', 'create', 'edit', 'delete'],
        'leads': ['view', 'create', 'edit', 'delete', 'assign', 'convert'],
        'jobs': ['view', 'create', 'edit', 'delete', 'assign', 'complete'],
        'estimates': ['view', 'create', 'edit', 'delete', 'approve', 'send'],
        'customers': ['view', 'create', 'edit', 'delete', 'import'],
        'schedule': ['view', 'create', 'edit', 'delete', 'manage'],
        'reports': ['view', 'export'],
        'team': ['view', 'create', 'edit', 'delete'],
        'settings': ['view', 'edit'],
        'billing': ['view', 'manage'],
        'admin': ['tenants', 'users', 'settings', 'logs', 'backup'],
    },
    'owner': {
        # Owner can do everything except system admin
        'storms': ['view', 'create', 'edit'],
        'leads': ['view', 'create', 'edit', 'delete', 'assign', 'convert'],
        'jobs': ['view', 'create', 'edit', 'delete', 'assign', 'complete'],
        'estimates': ['view', 'create', 'edit', 'delete', 'approve', 'send'],
        'customers': ['view', 'create', 'edit', 'delete', 'import'],
        'schedule': ['view', 'create', 'edit', 'delete', 'manage'],
        'reports': ['view', 'export'],
        'team': ['view', 'create', 'edit', 'delete'],
        'settings': ['view', 'edit'],
        'billing': ['view', 'manage'],
    },
    'manager': {
        # Manager: leads, jobs, estimates, customers, schedule
        'storms': ['view'],
        'leads': ['view', 'create', 'edit', 'assign', 'convert'],
        'jobs': ['view', 'create', 'edit', 'assign', 'complete'],
        'estimates': ['view', 'create', 'edit', 'approve', 'send'],
        'customers': ['view', 'create', 'edit'],
        'schedule': ['view', 'create', 'edit', 'manage'],
        'reports': ['view'],
        'team': ['view'],
    },
    'technician': {
        # Technician: assigned jobs only, view customers
        'storms': ['view'],
        'leads': ['view'],
        'jobs': ['view', 'complete'],  # Only assigned jobs
        'estimates': ['view'],
        'customers': ['view'],
        'schedule': ['view'],
    },
    'viewer': {
        # Viewer: read-only access
        'storms': ['view'],
        'leads': ['view'],
        'jobs': ['view'],
        'estimates': ['view'],
        'customers': ['view'],
        'schedule': ['view'],
        'reports': ['view'],
    }
}


def get_role_level(role: str) -> int:
    """Get the hierarchy level for a role."""
    return ROLE_HIERARCHY.get(role, 0)


def has_permission(role: str, resource: str, action: str) -> bool:
    """
    Check if a role has permission to perform an action on a resource.

    Args:
        role: User's role (admin, owner, manager, technician, viewer)
        resource: Resource type (storms, leads, jobs, etc.)
        action: Action to perform (view, create, edit, delete, etc.)

    Returns:
        True if role has permission, False otherwise
    """
    # Admin always has permission
    if role == 'admin':
        return True

    permissions = ROLE_PERMISSIONS.get(role, {})
    resource_perms = permissions.get(resource, [])

    return action in resource_perms


def can_access(resource: str, action: str):
    """
    Decorator to check if current user can perform action on resource.
    Must be used AFTER @login_required.

    Usage:
        @app.route('/api/leads/<id>', methods=['DELETE'])
        @login_required
        @can_access('leads', 'delete')
        def delete_lead(id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'error': 'Authentication required'}), 401

            user_role = g.current_user.get('role', 'viewer')

            # DEV_MODE: admin access
            if DEV_MODE:
                user_role = 'admin'

            if not has_permission(user_role, resource, action):
                return jsonify({
                    'error': 'Access denied',
                    'message': f'You do not have permission to {action} {resource}',
                    'required_permission': f'{resource}:{action}',
                    'your_role': user_role
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_role_level(min_level: str):
    """
    Decorator that requires a minimum role level.

    Args:
        min_level: Minimum role required (viewer, technician, manager, owner, admin)

    Usage:
        @app.route('/api/reports')
        @login_required
        @require_role_level('manager')
        def get_reports():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'error': 'Authentication required'}), 401

            user_role = g.current_user.get('role', 'viewer')

            # DEV_MODE: admin access
            if DEV_MODE:
                user_role = 'admin'

            user_level = get_role_level(user_role)
            required_level = get_role_level(min_level)

            if user_level < required_level:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'This action requires {min_level} level or higher',
                    'your_role': user_role,
                    'required_role': min_level
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def get_user_permissions(role: str) -> dict:
    """
    Get all permissions for a role.

    Args:
        role: User's role

    Returns:
        Dict of resource -> list of allowed actions
    """
    if role == 'admin':
        return ROLE_PERMISSIONS['admin']

    return ROLE_PERMISSIONS.get(role, {})


def get_permission_list(role: str) -> list:
    """
    Get permissions as a flat list of 'resource:action' strings.
    Used for JWT token and frontend permission checking.

    Args:
        role: User's role

    Returns:
        List of permission strings like ['leads:view', 'leads:create', ...]
    """
    permissions = get_user_permissions(role)
    result = []

    for resource, actions in permissions.items():
        for action in actions:
            result.append(f'{resource}:{action}')

    return result
