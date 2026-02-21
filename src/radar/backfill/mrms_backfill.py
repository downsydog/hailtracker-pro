"""
MRMS MESH Historical Backfill — core algorithm.

Fills the 90-day data gap between delayed NOAA Storm Events and
real-time NEXRAD detections by fetching historical MRMS MESH grids,
extracting hail blobs, stitching them into storm tracks, and
persisting them as hail_events with data_source='MRMS_BACKFILL'.

Components:
    - extract_conus_blobs()  — national-scale blob detection via scipy
    - OfflineTracker          — centroid-based track stitching
    - persist_tracks()        — UPSERT into hail_events
    - dedupe_against_existing() — cross-source de-duplication
    - run_backfill()          — main orchestrator
"""

import json
import logging
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.radar.backfill.iowa_archive import IowaArchiveFetcher

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class HailBlob:
    """A single contiguous hail region from one MRMS grid timestamp."""

    blob_id: int
    timestamp: datetime
    centroid_lat: float
    centroid_lon: float
    max_mesh_mm: float
    area_km2: float
    bbox: Tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    polygon_geojson: str
    core_15_km2: float = 0.0
    core_25_km2: float = 0.0
    core_40_km2: float = 0.0
    core_15_geojson: Optional[str] = None
    core_25_geojson: Optional[str] = None
    core_40_geojson: Optional[str] = None


@dataclass
class Track:
    """A storm track assembled from blobs across multiple timesteps."""

    track_id: int
    blobs: List[HailBlob] = field(default_factory=list)
    missed_ticks: int = 0

    @property
    def start_time(self) -> datetime:
        return self.blobs[0].timestamp

    @property
    def end_time(self) -> datetime:
        return self.blobs[-1].timestamp

    @property
    def duration_minutes(self) -> float:
        dt = (self.end_time - self.start_time).total_seconds() / 60.0
        return max(dt, 0.0)

    @property
    def max_mesh_mm(self) -> float:
        return max(b.max_mesh_mm for b in self.blobs)

    @property
    def centroid_lat(self) -> float:
        total_area = sum(b.area_km2 for b in self.blobs)
        if total_area <= 0:
            return np.mean([b.centroid_lat for b in self.blobs])
        return sum(b.centroid_lat * b.area_km2 for b in self.blobs) / total_area

    @property
    def centroid_lon(self) -> float:
        total_area = sum(b.area_km2 for b in self.blobs)
        if total_area <= 0:
            return np.mean([b.centroid_lon for b in self.blobs])
        return sum(b.centroid_lon * b.area_km2 for b in self.blobs) / total_area

    @property
    def last_centroid(self) -> Tuple[float, float]:
        return (self.blobs[-1].centroid_lat, self.blobs[-1].centroid_lon)

    @property
    def total_area_km2(self) -> float:
        return max(b.area_km2 for b in self.blobs)

    def swath_polygon_geojson(self) -> Optional[str]:
        """Union of all blob polygons into a merged swath."""
        try:
            from shapely.geometry import shape as shapely_shape, mapping
            from shapely.ops import unary_union
        except ImportError:
            # Return the largest blob's polygon
            biggest = max(self.blobs, key=lambda b: b.area_km2)
            return biggest.polygon_geojson

        geoms = []
        for b in self.blobs:
            try:
                geoj = json.loads(b.polygon_geojson)
                g = shapely_shape(geoj)
                if g.is_valid:
                    geoms.append(g)
                else:
                    geoms.append(g.buffer(0))
            except Exception:
                continue

        if not geoms:
            return self.blobs[0].polygon_geojson

        union = unary_union(geoms)
        if union.is_empty:
            return self.blobs[0].polygon_geojson

        return json.dumps(mapping(union))

    def merged_core_geojson(self, threshold: int) -> Tuple[Optional[str], float]:
        """Union the core polygons at a given threshold (15/25/40)."""
        attr_geojson = f"core_{threshold}_geojson"
        attr_km2 = f"core_{threshold}_km2"

        # Collect non-None core polygons
        geojsons = []
        total_km2 = 0.0
        for b in self.blobs:
            gj = getattr(b, attr_geojson, None)
            if gj:
                geojsons.append(gj)
            total_km2 = max(total_km2, getattr(b, attr_km2, 0.0))

        if not geojsons:
            return None, total_km2

        try:
            from shapely.geometry import shape as shapely_shape, mapping
            from shapely.ops import unary_union

            geoms = []
            for gj_str in geojsons:
                g = shapely_shape(json.loads(gj_str))
                if not g.is_valid:
                    g = g.buffer(0)
                geoms.append(g)

            union = unary_union(geoms)
            if union.is_empty:
                return None, 0.0

            # Recompute area from union
            centroid_lat = self.centroid_lat
            cos_lat = math.cos(math.radians(centroid_lat))
            area_km2 = union.area * (111.32 ** 2) * cos_lat

            return json.dumps(mapping(union)), round(area_km2, 3)
        except ImportError:
            return geojsons[0] if geojsons else None, total_km2


