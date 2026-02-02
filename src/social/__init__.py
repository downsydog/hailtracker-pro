"""
HailTracker Pro - Social Media Module

Multi-language social media scraping for hail verification:
- Reddit (weather/storm subreddits)
- Twitter/X (via Nitter)
- YouTube (storm chaser videos)
- Instagram (hail photos)

Supports: English, French, Spanish
"""

from .reddit import RedditScraper
from .unified import UnifiedSocialScraper

__all__ = [
    'RedditScraper',
    'UnifiedSocialScraper',
]
