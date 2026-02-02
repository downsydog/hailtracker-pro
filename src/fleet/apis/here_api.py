"""
HERE Places API Client
======================
Free tier: 250,000 calls/month
Docs: https://developer.here.com/documentation/geocoding-search-api/dev_guide/index.html

Setup:
1. Sign up at https://developer.here.com
2. Create a project and get API key
3. Set environment variable: HERE_API_KEY=your_key_here

COMPREHENSIVE PDR FLEET PROSPECTING SEARCH TERMS
Updated with full list of service businesses that have work vehicles.
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

    # ==========================================================================
    # COMPREHENSIVE SEARCH TERMS FOR PDR FLEET PROSPECTING
    # ==========================================================================

    # DISTRIBUTION/DELIVERY
    DISTRIBUTION_TERMS = [
        'beverage distributor',
        'beer distributor',
        'wine distributor',
        'food distributor',
        'restaurant supply',
        'linen service',
        'uniform service',
        'vending machine',
        'propane delivery',
        'office supply',
        'janitorial supply',
        'building materials',
    ]

    # TRADES/SERVICE COMPANIES
    TRADES_TERMS = [
        'hvac',
        'heating and cooling',
        'air conditioning contractor',
        'plumber',
        'plumbing contractor',
        'electrician',
        'electrical contractor',
        'pest control',
        'exterminator',
        'landscaping',
        'lawn care',
        'lawn service',
        'tree service',
        'tree trimming',
        'roofing contractor',
        'roofer',
        'siding contractor',
        'gutter installation',
        'fence contractor',
        'pool service',
        'pool cleaning',
        'irrigation',
        'sprinkler system',
        'garage door repair',
        'locksmith',
        'painting contractor',
        'flooring contractor',
        'carpet cleaning',
        'concrete contractor',
        'paving contractor',
        'asphalt',
        'pressure washing',
        'window cleaning',
        'water damage restoration',
        'fire restoration',
        'mold remediation',
        'septic service',
        'portable toilet',
    ]

    # CONSTRUCTION/INDUSTRIAL
    CONSTRUCTION_TERMS = [
        'general contractor',
        'excavation',
        'grading',
        'surveying company',
        'well drilling',
        'crane service',
        'scaffolding',
        'equipment rental',
        'lumber yard',
        'building supply',
    ]

    # AUTOMOTIVE
    AUTOMOTIVE_TERMS = [
        'towing',
        'tow truck',
        'mobile mechanic',
        'auto glass',
        'windshield repair',
        'roadside assistance',
        'oil change',
        'mobile car wash',
        'mobile detailing',
    ]

    # MEDICAL/HEALTH
    MEDICAL_TERMS = [
        'home health',
        'home healthcare',
        'medical transport',
        'hospice',
        'mobile veterinary',
        'medical equipment',
        'pharmacy delivery',
    ]

    # TELECOM/TECH
    TELECOM_TERMS = [
        'cable installer',
        'satellite installer',
        'IT service',
        'copier service',
        'telecommunications',
        'security system',
        'alarm company',
    ]

    # WASTE/ENVIRONMENTAL
    WASTE_TERMS = [
        'waste management',
        'garbage service',
        'recycling company',
        'dumpster rental',
        'junk removal',
        'hazmat',
    ]

    # RENTAL COMPANIES
    RENTAL_TERMS = [
        'equipment rental',
        'tool rental',
        'party rental',
        'event rental',
        'trailer rental',
    ]

    # PROPERTY/FACILITIES
    PROPERTY_TERMS = [
        'property management',
        'janitorial service',
        'commercial cleaning',
        'floor care',
    ]

    # TRANSPORT/LOGISTICS
    TRANSPORT_TERMS = [
        'courier service',
        'delivery service',
        'freight',
        'trucking',
        'charter bus',
        'shuttle service',
        'limousine service',
    ]

    # OTHER SERVICE COMPANIES
    OTHER_TERMS = [
        'sign company',
        'sign shop',
        'print shop',
        'funeral home',
        'florist',
        'furniture delivery',
        'appliance store',
    ]

    # COMBINED FULL SEARCH TERM LIST
    SEARCH_TERMS = (
        DISTRIBUTION_TERMS +
        TRADES_TERMS +
        CONSTRUCTION_TERMS +
        AUTOMOTIVE_TERMS +
        MEDICAL_TERMS +
        TELECOM_TERMS +
        WASTE_TERMS +
        RENTAL_TERMS +
        PROPERTY_TERMS +
        TRANSPORT_TERMS +
        OTHER_TERMS
    )

    # Priority terms for quick searches (highest vehicle density)
    PRIORITY_TERMS = [
        'hvac', 'plumber', 'electrician', 'pest control',
        'landscaping', 'roofing', 'tree service', 'lawn care',
        'towing', 'auto body', 'general contractor',
        'pool service', 'fence contractor', 'concrete contractor',
        'septic service', 'garage door', 'locksmith',
        'property management', 'janitorial', 'sign company',
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
            'limit': limit,
            'apiKey': self.api_key,
        }

        if query:
            params['q'] = query

        # Use 'in' for circle search (mutually exclusive with 'at')
        if radius_meters:
            params['in'] = f'circle:{lat},{lon};r={radius_meters}'
        else:
            params['at'] = f'{lat},{lon}'

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
        """Search all comprehensive business types."""
        all_results = []
        seen_ids = set()

        for term in self.SEARCH_TERMS:
            results = self.search_radius(lat, lon, radius_meters, query=term, limit=50)

            for biz in results:
                if biz.get('here_id') not in seen_ids:
                    seen_ids.add(biz.get('here_id'))
                    all_results.append(biz)

        logger.info(f"[HERE] Found {len(all_results)} unique businesses across all terms")
        return all_results

    def search_priority_categories(self, lat: float, lon: float, radius_meters: int = 5000) -> List[Dict]:
        """Search priority/high-value business types only."""
        all_results = []
        seen_ids = set()

        for term in self.PRIORITY_TERMS:
            results = self.search_radius(lat, lon, radius_meters, query=term, limit=50)

            for biz in results:
                if biz.get('here_id') not in seen_ids:
                    seen_ids.add(biz.get('here_id'))
                    all_results.append(biz)

        logger.info(f"[HERE] Found {len(all_results)} unique businesses from priority terms")
        return all_results

    def search_by_category_group(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        group: str = 'trades'
    ) -> List[Dict]:
        """
        Search a specific category group.

        Groups: distribution, trades, construction, automotive, medical,
                telecom, waste, rental, property, transport, other
        """
        group_map = {
            'distribution': self.DISTRIBUTION_TERMS,
            'trades': self.TRADES_TERMS,
            'construction': self.CONSTRUCTION_TERMS,
            'automotive': self.AUTOMOTIVE_TERMS,
            'medical': self.MEDICAL_TERMS,
            'telecom': self.TELECOM_TERMS,
            'waste': self.WASTE_TERMS,
            'rental': self.RENTAL_TERMS,
            'property': self.PROPERTY_TERMS,
            'transport': self.TRANSPORT_TERMS,
            'other': self.OTHER_TERMS,
        }

        terms = group_map.get(group.lower(), self.TRADES_TERMS)
        all_results = []
        seen_ids = set()

        for term in terms:
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