# ---------------------------------------------------------------------------
# Blob extraction
# ---------------------------------------------------------------------------

def extract_conus_blobs(
    grid: Dict,
    min_mesh_mm: float = 15.0,
    min_area_km2: float = 5.0,
    timestamp: Optional[datetime] = None,
) -> List[HailBlob]:
    """
    Extract contiguous hail blobs from a full CONUS MRMS grid.

    Uses scipy.ndimage.label() for connected-component labeling (C-extension,
    handles the ~24M-cell CONUS grid in milliseconds).
    """
    from scipy.ndimage import label as ndimage_label

    lats = grid["lats"]
    lons = grid["lons"]
    mesh = grid["mesh_mm"]

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    # Step 1: threshold
    mask = mesh >= min_mesh_mm
    if not np.any(mask):
        return []

    # Step 2: connected components
    labeled, n_features = ndimage_label(mask)
    if n_features == 0:
        return []

    # Pre-compute cell area (varies with latitude)
    lat_step = abs(float(lats[1] - lats[0])) if len(lats) > 1 else 0.01
    lon_step = abs(float(lons[1] - lons[0])) if len(lons) > 1 else 0.01

    blobs = []
    blob_id = 0

    for label_idx in range(1, n_features + 1):
        rows, cols = np.where(labeled == label_idx)
        if len(rows) == 0:
            continue

        # Component cell coordinates
        cell_lats = lats[rows]
        cell_lons = lons[cols]
        cell_mesh = mesh[rows, cols]

        # Centroid
        centroid_lat = float(np.mean(cell_lats))
        centroid_lon = float(np.mean(cell_lons))

        # Area (cell count × cell area at mean latitude)
        cos_lat = math.cos(math.radians(centroid_lat))
        cell_area_km2 = (lat_step * 111.32) * (lon_step * 111.32 * cos_lat)
        area_km2 = float(len(rows)) * cell_area_km2

        if area_km2 < min_area_km2:
            continue

        # Peak MESH
        max_mesh = float(np.max(cell_mesh))

        # Bounding box
        bbox = (
            float(np.min(cell_lons)) - lon_step / 2,
            float(np.min(cell_lats)) - lat_step / 2,
            float(np.max(cell_lons)) + lon_step / 2,
            float(np.max(cell_lats)) + lat_step / 2,
        )

        # Build polygon (convex hull of cell center points)
        polygon_geojson = _build_blob_polygon(cell_lats, cell_lons, lat_step, lon_step)

        # Multi-threshold cores (25mm, 40mm within this component)
        core_15_km2 = area_km2  # The blob itself IS the 15mm core
        core_15_geojson = polygon_geojson

        core_25_km2, core_25_geojson = _extract_sub_core(
            mesh, rows, cols, lats, lons, 25.0, lat_step, lon_step, centroid_lat
        )
        core_40_km2, core_40_geojson = _extract_sub_core(
            mesh, rows, cols, lats, lons, 40.0, lat_step, lon_step, centroid_lat
        )

        blob_id += 1
        blobs.append(HailBlob(
            blob_id=blob_id,
            timestamp=timestamp,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            max_mesh_mm=max_mesh,
            area_km2=round(area_km2, 3),
            bbox=bbox,
            polygon_geojson=polygon_geojson,
            core_15_km2=round(core_15_km2, 3),
            core_25_km2=round(core_25_km2, 3),
            core_40_km2=round(core_40_km2, 3),
            core_15_geojson=core_15_geojson,
            core_25_geojson=core_25_geojson,
            core_40_geojson=core_40_geojson,
        ))

    return blobs


