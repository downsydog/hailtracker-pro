"""
Foursquare Places API Client (New 2025+ API)
=============================================
Client for Foursquare Places API using Service Keys.

Free tier: Limited calls, then requires credits
API Docs: https://docs.foursquare.com/developer/reference/place-search

Setup:
1. Go to https://foursquare.com/developers
2. Project Settings → Service API Keys → Generate Service API Key
3. Set environment variable: FOURSQUARE_SERVICE_KEY=your_key_here
"""

import requests
import os
import logging
import time
from typing import List, Dict, Optional

# KILL SWITCH - Added after 15,060 credits burned
try:
    from src.api_killswitch import check_before_api_call
except ImportError:
    def check_before_api_call(name): return os.environ.get('API_CALLS_ENABLED', 'false').lower() == 'true'

logger = logging.getLogger('FoursquareAPI')


class FoursquareAPI:
    """
    Foursquare Places API client using Service Keys.

    New endpoint: places-api.foursquare.com
    Auth: Bearer token with Service Key
    """

    # New API endpoint (2025+)
    BASE_URL = "https://places-api.foursquare.com/places/search"
    API_VERSION = "2025-06-17"

    # Rate limiting
    MIN_DELAY_SECONDS = 0.1  # 10 requests/second max
    MAX_RETRIES = 3

    def __init__(self, service_key: str = None):
        """
        Initialize Foursquare client with Service Key.

        Args:
            service_key: Foursquare Service Key (or set FOURSQUARE_SERVICE_KEY env var)
        """
        self.service_key = service_key or os.environ.get('FOURSQUARE_SERVICE_KEY')
        self._last_call_time = 0
        self._rate_limited = False

        self.session = requests.Session()
        if self.service_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.service_key}',
                'X-Places-Api-Version': self.API_VERSION,
                'Accept': 'application/json',
            })

    def is_configured(self) -> bool:
        """Check if Service Key is set."""
        return bool(self.service_key) and not self._rate_limited

    def _rate_limit_delay(self):
        """Enforce rate limiting between calls."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self.MIN_DELAY_SECONDS:
            time.sleep(self.MIN_DELAY_SECONDS - elapsed)
        self._last_call_time = time.time()

    def search_radius(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        query: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for businesses within radius.

        Args:
            lat: Latitude
            lon: Longitude
            radius_meters: Search radius in meters (max 100,000)
            query: Search query (e.g., "plumber", "roofing")
            limit: Max results (max 50)

        Returns:
            List of business dictionaries
        """
        # KILL SWITCH CHECK - Added after 15,060 credits burned
        if not check_before_api_call('Foursquare'):
            return []

        if not self.service_key:
            logger.warning("[Foursquare] Service key not configured")
            return []

        if self._rate_limited:
            logger.debug("[Foursquare] Skipping - rate limited")
            return []

        self._rate_limit_delay()

        params = {
            'll': f"{lat},{lon}",
            'radius': min(radius_meters, 100000),
            'limit': min(limit, 50),
        }

        if query:
            params['query'] = query

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=15)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_results(data.get('results', []))

                elif response.status_code == 401:
                    logger.error("[Foursquare] Invalid Service Key (401)")
                    return []

                elif response.status_code == 429:
                    # Check if it's a credit issue or rate limit
                    msg = response.json().get('message', '')
                    if 'credits' in msg.lower():
                        logger.warning("[Foursquare] No API credits remaining - disabling")
                        self._rate_limited = True
                        return []
                    else:
                        # Temporary rate limit - back off
                        wait_time = 2 ** attempt
                        logger.warning(f"[Foursquare] Rate limited, waiting {wait_time}s")
                        time.sleep(wait_time)
                        continue

                else:
                    logger.error(f"[Foursquare] Error {response.status_code}: {response.text[:100]}")
                    return []

            except requests.Timeout:
                logger.error("[Foursquare] Request timed out")
                return []
            except Exception as e:
                logger.error(f"[Foursquare] Error: {e}")
                return []

        return []

    def search_by_query(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        query: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """Alias for search_radius with query."""
        return self.search_radius(lat, lon, radius_meters, query, limit)

    # Foursquare Category IDs - batched for efficient API usage
    # Full list: https://docs.foursquare.com/data-products/docs/categories
    # Grouped into 8 batches (was 104 individual calls = 8,944 wasted calls per 86 tiles!)
    CATEGORY_BATCHES = [
        # Batch 1: Automotive (car dealers, rental, body shops)
        '17069,17070,17071,17072,17073,17074,17075',  # Car dealers, used cars, motorcycle, RV, boat
        # Batch 2: Auto Service
        '17076,17077,17078,17079,17080,17081,17082',  # Auto repair, body shop, car wash, oil change, tire, towing
        # Batch 3: Home Services - Trades
        '17116,17117,17118,17119,17120,17121',  # Contractor, electrician, HVAC, plumber, locksmith, painter
        # Batch 4: Home Services - Exterior
        '17122,17123,17124,17125,17126,17127',  # Landscaping, lawn, pool, roofing, pest control, tree service
        # Batch 5: Commercial/Industrial
        '17001,17002,17003,17004,17005',  # Warehouse, distribution, industrial, manufacturing
        # Batch 6: Government/Municipal
        '17006,17007,17008,17009,17010',  # City hall, fire station, police, post office, courthouse
        # Batch 7: Medical/Health
        '17011,17012,17013,17014,17015',  # Hospital, clinic, urgent care, nursing home, ambulance
        # Batch 8: Transportation/Fleet
        '17016,17017,17018,17019,17020',  # Trucking, moving, bus, taxi, limo
    ]

    def search_all_categories(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000
    ) -> List[Dict]:
        """
        Search for all fleet-relevant business categories.
        Uses focused list of high-value terms (11 calls per tile).
        """
        all_results = []
        seen_ids = set()

        # Focused search terms for service businesses
        search_terms = [
            'plumber', 'roofing', 'hvac',
            'electrician', 'landscaping', 'pest control',
            'towing', 'auto body', 'car dealer',
            'contractor', 'painter',
        ]

        for term in search_terms:
            if self._rate_limited:
                break

            results = self.search_radius(lat, lon, radius_meters, query=term, limit=50)

            for biz in results:
                biz_id = biz.get('foursquare_id')
                if biz_id and biz_id not in seen_ids:
                    seen_ids.add(biz_id)
                    all_results.append(biz)

        return all_results

    def search_all_fleet_categories(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000
    ) -> List[Dict]:
        """
        Search for all fleet-relevant business categories using BATCHED queries.

        EFFICIENCY FIX: Uses 20 batched API calls instead of 104 individual calls!
        - Old method: 104 categories × 1 call each = 104 API calls per tile
        - New method: 20 broad search terms = 20 API calls per tile
        - Savings: 84 API calls per tile = 81% reduction

        For 500 tiles: 10,000 calls instead of 52,000 calls
        """
        all_results = []
        seen_ids = set()

        # Use 20 broad search terms that cover all fleet-relevant categories
        # Each term catches multiple business types in one API call
        # Increased from 8 to 20 to ensure full coverage (still 84% reduction from 104)
        broad_search_terms = [
            # Automotive (4 terms)
            'car dealer',           # Catches: new cars, used cars, RV, boat, motorcycle dealers
            'auto service',         # Catches: repair, body shop, tire, oil change, towing
            # Trades (5 terms)
            'contractor',           # Catches: general, roofing, siding, concrete, framing, gutter
            'home services',        # Catches: plumber, electrician, hvac, painter
            'cleaning service',     # Catches: carpet, window, pressure washing, mold
            # Exterior (3 terms)
            'landscaping',          # Catches: lawn care, tree service, pest control
            'pool service',         # Catches: pool cleaning, pool repair
            'fence contractor',     # Catches: fencing, gates
            # Specialty (4 terms)
            'septic service',       # Catches: septic, portable toilets
            'garage door',          # Catches: garage door install/repair
            'security system',      # Catches: alarm, surveillance, phone systems
            'chimney sweep',        # Catches: chimney cleaning, fireplace
            # Commercial (4 terms)
            'warehouse',            # Catches: distribution, logistics, storage, industrial
            'dumpster rental',      # Catches: dumpster, junk removal, waste
            'delivery service',     # Catches: florist, pharmacy, furniture, propane
            'rental equipment',     # Catches: party rental, tool rental, event rental
            # Fleet/Govt (4 terms)
            'fleet service',        # Catches: trucking, moving, courier, transport
            'medical transport',    # Catches: ambulance, hospice, medical courier
            'municipal',            # Catches: city, county, fire, police, school
            'funeral home',         # Catches: funeral, mortuary
            # Additional coverage (5 terms)
            'restoration service',  # Catches: mold, water damage, fire damage
            'junk removal',         # Catches: junk hauling, debris removal
            'sign company',         # Catches: sign making, vehicle wraps
            'florist',              # Catches: flower shop, floral delivery
            'insulation',           # Catches: insulation contractor, spray foam
        ]

        for term in broad_search_terms:
            if self._rate_limited:
                break

            results = self.search_radius(lat, lon, radius_meters, query=term, limit=50)

            for biz in results:
                biz_id = biz.get('foursquare_id')
                if biz_id and biz_id not in seen_ids:
                    seen_ids.add(biz_id)
                    all_results.append(biz)

        return all_results

    def _parse_results(self, results: List[Dict]) -> List[Dict]:
        """Parse Foursquare results into standard format."""
        businesses = []

        for place in results:
            location = place.get('location', {})

            # Get coordinates
            lat = place.get('geocodes', {}).get('main', {}).get('latitude')
            lon = place.get('geocodes', {}).get('main', {}).get('longitude')

            # Get category
            categories = place.get('categories', [])
            category_name = categories[0].get('name', '') if categories else ''

            # Map to internal category
            internal_category = self._map_category(category_name)

            businesses.append({
                'name': place.get('name', ''),
                'address': location.get('address', ''),
                'city': location.get('locality', ''),
                'state': location.get('region', ''),
                'zip': location.get('postcode', ''),
                'phone': place.get('tel', ''),
                'website': place.get('website', ''),
                'latitude': lat,
                'longitude': lon,
                'category': internal_category,
                'foursquare_category': category_name,
                'source': 'foursquare',
                'foursquare_id': place.get('fsq_place_id', ''),
            })

        return businesses

    def _map_category(self, category_name: str) -> str:
        """Map Foursquare category to internal category."""
        name_lower = category_name.lower()

        if 'plumb' in name_lower:
            return 'plumbing'
        elif 'roof' in name_lower:
            return 'roofing'
        elif 'hvac' in name_lower or 'heating' in name_lower or 'air condition' in name_lower:
            return 'hvac'
        elif 'electric' in name_lower:
            return 'electrical'
        elif 'landscap' in name_lower or 'lawn' in name_lower:
            return 'landscaping'
        elif 'pest' in name_lower or 'exterminator' in name_lower:
            return 'pest_control'
        elif 'tow' in name_lower:
            return 'towing'
        elif 'body' in name_lower or 'collision' in name_lower:
            return 'body_shop'
        elif 'dealer' in name_lower:
            return 'car_dealership'
        elif 'contractor' in name_lower:
            return 'contractor'
        elif 'paint' in name_lower:
            return 'painting'
        elif 'hotel' in name_lower or 'motel' in name_lower:
            return 'hotel'
        elif 'hospital' in name_lower:
            return 'hospital'
        elif 'parking' in name_lower:
            return 'parking_structure'

        return 'other'

    def test_connection(self) -> Dict:
        """Test API connection and key validity."""
        if not self.service_key:
            return {
                'success': False,
                'configured': False,
                'message': 'Foursquare Service Key not configured. Set FOURSQUARE_SERVICE_KEY environment variable.'
            }

        try:
            response = self.session.get(
                self.BASE_URL,
                params={'ll': '35.4676,-97.5164', 'limit': 1},
                timeout=10
            )

            if response.status_code == 200:
                return {
                    'success': True,
                    'configured': True,
                    'message': 'Foursquare API is working'
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'configured': True,
                    'message': 'Invalid Foursquare Service Key'
                }
            elif response.status_code == 429:
                msg = response.json().get('message', '')
                if 'credits' in msg.lower():
                    return {
                        'success': False,
                        'configured': True,
                        'message': 'Foursquare: No API credits remaining. Add credits at https://foursquare.com/developers/orgs'
                    }
                return {
                    'success': False,
                    'configured': True,
                    'message': 'Foursquare rate limit exceeded'
                }
            else:
                return {
                    'success': False,
                    'configured': True,
                    'message': f'Foursquare returned status {response.status_code}'
                }

        except Exception as e:
            return {
                'success': False,
                'configured': True,
                'message': f'Connection error: {str(e)}'
            }


# Test function
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    api = FoursquareAPI()
    print("Testing Foursquare connection...")
    status = api.test_connection()
    print(f"Status: {status}")
