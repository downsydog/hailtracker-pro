"""
NEXRAD Dual-Polarization Data Fetcher
Downloads and processes Level-II radar data with dual-pol variables

Dual-polarization radar sends BOTH horizontal AND vertical pulses, giving us:
- Reflectivity (Z) - How much energy returns (rain vs hail intensity)
- Differential Reflectivity (ZDR) - Difference between H and V returns
  - Low ZDR (~0 dB) = Spherical objects (HAIL!)
  - High ZDR (3+ dB) = Flat objects (raindrops)
- Correlation Coefficient (CC) - How similar H and V pulses are
  - High CC (>0.97) = Uniform precipitation (rain)
  - Low CC (<0.90) = Mixed/tumbling objects (HAIL!)
- Specific Differential Phase (KDP) - Phase shift rate
  - High KDP = Heavy rain
  - Low KDP + High Z = Likely hail
"""

import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Check for optional dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import pyart
    PYART_AVAILABLE = True
except ImportError:
    PYART_AVAILABLE = False

try:
    import nexradaws
    NEXRADAWS_AVAILABLE = True
except ImportError:
    NEXRADAWS_AVAILABLE = False


@dataclass
class DualPolSignature:
    """Dual-polarization hail signature"""
    lat: float
    lon: float
    reflectivity: float  # dBZ
    zdr: Optional[float] = None  # Differential reflectivity (dB)
    cc: Optional[float] = None   # Correlation coefficient
    kdp: Optional[float] = None  # Specific differential phase (deg/km)
    hail_probability: float = 0.0  # 0-1
    hail_size_inches: float = 0.0
    range_km: float = 0.0
    azimuth: float = 0.0


