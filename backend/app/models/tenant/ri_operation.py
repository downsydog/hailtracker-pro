"""RIOperation model - canonical R&I operations catalog.

Phase 6A: R&I Justification Engine
Defines the standard R&I operations with associated metadata.
"""

from datetime import datetime
from app.extensions import db


# Valid risk levels
RI_RISK_LEVELS = ['low', 'medium', 'high']

# Valid categories
RI_CATEGORIES = ['interior', 'exterior', 'structural']

# Valid difficulty levels (Stage 6H-C)
RI_DIFFICULTY_LEVELS = ['economy', 'standard', 'luxury', 'exotic']


class RIOperation(db.Model):
    """A canonical R&I (Remove & Install) operation definition."""
    __tablename__ = 'ri_operations'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Operation identification
    code = db.Column(db.String(100), nullable=False)  # e.g., RI_HEADLINER_REMOVAL
    display_name = db.Column(db.String(255), nullable=False)  # e.g., "Headliner Removal"
    category = db.Column(db.String(50), default='interior')  # interior/exterior/structural
    description = db.Column(db.Text, nullable=True)
    risk_level = db.Column(db.String(20), default='medium')  # low/medium/high

    # Stage 6H-C: Expert mode extensions
    difficulty_level = db.Column(db.String(20), default='standard')  # economy/standard/luxury/exotic
    common_denials = db.Column(db.JSON, default=list)  # Array of denial codes this operation commonly faces
    default_required_steps = db.Column(db.JSON, default=list)  # Step codes that should be required by default
    is_seeded = db.Column(db.Boolean, default=False)  # True for system-seeded operations (cannot be deleted)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = db.relationship('RIStep', backref='operation', lazy='dynamic',
                           cascade='all, delete-orphan')

    # Unique constraint per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'code', name='uq_ri_operation_tenant_code'),
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'code': self.code,
            'display_name': self.display_name,
            'category': self.category,
            'description': self.description,
            'risk_level': self.risk_level,
            # Stage 6H-C fields
            'difficulty_level': self.difficulty_level or 'standard',
            'common_denials': self.common_denials or [],
            'default_required_steps': self.default_required_steps or [],
            'is_seeded': self.is_seeded or False,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_with_steps(self) -> dict:
        """Serialize with steps included."""
        data = self.to_dict()
        data['steps'] = [step.to_dict() for step in self.steps.order_by('order_index').all()]
        return data
