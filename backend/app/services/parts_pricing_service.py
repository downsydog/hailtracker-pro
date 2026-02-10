"""Parts Pricing Service - Stage 5S

Read-only pricing context for PartRequests.
Provides estimated price ranges for decision support WITHOUT:
- Creating orders
- Creating POs
- Auto-selecting vendors
- Any database writes

This is CONTEXT ONLY, not procurement.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy import func

from app.models.tenant import PartRequest


class PricingSource(str, Enum):
    """Source of pricing estimate."""
    HISTORICAL = 'historical'
    VENDOR_TABLE = 'vendor_table'
    MANUAL = 'manual'
    UNKNOWN = 'unknown'


class PriceConfidence(str, Enum):
    """Confidence level of pricing estimate."""
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


# Static vendor reference table (placeholder for future vendor API integration)
# Maps common part keywords to typical price ranges
VENDOR_REFERENCE_TABLE: Dict[str, Dict[str, float]] = {
    # Clips and fasteners
    'clip': {'low': 2.0, 'typical': 5.0, 'high': 15.0},
    'clips': {'low': 5.0, 'typical': 12.0, 'high': 30.0},
    'fastener': {'low': 3.0, 'typical': 8.0, 'high': 20.0},
    'retainer': {'low': 3.0, 'typical': 10.0, 'high': 25.0},
    'rivet': {'low': 2.0, 'typical': 6.0, 'high': 15.0},
    'grommet': {'low': 2.0, 'typical': 5.0, 'high': 12.0},

    # Trim and molding
    'molding': {'low': 25.0, 'typical': 75.0, 'high': 200.0},
    'moulding': {'low': 25.0, 'typical': 75.0, 'high': 200.0},
    'trim': {'low': 15.0, 'typical': 45.0, 'high': 120.0},
    'emblem': {'low': 20.0, 'typical': 50.0, 'high': 150.0},
    'badge': {'low': 15.0, 'typical': 40.0, 'high': 100.0},

    # Seals and weatherstripping
    'seal': {'low': 20.0, 'typical': 60.0, 'high': 180.0},
    'gasket': {'low': 15.0, 'typical': 45.0, 'high': 120.0},
    'weatherstrip': {'low': 30.0, 'typical': 80.0, 'high': 200.0},

    # Exterior components
    'antenna': {'low': 25.0, 'typical': 65.0, 'high': 150.0},
    'mirror': {'low': 50.0, 'typical': 150.0, 'high': 400.0},
    'handle': {'low': 30.0, 'typical': 80.0, 'high': 200.0},
    'cap': {'low': 10.0, 'typical': 30.0, 'high': 80.0},
    'cover': {'low': 15.0, 'typical': 45.0, 'high': 120.0},

    # Generic fallbacks
    'part': {'low': 20.0, 'typical': 60.0, 'high': 150.0},
    'parts': {'low': 30.0, 'typical': 90.0, 'high': 250.0},
}


def _normalize_text(text: str) -> str:
    """Normalize text for matching."""
    return text.lower().strip().replace('-', ' ').replace('_', ' ')


def _get_historical_pricing(
    tenant_id: int,
    part_number: Optional[str],
    description: str,
    exclude_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Get historical pricing from past PartRequests with approved amounts.

    Uses same-tenant data only for tenant safety.
    Returns None if no historical data found.
    """
    # Build base query - only look at requests with approved amounts
    query = PartRequest.query.filter(
        PartRequest.tenant_id == tenant_id,
        PartRequest.approved_amount.isnot(None),
        PartRequest.approved_amount > 0,
    )

    # Exclude current request if provided
    if exclude_id:
        query = query.filter(PartRequest.id != exclude_id)

    # Try to match by part number first (most reliable)
    if part_number:
        part_number_matches = query.filter(
            PartRequest.part_number == part_number
        ).all()

        if len(part_number_matches) >= 2:
            amounts = [float(r.approved_amount) for r in part_number_matches]
            return {
                'low': min(amounts),
                'typical': sum(amounts) / len(amounts),
                'high': max(amounts),
                'match_count': len(amounts),
                'match_type': 'part_number',
            }

    # Try description matching (fuzzy)
    normalized_desc = _normalize_text(description)
    desc_words = set(normalized_desc.split())

    # Get all historical requests for similarity matching
    all_historical = query.all()

    similar_amounts = []
    for req in all_historical:
        req_desc = _normalize_text(req.description)
        req_words = set(req_desc.split())

        # Calculate word overlap
        overlap = len(desc_words & req_words)
        if overlap >= 2 or (overlap >= 1 and len(desc_words) <= 2):
            similar_amounts.append(float(req.approved_amount))

    if len(similar_amounts) >= 2:
        return {
            'low': min(similar_amounts),
            'typical': sum(similar_amounts) / len(similar_amounts),
            'high': max(similar_amounts),
            'match_count': len(similar_amounts),
            'match_type': 'description',
        }

    return None


