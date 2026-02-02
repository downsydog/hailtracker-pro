"""
Seed RBAC Data
Creates roles, permissions, and role-permission mappings for the multi-tenant system.

Usage:
    python scripts/seed_rbac.py [database_path]

This script is idempotent - safe to run multiple times.
"""

import sqlite3
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.models.tenant_schema import init_tenant_schema

# ============================================================================
# ROLES
# ============================================================================
ROLES = [
    {
        "name": "owner",
        "display_name": "Owner",
        "description": "Full access to everything including billing. One per account.",
        "counts_as_seat": True,
        "sort_order": 1
    },
    {
        "name": "admin",
        "display_name": "Administrator",
        "description": "Full access except billing. Can manage users and settings.",
        "counts_as_seat": True,
        "sort_order": 2
    },
    {
        "name": "office",
        "display_name": "Office Staff",
        "description": "CRM, scheduling, claims processing. Cannot manage users.",
        "counts_as_seat": True,
        "sort_order": 3
    },
    {
        "name": "sales",
        "display_name": "Sales / Canvasser",
        "description": "Lead capture, hail maps, door-to-door. Sees only their leads.",
        "counts_as_seat": True,
        "sort_order": 4
    },
    {
        "name": "tech",
        "display_name": "Technician",
        "description": "Assigned jobs, status updates, photos. Sees only their work.",
        "counts_as_seat": True,
        "sort_order": 5
    },
    {
        "name": "estimator",
        "display_name": "Estimator",
        "description": "Create and edit estimates. Cannot approve or process claims.",
        "counts_as_seat": True,
        "sort_order": 6
    },
    {
        "name": "kiosk",
        "display_name": "Kiosk Device",
        "description": "Customer walk-in tablet. Lead capture only.",
        "counts_as_seat": False,
        "sort_order": 99
    }
]

