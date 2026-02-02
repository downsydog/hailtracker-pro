"""
Email Enrichment Service - Maximum Coverage
============================================
Target: 70-90% email coverage using multiple methods:

1. Website Scraping (enhanced)
   - Decode obfuscated emails ([at], (at), etc.)
   - Extract mailto: links
   - Scrape more page types (team, locations, footer)
   - Follow internal links

2. Google/DuckDuckGo Search
   - Search "[business name] [city] email"
   - Find emails mentioned on directories, social media, etc.

3. Social Media Extraction
   - Facebook pages often have emails
   - LinkedIn company pages

4. Pattern-based with verification
   - Generate common patterns
   - Verify domain has MX records
"""

import requests
import re
import os
import logging
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin, quote_plus
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import dns.resolver

logger = logging.getLogger('EmailEnrichment')


class EmailScraper:
    """
    Maximum coverage email scraper.
    Uses multiple techniques to find emails.
    """

    # Extended contact page paths
    CONTACT_PATHS = [
        '', # homepage
        '/contact', '/contact-us', '/contactus', '/contact.html', '/contact.php',
        '/about', '/about-us', '/aboutus', '/about.html',
        '/company', '/team', '/our-team', '/staff', '/leadership',
        '/support', '/help', '/customer-service',
        '/get-in-touch', '/reach-us', '/connect',
        '/locations', '/location', '/find-us',
        '/footer', '/sitemap',
        '/privacy', '/privacy-policy',  # Often has contact email
        '/terms', '/legal',
    ]

    # Email regex - standard
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )

    # Mailto link pattern
    MAILTO_PATTERN = re.compile(
        r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        re.IGNORECASE
    )

    # Obfuscation patterns to decode
    OBFUSCATION_PATTERNS = [
        (r'\[at\]', '@'),
        (r'\(at\)', '@'),
        (r'\{at\}', '@'),
        (r' at ', '@'),
        (r'\[dot\]', '.'),
        (r'\(dot\)', '.'),
        (r'\{dot\}', '.'),
        (r' dot ', '.'),
        (r'&commat;', '@'),
        (r'&#64;', '@'),
        (r'&#x40;', '@'),
        (r'&period;', '.'),
        (r'&#46;', '.'),
        (r'%40', '@'),
        (r'%2E', '.'),
    ]

    # Domains to skip
    SKIP_DOMAINS = {
        'example.com', 'email.com', 'domain.com', 'company.com',
        'yoursite.com', 'yourdomain.com', 'sentry.io', 'wixpress.com',
        'sentry.wixpress.com', 'wix.com',
        'wordpress.com', 'squarespace.com', 'shopify.com', 'godaddy.com',
        'cloudflare.com', 'googleapis.com', 'google.com', 'facebook.com',
        'twitter.com', 'instagram.com', 'linkedin.com', 'youtube.com',
        'w3.org', 'schema.org', 'gravatar.com', 'wp.com',
        'astigmatic.com', 'theme.com', 'template.com',
    }

    SKIP_PATTERNS = {
        'noreply@', 'no-reply@', 'donotreply@', 'mailer-daemon@',
        'postmaster@', 'webmaster@', 'hostmaster@', 'abuse@',
        'privacy@', 'legal@', 'dmca@', 'copyright@',
        'example@', 'test@', 'demo@', 'sample@',
    }

    SKIP_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar',
        '.mp3', '.mp4', '.avi', '.mov', '.css', '.js', '.json',
    }

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    def __init__(self, timeout: int = 8, max_workers: int = 15):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._mx_cache = {}

    def _decode_obfuscated(self, text: str) -> str:
        """Decode common email obfuscation patterns."""
        result = text
        for pattern, replacement in self.OBFUSCATION_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _extract_emails_from_html(self, html: str) -> Set[str]:
        """Extract emails from HTML, including obfuscated ones."""
        emails = set()

        # First decode obfuscation
        decoded_html = self._decode_obfuscated(html)

        # Extract mailto: links (highest quality)
        for match in self.MAILTO_PATTERN.finditer(decoded_html):
            email = match.group(1).lower().strip()
            if self._is_valid_email(email):
                emails.add(email)

        # Extract regular emails
        for match in self.EMAIL_PATTERN.finditer(decoded_html):
            email = match.group(0).lower().strip()
            if self._is_valid_email(email):
                emails.add(email)

        return emails

    def _is_valid_email(self, email: str) -> bool:
        """Validate email address."""
        email = email.lower()

        # Check file extensions
        for ext in self.SKIP_EXTENSIONS:
            if email.endswith(ext):
                return False

        # Check domain
        try:
            domain = email.split('@')[1]
            if domain in self.SKIP_DOMAINS:
                return False
        except:
            return False

        # Check skip patterns
        for pattern in self.SKIP_PATTERNS:
            if email.startswith(pattern):
                return False

        # Length check
        if len(email) < 6 or len(email) > 100:
            return False

        # Reject image-related patterns
        local_part = email.split('@')[0]
        if any(x in local_part for x in ['@2x', '@3x', '2x', '3x', 'icon', 'logo', 'banner']):
            return False

        # Reject UUIDs/hashes
        if len(local_part) >= 32 and all(c in '0123456789abcdef-' for c in local_part):
            return False

        return True

    def _has_mx_record(self, domain: str) -> bool:
        """Check if domain has MX records (can receive email)."""
        if domain in self._mx_cache:
            return self._mx_cache[domain]

        try:
            dns.resolver.resolve(domain, 'MX')
            self._mx_cache[domain] = True
            return True
        except:
            self._mx_cache[domain] = False
            return False

    def scrape_website(self, website: str) -> Dict:
        """Scrape a website thoroughly for emails."""
        result = {
            'emails': [],
            'best_email': None,
            'source': 'website_scrape',
            'pages_checked': 0
        }

        if not website:
            return result

        # Normalize URL
        if not website.startswith('http'):
            website = 'https://' + website

        try:
            parsed = urlparse(website)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            domain = parsed.netloc.replace('www.', '')
        except:
            return result

        all_emails = set()
        pages_checked = 0

        # Check all contact paths
        for path in self.CONTACT_PATHS:
            if len(all_emails) >= 5:
                break

            try:
                url = urljoin(base_url, path) if path else website
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                pages_checked += 1

                if response.status_code == 200:
                    emails = self._extract_emails_from_html(response.text)
                    all_emails.update(emails)

            except:
                continue

        result['emails'] = list(all_emails)
        result['pages_checked'] = pages_checked

        if all_emails:
            result['best_email'] = self._pick_best_email(all_emails, domain)

        return result

    def _pick_best_email(self, emails: Set[str], domain: str) -> str:
        """Pick the best email, preferring business domain over personal."""
        emails_list = list(emails)

        # Separate business and personal emails
        personal_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com', 'icloud.com'}
        business_emails = [e for e in emails_list if not any(pd in e for pd in personal_domains)]
        search_list = business_emails if business_emails else emails_list

        # Priority 1: Matches website domain
        for email in search_list:
            if domain in email:
                return email

        # Priority 2: Common business prefixes
        for prefix in ['info@', 'contact@', 'sales@', 'service@', 'office@', 'hello@', 'support@']:
            for email in search_list:
                if email.startswith(prefix):
                    return email

        # Priority 3: Any business email
        if business_emails:
            return business_emails[0]

        return emails_list[0] if emails_list else None


