"""
Real-Time Multi-Radar Fusion

Integrates NEXRAD data from multiple radars for improved hail detection.
Downloads, processes, and fuses data in real-time.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.radar.nexrad import NEXRADDownloader, NEXRADAWS_AVAILABLE, PYART_AVAILABLE
from src.radar.fusion import MultiRadarFusion, HailCore, FusedHailDetection, FusionProcessor
from src.radar.coverage import find_covering_radars, haversine_distance

logger = logging.getLogger('RealtimeFusion')


class RealtimeMultiRadarFusion:
    """
    Real-time multi-radar fusion for hail detection.

    Workflow:
    1. Find radars covering a location
    2. Download recent scans from each radar
    3. Process for MESH/hail signatures
    4. Fuse detections with confidence scoring
    """

    def __init__(self, data_dir: Optional[str] = None, max_radars: int = 5):
        """
        Initialize real-time fusion.

        Args:
            data_dir: Directory for radar data
            max_radars: Maximum radars to process (for performance)
        """
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / 'data' / 'radar_fusion'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.max_radars = max_radars
        self.downloader = NEXRADDownloader(str(self.data_dir / 'nexrad'))
        self.fusion_engine = MultiRadarFusion()
        self.processor = FusionProcessor(str(self.data_dir / 'fused'))

        # Cache for recent data
        self.radar_cache = {}
        self.cache_duration = timedelta(minutes=15)

    def get_covering_radars(self, lat: float, lon: float,
                            max_distance_km: float = 230) -> List[Dict]:
        """
        Find radars that cover a location.

        Args:
            lat: Latitude
            lon: Longitude
            max_distance_km: Maximum radar range

        Returns:
            List of radar info dicts, sorted by distance
        """
        coverage_list = find_covering_radars(lat, lon, max_distance_km=max_distance_km)

        # Convert RadarCoverage objects to dicts for easier use
        radars = []
        for cov in coverage_list[:self.max_radars]:
            radars.append({
                'id': cov.radar.site_code,
                'name': cov.radar.name,
                'lat': cov.radar.latitude,
                'lon': cov.radar.longitude,
                'distance_km': cov.distance_km,
                'bearing_deg': cov.bearing_deg,
                'quality': cov.coverage_quality,
                'is_primary': cov.is_primary,
            })

        return radars

    def download_recent_scans(
        self,
        radar_ids: List[str],
        lookback_minutes: int = 30
    ) -> Dict[str, List]:
        """
        Download recent scans from multiple radars.

        Args:
            radar_ids: List of radar IDs
            lookback_minutes: How far back to look

        Returns:
            Dict of radar_id -> list of downloaded file paths
        """
        if not NEXRADAWS_AVAILABLE:
            logger.error("nexradaws not available")
            return {}

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=lookback_minutes)

        results = {}

        def download_radar(radar_id):
            try:
                scans = self.downloader.list_available_files(
                    radar_id, start_time, end_time
                )

                if not scans:
                    return radar_id, []

                # Download most recent scan
                downloaded = []
                for scan in scans[-2:]:  # Last 2 scans
                    path = self.downloader.download_scan(scan)
                    if path:
                        downloaded.append(path)

                return radar_id, downloaded

            except Exception as e:
                logger.error(f"Error downloading {radar_id}: {e}")
                return radar_id, []

        # Download in parallel
        with ThreadPoolExecutor(max_workers=min(4, len(radar_ids))) as executor:
            futures = {executor.submit(download_radar, rid): rid for rid in radar_ids}

            for future in as_completed(futures):
                radar_id, files = future.result()
                results[radar_id] = files

        return results

    def process_scan_for_hail(
        self,
        scan_path: str,
        radar_id: str,
        radar_lat: float,
        radar_lon: float
    ) -> List[HailCore]:
        """
        Process a radar scan for hail signatures.

        Args:
            scan_path: Path to radar data file
            radar_id: Radar ID
            radar_lat: Radar latitude
            radar_lon: Radar longitude

        Returns:
            List of HailCore detections
        """
        if not PYART_AVAILABLE:
            logger.warning("PyART not available, using synthetic data")
            return self._generate_synthetic_cores(radar_id, radar_lat, radar_lon)

        try:
            import pyart

            # Read radar file
            radar = pyart.io.read_nexrad_archive(scan_path)

            # Get timestamp - handle various formats
            try:
                time_units = radar.time['units']
                # Format: "seconds since YYYY-MM-DDTHH:MM:SSZ"
                if 'since' in time_units:
                    time_str = time_units.split('since')[-1].strip()
                    # Try multiple formats
                    for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            timestamp = datetime.strptime(time_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()
            except Exception:
                timestamp = datetime.utcnow()

            # Get reflectivity
            if 'reflectivity' not in radar.fields:
                logger.warning(f"No reflectivity in {scan_path}")
                return []

            ref = radar.fields['reflectivity']['data']

            # Simple MESH approximation from max reflectivity
            # (Full MESH would require 3D analysis)
            max_ref = np.nanmax(ref, axis=0)

            # Convert to MESH using Witt et al. relationship
            # MESH ≈ 0.098 * SHI^0.5 where SHI relates to reflectivity
            mesh_approx = np.zeros_like(max_ref)
            hail_mask = max_ref >= 45  # dBZ threshold

            if np.any(hail_mask):
                # Approximate MESH from reflectivity (simplified)
                mesh_approx[hail_mask] = 0.1 * (max_ref[hail_mask] - 40) ** 0.5

            # Find hail cores
            cores = []
            from scipy import ndimage

            # Ensure 2D array for processing
            if mesh_approx.ndim == 1:
                # Reshape to 2D (azimuths x ranges)
                n_azimuths = ref.shape[0] if ref.ndim >= 1 else 360
                mesh_approx = mesh_approx.reshape(1, -1)
                max_ref = max_ref.reshape(1, -1)

            labeled, num_features = ndimage.label(mesh_approx > 0.5)

            for i in range(1, num_features + 1):
                core_mask = labeled == i
                core_mesh = mesh_approx[core_mask]

                if len(core_mesh) == 0:
                    continue

                max_mesh = float(np.nanmax(core_mesh))

                # Get position
                positions = np.where(core_mask)
                if len(positions) < 2 or len(positions[0]) == 0:
                    continue

                center_azimuth = np.mean(positions[1]) if len(positions) > 1 else 0
                center_range_idx = np.mean(positions[0])

                # Convert to lat/lon (simplified)
                range_km = center_range_idx * 0.25  # Approximate gate spacing
                azimuth_deg = center_azimuth * (360 / mesh_approx.shape[1])

                import math
                core_lat = radar_lat + (range_km / 111.0) * math.cos(math.radians(azimuth_deg))
                core_lon = radar_lon + (range_km / (111.0 * math.cos(math.radians(radar_lat)))) * math.sin(math.radians(azimuth_deg))

                distance = haversine_distance(radar_lat, radar_lon, core_lat, core_lon)
                confidence = 1.0 / (1.0 + distance / 150.0)

                cores.append(HailCore(
                    radar_site=radar_id,
                    timestamp=timestamp,
                    lat=core_lat,
                    lon=core_lon,
                    mesh_inches=max_mesh,
                    reflectivity_dbz=float(np.nanmax(max_ref[core_mask])),
                    distance_from_radar=distance,
                    detection_confidence=confidence
                ))

            return cores

        except Exception as e:
            import traceback
            logger.error(f"Error processing {scan_path}: {e}\n{traceback.format_exc()}")
            return []

    def _generate_synthetic_cores(
        self,
        radar_id: str,
        radar_lat: float,
        radar_lon: float
    ) -> List[HailCore]:
        """Generate synthetic hail cores for testing."""
        import random

        cores = []
        num_cores = random.randint(0, 3)

        for _ in range(num_cores):
            # Random offset from radar
            offset_km = random.uniform(30, 150)
            angle = random.uniform(0, 360)

            import math
            lat_offset = offset_km / 111.0 * math.cos(math.radians(angle))
            lon_offset = offset_km / (111.0 * math.cos(math.radians(radar_lat))) * math.sin(math.radians(angle))

            core_lat = radar_lat + lat_offset
            core_lon = radar_lon + lon_offset

            mesh = random.uniform(0.75, 3.0)
            reflectivity = random.uniform(55, 70)

            cores.append(HailCore(
                radar_site=radar_id,
                timestamp=datetime.utcnow(),
                lat=core_lat,
                lon=core_lon,
                mesh_inches=round(mesh, 2),
                reflectivity_dbz=round(reflectivity, 1),
                distance_from_radar=offset_km,
                detection_confidence=1.0 / (1.0 + offset_km / 150.0)
            ))

        return cores

    def get_fused_hail_detections(
        self,
        lat: float,
        lon: float,
        download_new: bool = True,
        use_cache: bool = True
    ) -> List[FusedHailDetection]:
        """
        Get fused hail detections for a location.

        Args:
            lat: Latitude
            lon: Longitude
            download_new: Whether to download new data
            use_cache: Whether to use cached data

        Returns:
            List of FusedHailDetection objects
        """
        print(f"\n{'='*60}")
        print(f"REAL-TIME MULTI-RADAR FUSION")
        print(f"{'='*60}")
        print(f"  Location: ({lat:.4f}, {lon:.4f})")

        # Find covering radars
        print(f"\n[1/4] Finding covering radars...")
        radars = self.get_covering_radars(lat, lon)
        print(f"  Found {len(radars)} radars within range")

        if not radars:
            print("  ERROR: No radars cover this location")
            return []

        for r in radars[:5]:
            print(f"    {r['id']}: {r['distance_km']:.1f} km")

        radar_ids = [r['id'] for r in radars]

        # Download scans
        all_detections = []

        if download_new and NEXRADAWS_AVAILABLE:
            print(f"\n[2/4] Downloading recent scans...")
            downloads = self.download_recent_scans(radar_ids)

            for radar_id, files in downloads.items():
                print(f"    {radar_id}: {len(files)} files")

                radar_info = next((r for r in radars if r['id'] == radar_id), None)
                if not radar_info:
                    continue

                for scan_path in files:
                    cores = self.process_scan_for_hail(
                        scan_path,
                        radar_id,
                        radar_info['lat'],
                        radar_info['lon']
                    )
                    all_detections.extend(cores)
        else:
            print(f"\n[2/4] Generating synthetic detections (real download disabled)...")
            for radar_info in radars:
                cores = self._generate_synthetic_cores(
                    radar_info['id'],
                    radar_info['lat'],
                    radar_info['lon']
                )
                all_detections.extend(cores)
                if cores:
                    print(f"    {radar_info['id']}: {len(cores)} cores")

        print(f"\n[3/4] Total detections: {len(all_detections)}")

        if not all_detections:
            print("  No hail detected")
            return []

        # Fuse detections
        print(f"\n[4/4] Fusing multi-radar detections...")
        fused = self.fusion_engine.fuse_detections(all_detections, (lat, lon))

        print(f"\n{'='*60}")
        print(f"FUSION RESULTS")
        print(f"{'='*60}")
        print(f"  Fused detections: {len(fused)}")

        for det in fused[:5]:
            print(f"\n  [{det.detection_id}]")
            print(f"    Location: ({det.lat:.4f}, {det.lon:.4f})")
            print(f"    MESH: {det.mesh_inches}\" (range: {det.mesh_min}\"-{det.mesh_max}\")")
            print(f"    Confidence: {det.mesh_confidence:.1%}")
            print(f"    Quality: {det.fusion_quality}")
            print(f"    Radars: {', '.join(det.contributing_radars)}")
            print(f"    Agreement: {det.agreement_score:.1%}")

        return fused

    def monitor_location(
        self,
        lat: float,
        lon: float,
        duration_minutes: int = 60,
        interval_seconds: int = 300
    ):
        """
        Monitor a location for hail over time.

        Args:
            lat: Latitude
            lon: Longitude
            duration_minutes: How long to monitor
            interval_seconds: Update interval
        """
        import time

        print(f"\n{'='*60}")
        print(f"HAIL MONITORING: ({lat:.4f}, {lon:.4f})")
        print(f"Duration: {duration_minutes} minutes, Interval: {interval_seconds}s")
        print(f"{'='*60}")

        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=duration_minutes)

        iteration = 0
        max_mesh_seen = 0

        while datetime.utcnow() < end_time:
            iteration += 1
            print(f"\n--- Update {iteration} ({datetime.utcnow().strftime('%H:%M:%S UTC')}) ---")

            try:
                detections = self.get_fused_hail_detections(
                    lat, lon,
                    download_new=False,  # Set True for real monitoring
                    use_cache=True
                )

                for det in detections:
                    if det.mesh_inches > max_mesh_seen:
                        max_mesh_seen = det.mesh_inches
                        print(f"\n  *** NEW MAX: {max_mesh_seen}\" hail detected! ***")

            except Exception as e:
                logger.error(f"Monitoring error: {e}")

            if datetime.utcnow() < end_time:
                print(f"\n  Next update in {interval_seconds} seconds...")
                time.sleep(interval_seconds)

        print(f"\n{'='*60}")
        print(f"MONITORING COMPLETE")
        print(f"{'='*60}")
        print(f"  Max MESH observed: {max_mesh_seen}\"")


def test_fusion():
    """Test the real-time fusion system."""
    print("\n" + "=" * 60)
    print("TESTING REAL-TIME MULTI-RADAR FUSION")
    print("=" * 60)

    fusion = RealtimeMultiRadarFusion()

    # Test location: Oklahoma City
    test_lat = 35.4676
    test_lon = -97.5164

    print(f"\nTest location: Oklahoma City ({test_lat}, {test_lon})")

    # Get fused detections (synthetic mode)
    detections = fusion.get_fused_hail_detections(
        test_lat, test_lon,
        download_new=False  # Use synthetic for testing
    )

    print(f"\nTest complete. Found {len(detections)} fused detections.")

    return detections


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_fusion()
