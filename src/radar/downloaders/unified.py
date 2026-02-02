"""
Unified Radar Downloader

Provides a single interface for downloading radar data from all sources:
- US NEXRAD (AWS S3)
- Canadian Environment Canada
- Mexican CONAGUA

Automatically routes requests to the appropriate downloader based on
the radar site's country.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Union
from dataclasses import dataclass
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from src.radar.coverage import get_radar_by_code, find_covering_radars, RadarSite

logger = logging.getLogger('UnifiedRadarDownloader')


@dataclass
class RadarDownload:
    """Unified radar download result."""
    site_code: str
    country: str
    timestamp: datetime
    local_path: str
    data_type: str  # 'level2', 'precipet', 'composite', etc.
    source: str     # 'nexrad', 'ec', 'conagua'


class UnifiedRadarDownloader:
    """
    Unified interface for downloading radar data from all North American sources.

    Automatically determines the correct downloader based on radar site location
    and handles country-specific data formats.
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize unified downloader.

        Args:
            data_dir: Base directory for all radar data
        """
        self.data_dir = Path(data_dir) if data_dir else Path('data/radar')
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize country-specific downloaders lazily
        self._nexrad = None
        self._canada = None
        self._mexico = None

    @property
    def nexrad(self):
        """Get NEXRAD downloader (lazy init)."""
        if self._nexrad is None:
            from .nexrad import NEXRADDownloader
            self._nexrad = NEXRADDownloader(data_dir=str(self.data_dir / 'nexrad'))
        return self._nexrad

    @property
    def canada(self):
        """Get Canada downloader (lazy init)."""
        if self._canada is None:
            from .canada import CanadaRadarDownloader
            self._canada = CanadaRadarDownloader(data_dir=str(self.data_dir / 'canada'))
        return self._canada

    @property
    def mexico(self):
        """Get Mexico downloader (lazy init)."""
        if self._mexico is None:
            from .mexico import MexicoRadarDownloader
            self._mexico = MexicoRadarDownloader(data_dir=str(self.data_dir / 'mexico'))
        return self._mexico

    def _get_country(self, site_code: str) -> Optional[str]:
        """Determine country for a radar site."""
        radar = get_radar_by_code(site_code)
        if radar:
            return radar.country

        # Infer from site code prefix
        if site_code.startswith('K') or site_code.startswith('P'):
            return 'US'
        elif site_code.startswith('CAS') or site_code.startswith('C'):
            return 'CA'
        elif site_code.startswith('MX'):
            return 'MX'

        return None

    def download_latest(self, site_code: str) -> Optional[RadarDownload]:
        """
        Download the latest available data from a radar site.

        Args:
            site_code: Radar site code

        Returns:
            RadarDownload object or None
        """
        country = self._get_country(site_code)

        if country == 'US':
            return self._download_nexrad_latest(site_code)
        elif country == 'CA':
            return self._download_canada_latest(site_code)
        elif country == 'MX':
            return self._download_mexico_latest(site_code)
        else:
            logger.error(f"Unknown country for radar {site_code}")
            return None

    def download_time_range(
        self,
        site_code: str,
        start_time: datetime,
        end_time: datetime = None,
        max_files: int = None
    ) -> List[RadarDownload]:
        """
        Download radar data for a time range.

        Args:
            site_code: Radar site code
            start_time: Start of time range
            end_time: End of time range
            max_files: Maximum files to download

        Returns:
            List of RadarDownload objects
        """
        country = self._get_country(site_code)

        if country == 'US':
            return self._download_nexrad_range(site_code, start_time, end_time, max_files)
        elif country == 'CA':
            # Canadian data is typically only recent
            return [self._download_canada_latest(site_code)] if self._download_canada_latest(site_code) else []
        elif country == 'MX':
            # Mexican data is typically only recent
            return [self._download_mexico_latest(site_code)] if self._download_mexico_latest(site_code) else []

        return []

    def download_for_location(
        self,
        lat: float,
        lon: float,
        timestamp: datetime = None,
        include_all_covering: bool = False
    ) -> List[RadarDownload]:
        """
        Download radar data for a specific location.

        Automatically finds covering radars and downloads from all of them
        if multi-radar coverage is requested.

        Args:
            lat: Latitude
            lon: Longitude
            timestamp: Time to download (default: latest)
            include_all_covering: Download from all covering radars

        Returns:
            List of RadarDownload objects
        """
        # Find covering radars
        max_radars = 5 if include_all_covering else 1
        coverages = find_covering_radars(lat, lon, max_radars=max_radars)

        if not coverages:
            logger.warning(f"No radar coverage for ({lat}, {lon})")
            return []

        downloads = []
        for coverage in coverages:
            radar = coverage.radar

            try:
                if timestamp:
                    # Download specific time
                    results = self.download_time_range(
                        radar.site_code,
                        timestamp - timedelta(minutes=15),
                        timestamp + timedelta(minutes=15),
                        max_files=1
                    )
                    downloads.extend(results)
                else:
                    # Download latest
                    result = self.download_latest(radar.site_code)
                    if result:
                        downloads.append(result)

            except Exception as e:
                logger.error(f"Failed to download from {radar.site_code}: {e}")

        return downloads

    def _download_nexrad_latest(self, site_code: str) -> Optional[RadarDownload]:
        """Download latest NEXRAD data."""
        try:
            path = self.nexrad.get_latest_scan(site_code)
            if path:
                return RadarDownload(
                    site_code=site_code,
                    country='US',
                    timestamp=datetime.utcnow(),
                    local_path=path,
                    data_type='level2',
                    source='nexrad'
                )
        except Exception as e:
            logger.error(f"NEXRAD download error for {site_code}: {e}")
        return None

    def _download_nexrad_range(
        self,
        site_code: str,
        start_time: datetime,
        end_time: datetime,
        max_files: int = None
    ) -> List[RadarDownload]:
        """Download NEXRAD data for time range."""
        downloads = []
        try:
            paths = self.nexrad.download_time_range(site_code, start_time, end_time, max_files)
            for path in paths:
                # Extract timestamp from filename
                filename = Path(path).name
                try:
                    # Parse NEXRAD filename: KXXX20231231_235959_V06
                    import re
                    match = re.search(r'(\d{8}_\d{6})', filename)
                    if match:
                        ts = datetime.strptime(match.group(1), '%Y%m%d_%H%M%S')
                    else:
                        ts = datetime.utcnow()
                except:
                    ts = datetime.utcnow()

                downloads.append(RadarDownload(
                    site_code=site_code,
                    country='US',
                    timestamp=ts,
                    local_path=path,
                    data_type='level2',
                    source='nexrad'
                ))
        except Exception as e:
            logger.error(f"NEXRAD range download error: {e}")

        return downloads

    def _download_canada_latest(self, site_code: str) -> Optional[RadarDownload]:
        """Download latest Canadian radar data."""
        try:
            path = self.canada.download_latest(site_code)
            if path:
                return RadarDownload(
                    site_code=site_code,
                    country='CA',
                    timestamp=datetime.utcnow(),
                    local_path=path,
                    data_type='precipet',
                    source='ec'
                )
        except Exception as e:
            logger.error(f"Canada download error for {site_code}: {e}")
        return None

    def _download_mexico_latest(self, site_code: str) -> Optional[RadarDownload]:
        """Download latest Mexican radar data."""
        try:
            path = self.mexico.download_latest(site_code)
            if path:
                return RadarDownload(
                    site_code=site_code,
                    country='MX',
                    timestamp=datetime.utcnow(),
                    local_path=path,
                    data_type='composite',
                    source='conagua'
                )
        except Exception as e:
            logger.error(f"Mexico download error for {site_code}: {e}")
        return None

    def get_status(self) -> Dict:
        """
        Get status of all downloaders.

        Returns:
            Dict with status info
        """
        return {
            'nexrad_available': self._nexrad is not None,
            'canada_available': self._canada is not None,
            'mexico_available': self._mexico is not None,
            'data_directory': str(self.data_dir),
        }


# Convenience functions
def download_for_event(
    lat: float,
    lon: float,
    event_time: datetime,
    data_dir: str = None
) -> List[RadarDownload]:
    """
    Download radar data for a hail event.

    Downloads from all covering radars to enable multi-radar fusion.

    Args:
        lat: Event latitude
        lon: Event longitude
        event_time: Time of event
        data_dir: Data directory

    Returns:
        List of RadarDownload objects
    """
    downloader = UnifiedRadarDownloader(data_dir=data_dir)
    return downloader.download_for_location(
        lat, lon,
        timestamp=event_time,
        include_all_covering=True
    )


def download_latest_for_region(
    state_province: str,
    data_dir: str = None
) -> List[RadarDownload]:
    """
    Download latest data from all radars in a state/province.

    Args:
        state_province: State or province code
        data_dir: Data directory

    Returns:
        List of RadarDownload objects
    """
    from src.radar.coverage import find_radars_by_state

    downloader = UnifiedRadarDownloader(data_dir=data_dir)
    radars = find_radars_by_state(state_province)

    downloads = []
    for radar in radars:
        result = downloader.download_latest(radar.site_code)
        if result:
            downloads.append(result)

    return downloads


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("UNIFIED RADAR DOWNLOADER TEST")
    print("=" * 60)

    downloader = UnifiedRadarDownloader(data_dir='data/test_unified')

    # Test different countries
    test_cases = [
        ('KFTG', 'US', 'Denver'),
        ('KTLX', 'US', 'Oklahoma City'),
        ('CASKR', 'CA', 'King City'),
        ('MXCDM', 'MX', 'Mexico City'),
    ]

    print("\nTesting individual radar downloads:")
    for site, country, name in test_cases:
        print(f"\n  {site} ({country} - {name})...")
        result = downloader.download_latest(site)
        if result:
            print(f"    Downloaded: {result.local_path}")
            print(f"    Type: {result.data_type}")
        else:
            print(f"    No data available")

    # Test location-based download
    print("\n" + "=" * 60)
    print("LOCATION-BASED DOWNLOAD TEST")
    print("=" * 60)

    print("\nDownloading for Oklahoma City (35.47, -97.52)...")
    results = downloader.download_for_location(
        35.47, -97.52,
        include_all_covering=True
    )
    print(f"Downloaded {len(results)} files:")
    for r in results:
        print(f"  - {r.site_code}: {r.local_path}")

    print("\nUnified downloader ready!")
