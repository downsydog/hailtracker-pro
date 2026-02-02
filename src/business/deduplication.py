"""
Business Deduplication Engine
=============================
Properly deduplicates businesses from multiple API sources.

Matching criteria (in priority order):
1. Same phone number (normalized to last 10 digits)
2. Coordinates within 50 meters AND similar name (>70%)
3. Same normalized address AND similar name (>80%)
4. Fuzzy name match (>90%) in same city

This handles the reality that different APIs format data differently:
- Yelp: "Firestone Complete Auto Care" at "2250 NW 23rd St, Oklahoma City, OK"
- Google: "Firestone Complete Auto Care" at "2250 NW 23rd St"
- HERE: "Firestone" at "2250 NW 23rd Street, Oklahoma City, OK 73107"
- Foursquare: "Firestone Complete Auto Care" at "2250 Northwest 23rd Street"

All of these are the SAME business.
"""

import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from math import radians, cos, sin, sqrt, atan2
from difflib import SequenceMatcher

logger = logging.getLogger('Deduplication')


def normalize_phone(phone: str) -> str:
    """
    Normalize phone to last 10 digits.

    Examples:
        "+1 (405) 445-4977" -> "4054454977"
        "405-445-4977" -> "4054454977"
        "14054454977" -> "4054454977"
    """
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) >= 10:
        return digits[-10:]
    return ""


def normalize_name(name: str) -> str:
    """
    Normalize business name for comparison.

    Removes:
    - Common suffixes (LLC, Inc, Corp, etc.)
    - Punctuation
    - Extra whitespace

    Examples:
        "Firestone Complete Auto Care, LLC" -> "firestone complete auto care"
        "O'Reilly Auto Parts" -> "oreilly auto parts"
    """
    if not name:
        return ""

    name = name.lower().strip()

    # Remove common business suffixes
    suffixes = [
        r'\s*,?\s*llc\.?$', r'\s*,?\s*inc\.?$', r'\s*,?\s*corp\.?$',
        r'\s*,?\s*ltd\.?$', r'\s*,?\s*co\.?$', r'\s*,?\s*company$',
        r'\s*,?\s*corporation$', r'\s*,?\s*incorporated$',
        r'\s*,?\s*limited$', r'\s*,?\s*services?$',
    ]
    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)

    # Remove punctuation except spaces
    name = re.sub(r'[^\w\s]', '', name)

    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def normalize_address(address: str) -> str:
    """
    Normalize address for comparison.

    Standardizes:
    - Street type abbreviations (Street -> St, Avenue -> Ave, etc.)
    - Direction abbreviations (Northwest -> NW, etc.)
    - Removes suite/unit numbers
    - Removes city/state/zip suffixes

    Examples:
        "2250 Northwest 23rd Street, Oklahoma City, OK" -> "2250 nw 23rd st"
        "2250 NW 23rd St" -> "2250 nw 23rd st"
    """
    if not address:
        return ""

    addr = address.lower().strip()

    # Remove everything after first comma (city, state, zip)
    addr = addr.split(',')[0]

    # Standardize directions
    addr = re.sub(r'\bnorthwest\b', 'nw', addr)
    addr = re.sub(r'\bnortheast\b', 'ne', addr)
    addr = re.sub(r'\bsouthwest\b', 'sw', addr)
    addr = re.sub(r'\bsoutheast\b', 'se', addr)
    addr = re.sub(r'\bnorth\b', 'n', addr)
    addr = re.sub(r'\bsouth\b', 's', addr)
    addr = re.sub(r'\beast\b', 'e', addr)
    addr = re.sub(r'\bwest\b', 'w', addr)

    # Standardize street types
    addr = re.sub(r'\bstreet\b', 'st', addr)
    addr = re.sub(r'\bavenue\b', 'ave', addr)
    addr = re.sub(r'\bboulevard\b', 'blvd', addr)
    addr = re.sub(r'\bdrive\b', 'dr', addr)
    addr = re.sub(r'\broad\b', 'rd', addr)
    addr = re.sub(r'\blane\b', 'ln', addr)
    addr = re.sub(r'\bcourt\b', 'ct', addr)
    addr = re.sub(r'\bplace\b', 'pl', addr)
    addr = re.sub(r'\bparkway\b', 'pkwy', addr)
    addr = re.sub(r'\bhighway\b', 'hwy', addr)

    # Remove suite/unit numbers
    addr = re.sub(r'\bsuite\s*[#]?\s*\w+', '', addr)
    addr = re.sub(r'\bste\s*[#]?\s*\w+', '', addr)
    addr = re.sub(r'\bunit\s*[#]?\s*\w+', '', addr)
    addr = re.sub(r'\b#\s*\w+', '', addr)

    # Remove punctuation
    addr = re.sub(r'[^\w\s]', '', addr)

    # Collapse whitespace
    addr = re.sub(r'\s+', ' ', addr).strip()

    return addr


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters."""
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')

    R = 6371000  # Earth radius in meters
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))


def name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity ratio between two names (0.0 to 1.0)."""
    if not name1 or not name2:
        return 0.0
    return SequenceMatcher(None, name1, name2).ratio()


