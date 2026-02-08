"""
Storm Cell Tracking API Routes
==============================
RESTful API for StormCellTracker functionality.

Endpoints:
- Cell tracking: process scans, get tracks, forecast positions
- Swath generation: create track swaths, all swaths
- Statistics: tracking statistics
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from src.core.auth.decorators import login_required

storm_tracking_api_bp = Blueprint('storm_tracking_api', __name__, url_prefix='/api/storm-cells')

# Global tracker instance (singleton for state persistence)
_tracker_instance = None


def get_tracker():
    """Get or create StormCellTracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        from src.radar.storm_cell_tracker import StormCellTracker
        _tracker_instance = StormCellTracker(simulation_mode=True)
    return _tracker_instance


def reset_tracker():
    """Reset tracker to clear state"""
    global _tracker_instance
    from src.radar.storm_cell_tracker import StormCellTracker
    _tracker_instance = StormCellTracker(simulation_mode=True)
    return _tracker_instance


# =============================================================================
# CELL TRACKING
# =============================================================================

@storm_tracking_api_bp.route('', methods=['GET'])
@login_required
def get_cell_tracks():
    """Get all tracked cell tracks"""
    tracker = get_tracker()
    min_duration = request.args.get('min_duration', 10, type=float)

    tracks = tracker.get_cell_tracks(min_duration_minutes=min_duration)

    # Convert to serializable format
    result = []
    for cell_id, track in tracks.items():
        result.append({
            'cell_id': track.cell_id,
            'start_time': track.start_time.isoformat(),
            'end_time': track.end_time.isoformat(),
            'duration_minutes': track.duration_minutes,
            'max_mesh_mm': track.max_mesh_mm,
            'max_mesh_inches': round(track.max_mesh_mm / 25.4, 2),
            'max_reflectivity': track.max_reflectivity,
            'avg_velocity_kmh': track.avg_velocity_kmh,
            'track_length_km': track.track_length_km,
            'lifecycle_stages': track.lifecycle_stages,
            'position_count': len(track.positions)
        })

    return jsonify({
        'tracks': result,
        'count': len(result)
    })


@storm_tracking_api_bp.route('/<int:cell_id>', methods=['GET'])
@login_required
def get_cell_track(cell_id):
    """Get specific cell track with full position history"""
    tracker = get_tracker()

    tracks = tracker.get_cell_tracks(min_duration_minutes=0)

    if cell_id not in tracks:
        return jsonify({'error': 'Cell not found'}), 404

    track = tracks[cell_id]

    # Get all positions for this cell
    positions = []
    for pos in track.positions:
        positions.append({
            'timestamp': pos.timestamp,
            'lat': pos.centroid_lat,
            'lon': pos.centroid_lon,
            'max_reflectivity': pos.max_reflectivity,
            'mesh_mm': pos.mesh_mm,
            'mesh_inches': round(pos.mesh_inches, 2),
            'velocity_kmh': pos.velocity_kmh,
            'direction_deg': pos.direction_deg,
            'stage': pos.stage,
            'age_minutes': pos.age_minutes
        })

    return jsonify({
        'cell_id': cell_id,
        'start_time': track.start_time.isoformat(),
        'end_time': track.end_time.isoformat(),
        'duration_minutes': track.duration_minutes,
        'max_mesh_mm': track.max_mesh_mm,
        'max_reflectivity': track.max_reflectivity,
        'avg_velocity_kmh': track.avg_velocity_kmh,
        'track_length_km': track.track_length_km,
        'lifecycle_stages': list(set(track.lifecycle_stages)),
        'positions': positions
    })


@storm_tracking_api_bp.route('/active', methods=['GET'])
@login_required
def get_active_cells():
    """Get currently active storm cells"""
    tracker = get_tracker()

    active = []
    for cell_id, cell in tracker.active_cells.items():
        active.append({
            'cell_id': cell.id,
            'timestamp': cell.timestamp,
            'lat': cell.centroid_lat,
            'lon': cell.centroid_lon,
            'max_reflectivity': cell.max_reflectivity,
            'mesh_mm': cell.mesh_mm,
            'mesh_inches': round(cell.mesh_inches, 2),
            'velocity_kmh': cell.velocity_kmh,
            'direction_deg': cell.direction_deg,
            'stage': cell.stage,
            'age_minutes': cell.age_minutes
        })

    return jsonify({
        'active_cells': active,
        'count': len(active)
    })


# =============================================================================
# SWATH GENERATION
# =============================================================================

