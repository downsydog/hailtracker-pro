"""
Iowa State Mesonet MRMS MESH historical archive fetcher.

Downloads and parses MRMS MESH grib2 files for arbitrary UTC timestamps
from the Iowa State Mesonet archive:

    https://mtarchive.geol.iastate.edu/YYYY/MM/DD/mrms/ncep/MESH/
        MESH_00.50_YYYYMMDD-HHMMSS.grib2.gz

Returns the same dict format as MRMSProvider.fetch_mesh_grid() so it
plugs into the same downstream code.
"""

import gzip
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)

ARCHIVE_BASE = "https://mtarchive.geol.iastate.edu"


class IowaArchiveFetcher:
    """Thread-safe historical MRMS MESH fetcher with disk cache."""

    def __init__(self, cache_dir: str = "data/mrms_cache", timeout: int = 30):
        self.cache_dir = cache_dir
        self.timeout = timeout
        self._local = threading.local()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self, dt: datetime) -> Optional[Dict]:
        """
        Fetch MRMS MESH grid for a specific UTC timestamp.

        Snaps to nearest 2-minute boundary, checks disk cache, downloads
        if missing, parses grib2 with cfgrib.

        Returns dict with keys:
            status, lats, lons, mesh_mm, source_time, provider
        Or None on failure.
        """
        dt = self._snap_2min(dt)

        # Try exact timestamp, then ±2min neighbors
        for offset_min in [0, -2, 2]:
            try_dt = dt + timedelta(minutes=offset_min)
            result = self._fetch_single(try_dt)
            if result is not None:
                return result

        logger.debug("No MESH file found near %s (tried ±2min)", dt.isoformat())
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _session(self) -> requests.Session:
        if not hasattr(self._local, "session"):
            s = requests.Session()
            s.headers["User-Agent"] = "HailTracker-Pro/1.0 (MRMS-Backfill)"
            self._local.session = s
        return self._local.session

    def _fetch_single(self, dt: datetime) -> Optional[Dict]:
        """Attempt to fetch a single timestamp (cache-first)."""
        cache_path = self._cache_path(dt)

        # Check disk cache
        if os.path.isfile(cache_path) and os.path.getsize(cache_path) > 0:
            return self._parse_cached(cache_path, dt)

        # Download
        url = self._build_url(dt)
        try:
            resp = self._session().get(url, timeout=self.timeout)
        except requests.RequestException as e:
            logger.debug("Download failed %s: %s", url, e)
            return None

        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            logger.debug("HTTP %d for %s", resp.status_code, url)
            return None

        # Write to cache atomically
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        tmp_path = cache_path + ".tmp"
        try:
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
            os.replace(tmp_path, cache_path)
        except OSError as e:
            logger.debug("Cache write failed: %s", e)
            # Parse from memory instead
            return self._parse_bytes(resp.content, dt)

        # Rate limit — be kind to Iowa State
        time.sleep(0.1)

        return self._parse_cached(cache_path, dt)

    def _parse_cached(self, cache_path: str, dt: datetime) -> Optional[Dict]:
        """Parse a cached grib2.gz file."""
        try:
            with open(cache_path, "rb") as f:
                raw_gz = f.read()
        except OSError as e:
            logger.debug("Cache read failed: %s", e)
            return None
        return self._parse_bytes(raw_gz, dt)

    def _parse_bytes(self, raw_gz: bytes, dt: datetime) -> Optional[Dict]:
        """Decompress and parse grib2 data.

        Reuses the cfgrib/xarray pattern from AWSMRMSProvider._fetch_from_noaa()
        (src/radar/mrms/providers.py:318-378).
        """
        try:
            raw_data = gzip.decompress(raw_gz)
        except (gzip.BadGzipFile, OSError) as e:
            logger.warning("Corrupt grib2.gz for %s: %s", dt.isoformat(), e)
            # Delete cached file so next run re-downloads
            cache_path = self._cache_path(dt)
            if os.path.isfile(cache_path):
                try:
                    os.unlink(cache_path)
                except OSError:
                    pass
            return None

        try:
            import cfgrib  # noqa: F401
            import xarray as xr
        except ImportError:
            logger.error("cfgrib/xarray not available — cannot parse grib2")
            return None

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".grib2")
        try:
            os.write(tmp_fd, raw_data)
            os.close(tmp_fd)

            ds = xr.open_dataset(tmp_path, engine="cfgrib")

            # MESH variable name varies; try common names
            mesh_data = None
            for var_name in ["MESH", "unknown", "parameterNumber"]:
                if var_name in ds:
                    mesh_data = ds[var_name].values
                    lats = ds.latitude.values
                    lons = ds.longitude.values
                    break

            if mesh_data is None:
                # Take the first data variable
                var_name = list(ds.data_vars)[0]
                mesh_data = ds[var_name].values
                lats = ds.latitude.values
                lons = ds.longitude.values

            ds.close()

            # Convert lons from 0-360 to -180..180 if needed
            if lons.max() > 180:
                # Need to re-sort lons after wrapping
                lons = np.where(lons > 180, lons - 360, lons)
                sort_idx = np.argsort(lons)
                lons = lons[sort_idx]
                mesh_data = mesh_data[:, sort_idx]

            # Replace NaN / fill values with 0
            mesh_data = np.nan_to_num(mesh_data, nan=0.0, posinf=0.0, neginf=0.0)

            # Check for empty grid
            if mesh_data.max() <= 0:
                return {
                    "status": "ok_empty",
                    "source_time": dt.isoformat(),
                    "provider": "iowa_archive",
                }

            return {
                "status": "ok_data",
                "lats": lats.astype(np.float64),
                "lons": lons.astype(np.float64),
                "mesh_mm": mesh_data.astype(np.float32),
                "source_time": dt.isoformat(),
                "provider": "iowa_archive",
            }

        except Exception as e:
            logger.warning("grib2 parse error for %s: %s", dt.isoformat(), e)
            # Delete cached file so next run re-downloads
            cache_path = self._cache_path(dt)
            if os.path.isfile(cache_path):
                try:
                    os.unlink(cache_path)
                except OSError:
                    pass
            return None
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _build_url(self, dt: datetime) -> str:
        return (
            f"{ARCHIVE_BASE}/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}"
            f"/mrms/ncep/MESH/"
            f"MESH_00.50_{dt.strftime('%Y%m%d-%H%M%S')}.grib2.gz"
        )

    def _cache_path(self, dt: datetime) -> str:
        day_dir = os.path.join(self.cache_dir, dt.strftime("%Y%m%d"))
        return os.path.join(day_dir, f"MESH_{dt.strftime('%H%M%S')}.grib2.gz")

    @staticmethod
    def _snap_2min(dt: datetime) -> datetime:
        """Snap to nearest even minute (MRMS updates every 2 min)."""
        minute = dt.minute
        snapped = minute - (minute % 2)
        return dt.replace(minute=snapped, second=0, microsecond=0)
