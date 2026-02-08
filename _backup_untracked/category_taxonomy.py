"""
Category Taxonomy - Single Source of Truth for Fleet/Business Categories
=========================================================================

This module defines ALL categories used across:
- Fleet discovery engines (SwathDiscovery, FastSwathDiscovery, TileBasedDiscovery)
- Fleet locations and prospecting
- OSM/Overpass queries
- UI dropdowns and reports

CANONICAL KEYS (use these everywhere):
- car_rental (NOT rental_car)
- service_trades (NOT service_company)
- parking_structure (for multi-level parking)
- body_shop (for collision/auto body)

Use normalize_category_key() to convert legacy keys to canonical keys.
"""

from typing import Dict, List, Optional, Any, Iterator, Tuple


# =============================================================================
# KEY ALIASES - Maps legacy/alternate keys to canonical keys
# =============================================================================
CATEGORY_ALIASES = {
    # Legacy keys from fleet_locations.py CATEGORY_QUERIES
    'rental_car': 'car_rental',
    'service_company': 'service_trades',
    'parking': 'parking_structure',

    # Alternate spellings
    'auto_body': 'body_shop',
    'collision': 'body_shop',
    'car_repair': 'body_shop',

    # Government variations
    'government': 'municipal',
    'city_government': 'municipal',
    'police': 'municipal',
    'fire_station': 'municipal',

    # School variations
    'school': 'school_district',
    'university': 'school_district',
    'college': 'school_district',

    # Rental variations
    'rental_car_company': 'car_rental',

    # Other
    'parking_garage': 'parking_structure',
    'parking_lot': 'parking_structure',
}


