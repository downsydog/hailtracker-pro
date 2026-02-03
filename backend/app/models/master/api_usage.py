"""API Usage tracking model."""

from datetime import datetime, date
from backend.app.extensions import db


class ApiUsage(db.Model):
    """Track API calls for cost monitoring and rate limiting."""
    __tablename__ = 'api_usage'

    id = db.Column(db.Integer, primary_key=True)
    api_name = db.Column(db.String(50), nullable=False)  # yelp, here, google, tomtom, foursquare
    calls_count = db.Column(db.Integer, default=0)
    date = db.Column(db.Date, default=date.today)
    storm_id = db.Column(db.Integer, db.ForeignKey('storms.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('api_name', 'date', name='unique_api_date'),
    )

    @classmethod
    def log_usage(cls, api_name, calls=1, storm_id=None):
        """Log API usage for today."""
        today = date.today()
        usage = cls.query.filter_by(api_name=api_name, date=today).first()

        if usage:
            usage.calls_count += calls
        else:
            usage = cls(api_name=api_name, calls_count=calls, date=today, storm_id=storm_id)
            db.session.add(usage)

        db.session.commit()
        return usage

    @classmethod
    def get_daily_usage(cls, api_name, target_date=None):
        """Get usage for a specific day."""
        if target_date is None:
            target_date = date.today()

        usage = cls.query.filter_by(api_name=api_name, date=target_date).first()
        return usage.calls_count if usage else 0

    @classmethod
    def get_monthly_usage(cls, api_name, year, month):
        """Get total usage for a month."""
        from sqlalchemy import extract, func

        result = db.session.query(func.sum(cls.calls_count)).filter(
            cls.api_name == api_name,
            extract('year', cls.date) == year,
            extract('month', cls.date) == month
        ).scalar()

        return result or 0

    @classmethod
    def get_all_usage_today(cls):
        """Get usage for all APIs today."""
        today = date.today()
        usage_records = cls.query.filter_by(date=today).all()

        return {u.api_name: u.calls_count for u in usage_records}

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'api_name': self.api_name,
            'calls_count': self.calls_count,
            'date': self.date.isoformat() if self.date else None,
        }
