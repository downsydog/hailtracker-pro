"""
Circuit Breaker Pattern

Prevents cascading failures by tracking error rates per key (e.g. radar_id)
and temporarily stopping requests to failing endpoints.

States:
  CLOSED   — Normal operation, requests pass through
  OPEN     — Too many failures, requests rejected immediately
  HALF_OPEN — After cooldown, allow one probe request

Usage:
    cb = CircuitBreaker(failure_threshold=5, cooldown_seconds=60)

    if cb.allow('KTLX'):
        try:
            result = download_radar('KTLX')
            cb.record_success('KTLX')
        except Exception as e:
            cb.record_failure('KTLX')
            raise

    # Or use the context manager:
    with cb.guard('KTLX'):
        download_radar('KTLX')
"""

import time
import threading
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


class CircuitBreakerOpen(Exception):
    """Raised when a circuit breaker is open."""
    def __init__(self, key: str, retry_after: float):
        self.key = key
        self.retry_after = retry_after
        super().__init__(f"Circuit open for '{key}', retry after {retry_after:.0f}s")


@dataclass
class _CircuitInfo:
    """Per-key circuit state."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    opened_at: float = 0.0


class CircuitBreaker:
    """
    Per-key circuit breaker.

    Args:
        failure_threshold: Number of consecutive failures to trip open (default: 5)
        cooldown_seconds: Seconds to wait before half-open probe (default: 60)
        success_threshold: Successes in half-open to close circuit (default: 2)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.success_threshold = success_threshold
        self._circuits: Dict[str, _CircuitInfo] = {}
        self._lock = threading.Lock()

    def _get_circuit(self, key: str) -> _CircuitInfo:
        if key not in self._circuits:
            self._circuits[key] = _CircuitInfo()
        return self._circuits[key]

    def allow(self, key: str) -> bool:
        """Check if a request is allowed for this key."""
        with self._lock:
            ci = self._get_circuit(key)

            if ci.state == CircuitState.CLOSED:
                return True

            if ci.state == CircuitState.OPEN:
                elapsed = time.monotonic() - ci.opened_at
                if elapsed >= self.cooldown_seconds:
                    ci.state = CircuitState.HALF_OPEN
                    ci.success_count = 0
                    logger.info("Circuit '%s' -> HALF_OPEN (cooldown elapsed)", key)
                    return True
                return False

            # HALF_OPEN: allow probe
            return True

    def record_success(self, key: str):
        """Record a successful operation."""
        with self._lock:
            ci = self._get_circuit(key)
            ci.last_success_time = time.monotonic()

            if ci.state == CircuitState.HALF_OPEN:
                ci.success_count += 1
                if ci.success_count >= self.success_threshold:
                    ci.state = CircuitState.CLOSED
                    ci.failure_count = 0
                    logger.info("Circuit '%s' -> CLOSED (recovered)", key)
            elif ci.state == CircuitState.CLOSED:
                ci.failure_count = 0  # Reset on success

    def record_failure(self, key: str):
        """Record a failed operation."""
        with self._lock:
            ci = self._get_circuit(key)
            ci.failure_count += 1
            ci.last_failure_time = time.monotonic()

            if ci.state == CircuitState.HALF_OPEN:
                ci.state = CircuitState.OPEN
                ci.opened_at = time.monotonic()
                logger.warning("Circuit '%s' -> OPEN (half-open probe failed)", key)
            elif ci.state == CircuitState.CLOSED:
                if ci.failure_count >= self.failure_threshold:
                    ci.state = CircuitState.OPEN
                    ci.opened_at = time.monotonic()
                    logger.warning(
                        "Circuit '%s' -> OPEN (threshold=%d reached)",
                        key, self.failure_threshold,
                    )

    @contextmanager
    def guard(self, key: str):
        """Context manager that checks the circuit and records result."""
        if not self.allow(key):
            ci = self._circuits.get(key)
            retry_after = self.cooldown_seconds
            if ci:
                elapsed = time.monotonic() - ci.opened_at
                retry_after = max(0, self.cooldown_seconds - elapsed)
            raise CircuitBreakerOpen(key, retry_after)

        try:
            yield
            self.record_success(key)
        except CircuitBreakerOpen:
            raise  # Don't double-record
        except Exception:
            self.record_failure(key)
            raise

    def get_state(self, key: str) -> str:
        """Get the current state of a circuit."""
        with self._lock:
            ci = self._get_circuit(key)
            return ci.state.value

    def get_status(self) -> Dict[str, Any]:
        """Get status of all circuits."""
        with self._lock:
            result = {}
            for key, ci in self._circuits.items():
                result[key] = {
                    'state': ci.state.value,
                    'failure_count': ci.failure_count,
                    'success_count': ci.success_count,
                }
            return result

    def reset(self, key: str = None):
        """Reset a circuit (or all circuits) to CLOSED."""
        with self._lock:
            if key:
                if key in self._circuits:
                    self._circuits[key] = _CircuitInfo()
            else:
                self._circuits.clear()
