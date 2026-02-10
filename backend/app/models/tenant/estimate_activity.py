"""Estimate Activity model for audit logging."""

from datetime import datetime
from app.extensions import db


class EstimateActivity(db.Model):
    """
    Activity log for PDR estimates.

    Tracks events like:
    - email_sent: Estimate package sent to adjuster
    - email_failed: Email send failed
    - status_changed: Estimate status changed
    - panel_added: Panel added to estimate
    - etc.
    """
    __tablename__ = 'estimate_activities'

    id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, nullable=False, index=True)

    # Activity type: email_sent, email_failed, status_changed, etc.
    activity_type = db.Column(db.String(50), nullable=False, index=True)

    # User who performed the action (optional for system events)
    user_id = db.Column(db.Integer, nullable=True)

    # JSON data for activity-specific info
    # e.g., {"to": "adj@ins.com", "subject": "...", "message_id": "..."}
    activity_data = db.Column(db.JSON, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<EstimateActivity {self.id} {self.activity_type} for estimate {self.estimate_id}>'

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'estimate_id': self.estimate_id,
            'activity_type': self.activity_type,
            'user_id': self.user_id,
            'activity_data': self.activity_data or {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def log(cls, estimate_id: int, activity_type: str, user_id: int = None, activity_data: dict = None):
        """
        Convenience method to create and save an activity log entry.

        Args:
            estimate_id: The estimate this activity belongs to
            activity_type: Type of activity (email_sent, email_failed, etc.)
            user_id: Optional user who performed the action
            activity_data: Optional dict with activity-specific data

        Returns:
            The created EstimateActivity instance
        """
        activity = cls(
            estimate_id=estimate_id,
            activity_type=activity_type,
            user_id=user_id,
            activity_data=activity_data
        )
        db.session.add(activity)
        db.session.commit()
        return activity
