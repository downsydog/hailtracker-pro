"""
MRMS data providers.

Primary:   NOAA MRMS MESH via HTTPS (Iowa State Mesonet MRMS archive)
Fallback:  Iowa Mesonet MRMS WMS tiles (lighter weight)

The MRMS MESH product we target is the "MESH" (Maximum Expected Size of Hail)
composite reflectivity product, available as grib2 or as pre-rendered imagery.

To keep dependencies light (no grib2 libs), we fetch pre-downsampled JSON/CSV
from the Iowa Mesonet MRMS interface OR fall back to a point-sampling approach.
"""

import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import requests
import numpy as np

logger = logging.getLogger(__name__)

# MRMS MESH product URLs
# Iowa Mesonet provides MRMS products as easily-parseable JSON
_MESONET_MRMS_BASE = "https://mesonet.agron.iastate.edu/api/1/mrms"


class MRMSProvider:
    """Base class for MRMS data providers."""

    def fetch_mesh_grid(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[Dict]:
        """
        Fetch MRMS MESH grid data.

        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) or None for CONUS

        Returns:
            Dict with keys:
                'status': str ('ok_data' | 'ok_empty' | 'synthetic')
                'lats': np.ndarray (1D)    — absent when status='ok_empty'
                'lons': np.ndarray (1D)    — absent when status='ok_empty'
                'mesh_mm': np.ndarray (2D) — absent when status='ok_empty'
                'source_time': str (ISO format)
                'provider': str
            Or None on failure (network/HTTP/parse error).
        """
        raise NotImplementedError


class MesonetMRMSProvider(MRMSProvider):
    """
    Iowa State Mesonet MRMS provider.

    Uses the Mesonet's MRMS MESH latest product endpoint.
    Falls back to a synthetic grid built from point queries if the
    bulk endpoint is unavailable.
    """

    # CONUS bounding box (default)
    CONUS_BBOX = (-130.0, 20.0, -60.0, 55.0)

    # Downsample resolution for CONUS (degrees)
    GRID_STEP = 0.25  # ~25km resolution for overlay

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'HailTracker-Pro/1.0 (MRMS-MESH-Ingest)',
        })

    def fetch_mesh_grid(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[Dict]:
        """Fetch MRMS MESH via Mesonet."""
        bbox = bbox or self.CONUS_BBOX
        min_lon, min_lat, max_lon, max_lat = bbox

        try:
            result = self._fetch_via_json_api(min_lon, min_lat, max_lon, max_lat)
            if result is not None:
                return result  # ok_data or ok_empty
        except Exception as e:
            logger.warning(f"Mesonet MRMS JSON API failed: {e}")

        try:
            return self._build_synthetic_grid(min_lon, min_lat, max_lon, max_lat)
        except Exception as e:
            logger.warning(f"Mesonet MRMS synthetic grid failed: {e}")

        return None

    def _fetch_via_json_api(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> Optional[Dict]:
        """
        Try the Mesonet MRMS JSON API for the latest MESH product.
        This endpoint may not always be available; we handle that gracefully.
        """
        url = (
            f"https://mesonet.agron.iastate.edu/geojson/network/MRMS.geojson"
        )
        try:
            resp = self._session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
        except Exception:
            return None

        # Parse GeoJSON point features with MESH values
        features = data.get('features', [])
        if not features:
            return {'status': 'ok_empty'}

        points = []
        for f in features:
            geom = f.get('geometry', {})
            props = f.get('properties', {})
            if geom.get('type') != 'Point':
                continue
            lon, lat = geom['coordinates'][:2]
            mesh_val = props.get('mesh', 0)
            if mesh_val is None:
                mesh_val = 0
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                points.append((lat, lon, float(mesh_val)))

        if not points:
            return {'status': 'ok_empty'}

        return self._points_to_grid(points, min_lon, min_lat, max_lon, max_lat)

    # Hard wall-clock cap for the synthetic-grid fallback.  Without this
    # the nested loop can run for thousands of seconds (5000 reqs × 5s each).
    _SYNTHETIC_MAX_SECONDS = int(os.environ.get('MRMS_SYNTHETIC_MAX_SECONDS', '15'))

    def _build_synthetic_grid(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> Optional[Dict]:
        """
        Build a synthetic MESH grid by querying the Mesonet MRMS
        point-value endpoint over a coarse grid.

        This is the most reliable fallback but slower.
        Wall-clock capped at ``_SYNTHETIC_MAX_SECONDS`` to prevent
        blocking the caller for minutes/hours.
        """
        from datetime import datetime, timezone

        step = self.GRID_STEP
        lats = np.arange(min_lat, max_lat + step / 2, step)
        lons = np.arange(min_lon, max_lon + step / 2, step)

        # Limit grid size to prevent excessive requests
        if len(lats) * len(lons) > 5000:
            # Increase step to keep grid manageable
            step = max(0.5, ((max_lat - min_lat) * (max_lon - min_lon) / 5000) ** 0.5)
            lats = np.arange(min_lat, max_lat + step / 2, step)
            lons = np.arange(min_lon, max_lon + step / 2, step)

        mesh_grid = np.zeros((len(lats), len(lons)), dtype=np.float32)

        # Batch query: use the MRMS point query endpoint
        # We sample a sparse grid and interpolate
        deadline = time.time() + self._SYNTHETIC_MAX_SECONDS
        sampled = 0
        budget_exhausted = False
        for i, lat in enumerate(lats):
            if budget_exhausted:
                break
            for j, lon in enumerate(lons):
                if time.time() >= deadline:
                    logger.info(
                        "Synthetic grid wall-clock cap (%ds) reached after %d samples",
                        self._SYNTHETIC_MAX_SECONDS, sampled,
                    )
                    budget_exhausted = True
                    break
                try:
                    url = (
                        f"https://mesonet.agron.iastate.edu/json/mrms_lookup.py"
                        f"?lat={lat:.3f}&lon={lon:.3f}&product=mesh"
                    )
                    resp = self._session.get(url, timeout=5)
                    if resp.status_code == 200:
                        result = resp.json()
                        val = result.get('value', 0)
                        if val is not None:
                            mesh_grid[i, j] = float(val)
                            sampled += 1
                except Exception:
                    pass

                # Rate limit
                if sampled > 0 and sampled % 50 == 0:
                    time.sleep(0.5)

        if sampled == 0:
            return None

        return {
            'status': 'synthetic',
            'lats': lats.astype(np.float64),
            'lons': lons.astype(np.float64),
            'mesh_mm': mesh_grid,
            'source_time': datetime.now(timezone.utc).isoformat(),
            'provider': 'mesonet_synthetic',
        }

    def _points_to_grid(
        self,
        points: List[Tuple[float, float, float]],
        min_lon: float, min_lat: float, max_lon: float, max_lat: float,
    ) -> Dict:
        """Convert scattered (lat, lon, mesh_mm) points to a regular grid."""
        from datetime import datetime, timezone

        step = self.GRID_STEP
        lats = np.arange(min_lat, max_lat + step / 2, step)
        lons = np.arange(min_lon, max_lon + step / 2, step)
        mesh_grid = np.zeros((len(lats), len(lons)), dtype=np.float32)

        # Nearest-neighbor binning
        for lat, lon, mesh_val in points:
            if mesh_val <= 0:
                continue
            i = int(round((lat - min_lat) / step))
            j = int(round((lon - min_lon) / step))
            if 0 <= i < len(lats) and 0 <= j < len(lons):
                mesh_grid[i, j] = max(mesh_grid[i, j], mesh_val)

        return {
            'status': 'ok_data',
            'lats': lats.astype(np.float64),
            'lons': lons.astype(np.float64),
            'mesh_mm': mesh_grid,
            'source_time': datetime.now(timezone.utc).isoformat(),
            'provider': 'mesonet_json',
        }


class AWSMRMSProvider(MRMSProvider):
    """
    NOAA MRMS MESH via HTTPS from NOAA's public MRMS distribution.

    The MRMS MESH product is published as grib2 files at:
    https://mrms.ncep.noaa.gov/data/2D/MESH/

    To avoid requiring grib2 parsing libraries, we download the latest
    grib2 file and parse it with numpy if pygrib or cfgrib is available,
    otherwise fall back to MesonetMRMSProvider.
    """

    MRMS_BASE_URL = "https://mrms.ncep.noaa.gov/data/2D/MESH/"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'HailTracker-Pro/1.0 (MRMS-MESH-Ingest)',
        })
        self._fallback = MesonetMRMSProvider(timeout=timeout)

    def fetch_mesh_grid(
        self,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[Dict]:
        """Fetch MRMS MESH from NOAA, fall back to Mesonet."""
        try:
            return self._fetch_from_noaa(bbox)
        except Exception as e:
            logger.info(f"NOAA MRMS fetch failed ({e}), falling back to Mesonet")
            return self._fallback.fetch_mesh_grid(bbox)

    def _fetch_from_noaa(
        self, bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[Dict]:
        """
        Attempt to fetch and parse the latest MRMS MESH grib2 from NOAA.
        Requires cfgrib or pygrib. If not available, raises ImportError
        which triggers fallback.
        """
        import gzip
        import tempfile
        import os
        from datetime import datetime, timezone

        # Get the latest file listing
        resp = self._session.get(self.MRMS_BASE_URL, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"MRMS index returned {resp.status_code}")

        # Parse file listing for latest .grib2.gz file
        text = resp.text
        import re
        files = re.findall(r'href="(MRMS_MESH_00\.50_\d{8}-\d{6}\.grib2\.gz)"', text)
        if not files:
            raise RuntimeError("No MESH grib2 files found in MRMS index")

        latest_file = sorted(files)[-1]
        file_url = f"{self.MRMS_BASE_URL}{latest_file}"

        # Download the grib2.gz
        resp = self._session.get(file_url, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"MESH download returned {resp.status_code}")

        # Decompress and parse
        raw_data = gzip.decompress(resp.content)

        # Try cfgrib (xarray-based)
        try:
            import cfgrib
            import xarray as xr

            with tempfile.NamedTemporaryFile(suffix='.grib2', delete=False) as f:
                f.write(raw_data)
                tmp_path = f.name

            try:
                ds = xr.open_dataset(tmp_path, engine='cfgrib')
                # MESH variable name varies; try common names
                for var_name in ['MESH', 'unknown', 'parameterNumber']:
                    if var_name in ds:
                        mesh_data = ds[var_name].values
                        lats = ds.latitude.values
                        lons = ds.longitude.values
                        break
                else:
                    # Take the first data variable
                    var_name = list(ds.data_vars)[0]
                    mesh_data = ds[var_name].values
                    lats = ds.latitude.values
                    lons = ds.longitude.values

                # Convert lons from 0-360 to -180..180 if needed
                if lons.max() > 180:
                    lons = np.where(lons > 180, lons - 360, lons)

                # Apply bbox filter if specified
                if bbox:
                    min_lon, min_lat, max_lon, max_lat = bbox
                    lat_mask = (lats >= min_lat) & (lats <= max_lat)
                    lon_mask = (lons >= min_lon) & (lons <= max_lon)
                    lat_indices = np.where(lat_mask)[0]
                    lon_indices = np.where(lon_mask)[0]
                    if len(lat_indices) > 0 and len(lon_indices) > 0:
                        lats = lats[lat_indices]
                        lons = lons[lon_indices]
                        mesh_data = mesh_data[np.ix_(lat_indices, lon_indices)]

                # Downsample if too large
                if mesh_data.size > 50000:
                    step = max(1, int(np.sqrt(mesh_data.size / 50000)))
                    mesh_data = mesh_data[::step, ::step]
                    lats = lats[::step]
                    lons = lons[::step]

                return {
                    'status': 'ok_data',
                    'lats': lats.astype(np.float64),
                    'lons': lons.astype(np.float64),
                    'mesh_mm': mesh_data.astype(np.float32),
                    'source_time': datetime.now(timezone.utc).isoformat(),
                    'provider': 'noaa_mrms',
                }
            finally:
                os.unlink(tmp_path)

        except ImportError:
            raise ImportError("cfgrib not available for grib2 parsing")


def get_provider(provider_name: str = 'aws') -> MRMSProvider:
    """Factory function for MRMS providers."""
    if provider_name == 'aws':
        return AWSMRMSProvider()
    elif provider_name == 'mesonet':
        return MesonetMRMSProvider()
    else:
        logger.warning(f"Unknown MRMS provider '{provider_name}', using mesonet")
        return MesonetMRMSProvider()
