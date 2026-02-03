"""
Tile-Based Business Discovery Service
======================================
Discovers businesses using tile-based searching across multiple data sources.

Benefits of tile-based approach:
1. Complete coverage of irregular swath shapes
2. Stays under API limits (Yelp: 50, Google: 60, Foursquare: 50 per search)
3. Searching 1000 tiles = 50,000+ potential results vs 50 for single search
4. Better precision for geographic filtering
5. Enables parallel searching
6. Tile-level caching for reuse

Supported sources (all 6 APIs):
- OSM (Overpass API) - comprehensive, free, unlimited
- Yelp - best for service businesses (5k/day, 50/call)
- Foursquare - good coverage (100k/month, 50/call)
- HERE - excellent data (250k/month, 100/call)
- TomTom - good backup (2.5k/day, 100/call)
- Google Places - most comprehensive ($200 credit, 60/call)
- BBB (Better Business Bureau) - accredited businesses
- Yellow Pages - service businesses (may be blocked)
"""

import json
import sqlite3
import logging
import time
import re
import os
from typing import List, Dict, Tuple, Optional, Callable
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import requests

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Find .env file in project root
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed

from .tile_system import SwathTileSystem, Tile

# Use the unified category taxonomy
from src.business.category_taxonomy import (
    CATEGORY_TAXONOMY,
    normalize_category_key,
    estimate_vehicles,
    detect_category_from_tags,
)

# Import all 6 APIs for tile-based searching
from src.fleet.apis.yelp_api import YelpAPI
from src.fleet.apis.here_api import HereAPI
from src.fleet.apis.tomtom_api import TomTomAPI
from src.fleet.apis.google_places_api import GooglePlacesAPI
from src.fleet.scrapers.foursquare_api import FoursquareAPI

# Import deduplication
from src.business.deduplication import deduplicate_businesses

logger = logging.getLogger('TileDiscovery')


