"""Storm model - represents a hail storm event."""

from datetime import datetime, timedelta
from backend.app.extensions import db


class Storm(db.Model):
    """Hail storm event from NOAA data."""
    __tablename__ = 'storms'

    id = db.Column(db.Integer, primary_key=True)
    noaa_id = db.Column(db.String(50), unique=True, nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    state = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, processing, ready, expired
    processed_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    business_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    swaths = db.relationship('Swath', backref='storm', lazy='dynamic', cascade='all, delete-orphan')
    storm_businesses = db.relationship('StormBusiness', backref='storm', lazy='dynamic', cascade='all, delete-orphan')

    def mark_processed(self):
        """Mark storm as processed and set expiration."""
        self.status = 'ready'
        self.processed_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(days=29)

    def is_expired(self):
        """Check if storm data has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'noaa_id': self.noaa_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'state': self.state,
            'status': self.status,
            'business_count': self.business_count,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }

    def __repr__(self):
        return f'<Storm {self.noaa_id} - {self.event_date}>'
