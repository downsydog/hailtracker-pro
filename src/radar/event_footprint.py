"""
Event footprint construction + MRMS core polygon extraction.

Pure-function module — no global state, no tracker dependency.
Replicates geo-math helpers from storm_cell_tracker as standalone functions.
"""

import json
import logging
import math
import os
import sqlite3
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_R_KM = 6371.0

# ---------------------------------------------------------------------------
# Geo helpers (self-contained, same formulas as storm_cell_tracker)
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return _R_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _calculate_bearing(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Bearing in degrees (0=North, 90=East)."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)
    y = math.sin(dlon_rad) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad)
         - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def _offset_position_km(
    lat: float, lon: float, distance_km: float, bearing_deg: float,
) -> Tuple[float, float]:
    """Offset a position by distance and bearing. Returns (lat, lon)."""
    bearing_rad = math.radians(bearing_deg)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(distance_km / _R_KM)
        + math.cos(lat_rad) * math.sin(distance_km / _R_KM) * math.cos(bearing_rad)
    )
    lon2 = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance_km / _R_KM) * math.cos(lat_rad),
        math.cos(distance_km / _R_KM) - math.sin(lat_rad) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def _create_circle_coords(
    center_lat: float, center_lon: float,
    radius_km: float, num_points: int = 24,
) -> List[List[float]]:
    """Create a closed [lon, lat] ring for a circle."""
    points = []
    for i in range(num_points):
        angle = (i / num_points) * 360.0
        lat, lon = _offset_position_km(center_lat, center_lon, radius_km, angle)
        points.append([lon, lat])
    points.append(points[0])
    return points


def _create_semicircle(
    center_lat: float, center_lon: float,
    radius_km: float, center_bearing: float,
    num_points: int = 5,
) -> List[List[float]]:
    """Create semicircle points for a track end cap."""
    points = []
    for i in range(num_points):
        angle_offset = -90 + (i / (num_points - 1)) * 180
        bearing = center_bearing + angle_offset
        lat, lon = _offset_position_km(center_lat, center_lon, radius_km, bearing)
        points.append([lon, lat])
    return points


def _build_variable_width_track(
    positions: List[Tuple[float, float]],
    widths_km: List[float],
) -> Optional[List[List[float]]]:
    """
    Build a variable-width track polygon ring from positions and per-point widths.
    Same algorithm as storm_cell_tracker.create_track_swath (line 557-618).

    Returns closed [lon, lat] ring, or None if fewer than 2 positions.
    """
    if len(positions) < 2:
        return None

    left_points = []
    right_points = []

    for i, (lat, lon) in enumerate(positions):
        half_w = widths_km[i] / 2.0
        if i < len(positions) - 1:
            bearing = _calculate_bearing(lat, lon, positions[i + 1][0], positions[i + 1][1])
        else:
            bearing = _calculate_bearing(positions[i - 1][0], positions[i - 1][1], lat, lon)

        l_lat, l_lon = _offset_position_km(lat, lon, half_w, bearing + 90)
        r_lat, r_lon = _offset_position_km(lat, lon, half_w, bearing - 90)
        left_points.append([l_lon, l_lat])
        right_points.append([r_lon, r_lat])

    # Start cap
    first_lat, first_lon = positions[0]
    first_bearing = _calculate_bearing(
        first_lat, first_lon, positions[1][0], positions[1][1],
    )
    start_cap = _create_semicircle(
        first_lat, first_lon, widths_km[0] / 2, first_bearing + 180, num_points=5,
    )

    # End cap
    last_lat, last_lon = positions[-1]
    last_bearing = _calculate_bearing(
        positions[-2][0], positions[-2][1], last_lat, last_lon,
    )
    end_cap = _create_semicircle(
        last_lat, last_lon, widths_km[-1] / 2, last_bearing, num_points=5,
    )

    ring = start_cap + left_points + end_cap + list(reversed(right_points))
    ring.append(ring[0])
    return ring


