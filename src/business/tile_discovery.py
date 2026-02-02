"""
Tile-Based Business Discovery Service
======================================
Discovers businesses using tile-based searching across multiple data sources.

Benefits of tile-based approach:
1. Complete coverage of irregular swath shapes
2. Stays under API limits (Google: 60 results per search)
3. Better precision for geographic filtering
4. Enables parallel searching
5. Tile-level caching for reuse

Supported sources:
- OSM (Overpass API) - comprehensive, free, has coordinates
- BBB (Better Business Bureau) - accredited businesses
- Yellow Pages - service businesses (may be blocked)
- Google Places (future) - most comprehensive, has limits
"""

import json
import sqlite3
import logging
import time
import re
from typing import List, Dict, Tuple, Optional, Callable
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import requests

from .tile_system import SwathTileSystem, Tile

logger = logging.getLogger('TileDiscovery')


class OverpassClient:
    """
    Resilient Overpass API client with server rotation and retry logic.

    Features:
    - Rotates between multiple Overpass API servers
    - Automatically retries failed requests on different servers
    - Rate limiting to avoid 429 errors
    - Marks temporarily failed servers to skip them
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
        self.min_delay = 1.5  # Minimum seconds between requests

    def get_next_server(self) -> str:
        """Get next available server, skipping failed ones."""
        available = [s for i, s in enumerate(self.SERVERS) if i not in self.failed_servers]

        if not available:
            # Reset failed servers and try again
            print("[OSM] All servers failed, resetting and retrying...")
            self.failed_servers.clear()
            available = self.SERVERS

        # Round-robin through available servers
        server = available[self.current_server_index % len(available)]
        self.current_server_index += 1
        return server

    def query(self, overpass_query: str, max_retries: int = 3, timeout: int = 30) -> dict:
        """
        Execute Overpass query with retry and server rotation.

        Returns parsed JSON or empty dict on failure.
        """
        # Rate limiting - wait between requests
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

        last_error = None

        for attempt in range(max_retries):
            server = self.get_next_server()
            server_name = server.split('/')[2][:25]

            try:
                print(f"[OSM] Attempt {attempt + 1}/{max_retries} using {server_name}...")

                response = requests.post(
                    server,
                    data={'data': overpass_query},
                    timeout=timeout,
                    headers={'User-Agent': 'HailTrackerPDR/2.0'}
                )

                self.last_request_time = time.time()

                if response.status_code == 200:
                    print(f"[OSM] Success from {server_name}")
                    return response.json()

                elif response.status_code == 429:
                    # Rate limited - mark server as failed temporarily
                    print(f"[OSM] Rate limited (429) on {server_name}, trying next server")
                    server_index = self.SERVERS.index(server) if server in self.SERVERS else -1
                    if server_index >= 0:
                        self.failed_servers.add(server_index)
                    time.sleep(2)

                elif response.status_code == 504:
                    # Timeout - try next server
                    print(f"[OSM] Timeout (504) on {server_name}, trying next server")
                    server_index = self.SERVERS.index(server) if server in self.SERVERS else -1
                    if server_index >= 0:
                        self.failed_servers.add(server_index)
                    time.sleep(1)

                elif response.status_code == 400:
                    # Bad query - don't retry
                    print(f"[OSM] Bad query (400): {response.text[:200]}")
                    return {}

                else:
                    print(f"[OSM] Error {response.status_code} on {server_name}")
                    last_error = f"HTTP {response.status_code}"
                    time.sleep(1)

            except requests.Timeout:
                print(f"[OSM] Request timeout on {server_name}")
                last_error = "Timeout"
                server_index = self.SERVERS.index(server) if server in self.SERVERS else -1
                if server_index >= 0:
                    self.failed_servers.add(server_index)
                time.sleep(1)

            except requests.ConnectionError as e:
                print(f"[OSM] Connection error on {server_name}: {e}")
                last_error = "Connection error"
                server_index = self.SERVERS.index(server) if server in self.SERVERS else -1
                if server_index >= 0:
                    self.failed_servers.add(server_index)
                time.sleep(1)

            except Exception as e:
                print(f"[OSM] Error: {e}")
                last_error = str(e)
                time.sleep(1)

        print(f"[OSM] All {max_retries} retries failed. Last error: {last_error}")
        return {}


# Global overpass client instance (reused for connection pooling)
_overpass_client = None

def get_overpass_client() -> OverpassClient:
    """Get or create the global Overpass client."""
    global _overpass_client
    if _overpass_client is None:
        _overpass_client = OverpassClient()
    return _overpass_client


class TileBasedDiscovery:
    """
    Discover businesses using tile-based searching.
    Works with OSM, BBB, Yellow Pages, and future Google Places.
    """

    # Nominatim endpoints
    NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
    NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

    # Vehicle estimates by category
    VEHICLE_ESTIMATES = {
        'car_dealership': 150, 'car_rental': 80, 'body_shop': 25,
        'hospital': 250, 'clinic': 40, 'school': 100, 'university': 300,
        'police': 40, 'fire_station': 25, 'government': 75,
        'hotel': 60, 'church': 50, 'landscaping': 15, 'hvac': 12,
        'plumbing': 10, 'electrical': 10, 'roofing': 8, 'contractor': 15,
        'pest_control': 8, 'moving': 20, 'courier': 25, 'logistics': 50,
        'default': 10
    }

    def __init__(self, tile_size_miles: float = 0.5, db_path: str = None):
        """
        Initialize tile-based discovery.

        Args:
            tile_size_miles: Size of each tile (0.5 recommended)
            db_path: Path to database for caching
        """
        self.tile_system = SwathTileSystem(tile_size_miles)

        data_dir = Path(__file__).parent.parent.parent / 'data'
        if db_path is None:
            db_path = str(data_dir / 'hailtracker_crm.db')
        self.db_path = db_path

        self._init_tile_cache()

    def _init_tile_cache(self):
        """Initialize tile-level cache table."""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tile_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tile_id TEXT,
                center_lat REAL,
                center_lon REAL,
                source TEXT,
                business_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tile_id, source)
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tile_cache_id ON tile_cache(tile_id)')
        conn.commit()
        conn.close()

    def discover_for_swaths(
        self,
        swaths: List[dict],
        sources: List[str] = None,
        progress_callback: Callable = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Discover businesses in swaths using tile-based approach.

        Args:
            swaths: List of GeoJSON swath polygons
            sources: List of sources: 'osm', 'bbb', 'yellowpages', 'google'
            progress_callback: Optional callback(current, total, tile)
            use_cache: Whether to use tile-level cache

        Returns:
            {
                'businesses': [...],
                'stats': {...},
                'tile_stats': {...}
            }
        """
        if sources is None:
            sources = ['osm']

        # Generate tiles for all swaths
        tiles = self.tile_system.generate_tiles_for_multiple_swaths(swaths)
        tile_stats = self.tile_system.get_tile_stats(tiles)

        logger.info(f"Generated {tile_stats['count']} tiles for {len(swaths)} swaths")
        logger.info(f"Sources: {sources}")

        all_businesses = []
        stats = {
            'tiles_total': len(tiles),
            'tiles_searched': 0,
            'tiles_from_cache': 0,
            'by_source': {s: 0 for s in sources},
            'geocoded': 0,
            'duplicates_removed': 0,
        }

        # Track reverse geocode results to avoid duplicate lookups
        location_cache = {}

        # Search each tile sequentially with progress
        print(f"\n{'='*60}")
        print(f"[Discovery] Starting tile-by-tile discovery...")
        print(f"[Discovery] Total tiles: {len(tiles)}, Sources: {sources}")
        print(f"{'='*60}\n")

        for i, tile in enumerate(tiles):
            tile_num = i + 1
            print(f"\n[Discovery] === Tile {tile_num}/{len(tiles)} === ({tile.tile_id})")

            if progress_callback:
                progress_callback(tile_num, len(tiles), tile)

            tile_businesses = []

            # OSM Search (has coordinates, no geocoding needed)
            if 'osm' in sources:
                cached = self._get_cached_tile(tile.tile_id, 'osm') if use_cache else None
                if cached:
                    osm_results = cached
                    stats['tiles_from_cache'] += 1
                    print(f"[Discovery] OSM: {len(osm_results)} from CACHE")
                else:
                    osm_results = self._search_osm_tile(tile)
                    self._cache_tile(tile.tile_id, 'osm', osm_results)
                    print(f"[Discovery] OSM: {len(osm_results)} from API (cached)")

                tile_businesses.extend(osm_results)
                stats['by_source']['osm'] += len(osm_results)

            # BBB Search (needs reverse geocode for city/state)
            if 'bbb' in sources:
                cached = self._get_cached_tile(tile.tile_id, 'bbb') if use_cache else None
                if cached:
                    bbb_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    city, state = self._get_location_for_tile(tile, location_cache)
                    if city and state:
                        bbb_results = self._search_bbb_tile(tile, city, state)
                        self._cache_tile(tile.tile_id, 'bbb', bbb_results)
                    else:
                        bbb_results = []

                tile_businesses.extend(bbb_results)
                stats['by_source']['bbb'] += len(bbb_results)

            # Yellow Pages Search (may be blocked)
            if 'yellowpages' in sources:
                cached = self._get_cached_tile(tile.tile_id, 'yellowpages') if use_cache else None
                if cached:
                    yp_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    city, state = self._get_location_for_tile(tile, location_cache)
                    if city and state:
                        yp_results = self._search_yellowpages_tile(tile, city, state)
                        self._cache_tile(tile.tile_id, 'yellowpages', yp_results)
                    else:
                        yp_results = []

                tile_businesses.extend(yp_results)
                stats['by_source']['yellowpages'] += len(yp_results)

            # Google Places (future)
            if 'google' in sources:
                google_results = self._search_google_tile(tile)
                tile_businesses.extend(google_results)
                stats['by_source']['google'] += len(google_results)

            # Manta (may be blocked - 403)
            if 'manta' in sources:
                cached = self._get_cached_tile(tile.tile_id, 'manta') if use_cache else None
                if cached:
                    manta_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    city, state = self._get_location_for_tile(tile, location_cache)
                    if city and state:
                        manta_results = self._search_manta_tile(tile, city, state)
                        self._cache_tile(tile.tile_id, 'manta', manta_results)
                    else:
                        manta_results = []

                tile_businesses.extend(manta_results)
                stats['by_source']['manta'] = stats['by_source'].get('manta', 0) + len(manta_results)

            # Foursquare (needs API key)
            if 'foursquare' in sources:
                cached = self._get_cached_tile(tile.tile_id, 'foursquare') if use_cache else None
                if cached:
                    fs_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    fs_results = self._search_foursquare_tile(tile)
                    if fs_results:  # Only cache if we got results (API configured)
                        self._cache_tile(tile.tile_id, 'foursquare', fs_results)

                tile_businesses.extend(fs_results)
                stats['by_source']['foursquare'] = stats['by_source'].get('foursquare', 0) + len(fs_results)

            all_businesses.extend(tile_businesses)
            stats['tiles_searched'] += 1

            # Rate limiting between tiles
            time.sleep(0.5)

        # Geocode businesses missing coordinates
        businesses_with_coords = []
        for biz in all_businesses:
            if biz.get('latitude') and biz.get('longitude'):
                businesses_with_coords.append(biz)
            else:
                coords = self._geocode_address(
                    biz.get('address', ''),
                    biz.get('city', ''),
                    biz.get('state', '')
                )
                if coords:
                    biz['latitude'] = coords[0]
                    biz['longitude'] = coords[1]
                    businesses_with_coords.append(biz)
                    stats['geocoded'] += 1
                    time.sleep(1)  # Nominatim rate limit

        # Point-in-polygon filter
        businesses_in_swath = []
        for biz in businesses_with_coords:
            for swath in swaths:
                if self._point_in_swath(biz['latitude'], biz['longitude'], swath):
                    businesses_in_swath.append(biz)
                    break

        # Deduplicate
        pre_dedup = len(businesses_in_swath)
        unique_businesses = self._deduplicate_businesses(businesses_in_swath)
        stats['duplicates_removed'] = pre_dedup - len(unique_businesses)

        # Add metadata
        for biz in unique_businesses:
            if 'tier' not in biz:
                biz['tier'] = self._get_tier(biz.get('category', 'other'))
            if 'estimated_vehicles' not in biz:
                biz['estimated_vehicles'] = self.VEHICLE_ESTIMATES.get(
                    biz.get('category', 'other'),
                    self.VEHICLE_ESTIMATES['default']
                )

        # Sort by tier then vehicles
        unique_businesses.sort(key=lambda x: (x.get('tier', 3), -x.get('estimated_vehicles', 0)))

        stats['total_found'] = len(unique_businesses)
        stats['total_vehicles'] = sum(b.get('estimated_vehicles', 10) for b in unique_businesses)

        # Count by category
        stats['by_category'] = {}
        for biz in unique_businesses:
            cat = biz.get('category', 'other')
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1

        logger.info(f"Discovery complete: {len(unique_businesses)} businesses")
        logger.info(f"By source: {stats['by_source']}")

        return {
            'success': True,
            'businesses': unique_businesses,
            'stats': stats,
            'tile_stats': tile_stats,
        }

    def _search_osm_tile(self, tile: Tile) -> List[Dict]:
        """
        Search OSM for businesses in a tile using resilient Overpass client.

        Uses smaller, focused queries with server rotation and retry logic.
        """
        try:
            radius_meters = int(tile.search_radius_miles * 1609.34)
            lat = tile.center_lat
            lon = tile.center_lon

            # Use shorter timeout for faster failover
            # Simplified query - most important fleet categories only
            query = f'''[out:json][timeout:25];
(
  node["shop"~"car|car_repair|car_parts"](around:{radius_meters},{lat},{lon});
  way["shop"~"car|car_repair"](around:{radius_meters},{lat},{lon});
  node["amenity"~"car_rental|hospital|clinic|police|fire_station|school"](around:{radius_meters},{lat},{lon});
  way["amenity"~"car_rental|hospital|police|fire_station|school"](around:{radius_meters},{lat},{lon});
  node["craft"](around:{radius_meters},{lat},{lon});
  node["office"~"company|government"](around:{radius_meters},{lat},{lon});
  node["tourism"="hotel"](around:{radius_meters},{lat},{lon});
  way["tourism"="hotel"](around:{radius_meters},{lat},{lon});
);
out center;'''

            # Use the resilient client with server rotation
            client = get_overpass_client()
            data = client.query(query, max_retries=3, timeout=30)

            if not data:
                print(f"[OSM] No data returned for tile {tile.tile_id}")
                return []

            elements = data.get('elements', [])
            businesses = []

            for elem in elements:
                biz = self._parse_osm_element(elem)
                if biz:
                    biz['source'] = 'osm'
                    biz['tile_id'] = tile.tile_id
                    businesses.append(biz)

            print(f"[OSM] Found {len(businesses)} businesses in tile {tile.tile_id}")
            return businesses

        except Exception as e:
            logger.error(f"OSM tile search error: {e}")
            print(f"[OSM] Exception in tile search: {e}")
            return []

    def _parse_osm_element(self, elem: dict) -> Optional[Dict]:
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
        category = self._detect_osm_category(tags)

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
            'osm_id': f"{elem.get('type', 'node')}_{elem.get('id', '')}",
        }

    def _detect_osm_category(self, tags: dict) -> str:
        """Detect business category from OSM tags."""
        if tags.get('shop') in ['car', 'car_dealer']:
            return 'car_dealership'
        if tags.get('amenity') == 'car_rental':
            return 'car_rental'
        if tags.get('shop') == 'car_repair' or 'body' in str(tags.get('craft', '')):
            return 'body_shop'
        if tags.get('amenity') == 'hospital':
            return 'hospital'
        if tags.get('amenity') == 'clinic':
            return 'clinic'
        if tags.get('amenity') == 'police':
            return 'police'
        if tags.get('amenity') == 'fire_station':
            return 'fire_station'
        if tags.get('amenity') == 'school':
            return 'school'
        if tags.get('tourism') == 'hotel':
            return 'hotel'
        if tags.get('amenity') == 'place_of_worship':
            return 'church'
        if tags.get('office') == 'government':
            return 'government'

        # Check craft tags
        craft = tags.get('craft', '').lower()
        if 'hvac' in craft or 'heating' in craft:
            return 'hvac'
        if 'plumb' in craft:
            return 'plumbing'
        if 'electri' in craft:
            return 'electrical'
        if 'roof' in craft:
            return 'roofing'
        if 'landscap' in craft:
            return 'landscaping'

        return 'other'

    def _search_bbb_tile(self, tile: Tile, city: str, state: str) -> List[Dict]:
        """Search BBB for businesses near a tile."""
        try:
            from src.fleet.scrapers.bbb import BBBScraper

            bbb = BBBScraper()

            # Priority categories for PDR fleet prospecting
            categories = [
                ('landscape-contractors', 'landscaping'),
                ('pest-control-services', 'pest_control'),
                ('air-conditioning-contractors-systems', 'hvac'),
                ('plumbers', 'plumbing'),
                ('roofing-contractors', 'roofing'),
            ]

            businesses = []
            for cat_slug, our_cat in categories[:3]:  # Limit to avoid too many requests
                try:
                    results = bbb.search(city, state, cat_slug, max_pages=1)
                    for biz in results:
                        businesses.append({
                            'name': biz.get('name', ''),
                            'category': our_cat,
                            'address': biz.get('address', ''),
                            'city': biz.get('city', city),
                            'state': biz.get('state', state),
                            'zip': biz.get('zip', ''),
                            'phone': biz.get('phone', ''),
                            'website': biz.get('website', ''),
                            'email': '',
                            'latitude': 0,
                            'longitude': 0,
                            'source': 'bbb',
                            'tile_id': tile.tile_id,
                            'bbb_accredited': True,
                        })
                    time.sleep(2)
                except Exception as e:
                    logger.debug(f"BBB category {cat_slug} failed: {e}")

            return businesses

        except Exception as e:
            logger.error(f"BBB tile search error: {e}")
            return []

    def _search_yellowpages_tile(self, tile: Tile, city: str, state: str) -> List[Dict]:
        """
        Search Yellow Pages for businesses near a tile.
        Uses Playwright headless browser to bypass anti-bot protection.
        """
        try:
            from src.fleet.scrapers.yellowpages_playwright import YellowPagesPlaywright

            # Use context manager for clean browser handling
            with YellowPagesPlaywright() as yp:
                # Search priority categories only (to limit time/resources)
                priority_cats = ['landscaping', 'hvac', 'plumbers', 'electricians',
                               'pest-control', 'roofing-contractors']
                results = []

                for category in priority_cats[:3]:  # Limit to 3 categories per tile
                    try:
                        cat_results = yp.search(city, state, category, max_pages=1)
                        results.extend(cat_results)
                    except Exception as e:
                        logger.debug(f"YP {category} failed: {e}")

            # Format results
            businesses = []
            for biz in results:
                businesses.append({
                    'name': biz.get('name', ''),
                    'category': biz.get('category', 'other'),
                    'address': biz.get('address', ''),
                    'city': biz.get('city', city),
                    'state': biz.get('state', state),
                    'zip': biz.get('zip', ''),
                    'phone': biz.get('phone', ''),
                    'website': biz.get('website', ''),
                    'email': '',
                    'latitude': tile.center_lat,  # Use tile center as approx location
                    'longitude': tile.center_lon,
                    'source': 'yellowpages',
                    'tile_id': tile.tile_id,
                })

            logger.info(f"Yellow Pages found {len(businesses)} businesses in {city}, {state}")
            return businesses

        except ImportError as e:
            logger.warning(f"Playwright not installed: {e}. Run: pip install playwright && playwright install chromium")
            return []
        except Exception as e:
            logger.error(f"Yellow Pages tile search error: {e}")
            return []

    def _search_google_tile(self, tile: Tile) -> List[Dict]:
        """
        Search Google Places for businesses in a tile.
        FUTURE IMPLEMENTATION - placeholder for now.

        Google Places API benefits:
        - Most comprehensive business data
        - Accurate coordinates
        - Up-to-date info

        Tile approach is ESSENTIAL for Google:
        - 60 result limit per search
        - Small tiles = under limit = 100% capture
        """
        # TODO: Implement when Google Places API is added
        return []

    def _search_manta_tile(self, tile: Tile, city: str, state: str) -> List[Dict]:
        """
        Search Manta.com for businesses near a tile.
        Uses Playwright headless browser to bypass anti-bot protection.
        """
        try:
            from src.fleet.scrapers.manta_playwright import MantaPlaywright

            # Use context manager for clean browser handling
            with MantaPlaywright() as manta:
                # Search priority categories
                priority_cats = ['landscaping', 'hvac', 'plumbing-contractors',
                               'electrical-contractors', 'pest-control-services',
                               'roofing-contractors']
                results = []

                for category in priority_cats[:3]:  # Limit to 3 categories per tile
                    try:
                        cat_results = manta.search(city, state, category)
                        results.extend(cat_results)
                    except Exception as e:
                        logger.debug(f"Manta {category} failed: {e}")

            # Format results
            businesses = []
            for biz in results:
                businesses.append({
                    'name': biz.get('name', ''),
                    'category': biz.get('category', 'other'),
                    'address': biz.get('address', ''),
                    'city': biz.get('city', city),
                    'state': biz.get('state', state),
                    'zip': biz.get('zip', ''),
                    'phone': biz.get('phone', ''),
                    'website': biz.get('website', ''),
                    'email': '',
                    'latitude': tile.center_lat,
                    'longitude': tile.center_lon,
                    'source': 'manta',
                    'tile_id': tile.tile_id,
                })

            logger.info(f"Manta found {len(businesses)} businesses in {city}, {state}")
            return businesses

        except ImportError as e:
            logger.warning(f"Playwright not installed: {e}. Run: pip install playwright && playwright install chromium")
            return []
        except Exception as e:
            logger.error(f"Manta tile search error: {e}")
            return []

    def _search_foursquare_tile(self, tile: Tile) -> List[Dict]:
        """
        Search Foursquare Places API for businesses in a tile.
        Requires FOURSQUARE_API_KEY environment variable.
        """
        try:
            from src.fleet.scrapers.foursquare_api import FoursquareAPI
            api = FoursquareAPI()

            if not api.is_configured():
                # Silently skip if not configured
                return []

            # Convert tile radius to meters
            radius_meters = int(tile.search_radius_miles * 1609.34)

            # Search all fleet-relevant categories
            results = api.search_all_fleet_categories(
                tile.center_lat,
                tile.center_lon,
                radius_meters
            )

            # Add tile_id to each result
            for biz in results:
                biz['tile_id'] = tile.tile_id

            return results

        except ImportError:
            logger.warning("FoursquareAPI not available")
            return []
        except Exception as e:
            logger.error(f"Foursquare tile search error: {e}")
            return []

    def _get_location_for_tile(self, tile: Tile, cache: dict) -> Tuple[str, str]:
        """Get city/state for a tile using reverse geocoding with caching."""
        cache_key = (round(tile.center_lat, 2), round(tile.center_lon, 2))

        if cache_key in cache:
            return cache[cache_key]

        city, state = self._reverse_geocode(tile.center_lat, tile.center_lon)
        cache[cache_key] = (city, state)

        return city, state

    def _reverse_geocode(self, lat: float, lon: float) -> Tuple[str, str]:
        """Reverse geocode coordinates to city, state."""
        try:
            response = requests.get(
                self.NOMINATIM_REVERSE_URL,
                params={'lat': lat, 'lon': lon, 'format': 'json'},
                headers={'User-Agent': 'HailTrackerPDR/2.0'},
                timeout=10
            )

            if response.ok:
                data = response.json()
                address = data.get('address', {})
                city = (address.get('city') or address.get('town') or
                        address.get('village') or address.get('county', ''))
                state = address.get('state', '')

                # Convert state name to abbreviation
                state = self._state_to_abbrev(state)

                time.sleep(1)  # Rate limit
                return city, state

        except Exception as e:
            logger.debug(f"Reverse geocode failed: {e}")

        return '', ''

    def _geocode_address(self, address: str, city: str, state: str) -> Optional[Tuple[float, float]]:
        """Geocode an address to coordinates."""
        if not address and not city:
            return None

        query_parts = [p for p in [address, city, state, 'USA'] if p]
        query = ', '.join(query_parts)

        try:
            response = requests.get(
                self.NOMINATIM_SEARCH_URL,
                params={'q': query, 'format': 'json', 'limit': 1},
                headers={'User-Agent': 'HailTrackerPDR/2.0'},
                timeout=10
            )

            if response.ok:
                results = response.json()
                if results:
                    return (float(results[0]['lat']), float(results[0]['lon']))

        except Exception as e:
            logger.debug(f"Geocode failed: {e}")

        return None

    def _state_to_abbrev(self, state_name: str) -> str:
        """Convert state name to abbreviation."""
        states = {
            'Oklahoma': 'OK', 'Texas': 'TX', 'Kansas': 'KS', 'Colorado': 'CO',
            'Nebraska': 'NE', 'Missouri': 'MO', 'Arkansas': 'AR', 'Louisiana': 'LA',
            'New Mexico': 'NM', 'Iowa': 'IA', 'Illinois': 'IL', 'Indiana': 'IN',
            'Ohio': 'OH', 'Kentucky': 'KY', 'Tennessee': 'TN', 'Mississippi': 'MS',
            'Alabama': 'AL', 'Georgia': 'GA', 'Florida': 'FL', 'South Carolina': 'SC',
            'North Carolina': 'NC', 'Virginia': 'VA', 'West Virginia': 'WV',
        }
        return states.get(state_name, state_name)

    def _point_in_swath(self, lat: float, lon: float, swath: dict) -> bool:
        """Check if point is inside swath polygon."""
        coords = None
        if swath.get('type') == 'Polygon':
            coords = swath['coordinates'][0]
        elif swath.get('type') == 'Feature':
            coords = swath['geometry']['coordinates'][0]

        if not coords:
            return False

        # Ray casting algorithm
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

    def _deduplicate_businesses(self, businesses: List[Dict]) -> List[Dict]:
        """Remove duplicate businesses based on name + location."""
        seen = {}
        unique = []

        for biz in businesses:
            name = (biz.get('name', '') or '').lower().strip()
            name = re.sub(r'[^\w\s]', '', name)
            name = re.sub(r'\s+', ' ', name).strip()[:30]

            lat = biz.get('latitude') or 0
            lon = biz.get('longitude') or 0

            # Round coordinates for dedup
            loc_key = f"{round(lat, 3)}_{round(lon, 3)}"
            dedup_key = f"{name}_{loc_key}"

            if dedup_key not in seen:
                seen[dedup_key] = True
                unique.append(biz)
            else:
                # Merge additional info if available
                existing_idx = next((i for i, u in enumerate(unique)
                                   if f"{u.get('name','').lower()[:30]}_{round(u.get('latitude',0),3)}_{round(u.get('longitude',0),3)}" == dedup_key), None)
                if existing_idx is not None:
                    existing = unique[existing_idx]
                    if biz.get('phone') and not existing.get('phone'):
                        existing['phone'] = biz['phone']
                    if biz.get('website') and not existing.get('website'):
                        existing['website'] = biz['website']

        return unique

    def _get_tier(self, category: str) -> int:
        """Get tier for a category (1=highest priority)."""
        tier1 = ['car_dealership', 'car_rental', 'hospital', 'police', 'fire_station', 'university']
        tier2 = ['body_shop', 'clinic', 'school', 'government', 'hotel', 'landscaping', 'hvac', 'plumbing']
        tier3 = ['electrical', 'roofing', 'contractor', 'pest_control', 'church', 'moving']

        if category in tier1:
            return 1
        if category in tier2:
            return 2
        if category in tier3:
            return 3
        return 3

    def _get_cached_tile(self, tile_id: str, source: str) -> Optional[List[Dict]]:
        """Get cached businesses for a tile."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('''
                SELECT business_data FROM tile_cache
                WHERE tile_id = ? AND source = ?
                AND created_at > datetime('now', '-7 days')
            ''', (tile_id, source))
            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row[0])

        except Exception as e:
            logger.debug(f"Cache read error: {e}")

        return None

    def _cache_tile(self, tile_id: str, source: str, businesses: List[Dict]):
        """Cache businesses for a tile."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT OR REPLACE INTO tile_cache (tile_id, source, business_data)
                VALUES (?, ?, ?)
            ''', (tile_id, source, json.dumps(businesses)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Cache write error: {e}")

    def clear_tile_cache(self, older_than_days: int = None):
        """Clear tile cache."""
        conn = sqlite3.connect(self.db_path)
        if older_than_days:
            conn.execute(f'''
                DELETE FROM tile_cache
                WHERE created_at < datetime('now', '-{older_than_days} days')
            ''')
        else:
            conn.execute('DELETE FROM tile_cache')
        conn.commit()
        conn.close()
        logger.info("Tile cache cleared")
