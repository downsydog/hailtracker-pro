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
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

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
GEO_QUALITY_HIGH = {'cell_union', 'polygon_union'}
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
    a_start = datetime.fromisoformat(ev_a['start_time'])
    a_end = datetime.fromisoformat(ev_a['end_time'])
    b_start = datetime.fromisoformat(ev_b['start_time'])
    b_end = datetime.fromisoformat(ev_b['end_time'])
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    if latest_start <= earliest_end:
        return 0.0
    return (latest_start - earliest_end).total_seconds() / 60.0


def _parse_utc(s: str) -> datetime:
    """Parse ISO timestamp, ensure UTC timezone."""
    dt = datetime.fromisoformat(s)
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
    """Idempotent CREATE TABLE + indexes + column migration for hail_swaths."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
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

def _compute_area_km2(
    geojson_strings: List[Optional[str]],
    centroid_lat: float,
    cluster: Optional[List[dict]] = None,
) -> Tuple[float, object, str]:
    """
    Compute swath area in km2 with fallback chain.
    Returns (area_km2, union_geometry_or_None, area_method).
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
            area_deg2 = union.area
            cos_lat = math.cos(math.radians(centroid_lat))
            area_km2 = area_deg2 * (111.32 ** 2) * cos_lat
            if area_km2 > 0:
                return area_km2, union, 'polygon_union'

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
    events_sorted = sorted(events, key=lambda e: e['start_time'])

    first_seen = min(ev['start_time'] for ev in events)
    last_seen = max(ev['end_time'] for ev in events)
    # Preserve original first_seen if swath existed before
    if previous_swath and previous_swath.get('first_seen_utc'):
        prev_first = previous_swath['first_seen_utc']
        if prev_first < first_seen:
            first_seen = prev_first

    first_dt = _parse_utc(first_seen)
    last_dt = _parse_utc(last_seen)
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

    # Geometry GeoJSON
    geometry_geojson = None
    if union_geom is not None:
        try:
            from shapely.geometry import mapping
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

_UPSERT_SQL = """
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
    ?, ?, ?,
    ?, ?,
    ?, ?,
    ?, ?,
    ?, ?, ?,
    ?, ?, ?,
    ?, ?,
    ?, ?,
    ?, ?,
    ?, ?, CURRENT_TIMESTAMP
)
ON CONFLICT(swath_id) DO UPDATE SET
    first_seen_utc = excluded.first_seen_utc,
    last_seen_utc = excluded.last_seen_utc,
    centroid_lat = excluded.centroid_lat,
    centroid_lon = excluded.centroid_lon,
    area_km2 = excluded.area_km2,
    severe_core_km2 = excluded.severe_core_km2,
    mean_hail_size = excluded.mean_hail_size,
    max_hail_size = MAX(hail_swaths.max_hail_size, excluded.max_hail_size),
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
    updated_at = CURRENT_TIMESTAMP
"""


def _upsert_swath(conn, swath: dict) -> None:
    """Execute UPSERT for a single swath dict."""
    conn.execute(_UPSERT_SQL, (
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
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=EVENT_WINDOW_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        rows = conn.execute("""
            SELECT swath_id, first_seen_utc, last_seen_utc,
                   centroid_lat, centroid_lon,
                   directional_vector_deg, velocity_kmh,
                   area_km2, severe_core_km2, impact_score,
                   lifecycle_state, decay_cycles, member_event_names,
                   area_method, geometry_quality, updated_at
            FROM hail_swaths
            WHERE lifecycle_state != 'EXPIRED'
              AND last_seen_utc >= ?
        """, (cutoff,)).fetchall()
    except Exception:
        return []
    return [dict(r) for r in rows]


def _fetch_recent_events(conn) -> List[dict]:
    """Fetch CONFIRMED events from recent window."""
    # Try extended columns, fallback to base
    try:
        rows = conn.execute("""
            SELECT event_name, center_lat, center_lon,
                   start_time, end_time,
                   max_hail_size, confidence_score,
                   swath_polygon, swath_area_sqmi,
                   swath_area_km2, swath_area_method,
                   mrms_core_25_km2, mrms_core_40_km2
            FROM hail_events
            WHERE status = 'CONFIRMED'
              AND data_source = 'NEXRAD_REALTIME'
              AND start_time >= datetime('now', ? || ' minutes')
        """, (f"-{EVENT_WINDOW_MINUTES}",)).fetchall()
    except Exception:
        try:
            rows = conn.execute("""
                SELECT event_name, center_lat, center_lon,
                       start_time, end_time,
                       max_hail_size, confidence_score,
                       swath_polygon, swath_area_sqmi
                FROM hail_events
                WHERE status = 'CONFIRMED'
                  AND data_source = 'NEXRAD_REALTIME'
            """).fetchall()
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

def update_swaths(db_path: str = 'data/hailtracker_crm.db') -> int:
    """
    Main entry point: fetch CONFIRMED events, assign to swaths via
    motion coherence, aggregate metrics, persist.

    Returns number of swaths upserted.
    """
    _ensure_table(db_path)

    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

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

        # Expire old swaths (use space-separated format to match DB timestamps)
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=EXPIRE_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            UPDATE hail_swaths
            SET lifecycle_state = 'EXPIRED', updated_at = CURRENT_TIMESTAMP
            WHERE lifecycle_state != 'EXPIRED'
              AND last_seen_utc < ?
        """, (cutoff,))

        conn.commit()
        return upserted

    except Exception:
        logger.exception("Swath intelligence engine error")
        return 0
    finally:
        conn.close()
