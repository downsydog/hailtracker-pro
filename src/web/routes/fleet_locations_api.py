"""
Fleet Locations API Routes
==========================
API for fleet location intelligence (business prospect discovery).

Endpoints:
- GET    /api/fleet-locations               - List locations with filters
- GET    /api/fleet-locations/search        - Search locations
- GET    /api/fleet-locations/bbox          - Get locations in bounding box
- GET    /api/fleet-locations/nearby        - Get locations near a point
- GET    /api/fleet-locations/categories    - Get category summary
- GET    /api/fleet-locations/stats         - Get overall stats
"""

from flask import Blueprint, request, jsonify, g
from src.core.auth.decorators import login_required, require_any_permission
import os

fleet_locations_api_bp = Blueprint('fleet_locations_api', __name__, url_prefix='/api/fleet-locations')


def get_fleet_manager():
    """Get FleetLocationManager instance"""
    from src.business.fleet_locations import FleetLocationManager
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return FleetLocationManager(db_path)


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
