"""
Territory-based Alerts API
===========================
Allows users to define geographic territories and receive alerts
when hail storms hit their areas.
"""

import os
import json
import math
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from src.core.auth.decorators import login_required
from src.db.database import Database

territory_alerts_api_bp = Blueprint('territory_alerts_api', __name__, url_prefix='/api/territory-alerts')


def get_db():
    """Get database connection."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return Database(db_path)


def ensure_tables():
    """Ensure territory tables exist."""
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS user_territories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            center_lat REAL NOT NULL,
            center_lon REAL NOT NULL,
            radius_miles REAL DEFAULT 25,
            polygon_geojson TEXT,
            alert_on_hail BOOLEAN DEFAULT 1,
            alert_on_severe BOOLEAN DEFAULT 1,
            min_hail_size REAL DEFAULT 0.75,
            email_alerts BOOLEAN DEFAULT 1,
            sms_alerts BOOLEAN DEFAULT 0,
            push_alerts BOOLEAN DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS territory_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            territory_id INTEGER NOT NULL,
            hail_event_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            alert_message TEXT,
            is_read BOOLEAN DEFAULT 0,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            read_at TEXT,
            FOREIGN KEY (territory_id) REFERENCES user_territories(id),
            FOREIGN KEY (hail_event_id) REFERENCES hail_events(id)
        )
    """)


# =============================================================================
# TERRITORY MANAGEMENT
# =============================================================================

@territory_alerts_api_bp.route('/territories', methods=['GET'])
@login_required
def list_territories():
    """List all territories for the current user."""
    from flask import session

    user_id = session.get('user_id', 1)
    ensure_tables()
    db = get_db()

    territories = db.execute("""
        SELECT * FROM user_territories
        WHERE user_id = ? AND is_active = 1
        ORDER BY name
    """, (user_id,))

    return jsonify({
        'territories': [dict(t) for t in territories],
        'count': len(territories)
    })


