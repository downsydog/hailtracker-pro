"""
Extract vertical reflectivity profiles from radar

Used for MESH algorithm - needs data from all elevation angles
to analyze full vertical column of storm
"""

import math
import numpy as np
from typing import List, Dict, Optional, Tuple


class VerticalProfileExtractor:
    """
    Extract vertical profile of reflectivity at a location

    Combines data from all radar elevation angles to build
    complete vertical column for MESH analysis
    """

    def __init__(self):
        """Initialize the extractor"""
        self.extraction_history: List[Dict] = []

    def extract_profile(
        self,
        radar,
        latitude: float,
        longitude: float
    ) -> List[Dict]:
        """
        Extract vertical reflectivity profile from PyART radar object

        Args:
            radar: PyART radar object
            latitude: Target latitude
            longitude: Target longitude

        Returns:
            List of {height, reflectivity, elevation, range_km} dicts
            Sorted by height

        Example:
            >>> extractor = VerticalProfileExtractor()
            >>> profile = extractor.extract_profile(radar, 32.7767, -96.7970)
            >>>
            >>> for point in profile:
            ...     print(f"{point['height']}m: {point['reflectivity']} dBZ")
        """

        # Get radar location
        radar_lat = radar.latitude['data'][0]
        radar_lon = radar.longitude['data'][0]

        # Calculate azimuth and range to target
        azimuth, range_km = self._latlon_to_radar_coords(
            radar_lat, radar_lon, latitude, longitude
        )

        profile = []

        # Loop through all elevation angles
        for sweep_num in range(radar.nsweeps):
            elevation = radar.fixed_angle['data'][sweep_num]

            # Get data for this sweep
            sweep_slice = radar.get_slice(sweep_num)

            try:
                # Try different field names
                reflectivity = None
                for field_name in ['reflectivity', 'DBZ', 'REF', 'DBZH']:
                    if field_name in radar.fields:
                        reflectivity = radar.get_field(sweep_num, field_name)
                        break

                if reflectivity is None:
                    continue

            except Exception:
                continue

            # Get azimuth and range arrays
            azimuth_data = radar.azimuth['data'][sweep_slice]
            range_data = radar.range['data'] / 1000.0  # Convert to km

            # Find closest gate to our target
            az_idx = np.argmin(np.abs(azimuth_data - azimuth))
            range_idx = np.argmin(np.abs(range_data - range_km))

            # Get reflectivity value
            z = reflectivity[az_idx, range_idx]

            # Skip masked (no data)
            if np.ma.is_masked(z):
                continue

            # Calculate beam height
            height = self._calculate_beam_height(range_km, elevation)

            profile.append({
                'height': int(height),
                'reflectivity': float(z),
                'elevation': float(elevation),
                'range_km': round(range_km, 2)
            })

        # Sort by height
        profile.sort(key=lambda x: x['height'])

        # Store in history
        self.extraction_history.append({
            'lat': latitude,
            'lon': longitude,
            'profile_points': len(profile),
            'max_height': max(p['height'] for p in profile) if profile else 0
        })

        return profile

    def _latlon_to_radar_coords(
        self,
        radar_lat: float, radar_lon: float,
        target_lat: float, target_lon: float
    ) -> Tuple[float, float]:
        """Convert lat/lon to radar azimuth and range"""

        # Calculate differences
        dlat = target_lat - radar_lat
        dlon = target_lon - radar_lon

        # Convert to km
        dlat_km = dlat * 111.0
        dlon_km = dlon * 111.0 * math.cos(math.radians(radar_lat))

        # Azimuth (0° = North)
        azimuth = math.degrees(math.atan2(dlon_km, dlat_km))
        if azimuth < 0:
            azimuth += 360

        # Range
        range_km = math.sqrt(dlat_km**2 + dlon_km**2)

        return azimuth, range_km

    def _calculate_beam_height(self, range_km: float, elevation: float) -> float:
        """
        Calculate radar beam height above ground

        Accounts for Earth curvature and atmospheric refraction

        Args:
            range_km: Range from radar
            elevation: Elevation angle (degrees)

        Returns:
            Height in meters
        """

        # Earth radius (km)
        Re = 6371.0

        # 4/3 Earth radius for standard refraction
        Ke = 4.0 / 3.0

        # Convert elevation to radians
        elev_rad = math.radians(elevation)

        # Height with Earth curvature
        # Formula from Doviak & Zrnic (1993)
        height_km = (
            (range_km**2 + (Ke * Re)**2 +
             2 * range_km * Ke * Re * math.sin(elev_rad))**0.5
            - Ke * Re
        )

        # Convert to meters
        return height_km * 1000

    @staticmethod
    def create_simulated_profile(
        storm_intensity: str = 'moderate',
        max_height_m: int = 10000,
        freezing_level_m: int = 3500
    ) -> List[Dict]:
        """
        Create a simulated vertical profile for testing

        Args:
            storm_intensity: 'weak', 'moderate', 'severe', or 'extreme'
            max_height_m: Maximum height to simulate
            freezing_level_m: Freezing level height

        Returns:
            List of {height, reflectivity} dicts
        """

        # Base reflectivity profiles by intensity
        intensity_profiles = {
            'weak': {
                'base_z': 40,
                'peak_z': 50,
                'peak_height': 4000
            },
            'moderate': {
                'base_z': 45,
                'peak_z': 60,
                'peak_height': 5000
            },
            'severe': {
                'base_z': 50,
                'peak_z': 68,
                'peak_height': 6000
            },
            'extreme': {
                'base_z': 55,
                'peak_z': 75,
                'peak_height': 6500
            }
        }

        if storm_intensity not in intensity_profiles:
            storm_intensity = 'moderate'

        params = intensity_profiles[storm_intensity]

        profile = []
        heights = range(2000, min(max_height_m + 1, 11000), 1000)

        for height in heights:
            # Gaussian-like profile centered on peak height
            distance_from_peak = abs(height - params['peak_height'])
            spread = 2000  # Width of the peak

            # Calculate reflectivity at this height
            z = params['peak_z'] - (distance_from_peak / spread) ** 2 * (params['peak_z'] - params['base_z'])

            # Decrease above 8km (storm top)
            if height > 8000:
                z -= (height - 8000) * 0.01

            profile.append({
                'height': height,
                'reflectivity': max(z, 20)  # Minimum 20 dBZ
            })

        return profile

    @staticmethod
    def create_profile_from_elevations(
        reflectivity_by_elevation: Dict[float, float],
        range_km: float
    ) -> List[Dict]:
        """
        Create vertical profile from reflectivity values at different elevations

        Args:
            reflectivity_by_elevation: Dict mapping elevation angle to reflectivity
            range_km: Range from radar in km

        Returns:
            List of {height, reflectivity, elevation} dicts
        """
        extractor = VerticalProfileExtractor()
        profile = []

        for elevation, reflectivity in reflectivity_by_elevation.items():
            height = extractor._calculate_beam_height(range_km, elevation)

            profile.append({
                'height': int(height),
                'reflectivity': reflectivity,
                'elevation': elevation,
                'range_km': range_km
            })

        profile.sort(key=lambda x: x['height'])
        return profile


