"""
Authentication Service
======================
Handles user registration, login, and team management.
"""

from datetime import datetime
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token
from backend.app.extensions import db
from backend.app.models.master.user import User
from backend.app.models.master.tenant import Tenant


class AuthService:
    """Authentication and user management service."""

    @staticmethod
    def register_tenant(company_name, owner_name, owner_email, password):
        """
        Register a new tenant (company) with owner account.
        This is the main signup flow.

        Args:
            company_name: Company name
            owner_name: Owner's full name
            owner_email: Owner's email
            password: Owner's password

        Returns:
            tuple: (tenant, owner) or (None, error_message)
        """
        # Check if email already exists
        if User.query.filter_by(email=owner_email.lower()).first():
            return None, "Email already registered"

        # Create slug from company name
        slug = company_name.lower().replace(' ', '-').replace("'", "")
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')

        # Make sure slug is unique
        base_slug = slug
        counter = 1
        while Tenant.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Create tenant
        tenant = Tenant(
            company_name=company_name,
            slug=slug,
            owner_email=owner_email.lower(),
            plan='free',
            status='active',
            max_users=8,
            database_name=f"tenant_{slug.replace('-', '_')}"
        )
        db.session.add(tenant)
        db.session.flush()  # Get tenant.id

        # Create owner user
        owner = User(
            tenant_id=tenant.id,
            email=owner_email.lower(),
            name=owner_name,
            role=User.ROLE_OWNER,
            is_active=True
        )
        owner.set_password(password)
        db.session.add(owner)

        db.session.commit()

        return tenant, owner

    @staticmethod
    def login(email, password):
        """
        Authenticate user and return tokens.

        Args:
            email: User email
            password: User password

        Returns:
            tuple: (result_dict, None) or (None, error_message)
        """
        user = User.query.filter_by(email=email.lower()).first()

        if not user:
            return None, "Invalid email or password"

        if not user.is_active:
            return None, "Account is deactivated"

        if not user.check_password(password):
            return None, "Invalid email or password"

        # Check tenant status
        tenant = Tenant.query.get(user.tenant_id)
        if not tenant or tenant.status != 'active':
            return None, "Account is suspended"

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Create tokens with user info
        identity = {
            'user_id': user.id,
            'tenant_id': user.tenant_id,
            'role': user.role,
            'email': user.email
        }

        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(),
            'tenant': {
                'id': tenant.id,
                'company_name': tenant.company_name,
                'slug': tenant.slug,
                'plan': tenant.plan
            }
        }, None

    @staticmethod
    def add_team_member(tenant_id, adder_role, name, email, password, role, phone=None):
        """
        Add a team member to a tenant.
        Only owner and manager can add members.

        Args:
            tenant_id: Tenant ID
            adder_role: Role of user adding the member
            name: New member's name
            email: New member's email
            password: New member's password
            role: New member's role
            phone: Optional phone number

        Returns:
            tuple: (user, None) or (None, error_message)
        """
        # Check permissions
        if adder_role not in [User.ROLE_OWNER, User.ROLE_MANAGER]:
            return None, "You don't have permission to add team members"

        # Check if email exists
        if User.query.filter_by(email=email.lower()).first():
            return None, "Email already registered"

        # Validate role
        if role not in User.ROLES:
            return None, f"Invalid role. Must be one of: {', '.join(User.ROLES)}"

        # Only owner can add another owner (shouldn't happen, but safety check)
        if role == User.ROLE_OWNER:
            return None, "Cannot add another owner"

        # Manager can't add another manager
        if role == User.ROLE_MANAGER and adder_role == User.ROLE_MANAGER:
            return None, "Only owner can add a manager"

        # Check unique role constraints (only 1 manager, 1 desk per tenant)
        if role in User.UNIQUE_ROLES:
            existing = User.query.filter_by(tenant_id=tenant_id, role=role, is_active=True).first()
            if existing:
                return None, f"A {role} already exists for this company"

        # Check max users (8 per tenant)
        tenant = Tenant.query.get(tenant_id)
        current_count = User.query.filter_by(tenant_id=tenant_id, is_active=True).count()
        if current_count >= tenant.max_users:
            return None, f"Maximum {tenant.max_users} users reached. Upgrade to add more."

        # Create user
        user = User(
            tenant_id=tenant_id,
            email=email.lower(),
            name=name,
            phone=phone,
            role=role,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        return user, None

    @staticmethod
    def update_team_member(tenant_id, user_id, updater_role, **updates):
        """
        Update a team member's info.

        Args:
            tenant_id: Tenant ID
            user_id: User ID to update
            updater_role: Role of user making the update
            **updates: Fields to update (name, phone, role)

        Returns:
            tuple: (user, None) or (None, error_message)
        """
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return None, "User not found"

        # Only owner and manager can update others
        if updater_role not in [User.ROLE_OWNER, User.ROLE_MANAGER]:
            return None, "You don't have permission to update team members"

        # Can't change owner's role
        if user.role == User.ROLE_OWNER and 'role' in updates:
            return None, "Cannot change owner's role"

        # Apply updates
        if 'name' in updates and updates['name']:
            user.name = updates['name']

        if 'phone' in updates:
            user.phone = updates['phone']

        if 'role' in updates and updates['role']:
            new_role = updates['role']

            # Validate role
            if new_role not in User.ROLES:
                return None, f"Invalid role. Must be one of: {', '.join(User.ROLES)}"

            # Check unique role constraints
            if new_role in User.UNIQUE_ROLES and new_role != user.role:
                existing = User.query.filter_by(
                    tenant_id=tenant_id, role=new_role, is_active=True
                ).first()
                if existing:
                    return None, f"A {new_role} already exists for this company"

            user.role = new_role

        db.session.commit()
        return user, None

    @staticmethod
    def change_password(user_id, old_password, new_password):
        """
        Change user's password.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            tuple: (True, message) or (False, error_message)
        """
        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        if not user.check_password(old_password):
            return False, "Current password is incorrect"

        if len(new_password) < 8:
            return False, "New password must be at least 8 characters"

        user.set_password(new_password)
        db.session.commit()

        return True, "Password changed successfully"

    @staticmethod
    def reset_password_admin(tenant_id, user_id, new_password, resetter_role):
        """
        Reset a user's password (admin action).

        Args:
            tenant_id: Tenant ID
            user_id: User ID to reset
            new_password: New password
            resetter_role: Role of user doing the reset

        Returns:
            tuple: (True, message) or (False, error_message)
        """
        if resetter_role not in [User.ROLE_OWNER, User.ROLE_MANAGER]:
            return False, "You don't have permission to reset passwords"

        user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return False, "User not found"

        if user.role == User.ROLE_OWNER and resetter_role != User.ROLE_OWNER:
            return False, "Only owner can reset owner's password"

        if len(new_password) < 8:
            return False, "Password must be at least 8 characters"

        user.set_password(new_password)
        db.session.commit()

        return True, "Password reset successfully"

    @staticmethod
    def reset_password_request(email):
        """
        Request password reset.
        In production, this would send an email with a reset link.

        Args:
            email: User email

        Returns:
            tuple: (True, message)
        """
        user = User.query.filter_by(email=email.lower()).first()
        if not user:
            # Don't reveal if email exists
            return True, "If that email exists, a reset link has been sent"

        # TODO: Generate reset token and send email
        # For now, just return success
        return True, "If that email exists, a reset link has been sent"

    @staticmethod
    def get_team_members(tenant_id):
        """
        Get all team members for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            list: List of user dicts
        """
        users = User.query.filter_by(tenant_id=tenant_id).order_by(
            # Sort by role importance, then name
            db.case(
                (User.role == User.ROLE_OWNER, 1),
                (User.role == User.ROLE_MANAGER, 2),
                (User.role == User.ROLE_DESK, 3),
                (User.role == User.ROLE_SALESMAN, 4),
                (User.role == User.ROLE_TECH, 5),
                else_=6
            ),
            User.name
        ).all()

        return [u.to_dict() for u in users]

    @staticmethod
    def get_active_team_members(tenant_id):
        """Get only active team members."""
        users = User.query.filter_by(tenant_id=tenant_id, is_active=True).order_by(
            User.role, User.name
        ).all()

        return [u.to_dict() for u in users]

    @staticmethod
    def deactivate_user(tenant_id, user_id, deactivator_role):
        """
        Deactivate a team member.

        Args:
            tenant_id: Tenant ID
            user_id: User ID to deactivate
            deactivator_role: Role of user deactivating

        Returns:
            tuple: (True, message) or (False, error_message)
        """
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return False, "User not found"

        # Can't deactivate owner
        if user.role == User.ROLE_OWNER:
            return False, "Cannot deactivate the owner"

        # Only owner and manager can deactivate
        if deactivator_role not in [User.ROLE_OWNER, User.ROLE_MANAGER]:
            return False, "You don't have permission to deactivate users"

        # Manager can't deactivate manager
        if user.role == User.ROLE_MANAGER and deactivator_role == User.ROLE_MANAGER:
            return False, "Only owner can deactivate manager"

        user.is_active = False
        db.session.commit()

        return True, "User deactivated"

    @staticmethod
    def reactivate_user(tenant_id, user_id, reactivator_role):
        """
        Reactivate a deactivated team member.

        Args:
            tenant_id: Tenant ID
            user_id: User ID to reactivate
            reactivator_role: Role of user reactivating

        Returns:
            tuple: (True, message) or (False, error_message)
        """
        user = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return False, "User not found"

        if user.is_active:
            return False, "User is already active"

        # Only owner and manager can reactivate
        if reactivator_role not in [User.ROLE_OWNER, User.ROLE_MANAGER]:
            return False, "You don't have permission to reactivate users"

        # Check max users before reactivating
        tenant = Tenant.query.get(tenant_id)
        current_count = User.query.filter_by(tenant_id=tenant_id, is_active=True).count()
        if current_count >= tenant.max_users:
            return False, f"Maximum {tenant.max_users} users reached. Upgrade to add more."

        user.is_active = True
        db.session.commit()

        return True, "User reactivated"
