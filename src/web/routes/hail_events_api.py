"""
Hail Events API Routes - COMPREHENSIVE
=======================================
RESTful API for all HailEventManager functionality.

Endpoints:
- Storm CRUD: create, update, delete, reopen
- Search: by state, city, severity, zip, date range
- Job-Storm Linking: link/unlink jobs to storms
- Statistics & ROI: storm stats, overall stats, performance
- Market Opportunity: revenue estimates
- Reports: storm, performance, summary, multi-storm
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date, timedelta
from src.core.auth.decorators import login_required, require_any_permission
from src.db.main_db import get_main_db, MAIN_DB_PATH
import os

hail_events_api_bp = Blueprint('hail_events_api', __name__, url_prefix='/api/hail-events')


def _get_hail_db():
    """Get Database instance pointed at the main DB (where hail_events lives)."""
    return get_main_db()


def get_manager():
    """Get HailEventManager instance"""
    from src.crm.managers.hail_event_manager import HailEventManager
    db = get_main_db()
    return HailEventManager(db)


# =============================================================================
# STORM CRUD
# =============================================================================

@hail_events_api_bp.route('', methods=['GET'])
def list_hail_events():
    """List hail events with filtering"""
    manager = get_manager()

    # Filters
    days = request.args.get('days', 90, type=int)
    severity = request.args.get('severity')
    status = request.args.get('status')
    limit = request.args.get('limit', 100, type=int)
    limit = min(limit, 500)

    cutoff = date.today() - timedelta(days=days)

    events = manager.search_storms(
        severity=severity,
        status=status,
        start_date=cutoff,
        limit=limit
    )

    # Get overall stats
    stats = manager.get_overall_storm_stats(days)

    return jsonify({
        'events': events,
        'count': len(events),
        'stats': stats
    })


@hail_events_api_bp.route('', methods=['POST'])
@login_required
def create_hail_event():
    """Create new hail storm event"""
    manager = get_manager()
    data = request.get_json()

    required = ['event_name', 'event_date', 'location', 'city', 'state', 'severity']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Parse date
    event_date = data['event_date']
    if isinstance(event_date, str):
        event_date = datetime.fromisoformat(event_date.replace('Z', '')).date()

    try:
        storm_id = manager.create_storm_event(
            event_name=data['event_name'],
            event_date=event_date,
            location=data['location'],
            city=data['city'],
            state=data['state'],
            severity=data['severity'],
            hail_size_inches=data.get('hail_size_inches'),
            affected_zip_codes=data.get('affected_zip_codes'),
            estimated_radius_miles=data.get('estimated_radius_miles'),
            insurance_storm_code=data.get('insurance_storm_code'),
            noaa_event_id=data.get('noaa_event_id'),
            estimated_vehicles_affected=data.get('estimated_vehicles_affected'),
            notes=data.get('notes')
        )

        storm = manager.get_storm_event(storm_id)
        return jsonify({'id': storm_id, 'storm': storm}), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@hail_events_api_bp.route('/<int:event_id>', methods=['GET'])
def get_hail_event(event_id):
    """Get hail event details"""
    manager = get_manager()

    event = manager.get_storm_event(event_id)
    if not event:
        return jsonify({'error': 'Hail event not found'}), 404

    # Add stats
    event['stats'] = manager.get_storm_stats(event_id)

    return jsonify(event)


@hail_events_api_bp.route('/<int:event_id>', methods=['PUT'])
@login_required
def update_hail_event(event_id):
    """Update hail storm event"""
    manager = get_manager()
    data = request.get_json()

    success = manager.update_storm_event(event_id, **data)

    if not success:
        return jsonify({'error': 'Event not found or update failed'}), 404

    event = manager.get_storm_event(event_id)
    return jsonify(event)


@hail_events_api_bp.route('/<int:event_id>', methods=['DELETE'])
@login_required
def close_hail_event(event_id):
    """Close (soft delete) hail storm event"""
    manager = get_manager()
    data = request.get_json() or {}

    success = manager.close_storm_event(event_id, notes=data.get('notes'))

    if not success:
        return jsonify({'error': 'Event not found'}), 404

    return jsonify({'success': True, 'status': 'CLOSED'})


@hail_events_api_bp.route('/<int:event_id>/reopen', methods=['POST'])
@login_required
def reopen_hail_event(event_id):
    """Reopen a closed storm event"""
    manager = get_manager()

    success = manager.reopen_storm_event(event_id)

    if not success:
        return jsonify({'error': 'Event not found'}), 404

    return jsonify({'success': True, 'status': 'ACTIVE'})


# =============================================================================
# SEARCH & FILTERING
# =============================================================================

@hail_events_api_bp.route('/search', methods=['GET'])
def search_hail_events():
    """Search storms with multiple filters"""
    manager = get_manager()

    state = request.args.get('state')
    city = request.args.get('city')
    severity = request.args.get('severity')
    status = request.args.get('status')
    zip_code = request.args.get('zip_code')
    limit = request.args.get('limit', 50, type=int)

    start_date = None
    end_date = None

    if request.args.get('start_date'):
        start_date = datetime.fromisoformat(request.args.get('start_date')).date()
    if request.args.get('end_date'):
        end_date = datetime.fromisoformat(request.args.get('end_date')).date()

    events = manager.search_storms(
        state=state,
        city=city,
        severity=severity,
        status=status,
        start_date=start_date,
        end_date=end_date,
        zip_code=zip_code,
        limit=limit
    )

    return jsonify({'events': events, 'count': len(events)})


@hail_events_api_bp.route('/active', methods=['GET'])
def get_active_events():
    """Get currently active hail events"""
    manager = get_manager()
    days_back = request.args.get('days', 90, type=int)

    events = manager.get_active_storms(days_back)

    return jsonify({'events': events, 'count': len(events)})


@hail_events_api_bp.route('/by-zip/<zip_code>', methods=['GET'])
@login_required
def get_events_by_zip(zip_code):
    """Get storms that affected a ZIP code"""
    manager = get_manager()

    events = manager.get_storms_by_zip(zip_code)

    return jsonify({'events': events, 'count': len(events), 'zip_code': zip_code})


@hail_events_api_bp.route('/by-severity/<severity>', methods=['GET'])
@login_required
def get_events_by_severity(severity):
    """Get storms by severity level"""
    manager = get_manager()
    days_back = request.args.get('days', 365, type=int)

    events = manager.get_storms_by_severity(severity.upper(), days_back)

    return jsonify({'events': events, 'count': len(events), 'severity': severity.upper()})


@hail_events_api_bp.route('/nearby', methods=['GET'])
def get_nearby_events():
    """Get hail events near a location"""
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius_miles = request.args.get('radius', 50, type=float)

    if not lat or not lon:
        return jsonify({'error': 'lat and lon parameters required'}), 400

    manager = get_manager()

    # Simple bounding box query
    lat_range = radius_miles / 69
    lon_range = radius_miles / 54

    # Search all recent storms and filter by approximate distance
    all_storms = manager.search_storms(limit=200)

    nearby = []
    for storm in all_storms:
        storm_lat = storm.get('center_lat') or storm.get('latitude')
        storm_lon = storm.get('center_lon') or storm.get('longitude')

        if storm_lat and storm_lon:
            if (abs(storm_lat - lat) <= lat_range and abs(storm_lon - lon) <= lon_range):
                nearby.append(storm)

    return jsonify({
        'events': nearby[:50],
        'count': len(nearby[:50]),
        'center': {'lat': lat, 'lon': lon},
        'radius_miles': radius_miles
    })


# =============================================================================
# STORM-JOB LINKING
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/link-job', methods=['POST'])
@login_required
def link_job_to_storm(event_id):
    """Link a job to a storm event"""
    manager = get_manager()
    data = request.get_json()

    if 'job_id' not in data:
        return jsonify({'error': 'job_id required'}), 400

    success = manager.link_job_to_storm(
        job_id=data['job_id'],
        storm_id=event_id,
        confidence=data.get('confidence', 'CONFIRMED'),
        notes=data.get('notes')
    )

    if not success:
        return jsonify({'error': 'Failed to link job'}), 400

    return jsonify({'success': True, 'storm_id': event_id, 'job_id': data['job_id']})


@hail_events_api_bp.route('/<int:event_id>/unlink-job/<int:job_id>', methods=['DELETE'])
@login_required
def unlink_job_from_storm(event_id, job_id):
    """Remove job-storm link"""
    manager = get_manager()

    success = manager.unlink_job_from_storm(job_id, event_id)

    return jsonify({'success': success})


@hail_events_api_bp.route('/<int:event_id>/jobs', methods=['GET'])
@login_required
def get_storm_jobs(event_id):
    """Get all jobs linked to a storm"""
    manager = get_manager()

    jobs = manager.get_storm_jobs(event_id)

    return jsonify({
        'storm_id': event_id,
        'jobs': jobs,
        'count': len(jobs)
    })


# Job-centric endpoints (also register under /api/jobs)
jobs_storm_bp = Blueprint('jobs_storm_api', __name__, url_prefix='/api/jobs')


@jobs_storm_bp.route('/<int:job_id>/storm', methods=['GET'])
@login_required
def get_job_storm(job_id):
    """Get storm linked to a job"""
    manager = get_manager()

    link = manager.get_job_storm_link(job_id)

    if not link:
        return jsonify({'job_id': job_id, 'storm': None})

    storm = manager.get_storm_event(link['hail_event_id'])

    return jsonify({
        'job_id': job_id,
        'storm': storm,
        'link': link
    })


@jobs_storm_bp.route('/<int:job_id>/find-storm', methods=['POST'])
@login_required
def find_matching_storm(job_id):
    """Auto-suggest storm for a job based on customer location and damage date"""
    manager = get_manager()
    data = request.get_json()

    if 'zip_code' not in data or 'damage_date' not in data:
        return jsonify({'error': 'zip_code and damage_date required'}), 400

    damage_date = data['damage_date']
    if isinstance(damage_date, str):
        damage_date = datetime.fromisoformat(damage_date.replace('Z', '')).date()

    days_range = data.get('days_range', 14)

    storm = manager.find_matching_storm(
        customer_zip=data['zip_code'],
        damage_date=damage_date,
        days_range=days_range
    )

    return jsonify({
        'job_id': job_id,
        'matching_storm': storm,
        'search_params': {
            'zip_code': data['zip_code'],
            'damage_date': str(damage_date),
            'days_range': days_range
        }
    })


# =============================================================================
# STATISTICS & ROI
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/stats', methods=['GET'])
@login_required
def get_storm_stats(event_id):
    """Get statistics for a specific storm"""
    manager = get_manager()

    stats = manager.get_storm_stats(event_id)

    if not stats:
        return jsonify({'error': 'Storm not found'}), 404

    return jsonify(stats)


@hail_events_api_bp.route('/stats/overall', methods=['GET'])
@login_required
def get_overall_stats():
    """Get overall storm statistics"""
    manager = get_manager()
    days = request.args.get('days', 365, type=int)

    stats = manager.get_overall_storm_stats(days)

    return jsonify(stats)


@hail_events_api_bp.route('/<int:event_id>/roi', methods=['GET'])
@login_required
def get_storm_roi(event_id):
    """Get ROI metrics for a storm"""
    manager = get_manager()

    roi = manager.get_storm_roi(event_id)

    if not roi:
        return jsonify({'error': 'Storm not found'}), 404

    return jsonify(roi)


@hail_events_api_bp.route('/performance', methods=['GET'])
@login_required
def get_all_storms_performance():
    """Get performance metrics for all storms"""
    manager = get_manager()

    start_date = None
    end_date = None
    min_jobs = request.args.get('min_jobs', 0, type=int)

    if request.args.get('start_date'):
        start_date = datetime.fromisoformat(request.args.get('start_date')).date()
    if request.args.get('end_date'):
        end_date = datetime.fromisoformat(request.args.get('end_date')).date()

    storms = manager.get_all_storms_performance(
        start_date=start_date,
        end_date=end_date,
        min_jobs=min_jobs
    )

    return jsonify({
        'storms': storms,
        'count': len(storms)
    })


@hail_events_api_bp.route('/compare', methods=['POST'])
@login_required
def compare_storms():
    """Compare performance across multiple storms"""
    manager = get_manager()
    data = request.get_json()

    if 'storm_ids' not in data:
        return jsonify({'error': 'storm_ids array required'}), 400

    comparison = manager.get_storm_comparison(data['storm_ids'])

    return jsonify(comparison)


# =============================================================================
# MARKET OPPORTUNITY
# =============================================================================

@hail_events_api_bp.route('/market-opportunity', methods=['POST'])
@login_required
def estimate_market_opportunity():
    """Calculate market opportunity for given parameters"""
    manager = get_manager()
    data = request.get_json()

    required = ['vehicles_affected', 'severity']
    for field in required:
        if field not in data:
            return jsonify({'error': f'{field} required'}), 400

    estimate = manager.estimate_market_opportunity(
        vehicles_affected=data['vehicles_affected'],
        severity=data['severity'],
        capture_rate=data.get('capture_rate', 0.05)
    )

    return jsonify(estimate)


# =============================================================================
# REPORTS
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/report', methods=['GET'])
@login_required
def get_storm_report(event_id):
    """Generate detailed storm report"""
    manager = get_manager()
    format_type = request.args.get('format', 'json')

    if format_type == 'text':
        report = manager.generate_storm_report(event_id)
        return report, 200, {'Content-Type': 'text/plain'}

    # JSON format - return structured data
    storm = manager.get_storm_event(event_id)
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404

    stats = manager.get_storm_stats(event_id)
    roi = manager.get_storm_roi(event_id)

    return jsonify({
        'storm': storm,
        'stats': stats,
        'roi': roi
    })


@hail_events_api_bp.route('/<int:event_id>/performance-report', methods=['GET'])
@login_required
def get_storm_performance_report(event_id):
    """Generate storm performance report"""
    manager = get_manager()
    format_type = request.args.get('format', 'json')

    if format_type == 'text':
        report = manager.generate_storm_performance_report(event_id)
        return report, 200, {'Content-Type': 'text/plain'}

    # JSON format
    roi = manager.get_storm_roi(event_id)
    storm = manager.get_storm_event(event_id)

    return jsonify({
        'storm': storm,
        'performance': roi
    })


@hail_events_api_bp.route('/summary-report', methods=['GET'])
@login_required
def get_summary_report():
    """Generate summary report of all storms"""
    manager = get_manager()
    days = request.args.get('days', 90, type=int)
    format_type = request.args.get('format', 'json')

    if format_type == 'text':
        report = manager.generate_summary_report(days)
        return report, 200, {'Content-Type': 'text/plain'}

    # JSON format
    stats = manager.get_overall_storm_stats(days)
    active = manager.get_active_storms(days)

    return jsonify({
        'period_days': days,
        'stats': stats,
        'active_storms': active
    })


@hail_events_api_bp.route('/multi-storm-report', methods=['GET'])
@login_required
def get_multi_storm_report():
    """Generate multi-storm performance report"""
    manager = get_manager()
    days = request.args.get('days', 365, type=int)
    format_type = request.args.get('format', 'json')

    if format_type == 'text':
        report = manager.generate_multi_storm_report(days)
        return report, 200, {'Content-Type': 'text/plain'}

    # JSON format
    cutoff = date.today() - timedelta(days=days)
    storms = manager.get_all_storms_performance(start_date=cutoff)
    stats = manager.get_overall_storm_stats(days)

    return jsonify({
        'period_days': days,
        'storms': storms,
        'stats': stats
    })


# =============================================================================
# SEVERITY HELPERS
# =============================================================================

@hail_events_api_bp.route('/severity-info/<severity>', methods=['GET'])
def get_severity_info(severity):
    """Get detailed info about a severity level"""
    manager = get_manager()

    info = manager.get_severity_info(severity.upper())

    if not info:
        return jsonify({'error': 'Unknown severity level'}), 404

    return jsonify({
        'severity': severity.upper(),
        'info': info
    })


@hail_events_api_bp.route('/severity-levels', methods=['GET'])
def get_all_severity_levels():
    """Get all severity level definitions"""
    manager = get_manager()

    return jsonify({
        'levels': manager.SEVERITY_LEVELS
    })


@hail_events_api_bp.route('/classify-severity', methods=['POST'])
@login_required
def classify_severity():
    """Classify severity based on hail size"""
    manager = get_manager()
    data = request.get_json()

    if 'hail_size_inches' not in data:
        return jsonify({'error': 'hail_size_inches required'}), 400

    severity = manager.classify_severity_by_hail_size(data['hail_size_inches'])
    info = manager.get_severity_info(severity)

    return jsonify({
        'hail_size_inches': data['hail_size_inches'],
        'severity': severity,
        'info': info
    })


# =============================================================================
# ADDRESS/LOCATION LOOKUP - "Was this location hit by hail?"
# =============================================================================

@hail_events_api_bp.route('/check-location', methods=['GET', 'POST'])
@login_required
def check_location_for_hail():
    """
    Check if a location was hit by hail in the past N years.

    Query params (GET) or JSON body (POST):
        lat: Latitude (required)
        lon: Longitude (required)
        years: Number of years to look back (default: 5)
        radius_miles: Search radius (default: 5)

    Returns:
        - was_hit: Boolean
        - events: List of hail events that affected this location
        - summary: Stats about severity, max hail size, etc.
    """
    import math
    import json

    # Get params from query string or JSON body
    if request.method == 'POST':
        data = request.get_json() or {}
        lat = data.get('lat')
        lon = data.get('lon')
        years = data.get('years', 5)
        radius_miles = data.get('radius_miles', 5)
    else:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        years = request.args.get('years', 5, type=int)
        radius_miles = request.args.get('radius_miles', 5, type=float)

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon are required'}), 400

    # Calculate date cutoff
    from datetime import date, timedelta
    cutoff_date = date.today() - timedelta(days=years * 365)

    # Get database connection (hail_events is in main DB)
    db = _get_hail_db()

    # Convert radius to approximate lat/lon delta
    # 1 degree latitude = ~69 miles
    # 1 degree longitude = ~69 * cos(lat) miles
    lat_delta = radius_miles / 69.0
    lon_delta = radius_miles / (69.0 * math.cos(math.radians(lat)))

    # Query for nearby events within bounding box
    events = db.execute("""
        SELECT
            id, event_name, event_date, center_lat, center_lon,
            max_hail_size, swath_polygon, swath_area_sqmi,
            estimated_vehicles, data_source, confidence_score
        FROM hail_events
        WHERE event_date >= ?
        AND center_lat BETWEEN ? AND ?
        AND center_lon BETWEEN ? AND ?
        ORDER BY event_date DESC
        LIMIT 100
    """, (
        cutoff_date.isoformat(),
        lat - lat_delta, lat + lat_delta,
        lon - lon_delta, lon + lon_delta
    ))

    # Filter to events where point is inside swath polygon
    matching_events = []
    for event in events:
        # Check if point is inside the swath polygon
        swath_json = event.get('swath_polygon')
        if swath_json:
            try:
                swath = json.loads(swath_json)
                if _point_in_polygon(lat, lon, swath):
                    matching_events.append({
                        'id': event['id'],
                        'event_name': event['event_name'],
                        'event_date': event['event_date'],
                        'hail_size_inches': event['max_hail_size'],
                        'distance_miles': _haversine_distance(
                            lat, lon,
                            event['center_lat'], event['center_lon']
                        ),
                        'data_source': event['data_source'],
                        'confidence': event['confidence_score']
                    })
            except json.JSONDecodeError:
                pass

        # If no polygon, check simple distance
        elif event.get('center_lat') and event.get('center_lon'):
            dist = _haversine_distance(lat, lon, event['center_lat'], event['center_lon'])
            if dist <= radius_miles:
                matching_events.append({
                    'id': event['id'],
                    'event_name': event['event_name'],
                    'event_date': event['event_date'],
                    'hail_size_inches': event['max_hail_size'],
                    'distance_miles': round(dist, 2),
                    'data_source': event['data_source'],
                    'confidence': event['confidence_score']
                })

    # Calculate summary stats
    was_hit = len(matching_events) > 0
    summary = {
        'total_events': len(matching_events),
        'max_hail_size': max((e['hail_size_inches'] or 0) for e in matching_events) if matching_events else 0,
        'years_checked': years,
        'radius_miles': radius_miles,
        'most_recent': matching_events[0]['event_date'] if matching_events else None,
        'by_year': {}
    }

    # Group by year
    for event in matching_events:
        year = event['event_date'][:4] if event['event_date'] else 'Unknown'
        summary['by_year'][year] = summary['by_year'].get(year, 0) + 1

    return jsonify({
        'was_hit': was_hit,
        'location': {'lat': lat, 'lon': lon},
        'summary': summary,
        'events': matching_events
    })


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in miles."""
    import math
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def _point_in_polygon(lat: float, lon: float, polygon: dict) -> bool:
    """Check if a point is inside a GeoJSON polygon using ray casting."""
    if polygon.get('type') != 'Polygon':
        return False

    coords = polygon.get('coordinates', [[]])[0]
    if len(coords) < 3:
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


