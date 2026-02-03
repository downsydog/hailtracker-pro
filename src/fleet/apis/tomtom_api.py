"""
TomTom Search API Client
========================
Free tier: 2,500 calls/day (75,000/month), 5 QPS limit
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
import time

# KILL SWITCH - Added after billing incidents
try:
    from src.api_killswitch import check_before_api_call
except ImportError:
    def check_before_api_call(name): return os.environ.get('API_CALLS_ENABLED', 'false').lower() == 'true'

logger = logging.getLogger('TomTomAPI')


class TomTomAPI:
    """
    TomTom Search API client.
    Free tier: 2,500 calls/day, 5 QPS (queries per second)
    """

    BASE_URL = "https://api.tomtom.com/search/2"

    # Rate limiting: 5 QPS = 200ms between calls
    MIN_DELAY_SECONDS = 0.2
    MAX_RETRIES = 3
    BACKOFF_MULTIPLIER = 2

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('TOMTOM_API_KEY')
        self._last_call_time = 0
        self._consecutive_errors = 0

    def _rate_limit_delay(self):
        """Enforce rate limiting between API calls."""
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
        limit: int = 100
    ) -> List[Dict]:
        """
        Search for businesses within radius with rate limiting and retry.
        """
        # KILL SWITCH CHECK
        if not check_before_api_call('TomTom'):
            return []

        if not self.api_key:
            logger.warning("[TomTom] API key not configured")
            return []

        # Enforce rate limit (5 QPS)
        self._rate_limit_delay()

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

        # Retry with exponential backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.get(url, params=params, timeout=15)

                if response.status_code == 200:
                    self._consecutive_errors = 0
                    data = response.json()
                    return self._parse_results(data.get('results', []))
                elif response.status_code == 401:
                    logger.error("[TomTom] Invalid API key (401)")
                    return []
                elif response.status_code in (429, 503):
                    # Rate limited - exponential backoff
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        wait_time = self.MIN_DELAY_SECONDS * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"[TomTom] Rate limited, waiting {wait_time:.1f}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 404:
                    # 404 can mean URL encoding issue - try once more
                    if attempt == 0:
                        logger.debug(f"[TomTom] 404 for query '{search_query}', retrying...")
                        time.sleep(0.5)
                        continue
                    logger.warning(f"[TomTom] 404 for query '{search_query}'")
                    return []
                else:
                    logger.error(f"[TomTom] Error {response.status_code}: {response.text[:200]}")
                    return []

            except requests.Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.MIN_DELAY_SECONDS * (self.BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"[TomTom] Timeout, retrying in {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue
                logger.error("[TomTom] Request timed out after retries")
                return []
            except Exception as e:
                logger.error(f"[TomTom] Error: {e}")
                return []

        return []

    def search_all_categories(self, lat: float, lon: float, radius_meters: int = 5000) -> List[Dict]:
        """
        Search relevant business types with rate-limited calls.
        Uses focused list of ~15 high-value terms instead of 100+.
        """
        all_results = []
        seen_ids = set()

        # Focused search terms - high-value service businesses only
        # This keeps API calls to ~15 per tile instead of 100+
        search_terms = [
            'plumber', 'plumbing',
            'roofer', 'roofing',
            'hvac', 'air conditioning',
            'electrician', 'electrical contractor',
            'landscaping', 'lawn service',
            'pest control', 'exterminator',
            'towing', 'tow truck',
            'auto body', 'collision repair',
            'car dealer', 'auto dealer',
            'contractor', 'home repair',
            'painter', 'painting contractor',
            'tree service',
        ]

        for term in search_terms:
            results = self.search_radius(lat, lon, radius_meters, query=term, limit=50)

            for biz in results:
                biz_id = biz.get('tomtom_id')
                if biz_id and biz_id not in seen_ids:
                    seen_ids.add(biz_id)
                    all_results.append(biz)

        return all_results

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