def is_duplicate(biz1: Dict, biz2: Dict,
                 phone_match: bool = True,
                 coord_threshold_m: float = 50,
                 name_threshold_coords: float = 0.70,
                 name_threshold_address: float = 0.80,
                 name_threshold_only: float = 0.90) -> Tuple[bool, str]:
    """
    Check if two businesses are duplicates.

    Args:
        biz1, biz2: Business dictionaries
        phone_match: Whether to check phone numbers
        coord_threshold_m: Max distance in meters to be considered same location
        name_threshold_coords: Min name similarity when coordinates match
        name_threshold_address: Min name similarity when addresses match
        name_threshold_only: Min name similarity for name-only matching

    Returns:
        Tuple of (is_duplicate, reason)
    """
    # 1. Phone number match (highest confidence)
    if phone_match:
        phone1 = normalize_phone(biz1.get('phone', ''))
        phone2 = normalize_phone(biz2.get('phone', ''))
        if phone1 and phone2 and phone1 == phone2:
            return True, "phone_match"

    # Get normalized values
    name1 = normalize_name(biz1.get('name', ''))
    name2 = normalize_name(biz2.get('name', ''))

    if not name1 or not name2:
        return False, ""

    # 2. Coordinate proximity + similar name
    lat1, lon1 = biz1.get('latitude'), biz1.get('longitude')
    lat2, lon2 = biz2.get('latitude'), biz2.get('longitude')

    if all([lat1, lon1, lat2, lon2]):
        distance = haversine_meters(lat1, lon1, lat2, lon2)
        if distance < coord_threshold_m:
            similarity = name_similarity(name1, name2)
            if similarity >= name_threshold_coords:
                return True, f"coords_{int(distance)}m_name_{similarity:.0%}"

    # 3. Same normalized address + similar name
    addr1 = normalize_address(biz1.get('address', ''))
    addr2 = normalize_address(biz2.get('address', ''))

    if addr1 and addr2 and addr1 == addr2:
        similarity = name_similarity(name1, name2)
        if similarity >= name_threshold_address:
            return True, f"address_name_{similarity:.0%}"

    # 4. Very similar name in same city (careful - may cause false positives)
    city1 = (biz1.get('city', '') or '').lower().strip()
    city2 = (biz2.get('city', '') or '').lower().strip()

    if city1 and city2 and city1 == city2:
        similarity = name_similarity(name1, name2)
        if similarity >= name_threshold_only:
            return True, f"name_{similarity:.0%}_same_city"

    return False, ""


def deduplicate_businesses(businesses: List[Dict],
                          merge_data: bool = True,
                          progress_callback=None) -> List[Dict]:
    """
    Deduplicate a list of businesses from multiple sources.

    Args:
        businesses: List of business dictionaries
        merge_data: If True, merge contact info from duplicates into keeper
        progress_callback: Optional callback(processed, total, duplicates)

    Returns:
        Deduplicated list of businesses
    """
    if not businesses:
        return []

    logger.info(f"Deduplicating {len(businesses)} businesses...")

    # Build index by phone for O(1) phone lookups
    phone_index: Dict[str, int] = {}  # phone -> index in unique list

    # Build spatial index for coordinate lookups (simple grid)
    # Grid cells are ~100m x ~100m
    coord_index: Dict[Tuple[int, int], List[int]] = {}  # (grid_x, grid_y) -> [indices]

    def get_grid_cell(lat: float, lon: float) -> Tuple[int, int]:
        """Get grid cell for coordinates (~100m resolution)."""
        if not lat or not lon:
            return (999999, 999999)
        # ~100m per grid cell at mid-latitudes
        return (int(lat * 1000), int(lon * 1000))

    def get_nearby_cells(lat: float, lon: float) -> List[Tuple[int, int]]:
        """Get this cell and 8 neighbors."""
        x, y = get_grid_cell(lat, lon)
        cells = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                cells.append((x + dx, y + dy))
        return cells

    unique: List[Dict] = []
    duplicates_found = 0

    for i, biz in enumerate(businesses):
        if progress_callback and i % 100 == 0:
            progress_callback(i, len(businesses), duplicates_found)

        is_dupe = False
        keeper_idx = None
        match_reason = ""

        # 1. Quick phone lookup
        phone = normalize_phone(biz.get('phone', ''))
        if phone and phone in phone_index:
            keeper_idx = phone_index[phone]
            is_dupe = True
            match_reason = "phone_match"

        # 2. Check nearby coordinates
        if not is_dupe:
            lat, lon = biz.get('latitude'), biz.get('longitude')
            if lat and lon:
                for cell in get_nearby_cells(lat, lon):
                    if cell in coord_index:
                        for idx in coord_index[cell]:
                            is_dup, reason = is_duplicate(biz, unique[idx], phone_match=False)
                            if is_dup:
                                keeper_idx = idx
                                is_dupe = True
                                match_reason = reason
                                break
                    if is_dupe:
                        break

        if is_dupe and keeper_idx is not None:
            duplicates_found += 1

            if merge_data:
                # Merge contact info into keeper
                keeper = unique[keeper_idx]

                # Prefer non-empty values
                if not keeper.get('phone') and biz.get('phone'):
                    keeper['phone'] = biz['phone']
                if not keeper.get('email') and biz.get('email'):
                    keeper['email'] = biz['email']
                if not keeper.get('website') and biz.get('website'):
                    keeper['website'] = biz['website']

                # Prefer longer/more complete address
                if len(str(biz.get('address', ''))) > len(str(keeper.get('address', ''))):
                    keeper['address'] = biz['address']
                    keeper['city'] = biz.get('city') or keeper.get('city')
                    keeper['state'] = biz.get('state') or keeper.get('state')
                    keeper['zip'] = biz.get('zip') or keeper.get('zip')

                # Track which sources found this business
                sources = keeper.get('_sources', [keeper.get('source', 'unknown')])
                sources.append(biz.get('source', 'unknown'))
                keeper['_sources'] = list(set(sources))
                keeper['_match_reasons'] = keeper.get('_match_reasons', []) + [match_reason]
        else:
            # New unique business
            new_idx = len(unique)
            unique.append(biz.copy())

            # Add to phone index
            if phone:
                phone_index[phone] = new_idx

            # Add to spatial index
            lat, lon = biz.get('latitude'), biz.get('longitude')
            if lat and lon:
                cell = get_grid_cell(lat, lon)
                if cell not in coord_index:
                    coord_index[cell] = []
                coord_index[cell].append(new_idx)

    logger.info(f"Deduplication complete: {len(businesses)} -> {len(unique)} ({duplicates_found} duplicates removed)")

    return unique


