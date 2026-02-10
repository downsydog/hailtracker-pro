"""
Permissions Service
====================
Lightweight RBAC system for estimating workflows.

Maps user roles to specific action permissions.
"""

from typing import Dict, List, Optional, Any
from enum import Enum


class Permission(str, Enum):
    """Available permissions for estimating workflows."""

    # Estimate actions
    ESTIMATE_VIEW = 'estimate.view'
    ESTIMATE_CREATE = 'estimate.create'
    ESTIMATE_EDIT_DAMAGE = 'estimate.edit_damage'
    ESTIMATE_EDIT_PRICING = 'estimate.edit_pricing'
    ESTIMATE_SEND_EMAIL = 'estimate.send_email'
    ESTIMATE_CREATE_SHARE_LINK = 'estimate.create_share_link'
    ESTIMATE_DOWNLOAD_DISPUTE_PACK = 'estimate.download_dispute_pack'
    ESTIMATE_DOWNLOAD_PDF = 'estimate.download_pdf'
    ESTIMATE_DOWNLOAD_PHOTOSHEET = 'estimate.download_photosheet'

    # Customer authorization actions (signature-based)
    ESTIMATE_REQUEST_SIGNATURE = 'estimate.request_signature'  # Request customer authorization
    ESTIMATE_APPROVE = 'estimate.approve'  # Legacy - now maps to insurer approve
    ESTIMATE_DECLINE = 'estimate.decline'  # Legacy - now maps to insurer decline

    # Insurer workflow actions
    INSURER_SUBMIT = 'insurer.submit'  # Submit estimate to insurer
    INSURER_APPROVE = 'insurer.approve'  # Record insurer approval (locks estimate)
    INSURER_DECLINE = 'insurer.decline'  # Record insurer decline/needs revision

    # Supplement actions
    SUPPLEMENT_CREATE = 'supplement.create'
    SUPPLEMENT_SEND = 'supplement.send'
    SUPPLEMENT_VIEW = 'supplement.view'

    # Photo actions
    PHOTO_UPLOAD = 'photo.upload'
    PHOTO_DELETE = 'photo.delete'

    # System actions (admin only)
    SYSTEM_SETTINGS = 'system.settings'
    SYSTEM_USERS = 'system.users'


# Role constants (matching User model)
ROLE_OWNER = 'owner'
ROLE_MANAGER = 'manager'
ROLE_DESK = 'desk'
ROLE_TECH = 'tech'
ROLE_SALESMAN = 'salesman'

