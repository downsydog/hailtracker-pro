"""
Category Taxonomy - FULL 70+ CATEGORY VERSION

Purpose:
- Provide 70+ specific business categories for fleet scraping
- Each category has its own API search terms for: Yelp, Foursquare, HERE, TomTom, Google Places, OSM
- This granular approach produced 3,539 businesses (1,567 service companies) in OKC test
- DO NOT COLLAPSE THESE INTO BUCKETS - each category searches differently

IMPORTANT: The collapsed 15-category version destroyed scraping effectiveness.
Each specific category (e.g., "hvac", "plumbing", "electrical") must search separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------
# API Search Term Mappings per Category
# Each category has specific search terms for each API
# ---------------------------------------------------------------------

@dataclass
class CategoryDefinition:
    """Full category definition with API mappings"""
    key: str
    display: str
    group: str  # SERVICE_TRADES, DISTRIBUTION, AUTOMOTIVE, etc.
    tier: int   # 1=highest value, 2=strong, 3=standard
    min_vehicles: int
    tags: List[str]
    # API-specific search terms
    yelp_categories: List[str]
    foursquare_categories: List[str]
    here_categories: List[str]
    tomtom_categories: List[str]
    google_types: List[str]
    osm_tags: Dict[str, str]


# ---------------------------------------------------------------------
# SERVICE TRADES (25 categories) - Tier 3
# These are the bread and butter - high volume, consistent fleet sizes
# ---------------------------------------------------------------------

SERVICE_TRADES_CATEGORIES: Dict[str, dict] = {
    "hvac": {
        "display": "HVAC Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["hvac", "heating", "cooling", "air conditioning", "furnace"],
        "yelp_categories": ["hvac"],
        "foursquare_categories": ["heating, ventilating, and air conditioning"],
        "here_categories": ["heating-ventilation-air-conditioning"],
        "tomtom_categories": ["heating, ventilation and air conditioning contractor"],
        "google_types": ["hvac_contractor"],
        "osm_tags": {"craft": "hvac"},
    },
    "plumbing": {
        "display": "Plumbing Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 6,
        "tags": ["plumber", "plumbing", "pipes", "drain"],
        "yelp_categories": ["plumbing"],
        "foursquare_categories": ["plumber"],
        "here_categories": ["plumber"],
        "tomtom_categories": ["plumber"],
        "google_types": ["plumber"],
        "osm_tags": {"craft": "plumber"},
    },
    "electrical": {
        "display": "Electrical Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 6,
        "tags": ["electrician", "electrical", "wiring"],
        "yelp_categories": ["electricians"],
        "foursquare_categories": ["electrician"],
        "here_categories": ["electrician"],
        "tomtom_categories": ["electrician"],
        "google_types": ["electrician"],
        "osm_tags": {"craft": "electrician"},
    },
    "roofing": {
        "display": "Roofing Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["roofer", "roofing", "roof repair"],
        "yelp_categories": ["roofing"],
        "foursquare_categories": ["roofing contractor"],
        "here_categories": ["roofing-contractor"],
        "tomtom_categories": ["roofing contractor"],
        "google_types": ["roofing_contractor"],
        "osm_tags": {"craft": "roofer"},
    },
    "landscaping": {
        "display": "Landscaping Company",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["landscaping", "lawn care", "lawn service", "grounds"],
        "yelp_categories": ["landscaping", "lawn_services"],
        "foursquare_categories": ["landscaper"],
        "here_categories": ["garden-lawn-care-services"],
        "tomtom_categories": ["landscape gardener"],
        "google_types": ["landscaping"],
        "osm_tags": {"landuse": "grass", "service": "landscaping"},
    },
    "pest_control": {
        "display": "Pest Control",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 12,
        "tags": ["pest control", "exterminator", "termite"],
        "yelp_categories": ["pest_control"],
        "foursquare_categories": ["pest control service"],
        "here_categories": ["pest-control"],
        "tomtom_categories": ["pest control"],
        "google_types": ["pest_control"],
        "osm_tags": {"shop": "pest_control"},
    },
    "painting": {
        "display": "Painting Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 5,
        "tags": ["painter", "painting", "house painting"],
        "yelp_categories": ["painters"],
        "foursquare_categories": ["painter"],
        "here_categories": ["painter"],
        "tomtom_categories": ["painter"],
        "google_types": ["painter"],
        "osm_tags": {"craft": "painter"},
    },
    "flooring": {
        "display": "Flooring Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["flooring", "carpet", "tile", "hardwood"],
        "yelp_categories": ["flooring", "carpeting"],
        "foursquare_categories": ["flooring store"],
        "here_categories": ["flooring"],
        "tomtom_categories": ["floor covering store"],
        "google_types": ["flooring_store"],
        "osm_tags": {"shop": "flooring"},
    },
    "appliance_repair": {
        "display": "Appliance Repair",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 6,
        "tags": ["appliance repair", "appliance service"],
        "yelp_categories": ["appliances", "appliancesrepair"],
        "foursquare_categories": ["appliance repair service"],
        "here_categories": ["appliance-repair"],
        "tomtom_categories": ["appliance repair"],
        "google_types": ["appliance_repair_service"],
        "osm_tags": {"shop": "appliance"},
    },
    "garage_door": {
        "display": "Garage Door Services",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["garage door", "overhead door"],
        "yelp_categories": ["garagedoorservices"],
        "foursquare_categories": ["garage door supplier"],
        "here_categories": ["garage-doors"],
        "tomtom_categories": ["garage door service"],
        "google_types": ["garage_door_supplier"],
        "osm_tags": {"shop": "doors"},
    },
    "pool_service": {
        "display": "Pool Service",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["pool service", "pool cleaning", "swimming pool"],
        "yelp_categories": ["poolservice", "poolcleaners"],
        "foursquare_categories": ["swimming pool service"],
        "here_categories": ["swimming-pool-contractor"],
        "tomtom_categories": ["swimming pool maintenance"],
        "google_types": ["swimming_pool_contractor"],
        "osm_tags": {"leisure": "swimming_pool"},
    },
    "window_door": {
        "display": "Window & Door Services",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["window", "door", "glass"],
        "yelp_categories": ["windows_installation", "doors"],
        "foursquare_categories": ["window installation service"],
        "here_categories": ["windows-doors"],
        "tomtom_categories": ["window installation"],
        "google_types": ["window_supplier"],
        "osm_tags": {"shop": "windows"},
    },
    "fence": {
        "display": "Fence Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["fence", "fencing"],
        "yelp_categories": ["fences_gates"],
        "foursquare_categories": ["fence contractor"],
        "here_categories": ["fence-contractor"],
        "tomtom_categories": ["fencing contractor"],
        "google_types": ["fence_contractor"],
        "osm_tags": {"craft": "fence"},
    },
    "tree_service": {
        "display": "Tree Service",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 5,
        "tags": ["tree service", "tree trimming", "arborist"],
        "yelp_categories": ["treeservices"],
        "foursquare_categories": ["tree service"],
        "here_categories": ["tree-service"],
        "tomtom_categories": ["tree surgeon"],
        "google_types": ["tree_service"],
        "osm_tags": {"landuse": "forest"},
    },
    "locksmith": {
        "display": "Locksmith",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["locksmith", "lock", "key"],
        "yelp_categories": ["locksmiths"],
        "foursquare_categories": ["locksmith"],
        "here_categories": ["locksmith"],
        "tomtom_categories": ["locksmith"],
        "google_types": ["locksmith"],
        "osm_tags": {"craft": "locksmith"},
    },
    "glass": {
        "display": "Glass Service",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["glass", "auto glass", "windshield"],
        "yelp_categories": ["glass_mirrors", "autoglass"],
        "foursquare_categories": ["glass service"],
        "here_categories": ["glass-mirror"],
        "tomtom_categories": ["glass and mirror shop"],
        "google_types": ["glass_shop"],
        "osm_tags": {"craft": "glaziery"},
    },
    "cleaning_janitorial": {
        "display": "Cleaning & Janitorial",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 15,
        "tags": ["cleaning", "janitorial", "maid", "housekeeping"],
        "yelp_categories": ["officecleaning", "homecleaning"],
        "foursquare_categories": ["janitorial service"],
        "here_categories": ["cleaning-services"],
        "tomtom_categories": ["cleaning service"],
        "google_types": ["cleaning_service"],
        "osm_tags": {"shop": "cleaning"},
    },
    "carpet_cleaning": {
        "display": "Carpet Cleaning",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 6,
        "tags": ["carpet cleaning", "upholstery cleaning"],
        "yelp_categories": ["carpetcleaning"],
        "foursquare_categories": ["carpet cleaner"],
        "here_categories": ["carpet-cleaning"],
        "tomtom_categories": ["carpet cleaning"],
        "google_types": ["carpet_cleaning_service"],
        "osm_tags": {"shop": "carpet"},
    },
    "irrigation": {
        "display": "Irrigation / Sprinkler",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 5,
        "tags": ["irrigation", "sprinkler", "lawn sprinkler"],
        "yelp_categories": ["irrigation"],
        "foursquare_categories": ["irrigation equipment supplier"],
        "here_categories": ["irrigation-systems"],
        "tomtom_categories": ["irrigation system contractor"],
        "google_types": ["irrigation_equipment_supplier"],
        "osm_tags": {"shop": "irrigation"},
    },
    "security_alarm": {
        "display": "Security & Alarm",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["security", "alarm", "surveillance"],
        "yelp_categories": ["securitysystems"],
        "foursquare_categories": ["security system supplier"],
        "here_categories": ["security-systems"],
        "tomtom_categories": ["security system installer"],
        "google_types": ["security_system_supplier"],
        "osm_tags": {"shop": "security"},
    },
    "water_treatment": {
        "display": "Water Treatment / Softener",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["water treatment", "water softener", "water filter"],
        "yelp_categories": ["waterheaterinstallationrepair"],
        "foursquare_categories": ["water softening equipment supplier"],
        "here_categories": ["water-treatment"],
        "tomtom_categories": ["water treatment service"],
        "google_types": ["water_treatment_plant"],
        "osm_tags": {"man_made": "water_works"},
    },
    "septic": {
        "display": "Septic Service",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["septic", "septic tank", "septic pumping"],
        "yelp_categories": ["septicservices"],
        "foursquare_categories": ["septic system service"],
        "here_categories": ["septic-systems"],
        "tomtom_categories": ["septic tank service"],
        "google_types": ["septic_system_service"],
        "osm_tags": {"man_made": "wastewater_plant"},
    },
    "chimney": {
        "display": "Chimney Service",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 3,
        "tags": ["chimney", "chimney sweep", "fireplace"],
        "yelp_categories": ["chimneysweeps"],
        "foursquare_categories": ["chimney sweep"],
        "here_categories": ["chimney-sweep"],
        "tomtom_categories": ["chimney sweep"],
        "google_types": ["chimney_sweep"],
        "osm_tags": {"craft": "chimney_sweeper"},
    },
    "insulation": {
        "display": "Insulation Contractor",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["insulation", "spray foam"],
        "yelp_categories": ["insulation_installation"],
        "foursquare_categories": ["insulation contractor"],
        "here_categories": ["insulation-contractor"],
        "tomtom_categories": ["insulation contractor"],
        "google_types": ["insulation_contractor"],
        "osm_tags": {"craft": "insulation"},
    },
    "gutter": {
        "display": "Gutter Service",
        "group": "SERVICE_TRADES",
        "tier": 3,
        "min_vehicles": 3,
        "tags": ["gutter", "gutters", "downspout"],
        "yelp_categories": ["gutter_services"],
        "foursquare_categories": ["gutter cleaning service"],
        "here_categories": ["gutter-services"],
        "tomtom_categories": ["gutter cleaning service"],
        "google_types": ["gutter_cleaning_service"],
        "osm_tags": {"craft": "roofer"},
    },
}


# ---------------------------------------------------------------------
# DISTRIBUTION (11 categories) - Tier 2-3
# Warehouses, logistics, food service distribution
# ---------------------------------------------------------------------

DISTRIBUTION_CATEGORIES: Dict[str, dict] = {
    "warehouse_distribution": {
        "display": "Warehouse / Distribution Center",
        "group": "DISTRIBUTION",
        "tier": 2,
        "min_vehicles": 40,
        "tags": ["warehouse", "distribution", "fulfillment"],
        "yelp_categories": ["couriers"],
        "foursquare_categories": ["distribution center"],
        "here_categories": ["distribution-center"],
        "tomtom_categories": ["distribution center"],
        "google_types": ["moving_company", "storage"],
        "osm_tags": {"building": "warehouse"},
    },
    "food_distribution": {
        "display": "Food / Beverage Distribution",
        "group": "DISTRIBUTION",
        "tier": 2,
        "min_vehicles": 30,
        "tags": ["food distribution", "beverage", "sysco", "us foods"],
        "yelp_categories": ["fooddeliveryservices"],
        "foursquare_categories": ["food distributor"],
        "here_categories": ["food-beverage-distribution"],
        "tomtom_categories": ["food products supplier"],
        "google_types": ["food_delivery"],
        "osm_tags": {"industrial": "food"},
    },
    "courier_delivery": {
        "display": "Courier / Delivery Service",
        "group": "DISTRIBUTION",
        "tier": 3,
        "min_vehicles": 20,
        "tags": ["courier", "delivery", "messenger"],
        "yelp_categories": ["couriers"],
        "foursquare_categories": ["courier service"],
        "here_categories": ["courier-services"],
        "tomtom_categories": ["courier service"],
        "google_types": ["courier_service"],
        "osm_tags": {"office": "courier"},
    },
    "medical_supply": {
        "display": "Medical Supply Distribution",
        "group": "DISTRIBUTION",
        "tier": 2,
        "min_vehicles": 15,
        "tags": ["medical supply", "medical equipment", "healthcare supply"],
        "yelp_categories": ["medicalsupplies"],
        "foursquare_categories": ["medical supply store"],
        "here_categories": ["medical-supplies"],
        "tomtom_categories": ["medical supply store"],
        "google_types": ["medical_supply_store"],
        "osm_tags": {"shop": "medical_supply"},
    },
    "building_materials": {
        "display": "Building Materials Supplier",
        "group": "DISTRIBUTION",
        "tier": 2,
        "min_vehicles": 25,
        "tags": ["building materials", "lumber", "construction supply"],
        "yelp_categories": ["buildingsupplies"],
        "foursquare_categories": ["building materials store"],
        "here_categories": ["building-materials"],
        "tomtom_categories": ["building materials supplier"],
        "google_types": ["building_materials_store"],
        "osm_tags": {"shop": "building_materials"},
    },
    "plumbing_supply": {
        "display": "Plumbing Supply",
        "group": "DISTRIBUTION",
        "tier": 3,
        "min_vehicles": 12,
        "tags": ["plumbing supply", "plumbing wholesale"],
        "yelp_categories": ["plumbing"],
        "foursquare_categories": ["plumbing supply store"],
        "here_categories": ["plumbing-supplies"],
        "tomtom_categories": ["plumbing supply store"],
        "google_types": ["plumbing_supply_store"],
        "osm_tags": {"shop": "plumbing"},
    },
    "electrical_supply": {
        "display": "Electrical Supply",
        "group": "DISTRIBUTION",
        "tier": 3,
        "min_vehicles": 12,
        "tags": ["electrical supply", "electrical wholesale"],
        "yelp_categories": ["electricians"],
        "foursquare_categories": ["electrical supply store"],
        "here_categories": ["electrical-supplies"],
        "tomtom_categories": ["electrical supply store"],
        "google_types": ["electrical_supply_store"],
        "osm_tags": {"shop": "electrical"},
    },
    "hvac_supply": {
        "display": "HVAC Supply",
        "group": "DISTRIBUTION",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["hvac supply", "hvac wholesale"],
        "yelp_categories": ["hvac"],
        "foursquare_categories": ["hvac equipment supplier"],
        "here_categories": ["hvac-supplies"],
        "tomtom_categories": ["hvac supply"],
        "google_types": ["hvac_contractor"],
        "osm_tags": {"shop": "hvac"},
    },
    "industrial_supply": {
        "display": "Industrial Supply",
        "group": "DISTRIBUTION",
        "tier": 2,
        "min_vehicles": 20,
        "tags": ["industrial supply", "industrial equipment", "grainger"],
        "yelp_categories": ["industrialsupplies"],
        "foursquare_categories": ["industrial equipment supplier"],
        "here_categories": ["industrial-supplies"],
        "tomtom_categories": ["industrial equipment supplier"],
        "google_types": ["hardware_store"],
        "osm_tags": {"shop": "industrial"},
    },
    "paper_packaging": {
        "display": "Paper / Packaging Supply",
        "group": "DISTRIBUTION",
        "tier": 3,
        "min_vehicles": 15,
        "tags": ["paper supply", "packaging", "box"],
        "yelp_categories": ["packaging"],
        "foursquare_categories": ["packaging supply store"],
        "here_categories": ["packaging-supplies"],
        "tomtom_categories": ["packaging service"],
        "google_types": ["packing_supply_store"],
        "osm_tags": {"shop": "packaging"},
    },
    "chemical_supply": {
        "display": "Chemical Supply",
        "group": "DISTRIBUTION",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["chemical supply", "industrial chemicals"],
        "yelp_categories": ["chemicalsuppliers"],
        "foursquare_categories": ["chemical company"],
        "here_categories": ["chemicals"],
        "tomtom_categories": ["chemical company"],
        "google_types": ["chemical_plant"],
        "osm_tags": {"industrial": "chemical"},
    },
}


# ---------------------------------------------------------------------
# AUTOMOTIVE (6 categories) - Tier 1-2
# High value targets - dealerships, rental, body shops
# ---------------------------------------------------------------------

AUTOMOTIVE_CATEGORIES: Dict[str, dict] = {
    "car_dealership": {
        "display": "Car Dealership",
        "group": "AUTOMOTIVE",
        "tier": 1,
        "min_vehicles": 150,
        "tags": ["dealership", "auto dealer", "car dealer", "new cars", "used cars"],
        "yelp_categories": ["cardealers", "usedcardealers"],
        "foursquare_categories": ["car dealer", "used car dealer"],
        "here_categories": ["car-dealer"],
        "tomtom_categories": ["car dealer"],
        "google_types": ["car_dealer"],
        "osm_tags": {"shop": "car"},
    },
    "car_rental": {
        "display": "Car Rental",
        "group": "AUTOMOTIVE",
        "tier": 1,
        "min_vehicles": 80,
        "tags": ["rental", "rent a car", "enterprise", "hertz", "avis"],
        "yelp_categories": ["carrental"],
        "foursquare_categories": ["car rental agency"],
        "here_categories": ["car-rental"],
        "tomtom_categories": ["car rental"],
        "google_types": ["car_rental"],
        "osm_tags": {"amenity": "car_rental"},
    },
    "body_shop": {
        "display": "Auto Body Shop",
        "group": "AUTOMOTIVE",
        "tier": 2,
        "min_vehicles": 25,
        "tags": ["body shop", "collision", "auto body", "dent repair"],
        "yelp_categories": ["bodyshops"],
        "foursquare_categories": ["auto body shop"],
        "here_categories": ["auto-body-shop"],
        "tomtom_categories": ["auto body shop"],
        "google_types": ["auto_body_shop"],
        "osm_tags": {"shop": "car_repair"},
    },
    "auto_repair": {
        "display": "Auto Repair Shop",
        "group": "AUTOMOTIVE",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["auto repair", "mechanic", "car repair"],
        "yelp_categories": ["autorepair"],
        "foursquare_categories": ["auto repair shop"],
        "here_categories": ["auto-service-repair"],
        "tomtom_categories": ["car repair"],
        "google_types": ["car_repair"],
        "osm_tags": {"shop": "car_repair"},
    },
    "tire_shop": {
        "display": "Tire Shop",
        "group": "AUTOMOTIVE",
        "tier": 3,
        "min_vehicles": 5,
        "tags": ["tire", "tires", "tire shop"],
        "yelp_categories": ["tires"],
        "foursquare_categories": ["tire shop"],
        "here_categories": ["tire-service"],
        "tomtom_categories": ["tire shop"],
        "google_types": ["tire_shop"],
        "osm_tags": {"shop": "tyres"},
    },
    "auto_parts": {
        "display": "Auto Parts Store",
        "group": "AUTOMOTIVE",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["auto parts", "car parts", "autozone", "oreilly", "advance"],
        "yelp_categories": ["autoparts"],
        "foursquare_categories": ["auto parts store"],
        "here_categories": ["auto-parts"],
        "tomtom_categories": ["auto parts store"],
        "google_types": ["auto_parts_store"],
        "osm_tags": {"shop": "car_parts"},
    },
}


# ---------------------------------------------------------------------
# CONSTRUCTION (9 categories) - Tier 2-3
# General contractors, excavation, concrete, etc.
# ---------------------------------------------------------------------

CONSTRUCTION_CATEGORIES: Dict[str, dict] = {
    "general_contractor": {
        "display": "General Contractor",
        "group": "CONSTRUCTION",
        "tier": 2,
        "min_vehicles": 15,
        "tags": ["general contractor", "builder", "construction company"],
        "yelp_categories": ["contractors"],
        "foursquare_categories": ["general contractor"],
        "here_categories": ["general-contractor"],
        "tomtom_categories": ["general contractor"],
        "google_types": ["general_contractor"],
        "osm_tags": {"office": "construction_company"},
    },
    "excavation": {
        "display": "Excavation / Grading",
        "group": "CONSTRUCTION",
        "tier": 2,
        "min_vehicles": 12,
        "tags": ["excavation", "grading", "earthwork", "dirt work"],
        "yelp_categories": ["excavationservices"],
        "foursquare_categories": ["excavating contractor"],
        "here_categories": ["excavation-contractor"],
        "tomtom_categories": ["excavating contractor"],
        "google_types": ["excavating_contractor"],
        "osm_tags": {"landuse": "construction"},
    },
    "concrete": {
        "display": "Concrete Contractor",
        "group": "CONSTRUCTION",
        "tier": 2,
        "min_vehicles": 10,
        "tags": ["concrete", "cement", "flatwork"],
        "yelp_categories": ["concretecontractors"],
        "foursquare_categories": ["concrete contractor"],
        "here_categories": ["concrete-contractor"],
        "tomtom_categories": ["concrete contractor"],
        "google_types": ["concrete_contractor"],
        "osm_tags": {"craft": "concrete"},
    },
    "masonry": {
        "display": "Masonry Contractor",
        "group": "CONSTRUCTION",
        "tier": 3,
        "min_vehicles": 6,
        "tags": ["masonry", "brick", "stone", "block"],
        "yelp_categories": ["masonry_concrete"],
        "foursquare_categories": ["masonry contractor"],
        "here_categories": ["masonry-contractor"],
        "tomtom_categories": ["masonry contractor"],
        "google_types": ["masonry_contractor"],
        "osm_tags": {"craft": "mason"},
    },
    "steel_fabrication": {
        "display": "Steel / Metal Fabrication",
        "group": "CONSTRUCTION",
        "tier": 2,
        "min_vehicles": 12,
        "tags": ["steel", "metal", "fabrication", "welding"],
        "yelp_categories": ["metalfabricators"],
        "foursquare_categories": ["metal fabricator"],
        "here_categories": ["metal-fabrication"],
        "tomtom_categories": ["steel fabrication"],
        "google_types": ["metal_fabricator"],
        "osm_tags": {"craft": "metal_construction"},
    },
    "paving": {
        "display": "Paving / Asphalt",
        "group": "CONSTRUCTION",
        "tier": 2,
        "min_vehicles": 15,
        "tags": ["paving", "asphalt", "blacktop", "parking lot"],
        "yelp_categories": ["pavingcontractors"],
        "foursquare_categories": ["paving contractor"],
        "here_categories": ["paving-contractor"],
        "tomtom_categories": ["paving contractor"],
        "google_types": ["paving_contractor"],
        "osm_tags": {"craft": "paver"},
    },
    "framing": {
        "display": "Framing Contractor",
        "group": "CONSTRUCTION",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["framing", "carpentry", "structural"],
        "yelp_categories": ["carpenters"],
        "foursquare_categories": ["framing contractor"],
        "here_categories": ["framing-contractor"],
        "tomtom_categories": ["framing contractor"],
        "google_types": ["carpenter"],
        "osm_tags": {"craft": "carpenter"},
    },
    "drywall": {
        "display": "Drywall Contractor",
        "group": "CONSTRUCTION",
        "tier": 3,
        "min_vehicles": 6,
        "tags": ["drywall", "sheetrock", "plaster"],
        "yelp_categories": ["drywall"],
        "foursquare_categories": ["drywall contractor"],
        "here_categories": ["drywall-contractor"],
        "tomtom_categories": ["drywall contractor"],
        "google_types": ["drywall_contractor"],
        "osm_tags": {"craft": "plasterer"},
    },
    "demolition": {
        "display": "Demolition Contractor",
        "group": "CONSTRUCTION",
        "tier": 2,
        "min_vehicles": 10,
        "tags": ["demolition", "wrecking"],
        "yelp_categories": ["demolitionservices"],
        "foursquare_categories": ["demolition contractor"],
        "here_categories": ["demolition-contractor"],
        "tomtom_categories": ["demolition contractor"],
        "google_types": ["demolition_contractor"],
        "osm_tags": {"landuse": "construction"},
    },
}


# ---------------------------------------------------------------------
# MEDICAL (6 categories) - Tier 2
# Hospitals, clinics, home health
# ---------------------------------------------------------------------

MEDICAL_CATEGORIES: Dict[str, dict] = {
    "hospital": {
        "display": "Hospital",
        "group": "MEDICAL",
        "tier": 2,
        "min_vehicles": 70,
        "tags": ["hospital", "medical center", "health system"],
        "yelp_categories": ["hospitals"],
        "foursquare_categories": ["hospital"],
        "here_categories": ["hospital"],
        "tomtom_categories": ["hospital"],
        "google_types": ["hospital"],
        "osm_tags": {"amenity": "hospital"},
    },
    "medical_clinic": {
        "display": "Medical Clinic",
        "group": "MEDICAL",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["clinic", "urgent care", "medical clinic"],
        "yelp_categories": ["medcenters", "urgentcare"],
        "foursquare_categories": ["medical clinic"],
        "here_categories": ["clinic"],
        "tomtom_categories": ["medical clinic"],
        "google_types": ["hospital"],
        "osm_tags": {"amenity": "clinic"},
    },
    "home_health": {
        "display": "Home Health Care",
        "group": "MEDICAL",
        "tier": 2,
        "min_vehicles": 25,
        "tags": ["home health", "home care", "visiting nurse"],
        "yelp_categories": ["homehealthcare"],
        "foursquare_categories": ["home health care service"],
        "here_categories": ["home-health-care"],
        "tomtom_categories": ["home health care"],
        "google_types": ["home_health_care_service"],
        "osm_tags": {"healthcare": "home_health"},
    },
    "nursing_home": {
        "display": "Nursing Home / Assisted Living",
        "group": "MEDICAL",
        "tier": 2,
        "min_vehicles": 15,
        "tags": ["nursing home", "assisted living", "senior care"],
        "yelp_categories": ["nursinghomes", "assistedliving"],
        "foursquare_categories": ["nursing home"],
        "here_categories": ["nursing-home"],
        "tomtom_categories": ["nursing home"],
        "google_types": ["nursing_home"],
        "osm_tags": {"amenity": "nursing_home"},
    },
    "ambulance": {
        "display": "Ambulance Service",
        "group": "MEDICAL",
        "tier": 1,
        "min_vehicles": 30,
        "tags": ["ambulance", "ems", "emergency medical"],
        "yelp_categories": ["emergencymedicine"],
        "foursquare_categories": ["ambulance service"],
        "here_categories": ["ambulance-service"],
        "tomtom_categories": ["ambulance service"],
        "google_types": ["ambulance_service"],
        "osm_tags": {"emergency": "ambulance_station"},
    },
    "dental": {
        "display": "Dental Office",
        "group": "MEDICAL",
        "tier": 3,
        "min_vehicles": 3,
        "tags": ["dentist", "dental", "orthodontist"],
        "yelp_categories": ["dentists"],
        "foursquare_categories": ["dentist"],
        "here_categories": ["dentist"],
        "tomtom_categories": ["dentist"],
        "google_types": ["dentist"],
        "osm_tags": {"amenity": "dentist"},
    },
}


# ---------------------------------------------------------------------
# TELECOM / UTILITIES (6 categories) - Tier 1-2
# Cable, telecom, electric, gas, water
# ---------------------------------------------------------------------

TELECOM_UTILITIES_CATEGORIES: Dict[str, dict] = {
    "electric_utility": {
        "display": "Electric Utility",
        "group": "TELECOM_UTILITIES",
        "tier": 1,
        "min_vehicles": 80,
        "tags": ["electric", "power company", "electric utility"],
        "yelp_categories": ["utilities"],
        "foursquare_categories": ["electric utility company"],
        "here_categories": ["electric-utility"],
        "tomtom_categories": ["electric utility"],
        "google_types": ["electric_utility_company"],
        "osm_tags": {"power": "plant"},
    },
    "gas_utility": {
        "display": "Gas Utility",
        "group": "TELECOM_UTILITIES",
        "tier": 1,
        "min_vehicles": 50,
        "tags": ["gas", "natural gas", "gas utility"],
        "yelp_categories": ["utilities"],
        "foursquare_categories": ["gas company"],
        "here_categories": ["gas-utility"],
        "tomtom_categories": ["gas company"],
        "google_types": ["gas_station"],
        "osm_tags": {"industrial": "gas"},
    },
    "water_utility": {
        "display": "Water Utility",
        "group": "TELECOM_UTILITIES",
        "tier": 1,
        "min_vehicles": 40,
        "tags": ["water", "water utility", "water district"],
        "yelp_categories": ["utilities"],
        "foursquare_categories": ["water utility"],
        "here_categories": ["water-utility"],
        "tomtom_categories": ["water utility"],
        "google_types": ["water_utility"],
        "osm_tags": {"man_made": "water_works"},
    },
    "cable_internet": {
        "display": "Cable / Internet Provider",
        "group": "TELECOM_UTILITIES",
        "tier": 1,
        "min_vehicles": 60,
        "tags": ["cable", "internet", "broadband", "fiber"],
        "yelp_categories": ["internetserviceproviders", "televisionserviceproviders"],
        "foursquare_categories": ["cable company"],
        "here_categories": ["cable-company"],
        "tomtom_categories": ["cable company"],
        "google_types": ["telecommunications_service_provider"],
        "osm_tags": {"telecom": "office"},
    },
    "telecom": {
        "display": "Telecommunications",
        "group": "TELECOM_UTILITIES",
        "tier": 1,
        "min_vehicles": 50,
        "tags": ["telecom", "telephone", "communications"],
        "yelp_categories": ["telecommunications"],
        "foursquare_categories": ["telecommunications company"],
        "here_categories": ["telecommunications"],
        "tomtom_categories": ["telecommunications company"],
        "google_types": ["telecommunications_service_provider"],
        "osm_tags": {"office": "telecommunication"},
    },
    "cell_tower": {
        "display": "Cell Tower Services",
        "group": "TELECOM_UTILITIES",
        "tier": 2,
        "min_vehicles": 20,
        "tags": ["cell tower", "wireless", "tower"],
        "yelp_categories": ["telecommunications"],
        "foursquare_categories": ["cell phone tower"],
        "here_categories": ["cell-tower"],
        "tomtom_categories": ["cellular tower"],
        "google_types": ["telecommunications_service_provider"],
        "osm_tags": {"man_made": "mast"},
    },
}


# ---------------------------------------------------------------------
# WASTE MANAGEMENT (5 categories) - Tier 2
# Trash, recycling, dumpster rental
# ---------------------------------------------------------------------

WASTE_CATEGORIES: Dict[str, dict] = {
    "waste_hauling": {
        "display": "Waste Hauling",
        "group": "WASTE",
        "tier": 2,
        "min_vehicles": 40,
        "tags": ["trash", "garbage", "waste", "refuse"],
        "yelp_categories": ["jaboremoval"],
        "foursquare_categories": ["waste management company"],
        "here_categories": ["waste-management"],
        "tomtom_categories": ["waste disposal service"],
        "google_types": ["waste_management"],
        "osm_tags": {"landuse": "landfill"},
    },
    "recycling": {
        "display": "Recycling Service",
        "group": "WASTE",
        "tier": 2,
        "min_vehicles": 25,
        "tags": ["recycling", "scrap", "metal recycling"],
        "yelp_categories": ["recyclingcenter"],
        "foursquare_categories": ["recycling center"],
        "here_categories": ["recycling"],
        "tomtom_categories": ["recycling center"],
        "google_types": ["recycling_center"],
        "osm_tags": {"amenity": "recycling"},
    },
    "dumpster_rental": {
        "display": "Dumpster Rental",
        "group": "WASTE",
        "tier": 3,
        "min_vehicles": 15,
        "tags": ["dumpster", "roll off", "container"],
        "yelp_categories": ["dumpsterrental"],
        "foursquare_categories": ["dumpster rental service"],
        "here_categories": ["dumpster-rental"],
        "tomtom_categories": ["dumpster rental"],
        "google_types": ["dumpster_rental_service"],
        "osm_tags": {"amenity": "waste_disposal"},
    },
    "hazmat": {
        "display": "Hazardous Waste",
        "group": "WASTE",
        "tier": 2,
        "min_vehicles": 15,
        "tags": ["hazmat", "hazardous", "toxic"],
        "yelp_categories": ["hazardouswaste"],
        "foursquare_categories": ["hazardous waste disposal"],
        "here_categories": ["hazardous-waste"],
        "tomtom_categories": ["hazardous waste disposal"],
        "google_types": ["hazardous_waste_disposal"],
        "osm_tags": {"amenity": "waste_disposal"},
    },
    "portable_toilet": {
        "display": "Portable Toilet Rental",
        "group": "WASTE",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["porta potty", "portable toilet", "sanitation"],
        "yelp_categories": ["portabletoiletrental"],
        "foursquare_categories": ["portable toilet company"],
        "here_categories": ["portable-toilet"],
        "tomtom_categories": ["portable toilet rental"],
        "google_types": ["portable_toilet_supplier"],
        "osm_tags": {"amenity": "toilets"},
    },
}


# ---------------------------------------------------------------------
# RENTAL / EQUIPMENT (5 categories) - Tier 2
# Equipment rental, tool rental, party rental
# ---------------------------------------------------------------------

RENTAL_CATEGORIES: Dict[str, dict] = {
    "equipment_rental": {
        "display": "Equipment Rental",
        "group": "RENTAL",
        "tier": 2,
        "min_vehicles": 20,
        "tags": ["equipment rental", "heavy equipment", "rental yard"],
        "yelp_categories": ["equipmentrental"],
        "foursquare_categories": ["equipment rental shop"],
        "here_categories": ["equipment-rental"],
        "tomtom_categories": ["equipment rental"],
        "google_types": ["equipment_rental_agency"],
        "osm_tags": {"shop": "rental"},
    },
    "tool_rental": {
        "display": "Tool Rental",
        "group": "RENTAL",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["tool rental", "home depot rental"],
        "yelp_categories": ["toolrental"],
        "foursquare_categories": ["tool rental"],
        "here_categories": ["tool-rental"],
        "tomtom_categories": ["tool rental"],
        "google_types": ["tool_rental"],
        "osm_tags": {"shop": "tool_hire"},
    },
    "party_rental": {
        "display": "Party / Event Rental",
        "group": "RENTAL",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["party rental", "tent rental", "event rental"],
        "yelp_categories": ["partysupplies", "partyequipmentrentals"],
        "foursquare_categories": ["party equipment rental"],
        "here_categories": ["party-rental"],
        "tomtom_categories": ["party equipment rental"],
        "google_types": ["party_store"],
        "osm_tags": {"shop": "party"},
    },
    "truck_rental": {
        "display": "Truck Rental",
        "group": "RENTAL",
        "tier": 2,
        "min_vehicles": 30,
        "tags": ["truck rental", "uhaul", "penske", "moving truck"],
        "yelp_categories": ["truckrental"],
        "foursquare_categories": ["truck rental"],
        "here_categories": ["truck-rental"],
        "tomtom_categories": ["truck rental"],
        "google_types": ["truck_rental_agency"],
        "osm_tags": {"amenity": "car_rental"},
    },
    "trailer_rental": {
        "display": "Trailer Rental",
        "group": "RENTAL",
        "tier": 3,
        "min_vehicles": 15,
        "tags": ["trailer rental", "utility trailer"],
        "yelp_categories": ["trailerrental"],
        "foursquare_categories": ["trailer rental"],
        "here_categories": ["trailer-rental"],
        "tomtom_categories": ["trailer rental"],
        "google_types": ["trailer_rental_service"],
        "osm_tags": {"shop": "trailer"},
    },
}


# ---------------------------------------------------------------------
# PROPERTY / REAL ESTATE (4 categories) - Tier 2-3
# Property management, apartments, HOA
# ---------------------------------------------------------------------

PROPERTY_CATEGORIES: Dict[str, dict] = {
    "property_management": {
        "display": "Property Management",
        "group": "PROPERTY",
        "tier": 2,
        "min_vehicles": 15,
        "tags": ["property management", "property manager"],
        "yelp_categories": ["propertymanagement"],
        "foursquare_categories": ["property management company"],
        "here_categories": ["property-management"],
        "tomtom_categories": ["property management company"],
        "google_types": ["real_estate_agency"],
        "osm_tags": {"office": "property_management"},
    },
    "large_apartment": {
        "display": "Large Apartment Complex",
        "group": "PROPERTY",
        "tier": 2,
        "min_vehicles": 200,
        "tags": ["apartment", "apartments", "apartment complex"],
        "yelp_categories": ["apartments"],
        "foursquare_categories": ["apartment complex"],
        "here_categories": ["apartment-complex"],
        "tomtom_categories": ["apartment complex"],
        "google_types": ["apartment_complex"],
        "osm_tags": {"building": "apartments"},
    },
    "hoa_management": {
        "display": "HOA Management",
        "group": "PROPERTY",
        "tier": 3,
        "min_vehicles": 5,
        "tags": ["hoa", "homeowner association", "community management"],
        "yelp_categories": ["propertymanagement"],
        "foursquare_categories": ["property management company"],
        "here_categories": ["hoa-management"],
        "tomtom_categories": ["property management"],
        "google_types": ["real_estate_agency"],
        "osm_tags": {"office": "association"},
    },
    "parking_structure": {
        "display": "Parking Structure",
        "group": "PROPERTY",
        "tier": 1,
        "min_vehicles": 300,
        "tags": ["parking garage", "parking structure", "parking lot"],
        "yelp_categories": ["parking"],
        "foursquare_categories": ["parking garage"],
        "here_categories": ["parking-garage"],
        "tomtom_categories": ["parking garage"],
        "google_types": ["parking"],
        "osm_tags": {"amenity": "parking"},
    },
}


# ---------------------------------------------------------------------
# GOVERNMENT / MUNICIPAL (8 categories) - Tier 1-2
# City, county, police, fire, schools
# ---------------------------------------------------------------------

GOVERNMENT_CATEGORIES: Dict[str, dict] = {
    "municipal_fleet": {
        "display": "Municipal Fleet",
        "group": "GOVERNMENT",
        "tier": 1,
        "min_vehicles": 80,
        "tags": ["city", "municipal", "city fleet", "public works"],
        "yelp_categories": ["publicservicesgovt"],
        "foursquare_categories": ["city hall"],
        "here_categories": ["government-office"],
        "tomtom_categories": ["government office"],
        "google_types": ["city_hall"],
        "osm_tags": {"amenity": "townhall"},
    },
    "county_fleet": {
        "display": "County Fleet",
        "group": "GOVERNMENT",
        "tier": 1,
        "min_vehicles": 100,
        "tags": ["county", "county fleet"],
        "yelp_categories": ["publicservicesgovt"],
        "foursquare_categories": ["county government office"],
        "here_categories": ["county-office"],
        "tomtom_categories": ["county council"],
        "google_types": ["local_government_office"],
        "osm_tags": {"office": "government"},
    },
    "police_department": {
        "display": "Police Department",
        "group": "GOVERNMENT",
        "tier": 1,
        "min_vehicles": 60,
        "tags": ["police", "sheriff", "law enforcement"],
        "yelp_categories": ["policedepartments"],
        "foursquare_categories": ["police station"],
        "here_categories": ["police-station"],
        "tomtom_categories": ["police station"],
        "google_types": ["police"],
        "osm_tags": {"amenity": "police"},
    },
    "fire_department": {
        "display": "Fire Department",
        "group": "GOVERNMENT",
        "tier": 1,
        "min_vehicles": 30,
        "tags": ["fire", "fire department", "fire station"],
        "yelp_categories": ["firedepartments"],
        "foursquare_categories": ["fire station"],
        "here_categories": ["fire-station"],
        "tomtom_categories": ["fire station"],
        "google_types": ["fire_station"],
        "osm_tags": {"amenity": "fire_station"},
    },
    "school_district": {
        "display": "School District",
        "group": "GOVERNMENT",
        "tier": 2,
        "min_vehicles": 60,
        "tags": ["school", "school district", "isd", "school bus"],
        "yelp_categories": ["elementaryschools", "highschools"],
        "foursquare_categories": ["school"],
        "here_categories": ["school"],
        "tomtom_categories": ["school"],
        "google_types": ["school"],
        "osm_tags": {"amenity": "school"},
    },
    "university": {
        "display": "University / College",
        "group": "GOVERNMENT",
        "tier": 2,
        "min_vehicles": 80,
        "tags": ["university", "college", "higher education"],
        "yelp_categories": ["collegesuniversities"],
        "foursquare_categories": ["university"],
        "here_categories": ["university"],
        "tomtom_categories": ["university"],
        "google_types": ["university"],
        "osm_tags": {"amenity": "university"},
    },
    "state_agency": {
        "display": "State Agency",
        "group": "GOVERNMENT",
        "tier": 1,
        "min_vehicles": 100,
        "tags": ["state", "state agency", "dot", "txdot"],
        "yelp_categories": ["publicservicesgovt"],
        "foursquare_categories": ["government building"],
        "here_categories": ["state-office"],
        "tomtom_categories": ["government office"],
        "google_types": ["local_government_office"],
        "osm_tags": {"office": "government"},
    },
    "federal_agency": {
        "display": "Federal Agency",
        "group": "GOVERNMENT",
        "tier": 1,
        "min_vehicles": 150,
        "tags": ["federal", "gsa", "usps", "federal agency"],
        "yelp_categories": ["publicservicesgovt"],
        "foursquare_categories": ["government building"],
        "here_categories": ["federal-office"],
        "tomtom_categories": ["government office"],
        "google_types": ["local_government_office"],
        "osm_tags": {"office": "government"},
    },
}


# ---------------------------------------------------------------------
# RETAIL / DELIVERY (5 categories) - Tier 3
# Pizza, pharmacy, florist, etc.
# ---------------------------------------------------------------------

RETAIL_DELIVERY_CATEGORIES: Dict[str, dict] = {
    "pizza_delivery": {
        "display": "Pizza Delivery",
        "group": "RETAIL_DELIVERY",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["pizza", "pizza delivery", "dominos", "papa johns"],
        "yelp_categories": ["pizza"],
        "foursquare_categories": ["pizza place"],
        "here_categories": ["pizza-restaurant"],
        "tomtom_categories": ["pizza restaurant"],
        "google_types": ["meal_delivery"],
        "osm_tags": {"amenity": "restaurant", "cuisine": "pizza"},
    },
    "pharmacy": {
        "display": "Pharmacy",
        "group": "RETAIL_DELIVERY",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["pharmacy", "drugstore", "cvs", "walgreens"],
        "yelp_categories": ["pharmacy"],
        "foursquare_categories": ["pharmacy"],
        "here_categories": ["pharmacy"],
        "tomtom_categories": ["pharmacy"],
        "google_types": ["pharmacy"],
        "osm_tags": {"amenity": "pharmacy"},
    },
    "florist": {
        "display": "Florist",
        "group": "RETAIL_DELIVERY",
        "tier": 3,
        "min_vehicles": 4,
        "tags": ["florist", "flower", "floral"],
        "yelp_categories": ["florists"],
        "foursquare_categories": ["florist"],
        "here_categories": ["florist"],
        "tomtom_categories": ["florist"],
        "google_types": ["florist"],
        "osm_tags": {"shop": "florist"},
    },
    "catering": {
        "display": "Catering",
        "group": "RETAIL_DELIVERY",
        "tier": 3,
        "min_vehicles": 6,
        "tags": ["catering", "caterer"],
        "yelp_categories": ["caterers"],
        "foursquare_categories": ["catering service"],
        "here_categories": ["catering"],
        "tomtom_categories": ["catering service"],
        "google_types": ["meal_delivery"],
        "osm_tags": {"amenity": "restaurant"},
    },
    "furniture_delivery": {
        "display": "Furniture Store / Delivery",
        "group": "RETAIL_DELIVERY",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["furniture", "furniture store", "mattress"],
        "yelp_categories": ["furniture"],
        "foursquare_categories": ["furniture store"],
        "here_categories": ["furniture-store"],
        "tomtom_categories": ["furniture store"],
        "google_types": ["furniture_store"],
        "osm_tags": {"shop": "furniture"},
    },
}


# ---------------------------------------------------------------------
# TRANSPORT (8 categories) - Tier 2
# Trucking, moving, towing, bus
# ---------------------------------------------------------------------

TRANSPORT_CATEGORIES: Dict[str, dict] = {
    "trucking": {
        "display": "Trucking Company",
        "group": "TRANSPORT",
        "tier": 2,
        "min_vehicles": 40,
        "tags": ["trucking", "freight", "hauling", "18 wheeler"],
        "yelp_categories": ["trucking"],
        "foursquare_categories": ["trucking company"],
        "here_categories": ["trucking-company"],
        "tomtom_categories": ["trucking company"],
        "google_types": ["trucking_company"],
        "osm_tags": {"industrial": "transport"},
    },
    "moving_company": {
        "display": "Moving Company",
        "group": "TRANSPORT",
        "tier": 2,
        "min_vehicles": 20,
        "tags": ["moving", "movers", "relocation"],
        "yelp_categories": ["movers"],
        "foursquare_categories": ["moving company"],
        "here_categories": ["moving-company"],
        "tomtom_categories": ["moving company"],
        "google_types": ["moving_company"],
        "osm_tags": {"office": "moving_company"},
    },
    "towing": {
        "display": "Towing Service",
        "group": "TRANSPORT",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["towing", "tow truck", "wrecker"],
        "yelp_categories": ["towing"],
        "foursquare_categories": ["towing service"],
        "here_categories": ["towing-service"],
        "tomtom_categories": ["towing service"],
        "google_types": ["towing_service"],
        "osm_tags": {"shop": "towing"},
    },
    "bus_company": {
        "display": "Bus / Charter Company",
        "group": "TRANSPORT",
        "tier": 2,
        "min_vehicles": 25,
        "tags": ["bus", "charter", "coach", "shuttle"],
        "yelp_categories": ["buses"],
        "foursquare_categories": ["bus line"],
        "here_categories": ["bus-company"],
        "tomtom_categories": ["bus company"],
        "google_types": ["bus_station"],
        "osm_tags": {"amenity": "bus_station"},
    },
    "taxi_limo": {
        "display": "Taxi / Limo Service",
        "group": "TRANSPORT",
        "tier": 3,
        "min_vehicles": 15,
        "tags": ["taxi", "limo", "limousine", "car service"],
        "yelp_categories": ["taxis", "limos"],
        "foursquare_categories": ["taxi"],
        "here_categories": ["taxi-service"],
        "tomtom_categories": ["taxi service"],
        "google_types": ["taxi_stand"],
        "osm_tags": {"amenity": "taxi"},
    },
    "auto_transport": {
        "display": "Auto Transport",
        "group": "TRANSPORT",
        "tier": 2,
        "min_vehicles": 20,
        "tags": ["auto transport", "car hauler", "vehicle transport"],
        "yelp_categories": ["vehicleshipping"],
        "foursquare_categories": ["car shipping company"],
        "here_categories": ["auto-transport"],
        "tomtom_categories": ["vehicle transport"],
        "google_types": ["moving_company"],
        "osm_tags": {"industrial": "transport"},
    },
    "hotshot": {
        "display": "Hotshot / Expedited Freight",
        "group": "TRANSPORT",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["hotshot", "expedited", "oilfield transport"],
        "yelp_categories": ["couriers"],
        "foursquare_categories": ["courier service"],
        "here_categories": ["freight-service"],
        "tomtom_categories": ["freight service"],
        "google_types": ["courier_service"],
        "osm_tags": {"industrial": "transport"},
    },
    "oilfield_services": {
        "display": "Oilfield Services",
        "group": "TRANSPORT",
        "tier": 1,
        "min_vehicles": 50,
        "tags": ["oilfield", "oil and gas", "drilling"],
        "yelp_categories": ["oilchange"],
        "foursquare_categories": ["oil and gas company"],
        "here_categories": ["oil-gas"],
        "tomtom_categories": ["oil and gas company"],
        "google_types": ["oil_refinery"],
        "osm_tags": {"industrial": "oil"},
    },
}


# ---------------------------------------------------------------------
# OTHER (6 categories) - Tier 2-3
# Golf, event venue, religious, insurance
# ---------------------------------------------------------------------

OTHER_CATEGORIES: Dict[str, dict] = {
    "golf_course": {
        "display": "Golf Course",
        "group": "OTHER",
        "tier": 2,
        "min_vehicles": 40,
        "tags": ["golf", "country club", "golf course"],
        "yelp_categories": ["golf"],
        "foursquare_categories": ["golf course"],
        "here_categories": ["golf-course"],
        "tomtom_categories": ["golf course"],
        "google_types": ["golf_course"],
        "osm_tags": {"leisure": "golf_course"},
    },
    "event_venue": {
        "display": "Event Venue / Arena",
        "group": "OTHER",
        "tier": 2,
        "min_vehicles": 120,
        "tags": ["arena", "stadium", "convention center", "event venue"],
        "yelp_categories": ["venues", "stadiumsarenas"],
        "foursquare_categories": ["event space"],
        "here_categories": ["event-venue"],
        "tomtom_categories": ["event venue"],
        "google_types": ["stadium"],
        "osm_tags": {"leisure": "stadium"},
    },
    "religious": {
        "display": "Religious Organization",
        "group": "OTHER",
        "tier": 3,
        "min_vehicles": 8,
        "tags": ["church", "temple", "mosque", "synagogue"],
        "yelp_categories": ["churches"],
        "foursquare_categories": ["church"],
        "here_categories": ["church"],
        "tomtom_categories": ["church"],
        "google_types": ["church"],
        "osm_tags": {"amenity": "place_of_worship"},
    },
    "insurance_office": {
        "display": "Insurance Office",
        "group": "OTHER",
        "tier": 3,
        "min_vehicles": 10,
        "tags": ["insurance", "insurance agent", "state farm", "allstate"],
        "yelp_categories": ["insurance"],
        "foursquare_categories": ["insurance company"],
        "here_categories": ["insurance-company"],
        "tomtom_categories": ["insurance company"],
        "google_types": ["insurance_agency"],
        "osm_tags": {"office": "insurance"},
    },
    "storage_facility": {
        "display": "Storage Facility",
        "group": "OTHER",
        "tier": 3,
        "min_vehicles": 5,
        "tags": ["storage", "self storage", "mini storage"],
        "yelp_categories": ["selfstorage"],
        "foursquare_categories": ["self storage facility"],
        "here_categories": ["storage-facility"],
        "tomtom_categories": ["self storage"],
        "google_types": ["storage"],
        "osm_tags": {"building": "warehouse"},
    },
    "rv_dealership": {
        "display": "RV / Boat Dealership",
        "group": "OTHER",
        "tier": 2,
        "min_vehicles": 50,
        "tags": ["rv", "motorhome", "camper", "boat"],
        "yelp_categories": ["rvdealers", "boatdealers"],
        "foursquare_categories": ["rv dealer"],
        "here_categories": ["rv-dealer"],
        "tomtom_categories": ["rv dealer"],
        "google_types": ["rv_dealer"],
        "osm_tags": {"shop": "caravan"},
    },
}


# ---------------------------------------------------------------------
# COMBINED CATEGORIES DICT (all 70+ categories)
# ---------------------------------------------------------------------

CATEGORIES: Dict[str, dict] = {
    **SERVICE_TRADES_CATEGORIES,
    **DISTRIBUTION_CATEGORIES,
    **AUTOMOTIVE_CATEGORIES,
    **CONSTRUCTION_CATEGORIES,
    **MEDICAL_CATEGORIES,
    **TELECOM_UTILITIES_CATEGORIES,
    **WASTE_CATEGORIES,
    **RENTAL_CATEGORIES,
    **PROPERTY_CATEGORIES,
    **GOVERNMENT_CATEGORIES,
    **RETAIL_DELIVERY_CATEGORIES,
    **TRANSPORT_CATEGORIES,
    **OTHER_CATEGORIES,
}


# ---------------------------------------------------------------------
# Category Groups for UI/filtering
# ---------------------------------------------------------------------

CATEGORY_GROUPS = {
    "SERVICE_TRADES": list(SERVICE_TRADES_CATEGORIES.keys()),
    "DISTRIBUTION": list(DISTRIBUTION_CATEGORIES.keys()),
    "AUTOMOTIVE": list(AUTOMOTIVE_CATEGORIES.keys()),
    "CONSTRUCTION": list(CONSTRUCTION_CATEGORIES.keys()),
    "MEDICAL": list(MEDICAL_CATEGORIES.keys()),
    "TELECOM_UTILITIES": list(TELECOM_UTILITIES_CATEGORIES.keys()),
    "WASTE": list(WASTE_CATEGORIES.keys()),
    "RENTAL": list(RENTAL_CATEGORIES.keys()),
    "PROPERTY": list(PROPERTY_CATEGORIES.keys()),
    "GOVERNMENT": list(GOVERNMENT_CATEGORIES.keys()),
    "RETAIL_DELIVERY": list(RETAIL_DELIVERY_CATEGORIES.keys()),
    "TRANSPORT": list(TRANSPORT_CATEGORIES.keys()),
    "OTHER": list(OTHER_CATEGORIES.keys()),
}


# ---------------------------------------------------------------------
# Legacy -> canonical aliases (backwards compatibility)
# ---------------------------------------------------------------------

ALIASES: Dict[str, str] = {
    # Service trades
    "service_company": "hvac",  # Default to HVAC for generic "service company"
    "service_trades": "hvac",

    # Automotive
    "rental_car": "car_rental",
    "dealer": "car_dealership",
    "dealerships": "car_dealership",
    "rentals": "car_rental",

    # Government
    "municipal": "municipal_fleet",
    "utilities": "electric_utility",

    # Property
    "parking": "parking_structure",
    "apartments": "large_apartment",

    # Education
    "school_university": "school_district",

    # Distribution
    "delivery_logistics": "warehouse_distribution",
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def normalize_category_key(key: str) -> str:
    """Normalize a category key to canonical form"""
    if not key:
        return ""
    k = key.strip().lower().replace(" ", "_").replace("-", "_")
    return ALIASES.get(k, k)


def get_categories_by_tier(tier: int) -> List[dict]:
    """Get all categories for a specific tier"""
    return [
        {"key": k, **v}
        for k, v in CATEGORIES.items()
        if int(v.get("tier", 3)) == int(tier)
    ]


def get_categories_by_group(group: str) -> List[dict]:
    """Get all categories in a specific group"""
    keys = CATEGORY_GROUPS.get(group.upper(), [])
    return [{"key": k, **CATEGORIES[k]} for k in keys if k in CATEGORIES]


def estimate_vehicles(category_key: str) -> int:
    """Estimate minimum vehicles for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return 0
    return int(cat.get("min_vehicles", 0))


