"""
API Middleware
==============
Authentication and authorization decorators.
"""

from functools import wraps
from flask import jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from backend.app.models.master.user import User


def get_current_user():
    """
    Get the current user from JWT token.

    Returns:
        dict: User identity from token or None
    """
    identity = get_jwt_identity()
    if not identity:
        return None
    return identity


def login_required(f):
    """
    Decorator to require login for a route.

    Usage:
        @app.route('/protected')
        @login_required
        def protected():
            return 'This is protected'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            # Store identity in g for easy access
            g.current_user = get_jwt_identity()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Authentication required',
                'code': 'auth_required',
                'message': str(e)
            }), 401
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin (owner) role.

    Usage:
        @app.route('/admin-only')
        @admin_required
        def admin_only():
            return 'Owner access only'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            g.current_user = identity

            if identity.get('role') != User.ROLE_OWNER:
                return jsonify({
                    'error': 'Owner access required',
                    'code': 'owner_required'
                }), 403

            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Authentication required',
                'code': 'auth_required',
                'message': str(e)
            }), 401
    return decorated_function


def manager_required(f):
    """
    Decorator to require manager or owner role.

    Usage:
        @app.route('/managers')
        @manager_required
        def managers_only():
            return 'Manager or owner access'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            g.current_user = identity

            if identity.get('role') not in [User.ROLE_OWNER, User.ROLE_MANAGER]:
                return jsonify({
                    'error': 'Manager access required',
                    'code': 'manager_required'
                }), 403

            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Authentication required',
                'code': 'auth_required',
                'message': str(e)
            }), 401
    return decorated_function


def desk_required(f):
    """
    Decorator to require desk, manager, or owner role.

    Usage:
        @app.route('/office')
        @desk_required
        def office_access():
            return 'Office staff access'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            g.current_user = identity

            allowed_roles = [User.ROLE_OWNER, User.ROLE_MANAGER, User.ROLE_DESK]
            if identity.get('role') not in allowed_roles:
                return jsonify({
                    'error': 'Office access required',
                    'code': 'desk_required'
                }), 403

            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Authentication required',
                'code': 'auth_required',
                'message': str(e)
            }), 401
    return decorated_function


def roles_required(*roles):
    """
    Decorator to require specific roles.

    Usage:
        @app.route('/specific')
        @roles_required('owner', 'manager', 'tech')
        def specific_roles():
            return 'Specific roles only'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                identity = get_jwt_identity()
                g.current_user = identity

                if identity.get('role') not in roles:
                    return jsonify({
                        'error': f'One of these roles required: {", ".join(roles)}',
                        'code': 'role_required'
                    }), 403

                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'auth_required',
                    'message': str(e)
                }), 401
        return decorated_function
    return decorator


def same_tenant_required(f):
    """
    Decorator to ensure user can only access their own tenant's data.
    Extracts tenant_id from URL and compares with token.

    Usage:
        @app.route('/tenant/<int:tenant_id>/data')
        @same_tenant_required
        def tenant_data(tenant_id):
            return 'Your tenant data'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            g.current_user = identity

            # Check if tenant_id in URL matches user's tenant
            url_tenant_id = kwargs.get('tenant_id')
            if url_tenant_id and url_tenant_id != identity.get('tenant_id'):
                return jsonify({
                    'error': 'Access denied to this tenant',
                    'code': 'tenant_mismatch'
                }), 403

            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Authentication required',
                'code': 'auth_required',
                'message': str(e)
            }), 401
    return decorated_function
