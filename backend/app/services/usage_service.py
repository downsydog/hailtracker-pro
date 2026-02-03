"""
Usage Service
=============
API usage tracking and limits.
"""

from datetime import date, timedelta
from sqlalchemy import func, extract
from backend.app.extensions import db
from backend.app.models.master.api_usage import ApiUsage


class UsageService:
    """Service for API usage tracking."""

    # API monthly limits
    LIMITS = {
        'yelp': 150000,      # 5,000/day
        'here': 250000,
        'tomtom': 75000,     # 2,500/day
        'google': 10000,     # Based on $200 credit
        'foursquare': 100000,
        'osm': None          # Unlimited
    }

    @staticmethod
    def log_api_call(api_name, calls=1, storm_id=None):
        """
        Log API usage.

        Args:
            api_name: Name of the API
            calls: Number of calls to log
            storm_id: Optional storm ID for tracking

        Returns:
            ApiUsage record
        """
        return ApiUsage.log_usage(api_name, calls, storm_id)

    @staticmethod
    def get_today_usage():
        """
        Get API usage for today.

        Returns:
            Dictionary of API name to call count
        """
        today = date.today()

        results = ApiUsage.query.filter_by(date=today).all()

        usage = {}
        for r in results:
            usage[r.api_name] = r.calls_count

        return usage

    @staticmethod
    def get_month_usage(year=None, month=None):
        """
        Get API usage for a month.

        Args:
            year: Year (defaults to current)
            month: Month (defaults to current)

        Returns:
            Dictionary of API name to usage details
        """
        if not year:
            year = date.today().year
        if not month:
            month = date.today().month

        results = db.session.query(
            ApiUsage.api_name,
            func.sum(ApiUsage.calls_count).label('total')
        ).filter(
            extract('year', ApiUsage.date) == year,
            extract('month', ApiUsage.date) == month
        ).group_by(ApiUsage.api_name).all()

        usage = {}
        for api_name, total in results:
            limit = UsageService.LIMITS.get(api_name)
            usage[api_name] = {
                'used': total,
                'limit': limit,
                'remaining': limit - total if limit else None,
                'percent': round((total / limit) * 100, 1) if limit else 0
            }

        return usage

    @staticmethod
    def check_can_use_api(api_name):
        """
        Check if we can make more calls to an API.

        Args:
            api_name: Name of the API

        Returns:
            Boolean indicating if API can be used
        """
        limit = UsageService.LIMITS.get(api_name)
        if not limit:
            return True  # Unlimited

        month_usage = ApiUsage.get_monthly_usage(
            api_name,
            date.today().year,
            date.today().month
        )

        return month_usage < limit

    @staticmethod
    def get_usage_history(days=30):
        """
        Get daily usage for the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary of date strings to API usage
        """
        cutoff = date.today() - timedelta(days=days)

        results = db.session.query(
            ApiUsage.date,
            ApiUsage.api_name,
            ApiUsage.calls_count
        ).filter(
            ApiUsage.date >= cutoff
        ).order_by(ApiUsage.date).all()

        # Group by date
        history = {}
        for d, api, count in results:
            date_str = d.isoformat()
            if date_str not in history:
                history[date_str] = {}
            history[date_str][api] = count

        return history
