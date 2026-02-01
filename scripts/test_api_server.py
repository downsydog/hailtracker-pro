#!/usr/bin/env python3
"""
Simple test API server for HailTracker frontend testing.
Serves storm data from PostgreSQL.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "hailtracker_master",
    "user": "hailtracker",
    "password": "hailtracker_dev_2024"
}


def get_db():
    """Get database connection."""
    return psycopg2.connect(**PG_CONFIG)


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "hailtracker-test-api"})


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

        if days:
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

        result = []
        for swath in swaths:
            hail_size = float(swath['max_hail_size']) if swath.get('max_hail_size') else 0
            if hail_size >= 2.0:
                severity = "SEVERE"
            elif hail_size >= 1.0:
                severity = "MODERATE"
            else:
                severity = "MINOR"

            item = {
                "id": swath['id'],
                "storm_id": swath['storm_id'],
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

            # Parse polygon
            if swath.get('polygon'):
                try:
                    if isinstance(swath['polygon'], str):
                        item['polygon'] = json.loads(swath['polygon'])
                    else:
                        item['polygon'] = swath['polygon']
                except:
                    pass

            result.append(item)

        return jsonify({
            "swaths": result,
            "count": len(result)
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
    return jsonify({"jobs": [], "stats": {"total": 0, "in_progress": 0, "total_revenue": 0}, "total": 0})

@app.route('/api/leads')
def get_leads():
    return jsonify({"leads": [], "total": 0})

@app.route('/api/estimates')
def get_estimates():
    return jsonify({"estimates": [], "total": 0})

@app.route('/api/notifications')
def get_notifications():
    return jsonify({"notifications": [], "total": 0, "unread_count": 0})

@app.route('/api/customers')
def get_customers():
    return jsonify({"customers": [], "total": 0})


if __name__ == '__main__':
    print("=" * 60)
    print("HailTracker Test API Server")
    print("=" * 60)
    print("\nEndpoints:")
    print("  GET /api/health       - Health check")
    print("  GET /api/stats        - Storm statistics")
    print("  GET /api/storms       - List storms")
    print("  GET /api/storms/<id>  - Get storm details")
    print("  GET /api/swaths       - Get swaths for map")
    print("  GET /api/hail-events  - Get hail events for map")
    print("\nStarting server on http://localhost:5000")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)
