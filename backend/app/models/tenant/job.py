"""Job model - scheduled/completed PDR work."""

from datetime import datetime
from app.extensions import db


class Job(db.Model):
    """A scheduled or completed PDR job."""
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    job_number = db.Column(db.String(50))
    status = db.Column(db.String(50), default='scheduled')
    vehicle_count = db.Column(db.Integer)
    total_amount = db.Column(db.Numeric(12, 2))
    scheduled_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    assigned_tech = db.Column(db.Integer)  # User ID of assigned tech
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Status constants
    STATUS_SCHEDULED = 'scheduled'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_RESCHEDULED = 'rescheduled'

    STATUSES = [STATUS_SCHEDULED, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_CANCELLED, STATUS_RESCHEDULED]

    def is_completed(self):
        """Check if job is completed."""
        return self.status == self.STATUS_COMPLETED

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'job_number': self.job_number,
            'status': self.status,
            'vehicle_count': self.vehicle_count,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'assigned_tech': self.assigned_tech,
            'notes': self.notes,
        }

    def __repr__(self):
        return f'<Job {self.job_number} - {self.status}>'
