"""
Storm Cell Tracking System

Identifies, tracks, and analyzes individual storm cells over time.

Benefits of cell tracking:
- Know exact storm path (not just scattered detections)
- Identify storm splits and mergers
- Calculate accurate motion vectors
- Create narrow, accurate swaths along actual path
- Predict where storm will go next

Accuracy improvement:
- Multi-radar composite: ~80%
- With cell tracking: ~82%
"""

import json
import math
import os
import random as _random_module
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class StormCell:
    """
    Individual storm cell at a point in time

    A storm cell is a discrete, organized area of convection
    that can be tracked from one radar scan to the next.
    """
    id: int
    timestamp: str  # ISO format

    # Position
    centroid_lat: float
    centroid_lon: float

    # Characteristics
    max_reflectivity: float  # dBZ
    mean_reflectivity: float  # dBZ
    area_km2: float  # Approximate area

    # MESH and hail
    mesh_mm: float = 0
    mesh_inches: float = 0
    posh: float = 0  # Probability of Severe Hail

    # Motion (calculated from tracking)
    velocity_kmh: float = 0
    direction_deg: float = 0  # 0=North, 90=East

    # Lifecycle
    age_minutes: float = 0
    stage: str = 'INITIATION'  # INITIATION, INTENSIFICATION, MATURE, DISSIPATION, TERMINATED

    # Track history (previous positions)
    previous_positions: List[Tuple[float, float]] = field(default_factory=list)

    # Source radar
    radar_id: Optional[str] = None

    # Hail score (0-1, from dual-pol or reflectivity-only)
    hail_score: float = 0.0
    hail_score_peak: float = 0.0
    hail_score_avg: float = 0.0
    hail_score_samples: int = 0

    # MRMS MESH backbone (optional, populated when ENABLE_MRMS=true)
    mrms_mesh_mm: Optional[float] = None      # MRMS MESH at cell centroid (mm)
    mrms_mesh_peak: Optional[float] = None     # Peak MRMS MESH across cell lifetime
    mrms_mesh_avg: Optional[float] = None      # Running avg MRMS MESH
    mrms_source_time: Optional[str] = None     # ISO time of MRMS grid used

    # Parent/child relationships (for splits/mergers)
    parent_id: Optional[int] = None
    children_ids: List[int] = field(default_factory=list)

    def __hash__(self):
        return hash((self.id, self.timestamp))


@dataclass
class CellTrack:
    """Complete track of a storm cell over its lifetime"""
    cell_id: int
    positions: List[StormCell]
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    max_mesh_mm: float
    max_reflectivity: float
    avg_velocity_kmh: float
    track_length_km: float
    lifecycle_stages: List[str]


@dataclass
class StormEvent:
    """A storm event composed of one or more nearby tracked cells."""
    event_id: str
    start_time: datetime
    end_time: datetime
    cell_ids: List[int]
    radar_ids: List[str]
    max_mesh_mm: float
    max_mesh_inches: float
    max_reflectivity: float
    estimated_area_sq_km: float
    centroid_lat: float
    centroid_lon: float
    severity: str   # light / moderate / severe
    confidence: float  # 0.0 - 0.95
    hail_score_peak: float = 0.0  # Max hail_score across member cells
    hail_score_avg: float = 0.0   # Mean hail_score_avg across member cells
    mrms_mesh_peak: Optional[float] = None  # Peak MRMS MESH (mm) across member cells
    mrms_mesh_avg: Optional[float] = None   # Mean MRMS MESH (mm) across member cells
    status: str = 'EXPIRED'  # ACTIVE / DISSIPATING / EXPIRED
    phase: str = 'NONE'  # DEVELOPING / IMPACTING / WEAKENING / NONE
    impact_window_minutes: int = 0
    event_quality_score: int = 0  # 0-100
    event_quality_reasons: List[str] = field(default_factory=list)
    # (A) Authoritative hail size: MRMS when available, else radar MESH
    authoritative_hail_mm: float = 0.0
    authoritative_hail_inches: float = 0.0
    # (B) Commercial confidence score (0-100) + evidence flags
    commercial_confidence: float = 0.0
    evidence_mrms: bool = False
    evidence_dualpol: bool = False
    evidence_multi_radar: bool = False
    evidence_spc: bool = False
    evidence_lsr: bool = False
    evidence_persistence: bool = False


