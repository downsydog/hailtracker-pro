"""PartRequest model - track parts needed for estimates/jobs.

Stage 5Q: Parts Requests from Estimates
Allows office to track parts needed per job/estimate as structured line items.
"""

from datetime import datetime
from app.extensions import db


# Parts status values (same as blocker_helpers.PARTS_STATUS_VALUES)
PARTS_STATUS_VALUES = [
    'needed',           # Initial - part identified as needed
    'approved_to_order', # Office approved, pending order
    'ordered',          # PO issued, waiting on delivery
    'shipped',          # Vendor shipped, in transit
    'received',         # Parts arrived at shop
    'installed',        # Parts installed, request complete
    'exception',        # Issue with parts (wrong part, damaged, etc.)
]


class PartRequest(db.Model):
    """A parts request linked to an estimate or job."""
    __tablename__ = 'part_requests'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Link to estimate OR job (at least one should be set)
    estimate_id = db.Column(db.Integer, db.ForeignKey('pdr_estimates.id'), nullable=True, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=True, index=True)

    # Part details
    description = db.Column(db.String(500), nullable=False)
    part_number = db.Column(db.String(100), nullable=True)
    qty = db.Column(db.Integer, default=1, nullable=False)

    # Status workflow (same values as blocker_helpers)
    parts_status = db.Column(db.String(50), default='needed', nullable=False)

    # Approval tracking (Stage 5T)
    approved_to_order = db.Column(db.Boolean, default=False)
    approved_amount = db.Column(db.Numeric(12, 2), nullable=True)
    approved_by = db.Column(db.Integer, nullable=True)  # User ID who approved
    approved_at = db.Column(db.DateTime, nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)  # Stage 5T: approval notes

    # Ordering details
    vendor = db.Column(db.String(255), nullable=True)
    po_number = db.Column(db.String(100), nullable=True)
    eta = db.Column(db.DateTime, nullable=True)

    # Additional info
    notes = db.Column(db.Text, nullable=True)
    priority = db.Column(db.Integer, default=50)  # 0-100, higher = more urgent

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)

    # Stage 5U: Status timeline tracking
    status_updated_at = db.Column(db.DateTime, nullable=True)
    status_updated_by = db.Column(db.Integer, nullable=True)
    ordered_at = db.Column(db.DateTime, nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)
    received_at = db.Column(db.DateTime, nullable=True)
    installed_at = db.Column(db.DateTime, nullable=True)
    previous_status = db.Column(db.String(50), nullable=True)  # For exception recovery

    # Relationships
    estimate = db.relationship('PDREstimate', backref=db.backref('part_requests', lazy='dynamic'))
    job = db.relationship('Job', backref=db.backref('part_requests', lazy='dynamic'))

    # Status constants (for convenience)
    STATUS_NEEDED = 'needed'
    STATUS_APPROVED = 'approved_to_order'
    STATUS_ORDERED = 'ordered'
    STATUS_SHIPPED = 'shipped'
    STATUS_RECEIVED = 'received'
    STATUS_INSTALLED = 'installed'
    STATUS_EXCEPTION = 'exception'

    # Stage 5U: Valid status transitions
    # Format: from_status -> [allowed_to_statuses]
    VALID_TRANSITIONS = {
        'needed': ['approved_to_order', 'exception'],
        'approved_to_order': ['ordered', 'exception', 'needed'],  # Can go back to needed
        'ordered': ['shipped', 'exception'],
        'shipped': ['received', 'exception'],
        'received': ['installed', 'exception'],
        'installed': ['exception'],  # Can mark exception even after installed (e.g., wrong part discovered)
        'exception': [],  # Recovery handled separately with previous_status
    }

    def can_transition_to(self, new_status: str) -> bool:
        """Check if transition to new_status is valid."""
        if new_status == 'exception':
            return True  # Can always go to exception
        if self.parts_status == 'exception':
            # From exception, can only go back to previous_status
            return new_status == self.previous_status
        return new_status in self.VALID_TRANSITIONS.get(self.parts_status, [])

    def get_allowed_transitions(self) -> list:
        """Get list of valid statuses this request can transition to."""
        if self.parts_status == 'exception':
            # Can only recover to previous status
            return [self.previous_status] if self.previous_status else []
        allowed = self.VALID_TRANSITIONS.get(self.parts_status, []).copy()
        if 'exception' not in allowed:
            allowed.append('exception')
        return allowed

    def is_open(self) -> bool:
        """Check if request is still open (not installed or cancelled)."""
        return self.parts_status not in ['installed']

    def is_overdue(self) -> bool:
        """Check if ETA has passed."""
        if not self.eta:
            return False
        return self.eta < datetime.utcnow()

    def compute_priority(self) -> int:
        """
        Compute priority score for sorting.
        Higher = more urgent.
        """
        score = 50  # Base score

        # ETA overdue = highest priority
        if self.is_overdue():
            score = 95

        # Status-based priority
        elif self.parts_status == 'exception':
            score = 90
        elif self.parts_status == 'needed' and not self.approved_to_order:
            score = 75  # Needs approval
        elif self.parts_status == 'approved_to_order':
            score = 70  # Approved but not ordered
        elif self.parts_status == 'ordered':
            score = 60
        elif self.parts_status == 'shipped':
            score = 55
        elif self.parts_status == 'received':
            score = 45
        elif self.parts_status == 'installed':
            score = 20

        return score

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'estimate_id': self.estimate_id,
            'job_id': self.job_id,
            'description': self.description,
            'part_number': self.part_number,
            'qty': self.qty,
            'parts_status': self.parts_status,
            'approved_to_order': self.approved_to_order,
            'approved_amount': float(self.approved_amount) if self.approved_amount else None,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approval_notes': self.approval_notes,
            'vendor': self.vendor,
            'po_number': self.po_number,
            'eta': self.eta.isoformat() if self.eta else None,
            'notes': self.notes,
            'priority': self.compute_priority(),
            'is_overdue': self.is_overdue(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            # Stage 5U: Timeline fields
            'status_updated_at': self.status_updated_at.isoformat() if self.status_updated_at else None,
            'status_updated_by': self.status_updated_by,
            'ordered_at': self.ordered_at.isoformat() if self.ordered_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
            'previous_status': self.previous_status,
            'allowed_transitions': self.get_allowed_transitions(),
        }
