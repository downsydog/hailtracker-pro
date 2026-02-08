"""
Fleet Locations API Routes
==========================
API for fleet location intelligence (business prospect discovery).

Multi-source discovery using FREE APIs:
- OpenStreetMap/Overpass API
- FMCSA Database (trucking companies)
- Yelp Fusion API (service businesses)

Endpoints:
- GET    /api/fleet-locations               - List locations with filters
- GET    /api/fleet-locations/search        - Search locations
- GET    /api/fleet-locations/bbox          - Get locations in bounding box
- GET    /api/fleet-locations/nearby        - Get locations near a point
- GET    /api/fleet-locations/categories    - Get category summary
- GET    /api/fleet-locations/stats         - Get overall stats
- POST   /api/fleet-locations/discover      - Discover fleet locations (multi-source)
- GET    /api/fleet-locations/cities        - Get unique cities in database
- GET    /api/fleet-locations/sources       - Get data source status
- GET    /api/fleet-locations/category-info - Get all category definitions
"""

from flask import Blueprint, request, jsonify, g
from src.core.auth.decorators import login_required, require_any_permission
import os
import logging
import sqlite3
import json

logger = logging.getLogger('FleetLocationsAPI')

fleet_locations_api_bp = Blueprint('fleet_locations_api', __name__, url_prefix='/api/fleet-locations')


def get_fleet_manager():
    """Get FleetLocationManager instance"""
    from src.business.fleet_locations import FleetLocationManager
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return FleetLocationManager(db_path)


def get_discovery_service():
    """Get FleetDiscoveryService instance"""
    try:
        from src.fleet.discovery_service import FleetDiscoveryService
        return FleetDiscoveryService()
    except ImportError:
        logger.warning("FleetDiscoveryService not available")
        return None


