"""
Redis-metadata + disk-backed MRMS MESH cache.

Drop-in replacement for MRMSCache.  Grid arrays live on disk under
``data/mrms/``;  Redis stores only lightweight metadata pointers so
the cache survives process restarts and is shareable across workers.

Disk layout:
    data/mrms/<YYYYMMDDHHMM>.npz   — timestamped archive
    data/mrms/latest.npz           — atomic-rename symlink to newest

Redis keys (metadata only — no large blobs):
    mrms:latest_path    STRING  path to latest .npz on disk, TTL 600s
    mrms:source_time    STRING  ISO timestamp, TTL 600s
    mrms:provider       STRING  provider name (mesonet, aws, …), TTL 600s
    mrms:last_status    STRING  ok_data|ok_empty|synthetic|error, TTL 600s
    mrms:update_count   INT  (INCR, no TTL)
    mrms:last_error     STRING, TTL 600s
"""

import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Redis key constants
_KEY_LATEST_PATH = 'mrms:latest_path'
_KEY_SOURCE_TIME = 'mrms:source_time'
_KEY_PROVIDER = 'mrms:provider'
_KEY_LAST_STATUS = 'mrms:last_status'
_KEY_UPDATE_COUNT = 'mrms:update_count'
_KEY_LAST_ERROR = 'mrms:last_error'

_META_TTL = 600        # 10 minutes
_MRMS_DIR = os.path.join('data', 'mrms')