@hail_events_api_bp.route('/impact-report', methods=['POST'])
@login_required
def generate_impact_report():
    """
    Generate a PDF hail impact report for a location.

    JSON body:
        lat: Latitude (required)
        lon: Longitude (required)
        years: Years to look back (default: 5)
        radius_miles: Search radius (default: 5)
        address: Optional street address for display
        company_name: Optional company name (default: from settings)
        company_phone: Optional contact phone
        company_email: Optional contact email
        company_website: Optional website

    Returns:
        PDF file download
    """
    from flask import Response, send_file
    import io

    data = request.get_json() or {}

    lat = data.get('lat')
    lon = data.get('lon')

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon are required'}), 400

    years = data.get('years', 5)
    radius_miles = data.get('radius_miles', 5)
    address = data.get('address')

    # Get company branding from request or use defaults
    company_name = data.get('company_name', 'HailTracker Pro')
    company_phone = data.get('company_phone', '')
    company_email = data.get('company_email', '')
    company_website = data.get('company_website', '')

    try:
        # First, get the location check data using the existing function
        # We'll call the logic directly rather than making another HTTP request
        import math
        import json as json_lib
        from datetime import date, timedelta

        cutoff_date = date.today() - timedelta(days=years * 365)

        db = _get_hail_db()

        lat_delta = radius_miles / 69.0
        lon_delta = radius_miles / (69.0 * math.cos(math.radians(lat)))

        events = db.execute("""
            SELECT
                id, event_name, event_date, center_lat, center_lon,
                max_hail_size, swath_polygon, swath_area_sqmi,
                estimated_vehicles, data_source, confidence_score
            FROM hail_events
            WHERE event_date >= ?
            AND center_lat BETWEEN ? AND ?
            AND center_lon BETWEEN ? AND ?
            ORDER BY event_date DESC
            LIMIT 100
        """, (
            cutoff_date.isoformat(),
            lat - lat_delta, lat + lat_delta,
            lon - lon_delta, lon + lon_delta
        ))

        matching_events = []
        for event in events:
            swath_json = event.get('swath_polygon')
            if swath_json:
                try:
                    swath = json_lib.loads(swath_json)
                    if _point_in_polygon(lat, lon, swath):
                        matching_events.append({
                            'id': event['id'],
                            'event_name': event['event_name'],
                            'event_date': event['event_date'],
                            'hail_size_inches': event['max_hail_size'] or 0,
                            'distance_miles': _haversine_distance(
                                lat, lon,
                                event['center_lat'], event['center_lon']
                            ),
                            'data_source': event['data_source'],
                            'confidence': event['confidence_score']
                        })
                except json_lib.JSONDecodeError:
                    pass
            elif event.get('center_lat') and event.get('center_lon'):
                dist = _haversine_distance(lat, lon, event['center_lat'], event['center_lon'])
                if dist <= radius_miles:
                    matching_events.append({
                        'id': event['id'],
                        'event_name': event['event_name'],
                        'event_date': event['event_date'],
                        'hail_size_inches': event['max_hail_size'] or 0,
                        'distance_miles': round(dist, 2),
                        'data_source': event['data_source'],
                        'confidence': event['confidence_score']
                    })

        # Build summary
        summary = {
            'total_events': len(matching_events),
            'max_hail_size': max((e['hail_size_inches'] or 0) for e in matching_events) if matching_events else 0,
            'years_checked': years,
            'radius_miles': radius_miles,
            'most_recent': matching_events[0]['event_date'] if matching_events else None,
            'by_year': {}
        }

        for event in matching_events:
            year = event['event_date'][:4] if event['event_date'] else 'Unknown'
            summary['by_year'][year] = summary['by_year'].get(year, 0) + 1

        # Generate PDF
        from src.reports.hail_impact_report import generate_hail_impact_report

        pdf_bytes = generate_hail_impact_report(
            location={'lat': lat, 'lon': lon},
            events=matching_events,
            summary=summary,
            address=address,
            radius_miles=radius_miles,
            years_checked=years,
            company_name=company_name,
            company_phone=company_phone,
            company_email=company_email,
            company_website=company_website
        )

        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"hail_impact_report_{timestamp}.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )

    except ImportError as e:
        return jsonify({
            'error': 'PDF generation requires reportlab. Install with: pip install reportlab',
            'details': str(e)
        }), 501
    except Exception as e:
        return jsonify({'error': f'Failed to generate report: {str(e)}'}), 500