def detect_category_from_tags(tags: List[str]) -> Optional[str]:
    """Detect category from a list of tags/keywords"""
    if not tags:
        return None
    tagset = {t.strip().lower() for t in tags if t and t.strip()}
    for key, meta in CATEGORIES.items():
        for t in meta.get("tags", []):
            if t.lower() in tagset:
                return key
    return None


def get_yelp_categories(category_key: str) -> List[str]:
    """Get Yelp category codes for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return []
    return cat.get("yelp_categories", [])


def get_foursquare_categories(category_key: str) -> List[str]:
    """Get Foursquare category names for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return []
    return cat.get("foursquare_categories", [])


def get_here_categories(category_key: str) -> List[str]:
    """Get HERE category IDs for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return []
    return cat.get("here_categories", [])


def get_tomtom_categories(category_key: str) -> List[str]:
    """Get TomTom category names for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return []
    return cat.get("tomtom_categories", [])


def get_google_types(category_key: str) -> List[str]:
    """Get Google Places types for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return []
    return cat.get("google_types", [])


def get_osm_tags(category_key: str) -> Dict[str, str]:
    """Get OpenStreetMap tags for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return {}
    return cat.get("osm_tags", {})


def get_all_api_search_terms(category_key: str) -> Dict[str, Any]:
    """Get all API search terms for a category"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return {}
    return {
        "yelp": cat.get("yelp_categories", []),
        "foursquare": cat.get("foursquare_categories", []),
        "here": cat.get("here_categories", []),
        "tomtom": cat.get("tomtom_categories", []),
        "google": cat.get("google_types", []),
        "osm": cat.get("osm_tags", {}),
    }


def get_all_category_keys() -> List[str]:
    """Get all category keys"""
    return list(CATEGORIES.keys())


def get_category_count() -> int:
    """Get total number of categories"""
    return len(CATEGORIES)


# ---------------------------------------------------------------------
# Backwards Compatibility Exports
# These names are used by other modules importing from this file
# ---------------------------------------------------------------------

# Alias for CATEGORIES - used by fleet_locations.py, fast_discovery.py, etc.
CATEGORY_TAXONOMY = CATEGORIES


def get_category(category_key: str) -> Optional[dict]:
    """Get a category definition by key (backwards compat)"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if cat:
        return {"key": ck, **cat}
    return None


def get_osm_tags_for_category(category_key: str) -> Dict[str, str]:
    """Get OSM tags for a category (backwards compat alias)"""
    return get_osm_tags(category_key)


def get_keywords_for_category(category_key: str) -> List[str]:
    """Get keywords/tags for a category (backwards compat)"""
    ck = normalize_category_key(category_key)
    cat = CATEGORIES.get(ck)
    if not cat:
        return []
    return cat.get("tags", [])


# Print category count when module loads (for debugging)
_total = get_category_count()
if _total < 70:
    import warnings
    warnings.warn(f"Category taxonomy only has {_total} categories. Expected 70+.")