class RedisMRMSCache:
    """
    Disk + Redis-metadata MRMS MESH cache (same interface as MRMSCache).

    * ``update()`` writes grid to ``data/mrms/<ts>.npz``, atomically
      renames to ``data/mrms/latest.npz``, and sets Redis metadata.
    * Reads use an in-process numpy grid (fast).  The grid is reloaded
      from disk only when ``mrms:source_time`` changes in Redis.
    """

    def __init__(self, redis_client, mrms_dir: str = _MRMS_DIR):
        """
        Args:
            redis_client: ``redis.Redis`` (or compatible) instance.
            mrms_dir: Directory for .npz files (default ``data/mrms``).
        """
        self._r = redis_client
        self._mrms_dir = mrms_dir
        os.makedirs(self._mrms_dir, exist_ok=True)

        # In-process memory cache
        self._local_grid: Optional[Dict] = None
        self._last_loaded_source_time: Optional[str] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Properties (MRMSCache interface)
    # ------------------------------------------------------------------

    @property
    def is_loaded(self) -> bool:
        grid = self._get_local_grid()
        return grid is not None

    @property
    def source_time(self) -> Optional[str]:
        grid = self._get_local_grid()
        return grid['source_time'] if grid else None

    @property
    def provider(self) -> Optional[str]:
        grid = self._get_local_grid()
        return grid['provider'] if grid else None

    @property
    def update_count(self) -> int:
        val = self._r.get(_KEY_UPDATE_COUNT)
        return int(val) if val else 0

    @property
    def last_error(self) -> Optional[str]:
        val = self._r.get(_KEY_LAST_ERROR)
        if val is None:
            return None
        return val.decode() if isinstance(val, bytes) else val

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def update(self, grid: Dict) -> None:
        """
        Persist grid to disk, update Redis metadata, refresh local cache.

        Writes to ``data/mrms/<YYYYMMDDHHMM>.npz`` then atomically
        renames a temp file to ``data/mrms/latest.npz``.
        """
        os.makedirs(self._mrms_dir, exist_ok=True)

        source_time_str = grid.get('source_time', '')

        # Timestamped filename
        try:
            dt = datetime.fromisoformat(source_time_str.replace('Z', '+00:00'))
            ts_label = dt.strftime('%Y%m%d%H%M%S')
        except (ValueError, AttributeError):
            ts_label = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')

        archive_path = os.path.join(self._mrms_dir, f'{ts_label}.npz')
        latest_path = os.path.join(self._mrms_dir, 'latest.npz')

        # Write to temp file, then rename (atomic on same filesystem)
        fd, tmp_path = tempfile.mkstemp(
            suffix='.npz', dir=self._mrms_dir,
        )
        try:
            os.close(fd)
            np.savez_compressed(
                tmp_path,
                lats=grid['lats'],
                lons=grid['lons'],
                mesh_mm=grid['mesh_mm'],
            )
            # Archive copy
            if not os.path.exists(archive_path):
                try:
                    # Hard-link archive from tmp before rename
                    import shutil
                    shutil.copy2(tmp_path, archive_path)
                except Exception:
                    pass

            # Atomic rename to latest.npz
            # On Windows os.rename fails if dest exists; use replace
            os.replace(tmp_path, latest_path)
            tmp_path = None  # don't clean up below
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        # Update Redis metadata (no grid bytes!)
        provider_str = grid.get('provider', '')
        status_str = grid.get('status', 'ok_data')
        pipe = self._r.pipeline()
        pipe.set(_KEY_LATEST_PATH, latest_path, ex=_META_TTL)
        pipe.set(_KEY_SOURCE_TIME, source_time_str, ex=_META_TTL)
        pipe.set(_KEY_PROVIDER, provider_str, ex=_META_TTL)
        pipe.set(_KEY_LAST_STATUS, status_str, ex=_META_TTL)
        pipe.incr(_KEY_UPDATE_COUNT)
        pipe.delete(_KEY_LAST_ERROR)
        pipe.execute()

        # Immediately update in-process cache
        parsed = {
            'lats': grid['lats'],
            'lons': grid['lons'],
            'mesh_mm': grid['mesh_mm'],
            'source_time': source_time_str,
            'provider': provider_str,
        }
        with self._lock:
            self._local_grid = parsed
            self._last_loaded_source_time = source_time_str

    def set_error(self, msg: str) -> None:
        """Record a fetch error without clearing the cache."""
        pipe = self._r.pipeline()
        pipe.set(_KEY_LAST_ERROR, msg, ex=_META_TTL)
        pipe.set(_KEY_LAST_STATUS, 'error', ex=_META_TTL)
        pipe.execute()

    def mark_alive(self, source_time: str = '', provider: str = '',
                   status: str = 'ok_empty') -> None:
        """Record a successful provider contact without writing grid data.

        Updates source_time and provider metadata (keeps MRMS "fresh" for
        health checks) but does NOT write any grid to disk or clear the
        existing cached grid.  Clears last_error.
        """
        if not source_time:
            source_time = datetime.now(timezone.utc).isoformat()
        pipe = self._r.pipeline()
        pipe.set(_KEY_SOURCE_TIME, source_time, ex=_META_TTL)
        if provider:
            pipe.set(_KEY_PROVIDER, provider, ex=_META_TTL)
        pipe.set(_KEY_LAST_STATUS, status, ex=_META_TTL)
        pipe.delete(_KEY_LAST_ERROR)
        pipe.execute()

    # ------------------------------------------------------------------
    # Read methods (all from in-process memory)
    # ------------------------------------------------------------------

    def query_point(self, lat: float, lon: float) -> Optional[float]:
        """Nearest-neighbor MESH lookup.  Returns mm or None."""
        grid = self._get_local_grid()
        if grid is None:
            return None

        lats = grid['lats']
        lons = grid['lons']
        mesh = grid['mesh_mm']

        i = int(np.argmin(np.abs(lats - lat)))
        j = int(np.argmin(np.abs(lons - lon)))

        if len(lats) > 1:
            lat_step = abs(float(lats[1] - lats[0]))
        else:
            lat_step = 1.0
        if len(lons) > 1:
            lon_step = abs(float(lons[1] - lons[0]))
        else:
            lon_step = 1.0

        if abs(float(lats[i]) - lat) > lat_step * 1.5:
            return None
        if abs(float(lons[j]) - lon) > lon_step * 1.5:
            return None

        val = float(mesh[i, j])
        return val if val > 0 else None

    def query_bbox(
        self,
        min_lon: float, min_lat: float,
        max_lon: float, max_lat: float,
    ) -> Optional[Dict]:
        """Query MESH stats within a bounding box."""
        grid = self._get_local_grid()
        if grid is None:
            return None

        lats = grid['lats']
        lons = grid['lons']
        mesh = grid['mesh_mm']

        lat_mask = (lats >= min_lat) & (lats <= max_lat)
        lon_mask = (lons >= min_lon) & (lons <= max_lon)

        lat_indices = np.where(lat_mask)[0]
        lon_indices = np.where(lon_mask)[0]

        if len(lat_indices) == 0 or len(lon_indices) == 0:
            return None

        sub = mesh[np.ix_(lat_indices, lon_indices)]
        nonzero = sub[sub > 0]

        if len(nonzero) == 0:
            return {'peak_mm': 0.0, 'avg_mm': 0.0, 'count': 0}

        return {
            'peak_mm': float(np.max(nonzero)),
            'avg_mm': float(np.mean(nonzero)),
            'count': int(len(nonzero)),
        }

    def get_geojson_grid(
        self,
        min_lon: float, min_lat: float,
        max_lon: float, max_lat: float,
        max_points: int = 2000,
    ) -> Dict:
        """Return downsampled GeoJSON FeatureCollection of MESH values."""
        grid = self._get_local_grid()
        if grid is None:
            return {'type': 'FeatureCollection', 'features': []}

        lats = grid['lats']
        lons = grid['lons']
        mesh = grid['mesh_mm']

        lat_mask = (lats >= min_lat) & (lats <= max_lat)
        lon_mask = (lons >= min_lon) & (lons <= max_lon)

        lat_indices = np.where(lat_mask)[0]
        lon_indices = np.where(lon_mask)[0]

        if len(lat_indices) == 0 or len(lon_indices) == 0:
            return {
                'type': 'FeatureCollection',
                'features': [],
                'properties': {
                    'source_time': grid.get('source_time'),
                    'provider': grid.get('provider'),
                },
            }

        total = len(lat_indices) * len(lon_indices)
        step = max(1, int(np.sqrt(total / max_points)))

        lat_sub = lat_indices[::step]
        lon_sub = lon_indices[::step]

        features: List[Dict] = []
        for i in lat_sub:
            for j in lon_sub:
                val = float(mesh[i, j])
                if val <= 0:
                    continue
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [round(float(lons[j]), 4), round(float(lats[i]), 4)],
                    },
                    'properties': {
                        'mesh_mm': round(val, 1),
                        'mesh_inches': round(val / 25.4, 2),
                    },
                })

        return {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'source_time': grid.get('source_time'),
                'provider': grid.get('provider'),
                'bbox': [min_lon, min_lat, max_lon, max_lat],
                'total_points': len(features),
            },
        }

    def get_status(self) -> Dict:
        """Return cache status summary."""
        grid = self._get_local_grid()
        uc = self.update_count
        le = self.last_error

        if grid is None:
            return {
                'loaded': False,
                'update_count': uc,
                'last_error': le,
            }

        mesh = grid['mesh_mm']
        nonzero = mesh[mesh > 0]

        return {
            'loaded': True,
            'source_time': grid.get('source_time'),
            'provider': grid.get('provider'),
            'grid_shape': list(mesh.shape),
            'nonzero_cells': int(len(nonzero)),
            'peak_mm': round(float(np.max(nonzero)), 1) if len(nonzero) > 0 else 0,
            'update_count': uc,
            'last_error': le,
        }

    # ------------------------------------------------------------------
    # Local cache — invalidate-on-source_time-change
    # ------------------------------------------------------------------

    def _get_local_grid(self) -> Optional[Dict]:
        """
        Return in-process grid.  Reloads from disk only when
        ``mrms:source_time`` in Redis differs from what we last loaded.
        """
        # Fast path: already loaded and source_time unchanged
        try:
            current_st = self._r.get(_KEY_SOURCE_TIME)
            if current_st is not None and isinstance(current_st, bytes):
                current_st = current_st.decode()
        except Exception:
            # Redis unreachable — serve from memory if available
            with self._lock:
                return self._local_grid

        with self._lock:
            if (
                self._local_grid is not None
                and current_st is not None
                and current_st == self._last_loaded_source_time
            ):
                return self._local_grid

        # Source time changed (or first load) → reload from disk
        grid = self._load_from_disk()
        with self._lock:
            if grid is not None:
                self._local_grid = grid
                self._last_loaded_source_time = current_st or grid.get('source_time')
            elif self._local_grid is None:
                # No disk file and nothing in memory
                return None
            # else: disk read failed, keep stale memory grid
        return grid if grid is not None else self._local_grid

    def _load_from_disk(self) -> Optional[Dict]:
        """Load latest.npz from disk.  Returns None on any failure."""
        latest_path = os.path.join(self._mrms_dir, 'latest.npz')
        try:
            if not os.path.exists(latest_path):
                return None

            npz = np.load(latest_path)

            # Read metadata from Redis
            source_time = self._r.get(_KEY_SOURCE_TIME)
            provider = self._r.get(_KEY_PROVIDER)
            if source_time is not None and isinstance(source_time, bytes):
                source_time = source_time.decode()
            if provider is not None and isinstance(provider, bytes):
                provider = provider.decode()

            return {
                'lats': npz['lats'],
                'lons': npz['lons'],
                'mesh_mm': npz['mesh_mm'],
                'source_time': source_time or '',
                'provider': provider or '',
            }
        except Exception as e:
            logger.warning("Failed to load MRMS grid from disk: %s", e)
            return None


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_instance: Optional[RedisMRMSCache] = None
_instance_lock = threading.Lock()


def get_mrms_cache(redis_url: str = 'redis://localhost:6379/0') -> RedisMRMSCache:
    """Get or create the singleton RedisMRMSCache instance."""
    global _instance
    if _instance is not None:
        return _instance

    with _instance_lock:
        if _instance is not None:
            return _instance

        import redis as redis_lib
        client = redis_lib.Redis.from_url(redis_url, decode_responses=False)
        _instance = RedisMRMSCache(client)
        return _instance
