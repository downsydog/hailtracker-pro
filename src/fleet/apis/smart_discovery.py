"""
Smart Discovery Service
=======================
Optimized business discovery with best contact coverage.

Strategy:
1. Prioritize HERE + Yelp (best phone/website coverage)
2. Use Google with Place Details enrichment
3. Add TomTom for additional coverage
4. Enrich with emails using Hunter.io or patterns
5. Deduplicate across all sources

This combines all APIs intelligently for maximum contact quality.
"""

import os
import logging
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
import time

logger = logging.getLogger('SmartDiscovery')


@dataclass
class DiscoveryStats:
    """Statistics from a discovery run."""
    total_found: int = 0
    unique_businesses: int = 0
    with_phone: int = 0
    with_email: int = 0
    with_website: int = 0
    with_address: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)


class SmartDiscoveryService:
    """
    Intelligent business discovery with optimized contact coverage.

    Combines multiple APIs with smart prioritization:
    - HERE: 100% phone coverage
    - Yelp: 98.8% phone, 100% website
    - Google: Best coverage, needs enrichment for contacts
    - TomTom: Good backup source
    """

    def __init__(self):
        """Initialize all API clients."""
        from src.fleet.apis.yelp_api import YelpAPI
        from src.fleet.apis.here_api import HereAPI
        from src.fleet.apis.tomtom_api import TomTomAPI
        from src.fleet.apis.google_places_api import GooglePlacesAPI
        from src.fleet.apis.email_enrichment import EmailEnrichmentService

        self.yelp = YelpAPI()
        self.here = HereAPI()
        self.tomtom = TomTomAPI()
        self.google = GooglePlacesAPI()
        self.email_service = EmailEnrichmentService()

        # Track what's configured
        self.configured_apis = []
        if self.here.is_configured():
            self.configured_apis.append('HERE')
        if self.yelp.is_configured():
            self.configured_apis.append('Yelp')
        if self.google.is_configured():
            self.configured_apis.append('Google')
        if self.tomtom.is_configured():
            self.configured_apis.append('TomTom')

    def discover(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 25000,
        enrich_google_contacts: bool = True,
        enrich_emails: bool = True,
        google_enrich_limit: int = 100,
        email_enrich_limit: int = 50,
        progress_callback: Callable = None
    ) -> tuple[List[Dict], DiscoveryStats]:
        """
        Run smart discovery with optimized contact coverage.

        Priority order (for contact quality):
        1. HERE (100% phone)
        2. Yelp (98.8% phone, 100% website)
        3. Google with enrichment
        4. TomTom (94.6% phone)

        Args:
            lat, lon: Center point
            radius_meters: Search radius
            enrich_google_contacts: Fetch Place Details for Google results
            enrich_emails: Run email enrichment on results
            google_enrich_limit: Max Google businesses to enrich
            email_enrich_limit: Max businesses to add emails to
            progress_callback: Optional callback(stage, message)

        Returns:
            Tuple of (businesses list, stats)
        """
        all_businesses = []
        seen_keys = set()  # For deduplication
        stats = DiscoveryStats()

        def log_progress(stage: str, message: str):
            logger.info(f"[{stage}] {message}")
            if progress_callback:
                progress_callback(stage, message)

        # ====================================================================
        # STAGE 1: HERE API (Best for phone - 100%)
        # ====================================================================
        if self.here.is_configured():
            log_progress("HERE", "Searching all categories...")
            try:
                results = self.here.search_all_categories(lat, lon, radius_meters)
                new_count = self._add_results(results, all_businesses, seen_keys, 'here')
                stats.by_source['HERE'] = len(results)
                log_progress("HERE", f"Found {len(results)} businesses ({new_count} unique)")
            except Exception as e:
                log_progress("HERE", f"Error: {e}")

        # ====================================================================
        # STAGE 2: Yelp API (Best for phone + website)
        # ====================================================================
        if self.yelp.is_configured():
            log_progress("Yelp", "Searching all categories...")
            try:
                results = self.yelp.search_all_categories(lat, lon, radius_meters)
                new_count = self._add_results(results, all_businesses, seen_keys, 'yelp')
                stats.by_source['Yelp'] = len(results)
                log_progress("Yelp", f"Found {len(results)} businesses ({new_count} unique)")
            except Exception as e:
                log_progress("Yelp", f"Error: {e}")

        # ====================================================================
        # STAGE 3: Google Places with Contact Enrichment
        # ====================================================================
        if self.google.is_configured():
            log_progress("Google", "Searching all categories...")
            try:
                results = self.google.search_all_categories(lat, lon, radius_meters)
                new_count = self._add_results(results, all_businesses, seen_keys, 'google')
                stats.by_source['Google'] = len(results)
                log_progress("Google", f"Found {len(results)} businesses ({new_count} unique)")
            except Exception as e:
                log_progress("Google", f"Error: {e}")

        # ====================================================================
        # STAGE 4: TomTom (Additional coverage)
        # ====================================================================
        if self.tomtom.is_configured():
            log_progress("TomTom", "Searching all categories...")
            try:
                results = self.tomtom.search_all_categories(lat, lon, radius_meters)
                new_count = self._add_results(results, all_businesses, seen_keys, 'tomtom')
                stats.by_source['TomTom'] = len(results)
                log_progress("TomTom", f"Found {len(results)} businesses ({new_count} unique)")
            except Exception as e:
                log_progress("TomTom", f"Error: {e}")

        # ====================================================================
        # STAGE 5: Email Enrichment (Maximum Coverage)
        # ====================================================================
        if enrich_emails:
            log_progress("Email", "Finding emails (scraping + search + patterns)...")
            try:
                # Enrich ALL businesses without email (not just those with websites)
                businesses_without_email = [
                    b for b in all_businesses
                    if not b.get('email')
                ]

                if businesses_without_email:
                    log_progress("Email", f"Finding emails for {len(businesses_without_email)} businesses...")

                    # Use all methods for maximum coverage
                    self.email_service.enrich_businesses(
                        businesses_without_email,
                        use_scraping=True,   # Scrape websites with obfuscation decoding
                        use_search=True,     # Search Google/DuckDuckGo for emails
                        use_patterns=True,   # MX-verified pattern emails
                        verify_mx=True,      # Only use patterns if domain accepts email
                        limit=None,
                        progress_callback=lambda stage, msg: log_progress(stage, msg)
                    )

                    # Count results by source
                    scraped = sum(1 for b in businesses_without_email if b.get('email_source') == 'website_scrape')
                    searched = sum(1 for b in businesses_without_email if b.get('email_source') == 'search')
                    pattern = sum(1 for b in businesses_without_email if 'pattern' in str(b.get('email_source', '')))
                    total_emails = scraped + searched + pattern

                    log_progress("Email", f"Found {total_emails} emails (scraped: {scraped}, searched: {searched}, pattern: {pattern})")
            except Exception as e:
                log_progress("Email", f"Error: {e}")

        # ====================================================================
        # Calculate final stats
        # ====================================================================
        stats.total_found = sum(stats.by_source.values())
        stats.unique_businesses = len(all_businesses)

        for biz in all_businesses:
            if biz.get('phone') and len(str(biz.get('phone', ''))) > 5:
                stats.with_phone += 1
            if biz.get('email') and '@' in str(biz.get('email', '')):
                stats.with_email += 1
            if biz.get('website') and len(str(biz.get('website', ''))) > 5:
                stats.with_website += 1
            if biz.get('address') and len(str(biz.get('address', ''))) > 5:
                stats.with_address += 1

            # Category stats
            cat = biz.get('category', 'Unknown')
            stats.by_category[cat] = stats.by_category.get(cat, 0) + 1

        return all_businesses, stats

    def _add_results(
        self,
        results: List[Dict],
        all_businesses: List[Dict],
        seen_keys: set,
        source: str
    ) -> int:
        """Add results with deduplication. Returns count of new businesses."""
        new_count = 0

        for biz in results:
            # Create dedup key from name + partial address
            name = (biz.get('name') or '').lower().strip()
            address = (biz.get('address') or '').lower()[:30]
            key = (name, address)

            if key not in seen_keys and name:
                seen_keys.add(key)
                biz['source'] = source
                all_businesses.append(biz)
                new_count += 1

        return new_count

    def discover_with_report(
        self,
        lat: float,
        lon: float,
        radius_meters: int = 25000,
        **kwargs
    ) -> str:
        """
        Run discovery and return formatted report.

        Returns:
            Formatted string report of results
        """
        businesses, stats = self.discover(lat, lon, radius_meters, **kwargs)

        report = []
        report.append("=" * 70)
        report.append("SMART DISCOVERY REPORT")
        report.append("=" * 70)
        report.append("")
        report.append(f"Location: {lat}, {lon}")
        report.append(f"Radius: {radius_meters/1000:.0f} km")
        report.append("")
        report.append("API RESULTS:")
        for source, count in stats.by_source.items():
            report.append(f"  {source}: {count}")
        report.append("")
        report.append(f"TOTAL UNIQUE: {stats.unique_businesses}")
        report.append("")
        report.append("CONTACT COVERAGE:")
        if stats.unique_businesses > 0:
            report.append(f"  Phone:   {stats.with_phone} ({stats.with_phone/stats.unique_businesses*100:.1f}%)")
            report.append(f"  Email:   {stats.with_email} ({stats.with_email/stats.unique_businesses*100:.1f}%)")
            report.append(f"  Website: {stats.with_website} ({stats.with_website/stats.unique_businesses*100:.1f}%)")
            report.append(f"  Address: {stats.with_address} ({stats.with_address/stats.unique_businesses*100:.1f}%)")
        report.append("")
        report.append("=" * 70)

        return "\n".join(report)

    def get_configured_apis(self) -> List[str]:
        """Return list of configured API names."""
        return self.configured_apis