class ProfileAnalyzer:
    """
    Analyze vertical reflectivity profiles for storm characteristics
    """

    @staticmethod
    def analyze_profile(profile: List[Dict]) -> Dict:
        """
        Analyze a vertical profile for storm characteristics

        Args:
            profile: List of {height, reflectivity} dicts

        Returns:
            Dict with analysis results
        """
        if not profile:
            return {'error': 'Empty profile'}

        reflectivities = [p['reflectivity'] for p in profile]
        heights = [p['height'] for p in profile]

        max_z = max(reflectivities)
        max_z_idx = reflectivities.index(max_z)
        max_z_height = heights[max_z_idx]

        # Calculate vertical gradient
        if len(profile) >= 2:
            gradients = []
            for i in range(1, len(profile)):
                dz = reflectivities[i] - reflectivities[i-1]
                dh = (heights[i] - heights[i-1]) / 1000.0  # km
                if dh > 0:
                    gradients.append(dz / dh)
            avg_gradient = sum(gradients) / len(gradients) if gradients else 0
        else:
            avg_gradient = 0

        # Determine storm type
        if max_z >= 65 and max_z_height >= 5000:
            storm_type = "Supercell"
        elif max_z >= 55 and max_z_height >= 4000:
            storm_type = "Severe Thunderstorm"
        elif max_z >= 45:
            storm_type = "Moderate Thunderstorm"
        else:
            storm_type = "Weak/Developing"

        # Calculate hail potential
        hail_zone_z = [
            p['reflectivity'] for p in profile
            if 4000 <= p['height'] <= 8000
        ]
        hail_potential = max(hail_zone_z) if hail_zone_z else 0

        return {
            'max_reflectivity': max_z,
            'max_z_height_m': max_z_height,
            'min_reflectivity': min(reflectivities),
            'avg_reflectivity': sum(reflectivities) / len(reflectivities),
            'storm_top_m': max(heights),
            'avg_gradient_dbz_per_km': round(avg_gradient, 2),
            'storm_type': storm_type,
            'hail_zone_max_z': hail_potential,
            'profile_depth_m': max(heights) - min(heights),
            'num_levels': len(profile)
        }


if __name__ == '__main__':
    # Quick test
    print("Vertical Profile Extractor Test")
    print("=" * 40)

    # Create simulated profiles
    for intensity in ['weak', 'moderate', 'severe', 'extreme']:
        profile = VerticalProfileExtractor.create_simulated_profile(intensity)
        analysis = ProfileAnalyzer.analyze_profile(profile)

        print(f"\n{intensity.upper()} Storm:")
        print(f"  Max Z: {analysis['max_reflectivity']:.1f} dBZ at {analysis['max_z_height_m']}m")
        print(f"  Storm Type: {analysis['storm_type']}")
        print(f"  Hail Zone Max: {analysis['hail_zone_max_z']:.1f} dBZ")
