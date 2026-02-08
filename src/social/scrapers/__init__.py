"""
Social Media Scrapers Package

Provides scrapers for:
- Reddit (using public JSON API)
- Twitter/X (using Nitter instances)
- Instagram (using public frontends)
"""

from .reddit import RedditHailScraper
from .twitter import TwitterHailScraper
from .instagram import InstagramHailScraper

__all__ = [
    'RedditHailScraper',
    'TwitterHailScraper',
    'InstagramHailScraper',
]
