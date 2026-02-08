"""
Unified Social Media Scraper

Combines all social media sources into a single interface:
- Reddit
- Twitter/X (via Nitter proxies)
- YouTube (via RSS/API)
- Instagram (limited)

Supports multi-language content (EN, FR, ES).
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json
import re
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.social.reddit import RedditScraper, RedditPost

logger = logging.getLogger('UnifiedSocialScraper')


@dataclass
class SocialPost:
    """Unified social media post."""
    platform: str
    post_id: str
    url: str
    author: str
    timestamp: datetime
    title: str
    content: str
    language: str

    # Media
    has_image: bool = False
    has_video: bool = False
    media_urls: List[str] = field(default_factory=list)

    # Location
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: Optional[str] = None
    state_province: Optional[str] = None

    # Hail data
    hail_mentioned: bool = False
    hail_size_text: Optional[str] = None
    hail_size_inches: Optional[float] = None

    # Engagement
    likes: int = 0
    shares: int = 0
    comments: int = 0
    views: int = 0

    # Analysis
    relevance_score: float = 0.0
    authenticity_score: float = 0.0
    is_verified: bool = False


class UnifiedSocialScraper:
    """
    Unified interface for all social media scraping.
    """

    def __init__(self, data_dir: str = None, db_path: str = None):
        """
        Initialize unified scraper.

        Args:
            data_dir: Directory for storing scraped data
            db_path: Path to database for storing results
        """
        self.data_dir = Path(data_dir) if data_dir else Path('data/social')
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path or str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')

        # Initialize platform scrapers
        self.reddit = RedditScraper(data_dir=str(self.data_dir / 'reddit'))

        # Statistics
        self.stats = {
            'total_scraped': 0,
            'reddit_posts': 0,
            'twitter_posts': 0,
            'youtube_posts': 0,
            'instagram_posts': 0,
            'with_location': 0,
            'with_hail_size': 0,
            'by_language': {'en': 0, 'fr': 0, 'es': 0}
        }

    def scrape_for_event(
        self,
        lat: float,
        lon: float,
        event_time: datetime,
        radius_km: float = 100,
        time_window_hours: int = 48
    ) -> List[SocialPost]:
        """
        Scrape social media for posts related to a hail event.

        Args:
            lat: Event latitude
            lon: Event longitude
            event_time: Time of event
            radius_km: Search radius
            time_window_hours: Time window around event

        Returns:
            List of relevant SocialPost objects
        """
        all_posts = []

        # Determine relevant locations/regions
        locations = self._get_relevant_locations(lat, lon)

        # Scrape Reddit
        logger.info(f"Scraping Reddit for event at ({lat:.2f}, {lon:.2f})")
        reddit_posts = self._scrape_reddit_for_event(
            locations, event_time, time_window_hours
        )
        all_posts.extend(reddit_posts)

        # Filter by relevance and approximate location
        filtered = self._filter_by_proximity(all_posts, lat, lon, radius_km)

        # Sort by relevance
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)

        return filtered

    def scrape_recent(
        self,
        time_filter: str = 'day',
        platforms: List[str] = None,
        languages: List[str] = None
    ) -> List[SocialPost]:
        """
        Scrape recent hail-related posts from all platforms.

        Args:
            time_filter: 'hour', 'day', 'week'
            platforms: List of platforms to scrape (default: all)
            languages: Language filter (default: all)

        Returns:
            List of SocialPost objects
        """
        if platforms is None:
            platforms = ['reddit']  # Add more as implemented
        if languages is None:
            languages = ['en', 'fr', 'es']

        all_posts = []

        if 'reddit' in platforms:
            logger.info("Scraping Reddit for recent hail posts...")
            reddit_posts = self.reddit.scrape_all_subreddits(
                time_filter=time_filter,
                limit_per_sub=25,
                priority_max=2  # Only top priority subreddits
            )

            for rp in reddit_posts:
                if rp.language in languages:
                    all_posts.append(self._convert_reddit_post(rp))

        self._update_stats(all_posts)
        return all_posts

    def _scrape_reddit_for_event(
        self,
        locations: List[str],
        event_time: datetime,
        time_window_hours: int
    ) -> List[SocialPost]:
        """Scrape Reddit for event-specific posts."""
        posts = []

        # Search in relevant subreddits
        relevant_subs = ['weather', 'stormchasing']

        # Add location-specific subreddits
        for loc in locations:
            loc_lower = loc.lower()
            if loc_lower in self.reddit.SUBREDDITS:
                relevant_subs.append(loc_lower)

        for subreddit in relevant_subs:
            try:
                # Build query with location and time
                query_parts = ['hail', 'hailstorm']
                query_parts.extend(locations)
                query = ' OR '.join(query_parts)

                reddit_posts = self.reddit.search_subreddit(
                    subreddit,
                    query=query,
                    time_filter='week',
                    limit=50
                )

                for rp in reddit_posts:
                    # Filter by time window
                    time_diff = abs((rp.created_utc - event_time).total_seconds() / 3600)
                    if time_diff <= time_window_hours:
                        posts.append(self._convert_reddit_post(rp))

            except Exception as e:
                logger.error(f"Error scraping r/{subreddit}: {e}")

        return posts

    def _convert_reddit_post(self, rp: RedditPost) -> SocialPost:
        """Convert RedditPost to unified SocialPost."""
        return SocialPost(
            platform='reddit',
            post_id=rp.post_id,
            url=rp.permalink,
            author=rp.author,
            timestamp=rp.created_utc,
            title=rp.title,
            content=rp.selftext,
            language=rp.language,
            has_image=rp.is_image,
            has_video=rp.is_video,
            media_urls=[rp.media_url] if rp.media_url else [],
            location_text=rp.location_text,
            hail_mentioned=rp.relevance_score > 0,
            hail_size_text=rp.hail_size_mentioned,
            hail_size_inches=rp.hail_size_inches,
            likes=rp.score,
            comments=rp.num_comments,
            relevance_score=rp.relevance_score
        )

    def _get_relevant_locations(self, lat: float, lon: float) -> List[str]:
        """Get relevant location names for a coordinate."""
        locations = []

        # Simple coordinate-to-location mapping for key areas
        # In production, use reverse geocoding
        location_grid = {
            # US - Tornado Alley
            (35.5, -97.5): ['Oklahoma', 'OKC', 'oklahoma city'],
            (32.8, -96.8): ['Dallas', 'Texas', 'DFW'],
            (29.8, -95.4): ['Houston', 'Texas'],
            (39.7, -105.0): ['Denver', 'Colorado'],
            (37.7, -100.0): ['Kansas', 'Dodge City'],
            (39.4, -101.7): ['Goodland', 'Kansas'],
            (35.2, -101.8): ['Amarillo', 'Texas'],
            (41.2, -96.0): ['Omaha', 'Nebraska'],

            # Canada
            (51.0, -114.1): ['Calgary', 'Alberta'],
            (53.5, -113.5): ['Edmonton', 'Alberta'],
            (49.9, -97.1): ['Winnipeg', 'Manitoba'],

            # Mexico
            (25.7, -100.3): ['Monterrey', 'Nuevo Leon'],
            (20.7, -103.3): ['Guadalajara', 'Jalisco'],
            (19.4, -99.1): ['Mexico City', 'CDMX'],
        }

        # Find nearest location
        min_dist = float('inf')
        nearest = None

        for (loc_lat, loc_lon), names in location_grid.items():
            dist = ((lat - loc_lat) ** 2 + (lon - loc_lon) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                nearest = names

        if nearest and min_dist < 3:  # Within ~300km
            locations.extend(nearest)

        return locations

    def _filter_by_proximity(
        self,
        posts: List[SocialPost],
        lat: float,
        lon: float,
        radius_km: float
    ) -> List[SocialPost]:
        """Filter posts by approximate proximity to location."""
        # This is approximate since we don't have exact coordinates for posts
        # In production, would use geocoding
        filtered = []

        for post in posts:
            # If post has coordinates, check distance
            if post.latitude and post.longitude:
                dist = 111 * ((post.latitude - lat) ** 2 +
                             ((post.longitude - lon) * 0.85) ** 2) ** 0.5
                if dist <= radius_km:
                    filtered.append(post)
            # Otherwise, include if has relevant location text
            elif post.location_text:
                filtered.append(post)
            # Include high-relevance posts without location
            elif post.relevance_score >= 0.7:
                filtered.append(post)

        return filtered

    def _update_stats(self, posts: List[SocialPost]):
        """Update scraping statistics."""
        for post in posts:
            self.stats['total_scraped'] += 1
            self.stats[f'{post.platform}_posts'] += 1

            if post.location_text or post.latitude:
                self.stats['with_location'] += 1
            if post.hail_size_inches:
                self.stats['with_hail_size'] += 1
            if post.language in self.stats['by_language']:
                self.stats['by_language'][post.language] += 1

    def store_in_database(self, posts: List[SocialPost]) -> int:
        """
        Store social posts in database.

        Args:
            posts: List of posts to store

        Returns:
            Number of posts stored
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stored = 0
        for post in posts:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO social_media_posts (
                        platform, post_url, post_id, author_username,
                        post_timestamp, scraped_timestamp,
                        latitude, longitude, location_text,
                        country, state_province,
                        title, description, language,
                        has_image, has_video, image_url,
                        hail_size_estimate_inches,
                        likes, shares, comments, views,
                        authenticity_score, is_verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post.platform,
                    post.url,
                    post.post_id,
                    post.author,
                    post.timestamp.isoformat(),
                    datetime.utcnow().isoformat(),
                    post.latitude,
                    post.longitude,
                    post.location_text,
                    post.country,
                    post.state_province,
                    post.title,
                    post.content[:1000] if post.content else None,
                    post.language,
                    post.has_image,
                    post.has_video,
                    post.media_urls[0] if post.media_urls else None,
                    post.hail_size_inches,
                    post.likes,
                    post.shares,
                    post.comments,
                    post.views,
                    post.authenticity_score,
                    post.is_verified
                ))
                stored += 1

            except Exception as e:
                logger.error(f"Error storing post {post.post_id}: {e}")

        conn.commit()
        conn.close()

        return stored

    def save_to_json(self, posts: List[SocialPost], filename: str = None) -> str:
        """Save posts to JSON file."""
        if not filename:
            filename = f"social_posts_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = self.data_dir / filename

        data = []
        for post in posts:
            data.append({
                'platform': post.platform,
                'post_id': post.post_id,
                'url': post.url,
                'author': post.author,
                'timestamp': post.timestamp.isoformat(),
                'title': post.title,
                'content': post.content[:500],
                'language': post.language,
                'has_image': post.has_image,
                'has_video': post.has_video,
                'media_urls': post.media_urls,
                'location_text': post.location_text,
                'latitude': post.latitude,
                'longitude': post.longitude,
                'hail_size_inches': post.hail_size_inches,
                'likes': post.likes,
                'relevance_score': post.relevance_score
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def get_stats(self) -> Dict:
        """Get scraping statistics."""
        return self.stats.copy()


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("UNIFIED SOCIAL SCRAPER TEST")
    print("=" * 60)

    scraper = UnifiedSocialScraper(data_dir='data/test_social')

    # Test scraping recent posts
    print("\nScraping recent hail posts...")
    posts = scraper.scrape_recent(time_filter='week')

    print(f"\nFound {len(posts)} relevant posts:")
    for post in posts[:10]:
        print(f"\n  [{post.platform}] {post.title[:50]}...")
        print(f"      {post.timestamp} | Relevance: {post.relevance_score:.2f}")
        if post.location_text:
            print(f"      Location: {post.location_text}")
        if post.hail_size_inches:
            print(f"      Hail: {post.hail_size_inches}\"")
        if post.has_image:
            print(f"      Has image")

    # Show stats
    print("\n" + "=" * 60)
    print("SCRAPING STATISTICS")
    print("=" * 60)
    stats = scraper.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Save results
    if posts:
        path = scraper.save_to_json(posts)
        print(f"\nSaved to: {path}")

    print("\nUnified social scraper ready!")
