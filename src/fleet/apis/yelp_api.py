"""
Yelp Fusion API Client
======================
Free tier: 5,000 calls/day (150,000/month)
Docs: https://docs.developer.yelp.com/reference/v3_business_search

Setup:
1. Sign up at https://www.yelp.com/developers
2. Create an app and get API key
3. Set environment variable: YELP_API_KEY=your_key_here

COMPREHENSIVE PDR FLEET PROSPECTING CATEGORIES
Updated with full list of service businesses that have work vehicles.
"""

import requests
from typing import List, Dict, Optional
import os
import logging
from math import radians, cos, sqrt

logger = logging.getLogger('YelpAPI')


class YelpAPI:
    """
    Yelp Fusion API client.
    Free tier: 5,000 calls/day
    """

    BASE_URL = "https://api.yelp.com/v3"

    # ==========================================================================
    # COMPREHENSIVE YELP CATEGORIES FOR PDR FLEET PROSPECTING
    # ==========================================================================
    # Full list: https://www.yelp.com/developers/documentation/v3/all_category_list

    # DISTRIBUTION/DELIVERY
    DISTRIBUTION_CATEGORIES = [
        'beer_and_wine',           # Beer/wine distributors
        'wholesale_stores',        # Wholesale distributors
        'couriers',                # Courier services
        'fooddeliveryservices',    # Food delivery
        'medicalequipment',        # Medical supply delivery
    ]

    # TRADES/SERVICE COMPANIES
    TRADES_CATEGORIES = [
        'hvac',                    # HVAC contractors
        'heating_air',             # Heating and air
        'plumbing',                # Plumbers
        'plumbers',                # Plumbers (alias)
        'electricians',            # Electricians
        'electrical',              # Electrical contractors
        'pest_control',            # Pest control
        'landscaping',             # Landscaping
        'lawn_services',           # Lawn care
        'tree_services',           # Tree service
        'roofing',                 # Roofing contractors
        'roof_inspection',         # Roof inspection
        'siding',                  # Siding contractors
        'gutter_services',         # Gutter installation
        'fences_gates',            # Fence contractors
        'pool_cleaners',           # Pool service
        'irrigation',              # Irrigation/sprinkler
        'garage_door_services',    # Garage door repair
        'locksmiths',              # Locksmiths
        'painters',                # Painting contractors
        'painting',                # Painters (alias)
        'flooring',                # Flooring contractors
        'carpet_cleaning',         # Carpet cleaning
        'concrete',                # Concrete contractors
        'paving',                  # Paving/asphalt
        'pressure_washers',        # Pressure washing
        'window_washing',          # Window cleaning
        'damage_restoration',      # Fire/water restoration
        'septic_services',         # Septic service
        'portabletoiletservices',  # Portable toilets
    ]

    # CONSTRUCTION/INDUSTRIAL
    CONSTRUCTION_CATEGORIES = [
        'contractors',             # General contractors
        'general_contractors',     # General contractors (alias)
        'excavationservices',      # Excavation/grading
        'surveyors',               # Land surveyors
        'equipmentrental',         # Equipment rental
        'buildingsupplies',        # Building supply
        'lumberyards',             # Lumber yards
    ]

    # AUTOMOTIVE
    AUTOMOTIVE_CATEGORIES = [
        'towing',                  # Towing service
        'auto_repair',             # Auto repair
        'body_shops',              # Body shops
        'auto_glass',              # Auto glass/Safelite
        'roadside_assistance',     # Roadside assistance
        'oilchange',               # Oil change
        'carwash',                 # Car wash
        'auto_detailing',          # Mobile detailing
        'car_dealers',             # Car dealerships
    ]

    # MEDICAL/HEALTH
    MEDICAL_CATEGORIES = [
        'homehealthcare',          # Home health
        'medtransport',            # Medical transport
        'hospice',                 # Hospice
        'veterinarians',           # Mobile vet
        'pharmacies',              # Pharmacy delivery
    ]

    # TELECOM/TECH
    TELECOM_CATEGORIES = [
        'isps',                    # Cable/internet installers
        'itservices',              # IT service
        'security_systems',        # Security/alarm systems
        'telecommunications',      # Phone systems
    ]

    # WASTE/ENVIRONMENTAL
    WASTE_CATEGORIES = [
        'junkremovalandhauling',   # Junk removal
        'recyclingcenter',         # Recycling
        'dumpsterrental',          # Dumpster rental
    ]

    # RENTAL COMPANIES
    RENTAL_CATEGORIES = [
        'partyrental',             # Party/event rental
        'partysupplies',           # Party supplies
        'trailerrental',           # Trailer rental
        'truck_rental',            # Truck rental
    ]

    # PROPERTY/FACILITIES
    PROPERTY_CATEGORIES = [
        'propertymanagement',      # Property management
        'janitorial',              # Janitorial service
        'office_cleaning',         # Commercial cleaning
    ]

    # OTHER SERVICE COMPANIES
    OTHER_CATEGORIES = [
        'signmaking',              # Sign companies
        'printingservices',        # Print shops
        'funeralservices',         # Funeral homes
        'limos',                   # Limo/shuttle service
        'transport',               # Transport services
        'movers',                  # Moving companies
        'moving_companies',        # Movers (alias)
        'solar_installation',      # Solar installers
    ]

    # COMBINED FULL CATEGORY LIST
    CATEGORIES = (
        DISTRIBUTION_CATEGORIES +
        TRADES_CATEGORIES +
        CONSTRUCTION_CATEGORIES +
        AUTOMOTIVE_CATEGORIES +
        MEDICAL_CATEGORIES +
        TELECOM_CATEGORIES +
        WASTE_CATEGORIES +
        RENTAL_CATEGORIES +
        PROPERTY_CATEGORIES +
        OTHER_CATEGORIES
    )

    # Optimized batch groups for API efficiency
    CATEGORY_BATCHES = [
        # Distribution/Delivery
        'beer_and_wine,wholesale_stores,couriers,fooddeliveryservices',
        # HVAC/Plumbing/Electrical
        'hvac,heating_air,plumbing,electricians',
        # Landscaping/Tree/Lawn
        'landscaping,lawn_services,tree_services,irrigation',
        # Roofing/Siding/Exterior
        'roofing,siding,gutter_services,fences_gates',
        # Pest/Pool/Cleaning
        'pest_control,pool_cleaners,carpet_cleaning,pressure_washers',
        # Trades misc
        'painters,flooring,concrete,paving',
        # Garage/Locks/Restoration
        'garage_door_services,locksmiths,damage_restoration,septic_services',
        # Construction
        'contractors,excavationservices,equipmentrental,buildingsupplies',
        # Automotive
        'towing,auto_repair,body_shops,auto_glass,car_dealers',
        # Medical
        'homehealthcare,medtransport,hospice,veterinarians',
        # Telecom/Security
        'isps,itservices,security_systems,telecommunications',
        # Waste/Junk
        'junkremovalandhauling,recyclingcenter,dumpsterrental',
        # Rental/Property
        'partyrental,trailerrental,propertymanagement,janitorial',
        # Other services
        'signmaking,printingservices,funeralservices,movers,limos',
    ]

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
        """Search all comprehensive fleet-relevant categories."""
        all_results = []
        seen_ids = set()

        for batch in self.CATEGORY_BATCHES:
            results = self.search_radius(lat, lon, radius_meters, categories=batch.split(','))

            for biz in results:
                if biz.get('yelp_id') not in seen_ids:
                    seen_ids.add(biz.get('yelp_id'))
                    all_results.append(biz)

        logger.info(f"[Yelp] Found {len(all_results)} unique businesses across all categories")
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
                telecom, waste, rental, property, other
        """
        group_map = {
            'distribution': self.DISTRIBUTION_CATEGORIES,
            'trades': self.TRADES_CATEGORIES,
            'construction': self.CONSTRUCTION_CATEGORIES,
            'automotive': self.AUTOMOTIVE_CATEGORIES,
            'medical': self.MEDICAL_CATEGORIES,
            'telecom': self.TELECOM_CATEGORIES,
            'waste': self.WASTE_CATEGORIES,
            'rental': self.RENTAL_CATEGORIES,
            'property': self.PROPERTY_CATEGORIES,
            'other': self.OTHER_CATEGORIES,
        }

        categories = group_map.get(group.lower(), self.TRADES_CATEGORIES)
        return self.search_radius(lat, lon, radius_meters, categories=categories)

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
