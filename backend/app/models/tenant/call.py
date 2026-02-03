"""Call model - call log for leads."""

from datetime import datetime
from backend.app.extensions import db


class Call(db.Model):
    """A phone call made to a lead."""
    __tablename__ = 'calls'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'))
    user_id = db.Column(db.Integer, nullable=False)  # Who made the call
    call_type = db.Column(db.String(50))  # outbound, inbound, voicemail
    duration_seconds = db.Column(db.Integer)
    outcome = db.Column(db.String(50))  # answered, voicemail, no_answer, busy, callback
    notes = db.Column(db.Text)
    callback_date = db.Column(db.DateTime)  # If callback requested
    called_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Outcome constants
    OUTCOME_ANSWERED = 'answered'
    OUTCOME_VOICEMAIL = 'voicemail'
    OUTCOME_NO_ANSWER = 'no_answer'
    OUTCOME_BUSY = 'busy'
    OUTCOME_CALLBACK = 'callback'
    OUTCOME_WRONG_NUMBER = 'wrong_number'
    OUTCOME_NOT_INTERESTED = 'not_interested'

    OUTCOMES = [
        OUTCOME_ANSWERED, OUTCOME_VOICEMAIL, OUTCOME_NO_ANSWER,
        OUTCOME_BUSY, OUTCOME_CALLBACK, OUTCOME_WRONG_NUMBER, OUTCOME_NOT_INTERESTED
    ]

    contact = db.relationship('Contact', backref='calls')

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'contact_id': self.contact_id,
            'user_id': self.user_id,
            'call_type': self.call_type,
            'duration_seconds': self.duration_seconds,
            'outcome': self.outcome,
            'notes': self.notes,
            'callback_date': self.callback_date.isoformat() if self.callback_date else None,
            'called_at': self.called_at.isoformat() if self.called_at else None,
        }

    def __repr__(self):
        return f'<Call {self.id} - {self.outcome}>'
