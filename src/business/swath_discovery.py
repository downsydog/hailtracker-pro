"""
Smart Swath-Based Business Discovery
=====================================
Finds fleet businesses within hail swath polygons using multiple data sources:
- OSM Overpass API (comprehensive, returns coordinates)
- Foursquare Places API (100k/month free)
- Yelp Fusion API (5k/day free)
- HERE Places API (250k/month free)
- TomTom Search API (2.5k/day free)
- Google Places API ($200/month credit)
- Yellow Pages (service businesses, requires geocoding)
- BBB (accredited businesses, requires geocoding)

Features:
- Comprehensive 80+ business category search
- Full contact info extraction (phone, website, email)
- Database caching (don't re-scrape same storm)
- Point-in-polygon filtering to only include businesses in actual swath
- Multi-source deduplication by name/address similarity

PDR Fleet Categories:
- Automotive: dealerships, rental, body shops, parts, car washes
- Service/Trades: landscaping, HVAC, plumbing, electrical, roofing, etc.
- Medical: hospitals, clinics, veterinary
- Government: police, fire, schools, post offices
- Commercial: hotels, storage, rental companies

Recommended API Usage:
- Primary: OSM (unlimited), Foursquare, Yelp
- Secondary: HERE, TomTom
- Expensive: Google (use sparingly)
"""
import json
import math
import sqlite3
import logging
import re
from typing import List, Dict, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime
import requests
import time
from difflib import SequenceMatcher

from src.radar.geo_utils import GeoUtils
from src.fleet.scrapers.yellowpages import YellowPagesScraper
from src.fleet.scrapers.bbb import BBBScraper
from src.fleet.scrapers.foursquare_api import FoursquareAPI
from src.fleet.apis.yelp_api import YelpAPI
from src.fleet.apis.here_api import HereAPI
from src.fleet.apis.tomtom_api import TomTomAPI
from src.fleet.apis.google_places_api import GooglePlacesAPI

# Use proper deduplication
from src.business.deduplication import deduplicate_businesses

# Use the unified category taxonomy
from src.business.category_taxonomy import (
    CATEGORY_TAXONOMY,
    normalize_category_key,
    estimate_vehicles,
    detect_category_from_tags,
    get_categories_by_tier,
)

logger = logging.getLogger('SwathDiscovery')