@hail_events_api_bp.route('/geocode-check', methods=['POST'])
@login_required
def geocode_and_check():
    """
    Geocode an address and check for hail history.

    JSON body:
        address: Street address (e.g., "123 Main St, Dallas, TX 75201")
        years: Years to look back (default: 5)

    Note: This requires a geocoding service. For now, returns an error
    suggesting to use lat/lon directly via /check-location.
    """
    data = request.get_json() or {}
    address = data.get('address')

    if not address:
        return jsonify({'error': 'address is required'}), 400

    # For now, we don't have a geocoding service integrated
    # Return a helpful message
    return jsonify({
        'error': 'Geocoding not yet implemented',
        'suggestion': 'Use /api/hail-events/check-location with lat and lon parameters',
        'example': {
            'endpoint': '/api/hail-events/check-location',
            'params': {'lat': 32.7767, 'lon': -96.7970, 'years': 5}
        },
        'tip': 'You can get coordinates from Google Maps by right-clicking on a location'
    }), 501


# =============================================================================
# STORM CALENDAR
# =============================================================================

@hail_events_api_bp.route('/calendar', methods=['GET'])
def get_storm_calendar():
    """
    Get storm calendar data for a specific month.

    Query params:
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
        state: Filter by state (optional)
        min_conf: Minimum confidence_score (0-100, default 0 = no filter)

    Returns:
        days: Dict mapping date strings to storm info
        month_stats: Summary statistics for the month
    """
    from calendar import monthrange

    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    state = request.args.get('state')
    min_conf = request.args.get('min_conf', 0, type=float)

    # Validate month
    if month < 1 or month > 12:
        return jsonify({'error': 'month must be 1-12'}), 400

    # Get first and last day of month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Query database (hail_events is in main DB)
    db = _get_hail_db()

    # Build query
    query = """
        SELECT
            event_date,
            id,
            event_name,
            max_hail_size,
            center_lat,
            center_lon,
            swath_area_sqmi,
            estimated_vehicles,
            data_source,
            confidence_score,
            swath_polygon,
            bbox_min_lat,
            bbox_max_lat,
            bbox_min_lon,
            bbox_max_lon,
            severity
        FROM hail_events
        WHERE event_date BETWEEN ? AND ?
    """
    params = [first_day.isoformat(), last_day.isoformat()]

    if min_conf > 0:
        query += " AND COALESCE(confidence_score, 100) >= ?"
        params.append(min_conf)

    if state:
        # Extract state from event_name if it contains state info
        query += " AND event_name LIKE ?"
        params.append(f'%{state}%')

    query += " ORDER BY event_date, max_hail_size DESC"

    try:
        events = db.execute(query, params)
    except Exception:
        # Fallback: bbox/severity columns may not exist yet
        query_fallback = """
            SELECT event_date, id, event_name, max_hail_size, center_lat, center_lon,
                   swath_area_sqmi, estimated_vehicles, data_source,
                   confidence_score, swath_polygon,
                   NULL as bbox_min_lat, NULL as bbox_max_lat,
                   NULL as bbox_min_lon, NULL as bbox_max_lon,
                   NULL as severity
            FROM hail_events WHERE event_date BETWEEN ? AND ?
        """
        fb_params = [first_day.isoformat(), last_day.isoformat()]
        if state:
            query_fallback += " AND event_name LIKE ?"
            fb_params.append(f'%{state}%')
        query_fallback += " ORDER BY event_date, max_hail_size DESC"
        events = db.execute(query_fallback, fb_params)

    # Group by date
    days = {}
    for event in events:
        event_date = str(event['event_date'])  # PG returns datetime.date; JSON keys must be str
        if event_date not in days:
            days[event_date] = {
                'count': 0,
                'max_hail_size': 0,
                'max_severity': 'MINOR',
                'total_vehicles': 0,
                'events': []
            }

        day = days[event_date]
        day['count'] += 1

        hail_size = event['max_hail_size'] or 0
        if hail_size > day['max_hail_size']:
            day['max_hail_size'] = hail_size

        # Determine severity
        if hail_size >= 2.0:
            severity = 'SEVERE'
        elif hail_size >= 1.0:
            severity = 'MODERATE'
        else:
            severity = 'MINOR'

        # Track max severity
        severity_order = {'MINOR': 1, 'MODERATE': 2, 'SEVERE': 3, 'CATASTROPHIC': 4}
        if severity_order.get(severity, 0) > severity_order.get(day['max_severity'], 0):
            day['max_severity'] = severity

        day['total_vehicles'] += event['estimated_vehicles'] or 0

        day['events'].append({
            'id': event['id'],
            'event_name': event['event_name'],
            'event_date': event_date,
            'hail_size': hail_size,
            'severity': severity,
            'lat': event['center_lat'],
            'lon': event['center_lon'],
            'area_sqmi': event['swath_area_sqmi'],
            'vehicles': event['estimated_vehicles'],
            'source': event['data_source'],
            'confidence_score': event['confidence_score'],
            'swath_polygon': event['swath_polygon'],
            'bbox_min_lat': event['bbox_min_lat'],
            'bbox_max_lat': event['bbox_max_lat'],
            'bbox_min_lon': event['bbox_min_lon'],
            'bbox_max_lon': event['bbox_max_lon'],
        })

    # Calculate month stats
    total_events = sum(d['count'] for d in days.values())
    storm_days = len(days)
    max_hail = max((d['max_hail_size'] for d in days.values()), default=0)
    total_vehicles = sum(d['total_vehicles'] for d in days.values())

    return jsonify({
        'year': year,
        'month': month,
        'days': days,
        'month_stats': {
            'total_events': total_events,
            'storm_days': storm_days,
            'max_hail_size': max_hail,
            'total_vehicles': total_vehicles,
            'severe_days': sum(1 for d in days.values() if d['max_severity'] == 'SEVERE'),
            'moderate_days': sum(1 for d in days.values() if d['max_severity'] == 'MODERATE'),
            'minor_days': sum(1 for d in days.values() if d['max_severity'] == 'MINOR')
        }
    })


