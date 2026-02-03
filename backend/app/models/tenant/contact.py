"""Contact model - people at a business."""

from datetime import datetime
from backend.app.extensions import db


class Contact(db.Model):
    """A contact person at a business lead."""
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    name = db.Column(db.String(255))
    title = db.Column(db.String(100))  # Fleet Manager, Owner, etc.
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    is_primary = db.Column(db.Boolean, default=False)
    is_decision_maker = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'name': self.name,
            'title': self.title,
            'phone': self.phone,
            'email': self.email,
            'is_primary': self.is_primary,
            'is_decision_maker': self.is_decision_maker,
            'notes': self.notes,
        }

    def __repr__(self):
        return f'<Contact {self.name}>'
