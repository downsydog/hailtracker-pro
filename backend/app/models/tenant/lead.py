"""Lead model - business opportunities for PDR work."""

from datetime import datetime
from app.extensions import db


class Lead(db.Model):
    """A potential PDR job from a discovered business."""
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, nullable=False)  # References master.businesses
    storm_id = db.Column(db.Integer, nullable=False)     # References master.storms
    status = db.Column(db.String(50), default='new')
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    assigned_to = db.Column(db.Integer)  # References users.id
    notes = db.Column(db.Text)
    estimated_vehicles = db.Column(db.Integer)
    estimated_value = db.Column(db.Numeric(12, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contacts = db.relationship('Contact', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    calls = db.relationship('Call', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    jobs = db.relationship('Job', backref='lead', lazy='dynamic', cascade='all, delete-orphan')
    estimates = db.relationship('Estimate', backref='lead', lazy='dynamic', cascade='all, delete-orphan')

    # Status constants
    STATUS_NEW = 'new'
    STATUS_CONTACTED = 'contacted'
    STATUS_QUOTED = 'quoted'
    STATUS_NEGOTIATING = 'negotiating'
    STATUS_WON = 'won'
    STATUS_LOST = 'lost'
    STATUS_NO_ANSWER = 'no_answer'
    STATUS_NOT_INTERESTED = 'not_interested'

    STATUSES = [
        STATUS_NEW, STATUS_CONTACTED, STATUS_QUOTED, STATUS_NEGOTIATING,
        STATUS_WON, STATUS_LOST, STATUS_NO_ANSWER, STATUS_NOT_INTERESTED
    ]

    ACTIVE_STATUSES = [STATUS_NEW, STATUS_CONTACTED, STATUS_QUOTED, STATUS_NEGOTIATING]
    CLOSED_STATUSES = [STATUS_WON, STATUS_LOST, STATUS_NO_ANSWER, STATUS_NOT_INTERESTED]

    def is_active(self):
        """Check if lead is still active."""
        return self.status in self.ACTIVE_STATUSES

    def is_won(self):
        """Check if lead was won."""
        return self.status == self.STATUS_WON

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'business_id': self.business_id,
            'storm_id': self.storm_id,
            'status': self.status,
            'priority': self.priority,
            'assigned_to': self.assigned_to,
            'notes': self.notes,
            'estimated_vehicles': self.estimated_vehicles,
            'estimated_value': float(self.estimated_value) if self.estimated_value else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Lead {self.id} - {self.status}>'
