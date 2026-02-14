"""
Storm Cell Tracking API Routes
==============================
RESTful API for StormCellTracker functionality.

Endpoints:
- Cell tracking: process scans, get tracks, forecast positions
- Swath generation: create track swaths, all swaths
- Statistics: tracking statistics
"""

import os
from flask import Blueprint, request, jsonify
from datetime import datetime
from src.core.auth.decorators import login_required

storm_tracking_api_bp = Blueprint('storm_tracking_api', __name__, url_prefix='/api/storm-cells')

# Global tracker instance (singleton for state persistence)
_tracker_instance = None


def get_tracker():
    """Get or create StormCellTracker instance (loads persisted state if available)"""
    global _tracker_instance
    if _tracker_instance is None:
        from src.radar.storm_cell_tracker import StormCellTracker
        state_path = StormCellTracker.DEFAULT_STATE_PATH
        if os.path.isfile(state_path):
            try:
                _tracker_instance = StormCellTracker.load_state(state_path, simulation_mode=True)
            except Exception:
                _tracker_instance = StormCellTracker(simulation_mode=True)
        else:
            _tracker_instance = StormCellTracker(simulation_mode=True)
    return _tracker_instance


def reset_tracker():
    """Reset tracker to clear state and remove persisted file"""
    global _tracker_instance
    from src.radar.storm_cell_tracker import StormCellTracker
    _tracker_instance = StormCellTracker(simulation_mode=True)
    state_path = StormCellTracker.DEFAULT_STATE_PATH
    if os.path.isfile(state_path):
        os.remove(state_path)
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
            'position_count': len(track.positions),
            'radar_id': track.positions[0].radar_id if track.positions else None,
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
            'age_minutes': pos.age_minutes,
            'radar_id': pos.radar_id,
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
        velocity_mph = round(cell.velocity_kmh * 0.621371, 1)
        active.append({
            'id': cell.id,
            'cell_id': cell.id,
            'timestamp': cell.timestamp,
            'lat': cell.centroid_lat,
            'lon': cell.centroid_lon,
            'max_reflectivity': round(cell.max_reflectivity, 1),
            'mesh_mm': round(cell.mesh_mm, 1),
            'mesh_inches': round(cell.mesh_inches, 2),
            'mesh': round(cell.mesh_inches, 2),
            'max_hail_size': round(cell.mesh_inches, 2),
            'vil': None,
            'echo_tops': None,
            'velocity_kmh': round(cell.velocity_kmh, 1),
            'velocity_mph': velocity_mph,
            'motion_speed': velocity_mph,
            'motion_speed_mph': velocity_mph,
            'direction_deg': round(cell.direction_deg, 1),
            'motion_direction': round(cell.direction_deg, 1),
            'stage': cell.stage,
            'lifecycle_stage': cell.stage,
            'age_minutes': round(cell.age_minutes, 1),
            'track_duration_minutes': round(cell.age_minutes, 1),
            'missed_scans': tracker.missed_scans.get(cell.id, 0),
            'radar_id': cell.radar_id,
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
# STORM EVENTS
# =============================================================================

@storm_tracking_api_bp.route('/events/active', methods=['GET'])
@login_required
def get_active_events():
    """Get top active events as a ranked FeatureCollection (the 'now feed')"""
    tracker = get_tracker()
    lookback = request.args.get('lookback', 180, type=int)
    join_km = request.args.get('join_km', 25.0, type=float)
    limit = request.args.get('limit', 10, type=int)
    buffer_km = request.args.get('buffer_km', 3.0, type=float)

    features = tracker.get_active_event_features(
        lookback_minutes=lookback,
        join_distance_km=join_km,
        limit=limit,
        buffer_km=buffer_km,
    )

    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
        'count': len(features),
    })


