"""
Storm Monitor API Routes
========================
RESTful API for StormMonitor control and status.

Endpoints:
- Status: get monitor status
- Control: start/stop monitoring
- Config: get/update configuration
"""

import math
from flask import Blueprint, request, jsonify
from src.core.auth.decorators import login_required
from src.alerts.monitor_defaults import national_monitor_defaults

storm_monitor_api_bp = Blueprint('storm_monitor_api', __name__, url_prefix='/api/storm-monitor')
system_api_bp = Blueprint('system_api', __name__, url_prefix='/api/system')

# Global monitor instance
_monitor_instance = None
_monitor_config = None
_started_by = 'unknown'


def get_monitor():
    """Get or create StormMonitor instance"""
    global _monitor_instance, _monitor_config

    if _monitor_instance is None:
        from src.alerts.storm_monitor import StormMonitor, MonitorConfig
        _monitor_config = MonitorConfig()
        _monitor_instance = StormMonitor(_monitor_config)

    return _monitor_instance


def set_monitor_instance(monitor, started_by='unknown'):
    """Set the global monitor instance (used by CLI and API)."""
    global _monitor_instance, _monitor_config, _started_by
    _monitor_instance = monitor
    _monitor_config = monitor.config
    _started_by = started_by


def get_default_config():
    """Get default monitor configuration as dict (national defaults + env overrides)."""
    from src.alerts.storm_monitor import MonitorConfig
    defaults = national_monitor_defaults()
    config = MonitorConfig(**defaults)
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
        'database_enabled': config.database_enabled,
        'enable_discovery_focus': config.enable_discovery_focus,
        'discovery_interval_seconds': config.discovery_interval_seconds,
        'focus_interval_seconds': config.focus_interval_seconds,
        'hot_ttl_seconds': config.hot_ttl_seconds,
        'hot_promote_dbz': config.hot_promote_dbz,
        'hot_promote_hail_score': config.hot_promote_hail_score,
        'max_workers': config.max_workers,
        'max_focus_radars': config.max_focus_radars,
        'max_discovery_radars_per_tick': config.max_discovery_radars_per_tick,
        'per_radar_timeout_seconds': config.per_radar_timeout_seconds,
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
        response = {'initialized': True}
        response.update(status)
        return jsonify(response)
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
    global _monitor_instance, _monitor_config, _started_by

    data = request.get_json() or {}

    # Apply any config overrides
    if data:
        from src.alerts.storm_monitor import StormMonitor, MonitorConfig

        # Build config from data
        config_params = {}

        _passthrough_keys = [
            'radar_ids', 'scan_interval_seconds', 'min_pdr_score',
            'coverage_region', 'coverage_regions',
            'enable_discovery_focus', 'discovery_interval_seconds',
            'focus_interval_seconds', 'hot_ttl_seconds',
            'hot_promote_dbz', 'hot_promote_hail_score',
            'max_workers', 'max_focus_radars',
            'max_discovery_radars_per_tick', 'per_radar_timeout_seconds',
        ]
        for key in _passthrough_keys:
            if key in data:
                config_params[key] = data[key]

        _monitor_config = MonitorConfig(**config_params)
        _monitor_instance = StormMonitor(_monitor_config)

    monitor = get_monitor()

    if monitor.running:
        return jsonify({
            'success': True,
            'message': 'already running',
            'started_by': _started_by,
        })

    try:
        # Start in background mode
        monitor.start(background=True)
        _started_by = 'api'
        return jsonify({
            'success': True,
            'message': 'Monitor started',
            'started_by': 'api',
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
            'database_enabled': _monitor_config.database_enabled,
            'enable_discovery_focus': _monitor_config.enable_discovery_focus,
            'discovery_interval_seconds': _monitor_config.discovery_interval_seconds,
            'focus_interval_seconds': _monitor_config.focus_interval_seconds,
            'hot_ttl_seconds': _monitor_config.hot_ttl_seconds,
            'hot_promote_dbz': _monitor_config.hot_promote_dbz,
            'hot_promote_hail_score': _monitor_config.hot_promote_hail_score,
            'max_workers': _monitor_config.max_workers,
            'max_focus_radars': _monitor_config.max_focus_radars,
            'max_discovery_radars_per_tick': _monitor_config.max_discovery_radars_per_tick,
            'per_radar_timeout_seconds': _monitor_config.per_radar_timeout_seconds,
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


# =============================================================================
# SYSTEM MODE (no auth required — for easy debugging / health checks)
# =============================================================================

def _build_system_mode_payload():
    """Build the system-mode JSON payload (shared by both route aliases).

    CRASH-PROOF: Reads only plain attributes — NO locks, NO SQLite, NO method
    calls that could block or deadlock during heavy concurrent radar processing.
    """
    import os
    import threading

    global _monitor_instance, _started_by

    if _monitor_instance is None or not getattr(_monitor_instance, 'running', False):
        return {
            'active_engine': 'none',
            'started_by': 'n/a',
            'monitor_running': False,
        }

    mon = _monitor_instance

    # --- Lock-free reads of simple attributes ---
    # _stats is a dict; reading individual keys is GIL-safe in CPython.
    stats = mon._stats  # reference, not copy — avoids acquiring _stats_lock
    last_tick = stats.get('last_tick_utc')
    processed_ok = stats.get('processed_ok', 0)
    processed_err = stats.get('processed_err', 0)
    processed_timeout = stats.get('processed_timeout', 0)
    cancelled = stats.get('cancelled_futures', 0)
    timed_out = stats.get('timed_out_futures', 0)
    avg_check = stats.get('avg_check_seconds', 0)

    # Hot radars: read dict keys without lock (snapshot may be stale, that's OK)
    try:
        hot_list = list(mon._hot_radars.keys())[:10]
        hot_count = len(mon._hot_radars)
    except RuntimeError:
        # dict changed size during iteration — harmless under GIL
        hot_list = []
        hot_count = 0

    # Last errors: snapshot of list tail
    try:
        errors = [str(e) for e in list(stats.get('last_errors', []))[-5:]]
    except Exception:
        errors = []

    scheduler_mode = 'unknown'
    try:
        scheduler_mode = ('discovery_focus'
                          if mon.config.enable_discovery_focus
                          else 'legacy')
    except Exception:
        pass

    return {
        'active_engine': 'storm_monitor',
        'started_by': _started_by,
        'monitor_running': True,
        'scheduler_mode': scheduler_mode,
        'hot_radar_count': hot_count,
        'hot_radars': hot_list,
        'last_tick_utc': last_tick,
        'avg_check_seconds': avg_check,
        'processed_ok': processed_ok,
        'processed_err': processed_err,
        'processed_timeout': processed_timeout,
        'cancelled_futures': cancelled,
        'timed_out_futures': timed_out,
        'last_errors': errors,
        'pid': os.getpid(),
        'thread': threading.current_thread().name,
    }


@storm_monitor_api_bp.route('/system-mode', methods=['GET'])
def get_system_mode():
    """GET /api/storm-monitor/system-mode"""
    try:
        return jsonify(_build_system_mode_payload())
    except Exception as exc:
        return jsonify({'error': str(exc), 'monitor_running': True}), 500


@system_api_bp.route('/mode', methods=['GET'])
def get_system_mode_alias():
    """GET /api/system/mode — canonical alias."""
    try:
        return jsonify(_build_system_mode_payload())
    except Exception as exc:
        return jsonify({'error': str(exc), 'monitor_running': True}), 500


# ---------------------------------------------------------------------------
# Health / Ready / Metrics (HARDEN-3)
# ---------------------------------------------------------------------------

@system_api_bp.route('/health', methods=['GET'])
def get_health():
    """GET /api/system/health — Liveness probe (always 200 if alive)."""
    from src.observability.health import get_health_check
    return jsonify(get_health_check().get_health())


@system_api_bp.route('/ready', methods=['GET'])
def get_ready():
    """GET /api/system/ready — Readiness probe (checks subsystems)."""
    from src.observability.health import get_health_check
    result = get_health_check().check_all()
    status_code = 200 if result['healthy'] else 503
    return jsonify(result), status_code


@system_api_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """GET /api/system/metrics — Lightweight application metrics."""
    from src.observability.health import get_health_check
    from src.db.engine import get_engine_info
    from src.workers.task_queue import get_task_queue

    hc = get_health_check()
    metrics = hc.get_metrics()
    metrics['db'] = get_engine_info()

    try:
        metrics['workers'] = get_task_queue().get_status()
    except Exception:
        metrics['workers'] = {'backend': 'unavailable'}

    return jsonify(metrics)


@system_api_bp.route('/cadence', methods=['GET'])
def cadence_report():
    """
    Human-readable national monitoring cadence report.
    No auth required — safe for ops dashboards.
    """
    try:
        from src.radar.coverage import get_all_radars
        radars = get_all_radars()
        radars_active = len(radars)
    except Exception:
        radars_active = None

    d = national_monitor_defaults()
    batch = int(d.get("max_discovery_radars_per_tick", 80))
    disc = int(d.get("discovery_interval_seconds", 300))
    focus = int(d.get("focus_interval_seconds", 180))
    max_focus = int(d.get("max_focus_radars", 100))
    timeout_s = int(d.get("per_radar_timeout_seconds", 60))
    workers = int(d.get("max_workers", 24))

    est_sweep_min = None
    if radars_active and batch > 0:
        ticks = math.ceil(radars_active / batch)
        est_sweep_min = round((ticks * disc) / 60.0, 1)

    verdict = "UNKNOWN"
    if est_sweep_min is not None:
        if est_sweep_min <= 20:
            verdict = f"OK: national sweep ~{est_sweep_min} min"
        elif est_sweep_min <= 45:
            verdict = f"MEH: national sweep ~{est_sweep_min} min (consider higher batch/workers)"
        else:
            verdict = f"BAD: national sweep ~{est_sweep_min} min (too slow for national 24/7)"

    return jsonify({
        "radars_active": radars_active,
        "max_workers": workers,
        "discovery_batch": batch,
        "discovery_interval_seconds": disc,
        "estimated_full_sweep_minutes": est_sweep_min,
        "focus_interval_seconds": focus,
        "max_focus_radars": max_focus,
        "per_radar_timeout_seconds": timeout_s,
        "verdict": verdict,
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
