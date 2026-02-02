"""
Storm Cell Identification
Identifies individual storm cells from radar data

WHY CELL TRACKING?
==================

Current problem:
- 10 detections over 30 minutes
- Are they the same storm moving? Or 10 different storms?
- Can't draw accurate swath without knowing the path

Cell tracking solution:
- Identify each unique cell
- Track position over time
- Know exact path each cell took
- Create narrow, accurate swaths

ALGORITHM:
1. Find all reflectivity cores >45 dBZ
2. Group nearby pixels into cells
3. Calculate cell centroid, size, intensity
4. Track cells frame-to-frame

RESULT:
- Know which detections belong to same storm
- Build accurate path-based swaths
- Distinguish between merged/split cells
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StormCell:
    """
    Individual storm cell

    Attributes represent cell at a single point in time
    """
    # Identification
    id: int
    timestamp: str

    # Position
    centroid_lat: float
    centroid_lon: float

    # Characteristics
    max_reflectivity: float
    mean_reflectivity: float
    area_km2: float

    # Hail properties
    mesh_mm: float = 0
    posh: float = 0

    # Motion (calculated from tracking)
    velocity_kmh: float = 0
    direction_deg: float = 0  # 0=North

    # Lifecycle
    age_minutes: int = 0
    stage: str = 'INITIATION'  # INITIATION, INTENSIFICATION, MATURE, DISSIPATION

    # History
    previous_positions: List[Tuple[float, float]] = field(default_factory=list)

    # Relationships
    parent_id: Optional[int] = None
    children_ids: List[int] = field(default_factory=list)


class CellIdentifier:
    """
    Identify storm cells from radar reflectivity field
    """

    # Detection thresholds
    REFLECTIVITY_THRESHOLD = 45  # dBZ - minimum for cell
    MIN_CELL_AREA = 5  # km² - minimum cell size
    MAX_CELL_AREA = 5000  # km² - maximum (filter out noise)

    @staticmethod
    def identify_cells(
        radar,
        scan_time: datetime,
        elevation_angle: float = 0.5
    ) -> List[StormCell]:
        """
        Identify all storm cells in radar scan

        Args:
            radar: PyART radar object
            scan_time: Scan timestamp
            elevation_angle: Elevation to analyze

        Returns:
            List of StormCell objects

        Example:
            >>> identifier = CellIdentifier()
            >>> cells = identifier.identify_cells(radar, datetime.now())
            >>> print(f"Found {len(cells)} storm cells")
            >>> for cell in cells:
            ...     print(f"Cell {cell.id}: {cell.max_reflectivity} dBZ")
        """

        # Find sweep index
        sweep_idx = CellIdentifier._find_sweep(radar, elevation_angle)

        if sweep_idx is None:
            return []

        # Get reflectivity field
        try:
            ref_field = None
            for field_name in ['reflectivity', 'DBZ', 'REF']:
                if field_name in radar.fields:
                    ref_field = radar.get_field(sweep_idx, field_name)
                    break

            if ref_field is None:
                return []
        except:
            return []

        # Threshold to find cells
        cell_mask = ref_field > CellIdentifier.REFLECTIVITY_THRESHOLD

        # Label connected regions
        try:
            from scipy import ndimage
            labeled_array, num_cells = ndimage.label(cell_mask)
        except ImportError:
            print("scipy required for cell identification")
            return []

        if num_cells == 0:
            return []

        # Get radar location
        radar_lat = radar.latitude['data'][0]
        radar_lon = radar.longitude['data'][0]

        # Extract cells
        cells = []
        cell_id = 1

        for cell_num in range(1, num_cells + 1):
            # Get cell pixels
            cell_pixels = labeled_array == cell_num
            pixel_count = np.sum(cell_pixels)

            # Filter by size
            if pixel_count < 5:  # Too small
                continue

            # Calculate cell properties
            cell_reflectivity = ref_field[cell_pixels]
            max_ref = float(np.max(cell_reflectivity))
            mean_ref = float(np.mean(cell_reflectivity))

            # Get centroid in radar coordinates
            indices = np.where(cell_pixels)
            az_indices = indices[0]
            range_indices = indices[1]

            # Get sweep data
            sweep_slice = radar.get_slice(sweep_idx)
            azimuths = radar.azimuth['data'][sweep_slice]
            ranges = radar.range['data'] / 1000.0  # km

            # Weighted centroid
            weights = cell_reflectivity / np.sum(cell_reflectivity)
            centroid_az_idx = int(np.sum(az_indices * weights))
            centroid_range_idx = int(np.sum(range_indices * weights))

            # Get azimuth and range at centroid
            azimuth = azimuths[centroid_az_idx]
            range_km = ranges[centroid_range_idx]

            # Convert to lat/lon
            centroid_lat, centroid_lon = CellIdentifier._radar_to_latlon(
                radar_lat, radar_lon, azimuth, range_km
            )

            # Estimate area (very rough)
            # Each pixel ≈ (range * beamwidth)²
            avg_range = range_km
            beamwidth_rad = np.radians(1.0)  # ~1° beamwidth
            pixel_size_km = avg_range * beamwidth_rad
            area_km2 = pixel_count * (pixel_size_km ** 2)

            # Filter by area
            if area_km2 < CellIdentifier.MIN_CELL_AREA:
                continue
            if area_km2 > CellIdentifier.MAX_CELL_AREA:
                continue

            # Create cell
            cell = StormCell(
                id=cell_id,
                timestamp=scan_time.isoformat(),
                centroid_lat=centroid_lat,
                centroid_lon=centroid_lon,
                max_reflectivity=max_ref,
                mean_reflectivity=mean_ref,
                area_km2=area_km2
            )

            cells.append(cell)
            cell_id += 1

        return cells

    @staticmethod
    def _find_sweep(radar, target_elevation: float) -> Optional[int]:
        """Find sweep closest to target elevation"""
        elevations = radar.fixed_angle['data']
        diff = np.abs(elevations - target_elevation)
        closest_idx = np.argmin(diff)

        if diff[closest_idx] <= 1.0:
            return closest_idx

        return None

    @staticmethod
    def _radar_to_latlon(
        radar_lat: float, radar_lon: float,
        azimuth: float, range_km: float
    ) -> Tuple[float, float]:
        """Convert radar polar to lat/lon"""

        import math

        R = 6371.0
        bearing = math.radians(azimuth)
        lat1 = math.radians(radar_lat)
        lon1 = math.radians(radar_lon)

        lat2 = math.asin(
            math.sin(lat1) * math.cos(range_km / R) +
            math.cos(lat1) * math.sin(range_km / R) * math.cos(bearing)
        )

        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(range_km / R) * math.cos(lat1),
            math.cos(range_km / R) - math.sin(lat1) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)
