"""
Twitter/Nitter Hail Scraper - REAL WORKING SCRAPER

Uses Nitter instances (Twitter frontend) to scrape without API keys.
Falls back to multiple Nitter instances for reliability.
"""

import os
import sys
import json
import time
import re
import sqlite3
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger('TwitterHailScraper')

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("BeautifulSoup not available. Install with: pip install beautifulsoup4")


class TwitterHailScraper:
    """
    Scrapes Twitter/X for hail-related posts using Nitter instances.

    Nitter is an open-source Twitter frontend that doesn't require API keys.
    Uses multiple instances for reliability.
    """

    # Public Nitter instances (updated Jan 2026 - these change frequently)
    NITTER_INSTANCES = [
        'https://xcancel.com',           # Most reliable Twitter mirror
        'https://nitter.poast.org',
        'https://nitter.privacydev.net',
        'https://nitter.woodland.cafe',
        'https://nitter.net',
        'https://nitter.1d4.us',
        'https://nitter.kavin.rocks',
        'https://nitter.unixfox.eu',
        'https://nitter.esmailelbob.xyz',
    ]

    # Search queries for hail
    HAIL_QUERIES = [
        'hail damage',
        'hail storm',
        'golf ball hail',
        'baseball hail',
        'hail dents',
        'car hail damage',
        'roof hail damage',
        '#hailstorm',
        '#haildamage',
        '#severeweather hail',
    ]

    # Weather accounts to monitor
    WEATHER_ACCOUNTS = [
        'NWS',
        'NWStornado',
        'spaborman',
        'ReedTimmerAccu',
        'TornadoVideos',
        'StormChasingUSA',
        'WxChasing',
    ]

    def __init__(self, db_path: Optional[str] = None, media_dir: Optional[str] = None):
        self.db_path = db_path or str(PROJECT_ROOT / 'data' / 'social_media.db')
        self.media_dir = Path(media_dir) if media_dir else PROJECT_ROOT / 'data' / 'social_media' / 'twitter'
        self.media_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

        self.working_instance = None
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS twitter_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT UNIQUE,
                username TEXT,
                display_name TEXT,
                content TEXT,
                post_date TEXT,
                scraped_at TEXT,
                url TEXT,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                has_media INTEGER DEFAULT 0,
                media_urls TEXT,
                location_mentioned TEXT,
                hail_size_mentioned TEXT,
                sentiment_score REAL,
                processed INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS twitter_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT,
                media_url TEXT,
                local_path TEXT,
                media_type TEXT,
                downloaded_at TEXT,
                file_hash TEXT,
                FOREIGN KEY (tweet_id) REFERENCES twitter_posts(tweet_id)
            )
        ''')

        conn.commit()
        conn.close()

    def _find_working_instance(self) -> Optional[str]:
        """Find a working Nitter instance."""
        if self.working_instance:
            # Test if still working
            try:
                resp = self.session.get(f"{self.working_instance}/search?q=test", timeout=10)
                if resp.status_code == 200:
                    return self.working_instance
            except:
                pass

        print("  Finding working Nitter instance...")
        for instance in self.NITTER_INSTANCES:
            try:
                resp = self.session.get(f"{instance}/search?q=weather", timeout=10)
                if resp.status_code == 200 and 'timeline' in resp.text.lower():
                    self.working_instance = instance
                    print(f"    Using: {instance}")
                    return instance
            except Exception as e:
                logger.debug(f"Instance {instance} failed: {e}")
                continue

        return None

    def _parse_tweet(self, tweet_element, instance_url: str) -> Optional[Dict]:
        """Parse a tweet element from Nitter HTML."""
        if not BS4_AVAILABLE:
            return None

        try:
            # Get tweet link/ID
            link_elem = tweet_element.select_one('a.tweet-link')
            if not link_elem:
                return None

            tweet_url = link_elem.get('href', '')
            tweet_id = tweet_url.split('/')[-1].split('#')[0] if tweet_url else None

            if not tweet_id:
                return None

            # Username
            username_elem = tweet_element.select_one('a.username')
            username = username_elem.text.strip().lstrip('@') if username_elem else 'unknown'

            # Display name
            name_elem = tweet_element.select_one('a.fullname')
            display_name = name_elem.text.strip() if name_elem else username

            # Content
            content_elem = tweet_element.select_one('div.tweet-content')
            content = content_elem.text.strip() if content_elem else ''

            # Date
            date_elem = tweet_element.select_one('span.tweet-date a')
            post_date = date_elem.get('title', '') if date_elem else ''

            # Stats
            stats = tweet_element.select('span.tweet-stat')
            likes = retweets = replies = 0
            for stat in stats:
                text = stat.text.strip().lower()
                icon = stat.select_one('span.icon-heart, span.icon-retweet, span.icon-comment')
                if icon:
                    class_name = ' '.join(icon.get('class', []))
                    num = re.search(r'(\d+)', text)
                    num = int(num.group(1)) if num else 0
                    if 'heart' in class_name:
                        likes = num
                    elif 'retweet' in class_name:
                        retweets = num
                    elif 'comment' in class_name:
                        replies = num

            # Media
            media_urls = []
            media_elems = tweet_element.select('a.still-image, video source')
            for media in media_elems:
                url = media.get('href') or media.get('src')
                if url:
                    if url.startswith('/'):
                        url = urljoin(instance_url, url)
                    media_urls.append(url)

            # Extract location mentions
            location = self._extract_location(content)

            # Extract hail size mentions
            hail_size = self._extract_hail_size(content)

            return {
                'tweet_id': tweet_id,
                'username': username,
                'display_name': display_name,
                'content': content,
                'post_date': post_date,
                'url': f"https://twitter.com/{username}/status/{tweet_id}",
                'likes': likes,
                'retweets': retweets,
                'replies': replies,
                'has_media': len(media_urls) > 0,
                'media_urls': media_urls,
                'location_mentioned': location,
                'hail_size_mentioned': hail_size,
            }

        except Exception as e:
            logger.error(f"Error parsing tweet: {e}")
            return None

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location mentions from text."""
        # US state patterns
        states = [
            'Texas', 'TX', 'Oklahoma', 'OK', 'Kansas', 'KS', 'Nebraska', 'NE',
            'Colorado', 'CO', 'Missouri', 'MO', 'Iowa', 'IA', 'Arkansas', 'AR',
            'Minnesota', 'MN', 'South Dakota', 'SD', 'North Dakota', 'ND',
            'Wyoming', 'WY', 'Montana', 'MT', 'Illinois', 'IL', 'Indiana', 'IN',
        ]

        cities = [
            'Dallas', 'Houston', 'Austin', 'San Antonio', 'Fort Worth',
            'Oklahoma City', 'Tulsa', 'Norman', 'Denver', 'Boulder',
            'Kansas City', 'Wichita', 'Omaha', 'Lincoln', 'Des Moines',
        ]

        text_upper = text.upper()

        for city in cities:
            if city.upper() in text_upper:
                return city

        for state in states:
            if state.upper() in text_upper:
                return state

        return None

    def _extract_hail_size(self, text: str) -> Optional[str]:
        """Extract hail size mentions from text."""
        text_lower = text.lower()

        sizes = {
            'softball': 'softball (4"+)',
            'grapefruit': 'grapefruit (4")',
            'baseball': 'baseball (2.75")',
            'tennis ball': 'tennis ball (2.5")',
            'golf ball': 'golf ball (1.75")',
            'half dollar': 'half dollar (1.25")',
            'quarter': 'quarter (1")',
            'nickel': 'nickel (0.88")',
            'penny': 'penny (0.75")',
            'marble': 'marble (0.5")',
            'pea': 'pea (0.25")',
        }

        for keyword, size in sizes.items():
            if keyword in text_lower:
                return size

        # Look for inch measurements
        inch_pattern = r'(\d+(?:\.\d+)?)\s*(?:inch|in|")'
        match = re.search(inch_pattern, text_lower)
        if match:
            return f'{match.group(1)}"'

        return None

    def search_hail_tweets(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Search for tweets matching a query.

        Args:
            query: Search query
            max_results: Maximum tweets to fetch

        Returns:
            List of tweet dicts
        """
        if not BS4_AVAILABLE:
            logger.error("BeautifulSoup required for Twitter scraping")
            return []

        instance = self._find_working_instance()
        if not instance:
            logger.error("No working Nitter instance found")
            return []

        tweets = []

        try:
            # Search URL
            search_url = f"{instance}/search?f=tweets&q={requests.utils.quote(query)}"

            resp = self.session.get(search_url, timeout=30)
            if resp.status_code != 200:
                logger.error(f"Search failed: {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find tweet containers
            tweet_elements = soup.select('div.timeline-item, div.tweet-card')

            for elem in tweet_elements[:max_results]:
                tweet = self._parse_tweet(elem, instance)
                if tweet:
                    tweets.append(tweet)

            logger.info(f"Found {len(tweets)} tweets for query: {query}")

        except Exception as e:
            logger.error(f"Error searching tweets: {e}")

        return tweets

    def get_user_tweets(self, username: str, max_results: int = 30) -> List[Dict]:
        """Get recent tweets from a user."""
        if not BS4_AVAILABLE:
            return []

        instance = self._find_working_instance()
        if not instance:
            return []

        tweets = []

        try:
            user_url = f"{instance}/{username}"
            resp = self.session.get(user_url, timeout=30)

            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')
            tweet_elements = soup.select('div.timeline-item, div.tweet-card')

            for elem in tweet_elements[:max_results]:
                tweet = self._parse_tweet(elem, instance)
                if tweet:
                    tweets.append(tweet)

        except Exception as e:
            logger.error(f"Error getting user tweets: {e}")

        return tweets

    def download_media(self, tweet: Dict) -> List[str]:
        """Download media from a tweet."""
        downloaded = []

        for url in tweet.get('media_urls', []):
            try:
                # Get filename
                parsed = urlparse(url)
                filename = os.path.basename(parsed.path)
                if not filename:
                    filename = f"{tweet['tweet_id']}_{len(downloaded)}.jpg"

                local_path = self.media_dir / filename

                if local_path.exists():
                    downloaded.append(str(local_path))
                    continue

                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200:
                    local_path.write_bytes(resp.content)
                    downloaded.append(str(local_path))

                    # Save to DB
                    self._save_media(tweet['tweet_id'], url, str(local_path), resp.content)

                time.sleep(0.5)  # Rate limit

            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")

        return downloaded

    def _save_media(self, tweet_id: str, url: str, local_path: str, content: bytes):
        """Save media record to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        file_hash = hashlib.md5(content).hexdigest()
        media_type = 'image' if any(ext in url.lower() for ext in ['.jpg', '.png', '.gif']) else 'video'

        cursor.execute('''
            INSERT OR IGNORE INTO twitter_media
            (tweet_id, media_url, local_path, media_type, downloaded_at, file_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tweet_id, url, local_path, media_type, datetime.now().isoformat(), file_hash))

        conn.commit()
        conn.close()

    def save_tweet(self, tweet: Dict) -> bool:
        """Save tweet to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO twitter_posts
                (tweet_id, username, display_name, content, post_date, scraped_at,
                 url, likes, retweets, replies, has_media, media_urls,
                 location_mentioned, hail_size_mentioned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tweet['tweet_id'],
                tweet['username'],
                tweet['display_name'],
                tweet['content'],
                tweet['post_date'],
                datetime.now().isoformat(),
                tweet['url'],
                tweet['likes'],
                tweet['retweets'],
                tweet['replies'],
                1 if tweet['has_media'] else 0,
                json.dumps(tweet['media_urls']),
                tweet.get('location_mentioned'),
                tweet.get('hail_size_mentioned'),
            ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error saving tweet: {e}")
            return False
        finally:
            conn.close()

    def scrape_all(self, download_media: bool = True) -> Dict:
        """
        Run full scrape: search queries + weather accounts.

        Returns:
            Dict with scrape statistics
        """
        print("\n" + "=" * 60)
        print("TWITTER/NITTER HAIL SCRAPER")
        print("=" * 60)

        stats = {
            'queries_searched': 0,
            'accounts_checked': 0,
            'tweets_found': 0,
            'tweets_saved': 0,
            'media_downloaded': 0,
            'hail_mentions': 0,
        }

        all_tweets = []

        # Search queries
        print(f"\n[1/2] Searching {len(self.HAIL_QUERIES)} hail queries...")
        for query in self.HAIL_QUERIES:
            print(f"  Searching: '{query}'...")
            tweets = self.search_hail_tweets(query, max_results=20)
            all_tweets.extend(tweets)
            stats['queries_searched'] += 1
            time.sleep(2)  # Rate limit between queries

        # Weather accounts
        print(f"\n[2/2] Checking {len(self.WEATHER_ACCOUNTS)} weather accounts...")
        for account in self.WEATHER_ACCOUNTS:
            print(f"  Checking: @{account}...")
            tweets = self.get_user_tweets(account, max_results=10)
            # Filter for hail-related
            hail_tweets = [t for t in tweets if 'hail' in t.get('content', '').lower()]
            all_tweets.extend(hail_tweets)
            stats['accounts_checked'] += 1
            time.sleep(2)

        # Deduplicate
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet['tweet_id'] not in seen_ids:
                seen_ids.add(tweet['tweet_id'])
                unique_tweets.append(tweet)

        stats['tweets_found'] = len(unique_tweets)

        # Save and download
        print(f"\n[3/3] Saving {len(unique_tweets)} unique tweets...")
        for tweet in unique_tweets:
            if self.save_tweet(tweet):
                stats['tweets_saved'] += 1

                if tweet.get('hail_size_mentioned'):
                    stats['hail_mentions'] += 1

                if download_media and tweet['has_media']:
                    downloaded = self.download_media(tweet)
                    stats['media_downloaded'] += len(downloaded)

        # Summary
        print(f"\n" + "=" * 60)
        print("SCRAPE COMPLETE")
        print("=" * 60)
        print(f"  Queries searched: {stats['queries_searched']}")
        print(f"  Accounts checked: {stats['accounts_checked']}")
        print(f"  Tweets found: {stats['tweets_found']}")
        print(f"  Tweets saved: {stats['tweets_saved']}")
        print(f"  Media downloaded: {stats['media_downloaded']}")
        print(f"  Hail size mentions: {stats['hail_mentions']}")

        return stats


def test_twitter_scraper():
    """Test the Twitter scraper."""
    print("\n" + "=" * 60)
    print("TESTING TWITTER/NITTER SCRAPER")
    print("=" * 60)

    scraper = TwitterHailScraper()

    # Test single search
    print("\n[Test 1] Searching for 'hail damage'...")
    tweets = scraper.search_hail_tweets('hail damage', max_results=5)

    if tweets:
        print(f"  Found {len(tweets)} tweets")
        for i, tweet in enumerate(tweets[:3], 1):
            print(f"\n  Tweet {i}:")
            print(f"    User: @{tweet['username']}")
            print(f"    Content: {tweet['content'][:100]}...")
            print(f"    Likes: {tweet['likes']}, RTs: {tweet['retweets']}")
            if tweet['hail_size_mentioned']:
                print(f"    Hail Size: {tweet['hail_size_mentioned']}")
    else:
        print("  No tweets found (Nitter instances may be down)")

    return tweets


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_twitter_scraper()
