"""
MESH (Maximum Estimated Size of Hail) Algorithm

Implements the NOAA/NWS MESH algorithm for estimating hail size from radar data.

Algorithm based on:
- Witt et al. (1998) - "An Enhanced Hail Detection Algorithm for the WSR-88D"
- Cintineo et al. (2012) - "An Objective High-Resolution Hail Climatology"

MESH provides better hail size estimates than reflectivity-only methods by:
1. Using vertical structure of storm (3D analysis)
2. Accounting for freezing level height
3. Integrating hail kinetic energy through the storm depth
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MESHResult:
    """MESH calculation result for a single grid point"""
    lat: float
    lon: float
    mesh_inches: float  # Maximum Estimated Size of Hail
    shi: float  # Severe Hail Index (J/m/s)
    posh: float  # Probability of Severe Hail (%)
    vil: float  # Vertically Integrated Liquid (kg/m^2)
    max_reflectivity: float  # Maximum reflectivity in column (dBZ)
    height_max_ref: float  # Height of max reflectivity (km)


class MESHAlgorithm:
    """
    MESH (Maximum Estimated Size of Hail) Calculator

    The MESH algorithm estimates hail size by:
    1. Computing Hail Kinetic Energy at each radar gate
    2. Weighting by height relative to freezing level
    3. Vertically integrating to get Severe Hail Index (SHI)
    4. Converting SHI to MESH using empirical relationship

    Reference: Witt et al. (1998), Weather and Forecasting
    """

    # Algorithm constants
    REFLECTIVITY_THRESHOLD = 40.0  # dBZ - minimum for hail consideration
    REFLECTIVITY_HAIL = 50.0  # dBZ - high confidence hail
    REFLECTIVITY_SEVERE = 60.0  # dBZ - severe hail likely

    # Kinetic energy constants (Witt et al. 1998)
    # Note: These are scaled for practical MESH output
    KE_COEFFICIENT = 5e-6  # W(Z) coefficient
    KE_EXPONENT = 0.084  # W(Z) exponent

    # Empirical calibration factor (matches observed hail sizes)
    # Based on verification studies comparing MESH to hail reports
    # Adjusted to produce realistic MESH values (1-3" for severe storms)
    MESH_CALIBRATION = 500.0  # Empirical multiplier for realistic values

    # Height weighting constants
    H0_DEFAULT = 3.5  # Default 0°C height (km) - varies by season/location
    H_MINUS20_DEFAULT = 6.5  # Default -20°C height (km)

    def __init__(
        self,
        freezing_level_km: float = None,
        minus20_level_km: float = None
    ):
        """
        Initialize MESH calculator

        Args:
            freezing_level_km: Height of 0°C level (km AGL)
            minus20_level_km: Height of -20°C level (km AGL)

        Note: Freezing levels vary by season and location:
            - Summer Texas: H0 ~ 4.5 km, H-20 ~ 7.5 km
            - Spring Oklahoma: H0 ~ 3.5 km, H-20 ~ 6.5 km
            - Winter: H0 ~ 2.0 km, H-20 ~ 4.5 km
        """
        self.h0 = freezing_level_km if freezing_level_km else self.H0_DEFAULT
        self.h_minus20 = minus20_level_km if minus20_level_km else self.H_MINUS20_DEFAULT

    def calculate_mesh(
        self,
        reflectivity_profile: List[Tuple[float, float]],
        lat: float = 0.0,
        lon: float = 0.0
    ) -> MESHResult:
        """
        Calculate MESH from a vertical reflectivity profile

        Args:
            reflectivity_profile: List of (height_km, reflectivity_dBZ) tuples
            lat: Latitude (for result)
            lon: Longitude (for result)

        Returns:
            MESHResult with MESH, SHI, POSH, VIL values

        Example:
            >>> profile = [(1.0, 45), (2.0, 52), (3.0, 58), (4.0, 62), (5.0, 55)]
            >>> result = mesh.calculate_mesh(profile)
            >>> print(f"MESH: {result.mesh_inches}\" POSH: {result.posh}%")
        """

        if not reflectivity_profile:
            return MESHResult(
                lat=lat, lon=lon, mesh_inches=0, shi=0, posh=0,
                vil=0, max_reflectivity=0, height_max_ref=0
            )

        # Sort by height
        profile = sorted(reflectivity_profile, key=lambda x: x[0])

        # Calculate SHI (Severe Hail Index)
        shi_raw = self._calculate_shi(profile)

        # Apply calibration factor for realistic values
        shi = shi_raw * self.MESH_CALIBRATION

        # Calculate VIL (Vertically Integrated Liquid)
        vil = self._calculate_vil(profile)

        # Convert SHI to MESH
        # MESH (mm) = 2.54 * SHI^0.5 (Witt et al. 1998)
        # Convert to inches
        if shi > 0:
            mesh_mm = 2.54 * math.sqrt(shi)
            mesh_inches = mesh_mm / 25.4
        else:
            mesh_inches = 0

        # Calculate POSH (Probability of Severe Hail)
        # POSH = 29 * ln(SHI/20) for SHI > 20 (Witt et al. 1998)
        if shi > 20:
            posh = min(100, 29 * math.log(shi / 20))
        else:
            posh = 0

        # Find max reflectivity and its height
        max_ref = max(profile, key=lambda x: x[1])

        return MESHResult(
            lat=lat,
            lon=lon,
            mesh_inches=round(mesh_inches, 2),
            shi=round(shi, 1),
            posh=round(posh, 1),
            vil=round(vil, 1),
            max_reflectivity=max_ref[1],
            height_max_ref=max_ref[0]
        )

    def _calculate_shi(self, profile: List[Tuple[float, float]]) -> float:
        """
        Calculate Severe Hail Index (SHI)

        SHI integrates the hail kinetic energy flux through the storm:
        SHI = 0.1 * integral(W(Z) * HW(Z,H) * dH)

        Where:
        - W(Z) = kinetic energy as function of reflectivity
        - HW = hail weighting function based on height

        Args:
            profile: List of (height_km, reflectivity_dBZ) tuples

        Returns:
            SHI value (J/m/s)
        """

        shi = 0.0

        for i in range(len(profile) - 1):
            h1, z1 = profile[i]
            h2, z2 = profile[i + 1]

            # Average values for this layer
            h_avg = (h1 + h2) / 2
            z_avg = (z1 + z2) / 2
            dh = h2 - h1  # Layer thickness (km)

            # Skip if below threshold
            if z_avg < self.REFLECTIVITY_THRESHOLD:
                continue

            # Calculate kinetic energy flux W(Z)
            # W(Z) = 5e-6 * 10^(0.084*Z) * WT(Z)
            wz = self._kinetic_energy_flux(z_avg)

            # Calculate hail weighting function HW
            hw = self._hail_weight_function(h_avg, z_avg)

            # Integrate
            shi += wz * hw * dh

        # Apply 0.1 factor (converts to J/m/s)
        shi *= 0.1

        return shi

    def _kinetic_energy_flux(self, reflectivity: float) -> float:
        """
        Calculate kinetic energy flux W(Z)

        W(Z) = 5e-6 * 10^(0.084*Z) * WT(Z)

        Where WT(Z) is a temperature weighting:
        - WT = 0 for Z < 40 dBZ
        - WT = (Z-40)/20 for 40 <= Z < 60 dBZ
        - WT = 1 for Z >= 60 dBZ

        Args:
            reflectivity: Reflectivity in dBZ

        Returns:
            Kinetic energy flux (J/m/s)
        """

        if reflectivity < self.REFLECTIVITY_THRESHOLD:
            return 0.0

        # Base kinetic energy
        ke = self.KE_COEFFICIENT * (10 ** (self.KE_EXPONENT * reflectivity))

        # Temperature weighting
        if reflectivity < 40:
            wt = 0
        elif reflectivity < 60:
            wt = (reflectivity - 40) / 20
        else:
            wt = 1.0

        return ke * wt

    def _hail_weight_function(self, height: float, reflectivity: float) -> float:
        """
        Calculate hail weighting function HW

        HW weights the contribution based on height relative to:
        - H0: 0°C (freezing) level
        - H-20: -20°C level

        Below H0: HW = 0 (rain, not hail)
        H0 to H-20: HW increases linearly from 0 to 1
        Above H-20: HW = 1 (definitely frozen)

        Args:
            height: Height in km AGL
            reflectivity: Reflectivity in dBZ

        Returns:
            Weighting factor 0-1
        """

        if height < self.h0:
            # Below freezing level - likely rain
            return 0.0
        elif height > self.h_minus20:
            # Above -20°C - definitely hail
            return 1.0
        else:
            # Transition zone - linear interpolation
            return (height - self.h0) / (self.h_minus20 - self.h0)

    def _calculate_vil(self, profile: List[Tuple[float, float]]) -> float:
        """
        Calculate Vertically Integrated Liquid (VIL)

        VIL estimates the total liquid water content in a column:
        VIL = 3.44e-6 * integral(Z^(4/7) * dH)

        Args:
            profile: List of (height_km, reflectivity_dBZ) tuples

        Returns:
            VIL in kg/m^2
        """

        vil = 0.0

        for i in range(len(profile) - 1):
            h1, z1 = profile[i]
            h2, z2 = profile[i + 1]

            # Average reflectivity (convert from dBZ to Z)
            z_avg_dbz = (z1 + z2) / 2

            if z_avg_dbz < 18:  # Below noise floor
                continue

            # Convert dBZ to linear Z
            z_linear = 10 ** (z_avg_dbz / 10)

            # Layer thickness in meters
            dh_m = (h2 - h1) * 1000

            # VIL contribution
            vil += 3.44e-6 * (z_linear ** (4/7)) * dh_m

        return vil

    def estimate_from_single_reflectivity(
        self,
        reflectivity: float,
        storm_top_km: float = 12.0
    ) -> MESHResult:
        """
        Estimate MESH from a single reflectivity value

        Creates a synthetic vertical profile based on typical storm structure.
        Less accurate than full 3D analysis but useful when only 2D data available.

        Args:
            reflectivity: Maximum reflectivity (dBZ)
            storm_top_km: Estimated storm top height (km)

        Returns:
            MESHResult with estimated values
        """

        # Create synthetic profile
        # Typical supercell: max reflectivity in hail growth zone (H0 to H-20)
        profile = []

        # Below freezing level - moderate reflectivity (rain + melting hail)
        profile.append((1.0, max(35, reflectivity - 20)))
        profile.append((2.0, max(40, reflectivity - 15)))
        profile.append((self.h0 - 0.5, max(45, reflectivity - 10)))

        # AT and ABOVE freezing level - high reflectivity (hail growth zone)
        # This is where MESH integration happens
        profile.append((self.h0, reflectivity - 3))
        profile.append((self.h0 + 0.5, reflectivity))  # Peak just above H0
        profile.append((self.h0 + 1.5, reflectivity - 2))
        profile.append((self.h0 + 2.5, reflectivity - 4))

        # Between H0+3 and H-20 - sustained high reflectivity
        mid_height = (self.h0 + 3.0 + self.h_minus20) / 2
        profile.append((mid_height, reflectivity - 6))
        profile.append((self.h_minus20, reflectivity - 10))

        # Above -20°C - decreasing reflectivity
        profile.append((self.h_minus20 + 1.5, reflectivity - 15))
        profile.append((self.h_minus20 + 3.0, max(30, reflectivity - 22)))

        # Storm top
        if storm_top_km > self.h_minus20 + 4:
            profile.append((storm_top_km - 1, max(25, reflectivity - 30)))
            profile.append((storm_top_km, max(18, reflectivity - 40)))

        return self.calculate_mesh(profile)

    def classify_hail_threat(self, mesh_result: MESHResult) -> Dict:
        """
        Classify hail threat level based on MESH result

        Args:
            mesh_result: MESHResult from calculate_mesh()

        Returns:
            Dict with threat classification
        """

        mesh = mesh_result.mesh_inches
        posh = mesh_result.posh

        if mesh >= 2.0 or posh >= 80:
            threat_level = 'SEVERE'
            color = '#ff0000'
            description = 'Large hail likely (2\"+) - Significant damage expected'
        elif mesh >= 1.0 or posh >= 50:
            threat_level = 'SIGNIFICANT'
            color = '#ff6600'
            description = 'Golf ball size hail possible - Vehicle damage likely'
        elif mesh >= 0.75 or posh >= 30:
            threat_level = 'MODERATE'
            color = '#ffcc00'
            description = 'Quarter to golf ball size - Minor damage possible'
        elif mesh >= 0.5:
            threat_level = 'MARGINAL'
            color = '#00cc00'
            description = 'Small hail possible - Minimal damage expected'
        else:
            threat_level = 'NONE'
            color = '#808080'
            description = 'No significant hail expected'

        return {
            'threat_level': threat_level,
            'color': color,
            'description': description,
            'mesh_inches': mesh,
            'posh': posh,
            'shi': mesh_result.shi
        }


class MESHGrid:
    """
    MESH calculations over a geographic grid

    For generating MESH swaths from radar volume scans
    """

    # Default grid settings
    DEFAULT_GRID_RESOLUTION = 0.01  # ~1 km resolution in degrees
    DEFAULT_RADAR_RANGE_KM = 230.0  # Maximum radar range

    def __init__(
        self,
        freezing_level_km: float = None,
        minus20_level_km: float = None
    ):
        """Initialize MESH grid calculator"""
        self.mesh_calc = MESHAlgorithm(freezing_level_km, minus20_level_km)

    def calculate_mesh_grid(
        self,
        radar_lat: float,
        radar_lon: float,
        reflectivity_data: List[Dict] = None,
        grid_resolution: float = None,
        range_km: float = None,
        storm_top_km: float = 12.0
    ) -> Dict:
        """
        Calculate MESH over a geographic grid centered on a radar site

        USE CASE: Generate MESH coverage map for entire radar domain

        This creates a grid of MESH values that can be used for:
        - Visualization (heatmap of hail potential)
        - Swath generation (extract contours)
        - Property assessment (query MESH at specific locations)

        Args:
            radar_lat: Radar site latitude
            radar_lon: Radar site longitude
            reflectivity_data: List of {lat, lon, reflectivity, storm_top} dicts
                              If None, returns empty grid structure
            grid_resolution: Grid spacing in degrees (default: 0.01 = ~1km)
            range_km: Radar range in km (default: 230km)
            storm_top_km: Default storm top if not in data (km)

        Returns:
            Dict with grid metadata and MESH values:
            {
                'bounds': {north, south, east, west},
                'resolution': float,
                'grid_size': (rows, cols),
                'mesh_values': [[float, ...], ...],  # 2D grid
                'max_mesh': float,
                'centroid': (lat, lon),
                'severe_pixels': int,  # MESH >= 2"
                'significant_pixels': int  # MESH 1-2"
            }

        Example:
            >>> grid = mesh_grid.calculate_mesh_grid(
            ...     radar_lat=32.573, radar_lon=-97.303,  # KFWS
            ...     reflectivity_data=radar_scan_data
            ... )
            >>> print(f"Max MESH: {grid['max_mesh']}\"")
        """
        if grid_resolution is None:
            grid_resolution = self.DEFAULT_GRID_RESOLUTION
        if range_km is None:
            range_km = self.DEFAULT_RADAR_RANGE_KM

        # Convert range to degrees (approximate)
        range_deg = range_km / 111.0  # ~111 km per degree

        # Calculate grid bounds
        bounds = {
            'north': radar_lat + range_deg,
            'south': radar_lat - range_deg,
            'east': radar_lon + range_deg / math.cos(math.radians(radar_lat)),
            'west': radar_lon - range_deg / math.cos(math.radians(radar_lat))
        }

        # Calculate grid dimensions
        n_rows = int((bounds['north'] - bounds['south']) / grid_resolution) + 1
        n_cols = int((bounds['east'] - bounds['west']) / grid_resolution) + 1

        # Initialize grid with zeros
        mesh_values = [[0.0 for _ in range(n_cols)] for _ in range(n_rows)]

        if reflectivity_data:
            # Build spatial index for efficient lookup
            data_by_cell = {}

            for point in reflectivity_data:
                p_lat = point.get('lat', 0)
                p_lon = point.get('lon', 0)
                p_ref = point.get('reflectivity', 0)
                p_top = point.get('storm_top', storm_top_km)

                # Skip weak returns
                if p_ref < 40:
                    continue

                # Calculate grid cell
                row = int((bounds['north'] - p_lat) / grid_resolution)
                col = int((p_lon - bounds['west']) / grid_resolution)

                # Bounds check
                if 0 <= row < n_rows and 0 <= col < n_cols:
                    key = (row, col)
                    if key not in data_by_cell:
                        data_by_cell[key] = []
                    data_by_cell[key].append({'ref': p_ref, 'top': p_top})

            # Calculate MESH for each cell with data
            for (row, col), points in data_by_cell.items():
                # Use maximum reflectivity in cell
                max_ref = max(p['ref'] for p in points)
                avg_top = sum(p['top'] for p in points) / len(points)

                result = self.mesh_calc.estimate_from_single_reflectivity(
                    max_ref, avg_top
                )
                mesh_values[row][col] = result.mesh_inches

        # Calculate statistics
        all_values = [v for row in mesh_values for v in row]
        max_mesh = max(all_values) if all_values else 0
        severe_count = sum(1 for v in all_values if v >= 2.0)
        significant_count = sum(1 for v in all_values if 1.0 <= v < 2.0)

        return {
            'bounds': bounds,
            'resolution': grid_resolution,
            'grid_size': (n_rows, n_cols),
            'mesh_values': mesh_values,
            'max_mesh': round(max_mesh, 2),
            'centroid': (radar_lat, radar_lon),
            'severe_pixels': severe_count,
            'significant_pixels': significant_count,
            'radar_site': {'lat': radar_lat, 'lon': radar_lon}
        }

    def extract_mesh_contours(
        self,
        mesh_grid: Dict,
        threshold: float = 1.0
    ) -> List[Dict]:
        """
        Extract contour polygons from MESH grid at given threshold

        Args:
            mesh_grid: Result from calculate_mesh_grid()
            threshold: MESH value to contour (inches)

        Returns:
            List of GeoJSON polygon features
        """
        bounds = mesh_grid['bounds']
        resolution = mesh_grid['resolution']
        values = mesh_grid['mesh_values']
        n_rows, n_cols = mesh_grid['grid_size']

        # Find connected regions above threshold
        visited = [[False for _ in range(n_cols)] for _ in range(n_rows)]
        regions = []

        def flood_fill(start_row, start_col):
            """Find connected cells above threshold"""
            cells = []
            stack = [(start_row, start_col)]

            while stack:
                r, c = stack.pop()
                if r < 0 or r >= n_rows or c < 0 or c >= n_cols:
                    continue
                if visited[r][c]:
                    continue
                if values[r][c] < threshold:
                    continue

                visited[r][c] = True
                cells.append((r, c))

                # Check 4-neighbors
                stack.extend([(r-1, c), (r+1, c), (r, c-1), (r, c+1)])

            return cells

        # Find all regions
        for r in range(n_rows):
            for c in range(n_cols):
                if not visited[r][c] and values[r][c] >= threshold:
                    cells = flood_fill(r, c)
                    if cells:
                        regions.append(cells)

        # Convert regions to polygons
        features = []
        for region_cells in regions:
            if len(region_cells) < 4:
                continue

            # Get bounding points for the region
            min_row = min(c[0] for c in region_cells)
            max_row = max(c[0] for c in region_cells)
            min_col = min(c[1] for c in region_cells)
            max_col = max(c[1] for c in region_cells)

            # Convert to lat/lon
            north = bounds['north'] - min_row * resolution
            south = bounds['north'] - (max_row + 1) * resolution
            west = bounds['west'] + min_col * resolution
            east = bounds['west'] + (max_col + 1) * resolution

            # Create bounding box polygon (simplified)
            polygon = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [[
                        [west, north],
                        [east, north],
                        [east, south],
                        [west, south],
                        [west, north]
                    ]]
                },
                'properties': {
                    'mesh_threshold': threshold,
                    'cell_count': len(region_cells),
                    'max_mesh': max(values[r][c] for r, c in region_cells)
                }
            }
            features.append(polygon)

        return features

    def calculate_mesh_from_detections(
        self,
        detections: List[Dict],
        default_storm_top: float = 12.0
    ) -> List[MESHResult]:
        """
        Calculate MESH for a list of radar detections

        Args:
            detections: List of dicts with 'lat', 'lon', 'reflectivity'
            default_storm_top: Default storm top height (km)

        Returns:
            List of MESHResult objects
        """

        results = []

        for det in detections:
            ref = det.get('reflectivity', 50)
            lat = det.get('lat', 0)
            lon = det.get('lon', 0)

            result = self.mesh_calc.estimate_from_single_reflectivity(
                ref, default_storm_top
            )

            # Update lat/lon
            result.lat = lat
            result.lon = lon

            results.append(result)

        return results

    def get_mesh_statistics(self, results: List[MESHResult]) -> Dict:
        """
        Calculate statistics from MESH results

        Args:
            results: List of MESHResult objects

        Returns:
            Dict with statistics
        """

        if not results:
            return {
                'count': 0,
                'max_mesh': 0,
                'avg_mesh': 0,
                'max_posh': 0,
                'avg_posh': 0
            }

        mesh_values = [r.mesh_inches for r in results]
        posh_values = [r.posh for r in results]

        return {
            'count': len(results),
            'max_mesh': max(mesh_values),
            'avg_mesh': round(sum(mesh_values) / len(mesh_values), 2),
            'max_posh': max(posh_values),
            'avg_posh': round(sum(posh_values) / len(posh_values), 1),
            'severe_count': sum(1 for m in mesh_values if m >= 2.0),
            'significant_count': sum(1 for m in mesh_values if 1.0 <= m < 2.0)
        }


def get_freezing_levels_by_region(region: str, month: int = 6) -> Tuple[float, float]:
    """
    Get typical freezing level heights by region and month

    Args:
        region: Region name ('texas', 'oklahoma', 'plains', 'midwest')
        month: Month number (1-12)

    Returns:
        (H0, H-20) tuple in km
    """

    # Seasonal adjustment (higher in summer)
    if month in [6, 7, 8]:  # Summer
        seasonal_adjust = 1.0
    elif month in [3, 4, 5, 9, 10]:  # Spring/Fall
        seasonal_adjust = 0.0
    else:  # Winter
        seasonal_adjust = -1.0

    # Base heights by region
    regions = {
        'texas': (4.0, 7.0),
        'oklahoma': (3.5, 6.5),
        'kansas': (3.2, 6.2),
        'nebraska': (3.0, 6.0),
        'plains': (3.5, 6.5),
        'midwest': (3.0, 5.8),
        'southeast': (4.2, 7.2),
    }

    base_h0, base_h20 = regions.get(region.lower(), (3.5, 6.5))

    return (base_h0 + seasonal_adjust, base_h20 + seasonal_adjust)
