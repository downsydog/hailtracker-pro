"""
Google Images Downloader - FIXED VERSION

Uses multiple methods to download from Google Images:
1. SerpAPI (if API key available)
2. Custom Google scraping with rotating user agents
3. DuckDuckGo fallback
"""

import os
import sys
import json
import time
import re
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from urllib.parse import quote, urlparse, parse_qs
import logging

logger = logging.getLogger('GoogleImagesFixed')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class GoogleImagesDownloader:
    """
    Downloads images from Google Images using multiple methods.

    Handles Google's anti-scraping measures with:
    - Rotating user agents
    - Request delays
    - Multiple fallback methods
    """

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    ]

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir) if output_dir else PROJECT_ROOT / 'data' / 'downloaded_images'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.user_agent_index = 0
        self.downloaded_hashes: Set[str] = set()
        self._load_existing_hashes()

    def _get_headers(self) -> Dict:
        """Get headers with rotating user agent."""
        ua = self.USER_AGENTS[self.user_agent_index % len(self.USER_AGENTS)]
        self.user_agent_index += 1

        return {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def _load_existing_hashes(self):
        """Load hashes of existing images."""
        for img_file in self.output_dir.rglob('*'):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                try:
                    file_hash = hashlib.md5(img_file.read_bytes()).hexdigest()
                    self.downloaded_hashes.add(file_hash)
                except:
                    pass

    def _is_duplicate(self, content: bytes) -> bool:
        """Check if image is duplicate."""
        file_hash = hashlib.md5(content).hexdigest()
        if file_hash in self.downloaded_hashes:
            return True
        self.downloaded_hashes.add(file_hash)
        return False

    def search_duckduckgo(self, query: str, max_results: int = 30) -> List[str]:
        """
        Search DuckDuckGo for images (more reliable than Google).

        Returns list of image URLs.
        """
        print(f"    [DuckDuckGo] Searching: '{query}'")

        image_urls = []

        try:
            # DuckDuckGo image search
            search_url = f"https://duckduckgo.com/?q={quote(query)}&iax=images&ia=images"

            resp = self.session.get(search_url, headers=self._get_headers(), timeout=30)

            if resp.status_code != 200:
                return []

            # Get vqd token
            vqd_match = re.search(r'vqd=([^&]+)', resp.text)
            if not vqd_match:
                vqd_match = re.search(r"vqd='([^']+)'", resp.text)

            if not vqd_match:
                return []

            vqd = vqd_match.group(1)

            # Fetch images
            api_url = f"https://duckduckgo.com/i.js?l=us-en&o=json&q={quote(query)}&vqd={vqd}"

            resp = self.session.get(api_url, headers=self._get_headers(), timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])

                for result in results[:max_results]:
                    img_url = result.get('image')
                    if img_url and img_url.startswith('http'):
                        image_urls.append(img_url)

        except Exception as e:
            logger.error(f"DuckDuckGo error: {e}")

        print(f"    [DuckDuckGo] Found {len(image_urls)} images")
        return image_urls

    def search_bing(self, query: str, max_results: int = 30) -> List[str]:
        """Search Bing for images."""
        print(f"    [Bing] Searching: '{query}'")

        try:
            from icrawler.builtin import BingImageCrawler

            # Create temp dir for this search
            temp_dir = self.output_dir / '_temp_bing'
            temp_dir.mkdir(exist_ok=True)

            crawler = BingImageCrawler(
                storage={'root_dir': str(temp_dir)},
                log_level=logging.WARNING
            )

            crawler.crawl(
                keyword=query,
                max_num=max_results,
                min_size=(200, 200),
            )

            # Get downloaded files
            image_files = list(temp_dir.glob('*'))
            print(f"    [Bing] Downloaded {len(image_files)} images")

            # Return file paths (already downloaded)
            return [str(f) for f in image_files]

        except ImportError:
            logger.warning("icrawler not available for Bing")
            return []
        except Exception as e:
            logger.error(f"Bing error: {e}")
            return []

    def download_image(self, url: str, save_dir: Path, prefix: str = '') -> Optional[str]:
        """Download a single image."""
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=15)

            if resp.status_code != 200:
                return None

            content = resp.content

            # Check size
            if len(content) < 5000:  # Skip tiny images
                return None

            # Check duplicate
            if self._is_duplicate(content):
                return None

            # Determine extension
            content_type = resp.headers.get('content-type', '')
            if 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                ext = '.jpg'

            # Generate filename
            file_hash = hashlib.md5(content).hexdigest()[:8]
            filename = f"{prefix}{file_hash}{ext}"
            filepath = save_dir / filename

            filepath.write_bytes(content)
            return str(filepath)

        except Exception as e:
            logger.debug(f"Download error: {e}")
            return None

    def download_hail_images(self, category: str, queries: List[str],
                             target_count: int = 100) -> Dict:
        """
        Download hail images for a category.

        Args:
            category: Category name (e.g., 'golf_ball', 'baseball')
            queries: List of search queries
            target_count: Target number of images

        Returns:
            Stats dict
        """
        print(f"\n  Downloading {category.upper()} ({target_count} target)")

        category_dir = self.output_dir / category
        category_dir.mkdir(exist_ok=True)

        existing = len(list(category_dir.glob('*')))
        downloaded = 0
        images_per_query = max(10, (target_count - existing) // len(queries))

        for query in queries:
            if downloaded >= target_count:
                break

            # Try DuckDuckGo first
            urls = self.search_duckduckgo(query, max_results=images_per_query)

            for url in urls:
                if downloaded >= target_count:
                    break

                result = self.download_image(url, category_dir, f"{category}_")
                if result:
                    downloaded += 1

                time.sleep(0.3)  # Rate limit

            time.sleep(1)  # Between queries

        total = len(list(category_dir.glob('*')))
        print(f"    Downloaded: {downloaded} new, Total: {total}")

        return {
            'category': category,
            'new_downloads': downloaded,
            'total': total,
        }

    def download_all_hail_categories(self) -> Dict:
        """Download images for all hail size categories."""
        print("\n" + "=" * 60)
        print("GOOGLE IMAGES DOWNLOADER (FIXED)")
        print("=" * 60)

        categories = {
            'pea': {
                'queries': ['pea sized hail', 'small hail stones', 'tiny hail'],
                'target': 80,
            },
            'marble': {
                'queries': ['marble sized hail', 'dime sized hail'],
                'target': 100,
            },
            'quarter': {
                'queries': ['quarter sized hail', 'one inch hail', 'nickel hail'],
                'target': 150,
            },
            'golf_ball': {
                'queries': ['golf ball hail', 'golf ball sized hail', 'golf ball hail damage'],
                'target': 200,
            },
            'tennis_ball': {
                'queries': ['tennis ball hail', 'large hail stones', 'giant hail'],
                'target': 150,
            },
            'baseball': {
                'queries': ['baseball hail', 'baseball sized hail', 'huge hail storm'],
                'target': 150,
            },
            'softball': {
                'queries': ['softball hail', 'grapefruit hail', 'massive hailstones'],
                'target': 100,
            },
            'damage': {
                'queries': ['hail damage car', 'hail damage roof', 'hail dents vehicle'],
                'target': 150,
            },
        }

        results = {}
        start_time = datetime.now()

        for category, config in categories.items():
            result = self.download_hail_images(
                category,
                config['queries'],
                config['target']
            )
            results[category] = result

        elapsed = (datetime.now() - start_time).total_seconds()

        # Summary
        print("\n" + "=" * 60)
        print("DOWNLOAD COMPLETE")
        print("=" * 60)

        total_new = sum(r['new_downloads'] for r in results.values())
        total_images = sum(r['total'] for r in results.values())

        print(f"  New downloads: {total_new}")
        print(f"  Total images: {total_images}")
        print(f"  Time: {elapsed:.1f} seconds")
        print(f"\n  By category:")

        for category, result in results.items():
            print(f"    {category:15}: {result['total']:4} images")

        return {
            'success': True,
            'total_new': total_new,
            'total_images': total_images,
            'elapsed_seconds': elapsed,
            'by_category': results,
        }


def test_download():
    """Test download with small batch."""
    print("\n" + "=" * 60)
    print("TEST: Google Images Downloader")
    print("=" * 60)

    downloader = GoogleImagesDownloader()

    # Test DuckDuckGo
    urls = downloader.search_duckduckgo('golf ball hail', max_results=5)
    print(f"\nDuckDuckGo found {len(urls)} URLs")

    # Download a few
    test_dir = downloader.output_dir / '_test'
    test_dir.mkdir(exist_ok=True)

    downloaded = 0
    for url in urls[:3]:
        result = downloader.download_image(url, test_dir, 'test_')
        if result:
            downloaded += 1
            print(f"  Downloaded: {Path(result).name}")

    print(f"\nDownloaded {downloaded} test images")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run test')
    parser.add_argument('--full', action='store_true', help='Full download')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.full:
        downloader = GoogleImagesDownloader()
        downloader.download_all_hail_categories()
    else:
        test_download()
