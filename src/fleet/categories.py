"""
Fleet Categories - 25 High-Value PDR Prospect Types
===================================================

Organized by tier:
- Tier 1: Highest value (big fleets, always pay)
- Tier 2: High value (solid fleet sizes)
- Tier 3: Good opportunities (smaller but worthwhile)
"""

FLEET_CATEGORIES = {
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
        'keywords': ['auto', 'motors', 'dealership', 'toyota', 'ford', 'honda',
                     'chevrolet', 'nissan', 'bmw', 'mercedes', 'hyundai', 'kia'],
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
        'keywords': ['enterprise', 'hertz', 'avis', 'budget', 'national', 'alamo',
                     'dollar', 'thrifty', 'sixt'],
    },
    'auto_auction': {
        'name': 'Auto Auctions',
        'tier': 1,
        'icon': '🏷️',
        'color': '#9C27B0',
        'est_vehicles': 500,
        'osm_tags': [],  # Rare in OSM, find via name search
        'keywords': ['copart', 'iaai', 'manheim', 'adesa', 'auction', 'auto auction'],
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
        'keywords': ['city of', 'municipal', 'city hall', 'police', 'fire department'],
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
        'keywords': ['electric', 'power', 'energy', 'gas', 'water', 'oncor',
                     'atmos', 'att', 'verizon', 'spectrum'],
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
        'keywords': ['fedex', 'ups', 'amazon', 'dhl', 'usps', 'logistics', 'freight'],
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
        'yelp_category': 'homehealthcare',
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
        ],
        'keywords': ['hvac', 'plumbing', 'plumber', 'electric', 'roofing', 'contractor'],
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
        'keywords': ['golf', 'country club'],
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
    },
}


def get_category_by_tier(tier: int) -> dict:
    """Get all categories for a specific tier."""
    return {k: v for k, v in FLEET_CATEGORIES.items() if v.get('tier') == tier}


def get_osm_tags_for_category(category: str) -> list:
    """Get OSM tags for a category."""
    cat = FLEET_CATEGORIES.get(category, {})
    return cat.get('osm_tags', [])


def get_all_osm_tags() -> list:
    """Get all unique OSM tags across all categories."""
    all_tags = []
    for cat in FLEET_CATEGORIES.values():
        all_tags.extend(cat.get('osm_tags', []))
    return all_tags


def estimate_vehicles_by_category(category: str, name: str = '', review_count: int = 0) -> int:
    """Estimate vehicle count based on category and business size indicators."""
    cat = FLEET_CATEGORIES.get(category, {})
    base = cat.get('est_vehicles', 10)

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
    large_chains = ['enterprise', 'hertz', 'sysco', 'fedex', 'ups', 'amazon',
                    'oncor', 'att', 'verizon', 'united rentals', 'sunbelt']
    if any(chain in name_lower for chain in large_chains):
        multiplier *= 1.5

    return int(base * multiplier)

# Compatibility shim (older code expects this here)
from src.business.category_taxonomy import normalize_category_key as normalize_category_key
