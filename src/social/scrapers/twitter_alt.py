"""
Twitter Alternative Scraper - Multiple Methods

Uses multiple fallback methods to scrape Twitter:
1. Nitter RSS feeds (more reliable than HTML)
2. Twitter Syndication API (embedded tweets)
3. Direct search via mobile site
"""

import os
import sys
import json
import time
import re
import sqlite3
import hashlib
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote, urlparse
import logging

logger = logging.getLogger('TwitterAltScraper')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class TwitterAlternativeScraper:
    """
    Alternative Twitter scraper using multiple methods.
    """

    # Nitter RSS endpoints (more reliable than HTML scraping)
    NITTER_RSS_INSTANCES = [
        'https://nitter.poast.org',
        'https://nitter.privacydev.net',
        'https://nitter.1d4.us',
        'https://nitter.woodland.cafe',
    ]

    # Twitter syndication API (for embedded tweets)
    SYNDICATION_API = 'https://syndication.twitter.com'

    # Search queries
    HAIL_QUERIES = [
        'hail damage',
        'hail storm',
        'golf ball hail',
        'hailstorm',
        '#haildamage',
    ]

    def __init__(self, db_path: Optional[str] = None, media_dir: Optional[str] = None):
        self.db_path = db_path or str(PROJECT_ROOT / 'data' / 'social_media.db')
        self.media_dir = Path(media_dir) if media_dir else PROJECT_ROOT / 'data' / 'social_media' / 'twitter'
        self.media_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/html, application/xml, */*',
        })

        self._init_db()

    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS twitter_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT UNIQUE,
                username TEXT,
                content TEXT,
                post_date TEXT,
                scraped_at TEXT,
                url TEXT,
                method TEXT,
                has_media INTEGER DEFAULT 0,
                media_urls TEXT,
                location_mentioned TEXT,
                hail_size_mentioned TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _extract_hail_size(self, text: str) -> Optional[str]:
        """Extract hail size from text."""
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

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        states = ['Texas', 'TX', 'Oklahoma', 'OK', 'Kansas', 'KS', 'Colorado', 'CO', 'Nebraska', 'NE']
        cities = ['Dallas', 'Houston', 'Austin', 'Oklahoma City', 'Denver', 'Wichita']
        text_upper = text.upper()
        for city in cities:
            if city.upper() in text_upper:
                return city
        for state in states:
            if state.upper() in text_upper:
                return state
        return None

    def scrape_via_rss(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Scrape via Nitter RSS feeds.
        RSS is often more reliable than HTML scraping.
        """
        tweets = []

        for instance in self.NITTER_RSS_INSTANCES:
            try:
                # RSS search endpoint
                rss_url = f"{instance}/search/rss?f=tweets&q={quote(query)}"

                resp = self.session.get(rss_url, timeout=15)
                if resp.status_code != 200:
                    continue

                # Parse RSS
                root = ET.fromstring(resp.content)
                items = root.findall('.//item')

                for item in items[:max_results]:
                    title = item.find('title')
                    link = item.find('link')
                    pubDate = item.find('pubDate')
                    description = item.find('description')
                    creator = item.find('{http://purl.org/dc/elements/1.1/}creator')

                    if title is None or link is None:
                        continue

                    content = title.text or ''
                    url = link.text or ''

                    # Extract tweet ID from URL
                    tweet_id = url.split('/')[-1].split('#')[0] if url else None

                    # Extract username
                    username = 'unknown'
                    if creator is not None and creator.text:
                        username = creator.text.lstrip('@')
                    elif '/' in url:
                        parts = url.split('/')
                        for i, p in enumerate(parts):
                            if p and parts[i-1] != 'status' and i > 0:
                                username = p
                                break

                    tweets.append({
                        'tweet_id': tweet_id,
                        'username': username,
                        'content': content,
                        'post_date': pubDate.text if pubDate is not None else '',
                        'url': url.replace(instance, 'https://twitter.com'),
                        'method': 'rss',
                        'has_media': '<img' in (description.text or '') if description is not None else False,
                        'hail_size_mentioned': self._extract_hail_size(content),
                        'location_mentioned': self._extract_location(content),
                    })

                if tweets:
                    print(f"    [RSS] {instance}: Found {len(tweets)} tweets")
                    return tweets

            except ET.ParseError:
                continue
            except Exception as e:
                logger.debug(f"RSS error for {instance}: {e}")
                continue

        return tweets

    def scrape_via_syndication(self, tweet_url: str) -> Optional[Dict]:
        """
        Get tweet data via Twitter's syndication API.
        Used for embedded tweets - works without auth.
        """
        try:
            # Extract tweet ID
            tweet_id = tweet_url.split('/')[-1].split('?')[0]

            # Syndication API endpoint
            api_url = f"{self.SYNDICATION_API}/tweet-result?id={tweet_id}"

            resp = self.session.get(api_url, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()

            return {
                'tweet_id': tweet_id,
                'username': data.get('user', {}).get('screen_name', 'unknown'),
                'content': data.get('text', ''),
                'post_date': data.get('created_at', ''),
                'url': tweet_url,
                'method': 'syndication',
                'has_media': bool(data.get('mediaDetails')),
                'hail_size_mentioned': self._extract_hail_size(data.get('text', '')),
                'location_mentioned': self._extract_location(data.get('text', '')),
            }

        except Exception as e:
            logger.debug(f"Syndication error: {e}")
            return None

    def scrape_via_search_api(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Try Twitter's public search suggestions/typeahead.
        Limited but doesn't require auth.
        """
        tweets = []

        try:
            # Twitter typeahead API (limited results)
            url = f"https://twitter.com/i/api/1.1/search/typeahead.json?q={quote(query)}&result_type=events"

            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # This returns limited data, mainly trends/topics
                topics = data.get('topics', [])
                for topic in topics[:5]:
                    if 'hail' in topic.get('topic', '').lower():
                        print(f"    [API] Found trending topic: {topic.get('topic')}")

        except Exception as e:
            logger.debug(f"Search API error: {e}")

        return tweets

    def scrape_via_web_search(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Find tweets via Google/DuckDuckGo site search.
        """
        tweets = []

        try:
            # DuckDuckGo search for tweets
            search_query = f"site:twitter.com {query}"
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote(search_query)}"

            resp = self.session.get(ddg_url, timeout=15)
            if resp.status_code != 200:
                return tweets

            if not BS4_AVAILABLE:
                return tweets

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Find result links
            results = soup.select('a.result__url')

            for result in results[:max_results]:
                url = result.get('href', '')
                if 'twitter.com' in url and '/status/' in url:
                    # Extract tweet ID
                    match = re.search(r'/status/(\d+)', url)
                    if match:
                        tweet_id = match.group(1)

                        # Get parent for text
                        parent = result.find_parent('div', class_='result')
                        snippet = ''
                        if parent:
                            snippet_elem = parent.select_one('.result__snippet')
                            if snippet_elem:
                                snippet = snippet_elem.text.strip()

                        tweets.append({
                            'tweet_id': tweet_id,
                            'username': url.split('/')[3] if len(url.split('/')) > 3 else 'unknown',
                            'content': snippet,
                            'post_date': '',
                            'url': url,
                            'method': 'web_search',
                            'has_media': False,
                            'hail_size_mentioned': self._extract_hail_size(snippet),
                            'location_mentioned': self._extract_location(snippet),
                        })

            if tweets:
                print(f"    [WebSearch] Found {len(tweets)} tweet links")

        except Exception as e:
            logger.debug(f"Web search error: {e}")

        return tweets

    def save_tweet(self, tweet: Dict) -> bool:
        """Save tweet to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO twitter_posts
                (tweet_id, username, content, post_date, scraped_at, url, method,
                 has_media, media_urls, location_mentioned, hail_size_mentioned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tweet['tweet_id'],
                tweet['username'],
                tweet['content'],
                tweet['post_date'],
                datetime.now().isoformat(),
                tweet['url'],
                tweet['method'],
                1 if tweet['has_media'] else 0,
                json.dumps(tweet.get('media_urls', [])),
                tweet.get('location_mentioned'),
                tweet.get('hail_size_mentioned'),
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Save error: {e}")
            return False
        finally:
            conn.close()

    def scrape_all(self) -> Dict:
        """Run all scraping methods."""
        print("\n" + "=" * 60)
        print("TWITTER ALTERNATIVE SCRAPER")
        print("=" * 60)

        stats = {
            'rss_tweets': 0,
            'web_search_tweets': 0,
            'total_saved': 0,
            'methods_tried': [],
        }

        all_tweets = []

        # Method 1: RSS feeds
        print("\n[Method 1] Trying Nitter RSS feeds...")
        stats['methods_tried'].append('rss')
        for query in self.HAIL_QUERIES[:3]:
            print(f"  Searching: '{query}'")
            tweets = self.scrape_via_rss(query, max_results=10)
            all_tweets.extend(tweets)
            stats['rss_tweets'] += len(tweets)
            time.sleep(2)

        # Method 2: Web search
        print("\n[Method 2] Trying web search...")
        stats['methods_tried'].append('web_search')
        for query in self.HAIL_QUERIES[:2]:
            print(f"  Searching: '{query}'")
            tweets = self.scrape_via_web_search(query, max_results=10)
            all_tweets.extend(tweets)
            stats['web_search_tweets'] += len(tweets)
            time.sleep(2)

        # Deduplicate
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet['tweet_id'] and tweet['tweet_id'] not in seen_ids:
                seen_ids.add(tweet['tweet_id'])
                unique_tweets.append(tweet)

        # Save
        print(f"\n[Saving] {len(unique_tweets)} unique tweets...")
        for tweet in unique_tweets:
            if self.save_tweet(tweet):
                stats['total_saved'] += 1

        # Summary
        print("\n" + "=" * 60)
        print("SCRAPE COMPLETE")
        print("=" * 60)
        print(f"  Methods tried: {', '.join(stats['methods_tried'])}")
        print(f"  RSS tweets: {stats['rss_tweets']}")
        print(f"  Web search tweets: {stats['web_search_tweets']}")
        print(f"  Total saved: {stats['total_saved']}")

        return stats


def test_alternative_scraper():
    """Test the alternative scraper."""
    scraper = TwitterAlternativeScraper()
    return scraper.scrape_all()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_alternative_scraper()
