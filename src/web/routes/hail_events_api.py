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
from src.core.auth.decorators import login_required
from src.db.database import Database
import os

# DEBUG: Confirm module is loaded
print("="*60)
print(">>> LOADING hail_events_api.py MODULE <<<")
print("="*60)

hail_events_api_bp = Blueprint('hail_events_api', __name__, url_prefix='/api/hail-events')

# DEBUG: Confirm blueprint is created
print(f">>> Blueprint created: {hail_events_api_bp.name} with prefix {hail_events_api_bp.url_prefix}")


def get_manager():
    """Get HailEventManager instance"""
    from src.crm.managers.hail_event_manager import HailEventManager
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    db = Database(db_path)
    return HailEventManager(db)


# =============================================================================
# STORM CRUD
# =============================================================================

@hail_events_api_bp.route('', methods=['GET'])
@login_required
def list_hail_events():
    """List hail events with filtering and verification data.

    Query params:
        days: Number of days to look back (default: 90)
        severity: Filter by severity
        status: Filter by status
        limit: Max results (default: 100, max: 500)
        include_verifications: Include verification counts (default: true)

        # Bounds filtering (for map viewport)
        min_lat, max_lat, min_lon, max_lon: Geographic bounds
    """
    import logging
    logger = logging.getLogger('HailTrackerWeb')

    # CRITICAL DEBUG - write to file
    import sys
    debug_file = open('C:/Users/xtxll/hail_api_debug.log', 'a')
    debug_file.write("\n" + "="*60 + "\n")
    debug_file.write(f">>> HAIL EVENTS LIST ENDPOINT CALLED at {date.today()}\n")
    debug_file.write(f">>> Request URL: {request.url}\n")
    debug_file.write(f">>> Request args: {dict(request.args)}\n")
    debug_file.write("="*60 + "\n")
    debug_file.flush()
    debug_file.close()

    # Also print to stdout with flush
    print("\n" + "="*60, flush=True)
    print(">>> HAIL EVENTS LIST ENDPOINT CALLED <<<", flush=True)
    print(f">>> Request URL: {request.url}", flush=True)
    print(f">>> Request args: {dict(request.args)}", flush=True)
    print("="*60 + "\n", flush=True)
    sys.stdout.flush()

    logger.info(f"[LIST-EVENTS] Request args: {dict(request.args)}")

    manager = get_manager()

    # Filters
    days = request.args.get('days', 90, type=int)
    severity = request.args.get('severity')
    status = request.args.get('status')
    limit = request.args.get('limit', 100, type=int)
    limit = min(limit, 500)
    include_verifications = request.args.get('include_verifications', 'true').lower() == 'true'

    # Bounds filtering for map viewport
    min_lat = request.args.get('min_lat', type=float)
    max_lat = request.args.get('max_lat', type=float)
    min_lon = request.args.get('min_lon', type=float)
    max_lon = request.args.get('max_lon', type=float)

    # Date filtering - show only storms from specific date
    event_date_filter = request.args.get('event_date')  # YYYY-MM-DD format

    logger.info(f"[LIST-EVENTS] event_date_filter={event_date_filter}, type={type(event_date_filter)}, bounds={min_lat},{max_lat},{min_lon},{max_lon}")
    print(f"[DEBUG] event_date_filter = '{event_date_filter}', request.args = {dict(request.args)}")

    cutoff = date.today() - timedelta(days=days)

    # If bounds provided, use direct SQL query for better performance
    if all([min_lat is not None, max_lat is not None, min_lon is not None, max_lon is not None]):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
        db = Database(db_path)

        # Build query based on whether date filter is provided
        if event_date_filter:
            # Filter to specific date
            query = """
                SELECT id, event_name, event_date, center_lat, center_lon,
                       max_hail_size, swath_polygon, swath_area_sqmi,
                       data_source, confidence_score, affected_locations,
                       estimated_vehicles, created_at
                FROM hail_events
                WHERE center_lat >= ? AND center_lat <= ?
                  AND center_lon >= ? AND center_lon <= ?
                  AND date(event_date) = date(?)
                ORDER BY event_date DESC
                LIMIT ?
            """
            events = db.execute(query, (min_lat, max_lat, min_lon, max_lon, event_date_filter, limit))
        else:
            # No date filter - use cutoff
            query = """
                SELECT id, event_name, event_date, center_lat, center_lon,
                       max_hail_size, swath_polygon, swath_area_sqmi,
                       data_source, confidence_score, affected_locations,
                       estimated_vehicles, created_at
                FROM hail_events
                WHERE center_lat >= ? AND center_lat <= ?
                  AND center_lon >= ? AND center_lon <= ?
                  AND event_date >= ?
                ORDER BY event_date DESC
                LIMIT ?
            """
            events = db.execute(query, (min_lat, max_lat, min_lon, max_lon, cutoff.isoformat(), limit))

        # Convert to list of dicts
        events = [dict(e) for e in events]
        logger.info(f"[LIST-EVENTS] With bounds: returned {len(events)} events, date_filter={event_date_filter}")
    else:
        # No bounds - ALWAYS use direct SQL query for date filtering
        print(f"\n[DEBUG] NO BOUNDS PATH")
        print(f"[DEBUG] event_date_filter = '{event_date_filter}' (type: {type(event_date_filter).__name__})")
        print(f"[DEBUG] bool(event_date_filter) = {bool(event_date_filter)}")

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
        db = Database(db_path)

        # ALWAYS check for date filter - be explicit
        if event_date_filter is not None and event_date_filter != '':
            # Filter to specific date (no bounds)
            print(f"[DEBUG] >>> APPLYING DATE FILTER: '{event_date_filter}'")
            query = """
                SELECT id, event_name, event_date, center_lat, center_lon,
                       max_hail_size, swath_polygon, swath_area_sqmi,
                       data_source, confidence_score, affected_locations,
                       estimated_vehicles, created_at
                FROM hail_events
                WHERE date(event_date) = date(?)
                ORDER BY event_date DESC
                LIMIT ?
            """
            print(f"[DEBUG] Executing: WHERE date(event_date) = date('{event_date_filter}')")
            events = db.execute(query, (event_date_filter, limit))
            print(f"[DEBUG] Query returned {len(events)} events")
            if events:
                unique_dates = set(e.get('event_date') for e in events)
                print(f"[DEBUG] Unique dates in results: {unique_dates}")
            logger.info(f"[LIST-EVENTS] Date filter applied (no bounds): {len(events)} events for date {event_date_filter}")
        else:
            # No date filter, no bounds - use manager (returns all recent events)
            print(f"[DEBUG] >>> NO DATE FILTER - using manager.search_storms()")
            events = manager.search_storms(
                severity=severity,
                status=status,
                start_date=cutoff,
                limit=limit
            )
            print(f"[DEBUG] manager.search_storms returned {len(events)} events")

    # Add verification data if requested
    if include_verifications and events:
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
            db = Database(db_path)

            # Get verification counts for all events in one query
            event_ids = [e['id'] for e in events if 'id' in e]
            if event_ids:
                placeholders = ','.join('?' * len(event_ids))
                verification_counts = db.execute(f"""
                    SELECT hail_event_id, COUNT(*) as count,
                           GROUP_CONCAT(DISTINCT source) as sources
                    FROM storm_verifications
                    WHERE hail_event_id IN ({placeholders})
                    GROUP BY hail_event_id
                """, event_ids)

                # Create lookup dict
                verif_lookup = {v['hail_event_id']: v for v in verification_counts}

                # Add to events
                for event in events:
                    verif = verif_lookup.get(event.get('id'))
                    if verif:
                        event['verification_count'] = verif['count']
                        event['verified'] = verif['count'] > 0
                        event['verification_sources'] = verif['sources'].split(',') if verif.get('sources') else []
                    else:
                        event['verification_count'] = 0
                        event['verified'] = False
                        event['verification_sources'] = []
        except Exception as e:
            # Log but don't fail the request
            import logging
            logging.warning(f"Failed to fetch verification data: {e}")

    # Get overall stats
    stats = manager.get_overall_storm_stats(days)

    return jsonify({
        'events': events,
        'count': len(events),
        'stats': stats,
        '_debug': {
            'event_date_filter': event_date_filter,
            'endpoint_version': 'v2-with-date-filter',
            'events_returned': len(events)
        }
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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

    # Get database connection
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    db = Database(db_path)

    # Convert radius to approximate lat/lon delta
    # 1 degree latitude = ~69 miles
    # 1 degree longitude = ~69 * cos(lat) miles
    lat_delta = radius_miles / 69.0
    lon_delta = radius_miles / (69.0 * math.cos(math.radians(lat)))

    # Query for nearby events within bounding box
    # Use larger limit to get all potential events, then filter by distance/polygon
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
        LIMIT 2000
    """, (
        cutoff_date.isoformat(),
        lat - lat_delta, lat + lat_delta,
        lon - lon_delta, lon + lon_delta
    ))

    # Filter to events within radius (using center distance)
    # The polygon check was too restrictive - most searches want events NEAR the location
    matching_events = []
    for event in events:
        if not event.get('center_lat') or not event.get('center_lon'):
            continue

        # Calculate distance from search point to event center
        dist = _haversine_distance(lat, lon, event['center_lat'], event['center_lon'])

        # Include if within radius
        if dist <= radius_miles:
            matching_events.append({
                'id': event['id'],
                'event_name': event['event_name'],
                'event_date': event['event_date'],
                'hail_size_inches': event['max_hail_size'],
                'max_hail_size': event['max_hail_size'],
                'swath_polygon': event['swath_polygon'],
                'swath_area_sqmi': event['swath_area_sqmi'],
                'center_lat': event['center_lat'],
                'center_lon': event['center_lon'],
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

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
        db = Database(db_path)

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
@login_required
def get_storm_calendar():
    """
    Get storm calendar data for a specific month.

    Query params:
        year: Year (default: current year)
        month: Month 1-12 (default: current month)
        state: Filter by state (optional)

    Returns:
        days: Dict mapping date strings to storm info
        month_stats: Summary statistics for the month
    """
    from calendar import monthrange

    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    state = request.args.get('state')

    # Validate month
    if month < 1 or month > 12:
        return jsonify({'error': 'month must be 1-12'}), 400

    # Get first and last day of month
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    # Query database
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    db = Database(db_path)

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
            data_source
        FROM hail_events
        WHERE event_date BETWEEN ? AND ?
    """
    params = [first_day.isoformat(), last_day.isoformat()]

    if state:
        # Extract state from event_name if it contains state info
        query += " AND event_name LIKE ?"
        params.append(f'%{state}%')

    query += " ORDER BY event_date, max_hail_size DESC"

    events = db.execute(query, params)

    # Group by date
    days = {}
    for event in events:
        event_date = event['event_date']
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
            'source': event['data_source']
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
@login_required
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

    # Query database
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    db = Database(db_path)

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
        event_date = event['event_date']
        try:
            month = int(event_date[5:7])
        except:
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
# SOCIAL MEDIA VERIFICATIONS
# =============================================================================

def get_verification_manager():
    """Get StormVerificationManager instance"""
    from src.crm.managers.storm_verification_manager import StormVerificationManager
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return StormVerificationManager(db_path)


@hail_events_api_bp.route('/<int:event_id>/verifications', methods=['GET'])
@login_required
def get_event_verifications(event_id):
    """
    Get all social media verifications for a hail event.

    Returns list of verification records with AI analysis results.
    """
    manager = get_verification_manager()

    verifications = manager.get_verifications_for_event(event_id)
    summary = manager.get_verification_summary(event_id)

    return jsonify({
        'event_id': event_id,
        'verifications': verifications,
        'summary': summary
    })


@hail_events_api_bp.route('/<int:event_id>/verifications', methods=['POST'])
@login_required
def add_event_verification(event_id):
    """
    Add a social media verification to a hail event.

    Body:
        source: reddit, twitter, instagram, youtube, facebook, manual
        post_url: URL of the post
        photo_url: URL of photo (optional)
        hail_size_mentioned: Text description of size (optional)
        hail_size_inches: Size in inches (optional)
        ... other optional fields
    """
    manager = get_verification_manager()
    data = request.get_json()

    if 'source' not in data or 'post_url' not in data:
        return jsonify({'error': 'source and post_url required'}), 400

    # Validate source
    valid_sources = ['reddit', 'twitter', 'instagram', 'youtube', 'facebook', 'manual']
    if data['source'] not in valid_sources:
        return jsonify({'error': f'source must be one of: {valid_sources}'}), 400

    try:
        verification_id = manager.add_verification(
            hail_event_id=event_id,
            source=data['source'],
            post_url=data['post_url'],
            **{k: v for k, v in data.items() if k not in ['source', 'post_url']}
        )

        return jsonify({
            'success': True,
            'verification_id': verification_id,
            'event_id': event_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/<int:event_id>/find-social-verification', methods=['POST'])
@login_required
def find_social_verification(event_id):
    """
    Search social media for posts matching this storm event.

    Uses the Reddit scraper to find relevant posts.

    Body:
        keywords: Optional additional keywords
        time_filter: hour, day, week, month (default: week)
        limit: Max posts to return (default: 25)

    Returns:
        posts: List of matching social media posts
    """
    data = request.get_json() or {}

    # Get event details
    manager = get_manager()
    event = manager.get_storm_event(event_id)

    if not event:
        return jsonify({'error': 'Event not found'}), 404

    # Build search keywords from event
    keywords = []

    # Add location-based keywords
    if event.get('event_name'):
        # Extract location from event name
        parts = event['event_name'].split(' - ')
        if parts:
            keywords.append(parts[0])  # Location name

    # Add date-based keywords
    if event.get('event_date'):
        event_date = event['event_date']
        if isinstance(event_date, str):
            event_date = datetime.fromisoformat(event_date).date()
        # Add month name
        keywords.append(event_date.strftime('%B'))

    # Add user-provided keywords
    if data.get('keywords'):
        if isinstance(data['keywords'], list):
            keywords.extend(data['keywords'])
        else:
            keywords.append(data['keywords'])

    # Always include "hail"
    keywords.append('hail')

    # Build search query
    search_query = ' '.join(keywords)

    try:
        from src.social.reddit import RedditScraper

        scraper = RedditScraper()

        time_filter = data.get('time_filter', 'week')
        limit = min(data.get('limit', 25), 100)

        # Search weather subreddits
        posts = []
        for subreddit in ['weather', 'stormchasing', 'tornado']:
            sub_posts = scraper.search_subreddit(
                subreddit,
                query=search_query,
                time_filter=time_filter,
                limit=limit // 3
            )
            posts.extend(sub_posts)

        # Convert to serializable format
        results = []
        for post in posts:
            results.append({
                'post_id': post.post_id,
                'subreddit': post.subreddit,
                'title': post.title,
                'author': post.author,
                'created_utc': post.created_utc.isoformat() if post.created_utc else None,
                'url': post.url,
                'permalink': post.permalink,
                'score': post.score,
                'num_comments': post.num_comments,
                'is_image': post.is_image,
                'is_video': post.is_video,
                'media_url': post.media_url,
                'thumbnail_url': post.thumbnail_url,
                'location_text': post.location_text,
                'hail_size_mentioned': post.hail_size_mentioned,
                'hail_size_inches': post.hail_size_inches,
                'relevance_score': post.relevance_score
            })

        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)

        return jsonify({
            'event_id': event_id,
            'search_query': search_query,
            'posts': results[:limit],
            'total_found': len(results)
        })

    except ImportError:
        return jsonify({
            'error': 'Reddit scraper not available',
            'tip': 'Install requests library: pip install requests'
        }), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/<int:event_id>/verification-summary', methods=['GET'])
@login_required
def get_verification_summary(event_id):
    """
    Get verification summary for a hail event.

    Returns:
        count: Number of verifications
        verified: Whether event is considered verified
        sources: List of sources used
        avg_confidence: Average AI confidence
        avg_size_inches: Average reported hail size
    """
    manager = get_verification_manager()

    summary = manager.get_verification_summary(event_id)

    return jsonify({
        'event_id': event_id,
        **summary
    })


@hail_events_api_bp.route('/verifications/<int:verification_id>', methods=['DELETE'])
@login_required
def delete_verification(verification_id):
    """Delete a verification."""
    manager = get_verification_manager()

    deleted = manager.delete_verification(verification_id)

    if not deleted:
        return jsonify({'error': 'Verification not found'}), 404

    return jsonify({
        'success': True,
        'deleted_id': verification_id
    })


@hail_events_api_bp.route('/verifications/<int:verification_id>/analyze', methods=['POST'])
@login_required
def analyze_verification_photo(verification_id):
    """
    Run AI analysis on a verification's photo.

    Downloads the photo and runs it through the hail size estimator.
    """
    manager = get_verification_manager()

    # Get verification
    conn = manager._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM storm_verifications WHERE id = ?", (verification_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Verification not found'}), 404

    verification = dict(row)
    photo_url = verification.get('photo_url')

    if not photo_url:
        return jsonify({'error': 'No photo URL for this verification'}), 400

    try:
        # Download image
        import requests
        from PIL import Image
        import io
        import numpy as np

        response = requests.get(photo_url, timeout=30)
        response.raise_for_status()

        img = Image.open(io.BytesIO(response.content))
        image_data = np.array(img)

        # Run through estimator
        from src.ml.models.hail_size_estimator import HailSizeEstimator
        estimator = HailSizeEstimator()
        estimator.load()

        result = estimator.estimate_size(image_data)

        # Update verification with AI results
        manager.update_ai_analysis(
            verification_id=verification_id,
            estimated_size=result['estimated_size_inches'],
            size_category=result['category'],
            confidence=result['confidence'],
            severity=result['severity'],
            detected_hail=True
        )

        return jsonify({
            'verification_id': verification_id,
            'analysis': result,
            'updated': True
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/<int:event_id>/auto-verify', methods=['POST'])
@login_required
def auto_verify_storm(event_id):
    """
    Automatically find and add social media verifications for a storm.

    Uses the Storm Verification Pipeline to:
    1. Search Reddit for matching hail posts
    2. Download and analyze photos with AI
    3. Store verifications linked to this event

    Body (optional):
        search_radius_days: Days before/after storm to search (default: 2)
        max_posts: Maximum posts to find (default: 20)
        auto_analyze: Whether to run AI on photos (default: true)

    Returns:
        posts_found: Number of matching posts found
        verifications_added: Number of verifications created
        photos_analyzed: Number of photos analyzed with AI
    """
    data = request.get_json() or {}

    # Get event details
    manager = get_manager()
    event = manager.get_storm_event(event_id)

    if not event:
        return jsonify({'error': 'Event not found'}), 404

    try:
        from src.social.storm_verification_pipeline import StormVerificationPipeline

        pipeline = StormVerificationPipeline()

        # Extract location info
        location = event.get('city') or event.get('event_name', '').split(' - ')[0]
        state = event.get('state')
        event_date = event.get('event_date')

        if isinstance(event_date, datetime):
            event_date = event_date.strftime('%Y-%m-%d')

        # Run pipeline
        result = pipeline.find_verifications_for_storm(
            storm_id=event_id,
            storm_location=location,
            storm_date=event_date,
            storm_state=state,
            search_radius_days=data.get('search_radius_days', 2),
            max_posts=data.get('max_posts', 20),
            auto_analyze=data.get('auto_analyze', True)
        )

        return jsonify({
            'event_id': event_id,
            'event_name': event.get('event_name'),
            'posts_found': result['posts_found'],
            'verifications_added': result['verifications_added'],
            'photos_analyzed': result['photos_analyzed'],
            'hail_detected': result.get('hail_detected', 0),
            'errors': result['errors'] if result['errors'] else None
        })

    except ImportError as e:
        return jsonify({
            'error': 'Storm verification pipeline not available',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/batch-verify', methods=['POST'])
@login_required
def batch_verify_storms():
    """
    Process multiple recent storms to find verifications.

    Body (optional):
        days_back: How many days of storms to process (default: 3)
        max_storms: Maximum storms to process (default: 10)
        auto_analyze: Whether to run AI on photos (default: true)

    Returns:
        storms_processed: Number of storms checked
        total_posts_found: Total matching posts
        total_verifications_added: Total new verifications
    """
    data = request.get_json() or {}

    try:
        from src.social.storm_verification_pipeline import StormVerificationPipeline

        pipeline = StormVerificationPipeline()

        result = pipeline.process_active_storms(
            days_back=data.get('days_back', 3),
            max_storms=data.get('max_storms', 10),
            auto_analyze=data.get('auto_analyze', True)
        )

        return jsonify({
            'storms_processed': result['storms_processed'],
            'total_posts_found': result['total_posts_found'],
            'total_verifications': result['total_verifications'],
            'storm_results': result['storm_results']
        })

    except ImportError as e:
        return jsonify({
            'error': 'Storm verification pipeline not available',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/populate-all-photos', methods=['POST'])
@login_required
def populate_all_photos():
    """
    Populate photos for ALL recent storms that are missing them.

    This is a batch operation that finds photos for storms that have
    fewer than 5 photos. Use this to pre-populate the database.

    Body (optional):
        days_back: How many days of storms to process (default: 90)
        min_photos: Minimum photos a storm should have (default: 5)
        skip_ai: Skip AI analysis for speed (default: true)

    Returns:
        storms_checked: Total storms checked
        storms_populated: Number of storms that got new photos
        total_photos_added: Total new photos found
    """
    import logging
    logger = logging.getLogger('HailTrackerWeb')

    data = request.get_json() or {}

    days_back = data.get('days_back', 90)
    min_photos = data.get('min_photos', 5)
    skip_ai = data.get('skip_ai', True)

    logger.info(f"[POPULATE] Starting batch photo population for {days_back} days")

    try:
        from src.social.storm_verification_pipeline import StormVerificationPipeline

        pipeline = StormVerificationPipeline()

        # Use the improved batch processor
        result = pipeline.process_active_storms(
            days_back=days_back,
            max_storms=100,  # Process up to 100 storms
            auto_analyze=not skip_ai
        )

        logger.info(f"[POPULATE] Completed: {result['storms_processed']} storms, {result['total_verifications']} photos")

        return jsonify({
            'success': True,
            'storms_checked': len(result['storm_results']),
            'storms_populated': result['storms_processed'],
            'total_photos_added': result['total_verifications'],
            'storms_skipped': sum(1 for r in result['storm_results'] if r.get('skipped')),
            'details': result['storm_results']
        })

    except ImportError as e:
        return jsonify({
            'error': 'Storm verification pipeline not available',
            'details': str(e)
        }), 503
    except Exception as e:
        import traceback
        logger.error(f"[POPULATE] Error: {e}")
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@hail_events_api_bp.route('/verification-stats', methods=['GET'])
@login_required
def get_verification_stats():
    """
    Get overall verification statistics.

    Query params:
        storm_id: Optional - filter stats to specific storm

    Returns:
        total_verifications: Total number of verifications
        with_photos: Count with photos
        with_videos: Count with videos
        ai_analyzed: Count analyzed by AI
        hail_detected: Count with hail detected
        by_source: Breakdown by source (reddit, twitter, etc.)
        by_size: Breakdown by hail size category
        avg_confidence: Average AI confidence score
    """
    try:
        from src.social.storm_verification_pipeline import StormVerificationPipeline

        pipeline = StormVerificationPipeline()

        storm_id = request.args.get('storm_id', type=int)
        stats = pipeline.get_verification_stats(storm_id)

        return jsonify(stats)

    except ImportError as e:
        return jsonify({
            'error': 'Storm verification pipeline not available',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/<int:event_id>/verification-quality', methods=['GET'])
@login_required
def get_verification_quality(event_id):
    """
    Get verification quality score for a storm event.

    Higher scores indicate more reliable verification.

    Returns:
        score: 0-100 quality score
        grade: Letter grade (A, B, C, D, F)
        breakdown: Details of how score was calculated
            - verification_count: Number of verifications
            - photo_count: Number with photos
            - video_count: Number with videos
            - ai_confirmed: Number with AI hail detection
            - high_engagement: Number with 50+ likes
            - multiple_sources: Number of unique sources
    """
    try:
        from src.social.storm_verification_pipeline import StormVerificationPipeline

        pipeline = StormVerificationPipeline()

        quality = pipeline.get_verification_quality_score(event_id)

        return jsonify({
            'event_id': event_id,
            **quality
        })

    except ImportError as e:
        return jsonify({
            'error': 'Storm verification pipeline not available',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# STORM PHOTOS - Auto-fetch from social media
# =============================================================================

@hail_events_api_bp.route('/<int:event_id>/photos', methods=['GET'])
@login_required
def get_storm_photos(event_id):
    """
    Get all verified hail photos for a storm.

    Returns photos that have been fetched and AI-verified.
    """
    import logging
    logger = logging.getLogger('HailTrackerWeb')

    logger.info(f"[PHOTOS] GET /api/hail-events/{event_id}/photos called")

    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
        db = Database(db_path)

        photos = db.execute("""
            SELECT id, hail_event_id, source, post_url, photo_url, thumbnail_url,
                   title, author, posted_at, location_mentioned,
                   ai_analyzed, ai_detected_hail, ai_estimated_size,
                   ai_size_category, ai_confidence, ai_severity,
                   likes, comments, created_at
            FROM storm_verifications
            WHERE hail_event_id = ?
            AND photo_url IS NOT NULL
            ORDER BY ai_detected_hail DESC, ai_confidence DESC, likes DESC
        """, (event_id,))

        logger.info(f"[PHOTOS] Event {event_id}: returning {len(photos)} photos")

        return jsonify({
            'event_id': event_id,
            'photos': photos,
            'count': len(photos)
        })
    except Exception as e:
        logger.error(f"[PHOTOS] Error for event {event_id}: {e}")
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/<int:event_id>/search-photos', methods=['POST'])
@login_required
def search_storm_photos(event_id):
    """
    Search social media for hail photos and auto-analyze with AI.

    This is the main endpoint for auto-fetching photos when clicking a storm.
    It searches Reddit, downloads photos, runs AI analysis, and stores results.

    Returns newly found and analyzed photos.
    """
    import logging
    logger = logging.getLogger('HailTrackerWeb')

    logger.info(f"[SEARCH-PHOTOS] POST /api/hail-events/{event_id}/search-photos called")

    data = request.get_json() or {}

    # Get storm details
    manager = get_manager()
    event = manager.get_storm_event(event_id)

    logger.info(f"[SEARCH-PHOTOS] Event {event_id}: {event.get('event_name') if event else 'NOT FOUND'}")

    if not event:
        return jsonify({'error': 'Storm not found'}), 404

    try:
        from src.social.storm_verification_pipeline import StormVerificationPipeline

        pipeline = StormVerificationPipeline()

        # Extract location - use city or parse from event_name
        location = event.get('city') or ''
        if not location and event.get('event_name'):
            # Parse "Dallas, TX - Jun 12, 2023" format
            name_parts = event['event_name'].split(' - ')
            if name_parts:
                location = name_parts[0]

        state = event.get('state')
        event_date = event.get('event_date')
        if isinstance(event_date, datetime):
            event_date = event_date.strftime('%Y-%m-%d')

        # Search with wider date range for old storms
        search_radius_days = data.get('search_radius_days', 7)

        logger.info(f"[SEARCH-PHOTOS] Searching: location='{location}', date='{event_date}', state='{state}'")

        # Run the pipeline
        result = pipeline.find_verifications_for_storm(
            storm_id=event_id,
            storm_location=location,
            storm_date=event_date,
            storm_state=state,
            search_radius_days=search_radius_days,
            max_posts=data.get('max_posts', 30),
            auto_analyze=True  # Always analyze photos
        )

        logger.info(f"[SEARCH-PHOTOS] Pipeline result: posts_found={result.get('posts_found')}, verifications={result.get('verifications_added')}")

        # Get the photos that were found
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
        db = Database(db_path)

        photos = db.execute("""
            SELECT id, hail_event_id, source, post_url, photo_url, thumbnail_url,
                   title, author, posted_at, location_mentioned,
                   ai_analyzed, ai_detected_hail, ai_estimated_size,
                   ai_size_category, ai_confidence, ai_severity,
                   likes, comments, created_at
            FROM storm_verifications
            WHERE hail_event_id = ?
            AND photo_url IS NOT NULL
            ORDER BY ai_detected_hail DESC, ai_confidence DESC, likes DESC
        """, (event_id,))

        return jsonify({
            'event_id': event_id,
            'search_performed': True,
            'posts_found': result['posts_found'],
            'photos_analyzed': result['photos_analyzed'],
            'hail_detected': result.get('hail_detected', 0),
            'photos': photos,
            'count': len(photos),
            'errors': result['errors'] if result['errors'] else None
        })

    except ImportError as e:
        return jsonify({
            'error': 'Photo search not available',
            'details': str(e)
        }), 503
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@hail_events_api_bp.route('/verified-storms', methods=['GET'])
@login_required
def get_verified_storms():
    """
    Get all storms that have social media verifications.

    Query params:
        min_score: Minimum quality score (default: 0)
        min_grade: Minimum letter grade (A, B, C, D, F)
        days: Days to look back (default: 90)
        limit: Max results (default: 50)

    Returns:
        storms: List of verified storms with quality scores
        count: Number of results
    """
    try:
        from src.social.storm_verification_pipeline import StormVerificationPipeline

        min_score = request.args.get('min_score', 0, type=int)
        min_grade = request.args.get('min_grade', 'F')
        days = request.args.get('days', 90, type=int)
        limit = request.args.get('limit', 50, type=int)

        grade_order = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}
        min_grade_value = grade_order.get(min_grade.upper(), 1)

        pipeline = StormVerificationPipeline()

        # Get storms with verifications
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
        db = Database(db_path)

        cutoff = date.today() - timedelta(days=days)

        # Get storms that have verifications
        storms_with_verifications = db.execute("""
            SELECT DISTINCT h.id, h.event_name, h.event_date, h.max_hail_size,
                   h.center_lat, h.center_lon, h.city, h.state,
                   COUNT(sv.id) as verification_count
            FROM hail_events h
            INNER JOIN storm_verifications sv ON h.id = sv.hail_event_id
            WHERE h.event_date >= ?
            GROUP BY h.id
            ORDER BY h.event_date DESC
            LIMIT ?
        """, (cutoff.isoformat(), limit * 2))

        # Calculate quality scores
        verified_storms = []
        for storm in storms_with_verifications:
            quality = pipeline.get_verification_quality_score(storm['id'])

            if quality['score'] >= min_score and grade_order.get(quality['grade'], 1) >= min_grade_value:
                verified_storms.append({
                    'id': storm['id'],
                    'event_name': storm['event_name'],
                    'event_date': storm['event_date'],
                    'max_hail_size': storm['max_hail_size'],
                    'center_lat': storm['center_lat'],
                    'center_lon': storm['center_lon'],
                    'city': storm.get('city'),
                    'state': storm.get('state'),
                    'verification_count': storm['verification_count'],
                    'quality_score': quality['score'],
                    'quality_grade': quality['grade']
                })

        # Sort by quality score
        verified_storms.sort(key=lambda x: x['quality_score'], reverse=True)

        return jsonify({
            'storms': verified_storms[:limit],
            'count': len(verified_storms[:limit]),
            'filters': {
                'min_score': min_score,
                'min_grade': min_grade,
                'days': days
            }
        })

    except ImportError as e:
        return jsonify({
            'error': 'Storm verification pipeline not available',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# DATE-BASED HAIL SWATH OVERLAY FOR FLEET MAP
# =============================================================================

@hail_events_api_bp.route('/by-date', methods=['GET'])
@login_required
def get_hail_events_by_date():
    """
    Get hail events for a specific date or date range with swath polygons.

    Query params:
        date: Single date (YYYY-MM-DD) - gets events for this exact date
        start_date: Start of range (YYYY-MM-DD)
        end_date: End of range (YYYY-MM-DD)
        state: Filter by state (optional)
        min_size: Minimum hail size in inches (optional)

    Returns events with swath polygons for map display.
    """
    import json as json_lib
    import sys

    # DEBUG: Log that the endpoint was reached
    print("\n" + "="*60, flush=True)
    print(">>> /api/hail-events/by-date ENDPOINT REACHED <<<", flush=True)
    print(f">>> Request args: {dict(request.args)}", flush=True)
    print("="*60 + "\n", flush=True)
    sys.stdout.flush()

    try:
        date_param = request.args.get('date')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        state = request.args.get('state')
        min_size = request.args.get('min_size', type=float)

        # Get database connection
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
        db = Database(db_path)

        print(f"[by-date] date_param={date_param}, db_path={db_path}", flush=True)

        # Build query - Note: hail_events table doesn't have a city column
        query = '''
            SELECT
                id,
                event_date,
                event_name,
                max_hail_size,
                swath_polygon,
                swath_area_sqmi,
                center_lat,
                center_lon,
                estimated_vehicles,
                data_source,
                confidence_score
            FROM hail_events
            WHERE 1=1
        '''
        params = []

        if date_param:
            # Single date - get events from that day
            query += " AND DATE(event_date) = DATE(?)"
            params.append(date_param)
        elif start_date and end_date:
            query += " AND DATE(event_date) BETWEEN DATE(?) AND DATE(?)"
            params.extend([start_date, end_date])
        elif start_date:
            query += " AND DATE(event_date) >= DATE(?)"
            params.append(start_date)
        elif end_date:
            query += " AND DATE(event_date) <= DATE(?)"
            params.append(end_date)
        else:
            # Default to last 30 days
            query += " AND event_date >= date('now', '-30 days')"

        if state:
            query += " AND (event_name LIKE ? OR event_name LIKE ?)"
            params.extend([f'%{state}%', f'%, {state} %'])

        if min_size:
            query += " AND max_hail_size >= ?"
            params.append(min_size)

        query += " ORDER BY event_date DESC, max_hail_size DESC LIMIT 200"

        print(f"[by-date] Executing query with params: {params}", flush=True)
        events = db.execute(query, params)
        print(f"[by-date] Query returned {len(events)} events", flush=True)

        results = []
        for event in events:
            # Extract city from event_name if possible (format: "City, ST - Date [Source:ID]")
            event_name = event.get('event_name', '')
            city = None
            if event_name and ' - ' in event_name:
                city_part = event_name.split(' - ')[0]
                if ', ' in city_part:
                    city = city_part.split(', ')[0]
                else:
                    city = city_part

            result = {
                'id': event['id'],
                'event_date': event['event_date'],
                'event_name': event['event_name'],
                'city': city,
                'max_hail_size': event['max_hail_size'],
                'center_lat': event['center_lat'],
                'center_lon': event['center_lon'],
                'area_sq_miles': event.get('swath_area_sqmi'),
                'estimated_vehicles': event.get('estimated_vehicles'),
                'data_source': event.get('data_source'),
                'confidence': event.get('confidence_score'),
            }

            # Parse swath polygon for map display
            swath = event.get('swath_polygon')
            if swath:
                try:
                    # Check if it's already GeoJSON
                    if swath.startswith('{'):
                        result['swath_geojson'] = json_lib.loads(swath)
                    else:
                        # Store raw for potential WKT parsing on frontend
                        result['swath_raw'] = swath
                except Exception as e:
                    print(f"[by-date] Error parsing swath for event {event['id']}: {e}", flush=True)

            results.append(result)

        print(f"[by-date] Returning {len(results)} events", flush=True)
        return jsonify({
            'count': len(results),
            'events': results,
            'query': {
                'date': date_param,
                'start_date': start_date,
                'end_date': end_date,
                'state': state,
                'min_size': min_size,
            }
        })

    except Exception as e:
        import traceback
        print(f"[by-date] ERROR: {e}", flush=True)
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@hail_events_api_bp.route('/dates', methods=['GET'])
@login_required
def get_hail_event_dates():
    """
    Get list of dates that have hail events.
    Useful for date picker to highlight dates with storms.

    Query params:
        year: Filter by year (default: current year)
        month: Filter by month (requires year, 1-12)
        state: Filter by state
        limit: Max dates to return (default: 365)

    Returns list of dates with event counts and max hail size.
    """
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', type=int)
    state = request.args.get('state')
    limit = request.args.get('limit', 365, type=int)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    db = Database(db_path)

    # Build query
    query = '''
        SELECT
            DATE(event_date) as date,
            COUNT(*) as event_count,
            MAX(max_hail_size) as max_size,
            SUM(estimated_vehicles) as total_vehicles,
            COUNT(DISTINCT CASE WHEN swath_polygon IS NOT NULL THEN id END) as events_with_swath
        FROM hail_events
        WHERE strftime('%Y', event_date) = ?
    '''
    params = [str(year)]

    if month:
        query += " AND strftime('%m', event_date) = ?"
        params.append(str(month).zfill(2))

    if state:
        query += " AND (event_name LIKE ? OR event_name LIKE ?)"
        params.extend([f'%{state}%', f'%, {state} %'])

    query += " GROUP BY DATE(event_date) ORDER BY date DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params)

    dates = []
    for row in rows:
        # Determine severity based on max hail size
        max_size = row['max_size'] or 0
        if max_size >= 2.0:
            severity = 'SEVERE'
        elif max_size >= 1.0:
            severity = 'MODERATE'
        else:
            severity = 'MINOR'

        dates.append({
            'date': row['date'],
            'event_count': row['event_count'],
            'max_size': max_size,
            'severity': severity,
            'total_vehicles': row['total_vehicles'] or 0,
            'has_swath': row['events_with_swath'] > 0,
        })

    return jsonify({
        'count': len(dates),
        'year': year,
        'month': month,
        'dates': dates
    })


@hail_events_api_bp.route('/<int:event_id>/affected-businesses', methods=['GET'])
@login_required
def get_businesses_in_swath(event_id):
    """
    Get all businesses that fall within a specific hail event's swath polygon.

    Returns businesses sorted by estimated vehicles (highest value first).
    """
    import json as json_lib
    import sqlite3

    # Get database connection
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    business_db_path = os.path.join(project_root, 'data', 'business_prospects.db')

    db = Database(db_path)

    # Get the hail event with swath
    event = db.execute('''
        SELECT id, event_name, event_date, city, max_hail_size,
               swath_polygon, center_lat, center_lon, swath_area_sqmi
        FROM hail_events WHERE id = ?
    ''', (event_id,))

    if not event:
        return jsonify({'error': 'Event not found'}), 404

    event = event[0]

    swath_data = event.get('swath_polygon')
    center_lat = event.get('center_lat')
    center_lon = event.get('center_lon')

    # Parse swath polygon or use center point with radius
    swath_geom = None
    bounds = None

    if swath_data:
        try:
            if swath_data.startswith('{'):
                swath_json = json_lib.loads(swath_data)
                # Get bounds from GeoJSON coordinates
                if swath_json.get('type') == 'Polygon':
                    coords = swath_json.get('coordinates', [[]])[0]
                    if coords:
                        lons = [c[0] for c in coords]
                        lats = [c[1] for c in coords]
                        bounds = {
                            'min_lon': min(lons),
                            'max_lon': max(lons),
                            'min_lat': min(lats),
                            'max_lat': max(lats),
                        }
                        swath_geom = swath_json
        except:
            pass

    # Fallback to center point with 10-mile radius
    if not bounds and center_lat and center_lon:
        radius_deg = 10 / 69.0  # ~10 miles
        bounds = {
            'min_lat': center_lat - radius_deg,
            'max_lat': center_lat + radius_deg,
            'min_lon': center_lon - radius_deg,
            'max_lon': center_lon + radius_deg,
        }

    if not bounds:
        return jsonify({
            'event': {
                'id': event['id'],
                'date': event['event_date'],
                'name': event['event_name'],
                'max_hail_size': event['max_hail_size'],
            },
            'affected_count': 0,
            'businesses': [],
            'error': 'No swath polygon or center coordinates available'
        })

    # Query businesses within bounding box
    try:
        business_conn = sqlite3.connect(business_db_path)
        business_conn.row_factory = sqlite3.Row
        bus_cursor = business_conn.cursor()

        bus_cursor.execute('''
            SELECT * FROM businesses
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            AND latitude IS NOT NULL
            AND longitude IS NOT NULL
        ''', (bounds['min_lat'], bounds['max_lat'], bounds['min_lon'], bounds['max_lon']))

        businesses = bus_cursor.fetchall()
        business_conn.close()
    except Exception as e:
        return jsonify({
            'event': {
                'id': event['id'],
                'date': event['event_date'],
                'name': event['event_name'],
            },
            'affected_count': 0,
            'businesses': [],
            'error': f'Business database not available: {str(e)}'
        })

    # Filter to businesses inside the polygon (if we have one)
    affected = []
    for biz in businesses:
        biz_lat = biz['latitude']
        biz_lon = biz['longitude']

        # If we have a polygon, do point-in-polygon check
        in_swath = True
        if swath_geom and swath_geom.get('type') == 'Polygon':
            in_swath = _point_in_polygon(biz_lat, biz_lon, swath_geom)

        if in_swath:
            affected.append({
                'id': biz['id'],
                'name': biz['name'],
                'address': biz['address'],
                'city': biz['city'],
                'state': biz['state'],
                'zip': biz['zip'],
                'phone': biz['phone'],
                'website': biz['website'],
                'category': biz['category'],
                'subcategory': biz.get('subcategory'),
                'estimated_vehicles': biz['estimated_vehicles'] or 0,
                'tier': biz['tier'],
                'latitude': biz_lat,
                'longitude': biz_lon,
                'source': biz['source'],
                'bbb_rating': biz.get('bbb_rating'),
            })

    # Sort by estimated vehicles (highest first)
    affected.sort(key=lambda x: x.get('estimated_vehicles', 0), reverse=True)

    total_vehicles = sum(b.get('estimated_vehicles', 0) for b in affected)

    return jsonify({
        'event': {
            'id': event['id'],
            'date': event['event_date'],
            'name': event['event_name'],
            'city': event.get('city'),
            'max_hail_size': event['max_hail_size'],
            'area_sq_miles': event.get('swath_area_sqmi'),
            'center_lat': center_lat,
            'center_lon': center_lon,
        },
        'affected_count': len(affected),
        'total_estimated_vehicles': total_vehicles,
        'estimated_value': total_vehicles * 500,  # Approx revenue per vehicle
        'businesses': affected,
    })


@hail_events_api_bp.route('/affected-businesses-by-date', methods=['GET'])
@login_required
def get_businesses_affected_by_date():
    """
    Get all businesses affected by hail events on a specific date.
    Combines all swaths from that date, or only specified events if event_ids provided.

    Query params:
        date: Date to check (YYYY-MM-DD) - REQUIRED
        min_size: Minimum hail size to include (optional)
        event_ids: Comma-separated list of event IDs to filter (optional, for viewport-based filtering)

    Returns businesses sorted by estimated vehicles.
    """
    import json as json_lib
    import sqlite3

    date_param = request.args.get('date')
    if not date_param:
        return jsonify({'error': 'date parameter required'}), 400

    min_size = request.args.get('min_size', type=float)
    event_ids_param = request.args.get('event_ids')  # Comma-separated event IDs for viewport filtering

    # Parse event IDs if provided
    viewport_filtered = False
    event_ids = None
    if event_ids_param:
        try:
            event_ids = [int(x.strip()) for x in event_ids_param.split(',') if x.strip()]
            viewport_filtered = True
            print(f"[affected-businesses] Viewport filtering enabled: {len(event_ids)} events", flush=True)
        except ValueError:
            pass

    # Get database connection
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    business_db_path = os.path.join(project_root, 'data', 'business_prospects.db')

    db = Database(db_path)

    # Build query based on whether event_ids filter is provided
    if event_ids and len(event_ids) > 0:
        # Viewport-based filtering: only get specified events
        placeholders = ','.join('?' * len(event_ids))
        query = f'''
            SELECT id, event_name, event_date, max_hail_size,
                   swath_polygon, center_lat, center_lon, swath_area_sqmi
            FROM hail_events
            WHERE id IN ({placeholders})
        '''
        params = event_ids
        if min_size:
            query += " AND max_hail_size >= ?"
            params.append(min_size)
    else:
        # No viewport filter: get all events for the date
        query = '''
            SELECT id, event_name, event_date, max_hail_size,
                   swath_polygon, center_lat, center_lon, swath_area_sqmi
            FROM hail_events
            WHERE DATE(event_date) = DATE(?)
        '''
        params = [date_param]
        if min_size:
            query += " AND max_hail_size >= ?"
            params.append(min_size)

    events = db.execute(query, params)

    if not events:
        return jsonify({
            'date': date_param,
            'event_count': 0,
            'events': [],
            'affected_count': 0,
            'businesses': []
        })

    # Collect all swath bounds and geometries
    all_bounds = {'min_lat': 90, 'max_lat': -90, 'min_lon': 180, 'max_lon': -180}
    swath_geoms = []
    event_info = []

    for event in events:
        swath_data = event.get('swath_polygon')
        center_lat = event.get('center_lat')
        center_lon = event.get('center_lon')

        # Parse city from event_name (format: "City, ST - Date [Source:ID]")
        event_name = event.get('event_name', '')
        city = None
        if event_name and ' - ' in event_name:
            location_part = event_name.split(' - ')[0]
            if ', ' in location_part:
                city = location_part.split(', ')[0]

        event_info.append({
            'id': event['id'],
            'name': event['event_name'],
            'city': city,
            'max_hail_size': event['max_hail_size'],
            'area_sq_miles': event.get('swath_area_sqmi'),
            'center_lat': center_lat,
            'center_lon': center_lon,
        })

        # Parse swath or use center
        if swath_data and swath_data.startswith('{'):
            try:
                swath_json = json_lib.loads(swath_data)
                if swath_json.get('type') == 'Polygon':
                    coords = swath_json.get('coordinates', [[]])[0]
                    if coords:
                        lons = [c[0] for c in coords]
                        lats = [c[1] for c in coords]
                        all_bounds['min_lon'] = min(all_bounds['min_lon'], min(lons))
                        all_bounds['max_lon'] = max(all_bounds['max_lon'], max(lons))
                        all_bounds['min_lat'] = min(all_bounds['min_lat'], min(lats))
                        all_bounds['max_lat'] = max(all_bounds['max_lat'], max(lats))
                        swath_geoms.append(swath_json)
            except:
                pass
        elif center_lat and center_lon:
            # Use center with 10-mile radius fallback
            radius_deg = 10 / 69.0
            all_bounds['min_lat'] = min(all_bounds['min_lat'], center_lat - radius_deg)
            all_bounds['max_lat'] = max(all_bounds['max_lat'], center_lat + radius_deg)
            all_bounds['min_lon'] = min(all_bounds['min_lon'], center_lon - radius_deg)
            all_bounds['max_lon'] = max(all_bounds['max_lon'], center_lon + radius_deg)

    # Check if we have valid bounds
    if all_bounds['min_lat'] >= all_bounds['max_lat']:
        return jsonify({
            'date': date_param,
            'event_count': len(events),
            'events': event_info,
            'affected_count': 0,
            'businesses': [],
            'error': 'No valid swath polygons or center coordinates found'
        })

    # Query businesses within combined bounding box
    try:
        business_conn = sqlite3.connect(business_db_path)
        business_conn.row_factory = sqlite3.Row
        bus_cursor = business_conn.cursor()

        bus_cursor.execute('''
            SELECT * FROM businesses
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            AND latitude IS NOT NULL
        ''', (all_bounds['min_lat'], all_bounds['max_lat'],
              all_bounds['min_lon'], all_bounds['max_lon']))

        businesses = bus_cursor.fetchall()
        business_conn.close()
    except Exception as e:
        return jsonify({
            'date': date_param,
            'event_count': len(events),
            'events': event_info,
            'affected_count': 0,
            'businesses': [],
            'error': f'Business database not available: {str(e)}'
        })

    # Filter to businesses inside any swath polygon
    affected = []
    for biz in businesses:
        biz_lat = biz['latitude']
        biz_lon = biz['longitude']

        # Check if in any swath polygon
        in_any_swath = False

        if swath_geoms:
            for swath in swath_geoms:
                if _point_in_polygon(biz_lat, biz_lon, swath):
                    in_any_swath = True
                    break
        else:
            # No polygons - include all in bounds
            in_any_swath = True

        if in_any_swath:
            affected.append({
                'id': biz['id'],
                'name': biz['name'],
                'address': biz['address'],
                'city': biz['city'],
                'state': biz['state'],
                'zip': biz['zip'],
                'phone': biz['phone'],
                'website': biz['website'],
                'category': biz['category'],
                'subcategory': biz.get('subcategory'),
                'estimated_vehicles': biz['estimated_vehicles'] or 0,
                'tier': biz['tier'],
                'latitude': biz_lat,
                'longitude': biz_lon,
                'source': biz['source'],
                'bbb_rating': biz.get('bbb_rating'),
            })

    # Sort by estimated vehicles
    affected.sort(key=lambda x: x.get('estimated_vehicles', 0), reverse=True)

    total_vehicles = sum(b.get('estimated_vehicles', 0) for b in affected)

    print(f"[affected-businesses] Returning {len(affected)} businesses, viewport_filtered={viewport_filtered}", flush=True)

    return jsonify({
        'date': date_param,
        'event_count': len(events),
        'events': event_info,
        'affected_count': len(affected),
        'total_estimated_vehicles': total_vehicles,
        'estimated_value': total_vehicles * 500,
        'businesses': affected,
        'viewport_filtered': viewport_filtered,
    })


# =============================================================================
# RECENT SIGNIFICANT STORMS
# =============================================================================

@hail_events_api_bp.route('/recent-significant')
@login_required
def get_recent_significant_storms():
    """
    Get recent significant hail events for quick testing.
    Returns storms with 1"+ hail from the last 90 days.

    Query params:
        days: Number of days to look back (default: 90)
        min_size: Minimum hail size in inches (default: 1.0)
        limit: Maximum storms to return (default: 20)
    """
    print(f"[recent-significant] Endpoint reached", flush=True)
    days = request.args.get('days', 90, type=int)
    min_size = request.args.get('min_size', 1.0, type=float)
    limit = min(request.args.get('limit', 20, type=int), 50)
    print(f"[recent-significant] days={days}, min_size={min_size}, limit={limit}", flush=True)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Use hailtracker_crm.db which has the hail_events table
    import sqlite3
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')

    try:
        print(f"[recent-significant] Connecting to db: {db_path}", flush=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        print(f"[recent-significant] Connected to database", flush=True)

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        print(f"[recent-significant] start_date={start_date}", flush=True)

        # Note: hail_events table doesn't have city/state columns
        # We'll extract from event_name which has format "City, ST - Date [Source:ID]"
        cursor.execute('''
            SELECT
                DATE(event_date) as storm_date,
                COUNT(*) as event_count,
                MAX(max_hail_size) as max_size,
                GROUP_CONCAT(DISTINCT event_name) as event_names,
                SUM(COALESCE(swath_area_sqmi, 0)) as total_area
            FROM hail_events
            WHERE event_date >= ?
            AND max_hail_size >= ?
            GROUP BY DATE(event_date)
            ORDER BY max_size DESC, event_count DESC
            LIMIT ?
        ''', (start_date, min_size, limit))

        rows = cursor.fetchall()
        conn.close()

        storms = []
        for row in rows:
            # Parse cities and states from event_names
            event_names = (row['event_names'] or '').split(',')
            cities_set = set()
            states_set = set()
            for name in event_names[:10]:  # Limit to first 10 to avoid processing too many
                name = name.strip()
                if ' - ' in name:
                    location_part = name.split(' - ')[0]
                    if ', ' in location_part:
                        parts = location_part.split(', ')
                        cities_set.add(parts[0].strip())
                        if len(parts) > 1:
                            states_set.add(parts[1].strip())

            cities_list = list(cities_set)[:5]
            states_list = list(states_set)
            max_hail = row['max_size'] or 0

            # Determine severity
            if max_hail >= 2.0:
                severity = 'SEVERE'
            elif max_hail >= 1.5:
                severity = 'SIGNIFICANT'
            else:
                severity = 'MODERATE'

            # Build display name from cities and states
            display_name = f"{cities_list[0] if cities_list else 'Unknown'}, {states_list[0] if states_list else 'US'}" if cities_list else row['storm_date']

            storms.append({
                'date': row['storm_date'],
                'total_events': row['event_count'],  # Frontend expects total_events
                'max_hail_size': max_hail,  # Frontend expects max_hail_size
                'states_affected': states_list,  # Frontend expects states_affected as list
                'major_cities': cities_list,  # Frontend expects major_cities as list
                'total_area_sq_miles': round(row['total_area'] or 0, 1),
                'display_name': display_name,  # Frontend expects display_name
                'severity': severity,
                # Keep old field names for backwards compatibility
                'event_count': row['event_count'],
                'max_size': max_hail,
                'states': ','.join(states_list),
                'cities': cities_list,
            })

        return jsonify({
            'count': len(storms),
            'days_back': days,  # Frontend expects days_back
            'min_size': min_size,
            'storms': storms
        })

    except Exception as e:
        import traceback
        print(f"[recent-significant] ERROR: {str(e)}", flush=True)
        print(f"[recent-significant] Traceback: {traceback.format_exc()}", flush=True)
        return jsonify({'error': str(e)}), 500


@hail_events_api_bp.route('/storm-summary/<storm_date>')
@login_required
def get_storm_summary(storm_date):
    """
    Get detailed summary for a specific storm date.
    Includes affected area, cities hit, and business count in swaths.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # Use hailtracker_crm.db which has the hail_events table
    import sqlite3
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get events for this date - note: no city/state columns
        cursor.execute('''
            SELECT
                id, event_date, event_name, max_hail_size,
                center_lat, center_lon, swath_area_sqmi,
                swath_polygon
            FROM hail_events
            WHERE DATE(event_date) = DATE(?)
            ORDER BY max_hail_size DESC
        ''', (storm_date,))

        raw_events = cursor.fetchall()
        conn.close()

        # Process events to extract city/state from event_name
        events = []
        for row in raw_events:
            event = dict(row)
            # Parse city/state from event_name (format: "City, ST - Date [Source:ID]")
            event_name = event.get('event_name', '')
            city = None
            state = None
            if event_name and ' - ' in event_name:
                location_part = event_name.split(' - ')[0]
                if ', ' in location_part:
                    parts = location_part.split(', ')
                    city = parts[0].strip()
                    if len(parts) > 1:
                        state = parts[1].strip()
            event['city'] = city
            event['state'] = state
            event['estimated_area_sq_miles'] = event.get('swath_area_sqmi')
            events.append(event)

        if not events:
            return jsonify({'error': 'No events found for this date'}), 404

        # Calculate totals
        total_area = sum(e.get('estimated_area_sq_miles') or 0 for e in events)
        cities = list(set(e['city'] for e in events if e.get('city')))
        states = list(set(e['state'] for e in events if e.get('state')))
        max_size = max(e.get('max_hail_size') or 0 for e in events)

        # Determine severity
        if max_size >= 2.0:
            severity = 'SEVERE'
        elif max_size >= 1.5:
            severity = 'SIGNIFICANT'
        else:
            severity = 'MODERATE'

        # Count businesses in affected area (rough estimate using bounding box)
        business_count = 0
        try:
            lats = [e['center_lat'] for e in events if e.get('center_lat')]
            lons = [e['center_lon'] for e in events if e.get('center_lon')]

            if lats and lons:
                min_lat, max_lat = min(lats) - 0.2, max(lats) + 0.2
                min_lon, max_lon = min(lons) - 0.2, max(lons) + 0.2

                bus_db_path = os.path.join(project_root, 'data', 'business_prospects.db')
                if os.path.exists(bus_db_path):
                    bus_conn = sqlite3.connect(bus_db_path)
                    bus_cursor = bus_conn.cursor()
                    bus_cursor.execute('''
                        SELECT COUNT(*) FROM businesses
                        WHERE latitude BETWEEN ? AND ?
                        AND longitude BETWEEN ? AND ?
                    ''', (min_lat, max_lat, min_lon, max_lon))
                    business_count = bus_cursor.fetchone()[0]
                    bus_conn.close()
        except Exception as e:
            pass  # Ignore business count errors

        return jsonify({
            'date': storm_date,
            'event_count': len(events),
            'max_hail_size': max_size,
            'total_area_sq_miles': round(total_area, 1),
            'cities': cities[:10],
            'states': states,
            'estimated_businesses_affected': business_count,
            'severity': severity,
            'events': [{
                'id': e['id'],
                'city': e['city'],
                'state': e['state'],
                'max_hail_size': e['max_hail_size'],
                'area_sq_miles': e.get('estimated_area_sq_miles'),
            } for e in events[:20]]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
