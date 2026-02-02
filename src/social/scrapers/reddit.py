"""
Reddit Hail Scraper - REAL WORKING SCRAPER

Uses Reddit's public JSON API (no authentication required for public posts)
Optionally uses PRAW for authenticated access with better rate limits.
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger('RedditHailScraper')

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class RedditHailScraper:
    """
    Scrapes Reddit for hail-related posts and images.

    Uses public JSON API by default (no auth needed).
    Can use PRAW for authenticated access if credentials provided.
    """

    # Subreddits to search
    HAIL_SUBREDDITS = [
        'weather',
        'WeatherPorn',
        'stormchasing',
        'tornado',
        'oklahoma',
        'texas',
        'colorado',
        'kansas',
        'Nebraska',
        'Denver',
        'Austin',
        'Dallas',
        'Houston',
        'hail',
    ]

    # Search terms
    SEARCH_TERMS = [
        'hail',
        'hail damage',
        'hail storm',
        'hailstorm',
        'hail stones',
        'golf ball hail',
        'baseball hail',
        'car hail damage',
    ]

    def __init__(self, db_path: Optional[str] = None, data_dir: Optional[str] = None):
        """Initialize scraper."""
        self.db_path = db_path or str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / 'data' / 'social_media'
        self.images_dir = self.data_dir / 'images' / 'reddit'

        # Create directories
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HailTracker/1.0 (Educational Research Project)'
        })

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # seconds between requests

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25,
                        time_filter: str = 'month') -> List[Dict]:
        """
        Search a subreddit using Reddit's JSON API.

        Args:
            subreddit: Subreddit name
            query: Search query
            limit: Max posts to return
            time_filter: 'hour', 'day', 'week', 'month', 'year', 'all'

        Returns:
            List of post data dicts
        """
        self._rate_limit()

        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            'q': query,
            'restrict_sr': 'on',
            'sort': 'new',
            't': time_filter,
            'limit': min(limit, 100),
        }

        try:
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 429:
                logger.warning("Rate limited, waiting 60 seconds...")
                time.sleep(60)
                return self.search_subreddit(subreddit, query, limit, time_filter)

            if response.status_code != 200:
                logger.error(f"Reddit API error: {response.status_code}")
                return []

            data = response.json()
            posts = []

            for child in data.get('data', {}).get('children', []):
                post = child.get('data', {})
                posts.append({
                    'id': post.get('id'),
                    'title': post.get('title'),
                    'selftext': post.get('selftext', ''),
                    'author': post.get('author'),
                    'subreddit': post.get('subreddit'),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'created_utc': post.get('created_utc'),
                    'url': post.get('url'),
                    'permalink': f"https://reddit.com{post.get('permalink', '')}",
                    'is_video': post.get('is_video', False),
                    'thumbnail': post.get('thumbnail'),
                    'preview': post.get('preview', {}),
                })

            return posts

        except Exception as e:
            logger.error(f"Error searching r/{subreddit}: {e}")
            return []

    def get_image_url(self, post: Dict) -> Optional[str]:
        """Extract best image URL from post."""
        url = post.get('url', '')

        # Direct image links
        if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
            return url

        # Imgur
        if 'imgur.com' in url and not url.endswith('.gifv'):
            if '/a/' not in url and '/gallery/' not in url:
                # Single image
                img_id = url.split('/')[-1].split('.')[0]
                return f"https://i.imgur.com/{img_id}.jpg"

        # Reddit preview images
        preview = post.get('preview', {})
        if preview:
            images = preview.get('images', [])
            if images:
                source = images[0].get('source', {})
                img_url = source.get('url', '').replace('&amp;', '&')
                if img_url:
                    return img_url

        # i.redd.it
        if 'i.redd.it' in url:
            return url

        return None

    def download_image(self, url: str, post_id: str) -> Optional[str]:
        """
        Download image and save locally.

        Returns:
            Local file path or None if failed
        """
        if not url:
            return None

        try:
            self._rate_limit()

            # Determine extension
            parsed = urlparse(url)
            ext = Path(parsed.path).suffix.lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                ext = '.jpg'

            # Create filename from post ID
            filename = f"reddit_{post_id}{ext}"
            filepath = self.images_dir / filename

            # Skip if already downloaded
            if filepath.exists():
                return str(filepath)

            # Download
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded: {filename}")
                return str(filepath)
            else:
                logger.warning(f"Failed to download {url}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    def save_to_database(self, posts: List[Dict]) -> int:
        """
        Save posts to database.

        Returns:
            Number of posts saved
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved = 0
        for post in posts:
            try:
                # Check if already exists
                cursor.execute(
                    "SELECT id FROM social_media_posts WHERE post_id = ?",
                    (f"reddit_{post['id']}",)
                )
                if cursor.fetchone():
                    continue

                # Insert post using existing schema columns
                cursor.execute("""
                    INSERT INTO social_media_posts (
                        platform, post_id, author_username, title, description,
                        post_url, image_url, local_image_path,
                        post_timestamp, scraped_timestamp,
                        likes, comments, location_text,
                        has_image
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'reddit',
                    f"reddit_{post['id']}",
                    post.get('author', 'unknown'),
                    post.get('title', '')[:500],
                    post.get('selftext', '')[:2000],
                    post.get('permalink', ''),
                    post.get('image_url', ''),
                    post.get('local_image_path', ''),
                    datetime.fromtimestamp(post.get('created_utc', 0)).isoformat() if post.get('created_utc') else None,
                    datetime.utcnow().isoformat(),
                    post.get('score', 0),
                    post.get('num_comments', 0),
                    f"r/{post.get('subreddit', '')}",
                    1 if post.get('local_image_path') else 0,
                ))
                saved += 1

            except Exception as e:
                logger.error(f"Error saving post {post.get('id')}: {e}")

        conn.commit()
        conn.close()

        return saved

    def scrape_hail_posts(self, subreddits: List[str] = None,
                         search_terms: List[str] = None,
                         max_posts: int = 50,
                         download_images: bool = True,
                         time_filter: str = 'month') -> Dict:
        """
        Main scraping function.

        Args:
            subreddits: List of subreddits to search (default: HAIL_SUBREDDITS)
            search_terms: Search terms (default: SEARCH_TERMS)
            max_posts: Maximum posts to collect
            download_images: Whether to download images
            time_filter: Time range ('hour', 'day', 'week', 'month', 'year', 'all')

        Returns:
            Dict with scraping results
        """
        subreddits = subreddits or self.HAIL_SUBREDDITS[:5]  # Start with top 5
        search_terms = search_terms or ['hail', 'hail damage']

        all_posts = []
        posts_with_images = []
        images_downloaded = 0

        print(f"\n{'='*60}")
        print(f"REDDIT HAIL SCRAPER - Searching {len(subreddits)} subreddits")
        print(f"{'='*60}")

        for subreddit in subreddits:
            for term in search_terms:
                if len(all_posts) >= max_posts:
                    break

                print(f"\n  Searching r/{subreddit} for '{term}'...")
                posts = self.search_subreddit(subreddit, term,
                                             limit=min(25, max_posts - len(all_posts)),
                                             time_filter=time_filter)

                for post in posts:
                    # Skip duplicates
                    if any(p['id'] == post['id'] for p in all_posts):
                        continue

                    # Get image URL
                    image_url = self.get_image_url(post)
                    post['image_url'] = image_url

                    if image_url and download_images:
                        local_path = self.download_image(image_url, post['id'])
                        post['local_image_path'] = local_path
                        if local_path:
                            images_downloaded += 1
                            posts_with_images.append(post)

                    all_posts.append(post)

                print(f"    Found {len(posts)} posts")

            if len(all_posts) >= max_posts:
                break

        # Save to database
        saved = self.save_to_database(all_posts)

        # Results
        results = {
            'total_posts': len(all_posts),
            'posts_with_images': len(posts_with_images),
            'images_downloaded': images_downloaded,
            'posts_saved_to_db': saved,
            'subreddits_searched': subreddits,
            'sample_posts': all_posts[:5],
        }

        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"  Total posts found: {results['total_posts']}")
        print(f"  Posts with images: {results['posts_with_images']}")
        print(f"  Images downloaded: {results['images_downloaded']}")
        print(f"  Saved to database: {results['posts_saved_to_db']}")

        if results['sample_posts']:
            print(f"\n  Sample posts:")
            for i, post in enumerate(results['sample_posts'][:3], 1):
                title = post.get('title', 'No title')[:60]
                score = post.get('score', 0)
                sub = post.get('subreddit', '?')
                has_img = 'IMG' if post.get('local_image_path') else '---'
                print(f"    {i}. [{has_img}] r/{sub} ({score} pts): {title}...")

        return results


def main():
    """Run the Reddit scraper."""
    import logging
    logging.basicConfig(level=logging.INFO)

    scraper = RedditHailScraper()

    # Scrape with focused subreddits
    results = scraper.scrape_hail_posts(
        subreddits=['weather', 'WeatherPorn', 'stormchasing', 'oklahoma', 'texas'],
        search_terms=['hail', 'hail damage', 'hail storm'],
        max_posts=50,
        download_images=True,
        time_filter='month'
    )

    return results


if __name__ == '__main__':
    results = main()
