"""
Permission decorators for route protection
"""

from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """
    Decorator to require admin role

    Usage:
        @app.route('/admin/users')
        @login_required
        @admin_required
        def manage_users():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if not current_user.is_admin():
            flash('You need admin privileges to access this page.', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """
    Decorator to require manager or admin role
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if not current_user.is_manager():
            flash('You need manager privileges to access this page.', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def permission_required(resource, action):
    """
    Decorator to require specific permission

    Usage:
        @app.route('/deals/create')
        @login_required
        @permission_required('deals', 'create')
        def create_deal():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            if not current_user.can(resource, action):
                flash(f'You do not have permission to {action} {resource}.', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def own_resource_or_admin(get_resource_owner_id):
    """
    Decorator to allow access only to own resources or if admin

    Usage:
        @app.route('/deal/<int:deal_id>/edit')
        @login_required
        @own_resource_or_admin(lambda deal_id: get_deal_owner(deal_id))
        def edit_deal(deal_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            # Admins can access everything
            if current_user.is_admin():
                return f(*args, **kwargs)

            # Check if user owns the resource
            resource_owner_id = get_resource_owner_id(**kwargs)

            if resource_owner_id != current_user.id:
                flash('You can only access your own resources.', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
