"""
Unified Business Discovery Service
===================================

Combines all scrapers to find fleet-relevant businesses.
Aggregates data from:
- Yellow Pages (yp.com)
- Google Maps Search
- Better Business Bureau (bbb.org)
- Manta.com business directory

All sources are 100% FREE to use.
"""

from typing import List, Dict, Optional, Tuple
import sqlite3
import logging
from pathlib import Path

from .yellowpages import YellowPagesScraper
from .google_places import GooglePlacesScraper
from .bbb import BBBScraper
from .manta import MantaScraper
from .geocoding import GeocodingService

logger = logging.getLogger('BusinessDiscovery')


class BusinessDiscoveryService:
    """
    Unified service for discovering all fleet-relevant businesses.

    Coordinates multiple scrapers to build a comprehensive database
    of businesses that have vehicle fleets.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the discovery service.

        Args:
            db_path: Path to SQLite database for storing results
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / 'data' / 'business_prospects.db'

        self.db_path = str(db_path)

        # Initialize scrapers
        self.yellowpages = YellowPagesScraper(self.db_path)
        self.google = GooglePlacesScraper(self.db_path)
        self.bbb = BBBScraper(self.db_path)
        self.manta = MantaScraper(self.db_path)

        # Initialize geocoding service
        self.geocoder = GeocodingService(self.db_path)

    def discover_city(self, city: str, state: str,
                      sources: List[str] = None,
                      categories: List[str] = None,
                      tier: int = None,
                      geocode: bool = False) -> Dict:
        """
        Discover all fleet-relevant businesses in a city.

        Args:
            city: City name
            state: State abbreviation (e.g., 'TX')
            sources: Which sources to use ['yellowpages', 'google', 'bbb', 'manta']
                    Default: ['bbb', 'manta'] (most reliable)
            categories: Which categories to search (YP search terms)
                       Default: all categories
            tier: Only search categories for this tier (1, 2, or 3)
                 Default: all tiers
            geocode: Whether to geocode businesses after scraping

        Returns:
            Dict with results summary and stats
        """
        if sources is None:
            # Default to BBB and Manta - most reliable free sources
            sources = ['bbb', 'manta']

        # Filter categories by tier if specified
        if tier and categories is None:
            categories = self.yellowpages.get_priority_categories(tier)

        results = {
            'city': city,
            'state': state,
            'sources': {},
            'total_new': 0,
            'errors': [],
        }

        total_sources = len(sources)
        source_index = 0

        logger.info(f"\n{'='*70}")
        logger.info(f"DISCOVERING FLEET PROSPECTS IN {city.upper()}, {state.upper()}")
        logger.info(f"Sources: {sources}")
        logger.info(f"{'='*70}")

        # Run each scraper
        if 'yellowpages' in sources:
            source_index += 1
            try:
                logger.info(f"\n[{source_index}/{total_sources}] Scraping Yellow Pages...")
                count = self.yellowpages.scrape_city(city, state, categories)
                results['sources']['yellowpages'] = count
                results['total_new'] += count
            except Exception as e:
                logger.error(f"Yellow Pages error: {e}")
                results['errors'].append(f"YellowPages: {str(e)}")
                results['sources']['yellowpages'] = 0

        if 'google' in sources:
            source_index += 1
            try:
                logger.info(f"\n[{source_index}/{total_sources}] Scraping Google...")
                # Use a subset of categories for Google (rate limited)
                google_cats = (categories or list(self.google.SEARCH_CATEGORIES.keys()))[:10]
                count = self.google.scrape_city(city, state, google_cats)
                results['sources']['google'] = count
                results['total_new'] += count
            except Exception as e:
                logger.error(f"Google error: {e}")
                results['errors'].append(f"Google: {str(e)}")
                results['sources']['google'] = 0

        if 'bbb' in sources:
            source_index += 1
            try:
                logger.info(f"\n[{source_index}/{total_sources}] Scraping BBB...")
                # Map YP categories to BBB categories if needed
                bbb_cats = None
                if categories:
                    bbb_cats = self._map_to_bbb_categories(categories)
                count = self.bbb.scrape_city(city, state, bbb_cats)
                results['sources']['bbb'] = count
                results['total_new'] += count
            except Exception as e:
                logger.error(f"BBB error: {e}")
                results['errors'].append(f"BBB: {str(e)}")
                results['sources']['bbb'] = 0

        if 'manta' in sources:
            source_index += 1
            try:
                logger.info(f"\n[{source_index}/{total_sources}] Scraping Manta...")
                # Map YP categories to Manta categories if needed
                manta_cats = None
                if categories:
                    manta_cats = self._map_to_manta_categories(categories)
                count = self.manta.scrape_city(city, state, manta_cats)
                results['sources']['manta'] = count
                results['total_new'] += count
            except Exception as e:
                logger.error(f"Manta error: {e}")
                results['errors'].append(f"Manta: {str(e)}")
                results['sources']['manta'] = 0

        # Geocode if requested
        if geocode and results['total_new'] > 0:
            logger.info(f"\nGeocoding {results['total_new']} new businesses...")
            try:
                geocoded = self.geocoder.geocode_businesses_in_db(limit=results['total_new'])
                results['geocoded'] = geocoded
            except Exception as e:
                logger.error(f"Geocoding error: {e}")
                results['errors'].append(f"Geocoding: {str(e)}")

        # Get final stats
        results['stats'] = self.get_city_stats(city, state)

        logger.info(f"\n{'='*70}")
        logger.info(f"DISCOVERY COMPLETE: {city}, {state}")
        logger.info(f"{'='*70}")
        logger.info(f"New businesses added: {results['total_new']}")
        logger.info(f"By source: {results['sources']}")

        if results['stats']:
            logger.info(f"Total in database: {results['stats']['total']}")
            logger.info(f"Estimated vehicles: {results['stats']['total_vehicles']}")

        if results['errors']:
            logger.warning(f"Errors: {results['errors']}")

        return results

    def _map_to_bbb_categories(self, yp_categories: List[str]) -> List[str]:
        """Map Yellow Pages search terms to BBB category slugs."""
        mapping = {
            'car dealers': 'auto-dealers-new-cars',
            'used car dealers': 'auto-dealers-used-cars',
            'landscaping': 'landscape-contractors',
            'lawn care': 'lawn-maintenance',
            'pest control': 'pest-control-services',
            'hvac': 'air-conditioning-contractors-systems',
            'plumbers': 'plumbers',
            'electricians': 'electricians',
            'roofing': 'roofing-contractors',
            'moving companies': 'movers',
            'security': 'security-control-equipment-systems-monitors',
            'towing': 'towing-automotive',
            'tree service': 'tree-service',
            'garage doors': 'garage-doors-openers',
        }

        bbb_cats = []
        for yp_cat in yp_categories:
            yp_lower = yp_cat.lower()
            for key, bbb_slug in mapping.items():
                if key in yp_lower:
                    bbb_cats.append(bbb_slug)
                    break

        return bbb_cats if bbb_cats else None

    def _map_to_manta_categories(self, yp_categories: List[str]) -> List[str]:
        """Map Yellow Pages search terms to Manta search terms."""
        mapping = {
            'car dealers': 'automobile dealers',
            'landscaping': 'landscaping services',
            'pest control': 'pest control',
            'hvac': 'hvac contractors',
            'plumbers': 'plumbers',
            'electricians': 'electricians',
            'roofing': 'roofing contractors',
            'moving companies': 'moving companies',
            'security': 'security services',
            'towing': 'towing services',
            'tree service': 'tree service',
            'garage doors': 'garage door',
        }

        manta_cats = []
        for yp_cat in yp_categories:
            yp_lower = yp_cat.lower()
            for key, manta_term in mapping.items():
                if key in yp_lower:
                    manta_cats.append(manta_term)
                    break

        return manta_cats if manta_cats else None

    def get_city_stats(self, city: str, state: str) -> Dict:
        """Get statistics for a specific city."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Total count and vehicles
        cursor.execute('''
            SELECT COUNT(*) as total, SUM(estimated_vehicles) as vehicles
            FROM businesses
            WHERE LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)
        ''', (city, state))

        row = cursor.fetchone()
        total = row['total'] or 0
        vehicles = row['vehicles'] or 0

        # By category
        cursor.execute('''
            SELECT category, COUNT(*) as count, SUM(estimated_vehicles) as vehicles
            FROM businesses
            WHERE LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)
            GROUP BY category
            ORDER BY SUM(estimated_vehicles) DESC
        ''', (city, state))

        by_category = [dict(row) for row in cursor.fetchall()]

        # By tier
        cursor.execute('''
            SELECT tier, COUNT(*) as count, SUM(estimated_vehicles) as vehicles
            FROM businesses
            WHERE LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)
            GROUP BY tier
            ORDER BY tier
        ''', (city, state))

        by_tier = [dict(row) for row in cursor.fetchall()]

        # By source
        cursor.execute('''
            SELECT source, COUNT(*) as count
            FROM businesses
            WHERE LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)
            GROUP BY source
        ''', (city, state))

        by_source = [dict(row) for row in cursor.fetchall()]

        # Count with coordinates
        cursor.execute('''
            SELECT COUNT(*) as geocoded
            FROM businesses
            WHERE LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)
              AND latitude IS NOT NULL AND longitude IS NOT NULL
        ''', (city, state))

        geocoded = cursor.fetchone()['geocoded'] or 0

        conn.close()

        return {
            'total': total,
            'total_vehicles': vehicles,
            'geocoded': geocoded,
            'by_category': by_category,
            'by_tier': by_tier,
            'by_source': by_source,
        }

    def search_businesses(self, city: str, state: str,
                          category: str = None,
                          min_vehicles: int = 0,
                          tier: int = None,
                          source: str = None,
                          geocoded_only: bool = False,
                          limit: int = 500) -> List[Dict]:
        """
        Search the database for businesses.

        Args:
            city: City name
            state: State abbreviation
            category: Filter by category
            min_vehicles: Minimum estimated vehicles
            tier: Filter by tier (1, 2, or 3)
            source: Filter by source (YellowPages, BBB, Google, Manta)
            geocoded_only: Only return businesses with coordinates
            limit: Maximum results to return

        Returns:
            List of business dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = '''
            SELECT * FROM businesses
            WHERE LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)
            AND estimated_vehicles >= ?
        '''
        params = [city, state, min_vehicles]

        if category:
            query += ' AND category = ?'
            params.append(category)

        if tier:
            query += ' AND tier = ?'
            params.append(tier)

        if source:
            query += ' AND source = ?'
            params.append(source)

        if geocoded_only:
            query += ' AND latitude IS NOT NULL AND longitude IS NOT NULL'

        query += ' ORDER BY estimated_vehicles DESC, tier ASC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)

        businesses = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return businesses

    def get_businesses_for_map(self, city: str = None, state: str = None,
                               bounds: Dict = None,
                               limit: int = 500) -> List[Dict]:
        """
        Get businesses with coordinates for map display.

        Args:
            city: Optional city filter
            state: Optional state filter
            bounds: Optional map bounds dict with north, south, east, west
            limit: Maximum results

        Returns:
            List of businesses with lat/lon for map markers
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = '''
            SELECT id, name, category, tier, estimated_vehicles,
                   address, city, state, zip, phone, website,
                   latitude, longitude, source, bbb_accredited
            FROM businesses
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        '''
        params = []

        if city and state:
            query += ' AND LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)'
            params.extend([city, state])

        if bounds:
            query += ''' AND latitude BETWEEN ? AND ?
                        AND longitude BETWEEN ? AND ?'''
            params.extend([bounds['south'], bounds['north'],
                          bounds['west'], bounds['east']])

        query += ' ORDER BY estimated_vehicles DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)

        businesses = []
        for row in cursor.fetchall():
            biz = dict(row)
            # Format for map marker
            biz['marker'] = {
                'lat': biz['latitude'],
                'lng': biz['longitude'],
                'title': biz['name'],
                'category': biz['category'],
                'tier': biz['tier'],
                'vehicles': biz['estimated_vehicles'],
            }
            businesses.append(biz)

        conn.close()
        return businesses

    def get_top_prospects(self, city: str, state: str,
                          limit: int = 50) -> List[Dict]:
        """
        Get top prospects for a city, sorted by potential value.

        Args:
            city: City name
            state: State abbreviation
            limit: Number of results

        Returns:
            List of top business prospects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Score formula: vehicles * tier_multiplier + bbb_bonus + review_bonus
        cursor.execute('''
            SELECT *,
                (estimated_vehicles * CASE tier
                    WHEN 1 THEN 3
                    WHEN 2 THEN 2
                    ELSE 1
                END) +
                (CASE WHEN bbb_accredited = 1 THEN 50 ELSE 0 END) +
                (COALESCE(review_count, 0) / 10) as prospect_score
            FROM businesses
            WHERE LOWER(city) = LOWER(?) AND UPPER(state) = UPPER(?)
            ORDER BY prospect_score DESC
            LIMIT ?
        ''', (city, state, limit))

        businesses = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return businesses

    def geocode_city_businesses(self, city: str, state: str,
                                 limit: int = 200) -> int:
        """
        Geocode businesses in a specific city.

        Args:
            city: City name
            state: State abbreviation
            limit: Maximum to geocode

        Returns:
            Number of businesses geocoded
        """
        return self.geocoder.geocode_businesses_in_db(limit=limit)

    def get_database_stats(self) -> Dict:
        """Get overall database statistics."""
        stats = self.yellowpages.get_stats()

        # Add geocoding stats
        geo_stats = self.geocoder.get_cache_stats()
        stats['geocode_cache'] = geo_stats

        return stats

    def export_to_csv(self, city: str, state: str,
                      filename: str = None) -> str:
        """
        Export businesses for a city to CSV.

        Args:
            city: City name
            state: State abbreviation
            filename: Output filename (default: city_state_prospects.csv)

        Returns:
            Path to the created CSV file
        """
        import csv
        from pathlib import Path

        if filename is None:
            filename = f"{city.lower().replace(' ', '_')}_{state.lower()}_prospects.csv"

        businesses = self.search_businesses(city, state, limit=10000)

        if not businesses:
            return None

        output_path = Path(self.db_path).parent / filename

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=businesses[0].keys())
            writer.writeheader()
            writer.writerows(businesses)

        logger.info(f"Exported {len(businesses)} businesses to {output_path}")
        return str(output_path)


# Convenience function
def discover_city(city: str, state: str,
                  sources: List[str] = None,
                  geocode: bool = False) -> Dict:
    """
    Quick function to discover businesses in a city.

    Args:
        city: City name
        state: State abbreviation
        sources: Optional list of sources
        geocode: Whether to geocode results

    Returns:
        Discovery results dictionary
    """
    service = BusinessDiscoveryService()
    return service.discover_city(city, state, sources=sources, geocode=geocode)
