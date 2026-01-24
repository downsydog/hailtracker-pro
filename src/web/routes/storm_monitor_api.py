"""
Storm Monitor API Routes
========================
RESTful API for StormMonitor control and status.

Endpoints:
- Status: get monitor status
- Control: start/stop monitoring
- Config: get/update configuration
"""

from flask import Blueprint, request, jsonify
from src.core.auth.decorators import login_required

storm_monitor_api_bp = Blueprint('storm_monitor_api', __name__, url_prefix='/api/storm-monitor')

# Global monitor instance
_monitor_instance = None
_monitor_config = None


def get_monitor():
    """Get or create StormMonitor instance"""
    global _monitor_instance, _monitor_config

    if _monitor_instance is None:
        from src.alerts.storm_monitor import StormMonitor, MonitorConfig
        _monitor_config = MonitorConfig()
        _monitor_instance = StormMonitor(_monitor_config)

    return _monitor_instance


def get_default_config():
    """Get default monitor configuration as dict"""
    from src.alerts.storm_monitor import MonitorConfig
    config = MonitorConfig()
    return {
        'radar_ids': config.radar_ids,
        'scan_interval_seconds': config.scan_interval_seconds,
        'lookback_minutes': config.lookback_minutes,
        'min_reflectivity_dbz': config.min_reflectivity_dbz,
        'min_mesh_mm': config.min_mesh_mm,
        'min_pdr_score': config.min_pdr_score,
        'coverage_region': config.coverage_region,
        'coverage_regions': config.coverage_regions,
        'coverage_center_lat': config.coverage_center_lat,
        'coverage_center_lon': config.coverage_center_lon,
        'coverage_radius_miles': config.coverage_radius_miles,
        'auto_select_radars': config.auto_select_radars,
        'enable_sound': config.enable_sound,
        'enable_console': config.enable_console,
        'enable_file_log': config.enable_file_log,
        'sms_enabled': config.sms_enabled,
        'email_enabled': config.email_enabled,
        'database_enabled': config.database_enabled
    }


# =============================================================================
# STATUS
# =============================================================================

@storm_monitor_api_bp.route('/status', methods=['GET'])
@login_required
def get_monitor_status():
    """Get current monitor status"""
    global _monitor_instance

    if _monitor_instance is None:
        return jsonify({
            'running': False,
            'initialized': False,
            'message': 'Monitor not initialized'
        })

    try:
        status = _monitor_instance.get_status()
        return jsonify({
            'running': status.get('running', False),
            'initialized': True,
            'radars': status.get('radars', []),
            'scans_processed': status.get('scans_processed', 0),
            'alerts_generated': status.get('alerts_generated', 0),
            'last_scan': status.get('last_scan'),
            'active_alerts': status.get('active_alerts', 0)
        })
    except Exception as e:
        return jsonify({
            'running': False,
            'initialized': True,
            'error': str(e)
        })


# =============================================================================
# CONTROL
# =============================================================================