def _build_blob_polygon(
    cell_lats: np.ndarray,
    cell_lons: np.ndarray,
    lat_step: float,
    lon_step: float,
) -> str:
    """Build a GeoJSON polygon from blob cell coordinates.

    Uses shapely convex hull for speed.  Falls back to bounding box.
    """
    try:
        from shapely.geometry import MultiPoint, mapping

        points = list(zip(cell_lons.tolist(), cell_lats.tolist()))
        if len(points) < 3:
            # Buffer a point/line
            mp = MultiPoint(points)
            poly = mp.buffer(max(lat_step, lon_step) * 0.6)
        else:
            mp = MultiPoint(points)
            poly = mp.convex_hull
            if poly.geom_type == "Point" or poly.geom_type == "LineString":
                poly = poly.buffer(max(lat_step, lon_step) * 0.6)

        return json.dumps(mapping(poly))
    except ImportError:
        pass

    # Fallback: bounding box
    min_lon = float(np.min(cell_lons)) - lon_step / 2
    min_lat = float(np.min(cell_lats)) - lat_step / 2
    max_lon = float(np.max(cell_lons)) + lon_step / 2
    max_lat = float(np.max(cell_lats)) + lat_step / 2
    bbox_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, max_lat], [max_lon, max_lat],
            [max_lon, min_lat], [min_lon, min_lat],
            [min_lon, max_lat],
        ]],
    }
    return json.dumps(bbox_geojson)


def _extract_sub_core(
    mesh: np.ndarray,
    parent_rows: np.ndarray,
    parent_cols: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    threshold_mm: float,
    lat_step: float,
    lon_step: float,
    centroid_lat: float,
) -> Tuple[float, Optional[str]]:
    """Extract a sub-threshold core within an existing blob."""
    sub_mask = mesh[parent_rows, parent_cols] >= threshold_mm
    if not np.any(sub_mask):
        return 0.0, None

    sub_lats = lats[parent_rows[sub_mask]]
    sub_lons = lons[parent_cols[sub_mask]]
    n_cells = int(np.sum(sub_mask))

    cos_lat = math.cos(math.radians(centroid_lat))
    cell_area_km2 = (lat_step * 111.32) * (lon_step * 111.32 * cos_lat)
    area_km2 = n_cells * cell_area_km2

    geojson = _build_blob_polygon(sub_lats, sub_lons, lat_step, lon_step)
    return round(area_km2, 3), geojson


# ---------------------------------------------------------------------------
# Haversine helper
# ---------------------------------------------------------------------------

_R_KM = 6371.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return _R_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Offline tracker
# ---------------------------------------------------------------------------

