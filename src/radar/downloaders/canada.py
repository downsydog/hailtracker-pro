"""
Canadian Radar Data Downloader

Downloads radar data from Environment and Climate Change Canada:
- Base URL: https://dd.weather.gc.ca/radar/
- Products: PRECIPET, CAPPI, etc.
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

logger = logging.getLogger('CanadaRadarDownloader')


@dataclass
class CanadaRadarFile:
    """Represents a Canadian radar file."""
    site_code: str
    timestamp: datetime
    product: str  # 'PRECIPET', 'CAPPI', etc.
    url: str
    local_path: str = None


class CanadaRadarDownloader:
    """
    Downloads Canadian radar data from Environment Canada.

    Data URL structure:
    https://dd.weather.gc.ca/radar/PRECIPET/GIF/{SITE}/
    https://dd.weather.gc.ca/radar/CAPPI/GIF/{SITE}/
    """

    BASE_URL = 'https://dd.weather.gc.ca/radar'

    # Available products
    PRODUCTS = {
        'PRECIPET': 'Precipitation estimate (rain rate)',
        'CAPPI': 'Constant Altitude PPI (reflectivity)',
        'DPQPE': 'Dual-pol QPE',
    }

    # Site code mappings (Environment Canada uses different codes)
    SITE_MAPPINGS = {
        'CASBE': 'XBE',  # Bethune
        'CASCM': 'WHK',  # Carvel
        'CASSA': 'XSM',  # Strathmore
        'CASAG': 'WUJ',  # Aldergrove
        'CASSI': 'XSS',  # Silver Star
        'CASMB': 'XMB',  # Foxwarren
        'CASWM': 'XWL',  # Woodlands
        'CASNB': 'XNC',  # Chipman
        'CASNL': 'WTP',  # Holyrood
        'CASNS': 'XGO',  # Halifax
        'CASFT': 'XFT',  # Franktown
        'CASBV': 'WBI',  # Britt
        'CASKR': 'WKR',  # King City
        'CASSP': 'WSO',  # Exeter
        'CASLA': 'WMN',  # Lac Castor
        'CASQC': 'XAM',  # Val d'Irene
        'CASSN': 'WVY',  # Villeroy
        'CASRF': 'XRA',  # Radisson SK
        'CASPY': 'XPR',  # Prince Albert
    }

    def __init__(self, data_dir: str = None):
        """
        Initialize Canada radar downloader.

        Args:
            data_dir: Directory for storing downloaded files
        """
        self.data_dir = Path(data_dir) if data_dir else Path('data/canada_radar')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    def _get_ec_site_code(self, site_code: str) -> str:
        """Convert our site code to Environment Canada code."""
        return self.SITE_MAPPINGS.get(site_code, site_code)

    def _parse_filename(self, filename: str) -> Optional[Dict]:
        """
        Parse Environment Canada radar filename.

        Format: YYYYMMDDHHMMSS_SITE_PRODUCT.gif
        """
        # Pattern varies by product
        patterns = [
            r'(\d{14})_(\w+)_(\w+)\.gif',
            r'(\d{12})_(\w+)\.gif',
        ]

        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                timestamp_str = groups[0]

                try:
                    if len(timestamp_str) == 14:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                    else:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M')
                    return {
                        'timestamp': timestamp,
                        'filename': filename
                    }
                except ValueError:
                    continue

        return None

    def list_available_images(
        self,
        site_code: str,
        product: str = 'PRECIPET',
        hours_back: int = 3
    ) -> List[CanadaRadarFile]:
        """
        List available radar images for a site.

        Args:
            site_code: Radar site code
            product: Radar product type
            hours_back: How many hours of data to list

        Returns:
            List of CanadaRadarFile objects
        """
        ec_site = self._get_ec_site_code(site_code)
        url = f"{self.BASE_URL}/{product}/GIF/{ec_site}/"

        files = []
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML to find .gif files
            # Simple regex approach (EC doesn't provide a proper API)
            gif_pattern = r'href="([^"]+\.gif)"'
            matches = re.findall(gif_pattern, response.text)

            for filename in matches:
                parsed = self._parse_filename(filename)
                if not parsed:
                    continue

                if parsed['timestamp'] >= cutoff:
                    files.append(CanadaRadarFile(
                        site_code=site_code,
                        timestamp=parsed['timestamp'],
                        product=product,
                        url=f"{url}{filename}"
                    ))

        except requests.RequestException as e:
            logger.warning(f"Error listing {site_code}/{product}: {e}")

        files.sort(key=lambda x: x.timestamp)
        return files

    def download_image(self, radar_file: CanadaRadarFile) -> str:
        """
        Download a radar image.

        Args:
            radar_file: CanadaRadarFile to download

        Returns:
            Local file path
        """
        # Organize by site/product/date
        date_str = radar_file.timestamp.strftime('%Y%m%d')
        local_dir = self.data_dir / radar_file.site_code / radar_file.product / date_str
        local_dir.mkdir(parents=True, exist_ok=True)

        filename = radar_file.url.split('/')[-1]
        local_path = local_dir / filename

        # Skip if already downloaded
        if local_path.exists() and local_path.stat().st_size > 0:
            radar_file.local_path = str(local_path)
            return str(local_path)

        logger.info(f"Downloading {radar_file.site_code} {radar_file.product} {radar_file.timestamp}")

        try:
            response = self.session.get(radar_file.url, timeout=60)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                f.write(response.content)

            radar_file.local_path = str(local_path)
            return str(local_path)

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if local_path.exists():
                local_path.unlink()
            raise

    def download_latest(
        self,
        site_code: str,
        product: str = 'PRECIPET'
    ) -> Optional[str]:
        """
        Download the latest image for a site.

        Args:
            site_code: Radar site code
            product: Radar product type

        Returns:
            Local file path or None
        """
        files = self.list_available_images(site_code, product, hours_back=1)

        if not files:
            logger.warning(f"No recent images for {site_code}")
            return None

        return self.download_image(files[-1])

    def get_composite_url(self) -> str:
        """
        Get URL for the national radar composite.

        Returns:
            URL for the latest national composite
        """
        return f"{self.BASE_URL}/NATIONAL_COMPOSITE/GIF/"

    def extract_reflectivity_from_gif(self, gif_path: str) -> Optional[Dict]:
        """
        Extract reflectivity data from Environment Canada GIF.

        The GIF uses a color palette where colors map to dBZ values.
        This is approximate as the exact palette varies.

        Args:
            gif_path: Path to downloaded GIF

        Returns:
            Dict with estimated max reflectivity and coverage info
        """
        if not HAS_PIL:
            logger.warning("PIL not available for image analysis")
            return None

        try:
            img = Image.open(gif_path)
            pixels = list(img.getdata())

            # Environment Canada color mapping (approximate)
            # These are rough mappings - actual values need calibration
            color_to_dbz = {
                (0, 255, 0): 20,      # Light green - light rain
                (0, 200, 0): 25,
                (0, 150, 0): 30,
                (255, 255, 0): 35,    # Yellow - moderate
                (255, 200, 0): 40,
                (255, 150, 0): 45,
                (255, 0, 0): 50,      # Red - heavy
                (200, 0, 0): 55,
                (150, 0, 150): 60,    # Purple - severe
                (255, 0, 255): 65,    # Magenta - extreme
            }

            max_dbz = 0
            significant_pixels = 0

            for pixel in pixels:
                if len(pixel) >= 3:
                    rgb = pixel[:3]
                    for color, dbz in color_to_dbz.items():
                        # Approximate color matching
                        if all(abs(c1 - c2) < 30 for c1, c2 in zip(rgb, color)):
                            if dbz > max_dbz:
                                max_dbz = dbz
                            if dbz >= 35:
                                significant_pixels += 1
                            break

            return {
                'max_reflectivity_dbz': max_dbz,
                'significant_pixel_count': significant_pixels,
                'total_pixels': len(pixels),
                'has_significant_returns': max_dbz >= 40
            }

        except Exception as e:
            logger.error(f"Error analyzing GIF: {e}")
            return None


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("CANADA RADAR DOWNLOADER TEST")
    print("=" * 60)

    downloader = CanadaRadarDownloader(data_dir='data/test_canada')

    # Test listing available sites
    test_sites = ['CASKR', 'CASWM', 'CASSA']

    for site in test_sites:
        print(f"\nListing images for {site}...")
        files = downloader.list_available_images(site, 'PRECIPET', hours_back=3)
        print(f"  Found {len(files)} images")

        if files:
            print(f"  Latest: {files[-1].timestamp}")
            # Download latest
            path = downloader.download_image(files[-1])
            print(f"  Downloaded to: {path}")

    print("\nCanada radar downloader ready!")
