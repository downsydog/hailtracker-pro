"""
HERE Places API Client
======================
Free tier: 250,000 calls/month
Docs: https://developer.here.com/documentation/geocoding-search-api/dev_guide/index.html

Setup:
1. Sign up at https://developer.here.com
2. Create a project and get API key
3. Set environment variable: HERE_API_KEY=your_key_here
"""

import requests
from typing import List, Dict
import os
import logging

logger = logging.getLogger('HereAPI')


class HereAPI:
    """
    HERE Places API client.
    Free tier: 250,000 calls/month
    """

    BASE_URL = "https://discover.search.hereapi.com/v1/discover"

    # HERE category IDs
    # Docs: https://developer.here.com/documentation/geocoding-search-api/dev_guide/topics/place-categories.html
    CATEGORIES = [
        '700-7600-0322',  # Auto Dealer
        '700-7600-0116',  # Auto Repair
        '700-7600-0117',  # Auto Body Shop
        '700-7600-0119',  # Car Wash
        '700-7600-0120',  # Towing
        '700-7850-0000',  # Fueling Station
        '700-7400-0000',  # Government Office
        '700-7400-0139',  # Police
        '700-7400-0140',  # Fire Station
        '800-8600-0000',  # Business Services
        '700-7100-0000',  # Shopping (includes many business types)
    ]

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('HERE_API_KEY')

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

        Args:
            lat, lon: Center point
            radius_meters: Search radius
            query: Text search (e.g., "landscaping")
            limit: Max results (max 100)
        """
        if not self.api_key:
            logger.warning("[HERE] API key not configured")
            return []

        params = {
            'at': f'{lat},{lon}',
            'limit': limit,
            'apiKey': self.api_key,
        }

        if query:
            params['q'] = query

        if radius_meters:
            params['in'] = f'circle:{lat},{lon};r={radius_meters}'

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                return self._parse_results(data.get('items', []))
            elif response.status_code == 401:
                logger.error("[HERE] Invalid API key (401)")
                return []
            elif response.status_code == 429:
                logger.error("[HERE] Rate limit exceeded (429)")
                return []
            else:
                logger.error(f"[HERE] Error {response.status_code}: {response.text[:200]}")
                return []

        except requests.Timeout:
            logger.error("[HERE] Request timed out")
            return []
        except Exception as e:
            logger.error(f"[HERE] Error: {e}")
            return []

    def search_all_categories(self, lat: float, lon: float, radius_meters: int = 5000) -> List[Dict]:
        """Search all relevant business types."""
        all_results = []
        seen_ids = set()

        # Search terms for service businesses
        search_terms = [
            'landscaping', 'lawn care', 'tree service',
            'hvac', 'air conditioning', 'heating',
            'plumber', 'plumbing',
            'electrician', 'electrical contractor',
            'pest control', 'exterminator',
            'roofing', 'roofer',
            'contractor', 'construction',
            'auto body', 'auto repair', 'car dealer',
            'towing', 'tow truck',
            'moving company', 'movers',
            'painting contractor',
            'fence company',
            'concrete contractor',
        ]

        for term in search_terms:
            results = self.search_radius(lat, lon, radius_meters, query=term, limit=50)

            for biz in results:
                if biz.get('here_id') not in seen_ids:
                    seen_ids.add(biz.get('here_id'))
                    all_results.append(biz)

        return all_results

    def _parse_results(self, items: list) -> List[Dict]:
        """Parse HERE results into standard format."""
        results = []

        for item in items:
            address = item.get('address', {})
            position = item.get('position', {})
            contacts = item.get('contacts', [])

            # Extract phone
            phone = ''
            for contact in contacts:
                if contact.get('phone'):
                    phones = contact.get('phone', [])
                    if phones:
                        phone = phones[0].get('value', '')
                        break

            # Extract website
            website = ''
            for contact in contacts:
                if contact.get('www'):
                    websites = contact.get('www', [])
                    if websites:
                        website = websites[0].get('value', '')
                        break

            results.append({
                'name': item.get('title', ''),
                'address': address.get('label', ''),
                'city': address.get('city', ''),
                'state': address.get('state', ''),
                'zip': address.get('postalCode', ''),
                'phone': phone,
                'website': website,
                'latitude': position.get('lat'),
                'longitude': position.get('lng'),
                'category': item.get('categories', [{}])[0].get('name', '') if item.get('categories') else '',
                'source': 'here',
                'here_id': item.get('id'),
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
                'message': 'HERE API key not configured. Set HERE_API_KEY environment variable.'
            }

        try:
            results = self.search_radius(35.4676, -97.5164, 1000, query='business', limit=1)
            return {
                'success': True,
                'configured': True,
                'message': 'HERE API is working'
            }
        except Exception as e:
            return {
                'success': False,
                'configured': True,
                'message': f'Connection error: {str(e)}'
            }