class OfflineTracker:
    """
    Stitch HailBlobs across time into storm tracks.

    Simple greedy centroid matching: for each new tick's blobs, match to
    the nearest active track within match_distance_km.  Unmatched blobs
    start new tracks.  Tracks with max_missed consecutive missed ticks
    are finalized.
    """

    def __init__(self, match_distance_km: float = 60.0, max_missed: int = 3):
        self.match_distance_km = match_distance_km
        self.max_missed = max_missed
        self.active_tracks: Dict[int, Track] = {}
        self.finalized_tracks: List[Track] = []
        self._next_id = 1

    def ingest_tick(self, blobs: List[HailBlob]) -> None:
        """Process one timestep's blobs."""
        matched_track_ids = set()
        unmatched_blobs = []

        # Build candidate list: (distance, blob, track_id)
        candidates = []
        for blob in blobs:
            for tid, track in self.active_tracks.items():
                last_lat, last_lon = track.last_centroid
                dist = _haversine_km(
                    blob.centroid_lat, blob.centroid_lon,
                    last_lat, last_lon,
                )
                if dist <= self.match_distance_km:
                    candidates.append((dist, blob, tid))

        # Greedy assignment: sort by distance, assign closest first
        candidates.sort(key=lambda x: x[0])
        assigned_blobs = set()

        for dist, blob, tid in candidates:
            if id(blob) in assigned_blobs or tid in matched_track_ids:
                continue
            # Assign blob to track
            self.active_tracks[tid].blobs.append(blob)
            self.active_tracks[tid].missed_ticks = 0
            matched_track_ids.add(tid)
            assigned_blobs.add(id(blob))

        # Unmatched blobs start new tracks
        new_track_ids = set()
        for blob in blobs:
            if id(blob) not in assigned_blobs:
                track = Track(track_id=self._next_id, blobs=[blob])
                self.active_tracks[self._next_id] = track
                new_track_ids.add(self._next_id)
                self._next_id += 1

        # Increment missed ticks for unmatched tracks (skip newly created)
        to_finalize = []
        for tid, track in self.active_tracks.items():
            if tid in matched_track_ids or tid in new_track_ids:
                continue
            track.missed_ticks += 1
            if track.missed_ticks >= self.max_missed:
                to_finalize.append(tid)

        # Finalize expired tracks
        for tid in to_finalize:
            self.finalized_tracks.append(self.active_tracks.pop(tid))

    def finalize_all(self) -> List[Track]:
        """Terminate all remaining active tracks."""
        for track in self.active_tracks.values():
            self.finalized_tracks.append(track)
        self.active_tracks.clear()
        return self.finalized_tracks


# ---------------------------------------------------------------------------
# Event naming + severity
# ---------------------------------------------------------------------------

def build_event_name(track: Track) -> str:
    """Deterministic event name for UPSERT idempotency."""
    t = track.start_time
    return (
        f"MRMS_{t.strftime('%Y%m%d_%H%Mz')}"
        f"_{track.centroid_lat:.3f}"
        f"_{track.centroid_lon:.3f}"
    )


def _classify_severity(max_hail_inches: float) -> str:
    """Severity from hail size (matches storm_monitor.py:1482-1490)."""
    if max_hail_inches >= 3.0:
        return "CATASTROPHIC"
    elif max_hail_inches >= 2.0:
        return "SEVERE"
    elif max_hail_inches >= 1.0:
        return "MODERATE"
    return "MINOR"