@storm_tracking_api_bp.route('/<int:cell_id>/swath', methods=['GET'])
@login_required
def get_cell_swath(cell_id):
    """Create swath polygon for a cell track"""
    tracker = get_tracker()
    buffer_km = request.args.get('buffer_km', 3.0, type=float)

    swath = tracker.create_track_swath(cell_id, buffer_km=buffer_km)

    if not swath:
        return jsonify({'error': 'Cell not found or insufficient track data'}), 404

    return jsonify({
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': swath['coordinates']
        },
        'properties': swath['properties']
    })


@storm_tracking_api_bp.route('/swaths', methods=['GET'])
@login_required
def get_all_swaths():
    """Create swath polygons for all tracked cells"""
    tracker = get_tracker()
    min_duration = request.args.get('min_duration', 10, type=float)
    buffer_km = request.args.get('buffer_km', 3.0, type=float)

    swaths = tracker.create_all_track_swaths(
        min_duration_minutes=min_duration,
        buffer_km=buffer_km
    )

    return jsonify({
        'type': 'FeatureCollection',
        'features': swaths,
        'count': len(swaths)
    })


# =============================================================================
# FORECASTING
# =============================================================================

@storm_tracking_api_bp.route('/<int:cell_id>/forecast', methods=['GET'])
@login_required
def get_cell_forecast(cell_id):
    """Forecast future positions of a cell"""
    tracker = get_tracker()
    forecast_minutes = request.args.get('minutes', 30, type=int)

    forecasts = tracker.get_cell_motion_forecast(cell_id, forecast_minutes)

    if not forecasts:
        return jsonify({'error': 'Cell not found or no velocity data'}), 404

    result = []
    for lat, lon, timestamp in forecasts:
        result.append({
            'lat': lat,
            'lon': lon,
            'timestamp': timestamp
        })

    return jsonify({
        'cell_id': cell_id,
        'forecast_minutes': forecast_minutes,
        'positions': result
    })


# =============================================================================
# STATISTICS
# =============================================================================

@storm_tracking_api_bp.route('/stats', methods=['GET'])
@login_required
def get_tracking_stats():
    """Get overall tracking statistics"""
    tracker = get_tracker()

    stats = tracker.get_tracking_statistics()

    return jsonify(stats)


# =============================================================================
# RADAR SCAN PROCESSING
# =============================================================================

@storm_tracking_api_bp.route('/process', methods=['POST'])
@login_required
def process_radar_scan():
    """Process radar detections and track cells"""
    tracker = get_tracker()
    data = request.get_json()

    if 'detections' not in data:
        return jsonify({'error': 'detections array required'}), 400

    scan_time = data.get('scan_time')
    if scan_time:
        scan_time = datetime.fromisoformat(scan_time.replace('Z', ''))
    else:
        scan_time = datetime.utcnow()

    cells = tracker.process_radar_scan(data['detections'], scan_time)

    result = []
    for cell in cells:
        result.append({
            'cell_id': cell.id,
            'lat': cell.centroid_lat,
            'lon': cell.centroid_lon,
            'max_reflectivity': cell.max_reflectivity,
            'mesh_mm': cell.mesh_mm,
            'velocity_kmh': cell.velocity_kmh,
            'direction_deg': cell.direction_deg,
            'stage': cell.stage
        })

    return jsonify({
        'cells': result,
        'count': len(result),
        'scan_time': scan_time.isoformat()
    })


@storm_tracking_api_bp.route('/simulate', methods=['POST'])
@login_required
def simulate_storm():
    """Create simulated storm track for testing"""
    tracker = reset_tracker()  # Start fresh
    data = request.get_json()

    start_lat = data.get('start_lat', 32.7)
    start_lon = data.get('start_lon', -96.8)
    direction_deg = data.get('direction', 45)
    speed_kmh = data.get('speed', 50)
    duration_minutes = data.get('duration', 60)
    peak_reflectivity = data.get('peak_reflectivity', 65)

    cells = tracker.process_simulated_storm(
        start_lat=start_lat,
        start_lon=start_lon,
        direction_deg=direction_deg,
        speed_kmh=speed_kmh,
        duration_minutes=duration_minutes,
        peak_reflectivity=peak_reflectivity
    )

    # Get resulting tracks and swaths
    tracks = tracker.get_cell_tracks(min_duration_minutes=5)
    swaths = tracker.create_all_track_swaths(min_duration_minutes=5)
    stats = tracker.get_tracking_statistics()

    return jsonify({
        'cells_created': len(cells),
        'tracks': len(tracks),
        'swaths': {
            'type': 'FeatureCollection',
            'features': swaths
        },
        'statistics': stats
    })


@storm_tracking_api_bp.route('/reset', methods=['POST'])
@login_required
def reset_tracking():
    """Reset tracker to clear all state"""
    reset_tracker()
    return jsonify({'success': True, 'message': 'Tracker reset'})
