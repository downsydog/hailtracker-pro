"""
TomTom Search API Client
========================
Free tier: 2,500 calls/day (75,000/month)
Docs: https://developer.tomtom.com/search-api/documentation/search-service/fuzzy-search

Setup:
1. Sign up at https://developer.tomtom.com
2. Create an app and get API key
3. Set environment variable: TOMTOM_API_KEY=your_key_here
"""

import requests
from typing import List, Dict
import os
import logging

logger = logging.getLogger('TomTomAPI')


class TomTomAPI:
    """
    TomTom Search API client.
    Free tier: 2,500 calls/day
    """

    BASE_URL = "https://api.tomtom.com/search/2"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('TOMTOM_API_KEY')

    def search_radius(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        query: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search for businesses within radius.
        """
        if not self.api_key:
            logger.warning("[TomTom] API key not configured")
            return []

        # Use POI search for better business results
        search_query = query or 'business'
        url = f"{self.BASE_URL}/poiSearch/{search_query}.json"

        params = {
            'key': self.api_key,
            'lat': lat,
            'lon': lon,
            'radius': radius_meters,
            'limit': limit,
        }

        try:
            response = requests.get(url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data.get('results', []))
            elif response.status_code == 401:
                logger.error("[TomTom] Invalid API key (401)")
                return []
            elif response.status_code == 429:
                logger.error("[TomTom] Rate limit exceeded (429)")
                return []
            else:
                logger.error(f"[TomTom] Error {response.status_code}: {response.text[:200]}")
                return []

        except requests.Timeout:
            logger.error("[TomTom] Request timed out")
            return []
        except Exception as e:
            logger.error(f"[TomTom] Error: {e}")
            return []

    def search_all_categories(self, lat: float, lon: float, radius_meters: int = 5000) -> List[Dict]:
        """Search all relevant business types using taxonomy."""
        all_results = []
        seen_ids = set()

        search_terms = self._get_taxonomy_search_terms()

        for term in search_terms:
            results = self.search_radius(lat, lon, radius_meters, query=term, limit=50)

            for biz in results:
                if biz.get('tomtom_id') not in seen_ids:
                    seen_ids.add(biz.get('tomtom_id'))
                    all_results.append(biz)

        return all_results

    def _get_taxonomy_search_terms(self) -> List[str]:
        """Get optimized search terms from taxonomy (display names only)."""
        try:
            from src.business.category_taxonomy import CATEGORIES
            terms = set()
            for cat_key, cat_data in CATEGORIES.items():
                # Use display name only (104 terms) - more efficient than all tags
                display = cat_data.get('display', '')
                if display:
                    terms.add(display.lower())
            return list(terms)
        except ImportError:
            return [
                'landscaping', 'hvac', 'plumber', 'electrician',
                'pest control', 'roofing', 'contractor',
                'auto body', 'car dealer', 'towing', 'moving',
            ]

    def _parse_results(self, results: list) -> List[Dict]:
        """Parse TomTom results into standard format."""
        parsed = []

        for item in results:
            address = item.get('address', {})
            position = item.get('position', {})
            poi = item.get('poi', {})

            parsed.append({
                'name': poi.get('name', ''),
                'address': address.get('freeformAddress', ''),
                'city': address.get('municipality', ''),
                'state': address.get('countrySubdivision', ''),
                'zip': address.get('postalCode', ''),
                'phone': poi.get('phone', ''),
                'website': poi.get('url', ''),
                'latitude': position.get('lat'),
                'longitude': position.get('lon'),
                'category': poi.get('categories', [''])[0] if poi.get('categories') else '',
                'source': 'tomtom',
                'tomtom_id': item.get('id'),
            })

        return parsed

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def test_connection(self) -> Dict:
        """Test API connection and key validity."""
        if not self.api_key:
            return {
                'success': False,
                'configured': False,
                'message': 'TomTom API key not configured. Set TOMTOM_API_KEY environment variable.'
            }

        try:
            results = self.search_radius(35.4676, -97.5164, 1000, query='business', limit=1)
            return {
                'success': True,
                'configured': True,
                'message': 'TomTom API is working'
            }
        except Exception as e:
            return {
                'success': False,
                'configured': True,
                'message': f'Connection error: {str(e)}'
            }