def _confidence_score(track: Track) -> float:
    """Confidence score based on track duration / number of detections."""
    if track.duration_minutes >= 30:
        return 80.0
    elif len(track.blobs) >= 2:
        return 70.0
    return 60.0


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _ensure_backfill_index(conn, is_pg: bool) -> None:
    """Create the partial unique index for MRMS_BACKFILL if missing.

    For PG this is handled by migration 006. For SQLite, create inline.
    """
    if not is_pg:
        try:
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_hail_events_mrms_backfill_upsert
                ON hail_events(event_name) WHERE data_source = 'MRMS_BACKFILL'
            """)
            conn.commit()
        except Exception:
            pass  # index already exists


def persist_tracks(
    tracks: List[Track],
    dry_run: bool = False,
) -> Dict:
    """
    Persist finalized tracks to hail_events table via UPSERT.

    Returns dict with created, updated, skipped counts.
    """
    from src.db.engine import get_connection, is_postgres, placeholder, ensure_schema

    if dry_run:
        logger.info("DRY RUN — would persist %d tracks", len(tracks))
        return {"created": 0, "updated": 0, "skipped": 0, "dry_run": True}

    # Ensure migration is applied (PG only)
    ensure_schema()

    _pg = is_postgres()
    _ph = placeholder()
    _scalar_max = "GREATEST" if _pg else "MAX"

    created = 0
    updated = 0

    with get_connection() as conn:
        cur = conn.cursor()

        _ensure_backfill_index(conn, _pg)

        for track in tracks:
            event_name = build_event_name(track)
            max_mesh = track.max_mesh_mm
            max_hail_inches = round(max_mesh / 25.4, 2)
            severity = _classify_severity(max_hail_inches)
            confidence = _confidence_score(track)

            swath_geojson = track.swath_polygon_geojson()
            swath_area_km2 = track.total_area_km2

            # Compute bounding box from all blobs
            all_min_lon = min(b.bbox[0] for b in track.blobs)
            all_min_lat = min(b.bbox[1] for b in track.blobs)
            all_max_lon = max(b.bbox[2] for b in track.blobs)
            all_max_lat = max(b.bbox[3] for b in track.blobs)

            # Merged core polygons
            core_15_geojson, core_15_km2 = track.merged_core_geojson(15)
            core_25_geojson, core_25_km2 = track.merged_core_geojson(25)
            core_40_geojson, core_40_km2 = track.merged_core_geojson(40)

            ev_persistence = 1 if track.duration_minutes >= 10 else 0

            try:
                cur.execute(f"""
                    INSERT INTO hail_events (
                        event_name, event_date, start_time, end_time,
                        center_lat, center_lon, swath_polygon, swath_area_sqmi,
                        max_hail_size, avg_hail_size, max_reflectivity, avg_reflectivity,
                        swath_method, num_detections, data_source, confidence_score,
                        evidence_mrms, evidence_dualpol, evidence_multi_radar,
                        evidence_spc, evidence_lsr, evidence_persistence,
                        bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon,
                        severity, status,
                        swath_area_km2, swath_area_method,
                        mrms_core_15_geojson, mrms_core_25_geojson, mrms_core_40_geojson,
                        mrms_core_15_km2, mrms_core_25_km2, mrms_core_40_km2
                    ) VALUES (
                        {_ph}, {_ph}, {_ph}, {_ph},
                        {_ph}, {_ph}, {_ph}, {_ph},
                        {_ph}, {_ph}, {_ph}, {_ph},
                        {_ph}, {_ph}, 'MRMS_BACKFILL', {_ph},
                        1, 0, 0,
                        0, 0, {_ph},
                        {_ph}, {_ph}, {_ph}, {_ph},
                        {_ph}, 'CONFIRMED',
                        {_ph}, {_ph},
                        {_ph}, {_ph}, {_ph},
                        {_ph}, {_ph}, {_ph}
                    )
                    ON CONFLICT(event_name) WHERE data_source = 'MRMS_BACKFILL'
                    DO UPDATE SET
                        end_time = excluded.end_time,
                        swath_polygon = excluded.swath_polygon,
                        swath_area_sqmi = excluded.swath_area_sqmi,
                        max_hail_size = {_scalar_max}(hail_events.max_hail_size, excluded.max_hail_size),
                        avg_hail_size = excluded.avg_hail_size,
                        num_detections = excluded.num_detections,
                        confidence_score = {_scalar_max}(hail_events.confidence_score, excluded.confidence_score),
                        evidence_mrms = {_scalar_max}(hail_events.evidence_mrms, excluded.evidence_mrms),
                        evidence_persistence = {_scalar_max}(hail_events.evidence_persistence, excluded.evidence_persistence),
                        bbox_min_lat = excluded.bbox_min_lat,
                        bbox_max_lat = excluded.bbox_max_lat,
                        bbox_min_lon = excluded.bbox_min_lon,
                        bbox_max_lon = excluded.bbox_max_lon,
                        severity = excluded.severity,
                        status = CASE
                            WHEN hail_events.status = 'CONFIRMED' THEN 'CONFIRMED'
                            ELSE excluded.status
                        END,
                        swath_area_km2 = excluded.swath_area_km2,
                        swath_area_method = excluded.swath_area_method,
                        mrms_core_15_geojson = excluded.mrms_core_15_geojson,
                        mrms_core_25_geojson = excluded.mrms_core_25_geojson,
                        mrms_core_40_geojson = excluded.mrms_core_40_geojson,
                        mrms_core_15_km2 = excluded.mrms_core_15_km2,
                        mrms_core_25_km2 = excluded.mrms_core_25_km2,
                        mrms_core_40_km2 = excluded.mrms_core_40_km2,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    event_name,
                    track.start_time.strftime("%Y-%m-%d"),
                    track.start_time.isoformat(),
                    track.end_time.isoformat(),
                    float(track.centroid_lat),
                    float(track.centroid_lon),
                    swath_geojson,
                    float(swath_area_km2 / 2.59),  # km2 -> sqmi
                    float(max_hail_inches),
                    float(max_hail_inches * 0.85),  # avg estimate
                    0.0,  # max_reflectivity (not available from MRMS MESH)
                    0.0,  # avg_reflectivity
                    "mrms_backfill",
                    len(track.blobs),
                    float(confidence),
                    int(ev_persistence),
                    float(all_min_lat), float(all_max_lat),
                    float(all_min_lon), float(all_max_lon),
                    severity,
                    float(swath_area_km2),
                    "mrms_backfill_union",
                    core_15_geojson, core_25_geojson, core_40_geojson,
                    float(core_15_km2), float(core_25_km2), float(core_40_km2),
                ))
                created += 1
            except Exception as e:
                logger.warning("Persist failed for %s: %s", event_name, e)
                # Rollback the failed statement for PG
                if _pg:
                    conn.rollback()
                continue

        if not _pg:
            conn.commit()

    logger.info("Persisted %d tracks (created=%d)", len(tracks), created)
    return {"created": created, "updated": updated, "skipped": 0}


