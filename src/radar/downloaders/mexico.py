"""
Mexican Radar Data Downloader

Downloads radar data from CONAGUA (Comision Nacional del Agua):
- SMN (Servicio Meteorologico Nacional)
- Provides radar imagery for Mexico

Note: CONAGUA data is more limited than NEXRAD/EC, often only
providing composite images rather than raw volumetric data.
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
import re
from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger('MexicoRadarDownloader')


@dataclass
class MexicoRadarFile:
    """Represents a Mexican radar file."""
    site_code: str
    timestamp: datetime
    product: str
    url: str
    local_path: str = None


class MexicoRadarDownloader:
    """
    Downloads Mexican radar data from CONAGUA/SMN.

    Note: Mexican radar data availability is more limited than
    US/Canadian sources. This downloader handles what's available
    and provides fallback options.
    """

    # CONAGUA radar base URLs
    BASE_URL = 'http://smn.conagua.gob.mx/es/observando-el-tiempo/radar-meteorologico'
    IMAGES_URL = 'http://smn.conagua.gob.mx/tools/DATA/Radar'

    # Site code to SMN region mappings
    SITE_REGIONS = {
        'MXVER': 'Veracruz',
        'MXTAM': 'Tamaulipas',
        'MXNLE': 'NuevoLeon',
        'MXSOA': 'Sonora_Guaymas',
        'MXSOB': 'Sonora_Mazatan',
        'MXCHI': 'Chihuahua',
        'MXBCS': 'BCS',
        'MXDGO': 'Durango',
        'MXSIN': 'Sinaloa',
        'MXJAL': 'Jalisco',
        'MXMCH': 'Michoacan',
        'MXCAM': 'Campeche',
        'MXYUC': 'Yucatan',
        'MXQRO': 'QuintanaRoo',
        'MXOAX': 'Oaxaca',
        'MXCDM': 'CDMX',
    }

    def __init__(self, data_dir: str = None):
        """
        Initialize Mexico radar downloader.

        Args:
            data_dir: Directory for storing downloaded files
        """
        self.data_dir = Path(data_dir) if data_dir else Path('data/mexico_radar')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HailTracker/2.0 (Weather Research)'
        })

    def _get_smn_region(self, site_code: str) -> str:
        """Convert site code to SMN region name."""
        return self.SITE_REGIONS.get(site_code, site_code)

    def get_latest_composite(self) -> Optional[str]:
        """
        Download the latest national radar composite for Mexico.

        Returns:
            Local file path or None
        """
        # CONAGUA provides national composites
        composite_url = f"{self.IMAGES_URL}/Nacional/ultimo.gif"

        try:
            response = self.session.get(composite_url, timeout=30)
            response.raise_for_status()

            local_path = self.data_dir / 'composite' / f"mexico_composite_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.gif"
            local_path.parent.mkdir(parents=True, exist_ok=True)

            with open(local_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded Mexico composite to {local_path}")
            return str(local_path)

        except requests.RequestException as e:
            logger.warning(f"Failed to download Mexico composite: {e}")
            return None

    def get_regional_image(self, site_code: str) -> Optional[str]:
        """
        Download regional radar image for a site.

        Args:
            site_code: Mexican radar site code

        Returns:
            Local file path or None
        """
        region = self._get_smn_region(site_code)

        # Try different URL patterns (CONAGUA changes these periodically)
        url_patterns = [
            f"{self.IMAGES_URL}/Regional/{region}/ultimo.gif",
            f"{self.IMAGES_URL}/{region}/ultimo.gif",
            f"{self.IMAGES_URL}/Radares/{region}.gif",
        ]

        for url in url_patterns:
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    timestamp = datetime.utcnow()
                    local_path = self.data_dir / site_code / f"{site_code}_{timestamp.strftime('%Y%m%d_%H%M')}.gif"
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(local_path, 'wb') as f:
                        f.write(response.content)

                    logger.info(f"Downloaded {site_code} to {local_path}")
                    return str(local_path)

            except requests.RequestException:
                continue

        logger.warning(f"Could not find radar image for {site_code}")
        return None

    def list_available_sites(self) -> List[str]:
        """
        Get list of available Mexican radar sites.

        Returns:
            List of site codes with available data
        """
        available = []

        for site_code in self.SITE_REGIONS.keys():
            region = self._get_smn_region(site_code)
            test_url = f"{self.IMAGES_URL}/Regional/{region}/ultimo.gif"

            try:
                response = self.session.head(test_url, timeout=10)
                if response.status_code == 200:
                    available.append(site_code)
            except requests.RequestException:
                pass

        return available

    def download_latest(self, site_code: str) -> Optional[str]:
        """
        Download latest available image for a site.

        Args:
            site_code: Mexican radar site code

        Returns:
            Local file path or None
        """
        return self.get_regional_image(site_code)

    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """
        Analyze radar image for precipitation intensity.

        Args:
            image_path: Path to downloaded image

        Returns:
            Dict with analysis results
        """
        if not HAS_PIL:
            logger.warning("PIL not available for image analysis")
            return None

        try:
            img = Image.open(image_path)
            pixels = list(img.getdata())

            # Mexican radar color palette (approximate)
            # Similar to US NWS colors
            color_intensity = {
                (0, 255, 0): 'light',       # Green - light
                (255, 255, 0): 'moderate',  # Yellow - moderate
                (255, 165, 0): 'heavy',     # Orange - heavy
                (255, 0, 0): 'intense',     # Red - intense
                (255, 0, 255): 'extreme',   # Magenta - extreme
            }

            intensity_counts = {'light': 0, 'moderate': 0, 'heavy': 0, 'intense': 0, 'extreme': 0}
            max_intensity = None

            for pixel in pixels:
                if len(pixel) >= 3:
                    rgb = pixel[:3]
                    for color, intensity in color_intensity.items():
                        if all(abs(c1 - c2) < 40 for c1, c2 in zip(rgb, color)):
                            intensity_counts[intensity] += 1
                            max_intensity = intensity
                            break

            has_significant = (
                intensity_counts['heavy'] > 100 or
                intensity_counts['intense'] > 50 or
                intensity_counts['extreme'] > 10
            )

            return {
                'intensity_counts': intensity_counts,
                'max_intensity': max_intensity,
                'has_significant_precipitation': has_significant,
                'potential_hail': intensity_counts['intense'] > 50 or intensity_counts['extreme'] > 10
            }

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return None


# Alternative data sources for Mexico
class MexicoAlternativeDownloader:
    """
    Alternative data sources for Mexican weather data.

    When CONAGUA radar is unavailable, try:
    - GOES-16 satellite imagery
    - GFS model data
    - US border radar spillover
    """

    def __init__(self):
        self.session = requests.Session()

    def get_goes_imagery(self, lat: float, lon: float) -> Optional[str]:
        """
        Get GOES-16 satellite imagery for a location.

        This can supplement or replace ground radar data.
        """
        # GOES imagery from NOAA
        goes_url = "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/gm/GEOCOLOR/latest.jpg"

        try:
            response = self.session.get(goes_url, timeout=30)
            if response.status_code == 200:
                return goes_url
        except requests.RequestException:
            pass

        return None

    def get_border_radar_spillover(self, lat: float, lon: float) -> List[str]:
        """
        Find US radars that may cover Mexican border regions.

        Returns:
            List of US radar sites that could provide coverage
        """
        border_radars = []

        # US radars near Mexican border
        us_border_sites = {
            'KEPZ': (31.8731, -106.6981),  # El Paso
            'KYUX': (32.4953, -114.6567),  # Yuma
            'KNKX': (32.9189, -117.0419),  # San Diego
            'KBRO': (25.9158, -97.4189),   # Brownsville
            'KDFX': (29.2728, -100.2803),  # Laughlin AFB
            'KMAF': (31.9433, -102.1894),  # Midland
        }

        for site, (site_lat, site_lon) in us_border_sites.items():
            # Check if location is within 200km of radar
            import math
            dist = 111 * math.sqrt((lat - site_lat)**2 + ((lon - site_lon) * math.cos(math.radians(lat)))**2)
            if dist < 200:
                border_radars.append(site)

        return border_radars


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("MEXICO RADAR DOWNLOADER TEST")
    print("=" * 60)

    downloader = MexicoRadarDownloader(data_dir='data/test_mexico')

    # Test national composite
    print("\nDownloading national composite...")
    composite = downloader.get_latest_composite()
    if composite:
        print(f"  Downloaded to: {composite}")
    else:
        print("  Composite not available")

    # Test regional images
    test_sites = ['MXCDM', 'MXNLE', 'MXJAL']
    for site in test_sites:
        print(f"\nDownloading {site}...")
        path = downloader.download_latest(site)
        if path:
            print(f"  Downloaded to: {path}")
        else:
            print(f"  {site} not available")

    # Test alternative sources
    print("\n" + "=" * 60)
    print("ALTERNATIVE DATA SOURCES")
    print("=" * 60)

    alt = MexicoAlternativeDownloader()

    # Check border radar coverage for Monterrey
    print("\nBorder radar coverage for Monterrey (25.67, -100.31):")
    border_radars = alt.get_border_radar_spillover(25.67, -100.31)
    print(f"  US radars with coverage: {border_radars}")

    print("\nMexico radar downloader ready!")
