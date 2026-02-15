"""
Event Persister — Bridge between in-memory StormCellTracker and hail_events DB.

Reads events + swaths from the tracker and upserts them into the
hail_events table so the calendar, map, and historical queries see them.

Usage:
    from src.radar.event_persister import persist_tracker_events

    # Called after each scan cycle in StormMonitor
    persist_tracker_events(tracker, db_path='data/hailtracker_crm.db')
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def persist_tracker_events(
    tracker,
    db_path: str = 'data/hailtracker_crm.db',
    lookback_minutes: int = 360,
    join_distance_km: float = 25.0,
    buffer_km: float = 3.0,
):
    """
    Read events from the tracker and upsert them into hail_events.

    Uses event_name = tracker event_id as the unique key.
    Events are INSERT OR REPLACE'd so repeated calls are safe.

    Args:
        tracker: StormCellTracker instance
        db_path: Path to the CRM SQLite database
        lookback_minutes: How far back to look for events
        join_distance_km: Cell join distance for event clustering
        buffer_km: Swath buffer for polygon generation
    """
    try:
        events = tracker.get_events(
            lookback_minutes=lookback_minutes,
            join_distance_km=join_distance_km,
        )
    except Exception as e:
        logger.warning("persist_tracker_events: get_events failed: %s", e)
        return 0

    if not events:
        return 0

    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')

    persisted = 0

    for ev in events:
        try:
            # Build swath polygon GeoJSON
            swath_json = None
            swath_method = 'tracker'
            swath_area_sqmi = 0.0

            try:
                merged = tracker.create_event_merged_swath(
                    ev.event_id,
                    buffer_km=buffer_km,
                    lookback_minutes=lookback_minutes,
                    join_distance_km=join_distance_km,
                )
                if merged and 'geometry' in merged:
                    swath_json = json.dumps(merged['geometry'])
                    props = merged.get('properties', {})
                    swath_method = props.get('swath_method', 'tracker')
                    swath_area_sqmi = props.get('swath_area_sqmi', 0.0) or 0.0
            except Exception as e:
                logger.debug("Swath generation failed for %s: %s", ev.event_id, e)

            # If no merged swath, try individual cell swaths
            if not swath_json:
                for cell_id in ev.cell_ids:
                    try:
                        cell_swath = tracker.create_track_swath(cell_id, buffer_km=buffer_km)
                        if cell_swath and 'geometry' in cell_swath:
                            swath_json = json.dumps(cell_swath['geometry'])
                            props = cell_swath.get('properties', {})
                            swath_method = props.get('method', 'track_buffer')
                            swath_area_sqmi = props.get('swath_area_sqmi', 0.0) or 0.0
                            break
                    except Exception:
                        pass

            # Fallback: point polygon if still no swath
            if not swath_json:
                swath_json = json.dumps({
                    'type': 'Point',
                    'coordinates': [ev.centroid_lon, ev.centroid_lat],
                })
                swath_method = 'centroid_point'

            # Convert area from sq km to sq mi if needed
            if swath_area_sqmi == 0.0 and ev.estimated_area_sq_km > 0:
                swath_area_sqmi = round(ev.estimated_area_sq_km * 0.386102, 1)

            # Compute motion from first cell's track (if available)
            storm_dir = 0.0
            storm_speed = 0.0
            try:
                tracks = tracker.get_cell_tracks(min_duration_minutes=0)
                for cid in ev.cell_ids:
                    if cid in tracks:
                        t = tracks[cid]
                        if len(t.positions) >= 2:
                            p0 = t.positions[0]
                            p1 = t.positions[-1]
                            import math
                            dlat = p1[0] - p0[0]
                            dlon = p1[1] - p0[1]
                            storm_dir = round((math.degrees(math.atan2(dlon, dlat)) + 360) % 360, 1)
                            storm_speed = round(t.avg_velocity_kmh * 0.621371, 1)  # km/h -> mph
                            break
            except Exception:
                pass

            # Map severity to max_hail_size (use tracker's MESH)
            max_hail_size = ev.max_mesh_inches
            avg_hail_size = round(max_hail_size * 0.65, 2) if max_hail_size > 0 else 0.0

            # Notes with metadata
            notes_meta = {
                '_meta': {
                    'tracker_event_id': ev.event_id,
                    'severity': ev.severity,
                    'status': ev.status,
                    'phase': ev.phase,
                    'hail_score_peak': ev.hail_score_peak,
                    'hail_score_avg': ev.hail_score_avg,
                    'event_quality_score': ev.event_quality_score,
                    'radar_ids': ev.radar_ids,
                    'cell_ids': ev.cell_ids,
                    'impact_window_minutes': ev.impact_window_minutes,
                }
            }

            # Check if this event already exists (by event_name = event_id)
            cur = conn.cursor()
            cur.execute(
                'SELECT id FROM hail_events WHERE event_name = ? AND data_source = ?',
                (ev.event_id, 'NEXRAD_REALTIME'),
            )
            existing = cur.fetchone()

            if existing:
                # Update existing row
                conn.execute("""
                    UPDATE hail_events SET
                        event_date = ?, start_time = ?, end_time = ?,
                        center_lat = ?, center_lon = ?, swath_polygon = ?,
                        swath_area_sqmi = ?, max_hail_size = ?, avg_hail_size = ?,
                        max_reflectivity = ?, avg_reflectivity = ?,
                        storm_motion_dir = ?, storm_motion_speed = ?,
                        swath_method = ?, num_detections = ?,
                        confidence_score = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    ev.start_time.strftime('%Y-%m-%d'),
                    ev.start_time.isoformat(),
                    ev.end_time.isoformat(),
                    ev.centroid_lat, ev.centroid_lon,
                    swath_json, swath_area_sqmi,
                    max_hail_size, avg_hail_size,
                    ev.max_reflectivity, round(ev.max_reflectivity * 0.85, 1),
                    storm_dir, storm_speed,
                    swath_method, len(ev.cell_ids),
                    ev.confidence,
                    existing[0],
                ))
            else:
                # Insert new row
                conn.execute("""
                    INSERT INTO hail_events (
                        event_name, event_date, start_time, end_time,
                        center_lat, center_lon, swath_polygon, swath_area_sqmi,
                        max_hail_size, avg_hail_size, max_reflectivity, avg_reflectivity,
                        storm_motion_dir, storm_motion_speed,
                        swath_method, num_detections, data_source,
                        confidence_score, estimated_vehicles
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ev.event_id,
                    ev.start_time.strftime('%Y-%m-%d'),
                    ev.start_time.isoformat(),
                    ev.end_time.isoformat(),
                    ev.centroid_lat, ev.centroid_lon,
                    swath_json, swath_area_sqmi,
                    max_hail_size, avg_hail_size,
                    ev.max_reflectivity, round(ev.max_reflectivity * 0.85, 1),
                    storm_dir, storm_speed,
                    swath_method, len(ev.cell_ids),
                    'NEXRAD_REALTIME',
                    ev.confidence, 0,
                ))
            persisted += 1

        except Exception as e:
            logger.warning("Failed to persist event %s: %s", ev.event_id, e)

    try:
        conn.commit()
    except Exception as e:
        logger.error("persist_tracker_events commit failed: %s", e)
    finally:
        conn.close()

    if persisted > 0:
        logger.info("Persisted %d/%d tracker events to %s", persisted, len(events), db_path)

    return persisted