@hail_events_api_bp.route('/calendar/year', methods=['GET'])
def get_storm_calendar_year():
    """
    Get storm calendar overview for an entire year.

    Query params:
        year: Year (default: current year)
        state: Filter by state (optional)

    Returns:
        months: Dict mapping month numbers to summary stats
        year_stats: Summary statistics for the year
    """
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    state = request.args.get('state')

    # Query database (hail_events is in main DB)
    db = _get_hail_db()

    # Query for entire year
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    query = """
        SELECT
            event_date,
            max_hail_size,
            estimated_vehicles
        FROM hail_events
        WHERE event_date BETWEEN ? AND ?
    """
    params = [start_date, end_date]

    if state:
        query += " AND event_name LIKE ?"
        params.append(f'%{state}%')

    events = db.execute(query, params)

    # Group by month
    months = {i: {
        'storm_days': set(),
        'total_events': 0,
        'max_hail_size': 0,
        'total_vehicles': 0,
        'severe_count': 0,
        'moderate_count': 0,
        'minor_count': 0
    } for i in range(1, 13)}

    for event in events:
        event_date = str(event['event_date'])  # PG returns datetime.date
        try:
            month = int(event_date[5:7])
        except Exception:
            continue

        m = months[month]
        m['storm_days'].add(event_date)
        m['total_events'] += 1

        hail_size = event['max_hail_size'] or 0
        if hail_size > m['max_hail_size']:
            m['max_hail_size'] = hail_size

        m['total_vehicles'] += event['estimated_vehicles'] or 0

        # Count by severity
        if hail_size >= 2.0:
            m['severe_count'] += 1
        elif hail_size >= 1.0:
            m['moderate_count'] += 1
        else:
            m['minor_count'] += 1

    # Convert sets to counts
    result_months = {}
    for month_num, data in months.items():
        result_months[month_num] = {
            'storm_days': len(data['storm_days']),
            'total_events': data['total_events'],
            'max_hail_size': data['max_hail_size'],
            'total_vehicles': data['total_vehicles'],
            'severe_count': data['severe_count'],
            'moderate_count': data['moderate_count'],
            'minor_count': data['minor_count']
        }

    # Calculate year stats
    total_events = sum(m['total_events'] for m in result_months.values())
    total_storm_days = sum(m['storm_days'] for m in result_months.values())
    max_hail = max((m['max_hail_size'] for m in result_months.values()), default=0)
    total_vehicles = sum(m['total_vehicles'] for m in result_months.values())

    return jsonify({
        'year': year,
        'months': result_months,
        'year_stats': {
            'total_events': total_events,
            'total_storm_days': total_storm_days,
            'max_hail_size': max_hail,
            'total_vehicles': total_vehicles,
            'peak_month': max(result_months.items(), key=lambda x: x[1]['total_events'])[0] if total_events > 0 else None
        }
    })