@storm_tracking_api_bp.route('/events', methods=['GET'])
@login_required
def get_events():
    """Get storm events (multi-cell grouping)"""
    tracker = get_tracker()
    lookback = request.args.get('lookback', 180, type=int)
    join_km = request.args.get('join_km', 25.0, type=float)

    events = tracker.get_events(lookback_minutes=lookback, join_distance_km=join_km)

    result = []
    for ev in events:
        result.append({
            'event_id': ev.event_id,
            'start_time': ev.start_time.isoformat(),
            'end_time': ev.end_time.isoformat(),
            'cell_ids': ev.cell_ids,
            'radar_ids': ev.radar_ids,
            'max_mesh_mm': ev.max_mesh_mm,
            'max_mesh_inches': ev.max_mesh_inches,
            'max_reflectivity': ev.max_reflectivity,
            'estimated_area_sq_km': ev.estimated_area_sq_km,
            'centroid_lat': ev.centroid_lat,
            'centroid_lon': ev.centroid_lon,
            'severity': ev.severity,
            'confidence': ev.confidence,
            'status': ev.status,
            'phase': ev.phase,
            'impact_window_minutes': ev.impact_window_minutes,
            'event_quality_score': ev.event_quality_score,
            'event_quality_reasons': ev.event_quality_reasons,
        })

    return jsonify({
        'events': result,
        'count': len(result),
    })


@storm_tracking_api_bp.route('/events/<event_id>/swaths', methods=['GET'])
@login_required
def get_event_swaths(event_id):
    """Get swaths for all cells in a storm event"""
    tracker = get_tracker()
    lookback = request.args.get('lookback', 180, type=int)
    join_km = request.args.get('join_km', 25.0, type=float)
    buffer_km = request.args.get('buffer_km', 3.0, type=float)

    events = tracker.get_events(lookback_minutes=lookback, join_distance_km=join_km)
    event = next((e for e in events if e.event_id == event_id), None)

    if not event:
        return jsonify({'error': 'Event not found'}), 404

    features = []
    for cell_id in event.cell_ids:
        swath = tracker.create_track_swath(cell_id, buffer_km=buffer_km)
        if swath:
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': swath['coordinates'],
                },
                'properties': swath['properties'],
            })

    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
        'event_id': event_id,
    })


@storm_tracking_api_bp.route('/events/<event_id>/swath-merged', methods=['GET'])
@login_required
def get_event_merged_swath(event_id):
    """Get a single merged swath polygon for all cells in a storm event"""
    tracker = get_tracker()
    buffer_km = request.args.get('buffer_km', 3.0, type=float)

    merged = tracker.create_event_merged_swath(event_id, buffer_km=buffer_km)

    if not merged:
        return jsonify({'error': 'Event not found or no swath data'}), 404

    return jsonify({
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': merged['coordinates'],
        },
        'properties': merged['properties'],
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
        velocity_mph = round(cell.velocity_kmh * 0.621371, 1)
        result.append({
            'id': cell.id,
            'cell_id': cell.id,
            'lat': cell.centroid_lat,
            'lon': cell.centroid_lon,
            'max_reflectivity': round(cell.max_reflectivity, 1),
            'mesh_mm': round(cell.mesh_mm, 1),
            'mesh_inches': round(cell.mesh_inches, 2),
            'velocity_kmh': round(cell.velocity_kmh, 1),
            'velocity_mph': velocity_mph,
            'motion_speed_mph': velocity_mph,
            'direction_deg': round(cell.direction_deg, 1),
            'motion_direction': round(cell.direction_deg, 1),
            'stage': cell.stage,
            'lifecycle_stage': cell.stage,
            'age_minutes': round(cell.age_minutes, 1),
            'radar_id': cell.radar_id,
        })

    tracker.save_state()

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
    seed = data.get('seed')  # optional int for deterministic simulation

    cells = tracker.process_simulated_storm(
        start_lat=start_lat,
        start_lon=start_lon,
        direction_deg=direction_deg,
        speed_kmh=speed_kmh,
        duration_minutes=duration_minutes,
        peak_reflectivity=peak_reflectivity,
        seed=seed,
    )

    # Get resulting tracks and swaths
    tracks = tracker.get_cell_tracks(min_duration_minutes=5)
    swaths = tracker.create_all_track_swaths(min_duration_minutes=5)
    stats = tracker.get_tracking_statistics()

    tracker.save_state()

    return jsonify({
        'cells_created': len(cells),
        'tracks': len(tracks),
        'swaths': {
            'type': 'FeatureCollection',
            'features': swaths
        },
        'statistics': stats,
        'seed': seed,
    })


@storm_tracking_api_bp.route('/reset', methods=['POST'])
@login_required
def reset_tracking():
    """Reset tracker to clear all state"""
    reset_tracker()
    return jsonify({'success': True, 'message': 'Tracker reset'})
