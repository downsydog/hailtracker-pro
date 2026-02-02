"""
Hybrid Business Discovery Strategy
===================================
Different strategies for different APIs to minimize requests.

OSM:     ONE bounding box query for ALL swaths (no tiles, no per-swath)
BBB:     Query by CITY (3-5 cities, not 1373 tiles)
YellowPages: Query by CITY
Manta:   Query by CITY
Google:  TILES (future - needed for 60 result limit)

BEFORE: 1373 tile queries = 45+ minutes
AFTER:  1 OSM query + city queries = ~60 seconds
"""

import json
import sqlite3
import logging
import time
import re
import hashlib
from typing import List, Dict, Tuple, Optional, Set
from pathlib import Path
from datetime import datetime
import requests

logger = logging.getLogger('FastDiscovery')

# Import scrapers for city-based queries
try:
    from src.fleet.scrapers.bbb import BBBScraper
    from src.fleet.scrapers.yellowpages import YellowPagesScraper
    from src.fleet.scrapers.manta import MantaScraper
    from src.fleet.scrapers.geocoding import GeocodingService
    SCRAPERS_AVAILABLE = True
except ImportError:
    SCRAPERS_AVAILABLE = False
    logger.warning("Scrapers not available - OSM only mode")


class FastOverpassClient:
    """
    Optimized Overpass client with minimal delays and server rotation.
    """

    SERVERS = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
        'https://overpass.openstreetmap.ru/api/interpreter',
    ]

    def __init__(self):
        self.current_server_index = 0
        self.failed_servers = set()
        self.last_request_time = 0
        self.min_delay = 0.5

    def get_next_server(self) -> str:
        available = [s for i, s in enumerate(self.SERVERS) if i not in self.failed_servers]
        if not available:
            self.failed_servers.clear()
            available = self.SERVERS
        server = available[self.current_server_index % len(available)]
        self.current_server_index += 1
        return server

    def query(self, overpass_query: str, max_retries: int = 3, timeout: int = 90) -> dict:
        """Execute query with retry and server rotation."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

        for attempt in range(max_retries):
            server = self.get_next_server()
            server_name = server.split('/')[2][:20]

            try:
                start = time.time()
                print(f"[OSM] Query attempt {attempt + 1}/{max_retries} on {server_name}...")

                response = requests.post(
                    server,
                    data={'data': overpass_query},
                    timeout=timeout,
                    headers={'User-Agent': 'HailTrackerPDR/2.0'}
                )

                self.last_request_time = time.time()
                query_time = time.time() - start

                if response.status_code == 200:
                    data = response.json()
                    elem_count = len(data.get('elements', []))
                    print(f"[OSM] Success: {elem_count} elements in {query_time:.1f}s")
                    return data

                elif response.status_code == 429:
                    print(f"[OSM] Rate limited on {server_name}")
                    idx = self.SERVERS.index(server) if server in self.SERVERS else -1
                    if idx >= 0:
                        self.failed_servers.add(idx)
                    time.sleep(2)

                elif response.status_code == 504:
                    print(f"[OSM] Timeout on {server_name}")
                    idx = self.SERVERS.index(server) if server in self.SERVERS else -1
                    if idx >= 0:
                        self.failed_servers.add(idx)

                else:
                    print(f"[OSM] Error {response.status_code}")

            except requests.Timeout:
                print(f"[OSM] Request timeout on {server_name}")
                idx = self.SERVERS.index(server) if server in self.SERVERS else -1
                if idx >= 0:
                    self.failed_servers.add(idx)

            except Exception as e:
                print(f"[OSM] Error: {e}")

        print(f"[OSM] All retries failed")
        return {}


# Global client
_fast_client = None

def get_fast_client() -> FastOverpassClient:
    global _fast_client
    if _fast_client is None:
        _fast_client = FastOverpassClient()
    return _fast_client


class FastSwathDiscovery:
    """
    Hybrid discovery - ONE OSM query for all swaths combined + city-based queries.

    OSM: 1 combined bounding box query
    YP/BBB/Manta: Query by city (priority categories only)

    28 swaths = 1 OSM query + ~10 city queries = ~60 seconds
    vs tile-based: 1373 API calls = 45+ minutes
    """

    VEHICLE_ESTIMATES = {
        'car_dealership': 150, 'car_rental': 80, 'body_shop': 25,
        'hospital': 250, 'clinic': 40, 'school': 100, 'university': 300,
        'police': 40, 'fire_station': 25, 'government': 75,
        'hotel': 60, 'church': 50, 'landscaping': 15, 'hvac': 12,
        'plumbing': 10, 'electrical': 10, 'roofing': 8, 'contractor': 15,
        'pest_control': 8, 'moving': 20, 'courier': 25, 'logistics': 50,
        'default': 10
    }

    # Priority categories for city-based scrapers (fewer = faster)
    PRIORITY_CATEGORIES_YP = [
        'car dealers', 'landscaping', 'pest control', 'hvac',
        'roofing contractors', 'plumbers', 'moving companies'
    ]

    PRIORITY_CATEGORIES_BBB = [
        'auto-dealers-new-cars', 'landscape-contractors', 'pest-control-services',
        'air-conditioning-contractors-systems', 'roofing-contractors', 'plumbers'
    ]

    PRIORITY_CATEGORIES_MANTA = [
        'new car dealers', 'landscaping services', 'pest control',
        'hvac contractors', 'roofing contractors', 'plumbing contractors'
    ]

    def __init__(self, db_path: str = None):
        data_dir = Path(__file__).parent.parent.parent / 'data'
        if db_path is None:
            db_path = str(data_dir / 'hailtracker_crm.db')
        self.db_path = db_path
        self._init_cache()

        # Initialize scrapers if available
        self.scrapers_enabled = SCRAPERS_AVAILABLE
        if self.scrapers_enabled:
            self.geocoder = GeocodingService(db_path=db_path)
            self.yp_scraper = YellowPagesScraper(db_path=db_path)
            self.bbb_scraper = BBBScraper(db_path=db_path)
            self.manta_scraper = MantaScraper(db_path=db_path)

    def _init_cache(self):
        """Initialize cache table."""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS swath_discovery_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                swath_hash TEXT UNIQUE,
                business_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_swath_cache_hash ON swath_discovery_cache(swath_hash)')
        conn.commit()
        conn.close()

    def _get_combined_hash(self, swaths: List[dict]) -> str:
        """Generate hash for all swaths combined."""
        all_coords = []
        for swath in swaths:
            coords = self._extract_coords(swath)
            if coords:
                all_coords.extend(coords)
        if not all_coords:
            return ""
        coord_str = json.dumps(sorted(all_coords), sort_keys=True)
        return hashlib.md5(coord_str.encode()).hexdigest()[:16]

    def _extract_coords(self, geojson: dict) -> Optional[List]:
        """Extract coordinates from GeoJSON."""
        try:
            if geojson.get('type') == 'Polygon':
                return geojson['coordinates'][0]
            elif geojson.get('type') == 'Feature':
                return geojson['geometry']['coordinates'][0]
            elif 'polygon' in geojson and geojson['polygon'].get('type') == 'Polygon':
                return geojson['polygon']['coordinates'][0]
        except:
            pass
        return None

    def _get_cached(self, cache_hash: str) -> Optional[List[Dict]]:
        """Get cached businesses."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('''
                SELECT business_data FROM swath_discovery_cache
                WHERE swath_hash = ?
                AND created_at > datetime('now', '-7 days')
            ''', (cache_hash,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
        return None

    def _set_cache(self, cache_hash: str, businesses: List[Dict]):
        """Cache businesses."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT OR REPLACE INTO swath_discovery_cache (swath_hash, business_data)
                VALUES (?, ?)
            ''', (cache_hash, json.dumps(businesses)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Cache write error: {e}")

    def _reverse_geocode(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Reverse geocode coordinates to get city/state.
        Uses Nominatim with caching.
        """
        try:
            # Check cache first
            cache_key = f"reverse_{lat:.3f}_{lon:.3f}"
            cached = self._get_cached(cache_key)
            if cached:
                return cached[0] if cached else None

            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 10,  # City level
            }
            headers = {'User-Agent': 'HailTrackerPDR/2.0'}

            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.ok:
                data = response.json()
                address = data.get('address', {})
                result = {
                    'city': address.get('city') or address.get('town') or address.get('county', ''),
                    'state': address.get('state', ''),
                    'country': address.get('country', ''),
                }
                # Cache for 30 days
                self._set_cache(cache_key, [result])
                return result
        except Exception as e:
            logger.debug(f"Reverse geocode error: {e}")
        return None

    def _get_cities_from_swaths(self, swaths: List[dict]) -> List[Dict]:
        """
        Get unique cities covered by swaths using reverse geocoding.
        Only samples a few points to minimize API calls.
        """
        cities = {}  # city_state -> {city, state}

        # Get centroid of each swath
        for swath in swaths[:10]:  # Limit to 10 swaths for speed
            coords = self._extract_coords(swath)
            if not coords or len(coords) < 3:
                continue

            # Calculate centroid
            lats = [c[1] for c in coords]
            lons = [c[0] for c in coords]
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)

            # Reverse geocode
            location = self._reverse_geocode(center_lat, center_lon)
            if location and location.get('city'):
                key = f"{location['city']}_{location['state']}"
                if key not in cities:
                    cities[key] = location
                    print(f"[FastDiscovery] Found city: {location['city']}, {location['state']}")

            # Rate limit for Nominatim
            time.sleep(1.1)

        return list(cities.values())

    def _query_city_sources(
        self,
        cities: List[Dict],
        include_yp: bool = True,
        include_bbb: bool = True,
        include_manta: bool = True,
        max_pages: int = 1
    ) -> Tuple[List[Dict], Dict]:
        """
        Query Yellow Pages, BBB, and Manta by city.
        Returns businesses and stats.
        """
        all_businesses = []
        stats = {'yp': 0, 'bbb': 0, 'manta': 0}

        if not self.scrapers_enabled:
            print("[FastDiscovery] Scrapers not available - skipping city sources")
            return all_businesses, stats

        for city_info in cities:
            city = city_info.get('city', '')
            state = city_info.get('state', '')

            if not city or not state:
                continue

            # Extract state abbreviation if full name
            state_abbr = state[:2].upper() if len(state) == 2 else self._state_to_abbr(state)

            print(f"\n[FastDiscovery] Querying city sources for {city}, {state_abbr}...")

            # Yellow Pages
            if include_yp:
                try:
                    for category in self.PRIORITY_CATEGORIES_YP[:4]:  # Limit categories
                        print(f"  [YP] {category}...")
                        results = self.yp_scraper.search(city, state_abbr, category, max_pages=max_pages)
                        for biz in results:
                            biz['source'] = 'YellowPages'
                        all_businesses.extend(results)
                        stats['yp'] += len(results)
                except Exception as e:
                    print(f"  [YP] Error: {e}")

            # BBB
            if include_bbb:
                try:
                    for category in self.PRIORITY_CATEGORIES_BBB[:4]:
                        print(f"  [BBB] {category}...")
                        results = self.bbb_scraper.search(city, state_abbr, category, max_pages=max_pages)
                        for biz in results:
                            biz['source'] = 'BBB'
                        all_businesses.extend(results)
                        stats['bbb'] += len(results)
                except Exception as e:
                    print(f"  [BBB] Error: {e}")

            # Manta
            if include_manta:
                try:
                    for category in self.PRIORITY_CATEGORIES_MANTA[:4]:
                        print(f"  [Manta] {category}...")
                        results = self.manta_scraper.search(city, state_abbr, category, max_pages=max_pages)
                        for biz in results:
                            biz['source'] = 'Manta'
                        all_businesses.extend(results)
                        stats['manta'] += len(results)
                except Exception as e:
                    print(f"  [Manta] Error: {e}")

        print(f"\n[FastDiscovery] City sources: YP={stats['yp']}, BBB={stats['bbb']}, Manta={stats['manta']}")
        return all_businesses, stats

    def _geocode_businesses(self, businesses: List[Dict], swath_polygons: List) -> List[Dict]:
        """
        Geocode businesses that don't have coordinates and filter to swaths.
        """
        if not self.scrapers_enabled:
            return []

        geocoded = []
        for biz in businesses:
            # Skip if already has coordinates
            if biz.get('latitude') and biz.get('longitude'):
                lat, lon = biz['latitude'], biz['longitude']
            else:
                # Try to geocode
                coords = self.geocoder.geocode_business(biz)
                if not coords:
                    continue
                lat, lon = coords
                biz['latitude'] = lat
                biz['longitude'] = lon

            # Check if in any swath polygon
            for polygon in swath_polygons:
                if self._point_in_polygon(lat, lon, polygon):
                    geocoded.append(biz)
                    break

        return geocoded

    def _state_to_abbr(self, state_name: str) -> str:
        """Convert state name to abbreviation."""
        states = {
            'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
            'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
            'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
            'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
            'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
            'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
            'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
            'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
            'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
            'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
            'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
            'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
            'Wisconsin': 'WI', 'Wyoming': 'WY'
        }
        return states.get(state_name, state_name[:2].upper())

    def discover_for_swaths(
        self,
        swaths: List[dict],
        use_cache: bool = True,
        include_osm: bool = True,
        include_yp: bool = True,
        include_bbb: bool = True,
        include_manta: bool = True
    ) -> Dict:
        """
        Discover businesses using HYBRID strategy.

        OSM: ONE bounding box query for ALL swaths (returns coords)
        YP/BBB/Manta: Query by city (needs geocoding)
        Result: 28 swaths = 1 OSM + ~10 city queries = ~60 seconds
        """
        total_start = time.time()

        city_sources_enabled = include_yp or include_bbb or include_manta

        print(f"\n{'='*60}")
        print(f"[FastDiscovery] HYBRID STRATEGY")
        print(f"[FastDiscovery] Total swaths: {len(swaths)}")
        print(f"[FastDiscovery] OSM: {include_osm}, YP: {include_yp}, BBB: {include_bbb}, Manta: {include_manta}")
        print(f"{'='*60}\n")

        stats = {
            'swaths_total': len(swaths),
            'osm_queries': 0,
            'osm_found': 0,
            'yp_found': 0,
            'bbb_found': 0,
            'manta_found': 0,
            'total_elements': 0,
            'swaths_from_cache': 0,
            'by_category': {},
            'by_source': {},
        }

        # Check cache first (for entire query)
        cache_hash = self._get_combined_hash(swaths)
        if use_cache and cache_hash:
            cached = self._get_cached(cache_hash)
            if cached is not None:
                print(f"[FastDiscovery] CACHE HIT: {len(cached)} businesses from cache")
                stats['swaths_from_cache'] = len(swaths)

                # Add metadata
                for biz in cached:
                    cat = biz.get('category', 'other')
                    stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1

                stats['total_found'] = len(cached)
                stats['total_vehicles'] = sum(b.get('estimated_vehicles', 10) for b in cached)

                total_time = time.time() - total_start
                print(f"[FastDiscovery] COMPLETE from cache in {total_time:.1f}s")

                return {
                    'success': True,
                    'businesses': cached,
                    'stats': stats,
                    'timing': {'total_seconds': round(total_time, 1), 'per_swath_avg': 0}
                }

        # Collect all coordinates for combined bounding box
        all_lats = []
        all_lons = []
        swath_polygons = []  # For point-in-polygon filtering

        for swath in swaths:
            coords = self._extract_coords(swath)
            if coords and len(coords) >= 3:
                swath_polygons.append(coords)
                for coord in coords:
                    all_lons.append(coord[0])
                    all_lats.append(coord[1])

        if not all_lats:
            print("[FastDiscovery] No valid swath coordinates")
            return {'success': True, 'businesses': [], 'stats': stats, 'timing': {'total_seconds': 0}}

        # Calculate combined bounding box with small buffer
        min_lat = min(all_lats) - 0.01
        max_lat = max(all_lats) + 0.01
        min_lon = min(all_lons) - 0.01
        max_lon = max(all_lons) + 0.01

        print(f"[FastDiscovery] Combined bounding box:")
        print(f"  SW: ({min_lat:.4f}, {min_lon:.4f})")
        print(f"  NE: ({max_lat:.4f}, {max_lon:.4f})")

        all_businesses = []
        osm_time = 0
        city_time = 0

        # ========== STEP 1: OSM Query ==========
        if include_osm:
            osm_start = time.time()
            osm_businesses = self._query_osm_combined(min_lat, min_lon, max_lat, max_lon)
            osm_time = time.time() - osm_start
            stats['osm_queries'] = 1
            stats['total_elements'] = len(osm_businesses)

            print(f"[FastDiscovery] OSM query returned {len(osm_businesses)} businesses in {osm_time:.1f}s")

            # Filter OSM results to swath polygons
            for biz in osm_businesses:
                lat = biz.get('latitude', 0)
                lon = biz.get('longitude', 0)
                for polygon in swath_polygons:
                    if self._point_in_polygon(lat, lon, polygon):
                        biz['source'] = 'OSM'
                        all_businesses.append(biz)
                        stats['osm_found'] += 1
                        break

            print(f"[FastDiscovery] OSM in swaths: {stats['osm_found']}")

        # ========== STEP 2: City-Based Sources (YP, BBB, Manta) ==========
        if city_sources_enabled and self.scrapers_enabled:
            city_start = time.time()

            # Get cities from swaths via reverse geocoding
            print(f"\n[FastDiscovery] Finding cities in swaths...")
            cities = self._get_cities_from_swaths(swaths)
            print(f"[FastDiscovery] Found {len(cities)} unique cities")

            if cities:
                # Query city-based sources
                city_businesses, city_stats = self._query_city_sources(
                    cities,
                    include_yp=include_yp,
                    include_bbb=include_bbb,
                    include_manta=include_manta,
                    max_pages=1
                )

                stats['yp_found'] = city_stats['yp']
                stats['bbb_found'] = city_stats['bbb']
                stats['manta_found'] = city_stats['manta']

                # Geocode and filter to swaths
                print(f"\n[FastDiscovery] Geocoding {len(city_businesses)} city-source businesses...")
                geocoded = self._geocode_businesses(city_businesses, swath_polygons)
                print(f"[FastDiscovery] {len(geocoded)} businesses geocoded and in swaths")

                all_businesses.extend(geocoded)

            city_time = time.time() - city_start
            print(f"[FastDiscovery] City sources completed in {city_time:.1f}s")

        # ========== STEP 3: Deduplicate and Finalize ==========
        print(f"\n[FastDiscovery] Total before dedup: {len(all_businesses)}")

        # Deduplicate
        unique = self._deduplicate(all_businesses)
        stats['duplicates_removed'] = len(all_businesses) - len(unique)

        print(f"[FastDiscovery] After dedup: {len(unique)} (removed {stats['duplicates_removed']})")

        # Add metadata
        for biz in unique:
            cat = biz.get('category', 'other')
            source = biz.get('source', 'unknown')
            if 'tier' not in biz:
                biz['tier'] = self._get_tier(cat)
            if 'estimated_vehicles' not in biz:
                biz['estimated_vehicles'] = self.VEHICLE_ESTIMATES.get(cat, 10)
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1

        # Sort by tier then vehicles
        unique.sort(key=lambda x: (x.get('tier', 3), -x.get('estimated_vehicles', 0)))

        stats['total_found'] = len(unique)
        stats['total_vehicles'] = sum(b.get('estimated_vehicles', 10) for b in unique)

        # Cache results
        if cache_hash:
            self._set_cache(cache_hash, unique)

        total_time = time.time() - total_start

        print(f"\n{'='*60}")
        print(f"[FastDiscovery] COMPLETE in {total_time:.1f}s")
        print(f"[FastDiscovery] Sources: OSM={stats['osm_found']}, YP={stats['yp_found']}, BBB={stats['bbb_found']}, Manta={stats['manta_found']}")
        print(f"[FastDiscovery] Total businesses in swaths: {stats['total_found']}")
        print(f"[FastDiscovery] Est. vehicles: {stats['total_vehicles']}")
        print(f"{'='*60}\n")

        return {
            'success': True,
            'businesses': unique,
            'stats': stats,
            'timing': {
                'total_seconds': round(total_time, 1),
                'osm_seconds': round(osm_time, 1),
                'city_seconds': round(city_time, 1),
            }
        }

    def _query_osm_combined(self, min_lat: float, min_lon: float,
                            max_lat: float, max_lon: float) -> List[Dict]:
        """
        Query OSM for ALL fleet-relevant businesses in combined bounding box.

        ONE query for all swaths instead of 1373 tile queries.
        Uses bbox syntax: (min_lat,min_lon,max_lat,max_lon)
        """
        # Comprehensive query for all fleet categories
        query = f'''[out:json][timeout:90];
(
  // Car dealerships and rentals
  node["shop"~"car|car_dealer|car_repair|car_parts"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["shop"~"car|car_dealer|car_repair"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["amenity"="car_rental"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="car_rental"]({min_lat},{min_lon},{max_lat},{max_lon});

  // Institutions with vehicle fleets
  node["amenity"="hospital"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="hospital"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["amenity"~"clinic|doctors|dentist"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["amenity"="police"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="police"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["amenity"="fire_station"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="fire_station"]({min_lat},{min_lon},{max_lat},{max_lon});

  // Schools and universities
  node["amenity"="school"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="school"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["amenity"="university"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="university"]({min_lat},{min_lon},{max_lat},{max_lon});

  // Service businesses (craft trades)
  node["craft"]({min_lat},{min_lon},{max_lat},{max_lon});

  // Offices and companies
  node["office"~"company|government|insurance"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["office"~"company|government"]({min_lat},{min_lon},{max_lat},{max_lon});

  // Hotels and lodging
  node["tourism"="hotel"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["tourism"="hotel"]({min_lat},{min_lon},{max_lat},{max_lon});
  node["tourism"="motel"]({min_lat},{min_lon},{max_lat},{max_lon});

  // Churches (often have buses/vans)
  node["amenity"="place_of_worship"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["amenity"="place_of_worship"]({min_lat},{min_lon},{max_lat},{max_lon});

  // Fuel stations and car washes
  node["amenity"~"fuel|car_wash"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out center;'''

        client = get_fast_client()
        data = client.query(query, max_retries=3, timeout=90)

        if not data:
            return []

        elements = data.get('elements', [])
        businesses = []

        for elem in elements:
            biz = self._parse_element(elem)
            if biz:
                businesses.append(biz)

        return businesses

    def _parse_element(self, elem: dict) -> Optional[Dict]:
        """Parse OSM element into business dict."""
        tags = elem.get('tags', {})
        name = tags.get('name', '').strip()

        if not name:
            return None

        # Get coordinates
        if elem.get('type') == 'way':
            lat = elem.get('center', {}).get('lat', 0)
            lon = elem.get('center', {}).get('lon', 0)
        else:
            lat = elem.get('lat', 0)
            lon = elem.get('lon', 0)

        if not lat or not lon:
            return None

        # Build address
        addr_parts = []
        if tags.get('addr:housenumber'):
            addr_parts.append(tags['addr:housenumber'])
        if tags.get('addr:street'):
            addr_parts.append(tags['addr:street'])
        address = ' '.join(addr_parts)

        # Detect category
        category = self._detect_category(tags)

        return {
            'name': name,
            'category': category,
            'address': address,
            'city': tags.get('addr:city', ''),
            'state': tags.get('addr:state', ''),
            'zip': tags.get('addr:postcode', ''),
            'phone': tags.get('phone') or tags.get('contact:phone', ''),
            'website': tags.get('website') or tags.get('contact:website', ''),
            'email': tags.get('email') or tags.get('contact:email', ''),
            'latitude': lat,
            'longitude': lon,
            'source': 'osm',
            'osm_id': f"{elem.get('type', 'node')}_{elem.get('id', '')}",
        }

    def _detect_category(self, tags: dict) -> str:
        """Detect business category from OSM tags."""
        shop = tags.get('shop', '')
        amenity = tags.get('amenity', '')
        craft = tags.get('craft', '').lower()
        tourism = tags.get('tourism', '')
        office = tags.get('office', '')

        if shop in ['car', 'car_dealer']:
            return 'car_dealership'
        if amenity == 'car_rental':
            return 'car_rental'
        if shop == 'car_repair' or 'body' in craft or 'car' in craft:
            return 'body_shop'
        if amenity == 'hospital':
            return 'hospital'
        if amenity in ['clinic', 'doctors', 'dentist']:
            return 'clinic'
        if amenity == 'police':
            return 'police'
        if amenity == 'fire_station':
            return 'fire_station'
        if amenity == 'school':
            return 'school'
        if amenity == 'university':
            return 'university'
        if tourism in ['hotel', 'motel']:
            return 'hotel'
        if amenity == 'place_of_worship':
            return 'church'
        if office == 'government':
            return 'government'
        if office in ['company', 'insurance']:
            return 'contractor'

        # Craft trades
        if 'hvac' in craft or 'heating' in craft or 'air_conditioning' in craft:
            return 'hvac'
        if 'plumb' in craft:
            return 'plumbing'
        if 'electri' in craft:
            return 'electrical'
        if 'roof' in craft:
            return 'roofing'
        if 'landscap' in craft or 'garden' in craft:
            return 'landscaping'
        if 'pest' in craft:
            return 'pest_control'
        if 'paint' in craft:
            return 'contractor'

        return 'other'

    def _point_in_polygon(self, lat: float, lon: float, coords: List) -> bool:
        """Ray casting point-in-polygon test."""
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

    def _deduplicate(self, businesses: List[Dict]) -> List[Dict]:
        """Remove duplicates by name + location."""
        seen = {}
        unique = []

        for biz in businesses:
            name = (biz.get('name', '') or '').lower().strip()
            name = re.sub(r'[^\w\s]', '', name)[:30]

            lat = round(biz.get('latitude', 0), 3)
            lon = round(biz.get('longitude', 0), 3)

            key = f"{name}_{lat}_{lon}"

            if key not in seen:
                seen[key] = True
                unique.append(biz)

        return unique

    def _get_tier(self, category: str) -> int:
        """Get tier for category."""
        tier1 = ['car_dealership', 'car_rental', 'hospital', 'police', 'fire_station', 'university']
        tier2 = ['body_shop', 'clinic', 'school', 'government', 'hotel', 'landscaping', 'hvac']

        if category in tier1:
            return 1
        if category in tier2:
            return 2
        return 3