# =============================================================================
# CANONICAL CATEGORY TAXONOMY
# =============================================================================
CATEGORY_TAXONOMY = {
    # =========================================================================
    # TIER 1 - HIGHEST VALUE (Big fleets, always pay)
    # =========================================================================
    'car_dealership': {
        'name': 'Car Dealerships',
        'tier': 1,
        'icon': '🚗',
        'color': '#4CAF50',
        'est_vehicles': 150,
        'osm_tags': [
            {'shop': 'car'},
            {'shop': 'car_parts'},
            {'shop': 'motorcycle'},
        ],
        'keywords': [
            'chevrolet', 'ford', 'toyota', 'honda', 'nissan', 'hyundai', 'kia',
            'bmw', 'mercedes', 'audi', 'lexus', 'infiniti', 'acura', 'volvo',
            'volkswagen', 'subaru', 'mazda', 'mitsubishi', 'chrysler', 'dodge',
            'jeep', 'ram', 'gmc', 'buick', 'cadillac', 'lincoln', 'tesla',
            'porsche', 'jaguar', 'land rover', 'maserati', 'alfa romeo',
            'auto', 'motors', 'dealership', 'cars', 'automotive'
        ],
        'subcategories': {
            'luxury': ['bmw', 'mercedes', 'audi', 'lexus', 'porsche', 'jaguar', 'tesla', 'maserati'],
            'truck': ['ford', 'chevrolet', 'gmc', 'ram', 'toyota tundra']
        },
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
    },

    'car_rental': {
        'name': 'Car Rental',
        'tier': 1,
        'icon': '🔑',
        'color': '#2196F3',
        'est_vehicles': 80,
        'osm_tags': [
            {'amenity': 'car_rental'},
        ],
        'keywords': [
            'enterprise', 'hertz', 'avis', 'budget', 'national', 'alamo',
            'dollar', 'thrifty', 'sixt', 'europcar', 'rent-a-car', 'rental'
        ],
        'airport_multiplier': 2.5,
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'carrental',
    },

    'auto_auction': {
        'name': 'Auto Auctions',
        'tier': 1,
        'icon': '🏷️',
        'color': '#9C27B0',
        'est_vehicles': 500,
        'osm_tags': [],  # Rare in OSM, find via name search
        'keywords': ['copart', 'iaai', 'manheim', 'adesa', 'auction', 'auto auction'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'autosauctions',
    },

    'municipal': {
        'name': 'City/Municipal',
        'tier': 1,
        'icon': '🏛️',
        'color': '#F44336',
        'est_vehicles': 75,
        'osm_tags': [
            {'amenity': 'townhall'},
            {'amenity': 'police'},
            {'amenity': 'fire_station'},
            {'office': 'government'},
        ],
        'keywords': [
            'city of', 'municipal', 'city hall', 'police', 'fire department',
            'civic', 'government', 'sheriff', 'public works', 'parks'
        ],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    'county_government': {
        'name': 'County Government',
        'tier': 1,
        'icon': '🏢',
        'color': '#E91E63',
        'est_vehicles': 100,
        'osm_tags': [
            {'office': 'government'},
            {'amenity': 'courthouse'},
        ],
        'keywords': ['county', 'sheriff', 'courthouse', 'assessor', 'public works'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    'school_district': {
        'name': 'Schools & Districts',
        'tier': 1,
        'icon': '🏫',
        'color': '#673AB7',
        'est_vehicles': 100,
        'osm_tags': [
            {'amenity': 'school'},
            {'amenity': 'university'},
            {'amenity': 'college'},
        ],
        'keywords': ['school', 'isd', 'independent school', 'university', 'college'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    'hospital': {
        'name': 'Hospitals & Medical',
        'tier': 1,
        'icon': '🏥',
        'color': '#E91E63',
        'est_vehicles': 200,
        'osm_tags': [
            {'amenity': 'hospital'},
            {'healthcare': 'hospital'},
        ],
        'keywords': ['hospital', 'medical center', 'health system'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    'transit': {
        'name': 'Transit/Bus Depots',
        'tier': 1,
        'icon': '🚌',
        'color': '#3F51B5',
        'est_vehicles': 150,
        'osm_tags': [
            {'amenity': 'bus_station'},
            {'public_transport': 'station'},
        ],
        'keywords': ['transit', 'bus', 'metro', 'dart', 'via', 'transportation'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    # =========================================================================
    # TIER 2 - HIGH VALUE (Solid fleet sizes)
    # =========================================================================
    'utility': {
        'name': 'Utility Companies',
        'tier': 2,
        'icon': '⚡',
        'color': '#FFEB3B',
        'est_vehicles': 100,
        'osm_tags': [
            {'power': 'plant'},
            {'power': 'substation'},
            {'office': 'telecommunication'},
            {'telecom': 'exchange'},
        ],
        'keywords': [
            'electric', 'power', 'energy', 'gas', 'water', 'sewer',
            'utility', 'at&t', 'verizon', 't-mobile', 'sprint', 'cox',
            'comcast', 'spectrum', 'centurylink', 'oncor', 'txu', 'atmos'
        ],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    'landscaping': {
        'name': 'Landscaping/Lawn Care',
        'tier': 2,
        'icon': '🌳',
        'color': '#8BC34A',
        'est_vehicles': 15,
        'osm_tags': [
            {'shop': 'garden_centre'},
            {'landuse': 'plant_nursery'},
        ],
        'keywords': ['landscaping', 'lawn', 'tree service', 'irrigation', 'nursery'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'landscaping',
        'fmcsa': True,
    },

    'pest_control': {
        'name': 'Pest Control',
        'tier': 2,
        'icon': '🐜',
        'color': '#795548',
        'est_vehicles': 20,
        'osm_tags': [],  # Rarely in OSM, use Yelp
        'keywords': ['pest', 'exterminator', 'terminix', 'orkin'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'pest_control',
    },

    'food_distribution': {
        'name': 'Food/Beverage Distribution',
        'tier': 2,
        'icon': '🍔',
        'color': '#FF9800',
        'est_vehicles': 100,
        'osm_tags': [
            {'building': 'warehouse'},
        ],
        'keywords': ['sysco', 'us foods', 'coca-cola', 'pepsi', 'budweiser', 'distributor'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'fmcsa': True,
    },

    'delivery': {
        'name': 'Delivery/Logistics',
        'tier': 2,
        'icon': '📦',
        'color': '#607D8B',
        'est_vehicles': 150,
        'osm_tags': [
            {'amenity': 'post_office'},
            {'office': 'logistics'},
            {'building': 'warehouse'},
        ],
        'keywords': [
            'fedex', 'ups', 'amazon', 'dhl', 'usps', 'logistics', 'freight',
            'warehouse', 'distribution', 'shipping'
        ],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'fmcsa': True,
    },

    'moving': {
        'name': 'Moving Companies',
        'tier': 2,
        'icon': '🚚',
        'color': '#00BCD4',
        'est_vehicles': 25,
        'osm_tags': [],  # Use Yelp/FMCSA
        'keywords': ['moving', 'movers', 'u-haul', 'penske', 'two men'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'movers',
        'fmcsa': True,
    },

    'equipment_rental': {
        'name': 'Equipment Rental',
        'tier': 2,
        'icon': '🔨',
        'color': '#FF5722',
        'est_vehicles': 40,
        'osm_tags': [
            {'shop': 'tool_hire'},
        ],
        'keywords': ['united rentals', 'sunbelt', 'rental', 'equipment'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'equipmentrental',
    },

    'security': {
        'name': 'Security Companies',
        'tier': 2,
        'icon': '🔒',
        'color': '#212121',
        'est_vehicles': 30,
        'osm_tags': [
            {'office': 'security'},
        ],
        'keywords': ['security', 'adt', 'brinks', 'securitas', 'patrol'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'securityservices',
    },

    'home_health': {
        'name': 'Home Health Services',
        'tier': 2,
        'icon': '🩺',
        'color': '#009688',
        'est_vehicles': 25,
        'osm_tags': [],
        'keywords': ['home health', 'hospice', 'medical transport', 'ambulance'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
        'yelp_category': 'homehealthcare',
    },

    'body_shop': {
        'name': 'Auto Body/Collision',
        'tier': 2,
        'icon': '🔧',
        'color': '#FF5722',
        'est_vehicles': 25,
        'osm_tags': [
            {'shop': 'car_repair'},
            {'craft': 'car_body'},
            {'amenity': 'vehicle_inspection'},
            {'shop': 'tyres'},
        ],
        'keywords': [
            'body shop', 'collision', 'auto body', 'paint', 'dent',
            'repair', 'automotive', 'service center', 'mechanic', 'tire'
        ],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
    },

    # =========================================================================
    # TIER 3 - GOOD OPPORTUNITIES (Smaller but worthwhile)
    # =========================================================================
    'service_trades': {
        'name': 'Service Trades (HVAC/Plumbing)',
        'tier': 3,
        'icon': '🔧',
        'color': '#FF9800',
        'est_vehicles': 15,
        'osm_tags': [
            {'craft': 'hvac'},
            {'craft': 'plumber'},
            {'craft': 'electrician'},
            {'craft': 'roofer'},
            {'craft': 'painter'},
            {'craft': 'carpenter'},
            {'craft': 'floorer'},
            {'craft': 'gardener'},
            {'craft': 'locksmith'},
            {'craft': 'window_construction'},
            {'craft': 'insulation'},
            {'craft': 'plasterer'},
            {'craft': 'tiler'},
            {'craft': 'stonemason'},
            {'craft': 'bricklayer'},
            {'office': 'company'},
            {'office': 'contractor'},
            {'office': 'construction_company'},
            {'shop': 'trade'},
        ],
        'keywords': [
            'hvac', 'heating', 'cooling', 'air conditioning', 'furnace',
            'plumbing', 'plumber', 'electrician', 'electrical',
            'landscap', 'lawn care', 'lawn service', 'lawn maintenance',
            'tree service', 'tree trimming', 'tree removal', 'irrigation', 'sprinkler',
            'roofing', 'roofer', 'siding', 'gutter', 'fence', 'fencing',
            'pest control', 'exterminator', 'pool service', 'pool cleaning',
            'garage door', 'locksmith', 'painting', 'painter', 'flooring',
            'carpet cleaning', 'concrete', 'paving', 'asphalt',
            'pressure washing', 'power washing', 'window cleaning',
            'restoration', 'water damage', 'fire damage', 'mold',
            'septic', 'portable toilet', 'porta potty',
            'contractor', 'construction', 'excavation', 'grading',
            'surveying', 'surveyor', 'well drilling', 'crane',
            'beverage', 'distributor', 'linen service', 'uniform',
            'vending', 'propane', 'delivery',
            'property management', 'janitorial', 'janitor', 'commercial cleaning',
            'sign company', 'sign shop', 'courier', 'freight',
            'home health', 'medical transport', 'hospice',
            'cable', 'satellite', 'security system', 'alarm',
            'waste', 'garbage', 'recycling', 'dumpster', 'junk removal',
        ],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'hvac,plumbing,electricians,roofing',
    },

    'towing': {
        'name': 'Towing Companies',
        'tier': 3,
        'icon': '🚛',
        'color': '#FFC107',
        'est_vehicles': 15,
        'osm_tags': [],
        'keywords': ['towing', 'tow', 'wrecker'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'yelp_category': 'towing',
    },

    'church': {
        'name': 'Churches (Large)',
        'tier': 3,
        'icon': '⛪',
        'color': '#9E9E9E',
        'est_vehicles': 20,
        'osm_tags': [
            {'amenity': 'place_of_worship'},
            {'building': 'church'},
        ],
        'keywords': ['church', 'baptist', 'methodist', 'catholic', 'christian'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    'hotel': {
        'name': 'Hotels/Motels',
        'tier': 3,
        'icon': '🏨',
        'color': '#009688',
        'est_vehicles': 60,
        'osm_tags': [
            {'tourism': 'hotel'},
            {'tourism': 'motel'},
            {'building': 'hotel'},
        ],
        'keywords': ['hotel', 'motel', 'marriott', 'hilton', 'hyatt', 'inn'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
    },

    'golf_course': {
        'name': 'Golf Courses',
        'tier': 3,
        'icon': '⛳',
        'color': '#8BC34A',
        'est_vehicles': 100,
        'osm_tags': [
            {'leisure': 'golf_course'},
        ],
        'keywords': ['golf', 'country club', 'links'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
        'luxury_likely': True,
    },

    'funeral': {
        'name': 'Funeral Homes',
        'tier': 3,
        'icon': '🕯️',
        'color': '#424242',
        'est_vehicles': 10,
        'osm_tags': [
            {'amenity': 'funeral_hall'},
        ],
        'keywords': ['funeral', 'mortuary', 'cemetery'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
        'yelp_category': 'funeralservices',
    },

    'nursing_home': {
        'name': 'Senior Living',
        'tier': 3,
        'icon': '👴',
        'color': '#78909C',
        'est_vehicles': 15,
        'osm_tags': [
            {'amenity': 'nursing_home'},
            {'amenity': 'social_facility'},
        ],
        'keywords': ['nursing', 'assisted living', 'senior', 'retirement'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': False,
        'yelp_category': 'assistedliving',
    },

    'car_wash': {
        'name': 'Car Wash',
        'tier': 3,
        'icon': '🧽',
        'color': '#00ACC1',
        'est_vehicles': 10,
        'osm_tags': [
            {'amenity': 'car_wash'},
        ],
        'keywords': ['car wash', 'wash', 'detail', 'auto spa'],
        'include_in_fleet': True,
        'include_in_swath': True,
        'can_canvas_lot': True,
    },

    'parking_structure': {
        'name': 'Parking Structures',
        'tier': 3,
        'icon': '🅿️',
        'color': '#607D8B',
        'est_vehicles': 300,
        'osm_tags': [
            {'amenity': 'parking'},
            {'building': 'parking'},
        ],
        'keywords': ['parking', 'garage', 'structure', 'deck'],
        'include_in_fleet': False,  # Not fleet sales targets
        'include_in_swath': True,   # Good for canvassing
        'can_canvas_lot': True,
        'capacity_field': 'capacity',
        'filter_parking_types': ['multi-storey', 'underground', 'surface'],
    },

    'apartment': {
        'name': 'Apartment Complexes',
        'tier': 3,
        'icon': '🏢',
        'color': '#795548',
        'est_vehicles': 150,
        'osm_tags': [
            {'building': 'apartments'},
        ],
        'keywords': [
            'apartments', 'residence', 'living', 'homes', 'village',
            'complex', 'place', 'manor', 'park', 'gardens', 'terrace'
        ],
        'include_in_fleet': False,  # Not fleet sales targets
        'include_in_swath': True,   # Good for residential canvassing
        'can_canvas_lot': True,
        'min_for_interest': 100,
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_category_key(key: str) -> str:
    """
    Convert any category key (including legacy/alternate) to canonical key.

    Examples:
        normalize_category_key('rental_car') -> 'car_rental'
        normalize_category_key('car_rental') -> 'car_rental'
        normalize_category_key('service_company') -> 'service_trades'
    """
    if key in CATEGORY_TAXONOMY:
        return key
    return CATEGORY_ALIASES.get(key, key)


def get_category(key: str) -> Optional[Dict[str, Any]]:
    """
    Get category config by key (handles aliases).

    Returns None if category not found.
    """
    canonical_key = normalize_category_key(key)
    return CATEGORY_TAXONOMY.get(canonical_key)


def get_category_or_default(key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get category config with a default fallback."""
    result = get_category(key)
    if result is None:
        return default or {
            'name': key.replace('_', ' ').title(),
            'tier': 3,
            'icon': '📍',
            'color': '#9E9E9E',
            'est_vehicles': 10,
            'osm_tags': [],
            'keywords': [],
            'include_in_fleet': True,
            'include_in_swath': True,
        }
    return result


def iter_categories(
    include_in_fleet: Optional[bool] = None,
    include_in_swath: Optional[bool] = None,
    tier: Optional[int] = None,
    can_canvas_lot: Optional[bool] = None,
) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """
    Iterate over categories with optional filters.

    Args:
        include_in_fleet: If True, only return fleet-targetable categories
        include_in_swath: If True, only return swath-discoverable categories
        tier: If set, only return categories of this tier
        can_canvas_lot: If True, only return lot-canvassable categories

    Yields:
        (key, config) tuples
    """
    for key, config in CATEGORY_TAXONOMY.items():
        if include_in_fleet is not None and config.get('include_in_fleet') != include_in_fleet:
            continue
        if include_in_swath is not None and config.get('include_in_swath') != include_in_swath:
            continue
        if tier is not None and config.get('tier') != tier:
            continue
        if can_canvas_lot is not None and config.get('can_canvas_lot') != can_canvas_lot:
            continue
        yield key, config


def get_categories_by_tier(tier: int) -> Dict[str, Dict[str, Any]]:
    """Get all categories for a specific tier."""
    return {k: v for k, v in iter_categories(tier=tier)}


def get_fleet_categories() -> Dict[str, Dict[str, Any]]:
    """Get all categories suitable for fleet prospecting."""
    return {k: v for k, v in iter_categories(include_in_fleet=True)}


def get_swath_categories() -> Dict[str, Dict[str, Any]]:
    """Get all categories suitable for swath discovery."""
    return {k: v for k, v in iter_categories(include_in_swath=True)}


def get_osm_tags_for_category(key: str) -> List[Dict[str, str]]:
    """Get OSM tags for a category."""
    config = get_category(key)
    if config:
        return config.get('osm_tags', [])
    return []


def get_all_osm_tags() -> List[Dict[str, str]]:
    """Get all unique OSM tags across all categories."""
    seen = set()
    all_tags = []
    for _, config in iter_categories():
        for tag in config.get('osm_tags', []):
            tag_key = tuple(sorted(tag.items()))
            if tag_key not in seen:
                seen.add(tag_key)
                all_tags.append(tag)
    return all_tags


def get_keywords_for_category(key: str) -> List[str]:
    """Get keywords for a category."""
    config = get_category(key)
    if config:
        return config.get('keywords', [])
    return []


def estimate_vehicles(
    category: str,
    name: str = '',
    review_count: int = 0,
    is_airport: bool = False,
) -> int:
    """
    Estimate vehicle count based on category and business size indicators.

    Args:
        category: Category key (canonical or alias)
        name: Business name (for chain detection)
        review_count: Number of reviews (proxy for business size)
        is_airport: Whether location is near an airport

    Returns:
        Estimated vehicle count
    """
    config = get_category(category)
    if not config:
        return 10

    base = config.get('est_vehicles', 10)

    # Adjust by review count (proxy for business size)
    if review_count > 200:
        multiplier = 2.0
    elif review_count > 100:
        multiplier = 1.5
    elif review_count > 50:
        multiplier = 1.2
    else:
        multiplier = 1.0

    # Adjust by name keywords (larger chains)
    name_lower = name.lower()
    large_chains = [
        'enterprise', 'hertz', 'sysco', 'fedex', 'ups', 'amazon',
        'oncor', 'att', 'verizon', 'united rentals', 'sunbelt'
    ]
    if any(chain in name_lower for chain in large_chains):
        multiplier *= 1.5

    # Airport multiplier for car rentals
    if is_airport and config.get('airport_multiplier'):
        multiplier *= config['airport_multiplier']

    return int(base * multiplier)


def detect_category_from_tags(tags: Dict[str, str]) -> Optional[str]:
    """
    Detect category from OSM tags.

    Args:
        tags: OSM tags dictionary

    Returns:
        Canonical category key or None
    """
    # Direct tag matches (most specific first)
    amenity = tags.get('amenity')
    shop = tags.get('shop')
    craft = tags.get('craft')
    office = tags.get('office')
    tourism = tags.get('tourism')
    building = tags.get('building')
    leisure = tags.get('leisure')
    healthcare = tags.get('healthcare')

    # Tier 1 matches
    if amenity == 'car_rental':
        return 'car_rental'
    if shop == 'car':
        return 'car_dealership'
    if amenity == 'hospital' or healthcare == 'hospital':
        return 'hospital'
    if amenity in ('police', 'fire_station', 'townhall') or office == 'government':
        return 'municipal'
    if amenity in ('school', 'university', 'college'):
        return 'school_district'
    if amenity == 'courthouse':
        return 'county_government'
    if amenity == 'bus_station':
        return 'transit'

    # Tier 2 matches
    if shop == 'car_repair' or craft == 'car_body':
        return 'body_shop'
    if office == 'logistics' or amenity == 'post_office':
        return 'delivery'
    if office == 'telecommunication' or tags.get('power'):
        return 'utility'
    if shop == 'garden_centre' or tags.get('landuse') == 'plant_nursery':
        return 'landscaping'
    if shop == 'tool_hire':
        return 'equipment_rental'
    if office == 'security':
        return 'security'

    # Tier 3 matches
    if craft in ('hvac', 'plumber', 'electrician', 'roofer', 'painter', 'carpenter'):
        return 'service_trades'
    if tourism in ('hotel', 'motel'):
        return 'hotel'
    if leisure == 'golf_course':
        return 'golf_course'
    if amenity == 'parking' or building == 'parking':
        return 'parking_structure'
    if building == 'apartments':
        return 'apartment'
    if amenity == 'place_of_worship' or building == 'church':
        return 'church'
    if amenity == 'car_wash':
        return 'car_wash'
    if amenity == 'nursing_home':
        return 'nursing_home'
    if amenity == 'funeral_hall':
        return 'funeral'

    return None


def detect_category_from_name(name: str) -> Optional[str]:
    """
    Detect category from business name using keywords.

    Args:
        name: Business name

    Returns:
        Canonical category key or None (returns highest-tier match)
    """
    if not name:
        return None

    name_lower = name.lower()
    matches = []

    for key, config in CATEGORY_TAXONOMY.items():
        for keyword in config.get('keywords', []):
            if keyword.lower() in name_lower:
                matches.append((key, config.get('tier', 3)))
                break

    if matches:
        # Return highest tier (lowest number) match
        matches.sort(key=lambda x: x[1])
        return matches[0][0]

    return None


def get_ui_categories() -> List[Dict[str, Any]]:
    """
    Get categories formatted for UI dropdowns.

    Returns list sorted by tier then name.
    """
    result = []
    for key, config in CATEGORY_TAXONOMY.items():
        if config.get('include_in_fleet', True):
            result.append({
                'key': key,
                'name': config['name'],
                'tier': config.get('tier', 3),
                'icon': config.get('icon', '📍'),
                'color': config.get('color', '#9E9E9E'),
            })

    result.sort(key=lambda x: (x['tier'], x['name']))
    return result


# =============================================================================
# BACKWARDS COMPATIBILITY EXPORTS
# =============================================================================
# These allow existing code to import from this module
FLEET_CATEGORIES = CATEGORY_TAXONOMY  # Alias for existing imports

def get_category_by_tier(tier: int) -> Dict[str, Dict[str, Any]]:
    """Backwards-compatible alias for get_categories_by_tier."""
    return get_categories_by_tier(tier)

def estimate_vehicles_by_category(category: str, name: str = '', review_count: int = 0) -> int:
    """Backwards-compatible alias for estimate_vehicles."""
    return estimate_vehicles(category, name, review_count)
