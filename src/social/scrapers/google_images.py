"""
Google Images Scraper for Hail Photos

Searches Google Images for hail photos by location and date.
No API key required - uses web scraping.
"""

import re
import time
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import quote, urlencode
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger('GoogleImagesScraper')


@dataclass
class ImageResult:
    """Represents a Google Images search result."""
    url: str
    thumbnail_url: str
    source_url: str
    title: str
    source_domain: str
    width: int = 0
    height: int = 0


class GoogleImagesScraper:
    """
    Scrapes Google Images for hail-related photos.

    Uses Google's image search without API key.
    """

    SEARCH_URL = 'https://www.google.com/search'

    def __init__(self, rate_limit_seconds: float = 2.0):
        self.rate_limit = rate_limit_seconds
        self.last_request_time = 0

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def search_hail_photos(
        self,
        location: str,
        date: Optional[str] = None,
        max_results: int = 20
    ) -> List[ImageResult]:
        """
        Search for hail photos by location.

        Args:
            location: City, state, or region
            date: Optional date string (e.g., "May 2024", "2024")
            max_results: Maximum images to return

        Returns:
            List of ImageResult objects
        """
        # Build search query
        query_parts = ['hail storm', location]
        if date:
            query_parts.append(date)

        query = ' '.join(query_parts)

        return self._search(query, max_results)

    def search_hail_damage(
        self,
        location: str,
        damage_type: str = 'car',
        max_results: int = 20
    ) -> List[ImageResult]:
        """
        Search for hail damage photos.

        Args:
            location: City, state, or region
            damage_type: 'car', 'roof', 'vehicle', 'property'
            max_results: Maximum images to return
        """
        query = f'hail {damage_type} damage {location}'
        return self._search(query, max_results)

    def _search(self, query: str, max_results: int = 20) -> List[ImageResult]:
        """
        Perform image search.
        """
        self._rate_limit()

        params = {
            'q': query,
            'tbm': 'isch',  # Image search
            'hl': 'en',
            'safe': 'off',
        }

        try:
            response = self.session.get(
                self.SEARCH_URL,
                params=params,
                timeout=15
            )
            response.raise_for_status()

            return self._parse_results(response.text, max_results)

        except Exception as e:
            logger.error(f"Google Images search failed: {e}")
            return []

    def _parse_results(self, html: str, max_results: int) -> List[ImageResult]:
        """
        Parse image URLs from Google search results.
        """
        results = []

        # Pattern to extract image data from Google's JSON-like structure
        # Google embeds image data in script tags

        # Look for image URLs in the page
        # Pattern for direct image URLs
        img_patterns = [
            r'"ou":"(https?://[^"]+\.(?:jpg|jpeg|png|gif|webp)[^"]*)"',
            r'"tu":"(https?://[^"]+)"',  # Thumbnail URLs
            r'data-src="(https?://[^"]+\.(?:jpg|jpeg|png|gif|webp)[^"]*)"',
        ]

        found_urls = set()

        for pattern in img_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for url in matches:
                # Clean URL
                url = url.replace('\\u003d', '=').replace('\\u0026', '&')

                # Skip Google's own images
                if 'google.com' in url or 'gstatic.com' in url:
                    continue

                # Skip tiny images
                if 'favicon' in url.lower() or 'icon' in url.lower():
                    continue

                if url not in found_urls:
                    found_urls.add(url)

                    if len(results) >= max_results:
                        break

                    results.append(ImageResult(
                        url=url,
                        thumbnail_url=url,
                        source_url=url,
                        title=f"Hail photo",
                        source_domain=self._extract_domain(url)
                    ))

        # Also try to extract from data attributes
        data_pattern = r'\["(https?://[^"]+\.(?:jpg|jpeg|png|gif|webp)[^"]*)",\s*\d+,\s*\d+\]'
        matches = re.findall(data_pattern, html)

        for url in matches:
            url = url.replace('\\u003d', '=').replace('\\u0026', '&')
            if url not in found_urls and 'google.com' not in url:
                found_urls.add(url)

                if len(results) >= max_results:
                    break

                results.append(ImageResult(
                    url=url,
                    thumbnail_url=url,
                    source_url=url,
                    title="Hail photo",
                    source_domain=self._extract_domain(url)
                ))

        return results[:max_results]

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return 'unknown'


# Use Bing Images which is more reliable for scraping
class DuckDuckGoImagesScraper:
    """
    Scrapes Bing Images - more reliable than DuckDuckGo.
    Falls back to simple web search parsing.
    """

    BING_SEARCH_URL = 'https://www.bing.com/images/search'

    def __init__(self, rate_limit_seconds: float = 1.5):
        self.rate_limit = rate_limit_seconds
        self.last_request_time = 0

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def search_hail_photos(
        self,
        location: str,
        date: Optional[str] = None,
        max_results: int = 20
    ) -> List[ImageResult]:
        """Search Bing Images for hail photos."""
        query_parts = ['hail storm', location]
        if date:
            query_parts.append(date)

        query = ' '.join(query_parts)

        self._rate_limit()

        try:
            # Search Bing Images
            resp = self.session.get(
                self.BING_SEARCH_URL,
                params={'q': query, 'form': 'HDRSC2'},
                timeout=15
            )

            if resp.status_code != 200:
                logger.warning(f"Bing search returned status {resp.status_code}")
                return []

            return self._parse_bing_results(resp.text, max_results)

        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []

    def _parse_bing_results(self, html: str, max_results: int) -> List[ImageResult]:
        """Parse image URLs from Bing search results (updated for 2025-2026)."""
        results = []

        # Bing's HTML structure changed - use broader pattern to find image URLs
        all_image_urls = re.findall(
            r'(https?://[a-zA-Z0-9_./-]+\.(?:jpg|jpeg|png|webp|gif))',
            html,
            re.IGNORECASE
        )

        # Also try legacy patterns
        legacy_patterns = [
            r'"murl":"(https?://[^"]+)"',
            r'"turl":"(https?://[^"]+)"',
            r'imgurl=(https?://[^&"]+)',
        ]
        for pattern in legacy_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            all_image_urls.extend(matches)

        found_urls = set()

        for url in all_image_urls:
            # Decode URL
            url = url.replace('\\u002f', '/').replace('\\u003a', ':').replace('\\u0026', '&')
            url = url.replace('%3A', ':').replace('%2F', '/')

            # Skip Bing's own resources
            skip_domains = ['bing.com', 'bing.net', 'microsoft.com', 'msn.com', 'live.com']
            if any(x in url.lower() for x in skip_domains):
                continue

            # Skip tiny/utility images
            skip_keywords = ['favicon', 'icon', 'logo', 'pixel', '1x1', 'blank', 'spacer']
            if any(x in url.lower() for x in skip_keywords):
                continue

            if url not in found_urls and len(results) < max_results:
                found_urls.add(url)
                results.append(ImageResult(
                    url=url,
                    thumbnail_url=url,
                    source_url=url,
                    title="Hail photo",
                    source_domain=self._extract_domain(url)
                ))

        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return 'unknown'


# Test
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("Testing DuckDuckGo Images...")
    ddg = DuckDuckGoImagesScraper()
    results = ddg.search_hail_photos('Dallas Texas', 'May 2024', max_results=5)

    print(f"Found {len(results)} images:")
    for r in results:
        print(f"  - {r.title[:40]}... ({r.source_domain})")
        print(f"    URL: {r.url[:60]}...")
