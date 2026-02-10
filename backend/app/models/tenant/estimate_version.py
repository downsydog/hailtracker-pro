"""Estimate Version model for baseline snapshots."""

from datetime import datetime
from app.extensions import db


class EstimateVersion(db.Model):
    """
    Baseline snapshot of an estimate at a point in time.

    Used for supplement diff calculations - captures the state
    of the estimate before additional damage was discovered.
    """
    __tablename__ = 'estimate_versions'

    id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False, default=1)

    # JSON snapshot of entire estimate state
    # Includes: panels, totals, ri_ops, vehicle info, etc.
    snapshot_json = db.Column(db.JSON, nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)  # user_id

    # Optional description
    description = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('estimate_id', 'version_number', name='uq_estimate_version'),
    )

    def __repr__(self):
        return f'<EstimateVersion {self.id} est={self.estimate_id} v{self.version_number}>'

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'estimate_id': self.estimate_id,
            'version_number': self.version_number,
            'snapshot_json': self.snapshot_json,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }

    @classmethod
    def create_snapshot(cls, estimate_id: int, snapshot_data: dict, user_id: int = None, description: str = None):
        """
        Create a new version snapshot for an estimate.

        Args:
            estimate_id: The estimate to snapshot
            snapshot_data: Dict containing full estimate state
            user_id: Optional user creating the snapshot
            description: Optional description (e.g., "Initial estimate", "Pre-supplement #1")

        Returns:
            The created EstimateVersion instance
        """
        # Get next version number
        max_version = db.session.query(db.func.max(cls.version_number)).filter_by(
            estimate_id=estimate_id
        ).scalar() or 0

        version = cls(
            estimate_id=estimate_id,
            version_number=max_version + 1,
            snapshot_json=snapshot_data,
            created_by=user_id,
            description=description
        )
        db.session.add(version)
        db.session.commit()
        return version