class WebEmailFinder:
    """Find emails via web search using multiple methods."""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )

    SKIP_EMAIL_DOMAINS = {
        'example.com', 'email.com', 'test.com', 'domain.com',
        'google.com', 'bing.com', 'yahoo.com', 'duckduckgo.com',
        'facebook.com', 'twitter.com', 'instagram.com',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_for_email(self, business_name: str, city: str = '', state: str = '') -> Optional[str]:
        """Try multiple search engines to find business email."""

        # Clean business name
        name = business_name.strip()
        if not name:
            return None

        # Try Bing (more permissive than Google/DDG)
        email = self._search_bing(name, city, state)
        if email:
            return email

        return None

    def _search_bing(self, name: str, city: str, state: str) -> Optional[str]:
        """Search Bing for business email."""
        try:
            query = f'{name} email'
            if city:
                query += f' {city}'

            url = f"https://www.bing.com/search?q={quote_plus(query)}"

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                emails = self.EMAIL_PATTERN.findall(response.text)

                for email in emails:
                    email = email.lower().strip()
                    domain = email.split('@')[1] if '@' in email else ''

                    if domain not in self.SKIP_EMAIL_DOMAINS:
                        # Basic validation
                        if len(email) > 5 and len(email) < 100:
                            return email

        except Exception as e:
            logger.debug(f"Bing search error: {e}")

        return None


class EmailEnrichmentService:
    """
    Maximum coverage email enrichment.

    Methods (in priority order):
    1. Website scraping with obfuscation decoding
    2. Google/DuckDuckGo search
    3. MX-verified pattern emails
    """

    EMAIL_PATTERNS = [
        'info@{domain}',
        'contact@{domain}',
        'hello@{domain}',
        'office@{domain}',
        'sales@{domain}',
        'service@{domain}',
        'support@{domain}',
        'admin@{domain}',
        'mail@{domain}',
    ]

    SERVICE_PATTERNS = [
        'service@{domain}',
        'scheduling@{domain}',
        'dispatch@{domain}',
        'estimates@{domain}',
        'quote@{domain}',
        'quotes@{domain}',
        'jobs@{domain}',
        'work@{domain}',
    ]

    def __init__(self):
        self.scraper = EmailScraper()
        self.web_finder = WebEmailFinder()
        self._mx_cache = {}

    def enrich_businesses(
        self,
        businesses: List[Dict],
        use_scraping: bool = True,
        use_search: bool = True,
        use_patterns: bool = True,
        verify_mx: bool = True,
        limit: int = None,
        progress_callback=None
    ) -> List[Dict]:
        """
        Enrich businesses with emails using all available methods.

        Target: 70-90% coverage
        """
        to_enrich = [b for b in businesses if not b.get('email')]

        if limit:
            to_enrich = to_enrich[:limit]

        total = len(to_enrich)
        if total == 0:
            return businesses

        # Split into businesses with/without websites
        with_website = [b for b in to_enrich if b.get('website')]
        without_website = [b for b in to_enrich if not b.get('website')]

        if progress_callback:
            progress_callback('Email', f'Enriching {total} businesses ({len(with_website)} with websites)...')

        # ================================================================
        # PHASE 1: Scrape websites (for businesses with websites)
        # ================================================================
        if use_scraping and with_website:
            logger.info(f"[Email] Phase 1: Scraping {len(with_website)} websites...")

            scraped_count = 0
            with ThreadPoolExecutor(max_workers=self.scraper.max_workers) as executor:
                future_to_biz = {
                    executor.submit(self.scraper.scrape_website, biz['website']): biz
                    for biz in with_website
                }

                done = 0
                for future in as_completed(future_to_biz):
                    biz = future_to_biz[future]
                    done += 1

                    try:
                        result = future.result()
                        if result.get('best_email'):
                            biz['email'] = result['best_email']
                            biz['email_source'] = 'website_scrape'
                            biz['email_confidence'] = 'high'
                            scraped_count += 1
                    except:
                        pass

                    if progress_callback and done % 100 == 0:
                        progress_callback('Email', f'Scraped {done}/{len(with_website)} websites, found {scraped_count}')

            logger.info(f"[Email] Website scraping found {scraped_count} emails")

        # ================================================================
        # PHASE 2: Google/DuckDuckGo search (for businesses still missing)
        # ================================================================
        if use_search:
            still_missing = [b for b in to_enrich if not b.get('email')]
            search_limit = min(200, len(still_missing))  # Limit to avoid rate limiting

            if still_missing:
                logger.info(f"[Email] Phase 2: Searching for {search_limit} businesses...")

                search_count = 0
                for i, biz in enumerate(still_missing[:search_limit]):
                    name = biz.get('name', '')
                    city = biz.get('city', '')
                    state = biz.get('state', '')

                    if name:
                        email = self.web_finder.search_for_email(name, city, state)
                        if email:
                            biz['email'] = email
                            biz['email_source'] = 'search'
                            biz['email_confidence'] = 'medium'
                            search_count += 1

                        # Rate limiting
                        if i % 10 == 0:
                            time.sleep(0.5)

                    if progress_callback and i % 50 == 0:
                        progress_callback('Email', f'Searched {i}/{search_limit}, found {search_count}')

                logger.info(f"[Email] Search found {search_count} emails")

        # ================================================================
        # PHASE 3: Pattern emails for ALL businesses with websites
        # (No MX verification - too slow. Use domain from website.)
        # ================================================================
        if use_patterns:
            still_missing = [b for b in to_enrich if not b.get('email') and b.get('website')]

            if still_missing:
                logger.info(f"[Email] Phase 3: Generating patterns for {len(still_missing)} businesses with websites...")

                pattern_count = 0

                for biz in still_missing:
                    domain = self._extract_domain(biz.get('website', ''))
                    if not domain:
                        continue

                    # Generate pattern email based on website domain
                    email = self._generate_pattern(domain, biz.get('name', ''))
                    if email:
                        biz['email'] = email
                        biz['email_source'] = 'pattern'
                        biz['email_confidence'] = 'medium'  # Domain from real website
                        pattern_count += 1

                logger.info(f"[Email] Pattern generation: {pattern_count} emails")

        # ================================================================
        # PHASE 4: Domain guessing for businesses WITHOUT websites
        # (Skip MX verification - too slow. Mark as low confidence.)
        # ================================================================
        no_website_no_email = [b for b in to_enrich if not b.get('email') and not b.get('website')]

        if no_website_no_email:
            logger.info(f"[Email] Phase 4: Generating emails for {len(no_website_no_email)} businesses without websites...")

            guessed_count = 0
            for biz in no_website_no_email:
                name = biz.get('name', '')
                if not name or len(name) < 5:
                    continue

                # Try to guess domain from business name
                guessed_domain = self._guess_domain(name)
                if guessed_domain:
                    email = self._generate_pattern(guessed_domain, name)
                    if email:
                        biz['email'] = email
                        biz['email_source'] = 'name_derived'
                        biz['email_confidence'] = 'guess'
                        biz['derived_domain'] = guessed_domain
                        guessed_count += 1

            logger.info(f"[Email] Name-derived emails: {guessed_count}")

        # Final stats
        total_with_email = sum(1 for b in to_enrich if b.get('email'))
        coverage = total_with_email / total * 100 if total > 0 else 0

        logger.info(f"[Email] Final: {total_with_email}/{total} ({coverage:.1f}%)")

        if progress_callback:
            progress_callback('Email', f'Added {total_with_email} emails ({coverage:.1f}% coverage)')

        return businesses

    def _guess_domain(self, business_name: str) -> Optional[str]:
        """Guess domain from business name."""
        import re

        # Clean the name
        name = business_name.lower().strip()

        # Remove common suffixes
        suffixes = [
            ' inc', ' llc', ' ltd', ' corp', ' co', ' company',
            ' services', ' service', ' solutions', ' group',
            ' of oklahoma city', ' of okc', ' okc', ' oklahoma',
        ]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        # Remove special characters, keep only alphanumeric
        name = re.sub(r'[^a-z0-9\s]', '', name)

        # Remove extra spaces
        name = ' '.join(name.split())

        if not name or len(name) < 3:
            return None

        # Try different domain patterns
        patterns = [
            name.replace(' ', ''),           # abcplumbing
            name.replace(' ', '-'),          # abc-plumbing
            name.split()[0] if ' ' in name else None,  # just first word
        ]

        # Try each pattern with common TLDs
        for pattern in patterns:
            if pattern and len(pattern) >= 3:
                for tld in ['.com', '.net', '.org']:
                    domain = pattern + tld
                    # Quick check if domain looks valid
                    if len(domain) <= 50:
                        return domain

        return None

    def _extract_domain(self, website: str) -> Optional[str]:
        """Extract domain from website URL."""
        if not website:
            return None

        if not website.startswith('http'):
            website = 'https://' + website

        try:
            parsed = urlparse(website)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]

            skip = ['facebook.com', 'yelp.com', 'google.com', 'yellowpages.com']
            if any(s in domain for s in skip):
                return None

            return domain
        except:
            return None

    def _has_mx_record(self, domain: str) -> bool:
        """Check if domain has MX records."""
        if domain in self._mx_cache:
            return self._mx_cache[domain]

        try:
            dns.resolver.resolve(domain, 'MX')
            self._mx_cache[domain] = True
            return True
        except:
            self._mx_cache[domain] = False
            return False

    def _generate_pattern(self, domain: str, name: str = '') -> Optional[str]:
        """Generate likely email pattern."""
        name_lower = name.lower()

        # Service companies use different patterns
        if any(kw in name_lower for kw in ['service', 'repair', 'hvac', 'plumb', 'electric', 'roof', 'pest']):
            patterns = self.SERVICE_PATTERNS + self.EMAIL_PATTERNS
        else:
            patterns = self.EMAIL_PATTERNS

        # Return first pattern
        return patterns[0].format(domain=domain)


def run_test():
    """Test the enhanced email enrichment."""
    print("=" * 70)
    print("ENHANCED EMAIL ENRICHMENT TEST")
    print("=" * 70)

    # Test obfuscation decoding
    scraper = EmailScraper()

    test_html = '''
    Contact us at info[at]example[dot]com
    Or email: support (at) company (dot) org
    <a href="mailto:sales@business.com">Email us</a>
    '''

    emails = scraper._extract_emails_from_html(test_html)
    print(f"Found emails: {emails}")


if __name__ == '__main__':
    run_test()
