"""Estimate Supplement model for tracking damage discovery changes."""

from datetime import datetime
from app.extensions import db


# Discovery type constants
DISCOVERY_TYPES = [
    'hidden_damage',
    'additional_panels',
    'severity_increase',
    'access_limitation',
    'part_condition',
    'corrosion',
    'prior_damage',
    'manufacturer_spec',
    'other'
]


class EstimateSupplement(db.Model):
    """
    A supplement captures changes to an estimate after initial approval.

    Tracks:
    - What changed (delta from baseline version)
    - Why it changed (discovery type + narrative)
    - Evidence (linked photos)
    - Status (draft -> sent -> approved)
    """
    __tablename__ = 'estimate_supplements'

    id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, nullable=False, index=True)

    # Reference to baseline version this supplement is diffed against
    baseline_version_id = db.Column(db.Integer, db.ForeignKey('estimate_versions.id'), nullable=False)

    # Supplement number within this estimate (1, 2, 3...)
    supplement_number = db.Column(db.Integer, nullable=False, default=1)

    # Discovery type from templates
    discovery_type = db.Column(db.String(50), nullable=False, default='hidden_damage')

    # Short summary for quick reference
    summary = db.Column(db.String(500), nullable=True)

    # Generated narrative explaining the supplement
    narrative = db.Column(db.Text, nullable=True)

    # Computed diff between baseline and current state
    # Structure: { panels: [...], totals: {...}, ri_ops: [...] }
    delta_json = db.Column(db.JSON, nullable=True)

    # Price impact
    original_total = db.Column(db.Numeric(12, 2), nullable=True)
    revised_total = db.Column(db.Numeric(12, 2), nullable=True)
    delta_amount = db.Column(db.Numeric(12, 2), nullable=True)

    # Status workflow
    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUSES = [STATUS_DRAFT, STATUS_SENT, STATUS_APPROVED, STATUS_REJECTED]

    status = db.Column(db.String(20), default=STATUS_DRAFT)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    # Relationship to baseline version
    baseline_version = db.relationship('EstimateVersion', backref='supplements')

    __table_args__ = (
        db.UniqueConstraint('estimate_id', 'supplement_number', name='uq_estimate_supplement'),
    )

    def __repr__(self):
        return f'<EstimateSupplement {self.id} est={self.estimate_id} #{self.supplement_number}>'

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'estimate_id': self.estimate_id,
            'baseline_version_id': self.baseline_version_id,
            'supplement_number': self.supplement_number,
            'discovery_type': self.discovery_type,
            'summary': self.summary,
            'narrative': self.narrative,
            'delta_json': self.delta_json,
            'original_total': float(self.original_total) if self.original_total else None,
            'revised_total': float(self.revised_total) if self.revised_total else None,
            'delta_amount': float(self.delta_amount) if self.delta_amount else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }

    def mark_sent(self):
        """Mark supplement as sent."""
        self.status = self.STATUS_SENT
        self.sent_at = datetime.utcnow()

    def mark_approved(self):
        """Mark supplement as approved."""
        self.status = self.STATUS_APPROVED
        self.approved_at = datetime.utcnow()


class SupplementPhotoLink(db.Model):
    """Links photos to supplements as evidence."""
    __tablename__ = 'supplement_photo_links'

    id = db.Column(db.Integer, primary_key=True)
    supplement_id = db.Column(db.Integer, db.ForeignKey('estimate_supplements.id'), nullable=False, index=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('estimate_photos.id'), nullable=False)

    # Optional: mark as key evidence
    is_key_evidence = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('supplement_id', 'photo_id', name='uq_supplement_photo'),
    )

    def __repr__(self):
        return f'<SupplementPhotoLink supp={self.supplement_id} photo={self.photo_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'supplement_id': self.supplement_id,
            'photo_id': self.photo_id,
            'is_key_evidence': self.is_key_evidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
