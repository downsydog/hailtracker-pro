"""
Damage Grid — Per-cell hail damage heatmap across event swaths.

Generates a grid of cells over an event bounding box, computes
authoritative hail size, damage probability, severity, and confidence
for each cell. Persists to hail_damage_grid table and serves as GeoJSON.
"""

import math
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.db.engine import get_raw_connection, is_postgres
from src.db.compat import sql

logger = logging.getLogger(__name__)

# --- Config from env ---
CELL_SIZE_KM = float(os.environ.get("DAMAGE_GRID_CELL_KM", "2.0"))
MAX_CELLS = int(os.environ.get("DAMAGE_GRID_MAX_CELLS", "40000"))
MIN_PROB = float(os.environ.get("DAMAGE_GRID_MIN_PROB", "0.1"))
MIN_CONF = float(os.environ.get("DAMAGE_GRID_MIN_CONF", "45"))

# Severity thresholds
SEVERITY_THRESHOLDS = [
    (0.80, "CATASTROPHIC"),
    (0.55, "SEVERE"),
    (0.30, "MODERATE"),
    (0.10, "LIGHT"),
    (0.00, "NONE"),
]

# Evidence mask bits
EV_MRMS = 1 << 0
EV_IDW_3 = 1 << 1
EV_IDW_1 = 1 << 2
EV_DWELL = 1 << 3