# Permission mappings per role
# Higher roles inherit from lower roles conceptually, but we define explicitly for clarity
ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    ROLE_OWNER: [
        # All permissions
        Permission.ESTIMATE_VIEW,
        Permission.ESTIMATE_CREATE,
        Permission.ESTIMATE_EDIT_DAMAGE,
        Permission.ESTIMATE_EDIT_PRICING,
        Permission.ESTIMATE_SEND_EMAIL,
        Permission.ESTIMATE_CREATE_SHARE_LINK,
        Permission.ESTIMATE_DOWNLOAD_DISPUTE_PACK,
        Permission.ESTIMATE_DOWNLOAD_PDF,
        Permission.ESTIMATE_DOWNLOAD_PHOTOSHEET,
        Permission.ESTIMATE_REQUEST_SIGNATURE,
        Permission.ESTIMATE_APPROVE,
        Permission.ESTIMATE_DECLINE,
        # Insurer workflow
        Permission.INSURER_SUBMIT,
        Permission.INSURER_APPROVE,
        Permission.INSURER_DECLINE,
        # Supplements
        Permission.SUPPLEMENT_CREATE,
        Permission.SUPPLEMENT_SEND,
        Permission.SUPPLEMENT_VIEW,
        Permission.PHOTO_UPLOAD,
        Permission.PHOTO_DELETE,
        Permission.SYSTEM_SETTINGS,
        Permission.SYSTEM_USERS,
    ],

    ROLE_MANAGER: [
        # All except system settings
        Permission.ESTIMATE_VIEW,
        Permission.ESTIMATE_CREATE,
        Permission.ESTIMATE_EDIT_DAMAGE,
        Permission.ESTIMATE_EDIT_PRICING,
        Permission.ESTIMATE_SEND_EMAIL,
        Permission.ESTIMATE_CREATE_SHARE_LINK,
        Permission.ESTIMATE_DOWNLOAD_DISPUTE_PACK,
        Permission.ESTIMATE_DOWNLOAD_PDF,
        Permission.ESTIMATE_DOWNLOAD_PHOTOSHEET,
        Permission.ESTIMATE_REQUEST_SIGNATURE,
        Permission.ESTIMATE_APPROVE,
        Permission.ESTIMATE_DECLINE,
        # Insurer workflow
        Permission.INSURER_SUBMIT,
        Permission.INSURER_APPROVE,
        Permission.INSURER_DECLINE,
        # Supplements
        Permission.SUPPLEMENT_CREATE,
        Permission.SUPPLEMENT_SEND,
        Permission.SUPPLEMENT_VIEW,
        Permission.PHOTO_UPLOAD,
        Permission.PHOTO_DELETE,
        Permission.SYSTEM_USERS,
    ],

    ROLE_DESK: [
        # Estimator role - can do most estimate actions
        Permission.ESTIMATE_VIEW,
        Permission.ESTIMATE_CREATE,
        Permission.ESTIMATE_EDIT_DAMAGE,
        Permission.ESTIMATE_EDIT_PRICING,
        Permission.ESTIMATE_SEND_EMAIL,
        Permission.ESTIMATE_CREATE_SHARE_LINK,
        Permission.ESTIMATE_DOWNLOAD_DISPUTE_PACK,
        Permission.ESTIMATE_DOWNLOAD_PDF,
        Permission.ESTIMATE_DOWNLOAD_PHOTOSHEET,
        Permission.ESTIMATE_REQUEST_SIGNATURE,
        Permission.ESTIMATE_APPROVE,
        Permission.ESTIMATE_DECLINE,
        # Insurer workflow
        Permission.INSURER_SUBMIT,
        Permission.INSURER_APPROVE,
        Permission.INSURER_DECLINE,
        # Supplements
        Permission.SUPPLEMENT_CREATE,
        Permission.SUPPLEMENT_SEND,
        Permission.SUPPLEMENT_VIEW,
        Permission.PHOTO_UPLOAD,
        Permission.PHOTO_DELETE,
    ],

    ROLE_TECH: [
        # Tech role - limited, no sending/sharing/dispute packs/approvals
        Permission.ESTIMATE_VIEW,
        Permission.ESTIMATE_EDIT_DAMAGE,
        Permission.ESTIMATE_DOWNLOAD_PDF,
        Permission.ESTIMATE_DOWNLOAD_PHOTOSHEET,
        Permission.SUPPLEMENT_VIEW,
        Permission.PHOTO_UPLOAD,
    ],

    ROLE_SALESMAN: [
        # Sales role - view and create estimates, but limited actions
        Permission.ESTIMATE_VIEW,
        Permission.ESTIMATE_CREATE,
        Permission.ESTIMATE_EDIT_DAMAGE,
        Permission.ESTIMATE_DOWNLOAD_PDF,
        Permission.SUPPLEMENT_VIEW,
        Permission.PHOTO_UPLOAD,
    ],
}

# Human-readable descriptions for permissions (for UI tooltips)
PERMISSION_DESCRIPTIONS: Dict[Permission, str] = {
    Permission.ESTIMATE_SEND_EMAIL: "Send estimate to adjuster",
    Permission.ESTIMATE_CREATE_SHARE_LINK: "Create shareable link",
    Permission.ESTIMATE_DOWNLOAD_DISPUTE_PACK: "Download dispute pack",
    Permission.ESTIMATE_REQUEST_SIGNATURE: "Request customer authorization signature",
    Permission.ESTIMATE_APPROVE: "Legacy: approve estimate",
    Permission.ESTIMATE_DECLINE: "Legacy: decline estimate",
    Permission.INSURER_SUBMIT: "Submit estimate to insurer",
    Permission.INSURER_APPROVE: "Record insurer approval (locks estimate)",
    Permission.INSURER_DECLINE: "Record insurer decline/needs revision",
    Permission.SUPPLEMENT_CREATE: "Create supplements",
    Permission.SUPPLEMENT_SEND: "Send supplement to adjuster",
}