def _get_vendor_table_pricing(description: str) -> Optional[Dict[str, Any]]:
    """
    Get pricing from static vendor reference table.

    Matches keywords in description against known part types.
    """
    normalized = _normalize_text(description)

    # Check each keyword in the reference table
    for keyword, prices in VENDOR_REFERENCE_TABLE.items():
        if keyword in normalized:
            return {
                'low': prices['low'],
                'typical': prices['typical'],
                'high': prices['high'],
                'matched_keyword': keyword,
            }

    return None


def get_price_preview(
    part_request: PartRequest,
    tenant_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get estimated price preview for a single PartRequest.

    This is READ-ONLY - no database writes occur.

    Returns:
        {
            'low_estimate': number | None,
            'typical_estimate': number | None,
            'high_estimate': number | None,
            'source': PricingSource value,
            'confidence': PriceConfidence value,
            'notes': string | None
        }
    """
    # Use provided tenant_id or get from request
    tid = tenant_id or part_request.tenant_id

    # If request already has an approved amount, use it
    if part_request.approved_amount and float(part_request.approved_amount) > 0:
        amount = float(part_request.approved_amount)
        return {
            'low_estimate': amount,
            'typical_estimate': amount,
            'high_estimate': amount,
            'source': PricingSource.MANUAL.value,
            'confidence': PriceConfidence.HIGH.value,
            'notes': 'Approved amount on record',
        }

    # Try historical pricing first
    historical = _get_historical_pricing(
        tenant_id=tid,
        part_number=part_request.part_number,
        description=part_request.description,
        exclude_id=part_request.id,
    )

    if historical:
        match_type = historical.get('match_type', 'unknown')
        match_count = historical.get('match_count', 0)

        return {
            'low_estimate': round(historical['low'], 2),
            'typical_estimate': round(historical['typical'], 2),
            'high_estimate': round(historical['high'], 2),
            'source': PricingSource.HISTORICAL.value,
            'confidence': PriceConfidence.HIGH.value if match_count >= 3 else PriceConfidence.MEDIUM.value,
            'notes': f'Based on {match_count} prior {"part#" if match_type == "part_number" else "similar"} requests',
        }

    # Try vendor table
    vendor_pricing = _get_vendor_table_pricing(part_request.description)

    if vendor_pricing:
        # Multiply by quantity
        qty = part_request.qty or 1
        return {
            'low_estimate': round(vendor_pricing['low'] * qty, 2),
            'typical_estimate': round(vendor_pricing['typical'] * qty, 2),
            'high_estimate': round(vendor_pricing['high'] * qty, 2),
            'source': PricingSource.VENDOR_TABLE.value,
            'confidence': PriceConfidence.MEDIUM.value,
            'notes': f'Reference estimate for {vendor_pricing["matched_keyword"]}',
        }

    # Unknown - no pricing data available
    return {
        'low_estimate': None,
        'typical_estimate': None,
        'high_estimate': None,
        'source': PricingSource.UNKNOWN.value,
        'confidence': PriceConfidence.LOW.value,
        'notes': 'No pricing data available',
    }


def get_bulk_price_previews(
    part_requests: List[PartRequest],
    tenant_id: Optional[int] = None
) -> Dict[int, Dict[str, Any]]:
    """
    Get price previews for multiple PartRequests.

    This is READ-ONLY - no database writes occur.

    Args:
        part_requests: List of PartRequest objects
        tenant_id: Optional tenant ID override

    Returns:
        Dict mapping part_request.id -> price preview dict
    """
    result = {}

    for req in part_requests:
        tid = tenant_id or req.tenant_id
        result[req.id] = get_price_preview(req, tid)

    return result


def get_total_exposure(
    part_requests: List[PartRequest],
    tenant_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate total estimated parts exposure.

    Uses typical_estimate where available.

    Returns:
        {
            'total_typical': number,
            'total_low': number,
            'total_high': number,
            'count_priced': number,
            'count_unknown': number,
        }
    """
    previews = get_bulk_price_previews(part_requests, tenant_id)

    total_typical = 0.0
    total_low = 0.0
    total_high = 0.0
    count_priced = 0
    count_unknown = 0

    for preview in previews.values():
        if preview.get('typical_estimate') is not None:
            total_typical += preview['typical_estimate']
            total_low += preview.get('low_estimate') or preview['typical_estimate']
            total_high += preview.get('high_estimate') or preview['typical_estimate']
            count_priced += 1
        else:
            count_unknown += 1

    return {
        'total_typical': round(total_typical, 2),
        'total_low': round(total_low, 2),
        'total_high': round(total_high, 2),
        'count_priced': count_priced,
        'count_unknown': count_unknown,
    }