# ---------------------------------------------------------------------------
# De-duplication
# ---------------------------------------------------------------------------

def dedupe_against_existing(
    tracks: List[Track],
    dedupe_distance_km: float = 30.0,
    dedupe_overlap: float = 0.25,
) -> Tuple[List[Track], List[Track]]:
    """
    Filter tracks against existing hail_events.

    Returns (new_tracks, duplicate_tracks).
    """
    from src.db.engine import get_connection, is_postgres, placeholder

    if not tracks:
        return [], []

    _pg = is_postgres()
    _ph = placeholder()

    new_tracks = []
    dupe_tracks = []

    with get_connection() as conn:
        cur = conn.cursor()

        for track in tracks:
            track_date = track.start_time.date()
            date_lo = (track_date - timedelta(days=1)).isoformat()
            date_hi = (track_date + timedelta(days=1)).isoformat()
            clat = track.centroid_lat
            clon = track.centroid_lon

            # Query nearby existing events (±1 day, rough lat/lon box)
            km_to_deg = dedupe_distance_km / 111.0
            lat_min = clat - km_to_deg
            lat_max = clat + km_to_deg
            cos_lat = math.cos(math.radians(clat))
            lon_margin = km_to_deg / max(cos_lat, 0.1)
            lon_min = clon - lon_margin
            lon_max = clon + lon_margin

            cur.execute(f"""
                SELECT id, event_name, center_lat, center_lon,
                       swath_polygon, data_source
                FROM hail_events
                WHERE event_date BETWEEN {_ph} AND {_ph}
                  AND center_lat BETWEEN {_ph} AND {_ph}
                  AND center_lon BETWEEN {_ph} AND {_ph}
                  AND data_source != 'MRMS_BACKFILL'
            """, (date_lo, date_hi, lat_min, lat_max, lon_min, lon_max))

            rows = cur.fetchall()
            is_dupe = False

            for row in rows:
                # Row may be tuple or dict-like depending on backend
                if hasattr(row, "keys"):
                    r_lat = row["center_lat"]
                    r_lon = row["center_lon"]
                    r_poly = row.get("swath_polygon")
                else:
                    r_lat = row[2]
                    r_lon = row[3]
                    r_poly = row[4]

                # Distance check
                dist = _haversine_km(clat, clon, float(r_lat), float(r_lon))
                if dist > dedupe_distance_km:
                    continue

                # If within distance, check polygon overlap if available
                if r_poly and dedupe_overlap > 0:
                    iou = _compute_iou(track.swath_polygon_geojson(), r_poly)
                    if iou >= dedupe_overlap:
                        is_dupe = True
                        break
                elif dist <= dedupe_distance_km * 0.5:
                    # Very close centroid — consider duplicate even without polygon
                    is_dupe = True
                    break

            if is_dupe:
                dupe_tracks.append(track)
            else:
                new_tracks.append(track)

    logger.info(
        "Dedupe: %d new, %d duplicates (of %d total)",
        len(new_tracks), len(dupe_tracks), len(tracks),
    )
    return new_tracks, dupe_tracks


