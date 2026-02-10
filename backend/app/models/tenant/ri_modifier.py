"""RIModifier model - time modifiers for R&I operations.

Phase 6A: R&I Justification Engine
Modifiers add time based on vehicle complexity, risk, or material factors.
"""

from datetime import datetime
from app.extensions import db


# Modifier categories
RI_MODIFIER_CATEGORIES = ['risk', 'complexity', 'material']


class RIModifier(db.Model):
    """A modifier that adds time to R&I operations based on complexity factors."""
    __tablename__ = 'ri_modifiers'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Modifier identification
    modifier_code = db.Column(db.String(100), nullable=False)  # e.g., PANORAMIC_GLASS_PRESENT
    label = db.Column(db.String(255), nullable=False)  # e.g., "Panoramic Glass Present"

    # Time adjustment
    adds_time_hours = db.Column(db.Float, default=0.0)  # Additional hours

    # Justification
    reason = db.Column(db.Text, nullable=True)  # Why this adds time
    category = db.Column(db.String(50), default='complexity')  # risk/complexity/material

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'modifier_code', name='uq_ri_modifier_tenant_code'),
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'modifier_code': self.modifier_code,
            'label': self.label,
            'adds_time_hours': self.adds_time_hours,
            'reason': self.reason,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
