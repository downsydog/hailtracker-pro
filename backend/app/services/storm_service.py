"""
Storm Service
=============
Operations for querying storms and businesses from the master database.
"""

from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models.master.storm import Storm
from app.models.master.swath import Swath
from app.models.master.business import Business, StormBusiness


class StormService:
    """Service for storm and business queries."""

    @staticmethod
    def get_recent_storms(days=30, state=None, min_hail_size=None):
        """
        Get recent storms that are ready (processed).

        Args:
            days: Number of days to look back
            state: Filter by state
            min_hail_size: Minimum hail size in inches

        Returns:
            List of storm dictionaries
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = Storm.query.filter(
            Storm.status == 'ready',
            Storm.event_date >= cutoff
        )

        if state:
            query = query.filter(Storm.state == state)

        storms = query.order_by(Storm.event_date.desc()).all()

        result = []
        for storm in storms:
            # Get swath info
            swaths = Swath.query.filter_by(storm_id=storm.id).all()
            max_hail = max([float(s.max_hail_size or 0) for s in swaths]) if swaths else 0

            if min_hail_size and max_hail < min_hail_size:
                continue

            result.append({
                'id': storm.id,
                'noaa_id': storm.noaa_id,
                'event_date': storm.event_date.isoformat(),
                'state': storm.state,
                'status': storm.status,
                'business_count': storm.business_count,
                'swath_count': len(swaths),
                'max_hail_size': max_hail,
                'expires_at': storm.expires_at.isoformat() if storm.expires_at else None,
                'cities': list(set([s.city for s in swaths if s.city]))[:5]
            })

        return result

    @staticmethod
    def get_storm_detail(storm_id):
        """
        Get detailed storm info with all swaths.

        Args:
            storm_id: Storm ID

        Returns:
            Storm dictionary with swaths or None
        """
        storm = Storm.query.get(storm_id)
        if not storm:
            return None

        swaths = Swath.query.filter_by(storm_id=storm_id).all()

        return {
            'id': storm.id,
            'noaa_id': storm.noaa_id,
            'event_date': storm.event_date.isoformat(),
            'state': storm.state,
            'status': storm.status,
            'business_count': storm.business_count,
            'processed_at': storm.processed_at.isoformat() if storm.processed_at else None,
            'expires_at': storm.expires_at.isoformat() if storm.expires_at else None,
            'swaths': [{
                'id': s.id,
                'city': s.city,
                'state': s.state,
                'county': s.county,
                'max_hail_size': float(s.max_hail_size) if s.max_hail_size else None,
                'center_lat': float(s.center_lat) if s.center_lat else None,
                'center_lon': float(s.center_lon) if s.center_lon else None,
                'polygon': s.polygon,
                'area_sq_miles': float(s.area_sq_miles) if s.area_sq_miles else None
            } for s in swaths]
        }

    @staticmethod
    def get_storm_businesses(storm_id, category=None, min_vehicles=None, limit=500):
        """
        Get businesses affected by a storm.

        Args:
            storm_id: Storm ID
            category: Filter by business category
            min_vehicles: Minimum estimated vehicles
            limit: Max results to return

        Returns:
            List of business dictionaries
        """
        query = db.session.query(Business).join(
            StormBusiness,
            Business.id == StormBusiness.business_id
        ).filter(
            StormBusiness.storm_id == storm_id,
            StormBusiness.in_swath == True
        )

        if category:
            query = query.filter(Business.category == category)

        if min_vehicles:
            query = query.filter(Business.estimated_vehicles >= min_vehicles)

        businesses = query.limit(limit).all()

        return [b.to_dict() for b in businesses]

    @staticmethod
    def get_business_categories(storm_id):
        """
        Get list of categories with counts for a storm.

        Args:
            storm_id: Storm ID

        Returns:
            List of category dictionaries with counts
        """
        results = db.session.query(
            Business.category,
            func.count(Business.id).label('count')
        ).join(
            StormBusiness,
            Business.id == StormBusiness.business_id
        ).filter(
            StormBusiness.storm_id == storm_id,
            StormBusiness.in_swath == True
        ).group_by(
            Business.category
        ).order_by(
            func.count(Business.id).desc()
        ).all()

        return [{'category': r[0], 'count': r[1]} for r in results]

    @staticmethod
    def get_storms_by_date(date):
        """
        Get storms for a specific date.

        Args:
            date: Date object

        Returns:
            List of storm detail dictionaries
        """
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())

        storms = Storm.query.filter(
            Storm.event_date >= start,
            Storm.event_date <= end,
            Storm.status == 'ready'
        ).all()

        return [StormService.get_storm_detail(s.id) for s in storms]

    @staticmethod
    def search_storms(query_text, limit=20):
        """
        Search storms by city, state, or NOAA ID.

        Args:
            query_text: Search query
            limit: Max results

        Returns:
            List of storm dictionaries
        """
        # Search in swaths for city matches
        swath_matches = Swath.query.filter(
            Swath.city.ilike(f'%{query_text}%')
        ).limit(50).all()

        storm_ids = set([s.storm_id for s in swath_matches])

        # Also search by state
        state_matches = Storm.query.filter(
            Storm.state.ilike(f'%{query_text}%'),
            Storm.status == 'ready'
        ).limit(20).all()

        storm_ids.update([s.id for s in state_matches])

        # Get storm details
        storms = Storm.query.filter(
            Storm.id.in_(storm_ids),
            Storm.status == 'ready'
        ).order_by(Storm.event_date.desc()).limit(limit).all()

        result = []
        for storm in storms:
            swaths = Swath.query.filter_by(storm_id=storm.id).all()
            result.append({
                'id': storm.id,
                'noaa_id': storm.noaa_id,
                'event_date': storm.event_date.isoformat(),
                'state': storm.state,
                'business_count': storm.business_count,
                'cities': list(set([s.city for s in swaths if s.city]))[:5]
            })

        return result
