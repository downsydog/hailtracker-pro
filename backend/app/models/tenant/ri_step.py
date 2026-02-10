"""RIStep model - individual steps within an R&I operation.

Phase 6A: R&I Justification Engine
Each step has a base time and justification metadata.
"""

from datetime import datetime
from app.extensions import db


# Denial resistance levels
RI_DENIAL_RESISTANCE = ['high', 'medium', 'low']


class RIStep(db.Model):
    """A step within an R&I operation with time and justification metadata."""
    __tablename__ = 'ri_steps'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Link to operation
    operation_id = db.Column(db.Integer, db.ForeignKey('ri_operations.id'), nullable=False, index=True)

    # Step identification
    step_code = db.Column(db.String(100), nullable=False)  # e.g., REMOVE_SUN_VISORS
    label = db.Column(db.String(255), nullable=False)  # e.g., "Remove sun visors"
    description = db.Column(db.Text, nullable=True)

    # Time and requirements
    base_time_hours = db.Column(db.Float, default=0.0)  # Base time in hours
    required = db.Column(db.Boolean, default=True)  # Is this step mandatory?

    # Justification metadata
    denial_resistance = db.Column(db.String(20), default='medium')  # high/medium/low
    risk_tags = db.Column(db.JSON, default=list)  # Array of strings: ['airbag', 'electrical', etc.]

    # Stage 6H-C: Expert mode extensions
    oem_dependency = db.Column(db.Boolean, default=False)  # Requires OEM-specific procedure
    safety_critical = db.Column(db.Boolean, default=False)  # Involves safety systems (airbag, seatbelt, etc.)

    # Ordering
    order_index = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint per operation
    __table_args__ = (
        db.UniqueConstraint('operation_id', 'step_code', name='uq_ri_step_operation_code'),
    )

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'operation_id': self.operation_id,
            'step_code': self.step_code,
            'label': self.label,
            'description': self.description,
            'base_time_hours': self.base_time_hours,
            'required': self.required,
            'denial_resistance': self.denial_resistance,
            'risk_tags': self.risk_tags or [],
            # Stage 6H-C fields
            'oem_dependency': self.oem_dependency or False,
            'safety_critical': self.safety_critical or False,
            'order_index': self.order_index,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
