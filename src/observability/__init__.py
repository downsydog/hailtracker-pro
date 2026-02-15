"""
Observability Module

Provides:
  - Structured JSON logging (LOG_FORMAT=json)
  - Health/Ready endpoints
  - Application metrics
"""

from .logging_config import configure_logging
from .health import HealthCheck

__all__ = ['configure_logging', 'HealthCheck']
