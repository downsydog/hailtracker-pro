"""Tenant and Subscription models - multi-tenant support."""

from datetime import datetime
from app.extensions import db


class Tenant(db.Model):
    """A customer company (PDR business) using HailTracker Pro."""
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # URL-safe identifier
    owner_email = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(50), default='free')  # free, pro, enterprise
    status = db.Column(db.String(20), default='active')  # active, suspended, cancelled
    stripe_customer_id = db.Column(db.String(100))
    max_users = db.Column(db.Integer, default=8)
    database_name = db.Column(db.String(100))  # tenant-specific database
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='tenant', lazy='dynamic', cascade='all, delete-orphan')
    subscription = db.relationship('Subscription', backref='tenant', uselist=False, cascade='all, delete-orphan')

    # Plan limits
    PLAN_LIMITS = {
        'free': {'users': 2, 'storms_per_month': 3},
        'pro': {'users': 8, 'storms_per_month': 50},
        'enterprise': {'users': 100, 'storms_per_month': -1},  # -1 = unlimited
    }

    def get_plan_limits(self):
        """Get limits for current plan."""
        return self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS['free'])

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'slug': self.slug,
            'owner_email': self.owner_email,
            'plan': self.plan,
            'status': self.status,
            'max_users': self.max_users,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Tenant {self.company_name}>'


class Subscription(db.Model):
    """Stripe subscription for a tenant."""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    plan = db.Column(db.String(50))
    status = db.Column(db.String(20))  # active, past_due, cancelled
    stripe_subscription_id = db.Column(db.String(100))
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_active(self):
        """Check if subscription is active."""
        return self.status == 'active'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'plan': self.plan,
            'status': self.status,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
        }
