"""
Estimate Photo Model
====================

Stores photo attachments for PDR estimates.
Photos can be associated with specific panels or be unassigned.
Supports supplement evidence flagging for insurance documentation.
"""

from datetime import datetime
from app.extensions import db


class EstimatePhoto(db.Model):
    """Photo attachment for a PDR estimate."""

    __tablename__ = 'estimate_photos'

    id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, nullable=False, index=True)

    # Photo storage
    file_path = db.Column(db.String(500), nullable=False)  # Local path or URL
    file_name = db.Column(db.String(255))  # Original filename
    file_size = db.Column(db.Integer)  # Size in bytes
    mime_type = db.Column(db.String(100), default='image/jpeg')

    # Panel association (nullable = unassigned)
    panel_name = db.Column(db.String(50), nullable=True, index=True)

    # Photo metadata
    photo_type = db.Column(db.String(50), default='damage')  # damage, before, after, detail
    caption = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Supplement evidence flag
    is_supplement_evidence = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Serialize photo to dictionary."""
        return {
            'id': self.id,
            'estimate_id': self.estimate_id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'panel_name': self.panel_name,
            'photo_type': self.photo_type,
            'caption': self.caption,
            'notes': self.notes,
            'is_supplement_evidence': self.is_supplement_evidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<EstimatePhoto {self.id} estimate={self.estimate_id} panel={self.panel_name}>'
