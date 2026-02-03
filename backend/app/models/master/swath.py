"""Swath model - represents a hail swath polygon."""

from datetime import datetime
from backend.app.extensions import db


class Swath(db.Model):
    """Hail swath polygon from NOAA data."""
    __tablename__ = 'swaths'

    id = db.Column(db.Integer, primary_key=True)
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id'), nullable=False)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    county = db.Column(db.String(100))
    max_hail_size = db.Column(db.Numeric(4, 2))  # in inches
    polygon = db.Column(db.JSON)  # GeoJSON polygon
    center_lat = db.Column(db.Numeric(10, 7))
    center_lon = db.Column(db.Numeric(10, 7))
    area_sq_miles = db.Column(db.Numeric(10, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'storm_id': self.storm_id,
            'city': self.city,
            'state': self.state,
            'county': self.county,
            'max_hail_size': float(self.max_hail_size) if self.max_hail_size else None,
            'polygon': self.polygon,
            'center_lat': float(self.center_lat) if self.center_lat else None,
            'center_lon': float(self.center_lon) if self.center_lon else None,
            'area_sq_miles': float(self.area_sq_miles) if self.area_sq_miles else None,
        }

    def __repr__(self):
        return f'<Swath {self.city}, {self.state} - {self.max_hail_size}">'