# ============================================================================
# PERMISSIONS
# ============================================================================
PERMISSIONS = [
    # Dashboard
    {"name": "dashboard.view", "display_name": "View Dashboard", "category": "dashboard", "sort_order": 1},
    {"name": "dashboard.analytics", "display_name": "View Analytics", "category": "dashboard", "sort_order": 2},

    # Customers
    {"name": "customers.view_all", "display_name": "View All Customers", "category": "customers", "sort_order": 10},
    {"name": "customers.view_own", "display_name": "View Own Customers", "category": "customers", "sort_order": 11},
    {"name": "customers.create", "display_name": "Create Customers", "category": "customers", "sort_order": 12},
    {"name": "customers.edit", "display_name": "Edit Customers", "category": "customers", "sort_order": 13},
    {"name": "customers.delete", "display_name": "Delete Customers", "category": "customers", "sort_order": 14},

    # Leads
    {"name": "leads.view_all", "display_name": "View All Leads", "category": "leads", "sort_order": 20},
    {"name": "leads.view_own", "display_name": "View Own Leads", "category": "leads", "sort_order": 21},
    {"name": "leads.create", "display_name": "Create Leads", "category": "leads", "sort_order": 22},
    {"name": "leads.edit", "display_name": "Edit Leads", "category": "leads", "sort_order": 23},
    {"name": "leads.convert", "display_name": "Convert Leads to Customers", "category": "leads", "sort_order": 24},
    {"name": "leads.assign", "display_name": "Assign Leads", "category": "leads", "sort_order": 25},

    # Vehicles
    {"name": "vehicles.view", "display_name": "View Vehicles", "category": "vehicles", "sort_order": 30},
    {"name": "vehicles.create", "display_name": "Create Vehicles", "category": "vehicles", "sort_order": 31},
    {"name": "vehicles.edit", "display_name": "Edit Vehicles", "category": "vehicles", "sort_order": 32},

    # Jobs
    {"name": "jobs.view_all", "display_name": "View All Jobs", "category": "jobs", "sort_order": 40},
    {"name": "jobs.view_assigned", "display_name": "View Assigned Jobs", "category": "jobs", "sort_order": 41},
    {"name": "jobs.create", "display_name": "Create Jobs", "category": "jobs", "sort_order": 42},
    {"name": "jobs.edit", "display_name": "Edit Jobs", "category": "jobs", "sort_order": 43},
    {"name": "jobs.assign", "display_name": "Assign Jobs", "category": "jobs", "sort_order": 44},
    {"name": "jobs.update_status", "display_name": "Update Job Status", "category": "jobs", "sort_order": 45},
    {"name": "jobs.delete", "display_name": "Delete Jobs", "category": "jobs", "sort_order": 46},

    # Estimates
    {"name": "estimates.view_all", "display_name": "View All Estimates", "category": "estimates", "sort_order": 50},
    {"name": "estimates.view_own", "display_name": "View Own Estimates", "category": "estimates", "sort_order": 51},
    {"name": "estimates.create", "display_name": "Create Estimates", "category": "estimates", "sort_order": 52},
    {"name": "estimates.edit", "display_name": "Edit Estimates", "category": "estimates", "sort_order": 53},
    {"name": "estimates.approve", "display_name": "Approve Estimates", "category": "estimates", "sort_order": 54},
    {"name": "estimates.send", "display_name": "Send Estimates", "category": "estimates", "sort_order": 55},
    {"name": "estimates.delete", "display_name": "Delete Estimates", "category": "estimates", "sort_order": 56},

    # Insurance / Claims
    {"name": "claims.view", "display_name": "View Claims", "category": "claims", "sort_order": 60},
    {"name": "claims.create", "display_name": "Create Claims", "category": "claims", "sort_order": 61},
    {"name": "claims.manage", "display_name": "Manage Claims", "category": "claims", "sort_order": 62},

    # Scheduling
    {"name": "schedule.view", "display_name": "View Schedule", "category": "schedule", "sort_order": 70},
    {"name": "schedule.manage", "display_name": "Manage Schedule", "category": "schedule", "sort_order": 71},

    # Invoices / Payments
    {"name": "invoices.view", "display_name": "View Invoices", "category": "invoices", "sort_order": 80},
    {"name": "invoices.create", "display_name": "Create Invoices", "category": "invoices", "sort_order": 81},
    {"name": "invoices.manage", "display_name": "Manage Invoices", "category": "invoices", "sort_order": 82},
    {"name": "payments.record", "display_name": "Record Payments", "category": "invoices", "sort_order": 83},

    # Hail / Weather
    {"name": "hail.view_map", "display_name": "View Hail Map", "category": "hail", "sort_order": 90},
    {"name": "hail.view_swaths", "display_name": "View Storm Swaths", "category": "hail", "sort_order": 91},
    {"name": "hail.manage_alerts", "display_name": "Manage Hail Alerts", "category": "hail", "sort_order": 92},

    # Technicians (as records, not users)
    {"name": "technicians.view", "display_name": "View Technicians", "category": "technicians", "sort_order": 100},
    {"name": "technicians.manage", "display_name": "Manage Technicians", "category": "technicians", "sort_order": 101},

    # Reports
    {"name": "reports.view", "display_name": "View Reports", "category": "reports", "sort_order": 110},
    {"name": "reports.export", "display_name": "Export Reports", "category": "reports", "sort_order": 111},

    # Communications
    {"name": "communications.view", "display_name": "View Communications", "category": "communications", "sort_order": 120},
    {"name": "communications.send", "display_name": "Send Communications", "category": "communications", "sort_order": 121},

    # Documents / Photos
    {"name": "documents.view", "display_name": "View Documents", "category": "documents", "sort_order": 130},
    {"name": "documents.upload", "display_name": "Upload Documents", "category": "documents", "sort_order": 131},
    {"name": "documents.delete", "display_name": "Delete Documents", "category": "documents", "sort_order": 132},

    # Users / Admin
    {"name": "users.view", "display_name": "View Users", "category": "admin", "sort_order": 140},
    {"name": "users.create", "display_name": "Create Users", "category": "admin", "sort_order": 141},
    {"name": "users.edit", "display_name": "Edit Users", "category": "admin", "sort_order": 142},
    {"name": "users.deactivate", "display_name": "Deactivate Users", "category": "admin", "sort_order": 143},

    # Settings
    {"name": "settings.view", "display_name": "View Settings", "category": "admin", "sort_order": 150},
    {"name": "settings.manage", "display_name": "Manage Settings", "category": "admin", "sort_order": 151},

    # Billing (owner only)
    {"name": "billing.view", "display_name": "View Billing", "category": "billing", "sort_order": 160},
    {"name": "billing.manage", "display_name": "Manage Billing", "category": "billing", "sort_order": 161},

    # Kiosk-specific
    {"name": "kiosk.intake", "display_name": "Customer Intake Form", "category": "kiosk", "sort_order": 170},
]