def discover_okc_storm():
    """Discover businesses for Oklahoma City storm."""
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 70)
    print("SMART DISCOVERY - OKLAHOMA CITY STORM")
    print("October 23, 2025")
    print("=" * 70)
    print()

    service = SmartDiscoveryService()

    print(f"Configured APIs: {', '.join(service.get_configured_apis())}")
    print()

    # Run discovery
    businesses, stats = service.discover(
        lat=35.4676,
        lon=-97.5164,
        radius_meters=25000,
        enrich_google_contacts=True,
        enrich_emails=True,
        google_enrich_limit=100,
        email_enrich_limit=100,
        progress_callback=lambda stage, msg: print(f"[{stage}] {msg}")
    )

    print()
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print()
    print(f"Total Found: {stats.total_found}")
    print(f"Unique Businesses: {stats.unique_businesses}")
    print()
    print("Contact Coverage:")
    if stats.unique_businesses > 0:
        print(f"  Phone:   {stats.with_phone} ({stats.with_phone/stats.unique_businesses*100:.1f}%)")
        print(f"  Email:   {stats.with_email} ({stats.with_email/stats.unique_businesses*100:.1f}%)")
        print(f"  Website: {stats.with_website} ({stats.with_website/stats.unique_businesses*100:.1f}%)")
        print(f"  Address: {stats.with_address} ({stats.with_address/stats.unique_businesses*100:.1f}%)")
    print()

    # Show sample with complete contact info
    print("=" * 70)
    print("SAMPLE BUSINESSES WITH COMPLETE CONTACT INFO")
    print("=" * 70)
    print()

    complete = [b for b in businesses if b.get('phone') and b.get('email') and b.get('website')]
    if not complete:
        complete = [b for b in businesses if b.get('phone') and b.get('website')][:10]

    for biz in complete[:10]:
        print(f"[{biz.get('source', 'unknown').upper()}] {biz.get('name', 'Unknown')}")
        print(f"  Phone:   {biz.get('phone', 'N/A')}")
        print(f"  Email:   {biz.get('email', 'N/A')}")
        print(f"  Website: {str(biz.get('website', 'N/A'))[:50]}")
        print(f"  Address: {biz.get('address', 'N/A')}")
        print()

    return businesses, stats


if __name__ == '__main__':
    discover_okc_storm()
