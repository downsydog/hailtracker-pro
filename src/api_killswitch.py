"""
API KILL SWITCH
===============
EMERGENCY: All API calls are DISABLED until manually re-enabled.

Set environment variable to re-enable:
    API_CALLS_ENABLED=true

This was added after discovering:
- Google Places: $200+ bill from 104 calls/tile
- Foursquare: 15,060 credits burned
- Potential damage on HERE, TomTom, Yelp

DO NOT ENABLE WITHOUT KYLE'S APPROVAL.
"""

import os
import logging

logger = logging.getLogger('APIKillSwitch')

# KILL SWITCH - Default to DISABLED
_API_CALLS_ENABLED = None

def api_calls_enabled() -> bool:
    """
    Check if API calls are enabled.

    Returns False (DISABLED) unless:
    - Environment variable API_CALLS_ENABLED=true is set

    This is a safety measure after discovering billing issues.
    """
    global _API_CALLS_ENABLED

    if _API_CALLS_ENABLED is None:
        env_value = os.environ.get('API_CALLS_ENABLED', 'false').lower()
        _API_CALLS_ENABLED = env_value == 'true'

        if not _API_CALLS_ENABLED:
            logger.warning("=" * 60)
            logger.warning("API CALLS DISABLED - Kill switch is ON")
            logger.warning("Set API_CALLS_ENABLED=true to enable")
            logger.warning("=" * 60)

    return _API_CALLS_ENABLED


def check_before_api_call(api_name: str) -> bool:
    """
    Call this before ANY API request.
    Returns True if call is allowed, False if blocked.

    Usage:
        from src.api_killswitch import check_before_api_call

        if not check_before_api_call('Google'):
            return []  # Don't make the call
    """
    if not api_calls_enabled():
        logger.warning(f"[BLOCKED] {api_name} API call blocked by kill switch")
        return False
    return True


# For backwards compatibility - can import and call directly
def is_enabled() -> bool:
    return api_calls_enabled()