# =============================================================================
# DAMAGE GRID ENDPOINTS
# =============================================================================

@hail_events_api_bp.route('/damage-grid', methods=['GET'])
def get_damage_grid_bbox():
    """
    Query damage grid cells by bounding box.

    Query params:
        min_lat, max_lat, min_lon, max_lon (required)
        min_prob: Minimum damage probability (default 0.1)
        min_conf: Minimum cell confidence (default 0)
        max_cells: Maximum cells to return (default 20000)
        format: 'geojson' (default) or 'raw'
    """
    min_lat = request.args.get('min_lat', type=float)
    max_lat = request.args.get('max_lat', type=float)
    min_lon = request.args.get('min_lon', type=float)
    max_lon = request.args.get('max_lon', type=float)

    if None in (min_lat, max_lat, min_lon, max_lon):
        return jsonify({'error': 'min_lat, max_lat, min_lon, max_lon required'}), 400

    min_prob = request.args.get('min_prob', 0.1, type=float)
    min_conf = request.args.get('min_conf', 0, type=float)
    max_cells = request.args.get('max_cells', 20000, type=int)
    fmt = request.args.get('format', 'geojson')

    from src.radar.damage_grid import query_damage_grid_bbox, cells_to_geojson

    cells = query_damage_grid_bbox(
        min_lon=min_lon, min_lat=min_lat,
        max_lon=max_lon, max_lat=max_lat,
        db_path=MAIN_DB_PATH,
        min_prob=min_prob, min_conf=min_conf, max_cells=max_cells,
    )

    if fmt == 'raw':
        return jsonify({'cells': cells, 'count': len(cells)})

    geojson = cells_to_geojson(cells)
    return jsonify(geojson)