class DualPolRadar:
    """
    Fetch and process NEXRAD Level-II dual-polarization data

    Dual-pol radar provides better hail detection by analyzing:
    - Shape (ZDR) - Hail is spherical, rain is flat
    - Tumbling (CC) - Hail tumbles, rain falls uniformly
    - Phase shift (KDP) - Helps distinguish heavy rain
    """

    # Dual-pol field names (PyART standard)
    REFLECTIVITY = 'reflectivity'
    ZDR = 'differential_reflectivity'
    CC = 'cross_correlation_ratio'
    KDP = 'specific_differential_phase'

    # Hail detection thresholds (from research papers)
    # Sources: Kumjian & Ryzhkov (2008), Park et al. (2009)
    HAIL_THRESHOLDS = {
        'reflectivity_min': 50,      # dBZ - minimum for hail consideration
        'reflectivity_severe': 60,   # dBZ - severe hail likely
        'zdr_max_hail': 1.0,         # dB - hail is spherical (low ZDR)
        'cc_max_hail': 0.90,         # correlation - hail is tumbling (low CC)
        'kdp_min': 0.5,              # deg/km - helps separate heavy rain
    }

    # Simulated data mode flag (for testing without actual radar data)
    SIMULATION_MODE = not (PYART_AVAILABLE and NEXRADAWS_AVAILABLE and NUMPY_AVAILABLE)

    def __init__(self):
        """Initialize dual-pol radar fetcher"""
        if self.SIMULATION_MODE:
            print("Note: Running in simulation mode (pyart/nexradaws not installed)")
            print("      Install with: pip install arm-pyart nexradaws")
        else:
            self.conn = nexradaws.NexradAwsInterface()

    def fetch_radar_scan(
        self,
        radar_site: str,
        scan_time: datetime
    ) -> Optional[object]:
        """
        Fetch NEXRAD Level-II scan from AWS S3

        Args:
            radar_site: 4-letter radar ID (e.g. 'KFWS')
            scan_time: Datetime of scan

        Returns:
            PyART radar object with dual-pol data (or None in simulation mode)

        Example:
            >>> radar = fetcher.fetch_radar_scan('KFWS', datetime(2024, 11, 15, 14, 30))
        """

        if self.SIMULATION_MODE:
            print(f"[Simulation] Would fetch {radar_site} scan for {scan_time}")
            return None

        try:
            # Get available scans for this time
            scans = self.conn.get_avail_scans_in_range(
                scan_time - timedelta(minutes=10),
                scan_time + timedelta(minutes=10),
                radar_site
            )

            if not scans:
                print(f"No scans found for {radar_site} at {scan_time}")
                return None

            # Download first available scan
            scan = scans[0]

            print(f"Downloading {radar_site} scan from {scan.scan_time}...")

            # Download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gz') as tmp:
                tmp_path = tmp.name
                self.conn.download(scan, tmp_path)

            # Read with PyART
            radar = pyart.io.read_nexrad_archive(tmp_path)

            # Clean up temp file
            os.unlink(tmp_path)

            print(f"Loaded radar scan with {len(radar.fields)} fields")
            print(f"   Available fields: {', '.join(radar.fields.keys())}")

            return radar

        except Exception as e:
            print(f"Error fetching radar data: {e}")
            return None

    def extract_hail_signatures(
        self,
        radar: object = None,
        elevation_angle: float = 0.5
    ) -> List[DualPolSignature]:
        """
        Extract hail signatures from dual-pol data

        Args:
            radar: PyART radar object (None for simulation)
            elevation_angle: Radar elevation to analyze (degrees)

        Returns:
            List of DualPolSignature objects

        Algorithm:
            1. Find high reflectivity cores (>50 dBZ)
            2. Check ZDR (should be low for hail)
            3. Check CC (should be low for hail)
            4. Calculate hail probability
        """

        if self.SIMULATION_MODE or radar is None:
            return self._simulate_hail_signatures()

        # Find sweep closest to desired elevation
        sweep_idx = self._get_sweep_index(radar, elevation_angle)

        if sweep_idx is None:
            print(f"No sweep found near {elevation_angle} degrees")
            return []

        # Extract data for this sweep
        sweep_slice = radar.get_slice(sweep_idx)

        # Get dual-pol fields
        ref = radar.get_field(sweep_idx, self.REFLECTIVITY)

        # Check if dual-pol fields available
        has_zdr = self.ZDR in radar.fields
        has_cc = self.CC in radar.fields

        zdr = radar.get_field(sweep_idx, self.ZDR) if has_zdr else None
        cc = radar.get_field(sweep_idx, self.CC) if has_cc else None

        if not has_zdr:
            print("Warning: No ZDR data available")
        if not has_cc:
            print("Warning: No CC data available")

        # Get coordinates
        azimuth = radar.azimuth['data'][sweep_slice]
        range_km = radar.range['data'] / 1000.0

        # Radar location
        radar_lat = radar.latitude['data'][0]
        radar_lon = radar.longitude['data'][0]

        # Find hail signatures
        detections = []

        for az_idx in range(len(azimuth)):
            for range_idx in range(len(range_km)):

                # Get values at this gate
                z = ref[az_idx, range_idx]

                # Skip if no data or below threshold
                if np.ma.is_masked(z) or z < self.HAIL_THRESHOLDS['reflectivity_min']:
                    continue

                # Get dual-pol values
                zdr_val = None
                cc_val = None

                if zdr is not None and not np.ma.is_masked(zdr[az_idx, range_idx]):
                    zdr_val = float(zdr[az_idx, range_idx])

                if cc is not None and not np.ma.is_masked(cc[az_idx, range_idx]):
                    cc_val = float(cc[az_idx, range_idx])

                # Calculate hail probability
                hail_prob = self._calculate_hail_probability(float(z), zdr_val, cc_val)

                # Only keep high probability detections
                if hail_prob < 0.5:
                    continue

                # Convert to lat/lon
                lat, lon = self._radar_coords_to_latlon(
                    radar_lat, radar_lon,
                    azimuth[az_idx], range_km[range_idx]
                )

                # Estimate hail size
                hail_size = self._estimate_hail_size(float(z), zdr_val)

                detections.append(DualPolSignature(
                    lat=lat,
                    lon=lon,
                    reflectivity=float(z),
                    zdr=zdr_val,
                    cc=cc_val,
                    hail_probability=hail_prob,
                    hail_size_inches=hail_size,
                    range_km=float(range_km[range_idx]),
                    azimuth=float(azimuth[az_idx])
                ))

        print(f"Found {len(detections)} hail signatures")

        # Filter to significant detections (combine nearby points)
        filtered = self._filter_detections(detections)

        print(f"Filtered to {len(filtered)} significant hail cores")

        return filtered

    def _simulate_hail_signatures(self) -> List[DualPolSignature]:
        """
        Generate simulated hail signatures for testing

        Returns realistic dual-pol values based on research
        """

        print("Generating simulated dual-pol hail signatures...")

        # Simulated DFW hail event
        signatures = [
            DualPolSignature(
                lat=32.70, lon=-97.00,
                reflectivity=55.0, zdr=0.8, cc=0.88,
                hail_probability=0.72,
                hail_size_inches=1.25,
                range_km=45.0, azimuth=120.0
            ),
            DualPolSignature(
                lat=32.75, lon=-96.90,
                reflectivity=62.0, zdr=0.3, cc=0.85,
                hail_probability=0.85,
                hail_size_inches=1.75,
                range_km=52.0, azimuth=125.0
            ),
            DualPolSignature(
                lat=32.80, lon=-96.80,
                reflectivity=68.0, zdr=-0.2, cc=0.82,
                hail_probability=0.92,
                hail_size_inches=2.50,
                range_km=60.0, azimuth=130.0
            ),
            DualPolSignature(
                lat=32.85, lon=-96.70,
                reflectivity=65.0, zdr=0.1, cc=0.84,
                hail_probability=0.88,
                hail_size_inches=2.00,
                range_km=68.0, azimuth=135.0
            ),
            DualPolSignature(
                lat=32.90, lon=-96.60,
                reflectivity=58.0, zdr=0.6, cc=0.87,
                hail_probability=0.75,
                hail_size_inches=1.50,
                range_km=75.0, azimuth=140.0
            ),
        ]

        print(f"Generated {len(signatures)} simulated hail signatures")

        return signatures

    def _calculate_hail_probability(
        self,
        reflectivity: float,
        zdr: Optional[float],
        cc: Optional[float]
    ) -> float:
        """
        Calculate probability of hail based on dual-pol signatures

        Algorithm based on:
        - Kumjian & Ryzhkov (2008) - "Polarimetric Signatures in Supercell Thunderstorms"
        - Park et al. (2009) - "The Hydrometeor Classification Algorithm"

        Args:
            reflectivity: Reflectivity (dBZ)
            zdr: Differential reflectivity (dB)
            cc: Correlation coefficient

        Returns:
            Probability 0.0 - 1.0
        """

        probability = 0.0

        # Factor 1: High reflectivity (40% weight)
        if reflectivity >= 60:
            probability += 0.40
        elif reflectivity >= 55:
            probability += 0.30
        elif reflectivity >= 50:
            probability += 0.20

        # Factor 2: Low ZDR indicates spherical hail (30% weight)
        if zdr is not None:
            if zdr <= 0.5:
                probability += 0.30
            elif zdr <= 1.0:
                probability += 0.20
            elif zdr <= 1.5:
                probability += 0.10
        else:
            # No ZDR data - assume moderate probability
            probability += 0.15

        # Factor 3: Low CC indicates tumbling hail (30% weight)
        if cc is not None:
            if cc <= 0.85:
                probability += 0.30
            elif cc <= 0.90:
                probability += 0.20
            elif cc <= 0.95:
                probability += 0.10
        else:
            # No CC data - assume moderate probability
            probability += 0.15

        return min(probability, 1.0)

    def _estimate_hail_size(
        self,
        reflectivity: float,
        zdr: Optional[float]
    ) -> float:
        """
        Estimate hail size from radar data

        Uses combination of:
        - Reflectivity (higher = larger)
        - ZDR (lower = more spherical = larger hail)

        Args:
            reflectivity: Reflectivity (dBZ)
            zdr: Differential reflectivity (dB)

        Returns:
            Estimated hail size in inches
        """

        # Base estimate from reflectivity only
        # (Traditional method - improved with dual-pol)
        if reflectivity >= 70:
            size = 3.0  # Baseball+
        elif reflectivity >= 65:
            size = 2.5  # Tennis ball
        elif reflectivity >= 60:
            size = 2.0  # Lime / Golf ball+
        elif reflectivity >= 55:
            size = 1.5  # Walnut
        elif reflectivity >= 50:
            size = 1.0  # Quarter
        else:
            size = 0.75  # Penny

        # Adjust based on ZDR
        # Lower ZDR = larger hail (more spherical)
        if zdr is not None:
            if zdr < 0:
                size *= 1.2  # Likely giant hail
            elif zdr < 0.5:
                size *= 1.1  # Large hail
            elif zdr > 2.0:
                size *= 0.8  # Might be heavy rain, not hail

        return round(size, 2)

    def _get_sweep_index(self, radar: object, elevation: float) -> Optional[int]:
        """Find sweep index closest to desired elevation angle"""

        if not NUMPY_AVAILABLE:
            return 0

        elevations = radar.fixed_angle['data']

        # Find closest
        diff = np.abs(elevations - elevation)
        closest_idx = np.argmin(diff)

        if diff[closest_idx] > 1.0:  # More than 1 degree different
            return None

        return closest_idx

    def _radar_coords_to_latlon(
        self,
        radar_lat: float,
        radar_lon: float,
        azimuth: float,
        range_km: float
    ) -> Tuple[float, float]:
        """
        Convert radar polar coordinates to lat/lon

        Args:
            radar_lat: Radar latitude
            radar_lon: Radar longitude
            azimuth: Azimuth angle (degrees from north)
            range_km: Range (kilometers)

        Returns:
            (lat, lon) tuple
        """

        import math

        # Earth radius in km
        R = 6371.0

        # Convert to radians
        lat1 = math.radians(radar_lat)
        lon1 = math.radians(radar_lon)
        bearing = math.radians(azimuth)

        # Calculate new position
        lat2 = math.asin(
            math.sin(lat1) * math.cos(range_km / R) +
            math.cos(lat1) * math.sin(range_km / R) * math.cos(bearing)
        )

        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(range_km / R) * math.cos(lat1),
            math.cos(range_km / R) - math.sin(lat1) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)

    def _filter_detections(
        self,
        detections: List[DualPolSignature],
        min_spacing_km: float = 5.0
    ) -> List[DualPolSignature]:
        """
        Filter detections to remove duplicates and combine nearby points

        Args:
            detections: List of DualPolSignature objects
            min_spacing_km: Minimum spacing between detections

        Returns:
            Filtered list of significant detections
        """

        if len(detections) < 2:
            return detections

        # Sort by hail probability (highest first)
        sorted_dets = sorted(detections, key=lambda x: x.hail_probability, reverse=True)

        filtered = []

        for det in sorted_dets:
            # Check if too close to existing detection
            too_close = False

            for existing in filtered:
                # Calculate distance
                dlat = det.lat - existing.lat
                dlon = det.lon - existing.lon
                dist_deg = (dlat**2 + dlon**2)**0.5
                dist_km = dist_deg * 111  # Rough conversion

                if dist_km < min_spacing_km:
                    too_close = True
                    break

            if not too_close:
                filtered.append(det)

        return filtered

    def signatures_to_detections(
        self,
        signatures: List[DualPolSignature],
        timestamp: str,
        storm_motion_dir: Optional[float] = None,
        storm_motion_speed: Optional[float] = None
    ) -> List['HailDetection']:
        """
        Convert dual-pol signatures to HailDetection objects

        Args:
            signatures: List of DualPolSignature objects
            timestamp: ISO format timestamp
            storm_motion_dir: Storm direction (degrees)
            storm_motion_speed: Storm speed (mph)

        Returns:
            List of HailDetection objects for swath generation
        """

        from src.radar.swath_generator import HailDetection

        detections = []

        for sig in signatures:
            detections.append(HailDetection(
                lat=sig.lat,
                lon=sig.lon,
                hail_size=sig.hail_size_inches,
                timestamp=timestamp,
                reflectivity=sig.reflectivity,
                zdr=sig.zdr,
                cc=sig.cc,
                hail_probability=sig.hail_probability,
                storm_motion_dir=storm_motion_dir,
                storm_motion_speed=storm_motion_speed
            ))

        return detections

    def calculate_mesh_for_signatures(
        self,
        signatures: List[DualPolSignature],
        freezing_level_km: float = 3.5,
        storm_top_km: float = 12.0
    ) -> List[DualPolSignature]:
        """
        Calculate MESH hail sizes for signatures and update them

        MESH (Maximum Estimated Size of Hail) provides more accurate
        size estimates by considering vertical storm structure.

        Args:
            signatures: List of DualPolSignature objects
            freezing_level_km: Height of 0°C level (km)
            storm_top_km: Estimated storm top height (km)

        Returns:
            Updated signatures with MESH-based hail sizes
        """

        from src.radar.mesh_algorithm import MESHAlgorithm

        mesh_calc = MESHAlgorithm(
            freezing_level_km=freezing_level_km,
            minus20_level_km=freezing_level_km + 3.0
        )

        updated = []

        for sig in signatures:
            # Calculate MESH from reflectivity
            mesh_result = mesh_calc.estimate_from_single_reflectivity(
                sig.reflectivity,
                storm_top_km
            )

            # Create updated signature with MESH size
            updated_sig = DualPolSignature(
                lat=sig.lat,
                lon=sig.lon,
                reflectivity=sig.reflectivity,
                zdr=sig.zdr,
                cc=sig.cc,
                kdp=sig.kdp,
                hail_probability=sig.hail_probability,
                hail_size_inches=mesh_result.mesh_inches,  # MESH-based size
                range_km=sig.range_km,
                azimuth=sig.azimuth
            )

            updated.append(updated_sig)

        return updated


def get_dualpol_availability() -> Dict[str, bool]:
    """
    Check availability of dual-pol dependencies

    Returns:
        Dict with availability status
    """
    return {
        'numpy': NUMPY_AVAILABLE,
        'pyart': PYART_AVAILABLE,
        'nexradaws': NEXRADAWS_AVAILABLE,
        'simulation_mode': DualPolRadar.SIMULATION_MODE
    }
