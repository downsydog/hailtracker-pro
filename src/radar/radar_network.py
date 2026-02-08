"""
NEXRAD Radar Network Manager
Manages multiple radars for composite analysis

WHY MULTI-RADAR?
================

Single radar problems:
- Coverage gaps beyond 100km
- Beam blockage from terrain/buildings
- Beam too high at long range
- Can't verify detections

Multi-radar solution:
- Fill coverage gaps
- View storm from multiple angles
- Cross-validate detections
- Better accuracy at all ranges

EXAMPLE:
Dallas is covered by:
- KFWS (Fort Worth) - 30 miles west
- KDFW (Dallas/Fort Worth) - direct
- KTLX (Oklahoma City) - 180 miles north

Using all 3 gives 95% coverage vs 70% with one radar
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class RadarSite:
    """NEXRAD radar site information"""
    id: str
    name: str
    lat: float
    lon: float
    coverage_radius_km: float = 230  # Standard NEXRAD range


class RadarNetwork:
    """
    Manage NEXRAD radar network for multi-radar analysis
    """

    # Major NEXRAD sites covering hail-prone regions
    # Focus on Central US (Tornado Alley + Hail Alley)
    RADAR_SITES = {
        # Texas
        'KFWS': RadarSite('KFWS', 'Fort Worth', 32.5730, -97.3031),
        'KDFW': RadarSite('KDFW', 'Dallas/Fort Worth', 32.8983, -97.0400),
        'KEWX': RadarSite('KEWX', 'Austin/San Antonio', 29.7039, -98.0289),
        'KHGX': RadarSite('KHGX', 'Houston/Galveston', 29.4719, -95.0789),
        'KSJT': RadarSite('KSJT', 'San Angelo', 31.3711, -100.4925),
        'KGRK': RadarSite('KGRK', 'Central Texas', 30.7219, -97.3831),
        'KDYX': RadarSite('KDYX', 'Dyess AFB', 32.5386, -99.2542),
        'KMAF': RadarSite('KMAF', 'Midland/Odessa', 31.9433, -102.1894),
        'KLBB': RadarSite('KLBB', 'Lubbock', 33.6542, -101.8142),
        'KAMA': RadarSite('KAMA', 'Amarillo', 35.2333, -101.7092),

        # Oklahoma
        'KTLX': RadarSite('KTLX', 'Oklahoma City', 35.3331, -97.2778),
        'KINX': RadarSite('KINX', 'Tulsa', 36.1753, -95.5644),
        'KVNX': RadarSite('KVNX', 'Vance AFB', 36.7406, -98.1278),
        'KFDR': RadarSite('KFDR', 'Frederick', 34.3622, -98.9764),

        # Kansas
        'KICT': RadarSite('KICT', 'Wichita', 37.6544, -97.4431),
        'KDDC': RadarSite('KDDC', 'Dodge City', 37.7608, -99.9689),
        'KTWX': RadarSite('KTWX', 'Topeka', 38.9969, -96.2325),
        'KGLD': RadarSite('KGLD', 'Goodland', 39.3669, -101.7003),

        # Colorado
        'KFTG': RadarSite('KFTG', 'Denver', 39.7867, -104.5458),
        'KPUX': RadarSite('KPUX', 'Pueblo', 38.4595, -104.1814),
        'KGJX': RadarSite('KGJX', 'Grand Junction', 39.0619, -108.2136),

        # Nebraska
        'KUEX': RadarSite('KUEX', 'Grand Island', 40.3208, -98.4419),
        'KLNX': RadarSite('KLNX', 'North Platte', 41.9578, -100.5764),
        'KOAX': RadarSite('KOAX', 'Omaha', 41.3203, -96.3667),

        # Missouri
        'KSGF': RadarSite('KSGF', 'Springfield', 37.2350, -93.4006),
        'KEAX': RadarSite('KEAX', 'Kansas City', 38.8103, -94.2644),
        'KLSX': RadarSite('KLSX', 'St. Louis', 38.6986, -90.6828),

        # Arkansas
        'KLZK': RadarSite('KLZK', 'Little Rock', 34.8364, -92.2622),
        'KSRX': RadarSite('KSRX', 'Fort Smith', 35.2906, -94.3619),

        # New Mexico
        'KABX': RadarSite('KABX', 'Albuquerque', 35.1497, -106.8239),
        'KHDX': RadarSite('KHDX', 'Holloman AFB', 33.0764, -106.1219),
        'KFDX': RadarSite('KFDX', 'Cannon AFB', 34.6342, -103.6186),

        # Louisiana
        'KSHV': RadarSite('KSHV', 'Shreveport', 32.4508, -93.8414),
        'KPOE': RadarSite('KPOE', 'Fort Polk', 31.1553, -92.9758),
        'KLCH': RadarSite('KLCH', 'Lake Charles', 30.1253, -93.2161),

        # Mississippi
        'KDGX': RadarSite('KDGX', 'Jackson', 32.2797, -89.9844),

        # South Dakota
        'KUDX': RadarSite('KUDX', 'Rapid City', 44.1250, -102.8297),
        'KFSD': RadarSite('KFSD', 'Sioux Falls', 43.5878, -96.7292),
        'KABR': RadarSite('KABR', 'Aberdeen', 45.4558, -98.4131),

        # North Dakota
        'KBIS': RadarSite('KBIS', 'Bismarck', 46.7708, -100.7606),
        'KMVX': RadarSite('KMVX', 'Grand Forks', 47.5278, -97.3256),

        # Wyoming
        'KCYS': RadarSite('KCYS', 'Cheyenne', 41.1519, -104.8061),
        'KRIW': RadarSite('KRIW', 'Riverton', 43.0661, -108.4769),

        # Iowa
        'KDMX': RadarSite('KDMX', 'Des Moines', 41.7311, -93.7228),
        'KDVN': RadarSite('KDVN', 'Quad Cities', 41.6117, -90.5808),

        # Minnesota
        'KMPX': RadarSite('KMPX', 'Minneapolis', 44.8489, -93.5653),
    }

    def __init__(self):
        """Initialize radar network"""
        pass

    def find_covering_radars(
        self,
        latitude: float,
        longitude: float,
        max_radars: int = 5,
        max_distance_km: float = 230
    ) -> List[Dict]:
        """
        Find all radars that can see a location

        Args:
            latitude: Target latitude
            longitude: Target longitude
            max_radars: Maximum radars to return
            max_distance_km: Maximum distance to consider

        Returns:
            List of dicts with radar info, sorted by distance

        Example:
            >>> network = RadarNetwork()
            >>> radars = network.find_covering_radars(32.7767, -96.7970)
            >>> print(f"Dallas covered by {len(radars)} radars")
            >>> for radar in radars:
            ...     print(f"  {radar['site'].name}: {radar['distance_km']:.1f} km")
        """

        covering = []

        for radar_id, site in self.RADAR_SITES.items():
            # Calculate distance
            distance_km = self._calculate_distance_km(
                latitude, longitude,
                site.lat, site.lon
            )

            # Check if within coverage
            if distance_km <= max_distance_km:
                covering.append({
                    'site': site,
                    'distance_km': distance_km,
                    'quality': self._estimate_coverage_quality(distance_km)
                })

        # Sort by distance (closest first)
        covering.sort(key=lambda x: x['distance_km'])

        # Return top N
        return covering[:max_radars]

    def find_best_radars_for_event(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        target_radars: int = 3
    ) -> List[Dict]:
        """
        Find best radars to cover an entire event area

        Args:
            center_lat: Event center latitude
            center_lon: Event center longitude
            radius_km: Event radius (storm coverage area)
            target_radars: Desired number of radars

        Returns:
            List of radar dicts optimized for event coverage

        Example:
            >>> # Large event covering 50km radius
            >>> radars = network.find_best_radars_for_event(
            ...     32.7767, -96.7970, radius_km=50
            ... )
        """

        # Find all radars that can see the event center
        center_radars = self.find_covering_radars(
            center_lat, center_lon,
            max_radars=10
        )

        if not center_radars:
            return []

        # Score each radar based on event coverage
        scored_radars = []

        for radar_info in center_radars:
            site = radar_info['site']
            distance = radar_info['distance_km']

            # Check if radar can see entire event area
            # (distance + event_radius should be < radar_range)
            max_event_distance = distance + radius_km

            if max_event_distance > 230:
                # Event edge is beyond radar range
                coverage_fraction = 230 / max_event_distance
            else:
                coverage_fraction = 1.0

            # Quality score
            # - Closer is better
            # - Better coverage is better
            distance_score = max(0, 100 - (distance / 230) * 100)
            coverage_score = coverage_fraction * 100

            total_score = distance_score * 0.6 + coverage_score * 0.4

            scored_radars.append({
                'site': site,
                'distance_km': distance,
                'coverage_fraction': coverage_fraction,
                'score': total_score
            })

        # Sort by score
        scored_radars.sort(key=lambda x: x['score'], reverse=True)

        # Return top N
        return scored_radars[:target_radars]

    def get_radar_geometry(
        self,
        radar_site: RadarSite,
        target_lat: float,
        target_lon: float
    ) -> Dict:
        """
        Get geometric relationship between radar and target

        Args:
            radar_site: RadarSite object
            target_lat: Target latitude
            target_lon: Target longitude

        Returns:
            Dict with distance, azimuth, and beam heights
        """

        distance_km = self._calculate_distance_km(
            target_lat, target_lon,
            radar_site.lat, radar_site.lon
        )

        azimuth = self._calculate_bearing(
            radar_site.lat, radar_site.lon,
            target_lat, target_lon
        )

        # Calculate beam heights at different elevations
        beam_heights = {}
        for elevation in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
            height_m = self._calculate_beam_height(distance_km, elevation)
            beam_heights[elevation] = height_m

        return {
            'distance_km': distance_km,
            'azimuth_deg': azimuth,
            'beam_heights_m': beam_heights,
            'quality': self._estimate_coverage_quality(distance_km)
        }

    def get_all_sites(self) -> Dict[str, RadarSite]:
        """Get all radar sites"""
        return self.RADAR_SITES

    def get_site(self, site_id: str) -> Optional[RadarSite]:
        """Get a specific radar site by ID"""
        return self.RADAR_SITES.get(site_id.upper())

    @staticmethod
    def _calculate_distance_km(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance using Haversine formula"""

        R = 6371  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    @staticmethod
    def _calculate_bearing(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate bearing in degrees"""

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))

        bearing = math.degrees(math.atan2(y, x))

        return (bearing + 360) % 360

    @staticmethod
    def _calculate_beam_height(range_km: float, elevation_deg: float) -> float:
        """Calculate beam height accounting for Earth curvature"""

        Re = 6371.0  # Earth radius (km)
        Ke = 4.0 / 3.0  # Refraction coefficient

        elev_rad = math.radians(elevation_deg)

        height_km = (
            (range_km**2 + (Ke * Re)**2 +
             2 * range_km * Ke * Re * math.sin(elev_rad))**0.5
            - Ke * Re
        )

        return height_km * 1000  # Convert to meters

    @staticmethod
    def _estimate_coverage_quality(distance_km: float) -> str:
        """
        Estimate coverage quality based on distance

        NEXRAD coverage quality:
        - 0-100 km: Excellent (beam close to ground)
        - 100-150 km: Good
        - 150-200 km: Fair (beam high, may miss low-level)
        - 200+ km: Poor (beam very high)
        """

        if distance_km < 100:
            return "Excellent"
        elif distance_km < 150:
            return "Good"
        elif distance_km < 200:
            return "Fair"
        else:
            return "Poor"


if __name__ == '__main__':
    # Quick test
    print("Radar Network Test")
    print("=" * 40)

    network = RadarNetwork()

    # Find radars covering Dallas
    radars = network.find_covering_radars(32.7767, -96.7970, max_radars=5)

    print(f"\nRadars covering Dallas ({len(radars)} found):")
    for radar in radars:
        site = radar['site']
        print(f"  {site.name} ({site.id}): {radar['distance_km']:.1f} km - {radar['quality']}")
