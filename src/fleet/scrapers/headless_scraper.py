"""
Base Headless Browser Scraper
=============================
Uses Playwright to run a real Chromium browser for scraping.
Bypasses anti-bot protection that blocks simple HTTP requests.
"""

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
import random
import time
import logging
from typing import Optional

logger = logging.getLogger('HeadlessScraper')


class HeadlessScraper:
    """
    Base class for headless browser scraping.
    Uses Playwright to run a real Chromium browser.

    Usage:
        with HeadlessScraper() as scraper:
            scraper.page.goto('https://example.com')
            html = scraper.page.content()
    """

    def __init__(self, headless: bool = True):
        """
        Initialize scraper.

        Args:
            headless: Run browser without visible window (default True)
        """
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start_browser(self):
        """Start the browser."""
        logger.info("Starting headless browser...")

        self.playwright = sync_playwright().start()

        # Launch Chromium with anti-detection settings
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certifcate-errors',
                '--ignore-certifcate-errors-spki-list',
            ]
        )

        # Create context with realistic settings
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Chicago',
            geolocation={'latitude': 35.4676, 'longitude': -97.5164},  # OKC
            permissions=['geolocation'],
        )

        # Add stealth scripts to hide automation
        self.context.add_init_script("""
            // Hide webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Hide automation
            window.chrome = { runtime: {} };

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        self.page = self.context.new_page()

        # Block unnecessary resources for speed
        def handle_route(route):
            if route.request.resource_type in ['image', 'font', 'media']:
                route.abort()
            else:
                route.continue_()

        self.page.route("**/*", handle_route)

        logger.info("Browser started successfully")

    def close_browser(self):
        """Clean up browser resources."""
        logger.info("Closing browser...")
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
            logger.debug(f"Error closing browser: {e}")

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    def random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Random delay to appear human-like."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def scroll_page(self, scroll_pause: float = 0.5):
        """Scroll down the page like a human would."""
        try:
            # Scroll to 30%
            self.page.evaluate("""
                window.scrollTo({
                    top: document.body.scrollHeight * 0.3,
                    behavior: 'smooth'
                });
            """)
            time.sleep(scroll_pause)

            # Scroll to 60%
            self.page.evaluate("""
                window.scrollTo({
                    top: document.body.scrollHeight * 0.6,
                    behavior: 'smooth'
                });
            """)
            time.sleep(scroll_pause)

            # Scroll to bottom
            self.page.evaluate("""
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)
            time.sleep(scroll_pause)

        except Exception as e:
            logger.debug(f"Scroll error: {e}")

    def wait_for_content(self, selector: str, timeout: int = 10000):
        """Wait for a specific element to appear."""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except:
            return False

    def safe_goto(self, url: str, timeout: int = 30000) -> bool:
        """Navigate to URL with error handling."""
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False

    def get_page_content(self) -> str:
        """Get current page HTML content."""
        try:
            return self.page.content()
        except:
            return ""

    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_browser()
        return False


# Quick test function
def test_headless():
    """Test the headless browser."""
    print("Testing headless browser...")

    with HeadlessScraper() as scraper:
        print("Navigating to example.com...")
        scraper.safe_goto("https://example.com")
        scraper.random_delay(1, 2)

        html = scraper.get_page_content()
        print(f"Page content length: {len(html)} chars")
        print("Success!" if "Example Domain" in html else "Failed to load page")


if __name__ == '__main__':
    test_headless()
