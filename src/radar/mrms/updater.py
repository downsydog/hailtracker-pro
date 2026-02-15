"""
Background MRMS updater thread.

Non-blocking daemon thread that periodically refreshes the MRMS MESH cache.
"""

import logging
import os
import threading
import time
from typing import Optional

from .cache import MRMSCache
from .providers import get_provider, MRMSProvider

logger = logging.getLogger(__name__)


class MRMSUpdater:
    """
    Background daemon thread that periodically fetches MRMS MESH data
    and updates the shared MRMSCache.

    Thread-safe, idempotent start/stop.
    """

    def __init__(
        self,
        cache: Optional[MRMSCache] = None,
        refresh_seconds: Optional[int] = None,
        provider_name: Optional[str] = None,
    ):
        self._cache = cache or MRMSCache()
        self._refresh_seconds = refresh_seconds or int(
            os.environ.get('MRMS_REFRESH_SECONDS', '120')
        )
        self._provider_name = provider_name or os.environ.get('MRMS_PROVIDER', 'aws')
        self._provider: MRMSProvider = get_provider(self._provider_name)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    @property
    def cache(self) -> MRMSCache:
        return self._cache

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the background updater. Idempotent."""
        if self._running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name='mrms-updater',
            daemon=True,
        )
        self._running = True
        self._thread.start()
        logger.info(
            f"MRMSUpdater started (provider={self._provider_name}, "
            f"refresh={self._refresh_seconds}s)"
        )

    def stop(self) -> None:
        """Stop the background updater. Idempotent."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("MRMSUpdater stopped")

    def fetch_once(self) -> bool:
        """
        Perform a single MRMS fetch and cache update.

        Returns True if successful, False otherwise.
        Safe to call from any thread (used for testing).
        """
        try:
            grid = self._provider.fetch_mesh_grid()
            if grid is not None:
                self._cache.update(grid)
                logger.info(
                    f"MRMS MESH updated: provider={grid.get('provider')}, "
                    f"source_time={grid.get('source_time')}"
                )
                return True
            else:
                self._cache.set_error("Provider returned None")
                return False
        except Exception as e:
            msg = f"MRMS fetch error: {e}"
            logger.warning(msg)
            self._cache.set_error(msg)
            return False

    def _run_loop(self) -> None:
        """Main updater loop. Runs in daemon thread."""
        # Initial fetch with short retry
        for attempt in range(3):
            if self._stop_event.is_set():
                break
            if self.fetch_once():
                break
            logger.info(f"MRMS initial fetch attempt {attempt + 1}/3 failed, retrying...")
            self._stop_event.wait(5)

        # Periodic refresh
        while not self._stop_event.is_set():
            self._stop_event.wait(self._refresh_seconds)
            if self._stop_event.is_set():
                break
            try:
                self.fetch_once()
            except Exception as e:
                logger.warning(f"MRMS refresh error: {e}")

        self._running = False

    def get_status(self) -> dict:
        """Return updater + cache status."""
        status = self._cache.get_status()
        status['updater_running'] = self._running
        status['refresh_seconds'] = self._refresh_seconds
        status['provider'] = self._provider_name
        return status
