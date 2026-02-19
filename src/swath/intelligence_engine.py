"""
Swath Intelligence Engine v2 — Motion-Coherent Swath Tracking.

Assigns CONFIRMED hail events to swaths using kinematic consistency
(forward projection, bearing/velocity matching) instead of simple
spatial+temporal BFS clustering.

Features:
- Stable swath IDs (persist across cycles, not regenerated from member hash)
- Motion-coherence scoring for event→swath assignment
- Geometry quality ranking with impact damping
- Incremental assignment: events sorted by time, swath state updated after each

Called as deferred work from storm_monitor._persist_tracker_events()
after hail_events and damage_grid persistence completes.
"""

import hashlib
import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _dict_cursor(conn):
    """Return a cursor that yields dict-like rows for both SQLite and PG.

    ``get_connection()`` yields raw psycopg2 pool connections whose default
    cursors return tuples.  This helper creates a ``RealDictCursor`` when
    on PostgreSQL so that ``dict(row)`` works the same as ``sqlite3.Row``.
    """
    try:
        from src.db.engine import is_postgres
        if is_postgres():
            import psycopg2.extras
            return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception:
        pass
    return conn.cursor()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_CONFIRMED_EVENTS = 2
MIN_SEVERE_CORE_KM2 = 5.0
EXPIRE_MINUTES = 45.0
MATURE_CORE_KM2 = 10.0
MATURE_IMPACT = 60
EVENT_WINDOW_MINUTES = 90

# Motion coherence
BASE_GATE_KM = 35.0
MAX_GATE_KM = 90.0
BEARING_GATE_DEG = 45.0
MAX_DT_MINUTES = 75.0
MIN_MATCH_SCORE = 0.45
COARSE_FILTER_KM = 120.0

# Geometry quality
GEO_QUALITY_HIGH = {'cell_union', 'polygon_union'}  # polygon_union kept for legacy data
GEO_QUALITY_MED = {'centroid_buffer', 'sum_km2', 'sum_sqmi'}


# ---------------------------------------------------------------------------
# Geo utilities (self-contained)
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing in degrees from point 1 to point 2."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(rlat2)
    y = (math.cos(rlat1) * math.sin(rlat2)
         - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon))
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _angular_diff(a: float, b: float) -> float:
    """Smallest angular difference in degrees (0-180)."""
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


def _forward_position(lat: float, lon: float, bearing_deg: float,
                      distance_km: float) -> Tuple[float, float]:
    """Move point forward along bearing by distance_km. Returns (lat, lon)."""
    R = 6371.0
    d = distance_km / R
    brng = math.radians(bearing_deg)
    rlat = math.radians(lat)
    rlon = math.radians(lon)
    new_lat = math.asin(
        math.sin(rlat) * math.cos(d) +
        math.cos(rlat) * math.sin(d) * math.cos(brng)
    )
    new_lon = rlon + math.atan2(
        math.sin(brng) * math.sin(d) * math.cos(rlat),
        math.cos(d) - math.sin(rlat) * math.sin(new_lat)
    )
    return math.degrees(new_lat), math.degrees(new_lon)


def _time_gap_minutes(ev_a: dict, ev_b: dict) -> float:
    """Minimum temporal gap (minutes) between two events' time ranges."""
    a_start = _parse_utc(ev_a['start_time'])
    a_end = _parse_utc(ev_a['end_time'])
    b_start = _parse_utc(ev_b['start_time'])
    b_end = _parse_utc(ev_b['end_time'])
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    if latest_start <= earliest_end:
        return 0.0
    return (latest_start - earliest_end).total_seconds() / 60.0


def _parse_utc(s) -> datetime:
    """Parse ISO timestamp or pass through datetime, ensure UTC timezone.

    PostgreSQL returns ``datetime`` objects from TIMESTAMP columns while
    SQLite returns ISO-format strings.  Handle both transparently.
    """
    if isinstance(s, datetime):
        dt = s
    else:
        dt = datetime.fromisoformat(str(s))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Geometry quality
# ---------------------------------------------------------------------------

def _geometry_quality(methods: List[str]) -> str:
    """Determine geometry quality rank from list of area/swath methods."""
    for m in methods:
        if m in GEO_QUALITY_HIGH:
            return 'HIGH'
    for m in methods:
        if m in GEO_QUALITY_MED:
            return 'MED'
    return 'LOW'


# ---------------------------------------------------------------------------
# Table management
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hail_swaths (
    swath_id TEXT PRIMARY KEY,
    first_seen_utc TEXT NOT NULL,
    last_seen_utc TEXT NOT NULL,
    centroid_lat REAL NOT NULL,
    centroid_lon REAL NOT NULL,
    area_km2 REAL DEFAULT 0,
    severe_core_km2 REAL DEFAULT 0,
    mean_hail_size REAL DEFAULT 0,
    max_hail_size REAL DEFAULT 0,
    impact_score INTEGER DEFAULT 0,
    impact_tier TEXT DEFAULT 'LOW',
    lifecycle_state TEXT DEFAULT 'FORMING',
    confidence_avg REAL DEFAULT 0,
    confirmed_event_count INTEGER DEFAULT 0,
    candidate_event_count INTEGER DEFAULT 0,
    directional_vector_deg REAL,
    velocity_kmh REAL,
    growth_rate_km2_per_min REAL DEFAULT 0,
    decay_cycles INTEGER DEFAULT 0,
    geometry_geojson TEXT,
    member_event_names TEXT,
    area_method TEXT DEFAULT 'unknown',
    geometry_quality TEXT DEFAULT 'LOW',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_swaths_time ON hail_swaths(last_seen_utc)",
    "CREATE INDEX IF NOT EXISTS idx_swaths_state ON hail_swaths(lifecycle_state)",
    "CREATE INDEX IF NOT EXISTS idx_swaths_impact ON hail_swaths(impact_score)",
    "CREATE INDEX IF NOT EXISTS idx_swaths_loc ON hail_swaths(centroid_lat, centroid_lon)",
]


