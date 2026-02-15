"""
MRMS MESH National Backbone

Provides CONUS-wide MRMS Maximum Expected Size of Hail (MESH) data
via background refresh with thread-safe caching.

Env gates:
    ENABLE_MRMS=true/false (default false)
    MRMS_REFRESH_SECONDS=120
    MRMS_PROVIDER=aws  (fallback: mesonet)
"""

from .cache import MRMSCache
from .updater import MRMSUpdater

__all__ = ['MRMSCache', 'MRMSUpdater']
