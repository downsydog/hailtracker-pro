"""
Manta.com Scraper using Playwright with Advanced Stealth
=========================================================
Uses Firefox browser with playwright-stealth to bypass anti-bot protection.
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from typing import List, Dict
import re
import logging
import random
import time

logger = logging.getLogger('MantaPlaywright')


class MantaPlaywright:
    """
    Manta.com scraper using Firefox with advanced stealth.
    Bypasses aggressive anti-bot protection.
    """

    BASE_URL = "https://www.manta.com"

    # Categories for fleet-relevant businesses
    CATEGORIES = [
        # Landscaping
        'landscaping', 'landscaping-services', 'lawn-maintenance', 'lawn-care',
        'tree-service', 'tree-trimming',

        # HVAC
        'hvac', 'heating-air-conditioning', 'air-conditioning-contractors',
        'heating-contractors', 'furnace-repair',

        # Plumbing
        'plumbers', 'plumbing-contractors', 'drain-cleaning',

        # Electrical
        'electricians', 'electrical-contractors',

        # Pest Control
        'pest-control', 'pest-control-services', 'exterminators',

        # Roofing
        'roofing-contractors', 'roofers', 'roof-repair',

        # General Contractors
        'general-contractors', 'contractors', 'remodeling-contractors',

        # Auto
        'auto-body-repair', 'auto-repair', 'auto-body-shops',
        'car-dealers', 'towing-services',

        # Moving
        'moving-companies', 'movers', 'moving-services',

        # Cleaning
        'cleaning-services', 'janitorial-services', 'commercial-cleaning',

        # Other Trades
        'painting-contractors', 'fence-contractors', 'concrete-contractors',
        'garage-door-services', 'locksmiths',
    ]

    # Priority categories
    PRIORITY_CATEGORIES = [
        'landscaping', 'hvac', 'plumbing-contractors', 'electrical-contractors',
        'pest-control-services', 'roofing-contractors', 'auto-body-repair',
        'towing-services', 'moving-companies', 'cleaning-services',
    ]

    def __init__(self, headless: bool = True):
        """Initialize scraper."""
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def start_browser(self):
        """Start Firefox browser with stealth patches."""
        logger.info("[Manta] Starting Firefox with stealth...")

        self.playwright = sync_playwright().start()

        # Use Firefox - better at bypassing detection
        self.browser = self.playwright.firefox.launch(
            headless=self.headless,
            firefox_user_prefs={
                # Disable telemetry
                'toolkit.telemetry.enabled': False,
                'datareporting.policy.dataSubmissionEnabled': False,
                # Disable WebRTC leak
                'media.peerconnection.enabled': False,
                # Disable battery API
                'dom.battery.enabled': False,
                # Spoof screen resolution
                'privacy.resistFingerprinting': False,
            }
        )

        # Create context with realistic settings
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            locale='en-US',
            timezone_id='America/Chicago',
            geolocation={'latitude': 35.4676, 'longitude': -97.5164},
            permissions=['geolocation'],
        )

        # Add cookies that a real user might have
        self.context.add_cookies([
            {
                'name': '_ga',
                'value': f'GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time()) - random.randint(86400, 604800)}',
                'domain': '.manta.com',
                'path': '/'
            },
            {
                'name': 'session_id',
                'value': f'{random.randint(100000000, 999999999)}',
                'domain': '.manta.com',
                'path': '/'
            }
        ])

        self.page = self.context.new_page()

        # Apply stealth patches
        stealth = Stealth(
            navigator_webdriver=True,
            navigator_plugins=True,
            navigator_languages=True,
            navigator_platform=True,
            navigator_vendor=True,
            navigator_hardware_concurrency=True,
            webgl_vendor=True,
            chrome_runtime=True,
            navigator_user_agent=True,
        )
        stealth.apply_stealth_sync(self.page)

        # Additional stealth: override navigator properties
        self.page.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Override platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            // Override hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            // Override device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });

            // Spoof WebGL vendor/renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };

            // Override chrome object (some sites check for it even on Firefox)
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        logger.info("[Manta] Firefox stealth browser ready")

    def close(self):
        """Close browser and cleanup."""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")

    def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Random delay to simulate human behavior."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def human_scroll(self):
        """Scroll page like a human would."""
        # Get page height
        height = self.page.evaluate("document.body.scrollHeight")

        # Scroll in chunks with random pauses
        current = 0
        while current < height:
            scroll_amount = random.randint(200, 500)
            current += scroll_amount
            self.page.evaluate(f"window.scrollTo(0, {current})")
            time.sleep(random.uniform(0.1, 0.3))

        # Scroll back up a bit
        self.page.evaluate(f"window.scrollTo(0, {random.randint(0, 300)})")

    def move_mouse_randomly(self):
        """Move mouse to simulate human presence."""
        try:
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 1800)
                y = random.randint(100, 900)
                self.page.mouse.move(x, y)
                time.sleep(random.uniform(0.05, 0.15))
        except:
            pass

    def search(self, city: str, state: str, category: str, max_results: int = 50) -> List[Dict]:
        """
        Search Manta for businesses using homepage search form.

        Args:
            city: City name
            state: State abbreviation
            category: Business category to search
            max_results: Maximum results to return

        Returns:
            List of business dictionaries
        """
        results = []

        try:
            logger.info(f"[Manta] Searching: {category} in {city}, {state}")

            # Navigate to homepage
            self.page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=30000)
            self.random_delay(1.5, 2.5)

            # Find search inputs by name attribute
            search_input = self.page.query_selector('input[name="search"]')
            location_input = self.page.query_selector('input[name="location"]')

            if not search_input:
                logger.error("[Manta] Could not find search input")
                return []

            # Fill search form
            search_input.fill(category)
            self.random_delay(0.3, 0.6)

            if location_input:
                location_input.fill(f"{city}, {state}")
                self.random_delay(0.3, 0.6)

            # Click submit button
            submit_btn = self.page.query_selector('button')
            if submit_btn:
                submit_btn.click()
            else:
                self.page.keyboard.press('Enter')

            # Wait for AJAX results to load (Manta loads results via JavaScript)
            logger.debug("[Manta] Waiting for AJAX results...")
            self.random_delay(6.0, 8.0)

            # Scroll to trigger lazy loading
            for _ in range(3):
                self.page.evaluate('window.scrollBy(0, 500)')
                time.sleep(0.5)

            self.random_delay(1.5, 2.5)

            # Get content and parse
            content = self.page.content()
            current_url = self.page.url
            logger.debug(f"[Manta] Results URL: {current_url}")

            # Parse results
            results = self._parse_results(content, category, city, state)
            logger.info(f"[Manta] Found {len(results)} results")

        except Exception as e:
            logger.error(f"[Manta] Error: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        return results[:max_results]

    def _parse_results(self, html: str, category: str, city: str = '', state: str = '') -> List[Dict]:
        """Parse Manta search results from company links."""
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        seen_names = set()

        # Manta loads results via JavaScript - extract from company links
        company_links = soup.select('a[href*="/c/"]')
        logger.debug(f"[Manta] Found {len(company_links)} company links")

        for link in company_links:
            try:
                name = link.get_text(strip=True)

                # Skip empty, short names, or already seen
                if not name or len(name) < 3:
                    continue

                name_lower = name.lower()
                if name_lower in seen_names:
                    continue
                seen_names.add(name_lower)

                # Build business record
                href = link.get('href', '')
                manta_url = f"{self.BASE_URL}{href}" if href.startswith('/') else href

                business = {
                    'name': name,
                    'phone': '',
                    'address': '',
                    'city': city,
                    'state': state,
                    'zip': '',
                    'website': '',
                    'category': category,
                    'source': 'manta',
                    'manta_url': manta_url,
                }

                # Try to find parent container with more info
                parent = link.find_parent(['div', 'article', 'li', 'section'])
                if parent:
                    # Look for phone
                    phone_el = parent.select_one('[href^="tel:"]')
                    if phone_el:
                        phone = phone_el.get('href', '').replace('tel:', '')
                        business['phone'] = self._clean_phone(phone)

                    # Look for address
                    addr_el = parent.select_one('.address, [class*="address"], [class*="street"]')
                    if addr_el:
                        business['address'] = addr_el.get_text(strip=True)

                    # Look for location info
                    loc_el = parent.select_one('[class*="location"], [class*="city"]')
                    if loc_el:
                        loc_text = loc_el.get_text(strip=True)
                        match = re.match(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})?', loc_text)
                        if match:
                            business['city'] = match.group(1).strip()
                            business['state'] = match.group(2)
                            business['zip'] = match.group(3) or ''

                results.append(business)

            except Exception as e:
                logger.debug(f"Parse error: {e}")
                continue

        return results

    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number."""
        if not phone:
            return ''

        digits = re.sub(r'[^\d]', '', phone)

        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            digits = digits[1:]
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

        return phone

    def search_priority_categories(self, city: str, state: str) -> List[Dict]:
        """
        Search only priority categories (faster).

        Args:
            city: City name
            state: State abbreviation

        Returns:
            Combined list of businesses
        """
        return self.search_multiple_categories(city, state, self.PRIORITY_CATEGORIES)

    def search_multiple_categories(
        self,
        city: str,
        state: str,
        categories: List[str] = None
    ) -> List[Dict]:
        """
        Search multiple categories.

        Args:
            city: City name
            state: State abbreviation
            categories: List of categories (uses PRIORITY_CATEGORIES if None)

        Returns:
            Combined list of unique businesses
        """
        if categories is None:
            categories = self.PRIORITY_CATEGORIES

        all_results = []
        seen_names = set()

        for category in categories:
            try:
                results = self.search(city, state, category)

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

        logger.info(f"[Manta] Total unique businesses: {len(all_results)}")
        return all_results


# Test function
def test_manta():
    """Test Manta scraper with stealth."""
    print("Testing Manta Playwright scraper with Firefox stealth...")

    with MantaPlaywright(headless=True) as manta:
        results = manta.search('Oklahoma City', 'OK', 'landscaping')
        print(f"\nFound {len(results)} results:")

        for r in results[:10]:
            print(f"  - {r.get('name')}")
            print(f"    Phone: {r.get('phone')}")
            print(f"    Address: {r.get('address')}")
            print()

    return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_manta()