@hail_events_api_bp.route('/<event_name>/damage-grid', methods=['GET'])
def get_event_damage_grid(event_name):
    """
    Get damage grid for a specific event.

    Query params:
        min_prob: Minimum damage probability (default 0.0)
        min_conf: Minimum cell confidence (default 0)
        max_cells: Maximum cells (default 20000)
        format: 'geojson' (default) or 'raw'
    """
    min_prob = request.args.get('min_prob', 0.0, type=float)
    min_conf = request.args.get('min_conf', 0, type=float)
    max_cells = request.args.get('max_cells', 20000, type=int)
    fmt = request.args.get('format', 'geojson')

    from src.radar.damage_grid import query_damage_grid, cells_to_geojson

    cells = query_damage_grid(
        event_name=event_name,
        db_path=MAIN_DB_PATH,
        min_prob=min_prob, min_conf=min_conf, max_cells=max_cells,
    )

    if not cells:
        return jsonify({'error': 'No damage grid data', 'event_name': event_name}), 404

    if fmt == 'raw':
        return jsonify({'event_name': event_name, 'cells': cells, 'count': len(cells)})

    geojson = cells_to_geojson(cells)
    geojson['event_name'] = event_name
    geojson['cell_count'] = len(cells)
    return jsonify(geojson)


# =============================================================================
# BUSINESSES IN SWATH (read from swath_businesses cache)
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/businesses', methods=['GET'])
def get_event_businesses(event_id):
    """
    Return cached businesses discovered inside this event's hail swath.

    Reads from the swath_businesses cache table in the CRM database.
    Returns empty list if no businesses have been discovered yet.

    Query params:
        limit: max results (default 200)
    """
    import sqlite3 as _sqlite3

    limit = min(int(request.args.get('limit', 200)), 500)

    # swath_businesses cache lives in the CRM SQLite DB
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    crm_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')

    try:
        conn = _sqlite3.connect(crm_path)
        conn.row_factory = _sqlite3.Row
        rows = conn.execute(
            '''SELECT name, category, address, city, state, zip,
                      phone, website, latitude, longitude,
                      estimated_vehicles, source
               FROM swath_businesses
               WHERE event_id = ? AND in_swath = 1
               ORDER BY estimated_vehicles DESC
               LIMIT ?''',
            (event_id, limit)
        ).fetchall()
        conn.close()

        businesses = [dict(r) for r in rows]
        return jsonify({
            'event_id': event_id,
            'businesses': businesses,
            'count': len(businesses),
        })
    except (_sqlite3.OperationalError, FileNotFoundError):
        # Table or file doesn't exist yet — no businesses discovered
        return jsonify({
            'event_id': event_id,
            'businesses': [],
            'count': 0,
        })


