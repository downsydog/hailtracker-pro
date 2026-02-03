"""
Yelp Fusion API Client
======================
Free tier: 5,000 calls/day (150,000/month)
Docs: https://docs.developer.yelp.com/reference/v3_business_search

Setup:
1. Sign up at https://www.yelp.com/developers
2. Create an app and get API key
3. Set environment variable: YELP_API_KEY=your_key_here
"""

import requests
from typing import List, Dict, Optional
import os
import logging
from math import radians, cos, sqrt

# KILL SWITCH - Added after billing incidents
try:
    from src.api_killswitch import check_before_api_call
except ImportError:
    def check_before_api_call(name): return os.environ.get('API_CALLS_ENABLED', 'false').lower() == 'true'

logger = logging.getLogger('YelpAPI')


def _get_all_yelp_categories() -> List[str]:
    """Get all Yelp categories from the taxonomy (104 categories -> 108 Yelp terms)."""
    try:
        from src.business.category_taxonomy import CATEGORIES, get_yelp_categories
        all_cats = set()
        for cat_key in CATEGORIES:
            yelp_cats = get_yelp_categories(cat_key)
            all_cats.update(yelp_cats)
        return list(all_cats)
    except ImportError:
        # Fallback if taxonomy not available
        return [
            'landscaping', 'lawn_services', 'tree_services', 'hvac',
            'plumbing', 'electricians', 'pest_control', 'roofing',
            'contractors', 'auto_repair', 'body_shops', 'towing',
            'car_dealers', 'movers', 'security_systems', 'painters',
        ]


class YelpAPI:
    """
    Yelp Fusion API client.
    Free tier: 5,000 calls/day
    """

    BASE_URL = "https://api.yelp.com/v3"

    # Categories from taxonomy (108 Yelp categories from 104 business types)
    # Full list: https://www.yelp.com/developers/documentation/v3/all_category_list
    CATEGORIES = _get_all_yelp_categories()

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('YELP_API_KEY')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
        } if self.api_key else {}

    def search_radius(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        categories: List[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for businesses within radius of a point.

        Args:
            lat, lon: Center point
            radius_meters: Search radius (max 40000)
            categories: List of Yelp categories to search
            limit: Max results (max 50 per request)
        """
        # KILL SWITCH CHECK
        if not check_before_api_call('Yelp'):
            return []

        if not self.api_key:
            logger.warning("[Yelp] API key not configured")
            return []

        url = f"{self.BASE_URL}/businesses/search"

        params = {
            'latitude': lat,
            'longitude': lon,
            'radius': min(radius_meters, 40000),
            'limit': limit,
            'sort_by': 'distance',
        }

        if categories:
            params['categories'] = ','.join(categories)

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data.get('businesses', []))
            elif response.status_code == 401:
                logger.error("[Yelp] Invalid API key (401)")
                return []
            elif response.status_code == 429:
                logger.error("[Yelp] Rate limit exceeded (429)")
                return []
            else:
                logger.error(f"[Yelp] Error {response.status_code}: {response.text[:200]}")
                return []

        except requests.Timeout:
            logger.error("[Yelp] Request timed out")
            return []
        except Exception as e:
            logger.error(f"[Yelp] Error: {e}")
            return []

    def search_area(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        categories: List[str] = None
    ) -> List[Dict]:
        """
        Search a bounding box area.
        Yelp doesn't support bbox directly, so we query the center.
        """
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # Calculate approximate radius
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon

        # Rough conversion to meters
        lat_meters = lat_diff * 111000
        lon_meters = lon_diff * 111000 * cos(radians(center_lat))
        radius = int(sqrt(lat_meters**2 + lon_meters**2) / 2)
        radius = min(radius, 40000)  # Yelp max

        return self.search_radius(center_lat, center_lon, radius, categories)

    def search_all_categories(self, lat: float, lon: float, radius_meters: int = 5000) -> List[Dict]:
        """Search all relevant categories."""
        all_results = []
        seen_ids = set()

        # Batch categories to reduce API calls
        category_batches = [
            'landscaping,lawn_services,tree_services',
            'hvac,plumbing,electricians',
            'pest_control,roofing,contractors',
            'auto_repair,body_shops,towing,car_dealers',
            'movers,painters,fences_gates,concrete',
            'locksmiths,garage_door_services,security_systems',
        ]

        for batch in category_batches:
            results = self.search_radius(lat, lon, radius_meters, categories=batch.split(','))

            for biz in results:
                if biz.get('yelp_id') not in seen_ids:
                    seen_ids.add(biz.get('yelp_id'))
                    all_results.append(biz)

        return all_results

    def _parse_results(self, businesses: list) -> List[Dict]:
        """Parse Yelp results into standard format."""
        results = []

        for biz in businesses:
            location = biz.get('location', {})

            results.append({
                'name': biz.get('name', ''),
                'address': ', '.join(filter(None, [
                    location.get('address1'),
                    location.get('city'),
                    location.get('state'),
                    location.get('zip_code'),
                ])),
                'city': location.get('city', ''),
                'state': location.get('state', ''),
                'zip': location.get('zip_code', ''),
                'phone': biz.get('phone', ''),
                'website': biz.get('url', ''),  # Yelp page URL
                'latitude': biz.get('coordinates', {}).get('latitude'),
                'longitude': biz.get('coordinates', {}).get('longitude'),
                'category': biz.get('categories', [{}])[0].get('title', '') if biz.get('categories') else '',
                'rating': biz.get('rating'),
                'review_count': biz.get('review_count'),
                'source': 'yelp',
                'yelp_id': biz.get('id'),
            })

        return results

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def test_connection(self) -> Dict:
        """Test API connection and key validity."""
        if not self.api_key:
            return {
                'success': False,
                'configured': False,
                'message': 'Yelp API key not configured. Set YELP_API_KEY environment variable.'
            }

        try:
            results = self.search_radius(35.4676, -97.5164, 1000, limit=1)
            return {
                'success': True,
                'configured': True,
                'message': f'Yelp API is working'
            }
        except Exception as e:
            return {
                'success': False,
                'configured': True,
                'message': f'Connection error: {str(e)}'
            }
