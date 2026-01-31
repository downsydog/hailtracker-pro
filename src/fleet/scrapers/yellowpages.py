"""
Yellow Pages (yp.com) Scraper - Enhanced Anti-Detection
========================================================

Best source for local service businesses.
Scrapes business listings with name, address, phone, website, etc.

FREE to use - no API key required.
Enhanced with anti-detection measures to avoid blocking.
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

logger = logging.getLogger('YellowPagesScraper')


class YellowPagesScraper(BaseScraper):
    """Scrape business listings from Yellow Pages (yp.com) with anti-detection."""

    BASE_URL = "https://www.yellowpages.com"

    # Rotate through realistic user agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    # Search terms mapped to our categories
    SEARCH_CATEGORIES = {
        # Tier 1 - High vehicle count
        'car dealers': 'car_dealership',
        'new car dealers': 'car_dealership',
        'used car dealers': 'car_dealership',
        'auto dealers': 'car_dealership',
        'auto auctions': 'auto_auction',
        'car rental': 'car_rental',
        'truck rental': 'car_rental',
        'van rental': 'car_rental',

        # Tier 2 - Medium vehicle count
        'landscaping': 'landscaping',
        'landscaping contractors': 'landscaping',
        'landscape design': 'landscaping',
        'lawn care': 'lawn_care',
        'lawn maintenance': 'lawn_care',
        'lawn service': 'lawn_care',
        'pest control': 'pest_control',
        'exterminators': 'pest_control',
        'termite control': 'pest_control',
        'hvac': 'hvac',
        'air conditioning': 'hvac',
        'heating contractors': 'hvac',
        'air conditioning contractors': 'hvac',
        'plumbers': 'plumbing',
        'plumbing': 'plumbing',
        'plumbing contractors': 'plumbing',
        'electricians': 'electrical',
        'electrical contractors': 'electrical',
        'roofing contractors': 'roofing',
        'roofers': 'roofing',
        'roofing': 'roofing',
        'general contractors': 'general_contractor',
        'contractors': 'contractor',
        'building contractors': 'contractor',
        'moving companies': 'moving',
        'movers': 'moving',
        'moving services': 'moving',
        'security companies': 'security',
        'security services': 'security',
        'security systems': 'security',
        'property management': 'property_management',
        'property managers': 'property_management',
        'janitorial services': 'janitorial',
        'commercial cleaning': 'cleaning',
        'cleaning services': 'cleaning',
        'office cleaning': 'cleaning',
        'towing': 'towing',
        'tow trucks': 'towing',
        'towing service': 'towing',
        'courier services': 'courier',
        'delivery service': 'delivery',

        # Tier 3 - Smaller fleets
        'pool service': 'pool_service',
        'swimming pool service': 'pool_service',
        'pool cleaning': 'pool_service',
        'garage doors': 'garage_door',
        'garage door repair': 'garage_door',
        'appliance repair': 'appliance_repair',
        'appliance service': 'appliance_repair',
        'carpet cleaning': 'carpet_cleaning',
        'carpet cleaners': 'carpet_cleaning',
        'window cleaning': 'window_cleaning',
        'window cleaners': 'window_cleaning',
        'pressure washing': 'pressure_washing',
        'power washing': 'pressure_washing',
        'painters': 'painting',
        'painting contractors': 'painting',
        'house painters': 'painting',
        'flooring': 'flooring',
        'flooring contractors': 'flooring',
        'floor installation': 'flooring',
        'tree service': 'tree_service',
        'tree trimming': 'tree_service',
        'tree removal': 'tree_service',
        'irrigation': 'irrigation',
        'sprinkler systems': 'irrigation',
        'lawn sprinklers': 'irrigation',
        'septic services': 'septic',
        'septic tank': 'septic',
        'locksmiths': 'locksmith',
        'locksmith': 'locksmith',
        'glass repair': 'glass_repair',
        'auto glass': 'glass_repair',
        'window repair': 'glass_repair',
        'fencing': 'fencing',
        'fence contractors': 'fencing',
        'fence installation': 'fencing',
        'concrete contractors': 'concrete',
        'concrete': 'concrete',
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

        # Random user agent
        user_agent = random.choice(self.USER_AGENTS)

        # Realistic browser headers
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })

    def _rotate_user_agent(self):
        """Rotate to a new user agent."""
        user_agent = random.choice(self.USER_AGENTS)
        self.session.headers['User-Agent'] = user_agent
        logger.debug(f"Rotated user agent")

    def _smart_delay(self, min_delay: float = 3, max_delay: float = 8):
        """
        Smart delay with variable timing to appear more human.
        Increases delay after many requests.
        """
        # Add extra delay every 10 requests
        extra_delay = (self._request_count // 10) * 2

        # Jitter the delay
        base_delay = random.uniform(min_delay, max_delay)
        delay = base_delay + extra_delay + random.uniform(0, 1)

        # Ensure minimum time between requests
        time_since_last = time.time() - self._last_request_time
        if time_since_last < delay:
            time.sleep(delay - time_since_last)

        self._last_request_time = time.time()
        self._request_count += 1

        # Rotate user agent every 5 requests
        if self._request_count % 5 == 0:
            self._rotate_user_agent()

    def _make_request(self, url: str, retry_count: int = 3) -> Optional[requests.Response]:
        """Make request with retry logic and anti-detection."""
        for attempt in range(retry_count):
            try:
                self._smart_delay()

                # Add referer for subsequent requests
                if self._request_count > 1:
                    self.session.headers['Referer'] = self.BASE_URL

                response = self.session.get(url, timeout=30)

                # Check for blocking
                if response.status_code == 403:
                    logger.warning(f"Got 403 - rotating user agent (attempt {attempt + 1})")
                    self._rotate_user_agent()
                    time.sleep(random.uniform(10, 20))  # Longer backoff
                    continue

                if response.status_code == 429:
                    logger.warning(f"Rate limited - backing off (attempt {attempt + 1})")
                    time.sleep(random.uniform(30, 60))
                    continue

                return response

            except requests.RequestException as e:
                logger.warning(f"Request failed: {e} (attempt {attempt + 1})")
                time.sleep(random.uniform(5, 10))

        return None

    def search(self, city: str, state: str, search_term: str,
               max_pages: int = 3) -> List[Dict]:
        """
        Search Yellow Pages for businesses with anti-detection.

        Args:
            city: City name
            state: State abbreviation (e.g., 'TX')
            search_term: What to search for (e.g., 'landscaping')
            max_pages: Maximum pages to scrape (default: 3)

        Returns:
            List of business dictionaries
        """
        businesses = []
        category = self.SEARCH_CATEGORIES.get(
            search_term.lower(),
            search_term.lower().replace(' ', '_')
        )

        # First, visit the homepage to get cookies
        logger.debug("Visiting homepage to establish session...")
        home_response = self._make_request(self.BASE_URL)
        if home_response and home_response.ok:
            logger.debug("Homepage loaded successfully")

        time.sleep(random.uniform(2, 4))

        for page in range(1, max_pages + 1):
            try:
                # Build URL
                search_encoded = quote_plus(search_term)
                location_encoded = quote_plus(f"{city}, {state}")

                if page == 1:
                    url = f"{self.BASE_URL}/search?search_terms={search_encoded}&geo_location_terms={location_encoded}"
                else:
                    url = f"{self.BASE_URL}/search?search_terms={search_encoded}&geo_location_terms={location_encoded}&page={page}"

                logger.debug(f"Fetching: {url}")
                response = self._make_request(url)

                if not response:
                    logger.warning(f"Failed to fetch page {page}")
                    break

                if response.status_code == 404:
                    logger.debug(f"Page {page} not found, stopping")
                    break

                if not response.ok:
                    logger.warning(f"YP request failed: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Check if we got blocked (CAPTCHA page)
                if 'captcha' in response.text.lower() or 'robot' in response.text.lower():
                    logger.warning("Detected anti-bot page, backing off...")
                    time.sleep(random.uniform(60, 120))
                    self._setup_stealth_session()  # Reset session
                    break

                # Find business listings - YP uses various class names
                listings = []

                # Try different selectors
                selectors = [
                    'div.result',
                    'div.srp-listing',
                    'div.v-card',
                    'div.search-results div.info',
                    'article.result',
                    'div[class*="organic"]',
                    'div.info-section',
                ]

                for selector in selectors:
                    listings = soup.select(selector)
                    if listings:
                        logger.debug(f"Found listings with selector: {selector}")
                        break

                if not listings:
                    # Try finding by data attribute
                    listings = soup.find_all('div', attrs={'data-analytics': True})
                    listings = [l for l in listings if 'listing' in str(l.get('data-analytics', '')).lower()]

                if not listings:
                    # Try script-based extraction (some YP pages use JSON)
                    scripts = soup.find_all('script', type='application/ld+json')
                    for script in scripts:
                        try:
                            import json
                            data = json.loads(script.string)
                            if isinstance(data, list):
                                for item in data:
                                    if item.get('@type') == 'LocalBusiness':
                                        biz = self._parse_json_listing(item, city, state, category)
                                        if biz:
                                            businesses.append(biz)
                        except:
                            pass

                if not listings:
                    logger.debug(f"No listings found on page {page}")
                    # Save debug HTML for analysis
                    break

                page_count = 0
                for listing in listings:
                    try:
                        business = self._parse_listing(listing, city, state, category)
                        if business and business.get('name'):
                            businesses.append(business)
                            page_count += 1
                    except Exception as e:
                        logger.debug(f"Error parsing listing: {e}")
                        continue

                logger.info(f"  Page {page}: Found {page_count} listings")

                if page_count == 0:
                    break

                # Check for next page
                next_link = soup.find('a', class_='next') or soup.find('a', text=re.compile(r'Next', re.I))
                if not next_link:
                    break

            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                break

        return businesses

    def _parse_json_listing(self, data: dict, city: str, state: str, category: str) -> Optional[Dict]:
        """Parse a JSON-LD business listing."""
        try:
            business = {
                'source': 'YellowPages',
                'city': city,
                'state': state.upper(),
                'category': category,
                'name': data.get('name', ''),
            }

            if not business['name']:
                return None

            address = data.get('address', {})
            if isinstance(address, dict):
                business['address'] = address.get('streetAddress', '')
                business['city'] = address.get('addressLocality', city)
                business['state'] = address.get('addressRegion', state)
                business['zip'] = address.get('postalCode', '')

            business['phone'] = data.get('telephone', '')
            business['website'] = data.get('url', '')

            rating = data.get('aggregateRating', {})
            if isinstance(rating, dict):
                business['rating'] = float(rating.get('ratingValue', 0))
                business['review_count'] = int(rating.get('reviewCount', 0))

            return business
        except:
            return None

    def _parse_listing(self, listing, city: str, state: str, category: str) -> Optional[Dict]:
        """Parse a single business listing from Yellow Pages."""
        business = {
            'source': 'YellowPages',
            'city': city,
            'state': state.upper(),
            'category': category,
        }

        # Business name - try multiple selectors
        name_elem = None
        for selector in ['a.business-name', 'h2 a', '.business-name', 'a[class*="name"]',
                         '.n a', 'a.listing-name', '[class*="business"] a']:
            name_elem = listing.select_one(selector)
            if name_elem:
                break

        if name_elem:
            business['name'] = self._clean_text(name_elem.get_text())
        else:
            # Try getting name from any prominent link
            links = listing.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                if len(text) > 5 and not text.lower().startswith(('more', 'view', 'see', 'http')):
                    business['name'] = text
                    break

        if not business.get('name'):
            return None  # Skip if no name found

        # Address
        addr_elem = listing.select_one('.street-address, .adr .street-address, [class*="address"], .addr')
        if addr_elem:
            business['address'] = self._clean_text(addr_elem.get_text())

        # City/State/Zip from locality
        locality_elem = listing.select_one('.locality, .adr .locality')
        if locality_elem:
            loc_text = self._clean_text(locality_elem.get_text())
            # Parse "City, ST 12345" format
            match = re.match(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', loc_text)
            if match:
                business['city'] = match.group(1)
                business['state'] = match.group(2)
                if match.group(3):
                    business['zip'] = match.group(3)

        # Phone - try multiple patterns
        phone_elem = listing.select_one('.phones, .phone, [class*="phone"]')
        if phone_elem:
            phone_text = phone_elem.get_text(strip=True)
            # Clean up phone format
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', phone_text)
            if phone_match:
                business['phone'] = phone_match.group()
            else:
                business['phone'] = phone_text

        # Website
        website_elem = listing.select_one('a.track-visit-website, a[href*="website"], a.website-link')
        if website_elem:
            href = website_elem.get('href', '')
            if href and not href.startswith('/'):
                business['website'] = href

        # Rating (usually 0-5 stars)
        rating_elem = listing.select_one('.ratings, [class*="rating"]')
        if rating_elem:
            # Look for numeric rating or star count
            rating_class = rating_elem.get('class', [])
            for cls in rating_class:
                match = re.search(r'(\d+)', str(cls))
                if match:
                    rating = int(match.group(1))
                    # Normalize - sometimes it's 0-10, sometimes 0-50
                    if rating > 10:
                        business['rating'] = rating / 10
                    elif rating > 5:
                        business['rating'] = rating / 2
                    else:
                        business['rating'] = float(rating)
                    break

        # Review count
        review_elem = listing.select_one('.review-count, [class*="count"]')
        if review_elem:
            review_text = review_elem.get_text()
            match = re.search(r'(\d+)', review_text)
            if match:
                business['review_count'] = int(match.group(1))

        # Years in business
        years_elem = listing.find(string=re.compile(r'years?\s*(in\s*)?business', re.I))
        if years_elem:
            match = re.search(r'(\d+)\s*years?', str(years_elem), re.I)
            if match:
                business['years_in_business'] = int(match.group(1))

        # Categories/services from listing
        cats_elem = listing.select_one('.categories, .cats')
        if cats_elem:
            business['subcategory'] = self._clean_text(cats_elem.get_text())

        return business

    def scrape_city(self, city: str, state: str,
                    categories: List[str] = None,
                    max_pages: int = 2) -> int:
        """
        Scrape all fleet-relevant businesses in a city.

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
        logger.info(f"Scraping Yellow Pages for {city}, {state}")
        logger.info(f"Categories: {len(categories)}")
        logger.info(f"{'='*60}")

        total_saved = 0

        for search_term in categories:
            logger.info(f"\nSearching: {search_term}")

            try:
                businesses = self.search(city, state, search_term, max_pages=max_pages)

                saved = 0
                for biz in businesses:
                    if self.save_business(biz):
                        saved += 1

                total_saved += saved
                logger.info(f"  Saved {saved} new businesses")

                # Longer delay between categories to avoid detection
                self._smart_delay(5, 10)

            except Exception as e:
                logger.error(f"  Error: {e}")
                continue

        logger.info(f"\nTotal saved for {city}, {state}: {total_saved}")
        return total_saved

    def get_priority_categories(self, tier: int = None) -> List[str]:
        """
        Get categories filtered by tier for targeted scraping.

        Args:
            tier: 1, 2, or 3 (None for all)

        Returns:
            List of search terms for that tier
        """
        tier_mapping = {
            1: ['car dealers', 'used car dealers', 'auto auctions', 'car rental'],
            2: ['landscaping', 'pest control', 'hvac', 'plumbers', 'electricians',
                'roofing contractors', 'moving companies', 'security services',
                'property management', 'janitorial services', 'towing'],
            3: ['pool service', 'garage doors', 'appliance repair', 'carpet cleaning',
                'window cleaning', 'painters', 'tree service', 'fencing', 'concrete contractors'],
        }

        if tier:
            return tier_mapping.get(tier, [])

        return list(self.SEARCH_CATEGORIES.keys())