def _ensure_table(db_path: str) -> None:
    """Idempotent CREATE TABLE + indexes + column migration for hail_swaths.

    When PostgreSQL is active, the PostGIS migration DDL (001_postgis_schema.sql)
    is expected to have created hail_swaths already via engine.ensure_schema().
    This function only runs the SQLite DDL path as a fallback.
    """
    from src.db.engine import is_postgres, get_connection, ensure_schema

    if is_postgres():
        ensure_schema()
        return

    # SQLite path: use direct file-based connection for schema init
    import sqlite3 as _sqlite3
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = _sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute(_CREATE_TABLE_SQL)
    for idx_sql in _INDEXES:
        conn.execute(idx_sql)
    for col_def in [
        ('area_method', "TEXT DEFAULT 'unknown'"),
        ('geometry_quality', "TEXT DEFAULT 'LOW'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE hail_swaths ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Legacy clustering (kept for fallback / tests)
# ---------------------------------------------------------------------------

SPATIAL_PROXIMITY_KM = 40.0
TEMPORAL_PROXIMITY_MIN = 45.0


def _cluster_events(events: List[dict]) -> List[List[dict]]:
    """
    Single-link BFS clustering of events by spatial + temporal proximity.
    Returns list of clusters (each a list of event dicts sorted by start_time).
    Only clusters meeting the persistence threshold are returned.
    """
    n = len(events)
    if n == 0:
        return []

    adj: Dict[int, List[int]] = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            dist = _haversine_km(
                events[i]['center_lat'], events[i]['center_lon'],
                events[j]['center_lat'], events[j]['center_lon'],
            )
            if dist > SPATIAL_PROXIMITY_KM:
                continue
            gap = _time_gap_minutes(events[i], events[j])
            if gap > TEMPORAL_PROXIMITY_MIN:
                continue
            adj[i].append(j)
            adj[j].append(i)

    from collections import deque
    visited = set()
    clusters = []
    for seed in range(n):
        if seed in visited:
            continue
        component = []
        queue = deque([seed])
        visited.add(seed)
        while queue:
            node = queue.popleft()
            component.append(events[node])
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        component.sort(key=lambda e: e['start_time'])
        clusters.append(component)

    result = []
    for cluster in clusters:
        if len(cluster) >= MIN_CONFIRMED_EVENTS:
            result.append(cluster)
            continue
        severe_area = sum(
            (ev.get('swath_area_sqmi', 0) or 0) * 2.59
            for ev in cluster
            if (ev.get('max_hail_size', 0) or 0) >= 2.0
        )
        if severe_area >= MIN_SEVERE_CORE_KM2:
            result.append(cluster)

    return result


# ---------------------------------------------------------------------------
# Stable swath ID generation
# ---------------------------------------------------------------------------

def _generate_stable_swath_id(first_event: dict) -> str:
    """
    Generate a stable swath ID from the first event assigned.
    Format: SWATH_{date}_{lat_grid}_{lon_grid}_{hash8}
    Once created and stored in DB, the ID never changes.
    """
    start = first_event['start_time']
    if isinstance(start, datetime):
        date_str = start.strftime('%Y%m%d')
    else:
        date_str = start[:10].replace('-', '')
    lat = first_event['center_lat']
    lon = first_event['center_lon']
    # Grid snap to 0.1 degree
    lat_grid = round(lat, 1)
    lon_grid = round(lon, 1)
    # Hash from event name + timestamp for uniqueness
    hash_input = f"{first_event['event_name']}|{start}|{lat}|{lon}".encode()
    hash8 = hashlib.md5(hash_input).hexdigest()[:8]
    return f"SWATH_{date_str}_{lat_grid:.1f}_{lon_grid:.1f}_{hash8}"


def _generate_swath_id(cluster: List[dict]) -> str:
    """Legacy: deterministic swath ID from sorted member event names."""
    names = sorted(ev['event_name'] for ev in cluster)
    earliest = min(ev['start_time'] for ev in cluster)
    if isinstance(earliest, datetime):
        date_str = earliest.strftime('%Y%m%d')
    else:
        date_str = earliest[:10].replace('-', '')
    centroid_lat = sum(ev['center_lat'] for ev in cluster) / len(cluster)
    centroid_lon = sum(ev['center_lon'] for ev in cluster) / len(cluster)
    hash_input = '|'.join(names).encode()
    hash8 = hashlib.md5(hash_input).hexdigest()[:8]
    return f"SWATH_{date_str}_{centroid_lat:.2f}_{centroid_lon:.2f}_{hash8}"


# ---------------------------------------------------------------------------
# Motion coherence scoring
# ---------------------------------------------------------------------------

def _compute_motion_score(
    swath: dict,
    event: dict,
) -> Tuple[float, float]:
    """
    Compute motion-coherence score for assigning event to swath.

    Returns (score, dist_km) where score in [0, 1].
    Higher score = better match.
    """
    ev_lat = event['center_lat']
    ev_lon = event['center_lon']
    ev_start = _parse_utc(event['start_time'])

    sw_lat = swath['centroid_lat']
    sw_lon = swath['centroid_lon']
    sw_last = _parse_utc(swath['last_seen_utc'])
    sw_bearing = swath.get('directional_vector_deg') or 0.0
    sw_vel = swath.get('velocity_kmh') or 0.0

    # Time delta
    dt_sec = (ev_start - sw_last).total_seconds()
    dt_min = max(0.0, dt_sec / 60.0)  # clamp negative to 0
    dt_hours = dt_min / 60.0

    # Hard gate: time
    if dt_min > MAX_DT_MINUTES:
        return -1.0, 999.0

    # Forward-project swath position
    if sw_vel > 0 and dt_hours > 0:
        pred_lat, pred_lon = _forward_position(sw_lat, sw_lon, sw_bearing,
                                               sw_vel * dt_hours)
    else:
        pred_lat, pred_lon = sw_lat, sw_lon

    # Distance to predicted position
    dist_km = _haversine_km(pred_lat, pred_lon, ev_lat, ev_lon)

    # Dynamic gate: base + speed-dependent expansion, clamped
    dynamic_gate = BASE_GATE_KM + 0.25 * sw_vel * dt_hours
    dynamic_gate = max(BASE_GATE_KM, min(MAX_GATE_KM, dynamic_gate))

    # Hard gate: distance
    if dist_km > dynamic_gate:
        return -1.0, dist_km

    # Score components
    score = 1.0

    # Distance penalty (0.6 weight)
    dist_penalty = (dist_km / dynamic_gate) * 0.6
    score -= dist_penalty

    # Bearing consistency penalty (0.3 weight, only if swath has known bearing)
    if sw_vel > 5.0:  # only penalize bearing if swath is moving meaningfully
        # Estimate event bearing from swath centroid to event
        ev_bearing = _bearing_deg(sw_lat, sw_lon, ev_lat, ev_lon)
        bearing_diff = _angular_diff(sw_bearing, ev_bearing)
        if bearing_diff > BEARING_GATE_DEG:
            return -1.0, dist_km
        bearing_penalty = (bearing_diff / 90.0) * 0.3
        score -= bearing_penalty

    # Velocity penalty (0.1 weight) — skip if we can't estimate event speed
    # We don't have event velocity directly; skip this component for now

    return max(0.0, score), dist_km


# ---------------------------------------------------------------------------
# Area computation (unchanged from v1)
# ---------------------------------------------------------------------------

def _postgis_area_km2(geojson_str: str) -> Optional[float]:
    """Compute area in km2 using PostGIS geography cast (authoritative)."""
    try:
        from src.db.engine import is_postgres, get_connection, placeholder as ph
        if not is_postgres():
            return None
        p = ph()
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                SELECT ST_Area(
                    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON({p}), 4326))::geography
                ) / 1e6 AS area_km2
            """, (geojson_str,))
            row = cur.fetchone()
            if row is None:
                return None
            val = row[0] if not isinstance(row, dict) else row.get('area_km2')
            return float(val) if val is not None else None
    except Exception:
        return None


def _compute_area_km2(
    geojson_strings: List[Optional[str]],
    centroid_lat: float,
    cluster: Optional[List[dict]] = None,
) -> Tuple[float, object, str]:
    """
    Compute swath area in km2 with fallback chain.
    Returns (area_km2, union_geometry_or_None, area_method).

    When PostGIS is available, the final area is computed via
    ST_Area(geom::geography)/1e6 for geodetic accuracy.
    """
    # --- Attempt 1: Shapely polygon union ---
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union

        polys = []
        for gj_str in geojson_strings:
            if not gj_str:
                continue
            try:
                geoj = json.loads(gj_str)
                if geoj.get('type') == 'Feature':
                    geoj = geoj.get('geometry', geoj)
                elif geoj.get('type') == 'FeatureCollection':
                    for feat in geoj.get('features', []):
                        g = feat.get('geometry')
                        if g:
                            geom = shape(g)
                            if not geom.is_valid:
                                geom = geom.buffer(0)
                            polys.append(geom)
                    continue
                geom = shape(geoj)
                if not geom.is_valid:
                    geom = geom.buffer(0)
                polys.append(geom)
            except Exception:
                continue

        if polys:
            union = unary_union(polys)

            # Try PostGIS geography area (authoritative geodetic math)
            try:
                from shapely.geometry import mapping
                union_geojson = json.dumps(mapping(union))
                pg_area = _postgis_area_km2(union_geojson)
                if pg_area is not None and pg_area > 0:
                    return pg_area, union, 'cell_union'
            except Exception:
                pass

            # Fallback: Shapely planar approximation
            area_deg2 = union.area
            cos_lat = math.cos(math.radians(centroid_lat))
            area_km2 = area_deg2 * (111.32 ** 2) * cos_lat
            if area_km2 > 0:
                return area_km2, union, 'cell_union'

    except ImportError:
        pass

    # --- Attempt 2a: Direct km2 from hail_events.swath_area_km2 ---
    if cluster:
        total_km2 = sum(
            (ev.get('swath_area_km2', 0) or 0) for ev in cluster
        )
        if total_km2 > 0:
            return total_km2, None, 'sum_km2'

    # --- Attempt 2b: Sum swath_area_sqmi from member events ---
    if cluster:
        total_sqmi = sum(
            (ev.get('swath_area_sqmi', 0) or 0) for ev in cluster
        )
        if total_sqmi > 0:
            return total_sqmi * 2.59, None, 'sum_sqmi'

    # --- Attempt 3: Radius proxy from centroid spread ---
    if cluster and len(cluster) >= 2:
        c_lat = sum(ev['center_lat'] for ev in cluster) / len(cluster)
        c_lon = sum(ev['center_lon'] for ev in cluster) / len(cluster)
        max_r = max(
            _haversine_km(c_lat, c_lon, ev['center_lat'], ev['center_lon'])
            for ev in cluster
        )
        r_km = max(3.0, max_r)
        area_km2 = math.pi * r_km ** 2
        return round(area_km2, 3), None, 'radius_proxy'

    return 0.0, None, 'unknown'


# ---------------------------------------------------------------------------
# Impact scoring with geometry quality damping
# ---------------------------------------------------------------------------

def _compute_impact_score(
    cluster: List[dict],
    severe_core_km2: float,
    duration_min: float,
    geo_quality: str = 'MED',
) -> int:
    """
    Economic impact score (0-100) with geometry quality damping.

    When geo_quality is LOW:
    - area/core components are damped by 0.25
    - unless MRMS core data is present (severe_core from MRMS is trusted)
    """
    n = len(cluster)
    if n == 0:
        return 0

    frac_2in = sum(1 for ev in cluster if (ev.get('max_hail_size', 0) or 0) >= 2.0) / n
    frac_1_5in = sum(1 for ev in cluster if (ev.get('max_hail_size', 0) or 0) >= 1.5) / n

    pts_severe = frac_2in * 30
    pts_signif = frac_1_5in * 20

    # Core component with quality damping
    core_raw = min(1.0, severe_core_km2 / 100.0) * 20
    has_mrms_core = any((ev.get('mrms_core_25_km2', 0) or 0) > 0 for ev in cluster)
    if geo_quality == 'LOW' and not has_mrms_core:
        core_raw *= 0.25

    pts_core = core_raw
    pts_duration = min(1.0, duration_min / 60.0) * 10
    pts_urban = 0.5 * 20  # placeholder

    score = pts_severe + pts_signif + pts_core + pts_duration + pts_urban
    return max(0, min(100, round(score)))


def _get_tier(score: int) -> str:
    """Map impact score to tier label."""
    if score >= 80:
        return 'EXTREME'
    elif score >= 60:
        return 'HIGH'
    elif score >= 30:
        return 'MODERATE'
    return 'LOW'


# ---------------------------------------------------------------------------
# Lifecycle model with geometry quality gate
# ---------------------------------------------------------------------------

def _compute_lifecycle(
    event_count: int,
    growth_rate: float,
    severe_core_km2: float,
    impact_score: int,
    last_seen_utc: str,
    previous_state: Optional[str],
    decay_cycles: int,
    geo_quality: str = 'MED',
    has_mrms_core: bool = False,
) -> Tuple[str, int]:
    """
    Determine lifecycle state and update decay cycle counter.
    MATURE requires MED+ geometry_quality OR actual MRMS core data present.
    """
    now = datetime.now(timezone.utc)
    try:
        last_seen = _parse_utc(last_seen_utc)
    except (ValueError, TypeError):
        last_seen = now

    minutes_since_last = (now - last_seen).total_seconds() / 60.0

    if previous_state == 'EXPIRED':
        return 'EXPIRED', decay_cycles

    if minutes_since_last > EXPIRE_MINUTES:
        return 'EXPIRED', decay_cycles

    new_decay = decay_cycles + 1 if growth_rate < 0 else 0

    if previous_state in ('MATURE', 'DECAYING') and new_decay >= 2:
        return 'DECAYING', new_decay

    if previous_state == 'MATURE':
        return 'MATURE', new_decay

    # MATURE gate: require MED+ geometry OR actual MRMS core data
    quality_ok = geo_quality in ('HIGH', 'MED')
    if (quality_ok or has_mrms_core) and severe_core_km2 >= MATURE_CORE_KM2 and impact_score >= MATURE_IMPACT:
        return 'MATURE', new_decay

    if event_count >= 2 and growth_rate > 0:
        return 'ORGANIZING', new_decay

    if event_count <= 1 or previous_state in (None, 'FORMING'):
        return 'FORMING', new_decay

    return 'ORGANIZING', new_decay


# ---------------------------------------------------------------------------
# Swath builder (per-swath metric aggregation)
# ---------------------------------------------------------------------------

def _build_swath_from_events(
    swath_id: str,
    events: List[dict],
    previous_swath: Optional[dict],
) -> dict:
    """
    Compute all swath fields from assigned event list.
    Uses stable swath_id (not regenerated).
    """
    n = len(events)
    events_sorted = sorted(events, key=lambda e: _parse_utc(e['start_time']))

    first_seen = min(_parse_utc(ev['start_time']) for ev in events)
    last_seen = max(_parse_utc(ev['end_time']) for ev in events)
    # Preserve original first_seen if swath existed before
    if previous_swath and previous_swath.get('first_seen_utc'):
        prev_first = _parse_utc(previous_swath['first_seen_utc'])
        if prev_first < first_seen:
            first_seen = prev_first

    first_dt = first_seen
    last_dt = last_seen
    duration_min = max(0, (last_dt - first_dt).total_seconds() / 60.0)

    centroid_lat = sum(ev['center_lat'] for ev in events) / n
    centroid_lon = sum(ev['center_lon'] for ev in events) / n

    hail_sizes = [(ev.get('max_hail_size', 0) or 0) for ev in events]
    max_hail = max(hail_sizes) if hail_sizes else 0
    mean_hail = sum(hail_sizes) / n if n > 0 else 0

    confs = [(ev.get('confidence_score', 0) or 0) for ev in events]
    confidence_avg = sum(confs) / n if n > 0 else 0

    # Area
    swath_polygons = [ev.get('swath_polygon') for ev in events]
    area_km2, union_geom, area_method = _compute_area_km2(
        swath_polygons, centroid_lat, cluster=events,
    )

    # Severe core
    severe_events = [ev for ev in events if (ev.get('max_hail_size', 0) or 0) >= 2.0]
    severe_polygons = [ev.get('swath_polygon') for ev in severe_events]
    if severe_events:
        severe_core_km2, _, _ = _compute_area_km2(
            severe_polygons, centroid_lat, cluster=severe_events,
        )
    else:
        severe_core_km2 = 0.0

    mrms_core_km2 = sum(
        (ev.get('mrms_core_25_km2', 0) or 0) for ev in events
    )
    if mrms_core_km2 > 0:
        severe_core_km2 = max(severe_core_km2, mrms_core_km2)

    # Direction and velocity from time-ordered events
    if n >= 2:
        earliest_ev = events_sorted[0]
        latest_ev = events_sorted[-1]
        direction_deg = _bearing_deg(
            earliest_ev['center_lat'], earliest_ev['center_lon'],
            latest_ev['center_lat'], latest_ev['center_lon'],
        )
        dist_km = _haversine_km(
            earliest_ev['center_lat'], earliest_ev['center_lon'],
            latest_ev['center_lat'], latest_ev['center_lon'],
        )
        hours = duration_min / 60.0
        velocity_kmh = dist_km / hours if hours > 0 else 0.0
    else:
        direction_deg = (previous_swath or {}).get('directional_vector_deg') or 0.0
        velocity_kmh = (previous_swath or {}).get('velocity_kmh') or 0.0

    # Geometry quality
    methods = []
    for ev in events:
        m = ev.get('swath_area_method') or ev.get('swath_method') or ''
        if m:
            methods.append(m)
    methods.append(area_method)
    geo_quality = _geometry_quality(methods)

    # Growth rate
    growth_rate = 0.0
    prev_area = 0.0
    prev_state = None
    prev_decay = 0
    if previous_swath:
        prev_area = previous_swath.get('area_km2', 0) or 0
        prev_state = previous_swath.get('lifecycle_state')
        prev_decay = previous_swath.get('decay_cycles', 0) or 0
        prev_updated = previous_swath.get('updated_at', '')
        try:
            prev_dt = _parse_utc(prev_updated)
            delta_min = (datetime.now(timezone.utc) - prev_dt).total_seconds() / 60.0
            if delta_min > 0:
                growth_rate = (area_km2 - prev_area) / delta_min
        except (ValueError, TypeError):
            pass

    # Impact (with geo quality damping)
    impact_score = _compute_impact_score(events, severe_core_km2, duration_min,
                                         geo_quality=geo_quality)
    impact_tier = _get_tier(impact_score)

    # Lifecycle (with geo quality gate)
    has_mrms_core = mrms_core_km2 > 0
    lifecycle_state, decay_cycles = _compute_lifecycle(
        event_count=n,
        growth_rate=growth_rate,
        severe_core_km2=severe_core_km2,
        impact_score=impact_score,
        last_seen_utc=last_seen,
        previous_state=prev_state,
        decay_cycles=prev_decay,
        geo_quality=geo_quality,
        has_mrms_core=has_mrms_core,
    )

    # Geometry GeoJSON — validate and repair if needed
    geometry_geojson = None
    if union_geom is not None:
        try:
            from shapely.geometry import mapping
            if not union_geom.is_valid:
                union_geom = union_geom.buffer(0)
                try:
                    from src.observability.metrics import SWATH_GEOMETRY_REPAIRED
                    SWATH_GEOMETRY_REPAIRED.inc()
                except Exception:
                    pass
                logger.info("Swath %s: geometry repaired via buffer(0)", swath_id)
            geometry_geojson = json.dumps(mapping(union_geom))
        except Exception:
            pass

    member_event_names = json.dumps(sorted(ev['event_name'] for ev in events))

    return {
        'swath_id': swath_id,
        'first_seen_utc': first_seen,
        'last_seen_utc': last_seen,
        'centroid_lat': round(centroid_lat, 6),
        'centroid_lon': round(centroid_lon, 6),
        'area_km2': round(area_km2, 3),
        'severe_core_km2': round(severe_core_km2, 3),
        'mean_hail_size': round(mean_hail, 3),
        'max_hail_size': round(max_hail, 3),
        'impact_score': impact_score,
        'impact_tier': impact_tier,
        'lifecycle_state': lifecycle_state,
        'confidence_avg': round(confidence_avg, 1),
        'confirmed_event_count': n,
        'candidate_event_count': 0,
        'directional_vector_deg': round(direction_deg, 1),
        'velocity_kmh': round(velocity_kmh, 1),
        'growth_rate_km2_per_min': round(growth_rate, 4),
        'decay_cycles': decay_cycles,
        'geometry_geojson': geometry_geojson,
        'member_event_names': member_event_names,
        'area_method': area_method,
        'geometry_quality': geo_quality,
    }


# Legacy wrapper for backward compat
def _build_swath(cluster: List[dict], previous_swath: Optional[dict]) -> dict:
    swath_id = _generate_swath_id(cluster)
    return _build_swath_from_events(swath_id, cluster, previous_swath)


# ---------------------------------------------------------------------------
# UPSERT SQL (v2 with geometry_quality)
# ---------------------------------------------------------------------------

def _build_upsert_sql() -> str:
    """Build backend-aware UPSERT SQL for hail_swaths."""
    from src.db.engine import placeholder as ph, is_postgres

    p = ph()
    now = 'NOW()' if is_postgres() else 'CURRENT_TIMESTAMP'
    greatest = 'GREATEST' if is_postgres() else 'MAX'

    return f"""
