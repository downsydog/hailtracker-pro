"""
Fleet Categories - Thin Wrapper for Category Taxonomy
======================================================

This module re-exports from the canonical category_taxonomy module
for backwards compatibility. All category definitions are now in:
    src/business/category_taxonomy.py

DO NOT add category definitions here - update the taxonomy instead.
"""

# Import everything from the canonical taxonomy
from src.business.category_taxonomy import (
    # Main data
    CATEGORY_TAXONOMY as FLEET_CATEGORIES,
    CATEGORY_ALIASES,

    # Core functions
    normalize_category_key,
    get_category,
    get_category_or_default,
    iter_categories,

    # Category getters
    get_categories_by_tier,
    get_fleet_categories,
    get_swath_categories,
    get_category_by_tier,  # Backwards compat alias

    # OSM/tag functions
    get_osm_tags_for_category,
    get_all_osm_tags,
    get_keywords_for_category,
    detect_category_from_tags,
    detect_category_from_name,

    # Vehicle estimation
    estimate_vehicles,
    estimate_vehicles_by_category,  # Backwards compat alias

    # UI helpers
    get_ui_categories,
)

# Re-export for backwards compatibility
__all__ = [
    'FLEET_CATEGORIES',
    'CATEGORY_ALIASES',
    'normalize_category_key',
    'get_category',
    'get_category_or_default',
    'iter_categories',
    'get_categories_by_tier',
    'get_fleet_categories',
    'get_swath_categories',
    'get_category_by_tier',
    'get_osm_tags_for_category',
    'get_all_osm_tags',
    'get_keywords_for_category',
    'detect_category_from_tags',
    'detect_category_from_name',
    'estimate_vehicles',
    'estimate_vehicles_by_category',
    'get_ui_categories',
]
