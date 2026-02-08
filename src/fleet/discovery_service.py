"""
Unified Fleet Discovery Service
===============================

Aggregates fleet location data from multiple FREE sources:
1. OpenStreetMap/Overpass API - Buildings, government, schools, businesses
2. FMCSA Database - Trucking companies with verified fleet sizes
3. Yelp Fusion API - Service businesses (landscaping, pest control, etc.)

All sources are FREE to use.
"""

import logging
import requests
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .fmcsa import FMCSADatabase
from .yelp_api import YelpFleetAPI
from .categories import FLEET_CATEGORIES, estimate_vehicles_by_category, normalize_category_key

logger = logging.getLogger('FleetDiscovery')


class FleetDiscoveryService:
    """Unified service for discovering all fleet locations in an area."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, yelp_api_key: str = None, db_path: str = None):
        """
        Initialize the fleet discovery service.

        Args:
            yelp_api_key: Optional Yelp API key (or set YELP_API_KEY env var)
            db_path: Path to the main database
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / 'data' / 'hailtracker_crm.db'

        self.db_path = str(db_path)
        self.fmcsa = FMCSADatabase()
        self.yelp = YelpFleetAPI(yelp_api_key)

    def discover_city(self, city: str, state: str,
                      bbox: Tuple[float, float, float, float] = None,
                      include_osm: bool = True,
                      include_fmcsa: bool = True,
                      include_yelp: bool = True) -> Dict:
        """
        Discover all fleet locations in a city using all data sources.

        Args:
            city: City name
            state: State abbreviation
            bbox: Optional (south, west, north, east) bounding box
            include_osm: Whether to search OSM/Overpass
            include_fmcsa: Whether to search FMCSA database
            include_yelp: Whether to search Yelp API

        Returns:
            Dict with locations from all sources and summary stats
        """
        results = {
            'city': city,
            'state': state,
            'sources': {},
            'all_locations': [],
            'stats': {},
            'errors': [],
        }

        # 1. OpenStreetMap/Overpass
        if include_osm:
            try:
                logger.info(f"[Discovery] Searching OSM for {city}, {state}...")
                osm_locations = self._search_osm(city, state, bbox)
                results['sources']['osm'] = len(osm_locations)
                results['all_locations'].extend(osm_locations)
                logger.info(f"[Discovery] OSM: Found {len(osm_locations)} locations")
            except Exception as e:
                logger.error(f"[Discovery] OSM error: {e}")
                results['errors'].append(f"OSM: {str(e)}")
                results['sources']['osm'] = 0

        # 2. FMCSA Database
        if include_fmcsa and self.fmcsa.is_populated():
            try:
                logger.info(f"[Discovery] Searching FMCSA database...")
                fmcsa_locations = self.fmcsa.search_by_city(city, state, min_vehicles=3)
                results['sources']['fmcsa'] = len(fmcsa_locations)

                # Convert FMCSA to standard format
                for loc in fmcsa_locations:
                    results['all_locations'].append({
                        'name': loc.get('name'),
                        'address': loc.get('physical_address'),
                        'city': loc.get('physical_city') or city,
                        'state': loc.get('physical_state') or state,
                        'zip': loc.get('physical_zip'),
                        'phone': loc.get('phone'),
                        'latitude': loc.get('latitude'),
                        'longitude': loc.get('longitude'),
                        'category': loc.get('category', 'delivery'),
                        'vehicle_count': loc.get('vehicle_count', 0),
                        'source': 'FMCSA',
                        'verified_fleet': True,
                        'power_units': loc.get('power_units'),
                        'drivers': loc.get('drivers'),
                        'dot_number': loc.get('dot_number'),
                    })

                logger.info(f"[Discovery] FMCSA: Found {len(fmcsa_locations)} carriers")
            except Exception as e:
                logger.error(f"[Discovery] FMCSA error: {e}")
                results['errors'].append(f"FMCSA: {str(e)}")
                results['sources']['fmcsa'] = 0
        else:
            results['sources']['fmcsa'] = 0
            if include_fmcsa:
                results['errors'].append("FMCSA: Database not populated")

        # 3. Yelp API
        if include_yelp and self.yelp.is_available():
            try:
                logger.info(f"[Discovery] Searching Yelp for service businesses...")
                yelp_locations = self.yelp.search_fleet_businesses(city, state)
                results['sources']['yelp'] = len(yelp_locations)
                results['all_locations'].extend(yelp_locations)
                logger.info(f"[Discovery] Yelp: Found {len(yelp_locations)} businesses")
            except Exception as e:
                logger.error(f"[Discovery] Yelp error: {e}")
                results['errors'].append(f"Yelp: {str(e)}")
                results['sources']['yelp'] = 0
        else:
            results['sources']['yelp'] = 0
            if include_yelp and not self.yelp.is_available():
                results['errors'].append("Yelp: API key not configured")

        # Deduplicate by name similarity and location
        results['all_locations'] = self._deduplicate(results['all_locations'])

        # Calculate stats
        results['stats'] = self._calculate_stats(results['all_locations'])

        logger.info(f"[Discovery] Complete: {results['stats']['total_locations']} locations, "
                    f"~{results['stats']['total_estimated_vehicles']} vehicles")

        return results

    def _search_osm(self, city: str, state: str,
                    bbox: Tuple[float, float, float, float] = None) -> List[Dict]:
        """Search OSM using Overpass API for all fleet-relevant categories."""
        locations = []

        # Build bounding box if not provided
        if bbox is None:
            bbox = self._get_city_bbox(city, state)
            if bbox is None:
                logger.warning(f"Could not determine bbox for {city}, {state}")
                return []

        south, west, north, east = bbox

        # Build comprehensive Overpass query for all categories
        for category, config in FLEET_CATEGORIES.items():
            osm_tags = config.get('osm_tags', [])
            if not osm_tags:
                continue

            # Build query parts for this category
            query_parts = []
            for tag_dict in osm_tags:
                for key, value in tag_dict.items():
                    if value == '*':
                        query_parts.append(f'node["{key}"]({south},{west},{north},{east});')
                        query_parts.append(f'way["{key}"]({south},{west},{north},{east});')
                    else:
                        query_parts.append(f'node["{key}"="{value}"]({south},{west},{north},{east});')
                        query_parts.append(f'way["{key}"="{value}"]({south},{west},{north},{east});')

            if not query_parts:
                continue

            query = f"""
[out:json][timeout:30];
(
{chr(10).join('  ' + p for p in query_parts)}
);
out center meta;
"""

            try:
                response = requests.post(
                    self.OVERPASS_URL,
                    data={'data': query},
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()

                elements = data.get('elements', [])

                for elem in elements:
                    tags = elem.get('tags', {})
                    name = tags.get('name', '')

                    if not name:
                        continue

                    # Get coordinates
                    if elem.get('type') == 'way':
                        lat = elem.get('center', {}).get('lat', 0)
                        lon = elem.get('center', {}).get('lon', 0)
                    else:
                        lat = elem.get('lat', 0)
                        lon = elem.get('lon', 0)

                    if not lat or not lon:
                        continue

                    # Build address
                    addr_parts = []
                    if tags.get('addr:housenumber'):
                        addr_parts.append(tags['addr:housenumber'])
                    if tags.get('addr:street'):
                        addr_parts.append(tags['addr:street'])
                    address = ' '.join(addr_parts) if addr_parts else ""

                    locations.append({
                        'name': name,
                        'address': address,
                        'city': tags.get('addr:city', city),
                        'state': tags.get('addr:state', state),
                        'zip': tags.get('addr:postcode', ''),
                        'phone': tags.get('phone') or tags.get('contact:phone', ''),
                        'website': tags.get('website') or tags.get('contact:website', ''),
                        'latitude': lat,
                        'longitude': lon,
                        'category': category,
                        'vehicle_count': config.get('est_vehicles', 10),
                        'source': 'OSM',
                        'osm_id': str(elem.get('id', '')),
                        'osm_type': elem.get('type', ''),
                        'operating_hours': tags.get('opening_hours', ''),
                    })

                # Rate limit to be nice to Overpass
                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"OSM query error for {category}: {e}")
                continue

        return locations

    def _get_city_bbox(self, city: str, state: str) -> Optional[Tuple[float, float, float, float]]:
        """Get bounding box for a city using Nominatim."""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': f"{city}, {state}, USA",
                'format': 'json',
                'limit': 1,
            }
            response = requests.get(url, params=params,
                                    headers={'User-Agent': 'HailTrackerPro/1.0'},
                                    timeout=30)
            data = response.json()

            if data and data[0].get('boundingbox'):
                bb = data[0]['boundingbox']
                # Nominatim returns [south, north, west, east]
                return (float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3]))

        except Exception as e:
            logger.warning(f"Could not get bbox for {city}, {state}: {e}")

        return None

    def _deduplicate(self, locations: List[Dict]) -> List[Dict]:
        """Remove duplicate locations based on name and address similarity."""
        seen = {}
        unique = []

        for loc in locations:
            # Create a key from name and rough location
            name = (loc.get('name') or '').lower().strip()
            lat = round(loc.get('latitude') or 0, 3)
            lon = round(loc.get('longitude') or 0, 3)

            # Use first 20 chars of name + rough coordinates as key
            key = f"{name[:20]}_{lat}_{lon}"

            if key not in seen:
                seen[key] = loc
                unique.append(loc)
            else:
                # Keep the one with more data (higher vehicle count, has phone, etc.)
                existing = seen[key]
                new_score = self._score_location(loc)
                old_score = self._score_location(existing)

                if new_score > old_score:
                    seen[key] = loc
                    unique = [l for l in unique if l != existing]
                    unique.append(loc)

        return unique

    def _score_location(self, loc: Dict) -> int:
        """Score a location by data completeness."""
        score = 0
        if loc.get('phone'):
            score += 10
        if loc.get('website') or loc.get('url'):
            score += 5
        if loc.get('address'):
            score += 5
        if loc.get('verified_fleet'):
            score += 20
        score += min(loc.get('vehicle_count', 0), 100)  # Cap at 100
        return score

    def _calculate_stats(self, locations: List[Dict]) -> Dict:
        """Calculate summary statistics."""
        total_vehicles = sum(loc.get('vehicle_count', 0) for loc in locations)

        # Count by category
        by_category = {}
        for loc in locations:
            cat = loc.get('category', 'other')
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by source
        by_source = {}
        for loc in locations:
            src = loc.get('source', 'unknown')
            by_source[src] = by_source.get(src, 0) + 1

        # Count by tier
        by_tier = {'tier_1': 0, 'tier_2': 0, 'tier_3': 0}
        for loc in locations:
            cat = loc.get('category', '')
            cat_config = FLEET_CATEGORIES.get(cat, {})
            tier = cat_config.get('tier', 3)
            by_tier[f'tier_{tier}'] = by_tier.get(f'tier_{tier}', 0) + 1

        # Count verified fleets
        verified_count = sum(1 for loc in locations if loc.get('verified_fleet'))

        return {
            'total_locations': len(locations),
            'total_estimated_vehicles': total_vehicles,
            'by_category': dict(sorted(by_category.items(), key=lambda x: -x[1])),
            'by_source': by_source,
            'by_tier': by_tier,
            'verified_fleets': verified_count,
            'average_vehicles_per_location': round(total_vehicles / max(len(locations), 1), 1),
        }

    def get_data_sources_status(self) -> List[Dict]:
        """Return information about available data sources."""
        return [
            {
                'name': 'OpenStreetMap',
                'status': 'active',
                'description': 'Buildings, government, schools, parking',
                'cost': 'FREE',
                'rate_limit': '~10K requests/day',
            },
            {
                'name': 'FMCSA Database',
                'status': 'active' if self.fmcsa.is_populated() else 'needs_import',
                'description': 'Trucking companies with verified fleet sizes',
                'cost': 'FREE',
                'carriers': self.fmcsa.get_stats().get('total_carriers', 0) if self.fmcsa.is_populated() else 0,
            },
            {
                'name': 'Yelp Fusion API',
                'status': 'active' if self.yelp.is_available() else 'needs_api_key',
                'description': 'Service businesses (landscaping, pest control, etc.)',
                'cost': 'FREE (5,000 calls/day)',
                'signup_url': 'https://www.yelp.com/developers/v3/manage_app',
            },
        ]
