"""
Google Maps/Places Scraper
==========================

Scrapes Google Maps search results without using the paid API.
Uses Google Search with local business intent.

Note: Google has anti-bot measures, so this scraper may be less reliable.
Use as a supplement to Yellow Pages and BBB.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import logging

from .base_scraper import BaseScraper

logger = logging.getLogger('GooglePlacesScraper')


class GooglePlacesScraper(BaseScraper):
    """Scrape Google Maps listings via Google Search."""

    # Search terms mapped to our categories
    SEARCH_CATEGORIES = {
        # Tier 1
        'car dealerships near me': 'car_dealership',
        'used car dealers near me': 'car_dealership',
        'auto dealers': 'car_dealership',
        'car rental companies': 'car_rental',

        # Tier 2
        'landscaping companies': 'landscaping',
        'lawn care services': 'lawn_care',
        'pest control companies': 'pest_control',
        'hvac companies': 'hvac',
        'plumbers near me': 'plumbing',
        'electricians near me': 'electrical',
        'roofing companies': 'roofing',
        'moving companies': 'moving',
        'security companies': 'security',
        'property management companies': 'property_management',
        'commercial cleaning services': 'cleaning',
        'towing services': 'towing',

        # Tier 3
        'pool service companies': 'pool_service',
        'garage door repair': 'garage_door',
        'appliance repair services': 'appliance_repair',
        'carpet cleaning services': 'carpet_cleaning',
        'window cleaning services': 'window_cleaning',
        'painting contractors': 'painting',
        'tree service companies': 'tree_service',
        'fencing contractors': 'fencing',
    }

    def search(self, city: str, state: str, search_term: str) -> List[Dict]:
        """
        Search Google for local businesses.

        Args:
            city: City name
            state: State abbreviation
            search_term: What to search for

        Returns:
            List of business dictionaries
        """
        businesses = []
        category = self.SEARCH_CATEGORIES.get(
            search_term.lower(),
            search_term.lower().replace(' ', '_').replace(' near me', '')
        )

        try:
            # Google search URL for local businesses
            query = f"{search_term} in {city}, {state}"
            url = f"https://www.google.com/search?q={quote_plus(query)}&num=20&gl=us"

            # Custom headers to appear more like a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }

            response = self.session.get(url, headers=headers, timeout=30)

            if not response.ok:
                logger.warning(f"Google search failed: {response.status_code}")
                return businesses

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for local pack / map results
            # Google's structure changes frequently, so we try multiple selectors

            # Method 1: Local business cards (3-pack)
            local_cards = soup.select('[data-attrid*="local"], .VkpGBb, [class*="local"]')

            # Method 2: Knowledge panel businesses
            if not local_cards:
                local_cards = soup.select('.rllt__details, [data-local-attribute]')

            # Method 3: Regular search results with business schema
            if not local_cards:
                local_cards = soup.find_all('div', attrs={'data-hveid': True})

            for card in local_cards:
                try:
                    business = self._parse_local_card(card, city, state, category)
                    if business and business.get('name'):
                        businesses.append(business)
                except Exception as e:
                    logger.debug(f"Error parsing card: {e}")
                    continue

            # Also try to find businesses in regular search results
            search_results = soup.select('.g, .tF2Cxc')
            for result in search_results[:10]:  # Limit to avoid noise
                try:
                    business = self._parse_search_result(result, city, state, category)
                    if business and business.get('name'):
                        # Avoid duplicates
                        if not any(b['name'] == business['name'] for b in businesses):
                            businesses.append(business)
                except:
                    continue

            logger.info(f"  Found {len(businesses)} businesses from Google")

        except Exception as e:
            logger.error(f"Google search error: {e}")

        return businesses

    def _parse_local_card(self, card, city: str, state: str, category: str) -> Optional[Dict]:
        """Parse a Google local business card."""
        business = {
            'source': 'Google',
            'city': city,
            'state': state.upper(),
            'category': category,
        }

        # Name - try various selectors
        name_elem = card.select_one('.OSrXXb, [role="heading"], .dbg0pd, .tNxQIb')
        if name_elem:
            business['name'] = self._clean_text(name_elem.get_text())
        else:
            return None

        # Address
        addr_elem = card.select_one('.rllt__details, [data-local-attribute="d3adr"], .W4Efsd')
        if addr_elem:
            addr_text = self._clean_text(addr_elem.get_text())
            # Try to parse address
            business['address'] = addr_text

        # Rating
        rating_elem = card.select_one('.yi40Hd, .PNlCoe, [aria-label*="stars"]')
        if rating_elem:
            # Try to extract rating from text or aria-label
            label = rating_elem.get('aria-label', '') or rating_elem.get_text()
            match = re.search(r'(\d+\.?\d*)', label)
            if match:
                try:
                    business['rating'] = float(match.group(1))
                except:
                    pass

        # Review count
        review_elem = card.select_one('.RDApEe, [class*="review"]')
        if review_elem:
            match = re.search(r'(\d+)', review_elem.get_text())
            if match:
                business['review_count'] = int(match.group(1))

        # Phone - sometimes in details
        phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', card.get_text())
        if phone_match:
            business['phone'] = phone_match.group()

        return business

    def _parse_search_result(self, result, city: str, state: str, category: str) -> Optional[Dict]:
        """Parse a regular Google search result that might be a business."""
        business = {
            'source': 'Google',
            'city': city,
            'state': state.upper(),
            'category': category,
        }

        # Title/Name
        title_elem = result.select_one('h3')
        if title_elem:
            title = self._clean_text(title_elem.get_text())
            # Filter out non-business results
            skip_patterns = ['yelp', 'yellowpages', 'bbb', 'angi', 'homeadvisor',
                           'top 10', 'best', 'review', 'directory', 'list']
            if any(p in title.lower() for p in skip_patterns):
                return None
            business['name'] = title
        else:
            return None

        # URL/Website
        link_elem = result.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('http') and 'google' not in href:
                business['website'] = href

        # Snippet might contain phone or address
        snippet = result.select_one('.VwiC3b, .aCOpRe')
        if snippet:
            text = snippet.get_text()
            # Phone
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            if phone_match:
                business['phone'] = phone_match.group()

        return business

    def scrape_city(self, city: str, state: str,
                    categories: List[str] = None) -> int:
        """
        Scrape Google for businesses in a city.

        Note: Google has rate limiting, so use sparingly.
        """
        if categories is None:
            categories = list(self.SEARCH_CATEGORIES.keys())

        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping Google for {city}, {state}")
        logger.info(f"{'='*60}")

        total_saved = 0

        for search_term in categories:
            logger.info(f"\nSearching: {search_term}")

            try:
                businesses = self.search(city, state, search_term)

                saved = 0
                for biz in businesses:
                    if self.save_business(biz):
                        saved += 1

                total_saved += saved
                logger.info(f"  Saved {saved} new businesses")

                # Longer delays for Google to avoid rate limiting
                self._random_delay(5, 10)

            except Exception as e:
                logger.error(f"  Error: {e}")
                continue

        return total_saved
