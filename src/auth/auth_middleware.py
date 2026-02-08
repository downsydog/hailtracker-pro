"""
JWT Authentication Middleware for HailTracker Pro
Decorators for protecting API routes
"""

from functools import wraps
from flask import request, jsonify, g
import os

from .jwt_utils import verify_token, get_dev_user, DEV_MODE


def login_required(f):
    """
    Decorator that requires a valid JWT token to access the route.

    In DEV_MODE, automatically uses a dev admin user UNLESS:
    - X-Test-Auth: true header is present (forces real auth)
    - Authorization header is present (uses real token)

    Usage:
        @app.route('/api/protected')
        @login_required
        def protected_route():
            user = g.current_user  # Access current user info
            return jsonify({'user_id': user['user_id']})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        test_auth = request.headers.get('X-Test-Auth', '').lower() == 'true'

        # DEV_MODE bypass - auto-authenticate as dev admin
        # UNLESS X-Test-Auth header is set OR Authorization header is present
        if DEV_MODE and not test_auth and not auth_header:
            dev_user = get_dev_user()
            g.current_user = {
                'user_id': dev_user['user_id'],
                'tenant_id': dev_user['tenant_id'],
                'email': dev_user['email'],
                'role': dev_user['role'],
                'name': dev_user['name']
            }
            return f(*args, **kwargs)

        # Real authentication required
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401

        # Extract token from "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'error': 'Invalid authorization format. Use: Bearer <token>'}), 401

        token = parts[1]

        # Verify the token
        payload = verify_token(token)

        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        if payload.get('type') != 'access':
            return jsonify({'error': 'Invalid token type'}), 401

        # Store user info in Flask's g object for access in route
        g.current_user = {
            'user_id': payload.get('user_id'),  # Use numeric user_id
            'tenant_id': payload.get('tenant_id'),
            'email': payload.get('email'),
            'role': payload.get('role'),
            'name': payload.get('name')
        }

        return f(*args, **kwargs)

    return decorated_function


def require_role(*allowed_roles):
    """
    Decorator that requires the user to have one of the specified roles.
    Must be used AFTER @login_required.

    Args:
        *allowed_roles: Role names that are allowed (e.g., 'admin', 'manager')

    Usage:
        @app.route('/api/admin/users')
        @login_required
        @require_role('admin')
        def admin_only_route():
            ...

        @app.route('/api/manage')
        @login_required
        @require_role('admin', 'manager')
        def manager_route():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({'error': 'Authentication required'}), 401

            user_role = g.current_user.get('role')

            # Admin always has access
            if user_role == 'admin':
                return f(*args, **kwargs)

            # Check if user's role is in allowed roles
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'This action requires one of these roles: {", ".join(allowed_roles)}',
                    'your_role': user_role
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def get_current_user():
    """
    Get the current authenticated user from Flask's g object.

    Returns:
        Dict with user info or None if not authenticated
    """
    return getattr(g, 'current_user', None)


def get_current_tenant_id():
    """
    Get the current user's tenant ID.

    Returns:
        Tenant ID or 1 (default) in DEV_MODE if not authenticated
    """
    user = get_current_user()
    if user:
        return user.get('tenant_id', 1)
    return 1 if DEV_MODE else None


def get_current_user_id():
    """
    Get the current user's ID.

    Returns:
        User ID or None if not authenticated
    """
    user = get_current_user()
    if user:
        return user.get('user_id')
    return 1 if DEV_MODE else None
