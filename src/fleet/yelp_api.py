"""
Yelp Fusion API Integration
===========================

FREE: 5,000 API calls per day
Sign up: https://www.yelp.com/developers/v3/manage_app

Great for finding service businesses with vehicle fleets:
- Landscaping companies
- Pest control
- HVAC contractors
- Moving companies
- Towing services
- And more
"""

import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger('YelpAPI')

# Check if requests is available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available for Yelp API")


class YelpFleetAPI:
    """Interface to Yelp Fusion API for business discovery."""

    BASE_URL = "https://api.yelp.com/v3"

    # Yelp-specific category mappings (maps our categories to Yelp search terms)
    # Note: Main category definitions are in src.business.category_taxonomy
    YELP_CATEGORY_MAPPING = {
        'landscaping': {
            'yelp_cats': 'landscaping,gardeners,lawn_services,tree_services,irrigation',
            'est_vehicles': 8,
        },
        'pest_control': {
            'yelp_cats': 'pest_control',
            'est_vehicles': 12,
        },
        'hvac': {
            'yelp_cats': 'hvac',
            'est_vehicles': 6,
        },
        'plumbing': {
            'yelp_cats': 'plumbing',
            'est_vehicles': 6,
        },
        'electrical': {
            'yelp_cats': 'electricians',
            'est_vehicles': 6,
        },
        'roofing': {
            'yelp_cats': 'roofing',
            'est_vehicles': 8,
        },
        'moving': {
            'yelp_cats': 'movers,truckrental',
            'est_vehicles': 15,
        },
        'towing': {
            'yelp_cats': 'towing',
            'est_vehicles': 8,
        },
        'security': {
            'yelp_cats': 'securityservices,security_systems',
            'est_vehicles': 10,
        },
        'home_health': {
            'yelp_cats': 'homehealthcare,medicalcouriers',
            'est_vehicles': 12,
        },
        'auto_service': {
            'yelp_cats': 'autorepair,auto_detailing,carrental,autoglass',
            'est_vehicles': 5,
        },
        'contractors': {
            'yelp_cats': 'contractors,generalcontractors',
            'est_vehicles': 8,
        },
        'funeral': {
            'yelp_cats': 'funeralservices',
            'est_vehicles': 8,
        },
        'equipment_rental': {
            'yelp_cats': 'equipmentrental,partyrental',
            'est_vehicles': 15,
        },
        'auto_auction': {
            'yelp_cats': 'autosauctions,carbuyers',
            'est_vehicles': 50,
        },
    }

    def __init__(self, api_key: str = None):
        """
        Initialize Yelp API client.

        Get your free API key at: https://www.yelp.com/developers/v3/manage_app
        Set environment variable: YELP_API_KEY=your_key_here
        """
        self.api_key = api_key or os.environ.get('YELP_API_KEY')
        if not self.api_key:
            logger.warning("No Yelp API key. Set YELP_API_KEY environment variable.")
            logger.warning("Get free key at: https://www.yelp.com/developers/v3/manage_app")

    def is_available(self) -> bool:
        """Check if Yelp API is available (has key and requests library)."""
        return bool(self.api_key) and REQUESTS_AVAILABLE

    def search_businesses(self,
                         city: str,
                         state: str,
                         categories: str = None,
                         limit: int = 50) -> List[Dict]:
        """
        Search for businesses in a city.

        Args:
            city: City name
            state: State abbreviation
            categories: Yelp category string (comma-separated)
            limit: Max results (max 50 per call)

        Returns:
            List of business dictionaries
        """
        if not self.is_available():
            return []

        url = f"{self.BASE_URL}/businesses/search"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        params = {
            "location": f"{city}, {state}",
            "limit": min(limit, 50),
            "sort_by": "review_count",  # Larger businesses tend to have more reviews
        }

        if categories:
            params["categories"] = categories

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            businesses = []
            for biz in data.get('businesses', []):
                # Extract location info
                location = biz.get('location', {})
                coords = biz.get('coordinates', {})

                businesses.append({
                    'name': biz.get('name'),
                    'address': ' '.join(location.get('display_address', [])),
                    'city': location.get('city'),
                    'state': location.get('state'),
                    'zip': location.get('zip_code'),
                    'phone': biz.get('display_phone') or biz.get('phone'),
                    'latitude': coords.get('latitude'),
                    'longitude': coords.get('longitude'),
                    'category': self._map_category(biz.get('categories', [])),
                    'yelp_categories': [c.get('alias') for c in biz.get('categories', [])],
                    'rating': biz.get('rating'),
                    'review_count': biz.get('review_count'),
                    'url': biz.get('url'),
                    'source': 'YELP',
                    'vehicle_count': self._estimate_vehicles(biz),
                    'yelp_id': biz.get('id'),
                })

            return businesses

        except Exception as e:
            logger.error(f"Yelp API error: {e}")
            return []

    def search_fleet_businesses(self, city: str, state: str) -> List[Dict]:
        """
        Search for all fleet-relevant businesses in a city.

        This makes multiple API calls (one per category group).
        Uses approximately 15 API calls.
        """
        if not self.is_available():
            logger.warning("Yelp API not available")
            return []

        all_businesses = []
        seen_ids = set()

        for category_name, config in self.YELP_CATEGORY_MAPPING.items():
            yelp_cats = config['yelp_cats']

            try:
                businesses = self.search_businesses(
                    city=city,
                    state=state,
                    categories=yelp_cats,
                    limit=50
                )

                for biz in businesses:
                    # Deduplicate by Yelp ID
                    biz_id = biz.get('yelp_id')
                    if biz_id and biz_id not in seen_ids:
                        seen_ids.add(biz_id)
                        biz['fleet_category'] = category_name
                        all_businesses.append(biz)

            except Exception as e:
                logger.warning(f"Error searching {category_name}: {e}")
                continue

        logger.info(f"Yelp: Found {len(all_businesses)} businesses in {city}, {state}")
        return all_businesses

    def _map_category(self, yelp_categories: List[Dict]) -> str:
        """Map Yelp categories to our fleet categories."""
        aliases = [c.get('alias', '') for c in yelp_categories]
        alias_str = ' '.join(aliases).lower()

        if any(x in alias_str for x in ['landscap', 'lawn', 'tree', 'garden', 'irrigation']):
            return 'landscaping'
        elif 'pest' in alias_str:
            return 'pest_control'
        elif 'hvac' in alias_str:
            return 'service_trades'
        elif 'plumb' in alias_str:
            return 'service_trades'
        elif 'electric' in alias_str:
            return 'service_trades'
        elif 'roof' in alias_str:
            return 'service_trades'
        elif any(x in alias_str for x in ['mover', 'moving', 'truck']):
            return 'moving'
        elif 'tow' in alias_str:
            return 'towing'
        elif 'security' in alias_str:
            return 'security'
        elif any(x in alias_str for x in ['homehealth', 'medical', 'hospice']):
            return 'home_health'
        elif 'funeral' in alias_str:
            return 'funeral'
        elif any(x in alias_str for x in ['autorepair', 'auto_detail', 'autoglass']):
            return 'body_shop'
        elif any(x in alias_str for x in ['contractor', 'generalcontractor']):
            return 'service_trades'
        elif any(x in alias_str for x in ['equipment', 'rental']):
            return 'equipment_rental'
        elif any(x in alias_str for x in ['auction', 'carbuyer']):
            return 'auto_auction'
        else:
            return 'service_trades'

    def _estimate_vehicles(self, biz: Dict) -> int:
        """Estimate vehicle count based on review count and category."""
        review_count = biz.get('review_count', 0) or 0
        categories = [c.get('alias', '') for c in biz.get('categories', [])]
        category_str = ' '.join(categories).lower()

        # Base estimate by category
        if any(x in category_str for x in ['landscap', 'lawn']):
            base = 8
        elif 'pest' in category_str:
            base = 12
        elif any(x in category_str for x in ['hvac', 'plumb', 'electric']):
            base = 6
        elif any(x in category_str for x in ['moving', 'mover']):
            base = 15
        elif 'towing' in category_str:
            base = 8
        elif any(x in category_str for x in ['auction', 'carbuyer']):
            base = 50
        else:
            base = 5

        # Adjust by review count (proxy for business size)
        if review_count > 200:
            multiplier = 2.0
        elif review_count > 100:
            multiplier = 1.5
        elif review_count > 50:
            multiplier = 1.2
        else:
            multiplier = 1.0

        return int(base * multiplier)

    def get_business_details(self, yelp_id: str) -> Optional[Dict]:
        """Get detailed information about a specific business."""
        if not self.is_available():
            return None

        url = f"{self.BASE_URL}/businesses/{yelp_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting business details: {e}")
            return None
