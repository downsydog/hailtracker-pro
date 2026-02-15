"""
Health and Readiness Checks

Provides:
  GET /api/system/health  — Liveness probe (always 200 if process is alive)
  GET /api/system/ready   — Readiness probe (checks DB, optional subsystems)
  GET /api/system/metrics — Lightweight application metrics
"""

import os
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Callable, Optional

logger = logging.getLogger(__name__)

# Process start time (for uptime)
_start_time = time.monotonic()
_start_utc = datetime.now(timezone.utc).isoformat()


class HealthCheck:
    """
    Aggregates readiness checks from subsystems.

    Usage:
        hc = HealthCheck()
        hc.register('database', check_db_func)
        hc.register('mrms_cache', check_mrms_func)

        status = hc.check_all()
        # {'healthy': True, 'checks': {'database': {'ok': True, 'ms': 2}, ...}}
    """

    def __init__(self):
        self._checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._lock = threading.Lock()
        # Counters
        self._request_count = 0
        self._error_count = 0

    def register(self, name: str, check_fn: Callable[[], Dict[str, Any]]):
        """Register a readiness check.

        check_fn should return {'ok': bool, ...extra_info}.
        It must not block for more than 5 seconds.
        """
        with self._lock:
            self._checks[name] = check_fn

    def increment_requests(self):
        self._request_count += 1

    def increment_errors(self):
        self._error_count += 1

    def check_all(self) -> Dict[str, Any]:
        """Run all readiness checks and return aggregated result."""
        results = {}
        all_ok = True

        with self._lock:
            checks = dict(self._checks)

        for name, fn in checks.items():
            t0 = time.monotonic()
            try:
                result = fn()
                result['ms'] = round((time.monotonic() - t0) * 1000, 1)
                results[name] = result
                if not result.get('ok', False):
                    all_ok = False
            except Exception as e:
                results[name] = {
                    'ok': False,
                    'error': str(e),
                    'ms': round((time.monotonic() - t0) * 1000, 1),
                }
                all_ok = False

        return {
            'healthy': all_ok,
            'checks': results,
        }

    def get_health(self) -> Dict[str, Any]:
        """Liveness probe — always returns OK if process is alive."""
        return {
            'status': 'ok',
            'uptime_seconds': round(time.monotonic() - _start_time, 1),
            'started_at': _start_utc,
            'pid': os.getpid(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Lightweight application metrics."""
        import sys
        return {
            'uptime_seconds': round(time.monotonic() - _start_time, 1),
            'started_at': _start_utc,
            'requests_total': self._request_count,
            'errors_total': self._error_count,
            'python_version': sys.version.split()[0],
            'pid': os.getpid(),
            'thread_count': threading.active_count(),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional[HealthCheck] = None
_instance_lock = threading.Lock()


def get_health_check() -> HealthCheck:
    """Get the singleton HealthCheck instance."""
    global _instance
    if _instance is not None:
        return _instance
    with _instance_lock:
        if _instance is not None:
            return _instance
        _instance = HealthCheck()
        return _instance
