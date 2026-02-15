"""
Thread-safe MRMS MESH cache.

Stores the latest MRMS grid in memory with atomic swap.
Provides point-query and bbox-sampling methods for consumers.
"""

import logging
import threading
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MRMSCache:
    """
    Thread-safe in-memory cache for MRMS MESH grid data.

    The cache holds one grid at a time (the latest). Updates are
    atomic (swap a reference under a lock). Reads are lock-free
    after grabbing the reference.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._grid: Optional[Dict] = None  # The cached grid dict
        self._update_count: int = 0
        self._last_error: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        """Whether a grid is currently cached."""
        return self._grid is not None

    @property
    def source_time(self) -> Optional[str]:
        """ISO timestamp of the cached grid, or None."""
        g = self._grid
        return g['source_time'] if g else None

    @property
    def provider(self) -> Optional[str]:
        """Provider name of the cached grid, or None."""
        g = self._grid
        return g['provider'] if g else None

    @property
    def update_count(self) -> int:
        return self._update_count

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def update(self, grid: Dict) -> None:
        """Atomically replace the cached grid."""
        with self._lock:
            self._grid = grid
            self._update_count += 1
            self._last_error = None

    def set_error(self, msg: str) -> None:
        """Record a fetch error without clearing the cache."""
        with self._lock:
            self._last_error = msg

    def query_point(self, lat: float, lon: float) -> Optional[float]:
        """
        Query MESH value at a single point (nearest-neighbor).

        Returns MESH in mm, or None if no grid cached or point is outside.
        """
        grid = self._grid
        if grid is None:
            return None

        lats = grid['lats']
        lons = grid['lons']
        mesh = grid['mesh_mm']

        # Nearest index
        i = int(np.argmin(np.abs(lats - lat)))
        j = int(np.argmin(np.abs(lons - lon)))

        # Check if the nearest grid point is reasonably close (within 1 step)
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
        """
        Query MESH values within a bounding box.

        Returns dict with:
            'peak_mm': float (max MESH in bbox)
            'avg_mm': float (mean of nonzero MESH in bbox)
            'count': int (number of nonzero cells)
        Or None if no grid cached.
        """
        grid = self._grid
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
        """
        Return a downsampled GeoJSON FeatureCollection of MESH values
        within the given bbox. Each feature is a Point with mesh_mm property.

        Args:
            min_lon, min_lat, max_lon, max_lat: Bounding box
            max_points: Maximum points to return (downsamples if needed)

        Returns:
            GeoJSON FeatureCollection dict
        """
        grid = self._grid
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

        # Determine downsample step
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
        grid = self._grid
        if grid is None:
            return {
                'loaded': False,
                'update_count': self._update_count,
                'last_error': self._last_error,
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
            'update_count': self._update_count,
            'last_error': self._last_error,
        }
