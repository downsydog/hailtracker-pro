"""
Tenant Context for HailTracker Pro
Gets current tenant from JWT token for multi-tenant queries
"""

from flask import g
import os

# DEV_MODE defaults to tenant_id = 1
DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'
DEFAULT_TENANT_ID = 1


def get_current_tenant_id() -> int:
    """
    Get the current user's tenant ID from the JWT token.

    In DEV_MODE or if no user is authenticated, returns DEFAULT_TENANT_ID (1).

    Returns:
        int: Current tenant ID
    """
    # Check if we have a current user from the JWT middleware
    if hasattr(g, 'current_user') and g.current_user:
        tenant_id = g.current_user.get('tenant_id')
        if tenant_id is not None:
            return int(tenant_id)

    # Fallback to default tenant in DEV_MODE
    if DEV_MODE:
        return DEFAULT_TENANT_ID

    # No user and not in DEV_MODE - this shouldn't happen for protected routes
    return DEFAULT_TENANT_ID


def get_current_user_id() -> int:
    """
    Get the current user's ID from the JWT token.

    Returns:
        int: Current user ID, or 1 in DEV_MODE
    """
    if hasattr(g, 'current_user') and g.current_user:
        user_id = g.current_user.get('user_id')
        if user_id is not None:
            return int(user_id)

    if DEV_MODE:
        return 1

    return None


def get_current_user_role() -> str:
    """
    Get the current user's role from the JWT token.

    Returns:
        str: User role (admin, owner, manager, technician, viewer)
    """
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user.get('role', 'viewer')

    if DEV_MODE:
        return 'admin'

    return 'viewer'


def is_admin() -> bool:
    """Check if current user is an admin."""
    return get_current_user_role() == 'admin'


def is_owner_or_admin() -> bool:
    """Check if current user is an owner or admin."""
    role = get_current_user_role()
    return role in ('admin', 'owner')


def is_manager_or_above() -> bool:
    """Check if current user is a manager, owner, or admin."""
    role = get_current_user_role()
    return role in ('admin', 'owner', 'manager')


def tenant_filter(query: str, table_alias: str = None) -> str:
    """
    Add tenant_id filter to a SQL query.

    Args:
        query: The SQL query to modify
        table_alias: Optional table alias (e.g., 'l' for leads)

    Returns:
        Modified query with tenant_id filter

    Example:
        query = "SELECT * FROM leads WHERE status = 'new'"
        query = tenant_filter(query, 'leads')
        # Result: "SELECT * FROM leads WHERE status = 'new' AND leads.tenant_id = 1"
    """
    tenant_id = get_current_tenant_id()
    prefix = f"{table_alias}." if table_alias else ""

    # Check if query already has WHERE clause
    if 'WHERE' in query.upper():
        return f"{query} AND {prefix}tenant_id = {tenant_id}"
    else:
        return f"{query} WHERE {prefix}tenant_id = {tenant_id}"


def get_tenant_context() -> dict:
    """
    Get full tenant context including user info.

    Returns:
        dict with tenant_id, user_id, role, and permissions
    """
    return {
        'tenant_id': get_current_tenant_id(),
        'user_id': get_current_user_id(),
        'role': get_current_user_role(),
        'is_admin': is_admin(),
        'is_owner_or_admin': is_owner_or_admin(),
        'is_manager_or_above': is_manager_or_above(),
        'dev_mode': DEV_MODE
    }
