"""
US NEXRAD Radar Data Downloader

Downloads Level 2 radar data from AWS S3:
- Real-time: s3://unidata-nexrad-level2-chunks/
- Archive: s3://noaa-nexrad-level2/
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
import re

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

logger = logging.getLogger('NEXRADDownloader')


@dataclass
class NEXRADFile:
    """Represents a NEXRAD radar file."""
    site_code: str
    timestamp: datetime
    s3_key: str
    local_path: str = None
    file_size: int = 0


class NEXRADDownloader:
    """
    Downloads US NEXRAD Level 2 radar data from AWS S3.

    Public S3 buckets (no credentials needed):
    - Real-time: unidata-nexrad-level2-chunks
    - Archive: noaa-nexrad-level2
    """

    ARCHIVE_BUCKET = 'noaa-nexrad-level2'
    REALTIME_BUCKET = 'unidata-nexrad-level2-chunks'

    def __init__(self, data_dir: str = None):
        """
        Initialize NEXRAD downloader.

        Args:
            data_dir: Directory for storing downloaded files
        """
        if not HAS_BOTO3:
            raise ImportError("boto3 is required for NEXRAD downloads. Install with: pip install boto3")

        self.data_dir = Path(data_dir) if data_dir else Path('data/nexrad')
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Configure S3 client for anonymous access
        self.s3 = boto3.client(
            's3',
            config=Config(signature_version=UNSIGNED),
            region_name='us-east-1'
        )

    def _parse_filename(self, filename: str) -> Optional[Tuple[str, datetime]]:
        """
        Parse NEXRAD filename to extract site code and timestamp.

        Format: KXXX20231231_235959_V06
        """
        # Pattern: SITE + YYYYMMDD_HHMMSS + _V## (or similar suffix)
        pattern = r'^([A-Z]{4})(\d{8}_\d{6})'
        match = re.match(pattern, filename)

        if not match:
            return None

        site_code = match.group(1)
        timestamp_str = match.group(2)

        try:
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            return site_code, timestamp
        except ValueError:
            return None

    def list_available_scans(
        self,
        site_code: str,
        start_time: datetime,
        end_time: datetime = None
    ) -> List[NEXRADFile]:
        """
        List available radar scans for a site within a time range.

        Args:
            site_code: Radar site code (e.g., 'KFTG')
            start_time: Start of time range
            end_time: End of time range (default: start_time + 1 hour)

        Returns:
            List of NEXRADFile objects
        """
        if end_time is None:
            end_time = start_time + timedelta(hours=1)

        files = []

        # Iterate through each day in the range
        current_date = start_time.date()
        end_date = end_time.date()

        while current_date <= end_date:
            # Construct S3 prefix: YYYY/MM/DD/SITE/
            prefix = f"{current_date.year}/{current_date.month:02d}/{current_date.day:02d}/{site_code}/"

            try:
                paginator = self.s3.get_paginator('list_objects_v2')
                pages = paginator.paginate(
                    Bucket=self.ARCHIVE_BUCKET,
                    Prefix=prefix
                )

                for page in pages:
                    for obj in page.get('Contents', []):
                        key = obj['Key']
                        filename = key.split('/')[-1]

                        # Skip MDM files (metadata)
                        if '_MDM' in filename:
                            continue

                        parsed = self._parse_filename(filename)
                        if not parsed:
                            continue

                        file_site, file_time = parsed

                        # Check if within time range
                        if start_time <= file_time <= end_time:
                            files.append(NEXRADFile(
                                site_code=file_site,
                                timestamp=file_time,
                                s3_key=key,
                                file_size=obj.get('Size', 0)
                            ))

            except Exception as e:
                logger.warning(f"Error listing {site_code} for {current_date}: {e}")

            current_date += timedelta(days=1)

        # Sort by timestamp
        files.sort(key=lambda x: x.timestamp)

        return files

    def download_scan(self, nexrad_file: NEXRADFile) -> str:
        """
        Download a single radar scan.

        Args:
            nexrad_file: NEXRADFile object to download

        Returns:
            Local file path
        """
        # Organize by site/date
        date_str = nexrad_file.timestamp.strftime('%Y%m%d')
        local_dir = self.data_dir / nexrad_file.site_code / date_str
        local_dir.mkdir(parents=True, exist_ok=True)

        filename = nexrad_file.s3_key.split('/')[-1]
        local_path = local_dir / filename

        # Skip if already downloaded
        if local_path.exists() and local_path.stat().st_size > 0:
            logger.debug(f"Already exists: {local_path}")
            nexrad_file.local_path = str(local_path)
            return str(local_path)

        logger.info(f"Downloading {nexrad_file.site_code} {nexrad_file.timestamp}")

        try:
            self.s3.download_file(
                self.ARCHIVE_BUCKET,
                nexrad_file.s3_key,
                str(local_path)
            )
            nexrad_file.local_path = str(local_path)
            return str(local_path)

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if local_path.exists():
                local_path.unlink()
            raise

    def download_time_range(
        self,
        site_code: str,
        start_time: datetime,
        end_time: datetime = None,
        max_files: int = None
    ) -> List[str]:
        """
        Download all scans in a time range.

        Args:
            site_code: Radar site code
            start_time: Start of time range
            end_time: End of time range
            max_files: Maximum number of files to download

        Returns:
            List of local file paths
        """
        # List available files
        files = self.list_available_scans(site_code, start_time, end_time)

        if not files:
            logger.warning(f"No files found for {site_code} in time range")
            return []

        # Limit files if requested
        if max_files and len(files) > max_files:
            files = files[:max_files]

        # Download each file
        local_paths = []
        for nexrad_file in files:
            try:
                path = self.download_scan(nexrad_file)
                local_paths.append(path)
            except Exception as e:
                logger.error(f"Failed to download {nexrad_file.s3_key}: {e}")

        return local_paths

    def get_latest_scan(self, site_code: str) -> Optional[str]:
        """
        Get the most recent scan from a radar site.

        Uses the real-time chunks bucket for lowest latency.

        Args:
            site_code: Radar site code

        Returns:
            Local file path or None
        """
        # Try real-time bucket first
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.REALTIME_BUCKET,
                Prefix=f"{site_code}/",
                MaxKeys=50
            )

            if 'Contents' not in response:
                # Fall back to archive bucket with recent time
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=30)
                files = self.list_available_scans(site_code, start_time, end_time)
                if files:
                    return self.download_scan(files[-1])
                return None

            # Find the most recent file
            objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)

            for obj in objects:
                key = obj['Key']
                filename = key.split('/')[-1]

                if '_MDM' in filename:
                    continue

                parsed = self._parse_filename(filename)
                if not parsed:
                    continue

                site, timestamp = parsed

                # Download from real-time bucket
                local_dir = self.data_dir / site_code / 'realtime'
                local_dir.mkdir(parents=True, exist_ok=True)
                local_path = local_dir / filename

                if not local_path.exists():
                    self.s3.download_file(
                        self.REALTIME_BUCKET,
                        key,
                        str(local_path)
                    )

                return str(local_path)

        except Exception as e:
            logger.error(f"Error getting latest scan from {site_code}: {e}")

        return None

    def cleanup_old_files(self, max_age_days: int = 7):
        """
        Clean up old downloaded files.

        Args:
            max_age_days: Maximum age of files to keep
        """
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        for site_dir in self.data_dir.iterdir():
            if not site_dir.is_dir():
                continue

            for date_dir in site_dir.iterdir():
                if not date_dir.is_dir():
                    continue

                # Check if directory is old
                try:
                    dir_date = datetime.strptime(date_dir.name, '%Y%m%d')
                    if dir_date < cutoff:
                        import shutil
                        shutil.rmtree(str(date_dir))
                        logger.info(f"Cleaned up {date_dir}")
                except ValueError:
                    pass


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("NEXRAD DOWNLOADER TEST")
    print("=" * 60)

    downloader = NEXRADDownloader(data_dir='data/test_nexrad')

    # Test listing files
    test_site = 'KFTG'
    test_time = datetime(2024, 5, 15, 20, 0)  # Example date with likely storms

    print(f"\nListing scans for {test_site} around {test_time}")
    files = downloader.list_available_scans(
        test_site,
        test_time,
        test_time + timedelta(hours=1)
    )

    print(f"Found {len(files)} files")
    for f in files[:5]:
        print(f"  {f.timestamp} - {f.file_size / 1024:.1f} KB")

    if files:
        print("\nDownloading first file...")
        path = downloader.download_scan(files[0])
        print(f"Downloaded to: {path}")

    print("\nNEXRAD downloader ready!")
