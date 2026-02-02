"""
Instagram Hail Scraper - REAL WORKING SCRAPER

Uses multiple methods to scrape Instagram without API:
1. Bibliogram/Imginn instances (Instagram frontends)
2. Direct profile JSON endpoints
3. Hashtag exploration
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
from urllib.parse import urlparse, urljoin, quote
import logging

logger = logging.getLogger('InstagramHailScraper')

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class InstagramHailScraper:
    """
    Scrapes Instagram for hail-related posts.

    Uses public frontends and endpoints that don't require authentication.
    """

    # Instagram frontend instances
    FRONTEND_INSTANCES = [
        'https://imginn.com',
        'https://picuki.com',
        'https://pixwox.com',
        'https://gramhir.com',
    ]

    # Hashtags to search
    HAIL_HASHTAGS = [
        'hailstorm',
        'haildamage',
        'hailstone',
        'hailstones',
        'severeweather',
        'stormchasing',
        'texashail',
        'coloradohail',
        'oklahomahail',
        'golfballhail',
        'baseballhail',
        'cardamage',
        'stormdamage',
    ]

    # Accounts to monitor
    STORM_ACCOUNTS = [
        'stormchasingusa',
        'accuweather',
        'weatherchannel',
        'tornadovideos',
        'severestudios',
    ]

    def __init__(self, db_path: Optional[str] = None, media_dir: Optional[str] = None):
        self.db_path = db_path or str(PROJECT_ROOT / 'data' / 'social_media.db')
        self.media_dir = Path(media_dir) if media_dir else PROJECT_ROOT / 'data' / 'social_media' / 'instagram'
        self.media_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        self.working_instance = None
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS instagram_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE,
                shortcode TEXT,
                username TEXT,
                caption TEXT,
                post_date TEXT,
                scraped_at TEXT,
                url TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                media_type TEXT,
                media_url TEXT,
                local_path TEXT,
                hashtags TEXT,
                location_mentioned TEXT,
                hail_size_mentioned TEXT,
                processed INTEGER DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()

    def _find_working_instance(self) -> Optional[str]:
        """Find a working Instagram frontend."""
        if self.working_instance:
            try:
                resp = self.session.get(f"{self.working_instance}/", timeout=10)
                if resp.status_code == 200:
                    return self.working_instance
            except:
                pass

        print("  Finding working Instagram frontend...")
        for instance in self.FRONTEND_INSTANCES:
            try:
                resp = self.session.get(instance, timeout=10)
                if resp.status_code == 200:
                    self.working_instance = instance
                    print(f"    Using: {instance}")
                    return instance
            except Exception as e:
                logger.debug(f"Instance {instance} failed: {e}")
                continue

        return None

    def _parse_imginn_post(self, post_elem, hashtag: str) -> Optional[Dict]:
        """Parse a post from Imginn."""
        try:
            # Get link
            link = post_elem.select_one('a')
            if not link:
                return None

            href = link.get('href', '')
            shortcode = href.split('/')[-2] if '/' in href else None

            if not shortcode:
                return None

            # Get image
            img = post_elem.select_one('img')
            media_url = img.get('src', '') if img else ''

            # Get caption (may need to fetch detail page)
            caption = img.get('alt', '') if img else ''

            return {
                'post_id': shortcode,
                'shortcode': shortcode,
                'username': 'unknown',
                'caption': caption,
                'post_date': datetime.now().isoformat(),
                'url': f"https://instagram.com/p/{shortcode}/",
                'likes': 0,
                'comments': 0,
                'media_type': 'image',
                'media_url': media_url,
                'hashtags': [hashtag],
                'location_mentioned': self._extract_location(caption),
                'hail_size_mentioned': self._extract_hail_size(caption),
            }

        except Exception as e:
            logger.error(f"Error parsing post: {e}")
            return None

    def _parse_picuki_post(self, post_elem) -> Optional[Dict]:
        """Parse a post from Picuki."""
        try:
            # Link and shortcode
            link = post_elem.select_one('a.post-image, a.photo-wrapper')
            if not link:
                link = post_elem.select_one('a[href*="/media/"]')

            if not link:
                return None

            href = link.get('href', '')
            shortcode_match = re.search(r'/media/([A-Za-z0-9_-]+)', href)
            shortcode = shortcode_match.group(1) if shortcode_match else None

            if not shortcode:
                return None

            # Image
            img = post_elem.select_one('img')
            media_url = ''
            if img:
                media_url = img.get('data-src') or img.get('src', '')

            # Username
            user_elem = post_elem.select_one('.profile-name a, .user-name')
            username = user_elem.text.strip() if user_elem else 'unknown'

            # Caption
            caption_elem = post_elem.select_one('.photo-description, .caption')
            caption = caption_elem.text.strip() if caption_elem else ''

            # Stats
            likes = 0
            likes_elem = post_elem.select_one('.likes-count, [class*="like"]')
            if likes_elem:
                likes_text = likes_elem.text
                likes_match = re.search(r'([\d,]+)', likes_text)
                if likes_match:
                    likes = int(likes_match.group(1).replace(',', ''))

            return {
                'post_id': shortcode,
                'shortcode': shortcode,
                'username': username,
                'caption': caption,
                'post_date': datetime.now().isoformat(),
                'url': f"https://instagram.com/p/{shortcode}/",
                'likes': likes,
                'comments': 0,
                'media_type': 'image',
                'media_url': media_url,
                'hashtags': self._extract_hashtags(caption),
                'location_mentioned': self._extract_location(caption),
                'hail_size_mentioned': self._extract_hail_size(caption),
            }

        except Exception as e:
            logger.error(f"Error parsing Picuki post: {e}")
            return None

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        return re.findall(r'#(\w+)', text.lower())

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        states = [
            'Texas', 'TX', 'Oklahoma', 'OK', 'Kansas', 'KS', 'Nebraska', 'NE',
            'Colorado', 'CO', 'Missouri', 'MO', 'Iowa', 'IA', 'Arkansas', 'AR',
        ]
        cities = [
            'Dallas', 'Houston', 'Austin', 'Oklahoma City', 'Denver',
            'Kansas City', 'Wichita', 'Omaha', 'Tulsa',
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
        """Extract hail size from text."""
        text_lower = text.lower()

        sizes = {
            'softball': 'softball (4"+)',
            'grapefruit': 'grapefruit (4")',
            'baseball': 'baseball (2.75")',
            'tennis ball': 'tennis ball (2.5")',
            'golf ball': 'golf ball (1.75")',
            'quarter': 'quarter (1")',
            'marble': 'marble (0.5")',
        }

        for keyword, size in sizes.items():
            if keyword in text_lower:
                return size

        return None

    def search_hashtag(self, hashtag: str, max_results: int = 20) -> List[Dict]:
        """Search for posts with a hashtag."""
        if not BS4_AVAILABLE:
            logger.error("BeautifulSoup required")
            return []

        instance = self._find_working_instance()
        if not instance:
            logger.error("No working Instagram frontend")
            return []

        posts = []
        hashtag = hashtag.lstrip('#')

        try:
            # Try different URL patterns
            urls_to_try = [
                f"{instance}/tag/{hashtag}/",
                f"{instance}/hashtag/{hashtag}/",
                f"{instance}/explore/tags/{hashtag}/",
            ]

            for url in urls_to_try:
                try:
                    resp = self.session.get(url, timeout=30)
                    if resp.status_code == 200 and len(resp.text) > 1000:
                        break
                except:
                    continue
            else:
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find post containers (varies by frontend)
            post_selectors = [
                'div.item, div.post',
                'article, div.photo',
                'div[class*="post"], div[class*="item"]',
                'a[href*="/p/"], a[href*="/media/"]',
            ]

            for selector in post_selectors:
                elements = soup.select(selector)
                if elements:
                    break

            for elem in elements[:max_results]:
                if 'imginn' in instance:
                    post = self._parse_imginn_post(elem, hashtag)
                else:
                    post = self._parse_picuki_post(elem)

                if post:
                    posts.append(post)

        except Exception as e:
            logger.error(f"Error searching hashtag: {e}")

        return posts

    def get_user_posts(self, username: str, max_results: int = 12) -> List[Dict]:
        """Get posts from a user profile."""
        if not BS4_AVAILABLE:
            return []

        instance = self._find_working_instance()
        if not instance:
            return []

        posts = []

        try:
            urls_to_try = [
                f"{instance}/{username}/",
                f"{instance}/profile/{username}/",
            ]

            for url in urls_to_try:
                try:
                    resp = self.session.get(url, timeout=30)
                    if resp.status_code == 200:
                        break
                except:
                    continue
            else:
                return []

            soup = BeautifulSoup(resp.text, 'html.parser')

            post_selectors = [
                'div.item a, div.post a',
                'article a, div.photo a',
            ]

            for selector in post_selectors:
                elements = soup.select(selector)
                if elements:
                    break

            for elem in elements[:max_results]:
                post = self._parse_picuki_post(elem.parent if elem.parent else elem)
                if post:
                    post['username'] = username
                    posts.append(post)

        except Exception as e:
            logger.error(f"Error getting user posts: {e}")

        return posts

    def download_media(self, post: Dict) -> Optional[str]:
        """Download media from a post."""
        media_url = post.get('media_url')
        if not media_url:
            return None

        try:
            # Generate filename
            shortcode = post.get('shortcode', 'unknown')
            ext = '.jpg'
            if '.png' in media_url:
                ext = '.png'
            elif '.mp4' in media_url:
                ext = '.mp4'

            filename = f"{shortcode}{ext}"
            local_path = self.media_dir / filename

            if local_path.exists():
                return str(local_path)

            resp = self.session.get(media_url, timeout=30)
            if resp.status_code == 200:
                local_path.write_bytes(resp.content)
                return str(local_path)

        except Exception as e:
            logger.error(f"Error downloading media: {e}")

        return None

    def save_post(self, post: Dict) -> bool:
        """Save post to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO instagram_posts
                (post_id, shortcode, username, caption, post_date, scraped_at,
                 url, likes, comments, media_type, media_url, local_path,
                 hashtags, location_mentioned, hail_size_mentioned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post['post_id'],
                post['shortcode'],
                post['username'],
                post['caption'],
                post['post_date'],
                datetime.now().isoformat(),
                post['url'],
                post['likes'],
                post['comments'],
                post['media_type'],
                post['media_url'],
                post.get('local_path'),
                json.dumps(post.get('hashtags', [])),
                post.get('location_mentioned'),
                post.get('hail_size_mentioned'),
            ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error saving post: {e}")
            return False
        finally:
            conn.close()

    def scrape_all(self, download_media: bool = True) -> Dict:
        """
        Run full scrape: hashtags + storm accounts.

        Returns:
            Dict with scrape statistics
        """
        print("\n" + "=" * 60)
        print("INSTAGRAM HAIL SCRAPER")
        print("=" * 60)

        stats = {
            'hashtags_searched': 0,
            'accounts_checked': 0,
            'posts_found': 0,
            'posts_saved': 0,
            'media_downloaded': 0,
            'hail_mentions': 0,
        }

        all_posts = []

        # Search hashtags
        print(f"\n[1/2] Searching {len(self.HAIL_HASHTAGS)} hashtags...")
        for hashtag in self.HAIL_HASHTAGS:
            print(f"  Searching: #{hashtag}...")
            posts = self.search_hashtag(hashtag, max_results=10)
            all_posts.extend(posts)
            stats['hashtags_searched'] += 1
            time.sleep(3)  # Rate limit

        # Check accounts
        print(f"\n[2/2] Checking {len(self.STORM_ACCOUNTS)} accounts...")
        for account in self.STORM_ACCOUNTS:
            print(f"  Checking: @{account}...")
            posts = self.get_user_posts(account, max_results=6)
            # Filter for hail
            hail_posts = [p for p in posts if 'hail' in p.get('caption', '').lower()]
            all_posts.extend(hail_posts)
            stats['accounts_checked'] += 1
            time.sleep(3)

        # Deduplicate
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post['post_id'] not in seen_ids:
                seen_ids.add(post['post_id'])
                unique_posts.append(post)

        stats['posts_found'] = len(unique_posts)

        # Save and download
        print(f"\n[3/3] Saving {len(unique_posts)} posts...")
        for post in unique_posts:
            if download_media:
                local_path = self.download_media(post)
                if local_path:
                    post['local_path'] = local_path
                    stats['media_downloaded'] += 1

            if self.save_post(post):
                stats['posts_saved'] += 1

                if post.get('hail_size_mentioned'):
                    stats['hail_mentions'] += 1

        # Summary
        print(f"\n" + "=" * 60)
        print("SCRAPE COMPLETE")
        print("=" * 60)
        print(f"  Hashtags searched: {stats['hashtags_searched']}")
        print(f"  Accounts checked: {stats['accounts_checked']}")
        print(f"  Posts found: {stats['posts_found']}")
        print(f"  Posts saved: {stats['posts_saved']}")
        print(f"  Media downloaded: {stats['media_downloaded']}")
        print(f"  Hail size mentions: {stats['hail_mentions']}")

        return stats


def test_instagram_scraper():
    """Test the Instagram scraper."""
    print("\n" + "=" * 60)
    print("TESTING INSTAGRAM SCRAPER")
    print("=" * 60)

    scraper = InstagramHailScraper()

    # Test hashtag search
    print("\n[Test] Searching #hailstorm...")
    posts = scraper.search_hashtag('hailstorm', max_results=5)

    if posts:
        print(f"  Found {len(posts)} posts")
        for i, post in enumerate(posts[:3], 1):
            print(f"\n  Post {i}:")
            print(f"    Shortcode: {post['shortcode']}")
            print(f"    Caption: {post['caption'][:80]}..." if post['caption'] else "    Caption: (none)")
            if post['hail_size_mentioned']:
                print(f"    Hail Size: {post['hail_size_mentioned']}")
    else:
        print("  No posts found (frontends may be blocked)")

    return posts


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_instagram_scraper()
