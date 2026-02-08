"""
Storm Verification Pipeline

Automatically finds and links social media hail photos to storm events.
This connects:
- Active storm events from the database
- Reddit scraper to find hail photos
- HailSizeEstimator ML model to analyze photos
- StormVerificationManager to store verifications

WORKFLOW:
1. Get active/recent storm events
2. For each storm, search Reddit for matching posts (location + time)
3. Download and analyze hail photos with ML
4. Store verifications linked to the storm event
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys
import json
import base64

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger('StormVerificationPipeline')


class StormVerificationPipeline:
    """
    Orchestrates social media verification of storm events.

    Uses MULTIPLE sources for best coverage:
    - Reddit (weather subreddits)
    - Twitter/Nitter (via RSS feeds)
    - DuckDuckGo Images (web images)
    - Fallback: Generic hail photos for the region
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the pipeline.

        Args:
            db_path: Path to database (defaults to hailtracker_crm.db)
        """
        self.db_path = db_path

        # Lazy load components
        self._reddit_scraper = None
        self._twitter_scraper = None
        self._image_scraper = None
        self._verification_manager = None
        self._hail_estimator = None
        self._photo_validator = None

    @property
    def reddit_scraper(self):
        """Lazy load Reddit scraper."""
        if self._reddit_scraper is None:
            try:
                from src.social.reddit import RedditScraper
                self._reddit_scraper = RedditScraper()
                logger.info("Reddit scraper initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit scraper: {e}")
        return self._reddit_scraper

    @property
    def twitter_scraper(self):
        """Lazy load Twitter/Nitter scraper."""
        if self._twitter_scraper is None:
            try:
                from src.social.scrapers.twitter_alt import TwitterAlternativeScraper
                self._twitter_scraper = TwitterAlternativeScraper()
                logger.info("Twitter scraper initialized")
            except Exception as e:
                logger.warning(f"Twitter scraper not available: {e}")
        return self._twitter_scraper

    @property
    def image_scraper(self):
        """Lazy load DuckDuckGo image scraper."""
        if self._image_scraper is None:
            try:
                from src.social.scrapers.google_images import DuckDuckGoImagesScraper
                self._image_scraper = DuckDuckGoImagesScraper()
                logger.info("Image scraper initialized")
            except Exception as e:
                logger.warning(f"Image scraper not available: {e}")
        return self._image_scraper

    @property
    def multi_source_scraper(self):
        """Lazy load multi-source scraper for comprehensive coverage."""
        if not hasattr(self, '_multi_source_scraper'):
            self._multi_source_scraper = None
        if self._multi_source_scraper is None:
            try:
                from src.social.scrapers.multi_source import MultiSourceHailScraper
                self._multi_source_scraper = MultiSourceHailScraper()
                logger.info("Multi-source scraper initialized (Bing, Flickr, YouTube, Wikimedia, News, Twitter)")
            except Exception as e:
                logger.warning(f"Multi-source scraper not available: {e}")
        return self._multi_source_scraper

    @property
    def verification_manager(self):
        """Lazy load verification manager."""
        if self._verification_manager is None:
            try:
                from src.crm.managers.storm_verification_manager import StormVerificationManager
                self._verification_manager = StormVerificationManager(self.db_path)
                logger.info("Verification manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize verification manager: {e}")
        return self._verification_manager

    @property
    def hail_estimator(self):
        """Lazy load hail size estimator ML model."""
        if self._hail_estimator is None:
            try:
                from src.ml.models.hail_size_estimator import HailSizeEstimator
                self._hail_estimator = HailSizeEstimator()
                logger.info("Hail size estimator initialized")
            except Exception as e:
                logger.warning(f"Hail size estimator not available: {e}")
        return self._hail_estimator

    @property
    def photo_validator(self):
        """Lazy load photo authenticity validator."""
        if self._photo_validator is None:
            try:
                from src.ml.models.photo_validator import PhotoAuthenticityValidator
                self._photo_validator = PhotoAuthenticityValidator()
                logger.info("Photo validator initialized")
            except Exception as e:
                logger.warning(f"Photo validator not available: {e}")
        return self._photo_validator

    def find_verifications_for_storm(
        self,
        storm_id: int,
        storm_location: str,
        storm_date: str,
        storm_state: str = None,
        search_radius_days: int = 7,  # Wider default
        max_posts: int = 30,
        auto_analyze: bool = True
    ) -> Dict:
        """
        Find and store social media verifications for a storm event.

        Uses MULTIPLE sources with fallback strategy:
        1. Reddit (weather subreddits)
        2. Twitter via Nitter
        3. DuckDuckGo Images
        4. Fallback: Generic hail photos for region

        Args:
            storm_id: ID of the hail event in database
            storm_location: Location string (city, region, etc.)
            storm_date: Date of storm (YYYY-MM-DD)
            storm_state: State/province code (TX, OK, etc.)
            search_radius_days: Days before/after storm to search
            max_posts: Maximum posts to retrieve
            auto_analyze: Whether to run ML analysis on photos

        Returns:
            Dict with results summary
        """
        results = {
            'storm_id': storm_id,
            'posts_found': 0,
            'verifications_added': 0,
            'photos_analyzed': 0,
            'hail_detected': 0,
            'sources_searched': [],
            'errors': []
        }

        try:
            # Parse storm date
            storm_dt = datetime.strptime(storm_date, '%Y-%m-%d')
            days_since_storm = (datetime.now() - storm_dt).days

            # Build search query - use location-specific search
            location_term = storm_location.split(',')[0].strip() if storm_location else ''
            state_term = storm_state or ''

            # Build multiple query variants for better coverage
            queries = []
            if location_term:
                queries.append(f'hail {location_term}')
                queries.append(f'hail storm {location_term}')
                queries.append(f'hail damage {location_term}')
            if state_term:
                queries.append(f'hail {state_term}')
                queries.append(f'hail storm {state_term}')
            if not queries:
                queries = ['hail storm', 'hailstorm damage']

            logger.info(f"Search queries: {queries}")

            # Determine time filter based on storm age
            if days_since_storm <= 7:
                time_filter = 'week'
                search_radius_days = max(search_radius_days, 7)
            elif days_since_storm <= 30:
                time_filter = 'month'
                search_radius_days = max(search_radius_days, 14)
            elif days_since_storm <= 365:
                time_filter = 'year'
                search_radius_days = max(search_radius_days, 30)
            else:
                time_filter = 'all'
                search_radius_days = 365  # Wide radius for old storms

            logger.info(f"Searching for storm from {storm_date} ({days_since_storm} days ago)")

            all_posts = []

            # =============================================
            # SOURCE 1: Reddit
            # =============================================
            if self.reddit_scraper:
                try:
                    reddit_posts = self._search_reddit(
                        queries[0],
                        storm_location,
                        storm_state,
                        storm_dt,
                        time_filter,
                        search_radius_days,
                        max_posts // 2
                    )
                    all_posts.extend(reddit_posts)
                    results['sources_searched'].append('reddit')
                    logger.info(f"Reddit: Found {len(reddit_posts)} posts")
                except Exception as e:
                    logger.warning(f"Reddit search failed: {e}")
                    results['errors'].append(f"Reddit: {str(e)}")

            # =============================================
            # SOURCE 2: Twitter via Nitter
            # =============================================
            if self.twitter_scraper:
                try:
                    twitter_posts = self._search_twitter(
                        queries,
                        location_term,
                        max_posts // 3
                    )
                    all_posts.extend(twitter_posts)
                    results['sources_searched'].append('twitter')
                    logger.info(f"Twitter: Found {len(twitter_posts)} posts")
                except Exception as e:
                    logger.warning(f"Twitter search failed: {e}")
                    results['errors'].append(f"Twitter: {str(e)}")

            # =============================================
            # SOURCE 3: DuckDuckGo Images
            # =============================================
            if self.image_scraper:
                try:
                    # Build date string for search
                    storm_month_year = storm_dt.strftime('%B %Y')
                    image_posts = self._search_images(
                        location_term or state_term,
                        storm_month_year if days_since_storm <= 365 else None,
                        max_posts // 3
                    )
                    all_posts.extend(image_posts)
                    results['sources_searched'].append('images')
                    logger.info(f"Images: Found {len(image_posts)} results")
                except Exception as e:
                    logger.warning(f"Image search failed: {e}")
                    results['errors'].append(f"Images: {str(e)}")

            # =============================================
            # SOURCE 4: Multi-Source (Wikimedia, YouTube, Flickr, News, etc.)
            # =============================================
            if self.multi_source_scraper:
                try:
                    storm_month_year = storm_dt.strftime('%B %Y')
                    multi_photos = self.multi_source_scraper.search_all_sources(
                        location=location_term,
                        state=state_term,
                        date=storm_month_year if days_since_storm <= 365 else None,
                        max_per_source=max_posts // 6,
                        parallel=True
                    )
                    # Convert to post-like objects
                    for photo in multi_photos:
                        from dataclasses import dataclass
                        @dataclass
                        class PhotoPost:
                            is_image: bool = True
                            media_url: str = ''
                            url: str = ''
                            title: str = ''
                            author: str = ''
                            relevance_score: float = 0.5
                            source: str = ''

                        post = PhotoPost(
                            is_image=True,
                            media_url=photo.url,
                            url=photo.source_url,
                            title=photo.title,
                            author=photo.author or photo.source,
                            relevance_score=photo.relevance_score,
                            source=photo.source
                        )
                        all_posts.append(post)

                    results['sources_searched'].extend(['wikimedia', 'youtube', 'flickr', 'news', 'nitter'])
                    logger.info(f"Multi-source: Found {len(multi_photos)} photos from various sources")
                except Exception as e:
                    logger.warning(f"Multi-source search failed: {e}")
                    results['errors'].append(f"Multi-source: {str(e)}")

            # =============================================
            # FALLBACK: If few images, search broader
            # =============================================
            # Count posts with images
            image_posts = [p for p in all_posts if getattr(p, 'is_image', False) or getattr(p, 'media_url', None)]

            # AGGRESSIVE FALLBACK - Always try to get at least 5 photos
            MIN_PHOTOS_TARGET = 5

            if len(image_posts) < MIN_PHOTOS_TARGET:
                logger.info(f"Only {len(image_posts)} images found, trying aggressive fallback...")

                if self.reddit_scraper:
                    # Level 1: State-specific searches
                    fallback_queries_l1 = [
                        f'hail {state_term}' if state_term else 'hail storm',
                        f'hail damage {state_term}' if state_term else 'hail damage',
                        f'hailstorm {state_term}' if state_term else 'severe hail',
                    ]

                    for q in fallback_queries_l1:
                        if len(image_posts) >= MIN_PHOTOS_TARGET:
                            break
                        try:
                            for subreddit in ['weather', 'stormchasing']:
                                generic_posts = self.reddit_scraper.search_subreddit(
                                    subreddit,
                                    query=q,
                                    time_filter='year',
                                    limit=15,
                                    sort='top'
                                )
                                for post in generic_posts:
                                    if post.is_image and post.media_url:
                                        post.relevance_score = 0.35
                                        all_posts.append(post)
                                        image_posts.append(post)
                                        if len(image_posts) >= MIN_PHOTOS_TARGET:
                                            break
                        except Exception:
                            pass

                    # Level 2: Generic hail searches (high-engagement posts)
                    if len(image_posts) < MIN_PHOTOS_TARGET:
                        logger.info("Fallback level 2: Generic hail searches...")
                        generic_queries = [
                            'hail size comparison',
                            'baseball hail',
                            'golf ball hail',
                            'large hail damage',
                            'hail car damage',
                        ]

                        for q in generic_queries:
                            if len(image_posts) >= MIN_PHOTOS_TARGET:
                                break
                            try:
                                posts = self.reddit_scraper.search_subreddit(
                                    'weather',
                                    query=q,
                                    time_filter='all',  # All time for best images
                                    limit=10,
                                    sort='top'
                                )
                                for post in posts:
                                    if post.is_image and post.media_url and post.score > 50:
                                        post.relevance_score = 0.25
                                        all_posts.append(post)
                                        image_posts.append(post)
                                        if len(image_posts) >= MIN_PHOTOS_TARGET:
                                            break
                            except Exception:
                                pass

                    # Level 3: Browse top posts from weather subs
                    if len(image_posts) < 3:
                        logger.info("Fallback level 3: Top weather posts...")
                        try:
                            top_posts = self.reddit_scraper.get_subreddit_posts(
                                'weather',
                                sort='top',
                                time_filter='month',
                                limit=30
                            )
                            for post in top_posts:
                                if post.is_image and post.media_url:
                                    # Check if hail-related
                                    title_lower = (post.title or '').lower()
                                    if any(kw in title_lower for kw in ['hail', 'storm', 'severe', 'damage']):
                                        post.relevance_score = 0.2
                                        all_posts.append(post)
                                        image_posts.append(post)
                                        if len(image_posts) >= MIN_PHOTOS_TARGET:
                                            break
                        except Exception:
                            pass

                    results['sources_searched'].append('fallback_reddit')

            # Filter to only posts WITH images/media
            posts_with_images = [
                p for p in all_posts
                if getattr(p, 'is_image', False) or getattr(p, 'media_url', None)
            ]

            # Sort by relevance and limit
            posts_with_images.sort(key=lambda p: getattr(p, 'relevance_score', 0), reverse=True)
            posts_with_images = posts_with_images[:max_posts]

            results['posts_found'] = len(posts_with_images)

            # Process each post (only those with images)
            for post in posts_with_images:
                try:
                    verification_id = self._process_post(
                        storm_id=storm_id,
                        post=post,
                        auto_analyze=auto_analyze
                    )

                    if verification_id:
                        results['verifications_added'] += 1

                        if getattr(post, 'is_image', False) and auto_analyze:
                            results['photos_analyzed'] += 1

                except Exception as e:
                    post_id = getattr(post, 'post_id', 'unknown')
                    logger.warning(f"Error processing post {post_id}: {e}")
                    results['errors'].append(f"Post {post_id}: {str(e)}")

            logger.info(
                f"Storm {storm_id}: Found {results['posts_found']} posts from "
                f"{results['sources_searched']}, added {results['verifications_added']} verifications"
            )

        except Exception as e:
            logger.error(f"Pipeline error for storm {storm_id}: {e}")
            results['errors'].append(str(e))

        return results

    def _search_reddit(
        self,
        query: str,
        location: str,
        state: str,
        storm_dt: datetime,
        time_filter: str,
        search_radius_days: int,
        max_posts: int
    ) -> List:
        """Search Reddit for hail posts."""
        all_posts = []
        subreddits = self._get_subreddits_for_location(location, state)

        for subreddit in subreddits[:5]:
            try:
                posts = self.reddit_scraper.search_subreddit(
                    subreddit=subreddit,
                    query=query,
                    time_filter=time_filter,
                    limit=max_posts // len(subreddits[:5]) + 3
                )

                # Only filter by date if not a fallback search
                for post in posts:
                    if storm_dt:
                        post_date = post.created_utc.date()
                        days_diff = abs((post_date - storm_dt.date()).days)

                        if days_diff <= search_radius_days:
                            relevance = self._calculate_relevance(
                                post, location, state, days_diff
                            )
                            post.relevance_score = relevance
                            all_posts.append(post)
                    else:
                        all_posts.append(post)

            except Exception as e:
                logger.warning(f"Error searching r/{subreddit}: {e}")

        return all_posts

    def _search_twitter(
        self,
        queries: List[str],
        location: str,
        max_posts: int
    ) -> List:
        """Search Twitter via Nitter for hail posts."""
        all_posts = []

        for query in queries[:2]:  # Limit to 2 queries
            try:
                tweets = self.twitter_scraper.scrape_via_rss(
                    query=query,
                    max_results=max_posts // 2
                )

                for tweet in tweets:
                    # Convert to a simple object with needed attributes
                    class TwitterPost:
                        pass

                    post = TwitterPost()
                    post.post_id = tweet.get('tweet_id', '')
                    post.title = tweet.get('content', '')[:100]
                    post.url = tweet.get('url', '')
                    post.media_url = None
                    post.is_image = tweet.get('has_media', False)
                    post.relevance_score = 0.5 if location and location.lower() in tweet.get('content', '').lower() else 0.3
                    post.author = tweet.get('username', '')
                    post.source = 'twitter'

                    all_posts.append(post)

            except Exception as e:
                logger.warning(f"Twitter search error for '{query}': {e}")

        return all_posts

    def _search_images(
        self,
        location: str,
        date_str: str,
        max_results: int
    ) -> List:
        """Search DuckDuckGo for hail images."""
        all_posts = []

        try:
            results = self.image_scraper.search_hail_photos(
                location=location,
                date=date_str,
                max_results=max_results
            )

            for img in results:
                # Convert to a simple object with needed attributes
                class ImagePost:
                    pass

                post = ImagePost()
                post.post_id = f"img_{hash(img.url) % 10000}"
                post.title = img.title or f"Hail photo from {location}"
                post.url = img.source_url
                post.media_url = img.url
                post.thumbnail_url = img.thumbnail_url
                post.is_image = True
                post.relevance_score = 0.4  # Lower than social media posts
                post.author = img.source_domain
                post.source = 'images'

                all_posts.append(post)

        except Exception as e:
            logger.warning(f"Image search error: {e}")

        return all_posts

    def _get_subreddits_for_location(
        self,
        location: str,
        state: str = None
    ) -> List[str]:
        """
        Get relevant subreddits for a location.

        Args:
            location: Location string
            state: State code

        Returns:
            List of subreddit names, prioritized
        """
        subreddits = ['weather', 'stormchasing']  # Always search these

        # State-specific subreddits
        state_subs = {
            'TX': ['texas', 'Dallas', 'houston', 'Austin', 'sanantonio'],
            'OK': ['oklahoma', 'okc'],
            'KS': ['kansas'],
            'CO': ['colorado', 'Denver'],
            'NE': ['Nebraska'],
            'AB': ['alberta', 'Calgary', 'Edmonton'],  # Canada
            'SK': ['saskatchewan'],
            'MB': ['Manitoba', 'Winnipeg'],
            'QC': ['Quebec', 'montreal'],
            # Mexico
            'NL': ['Monterrey'],
            'JAL': ['Guadalajara'],
        }

        if state and state.upper() in state_subs:
            subreddits.extend(state_subs[state.upper()])

        # Check location string for city names
        location_lower = (location or '').lower()
        city_subs = {
            'dallas': 'Dallas',
            'houston': 'houston',
            'austin': 'Austin',
            'denver': 'Denver',
            'oklahoma city': 'okc',
            'calgary': 'Calgary',
            'edmonton': 'Edmonton',
        }

        for city, sub in city_subs.items():
            if city in location_lower and sub not in subreddits:
                subreddits.append(sub)

        return subreddits

    def _calculate_relevance(
        self,
        post,
        storm_location: str,
        storm_state: str,
        days_diff: int
    ) -> float:
        """
        Calculate relevance score for a post.

        Args:
            post: RedditPost object
            storm_location: Expected location
            storm_state: Expected state
            days_diff: Days from storm date

        Returns:
            Relevance score 0-1
        """
        score = 0.5  # Base score

        # Date proximity (closer = better)
        if days_diff == 0:
            score += 0.3
        elif days_diff == 1:
            score += 0.2
        elif days_diff == 2:
            score += 0.1

        # Has image/media
        if post.is_image or post.media_url:
            score += 0.15

        # Has hail size mentioned
        if post.hail_size_inches:
            score += 0.1

        # Location match
        if storm_location and post.location_text:
            loc_lower = storm_location.lower()
            post_loc_lower = post.location_text.lower()
            if any(word in post_loc_lower for word in loc_lower.split()):
                score += 0.15

        # Engagement (popular posts more likely to be real)
        if post.score > 100:
            score += 0.1
        elif post.score > 50:
            score += 0.05

        return min(score, 1.0)

    def _process_post(
        self,
        storm_id: int,
        post,
        auto_analyze: bool = True
    ) -> Optional[int]:
        """
        Process a single post and create verification.

        Handles posts from multiple sources: Reddit, Twitter, Images

        Args:
            storm_id: ID of storm event
            post: Post object (Reddit, Twitter, or Image)
            auto_analyze: Whether to run ML analysis

        Returns:
            Verification ID if created, None otherwise
        """
        # Determine source
        source = getattr(post, 'source', 'reddit')
        post_id = getattr(post, 'post_id', str(hash(getattr(post, 'url', ''))))

        # Skip if verification manager not available
        if not self.verification_manager:
            logger.warning("Verification manager not available")
            return None

        # Check if already exists
        try:
            existing = self.verification_manager.search_verifications(
                source=source,
                limit=100
            )
            for v in existing:
                if v.get('post_id') == post_id:
                    logger.debug(f"Post {post_id} already exists as verification")
                    return None
        except Exception as e:
            logger.warning(f"Error checking existing verifications: {e}")

        # Extract fields based on source type
        if source == 'reddit':
            permalink = getattr(post, 'permalink', '')
            # Handle both relative and absolute permalinks
            if permalink.startswith('http'):
                post_url = permalink
            else:
                post_url = f"https://reddit.com{permalink}"
            author = getattr(post, 'author', '')
            title = getattr(post, 'title', '')
            content = getattr(post, 'selftext', '')[:1000] if getattr(post, 'selftext', '') else None
            posted_at = getattr(post, 'created_utc', datetime.now()).isoformat() if hasattr(post, 'created_utc') else None
            location_mentioned = getattr(post, 'location_text', None)
            hail_size_mentioned = getattr(post, 'hail_size_mentioned', None)
            hail_size_inches = getattr(post, 'hail_size_inches', None)
            likes = getattr(post, 'score', 0)
            comments = getattr(post, 'num_comments', 0)
        elif source == 'twitter':
            post_url = getattr(post, 'url', '')
            author = getattr(post, 'author', '')
            title = getattr(post, 'title', '')
            content = None
            posted_at = None
            location_mentioned = None
            hail_size_mentioned = None
            hail_size_inches = None
            likes = 0
            comments = 0
        else:  # images
            post_url = getattr(post, 'url', '')
            author = getattr(post, 'author', '')
            title = getattr(post, 'title', '')
            content = None
            posted_at = None
            location_mentioned = None
            hail_size_mentioned = None
            hail_size_inches = None
            likes = 0
            comments = 0

        # Get common fields
        photo_url = getattr(post, 'media_url', None)
        thumbnail_url = getattr(post, 'thumbnail_url', None)
        relevance_score = getattr(post, 'relevance_score', 0.5)
        is_image = getattr(post, 'is_image', False)

        # Create verification
        try:
            verification_id = self.verification_manager.add_verification(
                hail_event_id=storm_id,
                source=source,
                post_url=post_url,
                post_id=post_id,
                author=author,
                title=title,
                content=content,
                photo_url=photo_url,
                thumbnail_url=thumbnail_url,
                posted_at=posted_at,
                location_mentioned=location_mentioned,
                hail_size_mentioned=hail_size_mentioned,
                hail_size_inches=hail_size_inches,
                likes=likes,
                comments=comments,
                relevance_score=relevance_score
            )

            logger.info(f"Created verification {verification_id} for {source} post {post_id}")

            # Analyze photo if available
            if auto_analyze and is_image and photo_url and self.hail_estimator:
                try:
                    self._analyze_verification_photo(verification_id, photo_url)
                except Exception as e:
                    logger.warning(f"Photo analysis failed for {post_id}: {e}")

            return verification_id

        except Exception as e:
            logger.error(f"Error creating verification for {post_id}: {e}")
            return None

    def _analyze_verification_photo(
        self,
        verification_id: int,
        photo_url: str
    ) -> bool:
        """
        Download and analyze a verification photo.

        Args:
            verification_id: ID of verification record
            photo_url: URL of photo to analyze

        Returns:
            True if analysis succeeded
        """
        try:
            import requests
            import numpy as np
            from PIL import Image
            import io

            # Download image
            headers = {'User-Agent': 'HailTracker/1.0'}
            response = requests.get(photo_url, headers=headers, timeout=30)
            response.raise_for_status()

            # Convert to numpy array for ML model
            img = Image.open(io.BytesIO(response.content))
            img_array = np.array(img.convert('RGB'))

            # Run hail size estimation
            if self.hail_estimator:
                result = self.hail_estimator.estimate_size(img_array)

                # Check if hail detected (confidence > 30% and size > 0)
                hail_detected = result.get('confidence', 0) > 30 and result.get('estimated_size_inches', 0) > 0.25

                self.verification_manager.update_ai_analysis(
                    verification_id=verification_id,
                    estimated_size=result.get('estimated_size_inches', 0),
                    size_category=result.get('category', 'unknown'),
                    confidence=result.get('confidence', 0),
                    severity=result.get('severity', 'unknown'),
                    detected_hail=hail_detected
                )

                if hail_detected:
                    logger.info(
                        f"Verification {verification_id}: Detected {result.get('category')} "
                        f"hail ({result.get('estimated_size_inches', 0):.2f}\") - {result.get('confidence', 0):.0f}% confidence"
                    )
                    return True
                else:
                    logger.debug(f"Verification {verification_id}: No hail detected in image")

        except Exception as e:
            logger.error(f"Photo analysis error for verification {verification_id}: {e}")

        return False

    def get_verification_stats(self, storm_id: int = None) -> Dict:
        """
        Get statistics about verifications.

        Args:
            storm_id: Optional storm ID to filter by

        Returns:
            Dict with verification statistics
        """
        verifications = self.verification_manager.search_verifications(
            hail_event_id=storm_id,
            limit=1000
        )

        stats = {
            'total_verifications': len(verifications),
            'with_photos': 0,
            'with_videos': 0,
            'ai_analyzed': 0,
            'hail_detected': 0,
            'by_source': {},
            'by_size': {},
            'avg_confidence': 0,
        }

        confidence_sum = 0
        confidence_count = 0

        for v in verifications:
            if v.get('photo_url'):
                stats['with_photos'] += 1
            if v.get('video_url'):
                stats['with_videos'] += 1
            if v.get('ai_analyzed'):
                stats['ai_analyzed'] += 1
            if v.get('ai_detected_hail'):
                stats['hail_detected'] += 1

            # Count by source
            source = v.get('source', 'unknown')
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1

            # Count by size category
            size = v.get('ai_size_category') or v.get('hail_size_mentioned') or 'unknown'
            stats['by_size'][size] = stats['by_size'].get(size, 0) + 1

            # Average confidence
            if v.get('ai_confidence'):
                confidence_sum += v['ai_confidence']
                confidence_count += 1

        if confidence_count > 0:
            stats['avg_confidence'] = confidence_sum / confidence_count

        return stats

    def get_verification_quality_score(self, storm_id: int) -> Dict:
        """
        Calculate a quality score for storm verification.

        Higher scores indicate more reliable verification.

        Args:
            storm_id: Storm event ID

        Returns:
            Dict with quality score and breakdown
        """
        verifications = self.verification_manager.get_verifications_for_event(storm_id)

        if not verifications:
            return {
                'score': 0,
                'grade': 'F',
                'breakdown': {
                    'no_verifications': True
                }
            }

        score = 0
        breakdown = {
            'verification_count': len(verifications),
            'photo_count': 0,
            'video_count': 0,
            'ai_confirmed': 0,
            'high_engagement': 0,
            'multiple_sources': 0,
        }

        sources = set()

        for v in verifications:
            # Base points for having verifications
            score += 10

            # Points for photos
            if v.get('photo_url'):
                score += 15
                breakdown['photo_count'] += 1

            # Points for videos (more reliable)
            if v.get('video_url'):
                score += 20
                breakdown['video_count'] += 1

            # Points for AI confirmation
            if v.get('ai_detected_hail'):
                score += 25
                breakdown['ai_confirmed'] += 1

            # Points for high engagement (community validation)
            if v.get('likes', 0) > 50:
                score += 10
                breakdown['high_engagement'] += 1

            sources.add(v.get('source', 'unknown'))

        # Bonus for multiple sources
        if len(sources) > 1:
            score += 20
            breakdown['multiple_sources'] = len(sources)

        # Cap at 100
        score = min(score, 100)

        # Determine grade
        if score >= 80:
            grade = 'A'
        elif score >= 60:
            grade = 'B'
        elif score >= 40:
            grade = 'C'
        elif score >= 20:
            grade = 'D'
        else:
            grade = 'F'

        return {
            'score': score,
            'grade': grade,
            'breakdown': breakdown
        }

    def process_active_storms(
        self,
        days_back: int = 3,
        max_storms: int = 10,
        auto_analyze: bool = True
    ) -> Dict:
        """
        Process all active/recent storms to find verifications.

        Args:
            days_back: How many days of storms to process
            max_storms: Maximum storms to process
            auto_analyze: Whether to run ML analysis

        Returns:
            Summary of processing results
        """
        import sqlite3

        results = {
            'storms_processed': 0,
            'total_verifications': 0,
            'total_posts_found': 0,
            'storm_results': []
        }

        # Get recent storms from database
        db_path = self.db_path or str(PROJECT_ROOT / 'data' / 'hailtracker_crm.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT id, event_name, event_date,
                   center_lat, center_lon, max_hail_size
            FROM hail_events
            WHERE event_date >= ?
            ORDER BY event_date DESC
            LIMIT ?
        """, (cutoff_date, max_storms))

        storms = cursor.fetchall()

        # Get counts of existing photos per storm
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hail_event_id, COUNT(*) as photo_count
            FROM storm_verifications
            WHERE photo_url IS NOT NULL
            GROUP BY hail_event_id
        """)
        existing_photos = {row['hail_event_id']: row['photo_count'] for row in cursor.fetchall()}
        conn.close()

        MIN_PHOTOS_NEEDED = 5

        for storm in storms:
            storm_dict = dict(storm)
            storm_id = storm_dict['id']

            # Skip storms that already have enough photos
            current_photos = existing_photos.get(storm_id, 0)
            if current_photos >= MIN_PHOTOS_NEEDED:
                logger.info(f"Storm {storm_id} already has {current_photos} photos, skipping")
                results['storm_results'].append({
                    'storm_id': storm_id,
                    'skipped': True,
                    'existing_photos': current_photos
                })
                continue

            # Parse location and state from event_name
            # Format: "Dallas Severe Hail - Jan 19" or "City, State - Date"
            event_name = storm_dict.get('event_name', '')
            location = ''
            state = ''

            if event_name:
                # Try to extract city from event name
                name_parts = event_name.split(' - ')
                if name_parts:
                    location_part = name_parts[0]
                    # Remove severity words
                    for word in ['Severe', 'Moderate', 'Minor', 'Catastrophic', 'Hail', 'Storm']:
                        location_part = location_part.replace(word, '').strip()
                    location = location_part.strip()

                    # Try to detect state abbreviation (TX, OK, etc.)
                    state_map = {
                        'Dallas': 'TX', 'Fort Worth': 'TX', 'Houston': 'TX', 'Austin': 'TX', 'San Antonio': 'TX',
                        'Oklahoma City': 'OK', 'Norman': 'OK', 'Tulsa': 'OK',
                        'Wichita': 'KS', 'Topeka': 'KS',
                        'Denver': 'CO', 'Colorado Springs': 'CO',
                        'Wichita Falls': 'TX'
                    }
                    for city, st in state_map.items():
                        if city.lower() in location.lower():
                            state = st
                            break

            storm_result = self.find_verifications_for_storm(
                storm_id=storm_id,
                storm_location=location,
                storm_date=storm_dict['event_date'],
                storm_state=state,
                auto_analyze=auto_analyze
            )

            results['storms_processed'] += 1
            results['total_verifications'] += storm_result['verifications_added']
            results['total_posts_found'] += storm_result['posts_found']
            results['storm_results'].append(storm_result)

        logger.info(
            f"Processed {results['storms_processed']} storms, "
            f"found {results['total_posts_found']} posts, "
            f"added {results['total_verifications']} verifications"
        )

        return results

    def get_verification_stats(self) -> Dict:
        """Get statistics about verifications."""
        verifications = self.verification_manager.search_verifications(limit=1000)

        stats = {
            'total_verifications': len(verifications),
            'by_source': {},
            'with_photos': 0,
            'ai_analyzed': 0,
            'hail_detected': 0,
            'avg_confidence': 0,
        }

        confidences = []

        for v in verifications:
            # By source
            source = v.get('source', 'unknown')
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1

            # Photo stats
            if v.get('photo_url'):
                stats['with_photos'] += 1

            if v.get('ai_analyzed'):
                stats['ai_analyzed'] += 1
                if v.get('ai_detected_hail'):
                    stats['hail_detected'] += 1
                if v.get('ai_confidence'):
                    confidences.append(v['ai_confidence'])

        if confidences:
            stats['avg_confidence'] = sum(confidences) / len(confidences)

        return stats


# CLI for testing
if __name__ == '__main__':
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Storm Verification Pipeline')
    parser.add_argument('--storm-id', type=int, help='Process specific storm ID')
    parser.add_argument('--days', type=int, default=3, help='Days of storms to process')
    parser.add_argument('--max-storms', type=int, default=5, help='Max storms to process')
    parser.add_argument('--no-analyze', action='store_true', help='Skip ML analysis')
    parser.add_argument('--stats', action='store_true', help='Show verification stats')

    args = parser.parse_args()

    pipeline = StormVerificationPipeline()

    if args.stats:
        stats = pipeline.get_verification_stats()
        print("\n=== Verification Statistics ===")
        print(f"Total verifications: {stats['total_verifications']}")
        print(f"By source: {stats['by_source']}")
        print(f"With photos: {stats['with_photos']}")
        print(f"AI analyzed: {stats['ai_analyzed']}")
        print(f"Hail detected: {stats['hail_detected']}")
        print(f"Avg confidence: {stats['avg_confidence']:.1f}%")

    elif args.storm_id:
        # Need to get storm details from DB first
        import sqlite3
        from pathlib import Path

        db_path = str(Path(__file__).parent.parent.parent / 'data' / 'hailtracker_crm.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM hail_events WHERE id = ?",
            (args.storm_id,)
        )
        storm = cursor.fetchone()
        conn.close()

        if storm:
            storm = dict(storm)
            result = pipeline.find_verifications_for_storm(
                storm_id=args.storm_id,
                storm_location=storm.get('city') or storm.get('event_name', ''),
                storm_date=storm['event_date'],
                storm_state=storm.get('state'),
                auto_analyze=not args.no_analyze
            )
            print(f"\n=== Results for Storm {args.storm_id} ===")
            print(f"Posts found: {result['posts_found']}")
            print(f"Verifications added: {result['verifications_added']}")
            if result['errors']:
                print(f"Errors: {result['errors']}")
        else:
            print(f"Storm {args.storm_id} not found")

    else:
        results = pipeline.process_active_storms(
            days_back=args.days,
            max_storms=args.max_storms,
            auto_analyze=not args.no_analyze
        )

        print("\n=== Pipeline Results ===")
        print(f"Storms processed: {results['storms_processed']}")
        print(f"Total posts found: {results['total_posts_found']}")
        print(f"Total verifications added: {results['total_verifications']}")
