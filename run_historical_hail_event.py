"""
Run Complete System with REAL Historical Hail Event

Fetches actual radar data from a KNOWN hail event to demonstrate
the full HailTracker Pro pipeline with real storm signatures.

This uses a documented severe hail event from the AWS NEXRAD archive.
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
    print("  nexradaws: NOT FOUND")
    sys.exit(1)

try:
    import pyart
    print("  pyart: OK")
except ImportError:
    print("  pyart: NOT FOUND")
    sys.exit(1)

print()

# Local imports
from src.radar.composite_analyzer import CompositeAnalyzer, RadarDetection
from src.radar.cell_tracker import CellTracker
from src.ml.hail_classifier import HailClassifier


class HistoricalHailProcessor:
    """Process historical hail events with real NEXRAD data."""

    def __init__(self):
        self.conn = nexradaws.NexradAwsInterface()
        self.composite_analyzer = CompositeAnalyzer()
        self.cell_tracker = CellTracker()
        self.classifier = HailClassifier(simulation_mode=True)
        self.temp_dir = tempfile.mkdtemp()

    def fetch_radar(self, radar_id: str, scan_time: datetime) -> Optional[object]:
        """Fetch radar scan from AWS."""
        try:
            start_time = scan_time - timedelta(minutes=10)
            end_time = scan_time + timedelta(minutes=10)

            print(f"  Searching {radar_id}...")
            scans = self.conn.get_avail_scans_in_range(start_time, end_time, radar_id)

            if not scans:
                print(f"  No scans found")
                return None

            print(f"  Found {len(scans)} scans")

            # Get closest scan
            def time_diff(s):
                st = s.scan_time
                if st.tzinfo is not None:
                    st = st.replace(tzinfo=None)
                return abs((st - scan_time).total_seconds())

            closest = min(scans, key=time_diff)
            print(f"  Downloading {closest.filename}...")

            results = self.conn.download(closest, self.temp_dir)

            if results.success:
                filepath = results.success[0].filepath
                radar = pyart.io.read_nexrad_archive(filepath)
                print(f"  Loaded: {radar.nsweeps} sweeps")
                return radar

        except Exception as e:
            print(f"  Error: {e}")

        return None

    def analyze_storm_area(self, radar, search_radius_gates: int = 50) -> Dict:
        """
        Find and analyze the strongest storm in the radar scan.

        Returns the location and characteristics of max reflectivity.
        """
        try:
            # Get low-level reflectivity (sweep 0 or 1)
            for sweep_idx in [0, 1, 2]:
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        if data.count() > 0:
                            # Find max reflectivity location
                            max_val = np.max(data)
                            if max_val < 40:  # No significant echoes
                                continue

                            max_idx = np.unravel_index(np.argmax(data), data.shape)
                            az_idx, rng_idx = max_idx

                            # Get azimuth and range
                            sweep_slice = radar.get_slice(sweep_idx)
                            azimuths = radar.azimuth['data'][sweep_slice]
                            ranges = radar.range['data'] / 1000.0

                            az = azimuths[az_idx]
                            rng = ranges[rng_idx]

                            # Convert to lat/lon
                            radar_lat = radar.latitude['data'][0]
                            radar_lon = radar.longitude['data'][0]
                            storm_lat, storm_lon = self._az_range_to_latlon(
                                radar_lat, radar_lon, az, rng
                            )

                            # Extract area statistics
                            az_min = max(0, az_idx - search_radius_gates)
                            az_max = min(data.shape[0], az_idx + search_radius_gates)
                            rng_min = max(0, rng_idx - search_radius_gates)
                            rng_max = min(data.shape[1], rng_idx + search_radius_gates)

                            area_data = data[az_min:az_max, rng_min:rng_max]

                            result = {
                                'max_reflectivity': float(max_val),
                                'mean_reflectivity': float(np.mean(area_data[area_data > 30])) if np.sum(area_data > 30) > 0 else 0,
                                'storm_lat': storm_lat,
                                'storm_lon': storm_lon,
                                'azimuth': az,
                                'range_km': rng,
                                'sweep_idx': sweep_idx
                            }

                            # Get dual-pol if available
                            for zdr_field in ['differential_reflectivity', 'ZDR']:
                                if zdr_field in radar.fields:
                                    zdr_data = radar.get_field(sweep_idx, zdr_field)
                                    zdr_area = zdr_data[az_min:az_max, rng_min:rng_max]
                                    if zdr_area.count() > 0:
                                        result['zdr'] = float(np.mean(zdr_area))
                                        result['zdr_min'] = float(np.min(zdr_area))
                                    break

                            for cc_field in ['cross_correlation_ratio', 'RHOHV', 'CC']:
                                if cc_field in radar.fields:
                                    cc_data = radar.get_field(sweep_idx, cc_field)
                                    cc_area = cc_data[az_min:az_max, rng_min:rng_max]
                                    if cc_area.count() > 0:
                                        result['cc'] = float(np.mean(cc_area))
                                        result['cc_min'] = float(np.min(cc_area))
                                    break

                            return result

            return {'max_reflectivity': 0, 'error': 'No significant echoes found'}

        except Exception as e:
            return {'max_reflectivity': 0, 'error': str(e)}

    def calculate_mesh(self, radar) -> Dict:
        """Calculate MESH from vertical profile."""
        try:
            max_refs = []
            heights = []

            for sweep_idx in range(min(radar.nsweeps, 14)):
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        if data.count() > 0:
                            max_ref = float(np.max(data))
                            sweep_slice = radar.get_slice(sweep_idx)
                            elev = np.mean(radar.elevation['data'][sweep_slice])
                            # Estimate height at 50km range
                            height = 50 * np.tan(np.radians(elev)) + (50**2) / (2 * 8500)
                            max_refs.append(max_ref)
                            heights.append(height)
                        break

            if not max_refs:
                return {'mesh_mm': 0, 'shi': 0, 'posh': 0}

            overall_max = max(max_refs)
            freezing_level = 3.5

            # Find max above freezing level
            above_freezing = [(h, r) for h, r in zip(heights, max_refs) if h > freezing_level]

            if above_freezing:
                max_above = max(r for h, r in above_freezing)
                if max_above >= 40:
                    mesh_mm = 2.54 * np.exp(0.1 * (max_above - 40))
                    mesh_mm = min(mesh_mm, 120)
                else:
                    mesh_mm = 0
            else:
                mesh_mm = 0

            shi = mesh_mm * 4 if mesh_mm > 0 else 0
            posh = min(99, 50 + mesh_mm) if mesh_mm >= 25 else (30 + mesh_mm if mesh_mm >= 10 else mesh_mm * 2)

            return {
                'mesh_mm': round(mesh_mm, 1),
                'shi': round(shi, 0),
                'posh': round(posh, 0),
                'max_reflectivity': round(overall_max, 1)
            }

        except Exception as e:
            return {'mesh_mm': 0, 'shi': 0, 'posh': 0, 'error': str(e)}

    def _az_range_to_latlon(self, radar_lat, radar_lon, azimuth, range_km):
        """Convert radar azimuth/range to lat/lon."""
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


def main():
    print("\n" + "=" * 70)
    print("HAILTRACKER PRO - HISTORICAL HAIL EVENT ANALYSIS")
    print("=" * 70 + "\n")

    processor = HistoricalHailProcessor()

    # Known severe weather events with hail
    # These are actual dates with documented severe weather
    historical_events = [
        # Recent events (more likely to have data available)
        {
            "name": "Texas Panhandle Storm",
            "date": datetime(2024, 5, 28, 22, 30),  # May 2024 TX outbreak
            "radar": "KAMA",
            "description": "Spring severe weather outbreak"
        },
        {
            "name": "Oklahoma Supercell",
            "date": datetime(2024, 5, 6, 23, 0),  # May 2024 OK storms
            "radar": "KTLX",
            "description": "Supercell with large hail"
        },
        {
            "name": "North Texas Storm",
            "date": datetime(2024, 4, 26, 21, 0),  # April 2024 DFW event
            "radar": "KFWS",
            "description": "DFW metro hail event"
        },
        {
            "name": "Kansas Supercell",
            "date": datetime(2024, 5, 21, 0, 30),  # May 2024 KS severe
            "radar": "KICT",
            "description": "Central Plains outbreak"
        },
    ]

    for event in historical_events:
        print(f"\n{'='*70}")
        print(f"EVENT: {event['name']}")
        print(f"Date: {event['date']}")
        print(f"Radar: {event['radar']}")
        print(f"Description: {event['description']}")
        print(f"{'='*70}\n")

        # Fetch radar data
        radar = processor.fetch_radar(event['radar'], event['date'])

        if radar is None:
            print("  No data available for this event")
            continue

        # Find and analyze strongest storm
        print("\nAnalyzing storm...")
        storm = processor.analyze_storm_area(radar)

        if storm.get('max_reflectivity', 0) < 40:
            print(f"  No significant storm found (max refl: {storm.get('max_reflectivity', 0)} dBZ)")
            continue

        print(f"\nSTORM FOUND:")
        print(f"  Location: ({storm.get('storm_lat', 0):.4f}, {storm.get('storm_lon', 0):.4f})")
        print(f"  Max Reflectivity: {storm['max_reflectivity']:.1f} dBZ")
        print(f"  Mean Reflectivity: {storm.get('mean_reflectivity', 0):.1f} dBZ")
        if 'zdr' in storm:
            print(f"  ZDR: {storm['zdr']:.2f} dB (min: {storm.get('zdr_min', 0):.2f})")
        if 'cc' in storm:
            print(f"  CC: {storm['cc']:.3f} (min: {storm.get('cc_min', 0):.3f})")

        # Calculate MESH
        print("\nCalculating MESH from vertical profile...")
        mesh_result = processor.calculate_mesh(radar)

        print(f"  MESH: {mesh_result['mesh_mm']:.1f} mm ({mesh_result['mesh_mm']/25.4:.2f}\")")
        print(f"  SHI: {mesh_result['shi']:.0f}")
        print(f"  POSH: {mesh_result['posh']:.0f}%")

        # ML Classification
        print("\nRunning ML Classification...")

        hail_event = processor.classifier.classify(
            lat=storm.get('storm_lat', 35.0),
            lon=storm.get('storm_lon', -97.0),
            timestamp=event['date'],
            radar_data={
                'max_reflectivity': storm['max_reflectivity'],
                'mesh': mesh_result['mesh_mm'],
                'posh': mesh_result['posh'],
                'zdr_min': storm.get('zdr_min', storm.get('zdr', 0.5)),
                'cc_min': storm.get('cc_min', storm.get('cc', 0.95)),
                'vil': mesh_result['shi'] / 4 if mesh_result['shi'] else 20
            },
            environmental_data={
                'freezing_level': 3.5,
                'cape': 2500,  # Assume high CAPE for severe event
                'shear_0_6km': 30,
                'srh': 250
            },
            multi_radar_data={
                'num_radars': 1,
                'agreement': 100
            }
        )

        print(f"\n{'='*70}")
        print("ML CLASSIFICATION RESULTS")
        print(f"{'='*70}")
        print(f"  Hail Detected: {'YES' if hail_event.hail_detected else 'NO'}")
        print(f"  Probability: {hail_event.hail_probability:.1f}%")
        print(f"  Estimated Size: {hail_event.estimated_size_mm:.1f} mm ({hail_event.estimated_size_mm/25.4:.2f}\")")
        print(f"  Severity: {hail_event.severity.upper()}")
        print(f"  Confidence: {hail_event.confidence:.1f}%")

        print(f"\nPDR BUSINESS ANALYSIS:")
        print(f"  Opportunity Score: {hail_event.pdr_opportunity_score:.1f}/100")

        if hail_event.pdr_opportunity_score >= 70:
            print(f"  Recommendation: HIGH PRIORITY - Deploy PDR team immediately")
            print(f"  Expected damage: Significant dents, $500-1500/vehicle")
        elif hail_event.pdr_opportunity_score >= 40:
            print(f"  Recommendation: MONITOR - Good PDR opportunity")
            print(f"  Expected damage: Moderate dents, $300-800/vehicle")
        else:
            print(f"  Recommendation: LOW PRIORITY")

        # Success! Found a storm
        print(f"\n{'='*70}")
        print("ANALYSIS COMPLETE - Real NEXRAD data processed successfully!")
        print(f"{'='*70}")
        break

    else:
        print("\nNo historical events with available data found.")
        print("The AWS NEXRAD archive may have gaps for these dates.")


if __name__ == '__main__':
    main()
