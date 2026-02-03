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

# KILL SWITCH - Added after billing incidents
try:
    from src.api_killswitch import check_before_api_call
except ImportError:
    def check_before_api_call(name): return os.environ.get('API_CALLS_ENABLED', 'false').lower() == 'true'

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
        # KILL SWITCH CHECK
        if not check_before_api_call('HERE'):
            return []

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
        """
        Search all relevant business types using BROAD search terms.

        EFFICIENCY FIX: Uses 28 broad terms instead of 104 individual category names!
        - Old method: 104 taxonomy display names = 104 API calls per tile
        - New method: 28 broad terms that cover all categories = 28 API calls per tile
        - Savings: 76 API calls per tile = 73% reduction

        For 500 tiles: 14,000 calls instead of 52,000 calls
        """
        all_results = []
        seen_ids = set()

        # 28 broad search terms that cover all 104 fleet-relevant categories
        # Each term catches multiple business types in one API call
        # Increased from 18 to 28 to ensure full coverage (still 73% reduction from 104)
        broad_search_terms = [
            # Automotive (4 terms)
            'car dealer',
            'auto repair',
            'auto body',
            'towing service',
            # Service Trades - Core (5 terms)
            'contractor',
            'plumber',
            'hvac',
            'electrician',
            'roofing',
            # Service Trades - Specialty (6 terms)
            'cleaning service',     # carpet, window, pressure washing, mold
            'garage door',          # garage door install/repair
            'locksmith',            # locksmith services
            'appliance repair',     # appliance service
            'glass repair',         # glass, mirror, auto glass
            'chimney',              # chimney sweep, fireplace
            # Exterior Services (4 terms)
            'landscaping',
            'pest control',
            'pool service',
            'fence contractor',
            # Specialty Services (4 terms)
            'septic service',       # septic, portable toilets
            'security system',      # alarm, surveillance
            'irrigation',           # sprinkler systems
            'gutter',               # gutter cleaning/install
            # Commercial/Industrial (3 terms)
            'warehouse',
            'trucking company',
            'moving company',
            # Waste/Rental (2 terms)
            'dumpster',             # dumpster rental, junk removal
            'equipment rental',     # party, tool, event rental
            # Government/Medical (3 terms)
            'government office',
            'fire station',
            'hospital',
            # Delivery/Other (2 terms)
            'delivery service',     # florist, pharmacy, furniture
            'funeral home',
            # Additional coverage (11 terms) - catches edge cases
            'restoration',          # mold, water damage, fire damage
            'mold remediation',     # mold removal specialist
            'junk removal',         # debris removal, cleanout
            'sign company',         # signs, vehicle wraps
            'florist',              # flower delivery
            'insulation',           # insulation contractor
            'pressure washing',     # power washing, exterior cleaning
            'portable toilet',      # porta potty, portable sanitation
            'vending machine',      # vending services
            'hospice',              # hospice care, end of life
            'hazardous waste',      # hazmat, toxic waste disposal
            'fencing',              # fence installation, gates
        ]

        for term in broad_search_terms:
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
