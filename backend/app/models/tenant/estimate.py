"""Estimate model - quotes for PDR work."""

from datetime import datetime
from app.extensions import db


class Estimate(db.Model):
    """A quote/estimate for PDR work."""
    __tablename__ = 'estimates'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    estimate_number = db.Column(db.String(50))
    status = db.Column(db.String(50), default='draft')
    vehicle_count = db.Column(db.Integer)
    price_per_vehicle = db.Column(db.Numeric(10, 2))
    total_amount = db.Column(db.Numeric(12, 2))
    valid_until = db.Column(db.Date)
    sent_at = db.Column(db.DateTime)
    accepted_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Status constants
    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_VIEWED = 'viewed'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_EXPIRED = 'expired'

    STATUSES = [STATUS_DRAFT, STATUS_SENT, STATUS_VIEWED, STATUS_ACCEPTED, STATUS_REJECTED, STATUS_EXPIRED]

    def is_accepted(self):
        """Check if estimate was accepted."""
        return self.status == self.STATUS_ACCEPTED

    def mark_sent(self):
        """Mark estimate as sent."""
        self.status = self.STATUS_SENT
        self.sent_at = datetime.utcnow()

    def mark_accepted(self):
        """Mark estimate as accepted."""
        self.status = self.STATUS_ACCEPTED
        self.accepted_at = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'estimate_number': self.estimate_number,
            'status': self.status,
            'vehicle_count': self.vehicle_count,
            'price_per_vehicle': float(self.price_per_vehicle) if self.price_per_vehicle else None,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
        }

    def __repr__(self):
        return f'<Estimate {self.estimate_number} - {self.status}>'