@storm_monitor_api_bp.route('/start', methods=['POST'])
@login_required
def start_monitor():
    """Start the storm monitor (background mode)"""
    global _monitor_instance, _monitor_config

    data = request.get_json() or {}

    # Apply any config overrides
    if data:
        from src.alerts.storm_monitor import StormMonitor, MonitorConfig

        # Build config from data
        config_params = {}

        if 'radar_ids' in data:
            config_params['radar_ids'] = data['radar_ids']
        if 'scan_interval_seconds' in data:
            config_params['scan_interval_seconds'] = data['scan_interval_seconds']
        if 'min_pdr_score' in data:
            config_params['min_pdr_score'] = data['min_pdr_score']
        if 'coverage_region' in data:
            config_params['coverage_region'] = data['coverage_region']
        if 'coverage_regions' in data:
            config_params['coverage_regions'] = data['coverage_regions']

        _monitor_config = MonitorConfig(**config_params)
        _monitor_instance = StormMonitor(_monitor_config)

    monitor = get_monitor()

    if monitor.running:
        return jsonify({
            'success': False,
            'message': 'Monitor already running'
        })

    try:
        # Start in background mode
        monitor.start(background=True)
        return jsonify({
            'success': True,
            'message': 'Monitor started',
            'radars': monitor.config.radar_ids
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@storm_monitor_api_bp.route('/stop', methods=['POST'])
@login_required
def stop_monitor():
    """Stop the storm monitor"""
    global _monitor_instance

    if _monitor_instance is None:
        return jsonify({
            'success': False,
            'message': 'Monitor not initialized'
        })

    if not _monitor_instance.running:
        return jsonify({
            'success': False,
            'message': 'Monitor not running'
        })

    try:
        _monitor_instance.stop()
        return jsonify({
            'success': True,
            'message': 'Monitor stopped'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# CONFIGURATION
# =============================================================================

@storm_monitor_api_bp.route('/config', methods=['GET'])
@login_required
def get_monitor_config():
    """Get current monitor configuration"""
    global _monitor_config

    if _monitor_config:
        return jsonify({
            'radar_ids': _monitor_config.radar_ids,
            'scan_interval_seconds': _monitor_config.scan_interval_seconds,
            'lookback_minutes': _monitor_config.lookback_minutes,
            'min_reflectivity_dbz': _monitor_config.min_reflectivity_dbz,
            'min_mesh_mm': _monitor_config.min_mesh_mm,
            'min_pdr_score': _monitor_config.min_pdr_score,
            'coverage_region': _monitor_config.coverage_region,
            'coverage_regions': _monitor_config.coverage_regions,
            'coverage_center_lat': _monitor_config.coverage_center_lat,
            'coverage_center_lon': _monitor_config.coverage_center_lon,
            'coverage_radius_miles': _monitor_config.coverage_radius_miles,
            'auto_select_radars': _monitor_config.auto_select_radars,
            'enable_sound': _monitor_config.enable_sound,
            'enable_console': _monitor_config.enable_console,
            'enable_file_log': _monitor_config.enable_file_log,
            'sms_enabled': _monitor_config.sms_enabled,
            'email_enabled': _monitor_config.email_enabled,
            'database_enabled': _monitor_config.database_enabled
        })

    return jsonify(get_default_config())


@storm_monitor_api_bp.route('/config', methods=['PUT'])
@login_required
def update_monitor_config():
    """Update monitor configuration (requires restart)"""
    global _monitor_instance, _monitor_config

    data = request.get_json()

    if _monitor_instance and _monitor_instance.running:
        return jsonify({
            'success': False,
            'message': 'Stop monitor before updating config'
        }), 400

    from src.alerts.storm_monitor import MonitorConfig

    # Get current config values
    current = get_default_config()
    if _monitor_config:
        current.update({
            'radar_ids': _monitor_config.radar_ids,
            'scan_interval_seconds': _monitor_config.scan_interval_seconds,
            'min_pdr_score': _monitor_config.min_pdr_score,
            'coverage_region': _monitor_config.coverage_region,
            'coverage_regions': _monitor_config.coverage_regions,
        })

    # Apply updates
    for key, value in data.items():
        if key in current:
            current[key] = value

    # Create new config
    _monitor_config = MonitorConfig(
        radar_ids=current['radar_ids'],
        scan_interval_seconds=current['scan_interval_seconds'],
        lookback_minutes=current['lookback_minutes'],
        min_reflectivity_dbz=current['min_reflectivity_dbz'],
        min_mesh_mm=current['min_mesh_mm'],
        min_pdr_score=current['min_pdr_score'],
        coverage_region=current['coverage_region'],
        coverage_regions=current['coverage_regions'],
        coverage_center_lat=current['coverage_center_lat'],
        coverage_center_lon=current['coverage_center_lon'],
        coverage_radius_miles=current['coverage_radius_miles'],
        auto_select_radars=current['auto_select_radars'],
        enable_sound=current['enable_sound'],
        enable_console=current['enable_console'],
        enable_file_log=current['enable_file_log'],
        sms_enabled=current['sms_enabled'],
        email_enabled=current['email_enabled'],
        database_enabled=current['database_enabled']
    )

    # Reinitialize monitor with new config
    from src.alerts.storm_monitor import StormMonitor
    _monitor_instance = StormMonitor(_monitor_config)

    return jsonify({
        'success': True,
        'message': 'Configuration updated',
        'config': current
    })


# =============================================================================
# AVAILABLE RADARS & REGIONS
# =============================================================================

@storm_monitor_api_bp.route('/radars', methods=['GET'])
@login_required
def get_available_radars():
    """Get list of available radar sites"""
    try:
        from src.radar.coverage import get_all_radars
        radars = get_all_radars()
        return jsonify({
            'radars': [
                {
                    'site_code': r.site_code,
                    'name': r.name,
                    'state': r.state_province,
                    'lat': r.latitude,
                    'lon': r.longitude
                }
                for r in radars
            ],
            'count': len(radars)
        })
    except ImportError:
        # Return common radars if coverage module not available
        return jsonify({
            'radars': [
                {'site_code': 'KFWS', 'name': 'Fort Worth', 'state': 'TX'},
                {'site_code': 'KDFW', 'name': 'Dallas/Fort Worth', 'state': 'TX'},
                {'site_code': 'KTLX', 'name': 'Oklahoma City', 'state': 'OK'},
                {'site_code': 'KICT', 'name': 'Wichita', 'state': 'KS'},
                {'site_code': 'KOAX', 'name': 'Omaha', 'state': 'NE'},
                {'site_code': 'KAMA', 'name': 'Amarillo', 'state': 'TX'},
            ],
            'count': 6
        })


@storm_monitor_api_bp.route('/regions', methods=['GET'])
@login_required
def get_available_regions():
    """Get list of named coverage regions"""
    try:
        from src.alerts.geo_filter import list_named_regions
        regions = list_named_regions()
        return jsonify({
            'regions': regions
        })
    except ImportError:
        return jsonify({
            'regions': [
                'hail_alley_core',
                'texas',
                'oklahoma',
                'kansas',
                'nebraska',
                'dallas_fort_worth',
                'oklahoma_city',
                'denver'
            ]
        })


# =============================================================================
# ALERTS
# =============================================================================

@storm_monitor_api_bp.route('/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get recent alerts from monitor"""
    global _monitor_instance

    if _monitor_instance is None:
        return jsonify({'alerts': [], 'count': 0})

    try:
        alerts = _monitor_instance.alert_manager.get_active_alerts()
        return jsonify({
            'alerts': [
                {
                    'id': a.id if hasattr(a, 'id') else None,
                    'level': a.level.name if hasattr(a.level, 'name') else str(a.level),
                    'event_name': a.event_name if hasattr(a, 'event_name') else 'Unknown',
                    'location': a.location if hasattr(a, 'location') else None,
                    'pdr_score': a.pdr_score if hasattr(a, 'pdr_score') else None,
                    'timestamp': a.timestamp.isoformat() if hasattr(a, 'timestamp') else None
                }
                for a in alerts
            ],
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({'alerts': [], 'count': 0, 'error': str(e)})


@storm_monitor_api_bp.route('/alerts/stats', methods=['GET'])
@login_required
def get_alert_stats():
    """Get alert statistics"""
    global _monitor_instance

    if _monitor_instance is None:
        return jsonify({'total': 0})

    try:
        stats = _monitor_instance.alert_manager.get_alert_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'total': 0, 'error': str(e)})


# =============================================================================
# RADAR HISTORY / REPLAY
# =============================================================================

@storm_monitor_api_bp.route('/radar/history', methods=['GET'])
@login_required
def get_radar_history():
    """
    Get radar frame URLs for replay.

    Query params:
        radar_id: Radar site code (e.g., 'KFWS')
        start_time: Start time ISO format (optional, default: 2 hours ago)
        end_time: End time ISO format (optional, default: now)
        product: Radar product (default: 'N0Q' for reflectivity)

    Returns list of frame URLs/metadata for radar replay.
    """
    from datetime import datetime, timedelta

    radar_id = request.args.get('radar_id', 'KFWS')
    product = request.args.get('product', 'N0Q')

    # Parse time range
    end_time = datetime.utcnow()
    if request.args.get('end_time'):
        try:
            end_time = datetime.fromisoformat(request.args.get('end_time').replace('Z', ''))
        except:
            pass

    start_time = end_time - timedelta(hours=2)
    if request.args.get('start_time'):
        try:
            start_time = datetime.fromisoformat(request.args.get('start_time').replace('Z', ''))
        except:
            pass

    # Calculate number of frames (typically every 5-10 minutes)
    duration_minutes = int((end_time - start_time).total_seconds() / 60)
    frame_interval = 5  # minutes
    num_frames = max(1, duration_minutes // frame_interval)

    # Generate frame metadata
    # Note: In production, these would be actual AWS S3 NEXRAD URLs or cached radar images
    frames = []
    for i in range(num_frames):
        frame_time = start_time + timedelta(minutes=i * frame_interval)
        frames.append({
            'timestamp': frame_time.isoformat() + 'Z',
            'radar_id': radar_id,
            'product': product,
            # Use IEM (Iowa Environmental Mesonet) for radar tiles
            # This is a real, free service for radar images
            'tile_url': f'https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-{frame_time.strftime("%Y%m%d%H%M")}/{{z}}/{{x}}/{{y}}.png',
            # Alternatively, use NWS radar imagery
            'image_url': f'https://radar.weather.gov/ridge/standard/{radar_id}_{product}_{frame_time.strftime("%Y%m%d%H%M")}.png',
            'index': i
        })

    return jsonify({
        'radar_id': radar_id,
        'product': product,
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'frame_count': len(frames),
        'frame_interval_minutes': frame_interval,
        'frames': frames
    })


@storm_monitor_api_bp.route('/radar/loop', methods=['GET'])
@login_required
def get_radar_loop():
    """
    Get animated radar loop URL for a region.

    Query params:
        region: Region code or radar ID
        duration: Loop duration in hours (default: 2)

    Returns URL for animated radar loop.
    """
    region = request.args.get('region', 'us')
    duration = request.args.get('duration', 2, type=int)

    # NWS provides animated loops for regions
    # Common region codes: us, conus, plus, pr, ak, hi
    loop_urls = {
        'us': 'https://radar.weather.gov/ridge/standard/CONUS-LARGE_loop.gif',
        'conus': 'https://radar.weather.gov/ridge/standard/CONUS-LARGE_loop.gif',
        'tx': 'https://radar.weather.gov/ridge/standard/CENTERGULF_loop.gif',
        'ok': 'https://radar.weather.gov/ridge/standard/SOUTHPLAINS_loop.gif',
        'central': 'https://radar.weather.gov/ridge/standard/CENTERGULF_loop.gif',
    }

    # If a specific radar is requested, use its local loop
    if region.upper().startswith('K') and len(region) == 4:
        loop_url = f'https://radar.weather.gov/ridge/standard/{region.upper()}_N0R_loop.gif'
    else:
        loop_url = loop_urls.get(region.lower(), loop_urls['us'])

    return jsonify({
        'region': region,
        'duration_hours': duration,
        'loop_url': loop_url,
        'frames_url': f'/api/storm-monitor/radar/history?radar_id={region.upper()}'
    })