# Required roles for each permission (for error messages)
PERMISSION_REQUIRED_ROLES: Dict[Permission, List[str]] = {
    Permission.ESTIMATE_SEND_EMAIL: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.ESTIMATE_CREATE_SHARE_LINK: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.ESTIMATE_DOWNLOAD_DISPUTE_PACK: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.ESTIMATE_REQUEST_SIGNATURE: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.ESTIMATE_APPROVE: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.ESTIMATE_DECLINE: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.INSURER_SUBMIT: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.INSURER_APPROVE: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.INSURER_DECLINE: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.SUPPLEMENT_CREATE: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.SUPPLEMENT_SEND: [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK],
    Permission.SYSTEM_SETTINGS: [ROLE_OWNER],
    Permission.SYSTEM_USERS: [ROLE_OWNER, ROLE_MANAGER],
}


def can(user_identity: Dict[str, Any], permission: Permission) -> bool:
    """
    Check if user has a specific permission.

    Args:
        user_identity: JWT identity dict with 'role', 'user_id', 'tenant_id'
        permission: Permission to check

    Returns:
        True if user has permission, False otherwise
    """
    if not user_identity:
        return False

    role = user_identity.get('role')
    if not role:
        return False

    # Get permissions for this role
    permissions = ROLE_PERMISSIONS.get(role, [])

    return permission in permissions


def get_user_permissions(role: str) -> List[str]:
    """
    Get all permissions for a given role.

    Args:
        role: User role string

    Returns:
        List of permission strings
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    return [p.value for p in permissions]


def get_permission_denied_message(permission: Permission) -> str:
    """
    Get a human-readable error message for permission denied.

    Args:
        permission: The denied permission

    Returns:
        Error message string
    """
    required_roles = PERMISSION_REQUIRED_ROLES.get(permission, [])
    if required_roles:
        roles_str = ', '.join(required_roles)
        return f"This action requires one of these roles: {roles_str}"
    return "You do not have permission to perform this action"


def get_role_display_name(role: str) -> str:
    """
    Get a human-readable display name for a role.

    Args:
        role: Role string

    Returns:
        Display name
    """
    display_names = {
        ROLE_OWNER: 'Owner',
        ROLE_MANAGER: 'Manager',
        ROLE_DESK: 'Estimator',
        ROLE_TECH: 'Technician',
        ROLE_SALESMAN: 'Sales',
    }
    return display_names.get(role, role.title())


def get_role_permissions_summary(role: str) -> Dict[str, bool]:
    """
    Get a summary of key permissions for a role.
    Useful for frontend UI gating.

    Args:
        role: User role string

    Returns:
        Dict mapping permission keys to boolean values
    """
    permissions = ROLE_PERMISSIONS.get(role, [])

    return {
        'canSendEmail': Permission.ESTIMATE_SEND_EMAIL in permissions,
        'canCreateShareLink': Permission.ESTIMATE_CREATE_SHARE_LINK in permissions,
        'canDownloadDisputePack': Permission.ESTIMATE_DOWNLOAD_DISPUTE_PACK in permissions,
        # Customer authorization
        'canRequestSignature': Permission.ESTIMATE_REQUEST_SIGNATURE in permissions,
        # Legacy (for backward compatibility)
        'canApproveEstimate': Permission.ESTIMATE_APPROVE in permissions,
        'canDeclineEstimate': Permission.ESTIMATE_DECLINE in permissions,
        # Insurer workflow
        'canSubmitToInsurer': Permission.INSURER_SUBMIT in permissions,
        'canInsurerApprove': Permission.INSURER_APPROVE in permissions,
        'canInsurerDecline': Permission.INSURER_DECLINE in permissions,
        # Supplements
        'canCreateSupplement': Permission.SUPPLEMENT_CREATE in permissions,
        'canSendSupplement': Permission.SUPPLEMENT_SEND in permissions,
        # Editing
        'canEditPricing': Permission.ESTIMATE_EDIT_PRICING in permissions,
        'canEditDamage': Permission.ESTIMATE_EDIT_DAMAGE in permissions,
        # System
        'canManageUsers': Permission.SYSTEM_USERS in permissions,
        'canManageSettings': Permission.SYSTEM_SETTINGS in permissions,
    }
