"""
Foursquare Places API Client
============================
Client for Foursquare Places API v3.

Free tier: 100,000 calls/month
API Docs: https://developer.foursquare.com/docs/places-api-overview

Setup:
1. Sign up at https://foursquare.com/developers/
2. Create a project and get API key
3. Set environment variable: FOURSQUARE_API_KEY=your_key_here
"""

import requests
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger('FoursquareAPI')


class FoursquareAPI:
    """
    Foursquare Places API client.

    Free tier: 100,000 calls/month
    Uses new places-api.foursquare.com endpoint (June 2025+)
    """

    BASE_URL = "https://places-api.foursquare.com/places/search"
    API_VERSION = "2025-06-17"

    # Foursquare category IDs for fleet-relevant businesses
    # Full list: https://developer.foursquare.com/docs/categories
    CATEGORIES = {
        # Automotive
        'automotive': '10000',          # Top-level automotive
        'auto_repair': '10007',         # Auto Garage / Mechanic
        'car_dealer': '10006',          # Car Dealership
        'car_wash': '10008',            # Car Wash
        'auto_body': '10001',           # Auto Body Shop
        'tire_shop': '10014',           # Tire Shop
        'car_rental': '10005',          # Car Rental

        # Service/Trades (under Building & Trades 12000)
        'contractor': '12009',          # Contractor
        'landscaping': '12066',         # Landscaping Company
        'plumbing': '12096',            # Plumber
        'electrical': '12030',          # Electrician
        'hvac': '12058',                # HVAC
        'roofing': '12103',             # Roofing Contractor
        'painting': '12088',            # Painter
        'flooring': '12042',            # Flooring
        'cleaning': '11128',            # Cleaning Service

        # Commercial
        'hotel': '19014',               # Hotel
        'hospital': '15014',            # Hospital
        'school': '12077',              # School

        # Parking (high vehicle density)
        'parking': '19020',             # Parking Lot

        # Corporate
        'office': '11000',              # Office
    }

    # Map our internal categories to Foursquare IDs
    CATEGORY_MAPPING = {
        'car_dealership': ['10006'],
        'car_rental': ['10005'],
        'body_shop': ['10001', '10007'],
        'parking': ['19020'],
        'hotel': ['19014'],
        'hospital': ['15014'],
        'school': ['12077'],
        'church': [],  # No good Foursquare category for churches
        'landscaping': ['12066'],
        'hvac': ['12058'],
        'plumbing': ['12096'],
        'electrical': ['12030'],
        'roofing': ['12103'],
        'pest_control': [],  # Limited coverage
        'contractor': ['12009'],
    }

    def __init__(self, api_key: str = None):
        """
        Initialize Foursquare client.

        Args:
            api_key: Foursquare API key (or set FOURSQUARE_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('FOURSQUARE_API_KEY')
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json',
                'X-Places-Api-Version': self.API_VERSION
            })

    def is_configured(self) -> bool:
        """Check if API key is set."""
        return bool(self.api_key)

    def search_radius(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 1000,
        categories: List[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for businesses within radius of a point.

        Args:
            lat: Latitude
            lon: Longitude
            radius_meters: Search radius in meters (max 100,000)
            categories: List of Foursquare category IDs (or our internal names)
            limit: Max results per request (max 50)

        Returns:
            List of business dictionaries
        """
        if not self.api_key:
            logger.warning("Foursquare API key not set")
            return []

        # Map internal category names to Foursquare IDs
        category_ids = []
        if categories:
            for cat in categories:
                if cat in self.CATEGORIES:
                    category_ids.append(self.CATEGORIES[cat])
                elif cat in self.CATEGORY_MAPPING:
                    category_ids.extend(self.CATEGORY_MAPPING[cat])
                else:
                    # Assume it's already a Foursquare ID
                    category_ids.append(cat)

        params = {
            'll': f"{lat},{lon}",
            'radius': min(radius_meters, 100000),  # Max 100km
            'limit': min(limit, 50),  # Max 50 per request
        }

        if category_ids:
            params['categories'] = ','.join(category_ids)

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                results = self._parse_results(data.get('results', []))
                logger.info(f"Foursquare found {len(results)} places at ({lat}, {lon})")
                return results

            elif response.status_code == 401:
                logger.error("Foursquare: Invalid API key (401)")
                return []

            elif response.status_code == 429:
                logger.error("Foursquare: Rate limit exceeded (429)")
                return []

            else:
                logger.error(f"Foursquare error: {response.status_code}")
                return []

        except requests.Timeout:
            logger.error("Foursquare request timed out")
            return []
        except Exception as e:
            logger.error(f"Foursquare error: {e}")
            return []

    def search_all_fleet_categories(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 1000
    ) -> List[Dict]:
        """
        Search for all fleet-relevant business categories.

        Args:
            lat: Latitude
            lon: Longitude
            radius_meters: Search radius in meters

        Returns:
            Combined list of businesses
        """
        # Key categories for fleet/PDR targets
        target_categories = [
            'car_dealer', 'auto_body', 'auto_repair', 'car_rental',
            'parking', 'hotel', 'hospital', 'school',
            'landscaping', 'hvac', 'plumbing', 'contractor'
        ]

        return self.search_radius(lat, lon, radius_meters, target_categories)

    def _parse_results(self, results: List[Dict]) -> List[Dict]:
        """Parse Foursquare results into standard format."""
        businesses = []

        for place in results:
            location = place.get('location', {})
            geocodes = place.get('geocodes', {})
            main_geo = geocodes.get('main', {})

            # Get primary category
            categories = place.get('categories', [])
            category_name = categories[0].get('name', '') if categories else ''
            category_id = categories[0].get('id', '') if categories else ''

            # Map to our internal category
            internal_category = self._map_category(category_id, category_name)

            businesses.append({
                'name': place.get('name', ''),
                'address': location.get('address', ''),
                'city': location.get('locality', ''),
                'state': location.get('region', ''),
                'zip': location.get('postcode', ''),
                'phone': place.get('tel', ''),
                'website': place.get('website', ''),
                'email': '',
                'latitude': main_geo.get('latitude'),
                'longitude': main_geo.get('longitude'),
                'category': internal_category,
                'foursquare_category': category_name,
                'source': 'foursquare',
                'foursquare_id': place.get('fsq_id', ''),
            })

        return businesses

    def _map_category(self, category_id: str, category_name: str) -> str:
        """Map Foursquare category to our internal category."""
        # Direct ID mapping
        for our_cat, fs_ids in self.CATEGORY_MAPPING.items():
            if category_id in fs_ids:
                return our_cat

        # Name-based fallback
        name_lower = category_name.lower()
        if 'dealer' in name_lower or 'dealership' in name_lower:
            return 'car_dealership'
        elif 'body' in name_lower or 'mechanic' in name_lower or 'repair' in name_lower:
            return 'body_shop'
        elif 'rental' in name_lower:
            return 'car_rental'
        elif 'parking' in name_lower:
            return 'parking'
        elif 'hotel' in name_lower or 'motel' in name_lower:
            return 'hotel'
        elif 'hospital' in name_lower or 'medical' in name_lower:
            return 'hospital'
        elif 'school' in name_lower:
            return 'school'
        elif 'church' in name_lower:
            return 'church'
        elif 'landscap' in name_lower:
            return 'landscaping'
        elif 'hvac' in name_lower or 'heating' in name_lower or 'cooling' in name_lower:
            return 'hvac'
        elif 'plumb' in name_lower:
            return 'plumbing'
        elif 'electric' in name_lower:
            return 'electrical'
        elif 'roof' in name_lower:
            return 'roofing'

        return 'other'

    def test_connection(self) -> Dict:
        """
        Test API connection and key validity.

        Returns:
            Status dict with success flag and message
        """
        if not self.api_key:
            return {
                'success': False,
                'configured': False,
                'message': 'Foursquare API key not configured. Set FOURSQUARE_API_KEY environment variable.'
            }

        try:
            # Test with a simple search
            response = self.session.get(
                self.BASE_URL,
                params={
                    'll': '35.4676,-97.5164',  # OKC
                    'radius': 1000,
                    'limit': 1
                },
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
                    'message': 'Invalid Foursquare API key'
                }
            elif response.status_code == 429:
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


# Convenience function for testing
def test_foursquare():
    """Quick test of Foursquare API."""
    api = FoursquareAPI()

    print("Testing Foursquare connection...")
    status = api.test_connection()
    print(f"Status: {status}")

    if status['success']:
        print("\nSearching near Oklahoma City...")
        results = api.search_all_fleet_categories(35.4676, -97.5164, radius_meters=2000)
        print(f"Found {len(results)} results")

        for r in results[:5]:
            print(f"  - {r.get('name')} ({r.get('category')}) | {r.get('address')}")

        return results

    return []


if __name__ == '__main__':
    test_foursquare()