# ============================================================================
# ROLE → PERMISSION MAPPING
# ============================================================================
ROLE_PERMISSIONS = {
    "owner": [
        # Everything - special case handled in code
        "*"
    ],

    "admin": [
        # Everything except billing
        "dashboard.view",
        "dashboard.analytics",
        "customers.view_all",
        "customers.create",
        "customers.edit",
        "customers.delete",
        "leads.view_all",
        "leads.create",
        "leads.edit",
        "leads.convert",
        "leads.assign",
        "vehicles.view",
        "vehicles.create",
        "vehicles.edit",
        "jobs.view_all",
        "jobs.create",
        "jobs.edit",
        "jobs.assign",
        "jobs.update_status",
        "jobs.delete",
        "estimates.view_all",
        "estimates.create",
        "estimates.edit",
        "estimates.approve",
        "estimates.send",
        "estimates.delete",
        "claims.view",
        "claims.create",
        "claims.manage",
        "schedule.view",
        "schedule.manage",
        "invoices.view",
        "invoices.create",
        "invoices.manage",
        "payments.record",
        "hail.view_map",
        "hail.view_swaths",
        "hail.manage_alerts",
        "technicians.view",
        "technicians.manage",
        "reports.view",
        "reports.export",
        "communications.view",
        "communications.send",
        "documents.view",
        "documents.upload",
        "documents.delete",
        "users.view",
        "users.create",
        "users.edit",
        "users.deactivate",
        "settings.view",
        "settings.manage",
    ],

    "office": [
        "dashboard.view",
        "dashboard.analytics",
        "customers.view_all",
        "customers.create",
        "customers.edit",
        "leads.view_all",
        "leads.create",
        "leads.edit",
        "leads.convert",
        "leads.assign",
        "vehicles.view",
        "vehicles.create",
        "vehicles.edit",
        "jobs.view_all",
        "jobs.create",
        "jobs.edit",
        "jobs.assign",
        "jobs.update_status",
        "estimates.view_all",
        "estimates.approve",
        "estimates.send",
        "claims.view",
        "claims.create",
        "claims.manage",
        "schedule.view",
        "schedule.manage",
        "invoices.view",
        "invoices.create",
        "invoices.manage",
        "payments.record",
        "technicians.view",
        "reports.view",
        "reports.export",
        "communications.view",
        "communications.send",
        "documents.view",
        "documents.upload",
    ],

    "sales": [
        "dashboard.view",
        "customers.view_own",
        "customers.create",
        "leads.view_own",
        "leads.create",
        "leads.edit",
        "vehicles.view",
        "vehicles.create",
        "hail.view_map",
        "hail.view_swaths",
        "communications.send",
        "documents.view",
        "documents.upload",
    ],

    "tech": [
        "dashboard.view",
        "customers.view_own",
        "jobs.view_assigned",
        "jobs.update_status",
        "vehicles.view",
        "estimates.view_own",
        "schedule.view",
        "documents.view",
        "documents.upload",
        "communications.send",
        # Special: can create leads (gas station mode)
        "leads.create",
    ],

    "estimator": [
        "dashboard.view",
        "customers.view_all",
        "customers.create",
        "vehicles.view",
        "vehicles.create",
        "vehicles.edit",
        "jobs.view_all",
        "estimates.view_all",
        "estimates.create",
        "estimates.edit",
        "estimates.send",
        "claims.view",
        "documents.view",
        "documents.upload",
    ],

    "kiosk": [
        "kiosk.intake",
        "leads.create",
        "customers.create",
        "vehicles.create",
    ],
}


