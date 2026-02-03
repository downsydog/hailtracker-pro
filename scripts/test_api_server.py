#!/usr/bin/env python3
"""
Simple test API server for HailTracker frontend testing.
Serves storm data from PostgreSQL and fleet data from SQLite.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before other imports

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import sqlite3
import json
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# PostgreSQL for storm data
PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "hailtracker_master",
    "user": "hailtracker",
    "password": "hailtracker_dev_2024"
}

# SQLite for fleet/CRM data (use OneDrive path - the active database)
SQLITE_DB = r'C:\Users\xtxll\OneDrive\Desktop\HailTracker\hailtracker-pro\data\hailtracker_crm.db'


def get_db():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(**PG_CONFIG)


def get_sqlite_db():
    """Get SQLite database connection."""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "hailtracker-test-api"})


# =============================================================================
# JWT AUTH ENDPOINTS (real authentication with PostgreSQL)
# =============================================================================

# Import and register auth blueprint
from auth.auth_routes import auth_bp
app.register_blueprint(auth_bp)

# Logout endpoint (simple, no state needed)
@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint."""
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route('/api/storms')
def get_storms():
    """Get storms with optional filters."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get query params
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        state = request.args.get('state')
        min_date = request.args.get('min_date')
        max_date = request.args.get('max_date')

        # Build query
        query = "SELECT * FROM storms WHERE 1=1"
        params = []

        if state:
            query += " AND state = %s"
            params.append(state)
        if min_date:
            query += " AND event_date >= %s"
            params.append(min_date)
        if max_date:
            query += " AND event_date <= %s"
            params.append(max_date)

        query += " ORDER BY event_date DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        storms = cursor.fetchall()

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM storms")
        total = cursor.fetchone()['count']

        conn.close()

        # Convert to serializable format
        result = []
        for storm in storms:
            item = dict(storm)
            if item.get('event_date'):
                item['event_date'] = item['event_date'].isoformat()
            if item.get('processed_at'):
                item['processed_at'] = item['processed_at'].isoformat()
            if item.get('expires_at'):
                item['expires_at'] = item['expires_at'].isoformat()
            if item.get('created_at'):
                item['created_at'] = item['created_at'].isoformat()
            result.append(item)

        return jsonify({
            "storms": result,
            "total": total,
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/storms/<int:storm_id>')
def get_storm(storm_id):
    """Get single storm with swath data."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get storm
        cursor.execute("SELECT * FROM storms WHERE id = %s", (storm_id,))
        storm = cursor.fetchone()

        if not storm:
            return jsonify({"error": "Storm not found"}), 404

        # Get swaths
        cursor.execute("SELECT * FROM swaths WHERE storm_id = %s", (storm_id,))
        swaths = cursor.fetchall()

        conn.close()

        # Convert to serializable format
        result = dict(storm)
        if result.get('event_date'):
            result['event_date'] = result['event_date'].isoformat()
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()

        swath_list = []
        for swath in swaths:
            s = dict(swath)
            if s.get('created_at'):
                s['created_at'] = s['created_at'].isoformat()
            # Parse polygon JSON if it's a string
            if s.get('polygon') and isinstance(s['polygon'], str):
                try:
                    s['polygon'] = json.loads(s['polygon'])
                except:
                    pass
            # Convert Decimal to float
            if s.get('center_lat'):
                s['center_lat'] = float(s['center_lat'])
            if s.get('center_lon'):
                s['center_lon'] = float(s['center_lon'])
            if s.get('max_hail_size'):
                s['max_hail_size'] = float(s['max_hail_size'])
            if s.get('area_sq_miles'):
                s['area_sq_miles'] = float(s['area_sq_miles'])
            swath_list.append(s)

        result['swaths'] = swath_list

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/swaths')
def get_swaths():
    """Get swaths with geospatial data for map display."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        limit = request.args.get('limit', 1000, type=int)
        min_hail_size = request.args.get('min_hail_size', type=float)

        query = """
            SELECT s.*, st.event_date, st.noaa_id
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.center_lat IS NOT NULL AND s.center_lon IS NOT NULL
        """
        params = []

        if min_hail_size:
            query += " AND s.max_hail_size >= %s"
            params.append(min_hail_size)

        query += " ORDER BY st.event_date DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        swaths = cursor.fetchall()
        conn.close()

        # Convert to GeoJSON-like format for map
        features = []
        for swath in swaths:
            feature = {
                "id": swath['id'],
                "storm_id": swath['storm_id'],
                "city": swath['city'],
                "state": swath['state'],
                "event_date": swath['event_date'].isoformat() if swath.get('event_date') else None,
                "max_hail_size": float(swath['max_hail_size']) if swath.get('max_hail_size') else None,
                "center_lat": float(swath['center_lat']) if swath.get('center_lat') else None,
                "center_lon": float(swath['center_lon']) if swath.get('center_lon') else None,
                "area_sq_miles": float(swath['area_sq_miles']) if swath.get('area_sq_miles') else None,
            }

            # Parse polygon
            if swath.get('polygon'):
                try:
                    if isinstance(swath['polygon'], str):
                        feature['polygon'] = json.loads(swath['polygon'])
                    else:
                        feature['polygon'] = swath['polygon']
                except:
                    pass

            features.append(feature)

        return jsonify({
            "swaths": features,
            "count": len(features)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Get storm statistics."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT
                COUNT(*) as total_storms,
                COUNT(DISTINCT state) as states_affected,
                MAX(event_date) as latest_storm,
                MIN(event_date) as earliest_storm
            FROM storms
        """)
        storm_stats = cursor.fetchone()

        cursor.execute("""
            SELECT
                COUNT(*) as total_swaths,
                AVG(max_hail_size) as avg_hail_size,
                MAX(max_hail_size) as max_hail_size,
                SUM(area_sq_miles) as total_area_sq_miles
            FROM swaths
            WHERE max_hail_size IS NOT NULL
        """)
        swath_stats = cursor.fetchone()

        conn.close()

        return jsonify({
            "storms": {
                "total": storm_stats['total_storms'],
                "states_affected": storm_stats['states_affected'],
                "latest": storm_stats['latest_storm'].isoformat() if storm_stats.get('latest_storm') else None,
                "earliest": storm_stats['earliest_storm'].isoformat() if storm_stats.get('earliest_storm') else None,
            },
            "swaths": {
                "total": swath_stats['total_swaths'],
                "avg_hail_size": float(swath_stats['avg_hail_size']) if swath_stats.get('avg_hail_size') else None,
                "max_hail_size": float(swath_stats['max_hail_size']) if swath_stats.get('max_hail_size') else None,
                "total_area_sq_miles": float(swath_stats['total_area_sq_miles']) if swath_stats.get('total_area_sq_miles') else None,
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/hail-events')
def get_hail_events():
    """Get hail events for the hail map (compatible with frontend API expectations)."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        limit = request.args.get('limit', 500, type=int)
        days = request.args.get('days', type=int)
        event_date = request.args.get('event_date')  # YYYY-MM-DD format for filtering

        query = """
            SELECT
                s.id,
                s.storm_id,
                st.noaa_id,
                st.event_date,
                s.center_lat,
                s.center_lon,
                s.max_hail_size,
                s.area_sq_miles as swath_area_sqmi,
                s.polygon as swath_polygon,
                s.city,
                s.state
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.center_lat IS NOT NULL
              AND s.center_lon IS NOT NULL
              AND s.max_hail_size IS NOT NULL
        """
        params = []

        # Filter by specific date if provided
        if event_date:
            query += " AND DATE(st.event_date) = %s"
            params.append(event_date)
        elif days:
            query += " AND st.event_date >= CURRENT_DATE - INTERVAL '%s days'"
            params.append(days)

        query += " ORDER BY st.event_date DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        events = cursor.fetchall()

        # Get stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_storms,
                COUNT(CASE WHEN event_date >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as active_storms,
                SUM(business_count) as total_estimated_vehicles
            FROM storms
        """)
        stats_row = cursor.fetchone()

        conn.close()

        result = []
        for e in events:
            # Determine severity based on hail size
            hail_size = float(e['max_hail_size']) if e.get('max_hail_size') else 0
            if hail_size >= 2.5:
                severity = 'CATASTROPHIC'
            elif hail_size >= 1.75:
                severity = 'SEVERE'
            elif hail_size >= 1.0:
                severity = 'MODERATE'
            else:
                severity = 'MINOR'

            event = {
                "id": e['id'],
                "event_name": e['city'] or f"Storm {e['noaa_id']}",
                "event_date": e['event_date'].isoformat() if e.get('event_date') else None,
                "center_lat": float(e['center_lat']) if e.get('center_lat') else None,
                "center_lon": float(e['center_lon']) if e.get('center_lon') else None,
                "latitude": float(e['center_lat']) if e.get('center_lat') else None,
                "longitude": float(e['center_lon']) if e.get('center_lon') else None,
                "max_hail_size": hail_size,
                "hail_size_inches": hail_size,
                "swath_area_sqmi": float(e['swath_area_sqmi']) if e.get('swath_area_sqmi') else None,
                "affected_area_sq_miles": float(e['swath_area_sqmi']) if e.get('swath_area_sqmi') else None,
                "state": e['state'],
                "city": e['city'],
                "severity": severity,
                "status": "ACTIVE" if e.get('event_date') else "CLOSED",
            }

            # Parse polygon
            if e.get('swath_polygon'):
                try:
                    if isinstance(e['swath_polygon'], str):
                        event['swath_polygon'] = json.loads(e['swath_polygon'])
                    else:
                        event['swath_polygon'] = e['swath_polygon']
                except:
                    pass

            result.append(event)

        return jsonify({
            "events": result,
            "count": len(result),
            "stats": {
                "period_days": days or 365,
                "total_storms": stats_row['total_storms'] if stats_row else 0,
                "active_storms": stats_row['active_storms'] if stats_row else 0,
                "total_estimated_vehicles": stats_row['total_estimated_vehicles'] or 0,
                "by_severity": {},
                "by_state": {}
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/hail-events/calendar')
def get_hail_calendar():
    """Get hail events calendar data in format expected by frontend."""
    try:
        year = request.args.get('year', type=int) or 2025
        month = request.args.get('month', type=int) or 1
        state = request.args.get('state')

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get all events for the month with details
        query = """
            SELECT
                s.id,
                s.city,
                s.state,
                s.max_hail_size,
                s.area_sq_miles,
                s.center_lat,
                s.center_lon,
                st.event_date
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.max_hail_size IS NOT NULL
              AND EXTRACT(YEAR FROM st.event_date) = %s
              AND EXTRACT(MONTH FROM st.event_date) = %s
        """
        params = [year, month]

        if state:
            query += " AND s.state = %s"
            params.append(state)

        query += " ORDER BY st.event_date, s.max_hail_size DESC"

        cursor.execute(query, params)
        events = cursor.fetchall()
        conn.close()

        # Group events by date
        days = {}
        total_events = 0
        max_hail_overall = 0
        severe_days = 0
        moderate_days = 0
        minor_days = 0

        for e in events:
            date_str = e['event_date'].strftime('%Y-%m-%d') if e.get('event_date') else None
            if not date_str:
                continue

            hail_size = float(e['max_hail_size']) if e.get('max_hail_size') else 0

            # Determine severity
            if hail_size >= 2.0:
                severity = "SEVERE"
            elif hail_size >= 1.0:
                severity = "MODERATE"
            else:
                severity = "MINOR"

            if date_str not in days:
                days[date_str] = {
                    "count": 0,
                    "max_hail_size": 0,
                    "max_severity": "MINOR",
                    "total_vehicles": 0,
                    "events": []
                }

            day = days[date_str]
            day["count"] += 1
            day["max_hail_size"] = max(day["max_hail_size"], hail_size)
            total_events += 1
            max_hail_overall = max(max_hail_overall, hail_size)

            # Update max severity
            if severity == "SEVERE":
                day["max_severity"] = "SEVERE"
            elif severity == "MODERATE" and day["max_severity"] != "SEVERE":
                day["max_severity"] = "MODERATE"

            # Add event details
            day["events"].append({
                "id": e['id'],
                "event_name": e['city'] or f"Storm {e['id']}",
                "event_date": date_str,
                "hail_size": hail_size,
                "severity": severity,
                "lat": float(e['center_lat']) if e.get('center_lat') else 0,
                "lon": float(e['center_lon']) if e.get('center_lon') else 0,
                "area_sqmi": float(e['area_sq_miles']) if e.get('area_sq_miles') else 0,
                "vehicles": 0
            })

        # Count severity days
        for day in days.values():
            if day["max_severity"] == "SEVERE":
                severe_days += 1
            elif day["max_severity"] == "MODERATE":
                moderate_days += 1
            else:
                minor_days += 1

        return jsonify({
            "data": {
                "year": year,
                "month": month,
                "days": days,
                "month_stats": {
                    "total_events": total_events,
                    "storm_days": len(days),
                    "max_hail_size": max_hail_overall,
                    "total_vehicles": 0,
                    "severe_days": severe_days,
                    "moderate_days": moderate_days,
                    "minor_days": minor_days
                }
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/hail-events/by-date')
def get_hail_events_by_date():
    """Get hail events for a specific date with swath polygons."""
    try:
        date = request.args.get('date')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        state = request.args.get('state')
        min_size = request.args.get('min_size', type=float)

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT
                s.id,
                s.storm_id,
                s.city,
                s.state,
                s.max_hail_size,
                s.area_sq_miles,
                s.center_lat,
                s.center_lon,
                s.polygon,
                st.event_date,
                st.noaa_id
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.center_lat IS NOT NULL
              AND s.center_lon IS NOT NULL
        """
        params = []

        if date:
            query += " AND DATE(st.event_date) = %s"
            params.append(date)
        elif start_date and end_date:
            query += " AND DATE(st.event_date) BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif start_date:
            query += " AND DATE(st.event_date) >= %s"
            params.append(start_date)

        if state:
            query += " AND s.state = %s"
            params.append(state)

        if min_size:
            query += " AND s.max_hail_size >= %s"
            params.append(min_size)

        query += " ORDER BY s.max_hail_size DESC LIMIT 500"

        cursor.execute(query, params)
        events = cursor.fetchall()
        conn.close()

        result = []
        for e in events:
            hail_size = float(e['max_hail_size']) if e.get('max_hail_size') else 0
            if hail_size >= 2.0:
                severity = "SEVERE"
            elif hail_size >= 1.0:
                severity = "MODERATE"
            else:
                severity = "MINOR"

            event = {
                "id": e['id'],
                "storm_id": e['storm_id'],
                "event_name": e['city'] or f"Storm {e['id']}",
                "city": e['city'],
                "state": e['state'],
                "event_date": e['event_date'].isoformat() if e.get('event_date') else None,
                "max_hail_size": hail_size,
                "hail_size_inches": hail_size,
                "severity": severity,
                "area_sq_miles": float(e['area_sq_miles']) if e.get('area_sq_miles') else None,
                "swath_area_sqmi": float(e['area_sq_miles']) if e.get('area_sq_miles') else None,
                "center_lat": float(e['center_lat']) if e.get('center_lat') else None,
                "center_lon": float(e['center_lon']) if e.get('center_lon') else None,
                "latitude": float(e['center_lat']) if e.get('center_lat') else None,
                "longitude": float(e['center_lon']) if e.get('center_lon') else None,
                "noaa_id": e['noaa_id']
            }

            # Parse polygon
            if e.get('polygon'):
                try:
                    if isinstance(e['polygon'], str):
                        event['swath_polygon'] = json.loads(e['polygon'])
                        event['polygon'] = json.loads(e['polygon'])
                    else:
                        event['swath_polygon'] = e['polygon']
                        event['polygon'] = e['polygon']
                except:
                    pass

            result.append(event)

        return jsonify({
            "events": result,
            "count": len(result),
            "query": {
                "date": date,
                "start_date": start_date,
                "end_date": end_date,
                "state": state,
                "min_size": min_size
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/hail-events/recent-significant')
def get_recent_significant():
    """Get recent significant hail events."""
    try:
        days = request.args.get('days', 90, type=int)
        min_size = request.args.get('min_size', 1.0, type=float)
        limit = request.args.get('limit', 30, type=int)

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT
                s.id,
                s.city,
                s.state,
                s.max_hail_size,
                s.area_sq_miles,
                s.center_lat,
                s.center_lon,
                st.event_date,
                st.noaa_id
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.max_hail_size >= %s
              AND st.event_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY st.event_date DESC, s.max_hail_size DESC
            LIMIT %s
        """, (min_size, days, limit))

        storms = cursor.fetchall()
        conn.close()

        result = []
        for storm in storms:
            result.append({
                "id": storm['id'],
                "city": storm['city'],
                "state": storm['state'],
                "max_hail_size": float(storm['max_hail_size']) if storm.get('max_hail_size') else None,
                "area_sq_miles": float(storm['area_sq_miles']) if storm.get('area_sq_miles') else None,
                "center_lat": float(storm['center_lat']) if storm.get('center_lat') else None,
                "center_lon": float(storm['center_lon']) if storm.get('center_lon') else None,
                "event_date": storm['event_date'].isoformat() if storm.get('event_date') else None,
                "noaa_id": storm['noaa_id']
            })

        return jsonify({
            "storms": result,
            "count": len(result),
            "days_back": days,
            "min_size": min_size
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/storm-cells/swaths')
def get_storm_cell_swaths():
    """Get storm cell swaths for the map."""
    try:
        limit = request.args.get('limit', 500, type=int)

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT
                s.id,
                s.storm_id,
                s.city,
                s.state,
                s.max_hail_size,
                s.area_sq_miles,
                s.center_lat,
                s.center_lon,
                s.polygon,
                st.event_date,
                st.noaa_id
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.center_lat IS NOT NULL
              AND s.center_lon IS NOT NULL
              AND s.max_hail_size IS NOT NULL
            ORDER BY st.event_date DESC
            LIMIT %s
        """, (limit,))

        swaths = cursor.fetchall()
        conn.close()

        # Convert to GeoJSON FeatureCollection format that frontend expects
        features = []
        for swath in swaths:
            hail_size = float(swath['max_hail_size']) if swath.get('max_hail_size') else 0
            if hail_size >= 2.0:
                severity = "SEVERE"
            elif hail_size >= 1.0:
                severity = "MODERATE"
            else:
                severity = "MINOR"

            # Parse polygon geometry
            geometry = None
            if swath.get('polygon'):
                try:
                    if isinstance(swath['polygon'], str):
                        geometry = json.loads(swath['polygon'])
                    else:
                        geometry = swath['polygon']
                except:
                    pass

            # Build GeoJSON Feature
            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "id": swath['id'],
                    "cell_id": swath['storm_id'],
                    "event_id": swath['id'],
                    "event_name": swath['city'],
                    "city": swath['city'],
                    "state": swath['state'],
                    "max_hail_size": hail_size,
                    "area_sq_miles": float(swath['area_sq_miles']) if swath.get('area_sq_miles') else None,
                    "center_lat": float(swath['center_lat']) if swath.get('center_lat') else None,
                    "center_lon": float(swath['center_lon']) if swath.get('center_lon') else None,
                    "event_date": swath['event_date'].isoformat() if swath.get('event_date') else None,
                    "noaa_id": swath['noaa_id'],
                    "severity": severity
                }
            }

            features.append(feature)

        # Return GeoJSON FeatureCollection format
        return jsonify({
            "type": "FeatureCollection",
            "features": features,
            "count": len(features)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/storm-cells/active')
def get_active_storm_cells():
    """Get active storm cells (mock - returns recent storms)."""
    try:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Return recent storms as "active" cells
        cursor.execute("""
            SELECT
                s.id,
                s.city,
                s.state,
                s.max_hail_size,
                s.center_lat,
                s.center_lon,
                st.event_date
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.center_lat IS NOT NULL
              AND s.center_lon IS NOT NULL
            ORDER BY st.event_date DESC
            LIMIT 50
        """)

        cells = cursor.fetchall()
        conn.close()

        result = []
        for cell in cells:
            result.append({
                "id": cell['id'],
                "name": cell['city'] or f"Cell {cell['id']}",
                "state": cell['state'],
                "lat": float(cell['center_lat']) if cell.get('center_lat') else None,
                "lon": float(cell['center_lon']) if cell.get('center_lon') else None,
                "max_hail_size": float(cell['max_hail_size']) if cell.get('max_hail_size') else None,
                "timestamp": cell['event_date'].isoformat() if cell.get('event_date') else None,
                "status": "ACTIVE"
            })

        return jsonify({
            "cells": result,
            "count": len(result)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/storm-monitor/radars')
def get_available_radars():
    """Get available radar stations (mock data)."""
    # Mock radar station data
    radars = [
        {"id": "KFWS", "name": "Fort Worth, TX", "lat": 32.5731, "lon": -97.3032, "status": "ACTIVE"},
        {"id": "KDFW", "name": "Dallas, TX", "lat": 32.7767, "lon": -96.7970, "status": "ACTIVE"},
        {"id": "KOUN", "name": "Norman, OK", "lat": 35.2226, "lon": -97.4395, "status": "ACTIVE"},
        {"id": "KTLX", "name": "Oklahoma City, OK", "lat": 35.3331, "lon": -97.2778, "status": "ACTIVE"},
        {"id": "KAMA", "name": "Amarillo, TX", "lat": 35.2334, "lon": -101.7092, "status": "ACTIVE"},
        {"id": "KLBB", "name": "Lubbock, TX", "lat": 33.6542, "lon": -101.8142, "status": "ACTIVE"},
        {"id": "KICT", "name": "Wichita, KS", "lat": 37.6547, "lon": -97.4428, "status": "ACTIVE"},
        {"id": "KDDC", "name": "Dodge City, KS", "lat": 37.7608, "lon": -99.9688, "status": "ACTIVE"},
    ]

    return jsonify({
        "radars": radars,
        "count": len(radars)
    })


@app.route('/api/hail-events/calendar/year')
def get_hail_calendar_year():
    """Get hail events calendar year summary."""
    try:
        year = request.args.get('year', type=int) or 2025

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get monthly summaries
        cursor.execute("""
            SELECT
                EXTRACT(MONTH FROM st.event_date) as month,
                COUNT(*) as total_events,
                MAX(s.max_hail_size) as max_hail_size,
                COUNT(DISTINCT DATE(st.event_date)) as storm_days
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE EXTRACT(YEAR FROM st.event_date) = %s
              AND s.max_hail_size IS NOT NULL
            GROUP BY EXTRACT(MONTH FROM st.event_date)
            ORDER BY month
        """, (year,))

        months_data = cursor.fetchall()
        conn.close()

        months = {}
        total_events = 0
        total_storm_days = 0
        max_hail_overall = 0
        peak_month = None
        peak_count = 0

        for m in months_data:
            month_num = int(m['month'])
            hail_size = float(m['max_hail_size']) if m.get('max_hail_size') else 0

            # Count severity
            severe_count = 1 if hail_size >= 2.0 else 0
            moderate_count = 1 if 1.0 <= hail_size < 2.0 else 0
            minor_count = 1 if hail_size < 1.0 else 0

            months[month_num] = {
                "storm_days": m['storm_days'],
                "total_events": m['total_events'],
                "max_hail_size": hail_size,
                "total_vehicles": 0,
                "severe_count": severe_count,
                "moderate_count": moderate_count,
                "minor_count": minor_count
            }

            total_events += m['total_events']
            total_storm_days += m['storm_days']
            max_hail_overall = max(max_hail_overall, hail_size)

            if m['total_events'] > peak_count:
                peak_count = m['total_events']
                peak_month = month_num

        return jsonify({
            "data": {
                "year": year,
                "months": months,
                "year_stats": {
                    "total_events": total_events,
                    "total_storm_days": total_storm_days,
                    "max_hail_size": max_hail_overall,
                    "peak_month": peak_month
                }
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Mock endpoints for other frontend API calls
@app.route('/api/jobs')
def get_jobs():
    """
    Get jobs for the current tenant.
    Tenant-scoped: filters by tenant_id from JWT.
    """
    from auth.tenant_context import get_current_tenant_id

    try:
        tenant_id = get_current_tenant_id()

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get jobs filtered by tenant_id
        cursor.execute("""
            SELECT * FROM jobs
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            LIMIT 100
        """, (tenant_id,))
        jobs = cursor.fetchall()

        # Get stats for this tenant
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                COALESCE(SUM(total_amount), 0) as total_revenue
            FROM jobs WHERE tenant_id = %s
        """, (tenant_id,))
        stats = cursor.fetchone()

        conn.close()

        return jsonify({
            "jobs": [dict(j) for j in jobs],
            "stats": {
                "total": stats['total'],
                "in_progress": stats['in_progress'],
                "total_revenue": float(stats['total_revenue'])
            },
            "total": stats['total'],
            "tenant_id": tenant_id
        })
    except Exception as e:
        return jsonify({"jobs": [], "stats": {"total": 0, "in_progress": 0, "total_revenue": 0}, "total": 0, "error": str(e)})

@app.route('/api/leads')
def get_leads():
    """
    Get leads for the current tenant.
    Tenant-scoped: filters by tenant_id from JWT.
    """
    from auth.tenant_context import get_current_tenant_id

    try:
        tenant_id = get_current_tenant_id()
        per_page = request.args.get('per_page', 100, type=int)
        page = request.args.get('page', 1, type=int)
        offset = (page - 1) * per_page

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get leads filtered by tenant_id
        cursor.execute("""
            SELECT * FROM leads
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (tenant_id, per_page, offset))
        leads = cursor.fetchall()

        # Get total count for this tenant
        cursor.execute("SELECT COUNT(*) FROM leads WHERE tenant_id = %s", (tenant_id,))
        total = cursor.fetchone()['count']

        conn.close()

        return jsonify({
            "leads": [dict(l) for l in leads],
            "total": total,
            "page": page,
            "per_page": per_page,
            "tenant_id": tenant_id
        })
    except Exception as e:
        return jsonify({"leads": [], "total": 0, "error": str(e)})

@app.route('/api/estimates')
def get_estimates():
    return jsonify({"estimates": [], "total": 0})

@app.route('/api/notifications')
def get_notifications():
    return jsonify({"notifications": [], "total": 0, "unread_count": 0})

@app.route('/api/customers')
def get_customers():
    return jsonify({"customers": [], "total": 0})


# =============================================================================
# SCHEDULE ENDPOINTS
# =============================================================================

@app.route('/api/schedule')
def get_schedule():
    """Get schedule slots for a date or date range."""
    date = request.args.get('date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    tech_id = request.args.get('tech_id', type=int)

    # Generate realistic schedule slots for the requested date
    from datetime import datetime, timedelta

    if date:
        target_date = datetime.strptime(date, '%Y-%m-%d')
    else:
        target_date = datetime.now()

    slots = []
    slot_id = 1

    # Generate time slots from 8 AM to 5 PM
    for hour in range(8, 17):
        for minute in [0, 30]:
            time_str = f"{hour:02d}:{minute:02d}"

            # Randomly assign status based on time
            if hour < 10:
                status = 'booked'
                job_num = f"JOB-{2025}{target_date.month:02d}{slot_id:04d}"
                customer = ['John Smith', 'Sarah Johnson', 'Mike Williams', 'Emily Davis'][slot_id % 4]
                vehicle = ['2022 Toyota Camry', '2021 Honda Accord', '2023 Ford F-150', '2020 Chevy Silverado'][slot_id % 4]
                tech = ['Mike Rodriguez', 'James Wilson', 'David Brown'][slot_id % 3]
            elif hour == 12:
                status = 'blocked'  # Lunch break
                job_num = None
                customer = None
                vehicle = None
                tech = None
            elif hour > 15:
                status = 'available'
                job_num = None
                customer = None
                vehicle = None
                tech = None
            else:
                # Mix of available and booked
                if slot_id % 3 == 0:
                    status = 'booked'
                    job_num = f"JOB-{2025}{target_date.month:02d}{slot_id:04d}"
                    customer = ['Robert Taylor', 'Jennifer Martinez', 'Chris Anderson'][slot_id % 3]
                    vehicle = ['2023 Tesla Model 3', '2022 BMW X5', '2021 Audi Q7'][slot_id % 3]
                    tech = ['Mike Rodriguez', 'James Wilson'][slot_id % 2]
                else:
                    status = 'available'
                    job_num = None
                    customer = None
                    vehicle = None
                    tech = None

            slot = {
                "id": slot_id,
                "date": target_date.strftime('%Y-%m-%d'),
                "time": time_str,
                "status": status,
                "duration_minutes": 30,
                "tech_id": (slot_id % 3) + 1 if tech else None,
                "tech_name": tech,
                "job_id": slot_id if job_num else None,
                "job_number": job_num,
                "customer_name": customer,
                "vehicle_name": vehicle
            }

            # Filter by tech_id if specified
            if tech_id and slot.get('tech_id') != tech_id:
                if status == 'booked':
                    slot_id += 1
                    continue

            slots.append(slot)
            slot_id += 1

    return jsonify({"slots": slots})


@app.route('/api/schedule/available')
def get_available_slots():
    """Get available slots for a specific date and appointment type."""
    date = request.args.get('date')
    appointment_type = request.args.get('appointment_type', 'inspection')

    from datetime import datetime

    if date:
        target_date = datetime.strptime(date, '%Y-%m-%d')
    else:
        target_date = datetime.now()

    # Generate available slots
    slots = []
    slot_id = 1

    for hour in range(9, 16):  # 9 AM to 4 PM for appointments
        if hour != 12:  # Skip lunch
            for minute in [0, 30]:
                # Only show some as available
                if slot_id % 2 == 0:
                    slots.append({
                        "id": slot_id,
                        "date": target_date.strftime('%Y-%m-%d'),
                        "time": f"{hour:02d}:{minute:02d}",
                        "status": "available",
                        "duration_minutes": 30 if appointment_type == 'inspection' else 60,
                        "tech_id": None,
                        "tech_name": None
                    })
                slot_id += 1

    return jsonify({"slots": slots})


@app.route('/api/schedule/slots/<int:slot_id>/book', methods=['POST'])
def book_slot(slot_id):
    """Book a schedule slot."""
    data = request.get_json() or {}
    job_id = data.get('job_id')

    return jsonify({
        "id": slot_id,
        "date": "2025-01-15",
        "time": "10:00",
        "status": "booked",
        "duration_minutes": 30,
        "job_id": job_id,
        "job_number": f"JOB-{job_id}",
        "tech_id": 1,
        "tech_name": "Mike Rodriguez"
    })


@app.route('/api/schedule/tokens')
def get_scheduling_tokens():
    """Get scheduling tokens."""
    return jsonify({"tokens": []})


@app.route('/api/schedule/tokens', methods=['POST'])
def create_scheduling_token():
    """Create a new scheduling token."""
    data = request.get_json() or {}
    return jsonify({
        "id": 1,
        "token": "abc123",
        "appointment_type": data.get('appointment_type', 'inspection'),
        "expires_at": "2025-02-01T00:00:00Z",
        "max_uses": data.get('max_uses', 10),
        "uses": 0,
        "is_active": True,
        "created_at": "2025-01-15T12:00:00Z"
    })


@app.route('/api/schedule/tokens/<int:token_id>', methods=['DELETE'])
def revoke_scheduling_token(token_id):
    """Revoke a scheduling token."""
    return jsonify({"success": True})


# =============================================================================
# FLEET LOCATIONS ENDPOINTS (Using real SQLite data)
# =============================================================================

def get_swath_bounds(event_ids):
    """Get bounding box from swath polygons for given event IDs."""
    if not event_ids:
        return None

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    placeholders = ','.join(['%s'] * len(event_ids))
    cursor.execute(f"""
        SELECT
            MIN(s.center_lat) - 0.5 as min_lat,
            MAX(s.center_lat) + 0.5 as max_lat,
            MIN(s.center_lon) - 0.5 as min_lon,
            MAX(s.center_lon) + 0.5 as max_lon
        FROM swaths s
        WHERE s.id IN ({placeholders})
    """, event_ids)

    result = cursor.fetchone()
    conn.close()

    if result and result['min_lat']:
        return {
            'min_lat': float(result['min_lat']),
            'max_lat': float(result['max_lat']),
            'min_lon': float(result['min_lon']),
            'max_lon': float(result['max_lon'])
        }
    return None


def query_fleet_locations(bounds=None, limit=500):
    """Query fleet locations from SQLite within optional bounds."""
    try:
        conn = get_sqlite_db()

        if bounds:
            query = """
                SELECT id, name, category, subcategory, address, city, state, zip_code,
                       lat, lon, phone, email, website, estimated_vehicles,
                       vehicle_confidence, data_source, worked_before
                FROM fleet_locations
                WHERE lat BETWEEN ? AND ?
                  AND lon BETWEEN ? AND ?
                  AND lat IS NOT NULL
                  AND lon IS NOT NULL
                ORDER BY estimated_vehicles DESC
                LIMIT ?
            """
            cursor = conn.execute(query, (
                bounds['min_lat'], bounds['max_lat'],
                bounds['min_lon'], bounds['max_lon'],
                limit
            ))
        else:
            query = """
                SELECT id, name, category, subcategory, address, city, state, zip_code,
                       lat, lon, phone, email, website, estimated_vehicles,
                       vehicle_confidence, data_source, worked_before
                FROM fleet_locations
                WHERE lat IS NOT NULL AND lon IS NOT NULL
                ORDER BY estimated_vehicles DESC
                LIMIT ?
            """
            cursor = conn.execute(query, (limit,))

        rows = cursor.fetchall()
        conn.close()

        businesses = []
        for row in rows:
            businesses.append({
                "id": row['id'],
                "name": row['name'] or "Unknown Business",
                "category": row['category'] or "other",
                "subcategory": row['subcategory'] or "",
                "address": row['address'] or "",
                "city": row['city'] or "",
                "state": row['state'] or "",
                "zip": row['zip_code'] or "",
                "phone": row['phone'] or "",
                "email": row['email'] or "",
                "website": row['website'] or "",
                "estimated_vehicles": row['estimated_vehicles'] or 0,
                "tier": 1 if (row['estimated_vehicles'] or 0) >= 100 else 2 if (row['estimated_vehicles'] or 0) >= 50 else 3,
                "latitude": row['lat'],
                "longitude": row['lon'],
                "source": row['data_source'] or "database",
                "added_to_crm": bool(row['worked_before'])
            })

        return businesses
    except Exception as e:
        print(f"Error querying fleet locations: {e}")
        return []


@app.route('/api/fleet-locations/tile-discover', methods=['POST'])
def tile_discover():
    """
    REAL tile-based business discovery using all 6 APIs.
    Uses TileBasedDiscovery service for actual API calls.
    """
    try:
        from src.business.tile_discovery import TileBasedDiscovery

        data = request.get_json() or {}
        event_ids = data.get('event_ids', [])
        tile_size = data.get('tile_size_miles', 0.5)
        sources = data.get('sources', ['osm', 'yelp', 'foursquare', 'here', 'tomtom', 'google'])
        force_refresh = data.get('force_refresh', False)
        max_tiles = data.get('max_tiles', 200)

        if not event_ids:
            return jsonify({'error': 'event_ids is required'}), 400

        # Validate sources
        valid_sources = ['osm', 'yelp', 'foursquare', 'here', 'tomtom', 'google', 'bbb', 'yellowpages']
        sources = [s for s in sources if s in valid_sources]
        if not sources:
            sources = ['osm']

        print(f"[TILE-DISCOVER] Events: {len(event_ids)}, Sources: {sources}, MaxTiles: {max_tiles}")

        # Load swath polygons from database
        swaths = []
        conn = get_sqlite_db()
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
                print(f"Skip invalid swath for event {row['id']}: {e}")

        conn.close()

        if not swaths:
            return jsonify({
                'success': True,
                'businesses': [],
                'stats': {'total_found': 0, 'message': 'No valid swath polygons found'},
            })

        print(f"[TILE-DISCOVER] Found {len(swaths)} swaths")

        # Use REAL tile-based discovery with actual API calls
        discovery = TileBasedDiscovery(tile_size_miles=tile_size)

        if force_refresh:
            discovery.clear_tile_cache()

        result = discovery.discover_for_swaths(
            swaths=swaths,
            sources=sources,
            use_cache=not force_refresh,
            max_tiles=max_tiles
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

        print(f"[TILE-DISCOVER] Complete: {len(businesses)} businesses from {result.get('stats', {}).get('by_source', {})}")

        return jsonify({
            'success': True,
            'businesses': businesses,
            'stats': result.get('stats', {}),
            'tile_stats': result.get('tile_stats', {}),
        })

    except Exception as e:
        import traceback
        print(f"[TILE-DISCOVER] Error: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e), "businesses": []}), 500


@app.route('/api/fleet-locations/fast-discover', methods=['POST'])
def fast_discover():
    """Fast hybrid business discovery."""
    try:
        data = request.get_json() or {}
        event_ids = data.get('event_ids', [])

        bounds = get_swath_bounds(event_ids) if event_ids else None
        businesses = query_fleet_locations(bounds, limit=200)

        by_category = {}
        by_source = {}
        total_vehicles = 0
        for b in businesses:
            cat = b.get('category', 'other')
            src = b.get('source', 'database')
            by_category[cat] = by_category.get(cat, 0) + 1
            by_source[src] = by_source.get(src, 0) + 1
            total_vehicles += b.get('estimated_vehicles', 0)

        return jsonify({
            "success": True,
            "businesses": businesses,
            "stats": {
                "swaths_total": len(event_ids),
                "swaths_from_cache": 0,
                "osm_queries": 1,
                "osm_found": len(businesses),
                "total_found": len(businesses),
                "duplicates_removed": 0,
                "total_vehicles": total_vehicles,
                "by_category": by_category,
                "by_source": by_source
            },
            "timing": {
                "total_seconds": 0.5,
                "osm_seconds": 0.3,
                "city_seconds": 0.2
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "businesses": []}), 500


@app.route('/api/fleet-locations/smart-scrape-swaths', methods=['POST'])
def smart_scrape_swaths():
    """Smart swath-based business discovery."""
    try:
        data = request.get_json() or {}
        event_ids = data.get('event_ids', [])

        bounds = get_swath_bounds(event_ids) if event_ids else None
        businesses = query_fleet_locations(bounds, limit=300)

        by_category = {}
        by_source = {}
        total_vehicles = 0
        for b in businesses:
            cat = b.get('category', 'other')
            src = b.get('source', 'database')
            by_category[cat] = by_category.get(cat, 0) + 1
            by_source[src] = by_source.get(src, 0) + 1
            total_vehicles += b.get('estimated_vehicles', 0)

        return jsonify({
            "success": True,
            "businesses": businesses,
            "stats": {
                "total_found": len(businesses),
                "cached": False,
                "from_cache": 0,
                "newly_scraped": len(businesses),
                "osm_found": by_source.get('osm', 0),
                "foursquare_found": 0,
                "yelp_found": 0,
                "geocoded": len(businesses),
                "duplicates_removed": 0,
                "final_in_swath": len(businesses),
                "by_category": by_category,
                "by_source": by_source,
                "total_vehicles": total_vehicles,
                "events_processed": len(event_ids)
            },
            "api_status": {
                "foursquare": {"configured": False, "free_tier": "1000/day"},
                "yelp": {"configured": False, "free_tier": "5000/day"},
                "osm": {"configured": True, "free_tier": "unlimited"}
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "businesses": []}), 500


@app.route('/api/fleet-locations')
def get_fleet_locations():
    """Get fleet locations with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        category = request.args.get('category')
        min_vehicles = request.args.get('min_vehicles', type=int)
        search = request.args.get('search')

        conn = get_sqlite_db()

        # Build query
        query = """
            SELECT id, name, category, subcategory, address, city, state, zip_code,
                   lat, lon, phone, email, website, estimated_vehicles,
                   vehicle_confidence, data_source
            FROM fleet_locations
            WHERE lat IS NOT NULL AND lon IS NOT NULL
        """
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)
        if min_vehicles:
            query += " AND estimated_vehicles >= ?"
            params.append(min_vehicles)
        if search:
            query += " AND (name LIKE ? OR city LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])

        # Get total count
        count_query = query.replace(
            "SELECT id, name, category, subcategory, address, city, state, zip_code, lat, lon, phone, email, website, estimated_vehicles, vehicle_confidence, data_source",
            "SELECT COUNT(*)"
        )
        total = conn.execute(count_query, params).fetchone()[0]

        # Add pagination
        query += " ORDER BY estimated_vehicles DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])

        rows = conn.execute(query, params).fetchall()
        conn.close()

        locations = []
        for row in rows:
            locations.append({
                "id": row['id'],
                "name": row['name'],
                "category": row['category'],
                "subcategory": row['subcategory'],
                "address": row['address'],
                "city": row['city'],
                "state": row['state'],
                "zip_code": row['zip_code'],
                "lat": row['lat'],
                "lon": row['lon'],
                "phone": row['phone'],
                "email": row['email'],
                "website": row['website'],
                "estimated_vehicles": row['estimated_vehicles'],
                "vehicle_confidence": row['vehicle_confidence'],
                "data_source": row['data_source']
            })

        return jsonify({
            "locations": locations,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/fleet-locations/categories')
def get_fleet_categories():
    """Get fleet location categories from SQLite."""
    try:
        conn = get_sqlite_db()
        cursor = conn.execute("""
            SELECT
                category,
                COUNT(*) as location_count,
                SUM(COALESCE(estimated_vehicles, 0)) as total_vehicles,
                AVG(COALESCE(estimated_vehicles, 0)) as avg_vehicles
            FROM fleet_locations
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY total_vehicles DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        categories = []
        for row in rows:
            display_name = row['category'].replace('_', ' ').title() if row['category'] else 'Other'
            categories.append({
                "category": row['category'],
                "display_name": display_name,
                "location_count": row['location_count'],
                "total_vehicles": row['total_vehicles'] or 0,
                "avg_vehicles": round(row['avg_vehicles'] or 0, 1),
                "potential_revenue": (row['total_vehicles'] or 0) * 2000  # $2000 avg per vehicle
            })

        return jsonify({"categories": categories})
    except Exception as e:
        return jsonify({"error": str(e), "categories": []}), 500


@app.route('/api/fleet-locations/stats')
def get_fleet_stats():
    """Get fleet location stats from SQLite."""
    try:
        conn = get_sqlite_db()

        # Get totals
        totals = conn.execute("""
            SELECT
                COUNT(*) as total_locations,
                SUM(COALESCE(estimated_vehicles, 0)) as total_vehicles,
                COUNT(DISTINCT category) as categories
            FROM fleet_locations
        """).fetchone()

        # Get top categories
        top_cats = conn.execute("""
            SELECT
                category,
                COUNT(*) as count,
                SUM(COALESCE(estimated_vehicles, 0)) as vehicles
            FROM fleet_locations
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY vehicles DESC
            LIMIT 5
        """).fetchall()

        conn.close()

        top_categories = [
            {"category": r['category'], "count": r['count'], "vehicles": r['vehicles'] or 0}
            for r in top_cats
        ]

        return jsonify({
            "total_locations": totals['total_locations'],
            "total_vehicles": totals['total_vehicles'] or 0,
            "categories": totals['categories'],
            "potential_revenue": (totals['total_vehicles'] or 0) * 2000,
            "top_categories": top_categories
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/fleet-leads')
def get_fleet_leads():
    """Get fleet leads from SQLite."""
    try:
        conn = get_sqlite_db()
        cursor = conn.execute("""
            SELECT * FROM fleet_leads
            ORDER BY created_at DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        conn.close()

        leads = [dict(row) for row in rows]
        return jsonify({
            "leads": leads,
            "count": len(leads)
        })
    except Exception as e:
        return jsonify({"leads": [], "count": 0})


@app.route('/api/fleet-leads/stats')
def get_fleet_leads_stats():
    """Get fleet leads stats from SQLite."""
    try:
        conn = get_sqlite_db()

        # Get stats by status
        by_status = conn.execute("""
            SELECT
                status,
                COUNT(*) as count,
                SUM(COALESCE(estimated_vehicles, 0)) as vehicles,
                SUM(COALESCE(quote_amount, 0)) as value
            FROM fleet_leads
            GROUP BY status
        """).fetchall()

        # Get by city
        by_city = conn.execute("""
            SELECT
                city, state,
                COUNT(*) as count,
                SUM(COALESCE(estimated_vehicles, 0)) as vehicles
            FROM fleet_leads
            GROUP BY city, state
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        conn.close()

        return jsonify({
            "by_status": [{"status": r['status'], "count": r['count'], "vehicles": r['vehicles'] or 0, "value": r['value'] or 0} for r in by_status],
            "pipeline": {"count": sum(r['count'] for r in by_status if r['status'] not in ('WON', 'LOST')), "vehicles": 0, "value": 0},
            "won": {"count": sum(r['count'] for r in by_status if r['status'] == 'WON'), "value": 0},
            "hail_affected": {"count": 0, "vehicles": 0},
            "followups_due": 0,
            "recent_activity": 0,
            "by_city": [{"city": r['city'], "state": r['state'], "count": r['count'], "vehicles": r['vehicles'] or 0} for r in by_city]
        })
    except Exception as e:
        return jsonify({
            "by_status": [],
            "pipeline": {"count": 0, "vehicles": 0, "value": 0},
            "won": {"count": 0, "value": 0},
            "hail_affected": {"count": 0, "vehicles": 0},
            "followups_due": 0,
            "recent_activity": 0,
            "by_city": []
        })


@app.route('/api/hail-events/recent-significant')
def get_recent_significant_v2():
    """Get recent significant storms for the sidebar."""
    try:
        days = request.args.get('days', 90, type=int)
        min_size = request.args.get('min_size', 1.0, type=float)
        limit = request.args.get('limit', 30, type=int)

        conn = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT
                DATE(st.event_date) as date,
                COUNT(*) as total_events,
                MAX(s.max_hail_size) as max_hail_size,
                array_agg(DISTINCT s.state) as states_affected,
                array_agg(DISTINCT s.city) as major_cities,
                SUM(COALESCE(s.area_sq_miles, 0)) as total_area_sq_miles
            FROM swaths s
            JOIN storms st ON s.storm_id = st.id
            WHERE s.max_hail_size >= %s
              AND st.event_date >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(st.event_date)
            ORDER BY DATE(st.event_date) DESC
            LIMIT %s
        """, (min_size, days, limit))

        storms = cursor.fetchall()
        conn.close()

        result = []
        for storm in storms:
            states = storm['states_affected'] or []
            cities = storm['major_cities'] or []
            result.append({
                "date": storm['date'].isoformat() if storm.get('date') else None,
                "total_events": storm['total_events'],
                "max_hail_size": float(storm['max_hail_size']) if storm.get('max_hail_size') else 0,
                "states_affected": [s for s in states if s],
                "major_cities": [c for c in cities if c][:5],
                "total_area_sq_miles": float(storm['total_area_sq_miles']) if storm.get('total_area_sq_miles') else 0,
                "display_name": f"{cities[0] if cities else 'Storm'} - {storm['date'].strftime('%b %d, %Y') if storm.get('date') else ''}"
            })

        return jsonify({
            "storms": result,
            "count": len(result),
            "days_back": days,
            "min_size": min_size
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# REAL SCRAPING ENDPOINTS (Using SwathDiscoveryService with APIs)
# =============================================================================

# Add project root to path for imports
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import the real discovery service (lazy import to avoid startup errors)
_discovery_service = None

def get_discovery_service():
    """Get or create the SwathDiscoveryService instance."""
    global _discovery_service
    if _discovery_service is None:
        try:
            from src.business.swath_discovery import SwathDiscoveryService
            _discovery_service = SwathDiscoveryService(
                crm_db_path=SQLITE_DB
            )
            print("[SwathDiscoveryService] Initialized successfully")
        except Exception as e:
            print(f"[SwathDiscoveryService] Failed to initialize: {e}")
            return None
    return _discovery_service


@app.route('/api/fleet-locations/real-scrape-swaths', methods=['POST'])
def real_scrape_swaths():
    """
    REAL swath-based business discovery using multiple data sources.

    Uses:
    - OSM Overpass API (free, unlimited)
    - Foursquare Places API (100k/month)
    - Yelp Fusion API (5k/day)
    - HERE Places API (250k/month)
    - TomTom Search API (2.5k/day)
    - Google Places API ($200/month credit)
    - Yellow Pages (web scraping)
    - BBB (web scraping)

    Request body:
    {
        "event_ids": [1, 2, 3],           // Required: swath event IDs to search
        "sources": ["osm", "foursquare"], // Optional: which sources to use
        "buffer_miles": 1.0,              // Optional: buffer around swaths
        "force_refresh": false            // Optional: ignore cache
    }
    """
    try:
        data = request.get_json() or {}
        event_ids = data.get('event_ids', [])
        sources = data.get('sources')  # None means use defaults
        buffer_miles = data.get('buffer_miles', 1.0)
        force_refresh = data.get('force_refresh', False)

        if not event_ids:
            return jsonify({
                "success": False,
                "error": "event_ids required",
                "businesses": []
            }), 400

        # Get the discovery service
        service = get_discovery_service()
        if service is None:
            return jsonify({
                "success": False,
                "error": "Discovery service not available",
                "businesses": []
            }), 500

        # Run the real discovery
        print(f"[RealScrape] Starting discovery for {len(event_ids)} events, sources={sources}")

        result = service.discover_for_events(
            event_ids=event_ids,
            buffer_miles=buffer_miles,
            force_refresh=force_refresh,
            sources=sources
        )

        businesses = result.get('businesses', [])
        stats = result.get('stats', {})

        print(f"[RealScrape] Found {len(businesses)} businesses")
        print(f"[RealScrape] Stats: {stats}")

        # Format response for frontend
        formatted_businesses = []
        for b in businesses:
            formatted_businesses.append({
                "id": b.get('osm_id') or f"biz_{len(formatted_businesses)}",
                "name": b.get('name', 'Unknown'),
                "category": b.get('category', 'other'),
                "address": b.get('address', ''),
                "city": b.get('city', ''),
                "state": b.get('state', ''),
                "zip": b.get('zip', ''),
                "phone": b.get('phone', ''),
                "website": b.get('website', ''),
                "email": b.get('email', ''),
                "latitude": b.get('latitude'),
                "longitude": b.get('longitude'),
                "estimated_vehicles": b.get('estimated_vehicles', 10),
                "tier": b.get('tier', 3),
                "source": b.get('source', 'unknown'),
                "added_to_crm": b.get('added_to_crm', False),
                "event_id": b.get('event_id'),
                "hail_date": b.get('hail_date'),
                "hail_size": b.get('hail_size')
            })

        return jsonify({
            "success": True,
            "businesses": formatted_businesses,
            "stats": stats,
            "api_status": service.get_api_status() if service else {}
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "businesses": []
        }), 500


@app.route('/api/fleet-locations/api-status')
def get_api_status():
    """Get the status of all configured APIs."""
    service = get_discovery_service()
    if service is None:
        return jsonify({
            "success": False,
            "error": "Discovery service not available",
            "apis": {}
        }), 500

    return jsonify({
        "success": True,
        "apis": service.get_api_status()
    })


@app.route('/api/fleet-locations/search-osm', methods=['POST'])
def search_osm_directly():
    """
    Direct OSM search for testing.

    Request body:
    {
        "lat": 35.4676,
        "lon": -97.5164,
        "radius_miles": 5.0
    }
    """
    try:
        data = request.get_json() or {}
        lat = data.get('lat')
        lon = data.get('lon')
        radius_miles = data.get('radius_miles', 5.0)

        if lat is None or lon is None:
            return jsonify({
                "success": False,
                "error": "lat and lon required",
                "businesses": []
            }), 400

        service = get_discovery_service()
        if service is None:
            return jsonify({
                "success": False,
                "error": "Discovery service not available",
                "businesses": []
            }), 500

        businesses = service.search_osm_comprehensive(lat, lon, radius_miles)

        return jsonify({
            "success": True,
            "businesses": businesses,
            "count": len(businesses),
            "search": {
                "lat": lat,
                "lon": lon,
                "radius_miles": radius_miles
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "businesses": []
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("HailTracker Test API Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET  /api/health                    - Health check")
    print("  GET  /api/stats                     - Storm statistics")
    print("  GET  /api/storms                    - List storms")
    print("  GET  /api/storms/<id>               - Get storm details")
    print("  GET  /api/swaths                    - Get swaths for map")
    print("  GET  /api/hail-events               - Get hail events for map")
    print("\n  FLEET DISCOVERY (Real Scraping):")
    print("  POST /api/fleet-locations/real-scrape-swaths  - REAL multi-source discovery")
    print("  GET  /api/fleet-locations/api-status          - Check API keys status")
    print("  POST /api/fleet-locations/search-osm          - Direct OSM search")
    print("\nStarting server on http://localhost:5000")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)
