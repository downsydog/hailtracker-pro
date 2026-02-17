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
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Track whether the swath columns have been ensured this process lifetime
_columns_ensured = False


def _ensure_swath_columns(conn, is_pg: bool) -> None:
    """Add swath_area_km2 and swath_area_method columns if missing."""
    global _columns_ensured
    if _columns_ensured:
        return
    cols = [
        ('swath_area_km2', 'DOUBLE PRECISION DEFAULT 0'),
        ('swath_area_method', "TEXT DEFAULT 'unknown'"),
    ]
    cur = conn.cursor()
    for col_name, col_def in cols:
        try:
            cur.execute(
                f"ALTER TABLE hail_events ADD COLUMN {col_name} {col_def}"
            )
        except Exception:
            pass  # column already exists
    _columns_ensured = True


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

    from src.db.engine import get_connection, placeholder as _ph, is_postgres

    p = _ph()
    pg = is_postgres()
    now_expr = 'NOW()' if pg else 'CURRENT_TIMESTAMP'
    persisted = 0

    with get_connection() as conn:
        _ensure_swath_columns(conn, pg)
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
                        swath_method = 'cell_union'
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
                                swath_method = 'centroid_buffer'
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
                    swath_method = 'centroid_buffer'

                # Convert area from sq km to sq mi if needed
                if swath_area_sqmi == 0.0 and ev.estimated_area_sq_km > 0:
                    swath_area_sqmi = round(ev.estimated_area_sq_km * 0.386102, 1)

                # Always compute km2 from sqmi for consistency
                swath_area_km2 = round(swath_area_sqmi * 2.58999, 3) if swath_area_sqmi > 0 else 0.0

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
                                storm_speed = round(t.avg_velocity_kmh * 0.621371, 1)
                                break
                except Exception:
                    pass

                # Map severity to max_hail_size (use tracker's MESH)
                max_hail_size = ev.max_mesh_inches
                avg_hail_size = round(max_hail_size * 0.65, 2) if max_hail_size > 0 else 0.0

                # Check if this event already exists (by event_name = event_id)
                cur = conn.cursor()
                cur.execute(
                    f'SELECT id FROM hail_events WHERE event_name = {p} AND data_source = {p}',
                    (ev.event_id, 'NEXRAD_REALTIME'),
                )
                existing = cur.fetchone()

                if existing:
                    existing_id = existing[0] if not isinstance(existing, dict) else existing['id']
                    cur.execute(f"""
                        UPDATE hail_events SET
                            event_date = {p}, start_time = {p}, end_time = {p},
                            center_lat = {p}, center_lon = {p}, swath_polygon = {p},
                            swath_area_sqmi = {p}, swath_area_km2 = {p},
                            max_hail_size = {p}, avg_hail_size = {p},
                            max_reflectivity = {p}, avg_reflectivity = {p},
                            storm_motion_dir = {p}, storm_motion_speed = {p},
                            swath_method = {p}, num_detections = {p},
                            confidence_score = {p}, updated_at = {now_expr}
                        WHERE id = {p}
                    """, (
                        ev.start_time.strftime('%Y-%m-%d'),
                        ev.start_time.isoformat(),
                        ev.end_time.isoformat(),
                        ev.centroid_lat, ev.centroid_lon,
                        swath_json, swath_area_sqmi, swath_area_km2,
                        max_hail_size, avg_hail_size,
                        ev.max_reflectivity, round(ev.max_reflectivity * 0.85, 1),
                        storm_dir, storm_speed,
                        swath_method, len(ev.cell_ids),
                        ev.confidence,
                        existing_id,
                    ))
                else:
                    cur.execute(f"""
                        INSERT INTO hail_events (
                            event_name, event_date, start_time, end_time,
                            center_lat, center_lon, swath_polygon,
                            swath_area_sqmi, swath_area_km2,
                            max_hail_size, avg_hail_size, max_reflectivity, avg_reflectivity,
                            storm_motion_dir, storm_motion_speed,
                            swath_method, num_detections, data_source,
                            confidence_score, estimated_vehicles
                        ) VALUES ({', '.join([p] * 20)})
                    """, (
                        ev.event_id,
                        ev.start_time.strftime('%Y-%m-%d'),
                        ev.start_time.isoformat(),
                        ev.end_time.isoformat(),
                        ev.centroid_lat, ev.centroid_lon,
                        swath_json, swath_area_sqmi, swath_area_km2,
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

    if persisted > 0:
        logger.info("Persisted %d/%d tracker events to %s", persisted, len(events), db_path)

    return persisted
