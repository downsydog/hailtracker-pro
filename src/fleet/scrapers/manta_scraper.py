"""
Manta.com Business Scraper
==========================
Scrapes business listings from Manta.com national directory.

URL pattern: https://www.manta.com/search?search_source=nav&search={category}&location={city}%2C+{state}
"""

import requests
from bs4 import BeautifulSoup
import time
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus

logger = logging.getLogger('MantaScraper')


class MantaScraper:
    """
    Scraper for Manta.com business directory.

    Manta is a large US business directory with good coverage
    of service businesses (landscaping, HVAC, plumbing, etc.)
    """

    BASE_URL = "https://www.manta.com/search"

    # Category mappings for common fleet business types
    CATEGORIES = {
        'landscaping': 'landscaping',
        'hvac': 'hvac',
        'plumbing': 'plumbing',
        'electrical': 'electrical contractor',
        'pest_control': 'pest control',
        'roofing': 'roofing',
        'auto_body': 'auto body',
        'car_dealer': 'car dealer',
        'trucking': 'trucking',
        'moving': 'moving company',
        'construction': 'construction',
        'cleaning': 'cleaning service',
        'tree_service': 'tree service',
        'painting': 'painting contractor',
        'flooring': 'flooring',
    }

    def __init__(self, delay_seconds: float = 2.0):
        """
        Initialize Manta scraper.

        Args:
            delay_seconds: Delay between requests to avoid rate limiting
        """
        self.delay = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def search(self, city: str, state: str, category: str, max_pages: int = 3) -> List[Dict]:
        """
        Search Manta for businesses.

        Args:
            city: City name
            state: State abbreviation (e.g., 'OK')
            category: Business category to search
            max_pages: Maximum pages to scrape (20 results per page)

        Returns:
            List of business dictionaries
        """
        all_results = []

        # Map category if needed
        search_term = self.CATEGORIES.get(category, category)
        location = f"{city}, {state}"

        for page in range(1, max_pages + 1):
            try:
                results = self._scrape_page(search_term, location, page)

                if not results:
                    logger.info(f"No more results on page {page}")
                    break

                all_results.extend(results)
                logger.info(f"Page {page}: found {len(results)} results")

                # Rate limiting
                if page < max_pages:
                    time.sleep(self.delay)

            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                break

        return all_results

    def _scrape_page(self, search_term: str, location: str, page: int = 1) -> List[Dict]:
        """Scrape a single page of Manta results."""

        params = {
            'search_source': 'nav',
            'search': search_term,
            'location': location,
        }

        if page > 1:
            params['pg'] = page

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=15
            )

            if response.status_code == 403:
                logger.error("Manta returned 403 Forbidden - blocked")
                return []

            if response.status_code == 429:
                logger.error("Manta returned 429 Too Many Requests - rate limited")
                return []

            if response.status_code != 200:
                logger.error(f"Manta returned status {response.status_code}")
                return []

            return self._parse_results(response.text)

        except requests.Timeout:
            logger.error("Manta request timed out")
            return []
        except Exception as e:
            logger.error(f"Manta request error: {e}")
            return []

    def _parse_results(self, html: str) -> List[Dict]:
        """Parse Manta search results page."""
        businesses = []

        soup = BeautifulSoup(html, 'html.parser')

        # Find business listings - Manta uses various card structures
        # Try multiple selectors
        listings = soup.select('.search-card, .results-card, [data-testid="search-result"]')

        if not listings:
            # Alternative selector
            listings = soup.select('.card, .business-card, .listing')

        if not listings:
            # Try finding by common patterns
            listings = soup.find_all('div', class_=re.compile(r'(search|result|listing|card)', re.I))

        for listing in listings:
            try:
                business = self._parse_listing(listing)
                if business and business.get('name'):
                    businesses.append(business)
            except Exception as e:
                logger.debug(f"Error parsing listing: {e}")
                continue

        return businesses

    def _parse_listing(self, listing) -> Optional[Dict]:
        """Parse a single business listing."""
        business = {
            'name': '',
            'address': '',
            'city': '',
            'state': '',
            'zip': '',
            'phone': '',
            'website': '',
            'category': '',
            'source': 'manta',
            'manta_url': '',
        }

        # Extract name - try multiple patterns
        name_elem = (
            listing.select_one('h2 a, h3 a, .business-name, .company-name, [data-testid="company-name"]') or
            listing.select_one('a[href*="/c/"]') or
            listing.find('a', href=re.compile(r'/c/'))
        )

        if name_elem:
            business['name'] = name_elem.get_text(strip=True)
            href = name_elem.get('href', '')
            if href:
                business['manta_url'] = f"https://www.manta.com{href}" if href.startswith('/') else href

        # Extract address
        address_elem = (
            listing.select_one('.address, .street-address, [data-testid="address"]') or
            listing.find(class_=re.compile(r'address', re.I))
        )
        if address_elem:
            business['address'] = address_elem.get_text(strip=True)

        # Extract city/state/zip
        location_elem = (
            listing.select_one('.city-state, .locality, [data-testid="location"]') or
            listing.find(class_=re.compile(r'(city|location|locality)', re.I))
        )
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            # Parse "City, ST 12345" format
            match = re.match(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', location_text)
            if match:
                business['city'] = match.group(1).strip()
                business['state'] = match.group(2)
                business['zip'] = match.group(3) or ''

        # Extract phone
        phone_elem = (
            listing.select_one('.phone, [data-testid="phone"], a[href^="tel:"]') or
            listing.find('a', href=re.compile(r'^tel:'))
        )
        if phone_elem:
            phone_text = phone_elem.get('href', '') or phone_elem.get_text(strip=True)
            phone_text = phone_text.replace('tel:', '')
            # Clean phone number
            phone_clean = re.sub(r'[^\d]', '', phone_text)
            if len(phone_clean) == 10:
                business['phone'] = f"({phone_clean[:3]}) {phone_clean[3:6]}-{phone_clean[6:]}"
            elif len(phone_clean) == 11 and phone_clean[0] == '1':
                phone_clean = phone_clean[1:]
                business['phone'] = f"({phone_clean[:3]}) {phone_clean[3:6]}-{phone_clean[6:]}"
            else:
                business['phone'] = phone_text

        # Extract website
        website_elem = listing.select_one('a[href*="website"], a.website, [data-testid="website"]')
        if website_elem:
            business['website'] = website_elem.get('href', '')

        # Extract category
        category_elem = (
            listing.select_one('.category, .industry, [data-testid="category"]') or
            listing.find(class_=re.compile(r'(category|industry)', re.I))
        )
        if category_elem:
            business['category'] = category_elem.get_text(strip=True)

        return business if business['name'] else None

    def search_multiple_categories(
        self,
        city: str,
        state: str,
        categories: List[str] = None,
        max_pages_per_category: int = 2
    ) -> List[Dict]:
        """
        Search multiple categories in a city.

        Args:
            city: City name
            state: State abbreviation
            categories: List of categories (uses all if None)
            max_pages_per_category: Max pages to scrape per category

        Returns:
            Combined list of unique businesses
        """
        if categories is None:
            categories = list(self.CATEGORIES.keys())

        all_results = []
        seen_names = set()

        for category in categories:
            logger.info(f"Searching Manta for {category} in {city}, {state}")

            results = self.search(city, state, category, max_pages_per_category)

            # Deduplicate by name
            for biz in results:
                name_key = biz.get('name', '').lower().strip()
                if name_key and name_key not in seen_names:
                    seen_names.add(name_key)
                    all_results.append(biz)

            # Delay between categories
            time.sleep(self.delay)

        return all_results

    def test_connection(self) -> Dict:
        """
        Test if Manta is accessible and not blocking.

        Returns:
            Status dict with success flag and message
        """
        try:
            response = self.session.get(
                self.BASE_URL,
                params={
                    'search_source': 'nav',
                    'search': 'landscaping',
                    'location': 'Oklahoma City, OK'
                },
                timeout=15
            )

            if response.status_code == 200:
                # Check if we got actual results or an error page
                if 'search-card' in response.text or 'results' in response.text.lower():
                    return {
                        'success': True,
                        'status_code': 200,
                        'message': 'Manta is accessible'
                    }
                else:
                    return {
                        'success': False,
                        'status_code': 200,
                        'message': 'Manta returned page but no results found'
                    }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'status_code': 403,
                    'message': 'Manta is blocking requests (403 Forbidden)'
                }
            elif response.status_code == 429:
                return {
                    'success': False,
                    'status_code': 429,
                    'message': 'Manta rate limiting (429 Too Many Requests)'
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'message': f'Manta returned status {response.status_code}'
                }

        except Exception as e:
            return {
                'success': False,
                'status_code': 0,
                'message': f'Connection error: {str(e)}'
            }


# Convenience function for testing
def test_manta():
    """Quick test of Manta scraper."""
    scraper = MantaScraper()

    print("Testing Manta connection...")
    status = scraper.test_connection()
    print(f"Status: {status}")

    if status['success']:
        print("\nSearching for landscaping in Oklahoma City, OK...")
        results = scraper.search('Oklahoma City', 'OK', 'landscaping', max_pages=1)
        print(f"Found {len(results)} results")

        for r in results[:5]:
            print(f"  - {r.get('name')} | {r.get('phone')} | {r.get('address')}")

        return results

    return []


if __name__ == '__main__':
    test_manta()