INSERT INTO hail_swaths (
    swath_id, first_seen_utc, last_seen_utc,
    centroid_lat, centroid_lon,
    area_km2, severe_core_km2,
    mean_hail_size, max_hail_size,
    impact_score, impact_tier, lifecycle_state,
    confidence_avg, confirmed_event_count, candidate_event_count,
    directional_vector_deg, velocity_kmh,
    growth_rate_km2_per_min, decay_cycles,
    geometry_geojson, member_event_names,
    area_method, geometry_quality, updated_at
) VALUES (
    {p}, {p}, {p},
    {p}, {p},
    {p}, {p},
    {p}, {p},
    {p}, {p}, {p},
    {p}, {p}, {p},
    {p}, {p},
    {p}, {p},
    {p}, {p},
    {p}, {p}, {now}
)
ON CONFLICT(swath_id) DO UPDATE SET
    first_seen_utc = excluded.first_seen_utc,
    last_seen_utc = excluded.last_seen_utc,
    centroid_lat = excluded.centroid_lat,
    centroid_lon = excluded.centroid_lon,
    area_km2 = excluded.area_km2,
    severe_core_km2 = excluded.severe_core_km2,
    mean_hail_size = excluded.mean_hail_size,
    max_hail_size = {greatest}(hail_swaths.max_hail_size, excluded.max_hail_size),
    impact_score = excluded.impact_score,
    impact_tier = excluded.impact_tier,
    lifecycle_state = CASE
        WHEN hail_swaths.lifecycle_state = 'EXPIRED' THEN 'EXPIRED'
        ELSE excluded.lifecycle_state
    END,
    confidence_avg = excluded.confidence_avg,
    confirmed_event_count = excluded.confirmed_event_count,
    candidate_event_count = excluded.candidate_event_count,
    directional_vector_deg = excluded.directional_vector_deg,
    velocity_kmh = excluded.velocity_kmh,
    growth_rate_km2_per_min = excluded.growth_rate_km2_per_min,
    decay_cycles = excluded.decay_cycles,
    geometry_geojson = excluded.geometry_geojson,
    member_event_names = excluded.member_event_names,
    area_method = excluded.area_method,
    geometry_quality = excluded.geometry_quality,
    updated_at = {now}
