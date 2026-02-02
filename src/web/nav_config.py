"""
Navigation configuration by role.
Defines what each role sees in their nav.

Roles:
- owner: Full access, desktop layout
- admin: Full access except billing, desktop layout
- office: CRM + operations, desktop layout
- estimator: Estimates + jobs, desktop layout
- sales: Mobile-optimized, lead capture focus
- tech: Mobile-optimized, job completion focus
"""

from typing import Dict, List, Optional


NAV_CONFIG = {
    "owner": {
        "layout": "desktop",
        "primary_action": {"label": "New Customer", "route": "/app/customers/new", "icon": "user-plus"},
        "items": [
            {"icon": "layout-dashboard", "label": "Dashboard", "route": "/app/dashboard", "permission": "dashboard.view"},
            {"type": "divider", "label": "CRM"},
            {"icon": "users", "label": "Customers", "route": "/app/customers", "permission": "customers.view_all"},
            {"icon": "target", "label": "Leads", "route": "/app/leads", "permission": "leads.view_all"},
            {"icon": "truck", "label": "Vehicles", "route": "/app/vehicles", "permission": "vehicles.view"},
            {"type": "divider", "label": "Operations"},
            {"icon": "briefcase", "label": "Jobs", "route": "/app/jobs", "permission": "jobs.view_all"},
            {"icon": "file-text", "label": "Estimates", "route": "/app/estimates", "permission": "estimates.view_all"},
            {"icon": "calendar", "label": "Schedule", "route": "/app/schedule", "permission": "schedule.view"},
            {"icon": "shield", "label": "Claims", "route": "/app/claims", "permission": "claims.view"},
            {"type": "divider", "label": "Weather"},
            {"icon": "cloud-rain", "label": "Hail Map", "route": "/app/hail-map", "permission": "hail.view_map"},
            {"icon": "alert-triangle", "label": "Storm Alerts", "route": "/app/alerts", "permission": "hail.manage_alerts"},
            {"type": "divider", "label": "Finance"},
            {"icon": "file-invoice-dollar", "label": "Invoices", "route": "/app/invoices", "permission": "invoices.view"},
            {"icon": "bar-chart-2", "label": "Reports", "route": "/app/reports", "permission": "reports.view"},
            {"type": "divider", "label": "Admin"},
            {"icon": "users-cog", "label": "Team", "route": "/app/team", "permission": "users.view"},
            {"icon": "tablet", "label": "Kiosks", "route": "/app/kiosks", "permission": "settings.manage"},
            {"icon": "settings", "label": "Settings", "route": "/app/settings", "permission": "settings.manage"},
            {"icon": "credit-card", "label": "Billing", "route": "/app/billing", "permission": "billing.view"},
        ]
    },

    "admin": {
        "layout": "desktop",
        "primary_action": {"label": "New Customer", "route": "/app/customers/new", "icon": "user-plus"},
        "items": [
            {"icon": "layout-dashboard", "label": "Dashboard", "route": "/app/dashboard", "permission": "dashboard.view"},
            {"type": "divider", "label": "CRM"},
            {"icon": "users", "label": "Customers", "route": "/app/customers", "permission": "customers.view_all"},
            {"icon": "target", "label": "Leads", "route": "/app/leads", "permission": "leads.view_all"},
            {"icon": "truck", "label": "Vehicles", "route": "/app/vehicles", "permission": "vehicles.view"},
            {"type": "divider", "label": "Operations"},
            {"icon": "briefcase", "label": "Jobs", "route": "/app/jobs", "permission": "jobs.view_all"},
            {"icon": "file-text", "label": "Estimates", "route": "/app/estimates", "permission": "estimates.view_all"},
            {"icon": "calendar", "label": "Schedule", "route": "/app/schedule", "permission": "schedule.view"},
            {"icon": "shield", "label": "Claims", "route": "/app/claims", "permission": "claims.view"},
            {"type": "divider", "label": "Weather"},
            {"icon": "cloud-rain", "label": "Hail Map", "route": "/app/hail-map", "permission": "hail.view_map"},
            {"icon": "alert-triangle", "label": "Storm Alerts", "route": "/app/alerts", "permission": "hail.manage_alerts"},
            {"type": "divider", "label": "Finance"},
            {"icon": "file-invoice-dollar", "label": "Invoices", "route": "/app/invoices", "permission": "invoices.view"},
            {"icon": "bar-chart-2", "label": "Reports", "route": "/app/reports", "permission": "reports.view"},
            {"type": "divider", "label": "Admin"},
            {"icon": "users-cog", "label": "Team", "route": "/app/team", "permission": "users.view"},
            {"icon": "tablet", "label": "Kiosks", "route": "/app/kiosks", "permission": "settings.manage"},
            {"icon": "settings", "label": "Settings", "route": "/app/settings", "permission": "settings.manage"},
        ]
    },

    "office": {
        "layout": "desktop",
        "primary_action": {"label": "New Customer", "route": "/app/customers/new", "icon": "user-plus"},
        "items": [
            {"icon": "layout-dashboard", "label": "Dashboard", "route": "/app/dashboard", "permission": "dashboard.view"},
            {"type": "divider", "label": "CRM"},
            {"icon": "users", "label": "Customers", "route": "/app/customers", "permission": "customers.view_all"},
            {"icon": "target", "label": "Leads", "route": "/app/leads", "permission": "leads.view_all"},
            {"icon": "truck", "label": "Vehicles", "route": "/app/vehicles", "permission": "vehicles.view"},
            {"type": "divider", "label": "Operations"},
            {"icon": "briefcase", "label": "Jobs", "route": "/app/jobs", "permission": "jobs.view_all"},
            {"icon": "file-text", "label": "Estimates", "route": "/app/estimates", "permission": "estimates.view_all"},
            {"icon": "calendar", "label": "Schedule", "route": "/app/schedule", "permission": "schedule.view"},
            {"icon": "shield", "label": "Claims", "route": "/app/claims", "permission": "claims.view"},
            {"type": "divider", "label": "Weather"},
            {"icon": "cloud-rain", "label": "Hail Map", "route": "/app/hail-map", "permission": "hail.view_map"},
            {"type": "divider", "label": "Finance"},
            {"icon": "file-invoice-dollar", "label": "Invoices", "route": "/app/invoices", "permission": "invoices.view"},
            {"icon": "bar-chart-2", "label": "Reports", "route": "/app/reports", "permission": "reports.view"},
        ]
    },

    "estimator": {
        "layout": "desktop",
        "primary_action": {"label": "New Estimate", "route": "/app/estimates/new", "icon": "file-plus"},
        "items": [
            {"icon": "layout-dashboard", "label": "Dashboard", "route": "/app/dashboard", "permission": "dashboard.view"},
            {"type": "divider", "label": "Work"},
            {"icon": "file-text", "label": "Estimates", "route": "/app/estimates", "permission": "estimates.view_all"},
            {"icon": "briefcase", "label": "Jobs", "route": "/app/jobs", "permission": "jobs.view_all"},
            {"type": "divider", "label": "Reference"},
            {"icon": "users", "label": "Customers", "route": "/app/customers", "permission": "customers.view_all"},
            {"icon": "truck", "label": "Vehicles", "route": "/app/vehicles", "permission": "vehicles.view"},
        ]
    },

    "sales": {
        "layout": "mobile",
        "primary_action": {"label": "New Lead", "route": "/app/leads/new", "icon": "plus"},
        "items": [
            {"icon": "home", "label": "Home", "route": "/app/dashboard"},
            {"icon": "map", "label": "Map", "route": "/app/hail-map"},
            {"icon": "plus-circle", "label": "Lead", "route": "/app/leads/new", "primary": True},
            {"icon": "list", "label": "Leads", "route": "/app/leads"},
            {"icon": "user", "label": "Me", "route": "/app/profile"},
        ]
    },

    "tech": {
        "layout": "mobile",
        "primary_action": {"label": "Update Job", "route": "/app/jobs/update", "icon": "edit"},
        "items": [
            {"icon": "home", "label": "Home", "route": "/app/dashboard"},
            {"icon": "briefcase", "label": "Jobs", "route": "/app/jobs"},
            {"icon": "camera", "label": "Photo", "route": "/app/photos/upload", "primary": True},
            {"icon": "clock", "label": "Hours", "route": "/app/hours"},
            {"icon": "user", "label": "Me", "route": "/app/profile"},
        ]
    }
}


