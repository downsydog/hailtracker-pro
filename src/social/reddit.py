"""
Reddit Scraper for Hail Reports

Scrapes hail-related posts from weather and storm subreddits.
Supports English, French, and Spanish content.
"""

import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import json

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger('RedditScraper')


@dataclass
class RedditPost:
    """Represents a Reddit post about hail."""
    post_id: str
    subreddit: str
    title: str
    author: str
    created_utc: datetime
    url: str
    permalink: str
    selftext: str
    score: int
    num_comments: int
    is_video: bool
    is_image: bool
    media_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    # Extracted data
    language: str = 'en'
    location_text: Optional[str] = None
    estimated_lat: Optional[float] = None
    estimated_lon: Optional[float] = None
    hail_size_mentioned: Optional[str] = None
    hail_size_inches: Optional[float] = None
    relevance_score: float = 0.0


class RedditScraper:
    """
    Scrapes Reddit for hail-related posts.

    Uses Reddit's public JSON API (no authentication required for public posts).
    Rate-limited to respect Reddit's guidelines.
    """

    # Reddit JSON API base (no OAuth needed for public posts)
    # Note: old.reddit.com search works better than www.reddit.com
    BASE_URL = 'https://old.reddit.com'

    # Hail-related subreddits (prioritized)
    SUBREDDITS = {
        # Weather/Storm (English)
        'weather': {'priority': 1, 'language': 'en'},
        'stormchasing': {'priority': 1, 'language': 'en'},
        'tornado': {'priority': 2, 'language': 'en'},
        'WeatherGifs': {'priority': 2, 'language': 'en'},
        'TropicalWeather': {'priority': 3, 'language': 'en'},
        'atoptics': {'priority': 3, 'language': 'en'},

        # Regional US (English)
        'oklahoma': {'priority': 2, 'language': 'en'},
        'texas': {'priority': 2, 'language': 'en'},
        'kansas': {'priority': 2, 'language': 'en'},
        'colorado': {'priority': 2, 'language': 'en'},
        'Nebraska': {'priority': 2, 'language': 'en'},
        'Denver': {'priority': 3, 'language': 'en'},
        'Dallas': {'priority': 3, 'language': 'en'},
        'houston': {'priority': 3, 'language': 'en'},
        'Austin': {'priority': 3, 'language': 'en'},
        'sanantonio': {'priority': 3, 'language': 'en'},
        'okc': {'priority': 3, 'language': 'en'},

        # Canadian (English/French)
        'alberta': {'priority': 2, 'language': 'en'},
        'Calgary': {'priority': 3, 'language': 'en'},
        'Edmonton': {'priority': 3, 'language': 'en'},
        'saskatchewan': {'priority': 3, 'language': 'en'},
        'Manitoba': {'priority': 3, 'language': 'en'},
        'Winnipeg': {'priority': 3, 'language': 'en'},
        'Quebec': {'priority': 3, 'language': 'fr'},
        'montreal': {'priority': 3, 'language': 'fr'},

        # Mexican (Spanish)
        'mexico': {'priority': 2, 'language': 'es'},
        'Monterrey': {'priority': 3, 'language': 'es'},
        'Guadalajara': {'priority': 3, 'language': 'es'},
        'MexicoCity': {'priority': 3, 'language': 'es'},
    }

    # Hail-related keywords by language
    HAIL_KEYWORDS = {
        'en': [
            'hail', 'hailstorm', 'hailstone', 'hailing',
            'golf ball', 'golfball', 'softball', 'baseball',
            'tennis ball', 'quarter size', 'nickel size', 'dime size',
            'car damage', 'windshield', 'dents', 'dented',
            'severe storm', 'supercell', 'storm damage'
        ],
        'fr': [
            'grêle', 'grele', 'grêlons', 'grelons',
            'tempête de grêle', 'averse de grêle',
            'dégâts', 'pare-brise', 'bosses',
            'orage violent', 'supercellule'
        ],
        'es': [
            'granizo', 'granizada', 'piedra', 'piedras',
            'tormenta de granizo', 'granizo del tamaño',
            'daños', 'parabrisas', 'abolladuras',
            'tormenta severa', 'supercelda'
        ]
    }

    # Size patterns by language
    SIZE_PATTERNS = {
        'en': [
            (r'(\d+(?:\.\d+)?)\s*(?:inch|in|")', 'inches'),
            (r'(\d+(?:\.\d+)?)\s*(?:cm|centimeter)', 'cm'),
            (r'golf\s*ball', 1.75),
            (r'tennis\s*ball', 2.5),
            (r'baseball', 2.75),
            (r'softball', 4.0),
            (r'quarter', 1.0),
            (r'nickel', 0.875),
            (r'dime', 0.7),
            (r'ping\s*pong', 1.5),
        ],
        'fr': [
            (r'(\d+(?:\.\d+)?)\s*(?:cm|centimètre)', 'cm'),
            (r'(\d+(?:\.\d+)?)\s*(?:mm|millimètre)', 'mm'),
            (r'balle de golf', 1.75),
            (r'balle de tennis', 2.5),
            (r'oeuf', 2.0),
        ],
        'es': [
            (r'(\d+(?:\.\d+)?)\s*(?:cm|centímetro)', 'cm'),
            (r'(\d+(?:\.\d+)?)\s*(?:mm|milímetro)', 'mm'),
            (r'pelota de golf', 1.75),
            (r'pelota de tenis', 2.5),
            (r'huevo', 2.0),
            (r'nuez', 1.25),
        ]
    }

    def __init__(
        self,
        data_dir: str = None,
        rate_limit_seconds: float = 2.0
    ):
        """
        Initialize Reddit scraper.

        Args:
            data_dir: Directory for storing scraped data
            rate_limit_seconds: Minimum time between requests
        """
        if not HAS_REQUESTS:
            raise ImportError("requests library required. Install with: pip install requests")

        self.data_dir = Path(data_dir) if data_dir else Path('data/social/reddit')
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.rate_limit = rate_limit_seconds
        self.last_request_time = 0

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HailTracker/2.0 (Weather Research Bot; Contact: research@example.com)'
        })

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, url: str, params: dict = None) -> Optional[Dict]:
        """Make rate-limited request to Reddit."""
        self._rate_limit()

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def search_subreddit(
        self,
        subreddit: str,
        query: str = None,
        time_filter: str = 'year',  # Default to year for better results
        limit: int = 25,
        min_relevance: float = 0.0  # Allow all posts by default
    ) -> List[RedditPost]:
        """
        Search a subreddit for hail-related posts.

        Args:
            subreddit: Subreddit name
            query: Search query (optional, uses hail keywords if None)
            time_filter: 'hour', 'day', 'week', 'month', 'year', 'all'
            limit: Maximum posts to return
            min_relevance: Minimum relevance score (0.0 = include all)

        Returns:
            List of RedditPost objects
        """
        # Get subreddit info
        sub_info = self.SUBREDDITS.get(subreddit, {'priority': 3, 'language': 'en'})
        language = sub_info['language']

        # Build search query if not provided
        if not query:
            keywords = self.HAIL_KEYWORDS.get(language, self.HAIL_KEYWORDS['en'])
            query = ' OR '.join(keywords[:5])  # Use top 5 keywords

        # Search endpoint - use 'top' sort for better quality results
        url = f"{self.BASE_URL}/r/{subreddit}/search.json"
        params = {
            'q': query,
            'restrict_sr': 'true',
            't': time_filter,
            'limit': min(limit, 100),
            'sort': 'top'  # Changed from 'new' to 'top' for better results
        }

        data = self._make_request(url, params)
        if not data:
            return []

        posts = []
        for child in data.get('data', {}).get('children', []):
            post_data = child.get('data', {})
            if not post_data:
                continue

            post = self._parse_post(post_data, language)
            if post and post.relevance_score >= min_relevance:
                posts.append(post)

        return posts

    def get_new_posts(
        self,
        subreddit: str,
        limit: int = 25
    ) -> List[RedditPost]:
        """
        Get newest posts from a subreddit.

        Args:
            subreddit: Subreddit name
            limit: Maximum posts to return

        Returns:
            List of RedditPost objects
        """
        sub_info = self.SUBREDDITS.get(subreddit, {'priority': 3, 'language': 'en'})
        language = sub_info['language']

        url = f"{self.BASE_URL}/r/{subreddit}/new.json"
        params = {'limit': min(limit, 100)}

        data = self._make_request(url, params)
        if not data:
            return []

        posts = []
        for child in data.get('data', {}).get('children', []):
            post_data = child.get('data', {})
            if not post_data:
                continue

            post = self._parse_post(post_data, language)
            if post:
                # Calculate relevance for new posts
                self._calculate_relevance(post)
                if post.relevance_score > 0:
                    posts.append(post)

        return posts

    def get_subreddit_posts(
        self,
        subreddit: str,
        sort: str = 'top',
        time_filter: str = 'month',
        limit: int = 25
    ) -> List[RedditPost]:
        """
        Get posts from a subreddit with specified sorting.

        Args:
            subreddit: Subreddit name
            sort: 'top', 'hot', 'new', 'rising'
            time_filter: For 'top' sort: 'hour', 'day', 'week', 'month', 'year', 'all'
            limit: Maximum posts to return

        Returns:
            List of RedditPost objects
        """
        sub_info = self.SUBREDDITS.get(subreddit, {'priority': 3, 'language': 'en'})
        language = sub_info['language']

        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = {'limit': min(limit, 100)}
        if sort == 'top':
            params['t'] = time_filter

        data = self._make_request(url, params)
        if not data:
            return []

        posts = []
        for child in data.get('data', {}).get('children', []):
            post_data = child.get('data', {})
            if not post_data:
                continue

            post = self._parse_post(post_data, language)
            if post:
                self._calculate_relevance(post)
                posts.append(post)

        return posts

    def _parse_post(self, data: Dict, language: str = 'en') -> Optional[RedditPost]:
        """Parse Reddit post data into RedditPost object."""
        try:
            created = datetime.utcfromtimestamp(data.get('created_utc', 0))

            url = data.get('url', '')

            # Determine if media - more comprehensive detection
            is_video = data.get('is_video', False) or 'v.redd.it' in url
            is_image = bool(
                data.get('post_hint') == 'image' or
                data.get('post_hint') == 'rich:video' or  # Some images have this
                url.endswith(('.jpg', '.png', '.gif', '.jpeg', '.webp')) or
                'i.redd.it' in url or
                'preview.redd.it' in url or
                'imgur.com' in url or
                data.get('is_gallery', False) or
                data.get('preview', {}).get('images')  # Has preview images
            )

            # Get media URL - more comprehensive extraction
            media_url = None
            thumbnail_url = None

            if is_image:
                # Direct image URL
                if url.endswith(('.jpg', '.png', '.gif', '.jpeg', '.webp')):
                    media_url = url
                elif 'i.redd.it' in url:
                    media_url = url
                elif 'imgur.com' in url:
                    # Convert imgur page URL to direct image
                    if '/a/' not in url and '/gallery/' not in url:
                        media_url = url.replace('imgur.com', 'i.imgur.com')
                        if not media_url.endswith(('.jpg', '.png', '.gif')):
                            media_url += '.jpg'

                # Fallback to preview images
                if not media_url and data.get('preview'):
                    images = data.get('preview', {}).get('images', [])
                    if images:
                        source = images[0].get('source', {})
                        media_url = source.get('url', '').replace('&amp;', '&')

                # Gallery posts - get first image
                if not media_url and data.get('is_gallery') and data.get('media_metadata'):
                    for media_id, media_info in data.get('media_metadata', {}).items():
                        if media_info.get('status') == 'valid' and media_info.get('e') == 'Image':
                            media_url = media_info.get('s', {}).get('u', '').replace('&amp;', '&')
                            break

            elif is_video and data.get('media'):
                media_url = data.get('media', {}).get('reddit_video', {}).get('fallback_url')

            # Get thumbnail
            thumb = data.get('thumbnail', '')
            if thumb.startswith('http'):
                thumbnail_url = thumb

            post = RedditPost(
                post_id=data.get('id', ''),
                subreddit=data.get('subreddit', ''),
                title=data.get('title', ''),
                author=data.get('author', '[deleted]'),
                created_utc=created,
                url=url,
                permalink=f"https://reddit.com{data.get('permalink', '')}",
                selftext=data.get('selftext', ''),
                score=data.get('score', 0),
                num_comments=data.get('num_comments', 0),
                is_video=is_video,
                is_image=is_image,
                media_url=media_url,
                thumbnail_url=thumbnail_url,
                language=language
            )

            # Calculate relevance and extract info
            self._calculate_relevance(post)
            self._extract_location(post)
            self._extract_hail_size(post)

            return post

        except Exception as e:
            logger.error(f"Error parsing post: {e}")
            return None

    def _calculate_relevance(self, post: RedditPost):
        """Calculate relevance score for a post."""
        text = f"{post.title} {post.selftext}".lower()
        keywords = self.HAIL_KEYWORDS.get(post.language, self.HAIL_KEYWORDS['en'])

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw.lower() in text)

        # Base score from keyword matches
        score = min(matches / 3.0, 1.0)

        # Boost for media
        if post.is_image or post.is_video:
            score *= 1.5

        # Boost for engagement
        if post.score > 100:
            score *= 1.2
        if post.num_comments > 20:
            score *= 1.1

        # Boost for size mentions
        if post.hail_size_inches and post.hail_size_inches >= 1.0:
            score *= 1.3

        post.relevance_score = min(score, 1.0)

    def _extract_location(self, post: RedditPost):
        """Extract location from post text."""
        text = f"{post.title} {post.selftext}"

        # US State patterns
        state_patterns = [
            r'\b([A-Z]{2})\b',  # Two-letter state codes
            r'in\s+(\w+(?:\s+\w+)?),?\s*(?:US|USA|United States)',
            r'(\w+),\s*(?:TX|OK|KS|CO|NE|SD|ND)',
        ]

        # Canadian province patterns
        province_patterns = [
            r'in\s+(\w+),?\s*(?:AB|SK|MB|ON|QC|BC)',
            r'(\w+),\s*(?:Alberta|Saskatchewan|Manitoba|Ontario|Quebec)',
        ]

        for pattern in state_patterns + province_patterns:
            match = re.search(pattern, text)
            if match:
                post.location_text = match.group(1)
                break

        # Also check subreddit for location hints
        location_subreddits = {
            'oklahoma': 'Oklahoma', 'texas': 'Texas', 'kansas': 'Kansas',
            'colorado': 'Colorado', 'Denver': 'Denver, CO',
            'Dallas': 'Dallas, TX', 'houston': 'Houston, TX',
            'Calgary': 'Calgary, AB', 'Edmonton': 'Edmonton, AB',
            'Winnipeg': 'Winnipeg, MB',
        }
        if not post.location_text and post.subreddit.lower() in location_subreddits:
            post.location_text = location_subreddits[post.subreddit.lower()]

    def _extract_hail_size(self, post: RedditPost):
        """Extract hail size from post text."""
        text = f"{post.title} {post.selftext}".lower()
        patterns = self.SIZE_PATTERNS.get(post.language, self.SIZE_PATTERNS['en'])

        for pattern in patterns:
            if isinstance(pattern[1], (int, float)):
                # Named size (golf ball, etc.)
                if re.search(pattern[0], text, re.IGNORECASE):
                    post.hail_size_mentioned = pattern[0]
                    post.hail_size_inches = pattern[1]
                    return
            else:
                # Numeric size
                match = re.search(pattern[0], text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    unit = pattern[1]
                    if unit == 'cm':
                        post.hail_size_inches = value / 2.54
                    elif unit == 'mm':
                        post.hail_size_inches = value / 25.4
                    else:
                        post.hail_size_inches = value
                    post.hail_size_mentioned = match.group(0)
                    return

    def scrape_all_subreddits(
        self,
        time_filter: str = 'week',
        limit_per_sub: int = 25,
        priority_max: int = 3
    ) -> List[RedditPost]:
        """
        Scrape all configured subreddits for hail posts.

        Args:
            time_filter: Time filter for search
            limit_per_sub: Max posts per subreddit
            priority_max: Only scrape subreddits with priority <= this

        Returns:
            List of all relevant posts
        """
        all_posts = []

        # Sort by priority
        sorted_subs = sorted(
            self.SUBREDDITS.items(),
            key=lambda x: x[1]['priority']
        )

        for subreddit, info in sorted_subs:
            if info['priority'] > priority_max:
                continue

            logger.info(f"Scraping r/{subreddit}...")

            try:
                posts = self.search_subreddit(
                    subreddit,
                    time_filter=time_filter,
                    limit=limit_per_sub
                )
                all_posts.extend(posts)
                logger.info(f"  Found {len(posts)} relevant posts")

            except Exception as e:
                logger.error(f"Error scraping r/{subreddit}: {e}")

        # Deduplicate by post_id
        seen = set()
        unique_posts = []
        for post in all_posts:
            if post.post_id not in seen:
                seen.add(post.post_id)
                unique_posts.append(post)

        # Sort by relevance and recency
        unique_posts.sort(
            key=lambda x: (x.relevance_score, x.created_utc),
            reverse=True
        )

        return unique_posts

    def save_posts(self, posts: List[RedditPost], filename: str = None) -> str:
        """Save posts to JSON file."""
        if not filename:
            filename = f"reddit_posts_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = self.data_dir / filename

        data = []
        for post in posts:
            data.append({
                'post_id': post.post_id,
                'subreddit': post.subreddit,
                'title': post.title,
                'author': post.author,
                'created_utc': post.created_utc.isoformat(),
                'url': post.url,
                'permalink': post.permalink,
                'score': post.score,
                'num_comments': post.num_comments,
                'is_video': post.is_video,
                'is_image': post.is_image,
                'media_url': post.media_url,
                'language': post.language,
                'location_text': post.location_text,
                'hail_size_mentioned': post.hail_size_mentioned,
                'hail_size_inches': post.hail_size_inches,
                'relevance_score': post.relevance_score
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(output_path)


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("REDDIT SCRAPER TEST")
    print("=" * 60)

    scraper = RedditScraper(data_dir='data/test_reddit')

    # Test searching a weather subreddit
    print("\nSearching r/weather for hail posts...")
    posts = scraper.search_subreddit('weather', time_filter='month', limit=10)

    print(f"Found {len(posts)} relevant posts:")
    for post in posts[:5]:
        print(f"\n  [{post.relevance_score:.2f}] {post.title[:60]}...")
        print(f"      r/{post.subreddit} | Score: {post.score} | {post.created_utc}")
        if post.location_text:
            print(f"      Location: {post.location_text}")
        if post.hail_size_inches:
            print(f"      Hail size: {post.hail_size_inches}\"")
        if post.is_image:
            print(f"      Has image: {post.media_url}")

    # Save results
    if posts:
        path = scraper.save_posts(posts)
        print(f"\nSaved to: {path}")

    print("\nReddit scraper ready!")
