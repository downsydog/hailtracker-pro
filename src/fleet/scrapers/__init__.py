"""
Fleet Business Scrapers
=======================

Multi-source business discovery for PDR fleet prospecting.
All sources are FREE to use.

Available scrapers:
- YellowPagesScraper: Yellow Pages (yp.com) - service businesses
- GooglePlacesScraper: Google Maps search results
- BBBScraper: Better Business Bureau accredited businesses
- MantaScraper: Manta.com business directory
- BusinessDiscoveryService: Unified discovery using all sources

Utilities:
- GeocodingService: Convert addresses to lat/lon coordinates (Nominatim)
"""

from .base_scraper import BaseScraper
from .yellowpages import YellowPagesScraper
from .google_places import GooglePlacesScraper
from .bbb import BBBScraper
from .manta import MantaScraper
from .geocoding import GeocodingService, geocode_all_businesses
from .discovery import BusinessDiscoveryService, discover_city

__all__ = [
    'BaseScraper',
    'YellowPagesScraper',
    'GooglePlacesScraper',
    'BBBScraper',
    'MantaScraper',
    'GeocodingService',
    'geocode_all_businesses',
    'BusinessDiscoveryService',
    'discover_city',
]