def seed_roles(cursor):
    """Seed role data"""
    print("\nSeeding roles...")

    for role in ROLES:
        cursor.execute("""
            INSERT OR REPLACE INTO roles (name, display_name, description, counts_as_seat, is_system, sort_order)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (
            role["name"],
            role["display_name"],
            role["description"],
            1 if role["counts_as_seat"] else 0,
            role["sort_order"]
        ))
        print(f"  [+] {role['display_name']} ({role['name']})")

    return len(ROLES)


def seed_permissions(cursor):
    """Seed permission data"""
    print("\nSeeding permissions...")

    categories = {}
    for perm in PERMISSIONS:
        cat = perm["category"]
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1

        cursor.execute("""
            INSERT OR REPLACE INTO permissions (name, display_name, category, sort_order)
            VALUES (?, ?, ?, ?)
        """, (
            perm["name"],
            perm["display_name"],
            perm["category"],
            perm["sort_order"]
        ))

    for cat, count in sorted(categories.items()):
        print(f"  [+] {cat}: {count} permissions")

    return len(PERMISSIONS)


def seed_role_permissions(cursor):
    """Seed role-permission mappings"""
    print("\nSeeding role-permission mappings...")

    # Get role IDs
    cursor.execute("SELECT id, name FROM roles")
    role_map = {row[1]: row[0] for row in cursor.fetchall()}

    # Get permission IDs
    cursor.execute("SELECT id, name FROM permissions")
    perm_map = {row[1]: row[0] for row in cursor.fetchall()}

    # Get all permission names for wildcard expansion
    all_permissions = list(perm_map.keys())

    total_mappings = 0

    for role_name, permissions in ROLE_PERMISSIONS.items():
        if role_name not in role_map:
            print(f"  [!] Role '{role_name}' not found, skipping")
            continue

        role_id = role_map[role_name]

        # Expand wildcards
        expanded_permissions = []
        for perm in permissions:
            if perm == "*":
                # All permissions
                expanded_permissions.extend(all_permissions)
            elif perm.endswith(".*"):
                # Category wildcard (e.g., "dashboard.*")
                category = perm[:-2]
                expanded_permissions.extend([p for p in all_permissions if p.startswith(category + ".")])
            else:
                expanded_permissions.append(perm)

        # Remove duplicates while preserving order
        seen = set()
        unique_permissions = []
        for p in expanded_permissions:
            if p not in seen:
                seen.add(p)
                unique_permissions.append(p)

        count = 0
        for perm_name in unique_permissions:
            if perm_name not in perm_map:
                # Permission might not exist (e.g., typo)
                continue

            perm_id = perm_map[perm_name]
            cursor.execute("""
                INSERT OR REPLACE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            """, (role_id, perm_id))
            count += 1

        print(f"  [+] {role_name}: {count} permissions")
        total_mappings += count

    return total_mappings


def seed_rbac(db_path: str = "data/hailtracker_crm.db"):
    """
    Main function to seed all RBAC data.
    Creates tenant schema if needed, then seeds roles/permissions.
    """
    print("=" * 60)
    print("RBAC SEED SCRIPT")
    print("=" * 60)

    # Ensure schema exists
    print("\nStep 1: Ensuring tenant schema exists...")
    init_tenant_schema(db_path)

    # Connect and seed data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Seed roles
        role_count = seed_roles(cursor)

        # Seed permissions
        perm_count = seed_permissions(cursor)

        # Seed role-permission mappings
        mapping_count = seed_role_permissions(cursor)

        conn.commit()

        print("\n" + "=" * 60)
        print("RBAC SEEDING COMPLETE")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Roles: {role_count}")
        print(f"  - Permissions: {perm_count}")
        print(f"  - Role-Permission Mappings: {mapping_count}")
        print()

        # Show role summary
        print("Role Summary:")
        cursor.execute("""
            SELECT r.display_name, r.counts_as_seat, COUNT(rp.id) as perm_count
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            GROUP BY r.id
            ORDER BY r.sort_order
        """)
        for row in cursor.fetchall():
            seat_status = "seat" if row[1] else "no-seat"
            print(f"  - {row[0]}: {row[2]} permissions ({seat_status})")

        return True

    except Exception as e:
        print(f"\n[ERROR] Seeding failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/hailtracker_crm.db"

    seed_rbac(db_path)
