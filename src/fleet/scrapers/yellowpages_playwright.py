"""
Yellow Pages Scraper using Playwright
======================================
Bypasses anti-bot protection using headless Chromium browser.
"""

from .headless_scraper import HeadlessScraper
from bs4 import BeautifulSoup
from typing import List, Dict
import re
import logging

logger = logging.getLogger('YellowPagesPlaywright')


class YellowPagesPlaywright(HeadlessScraper):
    """
    Yellow Pages scraper using headless browser.
    Bypasses 403 anti-bot protection.
    """

    BASE_URL = "https://www.yellowpages.com"

    # Categories for fleet-relevant businesses
    CATEGORIES = [
        # Landscaping & Lawn
        'landscaping', 'lawn-care', 'tree-service', 'irrigation',

        # HVAC
        'hvac', 'heating-contractors', 'air-conditioning', 'furnace-repair',

        # Plumbing
        'plumbers', 'plumbing-contractors', 'drain-cleaning',

        # Electrical
        'electricians', 'electrical-contractors',

        # Pest Control
        'pest-control', 'exterminators', 'termite-control',

        # Roofing
        'roofing-contractors', 'roofers', 'roof-repair',

        # General Contractors
        'general-contractors', 'contractors', 'remodeling',

        # Auto
        'auto-body-shops', 'auto-repair', 'car-dealers', 'towing',

        # Moving & Logistics
        'moving-companies', 'movers', 'storage',

        # Cleaning
        'cleaning-services', 'janitorial', 'carpet-cleaning',

        # Other Trades
        'painting-contractors', 'fencing-contractors', 'concrete-contractors',
        'garage-door-repair', 'locksmith', 'glass-repair',
        'flooring-contractors', 'gutter-contractors', 'foundation-repair',
        'water-damage-restoration', 'security-systems', 'septic-tank-service',
    ]

    # Priority categories (most likely to have fleet vehicles)
    PRIORITY_CATEGORIES = [
        'landscaping', 'hvac', 'plumbers', 'electricians',
        'pest-control', 'roofing-contractors', 'auto-body-shops',
        'towing', 'moving-companies', 'cleaning-services',
    ]

    def search(self, city: str, state: str, category: str, max_pages: int = 2) -> List[Dict]:
        """
        Search Yellow Pages for businesses.

        Args:
            city: City name
            state: State abbreviation (e.g., 'OK')
            category: Business category to search
            max_pages: Maximum pages to scrape

        Returns:
            List of business dictionaries
        """
        results = []

        for page_num in range(1, max_pages + 1):
            # Build URL
            location = f"{city}, {state}".replace(' ', '+')
            url = f"{self.BASE_URL}/search?search_terms={category}&geo_location_terms={location}"
            if page_num > 1:
                url += f"&page={page_num}"

            try:
                logger.info(f"[YP] Fetching: {category} in {city}, {state} (page {page_num})")

                # Navigate to page
                if not self.safe_goto(url, timeout=30000):
                    logger.error(f"[YP] Failed to load page {page_num}")
                    break

                # Wait for content to load
                self.random_delay(1.5, 3.0)
                self.scroll_page()
                self.random_delay(0.5, 1.5)

                # Get and parse HTML
                html = self.get_page_content()
                page_results = self._parse_results(html, category)

                if not page_results:
                    logger.info(f"[YP] No results on page {page_num}, stopping")
                    break

                results.extend(page_results)
                logger.info(f"[YP] Found {len(page_results)} on page {page_num}")

                # Delay between pages
                if page_num < max_pages:
                    self.random_delay(2.0, 4.0)

            except Exception as e:
                logger.error(f"[YP] Error on page {page_num}: {e}")
                break

        return results

    def _parse_results(self, html: str, category: str) -> List[Dict]:
        """Parse search results from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # Find all result cards - Yellow Pages uses various selectors
        listings = (
            soup.select('.result') or
            soup.select('.srp-listing') or
            soup.select('[class*="result"]') or
            soup.select('.organic') or
            soup.find_all('div', {'class': re.compile(r'result|listing', re.I)})
        )

        for listing in listings:
            try:
                business = self._parse_listing(listing, category)
                if business and business.get('name'):
                    results.append(business)
            except Exception as e:
                logger.debug(f"Parse error: {e}")
                continue

        return results

    def _parse_listing(self, listing, category: str) -> Dict:
        """Parse a single listing."""
        business = {
            'name': '',
            'phone': '',
            'address': '',
            'city': '',
            'state': '',
            'zip': '',
            'website': '',
            'category': category,
            'source': 'yellowpages',
        }

        # Name
        name_el = (
            listing.select_one('.business-name') or
            listing.select_one('a.business-name') or
            listing.select_one('[class*="business-name"]') or
            listing.select_one('h2 a') or
            listing.select_one('h3 a')
        )
        if not name_el:
            return None

        name = name_el.get_text(strip=True)

        # Skip ads and sponsored content
        if not name or 'ad' in name.lower() or 'sponsored' in name.lower():
            return None

        business['name'] = name

        # Phone
        phone_el = (
            listing.select_one('.phones') or
            listing.select_one('.phone') or
            listing.select_one('[class*="phone"]') or
            listing.select_one('a[href^="tel:"]')
        )
        if phone_el:
            phone = phone_el.get_text(strip=True)
            if not phone and phone_el.get('href'):
                phone = phone_el.get('href').replace('tel:', '')
            business['phone'] = self._clean_phone(phone)

        # Address
        street_el = listing.select_one('.street-address') or listing.select_one('[class*="street"]')
        locality_el = listing.select_one('.locality') or listing.select_one('[class*="locality"]')

        if street_el:
            business['address'] = street_el.get_text(strip=True)
        if locality_el:
            locality_text = locality_el.get_text(strip=True)
            # Parse "City, ST 12345"
            match = re.match(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', locality_text)
            if match:
                business['city'] = match.group(1).strip()
                business['state'] = match.group(2)
                business['zip'] = match.group(3) or ''

        # Website
        website_el = (
            listing.select_one('a.track-visit-website') or
            listing.select_one('[class*="website"]') or
            listing.select_one('a[href*="http"]:not([href*="yellowpages"])')
        )
        if website_el:
            href = website_el.get('href', '')
            if href and 'yellowpages' not in href.lower():
                business['website'] = href

        return business

    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number."""
        if not phone:
            return ''

        # Extract digits
        digits = re.sub(r'[^\d]', '', phone)

        # Format as (XXX) XXX-XXXX
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            digits = digits[1:]
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

        return phone

    def search_priority_categories(self, city: str, state: str, max_pages_per_category: int = 1) -> List[Dict]:
        """
        Search only priority categories (faster).

        Args:
            city: City name
            state: State abbreviation
            max_pages_per_category: Max pages per category

        Returns:
            Combined list of businesses
        """
        return self.search_multiple_categories(
            city, state,
            self.PRIORITY_CATEGORIES,
            max_pages_per_category
        )

    def search_multiple_categories(
        self,
        city: str,
        state: str,
        categories: List[str] = None,
        max_pages_per_category: int = 1
    ) -> List[Dict]:
        """
        Search multiple categories.

        Args:
            city: City name
            state: State abbreviation
            categories: List of categories (uses PRIORITY_CATEGORIES if None)
            max_pages_per_category: Max pages per category

        Returns:
            Combined list of unique businesses
        """
        if categories is None:
            categories = self.PRIORITY_CATEGORIES

        all_results = []
        seen_names = set()

        for category in categories:
            try:
                results = self.search(city, state, category, max_pages_per_category)

                # Deduplicate by name
                for biz in results:
                    name_key = biz.get('name', '').lower().strip()
                    if name_key and name_key not in seen_names:
                        seen_names.add(name_key)
                        all_results.append(biz)

                # Delay between categories
                self.random_delay(2.0, 4.0)

            except Exception as e:
                logger.error(f"Category {category} error: {e}")
                continue

        logger.info(f"[YP] Total unique businesses: {len(all_results)}")
        return all_results


# Test function
def test_yellowpages():
    """Test Yellow Pages scraper."""
    print("Testing Yellow Pages Playwright scraper...")

    with YellowPagesPlaywright() as yp:
        results = yp.search('Oklahoma City', 'OK', 'landscaping', max_pages=1)
        print(f"\nFound {len(results)} results:")

        for r in results[:10]:
            print(f"  - {r.get('name')}")
            print(f"    Phone: {r.get('phone')}")
            print(f"    Address: {r.get('address')}")
            print()

    return results


if __name__ == '__main__':
    test_yellowpages()
