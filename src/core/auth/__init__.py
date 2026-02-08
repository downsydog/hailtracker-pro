"""
Core authentication and authorization module
Multi-tenant RBAC system
"""

from .auth_manager import AuthManager, SeatLimitExceeded
from .decorators import (
    login_required,
    require_permission,
    require_any_permission,
    require_role,
    owner_only,
    admin_only,
    kiosk_allowed
)
from .middleware import TenantMiddleware, org_scope, get_current_org_id, get_current_user_id

__all__ = [
    'AuthManager',
    'SeatLimitExceeded',
    'login_required',
    'require_permission',
    'require_any_permission',
    'require_role',
    'owner_only',
    'admin_only',
    'kiosk_allowed',
    'TenantMiddleware',
    'org_scope',
    'get_current_org_id',
    'get_current_user_id'
]
