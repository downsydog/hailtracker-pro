"""Business models - discovered businesses and storm associations."""

from datetime import datetime
from backend.app.extensions import db


class Business(db.Model):
    """Business discovered from APIs (Yelp, HERE, Google, etc.)."""
    __tablename__ = 'businesses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip = db.Column(db.String(20))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255))
    email_source = db.Column(db.String(50))  # website_scrape, pattern, name_derived
    email_confidence = db.Column(db.String(20))  # high, medium, low, guess
    website = db.Column(db.String(255))
    lat = db.Column(db.Numeric(10, 7))
    lon = db.Column(db.Numeric(10, 7))
    source = db.Column(db.String(50))  # yelp, here, google, tomtom, osm
    source_id = db.Column(db.String(100))
    estimated_vehicles = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('source', 'source_id', name='unique_source_business'),
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'subcategory': self.subcategory,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip': self.zip,
            'phone': self.phone,
            'email': self.email,
            'email_source': self.email_source,
            'email_confidence': self.email_confidence,
            'website': self.website,
            'lat': float(self.lat) if self.lat else None,
            'lon': float(self.lon) if self.lon else None,
            'source': self.source,
            'estimated_vehicles': self.estimated_vehicles,
        }

    def __repr__(self):
        return f'<Business {self.name}>'


class StormBusiness(db.Model):
    """Association between storms and businesses."""
    __tablename__ = 'storm_businesses'

    id = db.Column(db.Integer, primary_key=True)
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id'), nullable=False)
    swath_id = db.Column(db.Integer, db.ForeignKey('swaths.id'))
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    in_swath = db.Column(db.Boolean, default=True)
    distance_from_center = db.Column(db.Numeric(10, 2))  # in miles
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('storm_id', 'business_id', name='unique_storm_business'),
    )

    # Relationships
    business = db.relationship('Business', backref='storm_links')
    swath = db.relationship('Swath', backref='storm_businesses')

    def to_dict(self):
        """Convert to dictionary including business details."""
        result = {
            'id': self.id,
            'storm_id': self.storm_id,
            'swath_id': self.swath_id,
            'in_swath': self.in_swath,
            'distance_from_center': float(self.distance_from_center) if self.distance_from_center else None,
        }
        if self.business:
            result['business'] = self.business.to_dict()
        return result
