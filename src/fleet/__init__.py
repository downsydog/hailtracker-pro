"""
Fleet Discovery Module
======================
Multi-source fleet location discovery for PDR prospecting.

Data Sources:
1. OpenStreetMap/Overpass API (FREE) - Buildings, government, schools
2. FMCSA Database (FREE) - Trucking companies with verified fleet sizes
3. Yelp Fusion API (FREE 5K/day) - Service businesses
"""

from .fmcsa import FMCSADatabase
from .yelp_api import YelpFleetAPI
from .discovery_service import FleetDiscoveryService
from .categories import FLEET_CATEGORIES

__all__ = [
    'FMCSADatabase',
    'YelpFleetAPI',
    'FleetDiscoveryService',
    'FLEET_CATEGORIES',
]
