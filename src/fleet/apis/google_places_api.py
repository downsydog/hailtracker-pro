"""
Google Places API Client
========================
Free tier: $200/month credit
IMPORTANT: Uses pagination for complete coverage (60 result limit per query)
Docs: https://developers.google.com/maps/documentation/places/web-service/nearby-search

Setup:
1. Go to https://console.cloud.google.com
2. Create a project and enable Places API
3. Create API key with Places API permissions
4. Set environment variable: GOOGLE_PLACES_API_KEY=your_key_here
"""

import requests
from typing import List, Dict
import os
import logging
import time

# KILL SWITCH - Added after $200 billing incident
try:
    from src.api_killswitch import check_before_api_call
except ImportError:
    def check_before_api_call(name): return os.environ.get('API_CALLS_ENABLED', 'false').lower() == 'true'

logger = logging.getLogger('GooglePlacesAPI')


class GooglePlacesAPI:
    """
    Google Places API client.
    Free tier: $200/month credit
    IMPORTANT: Uses tiles for complete coverage (60 result limit per query)
    """

    BASE_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    # Google place types
    # Docs: https://developers.google.com/maps/documentation/places/web-service/supported_types
    TYPES = [
        'car_dealer', 'car_rental', 'car_repair', 'car_wash',
        'gas_station', 'parking',
        'local_government_office', 'police', 'fire_station',
        'school', 'university',
        'moving_company', 'storage',
        'general_contractor', 'electrician', 'plumber', 'roofing_contractor',
        'painter', 'locksmith',
    ]

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')

    def search_radius(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 5000,
        place_type: str = None,
        keyword: str = None
    ) -> List[Dict]:
        """
        Search for places within radius.

        NOTE: Max 60 results per query. Use tiles for complete coverage.
        """
        # KILL SWITCH CHECK - Added after $200 billing incident
        if not check_before_api_call('Google'):
            return []

        if not self.api_key:
            logger.warning("[Google] API key not configured")
            return []

        params = {
            'location': f'{lat},{lon}',
            'radius': radius_meters,
            'key': self.api_key,
        }

        if place_type:
            params['type'] = place_type

        if keyword:
            params['keyword'] = keyword

        all_results = []

        try:
            # First page
            response = requests.get(self.BASE_URL, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()

                if data.get('status') not in ['OK', 'ZERO_RESULTS']:
                    logger.error(f"[Google] Status: {data.get('status')} - {data.get('error_message', '')}")
                    return []

                all_results.extend(self._parse_results(data.get('results', [])))

                # Get next pages (up to 60 total)
                while data.get('next_page_token'):
                    time.sleep(2)  # Required delay for next_page_token

                    next_params = {
                        'pagetoken': data['next_page_token'],
                        'key': self.api_key,
                    }

                    response = requests.get(self.BASE_URL, params=next_params, timeout=15)

                    if response.status_code == 200:
                        data = response.json()
                        all_results.extend(self._parse_results(data.get('results', [])))
                    else:
                        break

                return all_results
            elif response.status_code == 401:
                logger.error("[Google] Invalid API key (401)")
                return []
            elif response.status_code == 429:
                logger.error("[Google] Rate limit exceeded (429)")
                return []
            else:
                logger.error(f"[Google] Error {response.status_code}")
                return []

        except requests.Timeout:
            logger.error("[Google] Request timed out")
            return []
        except Exception as e:
            logger.error(f"[Google] Error: {e}")
            return []

    def search_all_categories(self, lat: float, lon: float, radius_meters: int = 5000) -> List[Dict]:
        """
        Search all relevant place types using BROAD search terms.

        EFFICIENCY FIX: Uses 22 broad terms instead of 104 individual category names!
        - Old method: 104 taxonomy display names = 104 API calls per tile
        - New method: 22 broad terms that cover all categories = 22 API calls per tile
        - Savings: 82 API calls per tile = 79% reduction

        For 500 tiles: 11,000 calls instead of 52,000 calls

        Note: Google Places charges per call, so this saves significant money!
        """
        all_results = []
        seen_ids = set()

        # 22 broad search terms that cover all 104 fleet-relevant categories
        # Google Places is expensive - but need coverage (still 79% reduction from 104)
        broad_keywords = [
            # Automotive (4 terms)
            'car dealer',
            'auto body shop',
            'auto repair',
            'towing',
            # Service Trades - Core (5 terms)
            'contractor',
            'plumber',
            'hvac contractor',
            'electrician',
            'roofing contractor',
            # Service Trades - Specialty (5 terms)
            'cleaning service',     # carpet, window, mold, pressure washing
            'garage door',
            'locksmith',
            'appliance repair',
            'glass repair',
            # Exterior (3 terms)
            'landscaping',
            'pest control',
            'pool service',
            # Specialty (3 terms)
            'septic',
            'security system',
            'dumpster rental',
            # Commercial/Other (2 terms)
            'warehouse',
            'city hall',
            # Additional coverage (5 terms)
            'restoration company',  # mold, water, fire damage
            'junk removal',         # debris, cleanout
            'sign company',         # signs, wraps
            'florist',              # flower shop
            'insulation contractor',# spray foam, attic insulation
        ]

        for keyword in broad_keywords:
            results = self.search_radius(lat, lon, radius_meters, keyword=keyword)

            for biz in results:
                if biz.get('google_id') not in seen_ids:
                    seen_ids.add(biz.get('google_id'))
                    all_results.append(biz)

        return all_results

    def search_tiles(
        self,
        tiles: List[Dict],
        keywords: List[str] = None,
        progress_callback=None
    ) -> List[Dict]:
        """
        Search Google Places using tiles for complete coverage.

        Google returns max 60 results per query, so we break the area
        into small tiles and query each one.

        Args:
            tiles: List of tile dicts with center_lat, center_lon, search_radius_miles
            keywords: Keywords to search (defaults to fleet-relevant terms)
            progress_callback: Optional callback(tiles_done, total_tiles, results_count)

        Returns:
            Deduplicated list of businesses
        """
        if not self.api_key:
            logger.warning("[Google] API key not configured")
            return []

        if keywords is None:
            keywords = [
                'car dealer', 'auto dealer',
                'auto body', 'body shop',
                'landscaping', 'lawn care',
                'hvac', 'plumber', 'electrician',
                'roofing', 'contractor',
            ]

        all_results = []
        seen_ids = set()

        total_tiles = len(tiles)
        logger.info(f"[Google] Searching {total_tiles} tiles with {len(keywords)} keywords...")

        for i, tile in enumerate(tiles):
            center_lat = tile.get('center_lat') or tile.get('lat')
            center_lon = tile.get('center_lon') or tile.get('lon')
            radius_miles = tile.get('search_radius_miles', 0.5)
            radius_meters = int(radius_miles * 1609)

            # Search each keyword for this tile
            for keyword in keywords:
                results = self.search_radius(
                    center_lat,
                    center_lon,
                    radius_meters,
                    keyword=keyword
                )

                # Dedupe as we go
                for biz in results:
                    google_id = biz.get('google_id')
                    if google_id and google_id not in seen_ids:
                        seen_ids.add(google_id)
                        all_results.append(biz)

                # Small delay to respect rate limits
                time.sleep(0.1)

            # Progress logging
            if (i + 1) % 10 == 0 or (i + 1) == total_tiles:
                logger.info(f"[Google] Searched {i + 1}/{total_tiles} tiles, found {len(all_results)} unique businesses")

            if progress_callback:
                progress_callback(i + 1, total_tiles, len(all_results))

        logger.info(f"[Google] Total: {len(all_results)} unique businesses from {total_tiles} tiles")
        return all_results

    def search_swaths_with_tiles(
        self,
        swaths: List[Dict],
        tile_size_miles: float = 0.25,
        keywords: List[str] = None
    ) -> List[Dict]:
        """
        Search Google Places within swath polygons using tile-based approach.

        This is the recommended method for complete coverage within swaths.

        Args:
            swaths: List of GeoJSON swath polygons
            tile_size_miles: Size of tiles (0.5 recommended)
            keywords: Search keywords

        Returns:
            List of unique businesses within swaths
        """
        from src.business.tile_system import SwathTileSystem

        # Generate tiles for all swaths
        tile_system = SwathTileSystem(tile_size_miles=tile_size_miles)
        tiles = tile_system.generate_tiles_for_multiple_swaths(swaths)

        logger.info(f"[Google] Generated {len(tiles)} tiles for {len(swaths)} swaths")

        if not tiles:
            logger.warning("[Google] No tiles generated for swaths")
            return []

        # Convert Tile objects to dicts
        tile_dicts = [t.to_dict() for t in tiles]

        # Search all tiles
        return self.search_tiles(tile_dicts, keywords=keywords)

    def _parse_results(self, results: list) -> List[Dict]:
        """Parse Google Places results into standard format."""
        parsed = []

        for place in results:
            location = place.get('geometry', {}).get('location', {})

            parsed.append({
                'name': place.get('name', ''),
                'address': place.get('vicinity', ''),
                'city': '',  # Not directly provided
                'state': '',
                'zip': '',
                'phone': '',  # Requires Place Details API call
                'website': '',  # Requires Place Details API call
                'latitude': location.get('lat'),
                'longitude': location.get('lng'),
                'category': place.get('types', [''])[0] if place.get('types') else '',
                'rating': place.get('rating'),
                'source': 'google',
                'google_id': place.get('place_id'),
            })

        return parsed

    def get_place_details(self, place_id: str) -> Dict:
        """
        Get detailed info for a place (phone, website, etc.)
        Note: Each call costs extra - use sparingly.
        """
        if not self.api_key:
            return {}

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'fields': 'formatted_phone_number,website,formatted_address',
            'key': self.api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})
                return {
                    'phone': result.get('formatted_phone_number', ''),
                    'website': result.get('website', ''),
                    'address': result.get('formatted_address', ''),
                }
        except Exception as e:
            logger.error(f"[Google] Error getting place details: {e}")

        return {}

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def test_connection(self) -> Dict:
        """Test API connection and key validity."""
        if not self.api_key:
            return {
                'success': False,
                'configured': False,
                'message': 'Google Places API key not configured. Set GOOGLE_PLACES_API_KEY environment variable.'
            }

        try:
            params = {
                'location': '35.4676,-97.5164',
                'radius': 1000,
                'key': self.api_key,
            }
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            data = response.json()

            if data.get('status') in ['OK', 'ZERO_RESULTS']:
                return {
                    'success': True,
                    'configured': True,
                    'message': 'Google Places API is working'
                }
            else:
                return {
                    'success': False,
                    'configured': True,
                    'message': f"API error: {data.get('status')} - {data.get('error_message', '')}"
                }
        except Exception as e:
            return {
                'success': False,
                'configured': True,
                'message': f'Connection error: {str(e)}'
            }
