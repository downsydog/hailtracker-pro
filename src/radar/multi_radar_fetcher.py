"""
Multi-Radar Data Fetcher
Fetch data from multiple radars simultaneously for composite analysis

WHY MULTI-RADAR?
================
- Fill coverage gaps beyond single radar range
- View storms from multiple angles
- Cross-validate detections
- Better accuracy at all ranges (80% vs 75%)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from .radar_network import RadarNetwork, RadarSite

# Check for optional dependencies
try:
    import nexradaws
    NEXRADAWS_AVAILABLE = True
except ImportError:
    NEXRADAWS_AVAILABLE = False

try:
    import pyart
    PYART_AVAILABLE = True
except ImportError:
    PYART_AVAILABLE = False


@dataclass
class RadarScan:
    """Data from a single radar scan"""
    site: RadarSite
    radar: object  # PyART radar object
    scan_time: datetime
    distance_km: float
    quality: str
    coverage_fraction: float = 1.0
    score: float = 0.0


class MultiRadarFetcher:
    """
    Fetch radar data from multiple sites simultaneously

    Uses AWS NEXRAD archive for historical data or real-time feeds
    """

    def __init__(self):
        """Initialize multi-radar fetcher"""
        self.network = RadarNetwork()
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required libraries are available"""
        self.live_mode = NEXRADAWS_AVAILABLE and PYART_AVAILABLE
        if not self.live_mode:
            print("Note: Running in simulation mode (nexradaws/pyart not available)")

    def fetch_multi_radar(
        self,
        latitude: float,
        longitude: float,
        scan_time: datetime,
        num_radars: int = 3,
        time_window_minutes: int = 10
    ) -> List[Dict]:
        """
        Fetch radar data from multiple sites covering a location

        Args:
            latitude: Target latitude
            longitude: Target longitude
            scan_time: Desired scan time
            num_radars: Number of radars to use (default: 3)
            time_window_minutes: Time window for scan search

        Returns:
            List of dicts with radar data: {
                'site': RadarSite,
                'radar': PyART radar object (or None in simulation),
                'distance_km': float,
                'quality': str,
                'scan_time': datetime
            }

        Example:
            >>> fetcher = MultiRadarFetcher()
            >>> radars = fetcher.fetch_multi_radar(
            ...     32.7767, -96.7970,  # Dallas
            ...     datetime(2024, 11, 15, 14, 30),
            ...     num_radars=3
            ... )
            >>> print(f"Fetched data from {len(radars)} radars")
        """

        print(f"\nFinding radars covering {latitude:.4f}, {longitude:.4f}")

        # Find covering radars
        covering_radars = self.network.find_covering_radars(
            latitude, longitude,
            max_radars=num_radars
        )

        if not covering_radars:
            print("No radars found covering this location")
            return []

        print(f"Found {len(covering_radars)} radars:")
        for radar_info in covering_radars:
            site = radar_info['site']
            distance = radar_info['distance_km']
            quality = radar_info['quality']
            print(f"   {site.name} ({site.id}): {distance:.1f} km - {quality}")

        print()

        # Fetch from each radar
        results = []

        for radar_info in covering_radars:
            site = radar_info['site']

            print(f"Fetching {site.name} ({site.id})...")

            if self.live_mode:
                radar_obj = self._fetch_radar_live(
                    site.id,
                    scan_time,
                    time_window_minutes
                )
            else:
                radar_obj = self._simulate_radar(site, scan_time)

            if radar_obj is not None:
                results.append({
                    'site': site,
                    'radar': radar_obj,
                    'distance_km': radar_info['distance_km'],
                    'quality': radar_info['quality'],
                    'scan_time': scan_time
                })
                print(f"   Success")
            else:
                print(f"   No data available")

            print()

        print(f"Successfully fetched {len(results)}/{len(covering_radars)} radars")
        print()

        return results

    def fetch_for_event_area(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        scan_time: datetime,
        num_radars: int = 3
    ) -> List[Dict]:
        """
        Fetch radars optimized for covering entire event area

        Args:
            center_lat: Event center latitude
            center_lon: Event center longitude
            radius_km: Event radius
            scan_time: Scan time
            num_radars: Target number of radars

        Returns:
            List of radar data dicts with coverage scoring
        """

        print(f"\nFinding radars for event area")
        print(f"   Center: {center_lat:.4f}, {center_lon:.4f}")
        print(f"   Radius: {radius_km} km")

        # Find best radars for event
        best_radars = self.network.find_best_radars_for_event(
            center_lat, center_lon,
            radius_km,
            num_radars
        )

        if not best_radars:
            print("No radars found")
            return []

        print(f"\nSelected {len(best_radars)} radars:")
        for radar_info in best_radars:
            site = radar_info['site']
            print(f"   {site.name} ({site.id})")
            print(f"     Distance: {radar_info['distance_km']:.1f} km")
            print(f"     Coverage: {radar_info['coverage_fraction']*100:.0f}%")
            print(f"     Score: {radar_info['score']:.1f}")

        print()

        # Fetch from each
        results = []

        for radar_info in best_radars:
            site = radar_info['site']

            print(f"Fetching {site.name}...")

            if self.live_mode:
                radar_obj = self._fetch_radar_live(site.id, scan_time)
            else:
                radar_obj = self._simulate_radar(site, scan_time)

            if radar_obj is not None:
                results.append({
                    'site': site,
                    'radar': radar_obj,
                    'distance_km': radar_info['distance_km'],
                    'coverage_fraction': radar_info['coverage_fraction'],
                    'score': radar_info['score'],
                    'scan_time': scan_time
                })
                print(f"   Success")
            else:
                print(f"   No data")

            print()

        return results

    def _fetch_radar_live(
        self,
        site_id: str,
        scan_time: datetime,
        time_window_minutes: int = 10
    ) -> Optional[object]:
        """
        Fetch radar data from AWS NEXRAD archive

        Args:
            site_id: Radar site ID (e.g., 'KFWS')
            scan_time: Target scan time
            time_window_minutes: Search window

        Returns:
            PyART radar object or None
        """
        if not self.live_mode:
            return None

        try:
            conn = nexradaws.NexradAwsInterface()

            # Search for scans in time window
            start_time = scan_time - timedelta(minutes=time_window_minutes)
            end_time = scan_time + timedelta(minutes=time_window_minutes)

            scans = conn.get_avail_scans_in_range(
                start_time, end_time, site_id
            )

            if not scans:
                return None

            # Get closest scan to target time
            closest = min(scans, key=lambda s: abs(
                (s.scan_time - scan_time).total_seconds()
            ))

            # Download
            results = conn.download(closest, '/tmp')

            if results.success:
                # Read with PyART
                radar = pyart.io.read_nexrad_archive(
                    results.success[0].filepath
                )
                return radar

        except Exception as e:
            print(f"   Error: {e}")

        return None

    def _simulate_radar(
        self,
        site: RadarSite,
        scan_time: datetime
    ) -> Dict:
        """
        Create simulated radar data for testing

        Returns a dict simulating radar properties instead of PyART object
        """
        return {
            'site_id': site.id,
            'site_name': site.name,
            'scan_time': scan_time.isoformat(),
            'nsweeps': 14,  # Typical VCP 212
            'fields': ['reflectivity', 'differential_reflectivity',
                      'cross_correlation_ratio', 'specific_differential_phase'],
            'latitude': site.lat,
            'longitude': site.lon,
            'simulated': True
        }

    def get_combined_coverage(
        self,
        radar_results: List[Dict],
        target_lat: float,
        target_lon: float
    ) -> Dict:
        """
        Analyze combined coverage from multiple radars

        Args:
            radar_results: List of fetch results
            target_lat: Target location latitude
            target_lon: Target location longitude

        Returns:
            Dict with coverage analysis
        """
        if not radar_results:
            return {
                'num_radars': 0,
                'coverage_quality': 'None',
                'best_radar': None,
                'lowest_beam_height': None
            }

        # Find best radar (closest)
        best = min(radar_results, key=lambda r: r['distance_km'])

        # Calculate lowest beam height (from closest radar)
        beam_height = self.network._calculate_beam_height(
            best['distance_km'], 0.5  # 0.5 degree elevation
        )

        # Determine overall quality
        qualities = [r['quality'] for r in radar_results]
        if 'Excellent' in qualities:
            overall = 'Excellent'
        elif 'Good' in qualities:
            overall = 'Good'
        elif 'Fair' in qualities:
            overall = 'Fair'
        else:
            overall = 'Poor'

        return {
            'num_radars': len(radar_results),
            'coverage_quality': overall,
            'best_radar': best['site'].id,
            'best_distance_km': best['distance_km'],
            'lowest_beam_height_m': beam_height,
            'radars': [r['site'].id for r in radar_results]
        }


if __name__ == '__main__':
    # Quick test
    print("Multi-Radar Fetcher Test")
    print("=" * 40)

    fetcher = MultiRadarFetcher()

    # Test finding radars for Dallas
    results = fetcher.fetch_multi_radar(
        32.7767, -96.7970,
        datetime.now(),
        num_radars=3
    )

    if results:
        coverage = fetcher.get_combined_coverage(results, 32.7767, -96.7970)
        print(f"\nCombined coverage:")
        print(f"  Radars: {coverage['num_radars']}")
        print(f"  Quality: {coverage['coverage_quality']}")
        print(f"  Best radar: {coverage['best_radar']}")