class TileBasedDiscovery:
    """
    Discover businesses using tile-based searching.
    Works with OSM, BBB, Yellow Pages, and future Google Places.
    """

    # Overpass API endpoints (multiple servers for fallback)
    OVERPASS_SERVERS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
    ]
    OVERPASS_URL = OVERPASS_SERVERS[0]  # Default

    # OSM rate limiting: 2 second delay between calls (fair use policy)
    OSM_MIN_DELAY_SECONDS = 2.0
    OSM_MAX_RETRIES = 3
    OSM_BACKOFF_MULTIPLIER = 2

    # Nominatim endpoints
    NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
    NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

    # Vehicle estimates now come from unified taxonomy
    @property
    def VEHICLE_ESTIMATES(self) -> dict:
        """Get vehicle estimates from taxonomy (backwards compat)."""
        estimates = {'default': 10}
        for key, config in CATEGORY_TAXONOMY.items():
            estimates[key] = config.get('est_vehicles', 10)
        return estimates

    def __init__(self, tile_size_miles: float = 0.25, db_path: str = None):
        """
        Initialize tile-based discovery.

        Args:
            tile_size_miles: Size of each tile (0.25 sq mile = Kyle's proven config)
            db_path: Path to database for caching
        """
        self.tile_system = SwathTileSystem(tile_size_miles)

        data_dir = Path(__file__).parent.parent.parent / 'data'
        if db_path is None:
            db_path = str(data_dir / 'hailtracker_crm.db')
        self.db_path = db_path

        # Initialize all 6 APIs
        self.yelp = YelpAPI()
        self.foursquare = FoursquareAPI()
        self.here = HereAPI()
        self.tomtom = TomTomAPI()
        self.google = GooglePlacesAPI()

        # OSM rate limiting tracking
        self._osm_last_call_time = 0
        self._osm_current_server_idx = 0

        # Track which APIs are configured
        self.configured_apis = []
        if self.yelp.is_configured():
            self.configured_apis.append('yelp')
        if self.foursquare.is_configured():
            self.configured_apis.append('foursquare')
        if self.here.is_configured():
            self.configured_apis.append('here')
        if self.tomtom.is_configured():
            self.configured_apis.append('tomtom')
        if self.google.is_configured():
            self.configured_apis.append('google')
        # OSM is always available (no API key needed)
        self.configured_apis.append('osm')

        logger.info(f"TileBasedDiscovery initialized with APIs: {self.configured_apis}")

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
        use_cache: bool = True,
        max_tiles: int = 0
    ) -> Dict:
        """
        Discover businesses in swaths using tile-based approach.

        Args:
            swaths: List of GeoJSON swath polygons
            sources: List of sources: 'osm', 'yelp', 'foursquare', 'here', 'tomtom', 'google'
            progress_callback: Optional callback(current, total, tile)
            use_cache: Whether to use tile-level cache
            max_tiles: Maximum tiles to search (0 = unlimited).
                       Tiles are prioritized by proximity to urban centers.

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
        all_tiles = self.tile_system.generate_tiles_for_multiple_swaths(swaths)

        # Smart tile selection: prioritize tiles near urban centers
        # Sort by distance from centroid (denser areas tend to be central)
        if len(all_tiles) > 0:
            # Calculate centroid of all tiles
            avg_lat = sum(t.center_lat for t in all_tiles) / len(all_tiles)
            avg_lon = sum(t.center_lon for t in all_tiles) / len(all_tiles)

            # Sort tiles by distance from centroid (closest first = urban core)
            all_tiles.sort(key=lambda t: (
                (t.center_lat - avg_lat)**2 + (t.center_lon - avg_lon)**2
            ))

        # Limit tiles if max_tiles specified
        if max_tiles > 0 and len(all_tiles) > max_tiles:
            tiles = all_tiles[:max_tiles]
            logger.info(f"Limiting to {max_tiles} tiles (of {len(all_tiles)} total)")
        else:
            tiles = all_tiles

        tile_stats = self.tile_system.get_tile_stats(tiles)
        tile_stats['total_available'] = len(all_tiles)
        tile_stats['limited'] = max_tiles > 0 and len(all_tiles) > max_tiles

        logger.info(f"Searching {len(tiles)} tiles for {len(swaths)} swaths")
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

        # Search each tile
        for i, tile in enumerate(tiles):
            if progress_callback:
                progress_callback(i + 1, len(tiles), tile)

            tile_businesses = []

            # OSM Search (has coordinates, no geocoding needed)
            if 'osm' in sources:
                cached = self._get_cached_tile(tile.tile_id, 'osm') if use_cache else None
                if cached:
                    osm_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    osm_results = self._search_osm_tile(tile)
                    self._cache_tile(tile.tile_id, 'osm', osm_results)

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

            # Yelp Search (50 results/call, best for service businesses)
            if 'yelp' in sources and self.yelp.is_configured():
                cached = self._get_cached_tile(tile.tile_id, 'yelp') if use_cache else None
                if cached:
                    yelp_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    yelp_results = self._search_yelp_tile(tile)
                    self._cache_tile(tile.tile_id, 'yelp', yelp_results)

                tile_businesses.extend(yelp_results)
                stats['by_source']['yelp'] = stats['by_source'].get('yelp', 0) + len(yelp_results)

            # Foursquare Search (50 results/call, 100k/month)
            if 'foursquare' in sources and self.foursquare.is_configured():
                cached = self._get_cached_tile(tile.tile_id, 'foursquare') if use_cache else None
                if cached:
                    fs_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    fs_results = self._search_foursquare_tile(tile)
                    self._cache_tile(tile.tile_id, 'foursquare', fs_results)

                tile_businesses.extend(fs_results)
                stats['by_source']['foursquare'] = stats['by_source'].get('foursquare', 0) + len(fs_results)

            # HERE Search (100 results/call, 250k/month - best per-call yield)
            if 'here' in sources and self.here.is_configured():
                cached = self._get_cached_tile(tile.tile_id, 'here') if use_cache else None
                if cached:
                    here_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    here_results = self._search_here_tile(tile)
                    self._cache_tile(tile.tile_id, 'here', here_results)

                tile_businesses.extend(here_results)
                stats['by_source']['here'] = stats['by_source'].get('here', 0) + len(here_results)

            # TomTom Search (100 results/call, 2.5k/day - use strategically)
            if 'tomtom' in sources and self.tomtom.is_configured():
                cached = self._get_cached_tile(tile.tile_id, 'tomtom') if use_cache else None
                if cached:
                    tomtom_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    tomtom_results = self._search_tomtom_tile(tile)
                    self._cache_tile(tile.tile_id, 'tomtom', tomtom_results)

                tile_businesses.extend(tomtom_results)
                stats['by_source']['tomtom'] = stats['by_source'].get('tomtom', 0) + len(tomtom_results)

            # Google Places (60 results/call via pagination, costs money)
            if 'google' in sources and self.google.is_configured():
                cached = self._get_cached_tile(tile.tile_id, 'google') if use_cache else None
                if cached:
                    google_results = cached
                    stats['tiles_from_cache'] += 1
                else:
                    google_results = self._search_google_tile(tile)
                    self._cache_tile(tile.tile_id, 'google', google_results)

                tile_businesses.extend(google_results)
                stats['by_source']['google'] = stats['by_source'].get('google', 0) + len(google_results)

            all_businesses.extend(tile_businesses)
            stats['tiles_searched'] += 1

            # Rate limiting between tiles
            # Commercial APIs can handle 0.2-0.3s between calls
            # OSM needs 1.5s+ but we'll rely on tile caching after first run
            time.sleep(0.2)

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

        # Deduplicate using proper deduplication engine
        pre_dedup = len(businesses_in_swath)
        stats['total_found'] = pre_dedup  # Raw count before deduplication
        unique_businesses = deduplicate_businesses(businesses_in_swath, merge_data=True)
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

        stats['unique_businesses'] = len(unique_businesses)
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

    def _osm_rate_limit_delay(self):
        """Enforce 2-second delay between OSM Overpass calls."""
        elapsed = time.time() - self._osm_last_call_time
        if elapsed < self.OSM_MIN_DELAY_SECONDS:
            time.sleep(self.OSM_MIN_DELAY_SECONDS - elapsed)
        self._osm_last_call_time = time.time()

    def _search_osm_tile(self, tile: Tile) -> List[Dict]:
        """
        Search OSM for businesses in a tile using Overpass API.
        Includes rate limiting, retry logic, and server fallback.
        """
        radius_meters = int(tile.search_radius_miles * 1609.34)

        query = f'''[out:json][timeout:60];
(
  // Automotive
  node["shop"="car"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["shop"="car"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["amenity"="car_rental"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["amenity"="car_rental"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["shop"="car_repair"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["shop"="car_repair"](around:{radius_meters},{tile.center_lat},{tile.center_lon});

  // Service/Trades
  node["craft"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["craft"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["office"="company"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["office"="company"](around:{radius_meters},{tile.center_lat},{tile.center_lon});

  // Medical
  node["amenity"="hospital"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["amenity"="hospital"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["amenity"="clinic"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["amenity"="clinic"](around:{radius_meters},{tile.center_lat},{tile.center_lon});

  // Government
  node["amenity"="police"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["amenity"="police"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["amenity"="fire_station"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["amenity"="fire_station"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["amenity"="school"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["amenity"="school"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["office"="government"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["office"="government"](around:{radius_meters},{tile.center_lat},{tile.center_lon});

  // Commercial
  node["tourism"="hotel"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["tourism"="hotel"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  node["amenity"="place_of_worship"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
  way["amenity"="place_of_worship"](around:{radius_meters},{tile.center_lat},{tile.center_lon});
);
out center meta;'''

        # Retry with exponential backoff, trying different servers
        for attempt in range(self.OSM_MAX_RETRIES):
            # Rate limit: 2 second delay between calls
            self._osm_rate_limit_delay()

            # Cycle through servers on retries
            server_idx = (self._osm_current_server_idx + attempt) % len(self.OVERPASS_SERVERS)
            server_url = self.OVERPASS_SERVERS[server_idx]

            try:
                response = requests.post(
                    server_url,
                    data={'data': query},
                    headers={'User-Agent': 'HailTrackerPDR/2.0'},
                    timeout=60
                )

                if response.status_code == 200:
                    # Success - update preferred server
                    self._osm_current_server_idx = server_idx
                    elements = response.json().get('elements', [])
                    businesses = []

                    for elem in elements:
                        biz = self._parse_osm_element(elem)
                        if biz:
                            biz['source'] = 'osm'
                            biz['tile_id'] = tile.tile_id
                            businesses.append(biz)

                    return businesses

                elif response.status_code in (429, 503, 504):
                    # Rate limited or gateway timeout - try different server
                    wait_time = self.OSM_MIN_DELAY_SECONDS * (self.OSM_BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"[OSM] {response.status_code} from {server_url}, "
                                 f"waiting {wait_time:.1f}s (attempt {attempt + 1}/{self.OSM_MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue

                else:
                    logger.warning(f"OSM tile query failed: {response.status_code}")
                    return []

            except requests.Timeout:
                wait_time = self.OSM_MIN_DELAY_SECONDS * (self.OSM_BACKOFF_MULTIPLIER ** attempt)
                logger.warning(f"[OSM] Timeout from {server_url}, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                continue

            except Exception as e:
                logger.error(f"OSM tile search error: {e}")
                return []

        logger.warning(f"[OSM] All {self.OSM_MAX_RETRIES} retries failed for tile {tile.tile_id}")
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
        """Detect business category from OSM tags using unified taxonomy."""
        category = detect_category_from_tags(tags)
        return normalize_category_key(category)

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
        """Search Yellow Pages for businesses near a tile."""
        try:
            from src.fleet.scrapers.yellowpages import YellowPagesScraper

            yp = YellowPagesScraper()

            search_terms = [
                ('landscaping', 'landscaping'),
                ('hvac', 'hvac'),
                ('plumbing', 'plumbing'),
            ]

            businesses = []
            for term, our_cat in search_terms[:2]:  # Limit searches
                try:
                    results = yp.search(city, state, term, max_pages=1)
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
                            'source': 'yellowpages',
                            'tile_id': tile.tile_id,
                        })
                    time.sleep(2)
                except Exception as e:
                    logger.debug(f"Yellow Pages term {term} failed: {e}")

            return businesses

        except Exception as e:
            logger.error(f"Yellow Pages tile search error: {e}")
            return []

    def _search_google_tile(self, tile: Tile) -> List[Dict]:
        """
        Search Google Places for businesses in a tile.
        Uses the tile center + radius to stay under 60 result limit.
        """
        try:
            radius_meters = int(tile.search_radius_miles * 1609.34)
            results = self.google.search_all_categories(
                tile.center_lat, tile.center_lon, radius_meters
            )
            for biz in results:
                biz['source'] = 'google'
            return results
        except Exception as e:
            logger.debug(f"Google tile search error: {e}")
            return []

    def _search_yelp_tile(self, tile: Tile) -> List[Dict]:
        """
        Search Yelp for businesses in a tile.
        Yelp returns max 50 results per search, so tile approach is essential.
        """
        try:
            radius_meters = int(tile.search_radius_miles * 1609.34)
            # Yelp max radius is 40000m
            radius_meters = min(radius_meters, 40000)
            results = self.yelp.search_all_categories(
                tile.center_lat, tile.center_lon, radius_meters
            )
            for biz in results:
                biz['source'] = 'yelp'
            return results
        except Exception as e:
            logger.debug(f"Yelp tile search error: {e}")
            return []

    def _search_foursquare_tile(self, tile: Tile) -> List[Dict]:
        """
        Search Foursquare for businesses in a tile.
        50 results per call, 100k calls/month - use generously.
        """
        try:
            radius_meters = int(tile.search_radius_miles * 1609.34)
            results = self.foursquare.search_all_fleet_categories(
                tile.center_lat, tile.center_lon, radius_meters
            )
            for biz in results:
                biz['source'] = 'foursquare'
            return results
        except Exception as e:
            logger.debug(f"Foursquare tile search error: {e}")
            return []

    def _search_here_tile(self, tile: Tile) -> List[Dict]:
        """
        Search HERE for businesses in a tile.
        100 results per call, 250k/month - best yield per call.
        """
        try:
            radius_meters = int(tile.search_radius_miles * 1609.34)
            results = self.here.search_all_categories(
                tile.center_lat, tile.center_lon, radius_meters
            )
            for biz in results:
                biz['source'] = 'here'
            return results
        except Exception as e:
            logger.debug(f"HERE tile search error: {e}")
            return []

    def _search_tomtom_tile(self, tile: Tile) -> List[Dict]:
        """
        Search TomTom for businesses in a tile.
        100 results per call, 2.5k/day - use strategically.
        """
        try:
            radius_meters = int(tile.search_radius_miles * 1609.34)
            results = self.tomtom.search_all_categories(
                tile.center_lat, tile.center_lon, radius_meters
            )
            for biz in results:
                biz['source'] = 'tomtom'
            return results
        except Exception as e:
            logger.debug(f"TomTom tile search error: {e}")
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
        """Get tier for a category from unified taxonomy."""
        normalized = normalize_category_key(category)
        cat_config = CATEGORY_TAXONOMY.get(normalized, {})
        return cat_config.get('tier', 3)

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
