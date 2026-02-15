"""
Safety Rails Module

Provides:
  - CircuitBreaker: per-key failure tracking with open/half-open/closed states
  - Backpressure: queue depth limits
  - Graceful shutdown signal handlers
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from .shutdown import install_shutdown_handlers

__all__ = ['CircuitBreaker', 'CircuitBreakerOpen', 'install_shutdown_handlers']
