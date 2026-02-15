"""
National StormMonitor defaults + environment overrides.

Design intent:
- Works out of the box for nationwide 24/7 monitoring.
- No "tornado alley" special casing.
- Env vars are optional; if absent, we use sane national defaults.
"""

from __future__ import annotations
import os


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default


def national_monitor_defaults() -> dict:
    """
    Return national-cadence defaults, overridable by env vars.

    With 206 active radars and batch=80 / interval=300s:
      ceil(206/80)=3 ticks × 300s = 900s = 15 min full national sweep.

    Env vars (all optional):
      STORM_ENABLE_DF          bool  (default True)
      STORM_MAX_WORKERS        int   (default 24)
      STORM_DISCOVERY_BATCH    int   (default 80)
      STORM_DISCOVERY_INTERVAL int   (default 300)
      STORM_FOCUS_INTERVAL     int   (default 180)
      STORM_TIMEOUT_SECONDS    int   (default 60)
      STORM_MAX_FOCUS_RADARS   int   (default 100)
      STORM_HOT_TTL_SECONDS    int   (default 2400)
    """
    return {
        "enable_discovery_focus": _env_bool("STORM_ENABLE_DF", True),
        "max_workers": _env_int("STORM_MAX_WORKERS", 24),
        "max_discovery_radars_per_tick": _env_int("STORM_DISCOVERY_BATCH", 80),
        "discovery_interval_seconds": _env_int("STORM_DISCOVERY_INTERVAL", 300),
        "focus_interval_seconds": _env_int("STORM_FOCUS_INTERVAL", 180),
        "per_radar_timeout_seconds": _env_int("STORM_TIMEOUT_SECONDS", 60),
        "max_focus_radars": _env_int("STORM_MAX_FOCUS_RADARS", 100),
        "hot_ttl_seconds": _env_int("STORM_HOT_TTL_SECONDS", 2400),
    }