class StormCellTracker:
    """
    Track storm cells through multiple radar scans

    The tracker:
    1. Detects cells in each radar scan
    2. Matches cells to previous tracks
    3. Calculates motion vectors
    4. Manages cell lifecycle (birth, split, merge, death)
    5. Creates swaths along cell tracks
    """

    # Tracking thresholds
    REFLECTIVITY_THRESHOLD = 40.0  # dBZ - minimum for cell consideration
    HAIL_REFLECTIVITY = 50.0  # dBZ - likely hail
    SEVERE_REFLECTIVITY = 60.0  # dBZ - severe hail
    MAX_TRACKING_DISTANCE_KM = 50.0  # Maximum distance cell can move between scans
    MIN_MATCH_SCORE = 60.0  # Minimum score for cell matching (0-100)
    SCAN_INTERVAL_MINUTES = 5.0  # Typical radar scan interval

    # Miss tolerance: keep cells active across gaps in detection
    MISSED_SCAN_TOL = 3  # Terminate after this many consecutive missed scans

    # Memory caps
    MAX_CELLS_HISTORY = 10000  # Max entries in cells_history

    # Cell lifecycle thresholds
    INTENSIFICATION_THRESHOLD = 5.0  # dBZ increase = intensifying
    DISSIPATION_THRESHOLD = -5.0  # dBZ decrease = weakening
    MATURE_REFLECTIVITY = 55.0  # dBZ threshold for mature stage

    def __init__(self, simulation_mode: bool = True):
        """
        Initialize storm cell tracker

        Args:
            simulation_mode: If True, use simulated data for testing
        """
        self.simulation_mode = simulation_mode
        self.cells_history: List[StormCell] = []  # All cells from all scans
        self.active_cells: Dict[int, StormCell] = {}  # Currently active cells
        self.terminated_cells: Dict[int, StormCell] = {}  # Terminated cells
        self.missed_scans: Dict[int, int] = {}  # cell_id -> consecutive missed scan count
        self.next_cell_id = 1
        self.last_scan_time: Optional[datetime] = None

    # -------------------------------------------------------------------------
    # State persistence
    # -------------------------------------------------------------------------

    DEFAULT_STATE_PATH = os.path.join('data', 'storm_cells', 'tracker_state.json')

    @staticmethod
    def _cell_to_dict(cell: 'StormCell') -> dict:
        return {
            'id': cell.id,
            'timestamp': cell.timestamp,
            'centroid_lat': cell.centroid_lat,
            'centroid_lon': cell.centroid_lon,
            'max_reflectivity': cell.max_reflectivity,
            'mean_reflectivity': cell.mean_reflectivity,
            'area_km2': cell.area_km2,
            'mesh_mm': cell.mesh_mm,
            'mesh_inches': cell.mesh_inches,
            'posh': cell.posh,
            'velocity_kmh': cell.velocity_kmh,
            'direction_deg': cell.direction_deg,
            'age_minutes': cell.age_minutes,
            'stage': cell.stage,
            'previous_positions': cell.previous_positions,
            'radar_id': cell.radar_id,
            'hail_score': cell.hail_score,
            'hail_score_peak': cell.hail_score_peak,
            'hail_score_avg': cell.hail_score_avg,
            'hail_score_samples': cell.hail_score_samples,
            'mrms_mesh_mm': cell.mrms_mesh_mm,
            'mrms_mesh_peak': cell.mrms_mesh_peak,
            'mrms_mesh_avg': cell.mrms_mesh_avg,
            'mrms_source_time': cell.mrms_source_time,
            'parent_id': cell.parent_id,
            'children_ids': cell.children_ids,
        }

    @staticmethod
    def _cell_from_dict(d: dict) -> 'StormCell':
        return StormCell(
            id=d['id'],
            timestamp=d['timestamp'],
            centroid_lat=d['centroid_lat'],
            centroid_lon=d['centroid_lon'],
            max_reflectivity=d['max_reflectivity'],
            mean_reflectivity=d['mean_reflectivity'],
            area_km2=d['area_km2'],
            mesh_mm=d.get('mesh_mm', 0),
            mesh_inches=d.get('mesh_inches', 0),
            posh=d.get('posh', 0),
            velocity_kmh=d.get('velocity_kmh', 0),
            direction_deg=d.get('direction_deg', 0),
            age_minutes=d.get('age_minutes', 0),
            stage=d.get('stage', 'INITIATION'),
            previous_positions=[tuple(p) for p in d.get('previous_positions', [])],
            radar_id=d.get('radar_id'),
            hail_score=d.get('hail_score', 0.0),
            hail_score_peak=d.get('hail_score_peak', 0.0),
            hail_score_avg=d.get('hail_score_avg', 0.0),
            hail_score_samples=d.get('hail_score_samples', 0),
            mrms_mesh_mm=d.get('mrms_mesh_mm'),
            mrms_mesh_peak=d.get('mrms_mesh_peak'),
            mrms_mesh_avg=d.get('mrms_mesh_avg'),
            mrms_source_time=d.get('mrms_source_time'),
            parent_id=d.get('parent_id'),
            children_ids=d.get('children_ids', []),
        )

    def to_state_dict(self) -> dict:
        """Serialize tracker state to a JSON-safe dict."""
        return {
            'next_cell_id': self.next_cell_id,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'missed_scans': {str(k): v for k, v in self.missed_scans.items()},
            'active_cells': {str(k): self._cell_to_dict(v) for k, v in self.active_cells.items()},
            'terminated_cells': {str(k): self._cell_to_dict(v) for k, v in self.terminated_cells.items()},
            'cells_history': [self._cell_to_dict(c) for c in self.cells_history[-self.MAX_CELLS_HISTORY:]],
        }

    @classmethod
    def from_state_dict(cls, state: dict, simulation_mode: bool = True) -> 'StormCellTracker':
        """Reconstruct a tracker from a state dict."""
        tracker = cls(simulation_mode=simulation_mode)
        tracker.next_cell_id = state.get('next_cell_id', 1)
        lst = state.get('last_scan_time')
        tracker.last_scan_time = datetime.fromisoformat(lst) if lst else None
        tracker.missed_scans = {int(k): v for k, v in state.get('missed_scans', {}).items()}
        tracker.active_cells = {int(k): cls._cell_from_dict(v) for k, v in state.get('active_cells', {}).items()}
        tracker.terminated_cells = {int(k): cls._cell_from_dict(v) for k, v in state.get('terminated_cells', {}).items()}
        tracker.cells_history = [cls._cell_from_dict(c) for c in state.get('cells_history', [])]
        return tracker

    def save_state(self, path: str = None) -> None:
        """Save tracker state to a JSON file."""
        path = path or self.DEFAULT_STATE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_state_dict(), f)

    @classmethod
    def load_state(cls, path: str = None, simulation_mode: bool = True) -> 'StormCellTracker':
        """Load tracker state from a JSON file."""
        path = path or cls.DEFAULT_STATE_PATH
        with open(path, 'r') as f:
            state = json.load(f)
        return cls.from_state_dict(state, simulation_mode=simulation_mode)

    def process_radar_scan(
        self,
        detections: List[Dict],
        scan_time: datetime
    ) -> List[StormCell]:
        """
        Process radar detections and identify/track cells

        Args:
            detections: List of detection dicts with lat, lon, reflectivity, etc.
            scan_time: Timestamp of scan

        Returns:
            List of StormCell objects detected in this scan

        Example:
            >>> tracker = StormCellTracker()
            >>> detections = [
            ...     {'lat': 32.7, 'lon': -96.8, 'reflectivity': 55, 'mesh_mm': 25},
            ...     {'lat': 32.75, 'lon': -96.75, 'reflectivity': 62, 'mesh_mm': 38},
            ... ]
            >>> cells = tracker.process_radar_scan(detections, datetime.now())
        """
        # Step 1: Filter detections above threshold
        valid_detections = [
            d for d in detections
            if d.get('reflectivity', 0) >= self.REFLECTIVITY_THRESHOLD
        ]

        if not valid_detections:
            # No detections this scan — increment missed_scans for all active cells
            self._age_unmatched_cells(matched_ids=set())
            self.last_scan_time = scan_time
            return []

        # Step 2: Group nearby detections into cells
        raw_cells = self._cluster_detections(valid_detections, scan_time)

        # Step 3: Match to existing tracks (if not first scan)
        if self.last_scan_time and self.active_cells:
            time_delta_minutes = (scan_time - self.last_scan_time).total_seconds() / 60
            matched_cells = self._match_cells(raw_cells, time_delta_minutes)
        else:
            # First scan - all cells are new
            matched_cells = self._initialize_cells(raw_cells)

        # Step 4: Update cell lifecycle stages
        for cell in matched_cells:
            self._update_lifecycle(cell)

        # Step 5: Store cells and cap history
        self.cells_history.extend(matched_cells)
        if len(self.cells_history) > self.MAX_CELLS_HISTORY:
            self.cells_history = self.cells_history[-self.MAX_CELLS_HISTORY:]

        # Step 6: Update active cells dict (preserve unmatched with miss-tolerance)
        matched_ids = {cell.id for cell in matched_cells}

        # Add/update matched cells, reset their missed_scans counter
        for cell in matched_cells:
            self.active_cells[cell.id] = cell
            self.missed_scans[cell.id] = 0

        # Handle unmatched active cells (miss-tolerance)
        self._age_unmatched_cells(matched_ids)

        self.last_scan_time = scan_time

        return matched_cells

    def _age_unmatched_cells(self, matched_ids: set):
        """
        Increment missed_scans for active cells not matched this scan.
        Terminate cells that exceed MISSED_SCAN_TOL.
        """
        for cell_id in list(self.active_cells.keys()):
            if cell_id in matched_ids:
                continue
            self.missed_scans[cell_id] = self.missed_scans.get(cell_id, 0) + 1
            if self.missed_scans[cell_id] >= self.MISSED_SCAN_TOL:
                # Truly terminated
                self.active_cells[cell_id].stage = 'TERMINATED'
                self.terminated_cells[cell_id] = self.active_cells.pop(cell_id)
                self.missed_scans.pop(cell_id, None)
            else:
                # Still alive but missing — mark as dissipating
                self.active_cells[cell_id].stage = 'DISSIPATION'

    def process_simulated_storm(
        self,
        start_lat: float,
        start_lon: float,
        direction_deg: float = 45,
        speed_kmh: float = 50,
        duration_minutes: int = 60,
        peak_reflectivity: float = 65,
        start_time: datetime = None,
        seed: Optional[int] = None,
    ) -> List[StormCell]:
        """
        Create simulated storm track for testing

        Args:
            start_lat: Starting latitude
            start_lon: Starting longitude
            direction_deg: Storm motion direction (0=North)
            speed_kmh: Storm speed in km/h
            duration_minutes: Total storm duration
            peak_reflectivity: Maximum reflectivity (dBZ)
            start_time: Start time (default: now)
            seed: Optional RNG seed for deterministic output

        Returns:
            List of all cells created during simulation
        """
        if start_time is None:
            start_time = datetime.utcnow()

        rng = _random_module.Random(seed)

        all_cells = []
        num_scans = duration_minutes // 5 + 1

        current_lat = start_lat
        current_lon = start_lon

        for i in range(num_scans):
            scan_time = start_time + timedelta(minutes=i * 5)

            # Calculate position based on motion
            distance_km = (speed_kmh / 60) * 5 * i  # Distance traveled
            current_lat, current_lon = self._offset_position(
                start_lat, start_lon, distance_km, direction_deg
            )

            # Intensity varies over lifecycle
            # Ramps up, peaks in middle, then decreases
            lifecycle_factor = 1.0 - abs(i - num_scans / 2) / (num_scans / 2)
            reflectivity = 45 + (peak_reflectivity - 45) * lifecycle_factor

            # Create detection
            detection = {
                'lat': current_lat,
                'lon': current_lon,
                'reflectivity': reflectivity,
                'mesh_mm': max(0, (reflectivity - 50) * 2),
                'area_km2': 50 + lifecycle_factor * 100
            }

            # Add some randomness for realism (seeded for determinism)
            detection['lat'] += rng.uniform(-0.02, 0.02)
            detection['lon'] += rng.uniform(-0.02, 0.02)
            detection['reflectivity'] += rng.uniform(-3, 3)
            detection['radar_id'] = 'SIM'

            # Deterministic hail_score from reflectivity (no dual-pol in sim)
            detection['hail_score'] = min(1.0, max(0.0, (detection['reflectivity'] - 50) / 20))

            cells = self.process_radar_scan([detection], scan_time)
            all_cells.extend(cells)

        return all_cells

    def get_cell_tracks(self, min_duration_minutes: float = 10) -> Dict[int, CellTrack]:
        """
        Get complete tracks for all cells

        Args:
            min_duration_minutes: Minimum track duration to include

        Returns:
            Dict of {cell_id: CellTrack}
        """
        # Group cells by ID
        cells_by_id = defaultdict(list)
        for cell in self.cells_history:
            cells_by_id[cell.id].append(cell)

        tracks = {}

        for cell_id, positions in cells_by_id.items():
            if len(positions) < 2:
                continue

            # Sort by timestamp
            positions = sorted(positions, key=lambda c: c.timestamp)

            # Calculate duration
            start_time = datetime.fromisoformat(positions[0].timestamp)
            end_time = datetime.fromisoformat(positions[-1].timestamp)
            duration = (end_time - start_time).total_seconds() / 60

            if duration < min_duration_minutes:
                continue

            # Calculate track statistics
            max_mesh = max(c.mesh_mm for c in positions)
            max_ref = max(c.max_reflectivity for c in positions)
            velocities = [c.velocity_kmh for c in positions if c.velocity_kmh > 0]
            avg_velocity = sum(velocities) / len(velocities) if velocities else 0

            # Calculate total track length
            track_length = 0
            for i in range(1, len(positions)):
                dist = self._calculate_distance(
                    positions[i-1].centroid_lat, positions[i-1].centroid_lon,
                    positions[i].centroid_lat, positions[i].centroid_lon
                )
                track_length += dist

            # Get lifecycle stages
            stages = [c.stage for c in positions]

            tracks[cell_id] = CellTrack(
                cell_id=cell_id,
                positions=positions,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                max_mesh_mm=max_mesh,
                max_reflectivity=max_ref,
                avg_velocity_kmh=avg_velocity,
                track_length_km=track_length,
                lifecycle_stages=stages
            )

        return tracks

    def create_track_swath(
        self,
        cell_id: int,
        buffer_km: float = 3.0
    ) -> Optional[Dict]:
        """
        Create swath polygon for a specific cell track

        Args:
            cell_id: Cell ID to create swath for
            buffer_km: Buffer distance around track (km)

        Returns:
            GeoJSON polygon of track swath, or None if cell not found
        """
        tracks = self.get_cell_tracks(min_duration_minutes=0)

        if cell_id not in tracks:
            return None

        track = tracks[cell_id]
        positions = track.positions

        if len(positions) < 2:
            return None

        # Extract centroids
        centroids = [(c.centroid_lat, c.centroid_lon) for c in positions]

        # Calculate per-point swath width based on each position's MESH
        widths_km = []
        for pos in positions:
            mesh_inches_i = pos.mesh_mm / 25.4 if pos.mesh_mm > 0 else 0
            width_i = max(buffer_km, mesh_inches_i * 2 + 2)
            widths_km.append(width_i)

        # Build swath polygon with variable width
        left_points = []
        right_points = []

        for i in range(len(centroids)):
            lat, lon = centroids[i]
            half_width = widths_km[i] / 2

            # Calculate bearing
            if i < len(centroids) - 1:
                next_lat, next_lon = centroids[i + 1]
                bearing = self._calculate_bearing(lat, lon, next_lat, next_lon)
            else:
                prev_lat, prev_lon = centroids[i - 1]
                bearing = self._calculate_bearing(prev_lat, prev_lon, lat, lon)

            # Perpendicular offsets using this point's width
            left_lat, left_lon = self._offset_position(
                lat, lon, half_width, bearing + 90
            )
            right_lat, right_lon = self._offset_position(
                lat, lon, half_width, bearing - 90
            )

            left_points.append([left_lon, left_lat])
            right_points.append([right_lon, right_lat])

        # Create end caps using first/last width
        first_lat, first_lon = centroids[0]
        if len(centroids) > 1:
            first_bearing = self._calculate_bearing(
                first_lat, first_lon,
                centroids[1][0], centroids[1][1]
            )
        else:
            first_bearing = 0

        start_cap = self._create_semicircle(
            first_lat, first_lon,
            widths_km[0] / 2,
            first_bearing + 180,
            num_points=5
        )

        last_lat, last_lon = centroids[-1]
        if len(centroids) > 1:
            last_bearing = self._calculate_bearing(
                centroids[-2][0], centroids[-2][1],
                last_lat, last_lon
            )
        else:
            last_bearing = 0

        end_cap = self._create_semicircle(
            last_lat, last_lon,
            widths_km[-1] / 2,
            last_bearing,
            num_points=5
        )

        # Combine: start cap + left side + end cap + right side (reversed)
        polygon_points = start_cap + left_points + end_cap + list(reversed(right_points))
        polygon_points.append(polygon_points[0])  # Close polygon

        # Calculate area using average width
        avg_width_km = sum(widths_km) / len(widths_km)
        area_sq_km = track.track_length_km * avg_width_km
        mesh_inches_list = [pos.mesh_mm / 25.4 for pos in positions]

        # Hail score stats from cell positions
        hs_peaks = [p.hail_score_peak for p in positions]
        hs_avgs = [p.hail_score_avg for p in positions if p.hail_score_samples > 0]
        hs_last = positions[-1].hail_score if positions else 0.0

        # MRMS MESH stats from cell positions
        mrms_peaks_list = [p.mrms_mesh_peak for p in positions if p.mrms_mesh_peak is not None]
        mrms_avgs_list = [p.mrms_mesh_avg for p in positions if p.mrms_mesh_avg is not None]
        mrms_peak_val = max(mrms_peaks_list) if mrms_peaks_list else None
        mrms_avg_val = round(sum(mrms_avgs_list) / len(mrms_avgs_list), 1) if mrms_avgs_list else None

        props = {
            'cell_id': cell_id,
            'method': 'cell_tracking',
            'duration_minutes': round(track.duration_minutes, 1),
            'track_points': len(positions),
            'track_length_km': round(track.track_length_km, 1),
            'max_reflectivity': round(track.max_reflectivity, 1),
            'max_mesh_mm': round(track.max_mesh_mm, 1),
            'max_mesh_inches': round(max(mesh_inches_list), 2),
            'avg_mesh_inches': round(sum(mesh_inches_list) / len(mesh_inches_list), 2),
            'width_min_km': round(min(widths_km), 1),
            'width_max_km': round(max(widths_km), 1),
            'swath_width_km': round(avg_width_km, 1),
            'area_sq_km': round(area_sq_km, 1),
            'area_sq_miles': round(area_sq_km * 0.386, 1),
            'avg_velocity_kmh': round(track.avg_velocity_kmh, 1),
            'start_time': track.start_time.isoformat(),
            'end_time': track.end_time.isoformat(),
            'event_date': track.start_time.strftime('%Y-%m-%d'),
            'lifecycle_stages': list(set(track.lifecycle_stages)),
            'radar_id': self._track_radar_id(positions),
            'hail_score_peak': round(max(hs_peaks) if hs_peaks else 0.0, 4),
            'hail_score_avg': round(sum(hs_avgs) / len(hs_avgs) if hs_avgs else 0.0, 4),
            'hail_score_last': round(hs_last, 4),
            'mrms_mesh_peak': mrms_peak_val,
            'mrms_mesh_avg': mrms_avg_val,
        }

        sq, sr = self._compute_swath_quality(props)
        props['swath_quality_score'] = sq
        props['swath_quality_reasons'] = sr

        return {
            'type': 'Polygon',
            'coordinates': [polygon_points],
            'properties': props,
        }

    def _track_radar_id(self, positions: List[StormCell]) -> Optional[str]:
        """Return the radar_id for a track, or 'MULTI' if mixed."""
        ids = {pos.radar_id for pos in positions if pos.radar_id is not None}
        if len(ids) == 0:
            return None
        if len(ids) == 1:
            return ids.pop()
        return 'MULTI'

    def create_all_track_swaths(
        self,
        min_duration_minutes: float = 10,
        buffer_km: float = 3.0
    ) -> List[Dict]:
        """
        Create swath polygons for all tracked cells

        Args:
            min_duration_minutes: Minimum track duration
            buffer_km: Buffer around each track

        Returns:
            List of GeoJSON polygon features
        """
        tracks = self.get_cell_tracks(min_duration_minutes)
        swaths = []

        for cell_id in tracks:
            swath = self.create_track_swath(cell_id, buffer_km)
            if swath:
                swaths.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': swath['coordinates']
                    },
                    'properties': swath['properties']
                })

        return swaths

    # -------------------------------------------------------------------------
    # Storm event grouping
    # -------------------------------------------------------------------------

    def get_events(
        self,
        lookback_minutes: int = 180,
        join_distance_km: float = 25.0,
    ) -> List['StormEvent']:
        """
        Group nearby cells into storm events using single-link BFS clustering.

        Event IDs are stable across runs given identical underlying cells,
        regardless of dict iteration order or BFS discovery order.

        Args:
            lookback_minutes: Consider cells active/terminated within this window.
            join_distance_km: Max distance between cells to join into same event.

        Returns:
            List of StormEvent objects.
        """
        now = self.last_scan_time or datetime.utcnow()
        cutoff = now - timedelta(minutes=lookback_minutes)

        # Gather candidate cells: active + recently terminated
        candidates: Dict[int, StormCell] = {}
        for cid, cell in self.active_cells.items():
            candidates[cid] = cell
        for cid, cell in self.terminated_cells.items():
            try:
                ts = datetime.fromisoformat(cell.timestamp)
            except (ValueError, TypeError):
                continue
            if ts >= cutoff:
                candidates[cid] = cell

        if not candidates:
            return []

        # Sort candidate cell IDs deterministically
        def _cell_sort_key(cid):
            c = candidates[cid]
            return (c.radar_id or '', c.id, c.timestamp)

        cids = sorted(candidates.keys(), key=_cell_sort_key)

        # Build adjacency by proximity (single-link)
        adj: Dict[int, List[int]] = {c: [] for c in cids}
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                ci, cj = candidates[cids[i]], candidates[cids[j]]
                dist = self._calculate_distance(
                    ci.centroid_lat, ci.centroid_lon,
                    cj.centroid_lat, cj.centroid_lon,
                )
                if dist <= join_distance_km:
                    adj[cids[i]].append(cids[j])
                    adj[cids[j]].append(cids[i])

        # Sort neighbor lists for deterministic BFS traversal
        for cid in adj:
            adj[cid].sort(key=_cell_sort_key)

        # BFS to find connected components (deterministic seed order)
        visited = set()
        clusters: List[List[int]] = []
        for cid in cids:
            if cid in visited:
                continue
            queue = [cid]
            visited.add(cid)
            component = []
            while queue:
                cur = queue.pop(0)
                component.append(cur)
                for nb in adj[cur]:
                    if nb not in visited:
                        visited.add(nb)
                        queue.append(nb)
            clusters.append(sorted(component))

        # Build StormEvent per cluster
        tracks = self.get_cell_tracks(min_duration_minutes=0)

        # Pre-compute cluster metadata for sorting
        cluster_meta = []
        for cluster_cids in clusters:
            cells_in_cluster = [candidates[c] for c in cluster_cids]
            centroid_lat = round(sum(c.centroid_lat for c in cells_in_cluster) / len(cells_in_cluster), 3)
            centroid_lon = round(sum(c.centroid_lon for c in cells_in_cluster) / len(cells_in_cluster), 3)
            cluster_key = '-'.join(map(str, cluster_cids))  # already sorted
            cluster_meta.append((centroid_lat, centroid_lon, cluster_key, cluster_cids))

        # Sort clusters deterministically by (lat, lon, key)
        cluster_meta.sort(key=lambda m: (m[0], m[1], m[2]))

        events: List[StormEvent] = []

        for centroid_lat, centroid_lon, cluster_key, cluster_cids in cluster_meta:
            cells_in_cluster = [candidates[c] for c in cluster_cids]

            # Time range
            timestamps = []
            for c in cells_in_cluster:
                try:
                    timestamps.append(datetime.fromisoformat(c.timestamp))
                except (ValueError, TypeError):
                    pass
            for cid in cluster_cids:
                if cid in tracks:
                    timestamps.append(tracks[cid].start_time)
                    timestamps.append(tracks[cid].end_time)
            if not timestamps:
                continue
            start_time = min(timestamps)
            end_time = max(timestamps)
            duration_minutes = (end_time - start_time).total_seconds() / 60

            # Event time: max timestamp rounded down to minute
            event_time = max(timestamps).replace(second=0, microsecond=0)

            # Aggregated stats
            max_mesh_mm = max((c.mesh_mm for c in cells_in_cluster), default=0)
            for cid in cluster_cids:
                if cid in tracks:
                    max_mesh_mm = max(max_mesh_mm, tracks[cid].max_mesh_mm)
            max_mesh_inches = max_mesh_mm / 25.4
            max_ref = max((c.max_reflectivity for c in cells_in_cluster), default=0)
            for cid in cluster_cids:
                if cid in tracks:
                    max_ref = max(max_ref, tracks[cid].max_reflectivity)

            # Radar IDs (sorted for stability)
            radar_ids = sorted({c.radar_id for c in cells_in_cluster if c.radar_id})

            # Hail score aggregation across cells in cluster
            ev_hs_peak = max((c.hail_score_peak for c in cells_in_cluster), default=0.0)
            hs_avgs_with_samples = [
                c.hail_score_avg for c in cells_in_cluster if c.hail_score_samples > 0
            ]
            ev_hs_avg = (
                sum(hs_avgs_with_samples) / len(hs_avgs_with_samples)
                if hs_avgs_with_samples else 0.0
            )

            # Estimated area from tracks
            area = 0.0
            for cid in cluster_cids:
                if cid in tracks:
                    t = tracks[cid]
                    avg_width = 6.0  # default km
                    area += t.track_length_km * avg_width

            # MRMS MESH aggregation across cells
            mrms_peaks = [c.mrms_mesh_peak for c in cells_in_cluster if c.mrms_mesh_peak is not None]
            mrms_avgs = [c.mrms_mesh_avg for c in cells_in_cluster if c.mrms_mesh_avg is not None]
            ev_mrms_peak = max(mrms_peaks) if mrms_peaks else None
            ev_mrms_avg = round(sum(mrms_avgs) / len(mrms_avgs), 1) if mrms_avgs else None

            # (A) Authoritative hail size: prefer MRMS when available
            if ev_mrms_peak is not None and ev_mrms_peak > 0:
                auth_hail_mm = ev_mrms_peak
            else:
                auth_hail_mm = max_mesh_mm
            auth_hail_inches = round(auth_hail_mm / 25.4, 2) if auth_hail_mm > 0 else 0.0

            # Severity (stable thresholds) — uses authoritative hail
            if auth_hail_inches >= 1.25 or max_ref >= 65.0:
                severity = 'severe'
            elif auth_hail_inches >= 1.00 or max_ref >= 58.0:
                severity = 'moderate'
            else:
                severity = 'light'

            # (B) Commercial confidence scoring (0-100)
            # Evidence flags
            ev_evidence_mrms = ev_mrms_peak is not None and ev_mrms_peak > 0
            ev_evidence_dualpol = ev_hs_peak >= 0.35  # hail_score from dual-pol gating
            ev_evidence_multi_radar = len(radar_ids) >= 2
            ev_evidence_persistence = duration_minutes >= 10 or len(cluster_cids) >= 2
            ev_evidence_spc = False   # populated by external SPC feed if available
            ev_evidence_lsr = False   # populated by external LSR feed if available

            # Component scores (0..1)
            mrms_sc = 0.0
            if ev_evidence_mrms and ev_mrms_peak is not None:
                mrms_sc = max(0.0, min(1.0, (ev_mrms_peak - 15.0) / 35.0))  # 0@15mm, 1@50mm
            dualpol_sc = min(1.0, ev_hs_peak / 0.7) if ev_evidence_dualpol else 0.0
            agree_sc = 1.0 if len(radar_ids) >= 3 else (0.6 if len(radar_ids) >= 2 else 0.0)
            spc_sc = 0.0   # future: SPC hail prob near centroid
            lsr_sc = 0.0   # future: LSR hail report match
            persist_sc = min(1.0, duration_minutes / 20.0) if ev_evidence_persistence else 0.0

            commercial_conf = round(
                (mrms_sc * 30 + dualpol_sc * 20 + agree_sc * 15 +
                 spc_sc * 15 + lsr_sc * 10 + persist_sc * 10)
            )
            commercial_conf = max(0, min(100, commercial_conf))

            # Legacy confidence (0.0 - 0.95) kept for backward compat
            confidence = 0.4
            if radar_ids:
                confidence += 0.1
            if len(cluster_cids) >= 2:
                confidence += 0.1
            if max_ref >= 68.0:
                confidence += 0.1
            if auth_hail_inches >= 1.50:
                confidence += 0.1
            if duration_minutes >= 20:
                confidence += 0.1
            if ev_mrms_peak is not None and ev_mrms_peak >= 25.0:
                confidence += 0.05
            confidence = min(confidence, 0.95)

            # Stable event_id (no index, uses cluster_key)
            event_id = (
                f"{event_time.strftime('%Y%m%d_%H%MZ')}"
                f"_{centroid_lat:.3f}"
                f"_{centroid_lon:.3f}"
                f"_{cluster_key}"
            )

            # --- Operational classification: status, phase, impact_window ---
            # Active cells = non-terminated within 15 min of event_time
            active_in_cluster = []
            for c in cells_in_cluster:
                if c.stage == 'TERMINATED':
                    continue
                try:
                    ct = datetime.fromisoformat(c.timestamp)
                except (ValueError, TypeError):
                    continue
                if (event_time - ct).total_seconds() / 60 <= 15:
                    active_in_cluster.append(c)

            # Status
            if active_in_cluster:
                status = 'ACTIVE'
            elif any(c.stage == 'DISSIPATION' for c in cells_in_cluster):
                status = 'DISSIPATING'
            else:
                status = 'EXPIRED'

            # Phase
            age_max = max((c.age_minutes for c in cells_in_cluster), default=0)
            if status != 'ACTIVE':
                phase = 'NONE'
            elif (max_mesh_inches >= 1.00 or max_ref >= 60) and age_max >= 10:
                phase = 'IMPACTING'
            elif age_max < 10 and max_ref >= 50:
                phase = 'DEVELOPING'
            elif any(c.stage == 'DISSIPATION' for c in cells_in_cluster) or (max_ref < 55 and age_max > 20):
                phase = 'WEAKENING'
            else:
                phase = 'DEVELOPING'

            # Impact window
            impact_window_minutes = 0
            if phase == 'IMPACTING':
                # Get avg velocity from tracks or cluster cells
                avg_vel = 0.0
                for cid in cluster_cids:
                    if cid in tracks:
                        avg_vel = max(avg_vel, tracks[cid].avg_velocity_kmh)
                if avg_vel == 0:
                    vels = [c.velocity_kmh for c in cells_in_cluster if c.velocity_kmh > 0]
                    avg_vel = sum(vels) / len(vels) if vels else 0
                avg_vel = max(avg_vel, 20)  # floor at 20 km/h

                # Estimate remaining distance
                remaining_km = 15.0
                for cid in cluster_cids:
                    if cid in tracks:
                        remaining_km = max(remaining_km, 0.35 * tracks[cid].track_length_km)

                impact_window_minutes = max(5, min(90, int((remaining_km / avg_vel) * 60)))

            # Total track points across all cells in cluster
            total_track_points = sum(
                len(tracks[cid].positions) for cid in cluster_cids if cid in tracks
            )

            eq_score, eq_reasons = self._compute_event_quality(
                severity=severity,
                max_mesh_inches=max_mesh_inches,
                duration_minutes=duration_minutes,
                radar_ids=radar_ids,
                total_track_points=total_track_points,
                status=status,
                phase=phase,
                max_reflectivity=max_ref,
            )

            events.append(StormEvent(
                event_id=event_id,
                start_time=start_time,
                end_time=end_time,
                cell_ids=cluster_cids,
                radar_ids=radar_ids,
                max_mesh_mm=round(max_mesh_mm, 1),
                max_mesh_inches=round(max_mesh_inches, 2),
                max_reflectivity=round(max_ref, 1),
                estimated_area_sq_km=round(area, 1),
                centroid_lat=centroid_lat,
                centroid_lon=centroid_lon,
                severity=severity,
                confidence=round(confidence, 2),
                hail_score_peak=round(ev_hs_peak, 4),
                hail_score_avg=round(ev_hs_avg, 4),
                mrms_mesh_peak=ev_mrms_peak,
                mrms_mesh_avg=ev_mrms_avg,
                status=status,
                phase=phase,
                impact_window_minutes=impact_window_minutes,
                event_quality_score=eq_score,
                event_quality_reasons=eq_reasons,
                authoritative_hail_mm=round(auth_hail_mm, 1),
                authoritative_hail_inches=auth_hail_inches,
                commercial_confidence=commercial_conf,
                evidence_mrms=ev_evidence_mrms,
                evidence_dualpol=ev_evidence_dualpol,
                evidence_multi_radar=ev_evidence_multi_radar,
                evidence_spc=ev_evidence_spc,
                evidence_lsr=ev_evidence_lsr,
                evidence_persistence=ev_evidence_persistence,
            ))

        return events

    def create_event_merged_swath(
        self,
        event_id: str,
        buffer_km: float = 3.0,
        lookback_minutes: int = 180,
        join_distance_km: float = 25.0,
    ) -> Optional[Dict]:
        """
        Create a single merged swath polygon for all cells in a storm event.

        Uses shapely unary_union if available, falls back to convex hull.

        Returns:
            GeoJSON-like dict with 'type', 'coordinates', 'properties', or None.
        """
        events = self.get_events(
            lookback_minutes=lookback_minutes,
            join_distance_km=join_distance_km,
        )
        event = next((e for e in events if e.event_id == event_id), None)
        if not event:
            return None

        # Collect individual swath polygons
        swath_polys = []
        for cell_id in event.cell_ids:
            swath = self.create_track_swath(cell_id, buffer_km=buffer_km)
            if swath and swath.get('coordinates'):
                swath_polys.append(swath)

        if not swath_polys:
            return None

        now_iso = datetime.utcnow().isoformat() + 'Z'

        # Aggregate swath-level stats for merged quality scoring
        all_width_min = min((sp['properties'].get('width_min_km', 0) for sp in swath_polys), default=0)
        all_width_max = max((sp['properties'].get('width_max_km', 0) for sp in swath_polys), default=0)
        all_track_len = sum(sp['properties'].get('track_length_km', 0) for sp in swath_polys)
        all_max_mesh = max((sp['properties'].get('max_mesh_inches', 0) for sp in swath_polys), default=0)
        all_area_mi = sum(sp['properties'].get('area_sq_miles', 0) for sp in swath_polys)

        merged_swath_props = {
            'width_min_km': all_width_min,
            'width_max_km': all_width_max,
            'track_length_km': all_track_len,
            'max_mesh_inches': all_max_mesh,
            'area_sq_miles': all_area_mi,
        }
        msq, msr = self._compute_swath_quality(merged_swath_props)

        base_props = {
            'event_id': event.event_id,
            'cell_ids': sorted(event.cell_ids),
            'radar_ids': sorted(event.radar_ids),
            'swaths_merged': len(swath_polys),
            'created_at': now_iso,
            'event_quality_score': event.event_quality_score,
            'event_quality_reasons': event.event_quality_reasons,
            'swath_quality_score': msq,
            'swath_quality_reasons': msr,
            'hail_score_peak': event.hail_score_peak,
            'hail_score_avg': event.hail_score_avg,
            'mrms_mesh_peak': event.mrms_mesh_peak,
            'mrms_mesh_avg': event.mrms_mesh_avg,
        }

        # Try shapely union
        try:
            from shapely.geometry import shape, mapping
            from shapely.ops import unary_union

            geoms = []
            for sp in swath_polys:
                geom = shape({'type': 'Polygon', 'coordinates': sp['coordinates']})
                if geom.is_valid:
                    geoms.append(geom)
                else:
                    geoms.append(geom.buffer(0))

            if not geoms:
                return None

            merged = unary_union(geoms)

            # If MultiPolygon, pick largest
            if merged.geom_type == 'MultiPolygon':
                merged = max(merged.geoms, key=lambda g: g.area)

            geojson_geom = mapping(merged)
            base_props['method'] = 'shapely_union'

            return {
                'type': 'Polygon',
                'coordinates': geojson_geom['coordinates'],
                'properties': base_props,
            }

        except ImportError:
            pass

        # Fallback: convex hull of all vertices
        all_points = []
        for sp in swath_polys:
            for ring in sp['coordinates']:
                for pt in ring:
                    all_points.append((float(pt[0]), float(pt[1])))

        if len(all_points) < 3:
            return None

        hull = self._convex_hull(all_points)
        if len(hull) < 3:
            return None

        # Close the ring
        closed = hull + [hull[0]]
        base_props['method'] = 'convex_hull_fallback'

        return {
            'type': 'Polygon',
            'coordinates': [closed],
            'properties': base_props,
        }

    def get_active_event_features(
        self,
        lookback_minutes: int = 180,
        join_distance_km: float = 25.0,
        limit: int = 10,
        buffer_km: float = 3.0,
    ) -> List[Dict]:
        """
        Return GeoJSON Feature dicts for non-EXPIRED events, ranked by quality.

        Each Feature has a merged swath polygon (or best cell swath fallback)
        and full event metadata in properties.
        """
        limit = max(1, min(50, limit))

        events = self.get_events(
            lookback_minutes=lookback_minutes,
            join_distance_km=join_distance_km,
        )

        # Filter out EXPIRED
        active_events = [e for e in events if e.status != 'EXPIRED']

        features = []
        for event in active_events:
            # Try merged swath
            merged = self.create_event_merged_swath(
                event.event_id,
                buffer_km=buffer_km,
                lookback_minutes=lookback_minutes,
                join_distance_km=join_distance_km,
            )

            geometry = None
            method = None
            swath_quality_score = 0
            swath_quality_reasons = []
            track_length_km = 0.0

            if merged:
                geometry = {
                    'type': 'Polygon',
                    'coordinates': merged['coordinates'],
                }
                method = merged['properties'].get('method', 'merged')
                swath_quality_score = merged['properties'].get('swath_quality_score', 0)
                swath_quality_reasons = merged['properties'].get('swath_quality_reasons', [])
            else:
                # Fallback: pick best cell swath by swath_quality_score
                best_swath = None
                best_sq = -1
                for cell_id in event.cell_ids:
                    swath = self.create_track_swath(cell_id, buffer_km=buffer_km)
                    if swath:
                        sq = swath['properties'].get('swath_quality_score', 0)
                        if sq > best_sq:
                            best_sq = sq
                            best_swath = swath
                if best_swath:
                    geometry = {
                        'type': 'Polygon',
                        'coordinates': best_swath['coordinates'],
                    }
                    method = 'cell_fallback'
                    swath_quality_score = best_swath['properties'].get('swath_quality_score', 0)
                    swath_quality_reasons = best_swath['properties'].get('swath_quality_reasons', [])

            if geometry is None:
                continue

            # Track length: max among member cells
            tracks = self.get_cell_tracks(min_duration_minutes=0)
            for cid in event.cell_ids:
                if cid in tracks:
                    track_length_km = max(track_length_km, tracks[cid].track_length_km)

            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': {
                    'event_id': event.event_id,
                    'status': event.status,
                    'phase': event.phase,
                    'impact_window_minutes': event.impact_window_minutes,
                    'event_quality_score': event.event_quality_score,
                    'event_quality_reasons': event.event_quality_reasons,
                    'swath_quality_score': swath_quality_score,
                    'swath_quality_reasons': swath_quality_reasons,
                    'severity': event.severity,
                    'confidence': event.confidence,
                    'radar_ids': event.radar_ids,
                    'cell_ids': event.cell_ids,
                    'track_length_km': round(track_length_km, 1),
                    'max_mesh_inches': event.max_mesh_inches,
                    'max_reflectivity': event.max_reflectivity,
                    'hail_score_peak': event.hail_score_peak,
                    'hail_score_avg': event.hail_score_avg,
                    'mrms_mesh_peak': event.mrms_mesh_peak,
                    'mrms_mesh_avg': event.mrms_mesh_avg,
                    'authoritative_hail_mm': event.authoritative_hail_mm,
                    'authoritative_hail_inches': event.authoritative_hail_inches,
                    'commercial_confidence': event.commercial_confidence,
                    'evidence_mrms': event.evidence_mrms,
                    'evidence_dualpol': event.evidence_dualpol,
                    'evidence_multi_radar': event.evidence_multi_radar,
                    'evidence_spc': event.evidence_spc,
                    'evidence_lsr': event.evidence_lsr,
                    'evidence_persistence': event.evidence_persistence,
                    'event_time': event.end_time.isoformat(),
                    'method': method,
                },
            })

        # Sort: hail_score_peak desc, event_quality desc, swath_quality desc, event_time desc
        features.sort(key=lambda f: (
            -f['properties']['hail_score_peak'],
            -f['properties']['event_quality_score'],
            -f['properties']['swath_quality_score'],
            f['properties']['event_time'],
        ), reverse=False)

        return features[:limit]

    @staticmethod
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

    @staticmethod
    def _compute_event_quality(
        severity: str,
        max_mesh_inches: float,
        duration_minutes: float,
        radar_ids: List[str],
        total_track_points: int,
        status: str,
        phase: str,
        max_reflectivity: float,
    ) -> Tuple[int, List[str]]:
        """Compute event quality score (0-100) and reasons."""
        reasons = []
        score = 0

        # Severity points
        if severity == 'severe':
            score += 40; reasons.append('severity=severe (+40)')
        elif severity == 'moderate':
            score += 28; reasons.append('severity=moderate (+28)')
        else:
            score += 15; reasons.append('severity=light (+15)')

        # MESH points
        if max_mesh_inches >= 1.50:
            score += 32; reasons.append(f'MESH={max_mesh_inches:.2f}">=1.50 (+32)')
        elif max_mesh_inches >= 1.25:
            score += 26; reasons.append(f'MESH={max_mesh_inches:.2f}">=1.25 (+26)')
        elif max_mesh_inches >= 1.00:
            score += 18; reasons.append(f'MESH={max_mesh_inches:.2f}">=1.00 (+18)')
        elif max_mesh_inches >= 0.75:
            score += 10; reasons.append(f'MESH={max_mesh_inches:.2f}">=0.75 (+10)')

        # Duration points
        if duration_minutes >= 35:
            score += 18; reasons.append(f'duration={duration_minutes:.0f}min>=35 (+18)')
        elif duration_minutes >= 20:
            score += 12; reasons.append(f'duration={duration_minutes:.0f}min>=20 (+12)')
        elif duration_minutes >= 10:
            score += 6; reasons.append(f'duration={duration_minutes:.0f}min>=10 (+6)')

        # Radar points
        if len(radar_ids) >= 2:
            score += 12; reasons.append(f'radar_count={len(radar_ids)}>=2 (+12)')
        elif len(radar_ids) >= 1:
            score += 8; reasons.append(f'radar_count={len(radar_ids)}>=1 (+8)')

        # Stability points
        if total_track_points >= 3:
            score += 10; reasons.append(f'track_points={total_track_points}>=3 (+10)')

        # Penalties
        if status != 'ACTIVE':
            score -= 12; reasons.append(f'status={status}!=ACTIVE (-12)')
        if phase == 'WEAKENING':
            score -= 8; reasons.append('phase=WEAKENING (-8)')
        if max_reflectivity < 55:
            score -= 10; reasons.append(f'max_ref={max_reflectivity:.1f}<55 (-10)')

        return max(0, min(100, score)), reasons

    @staticmethod
    def _compute_swath_quality(props: Dict) -> Tuple[int, List[str]]:
        """Compute swath quality score (0-100) and reasons from swath properties."""
        reasons = []
        score = 50
        reasons.append('base (+50)')

        width_min = props.get('width_min_km', 0)
        width_max = props.get('width_max_km', 0)
        variability = width_max - width_min

        if 0.5 <= variability <= 2.0:
            score += 8; reasons.append(f'width_var={variability:.1f}km dynamic (+8)')
        elif variability < 0.3:
            pass  # no bonus
        elif variability > 3.0:
            score -= 6; reasons.append(f'width_var={variability:.1f}km chaotic (-6)')

        track_len = props.get('track_length_km', 0)
        if track_len >= 25:
            score += 12; reasons.append(f'track={track_len:.1f}km>=25 (+12)')

        max_mesh_in = props.get('max_mesh_inches', 0)
        if max_mesh_in >= 1.00:
            score += 10; reasons.append(f'MESH={max_mesh_in:.2f}">=1.00 (+10)')

        area_sq_mi = props.get('area_sq_miles', 0)
        if area_sq_mi < 5:
            score -= 10; reasons.append(f'area={area_sq_mi:.1f}sqmi<5 (-10)')

        return max(0, min(100, score)), reasons

    def get_cell_motion_forecast(
        self,
        cell_id: int,
        forecast_minutes: int = 30
    ) -> List[Tuple[float, float, str]]:
        """
        Forecast future positions of a cell based on current motion

        Args:
            cell_id: Cell ID to forecast
            forecast_minutes: How far ahead to forecast

        Returns:
            List of (lat, lon, timestamp) tuples for forecast positions
        """
        if cell_id not in self.active_cells:
            return []

        cell = self.active_cells[cell_id]

        if cell.velocity_kmh == 0:
            return []

        forecasts = []
        current_lat = cell.centroid_lat
        current_lon = cell.centroid_lon
        current_time = datetime.fromisoformat(cell.timestamp)

        # Forecast at 5-minute intervals
        for i in range(1, forecast_minutes // 5 + 1):
            forecast_time = current_time + timedelta(minutes=i * 5)
            distance_km = (cell.velocity_kmh / 60) * 5 * i

            forecast_lat, forecast_lon = self._offset_position(
                cell.centroid_lat, cell.centroid_lon,
                distance_km, cell.direction_deg
            )

            forecasts.append((forecast_lat, forecast_lon, forecast_time.isoformat()))

        return forecasts

    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================

    def _cluster_detections(
        self,
        detections: List[Dict],
        scan_time: datetime
    ) -> List[Dict]:
        """
        Group nearby detections into discrete cells

        Uses simple proximity clustering
        """
        if not detections:
            return []

        # Adaptive clustering: tighter radius for strong storms
        max_ref = max((d.get('reflectivity', 0) for d in detections), default=0)
        cluster_radius_km = 6.0 if max_ref >= 55 else 8.0
        clusters = []
        used = set()

        for i, det in enumerate(detections):
            if i in used:
                continue

            # Start new cluster
            cluster = [det]
            used.add(i)

            # Find nearby detections
            for j, other in enumerate(detections):
                if j in used:
                    continue

                dist = self._calculate_distance(
                    det['lat'], det['lon'],
                    other['lat'], other['lon']
                )

                if dist <= cluster_radius_km:
                    cluster.append(other)
                    used.add(j)

            # Calculate cluster properties
            if cluster:
                avg_lat = sum(d['lat'] for d in cluster) / len(cluster)
                avg_lon = sum(d['lon'] for d in cluster) / len(cluster)
                max_ref = max(d.get('reflectivity', 0) for d in cluster)
                mean_ref = sum(d.get('reflectivity', 0) for d in cluster) / len(cluster)
                total_area = sum(d.get('area_km2', 10) for d in cluster)
                max_mesh = max(d.get('mesh_mm', 0) for d in cluster)

                # Pick radar_id from cluster (use strongest detection's radar_id)
                cluster_radar_ids = {d.get('radar_id') for d in cluster if d.get('radar_id')}
                cluster_radar_id = cluster_radar_ids.pop() if len(cluster_radar_ids) == 1 else (
                    'MULTI' if len(cluster_radar_ids) > 1 else None
                )

                max_hail_score = max((d.get('hail_score', 0.0) for d in cluster), default=0.0)
                max_hail_score = min(1.0, max(0.0, float(max_hail_score or 0.0)))

                # MRMS MESH: take max across cluster detections
                mrms_vals = [d.get('mrms_mesh_mm') for d in cluster if d.get('mrms_mesh_mm') is not None]
                mrms_mesh_mm = max(mrms_vals) if mrms_vals else None
                mrms_srcs = [d.get('mrms_source_time') for d in cluster if d.get('mrms_source_time')]
                mrms_source_time = mrms_srcs[0] if mrms_srcs else None

                clusters.append({
                    'centroid_lat': avg_lat,
                    'centroid_lon': avg_lon,
                    'max_reflectivity': max_ref,
                    'mean_reflectivity': mean_ref,
                    'area_km2': total_area,
                    'mesh_mm': max_mesh,
                    'hail_score': max_hail_score,
                    'timestamp': scan_time.isoformat(),
                    'num_detections': len(cluster),
                    'radar_id': cluster_radar_id,
                    'mrms_mesh_mm': mrms_mesh_mm,
                    'mrms_source_time': mrms_source_time,
                })

        return clusters

    def _match_cells(
        self,
        detected_cells: List[Dict],
        time_delta_minutes: float
    ) -> List[StormCell]:
        """
        Match detected cells to existing tracks
        """
        matched_cells = []
        used_track_ids = set()

        for detection in detected_cells:
            best_match = None
            best_score = 0

            # Try to match to existing active cells
            for cell_id, active_cell in self.active_cells.items():
                if cell_id in used_track_ids:
                    continue

                score = self._calculate_match_score(
                    detection, active_cell, time_delta_minutes
                )

                if score > best_score:
                    best_match = active_cell
                    best_score = score

            # Create cell object
            if best_score >= self.MIN_MATCH_SCORE and best_match:
                # Matched to existing track
                cell = self._update_tracked_cell(
                    detection, best_match, time_delta_minutes
                )
                used_track_ids.add(cell.id)
            else:
                # New cell
                cell = self._create_new_cell(detection)

            matched_cells.append(cell)

        # Unmatched active cells are handled by _age_unmatched_cells
        # (miss-tolerance: they stay active until MISSED_SCAN_TOL is reached)

        return matched_cells

    def _calculate_match_score(
        self,
        detection: Dict,
        active_cell: StormCell,
        time_delta_minutes: float
    ) -> float:
        """
        Calculate how well a detection matches an active cell

        Returns:
            Match score 0-100
        """
        # Distance score
        distance_km = self._calculate_distance(
            detection['centroid_lat'], detection['centroid_lon'],
            active_cell.centroid_lat, active_cell.centroid_lon
        )

        # Expected distance based on cell velocity
        expected_distance = (active_cell.velocity_kmh / 60) * time_delta_minutes

        distance_diff = abs(distance_km - expected_distance)
        distance_score = max(0, 100 - (distance_diff / self.MAX_TRACKING_DISTANCE_KM * 100))

        # Intensity score
        intensity_diff = abs(detection['max_reflectivity'] - active_cell.max_reflectivity)
        intensity_score = max(0, 100 - (intensity_diff / 20 * 100))

        # Size score
        det_area = detection.get('area_km2', 50)
        size_ratio = min(det_area, active_cell.area_km2) / max(det_area, active_cell.area_km2)
        size_score = size_ratio * 100

        # Weighted average
        total_score = (
            distance_score * 0.5 +
            intensity_score * 0.3 +
            size_score * 0.2
        )

        return total_score

    def _update_tracked_cell(
        self,
        detection: Dict,
        previous_cell: StormCell,
        time_delta_minutes: float
    ) -> StormCell:
        """
        Update existing cell with new detection
        """
        # Calculate motion
        distance_km = self._calculate_distance(
            detection['centroid_lat'], detection['centroid_lon'],
            previous_cell.centroid_lat, previous_cell.centroid_lon
        )

        velocity_kmh = (distance_km / time_delta_minutes) * 60 if time_delta_minutes > 0 else 0

        direction_deg = self._calculate_bearing(
            previous_cell.centroid_lat, previous_cell.centroid_lon,
            detection['centroid_lat'], detection['centroid_lon']
        )

        # Calculate MESH in inches
        mesh_mm = detection.get('mesh_mm', 0)
        mesh_inches = mesh_mm / 25.4

        # Accumulate hail_score
        hs = min(1.0, max(0.0, float(detection.get('hail_score') or 0.0)))
        prev_n = previous_cell.hail_score_samples
        new_n = prev_n + 1
        new_avg = ((previous_cell.hail_score_avg * prev_n) + hs) / new_n if new_n > 0 else hs

        # MRMS MESH accumulation
        mrms_mm = detection.get('mrms_mesh_mm')
        mrms_src = detection.get('mrms_source_time')
        prev_mrms_peak = previous_cell.mrms_mesh_peak
        prev_mrms_avg = previous_cell.mrms_mesh_avg

        if mrms_mm is not None:
            new_mrms_peak = max(mrms_mm, prev_mrms_peak or 0)
            if prev_mrms_avg is not None:
                # Running average weighted by scan count
                new_mrms_avg = ((prev_mrms_avg * prev_n) + mrms_mm) / new_n
            else:
                new_mrms_avg = mrms_mm
        else:
            new_mrms_peak = prev_mrms_peak
            new_mrms_avg = prev_mrms_avg
            mrms_src = previous_cell.mrms_source_time

        # Create updated cell
        cell = StormCell(
            id=previous_cell.id,
            timestamp=detection['timestamp'],
            centroid_lat=detection['centroid_lat'],
            centroid_lon=detection['centroid_lon'],
            max_reflectivity=detection['max_reflectivity'],
            mean_reflectivity=detection.get('mean_reflectivity', detection['max_reflectivity'] - 5),
            area_km2=detection.get('area_km2', previous_cell.area_km2),
            mesh_mm=mesh_mm,
            mesh_inches=mesh_inches,
            velocity_kmh=velocity_kmh,
            direction_deg=direction_deg,
            age_minutes=previous_cell.age_minutes + time_delta_minutes,
            previous_positions=previous_cell.previous_positions + [
                (previous_cell.centroid_lat, previous_cell.centroid_lon)
            ],
            radar_id=detection.get('radar_id') or previous_cell.radar_id,
            hail_score=hs,
            hail_score_peak=max(previous_cell.hail_score_peak, hs),
            hail_score_avg=new_avg,
            hail_score_samples=new_n,
            mrms_mesh_mm=mrms_mm,
            mrms_mesh_peak=new_mrms_peak,
            mrms_mesh_avg=round(new_mrms_avg, 1) if new_mrms_avg is not None else None,
            mrms_source_time=mrms_src,
        )

        return cell

    def _create_new_cell(self, detection: Dict) -> StormCell:
        """
        Create new cell from detection
        """
        mesh_mm = detection.get('mesh_mm', 0)
        hs = min(1.0, max(0.0, float(detection.get('hail_score') or 0.0)))

        mrms_mm = detection.get('mrms_mesh_mm')
        mrms_src = detection.get('mrms_source_time')

        cell = StormCell(
            id=self.next_cell_id,
            timestamp=detection['timestamp'],
            centroid_lat=detection['centroid_lat'],
            centroid_lon=detection['centroid_lon'],
            max_reflectivity=detection['max_reflectivity'],
            mean_reflectivity=detection.get('mean_reflectivity', detection['max_reflectivity'] - 5),
            area_km2=detection.get('area_km2', 50),
            mesh_mm=mesh_mm,
            mesh_inches=mesh_mm / 25.4,
            stage='INITIATION',
            radar_id=detection.get('radar_id'),
            hail_score=hs,
            hail_score_peak=hs,
            hail_score_avg=hs,
            hail_score_samples=1,
            mrms_mesh_mm=mrms_mm,
            mrms_mesh_peak=mrms_mm,
            mrms_mesh_avg=mrms_mm,
            mrms_source_time=mrms_src,
        )

        self.next_cell_id += 1

        return cell

    def _initialize_cells(self, detected_cells: List[Dict]) -> List[StormCell]:
        """
        Initialize cells for first scan
        """
        return [self._create_new_cell(det) for det in detected_cells]

    def _update_lifecycle(self, cell: StormCell):
        """
        Update cell lifecycle stage based on age and intensity
        """
        if cell.age_minutes < 10:
            cell.stage = 'INITIATION'
        elif cell.max_reflectivity >= self.SEVERE_REFLECTIVITY:
            cell.stage = 'MATURE'
        elif cell.max_reflectivity >= self.MATURE_REFLECTIVITY:
            # Check if intensifying or weakening
            if len(cell.previous_positions) > 0:
                # Would need previous reflectivity to determine trend
                # For now, use velocity as proxy
                if cell.velocity_kmh > 40:
                    cell.stage = 'INTENSIFICATION'
                else:
                    cell.stage = 'MATURE'
            else:
                cell.stage = 'INTENSIFICATION'
        elif cell.age_minutes > 30:
            cell.stage = 'DISSIPATION'
        else:
            cell.stage = 'INTENSIFICATION'

    def _create_semicircle(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        center_bearing: float,
        num_points: int = 5
    ) -> List[List[float]]:
        """
        Create semicircle points for end cap
        """
        points = []

        for i in range(num_points):
            angle_offset = -90 + (i / (num_points - 1)) * 180
            bearing = center_bearing + angle_offset

            lat, lon = self._offset_position(
                center_lat, center_lon, radius_km, bearing
            )
            points.append([lon, lat])

        return points

    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================

    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance in km using Haversine formula"""
        R = 6371  # Earth radius in km

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _calculate_bearing(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate bearing in degrees (0=North, 90=East)"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))

        bearing = math.degrees(math.atan2(y, x))

        return (bearing + 360) % 360

    def _offset_position(
        self,
        lat: float, lon: float,
        distance_km: float, bearing_deg: float
    ) -> Tuple[float, float]:
        """Offset a position by distance and bearing"""
        R = 6371  # Earth radius in km
        bearing_rad = math.radians(bearing_deg)
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        lat2 = math.asin(
            math.sin(lat_rad) * math.cos(distance_km / R) +
            math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
        )

        lon2 = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
            math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)

    def get_tracking_statistics(self) -> Dict:
        """
        Get overall tracking statistics
        """
        tracks = self.get_cell_tracks(min_duration_minutes=0)

        if not tracks:
            return {
                'total_cells_detected': len(set(c.id for c in self.cells_history)),
                'tracks_10min_plus': 0,
                'active_cells': len(self.active_cells),
                'terminated_cells': len(self.terminated_cells)
            }

        durations = [t.duration_minutes for t in tracks.values()]
        velocities = [t.avg_velocity_kmh for t in tracks.values() if t.avg_velocity_kmh > 0]
        mesh_values = [t.max_mesh_mm for t in tracks.values()]

        return {
            'total_cells_detected': len(set(c.id for c in self.cells_history)),
            'tracks_10min_plus': len([d for d in durations if d >= 10]),
            'active_cells': len(self.active_cells),
            'terminated_cells': len(self.terminated_cells),
            'avg_track_duration_min': sum(durations) / len(durations) if durations else 0,
            'max_track_duration_min': max(durations) if durations else 0,
            'avg_velocity_kmh': sum(velocities) / len(velocities) if velocities else 0,
            'max_mesh_mm': max(mesh_values) if mesh_values else 0
        }


def create_tracked_swath_from_detections(
    detections: List[Dict],
    timestamps: List[datetime],
    buffer_km: float = 3.0
) -> Dict:
    """
    Convenience function to create tracked swath from detection series

    Args:
        detections: List of detection dicts (one per timestamp)
        timestamps: List of datetime objects (matching detections)
        buffer_km: Buffer around track

    Returns:
        GeoJSON FeatureCollection with track swaths
    """
    tracker = StormCellTracker()

    for detection, timestamp in zip(detections, timestamps):
        tracker.process_radar_scan([detection], timestamp)

    swaths = tracker.create_all_track_swaths(min_duration_minutes=5, buffer_km=buffer_km)

    return {
        'type': 'FeatureCollection',
        'features': swaths,
        'properties': {
            'method': 'cell_tracking',
            'statistics': tracker.get_tracking_statistics()
        }
    }