# =============================================================================
# DISCOVER BUSINESSES (run OSM discovery into swath_businesses cache)
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/discover-businesses', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def discover_event_businesses(event_id):
    """
    Run business discovery for a hail event's swath area.

    Fetches the event from the main DB (PG or SQLite), runs OSM discovery,
    filters by point-in-polygon, and caches results in the CRM DB.

    JSON body (all optional):
        force_refresh: bool  — re-run even if cache exists (default false)

    Returns:
        {success, event_id, discovered_count, total_cached_count}
    """
    import json
    import sqlite3 as _sqlite3
    import logging

    logger = logging.getLogger(__name__)
    body = request.get_json(silent=True) or {}
    force_refresh = body.get('force_refresh', False)

    # 1. Fetch event from main DB (works with both PG and SQLite)
    db = get_main_db()
    rows = db.execute(
        "SELECT id, event_name, event_date, center_lat, center_lon, "
        "max_hail_size, swath_polygon FROM hail_events WHERE id = ?",
        (event_id,)
    )

    if not rows:
        return jsonify({'success': False, 'error': 'Event not found'}), 404

    event = rows[0]
    center_lat = event.get('center_lat')
    center_lon = event.get('center_lon')

    if not center_lat or not center_lon:
        return jsonify({
            'success': False,
            'error': 'Event missing center coordinates'
        }), 400

    # 2. Check CRM cache
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    crm_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')

    try:
        crm_conn = _sqlite3.connect(crm_path)
        cached_count = crm_conn.execute(
            'SELECT COUNT(*) FROM swath_businesses WHERE event_id = ?',
            (event_id,)
        ).fetchone()[0]
        crm_conn.close()
    except _sqlite3.OperationalError:
        cached_count = 0

    if cached_count > 0 and not force_refresh:
        return jsonify({
            'success': True,
            'event_id': event_id,
            'discovered_count': 0,
            'total_cached_count': cached_count,
            'source': 'cache'
        })

    # 3. Initialize discovery service (CRM path only — we skip hail DB read)
    from src.business.swath_discovery import SwathDiscoveryService
    service = SwathDiscoveryService(crm_db_path=crm_path)

    # 4. Build swath polygon from event data
    polygon = None
    raw_polygon = event.get('swath_polygon')
    if raw_polygon:
        try:
            geojson = json.loads(raw_polygon) if isinstance(raw_polygon, str) else raw_polygon
            if geojson and geojson.get('type') == 'Polygon':
                polygon = geojson
        except (json.JSONDecodeError, TypeError):
            pass

    max_hail = float(event.get('max_hail_size') or 1.0)
    if polygon is None:
        radius_miles = max(2.0, max_hail * 2.5)
        polygon = service._create_circle_polygon(
            float(center_lat), float(center_lon), radius_miles
        )

    # 5. Calculate search radius
    search_area = service.get_swath_search_area(polygon)
    if search_area:
        _, _, radius_miles = search_area
    else:
        radius_miles = max(2.0, max_hail * 2.5)

    # Add small buffer for edge businesses
    search_radius = radius_miles + 1.0

    # 6. Run OSM discovery (free, unlimited, no API key needed)
    logger.info(
        "Running OSM discovery for event %s at (%.4f, %.4f) radius %.1f mi",
        event_id, float(center_lat), float(center_lon), search_radius
    )
    try:
        businesses = service.search_osm_comprehensive(
            float(center_lat), float(center_lon), search_radius
        )
    except Exception as e:
        logger.error("OSM discovery failed for event %s: %s", event_id, e)
        return jsonify({
            'success': False,
            'error': f'Discovery failed: {str(e)}'
        }), 500

    # 7. Point-in-polygon filter
    in_swath = [
        b for b in businesses
        if service.point_in_polygon(
            float(b.get('latitude', 0)),
            float(b.get('longitude', 0)),
            polygon
        )
    ]

    logger.info(
        "Event %s: %d OSM results, %d in swath",
        event_id, len(businesses), len(in_swath)
    )

    # 8. Clear old cache if force_refresh
    if force_refresh and cached_count > 0:
        try:
            crm_conn = _sqlite3.connect(crm_path)
            crm_conn.execute(
                'DELETE FROM swath_businesses WHERE event_id = ?',
                (event_id,)
            )
            crm_conn.commit()
            crm_conn.close()
        except _sqlite3.OperationalError:
            pass

    # 9. Save to cache
    storm_date = event.get('event_date', '')
    service._save_businesses_to_cache(in_swath, event_id, storm_date)

    # 10. Get final cached count
    try:
        crm_conn = _sqlite3.connect(crm_path)
        total_count = crm_conn.execute(
            'SELECT COUNT(*) FROM swath_businesses WHERE event_id = ?',
            (event_id,)
        ).fetchone()[0]
        crm_conn.close()
    except _sqlite3.OperationalError:
        total_count = len(in_swath)

    return jsonify({
        'success': True,
        'event_id': event_id,
        'discovered_count': len(in_swath),
        'total_cached_count': total_count,
        'source': 'discovery'
    })