def _compute_iou(geojson_a: Optional[str], geojson_b: Optional[str]) -> float:
    """Compute intersection-over-union of two GeoJSON polygons."""
    if not geojson_a or not geojson_b:
        return 0.0
    try:
        from shapely.geometry import shape as shapely_shape

        ga = shapely_shape(json.loads(geojson_a))
        gb = shapely_shape(json.loads(geojson_b))
        if not ga.is_valid:
            ga = ga.buffer(0)
        if not gb.is_valid:
            gb = gb.buffer(0)

        intersection = ga.intersection(gb).area
        union = ga.union(gb).area
        if union <= 0:
            return 0.0
        return intersection / union
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_backfill(
    start_date: date,
    end_date: date,
    min_mesh_mm: float = 15.0,
    min_core_km2: float = 5.0,
    tick_minutes: int = 10,
    workers: int = 6,
    dedupe: bool = True,
    dedupe_distance_km: float = 30.0,
    dedupe_overlap: float = 0.25,
    dry_run: bool = False,
    cache_dir: str = "data/mrms_cache",
) -> Dict:
    """
    Main MRMS MESH backfill orchestrator.

    1. For each day: quick-probe, then full-tick fetch if hail detected
    2. Extract blobs, feed to offline tracker
    3. Finalize tracks, dedupe, persist
    """
    wall_start = time.time()

    fetcher = IowaArchiveFetcher(cache_dir=cache_dir)
    tracker = OfflineTracker(
        match_distance_km=60.0 * (tick_minutes / 10.0),
        max_missed=3,
    )

    stats = {
        "days_processed": 0,
        "days_with_hail": 0,
        "days_skipped": 0,
        "ticks_fetched": 0,
        "ticks_with_data": 0,
        "total_blobs": 0,
        "tracks_formed": 0,
        "tracks_deduped": 0,
        "events_written": 0,
        "wall_seconds": 0.0,
        "errors": 0,
    }

    current_day = start_date
    while current_day < end_date:
        logger.info("Processing day %s", current_day)
        stats["days_processed"] += 1

        # Quick probe: check 3 sample times for hail
        has_hail = _quick_probe_day(fetcher, current_day, min_mesh_mm, workers)

        if not has_hail:
            logger.info("  Day %s: no hail detected in probes, skipping", current_day)
            stats["days_skipped"] += 1
            # Still feed empty tick to tracker so tracks can expire
            tracker.ingest_tick([])
            current_day += timedelta(days=1)
            continue

        stats["days_with_hail"] += 1

        # Generate all tick timestamps for this day
        day_ticks = _generate_day_ticks(current_day, tick_minutes)

        # Fetch all ticks in parallel
        grids = _parallel_fetch(fetcher, day_ticks, workers)

        # Process sequentially (tracker is stateful)
        for tick_dt in day_ticks:
            grid = grids.get(tick_dt)
            stats["ticks_fetched"] += 1

            if grid is None or grid.get("status") != "ok_data":
                tracker.ingest_tick([])
                continue

            stats["ticks_with_data"] += 1
            blobs = extract_conus_blobs(
                grid, min_mesh_mm, min_core_km2, timestamp=tick_dt,
            )
            stats["total_blobs"] += len(blobs)
            tracker.ingest_tick(blobs)

            # Free memory
            del grid

        current_day += timedelta(days=1)

    # Finalize all remaining tracks
    all_tracks = tracker.finalize_all()
    stats["tracks_formed"] = len(all_tracks)
    logger.info("Finalized %d tracks", len(all_tracks))

    # De-duplicate
    if dedupe and all_tracks:
        try:
            new_tracks, dupe_tracks = dedupe_against_existing(
                all_tracks, dedupe_distance_km, dedupe_overlap,
            )
            stats["tracks_deduped"] = len(dupe_tracks)
            all_tracks = new_tracks
        except Exception as e:
            logger.warning("Dedupe failed, proceeding with all tracks: %s", e)
            stats["errors"] += 1

    # Persist
    if all_tracks:
        result = persist_tracks(all_tracks, dry_run=dry_run)
        stats["events_written"] = result.get("created", 0)
    else:
        logger.info("No tracks to persist")

    stats["wall_seconds"] = round(time.time() - wall_start, 1)

    logger.info(
        "Backfill complete: days=%d hail_days=%d ticks=%d blobs=%d "
        "tracks=%d deduped=%d written=%d wall=%.1fs",
        stats["days_processed"], stats["days_with_hail"],
        stats["ticks_fetched"], stats["total_blobs"],
        stats["tracks_formed"], stats["tracks_deduped"],
        stats["events_written"], stats["wall_seconds"],
    )
    return stats


