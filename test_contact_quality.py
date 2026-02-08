"""
Contact Info Quality Analysis
Oklahoma City Storm - October 23, 2025

Check data quality for discovered businesses
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Oklahoma City coordinates
OKC_LAT = 35.4676
OKC_LON = -97.5164
RADIUS_METERS = 25000


def analyze_contact_quality():
    print("=" * 80)
    print("CONTACT INFO QUALITY ANALYSIS")
    print("Oklahoma City Storm - October 23, 2025")
    print("=" * 80)
    print()

    # Store results by source
    results_by_source = {}

    # ========================================================================
    # 1. YELP API
    # ========================================================================
    print("Fetching from Yelp...")
    try:
        from src.fleet.apis.yelp_api import YelpAPI
        yelp = YelpAPI()
        if yelp.is_configured():
            results = yelp.search_all_categories(OKC_LAT, OKC_LON, RADIUS_METERS)
            results_by_source['Yelp'] = results
            print(f"  Got {len(results)} businesses")
        else:
            results_by_source['Yelp'] = []
    except Exception as e:
        print(f"  Error: {e}")
        results_by_source['Yelp'] = []

    # ========================================================================
    # 2. HERE API
    # ========================================================================
    print("Fetching from HERE...")
    try:
        from src.fleet.apis.here_api import HereAPI
        here = HereAPI()
        if here.is_configured():
            results = here.search_priority_categories(OKC_LAT, OKC_LON, RADIUS_METERS)
            results_by_source['HERE'] = results
            print(f"  Got {len(results)} businesses")
        else:
            results_by_source['HERE'] = []
    except Exception as e:
        print(f"  Error: {e}")
        results_by_source['HERE'] = []

    # ========================================================================
    # 3. TOMTOM API
    # ========================================================================
    print("Fetching from TomTom...")
    try:
        from src.fleet.apis.tomtom_api import TomTomAPI
        tomtom = TomTomAPI()
        if tomtom.is_configured():
            results = tomtom.search_priority_categories(OKC_LAT, OKC_LON, RADIUS_METERS)
            results_by_source['TomTom'] = results
            print(f"  Got {len(results)} businesses")
        else:
            results_by_source['TomTom'] = []
    except Exception as e:
        print(f"  Error: {e}")
        results_by_source['TomTom'] = []

    # ========================================================================
    # 4. GOOGLE PLACES API
    # ========================================================================
    print("Fetching from Google...")
    try:
        from src.fleet.apis.google_places_api import GooglePlacesAPI
        google = GooglePlacesAPI()
        if google.is_configured():
            results = google.search_priority_categories(OKC_LAT, OKC_LON, RADIUS_METERS)
            results_by_source['Google'] = results
            print(f"  Got {len(results)} businesses")
        else:
            results_by_source['Google'] = []
    except Exception as e:
        print(f"  Error: {e}")
        results_by_source['Google'] = []

    # ========================================================================
    # 5. OSM DATABASE
    # ========================================================================
    print("Fetching from OSM database...")
    try:
        from src.business.fleet_locations import FleetLocationManager
        db_path = os.path.join(os.path.dirname(__file__), "data", "fleet_locations.db")
        if os.path.exists(db_path):
            manager = FleetLocationManager(db_path)
            results = manager.get_locations_in_bbox(35.25, -97.75, 35.65, -97.30)
            results_by_source['OSM'] = results
            print(f"  Got {len(results)} businesses")
        else:
            results_by_source['OSM'] = []
    except Exception as e:
        print(f"  Error: {e}")
        results_by_source['OSM'] = []

    print()
    print("=" * 80)
    print("CONTACT INFO QUALITY BY SOURCE")
    print("=" * 80)
    print()

    # Analyze each source
    all_businesses = []
    source_stats = {}

    for source, businesses in results_by_source.items():
        total = len(businesses)
        if total == 0:
            continue

        has_phone = 0
        has_email = 0
        has_website = 0
        has_address = 0
        has_coords = 0

        for biz in businesses:
            phone = biz.get('phone', '') or ''
            email = biz.get('email', '') or ''
            website = biz.get('website', '') or ''
            address = biz.get('address', '') or ''
            lat = biz.get('latitude') or biz.get('lat')
            lon = biz.get('longitude') or biz.get('lon')

            if phone and len(phone) > 5:
                has_phone += 1
            if email and '@' in email:
                has_email += 1
            if website and ('http' in website or 'www' in website or '.com' in website):
                has_website += 1
            if address and len(address) > 5:
                has_address += 1
            if lat and lon:
                has_coords += 1

            # Add source tag
            biz['source'] = source.lower()
            all_businesses.append(biz)

        source_stats[source] = {
            'total': total,
            'phone': has_phone,
            'email': has_email,
            'website': has_website,
            'address': has_address,
            'coords': has_coords,
        }

        print(f"{source}:")
        print(f"  Total businesses: {total}")
        print(f"  With phone:       {has_phone:4} ({has_phone/total*100:5.1f}%)")
        print(f"  With email:       {has_email:4} ({has_email/total*100:5.1f}%)")
        print(f"  With website:     {has_website:4} ({has_website/total*100:5.1f}%)")
        print(f"  With address:     {has_address:4} ({has_address/total*100:5.1f}%)")
        print(f"  With coordinates: {has_coords:4} ({has_coords/total*100:5.1f}%)")
        print()

    # ========================================================================
    # OVERALL TOTALS
    # ========================================================================
    print("=" * 80)
    print("OVERALL TOTALS (ALL SOURCES)")
    print("=" * 80)
    print()

    total_all = sum(s['total'] for s in source_stats.values())
    total_phone = sum(s['phone'] for s in source_stats.values())
    total_email = sum(s['email'] for s in source_stats.values())
    total_website = sum(s['website'] for s in source_stats.values())
    total_address = sum(s['address'] for s in source_stats.values())
    total_coords = sum(s['coords'] for s in source_stats.values())

    print(f"Total businesses:   {total_all}")
    print(f"With phone:         {total_phone:4} ({total_phone/total_all*100:5.1f}%)")
    print(f"With email:         {total_email:4} ({total_email/total_all*100:5.1f}%)")
    print(f"With website:       {total_website:4} ({total_website/total_all*100:5.1f}%)")
    print(f"With address:       {total_address:4} ({total_address/total_all*100:5.1f}%)")
    print(f"With coordinates:   {total_coords:4} ({total_coords/total_all*100:5.1f}%)")
    print()

    # ========================================================================
    # QUALITY SCORE
    # ========================================================================
    print("=" * 80)
    print("DATA QUALITY SCORE BY SOURCE")
    print("=" * 80)
    print()
    print("Quality Score = (phone + address + coords) / 3")
    print()

    for source, stats in source_stats.items():
        total = stats['total']
        if total == 0:
            continue
        phone_pct = stats['phone'] / total * 100
        addr_pct = stats['address'] / total * 100
        coords_pct = stats['coords'] / total * 100
        quality_score = (phone_pct + addr_pct + coords_pct) / 3

        bar_len = int(quality_score / 2)
        bar = "=" * bar_len

        print(f"  {source:10} : {quality_score:5.1f}% [{bar}]")

    print()

    # ========================================================================
    # EXAMPLE BUSINESSES WITH FULL CONTACT INFO
    # ========================================================================
    print("=" * 80)
    print("EXAMPLE BUSINESSES WITH FULL CONTACT INFO")
    print("=" * 80)
    print()

    # Find businesses with the most complete info
    complete_businesses = []
    for biz in all_businesses:
        phone = biz.get('phone', '') or ''
        website = biz.get('website', '') or ''
        address = biz.get('address', '') or ''
        lat = biz.get('latitude') or biz.get('lat')
        lon = biz.get('longitude') or biz.get('lon')

        # Score completeness
        score = 0
        if phone and len(phone) > 5:
            score += 1
        if website and len(website) > 5:
            score += 1
        if address and len(address) > 5:
            score += 1
        if lat and lon:
            score += 1

        if score >= 3:  # At least 3 fields complete
            complete_businesses.append((biz, score))

    # Sort by score and show top examples
    complete_businesses.sort(key=lambda x: -x[1])

    # Group by source
    shown_sources = set()
    examples_shown = 0

    for biz, score in complete_businesses:
        source = biz.get('source', 'unknown')

        # Show 2-3 examples per source
        source_count = sum(1 for b, _ in complete_businesses[:examples_shown+1] if b.get('source') == source)
        if source_count > 3:
            continue

        name = biz.get('name', 'Unknown')
        phone = biz.get('phone', 'N/A') or 'N/A'
        website = biz.get('website', 'N/A') or 'N/A'
        address = biz.get('address', 'N/A') or 'N/A'
        city = biz.get('city', '') or ''
        state = biz.get('state', '') or ''
        category = biz.get('category', 'Unknown') or 'Unknown'
        lat = biz.get('latitude') or biz.get('lat') or 'N/A'
        lon = biz.get('longitude') or biz.get('lon') or 'N/A'

        print(f"[{source.upper()}] {name}")
        print(f"  Category: {category}")
        print(f"  Phone:    {phone}")
        print(f"  Website:  {website[:60]}{'...' if len(str(website)) > 60 else ''}")
        print(f"  Address:  {address}")
        if city or state:
            print(f"  City:     {city}, {state}")
        print(f"  Coords:   {lat}, {lon}")
        print()

        examples_shown += 1
        if examples_shown >= 15:
            break

    # ========================================================================
    # SUMMARY TABLE
    # ========================================================================
    print("=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print()
    print(f"{'Source':<12} {'Total':>8} {'Phone':>8} {'Email':>8} {'Website':>8} {'Address':>8}")
    print("-" * 60)

    for source, stats in sorted(source_stats.items(), key=lambda x: -x[1]['total']):
        print(f"{source:<12} {stats['total']:>8} {stats['phone']:>8} {stats['email']:>8} {stats['website']:>8} {stats['address']:>8}")

    print("-" * 60)
    print(f"{'TOTAL':<12} {total_all:>8} {total_phone:>8} {total_email:>8} {total_website:>8} {total_address:>8}")
    print()

    # Best source for contacts
    print("=" * 80)
    print("BEST SOURCES FOR CONTACT INFO")
    print("=" * 80)
    print()

    if source_stats:
        # Best for phone
        best_phone = max(source_stats.items(), key=lambda x: x[1]['phone']/x[1]['total'] if x[1]['total'] > 0 else 0)
        print(f"Best for PHONE:   {best_phone[0]} ({best_phone[1]['phone']}/{best_phone[1]['total']} = {best_phone[1]['phone']/best_phone[1]['total']*100:.0f}%)")

        # Best for website
        best_website = max(source_stats.items(), key=lambda x: x[1]['website']/x[1]['total'] if x[1]['total'] > 0 else 0)
        print(f"Best for WEBSITE: {best_website[0]} ({best_website[1]['website']}/{best_website[1]['total']} = {best_website[1]['website']/best_website[1]['total']*100:.0f}%)")

        # Best for address
        best_address = max(source_stats.items(), key=lambda x: x[1]['address']/x[1]['total'] if x[1]['total'] > 0 else 0)
        print(f"Best for ADDRESS: {best_address[0]} ({best_address[1]['address']}/{best_address[1]['total']} = {best_address[1]['address']/best_address[1]['total']*100:.0f}%)")

    print()
    print("=" * 80)


if __name__ == '__main__':
    analyze_contact_quality()
