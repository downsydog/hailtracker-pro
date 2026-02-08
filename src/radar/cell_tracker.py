"""
Storm Cell Tracker
Tracks cells frame-to-frame through time
"""

import math
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

from .cell_identifier import StormCell


class CellTracker:
    """
    Track storm cells through multiple radar scans

    ALGORITHM:
    1. Identify cells in current scan
    2. Match to cells from previous scan
    3. Calculate motion vectors
    4. Update lifecycle stages
    5. Handle splits/merges
    """

    # Tracking parameters
    MAX_TRACKING_DISTANCE_KM = 50  # Max distance cell can move between scans
    MIN_MATCH_SCORE = 60  # Minimum score to consider a match
    TYPICAL_SCAN_INTERVAL = 5  # minutes

    def __init__(self):
        """Initialize tracker"""
        self.cells_history = []  # All cells from all scans
        self.active_cells = {}  # Currently active cells {id: cell}
        self.terminated_cells = {}  # Dead cells {id: cell}
        self.next_cell_id = 1
        self.last_scan_time = None

    def process_scan(
        self,
        cells: List[StormCell],
        scan_time: datetime
    ) -> List[StormCell]:
        """
        Process radar scan and track cells

        Args:
            cells: List of identified cells in current scan
            scan_time: Timestamp of scan

        Returns:
            List of tracked cells (with IDs assigned)

        Example:
            >>> tracker = CellTracker()
            >>>
            >>> # First scan
            >>> cells1 = identifier.identify_cells(radar1, time1)
            >>> tracked1 = tracker.process_scan(cells1, time1)
            >>>
            >>> # Second scan (5 minutes later)
            >>> cells2 = identifier.identify_cells(radar2, time2)
            >>> tracked2 = tracker.process_scan(cells2, time2)
            >>> # Now cells have persistent IDs and motion vectors
        """

        if not cells:
            return []

        # First scan - initialize all cells
        if not self.last_scan_time or not self.active_cells:
            tracked = self._initialize_cells(cells)
            self.last_scan_time = scan_time
            return tracked

        # Calculate time delta
        time_delta_minutes = (scan_time - self.last_scan_time).total_seconds() / 60

        # Match cells to existing tracks
        matched_cells = self._match_cells(cells, time_delta_minutes)

        # Update lifecycle stages
        for cell in matched_cells:
            self._update_lifecycle(cell, time_delta_minutes)

        # Store in history
        self.cells_history.extend(matched_cells)

        # Update active cells
        # Mark old cells as terminated if not matched
        old_ids = set(self.active_cells.keys())
        new_ids = {cell.id for cell in matched_cells}
        terminated_ids = old_ids - new_ids

        for cell_id in terminated_ids:
            cell = self.active_cells[cell_id]
            cell.stage = 'DISSIPATION'
            self.terminated_cells[cell_id] = cell

        # Update active with new cells
        self.active_cells = {cell.id: cell for cell in matched_cells}

        self.last_scan_time = scan_time

        return matched_cells

    def get_cell_tracks(
        self,
        min_duration_minutes: int = 10
    ) -> Dict[int, List[StormCell]]:
        """
        Get complete tracks for all cells

        Args:
            min_duration_minutes: Filter cells shorter than this

        Returns:
            Dict of {cell_id: [cell_positions_over_time]}

        Example:
            >>> tracks = tracker.get_cell_tracks(min_duration_minutes=15)
            >>> for cell_id, track in tracks.items():
            ...     print(f"Cell {cell_id}: {len(track)} positions")
        """

        # Group by cell ID
        tracks = defaultdict(list)
        for cell in self.cells_history:
            tracks[cell.id].append(cell)

        # Filter short-lived cells
        filtered = {}
        for cell_id, track in tracks.items():
            if len(track) < 2:
                continue

            # Sort by time
            track.sort(key=lambda c: c.timestamp)

            # Calculate duration
            start = datetime.fromisoformat(track[0].timestamp)
            end = datetime.fromisoformat(track[-1].timestamp)
            duration = (end - start).total_seconds() / 60

            if duration >= min_duration_minutes:
                filtered[cell_id] = track

        return filtered

    def _initialize_cells(self, cells: List[StormCell]) -> List[StormCell]:
        """Initialize cells for first scan"""

        initialized = []

        for cell in cells:
            cell.id = self.next_cell_id
            cell.stage = 'INITIATION'
            cell.age_minutes = 0

            initialized.append(cell)
            self.active_cells[cell.id] = cell

            self.next_cell_id += 1

        self.cells_history.extend(initialized)

        return initialized

    def _match_cells(
        self,
        current_cells: List[StormCell],
        time_delta_minutes: float
    ) -> List[StormCell]:
        """
        Match current cells to active tracks

        Uses:
        - Distance (should be near predicted position)
        - Intensity (should be similar)
        - Size (should be similar)
        """

        matched = []
        used_track_ids = set()

        for cell in current_cells:
            best_match = None
            best_score = 0

            # Try to match to each active cell
            for cell_id, active_cell in self.active_cells.items():
                if cell_id in used_track_ids:
                    continue

                # Calculate match score
                score = self._calculate_match_score(
                    cell, active_cell, time_delta_minutes
                )

                if score > best_score:
                    best_match = active_cell
                    best_score = score

            # Assign ID based on match
            if best_score > self.MIN_MATCH_SCORE:
                # Matched - update existing cell
                cell.id = best_match.id
                cell.previous_positions = best_match.previous_positions + [
                    (best_match.centroid_lat, best_match.centroid_lon)
                ]
                cell.age_minutes = best_match.age_minutes + time_delta_minutes

                # Calculate motion
                distance_km = self._calculate_distance(
                    cell.centroid_lat, cell.centroid_lon,
                    best_match.centroid_lat, best_match.centroid_lon
                )

                cell.velocity_kmh = (distance_km / time_delta_minutes) * 60
                cell.direction_deg = self._calculate_bearing(
                    best_match.centroid_lat, best_match.centroid_lon,
                    cell.centroid_lat, cell.centroid_lon
                )

                used_track_ids.add(cell.id)
            else:
                # New cell
                cell.id = self.next_cell_id
                cell.stage = 'INITIATION'
                cell.age_minutes = 0
                self.next_cell_id += 1

            matched.append(cell)

        return matched

    def _calculate_match_score(
        self,
        current_cell: StormCell,
        active_cell: StormCell,
        time_delta_minutes: float
    ) -> float:
        """
        Score how well current cell matches active cell

        Returns:
            Score 0-100
        """

        # Distance score
        distance_km = self._calculate_distance(
            current_cell.centroid_lat, current_cell.centroid_lon,
            active_cell.centroid_lat, active_cell.centroid_lon
        )

        # Expected distance based on velocity
        expected_distance = (active_cell.velocity_kmh / 60) * time_delta_minutes
        distance_diff = abs(distance_km - expected_distance)

        distance_score = max(0, 100 - (distance_diff / self.MAX_TRACKING_DISTANCE_KM * 100))

        # Intensity score
        intensity_diff = abs(current_cell.max_reflectivity - active_cell.max_reflectivity)
        intensity_score = max(0, 100 - (intensity_diff / 20 * 100))

        # Size score
        if active_cell.area_km2 > 0:
            size_ratio = min(current_cell.area_km2, active_cell.area_km2) / max(current_cell.area_km2, active_cell.area_km2)
            size_score = size_ratio * 100
        else:
            size_score = 50

        # Weighted total
        total_score = (
            distance_score * 0.5 +
            intensity_score * 0.3 +
            size_score * 0.2
        )

        return total_score

    def _update_lifecycle(self, cell: StormCell, time_delta: float):
        """Update cell lifecycle stage"""

        # Simple lifecycle rules
        if cell.age_minutes < 10:
            cell.stage = 'INITIATION'
        elif cell.max_reflectivity > 60:
            cell.stage = 'MATURE'
        elif cell.velocity_kmh > 40:
            cell.stage = 'INTENSIFICATION'
        else:
            cell.stage = 'MATURE'

    @staticmethod
    def _calculate_distance(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Distance in km"""

        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    @staticmethod
    def _calculate_bearing(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Bearing in degrees"""

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))

        bearing = math.degrees(math.atan2(y, x))

        return (bearing + 360) % 360
