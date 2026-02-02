"""
Real-time Weather API Endpoints

Provides FREE real-time severe weather data:
- NWS Alerts with hail information
- Local Storm Reports (hail, tornado, wind)
- SPC Watches and Outlooks
- Unified monitoring service
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('realtime', __name__, url_prefix='/api/realtime')


def get_weather_modules():
    """Lazy import weather modules to avoid circular imports."""
    from src.weather.realtime_monitor import get_monitor
    from src.weather.nws_alerts import NWSAlerts
    from src.weather.iowa_mesonet import IowaMesonet
    from src.weather.spc import StormPredictionCenter
    return get_monitor, NWSAlerts, IowaMesonet, StormPredictionCenter


# ============================================================================
# Monitor Status & Control
# ============================================================================

@bp.route('/status')
def status():
    """
    Get real-time monitor status.

    Returns:
        Monitor status including running state, last update time,
        and counts of current alerts/reports
    """
    get_monitor, _, _, _ = get_weather_modules()
    monitor = get_monitor()
    return jsonify(monitor.get_status())


@bp.route('/start', methods=['POST'])
def start_monitor():
    """
    Start the real-time monitoring service.

    JSON body (optional):
        interval: Update interval in seconds (default 60)
        report_hours: Hours of reports to fetch (default 6)

    Returns:
        Status confirmation
    """
    get_monitor, _, _, _ = get_weather_modules()
    monitor = get_monitor()

    data = request.get_json() or {}
    interval = data.get('interval', 60)
    report_hours = data.get('report_hours', 6)

    monitor.start(interval_seconds=interval, report_hours=report_hours)

    return jsonify({
        'status': 'started',
        'interval_seconds': interval,
        'report_hours': report_hours
    })


@bp.route('/stop', methods=['POST'])
def stop_monitor():
    """
    Stop the real-time monitoring service.

    Returns:
        Status confirmation
    """
    get_monitor, _, _, _ = get_weather_modules()
    monitor = get_monitor()
    monitor.stop()
    return jsonify({'status': 'stopped'})


@bp.route('/fetch')
def fetch_now():
    """
    Fetch all real-time data immediately.

    Query params:
        hours: Hours of reports to fetch (default 6)

    Returns:
        All current weather data from all sources
    """
    get_monitor, _, _, _ = get_weather_modules()
    monitor = get_monitor()

    hours = request.args.get('hours', 6, type=int)
    data = monitor.fetch_all(report_hours=hours)

    return jsonify(data)


# ============================================================================
# NWS Alerts
# ============================================================================

@bp.route('/alerts')
def get_alerts():
    """
    Get current NWS severe weather alerts with hail info.

    Query params:
        state: Filter by state code (e.g., 'TX', 'OK')
        min_size: Minimum hail size in inches

    Returns:
        List of parsed alerts with hail/wind information
    """
    _, NWSAlerts, _, _ = get_weather_modules()
    nws = NWSAlerts()

    state = request.args.get('state')
    min_size = request.args.get('min_size', 0, type=float)

    if state:
        raw_alerts = nws.get_alerts_for_state(state)
        alerts = [nws.parse_hail_info(a) for a in raw_alerts]
        # Filter for hail mentions
        alerts = [a for a in alerts if
                  a.get('hail_size_inches') or 'HAIL' in a.get('description', '').upper()]
    else:
        alerts = nws.get_hail_alerts(min_size=min_size)

    return jsonify({
        'count': len(alerts),
        'timestamp': datetime.utcnow().isoformat(),
        'filters': {'state': state, 'min_size': min_size},
        'alerts': alerts
    })


@bp.route('/alerts/all-severe')
def get_all_severe_alerts():
    """
    Get all severe weather alerts organized by type.

    Returns:
        Alerts grouped by: tornado_warnings, tornado_watches,
        severe_thunderstorm_warnings, severe_thunderstorm_watches
    """
    _, NWSAlerts, _, _ = get_weather_modules()
    nws = NWSAlerts()

    data = nws.get_all_severe_alerts()
    data['timestamp'] = datetime.utcnow().isoformat()

    return jsonify(data)


@bp.route('/alerts/point')
def get_alerts_for_point():
    """
    Get alerts affecting a specific location.

    Query params:
        lat: Latitude (required)
        lon: Longitude (required)

    Returns:
        List of alerts affecting this point
    """
    _, NWSAlerts, _, _ = get_weather_modules()
    nws = NWSAlerts()

    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon required'}), 400

    raw_alerts = nws.get_alerts_for_point(lat, lon)
    alerts = [nws.parse_hail_info(a) for a in raw_alerts]

    return jsonify({
        'point': {'lat': lat, 'lon': lon},
        'count': len(alerts),
        'alerts': alerts
    })


# ============================================================================
# Local Storm Reports (Iowa Mesonet)
# ============================================================================

@bp.route('/hail-reports')
def get_hail_reports():
    """
    Get recent hail reports from Local Storm Reports.

    Query params:
        hours: How many hours back (default 24, max 168)
        state: Filter by state code
        min_size: Minimum hail size in inches

    Returns:
        List of verified hail reports with sizes
    """
    _, _, IowaMesonet, _ = get_weather_modules()
    iem = IowaMesonet()

    hours = min(request.args.get('hours', 24, type=int), 168)
    state = request.args.get('state')
    min_size = request.args.get('min_size', 0, type=float)

    reports = iem.get_hail_reports(hours=hours, state=state, min_size=min_size)

    return jsonify({
        'count': len(reports),
        'hours': hours,
        'filters': {'state': state, 'min_size': min_size},
        'timestamp': datetime.utcnow().isoformat(),
        'reports': reports
    })


@bp.route('/hail-stats')
def get_hail_stats():
    """
    Get hail report statistics.

    Query params:
        hours: How many hours to analyze (default 24)

    Returns:
        Statistics including max size, state breakdown, top reports
    """
    _, _, IowaMesonet, _ = get_weather_modules()
    iem = IowaMesonet()

    hours = request.args.get('hours', 24, type=int)
    stats = iem.get_hail_stats(hours=hours)
    stats['timestamp'] = datetime.utcnow().isoformat()

    return jsonify(stats)


@bp.route('/tornado-reports')
def get_tornado_reports():
    """
    Get recent tornado reports.

    Query params:
        hours: How many hours back (default 24)
        state: Filter by state code

    Returns:
        List of tornado reports
    """
    _, _, IowaMesonet, _ = get_weather_modules()
    iem = IowaMesonet()

    hours = request.args.get('hours', 24, type=int)
    state = request.args.get('state')

    reports = iem.get_tornado_reports(hours=hours, state=state)

    return jsonify({
        'count': len(reports),
        'hours': hours,
        'state': state,
        'reports': reports
    })


@bp.route('/wind-reports')
def get_wind_reports():
    """
    Get recent damaging wind reports.

    Query params:
        hours: How many hours back (default 24)
        state: Filter by state code
        min_speed: Minimum wind speed in mph (default 58)

    Returns:
        List of wind reports
    """
    _, _, IowaMesonet, _ = get_weather_modules()
    iem = IowaMesonet()

    hours = request.args.get('hours', 24, type=int)
    state = request.args.get('state')
    min_speed = request.args.get('min_speed', 58, type=int)

    reports = iem.get_wind_reports(hours=hours, state=state, min_speed=min_speed)

    return jsonify({
        'count': len(reports),
        'hours': hours,
        'min_speed_mph': min_speed,
        'state': state,
        'reports': reports
    })


@bp.route('/all-reports')
def get_all_reports():
    """
    Get all severe weather reports.

    Query params:
        hours: How many hours back (default 24)
        state: Filter by state code

    Returns:
        All reports grouped by type
    """
    _, _, IowaMesonet, _ = get_weather_modules()
    iem = IowaMesonet()

    hours = request.args.get('hours', 24, type=int)
    state = request.args.get('state')

    data = iem.get_all_severe_reports(hours=hours, state=state)

    return jsonify(data)


# ============================================================================
# SPC Watches & Outlooks
# ============================================================================

@bp.route('/watches')
def get_watches():
    """
    Get active tornado and severe thunderstorm watches.

    Returns:
        List of current watches with details
    """
    _, _, _, StormPredictionCenter = get_weather_modules()
    spc = StormPredictionCenter()

    watches = spc.get_current_watches()

    # Separate by type
    tornado_watches = [w for w in watches if 'Tornado' in w.get('event', '')]
    svr_watches = [w for w in watches if 'Severe Thunderstorm' in w.get('event', '')]

    return jsonify({
        'total_count': len(watches),
        'tornado_watches': len(tornado_watches),
        'severe_thunderstorm_watches': len(svr_watches),
        'timestamp': datetime.utcnow().isoformat(),
        'watches': watches
    })


@bp.route('/outlooks')
def get_outlooks():
    """
    Get current SPC convective outlooks.

    Returns:
        Day 1-3 categorical outlooks plus Day 1 probabilistic
    """
    _, _, _, StormPredictionCenter = get_weather_modules()
    spc = StormPredictionCenter()

    outlooks = spc.get_all_outlooks()

    return jsonify(outlooks)


@bp.route('/outlook/day1')
def get_day1_outlook():
    """
    Get Day 1 convective outlook (categorical risk).

    Returns:
        GeoJSON with risk areas (TSTM, MRGL, SLGT, ENH, MDT, HIGH)
    """
    _, _, _, StormPredictionCenter = get_weather_modules()
    spc = StormPredictionCenter()

    outlook = spc.get_convective_outlook_day1()
    risk_areas = spc.parse_outlook_risk(outlook)

    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'risk_areas': risk_areas,
        'geojson': outlook
    })


@bp.route('/outlook/hail')
def get_hail_outlook():
    """
    Get Day 1 hail probability outlook.

    Returns:
        GeoJSON with probability areas for 1"+ hail
    """
    _, _, _, StormPredictionCenter = get_weather_modules()
    spc = StormPredictionCenter()

    outlook = spc.get_hail_outlook_day1()
    risk_areas = spc.parse_outlook_risk(outlook)

    return jsonify({
        'timestamp': datetime.utcnow().isoformat(),
        'risk_areas': risk_areas,
        'geojson': outlook
    })


@bp.route('/mcd')
def get_mesoscale_discussions():
    """
    Get recent mesoscale discussions.

    Query params:
        hours: How many hours back (default 24)

    Returns:
        List of mesoscale discussions
    """
    _, _, _, StormPredictionCenter = get_weather_modules()
    spc = StormPredictionCenter()

    hours = request.args.get('hours', 24, type=int)
    mcds = spc.get_mesoscale_discussions(hours=hours)

    return jsonify({
        'count': len(mcds),
        'hours': hours,
        'discussions': mcds
    })


# ============================================================================
# Hail Summary
# ============================================================================

@bp.route('/hail-summary')
def get_hail_summary():
    """
    Get a summary of current hail activity.

    Returns:
        Activity status, max sizes, state breakdown, top reports
    """
    get_monitor, _, _, _ = get_weather_modules()
    monitor = get_monitor()

    # Ensure we have recent data
    if monitor.state.last_update is None:
        monitor.fetch_all(report_hours=6)

    summary = monitor.get_hail_summary()
    summary['timestamp'] = datetime.utcnow().isoformat()

    return jsonify(summary)
