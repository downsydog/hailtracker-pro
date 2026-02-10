"""Job model - scheduled/completed PDR work.

Jobs are the execution layer for PDR estimates.
A Job can be created from an approved PDREstimate to schedule and track repairs.
"""

from datetime import datetime
from app.extensions import db


class Job(db.Model):
    """A scheduled or completed PDR job linked to an estimate."""
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Link to estimate (primary linkage for hail jobs)
    estimate_id = db.Column(db.Integer, db.ForeignKey('pdr_estimates.id'), nullable=True, index=True)

    # Legacy link to lead (for fleet jobs without estimates)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)

    # Job identification
    job_number = db.Column(db.String(50), unique=True)

    # Customer info (denormalized for display)
    customer_id = db.Column(db.Integer, nullable=True)
    customer_name = db.Column(db.String(255))

    # Vehicle info (denormalized for display)
    vehicle_year = db.Column(db.Integer)
    vehicle_make = db.Column(db.String(100))
    vehicle_model = db.Column(db.String(100))

    # Pricing
    status = db.Column(db.String(50), default='scheduled')
    vehicle_count = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Numeric(12, 2))

    # Scheduling
    scheduled_date = db.Column(db.Date)
    scheduled_time = db.Column(db.Time, nullable=True)
    estimated_hours = db.Column(db.Numeric(5, 2), nullable=True)
    completed_date = db.Column(db.Date)
    assigned_tech = db.Column(db.Integer)  # User ID of assigned tech

    # Notes
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)

    # Relationship to estimate
    estimate = db.relationship('PDREstimate', backref=db.backref('job', uselist=False))

    # Status constants
    STATUS_SCHEDULED = 'scheduled'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_RESCHEDULED = 'rescheduled'

    STATUSES = [STATUS_SCHEDULED, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_CANCELLED, STATUS_RESCHEDULED]

    def generate_job_number(self):
        """Generate job number based on ID."""
        if not self.job_number and self.id:
            self.job_number = f'JOB-{self.id:05d}'

    def is_completed(self):
        """Check if job is completed."""
        return self.status == self.STATUS_COMPLETED

    def is_in_progress(self):
        """Check if job is in progress."""
        return self.status == self.STATUS_IN_PROGRESS

    def can_start(self):
        """Check if job can be started."""
        return self.status == self.STATUS_SCHEDULED

    def start_job(self):
        """Mark job as in progress."""
        if self.can_start():
            self.status = self.STATUS_IN_PROGRESS

    def complete_job(self):
        """Mark job as completed."""
        if self.status == self.STATUS_IN_PROGRESS:
            self.status = self.STATUS_COMPLETED
            self.completed_date = datetime.utcnow().date()

    def cancel_job(self):
        """Cancel the job."""
        if self.status not in [self.STATUS_COMPLETED]:
            self.status = self.STATUS_CANCELLED

    @classmethod
    def create_from_estimate(cls, estimate, user_id=None, scheduled_date=None, assigned_tech=None, notes=None):
        """
        Create a new job from a PDR estimate.

        Args:
            estimate: PDREstimate instance
            user_id: User creating the job
            scheduled_date: Optional scheduled date
            assigned_tech: Optional tech user ID
            notes: Optional notes

        Returns:
            New Job instance (not yet committed)
        """
        job = cls(
            tenant_id=estimate.tenant_id,
            estimate_id=estimate.id,
            lead_id=estimate.lead_id,
            customer_id=estimate.customer_id,
            customer_name=estimate.customer_name,
            vehicle_year=estimate.vehicle_year,
            vehicle_make=estimate.vehicle_make,
            vehicle_model=estimate.vehicle_model,
            vehicle_count=1,
            total_amount=estimate.insurer_approved_total or estimate.total_price,
            scheduled_date=scheduled_date,
            assigned_tech=assigned_tech,
            notes=notes,
            status=cls.STATUS_SCHEDULED,
            created_by=user_id
        )
        return job

    def to_dict(self, include_estimate=False):
        """Convert to dictionary."""
        result = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'estimate_id': self.estimate_id,
            'lead_id': self.lead_id,
            'job_number': self.job_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'vehicle_year': self.vehicle_year,
            'vehicle_make': self.vehicle_make,
            'vehicle_model': self.vehicle_model,
            'vehicle_display': f"{self.vehicle_year or ''} {self.vehicle_make or ''} {self.vehicle_model or ''}".strip() or None,
            'status': self.status,
            'vehicle_count': self.vehicle_count,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'estimated_hours': float(self.estimated_hours) if self.estimated_hours else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'assigned_tech': self.assigned_tech,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }

        if include_estimate and self.estimate:
            result['estimate'] = {
                'id': self.estimate.id,
                'estimate_number': self.estimate.estimate_number,
                'total_price': float(self.estimate.total_price) if self.estimate.total_price else 0,
                'insurer_approved_total': float(self.estimate.insurer_approved_total) if self.estimate.insurer_approved_total else None,
                'insurer_status': self.estimate.insurer_status,
                'customer_status': self.estimate.customer_status,
                'is_locked': self.estimate.is_locked(),
            }

        return result

    def __repr__(self):
        return f'<Job {self.job_number} - {self.status} (est:{self.estimate_id})>'