def _sigmoid(x: float) -> float:
    """Standard sigmoid, clamped to avoid overflow."""
    x = max(-20.0, min(20.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# =========================================================================
# GRID GENERATION
# =========================================================================

def generate_damage_grid(
    bbox: Dict[str, float],
    detections: List[Dict],
    event_confidence: float = 50.0,
    storm_speed_kmh: float = 0.0,
    storm_direction_deg: float = 0.0,
    cell_size_km: float = None,
    mrms_cache=None,
) -> List[Dict]:
    """
    Build a damage grid over a bounding box.

    Args:
        bbox: dict with bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon
        detections: list of detection dicts with lat, lon, mesh_mm (or hail_score)
        event_confidence: event-level confidence (0-100)
        storm_speed_kmh: storm translation speed
        storm_direction_deg: storm direction (degrees from north)
        cell_size_km: override cell size
        mrms_cache: optional MRMS cache object with query_point(lat, lon)

    Returns:
        list of cell dicts ready for DB insertion
    """
    cell_km = cell_size_km or CELL_SIZE_KM

    min_lat = bbox.get("bbox_min_lat", 0)
    max_lat = bbox.get("bbox_max_lat", 0)
    min_lon = bbox.get("bbox_min_lon", 0)
    max_lon = bbox.get("bbox_max_lon", 0)

    if max_lat <= min_lat or max_lon <= min_lon:
        return []

    # Adaptive cell size to stay under MAX_CELLS
    cell_km = _adaptive_cell_size(min_lat, max_lat, min_lon, max_lon, cell_km)

    center_lat = (min_lat + max_lat) / 2.0
    dlat = cell_km / 110.574
    dlon = cell_km / (111.320 * max(math.cos(math.radians(center_lat)), 0.01))

    # Expand bbox by 1 cell margin
    min_lat -= dlat
    max_lat += dlat
    min_lon -= dlon
    max_lon += dlon

    # Build detection index for IDW
    det_points = []
    for d in detections:
        mm = d.get("mesh_mm", 0) or d.get("hail_size", 0) * 25.4
        if mm > 0:
            det_points.append((d["lat"], d["lon"], mm))

    # Check MRMS availability
    mrms_ok = False
    if mrms_cache is not None:
        try:
            mrms_ok = getattr(mrms_cache, "loaded", False)
        except Exception:
            pass

    cells = []
    now_iso = datetime.utcnow().isoformat() + "Z"

    lat = min_lat + dlat / 2.0
    i = 0
    while lat < max_lat:
        lon = min_lon + dlon / 2.0
        j = 0
        while lon < max_lon:
            cell = _compute_cell(
                i=i, j=j,
                center_lat=lat, center_lon=lon,
                dlat=dlat, dlon=dlon,
                cell_km=cell_km,
                det_points=det_points,
                event_confidence=event_confidence,
                storm_speed_kmh=storm_speed_kmh,
                mrms_cache=mrms_cache if mrms_ok else None,
                now_iso=now_iso,
            )
            if cell is not None:
                cells.append(cell)
            lon += dlon
            j += 1
        lat += dlat
        i += 1

    return cells


def _adaptive_cell_size(
    min_lat: float, max_lat: float,
    min_lon: float, max_lon: float,
    cell_km: float,
) -> float:
    """Increase cell size if grid would exceed MAX_CELLS."""
    center_lat = (min_lat + max_lat) / 2.0
    lat_span_km = (max_lat - min_lat) * 110.574
    lon_span_km = (max_lon - min_lon) * 111.320 * max(math.cos(math.radians(center_lat)), 0.01)

    while cell_km < 20.0:
        rows = max(1, math.ceil(lat_span_km / cell_km))
        cols = max(1, math.ceil(lon_span_km / cell_km))
        if rows * cols <= MAX_CELLS:
            break
        cell_km *= 1.5
    return cell_km


def _compute_cell(
    i: int, j: int,
    center_lat: float, center_lon: float,
    dlat: float, dlon: float,
    cell_km: float,
    det_points: List[Tuple[float, float, float]],
    event_confidence: float,
    storm_speed_kmh: float,
    mrms_cache,
    now_iso: str,
) -> Optional[Dict]:
    """Compute damage metrics for a single grid cell."""

    evidence_mask = 0
    hail_mm = 0.0

    # 1) Try MRMS first
    if mrms_cache is not None:
        try:
            mesh_val = mrms_cache.query_point(center_lat, center_lon)
            if mesh_val is not None and mesh_val > 0:
                hail_mm = float(mesh_val)
                evidence_mask |= EV_MRMS
        except Exception:
            pass

    # 2) Fallback: IDW from detection points
    if hail_mm <= 0 and det_points:
        idw_mm, idw_count = _idw_hail(center_lat, center_lon, det_points, radius_km=15.0)
        if idw_mm > 0:
            hail_mm = idw_mm
            if idw_count >= 3:
                evidence_mask |= EV_IDW_3
            if idw_count >= 1:
                evidence_mask |= EV_IDW_1

    # Skip cells with no hail signal at all
    if hail_mm < 5.0:
        return None

    hail_in = round(hail_mm / 25.4, 2)

    # 3) Dwell seconds
    dwell_seconds = 0.0
    if storm_speed_kmh >= 5.0:
        dwell_seconds = _clamp((cell_km / storm_speed_kmh) * 3600.0, 5.0, 900.0)
        evidence_mask |= EV_DWELL

    # 4) Damage probability
    prob = _damage_probability(hail_mm, dwell_seconds)

    # 5) Severity
    severity = _severity_label(prob)

    # 6) Cell confidence
    conf = _cell_confidence(event_confidence, evidence_mask)

    return {
        "i": i, "j": j,
        "cell_size_km": cell_km,
        "center_lat": round(center_lat, 6),
        "center_lon": round(center_lon, 6),
        "bbox_min_lat": round(center_lat - dlat / 2, 6),
        "bbox_max_lat": round(center_lat + dlat / 2, 6),
        "bbox_min_lon": round(center_lon - dlon / 2, 6),
        "bbox_max_lon": round(center_lon + dlon / 2, 6),
        "authoritative_hail_mm": round(hail_mm, 1),
        "authoritative_hail_in": hail_in,
        "damage_probability": round(prob, 4),
        "damage_severity": severity,
        "cell_confidence": round(conf, 1),
        "dwell_seconds": round(dwell_seconds, 1),
        "evidence_mask": evidence_mask,
        "created_at": now_iso,
        "updated_at": now_iso,
    }


def _idw_hail(
    lat: float, lon: float,
    points: List[Tuple[float, float, float]],
    radius_km: float = 15.0,
    power: float = 2.0,
) -> Tuple[float, int]:
    """Inverse-distance weighted hail from detection points."""
    numer = 0.0
    denom = 0.0
    count = 0

    for plat, plon, mm in points:
        d_km = _haversine_km(lat, lon, plat, plon)
        if d_km > radius_km:
            continue
        if d_km < 0.01:
            return mm, 1  # exact hit
        w = 1.0 / (d_km ** power)
        numer += w * mm
        denom += w
        count += 1

    if denom > 0:
        return numer / denom, count
    return 0.0, 0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _damage_probability(hail_mm: float, dwell_seconds: float) -> float:
    """Deterministic damage probability model."""
    if hail_mm < 10:
        return 0.0

    size_score = _sigmoid((hail_mm - 18) / 7.0)
    severe_boost = _sigmoid((hail_mm - 32) / 6.0)
    dwell_factor = _clamp(dwell_seconds / 120.0, 0.0, 2.0)

    prob = 0.55 * size_score + 0.25 * severe_boost + 0.20 * (dwell_factor / 2.0)
    prob = _clamp(prob, 0.0, 1.0)

    if hail_mm < 15:
        prob *= 0.35

    return prob


def _severity_label(prob: float) -> str:
    """Map probability to severity label."""
    for threshold, label in SEVERITY_THRESHOLDS:
        if prob >= threshold:
            return label
    return "NONE"


def _cell_confidence(event_confidence: float, evidence_mask: int) -> float:
    """Adjust event confidence by local evidence."""
    conf = event_confidence
    if evidence_mask & EV_MRMS:
        conf += 10
    if evidence_mask & EV_IDW_3:
        conf += 5
    if not (evidence_mask & (EV_MRMS | EV_IDW_3 | EV_IDW_1)):
        conf -= 30
    return _clamp(conf, 0.0, 100.0)


# =========================================================================
# DATABASE PERSISTENCE
# =========================================================================

def ensure_damage_grid_table(db_path: str = "data/hailtracker_crm.db"):
    """Create hail_damage_grid table if it doesn't exist (idempotent)."""
    if is_postgres():
        conn = get_raw_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hail_damage_grid (
                id BIGSERIAL PRIMARY KEY,
                event_name TEXT NOT NULL,
                grid_version INTEGER NOT NULL DEFAULT 1,
                cell_size_km DOUBLE PRECISION NOT NULL,
                i INTEGER NOT NULL,
                j INTEGER NOT NULL,
                center_lat DOUBLE PRECISION NOT NULL,
                center_lon DOUBLE PRECISION NOT NULL,
                bbox_min_lat DOUBLE PRECISION NOT NULL,
                bbox_max_lat DOUBLE PRECISION NOT NULL,
                bbox_min_lon DOUBLE PRECISION NOT NULL,
                bbox_max_lon DOUBLE PRECISION NOT NULL,
                authoritative_hail_mm DOUBLE PRECISION NOT NULL DEFAULT 0,
                authoritative_hail_in DOUBLE PRECISION NOT NULL DEFAULT 0,
                damage_probability DOUBLE PRECISION NOT NULL DEFAULT 0,
                damage_severity TEXT NOT NULL DEFAULT 'NONE',
                cell_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
                dwell_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
                evidence_mask INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(event_name, grid_version, cell_size_km, i, j)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_damage_event ON hail_damage_grid(event_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_damage_bbox ON hail_damage_grid(bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_damage_center ON hail_damage_grid(center_lat, center_lon)")
        conn.commit()
        cur.close()
        conn.close()
    else:
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hail_damage_grid (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                grid_version INTEGER NOT NULL DEFAULT 1,
                cell_size_km REAL NOT NULL,
                i INTEGER NOT NULL,
                j INTEGER NOT NULL,
                center_lat REAL NOT NULL,
                center_lon REAL NOT NULL,
                bbox_min_lat REAL NOT NULL,
                bbox_max_lat REAL NOT NULL,
                bbox_min_lon REAL NOT NULL,
                bbox_max_lon REAL NOT NULL,
                authoritative_hail_mm REAL NOT NULL DEFAULT 0,
                authoritative_hail_in REAL NOT NULL DEFAULT 0,
                damage_probability REAL NOT NULL DEFAULT 0,
                damage_severity TEXT NOT NULL DEFAULT 'NONE',
                cell_confidence REAL NOT NULL DEFAULT 0,
                dwell_seconds REAL NOT NULL DEFAULT 0,
                evidence_mask INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(event_name, grid_version, cell_size_km, i, j)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_damage_event ON hail_damage_grid(event_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_damage_bbox ON hail_damage_grid(bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_damage_center ON hail_damage_grid(center_lat, center_lon)")
        conn.commit()
        conn.close()


def persist_damage_grid(
    event_name: str,
    cells: List[Dict],
    db_path: str = "data/hailtracker_crm.db",
    grid_version: int = 1,
):
    """
    Upsert damage grid cells for an event into the database.

    Idempotent: uses INSERT OR REPLACE on the unique key (SQLite) or
    INSERT ... ON CONFLICT ... DO UPDATE (PostgreSQL).
    """
    if not cells:
        return 0

    ensure_damage_grid_table(db_path)

    if is_postgres():
        conn = get_raw_connection()
        cur = conn.cursor()
        insert_sql = """
            INSERT INTO hail_damage_grid (
                event_name, grid_version, cell_size_km, i, j,
                center_lat, center_lon,
                bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon,
                authoritative_hail_mm, authoritative_hail_in,
                damage_probability, damage_severity, cell_confidence,
                dwell_seconds, evidence_mask, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_name, grid_version, cell_size_km, i, j) DO UPDATE SET
                center_lat = EXCLUDED.center_lat,
                center_lon = EXCLUDED.center_lon,
                bbox_min_lat = EXCLUDED.bbox_min_lat,
                bbox_max_lat = EXCLUDED.bbox_max_lat,
                bbox_min_lon = EXCLUDED.bbox_min_lon,
                bbox_max_lon = EXCLUDED.bbox_max_lon,
                authoritative_hail_mm = EXCLUDED.authoritative_hail_mm,
                authoritative_hail_in = EXCLUDED.authoritative_hail_in,
                damage_probability = EXCLUDED.damage_probability,
                damage_severity = EXCLUDED.damage_severity,
                cell_confidence = EXCLUDED.cell_confidence,
                dwell_seconds = EXCLUDED.dwell_seconds,
                evidence_mask = EXCLUDED.evidence_mask,
                updated_at = EXCLUDED.updated_at
        """
        inserted = 0
        for cell in cells:
            try:
                cur.execute("SAVEPOINT cell_sp")
                cur.execute(insert_sql, (
                    event_name, grid_version, float(cell["cell_size_km"]),
                    cell["i"], cell["j"],
                    float(cell["center_lat"]), float(cell["center_lon"]),
                    float(cell["bbox_min_lat"]), float(cell["bbox_max_lat"]),
                    float(cell["bbox_min_lon"]), float(cell["bbox_max_lon"]),
                    float(cell["authoritative_hail_mm"]), float(cell["authoritative_hail_in"]),
                    float(cell["damage_probability"]), cell["damage_severity"],
                    float(cell["cell_confidence"]), float(cell["dwell_seconds"]),
                    cell["evidence_mask"], cell["created_at"], cell["updated_at"],
                ))
                cur.execute("RELEASE SAVEPOINT cell_sp")
                inserted += 1
            except Exception as e:
                try:
                    cur.execute("ROLLBACK TO SAVEPOINT cell_sp")
                except Exception:
                    pass
                logger.warning("Failed to persist grid cell (%d,%d): %s", cell["i"], cell["j"], e)
        conn.commit()
        cur.close()
        conn.close()
        return inserted
    else:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        inserted = 0
        for cell in cells:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO hail_damage_grid (
                        event_name, grid_version, cell_size_km, i, j,
                        center_lat, center_lon,
                        bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon,
                        authoritative_hail_mm, authoritative_hail_in,
                        damage_probability, damage_severity, cell_confidence,
                        dwell_seconds, evidence_mask, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_name, grid_version, cell["cell_size_km"],
                    cell["i"], cell["j"],
                    cell["center_lat"], cell["center_lon"],
                    cell["bbox_min_lat"], cell["bbox_max_lat"],
                    cell["bbox_min_lon"], cell["bbox_max_lon"],
                    cell["authoritative_hail_mm"], cell["authoritative_hail_in"],
                    cell["damage_probability"], cell["damage_severity"],
                    cell["cell_confidence"], cell["dwell_seconds"],
                    cell["evidence_mask"], cell["created_at"], cell["updated_at"],
                ))
                inserted += 1
            except Exception as e:
                logger.warning("Failed to persist grid cell (%d,%d): %s", cell["i"], cell["j"], e)

        conn.commit()
        conn.close()
        return inserted


# =========================================================================
# QUERY + GEOJSON
# =========================================================================

def query_damage_grid(
    event_name: str,
    db_path: str = "data/hailtracker_crm.db",
    min_prob: float = 0.0,
    min_conf: float = 0.0,
    max_cells: int = 20000,
) -> List[Dict]:
    """Query damage grid cells for an event."""
    ensure_damage_grid_table(db_path)

    if is_postgres():
        conn = get_raw_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM hail_damage_grid
            WHERE event_name = %s
              AND damage_probability >= %s
              AND cell_confidence >= %s
            ORDER BY damage_probability DESC
            LIMIT %s
        """, (event_name, min_prob, min_conf, max_cells))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    else:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM hail_damage_grid
            WHERE event_name = ?
              AND damage_probability >= ?
              AND cell_confidence >= ?
            ORDER BY damage_probability DESC
            LIMIT ?
        """, (event_name, min_prob, min_conf, max_cells)).fetchall()
        conn.close()
        return [dict(r) for r in rows]


def query_damage_grid_bbox(
    min_lon: float, min_lat: float,
    max_lon: float, max_lat: float,
    db_path: str = "data/hailtracker_crm.db",
    min_prob: float = 0.0,
    min_conf: float = 0.0,
    max_cells: int = 20000,
) -> List[Dict]:
    """Query damage grid cells by bounding box."""
    ensure_damage_grid_table(db_path)

    if is_postgres():
        conn = get_raw_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM hail_damage_grid
            WHERE center_lat BETWEEN %s AND %s
              AND center_lon BETWEEN %s AND %s
              AND damage_probability >= %s
              AND cell_confidence >= %s
            ORDER BY damage_probability DESC
            LIMIT %s
        """, (min_lat, max_lat, min_lon, max_lon, min_prob, min_conf, max_cells))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    else:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM hail_damage_grid
            WHERE center_lat BETWEEN ? AND ?
              AND center_lon BETWEEN ? AND ?
              AND damage_probability >= ?
              AND cell_confidence >= ?
            ORDER BY damage_probability DESC
            LIMIT ?
        """, (min_lat, max_lat, min_lon, max_lon, min_prob, min_conf, max_cells)).fetchall()
        conn.close()
        return [dict(r) for r in rows]


def cells_to_geojson(cells: List[Dict]) -> Dict:
    """Convert grid cells to a GeoJSON FeatureCollection of bbox polygons."""
    features = []
    for c in cells:
        coords = [[
            [c["bbox_min_lon"], c["bbox_min_lat"]],
            [c["bbox_max_lon"], c["bbox_min_lat"]],
            [c["bbox_max_lon"], c["bbox_max_lat"]],
            [c["bbox_min_lon"], c["bbox_max_lat"]],
            [c["bbox_min_lon"], c["bbox_min_lat"]],
        ]]
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": coords},
            "properties": {
                "hail_mm": c.get("authoritative_hail_mm", 0),
                "hail_in": c.get("authoritative_hail_in", 0),
                "damage_probability": c.get("damage_probability", 0),
                "damage_severity": c.get("damage_severity", "NONE"),
                "cell_confidence": c.get("cell_confidence", 0),
                "dwell_seconds": c.get("dwell_seconds", 0),
                "evidence_mask": c.get("evidence_mask", 0),
                "event_name": c.get("event_name", ""),
            },
        })
    return {"type": "FeatureCollection", "features": features}