def get_nav_for_user(user: dict) -> dict:
    """
    Get navigation config for a user based on their role.

    Args:
        user: User dict with role and permissions

    Returns:
        Dict with layout, primary_action, and filtered items
    """
    if not user:
        return {'layout': 'desktop', 'primary_action': None, 'items': []}

    role = user.get('role', 'office')
    config = NAV_CONFIG.get(role, NAV_CONFIG['office'])

    # Filter items by permission
    filtered_items = []
    user_permissions = set(user.get('permissions', []))

    # Check if user has wildcard permission (full access)
    has_all_permissions = '*' in user_permissions

    for item in config['items']:
        if item.get('type') == 'divider':
            filtered_items.append(item)
        elif 'permission' not in item or has_all_permissions or item['permission'] in user_permissions:
            filtered_items.append(item)

    # Remove orphaned dividers (dividers with no items after them)
    cleaned_items = []
    for i, item in enumerate(filtered_items):
        if item.get('type') == 'divider':
            # Check if there's a non-divider item after this
            has_following_item = False
            for j in range(i + 1, len(filtered_items)):
                if filtered_items[j].get('type') != 'divider':
                    has_following_item = True
                    break
                elif filtered_items[j].get('type') == 'divider':
                    # Another divider means this section is empty
                    break
            if has_following_item:
                cleaned_items.append(item)
        else:
            cleaned_items.append(item)

    # Remove leading dividers
    while cleaned_items and cleaned_items[0].get('type') == 'divider':
        cleaned_items.pop(0)

    # Remove trailing dividers
    while cleaned_items and cleaned_items[-1].get('type') == 'divider':
        cleaned_items.pop()

    return {
        'layout': config['layout'],
        'primary_action': config.get('primary_action'),
        'items': cleaned_items
    }


def get_role_display_name(role: str) -> str:
    """Get display name for a role"""
    display_names = {
        'owner': 'Owner',
        'admin': 'Administrator',
        'office': 'Office Staff',
        'estimator': 'Estimator',
        'sales': 'Sales',
        'tech': 'Technician',
        'kiosk': 'Kiosk'
    }
    return display_names.get(role, role.title())
