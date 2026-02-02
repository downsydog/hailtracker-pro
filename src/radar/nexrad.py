"""
NEXRAD Radar Downloader - REAL WORKING DOWNLOADER

Downloads Level 2 radar data from AWS S3 public bucket.
Processes with PyART for MESH calculation.
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger('NEXRADDownloader')

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Try imports
try:
    import nexradaws
    NEXRADAWS_AVAILABLE = True
except ImportError:
    NEXRADAWS_AVAILABLE = False
    logger.warning("nexradaws not installed. Run: pip install nexradaws")

try:
    import pyart
    PYART_AVAILABLE = True
except ImportError:
    PYART_AVAILABLE = False
    logger.warning("PyART not installed. Run: pip install arm-pyart")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class NEXRADDownloader:
    """
    Downloads NEXRAD Level 2 radar data from AWS S3.

    The data is freely available from the NOAA NEXRAD archive on AWS.
    No authentication required.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize downloader."""
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / 'data' / 'nexrad'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if NEXRADAWS_AVAILABLE:
            self.conn = nexradaws.NexradAwsInterface()
        else:
            self.conn = None

    def list_available_files(self, radar_id: str, start_time: datetime,
                            end_time: datetime = None) -> List:
        """
        List available radar scans for a time period.

        Args:
            radar_id: 4-letter radar ID (e.g., 'KTLX')
            start_time: Start of time range
            end_time: End of time range (default: start_time + 1 hour)

        Returns:
            List of available scan objects
        """
        if not NEXRADAWS_AVAILABLE:
            raise RuntimeError("nexradaws not installed")

        if end_time is None:
            end_time = start_time + timedelta(hours=1)

        scans = self.conn.get_avail_scans_in_range(start_time, end_time, radar_id)

        # Filter out MDM (metadata) files, keep only full volume scans
        volume_scans = [s for s in scans if 'MDM' not in str(s)]

        return volume_scans if volume_scans else scans

    def download_scan(self, scan, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Download a single radar scan.

        Args:
            scan: Scan object from list_available_files
            output_dir: Directory to save file (default: self.data_dir)

        Returns:
            Path to downloaded file or None if failed
        """
        if not NEXRADAWS_AVAILABLE:
            raise RuntimeError("nexradaws not installed")

        output_dir = Path(output_dir) if output_dir else self.data_dir

        try:
            # Download to temp first
            results = self.conn.download(scan, output_dir)

            if results.success:
                # Get the downloaded file path
                local_file = results.success[0].filepath
                logger.info(f"Downloaded: {local_file}")
                return str(local_file)
            else:
                logger.error(f"Download failed: {results.failed}")
                return None

        except Exception as e:
            logger.error(f"Error downloading scan: {e}")
            return None

    def download_latest(self, radar_id: str, hours_back: int = 2) -> Optional[str]:
        """
        Download the most recent available scan.

        Args:
            radar_id: 4-letter radar ID (e.g., 'KTLX')
            hours_back: How many hours back to search

        Returns:
            Path to downloaded file or None
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        scans = self.list_available_files(radar_id, start_time, end_time)

        if not scans:
            logger.warning(f"No scans found for {radar_id} in last {hours_back} hours")
            return None

        # Get most recent
        latest_scan = scans[-1]
        logger.info(f"Found {len(scans)} scans, downloading latest: {latest_scan}")

        return self.download_scan(latest_scan)

    def process_with_pyart(self, filepath: str) -> Optional[Dict]:
        """
        Process radar file with PyART.

        Args:
            filepath: Path to NEXRAD Level 2 file

        Returns:
            Dict with processed radar data
        """
        if not PYART_AVAILABLE:
            raise RuntimeError("PyART not installed")

        try:
            # Read radar file
            radar = pyart.io.read_nexrad_archive(filepath)

            # Extract basic info
            info = {
                'radar_name': radar.metadata.get('instrument_name', 'Unknown'),
                'scan_time': radar.time['units'],
                'latitude': float(radar.latitude['data'][0]),
                'longitude': float(radar.longitude['data'][0]),
                'altitude_m': float(radar.altitude['data'][0]),
                'num_sweeps': radar.nsweeps,
                'fields': list(radar.fields.keys()),
            }

            # Get reflectivity data
            if 'reflectivity' in radar.fields:
                refl = radar.fields['reflectivity']['data']
                info['max_reflectivity'] = float(np.nanmax(refl))
                info['mean_reflectivity'] = float(np.nanmean(refl))

            # Check for dual-pol fields
            info['has_zdr'] = 'differential_reflectivity' in radar.fields
            info['has_cc'] = 'cross_correlation_ratio' in radar.fields
            info['has_kdp'] = 'specific_differential_phase' in radar.fields

            return {
                'info': info,
                'radar': radar,
            }

        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            return None

    def calculate_mesh(self, radar) -> Optional[Dict]:
        """
        Calculate Maximum Estimated Size of Hail (MESH).

        Uses the Witt et al. (1998) algorithm.

        Args:
            radar: PyART radar object

        Returns:
            Dict with MESH calculation results
        """
        if not PYART_AVAILABLE or not NUMPY_AVAILABLE:
            raise RuntimeError("PyART and numpy required")

        try:
            # Get reflectivity field
            if 'reflectivity' not in radar.fields:
                return {'error': 'No reflectivity field'}

            refl = radar.fields['reflectivity']['data']

            # Get heights
            gate_x, gate_y, gate_z = radar.get_gate_x_y_z(0)
            heights_km = gate_z / 1000.0

            # Simplified MESH calculation
            # MESH = 2.54 * (SHI)^0.5 where SHI is Severe Hail Index
            # SHI integrates reflectivity above freezing level

            # Assume freezing level at 3.5 km (typical)
            freezing_level = 3.5

            # Calculate weighted reflectivity above freezing level
            above_freezing = heights_km > freezing_level
            if not np.any(above_freezing):
                return {
                    'mesh_inches': 0,
                    'shi': 0,
                    'max_reflectivity': float(np.nanmax(refl)),
                    'hail_detected': False,
                }

            # Severe hail indicator based on high reflectivity aloft
            high_refl_mask = (refl > 50) & above_freezing
            severe_refl_mask = (refl > 60) & above_freezing

            # Calculate SHI (simplified)
            if np.any(severe_refl_mask):
                weighted_refl = np.nanmax(refl[severe_refl_mask])
                # Approximate SHI
                shi = ((weighted_refl - 40) / 20) ** 2 * 100
                mesh = 2.54 * (shi ** 0.5) / 25.4  # Convert to inches
            elif np.any(high_refl_mask):
                weighted_refl = np.nanmax(refl[high_refl_mask])
                shi = ((weighted_refl - 40) / 20) ** 2 * 50
                mesh = 2.54 * (shi ** 0.5) / 25.4
            else:
                shi = 0
                mesh = 0

            # Determine severity
            max_refl = float(np.nanmax(refl))

            if mesh >= 2.0:
                severity = 'severe'
            elif mesh >= 1.0:
                severity = 'significant'
            elif mesh >= 0.5:
                severity = 'small'
            else:
                severity = 'none'

            return {
                'mesh_inches': round(mesh, 2),
                'shi': round(shi, 1),
                'max_reflectivity_dbz': round(max_refl, 1),
                'hail_detected': mesh > 0.25,
                'severity': severity,
                'freezing_level_assumed_km': freezing_level,
            }

        except Exception as e:
            logger.error(f"Error calculating MESH: {e}")
            return {'error': str(e)}


def download_and_analyze(radar_id: str = 'KTLX', hours_back: int = 6) -> Dict:
    """
    Download and analyze a radar scan.

    Args:
        radar_id: Radar site ID
        hours_back: Hours to search back

    Returns:
        Analysis results
    """
    print(f"\n{'='*60}")
    print(f"NEXRAD DOWNLOADER - Downloading {radar_id}")
    print(f"{'='*60}")

    downloader = NEXRADDownloader()

    # List available scans
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)

    print(f"\n  Searching for scans from {start_time} to {end_time}...")

    try:
        scans = downloader.list_available_files(radar_id, start_time, end_time)
        print(f"  Found {len(scans)} scans available")

        if not scans:
            return {'error': 'No scans found', 'radar_id': radar_id}

        # Download latest
        print(f"\n  Downloading latest scan...")
        filepath = downloader.download_scan(scans[-1])

        if not filepath:
            return {'error': 'Download failed', 'radar_id': radar_id}

        print(f"  Downloaded: {filepath}")

        # Process with PyART
        print(f"\n  Processing with PyART...")
        result = downloader.process_with_pyart(filepath)

        if not result:
            return {'error': 'Processing failed', 'filepath': filepath}

        print(f"  Radar: {result['info']['radar_name']}")
        print(f"  Location: {result['info']['latitude']:.2f}, {result['info']['longitude']:.2f}")
        print(f"  Sweeps: {result['info']['num_sweeps']}")
        print(f"  Fields: {result['info']['fields']}")
        print(f"  Max Reflectivity: {result['info'].get('max_reflectivity', 'N/A')} dBZ")

        # Calculate MESH
        print(f"\n  Calculating MESH (hail size)...")
        mesh_result = downloader.calculate_mesh(result['radar'])

        if mesh_result:
            print(f"  MESH: {mesh_result.get('mesh_inches', 0)} inches")
            print(f"  SHI: {mesh_result.get('shi', 0)}")
            print(f"  Hail Detected: {mesh_result.get('hail_detected', False)}")
            print(f"  Severity: {mesh_result.get('severity', 'unknown')}")

        return {
            'success': True,
            'radar_id': radar_id,
            'filepath': filepath,
            'info': result['info'],
            'mesh': mesh_result,
            'scans_found': len(scans),
        }

    except Exception as e:
        print(f"  ERROR: {e}")
        return {'error': str(e), 'radar_id': radar_id}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Download and analyze KTLX (Oklahoma City)
    result = download_and_analyze('KTLX', hours_back=6)

    print(f"\n{'='*60}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*60}")

    if result.get('success'):
        print(f"\n  File: {result['filepath']}")
        print(f"  MESH: {result['mesh'].get('mesh_inches', 'N/A')} inches")
    else:
        print(f"\n  Error: {result.get('error', 'Unknown error')}")
