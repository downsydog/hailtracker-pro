"""PDR Estimate Panel model - individual panel damage entries."""

from datetime import datetime
from app.extensions import db


class PDREstimatePanel(db.Model):
    """A single panel damage entry within a PDR estimate."""
    __tablename__ = 'pdr_estimate_panels'

    id = db.Column(db.Integer, primary_key=True)
    estimate_id = db.Column(db.Integer, db.ForeignKey('pdr_estimates.id'), nullable=False, index=True)

    # Panel identification
    panel_name = db.Column(db.String(50), nullable=False)  # e.g., 'hood', 'roof', 'door_fl'
    panel_label = db.Column(db.String(100))  # Human-readable: 'Hood', 'Roof', 'Front Left Door'

    # Damage assessment
    dent_count = db.Column(db.Integer, default=0)
    count_range = db.Column(db.String(20))  # '1-5', '6-15', '16-30', '31-50', '51-75', '76-100', '100+'
    avg_size = db.Column(db.String(20))  # 'dime', 'nickel', 'quarter', 'half_dollar', 'golf_ball', 'larger'
    severity = db.Column(db.String(20))  # 'light', 'moderate', 'heavy', 'severe'

    # PDR Matrix fields (zone-based pricing)
    depth = db.Column(db.String(20))  # 'shallow', 'medium', 'deep'
    zone = db.Column(db.String(20))  # 'body', 'edge', 'crease', 'double'
    oversized = db.Column(db.Boolean, default=False)
    aluminum = db.Column(db.Boolean, default=False)

    # Pricing
    base_price = db.Column(db.Numeric(10, 2), default=0)
    multiplier = db.Column(db.Numeric(5, 2), default=1)
    adjustment = db.Column(db.Numeric(10, 2), default=0)
    line_total = db.Column(db.Numeric(10, 2), default=0)

    # R&I (Remove & Install) operations
    ri_required = db.Column(db.Boolean, default=False)
    ri_operations = db.Column(db.JSON, nullable=True)  # List of R&I operation IDs/codes
    ri_labor_hours = db.Column(db.Numeric(5, 2), default=0)
    ri_cost = db.Column(db.Numeric(10, 2), default=0)

    # Notes
    notes = db.Column(db.Text)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    estimate = db.relationship('PDREstimate', backref=db.backref('panels', lazy='dynamic', cascade='all, delete-orphan'))

    def calculate_line_total(self):
        """Calculate line total based on base price, multiplier, and adjustment."""
        base = float(self.base_price or 0)
        mult = float(self.multiplier or 1)
        adj = float(self.adjustment or 0)
        ri = float(self.ri_cost or 0)
        self.line_total = (base * mult) + adj + ri

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'estimate_id': self.estimate_id,
            'panel_name': self.panel_name,
            'panel_label': self.panel_label,
            'dent_count': self.dent_count,
            'count_range': self.count_range,
            'avg_size': self.avg_size,
            'severity': self.severity,
            'depth': self.depth,
            'zone': self.zone,
            'oversized': self.oversized,
            'aluminum': self.aluminum,
            'base_price': float(self.base_price) if self.base_price else 0,
            'multiplier': float(self.multiplier) if self.multiplier else 1,
            'adjustment': float(self.adjustment) if self.adjustment else 0,
            'line_total': float(self.line_total) if self.line_total else 0,
            'ri_required': self.ri_required,
            'ri_operations': self.ri_operations,
            'ri_labor_hours': float(self.ri_labor_hours) if self.ri_labor_hours else 0,
            'ri_cost': float(self.ri_cost) if self.ri_cost else 0,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<PDREstimatePanel {self.panel_name} on Estimate {self.estimate_id}>'