@territory_alerts_api_bp.route('/territories', methods=['POST'])
@login_required
def create_territory():
    """Create a new territory."""
    from flask import session

    user_id = session.get('user_id', 1)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['name', 'center_lat', 'center_lon']
    for field in required:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400

    ensure_tables()
    db = get_db()

    # Insert territory
    result = db.execute("""
        INSERT INTO user_territories (
            user_id, name, center_lat, center_lon, radius_miles,
            polygon_geojson, alert_on_hail, alert_on_severe,
            min_hail_size, email_alerts, sms_alerts, push_alerts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data['name'],
        data['center_lat'],
        data['center_lon'],
        data.get('radius_miles', 25),
        json.dumps(data.get('polygon')) if data.get('polygon') else None,
        data.get('alert_on_hail', True),
        data.get('alert_on_severe', True),
        data.get('min_hail_size', 0.75),
        data.get('email_alerts', True),
        data.get('sms_alerts', False),
        data.get('push_alerts', True)
    ))

    return jsonify({
        'success': True,
        'territory_id': result if isinstance(result, int) else None,
        'message': 'Territory created successfully'
    }), 201


@territory_alerts_api_bp.route('/territories/<int:territory_id>', methods=['GET'])
@login_required
def get_territory(territory_id):
    """Get a specific territory."""
    from flask import session

    user_id = session.get('user_id', 1)
    db = get_db()

    territory = db.execute("""
        SELECT * FROM user_territories
        WHERE id = ? AND user_id = ?
    """, (territory_id, user_id))

    if not territory:
        return jsonify({'error': 'Territory not found'}), 404

    return jsonify({'territory': dict(territory[0])})


@territory_alerts_api_bp.route('/territories/<int:territory_id>', methods=['PUT'])
@login_required
def update_territory(territory_id):
    """Update a territory."""
    from flask import session

    user_id = session.get('user_id', 1)
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    db = get_db()

    # Build update query dynamically
    fields = []
    values = []

    allowed_fields = [
        'name', 'center_lat', 'center_lon', 'radius_miles',
        'alert_on_hail', 'alert_on_severe', 'min_hail_size',
        'email_alerts', 'sms_alerts', 'push_alerts', 'is_active'
    ]

    for field in allowed_fields:
        if field in data:
            fields.append(f"{field} = ?")
            values.append(data[field])

    if data.get('polygon'):
        fields.append("polygon_geojson = ?")
        values.append(json.dumps(data['polygon']))

    fields.append("updated_at = ?")
    values.append(datetime.now().isoformat())

    values.extend([territory_id, user_id])

    db.execute(f"""
        UPDATE user_territories
        SET {', '.join(fields)}
        WHERE id = ? AND user_id = ?
    """, tuple(values))

    return jsonify({
        'success': True,
        'message': 'Territory updated successfully'
    })


@territory_alerts_api_bp.route('/territories/<int:territory_id>', methods=['DELETE'])
@login_required
def delete_territory(territory_id):
    """Delete a territory (soft delete)."""
    from flask import session

    user_id = session.get('user_id', 1)
    db = get_db()

    db.execute("""
        UPDATE user_territories
        SET is_active = 0, updated_at = ?
        WHERE id = ? AND user_id = ?
    """, (datetime.now().isoformat(), territory_id, user_id))

    return jsonify({
        'success': True,
        'message': 'Territory deleted successfully'
    })


# =============================================================================
# TERRITORY ALERTS
# =============================================================================

@territory_alerts_api_bp.route('/alerts', methods=['GET'])
@login_required
def list_alerts():
    """List alerts for user's territories."""
    from flask import session

    user_id = session.get('user_id', 1)
    days = request.args.get('days', 7, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    ensure_tables()
    db = get_db()

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    query = """
        SELECT ta.*, ut.name as territory_name,
               he.event_name, he.event_date, he.max_hail_size,
               he.center_lat as event_lat, he.center_lon as event_lon,
               he.affected_locations
        FROM territory_alerts ta
        JOIN user_territories ut ON ta.territory_id = ut.id
        LEFT JOIN hail_events he ON ta.hail_event_id = he.id
        WHERE ut.user_id = ? AND ta.sent_at >= ?
    """

    if unread_only:
        query += " AND ta.is_read = 0"

    query += " ORDER BY ta.sent_at DESC LIMIT 100"

    alerts = db.execute(query, (user_id, cutoff_date))

    return jsonify({
        'alerts': [dict(a) for a in alerts],
        'count': len(alerts)
    })


@territory_alerts_api_bp.route('/alerts/<int:alert_id>/read', methods=['POST'])
@login_required
def mark_alert_read(alert_id):
    """Mark an alert as read."""
    db = get_db()

    db.execute("""
        UPDATE territory_alerts
        SET is_read = 1, read_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), alert_id))

    return jsonify({'success': True})


@territory_alerts_api_bp.route('/alerts/mark-all-read', methods=['POST'])
@login_required
def mark_all_alerts_read():
    """Mark all alerts as read for user."""
    from flask import session

    user_id = session.get('user_id', 1)
    db = get_db()

    db.execute("""
        UPDATE territory_alerts
        SET is_read = 1, read_at = ?
        WHERE territory_id IN (
            SELECT id FROM user_territories WHERE user_id = ?
        ) AND is_read = 0
    """, (datetime.now().isoformat(), user_id))

    return jsonify({'success': True, 'message': 'All alerts marked as read'})


# =============================================================================
# CHECK STORMS AGAINST TERRITORIES
# =============================================================================

def _haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in miles."""
    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


@territory_alerts_api_bp.route('/check-storms', methods=['POST'])
@login_required
def check_storms_in_territories():
    """
    Check if recent storms intersect with user's territories.
    Creates alerts for matching storms.
    """
    from flask import session

    user_id = session.get('user_id', 1)
    data = request.get_json() or {}
    hours_back = data.get('hours_back', 24)

    ensure_tables()
    db = get_db()

    # Get user's active territories
    territories = db.execute("""
        SELECT * FROM user_territories
        WHERE user_id = ? AND is_active = 1
    """, (user_id,))

    if not territories:
        return jsonify({
            'message': 'No territories configured',
            'alerts_created': 0
        })

    # Get recent hail events
    cutoff_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()

    events = db.execute("""
        SELECT * FROM hail_events
        WHERE created_at >= ? OR event_date >= ?
        ORDER BY event_date DESC
        LIMIT 100
    """, (cutoff_time, cutoff_time[:10]))

    alerts_created = 0
    matching_storms = []

    for territory in territories:
        t_lat = territory['center_lat']
        t_lon = territory['center_lon']
        t_radius = territory['radius_miles'] or 25
        min_hail = territory['min_hail_size'] or 0.75

        for event in events:
            e_lat = event.get('center_lat') or event.get('latitude')
            e_lon = event.get('center_lon') or event.get('longitude')
            hail_size = event.get('max_hail_size') or event.get('hail_size_inches') or 0

            if e_lat is None or e_lon is None:
                continue

            # Check if event is within territory radius
            distance = _haversine_distance(t_lat, t_lon, e_lat, e_lon)

            if distance <= t_radius and hail_size >= min_hail:
                # Check if alert already exists
                existing = db.execute("""
                    SELECT id FROM territory_alerts
                    WHERE territory_id = ? AND hail_event_id = ?
                """, (territory['id'], event['id']))

                if not existing:
                    # Create alert
                    alert_message = (
                        f"Hail storm detected in your territory '{territory['name']}'. "
                        f"Event: {event.get('event_name', 'Unknown')} "
                        f"with {hail_size}\" hail, {distance:.1f} miles from territory center."
                    )

                    db.execute("""
                        INSERT INTO territory_alerts (
                            territory_id, hail_event_id, alert_type, alert_message
                        ) VALUES (?, ?, ?, ?)
                    """, (territory['id'], event['id'], 'HAIL_IN_TERRITORY', alert_message))

                    alerts_created += 1
                    matching_storms.append({
                        'territory_id': territory['id'],
                        'territory_name': territory['name'],
                        'event_id': event['id'],
                        'event_name': event.get('event_name'),
                        'hail_size': hail_size,
                        'distance_miles': round(distance, 1)
                    })

    return jsonify({
        'success': True,
        'alerts_created': alerts_created,
        'matching_storms': matching_storms,
        'territories_checked': len(territories),
        'events_checked': len(events)
    })


@territory_alerts_api_bp.route('/stats', methods=['GET'])
@login_required
def get_territory_stats():
    """Get statistics for user's territories."""
    from flask import session

    user_id = session.get('user_id', 1)
    ensure_tables()
    db = get_db()

    # Count territories
    territories = db.execute("""
        SELECT COUNT(*) as count FROM user_territories
        WHERE user_id = ? AND is_active = 1
    """, (user_id,))

    # Count unread alerts
    unread = db.execute("""
        SELECT COUNT(*) as count FROM territory_alerts ta
        JOIN user_territories ut ON ta.territory_id = ut.id
        WHERE ut.user_id = ? AND ta.is_read = 0
    """, (user_id,))

    # Count alerts this week
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    week_alerts = db.execute("""
        SELECT COUNT(*) as count FROM territory_alerts ta
        JOIN user_territories ut ON ta.territory_id = ut.id
        WHERE ut.user_id = ? AND ta.sent_at >= ?
    """, (user_id, week_ago))

    return jsonify({
        'territories_count': territories[0]['count'] if territories else 0,
        'unread_alerts': unread[0]['count'] if unread else 0,
        'alerts_this_week': week_alerts[0]['count'] if week_alerts else 0
    })