def analyze_duplicates(businesses: List[Dict]) -> Dict:
    """
    Analyze a list of businesses for potential duplicates.

    Returns statistics about duplicate detection.
    """
    total = len(businesses)

    # Count by phone
    phones = {}
    for biz in businesses:
        phone = normalize_phone(biz.get('phone', ''))
        if phone:
            phones[phone] = phones.get(phone, 0) + 1

    phone_dupes = sum(count - 1 for count in phones.values() if count > 1)

    # Count exact name matches
    names = {}
    for biz in businesses:
        name = normalize_name(biz.get('name', ''))
        if name:
            names[name] = names.get(name, 0) + 1

    name_dupes = sum(count - 1 for count in names.values() if count > 1)

    # Count exact address matches
    addresses = {}
    for biz in businesses:
        addr = normalize_address(biz.get('address', ''))
        if addr:
            addresses[addr] = addresses.get(addr, 0) + 1

    addr_dupes = sum(count - 1 for count in addresses.values() if count > 1)

    return {
        'total': total,
        'unique_phones': len(phones),
        'phone_duplicates': phone_dupes,
        'unique_names': len(names),
        'name_duplicates': name_dupes,
        'unique_addresses': len(addresses),
        'address_duplicates': addr_dupes,
        'estimated_unique': total - max(phone_dupes, name_dupes),
    }


# Convenience function for testing
def test_deduplication():
    """Test deduplication with sample data."""
    # Simulated results from different APIs for same businesses
    sample = [
        # Same Firestone from 3 APIs
        {'name': 'Firestone Complete Auto Care', 'address': '2250 Northwest 23rd Street',
         'phone': '(405) 445-4977', 'latitude': 35.4875, 'longitude': -97.5589, 'source': 'foursquare'},
        {'name': 'Firestone Complete Auto Care', 'address': '2250 NW 23rd St, Oklahoma City',
         'phone': '', 'latitude': 35.4874, 'longitude': -97.5590, 'source': 'google'},
        {'name': 'Firestone', 'address': '2250 NW 23rd St, Oklahoma City, OK 73107',
         'phone': '+1 405-445-4977', 'latitude': 35.4875, 'longitude': -97.5589, 'source': 'here'},

        # Same AutoZone from 2 APIs
        {'name': 'AutoZone Auto Parts', 'address': '123 Main St, Oklahoma City, OK',
         'phone': '405-555-1234', 'latitude': 35.4700, 'longitude': -97.5200, 'source': 'yelp'},
        {'name': 'AutoZone', 'address': '123 Main Street',
         'phone': '4055551234', 'latitude': 35.4700, 'longitude': -97.5201, 'source': 'google'},

        # Different business
        {'name': "O'Reilly Auto Parts", 'address': '456 Oak Ave, Oklahoma City, OK',
         'phone': '405-555-5678', 'latitude': 35.4800, 'longitude': -97.5300, 'source': 'yelp'},
    ]

    print("Before deduplication:")
    for biz in sample:
        print(f"  [{biz['source']:10}] {biz['name']:30} | {biz.get('phone', 'N/A'):15}")

    print(f"\nTotal: {len(sample)}")

    deduped = deduplicate_businesses(sample)

    print(f"\nAfter deduplication: {len(deduped)}")
    for biz in deduped:
        sources = biz.get('_sources', [biz.get('source')])
        print(f"  {biz['name']:30} | Phone: {biz.get('phone', 'N/A'):15} | Sources: {sources}")

    return deduped


if __name__ == '__main__':
    test_deduplication()
