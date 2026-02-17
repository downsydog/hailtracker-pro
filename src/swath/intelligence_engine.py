"""
Swath Intelligence Engine v1.

Clusters CONFIRMED hail events into coherent, evolving swaths with
economic impact scores and lifecycle tracking.

Called as deferred work from storm_monitor._persist_tracker_events()
after hail_events and damage_grid persistence completes.
"""

import hashlib
import json
import logging
import math
import os
import sqlite3
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPATIAL_PROXIMITY_KM = 40.0
TEMPORAL_PROXIMITY_MIN = 45.0
MIN_CONFIRMED_EVENTS = 2
MIN_SEVERE_CORE_KM2 = 5.0
EXPIRE_MINUTES = 45.0
MATURE_CORE_KM2 = 10.0
MATURE_IMPACT = 60

# ---------------------------------------------------------------------------
# Geo utilities (self-contained, copied from storm_cell_tracker pattern)
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


def _time_gap_minutes(ev_a: dict, ev_b: dict) -> float:
    """Minimum temporal gap (minutes) between two events' time ranges."""
    a_start = datetime.fromisoformat(ev_a['start_time'])
    a_end = datetime.fromisoformat(ev_a['end_time'])
    b_start = datetime.fromisoformat(ev_b['start_time'])
    b_end = datetime.fromisoformat(ev_b['end_time'])
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    if latest_start <= earliest_end:
        return 0.0  # overlapping
    return (latest_start - earliest_end).total_seconds() / 60.0


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
    # Column migration (idempotent)
    for col_def in [
        ('area_method', "TEXT DEFAULT 'unknown'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE hail_swaths ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass  # column already exists
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------

def _cluster_events(events: List[dict]) -> List[List[dict]]:
    """
    Single-link BFS clustering of events by spatial + temporal proximity.

    Returns list of clusters (each a list of event dicts sorted by start_time).
    Only clusters meeting the persistence threshold are returned.
    """
    n = len(events)
    if n == 0:
        return []

    # Build adjacency list
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

    # BFS connected components
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

    # Filter by persistence threshold
    result = []
    for cluster in clusters:
        if len(cluster) >= MIN_CONFIRMED_EVENTS:
            result.append(cluster)
            continue
        # Check severe core area (sum of swath areas for >= 2.0" events)
        severe_area = sum(
            (ev.get('swath_area_sqmi', 0) or 0) * 2.59
            for ev in cluster
            if (ev.get('max_hail_size', 0) or 0) >= 2.0
        )
        if severe_area >= MIN_SEVERE_CORE_KM2:
            result.append(cluster)

    return result


# ---------------------------------------------------------------------------
# Area computation
# ---------------------------------------------------------------------------

def _compute_area_km2(
    geojson_strings: List[Optional[str]],
    centroid_lat: float,
    cluster: Optional[List[dict]] = None,
) -> Tuple[float, object, str]:
    """
    Compute swath area in km2 with fallback chain.

    Returns (area_km2, union_geometry_or_None, area_method).
    area_method: 'polygon_union' | 'sum_sqmi' | 'radius_proxy' | 'unknown'
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
        # Conservative: use max radius from centroid, minimum 3km
        r_km = max(3.0, max_r)
        area_km2 = math.pi * r_km ** 2
        return round(area_km2, 3), None, 'radius_proxy'

    return 0.0, None, 'unknown'


# ---------------------------------------------------------------------------
# Impact scoring
# ---------------------------------------------------------------------------

def _compute_impact_score(
    cluster: List[dict],
    severe_core_km2: float,
    duration_min: float,
) -> int:
    """
    Economic impact score (0-100).

    Weights:
      30 pts: fraction of events with max_hail_size >= 2.0"
      20 pts: fraction of events with max_hail_size >= 1.5"
      20 pts: severe_core_km2 magnitude (capped at 100km2)
      10 pts: persistence duration (capped at 60min)
      20 pts: urban/fleet density placeholder (stub = 0.5)
    """
    n = len(cluster)
    if n == 0:
        return 0

    frac_2in = sum(1 for ev in cluster if (ev.get('max_hail_size', 0) or 0) >= 2.0) / n
    frac_1_5in = sum(1 for ev in cluster if (ev.get('max_hail_size', 0) or 0) >= 1.5) / n

    pts_severe = frac_2in * 30
    pts_signif = frac_1_5in * 20
    pts_core = min(1.0, severe_core_km2 / 100.0) * 20
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
# Lifecycle model
# ---------------------------------------------------------------------------

def _compute_lifecycle(
    event_count: int,
    growth_rate: float,
    severe_core_km2: float,
    impact_score: int,
    last_seen_utc: str,
    previous_state: Optional[str],
    decay_cycles: int,
) -> Tuple[str, int]:
    """
    Determine lifecycle state and update decay cycle counter.

    Returns (new_state, new_decay_cycles).
    """
    now = datetime.now(timezone.utc)
    try:
        last_seen = datetime.fromisoformat(last_seen_utc)
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        last_seen = now

    minutes_since_last = (now - last_seen).total_seconds() / 60.0

    # EXPIRED is terminal
    if previous_state == 'EXPIRED':
        return 'EXPIRED', decay_cycles

    # Check expiration
    if minutes_since_last > EXPIRE_MINUTES:
        return 'EXPIRED', decay_cycles

    # Track consecutive negative growth
    new_decay = decay_cycles + 1 if growth_rate < 0 else 0

    # DECAYING: consecutive negative growth from MATURE or already DECAYING
    if previous_state in ('MATURE', 'DECAYING') and new_decay >= 2:
        return 'DECAYING', new_decay

    # MATURE: never downgrade except to DECAYING/EXPIRED
    if previous_state == 'MATURE':
        return 'MATURE', new_decay

    # Check MATURE transition
    if severe_core_km2 >= MATURE_CORE_KM2 and impact_score >= MATURE_IMPACT:
        return 'MATURE', new_decay

    # ORGANIZING: >= 2 events + positive growth
    if event_count >= 2 and growth_rate > 0:
        return 'ORGANIZING', new_decay

    # FORMING: default for new/single-event swaths
    if event_count <= 1 or previous_state in (None, 'FORMING'):
        return 'FORMING', new_decay

    # Multi-event but no positive growth yet
    return 'ORGANIZING', new_decay


# ---------------------------------------------------------------------------
# Swath builder
# ---------------------------------------------------------------------------

def _generate_swath_id(cluster: List[dict]) -> str:
    """Deterministic swath ID from sorted member event names."""
    names = sorted(ev['event_name'] for ev in cluster)
    earliest = min(ev['start_time'] for ev in cluster)
    date_str = earliest[:10].replace('-', '')

    centroid_lat = sum(ev['center_lat'] for ev in cluster) / len(cluster)
    centroid_lon = sum(ev['center_lon'] for ev in cluster) / len(cluster)

    hash_input = '|'.join(names).encode()
    hash8 = hashlib.md5(hash_input).hexdigest()[:8]

    return f"SWATH_{date_str}_{centroid_lat:.2f}_{centroid_lon:.2f}_{hash8}"


def _build_swath(cluster: List[dict], previous_swath: Optional[dict]) -> dict:
    """
    Compute all swath fields from a cluster of event dicts.

    previous_swath: existing DB row (dict) for growth rate + lifecycle, or None.
    """
    n = len(cluster)
    swath_id = _generate_swath_id(cluster)

    # Time range
    first_seen = min(ev['start_time'] for ev in cluster)
    last_seen = max(ev['end_time'] for ev in cluster)
    first_dt = datetime.fromisoformat(first_seen)
    last_dt = datetime.fromisoformat(last_seen)
    duration_min = max(0, (last_dt - first_dt).total_seconds() / 60.0)

    # Centroid
    centroid_lat = sum(ev['center_lat'] for ev in cluster) / n
    centroid_lon = sum(ev['center_lon'] for ev in cluster) / n

    # Hail sizes
    hail_sizes = [(ev.get('max_hail_size', 0) or 0) for ev in cluster]
    max_hail = max(hail_sizes) if hail_sizes else 0
    mean_hail = sum(hail_sizes) / n if n > 0 else 0

    # Confidence
    confs = [(ev.get('confidence_score', 0) or 0) for ev in cluster]
    confidence_avg = sum(confs) / n if n > 0 else 0

    # Area (with fallback chain)
    swath_polygons = [ev.get('swath_polygon') for ev in cluster]
    area_km2, union_geom, area_method = _compute_area_km2(
        swath_polygons, centroid_lat, cluster=cluster,
    )

    # Severe core: area from events with hail >= 2.0"
    severe_events = [ev for ev in cluster if (ev.get('max_hail_size', 0) or 0) >= 2.0]
    severe_polygons = [ev.get('swath_polygon') for ev in severe_events]
    if severe_events:
        severe_core_km2, _, _ = _compute_area_km2(
            severe_polygons, centroid_lat, cluster=severe_events,
        )
    else:
        severe_core_km2 = 0.0

    # Enhance severe core with MRMS 25mm core data if available
    mrms_core_km2 = sum(
        (ev.get('mrms_core_25_km2', 0) or 0) for ev in cluster
    )
    if mrms_core_km2 > 0:
        severe_core_km2 = max(severe_core_km2, mrms_core_km2)

    # Direction and velocity
    earliest_ev = cluster[0]
    latest_ev = cluster[-1]
    if n >= 2:
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
        direction_deg = 0.0
        velocity_kmh = 0.0

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
            prev_dt = datetime.fromisoformat(prev_updated)
            delta_min = (datetime.now(timezone.utc) - prev_dt.replace(tzinfo=timezone.utc)).total_seconds() / 60.0
            if delta_min > 0:
                growth_rate = (area_km2 - prev_area) / delta_min
        except (ValueError, TypeError):
            pass

    # Impact
    impact_score = _compute_impact_score(cluster, severe_core_km2, duration_min)
    impact_tier = _get_tier(impact_score)

    # Lifecycle
    lifecycle_state, decay_cycles = _compute_lifecycle(
        event_count=n,
        growth_rate=growth_rate,
        severe_core_km2=severe_core_km2,
        impact_score=impact_score,
        last_seen_utc=last_seen,
        previous_state=prev_state,
        decay_cycles=prev_decay,
    )

    # Geometry GeoJSON
    geometry_geojson = None
    if union_geom is not None:
        try:
            from shapely.geometry import mapping
            geometry_geojson = json.dumps(mapping(union_geom))
        except Exception:
            pass

    member_event_names = json.dumps(sorted(ev['event_name'] for ev in cluster))

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
    }


# ---------------------------------------------------------------------------
# Public API
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
    area_method, updated_at
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
    ?, CURRENT_TIMESTAMP
)
ON CONFLICT(swath_id) DO UPDATE SET
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
    updated_at = CURRENT_TIMESTAMP
"""


def update_swaths(db_path: str = 'data/hailtracker_crm.db') -> int:
    """
    Main entry point: read CONFIRMED events, cluster into swaths, persist.

    Returns number of swaths upserted.
    """
    _ensure_table(db_path)

    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    try:
        # Read CONFIRMED events (try extended columns, fallback to base)
        try:
            rows = conn.execute("""
                SELECT event_name, center_lat, center_lon,
                       start_time, end_time,
                       max_hail_size, confidence_score,
                       swath_polygon, swath_area_sqmi,
                       swath_area_km2, mrms_core_25_km2
                FROM hail_events
                WHERE status = 'CONFIRMED'
                  AND data_source = 'NEXRAD_REALTIME'
            """).fetchall()
        except Exception:
            rows = conn.execute("""
                SELECT event_name, center_lat, center_lon,
                       start_time, end_time,
                       max_hail_size, confidence_score,
                       swath_polygon, swath_area_sqmi
                FROM hail_events
                WHERE status = 'CONFIRMED'
                  AND data_source = 'NEXRAD_REALTIME'
            """).fetchall()

        if not rows:
            return 0

        events = [dict(r) for r in rows]

        # Cluster
        clusters = _cluster_events(events)
        if not clusters:
            return 0

        upserted = 0
        for cluster in clusters:
            swath_id = _generate_swath_id(cluster)

            # Read previous swath for growth rate + lifecycle continuity
            prev_row = conn.execute(
                "SELECT * FROM hail_swaths WHERE swath_id = ?",
                (swath_id,),
            ).fetchone()
            previous_swath = dict(prev_row) if prev_row else None

            swath = _build_swath(cluster, previous_swath)

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
            ))
            upserted += 1

        # Expire old swaths
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=EXPIRE_MINUTES)).isoformat()
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