@fleet_locations_api_bp.route('')
@login_required
@require_any_permission('leads.view_all', 'leads.view_own', 'admin.access')
def list_locations():
    """List fleet locations with filtering and pagination"""
    manager = get_fleet_manager()

    # Filters
    category = request.args.get('category')
    min_vehicles = request.args.get('min_vehicles', 0, type=int)
    search = request.args.get('search', '').strip()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    per_page = min(per_page, 500)
    offset = (page - 1) * per_page

    try:
        conn = manager._get_conn()

        # Build query
        where_clauses = ['1=1']
        params = []

        if category and category != 'all':
            where_clauses.append('fl.category = ?')
            params.append(category)

        if min_vehicles > 0:
            where_clauses.append('fl.estimated_vehicles >= ?')
            params.append(min_vehicles)

        if search:
            where_clauses.append('(fl.name LIKE ? OR fl.city LIKE ? OR fl.address LIKE ?)')
            params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

        where_sql = ' AND '.join(where_clauses)

        # Get count
        count_query = f"SELECT COUNT(*) FROM fleet_locations fl WHERE {where_sql}"
        total = conn.execute(count_query, params).fetchone()[0]

        # Get locations
        query = f"""
            SELECT fl.*, fc.icon, fc.color, fc.tier, fc.display_name as category_name
            FROM fleet_locations fl
            LEFT JOIN fleet_categories fc ON fl.category = fc.category
            WHERE {where_sql}
            ORDER BY fl.estimated_vehicles DESC
            LIMIT ? OFFSET ?
        """
        params.extend([per_page, offset])

        rows = conn.execute(query, params).fetchall()
        locations = [dict(row) for row in rows]

        conn.close()

        return jsonify({
            'locations': locations,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/search')
@login_required
def search_locations():
    """Search locations by name, address, or category"""
    manager = get_fleet_manager()

    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 100)

    if not query:
        return jsonify({'locations': []})

    try:
        locations = manager.search_locations(query, limit)
        return jsonify({'locations': locations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/bbox')
@login_required
def locations_in_bbox():
    """Get locations within a bounding box"""
    manager = get_fleet_manager()

    try:
        south = request.args.get('south', type=float)
        west = request.args.get('west', type=float)
        north = request.args.get('north', type=float)
        east = request.args.get('east', type=float)

        if None in [south, west, north, east]:
            return jsonify({'error': 'Missing bounding box parameters (south, west, north, east)'}), 400

        categories = request.args.getlist('category')
        if not categories:
            categories = None

        locations = manager.get_locations_in_bbox(south, west, north, east, categories)
        return jsonify({'locations': locations})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/nearby')
@login_required
def locations_nearby():
    """Get locations near a point within radius"""
    manager = get_fleet_manager()

    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius_km = request.args.get('radius', 50, type=float)
        min_vehicles = request.args.get('min_vehicles', 0, type=int)

        if lat is None or lon is None:
            return jsonify({'error': 'Missing lat/lon parameters'}), 400

        categories = request.args.getlist('category')
        if not categories:
            categories = None

        locations = manager.get_locations_near_point(
            lat, lon, radius_km, categories, min_vehicles
        )
        return jsonify({'locations': locations})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/categories')
@login_required
def category_summary():
    """Get summary of locations by category"""
    manager = get_fleet_manager()

    try:
        categories = manager.get_category_summary()
        return jsonify({'categories': categories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/stats')
@login_required
def location_stats():
    """Get overall fleet location statistics"""
    manager = get_fleet_manager()

    try:
        conn = manager._get_conn()

        # Get overall stats
        stats = conn.execute("""
            SELECT
                COUNT(*) as total_locations,
                SUM(estimated_vehicles) as total_vehicles,
                COUNT(DISTINCT category) as categories,
                ROUND(SUM(estimated_vehicles * avg_revenue_per_vehicle), 0) as potential_revenue
            FROM fleet_locations
        """).fetchone()

        # Get top categories
        top_categories = conn.execute("""
            SELECT category, COUNT(*) as count, SUM(estimated_vehicles) as vehicles
            FROM fleet_locations
            GROUP BY category
            ORDER BY vehicles DESC
            LIMIT 5
        """).fetchall()

        conn.close()

        return jsonify({
            'total_locations': stats['total_locations'] or 0,
            'total_vehicles': stats['total_vehicles'] or 0,
            'categories': stats['categories'] or 0,
            'potential_revenue': stats['potential_revenue'] or 0,
            'top_categories': [dict(c) for c in top_categories]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/discover', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def discover_city():
    """
    Discover fleet locations for a city using multiple FREE data sources:
    - OpenStreetMap/Overpass API (buildings, government, schools)
    - FMCSA Database (trucking companies with verified fleet sizes)
    - Yelp Fusion API (service businesses)

    POST body:
    {
        "city": "Denver",
        "state": "CO",
        "bbox": [south, west, north, east],  // optional
        "sources": ["osm", "fmcsa", "yelp"]  // optional, defaults to all
    }
    """
    manager = get_fleet_manager()
    discovery = get_discovery_service()

    data = request.get_json() or {}
    city = data.get('city', '').strip()
    state = data.get('state', '').strip()
    bbox = data.get('bbox')  # Optional [south, west, north, east]
    sources = data.get('sources', ['osm', 'fmcsa', 'yelp'])

    if not city or not state:
        return jsonify({'error': 'City and state are required'}), 400

    # Convert bbox list to tuple if provided
    bbox_tuple = None
    if bbox and len(bbox) == 4:
        bbox_tuple = tuple(bbox)

    try:
        # Check existing count for this city
        conn = manager._get_conn()
        existing = conn.execute(
            "SELECT COUNT(*) FROM fleet_locations WHERE LOWER(city) = LOWER(?) AND LOWER(state) = LOWER(?)",
            (city, state)
        ).fetchone()[0]
        conn.close()

        # Try new multi-source discovery first
        if discovery:
            logger.info(f"Running multi-source discovery for {city}, {state}")
            discovery_results = discovery.discover_city(
                city, state, bbox_tuple,
                include_osm='osm' in sources,
                include_fmcsa='fmcsa' in sources,
                include_yelp='yelp' in sources
            )

            # Save discovered locations to database
            saved_count = 0
            for loc in discovery_results.get('all_locations', []):
                if loc.get('latitude') and loc.get('longitude'):
                    try:
                        manager.save_locations([_dict_to_fleet_location(loc, city, state)])
                        saved_count += 1
                    except Exception as e:
                        logger.warning(f"Error saving location: {e}")
                        continue

            # Get new total
            conn = manager._get_conn()
            new_total = conn.execute(
                "SELECT COUNT(*) FROM fleet_locations WHERE LOWER(city) = LOWER(?) AND LOWER(state) = LOWER(?)",
                (city, state)
            ).fetchone()[0]
            conn.close()

            return jsonify({
                'success': True,
                'city': city,
                'state': state,
                'existing_locations': existing,
                'new_locations': saved_count,
                'total_locations': new_total,
                'sources_searched': discovery_results.get('sources', {}),
                'stats': discovery_results.get('stats', {}),
                'errors': discovery_results.get('errors', []),
            })

        # Fallback to original OSM-only discovery
        else:
            logger.info(f"Running OSM-only discovery for {city}, {state}")
            results = manager.seed_city(city, state, bbox_tuple)

            conn = manager._get_conn()
            new_total = conn.execute(
                "SELECT COUNT(*) FROM fleet_locations WHERE LOWER(city) = LOWER(?) AND LOWER(state) = LOWER(?)",
                (city, state)
            ).fetchone()[0]
            conn.close()

            return jsonify({
                'success': True,
                'city': city,
                'state': state,
                'existing_locations': existing,
                'new_locations': results.get('total', 0),
                'total_locations': new_total,
                'sources_searched': {'osm': results.get('total', 0)},
                'by_category': {k: v for k, v in results.items() if k != 'total'}
            })

    except Exception as e:
        import traceback
        logger.error(f"Discovery error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


def _dict_to_fleet_location(loc: dict, default_city: str, default_state: str):
    """Convert discovery result dict to FleetLocation object."""
    from src.business.fleet_locations import FleetLocation

    return FleetLocation(
        name=loc.get('name', ''),
        category=loc.get('category', 'other'),
        address=loc.get('address', ''),
        city=loc.get('city') or default_city,
        state=loc.get('state') or default_state,
        zip_code=loc.get('zip', ''),
        lat=loc.get('latitude', 0),
        lon=loc.get('longitude', 0),
        phone=loc.get('phone', ''),
        website=loc.get('website') or loc.get('url', ''),
        estimated_vehicles=loc.get('vehicle_count', 10),
        osm_id=loc.get('osm_id', ''),
        osm_type=loc.get('osm_type', ''),
        data_source=loc.get('source', 'DISCOVERY'),
    )


@fleet_locations_api_bp.route('/cities')
@login_required
def list_cities():
    """Get unique cities with location counts from the database"""
    manager = get_fleet_manager()

    try:
        conn = manager._get_conn()

        rows = conn.execute("""
            SELECT
                city,
                state,
                COUNT(*) as location_count,
                SUM(estimated_vehicles) as total_vehicles
            FROM fleet_locations
            WHERE city IS NOT NULL AND city != ''
            GROUP BY LOWER(city), LOWER(state)
            ORDER BY total_vehicles DESC
        """).fetchall()

        conn.close()

        cities = [
            {
                'city': row['city'],
                'state': row['state'],
                'location_count': row['location_count'],
                'total_vehicles': row['total_vehicles'] or 0
            }
            for row in rows
        ]

        return jsonify({'cities': cities})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/sources')
@login_required
def get_data_sources():
    """Get status of all available data sources."""
    discovery = get_discovery_service()

    if discovery:
        sources = discovery.get_data_sources_status()
    else:
        sources = [
            {
                'name': 'OpenStreetMap',
                'status': 'active',
                'description': 'Buildings, government, schools, parking',
                'cost': 'FREE',
            },
            {
                'name': 'FMCSA Database',
                'status': 'not_configured',
                'description': 'Trucking companies with verified fleet sizes',
                'cost': 'FREE',
                'setup_url': 'https://ai.fmcsa.dot.gov/SMS/Tools/Downloads.aspx',
            },
            {
                'name': 'Yelp Fusion API',
                'status': 'not_configured',
                'description': 'Service businesses (landscaping, pest control, etc.)',
                'cost': 'FREE (5,000 calls/day)',
                'setup_url': 'https://www.yelp.com/developers/v3/manage_app',
            },
        ]

    return jsonify({'sources': sources})


@fleet_locations_api_bp.route('/category-info')
@login_required
def get_category_info():
    """Get all fleet category definitions with icons, colors, and estimated vehicles."""
    try:
        from src.fleet.categories import FLEET_CATEGORIES

        categories = []
        for key, config in FLEET_CATEGORIES.items():
            categories.append({
                'key': key,
                'name': config.get('name', key),
                'tier': config.get('tier', 3),
                'icon': config.get('icon', '📍'),
                'color': config.get('color', '#888888'),
                'est_vehicles': config.get('est_vehicles', 10),
                'keywords': config.get('keywords', []),
                'yelp_category': config.get('yelp_category'),
                'fmcsa': config.get('fmcsa', False),
            })

        # Sort by tier then name
        categories.sort(key=lambda x: (x['tier'], x['name']))

        return jsonify({
            'categories': categories,
            'tier_descriptions': {
                1: 'Highest Value - Big fleets, always pay',
                2: 'High Value - Solid fleet sizes',
                3: 'Good Opportunities - Smaller but worthwhile',
            }
        })

    except ImportError:
        # Fallback to basic categories if new module not available
        return jsonify({
            'categories': [
                {'key': 'car_dealership', 'name': 'Car Dealership', 'tier': 1, 'icon': '🚗', 'color': '#4CAF50'},
                {'key': 'car_rental', 'name': 'Car Rental', 'tier': 1, 'icon': '🔑', 'color': '#2196F3'},
                {'key': 'municipal', 'name': 'Municipal', 'tier': 1, 'icon': '🏛️', 'color': '#F44336'},
                {'key': 'hospital', 'name': 'Hospital', 'tier': 1, 'icon': '🏥', 'color': '#E91E63'},
                {'key': 'school_district', 'name': 'Schools', 'tier': 1, 'icon': '🏫', 'color': '#673AB7'},
            ]
        })


# =============================================================================
# BUSINESS SCRAPER ENDPOINTS
# =============================================================================

def get_business_discovery():
    """Get BusinessDiscoveryService instance."""
    try:
        from src.fleet.scrapers.discovery import BusinessDiscoveryService
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'business_prospects.db')
        return BusinessDiscoveryService(db_path)
    except ImportError:
        logger.warning("BusinessDiscoveryService not available")
        return None


@fleet_locations_api_bp.route('/scrape', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def scrape_businesses():
    """
    Scrape businesses for a city from multiple sources.

    POST body:
    {
        "city": "Dallas",
        "state": "TX",
        "sources": ["bbb", "manta"],  // optional, default: ['bbb', 'manta']
        "categories": ["landscaping", "pest control"],  // optional, default: all
        "tier": 2,  // optional, only scrape tier 2 categories
        "geocode": true  // optional, geocode after scraping (default: false)
    }
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Scraper service not available'}), 503

    data = request.get_json() or {}
    city = data.get('city', '').strip()
    state = data.get('state', '').strip()
    sources = data.get('sources')
    categories = data.get('categories')
    tier = data.get('tier')
    geocode = data.get('geocode', False)

    if not city or not state:
        return jsonify({'error': 'city and state are required'}), 400

    try:
        logger.info(f"Starting business scrape for {city}, {state}")

        results = discovery.discover_city(
            city, state,
            sources=sources,
            categories=categories,
            tier=tier,
            geocode=geocode
        )

        return jsonify({
            'success': True,
            'city': city,
            'state': state,
            'new_businesses': results['total_new'],
            'by_source': results['sources'],
            'stats': results['stats'],
            'geocoded': results.get('geocoded', 0),
            'errors': results.get('errors', []),
        })

    except Exception as e:
        import traceback
        logger.error(f"Scrape error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/businesses')
@login_required
def get_scraped_businesses():
    """
    Get scraped businesses for a city.

    Query params:
    - city: City name (required)
    - state: State abbreviation (required)
    - category: Filter by category
    - min_vehicles: Minimum estimated vehicles
    - tier: Filter by tier (1, 2, 3)
    - source: Filter by source (YellowPages, BBB, Google)
    - limit: Max results (default: 500)
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Scraper service not available'}), 503

    city = request.args.get('city')
    state = request.args.get('state')
    category = request.args.get('category')
    min_vehicles = request.args.get('min_vehicles', 0, type=int)
    tier = request.args.get('tier', type=int)
    source = request.args.get('source')
    limit = request.args.get('limit', 500, type=int)

    if not city or not state:
        return jsonify({'error': 'city and state are required'}), 400

    try:
        businesses = discovery.search_businesses(
            city, state,
            category=category,
            min_vehicles=min_vehicles,
            tier=tier,
            source=source,
            limit=limit
        )

        return jsonify({
            'city': city,
            'state': state,
            'count': len(businesses),
            'businesses': businesses
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/businesses/top-prospects')
@login_required
def get_top_prospects():
    """
    Get top prospects for a city, sorted by potential value.

    Query params:
    - city: City name (required)
    - state: State abbreviation (required)
    - limit: Max results (default: 50)
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Scraper service not available'}), 503

    city = request.args.get('city')
    state = request.args.get('state')
    limit = request.args.get('limit', 50, type=int)

    if not city or not state:
        return jsonify({'error': 'city and state are required'}), 400

    try:
        prospects = discovery.get_top_prospects(city, state, limit=limit)

        return jsonify({
            'city': city,
            'state': state,
            'count': len(prospects),
            'prospects': prospects
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/businesses/stats')
@login_required
def get_business_stats():
    """Get overall scraped business database statistics."""
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Scraper service not available'}), 503

    try:
        stats = discovery.get_database_stats()
        return jsonify(stats)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/businesses/export')
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def export_businesses():
    """
    Export businesses for a city to CSV.

    Query params:
    - city: City name (required)
    - state: State abbreviation (required)
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Scraper service not available'}), 503

    city = request.args.get('city')
    state = request.args.get('state')

    if not city or not state:
        return jsonify({'error': 'city and state are required'}), 400

    try:
        filepath = discovery.export_to_csv(city, state)

        if not filepath:
            return jsonify({'error': 'No businesses found to export'}), 404

        return jsonify({
            'success': True,
            'filepath': filepath
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/scraper-sources')
@login_required
def get_scraper_sources():
    """Get list of available scraper sources."""
    return jsonify({
        'sources': [
            {
                'id': 'bbb',
                'name': 'Better Business Bureau',
                'description': 'Verified/accredited businesses - highest quality leads',
                'cost': 'FREE',
                'reliability': 'Very High',
                'rate_limit': '~50 requests/hour recommended',
            },
            {
                'id': 'manta',
                'name': 'Manta.com',
                'description': 'Comprehensive business directory with employee counts',
                'cost': 'FREE',
                'reliability': 'High',
                'rate_limit': '~50 requests/hour recommended',
            },
            {
                'id': 'yellowpages',
                'name': 'Yellow Pages',
                'description': 'Service businesses (may require anti-detection)',
                'cost': 'FREE',
                'reliability': 'Medium',
                'rate_limit': '~100 requests/hour recommended',
            },
            {
                'id': 'google',
                'name': 'Google Maps',
                'description': 'Most comprehensive but has strong anti-bot measures',
                'cost': 'FREE',
                'reliability': 'Low',
                'rate_limit': 'Use sparingly - easily blocked',
            },
        ],
        'categories': {
            'tier1': [
                'car dealers', 'auto auctions', 'car rental',
            ],
            'tier2': [
                'landscaping', 'pest control', 'hvac', 'plumbers',
                'electricians', 'roofing', 'moving companies',
                'security services', 'property management', 'towing',
            ],
            'tier3': [
                'pool service', 'garage doors', 'carpet cleaning',
                'window cleaning', 'painters', 'tree service',
                'fencing', 'concrete contractors',
            ],
        }
    })


# =============================================================================
# GEOCODING ENDPOINTS
# =============================================================================

def get_geocoding_service():
    """Get GeocodingService instance."""
    try:
        from src.fleet.scrapers.geocoding import GeocodingService
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'business_prospects.db')
        return GeocodingService(db_path)
    except ImportError:
        logger.warning("GeocodingService not available")
        return None


@fleet_locations_api_bp.route('/geocode', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def geocode_businesses():
    """
    Geocode scraped businesses that don't have coordinates.

    POST body:
    {
        "city": "Dallas",  // optional filter
        "state": "TX",     // optional filter
        "limit": 100       // max businesses to geocode (default: 100)
    }
    """
    geocoder = get_geocoding_service()
    if not geocoder:
        return jsonify({'error': 'Geocoding service not available'}), 503

    data = request.get_json() or {}
    limit = data.get('limit', 100)

    try:
        logger.info(f"Starting geocoding (limit: {limit})")

        geocoded_count = geocoder.geocode_businesses_in_db(limit=limit)
        cache_stats = geocoder.get_cache_stats()

        return jsonify({
            'success': True,
            'geocoded': geocoded_count,
            'cache_stats': cache_stats
        })

    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/geocode/stats')
@login_required
def geocode_stats():
    """Get geocoding cache statistics."""
    geocoder = get_geocoding_service()
    if not geocoder:
        return jsonify({'error': 'Geocoding service not available'}), 503

    try:
        stats = geocoder.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# MAP DATA ENDPOINTS
# =============================================================================

@fleet_locations_api_bp.route('/businesses/map')
@login_required
def get_businesses_for_map():
    """
    Get businesses with coordinates for map display.

    Query params:
    - city: Optional city filter
    - state: Optional state filter
    - north, south, east, west: Optional bounding box
    - limit: Max results (default: 500)
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Service not available'}), 503

    city = request.args.get('city')
    state = request.args.get('state')
    limit = request.args.get('limit', 500, type=int)

    # Build bounds dict if provided
    bounds = None
    if all(request.args.get(k) for k in ['north', 'south', 'east', 'west']):
        bounds = {
            'north': request.args.get('north', type=float),
            'south': request.args.get('south', type=float),
            'east': request.args.get('east', type=float),
            'west': request.args.get('west', type=float),
        }

    try:
        businesses = discovery.get_businesses_for_map(
            city=city,
            state=state,
            bounds=bounds,
            limit=limit
        )

        return jsonify({
            'count': len(businesses),
            'businesses': businesses
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/businesses/city-stats')
@login_required
def get_city_stats():
    """
    Get statistics for a specific city.

    Query params:
    - city: City name (required)
    - state: State abbreviation (required)
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Service not available'}), 503

    city = request.args.get('city')
    state = request.args.get('state')

    if not city or not state:
        return jsonify({'error': 'city and state are required'}), 400

    try:
        stats = discovery.get_city_stats(city, state)
        return jsonify({
            'city': city,
            'state': state,
            'stats': stats
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# ROUTE OPTIMIZATION ENDPOINTS
# =============================================================================

@fleet_locations_api_bp.route('/optimize-route', methods=['POST'])
@login_required
def optimize_fleet_route():
    """
    Optimize route for visiting multiple fleet locations.
    Uses OSRM (free, open source routing engine).

    POST body:
    {
        "locations": [
            {"id": 1, "name": "...", "latitude": 32.7, "longitude": -96.8, "address": "..."},
            ...
        ],
        "start_location": {"latitude": 32.8, "longitude": -96.7}  // optional - your current location
    }

    Returns:
    {
        "success": true,
        "locations": [...],  // in optimized order
        "order": [0, 2, 1, 3],  // original indices in optimized order
        "total_distance_miles": 45.2,
        "total_time_minutes": 87,
        "route_geometry": {...},  // GeoJSON for map
        "legs": [...]
    }
    """
    try:
        from src.fleet.route_optimizer import optimize_route

        data = request.get_json()
        locations = data.get('locations', [])
        start_location = data.get('start_location')

        if len(locations) < 2:
            return jsonify({'success': False, 'error': 'Need at least 2 locations'}), 400

        result = optimize_route(locations, start_location)

        return jsonify(result)

    except ImportError:
        return jsonify({'error': 'Route optimizer not available'}), 503
    except Exception as e:
        logger.error(f"Route optimization error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@fleet_locations_api_bp.route('/directions', methods=['POST'])
@login_required
def get_route_directions():
    """
    Get turn-by-turn directions between two points.

    POST body:
    {
        "origin": {"latitude": 32.7, "longitude": -96.8},
        "destination": {"latitude": 32.9, "longitude": -96.6}
    }
    """
    try:
        from src.fleet.route_optimizer import get_directions

        data = request.get_json()
        origin = data.get('origin')
        destination = data.get('destination')

        if not origin or not destination:
            return jsonify({'success': False, 'error': 'Origin and destination required'}), 400

        result = get_directions(origin, destination)
        return jsonify(result)

    except ImportError:
        return jsonify({'error': 'Route optimizer not available'}), 503
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@fleet_locations_api_bp.route('/google-maps-url', methods=['POST'])
@login_required
def get_google_maps_url():
    """
    Generate a Google Maps directions URL for a route.

    POST body:
    {
        "locations": [
            {"latitude": 32.7, "longitude": -96.8},
            ...
        ]
    }
    """
    try:
        from src.fleet.route_optimizer import create_google_maps_url

        data = request.get_json()
        locations = data.get('locations', [])

        if not locations:
            return jsonify({'error': 'No locations provided'}), 400

        url = create_google_maps_url(locations)
        return jsonify({'success': True, 'url': url})

    except ImportError:
        return jsonify({'error': 'Route optimizer not available'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# MULTI-CITY BATCH SCRAPING ENDPOINTS
# =============================================================================

@fleet_locations_api_bp.route('/scrape-multiple', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def scrape_multiple_cities():
    """
    Scrape multiple cities at once.

    POST body:
    {
        "cities": [
            {"city": "Dallas", "state": "TX"},
            {"city": "Oklahoma City", "state": "OK"},
            {"city": "Denver", "state": "CO"}
        ],
        "sources": ["bbb"],  // optional, default: ["bbb"]
        "geocode": false  // optional, geocode after scraping
    }

    Returns:
    {
        "cities_processed": 3,
        "total_businesses": 1500,
        "total_vehicles": 35000,
        "by_city": [
            {"city": "Dallas", "state": "TX", "businesses": 500, "vehicles": 12000},
            ...
        ],
        "errors": []
    }
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Scraper service not available'}), 503

    data = request.get_json()
    cities_data = data.get('cities', [])
    sources = data.get('sources', ['bbb'])
    geocode = data.get('geocode', False)

    if not cities_data:
        return jsonify({'error': 'No cities provided'}), 400

    cities = [(c['city'], c['state']) for c in cities_data if c.get('city') and c.get('state')]

    if not cities:
        return jsonify({'error': 'No valid cities provided'}), 400

    try:
        all_results = {
            'cities_processed': 0,
            'total_businesses': 0,
            'total_vehicles': 0,
            'by_city': [],
            'errors': [],
        }

        for city, state in cities:
            logger.info(f"Processing {city}, {state}...")

            try:
                result = discovery.discover_city(city, state, sources=sources, geocode=geocode)

                all_results['cities_processed'] += 1
                all_results['total_businesses'] += result.get('stats', {}).get('total', 0)
                all_results['total_vehicles'] += result.get('stats', {}).get('total_vehicles', 0)
                all_results['by_city'].append({
                    'city': city,
                    'state': state,
                    'new_businesses': result.get('total_new', 0),
                    'total_businesses': result.get('stats', {}).get('total', 0),
                    'vehicles': result.get('stats', {}).get('total_vehicles', 0),
                    'sources': result.get('sources', {}),
                })

                if result.get('errors'):
                    all_results['errors'].extend([f"{city}, {state}: {e}" for e in result['errors']])

            except Exception as e:
                all_results['errors'].append(f"{city}, {state}: {str(e)}")
                logger.error(f"Error processing {city}, {state}: {e}")

        return jsonify(all_results)

    except Exception as e:
        logger.error(f"Multi-city scrape error: {e}")
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/geocode-all', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def geocode_all_businesses():
    """
    Geocode all businesses in database that don't have coordinates.

    POST body:
    {
        "limit": 200,  // optional, max businesses to geocode (default: 200)
        "city": "Dallas",  // optional, filter by city
        "state": "TX"  // optional, filter by state
    }
    """
    geocoder = get_geocoding_service()
    if not geocoder:
        return jsonify({'error': 'Geocoding service not available'}), 503

    data = request.get_json() or {}
    limit = data.get('limit', 200)

    try:
        geocoded = geocoder.geocode_businesses_in_db(limit=limit)
        stats = geocoder.get_cache_stats()

        return jsonify({
            'success': True,
            'geocoded': geocoded,
            'cache_stats': stats
        })

    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# HAIL-AFFECTED BUSINESSES
# =============================================================================

@fleet_locations_api_bp.route('/businesses/hail-affected')
@login_required
def get_hail_affected_businesses():
    """
    Get businesses that are within a radius of recent hail events.

    Query params:
    - city: City name (optional)
    - state: State abbreviation (optional)
    - radius_miles: Radius from hail reports (default: 15)
    - days: Look back period for hail (default: 14)
    """
    discovery = get_business_discovery()
    if not discovery:
        return jsonify({'error': 'Service not available'}), 503

    city = request.args.get('city')
    state = request.args.get('state')
    radius_miles = request.args.get('radius_miles', 15, type=float)
    days = request.args.get('days', 14, type=int)

    try:
        # Get businesses with coordinates
        businesses = discovery.get_businesses_for_map(city=city, state=state, limit=1000)

        if not businesses:
            return jsonify({'count': 0, 'businesses': []})

        # Try to get recent hail events
        try:
            import sqlite3
            hail_db = os.path.join(PROJECT_ROOT, 'data', 'hailtracker_crm.db')
            conn = sqlite3.connect(hail_db)
            conn.row_factory = sqlite3.Row

            hail_events = conn.execute('''
                SELECT center_lat as lat, center_lon as lon, event_date, max_hail_size
                FROM hail_events
                WHERE event_date >= date('now', ? || ' days')
                AND center_lat IS NOT NULL
                AND center_lon IS NOT NULL
            ''', (f'-{days}',)).fetchall()

            conn.close()
            hail_events = [dict(h) for h in hail_events]

        except Exception as e:
            logger.warning(f"Could not fetch hail events: {e}")
            hail_events = []

        if not hail_events:
            return jsonify({
                'count': 0,
                'businesses': [],
                'message': 'No recent hail events found'
            })

        # Calculate affected businesses
        import math

        def haversine(lat1, lon1, lat2, lon2):
            R = 3959  # Earth's radius in miles
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            return 2 * R * math.asin(math.sqrt(a))

        affected = []
        for biz in businesses:
            biz_lat = biz.get('latitude')
            biz_lon = biz.get('longitude')

            if not biz_lat or not biz_lon:
                continue

            for hail in hail_events:
                distance = haversine(biz_lat, biz_lon, hail['lat'], hail['lon'])

                if distance <= radius_miles:
                    affected_biz = biz.copy()
                    affected_biz['hail_distance'] = round(distance, 1)
                    affected_biz['hail_date'] = hail.get('event_date')
                    affected_biz['hail_size'] = hail.get('max_hail_size')
                    affected.append(affected_biz)
                    break  # Only count once per business

        # Sort by distance from hail, then by vehicles
        affected.sort(key=lambda x: (x.get('hail_distance', 99), -(x.get('estimated_vehicles', 0))))

        return jsonify({
            'count': len(affected),
            'hail_events': len(hail_events),
            'radius_miles': radius_miles,
            'businesses': affected
        })

    except Exception as e:
        logger.error(f"Hail-affected query error: {e}")
        return jsonify({'error': str(e)}), 500


# Add PROJECT_ROOT for the hail endpoint
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# =============================================================================
# SMART SWATH-BASED DISCOVERY
# =============================================================================

def get_swath_discovery_service():
    """Get SwathDiscoveryService instance."""
    try:
        from src.business.swath_discovery import SwathDiscoveryService
        db_path = os.path.join(PROJECT_ROOT, 'data', 'business_prospects.db')
        crm_db_path = os.path.join(PROJECT_ROOT, 'data', 'hailtracker_crm.db')
        return SwathDiscoveryService(db_path=db_path, crm_db_path=crm_db_path)
    except ImportError as e:
        logger.warning(f"SwathDiscoveryService not available: {e}")
        return None


@fleet_locations_api_bp.route('/smart-scrape-swaths', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def smart_scrape_swaths():
    """
    Discover businesses within hail swath polygons using multiple data sources.

    Data Sources (FREE APIs):
    - OSM/Overpass: 80+ categories, unlimited, returns coordinates directly
    - Foursquare: 100k/month free, excellent business data
    - Yelp: 5k/day free, best for service businesses
    - HERE: 250k/month free, good backup source
    - TomTom: 2.5k/day free, decent coverage
    - Google Places: $200/month credit, most complete but costs money
    - Yellow Pages: Service businesses (landscaping, HVAC, plumbing, etc.)
    - BBB: Accredited businesses (higher quality leads)

    Features:
    - Comprehensive business category search
    - Full contact info (phone, website, email, address)
    - Deduplication across sources
    - Geocoding for non-API results
    - Point-in-polygon filtering
    - Database caching

    POST body:
    {
        "event_ids": [80812, 80801, ...],  // Hail event IDs to search
        "buffer_miles": 1,                  // Extra buffer around swaths (default: 1)
        "force_refresh": false,             // If true, ignore cache and re-scrape
        "sources": ["osm", "foursquare", "yelp"],  // API sources to use (new style)
        // Legacy parameters (still supported):
        "include_osm": true,
        "include_yellowpages": true,
        "include_bbb": true
    }

    Available sources:
    - "osm": OpenStreetMap (unlimited) - RECOMMENDED
    - "foursquare": Foursquare Places (100k/mo) - RECOMMENDED
    - "yelp": Yelp Fusion (5k/day) - RECOMMENDED
    - "here": HERE Places (250k/mo) - OPTIONAL
    - "tomtom": TomTom Search (2.5k/day) - OPTIONAL
    - "google": Google Places ($200 credit) - USE SPARINGLY
    - "yellowpages": Yellow Pages scraper - OPTIONAL
    - "bbb": BBB scraper - OPTIONAL

    Returns:
    {
        "success": true,
        "businesses": [...],
        "stats": {
            "total_found": 150,
            "osm_found": 85,
            "foursquare_found": 65,
            "yelp_found": 45,
            "here_found": 0,
            "tomtom_found": 0,
            "google_found": 0,
            "yellowpages_found": 0,
            "bbb_found": 0,
            "duplicates_removed": 75,
            "geocoded": 25,
            "final_in_swath": 150,
            "by_category": {"car_dealership": 8, "landscaping": 12, ...},
            "by_source": {"osm": 100, "foursquare": 35, "yelp": 15},
            "total_vehicles": 4500
        },
        "api_status": {
            "foursquare": {"configured": true, "free_tier": "100,000 calls/month"},
            "yelp": {"configured": true, "free_tier": "5,000 calls/day"},
            ...
        }
    }
    """
    service = get_swath_discovery_service()
    if not service:
        return jsonify({'error': 'Smart discovery service not available'}), 503

    data = request.get_json() or {}
    event_ids = data.get('event_ids', [])
    buffer_miles = data.get('buffer_miles', 1.0)
    force_refresh = data.get('force_refresh', False)

    # New sources parameter (preferred)
    sources = data.get('sources')

    # Legacy parameters (for backward compatibility)
    include_osm = data.get('include_osm', True)
    include_yellowpages = data.get('include_yellowpages', True)
    include_bbb = data.get('include_bbb', True)

    if not event_ids:
        return jsonify({'error': 'event_ids is required'}), 400

    try:
        logger.info(f"Smart swath discovery for {len(event_ids)} events")
        if sources:
            logger.info(f"Sources: {sources}")
        else:
            logger.info(f"Legacy sources: OSM={include_osm}, YP={include_yellowpages}, BBB={include_bbb}")

        result = service.discover_for_events(
            event_ids=event_ids,
            buffer_miles=buffer_miles,
            force_refresh=force_refresh,
            sources=sources,  # New parameter
            include_osm=include_osm,
            include_yellowpages=include_yellowpages,
            include_bbb=include_bbb
        )

        # Convert business dicts to match AffectedBusiness interface
        businesses = []
        for biz in result.get('businesses', []):
            businesses.append({
                'id': biz.get('id') or hash(biz.get('name', '') + biz.get('address', '')) % 1000000,
                'name': biz.get('name', ''),
                'address': biz.get('address', ''),
                'city': biz.get('city', ''),
                'state': biz.get('state', ''),
                'zip': biz.get('zip', ''),
                'phone': biz.get('phone', ''),
                'website': biz.get('website', ''),
                'email': biz.get('email', ''),
                'category': biz.get('category', 'other'),
                'subcategory': '',
                'estimated_vehicles': biz.get('estimated_vehicles', 10),
                'tier': biz.get('tier', 3),
                'latitude': biz.get('latitude'),
                'longitude': biz.get('longitude'),
                'source': biz.get('source', 'osm'),
                'osm_id': biz.get('osm_id', ''),
                'added_to_crm': biz.get('added_to_crm', False),
                'hail_date': biz.get('hail_date'),
                'hail_size': biz.get('hail_size'),
                'event_id': biz.get('event_id'),
            })

        # Get API status for frontend display
        api_status = service.get_api_status()

        return jsonify({
            'success': True,
            'businesses': businesses,
            'stats': result.get('stats', {}),
            'api_status': api_status,
        })

    except Exception as e:
        import traceback
        logger.error(f"Smart scrape error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/api-status')
@login_required
def get_api_status():
    """Get configuration status of all discovery APIs."""
    service = get_swath_discovery_service()
    if not service:
        return jsonify({'error': 'Discovery service not available'}), 503

    return jsonify({
        'apis': service.get_api_status(),
        'recommended': ['osm', 'foursquare', 'yelp'],
        'setup_instructions': {
            'foursquare': 'Set FOURSQUARE_API_KEY in .env (get key at https://foursquare.com/developers)',
            'yelp': 'Set YELP_API_KEY in .env (get key at https://www.yelp.com/developers)',
            'here': 'Set HERE_API_KEY in .env (get key at https://developer.here.com)',
            'tomtom': 'Set TOMTOM_API_KEY in .env (get key at https://developer.tomtom.com)',
            'google': 'Set GOOGLE_PLACES_API_KEY in .env (get key at https://console.cloud.google.com)',
        }
    })


@fleet_locations_api_bp.route('/swath-businesses/<int:business_id>/add-to-crm', methods=['POST'])
@login_required
@require_any_permission('leads.create', 'admin.access')
def add_swath_business_to_crm(business_id):
    """
    Mark a swath-discovered business as added to CRM.

    This updates the swath_businesses cache table.
    """
    service = get_swath_discovery_service()
    if not service:
        return jsonify({'error': 'Service not available'}), 503

    try:
        success = service.add_to_crm(business_id)
        if success:
            return jsonify({'success': True, 'message': 'Business marked as added to CRM'})
        else:
            return jsonify({'error': 'Failed to update business'}), 500

    except Exception as e:
        logger.error(f"Add to CRM error: {e}")
        return jsonify({'error': str(e)}), 500


@fleet_locations_api_bp.route('/swath-businesses/clear-cache', methods=['POST'])
@login_required
@require_any_permission('admin.access')
def clear_swath_cache():
    """
    Clear cached swath business discoveries.

    POST body:
    {
        "event_ids": [80812, ...]  // Optional - clear specific events only
    }
    """
    service = get_swath_discovery_service()
    if not service:
        return jsonify({'error': 'Service not available'}), 503

    data = request.get_json() or {}
    event_ids = data.get('event_ids')

    try:
        service.clear_cache(event_ids)
        return jsonify({
            'success': True,
            'message': f"Cleared cache for {len(event_ids) if event_ids else 'all'} events"
        })

    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# TILE-BASED DISCOVERY (NEW)
# =============================================================================

def get_tile_discovery_service():
    """Get TileBasedDiscovery service instance."""
    try:
        from src.business.tile_discovery import TileBasedDiscovery
        # Use 0.25 sq mile tiles for maximum coverage (Kyle's proven tile size)
        return TileBasedDiscovery(tile_size_miles=0.25)
    except Exception as e:
        logger.warning(f"TileBasedDiscovery not available: {e}")
        return None


@fleet_locations_api_bp.route('/tile-discover', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def tile_discover_businesses():
    """
    Discover businesses using tile-based approach for complete swath coverage.

    Benefits over center+radius:
    - Complete coverage of irregular swath shapes
    - Stays under API limits (Google Places: 60 per search)
    - Better precision for geographic filtering
    - Tile-level caching for reuse

    POST body:
    {
        "event_ids": [80812, 80801, ...],     // Hail event IDs
        "tile_size_miles": 0.25,               // Tile size (0.25 recommended for max results)
        "sources": ["osm", "bbb"],             // Data sources to use
        "force_refresh": false                 // Ignore tile cache
    }

    Available sources (all 6 APIs for maximum coverage):
    - "osm": OpenStreetMap (comprehensive, free, unlimited) - WORKING
    - "yelp": Yelp Fusion API (50/call, 5k/day) - WORKING
    - "foursquare": Foursquare Places API (50/call, 100k/month) - WORKING
    - "here": HERE Places API (100/call, 250k/month) - WORKING
    - "tomtom": TomTom Search API (100/call, 2.5k/day) - WORKING
    - "google": Google Places API (60/call, costs $) - WORKING
    - "bbb": Better Business Bureau (accredited businesses) - WORKING
    - "yellowpages": Yellow Pages (may be blocked) - BLOCKED
    - "manta": Manta.com business directory (may be blocked) - BLOCKED

    Returns:
    {
        "success": true,
        "businesses": [...],
        "stats": {
            "tiles_total": 44,
            "tiles_searched": 44,
            "tiles_from_cache": 0,
            "by_source": {"osm": 68, "bbb": 0},
            "total_found": 20,
            "duplicates_removed": 16,
            "total_vehicles": 1350
        },
        "tile_stats": {
            "count": 44,
            "tile_size_miles": 0.5,
            "estimated_area_sq_miles": 11.0
        }
    }
    """
    print("=" * 60)
    print(">>> /api/fleet-locations/tile-discover ENDPOINT REACHED <<<")
    print(f">>> Request data: {request.get_json()}")
    print("=" * 60)

    service = get_tile_discovery_service()
    if not service:
        return jsonify({'error': 'Tile discovery service not available'}), 503

    data = request.get_json() or {}
    event_ids = data.get('event_ids', [])
    tile_size = data.get('tile_size_miles', 0.25)  # 0.25 sq miles for max results
    sources = data.get('sources', ['osm', 'yelp', 'foursquare', 'here', 'tomtom', 'google'])
    force_refresh = data.get('force_refresh', False)
    # Smart default: limit to 200 tiles for reasonable response time (~4-5 min)
    # Use max_tiles=0 for unlimited (full search)
    max_tiles = data.get('max_tiles', 200)

    if not event_ids:
        return jsonify({'error': 'event_ids is required'}), 400

    # Validate sources - all 6 APIs supported
    valid_sources = ['osm', 'yelp', 'foursquare', 'here', 'tomtom', 'google', 'bbb', 'yellowpages', 'manta']
    sources = [s for s in sources if s in valid_sources]
    if not sources:
        sources = ['osm', 'yelp', 'foursquare', 'here', 'tomtom', 'google']

    try:
        logger.info(f"Tile-based discovery for {len(event_ids)} events")
        logger.info(f"Tile size: {tile_size} miles, Sources: {sources}")

        # Load swath polygons from database
        swaths = []
        db_path = os.path.join(PROJECT_ROOT, 'data', 'hailtracker_crm.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        placeholders = ','.join('?' * len(event_ids))
        cursor = conn.execute(f'''
            SELECT id, event_name, event_date, swath_polygon, max_hail_size
            FROM hail_events
            WHERE id IN ({placeholders})
            AND swath_polygon IS NOT NULL
        ''', event_ids)

        for row in cursor:
            try:
                polygon = json.loads(row['swath_polygon'])
                swaths.append({
                    'event_id': row['id'],
                    'event_name': row['event_name'],
                    'event_date': row['event_date'],
                    'max_hail_size': row['max_hail_size'],
                    'polygon': polygon,
                    **polygon  # Spread polygon fields for compatibility
                })
            except Exception as e:
                logger.debug(f"Skip invalid swath for event {row['id']}: {e}")

        conn.close()

        if not swaths:
            return jsonify({
                'success': True,
                'businesses': [],
                'stats': {'total_found': 0, 'message': 'No valid swath polygons found'},
            })

        # Use tile-based discovery
        from src.business.tile_discovery import TileBasedDiscovery
        discovery = TileBasedDiscovery(tile_size_miles=tile_size)

        if force_refresh:
            discovery.clear_tile_cache()

        result = discovery.discover_for_swaths(
            swaths=swaths,
            sources=sources,
            use_cache=not force_refresh,
            max_tiles=max_tiles  # Limit tiles for faster response
        )

        # Format businesses for frontend
        businesses = []
        for biz in result.get('businesses', []):
            businesses.append({
                'id': biz.get('id') or abs(hash(biz.get('name', '') + biz.get('address', ''))) % 1000000,
                'name': biz.get('name', ''),
                'address': biz.get('address', ''),
                'city': biz.get('city', ''),
                'state': biz.get('state', ''),
                'zip': biz.get('zip', ''),
                'phone': biz.get('phone', ''),
                'website': biz.get('website', ''),
                'email': biz.get('email', ''),
                'category': biz.get('category', 'other'),
                'subcategory': '',
                'estimated_vehicles': biz.get('estimated_vehicles', 10),
                'tier': biz.get('tier', 3),
                'latitude': biz.get('latitude'),
                'longitude': biz.get('longitude'),
                'source': biz.get('source', 'osm'),
                'osm_id': biz.get('osm_id', ''),
                'tile_id': biz.get('tile_id', ''),
                'added_to_crm': False,
            })

        return jsonify({
            'success': True,
            'businesses': businesses,
            'stats': result.get('stats', {}),
            'tile_stats': result.get('tile_stats', {}),
        })

    except Exception as e:
        import traceback
        logger.error(f"Tile discovery error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# =============================================================================
# FAST SWATH-LEVEL DISCOVERY (OPTIMIZED)
# =============================================================================

@fleet_locations_api_bp.route('/fast-discover', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def fast_discover_businesses():
    """
    HYBRID business discovery using multiple sources.

    BEFORE: 28 swaths × 50 tiles = 1,373 API calls = 45+ minutes
    AFTER:  1 OSM query + city-based YP/BBB/Manta = ~60 seconds

    POST body:
    {
        "event_ids": [80812, 80801, ...],
        "force_refresh": false,
        "include_osm": true,
        "include_yp": true,
        "include_bbb": true,
        "include_manta": true
    }

    Returns:
    {
        "success": true,
        "businesses": [...],
        "stats": {
            "swaths_total": 28,
            "osm_found": 50,
            "yp_found": 30,
            "bbb_found": 20,
            "manta_found": 15,
            "total_found": 100,
            "total_vehicles": 3500
        },
        "timing": {
            "total_seconds": 60,
            "osm_seconds": 5,
            "city_seconds": 55
        }
    }
    """
    print("=" * 60)
    print(">>> /api/fleet-locations/fast-discover ENDPOINT REACHED <<<")
    print(f">>> Request data: {request.get_json()}")
    print("=" * 60)

    try:
        from src.business.fast_discovery import FastSwathDiscovery
        service = FastSwathDiscovery()
    except Exception as e:
        logger.error(f"FastSwathDiscovery import error: {e}")
        return jsonify({'error': 'Fast discovery service not available'}), 503

    data = request.get_json() or {}
    event_ids = data.get('event_ids', [])
    force_refresh = data.get('force_refresh', False)

    # Source options (all enabled by default)
    include_osm = data.get('include_osm', True)
    include_yp = data.get('include_yp', True)
    include_bbb = data.get('include_bbb', True)
    include_manta = data.get('include_manta', True)

    if not event_ids:
        return jsonify({'error': 'event_ids is required'}), 400

    try:
        logger.info(f"Fast discovery for {len(event_ids)} events")

        # Load swath polygons from database
        swaths = []
        db_path = os.path.join(PROJECT_ROOT, 'data', 'hailtracker_crm.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        placeholders = ','.join('?' * len(event_ids))
        cursor = conn.execute(f'''
            SELECT id, event_name, event_date, swath_polygon, max_hail_size
            FROM hail_events
            WHERE id IN ({placeholders})
            AND swath_polygon IS NOT NULL
        ''', event_ids)

        for row in cursor:
            try:
                polygon = json.loads(row['swath_polygon'])
                swaths.append({
                    'event_id': row['id'],
                    'event_name': row['event_name'],
                    'event_date': row['event_date'],
                    'max_hail_size': row['max_hail_size'],
                    'polygon': polygon,
                    **polygon
                })
            except Exception as e:
                logger.debug(f"Skip invalid swath for event {row['id']}: {e}")

        conn.close()

        if not swaths:
            return jsonify({
                'success': True,
                'businesses': [],
                'stats': {'message': 'No valid swaths found'},
            })

        # Use hybrid discovery (OSM + YP/BBB/Manta)
        result = service.discover_for_swaths(
            swaths=swaths,
            use_cache=not force_refresh,
            include_osm=include_osm,
            include_yp=include_yp,
            include_bbb=include_bbb,
            include_manta=include_manta
        )

        # Format businesses for frontend
        businesses = []
        for biz in result.get('businesses', []):
            businesses.append({
                'id': biz.get('id') or abs(hash(biz.get('name', '') + biz.get('address', ''))) % 1000000,
                'name': biz.get('name', ''),
                'address': biz.get('address', ''),
                'city': biz.get('city', ''),
                'state': biz.get('state', ''),
                'zip': biz.get('zip', ''),
                'phone': biz.get('phone', ''),
                'website': biz.get('website', ''),
                'email': biz.get('email', ''),
                'category': biz.get('category', 'other'),
                'subcategory': '',
                'estimated_vehicles': biz.get('estimated_vehicles', 10),
                'tier': biz.get('tier', 3),
                'latitude': biz.get('latitude'),
                'longitude': biz.get('longitude'),
                'source': biz.get('source', 'osm'),
                'osm_id': biz.get('osm_id', ''),
                'added_to_crm': False,
            })

        return jsonify({
            'success': True,
            'businesses': businesses,
            'stats': result.get('stats', {}),
            'timing': result.get('timing', {}),
        })

    except Exception as e:
        import traceback
        logger.error(f"Fast discovery error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# =============================================================================
# BATCH SCRAPING
# =============================================================================

# Preset city lists for batch scraping
SCRAPE_PRESETS = {
    'hail_alley': {
        'name': 'Hail Alley',
        'description': 'TX, OK, KS, CO, NE - highest hail frequency in the US',
        'cities': [
            {'city': 'Dallas', 'state': 'TX'},
            {'city': 'Fort Worth', 'state': 'TX'},
            {'city': 'Oklahoma City', 'state': 'OK'},
            {'city': 'Tulsa', 'state': 'OK'},
            {'city': 'Wichita', 'state': 'KS'},
            {'city': 'Kansas City', 'state': 'MO'},
            {'city': 'Denver', 'state': 'CO'},
            {'city': 'Colorado Springs', 'state': 'CO'},
            {'city': 'Omaha', 'state': 'NE'},
            {'city': 'Lubbock', 'state': 'TX'},
            {'city': 'Amarillo', 'state': 'TX'},
            {'city': 'San Antonio', 'state': 'TX'},
        ],
    },
    'texas': {
        'name': 'Texas',
        'description': 'Major Texas metro areas',
        'cities': [
            {'city': 'Dallas', 'state': 'TX'},
            {'city': 'Fort Worth', 'state': 'TX'},
            {'city': 'Houston', 'state': 'TX'},
            {'city': 'San Antonio', 'state': 'TX'},
            {'city': 'Austin', 'state': 'TX'},
            {'city': 'Arlington', 'state': 'TX'},
            {'city': 'Plano', 'state': 'TX'},
            {'city': 'Lubbock', 'state': 'TX'},
            {'city': 'Amarillo', 'state': 'TX'},
            {'city': 'McKinney', 'state': 'TX'},
            {'city': 'Frisco', 'state': 'TX'},
            {'city': 'Irving', 'state': 'TX'},
        ],
    },
    'midwest': {
        'name': 'Midwest',
        'description': 'IL, IN, OH, MI, WI, MN, MO, IA, NE',
        'cities': [
            {'city': 'Chicago', 'state': 'IL'},
            {'city': 'Indianapolis', 'state': 'IN'},
            {'city': 'Columbus', 'state': 'OH'},
            {'city': 'Detroit', 'state': 'MI'},
            {'city': 'Milwaukee', 'state': 'WI'},
            {'city': 'Minneapolis', 'state': 'MN'},
            {'city': 'St. Louis', 'state': 'MO'},
            {'city': 'Des Moines', 'state': 'IA'},
            {'city': 'Kansas City', 'state': 'MO'},
            {'city': 'Omaha', 'state': 'NE'},
        ],
    },
    'southeast': {
        'name': 'Southeast',
        'description': 'GA, TN, NC, AL, KY, AR, MS',
        'cities': [
            {'city': 'Atlanta', 'state': 'GA'},
            {'city': 'Nashville', 'state': 'TN'},
            {'city': 'Charlotte', 'state': 'NC'},
            {'city': 'Birmingham', 'state': 'AL'},
            {'city': 'Memphis', 'state': 'TN'},
            {'city': 'Louisville', 'state': 'KY'},
            {'city': 'Little Rock', 'state': 'AR'},
            {'city': 'Jackson', 'state': 'MS'},
        ],
    },
}


@fleet_locations_api_bp.route('/scrape-presets')
@login_required
def get_scrape_presets():
    """Get available preset city lists for batch scraping."""
    presets = {}
    for key, preset in SCRAPE_PRESETS.items():
        presets[key] = {
            'name': preset['name'],
            'description': preset['description'],
            'city_count': len(preset['cities']),
        }
    return jsonify(presets)


@fleet_locations_api_bp.route('/batch-scrape', methods=['POST'])
@login_required
@require_any_permission('admin.access', 'leads.create')
def batch_scrape_cities():
    """
    Batch scrape multiple cities for fleet businesses.

    POST body:
    {
        "cities": [{"city": "Dallas", "state": "TX"}, ...],
        "sources": ["bbb"],
        "geocode": true
    }

    OR use preset:
    {
        "preset": "hail_alley"
    }
    """
    data = request.get_json() or {}

    # Get cities from preset or direct list
    preset = data.get('preset')
    if preset and preset in SCRAPE_PRESETS:
        cities = SCRAPE_PRESETS[preset]['cities']
        logger.info(f"Using preset '{preset}' with {len(cities)} cities")
    else:
        cities = data.get('cities', [])

    if not cities:
        return jsonify({
            'error': 'No cities provided',
            'available_presets': list(SCRAPE_PRESETS.keys())
        }), 400

    sources = data.get('sources', ['bbb'])
    do_geocode = data.get('geocode', True)

    results = {
        'preset': preset,
        'total_cities': len(cities),
        'cities_completed': 0,
        'total_businesses': 0,
        'total_vehicles': 0,
        'by_city': [],
        'errors': [],
    }

    # Get discovery service
    service = get_discovery_service()
    if not service:
        return jsonify({'error': 'Discovery service not available'}), 500

    for city_info in cities:
        city = city_info['city']
        state = city_info['state']

        try:
            logger.info(f"Batch scraping: {city}, {state}")

            city_result = service.discover_city(city, state, sources=sources)
            stats = city_result.get('stats', {})

            city_data = {
                'city': city,
                'state': state,
                'businesses': stats.get('total', 0),
                'vehicles': stats.get('total_vehicles', 0),
                'sources': city_result.get('sources', {}),
            }

            results['by_city'].append(city_data)
            results['total_businesses'] += stats.get('total', 0)
            results['total_vehicles'] += stats.get('total_vehicles', 0)
            results['cities_completed'] += 1

        except Exception as e:
            error_msg = f"{city}, {state}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"Error scraping {city}, {state}: {e}")

    # Geocode all new businesses if requested
    if do_geocode and results['total_businesses'] > 0:
        try:
            from src.fleet.scrapers.geocoding import batch_geocode_businesses
            geocoded = batch_geocode_businesses(limit=500)
            results['geocoded'] = geocoded
        except Exception as e:
            results['geocode_error'] = str(e)
            logger.error(f"Geocoding error: {e}")

    # Calculate estimated value (assuming $500 average revenue per vehicle)
    results['estimated_value'] = results['total_vehicles'] * 500

    return jsonify(results)


# =============================================================================
# EMAIL TEMPLATES
# =============================================================================

@fleet_locations_api_bp.route('/email-templates')
@login_required
def list_email_templates():
    """List available email templates."""
    try:
        from src.fleet.email_templates import list_templates
        return jsonify({'templates': list_templates()})
    except ImportError:
        return jsonify({'error': 'Email templates not available'}), 500


@fleet_locations_api_bp.route('/email-templates/<template_key>')
@login_required
def get_email_template(template_key):
    """Get a specific template with optional variable substitution."""
    try:
        from src.fleet.email_templates import get_email_template

        variables = request.args.to_dict()
        result = get_email_template(template_key, variables)

        if not result:
            return jsonify({'error': 'Template not found'}), 404

        return jsonify(result)
    except ImportError:
        return jsonify({'error': 'Email templates not available'}), 500


@fleet_locations_api_bp.route('/email-templates/for-business/<int:business_id>')
@login_required
def get_email_template_for_business(business_id):
    """Get the best email template for a business, pre-filled with their info."""
    try:
        from src.fleet.email_templates import get_email_template, get_template_for_category
        import sqlite3

        # Get business from database
        db_path = os.path.join(PROJECT_ROOT, 'data', 'business_prospects.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM businesses WHERE id = ?', (business_id,))
        business = cursor.fetchone()
        conn.close()

        if not business:
            return jsonify({'error': 'Business not found'}), 404

        business = dict(business)

        # Determine if hail affected (check notes or recent hail)
        hail_affected = 'hail' in (business.get('notes', '') or '').lower()

        # Get best template
        template_key = get_template_for_category(
            business.get('category', ''),
            hail_affected=hail_affected
        )

        # Build variables
        variables = {
            'company_name': business.get('name'),
            'contact_name': 'Fleet Manager',
            'city': business.get('city'),
            'state': business.get('state'),
            'estimated_vehicles': business.get('estimated_vehicles', ''),
            'hail_date': 'recently',
            'sender_name': '[YOUR NAME]',
            'sender_company': '[YOUR COMPANY]',
            'sender_phone': '[YOUR PHONE]',
            'sender_email': '[YOUR EMAIL]',
        }

        result = get_email_template(template_key, variables)
        result['template_key'] = template_key
        result['business_id'] = business_id

        return jsonify(result)
    except ImportError:
        return jsonify({'error': 'Email templates not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# CALL SCRIPTS
# =============================================================================

@fleet_locations_api_bp.route('/call-scripts')
@login_required
def list_call_scripts():
    """List available call scripts."""
    try:
        from src.fleet.call_scripts import list_scripts
        return jsonify({'scripts': list_scripts()})
    except ImportError:
        return jsonify({'error': 'Call scripts not available'}), 500


@fleet_locations_api_bp.route('/call-scripts/<script_key>')
@login_required
def get_call_script(script_key):
    """Get a specific call script with optional variable substitution."""
    try:
        from src.fleet.call_scripts import get_call_script

        variables = request.args.to_dict()
        result = get_call_script(script_key, variables)

        if not result:
            return jsonify({'error': 'Script not found'}), 404

        return jsonify(result)
    except ImportError:
        return jsonify({'error': 'Call scripts not available'}), 500


@fleet_locations_api_bp.route('/call-scripts/for-business/<int:business_id>')
@login_required
def get_call_script_for_business(business_id):
    """Get the best call script for a business, pre-filled with their info."""
    try:
        from src.fleet.call_scripts import get_call_script, get_script_for_category
        import sqlite3

        # Get business from database
        db_path = os.path.join(PROJECT_ROOT, 'data', 'business_prospects.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM businesses WHERE id = ?', (business_id,))
        business = cursor.fetchone()
        conn.close()

        if not business:
            return jsonify({'error': 'Business not found'}), 404

        business = dict(business)

        # Determine if hail affected
        hail_affected = 'hail' in (business.get('notes', '') or '').lower()

        # Get best script
        script_key = get_script_for_category(
            business.get('category', ''),
            hail_affected=hail_affected
        )

        # Build variables
        variables = {
            'company_name': business.get('name'),
            'contact_name': 'there',
            'city': business.get('city'),
            'address': business.get('address', ''),
            'hail_date': 'recently',
            'caller_name': '[YOUR NAME]',
            'caller_company': '[YOUR COMPANY]',
            'price_range': '$75-150',
        }

        result = get_call_script(script_key, variables)
        result['script_key'] = script_key
        result['business_id'] = business_id
        result['business_name'] = business.get('name')
        result['business_phone'] = business.get('phone')

        return jsonify(result)
    except ImportError:
        return jsonify({'error': 'Call scripts not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
