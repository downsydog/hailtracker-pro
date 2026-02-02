"""
Instagram Alternative Scraper - Multiple Methods

Uses multiple fallback methods to find Instagram content:
1. Web search for Instagram posts
2. Bibliogram/alternative frontends
3. Instagram embed/oembed API
4. Google image search for Instagram content
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
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote, urlparse
import logging

logger = logging.getLogger('InstagramAltScraper')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class InstagramAlternativeScraper:
    """
    Alternative Instagram scraper using multiple methods.
    """

    # Instagram oembed API (works for public posts)
    OEMBED_API = 'https://api.instagram.com/oembed'

    # Alternative frontends to try
    FRONTENDS = [
        'https://imginn.com',
        'https://picuki.com',
        'https://gramhir.com',
        'https://dumpoir.com',
        'https://pixwox.com',
        'https://instanavigation.com',
    ]

    # Search terms
    HAIL_HASHTAGS = [
        'hailstorm',
        'haildamage',
        'golfballhail',
        'severeweather',
        'stormchasing',
    ]

    def __init__(self, db_path: Optional[str] = None, media_dir: Optional[str] = None):
        self.db_path = db_path or str(PROJECT_ROOT / 'data' / 'social_media.db')
        self.media_dir = Path(media_dir) if media_dir else PROJECT_ROOT / 'data' / 'social_media' / 'instagram'
        self.media_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })

        self._init_db()

    def _init_db(self):
        """Initialize database."""
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
                method TEXT,
                media_url TEXT,
                local_path TEXT,
                hashtags TEXT,
                hail_size_mentioned TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _extract_hail_size(self, text: str) -> Optional[str]:
        """Extract hail size from text."""
        if not text:
            return None
        text_lower = text.lower()
        sizes = {
            'softball': 'softball (4"+)',
            'baseball': 'baseball (2.75")',
            'tennis ball': 'tennis ball (2.5")',
            'golf ball': 'golf ball (1.75")',
            'quarter': 'quarter (1")',
        }
        for keyword, size in sizes.items():
            if keyword in text_lower:
                return size
        return None

    def get_post_via_oembed(self, post_url: str) -> Optional[Dict]:
        """
        Get post data via Instagram's oembed API.
        Works for public posts without authentication.
        """
        try:
            # Clean URL
            if not post_url.startswith('http'):
                post_url = f"https://instagram.com/p/{post_url}/"

            api_url = f"{self.OEMBED_API}?url={quote(post_url)}"

            resp = self.session.get(api_url, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()

            # Extract shortcode from URL
            shortcode = post_url.split('/p/')[-1].split('/')[0] if '/p/' in post_url else None

            return {
                'post_id': shortcode,
                'shortcode': shortcode,
                'username': data.get('author_name', 'unknown'),
                'caption': data.get('title', ''),
                'post_date': '',
                'url': post_url,
                'method': 'oembed',
                'media_url': data.get('thumbnail_url', ''),
                'hashtags': re.findall(r'#(\w+)', data.get('title', '')),
                'hail_size_mentioned': self._extract_hail_size(data.get('title', '')),
            }

        except Exception as e:
            logger.debug(f"Oembed error: {e}")
            return None

    def search_via_web(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Search for Instagram posts via web search engines.
        """
        posts = []

        try:
            # DuckDuckGo search
            search_query = f"site:instagram.com {query}"
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote(search_query)}"

            resp = self.session.get(ddg_url, timeout=15)
            if resp.status_code != 200:
                return posts

            if not BS4_AVAILABLE:
                return posts

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find Instagram links
            results = soup.select('a.result__url')

            for result in results[:max_results]:
                url = result.get('href', '')

                # Look for post URLs
                if 'instagram.com/p/' in url:
                    match = re.search(r'/p/([A-Za-z0-9_-]+)', url)
                    if match:
                        shortcode = match.group(1)

                        # Get snippet
                        parent = result.find_parent('div', class_='result')
                        caption = ''
                        if parent:
                            snippet = parent.select_one('.result__snippet')
                            if snippet:
                                caption = snippet.text.strip()

                        posts.append({
                            'post_id': shortcode,
                            'shortcode': shortcode,
                            'username': 'unknown',
                            'caption': caption,
                            'post_date': '',
                            'url': f"https://instagram.com/p/{shortcode}/",
                            'method': 'web_search',
                            'media_url': '',
                            'hashtags': re.findall(r'#(\w+)', caption),
                            'hail_size_mentioned': self._extract_hail_size(caption),
                        })

            if posts:
                print(f"    [WebSearch] Found {len(posts)} Instagram posts")

        except Exception as e:
            logger.debug(f"Web search error: {e}")

        return posts

    def search_via_google_images(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search Google Images for Instagram hail content.
        """
        posts = []

        try:
            # Search for Instagram content on Google Images
            search_query = f"site:instagram.com {query}"
            # Using DuckDuckGo images as fallback
            url = f"https://duckduckgo.com/?q={quote(search_query)}&iax=images&ia=images"

            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return posts

            # Extract vqd token
            vqd_match = re.search(r'vqd=([^&]+)', resp.text)
            if not vqd_match:
                return posts

            vqd = vqd_match.group(1)

            # Get images
            img_url = f"https://duckduckgo.com/i.js?q={quote(search_query)}&vqd={vqd}"
            resp = self.session.get(img_url, timeout=15)

            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])

                for r in results[:max_results]:
                    source_url = r.get('url', '')
                    if 'instagram.com' in source_url:
                        # Extract shortcode
                        match = re.search(r'/p/([A-Za-z0-9_-]+)', source_url)
                        if match:
                            shortcode = match.group(1)
                            posts.append({
                                'post_id': shortcode,
                                'shortcode': shortcode,
                                'username': 'unknown',
                                'caption': r.get('title', ''),
                                'post_date': '',
                                'url': f"https://instagram.com/p/{shortcode}/",
                                'method': 'image_search',
                                'media_url': r.get('image', ''),
                                'hashtags': [],
                                'hail_size_mentioned': self._extract_hail_size(r.get('title', '')),
                            })

                if posts:
                    print(f"    [ImageSearch] Found {len(posts)} Instagram images")

        except Exception as e:
            logger.debug(f"Image search error: {e}")

        return posts

    def try_frontends(self, hashtag: str, max_results: int = 10) -> List[Dict]:
        """
        Try multiple Instagram frontends.
        """
        posts = []

        for frontend in self.FRONTENDS:
            try:
                urls_to_try = [
                    f"{frontend}/tag/{hashtag}/",
                    f"{frontend}/hashtag/{hashtag}/",
                    f"{frontend}/explore/tags/{hashtag}/",
                ]

                for url in urls_to_try:
                    resp = self.session.get(url, timeout=10)
                    if resp.status_code == 200 and len(resp.text) > 5000:
                        if not BS4_AVAILABLE:
                            continue

                        soup = BeautifulSoup(resp.text, 'html.parser')

                        # Find post links
                        links = soup.select('a[href*="/p/"], a[href*="/media/"]')

                        for link in links[:max_results]:
                            href = link.get('href', '')
                            match = re.search(r'/(?:p|media)/([A-Za-z0-9_-]+)', href)
                            if match:
                                shortcode = match.group(1)

                                # Get image
                                img = link.select_one('img')
                                media_url = img.get('src', '') if img else ''
                                caption = img.get('alt', '') if img else ''

                                posts.append({
                                    'post_id': shortcode,
                                    'shortcode': shortcode,
                                    'username': 'unknown',
                                    'caption': caption,
                                    'post_date': '',
                                    'url': f"https://instagram.com/p/{shortcode}/",
                                    'method': f'frontend:{frontend.split("//")[1].split("/")[0]}',
                                    'media_url': media_url,
                                    'hashtags': [hashtag],
                                    'hail_size_mentioned': self._extract_hail_size(caption),
                                })

                        if posts:
                            print(f"    [Frontend] {frontend}: Found {len(posts)} posts")
                            return posts

            except Exception as e:
                logger.debug(f"Frontend {frontend} error: {e}")
                continue

        return posts

    def download_media(self, post: Dict) -> Optional[str]:
        """Download media from post."""
        media_url = post.get('media_url')
        if not media_url:
            return None

        try:
            shortcode = post.get('shortcode', 'unknown')
            ext = '.jpg'
            filename = f"{shortcode}{ext}"
            local_path = self.media_dir / filename

            if local_path.exists():
                return str(local_path)

            resp = self.session.get(media_url, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 1000:
                local_path.write_bytes(resp.content)
                return str(local_path)

        except Exception as e:
            logger.debug(f"Download error: {e}")

        return None

    def save_post(self, post: Dict) -> bool:
        """Save post to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO instagram_posts
                (post_id, shortcode, username, caption, post_date, scraped_at,
                 url, method, media_url, local_path, hashtags, hail_size_mentioned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post['post_id'],
                post['shortcode'],
                post['username'],
                post['caption'],
                post['post_date'],
                datetime.now().isoformat(),
                post['url'],
                post['method'],
                post.get('media_url', ''),
                post.get('local_path', ''),
                json.dumps(post.get('hashtags', [])),
                post.get('hail_size_mentioned'),
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False
        finally:
            conn.close()

    def scrape_all(self, download_media: bool = True) -> Dict:
        """Run all scraping methods."""
        print("\n" + "=" * 60)
        print("INSTAGRAM ALTERNATIVE SCRAPER")
        print("=" * 60)

        stats = {
            'web_search_posts': 0,
            'image_search_posts': 0,
            'frontend_posts': 0,
            'oembed_enriched': 0,
            'media_downloaded': 0,
            'total_saved': 0,
        }

        all_posts = []

        # Method 1: Web search
        print("\n[Method 1] Web search for Instagram posts...")
        for query in ['hail damage instagram', 'hailstorm instagram', 'golf ball hail instagram']:
            print(f"  Searching: '{query}'")
            posts = self.search_via_web(query, max_results=10)
            all_posts.extend(posts)
            stats['web_search_posts'] += len(posts)
            time.sleep(2)

        # Method 2: Image search
        print("\n[Method 2] Image search for Instagram content...")
        for query in ['hail damage', 'hailstorm']:
            print(f"  Searching: '{query}'")
            posts = self.search_via_google_images(query, max_results=5)
            all_posts.extend(posts)
            stats['image_search_posts'] += len(posts)
            time.sleep(2)

        # Method 3: Frontends
        print("\n[Method 3] Trying Instagram frontends...")
        for hashtag in self.HAIL_HASHTAGS[:3]:
            print(f"  Searching: #{hashtag}")
            posts = self.try_frontends(hashtag, max_results=5)
            all_posts.extend(posts)
            stats['frontend_posts'] += len(posts)
            time.sleep(2)

        # Deduplicate
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post['post_id'] and post['post_id'] not in seen_ids:
                seen_ids.add(post['post_id'])
                unique_posts.append(post)

        print(f"\n[Processing] {len(unique_posts)} unique posts...")

        # Try to enrich with oembed
        for post in unique_posts[:10]:  # Limit oembed calls
            enriched = self.get_post_via_oembed(post['url'])
            if enriched:
                post['username'] = enriched.get('username', post['username'])
                post['caption'] = enriched.get('caption') or post['caption']
                post['media_url'] = enriched.get('media_url') or post['media_url']
                stats['oembed_enriched'] += 1
            time.sleep(1)

        # Download media and save
        for post in unique_posts:
            if download_media and post.get('media_url'):
                local_path = self.download_media(post)
                if local_path:
                    post['local_path'] = local_path
                    stats['media_downloaded'] += 1

            if self.save_post(post):
                stats['total_saved'] += 1

        # Summary
        print("\n" + "=" * 60)
        print("SCRAPE COMPLETE")
        print("=" * 60)
        print(f"  Web search posts: {stats['web_search_posts']}")
        print(f"  Image search posts: {stats['image_search_posts']}")
        print(f"  Frontend posts: {stats['frontend_posts']}")
        print(f"  Oembed enriched: {stats['oembed_enriched']}")
        print(f"  Media downloaded: {stats['media_downloaded']}")
        print(f"  Total saved: {stats['total_saved']}")

        return stats


def test_alternative_scraper():
    """Test the alternative scraper."""
    scraper = InstagramAlternativeScraper()
    return scraper.scrape_all(download_media=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_alternative_scraper()