"""


def _upsert_swath(conn, swath: dict) -> None:
    """Execute UPSERT for a single swath dict."""
    sql = _build_upsert_sql()
    cur = conn.cursor()
    cur.execute(sql, (
        swath['swath_id'],
        swath['first_seen_utc'],
        swath['last_seen_utc'],
        swath['centroid_lat'],
        swath['centroid_lon'],
        swath['area_km2'],
        swath['severe_core_km2'],
        swath['mean_hail_size'],
        swath['max_hail_size'],
        swath['impact_score'],
        swath['impact_tier'],
        swath['lifecycle_state'],
        swath['confidence_avg'],
        swath['confirmed_event_count'],
        swath['candidate_event_count'],
        swath['directional_vector_deg'],
        swath['velocity_kmh'],
        swath['growth_rate_km2_per_min'],
        swath['decay_cycles'],
        swath['geometry_geojson'],
        swath['member_event_names'],
        swath['area_method'],
        swath['geometry_quality'],
    ))


# ---------------------------------------------------------------------------
# Motion-coherent assignment engine
# ---------------------------------------------------------------------------

def _fetch_active_swaths(conn) -> List[dict]:
    """Fetch non-EXPIRED swaths seen within EVENT_WINDOW_MINUTES."""
    from src.db.engine import placeholder as ph
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=EVENT_WINDOW_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        cur = _dict_cursor(conn)
        cur.execute(f"""
            SELECT swath_id, first_seen_utc, last_seen_utc,
                   centroid_lat, centroid_lon,
                   directional_vector_deg, velocity_kmh,
                   area_km2, severe_core_km2, impact_score,
                   lifecycle_state, decay_cycles, member_event_names,
                   area_method, geometry_quality, updated_at
            FROM hail_swaths
            WHERE lifecycle_state != 'EXPIRED'
              AND last_seen_utc >= {ph()}
        """, (cutoff,))
        rows = cur.fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def _fetch_recent_events(conn) -> List[dict]:
    """Fetch CONFIRMED events from recent window."""
    from src.db.engine import placeholder as ph, is_postgres

    p = ph()
    if is_postgres():
        time_filter = f"start_time >= NOW() + ({p} || ' minutes')::interval"
    else:
        time_filter = f"start_time >= datetime('now', {p} || ' minutes')"

    # Try extended columns, fallback to base.
    # Use SAVEPOINT so a column-missing error doesn't poison the PG transaction.
    pg = is_postgres()
    try:
        cur = _dict_cursor(conn)
        if pg:
            cur.execute("SAVEPOINT fetch_events_sp")
        cur.execute(f"""
            SELECT event_name, center_lat, center_lon,
                   start_time, end_time,
                   max_hail_size, confidence_score,
                   swath_polygon, swath_area_sqmi,
                   swath_area_km2, swath_area_method,
                   mrms_core_25_km2, mrms_core_40_km2
            FROM hail_events
            WHERE status = 'CONFIRMED'
              AND data_source = 'NEXRAD_REALTIME'
              AND {time_filter}
        """, (f"-{EVENT_WINDOW_MINUTES}",))
        rows = cur.fetchall()
        if pg:
            cur.execute("RELEASE SAVEPOINT fetch_events_sp")
    except Exception:
        try:
            if pg:
                conn.cursor().execute("ROLLBACK TO SAVEPOINT fetch_events_sp")
            cur = _dict_cursor(conn)
            cur.execute(f"""
                SELECT event_name, center_lat, center_lon,
                       start_time, end_time,
                       max_hail_size, confidence_score,
                       swath_polygon, swath_area_sqmi
                FROM hail_events
                WHERE status = 'CONFIRMED'
                  AND data_source = 'NEXRAD_REALTIME'
                  AND {time_filter}
            """, (f"-{EVENT_WINDOW_MINUTES}",))
            rows = cur.fetchall()
        except Exception:
            return []
    return [dict(r) for r in rows]


def _assign_events_to_swaths(
    events: List[dict],
    active_swaths: List[dict],
) -> Dict[str, List[dict]]:
    """
    Assign events to swaths using motion-coherence scoring.

    Returns dict: swath_id -> list of assigned events.
    New swaths get a fresh stable ID.
    """
    # Index active swaths by ID
    swath_map: Dict[str, dict] = {s['swath_id']: s for s in active_swaths}

    # Track which events are already assigned to each swath (from DB)
    assignments: Dict[str, List[dict]] = {}
    for sw in active_swaths:
        assignments[sw['swath_id']] = []

    # Sort events by start_time ascending
    events_sorted = sorted(events, key=lambda e: e['start_time'])

    # Track already-assigned event names to avoid duplicates
    assigned_names = set()
    # Also load existing member names from active swaths
    for sw in active_swaths:
        try:
            members = json.loads(sw.get('member_event_names', '[]') or '[]')
            for m in members:
                assigned_names.add(m)
        except (json.JSONDecodeError, TypeError):
            pass

    for ev in events_sorted:
        if ev['event_name'] in assigned_names:
            # Already assigned from a prior cycle; find which swath
            for sw_id, sw in swath_map.items():
                try:
                    members = json.loads(sw.get('member_event_names', '[]') or '[]')
                    if ev['event_name'] in members:
                        assignments[sw_id].append(ev)
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                # Member of a swath we no longer have active; re-evaluate
                assigned_names.discard(ev['event_name'])
                # Fall through to scoring below

        if ev['event_name'] in assigned_names:
            continue

        # Score against all active swaths within coarse filter
        best_score = -1.0
        best_sw_id = None

        for sw_id, sw in swath_map.items():
            # Coarse filter: raw distance
            raw_dist = _haversine_km(
                sw['centroid_lat'], sw['centroid_lon'],
                ev['center_lat'], ev['center_lon'],
            )
            if raw_dist > COARSE_FILTER_KM:
                continue

            score, dist = _compute_motion_score(sw, ev)
            if score >= MIN_MATCH_SCORE and score > best_score:
                best_score = score
                best_sw_id = sw_id

        if best_sw_id is not None:
            # Assign to existing swath
            assignments[best_sw_id].append(ev)
            assigned_names.add(ev['event_name'])
            # Update swath running state for next event's scoring
            sw = swath_map[best_sw_id]
            ev_start = _parse_utc(ev['start_time'])
            sw_last = _parse_utc(sw['last_seen_utc'])
            if ev_start >= sw_last:
                # Update bearing/velocity incrementally
                new_bearing = _bearing_deg(
                    sw['centroid_lat'], sw['centroid_lon'],
                    ev['center_lat'], ev['center_lon'],
                )
                dist_km = _haversine_km(
                    sw['centroid_lat'], sw['centroid_lon'],
                    ev['center_lat'], ev['center_lon'],
                )
                dt_hours = (ev_start - sw_last).total_seconds() / 3600.0
                new_vel = dist_km / dt_hours if dt_hours > 0 else sw.get('velocity_kmh', 0)
                # Exponential smoothing
                alpha = 0.4
                old_bearing = sw.get('directional_vector_deg') or new_bearing
                old_vel = sw.get('velocity_kmh') or new_vel
                # Smooth bearing (handle wraparound)
                diff = _angular_diff(old_bearing, new_bearing)
                if abs((new_bearing - old_bearing + 180) % 360 - 180) == diff:
                    smoothed_bearing = old_bearing + alpha * ((new_bearing - old_bearing + 180) % 360 - 180)
                else:
                    smoothed_bearing = new_bearing
                smoothed_bearing = smoothed_bearing % 360

                sw['directional_vector_deg'] = smoothed_bearing
                sw['velocity_kmh'] = old_vel * (1 - alpha) + new_vel * alpha
                sw['centroid_lat'] = ev['center_lat']
                sw['centroid_lon'] = ev['center_lon']
                sw['last_seen_utc'] = ev['end_time']
        else:
            # Create new swath
            new_id = _generate_stable_swath_id(ev)
            swath_map[new_id] = {
                'swath_id': new_id,
                'first_seen_utc': ev['start_time'],
                'last_seen_utc': ev['end_time'],
                'centroid_lat': ev['center_lat'],
                'centroid_lon': ev['center_lon'],
                'directional_vector_deg': 0.0,
                'velocity_kmh': 0.0,
                'area_km2': 0,
                'severe_core_km2': 0,
                'impact_score': 0,
                'lifecycle_state': None,
                'decay_cycles': 0,
                'member_event_names': '[]',
                'area_method': 'unknown',
                'geometry_quality': 'LOW',
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }
            assignments[new_id] = [ev]
            assigned_names.add(ev['event_name'])

    return assignments


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_swaths_geojson(
    simplify_meters: float = 0,
    lifecycle_states: Optional[List[str]] = None,
) -> List[dict]:
    """
    Fetch active swaths as GeoJSON-ready dicts.

    Args:
        simplify_meters: If > 0 and PostGIS available, apply
            ST_SimplifyPreserveTopology for lighter geometry at lower zoom.
        lifecycle_states: Filter by lifecycle state (default: non-EXPIRED).

    Returns list of swath dicts with ``geometry_geojson`` potentially
    simplified. When PostGIS is unavailable or simplify_meters is 0,
    returns raw stored geometry.
    """
    from src.db.engine import get_connection, is_postgres, placeholder as ph

    states = lifecycle_states or ['FORMING', 'ORGANIZING', 'MATURE', 'DECAYING']
    p = ph()
    pg = is_postgres()

    # Build geometry column expression
    if pg and simplify_meters > 0:
        geom_expr = (
            f"ST_AsGeoJSON(ST_SimplifyPreserveTopology(swath_geom, "
            f"{simplify_meters / 111320.0})) AS geometry_geojson_simplified"
        )
    else:
        geom_expr = "geometry_geojson"

    placeholders = ', '.join([p] * len(states))

    with get_connection() as conn:
        cur = _dict_cursor(conn)
        cur.execute(f"""
            SELECT swath_id, first_seen_utc, last_seen_utc,
                   centroid_lat, centroid_lon,
                   area_km2, severe_core_km2,
                   mean_hail_size, max_hail_size,
                   impact_score, impact_tier, lifecycle_state,
                   confidence_avg, confirmed_event_count,
                   directional_vector_deg, velocity_kmh,
                   area_method, geometry_quality,
                   updated_at, last_valid_swath_utc,
                   {geom_expr}
            FROM hail_swaths
            WHERE lifecycle_state IN ({placeholders})
            ORDER BY impact_score DESC
        """, tuple(states))
        rows = cur.fetchall()

    results = []
    for r in rows:
        d = dict(r)
        # Use simplified geometry if available
        if 'geometry_geojson_simplified' in d:
            d['geometry_geojson'] = d.pop('geometry_geojson_simplified')
        results.append(d)
    return results


def update_swaths(db_path: str = 'data/hailtracker_crm.db') -> int:
    """
    Main entry point: fetch CONFIRMED events, assign to swaths via
    motion coherence, aggregate metrics, persist.

    On success, sets ``last_valid_swath_utc`` on updated swaths so the
    API can report staleness.  On failure, existing swaths remain
    unchanged (last-known-good caching).

    Returns number of swaths upserted.
    """
    from src.db.engine import get_connection, is_postgres, placeholder as ph

    _ensure_table(db_path)

    with get_connection() as conn:
        try:
            events = _fetch_recent_events(conn)
            if not events:
                return 0

            active_swaths = _fetch_active_swaths(conn)

            # Assign events to swaths
            assignments = _assign_events_to_swaths(events, active_swaths)

            # Build swath map for previous state lookup
            prev_map = {s['swath_id']: s for s in active_swaths}

            upserted = 0
            upserted_ids = []
            for swath_id, assigned_events in assignments.items():
                if not assigned_events:
                    continue

                # Filter: require persistence threshold
                if len(assigned_events) < MIN_CONFIRMED_EVENTS:
                    severe_area = sum(
                        (ev.get('swath_area_sqmi', 0) or 0) * 2.59
                        for ev in assigned_events
                        if (ev.get('max_hail_size', 0) or 0) >= 2.0
                    )
                    if severe_area < MIN_SEVERE_CORE_KM2:
                        continue

                previous_swath = prev_map.get(swath_id)
                swath = _build_swath_from_events(swath_id, assigned_events, previous_swath)
                _upsert_swath(conn, swath)
                upserted += 1
                upserted_ids.append(swath_id)

            # Mark successfully updated swaths with last_valid_swath_utc
            if upserted_ids and is_postgres():
                p = ph()
                cur = conn.cursor()
                for sid in upserted_ids:
                    cur.execute(f"""
                        UPDATE hail_swaths
                        SET last_valid_swath_utc = NOW()
                        WHERE swath_id = {p}
                    """, (sid,))

            # Expire old swaths
            p = ph()
            now = 'NOW()' if is_postgres() else 'CURRENT_TIMESTAMP'
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=EXPIRE_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')
            cur = conn.cursor()
            cur.execute(f"""
                UPDATE hail_swaths
                SET lifecycle_state = 'EXPIRED', updated_at = {now}
                WHERE lifecycle_state != 'EXPIRED'
                  AND last_seen_utc < {p}
            """, (cutoff,))

            return upserted

        except Exception:
            # On failure, swaths remain unchanged in DB (last-known-good)
            logger.exception("Swath intelligence engine error — serving last known good swaths")
            return 0
