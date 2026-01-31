"""
Multi-API Fleet Business Discovery
==================================
API clients for discovering fleet-relevant businesses.

Free Tier Limits:
- Foursquare: 100,000 calls/month
- Yelp: 5,000 calls/day (150,000/month)
- HERE: 250,000 calls/month
- TomTom: 2,500 calls/day (75,000/month)
- Google Places: $200/month credit

Recommended usage:
- Primary: OSM (unlimited), Foursquare, Yelp
- Secondary: HERE, TomTom
- Expensive: Google (use sparingly)
"""

from .yelp_api import YelpAPI
from .here_api import HereAPI
from .tomtom_api import TomTomAPI
from .google_places_api import GooglePlacesAPI

__all__ = ['YelpAPI', 'HereAPI', 'TomTomAPI', 'GooglePlacesAPI']
