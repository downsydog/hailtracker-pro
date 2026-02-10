"""PDREstimateRI models - join tables linking R&I operations to estimates.

Phase 6A: R&I Justification Engine
Tracks which R&I operations are attached to each estimate, with selected
modifiers and step overrides.
"""

from datetime import datetime
from app.extensions import db


class PDREstimateRIOperation(db.Model):
    """Links an R&I operation to a PDR estimate with computed time."""
    __tablename__ = 'pdr_estimate_ri_operations'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Links
    estimate_id = db.Column(db.Integer, db.ForeignKey('pdr_estimates.id'), nullable=False, index=True)
    operation_id = db.Column(db.Integer, db.ForeignKey('ri_operations.id'), nullable=False, index=True)

    # Notes for this specific application
    notes = db.Column(db.Text, nullable=True)

    # Computed total (snapshot at compute time)
    computed_time_hours = db.Column(db.Float, default=0.0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    operation = db.relationship('RIOperation', backref='estimate_links')
    step_overrides = db.relationship('PDREstimateRIStepOverride', backref='estimate_ri_operation',
                                     lazy='dynamic', cascade='all, delete-orphan')
    modifier_selections = db.relationship('PDREstimateRIModifierSelection', backref='estimate_ri_operation',
                                          lazy='dynamic', cascade='all, delete-orphan')

    # Unique constraint - one operation per estimate
    __table_args__ = (
        db.UniqueConstraint('estimate_id', 'operation_id', name='uq_estimate_ri_operation'),
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'estimate_id': self.estimate_id,
            'operation_id': self.operation_id,
            'notes': self.notes,
            'computed_time_hours': self.computed_time_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PDREstimateRIStepOverride(db.Model):
    """Override for a specific step within an estimate's R&I operation."""
    __tablename__ = 'pdr_estimate_ri_step_overrides'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Links
    estimate_ri_operation_id = db.Column(db.Integer, db.ForeignKey('pdr_estimate_ri_operations.id'),
                                         nullable=False, index=True)
    step_id = db.Column(db.Integer, db.ForeignKey('ri_steps.id'), nullable=False, index=True)

    # Override values
    included = db.Column(db.Boolean, default=True)  # Allow excluding optional steps
    time_override_hours = db.Column(db.Float, nullable=True)  # Override base time if needed
    notes = db.Column(db.Text, nullable=True)

    # Relationship
    step = db.relationship('RIStep')

    # Unique constraint - one override per step per estimate operation
    __table_args__ = (
        db.UniqueConstraint('estimate_ri_operation_id', 'step_id', name='uq_estimate_ri_step_override'),
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'estimate_ri_operation_id': self.estimate_ri_operation_id,
            'step_id': self.step_id,
            'included': self.included,
            'time_override_hours': self.time_override_hours,
            'notes': self.notes,
        }


class PDREstimateRIModifierSelection(db.Model):
    """Selected modifier for an estimate's R&I operation."""
    __tablename__ = 'pdr_estimate_ri_modifier_selections'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Links
    estimate_ri_operation_id = db.Column(db.Integer, db.ForeignKey('pdr_estimate_ri_operations.id'),
                                         nullable=False, index=True)
    modifier_id = db.Column(db.Integer, db.ForeignKey('ri_modifiers.id'), nullable=False, index=True)

    # Optional notes
    notes = db.Column(db.Text, nullable=True)

    # Relationship
    modifier = db.relationship('RIModifier')

    # Unique constraint - one modifier selection per estimate operation
    __table_args__ = (
        db.UniqueConstraint('estimate_ri_operation_id', 'modifier_id', name='uq_estimate_ri_modifier_selection'),
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'estimate_ri_operation_id': self.estimate_ri_operation_id,
            'modifier_id': self.modifier_id,
            'notes': self.notes,
        }