# =============================================================================
# CONVERT BUSINESSES TO LEADS
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/convert-businesses-to-leads', methods=['POST'])
@login_required
@require_any_permission('leads.view_all', 'admin.access')
def convert_businesses_to_leads(event_id):
    """
    Convert discovered swath_businesses into CRM leads.

    Reads cached businesses for this event, deduplicates against existing
    leads/customers, and creates new lead records via CustomerManager.

    JSON body (all optional):
        mode: "all" | "top"  (default "all")
        top_n: int           (default 50, used when mode="top")
        min_estimated_vehicles: int  (filter, default 0)
        force: bool          (skip dedup if true, default false)

    Returns:
        {success, event_id, created, skipped, total_processed}
    """
    import sqlite3 as _sqlite3
    import logging

    logger = logging.getLogger(__name__)
    body = request.get_json(silent=True) or {}
    mode = body.get('mode', 'all')
    top_n = min(int(body.get('top_n', 50)), 500)
    min_vehicles = int(body.get('min_estimated_vehicles', 0))
    force = body.get('force', False)

    # 1. Fetch swath_businesses from CRM DB
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    crm_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')

    try:
        crm_conn = _sqlite3.connect(crm_path)
        crm_conn.row_factory = _sqlite3.Row

        query = '''SELECT id, name, category, address, city, state, zip,
                          phone, website, email, latitude, longitude,
                          estimated_vehicles, source, storm_date
                   FROM swath_businesses
                   WHERE event_id = ? AND in_swath = 1'''
        params = [event_id]

        if min_vehicles > 0:
            query += ' AND estimated_vehicles >= ?'
            params.append(min_vehicles)

        query += ' ORDER BY estimated_vehicles DESC'

        if mode == 'top':
            query += ' LIMIT ?'
            params.append(top_n)

        rows = crm_conn.execute(query, params).fetchall()
        businesses = [dict(r) for r in rows]
        crm_conn.close()
    except _sqlite3.OperationalError:
        return jsonify({
            'success': False,
            'error': 'No businesses discovered yet for this event'
        }), 404

    if not businesses:
        return jsonify({
            'success': True,
            'event_id': event_id,
            'created': 0,
            'skipped': 0,
            'total_processed': 0,
            'message': 'No businesses match the criteria'
        })

    # 2. Fetch event metadata from main DB
    db = get_main_db()
    event_rows = db.execute(
        "SELECT event_date, max_hail_size, event_name FROM hail_events WHERE id = ?",
        (event_id,)
    )
    event_meta = event_rows[0] if event_rows else {}
    storm_date = event_meta.get('event_date', '')
    max_hail = event_meta.get('max_hail_size', '')
    event_name = event_meta.get('event_name', '')

    # 3. Instantiate CustomerManager with CRM DB
    from src.db.database import Database
    from src.crm.managers.customer_manager import CustomerManager

    crm_db = Database(crm_path)
    mgr = CustomerManager(crm_db)

    created = 0
    skipped = 0
    created_ids = []
    converted_biz_ids = []

    for biz in businesses:
        # 4. Dedupe check (unless force=True)
        if not force:
            existing = None
            if biz.get('email'):
                existing = mgr._find_existing_lead_or_customer(
                    email=biz['email']
                )
            if not existing and biz.get('phone'):
                existing = mgr._find_existing_lead_or_customer(
                    phone=biz['phone']
                )
            # Fallback: check company_name + city for this event's leads
            if not existing and biz.get('name'):
                dupes = crm_db.execute(
                    "SELECT id FROM leads WHERE company_name = ? "
                    "AND hail_event_id = ? AND deleted_at IS NULL",
                    (biz['name'], event_id)
                )
                if dupes:
                    existing = dupes[0]

            if existing:
                skipped += 1
                continue

        # 5. Build lead data
        addr_parts = [biz.get('address', ''), biz.get('city', ''),
                      biz.get('state', ''), biz.get('zip', '')]
        full_addr = ', '.join(p for p in addr_parts if p)

        provenance = []
        if storm_date:
            provenance.append(f"Storm: {storm_date}")
        if max_hail:
            provenance.append(f"Max hail: {max_hail}\"")
        if event_name:
            provenance.append(f"Event: {event_name}")
        if biz.get('category'):
            provenance.append(f"Category: {biz['category']}")
        if full_addr:
            provenance.append(f"Address: {full_addr}")
        if biz.get('estimated_vehicles'):
            provenance.append(f"Est. vehicles: {biz['estimated_vehicles']}")
        if biz.get('website'):
            provenance.append(f"Website: {biz['website']}")

        lead_data = {
            'company_name': biz.get('name', ''),
            'phone': biz.get('phone', ''),
            'email': biz.get('email', ''),
            'source': 'HAIL_EVENT',
            'hail_event_id': event_id,
            'damage_type': 'HAIL',
            'notes': ' | '.join(provenance),
        }

        try:
            lead_id = mgr.create_lead(lead_data)
            created += 1
            created_ids.append(lead_id)
            converted_biz_ids.append(biz['id'])
        except Exception as e:
            logger.warning("Failed to create lead for %s: %s",
                           biz.get('name', ''), e)
            skipped += 1

    # 6. Mark converted businesses in swath_businesses cache
    if converted_biz_ids:
        try:
            crm_conn = _sqlite3.connect(crm_path)
            placeholders = ','.join('?' * len(converted_biz_ids))
            crm_conn.execute(
                f'UPDATE swath_businesses SET added_to_crm = 1 '
                f'WHERE id IN ({placeholders})',
                converted_biz_ids
            )
            crm_conn.commit()
            crm_conn.close()
        except _sqlite3.OperationalError:
            pass

    logger.info(
        "Event %s: converted %d businesses to leads (%d skipped)",
        event_id, created, skipped
    )

    return jsonify({
        'success': True,
        'event_id': event_id,
        'created': created,
        'skipped': skipped,
        'total_processed': len(businesses)
    })


# =============================================================================
# EXPORT BUSINESSES CSV
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/businesses.csv', methods=['GET'])
@login_required
def export_businesses_csv(event_id):
    """
    Export discovered businesses for a hail event as CSV.

    Query params:
        limit: max rows (default 500)

    Returns: CSV file download.
    """
    import csv
    import io
    import sqlite3 as _sqlite3
    from flask import Response

    limit = min(int(request.args.get('limit', 500)), 2000)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    crm_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')

    columns = ['name', 'category', 'address', 'city', 'state', 'zip',
               'phone', 'website', 'estimated_vehicles',
               'latitude', 'longitude', 'source']

    try:
        conn = _sqlite3.connect(crm_path)
        conn.row_factory = _sqlite3.Row
        rows = conn.execute(
            f'''SELECT {", ".join(columns)}
                FROM swath_businesses
                WHERE event_id = ? AND in_swath = 1
                ORDER BY estimated_vehicles DESC
                LIMIT ?''',
            (event_id, limit)
        ).fetchall()
        conn.close()
    except _sqlite3.OperationalError:
        rows = []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row[c] for c in columns])

    csv_content = output.getvalue()
    output.close()

    filename = f"businesses_event_{event_id}.csv"
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
