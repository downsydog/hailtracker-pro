"""
PDR Estimating Module
Zone-based dent pricing with panel difficulty and material modifiers.
"""

from .pricing_engine import (
    PricingEngine,
    calculate_estimate_total,
    get_tenant_pricing_config,
    create_pricing_profile,
    get_default_config,
    get_ri_library_items,
    get_ri_operation,
    get_vehicle_tier,
    DEFAULT_PRICING_CONFIG,
    TIER_MULTIPLIERS
)

from .estimate_routes import pdr_estimates_bp, work_orders_bp

from .supplement_generator import (
    generate_supplement_narrative,
    generate_discovery_narrative,
    generate_summary_narrative,
    get_discovery_template,
    list_discovery_types,
    DISCOVERY_TEMPLATES
)

from .pdf_generator import (
    generate_estimate_pdf,
    generate_supplement_pdf,
    generate_invoice_pdf
)

__all__ = [
    # Pricing Engine
    'PricingEngine',
    'calculate_estimate_total',
    'get_tenant_pricing_config',
    'create_pricing_profile',
    'get_default_config',
    'get_ri_library_items',
    'get_ri_operation',
    'get_vehicle_tier',
    'DEFAULT_PRICING_CONFIG',
    'TIER_MULTIPLIERS',
    # Routes
    'pdr_estimates_bp',
    # Supplement Generator
    'generate_supplement_narrative',
    'generate_discovery_narrative',
    'generate_summary_narrative',
    'get_discovery_template',
    'list_discovery_types',
    'DISCOVERY_TEMPLATES',
    # PDF Generator
    'generate_estimate_pdf',
    'generate_supplement_pdf',
    'generate_invoice_pdf'
]
