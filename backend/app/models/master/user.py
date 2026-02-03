"""User model - team members within a tenant."""

from datetime import datetime
from backend.app.extensions import db
import bcrypt


class User(db.Model):
    """A user belonging to a tenant (PDR company team member)."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    role = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Role constants
    ROLE_OWNER = 'owner'       # Full access, billing, can delete company
    ROLE_MANAGER = 'manager'   # Manage team, view all leads
    ROLE_DESK = 'desk'         # Office staff, view all leads, make calls
    ROLE_TECH = 'tech'         # Field tech, view assigned jobs only
    ROLE_SALESMAN = 'salesman' # Sales, view assigned leads only

    ROLES = [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK, ROLE_TECH, ROLE_SALESMAN]
    UNIQUE_ROLES = [ROLE_OWNER, ROLE_MANAGER, ROLE_DESK]  # Only one per company

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        """Verify password."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def is_owner(self):
        """Check if user is owner."""
        return self.role == self.ROLE_OWNER

    def is_manager(self):
        """Check if user is manager."""
        return self.role == self.ROLE_MANAGER

    def can_manage_team(self):
        """Check if user can manage team members."""
        return self.role in [self.ROLE_OWNER, self.ROLE_MANAGER]

    def can_view_all_leads(self):
        """Check if user can view all leads."""
        return self.role in [self.ROLE_OWNER, self.ROLE_MANAGER, self.ROLE_DESK]

    def can_manage_billing(self):
        """Check if user can manage billing."""
        return self.role == self.ROLE_OWNER

    def can_assign_leads(self):
        """Check if user can assign leads to team members."""
        return self.role in [self.ROLE_OWNER, self.ROLE_MANAGER, self.ROLE_DESK]

    def to_dict(self):
        """Convert to dictionary (excludes password)."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'tenant_id': self.tenant_id,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