class SwathDiscoveryService:
    """Discovers businesses within hail swath polygons using multiple data sources."""

    # Overpass API endpoint
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    # Nominatim geocoding endpoint
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    # Yellow Pages search terms for service businesses (these get good fleet results)
    YP_SEARCH_TERMS = [
        ('landscaping', 'landscaping'),
        ('lawn care', 'landscaping'),
        ('pest control', 'pest_control'),
        ('hvac contractors', 'hvac'),
        ('plumbing contractors', 'plumbing'),
        ('roofing contractors', 'roofing'),
        ('moving companies', 'moving'),
        ('electrical contractors', 'electrical'),
        ('tree service', 'landscaping'),
        ('pool service', 'pool_service'),
        ('carpet cleaning', 'cleaning'),
        ('window cleaning', 'cleaning'),
        ('painting contractors', 'contractor'),
        ('garage door', 'contractor'),
    ]

    # BBB category slugs for high-value service businesses
    BBB_CATEGORIES = [
        ('landscape-contractors', 'landscaping'),
        ('lawn-maintenance', 'landscaping'),
        ('pest-control-services', 'pest_control'),
        ('air-conditioning-contractors-systems', 'hvac'),
        ('heating-contractors', 'hvac'),
        ('plumbers', 'plumbing'),
        ('roofing-contractors', 'roofing'),
        ('movers', 'moving'),
        ('electricians', 'electrical'),
        ('tree-service', 'landscaping'),
        ('general-contractors', 'contractor'),
        ('garage-doors-openers', 'contractor'),
        ('painting-contractors', 'contractor'),
    ]

    # Vehicle estimates now come from unified taxonomy via estimate_vehicles()
    # Kept as property for backwards compatibility
    @property
    def VEHICLE_ESTIMATES(self) -> dict:
        """Get vehicle estimates from taxonomy (backwards compat)."""
        estimates = {'default': 10}
        for key, config in CATEGORY_TAXONOMY.items():
            estimates[key] = config.get('est_vehicles', 10)
        return estimates

    # Tier assignments now come from unified taxonomy
    @property
    def TIER_MAP(self) -> dict:
        """Get tier map from taxonomy (backwards compat)."""
        return {
            1: get_categories_by_tier(1),
            2: get_categories_by_tier(2),
            3: get_categories_by_tier(3),
        }

    def __init__(self, db_path: str = None, crm_db_path: str = None):
        """Initialize the SwathDiscoveryService."""
        data_dir = Path(__file__).parent.parent.parent / 'data'

        if db_path is None:
            db_path = str(data_dir / 'business_prospects.db')

        if crm_db_path is None:
            crm_db_path = str(data_dir / 'hailtracker_crm.db')

        self.db_path = db_path
        self.crm_db_path = crm_db_path

        # Initialize scrapers
        self.yp_scraper = YellowPagesScraper(db_path)
        self.bbb_scraper = BBBScraper(db_path)

        # Initialize API clients
        self.foursquare = FoursquareAPI()
        self.yelp = YelpAPI()
        self.here = HereAPI()
        self.tomtom = TomTomAPI()
        self.google = GooglePlacesAPI()

        self._init_cache_table()

    def _init_cache_table(self):
        """Create the swath_businesses cache table if it doesn't exist."""
        conn = sqlite3.connect(self.crm_db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS swath_businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                storm_date TEXT,
                osm_id TEXT,
                name TEXT,
                category TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                phone TEXT,
                website TEXT,
                email TEXT,
                latitude REAL,
                longitude REAL,
                estimated_vehicles INTEGER,
                source TEXT DEFAULT 'osm',
                in_swath BOOLEAN DEFAULT 1,
                added_to_crm BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, osm_id)
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_swath_biz_event ON swath_businesses(event_id)')
        conn.commit()
        conn.close()
        logger.info("Swath businesses cache table initialized")

    def _build_comprehensive_overpass_query(self, lat: float, lon: float,
                                             radius_meters: int) -> str:
        """
        Build a comprehensive Overpass QL query for ALL business types.

        This searches for 80+ business categories relevant to PDR fleet prospecting.
        """
        query = f'''[out:json][timeout:120];
(
  // ==================== AUTOMOTIVE ====================
  // Car dealerships
  node["shop"="car"](around:{radius_meters},{lat},{lon});
  way["shop"="car"](around:{radius_meters},{lat},{lon});
  node["shop"="car_dealer"](around:{radius_meters},{lat},{lon});
  way["shop"="car_dealer"](around:{radius_meters},{lat},{lon});

  // Car rental
  node["amenity"="car_rental"](around:{radius_meters},{lat},{lon});
  way["amenity"="car_rental"](around:{radius_meters},{lat},{lon});

  // Body shops and repair
  node["shop"="car_repair"](around:{radius_meters},{lat},{lon});
  way["shop"="car_repair"](around:{radius_meters},{lat},{lon});
  node["craft"="car_body"](around:{radius_meters},{lat},{lon});
  way["craft"="car_body"](around:{radius_meters},{lat},{lon});
  node["craft"="auto_body"](around:{radius_meters},{lat},{lon});
  way["craft"="auto_body"](around:{radius_meters},{lat},{lon});

  // Car parts
  node["shop"="car_parts"](around:{radius_meters},{lat},{lon});
  way["shop"="car_parts"](around:{radius_meters},{lat},{lon});
  node["shop"="tyres"](around:{radius_meters},{lat},{lon});
  way["shop"="tyres"](around:{radius_meters},{lat},{lon});

  // Motorcycle
  node["shop"="motorcycle"](around:{radius_meters},{lat},{lon});
  way["shop"="motorcycle"](around:{radius_meters},{lat},{lon});

  // Car wash
  node["amenity"="car_wash"](around:{radius_meters},{lat},{lon});
  way["amenity"="car_wash"](around:{radius_meters},{lat},{lon});

  // Fuel stations
  node["amenity"="fuel"](around:{radius_meters},{lat},{lon});
  way["amenity"="fuel"](around:{radius_meters},{lat},{lon});

  // Parking
  node["amenity"="parking"]["access"!="private"](around:{radius_meters},{lat},{lon});
  way["amenity"="parking"]["access"!="private"](around:{radius_meters},{lat},{lon});
  node["building"="parking"](around:{radius_meters},{lat},{lon});
  way["building"="parking"](around:{radius_meters},{lat},{lon});

  // ==================== SERVICE / TRADES ====================
  // Craft businesses (plumbers, electricians, HVAC, etc.)
  node["craft"](around:{radius_meters},{lat},{lon});
  way["craft"](around:{radius_meters},{lat},{lon});

  // Trade shops
  node["shop"="trade"](around:{radius_meters},{lat},{lon});
  way["shop"="trade"](around:{radius_meters},{lat},{lon});
  node["shop"="hardware"](around:{radius_meters},{lat},{lon});
  way["shop"="hardware"](around:{radius_meters},{lat},{lon});

  // Company offices (landscaping, contractors, etc.)
  node["office"="company"](around:{radius_meters},{lat},{lon});
  way["office"="company"](around:{radius_meters},{lat},{lon});

  // Moving companies
  node["office"="moving_company"](around:{radius_meters},{lat},{lon});
  way["office"="moving_company"](around:{radius_meters},{lat},{lon});

  // Courier/delivery
  node["office"="courier"](around:{radius_meters},{lat},{lon});
  way["office"="courier"](around:{radius_meters},{lat},{lon});
  node["office"="logistics"](around:{radius_meters},{lat},{lon});
  way["office"="logistics"](around:{radius_meters},{lat},{lon});

  // ==================== TELECOM / SECURITY ====================
  node["office"="telecommunication"](around:{radius_meters},{lat},{lon});
  way["office"="telecommunication"](around:{radius_meters},{lat},{lon});
  node["office"="security"](around:{radius_meters},{lat},{lon});
  way["office"="security"](around:{radius_meters},{lat},{lon});

  // ==================== MEDICAL ====================
  node["amenity"="hospital"](around:{radius_meters},{lat},{lon});
  way["amenity"="hospital"](around:{radius_meters},{lat},{lon});
  node["amenity"="clinic"](around:{radius_meters},{lat},{lon});
  way["amenity"="clinic"](around:{radius_meters},{lat},{lon});
  node["healthcare"](around:{radius_meters},{lat},{lon});
  way["healthcare"](around:{radius_meters},{lat},{lon});
  node["office"="healthcare"](around:{radius_meters},{lat},{lon});
  way["office"="healthcare"](around:{radius_meters},{lat},{lon});
  node["amenity"="veterinary"](around:{radius_meters},{lat},{lon});
  way["amenity"="veterinary"](around:{radius_meters},{lat},{lon});

  // ==================== GOVERNMENT ====================
  node["amenity"="police"](around:{radius_meters},{lat},{lon});
  way["amenity"="police"](around:{radius_meters},{lat},{lon});
  node["amenity"="fire_station"](around:{radius_meters},{lat},{lon});
  way["amenity"="fire_station"](around:{radius_meters},{lat},{lon});
  node["amenity"="townhall"](around:{radius_meters},{lat},{lon});
  way["amenity"="townhall"](around:{radius_meters},{lat},{lon});
  node["amenity"="courthouse"](around:{radius_meters},{lat},{lon});
  way["amenity"="courthouse"](around:{radius_meters},{lat},{lon});
  node["amenity"="post_office"](around:{radius_meters},{lat},{lon});
  way["amenity"="post_office"](around:{radius_meters},{lat},{lon});
  node["office"="government"](around:{radius_meters},{lat},{lon});
  way["office"="government"](around:{radius_meters},{lat},{lon});
  node["building"="government"](around:{radius_meters},{lat},{lon});
  way["building"="government"](around:{radius_meters},{lat},{lon});
  node["government"](around:{radius_meters},{lat},{lon});
  way["government"](around:{radius_meters},{lat},{lon});
  node["landuse"="military"](around:{radius_meters},{lat},{lon});
  way["landuse"="military"](around:{radius_meters},{lat},{lon});
  node["amenity"="prison"](around:{radius_meters},{lat},{lon});
  way["amenity"="prison"](around:{radius_meters},{lat},{lon});

  // Schools
  node["amenity"="school"](around:{radius_meters},{lat},{lon});
  way["amenity"="school"](around:{radius_meters},{lat},{lon});
  node["amenity"="university"](around:{radius_meters},{lat},{lon});
  way["amenity"="university"](around:{radius_meters},{lat},{lon});
  node["amenity"="college"](around:{radius_meters},{lat},{lon});
  way["amenity"="college"](around:{radius_meters},{lat},{lon});

  // ==================== OTHER COMMERCIAL ====================
  // Hotels/Motels
  node["tourism"="hotel"](around:{radius_meters},{lat},{lon});
  way["tourism"="hotel"](around:{radius_meters},{lat},{lon});
  node["tourism"="motel"](around:{radius_meters},{lat},{lon});
  way["tourism"="motel"](around:{radius_meters},{lat},{lon});

  // Churches (large parking lots)
  node["amenity"="place_of_worship"](around:{radius_meters},{lat},{lon});
  way["amenity"="place_of_worship"](around:{radius_meters},{lat},{lon});

  // Funeral homes
  node["amenity"="funeral_hall"](around:{radius_meters},{lat},{lon});
  way["amenity"="funeral_hall"](around:{radius_meters},{lat},{lon});
  node["shop"="funeral_directors"](around:{radius_meters},{lat},{lon});
  way["shop"="funeral_directors"](around:{radius_meters},{lat},{lon});

  // Storage/rental
  node["amenity"="storage_rental"](around:{radius_meters},{lat},{lon});
  way["amenity"="storage_rental"](around:{radius_meters},{lat},{lon});
  node["shop"="rental"](around:{radius_meters},{lat},{lon});
  way["shop"="rental"](around:{radius_meters},{lat},{lon});

  // Vending/wholesale
  node["amenity"="vending"](around:{radius_meters},{lat},{lon});
  way["amenity"="vending"](around:{radius_meters},{lat},{lon});
  node["shop"="beverages"]["wholesale"="yes"](around:{radius_meters},{lat},{lon});
  way["shop"="beverages"]["wholesale"="yes"](around:{radius_meters},{lat},{lon});
);
out center meta;'''
        return query

    def _execute_overpass_query(self, query: str, max_retries: int = 3) -> dict:
        """Execute Overpass query with retry logic."""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.OVERPASS_URL,
                    data={'data': query},
                    headers={'User-Agent': 'HailTrackerPDR/2.0'},
                    timeout=120
                )

                if response.status_code == 429:
                    # Rate limited, wait and retry
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"Overpass rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Overpass timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(10)
            except Exception as e:
                logger.error(f"Overpass query error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)

        return {'elements': []}

    def _detect_category(self, tags: dict) -> str:
        """Detect business category from OSM tags using unified taxonomy."""
        # Use the unified taxonomy's detection function
        category = detect_category_from_tags(tags)
        # Normalize the key to ensure consistency
        return normalize_category_key(category)

    def _extract_business(self, element: dict) -> Optional[dict]:
        """Extract a clean business object from an OSM element."""
        tags = element.get('tags', {})
        name = tags.get('name', '').strip()

        if not name:
            return None

        # Get coordinates
        if element.get('type') == 'way':
            lat = element.get('center', {}).get('lat', 0)
            lon = element.get('center', {}).get('lon', 0)
        else:
            lat = element.get('lat', 0)
            lon = element.get('lon', 0)

        if not lat or not lon:
            return None

        # Build full address
        addr_parts = []
        if tags.get('addr:housenumber'):
            addr_parts.append(tags['addr:housenumber'])
        if tags.get('addr:street'):
            addr_parts.append(tags['addr:street'])
        street_addr = ' '.join(addr_parts)

        city = tags.get('addr:city', '')
        state = tags.get('addr:state', '')
        zipcode = tags.get('addr:postcode', '')

        full_addr_parts = [street_addr]
        if city:
            full_addr_parts.append(city)
        if state:
            full_addr_parts.append(state)
        if zipcode:
            full_addr_parts.append(zipcode)
        full_address = ', '.join(p for p in full_addr_parts if p)

        # Get contact info
        phone = (tags.get('phone') or tags.get('contact:phone') or
                 tags.get('telephone') or '')
        website = (tags.get('website') or tags.get('contact:website') or
                   tags.get('url') or '')
        email = (tags.get('email') or tags.get('contact:email') or '')

        # Clean phone number
        if phone:
            phone = re.sub(r'[^\d+\-\(\)\s]', '', phone)

        # Detect category using unified taxonomy
        category = self._detect_category(tags)

        # Estimate vehicles using taxonomy
        est_vehicles = estimate_vehicles(category)

        # Get tier from taxonomy
        cat_config = CATEGORY_TAXONOMY.get(category, {})
        tier = cat_config.get('tier', 3)

        return {
            'name': name,
            'category': category,
            'address': full_address,
            'street': street_addr,
            'city': city,
            'state': state,
            'zip': zipcode,
            'phone': phone,
            'website': website,
            'email': email,
            'latitude': lat,
            'longitude': lon,
            'estimated_vehicles': est_vehicles,
            'tier': tier,
            'source': 'osm',
            'osm_id': f"{element.get('type', 'node')}_{element.get('id', '')}",
            'operator': tags.get('operator', ''),
            'brand': tags.get('brand', ''),
            'opening_hours': tags.get('opening_hours', ''),
        }

    def search_osm_comprehensive(self, lat: float, lon: float,
                                   radius_miles: float) -> List[dict]:
        """
        Search OSM for ALL business types within radius.

        Returns list of business dicts with full contact info.
        """
        radius_meters = int(radius_miles * 1609.34)

        logger.info(f"Searching OSM: ({lat:.4f}, {lon:.4f}) radius {radius_miles:.1f} mi ({radius_meters}m)")

        query = self._build_comprehensive_overpass_query(lat, lon, radius_meters)
        result = self._execute_overpass_query(query)

        elements = result.get('elements', [])
        logger.info(f"Overpass returned {len(elements)} elements")

        businesses = []
        seen_ids = set()

        for elem in elements:
            osm_id = f"{elem.get('type', 'node')}_{elem.get('id', '')}"
            if osm_id in seen_ids:
                continue
            seen_ids.add(osm_id)

            biz = self._extract_business(elem)
            if biz:
                businesses.append(biz)

        logger.info(f"Extracted {len(businesses)} businesses with names")

        return businesses

    def _geocode_address(self, address: str, city: str, state: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address using Nominatim.

        Returns (lat, lon) or None if not found.
        """
        if not address and not city:
            return None

        # Build search query
        query_parts = []
        if address:
            query_parts.append(address)
        if city:
            query_parts.append(city)
        if state:
            query_parts.append(state)
        query_parts.append('USA')

        query = ', '.join(query_parts)

        try:
            response = requests.get(
                self.NOMINATIM_URL,
                params={
                    'q': query,
                    'format': 'json',
                    'limit': 1,
                    'countrycodes': 'us',
                },
                headers={'User-Agent': 'HailTrackerPDR/2.0'},
                timeout=10
            )

            if response.ok:
                results = response.json()
                if results:
                    return (float(results[0]['lat']), float(results[0]['lon']))

        except Exception as e:
            logger.debug(f"Geocoding failed for '{query}': {e}")

        return None

    def _normalize_name(self, name: str) -> str:
        """Normalize business name for deduplication."""
        if not name:
            return ''
        # Remove common suffixes, punctuation, lowercase
        name = name.lower().strip()
        # Remove common business suffixes
        for suffix in [' llc', ' inc', ' corp', ' ltd', ' co', ' company', ' services', ' service']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        # Remove punctuation
        name = re.sub(r'[^\w\s]', '', name)
        # Collapse whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _names_similar(self, name1: str, name2: str, threshold: float = 0.8) -> bool:
        """Check if two business names are similar enough to be duplicates."""
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)

        if not n1 or not n2:
            return False

        # Exact match after normalization
        if n1 == n2:
            return True

        # Use sequence matcher for fuzzy matching
        ratio = SequenceMatcher(None, n1, n2).ratio()
        return ratio >= threshold

    def search_yellowpages(self, city: str, state: str, max_per_term: int = 1) -> List[dict]:
        """
        Search Yellow Pages for service businesses in a city.

        Args:
            city: City name
            state: State abbreviation (e.g., 'OK', 'TX')
            max_per_term: Max pages to scrape per search term

        Returns:
            List of business dicts
        """
        businesses = []
        seen_names = set()

        logger.info(f"Searching Yellow Pages for {city}, {state}")

        for search_term, our_category in self.YP_SEARCH_TERMS:
            try:
                results = self.yp_scraper.search(
                    city=city,
                    state=state,
                    search_term=search_term,
                    max_pages=max_per_term
                )

                for biz in results:
                    name_key = self._normalize_name(biz.get('name', ''))
                    if name_key and name_key not in seen_names:
                        seen_names.add(name_key)

                        businesses.append({
                            'name': biz.get('name', ''),
                            'category': our_category,
                            'address': biz.get('address', ''),
                            'city': biz.get('city', city),
                            'state': biz.get('state', state),
                            'zip': biz.get('zip', ''),
                            'phone': biz.get('phone', ''),
                            'website': biz.get('website', ''),
                            'email': '',
                            'latitude': 0,  # Will geocode later
                            'longitude': 0,
                            'estimated_vehicles': self.VEHICLE_ESTIMATES.get(our_category, 10),
                            'source': 'yellowpages',
                            'osm_id': f"yp_{name_key[:20]}_{len(businesses)}",
                        })

                # Rate limit between searches
                time.sleep(2)

            except Exception as e:
                logger.warning(f"Yellow Pages search failed for '{search_term}': {e}")
                continue

        logger.info(f"Yellow Pages found {len(businesses)} businesses in {city}, {state}")
        return businesses

    def search_bbb(self, city: str, state: str, max_per_category: int = 1) -> List[dict]:
        """
        Search BBB for accredited businesses in a city.

        Args:
            city: City name
            state: State abbreviation
            max_per_category: Max pages to scrape per category

        Returns:
            List of business dicts
        """
        businesses = []
        seen_names = set()

        logger.info(f"Searching BBB for {city}, {state}")

        for cat_slug, our_category in self.BBB_CATEGORIES:
            try:
                results = self.bbb_scraper.search(
                    city=city,
                    state=state,
                    category_slug=cat_slug,
                    max_pages=max_per_category
                )

                for biz in results:
                    name_key = self._normalize_name(biz.get('name', ''))
                    if name_key and name_key not in seen_names:
                        seen_names.add(name_key)

                        businesses.append({
                            'name': biz.get('name', ''),
                            'category': our_category,
                            'address': biz.get('address', ''),
                            'city': biz.get('city', city),
                            'state': biz.get('state', state),
                            'zip': biz.get('zip', ''),
                            'phone': biz.get('phone', ''),
                            'website': biz.get('website', ''),
                            'email': '',
                            'latitude': 0,  # Will geocode later
                            'longitude': 0,
                            'estimated_vehicles': self.VEHICLE_ESTIMATES.get(our_category, 10),
                            'source': 'bbb',
                            'osm_id': f"bbb_{name_key[:20]}_{len(businesses)}",
                            'bbb_accredited': True,
                        })

                # Rate limit between categories
                time.sleep(3)

            except Exception as e:
                logger.warning(f"BBB search failed for '{cat_slug}': {e}")
                continue

        logger.info(f"BBB found {len(businesses)} businesses in {city}, {state}")
        return businesses

    def _deduplicate_businesses(self, businesses: List[dict]) -> List[dict]:
        """
        Remove duplicate businesses across multiple sources.

        Keeps the one with most complete info (prefer OSM for coords).
        """
        if not businesses:
            return []

        unique = []
        seen_normalized = {}  # normalized_name -> index in unique

        for biz in businesses:
            name_key = self._normalize_name(biz.get('name', ''))
            if not name_key:
                continue

            # Check for exact normalized match
            if name_key in seen_normalized:
                idx = seen_normalized[name_key]
                existing = unique[idx]
                # Prefer OSM (has coords) or one with more info
                if biz.get('source') == 'osm' and existing.get('source') != 'osm':
                    unique[idx] = biz
                elif biz.get('phone') and not existing.get('phone'):
                    # Merge phone into existing
                    existing['phone'] = biz['phone']
                elif biz.get('website') and not existing.get('website'):
                    existing['website'] = biz['website']
                continue

            # Check for fuzzy match
            found_match = False
            for existing_name, idx in seen_normalized.items():
                if self._names_similar(name_key, existing_name, threshold=0.85):
                    found_match = True
                    existing = unique[idx]
                    # Prefer OSM (has coords)
                    if biz.get('source') == 'osm' and existing.get('source') != 'osm':
                        seen_normalized[name_key] = idx
                        unique[idx] = biz
                    break

            if not found_match:
                seen_normalized[name_key] = len(unique)
                unique.append(biz)

        return unique

    def _geocode_businesses(self, businesses: List[dict], swath_center: Tuple[float, float]) -> List[dict]:
        """
        Geocode businesses that don't have coordinates.

        Falls back to swath center if geocoding fails.
        """
        geocoded = []
        geocode_attempts = 0
        max_geocode = 50  # Limit geocoding calls per batch

        for biz in businesses:
            # Skip if already has valid coordinates
            if biz.get('latitude') and biz.get('longitude'):
                geocoded.append(biz)
                continue

            # Try to geocode
            coords = None
            if geocode_attempts < max_geocode:
                coords = self._geocode_address(
                    biz.get('address', ''),
                    biz.get('city', ''),
                    biz.get('state', '')
                )
                geocode_attempts += 1
                time.sleep(1)  # Nominatim rate limit

            if coords:
                biz['latitude'] = coords[0]
                biz['longitude'] = coords[1]
                geocoded.append(biz)
            else:
                # Skip businesses we can't locate
                logger.debug(f"Skipping {biz['name']} - no coordinates")

        return geocoded

    def get_swath_search_area(self, swath_polygon: dict) -> Optional[Tuple[float, float, float]]:
        """Calculate search area from swath polygon."""
        if swath_polygon.get('type') != 'Polygon':
            return None

        coords = swath_polygon.get('coordinates', [[]])[0]
        if len(coords) < 3:
            return None

        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        max_distance = 0
        for coord in coords:
            dist = GeoUtils.calculate_distance_miles(
                center_lat, center_lon, coord[1], coord[0]
            )
            max_distance = max(max_distance, dist)

        return (center_lat, center_lon, max_distance)

    def point_in_polygon(self, lat: float, lon: float, polygon: dict) -> bool:
        """Check if a point is inside a GeoJSON polygon using ray casting."""
        if polygon.get('type') != 'Polygon':
            return False

        coords = polygon.get('coordinates', [[]])[0]
        if len(coords) < 3:
            return False

        n = len(coords)
        inside = False

        p1_lon, p1_lat = coords[0]
        for i in range(1, n + 1):
            p2_lon, p2_lat = coords[i % n]
            if lat > min(p1_lat, p2_lat):
                if lat <= max(p1_lat, p2_lat):
                    if lon <= max(p1_lon, p2_lon):
                        if p1_lat != p2_lat:
                            xinters = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                        if p1_lon == p2_lon or lon <= xinters:
                            inside = not inside
            p1_lon, p1_lat = p2_lon, p2_lat

        return inside

    def load_swath_polygons(self, event_ids: List[int]) -> List[dict]:
        """Load swath polygons from database for given event IDs."""
        if not event_ids:
            return []

        conn = sqlite3.connect(self.crm_db_path)
        conn.row_factory = sqlite3.Row

        placeholders = ','.join('?' * len(event_ids))
        query = f"""
            SELECT id, event_name, event_date, max_hail_size,
                   center_lat, center_lon, swath_polygon
            FROM hail_events
            WHERE id IN ({placeholders})
              AND center_lat IS NOT NULL
              AND center_lon IS NOT NULL
        """

        cursor = conn.execute(query, event_ids)
        rows = cursor.fetchall()
        conn.close()

        swaths = []
        for row in rows:
            event_id = row['id']
            center_lat = row['center_lat']
            center_lon = row['center_lon']
            max_hail_size = row['max_hail_size'] or 1.0

            polygon = None
            is_synthetic = False

            if row['swath_polygon']:
                try:
                    geojson = json.loads(row['swath_polygon']) if isinstance(row['swath_polygon'], str) else row['swath_polygon']
                    if geojson and geojson.get('type') == 'Polygon':
                        polygon = geojson
                except (json.JSONDecodeError, TypeError):
                    pass

            if polygon is None:
                radius_miles = max(2.0, max_hail_size * 2.5)
                polygon = self._create_circle_polygon(center_lat, center_lon, radius_miles)
                is_synthetic = True

            event_name = row['event_name'] or ''
            city = event_name.split(',')[0].strip() if ',' in event_name else ''

            swaths.append({
                'event_id': event_id,
                'event_name': event_name,
                'event_date': row['event_date'],
                'city': city,
                'max_hail_size': max_hail_size,
                'center_lat': center_lat,
                'center_lon': center_lon,
                'polygon': polygon,
                'is_synthetic': is_synthetic,
            })

        return swaths

    def _create_circle_polygon(self, center_lat: float, center_lon: float,
                                radius_miles: float, num_points: int = 24) -> dict:
        """Create a circular GeoJSON polygon."""
        coords = []
        for i in range(num_points + 1):
            angle = (i / num_points) * 2 * math.pi
            point_lat, point_lon = GeoUtils.offset_position(
                center_lat, center_lon, radius_miles, math.degrees(angle)
            )
            coords.append([point_lon, point_lat])

        return {
            'type': 'Polygon',
            'coordinates': [coords]
        }

    def _get_cached_businesses(self, event_ids: List[int]) -> Tuple[List[dict], List[int]]:
        """
        Check cache for already-scraped events.

        Returns:
            Tuple of (cached_businesses, uncached_event_ids)
        """
        conn = sqlite3.connect(self.crm_db_path)
        conn.row_factory = sqlite3.Row

        placeholders = ','.join('?' * len(event_ids))

        # Get cached businesses
        cached = conn.execute(f'''
            SELECT * FROM swath_businesses
            WHERE event_id IN ({placeholders})
        ''', event_ids).fetchall()

        # Get which events have cached data
        cached_event_ids = set(row['event_id'] for row in cached)
        uncached_event_ids = [eid for eid in event_ids if eid not in cached_event_ids]

        conn.close()

        # Convert to dicts
        businesses = []
        for row in cached:
            businesses.append({
                'id': row['id'],
                'name': row['name'],
                'category': row['category'],
                'address': row['address'],
                'city': row['city'],
                'state': row['state'],
                'zip': row['zip'],
                'phone': row['phone'],
                'website': row['website'],
                'email': row['email'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'estimated_vehicles': row['estimated_vehicles'],
                'source': row['source'],
                'osm_id': row['osm_id'],
                'event_id': row['event_id'],
                'in_swath': bool(row['in_swath']),
                'added_to_crm': bool(row['added_to_crm']),
            })

        return businesses, uncached_event_ids

    def _save_businesses_to_cache(self, businesses: List[dict], event_id: int,
                                   storm_date: str):
        """Save discovered businesses to cache."""
        if not businesses:
            return

        conn = sqlite3.connect(self.crm_db_path)

        for biz in businesses:
            try:
                conn.execute('''
                    INSERT OR REPLACE INTO swath_businesses
                    (event_id, storm_date, osm_id, name, category, address, city,
                     state, zip, phone, website, email, latitude, longitude,
                     estimated_vehicles, source, in_swath)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id, storm_date, biz.get('osm_id', ''),
                    biz['name'], biz.get('category', 'other'), biz.get('address', ''),
                    biz.get('city', ''), biz.get('state', ''), biz.get('zip', ''),
                    biz.get('phone', ''), biz.get('website', ''), biz.get('email', ''),
                    biz.get('latitude', 0), biz.get('longitude', 0),
                    biz.get('estimated_vehicles', 10), biz.get('source', 'osm'),
                    1  # in_swath
                ))
            except Exception as e:
                logger.warning(f"Failed to cache business {biz['name']}: {e}")

        conn.commit()
        conn.close()
        logger.info(f"Cached {len(businesses)} businesses for event {event_id}")

    def _extract_city_state(self, event_name: str) -> Tuple[str, str]:
        """Extract city and state from event name like 'Oklahoma City, OK'."""
        if not event_name:
            return ('', '')

        parts = event_name.split(',')
        city = parts[0].strip() if len(parts) > 0 else ''
        state = parts[1].strip() if len(parts) > 1 else ''

        # Handle cases like "Norman, OK (Southwest)"
        if state and ' ' in state:
            state = state.split()[0]

        return (city, state)

    def discover_for_events(self, event_ids: List[int],
                            buffer_miles: float = 1.0,
                            force_refresh: bool = False,
                            sources: List[str] = None,
                            include_osm: bool = True,
                            include_yellowpages: bool = True,
                            include_bbb: bool = True) -> Dict:
        """
        Main discovery method using multiple data sources.

        Args:
            event_ids: List of hail event IDs to search
            buffer_miles: Extra buffer around swaths
            force_refresh: If True, ignore cache and re-scrape
            sources: List of source names to use. Options:
                     ['osm', 'foursquare', 'yelp', 'here', 'tomtom', 'google', 'yellowpages', 'bbb']
                     Default: ['osm', 'foursquare', 'yelp']
            include_osm: (legacy) Search OpenStreetMap
            include_yellowpages: (legacy) Search Yellow Pages
            include_bbb: (legacy) Search BBB

        Returns:
            Dict with businesses, stats, and metadata

        Recommended sources: ['osm', 'foursquare', 'yelp']
        - OSM: Free unlimited, good base coverage
        - Foursquare: 100k/month, excellent data
        - Yelp: 150k/month, best for service companies

        Additional sources: ['here', 'tomtom', 'google']
        - HERE: 250k/month, good backup
        - TomTom: 75k/month, decent coverage
        - Google: $200 credit, most complete but costs money
        """
        # Handle sources parameter (new style) or legacy bool params
        if sources is None:
            sources = []
            if include_osm:
                sources.append('osm')
            if include_yellowpages:
                sources.append('yellowpages')
            if include_bbb:
                sources.append('bbb')
            # Default to also include foursquare and yelp if available
            if self.foursquare.is_configured():
                sources.append('foursquare')
            if self.yelp.is_configured():
                sources.append('yelp')

        logger.info(f"Starting multi-source discovery for {len(event_ids)} events")
        logger.info(f"Sources: {sources}")

        all_businesses = []
        stats = {
            'total_found': 0,
            'cached': False,
            'from_cache': 0,
            'newly_scraped': 0,
            'osm_found': 0,
            'foursquare_found': 0,
            'yelp_found': 0,
            'here_found': 0,
            'tomtom_found': 0,
            'google_found': 0,
            'yellowpages_found': 0,
            'bbb_found': 0,
            'geocoded': 0,
            'duplicates_removed': 0,
            'final_in_swath': 0,
            'by_category': {},
            'by_source': {},
            'total_vehicles': 0,
            'events_processed': 0,
        }

        # Check cache first (unless force_refresh)
        uncached_event_ids = event_ids
        if not force_refresh:
            cached_businesses, uncached_event_ids = self._get_cached_businesses(event_ids)
            all_businesses.extend(cached_businesses)
            stats['from_cache'] = len(cached_businesses)
            if cached_businesses:
                stats['cached'] = True
                logger.info(f"Found {len(cached_businesses)} cached businesses")

        # Scrape uncached events
        if uncached_event_ids:
            swaths = self.load_swath_polygons(uncached_event_ids)
            logger.info(f"Scraping {len(swaths)} uncached swaths")

            # Track cities we've already scraped (for YP/BBB)
            scraped_cities = set()

            for swath in swaths:
                polygon = swath['polygon']
                search_area = self.get_swath_search_area(polygon)

                if not search_area:
                    continue

                center_lat, center_lon, max_radius = search_area
                search_radius_miles = max_radius + buffer_miles
                search_radius_meters = int(search_radius_miles * 1609.34)

                # Extract city/state for YP/BBB
                city, state = self._extract_city_state(swath.get('event_name', ''))
                city_key = f"{city}_{state}".lower()

                logger.info(f"Event {swath['event_id']}: {city}, {state} - {search_radius_miles:.1f} mi radius")

                # Collect all businesses from all sources for this swath
                swath_businesses_raw = []

                # 1. Search OSM (returns coordinates)
                if 'osm' in sources:
                    osm_results = self.search_osm_comprehensive(
                        center_lat, center_lon, search_radius_miles
                    )
                    stats['osm_found'] += len(osm_results)
                    swath_businesses_raw.extend(osm_results)
                    logger.info(f"  OSM: {len(osm_results)} businesses")

                # 2. Search Foursquare
                if 'foursquare' in sources and self.foursquare.is_configured():
                    try:
                        fs_results = self.foursquare.search_all_fleet_categories(
                            center_lat, center_lon, search_radius_meters
                        )
                        # Normalize field names
                        for biz in fs_results:
                            if 'latitude' not in biz and 'lat' in biz:
                                biz['latitude'] = biz.get('lat')
                            if 'longitude' not in biz and 'lon' in biz:
                                biz['longitude'] = biz.get('lon')
                            if 'longitude' not in biz and 'longitude' in biz:
                                pass  # already correct
                        stats['foursquare_found'] += len(fs_results)
                        swath_businesses_raw.extend(fs_results)
                        logger.info(f"  Foursquare: {len(fs_results)} businesses")
                    except Exception as e:
                        logger.warning(f"  Foursquare error: {e}")

                # 3. Search Yelp
                if 'yelp' in sources and self.yelp.is_configured():
                    try:
                        yelp_results = self.yelp.search_all_categories(
                            center_lat, center_lon, search_radius_meters
                        )
                        stats['yelp_found'] += len(yelp_results)
                        swath_businesses_raw.extend(yelp_results)
                        logger.info(f"  Yelp: {len(yelp_results)} businesses")
                    except Exception as e:
                        logger.warning(f"  Yelp error: {e}")

                # 4. Search HERE
                if 'here' in sources and self.here.is_configured():
                    try:
                        here_results = self.here.search_all_categories(
                            center_lat, center_lon, search_radius_meters
                        )
                        stats['here_found'] += len(here_results)
                        swath_businesses_raw.extend(here_results)
                        logger.info(f"  HERE: {len(here_results)} businesses")
                    except Exception as e:
                        logger.warning(f"  HERE error: {e}")

                # 5. Search TomTom
                if 'tomtom' in sources and self.tomtom.is_configured():
                    try:
                        tt_results = self.tomtom.search_all_categories(
                            center_lat, center_lon, search_radius_meters
                        )
                        stats['tomtom_found'] += len(tt_results)
                        swath_businesses_raw.extend(tt_results)
                        logger.info(f"  TomTom: {len(tt_results)} businesses")
                    except Exception as e:
                        logger.warning(f"  TomTom error: {e}")

                # 6. Search Google (use sparingly - costs money)
                if 'google' in sources and self.google.is_configured():
                    try:
                        google_results = self.google.search_all_categories(
                            center_lat, center_lon, search_radius_meters
                        )
                        stats['google_found'] += len(google_results)
                        swath_businesses_raw.extend(google_results)
                        logger.info(f"  Google: {len(google_results)} businesses")
                    except Exception as e:
                        logger.warning(f"  Google error: {e}")

                # 7. Search Yellow Pages (for service businesses)
                if 'yellowpages' in sources and city and state and city_key not in scraped_cities:
                    yp_results = self.search_yellowpages(city, state, max_per_term=1)
                    stats['yellowpages_found'] += len(yp_results)
                    swath_businesses_raw.extend(yp_results)
                    logger.info(f"  Yellow Pages: {len(yp_results)} businesses")

                # 8. Search BBB (for accredited businesses)
                if 'bbb' in sources and city and state and city_key not in scraped_cities:
                    bbb_results = self.search_bbb(city, state, max_per_category=1)
                    stats['bbb_found'] += len(bbb_results)
                    swath_businesses_raw.extend(bbb_results)
                    logger.info(f"  BBB: {len(bbb_results)} businesses")

                # Mark city as scraped (no need to re-scrape YP/BBB for same city)
                if city and state:
                    scraped_cities.add(city_key)

                # 9. Deduplicate across sources (using new deduplication engine)
                pre_dedup = len(swath_businesses_raw)
                swath_businesses_deduped = deduplicate_businesses(swath_businesses_raw, merge_data=True)
                stats['duplicates_removed'] += (pre_dedup - len(swath_businesses_deduped))
                logger.info(f"  After dedup: {len(swath_businesses_deduped)} (removed {pre_dedup - len(swath_businesses_deduped)})")

                # 10. Geocode businesses without coordinates
                businesses_needing_geocode = [b for b in swath_businesses_deduped if not b.get('latitude')]
                if businesses_needing_geocode:
                    logger.info(f"  Geocoding {len(businesses_needing_geocode)} businesses...")
                    swath_businesses_geocoded = self._geocode_businesses(
                        swath_businesses_deduped,
                        (center_lat, center_lon)
                    )
                    geocoded_count = sum(1 for b in swath_businesses_geocoded
                                        if b.get('latitude') and b.get('source') not in ['osm', 'foursquare', 'yelp', 'here', 'tomtom', 'google'])
                    stats['geocoded'] += geocoded_count
                else:
                    swath_businesses_geocoded = swath_businesses_deduped

                # 11. Filter to swath polygon (point-in-polygon)
                swath_businesses_final = []
                seen_names = set(b['name'].lower() for b in all_businesses)

                for biz in swath_businesses_geocoded:
                    # Must have coordinates
                    if not biz.get('latitude') or not biz.get('longitude'):
                        continue

                    # Must be inside swath polygon
                    if not self.point_in_polygon(biz['latitude'], biz['longitude'], polygon):
                        continue

                    # Skip duplicates from previous events
                    name_key = biz['name'].lower()
                    if name_key in seen_names:
                        continue

                    seen_names.add(name_key)
                    biz['event_id'] = swath['event_id']
                    biz['hail_date'] = swath['event_date']
                    biz['hail_size'] = swath['max_hail_size']
                    swath_businesses_final.append(biz)
                    all_businesses.append(biz)

                stats['final_in_swath'] += len(swath_businesses_final)
                logger.info(f"  Final in swath: {len(swath_businesses_final)} businesses")

                # Cache results
                self._save_businesses_to_cache(
                    swath_businesses_final,
                    swath['event_id'],
                    swath['event_date']
                )

                stats['newly_scraped'] += len(swath_businesses_final)
                stats['events_processed'] += 1

                # Rate limit between events
                time.sleep(1)

        # Calculate final stats
        stats['total_found'] = len(all_businesses)

        for biz in all_businesses:
            cat = biz.get('category', 'other')
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            stats['total_vehicles'] += biz.get('estimated_vehicles', 10)

            # Count by source
            source = biz.get('source', 'unknown')
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1

            # Add tier if not present
            if 'tier' not in biz:
                tier = 3
                for t, cats in self.TIER_MAP.items():
                    if cat in cats:
                        tier = t
                        break
                biz['tier'] = tier

        # Sort by tier (1 first) then by estimated vehicles (high first)
        all_businesses.sort(key=lambda x: (x.get('tier', 3), -x.get('estimated_vehicles', 0)))

        logger.info(f"Discovery complete: {len(all_businesses)} total businesses")
        logger.info(f"Final by source: {stats['by_source']}")

        return {
            'success': True,
            'businesses': all_businesses,
            'stats': stats,
        }

    def get_api_status(self) -> Dict:
        """Get the configuration status of all APIs."""
        return {
            'foursquare': {
                'configured': self.foursquare.is_configured(),
                'free_tier': '100,000 calls/month',
            },
            'yelp': {
                'configured': self.yelp.is_configured(),
                'free_tier': '5,000 calls/day',
            },
            'here': {
                'configured': self.here.is_configured(),
                'free_tier': '250,000 calls/month',
            },
            'tomtom': {
                'configured': self.tomtom.is_configured(),
                'free_tier': '2,500 calls/day',
            },
            'google': {
                'configured': self.google.is_configured(),
                'free_tier': '$200/month credit',
            },
            'osm': {
                'configured': True,  # Always available
                'free_tier': 'Unlimited',
            },
        }

    def add_to_crm(self, business_id: int) -> bool:
        """Mark a business as added to CRM."""
        try:
            conn = sqlite3.connect(self.crm_db_path)
            conn.execute('''
                UPDATE swath_businesses
                SET added_to_crm = 1
                WHERE id = ?
            ''', (business_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to mark business {business_id} as added to CRM: {e}")
            return False

    def clear_cache(self, event_ids: List[int] = None):
        """Clear cached businesses (optionally for specific events)."""
        conn = sqlite3.connect(self.crm_db_path)
        if event_ids:
            placeholders = ','.join('?' * len(event_ids))
            conn.execute(f'DELETE FROM swath_businesses WHERE event_id IN ({placeholders})', event_ids)
        else:
            conn.execute('DELETE FROM swath_businesses')
        conn.commit()
        conn.close()
        logger.info(f"Cleared cache for {len(event_ids) if event_ids else 'all'} events")
