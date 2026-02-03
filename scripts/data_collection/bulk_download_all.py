"""
Bulk Hail Photo Downloader - REAL DATA COLLECTION

Downloads 1,000+ hail photos from Google Images using icrawler.
Automatically organizes by hail size categories.
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from icrawler.builtin import GoogleImageCrawler, BingImageCrawler
    ICRAWLER_AVAILABLE = True
except ImportError:
    ICRAWLER_AVAILABLE = False
    print("ERROR: icrawler not installed. Run: pip install icrawler")

logger = logging.getLogger('BulkHailDownloader')


class BulkHailDownloader:
    """
    Downloads and organizes hail photos by size category.

    Categories based on NWS hail size scale:
    - pea: < 0.25" (small)
    - marble: 0.5" (small)
    - penny: 0.75"
    - nickel: 0.88"
    - quarter: 1" (severe threshold)
    - half_dollar: 1.25"
    - golf_ball: 1.75" (significant)
    - tennis_ball: 2.5"
    - baseball: 2.75" (giant)
    - softball: 4"+ (gorilla)
    """

    # Search queries organized by hail size
    SIZE_CATEGORIES = {
        'pea': {
            'size_inches': 0.25,
            'queries': [
                'pea sized hail',
                'small hail stones',
                'tiny hail pellets',
                'pea hail storm',
            ],
            'target_count': 80,
        },
        'marble': {
            'size_inches': 0.5,
            'queries': [
                'marble sized hail',
                'marble hail stones',
                'dime sized hail',
            ],
            'target_count': 100,
        },
        'quarter': {
            'size_inches': 1.0,
            'queries': [
                'quarter sized hail',
                'quarter hail damage',
                'one inch hail',
                'severe hail storm quarter',
                'nickel sized hail',
            ],
            'target_count': 150,
        },
        'golf_ball': {
            'size_inches': 1.75,
            'queries': [
                'golf ball hail',
                'golf ball sized hail',
                'golf ball hail damage',
                'large hail storm',
                'golf ball hailstones',
                'hail golf ball car',
            ],
            'target_count': 200,
        },
        'tennis_ball': {
            'size_inches': 2.5,
            'queries': [
                'tennis ball hail',
                'tennis ball sized hail',
                'giant hail stones',
                'tennis ball hail damage',
            ],
            'target_count': 150,
        },
        'baseball': {
            'size_inches': 2.75,
            'queries': [
                'baseball hail',
                'baseball sized hail',
                'baseball hail damage',
                'huge hail storm',
                'baseball hailstones car',
            ],
            'target_count': 150,
        },
        'softball': {
            'size_inches': 4.0,
            'queries': [
                'softball hail',
                'softball sized hail',
                'grapefruit hail',
                'giant hail record',
                'massive hailstones',
            ],
            'target_count': 100,
        },
        'damage': {
            'size_inches': None,  # Mixed sizes, focus on damage
            'queries': [
                'hail damage car',
                'hail damage roof',
                'hail damage windshield',
                'hail dents vehicle',
                'storm hail damage',
            ],
            'target_count': 150,
        },
    }

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize downloader."""
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / 'data' / 'training_images'
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create category directories
        for category in self.SIZE_CATEGORIES:
            (self.data_dir / category).mkdir(exist_ok=True)

        # Track downloaded files to avoid duplicates
        self.downloaded_hashes = set()
        self._load_existing_hashes()

        # Stats
        self.stats = {
            'total_downloaded': 0,
            'duplicates_skipped': 0,
            'errors': 0,
            'by_category': {cat: 0 for cat in self.SIZE_CATEGORIES},
        }

    def _load_existing_hashes(self):
        """Load hashes of existing images to avoid re-downloading."""
        for category_dir in self.data_dir.iterdir():
            if category_dir.is_dir():
                for img_file in category_dir.glob('*'):
                    if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        try:
                            file_hash = hashlib.md5(img_file.read_bytes()).hexdigest()
                            self.downloaded_hashes.add(file_hash)
                        except Exception:
                            pass

        if self.downloaded_hashes:
            print(f"  Loaded {len(self.downloaded_hashes)} existing image hashes")

    def _remove_duplicates(self, category_dir: Path) -> int:
        """Remove duplicate images from a directory after download."""
        removed = 0
        seen_hashes = {}

        for img_file in sorted(category_dir.glob('*')):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                try:
                    file_hash = hashlib.md5(img_file.read_bytes()).hexdigest()

                    if file_hash in seen_hashes:
                        # Duplicate - remove it
                        img_file.unlink()
                        removed += 1
                    elif file_hash in self.downloaded_hashes:
                        # Already have this image in another category
                        img_file.unlink()
                        removed += 1
                    else:
                        seen_hashes[file_hash] = img_file
                        self.downloaded_hashes.add(file_hash)
                except Exception as e:
                    logger.error(f"Error checking {img_file}: {e}")

        return removed

    def download_category(self, category: str, max_images: int = None,
                         use_bing: bool = False) -> Dict:
        """
        Download images for a single category.

        Args:
            category: Category name from SIZE_CATEGORIES
            max_images: Override max images (default: use target_count)
            use_bing: Use Bing instead of Google

        Returns:
            Dict with download stats
        """
        if not ICRAWLER_AVAILABLE:
            raise RuntimeError("icrawler not installed")

        if category not in self.SIZE_CATEGORIES:
            raise ValueError(f"Unknown category: {category}")

        config = self.SIZE_CATEGORIES[category]
        queries = config['queries']
        target = max_images or config['target_count']

        category_dir = self.data_dir / category
        category_dir.mkdir(exist_ok=True)

        images_per_query = max(10, target // len(queries))

        print(f"\n  >> Downloading {category.upper()} ({config.get('size_inches', 'mixed')} inches)")
        print(f"     Target: {target} images from {len(queries)} queries")

        total_before = len(list(category_dir.glob('*')))

        for i, query in enumerate(queries):
            print(f"     [{i+1}/{len(queries)}] Searching: '{query}'...")

            try:
                # Create crawler for this query
                if use_bing:
                    crawler = BingImageCrawler(
                        storage={'root_dir': str(category_dir)},
                        log_level=logging.WARNING
                    )
                else:
                    crawler = GoogleImageCrawler(
                        storage={'root_dir': str(category_dir)},
                        log_level=logging.WARNING
                    )

                # Crawl images
                crawler.crawl(
                    keyword=query,
                    max_num=images_per_query,
                    min_size=(200, 200),  # Minimum 200x200 pixels
                    file_idx_offset='auto',
                )

            except Exception as e:
                logger.error(f"Error crawling '{query}': {e}")
                self.stats['errors'] += 1

        # Remove duplicates
        duplicates_removed = self._remove_duplicates(category_dir)

        total_after = len(list(category_dir.glob('*')))
        new_images = total_after - total_before + duplicates_removed

        self.stats['by_category'][category] = total_after
        self.stats['total_downloaded'] += new_images
        self.stats['duplicates_skipped'] += duplicates_removed

        print(f"     Downloaded: {new_images} new images ({duplicates_removed} duplicates removed)")
        print(f"     Total in category: {total_after}")

        return {
            'category': category,
            'new_images': new_images,
            'total_images': total_after,
            'duplicates_removed': duplicates_removed,
        }

    def download_all(self, max_per_category: int = None,
                    categories: List[str] = None,
                    use_bing: bool = False) -> Dict:
        """
        Download images for all categories.

        Args:
            max_per_category: Override max images per category
            categories: Specific categories to download (default: all)
            use_bing: Use Bing instead of Google

        Returns:
            Dict with full download stats
        """
        categories = categories or list(self.SIZE_CATEGORIES.keys())

        print(f"\n{'='*60}")
        print(f"BULK HAIL PHOTO DOWNLOADER")
        print(f"{'='*60}")
        print(f"  Data directory: {self.data_dir}")
        print(f"  Categories: {len(categories)}")
        print(f"  Engine: {'Bing' if use_bing else 'Google'} Images")

        start_time = datetime.now()

        for category in categories:
            try:
                self.download_category(category, max_per_category, use_bing)
            except Exception as e:
                logger.error(f"Failed to download {category}: {e}")
                self.stats['errors'] += 1

        elapsed = (datetime.now() - start_time).total_seconds()

        # Final summary
        print(f"\n{'='*60}")
        print(f"DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"  Total images: {sum(self.stats['by_category'].values())}")
        print(f"  Duplicates skipped: {self.stats['duplicates_skipped']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Time: {elapsed:.1f} seconds")
        print(f"\n  By category:")

        for cat, count in self.stats['by_category'].items():
            size = self.SIZE_CATEGORIES[cat].get('size_inches')
            size_str = f"{size:>5}" if size else "mixed"
            print(f"    {cat:15} ({size_str}\"): {count:4} images")

        return {
            'success': True,
            'total_images': sum(self.stats['by_category'].values()),
            'by_category': self.stats['by_category'],
            'duplicates_skipped': self.stats['duplicates_skipped'],
            'errors': self.stats['errors'],
            'elapsed_seconds': elapsed,
            'data_dir': str(self.data_dir),
        }

    def get_training_manifest(self) -> Dict:
        """
        Generate a manifest of all downloaded images for ML training.

        Returns:
            Dict with image paths and labels
        """
        manifest = {
            'generated': datetime.now().isoformat(),
            'data_dir': str(self.data_dir),
            'categories': {},
            'total_images': 0,
        }

        for category, config in self.SIZE_CATEGORIES.items():
            category_dir = self.data_dir / category
            if not category_dir.exists():
                continue

            images = []
            for img_file in category_dir.glob('*'):
                if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    images.append({
                        'path': str(img_file),
                        'filename': img_file.name,
                        'size_inches': config.get('size_inches'),
                    })

            manifest['categories'][category] = {
                'count': len(images),
                'size_inches': config.get('size_inches'),
                'images': images,
            }
            manifest['total_images'] += len(images)

        return manifest


def test_download(num_images: int = 50):
    """
    Test download with a small batch.

    Args:
        num_images: Total images to download across categories
    """
    print(f"\n{'='*60}")
    print(f"TEST DOWNLOAD - {num_images} images")
    print(f"{'='*60}")

    downloader = BulkHailDownloader()

    # Download small batch from key categories
    test_categories = ['quarter', 'golf_ball', 'baseball']
    per_category = num_images // len(test_categories)

    results = downloader.download_all(
        max_per_category=per_category,
        categories=test_categories,
        use_bing=True  # Bing works better (Google blocks crawlers)
    )

    # Generate manifest
    manifest = downloader.get_training_manifest()

    print(f"\n  Training manifest generated:")
    print(f"    Total images: {manifest['total_images']}")
    for cat, data in manifest['categories'].items():
        print(f"    {cat}: {data['count']} images")

    return results


def full_download():
    """Download full dataset (1,000+ images)."""
    print(f"\n{'='*60}")
    print(f"FULL DOWNLOAD - 1,000+ images")
    print(f"{'='*60}")

    downloader = BulkHailDownloader()

    # Download all categories using Bing (Google blocks crawlers)
    results = downloader.download_all(use_bing=True)

    # Generate and save manifest
    manifest = downloader.get_training_manifest()

    manifest_path = downloader.data_dir / 'training_manifest.json'
    import json
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n  Manifest saved to: {manifest_path}")
    print(f"  Total training images: {manifest['total_images']}")

    return results


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Bulk Hail Photo Downloader')
    parser.add_argument('--test', action='store_true', help='Run test download (50 images)')
    parser.add_argument('--full', action='store_true', help='Run full download (1,000+ images)')
    parser.add_argument('--count', type=int, default=50, help='Number of test images')
    parser.add_argument('--category', type=str, help='Download specific category only')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.category:
        downloader = BulkHailDownloader()
        downloader.download_category(args.category, max_images=args.count)
    elif args.full:
        full_download()
    else:
        test_download(args.count)
