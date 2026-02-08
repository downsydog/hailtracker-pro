"""
Run Complete System with REAL NEXRAD Radar Data

Fetches actual radar data from AWS NEXRAD archive and processes
through the complete HailTracker Pro pipeline.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np

# Check dependencies
print("Checking dependencies...")

try:
    import nexradaws
    print("  nexradaws: OK")
except ImportError:
    print("  nexradaws: NOT FOUND - Installing...")
    os.system("pip install nexradaws")
    import nexradaws

try:
    import pyart
    print("  pyart: OK")
except ImportError:
    print("  pyart: NOT FOUND - Installing...")
    os.system("pip install arm-pyart")
    import pyart

try:
    from sklearn.ensemble import RandomForestClassifier
    print("  scikit-learn: OK")
except ImportError:
    print("  scikit-learn: NOT FOUND - Installing...")
    os.system("pip install scikit-learn")

print()

# Local imports
from src.radar.radar_network import RadarNetwork
from src.radar.composite_analyzer import CompositeAnalyzer, RadarDetection
from src.radar.cell_tracker import CellTracker
from src.radar.cell_identifier import StormCell
from src.ml.hail_classifier import HailClassifier, HailEvent
from src.ml.hail_ml_model import HailMLModel, HailFeatures


class RealNEXRADProcessor:
    """
    Process real NEXRAD radar data through the complete pipeline.
    """

    def __init__(self):
        self.conn = nexradaws.NexradAwsInterface()
        self.network = RadarNetwork()
        self.composite_analyzer = CompositeAnalyzer()
        self.cell_tracker = CellTracker()
        self.classifier = HailClassifier(simulation_mode=True)
        self.temp_dir = tempfile.mkdtemp()

    def find_recent_storms(self, hours_back: int = 24) -> List[Dict]:
        """
        Find recent radar scans that might contain storms.

        Returns list of potential events to analyze.
        """
        # Common severe weather locations
        locations = [
            {"name": "Dallas, TX", "lat": 32.7767, "lon": -96.7970, "radar": "KFWS"},
            {"name": "Oklahoma City, OK", "lat": 35.4676, "lon": -97.5164, "radar": "KTLX"},
            {"name": "Tulsa, OK", "lat": 36.1540, "lon": -95.9928, "radar": "KINX"},
            {"name": "Wichita, KS", "lat": 37.6872, "lon": -97.3301, "radar": "KICT"},
            {"name": "Amarillo, TX", "lat": 35.2220, "lon": -101.8313, "radar": "KAMA"},
        ]
        return locations

    def fetch_radar_scan(
        self,
        radar_id: str,
        scan_time: datetime,
        time_window_minutes: int = 15
    ) -> Optional[object]:
        """
        Fetch a radar scan from AWS NEXRAD archive.

        Args:
            radar_id: Radar site ID (e.g., 'KFWS')
            scan_time: Target time
            time_window_minutes: Search window

        Returns:
            PyART radar object or None
        """
        try:
            start_time = scan_time - timedelta(minutes=time_window_minutes)
            end_time = scan_time + timedelta(minutes=time_window_minutes)

            print(f"  Searching {radar_id} from {start_time} to {end_time}...")

            scans = self.conn.get_avail_scans_in_range(start_time, end_time, radar_id)

            if not scans:
                print(f"  No scans found for {radar_id}")
                return None

            print(f"  Found {len(scans)} scans")

            # Get closest to target time (handle timezone-aware vs naive)
            def time_diff(s):
                st = s.scan_time
                # Make scan_time timezone-naive for comparison
                if st.tzinfo is not None:
                    st = st.replace(tzinfo=None)
                return abs((st - scan_time).total_seconds())

            closest = min(scans, key=time_diff)

            print(f"  Downloading {closest.filename}...")

            # Download
            results = self.conn.download(closest, self.temp_dir)

            if results.success:
                filepath = results.success[0].filepath
                print(f"  Reading radar file...")
                radar = pyart.io.read_nexrad_archive(filepath)
                print(f"  Loaded: {radar.nsweeps} sweeps, {list(radar.fields.keys())}")
                return radar
            else:
                print(f"  Download failed")
                return None

        except Exception as e:
            print(f"  Error fetching {radar_id}: {e}")
            return None

    def extract_dualpol_values(
        self,
        radar,
        target_lat: float,
        target_lon: float,
        sweep_idx: int = 0
    ) -> Dict:
        """
        Extract dual-pol values at a target location from radar data.

        Args:
            radar: PyART radar object
            target_lat: Target latitude
            target_lon: Target longitude
            sweep_idx: Sweep index to use

        Returns:
            Dict with reflectivity, zdr, cc, kdp values
        """
        try:
            # Get radar location
            radar_lat = radar.latitude['data'][0]
            radar_lon = radar.longitude['data'][0]

            # Calculate azimuth and range to target
            az, rng = self._calculate_az_range(
                radar_lat, radar_lon, target_lat, target_lon
            )

            print(f"  Target at azimuth={az:.1f}deg, range={rng:.1f}km from radar")

            # Get sweep data
            sweep_slice = radar.get_slice(sweep_idx)
            azimuths = radar.azimuth['data'][sweep_slice]
            ranges = radar.range['data'] / 1000.0  # km

            # Find closest azimuth
            az_idx = np.argmin(np.abs(azimuths - az))

            # Find closest range
            rng_idx = np.argmin(np.abs(ranges - rng))

            # Extract values
            values = {}

            # Reflectivity
            for field_name in ['reflectivity', 'REF', 'DBZ']:
                if field_name in radar.fields:
                    data = radar.get_field(sweep_idx, field_name)
                    val = data[az_idx, rng_idx]
                    if not np.ma.is_masked(val):
                        values['reflectivity'] = float(val)
                    break

            # Get max reflectivity in area (5x5 gate box)
            if 'reflectivity' not in values:
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        # Get area around target
                        az_min, az_max = max(0, az_idx-5), min(data.shape[0], az_idx+5)
                        rng_min, rng_max = max(0, rng_idx-5), min(data.shape[1], rng_idx+5)
                        area_data = data[az_min:az_max, rng_min:rng_max]
                        if area_data.count() > 0:
                            values['reflectivity'] = float(np.max(area_data))
                            values['mean_reflectivity'] = float(np.mean(area_data[area_data > 20]))
                        break

            # ZDR
            for field_name in ['differential_reflectivity', 'ZDR']:
                if field_name in radar.fields:
                    data = radar.get_field(sweep_idx, field_name)
                    az_min, az_max = max(0, az_idx-5), min(data.shape[0], az_idx+5)
                    rng_min, rng_max = max(0, rng_idx-5), min(data.shape[1], rng_idx+5)
                    area_data = data[az_min:az_max, rng_min:rng_max]
                    if area_data.count() > 0:
                        values['zdr'] = float(np.mean(area_data))
                        values['zdr_min'] = float(np.min(area_data))
                    break

            # CC (Correlation Coefficient)
            for field_name in ['cross_correlation_ratio', 'RHOHV', 'CC']:
                if field_name in radar.fields:
                    data = radar.get_field(sweep_idx, field_name)
                    az_min, az_max = max(0, az_idx-5), min(data.shape[0], az_idx+5)
                    rng_min, rng_max = max(0, rng_idx-5), min(data.shape[1], rng_idx+5)
                    area_data = data[az_min:az_max, rng_min:rng_max]
                    if area_data.count() > 0:
                        values['cc'] = float(np.mean(area_data))
                        values['cc_min'] = float(np.min(area_data))
                    break

            # KDP
            for field_name in ['specific_differential_phase', 'KDP']:
                if field_name in radar.fields:
                    data = radar.get_field(sweep_idx, field_name)
                    az_min, az_max = max(0, az_idx-5), min(data.shape[0], az_idx+5)
                    rng_min, rng_max = max(0, rng_idx-5), min(data.shape[1], rng_idx+5)
                    area_data = data[az_min:az_max, rng_min:rng_max]
                    if area_data.count() > 0:
                        values['kdp'] = float(np.max(area_data))
                    break

            return values

        except Exception as e:
            print(f"  Error extracting dual-pol: {e}")
            return {}

    def _calculate_az_range(
        self,
        radar_lat: float,
        radar_lon: float,
        target_lat: float,
        target_lon: float
    ) -> Tuple[float, float]:
        """Calculate azimuth and range from radar to target."""
        import math

        # Haversine for distance
        R = 6371.0  # km
        lat1 = math.radians(radar_lat)
        lat2 = math.radians(target_lat)
        dlat = math.radians(target_lat - radar_lat)
        dlon = math.radians(target_lon - radar_lon)

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance_km = R * c

        # Bearing
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        azimuth = math.degrees(math.atan2(y, x))
        azimuth = (azimuth + 360) % 360

        return azimuth, distance_km

    def calculate_mesh_from_radar(self, radar, sweep_indices: List[int] = None) -> Dict:
        """
        Calculate MESH from vertical profile of radar data.

        Args:
            radar: PyART radar object
            sweep_indices: Which sweeps to use

        Returns:
            Dict with mesh_mm, shi, posh
        """
        if sweep_indices is None:
            sweep_indices = list(range(min(radar.nsweeps, 10)))

        try:
            # Get reflectivity from multiple elevations
            heights = []
            reflectivities = []

            for sweep_idx in sweep_indices:
                # Get elevation
                sweep_slice = radar.get_slice(sweep_idx)
                elevation = np.mean(radar.elevation['data'][sweep_slice])

                # Get max reflectivity in sweep
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        if data.count() > 0:
                            max_ref = float(np.max(data))
                            # Estimate height (simplified)
                            # Assume avg range of 50km, using 4/3 earth model
                            height_km = 50 * np.tan(np.radians(elevation)) + (50**2) / (2 * 8500)
                            heights.append(height_km)
                            reflectivities.append(max_ref)
                        break

            if not heights:
                return {'mesh_mm': 0, 'shi': 0, 'posh': 0}

            # Simplified MESH calculation
            max_ref = max(reflectivities)
            freezing_level = 3.5  # km, typical

            # MESH approximation based on max reflectivity above freezing level
            above_freezing = [(h, r) for h, r in zip(heights, reflectivities) if h > freezing_level]

            if above_freezing:
                max_ref_above = max(r for h, r in above_freezing)
                # MESH formula approximation
                if max_ref_above >= 40:
                    mesh_mm = 2.54 * np.exp(0.1 * (max_ref_above - 40))
                    mesh_mm = min(mesh_mm, 120)  # Cap at 120mm
                else:
                    mesh_mm = 0
            else:
                mesh_mm = 0

            # SHI approximation
            shi = mesh_mm * 4 if mesh_mm > 0 else 0

            # POSH approximation
            if mesh_mm >= 25:
                posh = min(99, 50 + mesh_mm)
            elif mesh_mm >= 10:
                posh = 30 + mesh_mm
            else:
                posh = mesh_mm * 2

            return {
                'mesh_mm': round(mesh_mm, 1),
                'shi': round(shi, 0),
                'posh': round(posh, 0),
                'max_reflectivity': round(max_ref, 1),
                'heights_analyzed': len(heights)
            }

        except Exception as e:
            print(f"  Error calculating MESH: {e}")
            return {'mesh_mm': 0, 'shi': 0, 'posh': 0}

    def process_event(
        self,
        location: Dict,
        scan_time: datetime
    ) -> Optional[HailEvent]:
        """
        Process a complete hail detection event with real data.

        Args:
            location: Dict with name, lat, lon, radar
            scan_time: Event time

        Returns:
            HailEvent with complete analysis
        """
        print(f"\n{'='*70}")
        print(f"PROCESSING: {location['name']}")
        print(f"Time: {scan_time}")
        print(f"Radar: {location['radar']}")
        print(f"{'='*70}\n")

        # Fetch radar data
        radar = self.fetch_radar_scan(location['radar'], scan_time)

        if radar is None:
            print("  No radar data available")
            return None

        # Extract dual-pol values
        print(f"\nExtracting dual-pol values...")
        dualpol = self.extract_dualpol_values(
            radar, location['lat'], location['lon']
        )

        if not dualpol:
            print("  Could not extract dual-pol values")
            return None

        print(f"  Reflectivity: {dualpol.get('reflectivity', 'N/A')} dBZ")
        print(f"  ZDR: {dualpol.get('zdr', 'N/A')} dB")
        print(f"  CC: {dualpol.get('cc', 'N/A')}")
        print(f"  KDP: {dualpol.get('kdp', 'N/A')} deg/km")

        # Calculate MESH
        print(f"\nCalculating MESH...")
        mesh_result = self.calculate_mesh_from_radar(radar)

        print(f"  Max Reflectivity: {mesh_result.get('max_reflectivity', 'N/A')} dBZ")
        print(f"  MESH: {mesh_result['mesh_mm']} mm ({mesh_result['mesh_mm']/25.4:.2f}\")")
        print(f"  SHI: {mesh_result['shi']}")
        print(f"  POSH: {mesh_result['posh']}%")

        # Run ML classification
        print(f"\nRunning ML classification...")

        event = self.classifier.classify(
            lat=location['lat'],
            lon=location['lon'],
            timestamp=scan_time,
            radar_data={
                'max_reflectivity': dualpol.get('reflectivity', mesh_result.get('max_reflectivity', 45)),
                'mesh': mesh_result['mesh_mm'],
                'posh': mesh_result['posh'],
                'zdr_min': dualpol.get('zdr_min', dualpol.get('zdr', 0.5)),
                'cc_min': dualpol.get('cc_min', dualpol.get('cc', 0.95)),
                'vil': mesh_result['shi'] / 4 if mesh_result['shi'] else 20
            },
            environmental_data={
                'freezing_level': 3.5,
                'cape': 1800,
                'shear_0_6km': 25,
                'srh': 180
            },
            multi_radar_data={
                'num_radars': 1,
                'agreement': 100
            }
        )

        # Print results
        print(f"\n{'='*70}")
        print("ML CLASSIFICATION RESULTS")
        print(f"{'='*70}")
        print(f"  Hail Detected: {event.hail_detected}")
        print(f"  Probability: {event.hail_probability:.1f}%")
        print(f"  Estimated Size: {event.estimated_size_mm:.1f} mm ({event.estimated_size_mm/25.4:.2f}\")")
        print(f"  Severity: {event.severity.upper()}")
        print(f"  Confidence: {event.confidence:.1f}%")
        print(f"  PDR Score: {event.pdr_opportunity_score:.1f}/100")

        return event


def main():
    print("\n" + "=" * 70)
    print("HAILTRACKER PRO - REAL NEXRAD DATA PROCESSING")
    print("=" * 70 + "\n")

    processor = RealNEXRADProcessor()

    # Use a recent time (within last few hours for best data availability)
    # For demo, we'll try multiple time windows
    now = datetime.utcnow()

    # Try different time windows
    time_windows = [
        now - timedelta(hours=1),
        now - timedelta(hours=3),
        now - timedelta(hours=6),
        now - timedelta(hours=12),
    ]

    # Try Dallas/Fort Worth radar first (usually has good data)
    locations = [
        {"name": "Dallas-Fort Worth, TX", "lat": 32.7767, "lon": -96.7970, "radar": "KFWS"},
        {"name": "Oklahoma City, OK", "lat": 35.4676, "lon": -97.5164, "radar": "KTLX"},
    ]

    success = False

    for location in locations:
        for scan_time in time_windows:
            print(f"\nTrying {location['name']} at {scan_time}...")

            try:
                event = processor.process_event(location, scan_time)

                if event:
                    success = True
                    print(f"\n{'='*70}")
                    print("COMPLETE EVENT SUMMARY")
                    print(f"{'='*70}")
                    print(f"Location: {location['name']}")
                    print(f"Time: {scan_time}")
                    print(f"Radar: {location['radar']}")
                    print()
                    print(f"HAIL ANALYSIS:")
                    print(f"  Detected: {'YES' if event.hail_detected else 'NO'}")
                    print(f"  Probability: {event.hail_probability:.1f}%")
                    print(f"  Size: {event.estimated_size_mm:.1f} mm")
                    print(f"  Severity: {event.severity}")
                    print()
                    print(f"PDR BUSINESS VALUE:")
                    print(f"  Opportunity Score: {event.pdr_opportunity_score:.1f}/100")

                    if event.pdr_opportunity_score >= 70:
                        print(f"  Recommendation: HIGH PRIORITY - Deploy PDR team")
                    elif event.pdr_opportunity_score >= 40:
                        print(f"  Recommendation: MONITOR - Potential opportunity")
                    else:
                        print(f"  Recommendation: LOW - Minor or no damage expected")

                    break

            except Exception as e:
                print(f"  Error: {e}")
                continue

        if success:
            break

    if not success:
        print("\nNo radar data found in recent time windows.")
        print("This could mean:")
        print("  1. AWS NEXRAD archive has lag (usually 15-30 min)")
        print("  2. Network connectivity issues")
        print("  3. Selected radars are temporarily offline")
        print()
        print("Try running again in a few minutes, or specify a historical event date.")

    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
