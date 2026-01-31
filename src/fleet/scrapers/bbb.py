"""
Better Business Bureau (BBB.org) Scraper
=========================================

BBB listings are verified/accredited businesses - higher quality leads.
These businesses are generally more established and reputable.

FREE to use - no API key required.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import logging

from .base_scraper import BaseScraper

logger = logging.getLogger('BBBScraper')


class BBBScraper(BaseScraper):
    """Scrape BBB accredited businesses."""

    BASE_URL = "https://www.bbb.org"

    # BBB category slugs mapped to our categories
    SEARCH_CATEGORIES = {
        # Tier 1
        'auto-dealers-new-cars': 'car_dealership',
        'auto-dealers-used-cars': 'car_dealership',
        'auto-renting-leasing': 'car_rental',

        # Tier 2
        'landscape-contractors': 'landscaping',
        'lawn-maintenance': 'lawn_care',
        'pest-control-services': 'pest_control',
        'air-conditioning-contractors-systems': 'hvac',
        'heating-contractors': 'hvac',
        'plumbers': 'plumbing',
        'plumbing-drains-sewer-cleaning': 'plumbing',
        'electricians': 'electrical',
        'roofing-contractors': 'roofing',
        'movers': 'moving',
        'moving-companies': 'moving',
        'security-control-equipment-systems-monitors': 'security',
        'security-systems-consultants': 'security',
        'property-management': 'property_management',
        'janitor-service': 'janitorial',
        'house-cleaning': 'cleaning',
        'towing-automotive': 'towing',
        'general-contractors': 'general_contractor',
        'building-contractors': 'contractor',

        # Tier 3
        'swimming-pool-service-repair': 'pool_service',
        'garage-doors-openers': 'garage_door',
        'appliances-household-major-repairs': 'appliance_repair',
        'carpet-rug-cleaners': 'carpet_cleaning',
        'window-cleaning': 'window_cleaning',
        'painting-contractors': 'painting',
        'tree-service': 'tree_service',
        'lawn-sprinkler-systems': 'irrigation',
        'septic-tanks-systems-cleaning': 'septic',
        'locks-locksmiths': 'locksmith',
        'glass-auto-plate-window': 'glass_repair',
        'fence-contractors': 'fencing',
        'concrete-contractors': 'concrete',
    }

    # BBB letter grades to numeric
    GRADE_MAP = {
        'A+': 5.0, 'A': 4.5, 'A-': 4.0,
        'B+': 3.5, 'B': 3.0, 'B-': 2.5,
        'C+': 2.0, 'C': 1.5, 'C-': 1.0,
        'D+': 0.75, 'D': 0.5, 'D-': 0.25,
        'F': 0.0
    }

    def search(self, city: str, state: str, category_slug: str,
               max_pages: int = 2) -> List[Dict]:
        """
        Search BBB for accredited businesses.

        Args:
            city: City name
            state: State abbreviation
            category_slug: BBB category slug (e.g., 'landscape-contractors')
            max_pages: Maximum pages to scrape

        Returns:
            List of business dictionaries
        """
        businesses = []
        our_category = self.SEARCH_CATEGORIES.get(
            category_slug,
            category_slug.replace('-', '_')
        )

        for page in range(1, max_pages + 1):
            try:
                # BBB search URL
                location = f"{city}, {state}"
                search_text = category_slug.replace('-', ' ')

                url = (
                    f"{self.BASE_URL}/search?"
                    f"find_country=USA&"
                    f"find_text={quote_plus(search_text)}&"
                    f"find_loc={quote_plus(location)}&"
                    f"find_type=Category&"
                    f"page={page}&"
                    f"sort=Relevance"
                )

                logger.debug(f"Fetching: {url}")
                response = self.session.get(url, timeout=30)

                if not response.ok:
                    logger.warning(f"BBB request failed: {response.status_code}")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # BBB uses profile links like /us/tx/dallas/profile/...
                # Find all business profile links
                profile_links = soup.select('a[href*="/us/"][href*="/profile/"]')

                # Filter to unique businesses (avoid duplicate links)
                seen_names = set()
                page_count = 0

                for link in profile_links:
                    try:
                        href = link.get('href', '')
                        name = link.get_text(strip=True)

                        # Skip empty names, "more" links, and duplicates
                        if not name or len(name) < 3 or 'more' in name.lower():
                            continue
                        if name in seen_names:
                            continue

                        seen_names.add(name)

                        # Build business dict
                        business = {
                            'source': 'BBB',
                            'city': city,
                            'state': state.upper(),
                            'category': our_category,
                            'name': name,
                            'bbb_accredited': True,
                            'website': f"https://www.bbb.org{href}" if href.startswith('/') else href,
                        }

                        # Try to get more details from parent container
                        parent = link.find_parent('div', class_=True)
                        if parent:
                            # Look for phone
                            phone_elem = parent.find(string=re.compile(r'\(\d{3}\)\s*\d{3}'))
                            if phone_elem:
                                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', str(phone_elem))
                                if phone_match:
                                    business['phone'] = phone_match.group()

                            # Look for address
                            addr_text = parent.get_text()
                            addr_match = re.search(r'(\d+\s+[\w\s]+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Cir)\.?)', addr_text)
                            if addr_match:
                                business['address'] = addr_match.group(1)

                        businesses.append(business)
                        page_count += 1

                    except Exception as e:
                        logger.debug(f"Error parsing BBB link: {e}")
                        continue

                logger.info(f"  Page {page}: Found {page_count} BBB listings")

                if page_count == 0:
                    break

                # Check if there are more pages
                next_link = soup.select_one('a[rel="next"], .pagination .next')
                if not next_link:
                    break

                self._random_delay(2, 4)

            except Exception as e:
                logger.error(f"BBB error on page {page}: {e}")
                break

        return businesses

    def _parse_listing(self, listing, city: str, state: str, category: str) -> Optional[Dict]:
        """Parse a single BBB listing."""
        business = {
            'source': 'BBB',
            'city': city,
            'state': state.upper(),
            'category': category,
            'bbb_accredited': True,
        }

        # Business name
        name_elem = listing.select_one(
            '.business-name, .result-business-name, h3 a, h4 a, '
            'a[href*="/business-reviews/"]'
        )
        if name_elem:
            business['name'] = self._clean_text(name_elem.get_text())
        else:
            return None

        # Phone
        phone_elem = listing.select_one('.phone, .result-phone, [class*="phone"]')
        if phone_elem:
            business['phone'] = phone_elem.get_text(strip=True)
        else:
            # Try to find phone pattern in text
            text = listing.get_text()
            phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            if phone_match:
                business['phone'] = phone_match.group()

        # Address
        addr_elem = listing.select_one('.address, .result-address, [class*="address"]')
        if addr_elem:
            business['address'] = self._clean_text(addr_elem.get_text())

        # City/State/Zip
        locality_elem = listing.select_one('.city-state-zip, .locality')
        if locality_elem:
            loc_text = self._clean_text(locality_elem.get_text())
            match = re.match(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', loc_text)
            if match:
                business['city'] = match.group(1)
                business['state'] = match.group(2)
                if match.group(3):
                    business['zip'] = match.group(3)

        # BBB Rating (letter grade)
        rating_elem = listing.select_one('.bbb-rating, .rating, [class*="grade"]')
        if rating_elem:
            grade_text = rating_elem.get_text(strip=True).upper()
            # Extract letter grade
            for grade in self.GRADE_MAP.keys():
                if grade in grade_text:
                    business['rating'] = self.GRADE_MAP[grade]
                    business['notes'] = f"BBB Grade: {grade}"
                    break

        # Accreditation status
        accred_elem = listing.select_one('.accredited, [class*="accredit"]')
        if accred_elem:
            accred_text = accred_elem.get_text().lower()
            business['bbb_accredited'] = 'accredited' in accred_text

        # Website (from link)
        website_elem = listing.select_one('a[href*="website"], a.website')
        if website_elem:
            business['website'] = website_elem.get('href', '')

        # Years in business
        years_elem = listing.find(string=re.compile(r'years?\s*(in\s*)?(business)?', re.I))
        if years_elem:
            match = re.search(r'(\d+)\s*years?', str(years_elem), re.I)
            if match:
                business['years_in_business'] = int(match.group(1))

        return business

    def scrape_city(self, city: str, state: str,
                    categories: List[str] = None,
                    max_pages: int = 2) -> int:
        """
        Scrape BBB for businesses in a city.

        Args:
            city: City name
            state: State abbreviation
            categories: List of BBB category slugs (default: all)
            max_pages: Max pages per category

        Returns:
            Number of new businesses saved
        """
        if categories is None:
            categories = list(self.SEARCH_CATEGORIES.keys())

        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping BBB for {city}, {state}")
        logger.info(f"Categories: {len(categories)}")
        logger.info(f"{'='*60}")

        total_saved = 0

        for cat_slug in categories:
            logger.info(f"\nSearching BBB: {cat_slug}")

            try:
                businesses = self.search(city, state, cat_slug, max_pages=max_pages)

                saved = 0
                for biz in businesses:
                    if self.save_business(biz):
                        saved += 1

                total_saved += saved
                logger.info(f"  Saved {saved} BBB businesses")

                # Delay between categories
                self._random_delay(3, 5)

            except Exception as e:
                logger.error(f"  Error: {e}")
                continue

        logger.info(f"\nTotal BBB businesses saved for {city}, {state}: {total_saved}")
        return total_saved

    def get_priority_categories(self) -> List[str]:
        """Get high-priority BBB categories for fleet prospecting."""
        return [
            'auto-dealers-new-cars',
            'auto-dealers-used-cars',
            'landscape-contractors',
            'pest-control-services',
            'air-conditioning-contractors-systems',
            'plumbers',
            'roofing-contractors',
            'movers',
            'general-contractors',
            'tree-service',
            'garage-doors-openers',
        ]