def _convex_hull(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Monotone chain convex hull. Returns CCW hull (no repeated last point)."""
    points = sorted(set(points))
    if len(points) <= 1:
        return list(points)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def _polygon_area_km2(ring: List[List[float]], centroid_lat: float) -> float:
    """Shoelace area of a [lon, lat] ring in km2 with cos(lat) correction."""
    n = len(ring)
    if n < 4:
        return 0.0
    area_deg2 = 0.0
    for i in range(n - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        area_deg2 += x1 * y2 - x2 * y1
    area_deg2 = abs(area_deg2) / 2.0
    cos_lat = math.cos(math.radians(centroid_lat))
    return area_deg2 * (111.32 ** 2) * cos_lat


# ---------------------------------------------------------------------------
# build_event_polygon
# ---------------------------------------------------------------------------

def build_event_polygon(
    cells_data: List[dict],
) -> Tuple[Optional[str], float, str]:
    """
    Build the best-possible polygon for a storm event from its member cells.

    Args:
        cells_data: list of dicts with keys:
            centroid_lat, centroid_lon, area_km2, mesh_mm,
            previous_positions (list of (lat, lon))

    Returns:
        (geojson_str | None, area_km2, method)
        method in {'cell_union', 'centroid_buffer', 'convex_hull', 'none'}
    """
    if not cells_data:
        return None, 0.0, 'none'

    cell_rings = []
    all_points = []  # for convex-hull fallback

    for cell in cells_data:
        clat = cell.get('centroid_lat', 0)
        clon = cell.get('centroid_lon', 0)
        area = cell.get('area_km2', 0) or 0
        mesh_mm = cell.get('mesh_mm', 0) or 0
        prev_pos = cell.get('previous_positions', []) or []

        positions = [(clat, clon)] + [(p[0], p[1]) for p in prev_pos]

        if len(positions) >= 2:
            # Variable-width track polygon
            mesh_in = mesh_mm / 25.4 if mesh_mm > 0 else 0
            widths = [max(4.0, mesh_in * 2 + 2)] * len(positions)
            ring = _build_variable_width_track(positions, widths)
            if ring:
                cell_rings.append(ring)
                all_points.extend([(pt[0], pt[1]) for pt in ring])
                continue

        # Single-position: buffer circle
        radius_km = max(2.0, math.sqrt(area / math.pi)) if area > 0 else 2.0
        ring = _create_circle_coords(clat, clon, radius_km, num_points=24)
        cell_rings.append(ring)
        all_points.extend([(pt[0], pt[1]) for pt in ring])

    if not cell_rings:
        return None, 0.0, 'none'

    # Centroid for area calculation
    avg_lat = sum(c.get('centroid_lat', 0) for c in cells_data) / len(cells_data)

    # Try shapely union
    try:
        from shapely.geometry import shape, mapping, Polygon as ShapelyPolygon
        from shapely.ops import unary_union

        geoms = []
        for ring in cell_rings:
            geom = ShapelyPolygon([(pt[0], pt[1]) for pt in ring])
            if not geom.is_valid:
                geom = geom.buffer(0)
            if not geom.is_empty:
                geoms.append(geom)

        if geoms:
            merged = unary_union(geoms)
            if merged.geom_type == 'MultiPolygon':
                merged = max(merged.geoms, key=lambda g: g.area)
            if not merged.is_empty:
                area_deg2 = merged.area
                cos_lat = math.cos(math.radians(avg_lat))
                area_km2 = area_deg2 * (111.32 ** 2) * cos_lat
                geojson = mapping(merged)
                method = 'cell_union' if len(cells_data) > 1 else 'centroid_buffer'
                return json.dumps(geojson), round(area_km2, 3), method

    except ImportError:
        pass

    # Fallback: convex hull
    if len(all_points) >= 3:
        hull = _convex_hull(all_points)
        if len(hull) >= 3:
            closed = hull + [hull[0]]
            # Convert (lon, lat) tuples to [lon, lat] lists
            coords = [[p[0], p[1]] for p in closed]
            area_km2 = _polygon_area_km2(coords, avg_lat)
            geojson = {
                'type': 'Polygon',
                'coordinates': [coords],
            }
            return json.dumps(geojson), round(area_km2, 3), 'convex_hull'

    # Last resort: centroid buffer from average cell
    if cells_data:
        total_area = sum((c.get('area_km2', 0) or 0) for c in cells_data)
        radius_km = max(2.0, math.sqrt(total_area / math.pi)) if total_area > 0 else 2.0
        ring = _create_circle_coords(avg_lat,
                                     sum(c.get('centroid_lon', 0) for c in cells_data) / len(cells_data),
                                     radius_km)
        area_km2 = math.pi * radius_km ** 2
        geojson = {'type': 'Polygon', 'coordinates': [ring]}
        return json.dumps(geojson), round(area_km2, 3), 'centroid_buffer'

    return None, 0.0, 'none'


# ---------------------------------------------------------------------------
# extract_mrms_cores
# ---------------------------------------------------------------------------

def extract_mrms_cores(
    mrms_cache,
    event_bbox: dict,
    event_polygon_geojson: Optional[str] = None,
    thresholds_mm: Optional[List[float]] = None,
) -> dict:
    """
    Extract MRMS MESH core polygons at multiple thresholds.

    Returns dict with keys like:
        'core_15': {'geojson': str, 'area_km2': float},
        'core_25': {'geojson': str, 'area_km2': float},
        'core_40': {'geojson': str, 'area_km2': float},
        'method': 'mrms_contour' | 'unavailable',
    """
    if thresholds_mm is None:
        thresholds_mm = [15, 25, 40]

    empty_result = {'method': 'unavailable'}
    for t in thresholds_mm:
        key = f'core_{int(t)}'
        empty_result[key] = {'geojson': None, 'area_km2': 0.0}

    if mrms_cache is None or not getattr(mrms_cache, 'is_loaded', False):
        return empty_result

    # Thread-safe grid snapshot
    grid = getattr(mrms_cache, '_grid', None)
    if grid is None:
        return empty_result

    try:
        import numpy as np
    except ImportError:
        return empty_result

    lats = grid.get('lats')
    lons = grid.get('lons')
    mesh = grid.get('mesh_mm')
    if lats is None or lons is None or mesh is None:
        return empty_result

    # Extract sub-grid within bbox
    min_lat = event_bbox.get('bbox_min_lat', 0)
    max_lat = event_bbox.get('bbox_max_lat', 0)
    min_lon = event_bbox.get('bbox_min_lon', 0)
    max_lon = event_bbox.get('bbox_max_lon', 0)

    lat_mask = (lats >= min_lat) & (lats <= max_lat)
    lon_mask = (lons >= min_lon) & (lons <= max_lon)
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]

    if len(lat_idx) == 0 or len(lon_idx) == 0:
        return empty_result

    sub_lats = lats[lat_idx]
    sub_lons = lons[lon_idx]
    sub_mesh = mesh[np.ix_(lat_idx, lon_idx)]

    # Lat/lon step sizes for grid cell rectangles
    lat_step = abs(float(sub_lats[1] - sub_lats[0])) if len(sub_lats) > 1 else 0.25
    lon_step = abs(float(sub_lons[1] - sub_lons[0])) if len(sub_lons) > 1 else 0.25

    centroid_lat = float((min_lat + max_lat) / 2)

    # Load event polygon for intersection (if provided)
    event_geom = None
    try:
        from shapely.geometry import shape as shapely_shape
        if event_polygon_geojson:
            geoj = json.loads(event_polygon_geojson)
            if geoj.get('type') == 'Feature':
                geoj = geoj.get('geometry', geoj)
            event_geom = shapely_shape(geoj)
            if not event_geom.is_valid:
                event_geom = event_geom.buffer(0)
    except (ImportError, Exception):
        pass

    result = {'method': 'mrms_contour'}

    # Process thresholds from lowest to highest.
    # Track the area of lower thresholds to enforce nesting:
    # higher-threshold areas must be <= lower-threshold areas.
    prev_area = float('inf')
    for threshold in sorted(thresholds_mm):
        key = f'core_{int(threshold)}'
        mask = sub_mesh >= threshold
        n_rows, n_cols = mask.shape

        if not np.any(mask):
            result[key] = {'geojson': None, 'area_km2': 0.0}
            continue

        # Build rectangles for all cells above threshold
        rects = []
        for ri in range(n_rows):
            for ci in range(n_cols):
                if mask[ri, ci]:
                    cell_lat = float(sub_lats[ri])
                    cell_lon = float(sub_lons[ci])
                    rects.append((
                        cell_lon - lon_step / 2, cell_lat - lat_step / 2,
                        cell_lon + lon_step / 2, cell_lat + lat_step / 2,
                    ))

        if not rects:
            result[key] = {'geojson': None, 'area_km2': 0.0}
            continue

        # Try shapely union of rectangles
        try:
            from shapely.geometry import box, mapping
            from shapely.ops import unary_union as s_union

            rect_geoms = [box(r[0], r[1], r[2], r[3]) for r in rects]
            union = s_union(rect_geoms)

            if event_geom is not None:
                union = union.intersection(event_geom)

            if union.is_empty:
                result[key] = {'geojson': None, 'area_km2': 0.0}
                continue

            area_deg2 = union.area
            cos_lat = math.cos(math.radians(centroid_lat))
            area_km2 = area_deg2 * (111.32 ** 2) * cos_lat

            # Enforce nesting: higher threshold must not exceed lower
            area_km2 = min(area_km2, prev_area)
            prev_area = area_km2

            geojson = mapping(union)
            result[key] = {
                'geojson': json.dumps(geojson),
                'area_km2': round(area_km2, 3),
            }
            continue

        except ImportError:
            pass

        # Fallback: bounding box of all rect cells
        all_min_lon = min(r[0] for r in rects)
        all_min_lat = min(r[1] for r in rects)
        all_max_lon = max(r[2] for r in rects)
        all_max_lat = max(r[3] for r in rects)

        bbox_geojson = {
            'type': 'Polygon',
            'coordinates': [[
                [all_min_lon, all_max_lat],
                [all_max_lon, all_max_lat],
                [all_max_lon, all_min_lat],
                [all_min_lon, all_min_lat],
                [all_min_lon, all_max_lat],
            ]],
        }
        width_deg = all_max_lon - all_min_lon
        height_deg = all_max_lat - all_min_lat
        cos_lat = math.cos(math.radians(centroid_lat))
        area_km2 = width_deg * 111.32 * height_deg * 111.32 * cos_lat
        area_km2 = min(area_km2, prev_area)
        prev_area = area_km2

        result[key] = {
            'geojson': json.dumps(bbox_geojson),
            'area_km2': round(area_km2, 3),
        }

    return result


# ---------------------------------------------------------------------------
# Column migration helper
# ---------------------------------------------------------------------------

_NEW_COLUMNS = [
    ('swath_area_km2', 'REAL'),
    ('swath_area_method', 'TEXT'),
    ('mrms_core_15_geojson', 'TEXT'),
    ('mrms_core_25_geojson', 'TEXT'),
    ('mrms_core_40_geojson', 'TEXT'),
    ('mrms_core_15_km2', 'REAL DEFAULT 0'),
    ('mrms_core_25_km2', 'REAL DEFAULT 0'),
    ('mrms_core_40_km2', 'REAL DEFAULT 0'),
]


def _ensure_columns(conn) -> None:
    """Add new columns to hail_events if missing (idempotent)."""
    for col_name, col_type in _NEW_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE hail_events ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# update_event_footprints (deferred entry point)
# ---------------------------------------------------------------------------

def update_event_footprints(
    db_path: str = 'data/hailtracker_crm.db',
    mrms_cache=None,
    recent_minutes: int = 90,
) -> int:
    """
    Deferred enrichment: upgrade centroid_point events to buffer circles
    and add MRMS core polygons.

    Opens its own WAL connection (same pattern as persist_damage_grid).
    Returns count of events updated.
    """
    if not os.path.exists(db_path):
        return 0

    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    try:
        _ensure_columns(conn)
        conn.commit()

        # Use SQL datetime for cutoff (matches CURRENT_TIMESTAMP format)
        rows = conn.execute("""
            SELECT event_name, center_lat, center_lon,
                   swath_polygon, swath_method, swath_area_sqmi,
                   bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
            FROM hail_events
            WHERE data_source = 'NEXRAD_REALTIME'
              AND updated_at >= datetime('now', ? || ' minutes')
              AND (swath_method = 'centroid_point'
                   OR mrms_core_15_geojson IS NULL)
        """, (str(-recent_minutes),)).fetchall()

        if not rows:
            return 0

        updated = 0
        for row in rows:
            event_name = row['event_name']
            clat = row['center_lat']
            clon = row['center_lon']
            swath_polygon = row['swath_polygon']
            swath_method = row['swath_method']
            swath_area_sqmi = row['swath_area_sqmi'] or 0

            updates = {}

            # Upgrade centroid_point to buffer circle
            if swath_method == 'centroid_point':
                area_km2 = swath_area_sqmi * 2.59 if swath_area_sqmi > 0 else 0
                radius_km = max(2.0, math.sqrt(area_km2 / math.pi)) if area_km2 > 0 else 2.0
                ring = _create_circle_coords(clat, clon, radius_km)
                geojson = {'type': 'Polygon', 'coordinates': [ring]}
                computed_area = math.pi * radius_km ** 2

                updates['swath_polygon'] = json.dumps(geojson)
                updates['swath_method'] = 'deferred_buffer'
                updates['swath_area_km2'] = round(computed_area, 2)
                updates['swath_area_method'] = 'deferred_buffer'
                swath_polygon = updates['swath_polygon']

            # MRMS core extraction
            if mrms_cache is not None and row['bbox_min_lat'] is not None:
                bbox = {
                    'bbox_min_lat': row['bbox_min_lat'],
                    'bbox_max_lat': row['bbox_max_lat'],
                    'bbox_min_lon': row['bbox_min_lon'],
                    'bbox_max_lon': row['bbox_max_lon'],
                }
                cores = extract_mrms_cores(mrms_cache, bbox, swath_polygon)
                if cores.get('method') == 'mrms_contour':
                    for t in [15, 25, 40]:
                        key = f'core_{t}'
                        if key in cores and cores[key].get('geojson'):
                            updates[f'mrms_core_{t}_geojson'] = cores[key]['geojson']
                            updates[f'mrms_core_{t}_km2'] = cores[key]['area_km2']

            if updates:
                set_clauses = ', '.join(f"{k} = ?" for k in updates)
                set_clauses += ', updated_at = CURRENT_TIMESTAMP'
                values = list(updates.values()) + [event_name]
                conn.execute(
                    f"UPDATE hail_events SET {set_clauses} WHERE event_name = ?",
                    values,
                )
                updated += 1

        conn.commit()
        return updated

    except Exception:
        logger.exception("Event footprint enrichment error")
        return 0
    finally:
        conn.close()
