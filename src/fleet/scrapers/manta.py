"""
Manta.com Business Directory Scraper
====================================

Manta is a comprehensive small business directory with company profiles.
Good source for business details including employee counts which helps estimate fleet size.

FREE to use - no API key required.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import logging
import random
import time

from .base_scraper import BaseScraper

logger = logging.getLogger('MantaScraper')


class MantaScraper(BaseScraper):
    """Scrape business listings from Manta.com."""

    BASE_URL = "https://www.manta.com"

    # Rotate through realistic user agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    ]

    # Search terms mapped to our categories
    SEARCH_CATEGORIES = {
        # Tier 1 - High vehicle count
        'new car dealers': 'car_dealership',
        'used car dealers': 'car_dealership',
        'automobile dealers': 'car_dealership',
        'car rental': 'car_rental',
        'truck rental': 'car_rental',

        # Tier 2 - Medium vehicle count
        'landscaping services': 'landscaping',
        'lawn care': 'lawn_care',
        'pest control': 'pest_control',
        'exterminators': 'pest_control',
        'hvac contractors': 'hvac',
        'heating and air conditioning': 'hvac',
        'plumbing contractors': 'plumbing',
        'plumbers': 'plumbing',
        'electrical contractors': 'electrical',
        'electricians': 'electrical',
        'roofing contractors': 'roofing',
        'general contractors': 'general_contractor',
        'moving companies': 'moving',
        'movers': 'moving',
        'security services': 'security',
        'property management': 'property_management',
        'janitorial services': 'janitorial',
        'cleaning services': 'cleaning',
        'towing services': 'towing',

        # Tier 3 - Smaller fleets
        'pool service': 'pool_service',
        'garage door': 'garage_door',
        'appliance repair': 'appliance_repair',
        'carpet cleaning': 'carpet_cleaning',
        'window cleaning': 'window_cleaning',
        'painting contractors': 'painting',
        'tree service': 'tree_service',
        'fence contractors': 'fencing',
        'concrete contractors': 'concrete',
        'locksmith': 'locksmith',
    }

    def __init__(self, db_path: str = None):
        """Initialize with anti-detection session."""
        super().__init__(db_path)
        self._setup_stealth_session()
        self._request_count = 0
        self._last_request_time = 0

    def _setup_stealth_session(self):
        """Configure session with anti-detection measures."""
        self.session = requests.Session()

        user_agent = random.choice(self.USER_AGENTS)

        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })

    def _smart_delay(self, min_delay: float = 2, max_delay: float = 5):
        """Smart delay with variable timing."""
        extra_delay = (self._request_count // 10) * 1
        delay = random.uniform(min_delay, max_delay) + extra_delay

        time_since_last = time.time() - self._last_request_time
        if time_since_last < delay:
            time.sleep(delay - time_since_last)

        self._last_request_time = time.time()
        self._request_count += 1

        # Rotate user agent periodically
        if self._request_count % 5 == 0:
            self.session.headers['User-Agent'] = random.choice(self.USER_AGENTS)

    def _make_request(self, url: str, retry_count: int = 3) -> Optional[requests.Response]:
        """Make request with retry logic."""
        for attempt in range(retry_count):
            try:
                self._smart_delay()

                if self._request_count > 1:
                    self.session.headers['Referer'] = self.BASE_URL

                response = self.session.get(url, timeout=30)

                if response.status_code in [403, 429]:
                    logger.warning(f"Got {response.status_code} - backing off (attempt {attempt + 1})")
                    time.sleep(random.uniform(15, 30))
                    self._setup_stealth_session()
                    continue

                return response

            except requests.RequestException as e:
                logger.warning(f"Request failed: {e} (attempt {attempt + 1})")
                time.sleep(random.uniform(5, 10))

        return None

    def search(self, city: str, state: str, search_term: str,
               max_pages: int = 2) -> List[Dict]:
        """
        Search Manta for businesses.

        Args:
            city: City name
            state: State abbreviation
            search_term: What to search for
            max_pages: Maximum pages to scrape

        Returns:
            List of business dictionaries
        """
        businesses = []
        category = self.SEARCH_CATEGORIES.get(
            search_term.lower(),
            search_term.lower().replace(' ', '_')
        )

        # Manta search URL format
        # https://www.manta.com/search?search_source=nav&search=landscaping&search_location=Dallas%2C+TX
        location = f"{city}, {state}"

        for page in range(1, max_pages + 1):
            try:
                search_encoded = quote_plus(search_term)
                location_encoded = quote_plus(location)

                if page == 1:
                    url = f"{self.BASE_URL}/search?search={search_encoded}&search_location={location_encoded}"
                else:
                    url = f"{self.BASE_URL}/search?search={search_encoded}&search_location={location_encoded}&pg={page}"

                logger.debug(f"Fetching: {url}")
                response = self._make_request(url)

                if not response or not response.ok:
                    logger.warning(f"Manta request failed on page {page}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Check for blocking
                if 'captcha' in response.text.lower() or 'access denied' in response.text.lower():
                    logger.warning("Detected anti-bot page")
                    break

                # Manta uses various listing containers
                listings = []

                selectors = [
                    'div.search-results-listing',
                    'div.listing-card',
                    'div[class*="result"]',
                    'article.listing',
                    'div.company-card',
                    'div[data-listing]',
                ]

                for selector in selectors:
                    listings = soup.select(selector)
                    if listings:
                        logger.debug(f"Found listings with selector: {selector}")
                        break

                if not listings:
                    # Try finding links to company profiles
                    profile_links = soup.select('a[href*="/c/"]')
                    seen_names = set()

                    for link in profile_links:
                        try:
                            name = link.get_text(strip=True)

                            # Skip empty, duplicate, or navigation links
                            if not name or len(name) < 3 or name in seen_names:
                                continue
                            if any(x in name.lower() for x in ['more', 'view', 'next', 'prev', 'page']):
                                continue

                            seen_names.add(name)

                            href = link.get('href', '')
                            business = {
                                'source': 'Manta',
                                'city': city,
                                'state': state.upper(),
                                'category': category,
                                'name': name,
                                'website': f"{self.BASE_URL}{href}" if href.startswith('/') else href,
                            }

                            # Try to get more info from parent container
                            parent = link.find_parent('div', class_=True)
                            if parent:
                                # Look for phone
                                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', parent.get_text())
                                if phone_match:
                                    business['phone'] = phone_match.group()

                                # Look for address
                                addr_text = parent.get_text()
                                addr_match = re.search(r'(\d+\s+[\w\s]+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Cir)\.?)', addr_text)
                                if addr_match:
                                    business['address'] = addr_match.group(1)

                                # Look for employee count (helps estimate fleet)
                                emp_match = re.search(r'(\d+)(?:\s*-\s*\d+)?\s*employees?', addr_text, re.I)
                                if emp_match:
                                    business['employee_count'] = int(emp_match.group(1))

                            businesses.append(business)

                        except Exception as e:
                            logger.debug(f"Error parsing Manta link: {e}")
                            continue

                page_count = len(seen_names) if not listings else 0

                # Parse structured listings if found
                for listing in listings:
                    try:
                        business = self._parse_listing(listing, city, state, category)
                        if business and business.get('name'):
                            businesses.append(business)
                            page_count += 1
                    except Exception as e:
                        logger.debug(f"Error parsing listing: {e}")
                        continue

                logger.info(f"  Page {page}: Found {page_count} Manta listings")

                if page_count == 0:
                    break

                # Check for next page
                next_link = soup.select_one('a.next, a[rel="next"], .pagination a:contains("Next")')
                if not next_link:
                    # Also check for page numbers
                    page_links = soup.select('.pagination a, .pager a')
                    has_next = any(str(page + 1) in (l.get_text() or '') for l in page_links)
                    if not has_next:
                        break

                self._random_delay(3, 5)

            except Exception as e:
                logger.error(f"Manta error on page {page}: {e}")
                break

        return businesses

    def _parse_listing(self, listing, city: str, state: str, category: str) -> Optional[Dict]:
        """Parse a single Manta listing."""
        business = {
            'source': 'Manta',
            'city': city,
            'state': state.upper(),
            'category': category,
        }

        # Business name
        name_elem = listing.select_one('h3 a, h4 a, .company-name, .listing-name, a.name')
        if name_elem:
            business['name'] = self._clean_text(name_elem.get_text())
        else:
            # Try any link
            link = listing.select_one('a')
            if link:
                text = link.get_text(strip=True)
                if len(text) > 3:
                    business['name'] = text

        if not business.get('name'):
            return None

        # Phone
        phone_elem = listing.select_one('.phone, [class*="phone"]')
        if phone_elem:
            phone_text = phone_elem.get_text(strip=True)
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', phone_text)
            if phone_match:
                business['phone'] = phone_match.group()

        # Address
        addr_elem = listing.select_one('.address, [class*="address"], .location')
        if addr_elem:
            business['address'] = self._clean_text(addr_elem.get_text())

        # City/State from text
        loc_elem = listing.select_one('.city-state, .locality')
        if loc_elem:
            loc_text = self._clean_text(loc_elem.get_text())
            match = re.match(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', loc_text)
            if match:
                business['city'] = match.group(1)
                business['state'] = match.group(2)
                if match.group(3):
                    business['zip'] = match.group(3)

        # Employee count (useful for fleet estimation)
        emp_elem = listing.find(string=re.compile(r'employees?', re.I))
        if emp_elem:
            match = re.search(r'(\d+)(?:\s*-\s*\d+)?\s*employees?', str(emp_elem), re.I)
            if match:
                business['employee_count'] = int(match.group(1))

        # Revenue (indicator of business size)
        rev_elem = listing.find(string=re.compile(r'\$[\d,]+[KMB]?', re.I))
        if rev_elem:
            business['notes'] = f"Revenue: {rev_elem.strip()}"

        # Website
        website_elem = listing.select_one('a[href*="http"]:not([href*="manta.com"])')
        if website_elem:
            business['website'] = website_elem.get('href', '')

        return business

    def scrape_city(self, city: str, state: str,
                    categories: List[str] = None,
                    max_pages: int = 2) -> int:
        """
        Scrape Manta for businesses in a city.

        Args:
            city: City name
            state: State abbreviation
            categories: List of search terms (default: all)
            max_pages: Max pages per category

        Returns:
            Number of new businesses saved
        """
        if categories is None:
            categories = list(self.SEARCH_CATEGORIES.keys())

        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping Manta for {city}, {state}")
        logger.info(f"Categories: {len(categories)}")
        logger.info(f"{'='*60}")

        total_saved = 0

        for search_term in categories:
            logger.info(f"\nSearching Manta: {search_term}")

            try:
                businesses = self.search(city, state, search_term, max_pages=max_pages)

                saved = 0
                for biz in businesses:
                    if self.save_business(biz):
                        saved += 1

                total_saved += saved
                logger.info(f"  Saved {saved} Manta businesses")

                self._smart_delay(4, 7)

            except Exception as e:
                logger.error(f"  Error: {e}")
                continue

        logger.info(f"\nTotal Manta businesses saved for {city}, {state}: {total_saved}")
        return total_saved

    def get_priority_categories(self) -> List[str]:
        """Get high-priority Manta categories for fleet prospecting."""
        return [
            'new car dealers',
            'used car dealers',
            'landscaping services',
            'pest control',
            'hvac contractors',
            'plumbing contractors',
            'roofing contractors',
            'moving companies',
            'tree service',
        ]