# ---------------------------------------------------------------------------
# Orchestrator helpers
# ---------------------------------------------------------------------------

def _quick_probe_day(
    fetcher: IowaArchiveFetcher,
    day: date,
    min_mesh_mm: float,
    workers: int,
) -> bool:
    """Quick probe: fetch 3 sample timestamps, check for any MESH >= threshold."""
    probe_hours = [6, 15, 21]  # UTC — covers diurnal convection cycle
    probe_dts = [
        datetime(day.year, day.month, day.day, h, 0, tzinfo=timezone.utc)
        for h in probe_hours
    ]

    with ThreadPoolExecutor(max_workers=min(workers, 3)) as pool:
        futures = {pool.submit(fetcher.fetch, dt): dt for dt in probe_dts}
        for future in as_completed(futures):
            try:
                grid = future.result()
            except Exception:
                continue
            if grid and grid.get("status") == "ok_data":
                mesh = grid["mesh_mm"]
                if np.max(mesh) >= min_mesh_mm:
                    # Cancel remaining futures — we know there's hail
                    return True
    return False


def _generate_day_ticks(day: date, tick_minutes: int) -> List[datetime]:
    """Generate tick timestamps for one day (00:00 UTC to 23:5x UTC)."""
    ticks = []
    dt = datetime(day.year, day.month, day.day, 0, 0, tzinfo=timezone.utc)
    end = dt + timedelta(days=1)
    step = timedelta(minutes=tick_minutes)
    while dt < end:
        ticks.append(dt)
        dt += step
    return ticks


def _parallel_fetch(
    fetcher: IowaArchiveFetcher,
    ticks: List[datetime],
    workers: int,
) -> Dict[datetime, Optional[Dict]]:
    """Fetch MRMS grids for all ticks in parallel."""
    results = {}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetcher.fetch, dt): dt for dt in ticks}
        for future in as_completed(futures):
            tick_dt = futures[future]
            try:
                results[tick_dt] = future.result()
            except Exception as e:
                logger.debug("Fetch error for %s: %s", tick_dt, e)
                results[tick_dt] = None

    return results
