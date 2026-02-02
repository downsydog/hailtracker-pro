"""
Category Taxonomy (canonical categories + helpers)

Purpose:
- Provide canonical category keys and aliases (legacy -> canonical)
- Provide tier assignment (tier 1/2/3)
- Provide helper functions for normalization and detection
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# ---------------------------------------------------------------------
# Canonical category definitions
# ---------------------------------------------------------------------

# Each category:
# - key: canonical slug
# - display: human name
# - tier: 1/2/3 (highest value targets = 1)
# - min_vehicles: default heuristic for estimated fleet size
# - tags: optional keywords useful for matching
CATEGORIES: Dict[str, dict] = {
    # Tier 1 (highest value)
    "car_dealership": {
        "display": "Car Dealership",
        "tier": 1,
        "min_vehicles": 150,
        "tags": ["dealership", "auto dealer", "car dealer"],
    },
    "car_rental": {
        "display": "Car Rental",
        "tier": 1,
        "min_vehicles": 80,
        "tags": ["rental", "rent a car"],
    },
    "parking_structure": {
        "display": "Parking Structure",
        "tier": 1,
        "min_vehicles": 300,
        "tags": ["parking garage", "garage", "parking structure"],
    },
    "municipal_fleet": {
        "display": "Municipal Fleet",
        "tier": 1,
        "min_vehicles": 80,
        "tags": ["city", "police", "fire", "public works", "municipal"],
    },
    "utility_company": {
        "display": "Utility Company",
        "tier": 1,
        "min_vehicles": 60,
        "tags": ["utility", "electric", "water", "gas"],
    },

    # Tier 2 (strong)
    "body_shop": {
        "display": "Body Shop",
        "tier": 2,
        "min_vehicles": 25,
        "tags": ["collision", "auto body", "body shop"],
    },
    "school_university": {
        "display": "School / University",
        "tier": 2,
        "min_vehicles": 60,
        "tags": ["school", "university", "college", "district"],
    },
    "hospital": {
        "display": "Hospital",
        "tier": 2,
        "min_vehicles": 70,
        "tags": ["hospital", "medical center"],
    },
    "event_venue": {
        "display": "Event Venue",
        "tier": 2,
        "min_vehicles": 120,
        "tags": ["arena", "stadium", "event venue"],
    },
    "large_apartment": {
        "display": "Large Apartments",
        "tier": 2,
        "min_vehicles": 200,
        "tags": ["apartments", "apartment complex"],
    },

    # Tier 3 (broad service trades + others)
    "service_trades": {
        "display": "Service Trades",
        "tier": 3,
        "min_vehicles": 12,
        "tags": ["hvac", "plumbing", "electrician", "contractor", "landscaping", "roofing"],
    },
    "delivery_logistics": {
        "display": "Delivery / Logistics",
        "tier": 3,
        "min_vehicles": 40,
        "tags": ["warehouse", "logistics", "delivery", "courier", "distribution"],
    },
    "property_management": {
        "display": "Property Management",
        "tier": 3,
        "min_vehicles": 15,
        "tags": ["property management", "janitorial"],
    },
    "insurance_office": {
        "display": "Insurance Office",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["insurance"],
    },
    "golf_course": {
        "display": "Golf Course",
        "tier": 3,
        "min_vehicles": 40,
        "tags": ["golf", "country club"],
    },
}

# ---------------------------------------------------------------------
# Legacy -> canonical aliases
# ---------------------------------------------------------------------
ALIASES: Dict[str, str] = {
    # Examples you showed earlier
    "rental_car": "car_rental",
    "service_company": "service_trades",
    "parking": "parking_structure",

    # Common variations
    "dealer": "car_dealership",
    "dealerships": "car_dealership",
    "rentals": "car_rental",
    "municipal": "municipal_fleet",
    "utilities": "utility_company",
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def normalize_category_key(key: str) -> str:
    if not key:
        return ""
    k = key.strip().lower().replace(" ", "_")
    return ALIASES.get(k, k)


def get_categories_by_tier(tier: int) -> List[dict]:
    return [
        {"key": k, **v}
        for k, v in CATEGORIES.items()
        if int(v.get("tier", 3)) == int(tier)
    ]


def estimate_vehicles(category_key: str) -> int:
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return 0
    return int(cat.get("min_vehicles", 0))


def detect_category_from_tags(tags: List[str]) -> Optional[str]:
    if not tags:
        return None
    tagset = {t.strip().lower() for t in tags if t and t.strip()}
    for key, meta in CATEGORIES.items():
        for t in meta.get("tags", []):
            if t.lower() in tagset:
                return key
    return None
