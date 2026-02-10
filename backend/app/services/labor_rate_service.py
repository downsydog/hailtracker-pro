"""Labor Rate Service - configurable R&I labor rates by region.

Stage 6E: Tenant Labor Rate Engine.
Resolves labor rates based on tenant configuration and estimate location.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, date
from app.extensions import db


# Validation constants
MAX_RATE = 500.0
MIN_RATE = 0.0
MAX_RULES = 200
MAX_ZIP_PREFIX_LEN = 5


def validate_labor_rates_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate a labor rates configuration.

    Returns list of validation errors (empty if valid).
    """
    errors = []

    # Validate default_ri_rate
    default_rate = config.get('default_ri_rate')
    if default_rate is not None:
        try:
            rate = float(default_rate)
            if rate < MIN_RATE or rate > MAX_RATE:
                errors.append(f'default_ri_rate must be between {MIN_RATE} and {MAX_RATE}')
        except (TypeError, ValueError):
            errors.append('default_ri_rate must be a number')

    # Validate currency
    currency = config.get('currency', 'USD')
    if currency not in ['USD', 'CAD']:
        errors.append('currency must be USD or CAD')

    # Validate rules
    rules = config.get('rules', [])
    if not isinstance(rules, list):
        errors.append('rules must be a list')
    elif len(rules) > MAX_RULES:
        errors.append(f'rules list cannot exceed {MAX_RULES} entries')
    else:
        for i, rule in enumerate(rules):
            rule_errors = _validate_rule(rule, i)
            errors.extend(rule_errors)

    return errors


def _validate_rule(rule: Dict[str, Any], index: int) -> List[str]:
    """Validate a single labor rate rule."""
    errors = []
    prefix = f'rules[{index}]'

    # Required fields
    if not rule.get('id'):
        errors.append(f'{prefix}: id is required')
    if not rule.get('name'):
        errors.append(f'{prefix}: name is required')

    # Validate ri_rate
    ri_rate = rule.get('ri_rate')
    if ri_rate is None:
        errors.append(f'{prefix}: ri_rate is required')
    else:
        try:
            rate = float(ri_rate)
            if rate < MIN_RATE or rate > MAX_RATE:
                errors.append(f'{prefix}: ri_rate must be between {MIN_RATE} and {MAX_RATE}')
        except (TypeError, ValueError):
            errors.append(f'{prefix}: ri_rate must be a number')

    # Validate zip_prefixes
    zip_prefixes = rule.get('zip_prefixes', [])
    if zip_prefixes:
        if not isinstance(zip_prefixes, list):
            errors.append(f'{prefix}: zip_prefixes must be a list')
        else:
            for j, zp in enumerate(zip_prefixes):
                if not isinstance(zp, str):
                    errors.append(f'{prefix}.zip_prefixes[{j}]: must be a string')
                elif not zp.isdigit():
                    errors.append(f'{prefix}.zip_prefixes[{j}]: must contain only digits')
                elif len(zp) > MAX_ZIP_PREFIX_LEN:
                    errors.append(f'{prefix}.zip_prefixes[{j}]: max length is {MAX_ZIP_PREFIX_LEN}')

    # Validate date range
    effective_from = rule.get('effective_from')
    effective_to = rule.get('effective_to')
    if effective_from:
        try:
            datetime.strptime(effective_from, '%Y-%m-%d')
        except ValueError:
            errors.append(f'{prefix}: effective_from must be YYYY-MM-DD format')
    if effective_to:
        try:
            datetime.strptime(effective_to, '%Y-%m-%d')
        except ValueError:
            errors.append(f'{prefix}: effective_to must be YYYY-MM-DD format')

    return errors


def get_labor_rate_config(tenant_id: int) -> Dict[str, Any]:
    """
    Get labor rate configuration for a tenant.

    Returns validated config with defaults applied.
    """
    from app.models.master.tenant import Tenant

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return Tenant.DEFAULT_LABOR_RATES.copy()

    return tenant.get_labor_rates_config()


def resolve_ri_rate_for_estimate(estimate) -> Dict[str, Any]:
    """
    Resolve the R&I labor rate for an estimate.

    Resolution order:
    1. If estimate has explicit override (ri_labor_rate set, source='override'), use it
    2. Try to match rules by specificity: zip > state > country
    3. Fall back to default_ri_rate

    Returns:
        {
            'rate': float,
            'source': 'override' | 'rule' | 'default',
            'rule_id': str | None,
            'rule_name': str | None,
            'reason': str
        }
    """
    from app.models.master.tenant import Tenant

    # Check for explicit override on estimate
    if (estimate.ri_labor_rate is not None and
        estimate.ri_labor_rate_source == 'override'):
        return {
            'rate': float(estimate.ri_labor_rate),
            'source': 'override',
            'rule_id': None,
            'rule_name': None,
            'reason': 'Manual override set on estimate'
        }

    # Get tenant config
    tenant = Tenant.query.get(estimate.tenant_id)
    if not tenant:
        return {
            'rate': 85.0,
            'source': 'default',
            'rule_id': None,
            'rule_name': None,
            'reason': 'Tenant not found, using system default'
        }

    config = tenant.get_labor_rates_config()
    default_rate = float(config.get('default_ri_rate', 85.0))
    rules = config.get('rules', [])

    if not rules:
        return {
            'rate': default_rate,
            'source': 'default',
            'rule_id': None,
            'rule_name': None,
            'reason': 'No rules configured'
        }

    # Extract location info from estimate
    # Try multiple fields for zip code
    estimate_zip = None
    estimate_state = None
    estimate_country = 'US'  # Default to US

    # Check if estimate has address fields
    if hasattr(estimate, 'zip_code') and estimate.zip_code:
        estimate_zip = str(estimate.zip_code)
    elif hasattr(estimate, 'customer_zip') and estimate.customer_zip:
        estimate_zip = str(estimate.customer_zip)

    if hasattr(estimate, 'state') and estimate.state:
        estimate_state = estimate.state.upper()
    elif hasattr(estimate, 'customer_state') and estimate.customer_state:
        estimate_state = estimate.customer_state.upper()

    # Determine reference date for effective date check
    reference_date = None
    if hasattr(estimate, 'date_of_loss') and estimate.date_of_loss:
        reference_date = estimate.date_of_loss
    elif estimate.created_at:
        reference_date = estimate.created_at.date() if isinstance(estimate.created_at, datetime) else estimate.created_at
    else:
        reference_date = date.today()

    # Find best matching rule
    best_match = None
    best_specificity = -1

    for rule in rules:
        # Check effective date range
        if not _is_rule_effective(rule, reference_date):
            continue

        # Calculate specificity score
        specificity = _calculate_rule_specificity(rule, estimate_zip, estimate_state, estimate_country)

        if specificity > best_specificity:
            best_specificity = specificity
            best_match = rule

    if best_match:
        return {
            'rate': float(best_match['ri_rate']),
            'source': 'rule',
            'rule_id': best_match.get('id'),
            'rule_name': best_match.get('name'),
            'reason': f"Matched rule: {best_match.get('name')}"
        }

    return {
        'rate': default_rate,
        'source': 'default',
        'rule_id': None,
        'rule_name': None,
        'reason': 'No matching rules found'
    }


def _is_rule_effective(rule: Dict[str, Any], reference_date) -> bool:
    """Check if a rule is effective for the given date."""
    effective_from = rule.get('effective_from')
    effective_to = rule.get('effective_to')

    if effective_from:
        try:
            from_date = datetime.strptime(effective_from, '%Y-%m-%d').date()
            if reference_date < from_date:
                return False
        except ValueError:
            pass

    if effective_to:
        try:
            to_date = datetime.strptime(effective_to, '%Y-%m-%d').date()
            if reference_date > to_date:
                return False
        except ValueError:
            pass

    return True


def _calculate_rule_specificity(
    rule: Dict[str, Any],
    estimate_zip: Optional[str],
    estimate_state: Optional[str],
    estimate_country: str
) -> int:
    """
    Calculate specificity score for a rule match.

    Higher score = more specific match.
    Returns -1 if rule doesn't match at all.

    Scoring:
    - ZIP prefix match: 100 + (prefix length * 10)
    - State match: 50
    - Country match: 10
    - City keyword match: 5 (bonus)
    """
    score = 0
    has_any_match = False

    # Check ZIP prefix match (highest priority)
    zip_prefixes = rule.get('zip_prefixes', [])
    if zip_prefixes and estimate_zip:
        for prefix in zip_prefixes:
            if estimate_zip.startswith(prefix):
                score = max(score, 100 + len(prefix) * 10)
                has_any_match = True
                break

    # Check state match
    rule_state = rule.get('state')
    if rule_state and estimate_state:
        if rule_state.upper() == estimate_state:
            if score == 0:  # Only set if no ZIP match
                score = 50
            has_any_match = True

    # Check country match
    rule_country = rule.get('country', 'US')
    if rule_country.upper() == estimate_country.upper():
        if score == 0:  # Only set if no ZIP or state match
            score = 10
        has_any_match = True

    # If rule has no location criteria, it matches everything at lowest priority
    if not zip_prefixes and not rule_state and not rule.get('country'):
        has_any_match = True
        score = 1

    return score if has_any_match else -1


def preview_rate_resolution(
    tenant_id: int,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    reference_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Preview rate resolution for testing.

    Creates a mock estimate-like object and runs resolution.
    """
    from app.models.master.tenant import Tenant

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return {
            'rate': 85.0,
            'source': 'default',
            'rule_id': None,
            'rule_name': None,
            'reason': 'Tenant not found'
        }

    config = tenant.get_labor_rates_config()
    default_rate = float(config.get('default_ri_rate', 85.0))
    rules = config.get('rules', [])

    if not rules:
        return {
            'rate': default_rate,
            'source': 'default',
            'rule_id': None,
            'rule_name': None,
            'reason': 'No rules configured'
        }

    # Parse reference date
    ref_date = date.today()
    if reference_date:
        try:
            ref_date = datetime.strptime(reference_date, '%Y-%m-%d').date()
        except ValueError:
            pass

    estimate_zip = zip_code
    estimate_state = state.upper() if state else None
    estimate_country = 'US'

    # Find best matching rule
    best_match = None
    best_specificity = -1

    for rule in rules:
        if not _is_rule_effective(rule, ref_date):
            continue

        specificity = _calculate_rule_specificity(rule, estimate_zip, estimate_state, estimate_country)

        if specificity > best_specificity:
            best_specificity = specificity
            best_match = rule

    if best_match:
        return {
            'rate': float(best_match['ri_rate']),
            'source': 'rule',
            'rule_id': best_match.get('id'),
            'rule_name': best_match.get('name'),
            'reason': f"Matched rule: {best_match.get('name')}"
        }

    return {
        'rate': default_rate,
        'source': 'default',
        'rule_id': None,
        'rule_name': None,
        'reason': 'No matching rules found'
    }


def set_estimate_ri_rate_override(
    estimate_id: int,
    tenant_id: int,
    rate: Optional[float],
    user_id: int
) -> Dict[str, Any]:
    """
    Set or clear an R&I rate override on an estimate.

    Args:
        estimate_id: The estimate ID
        tenant_id: The tenant ID (for safety)
        rate: The override rate, or None to clear
        user_id: The user making the change

    Returns:
        {
            'success': bool,
            'estimate_id': int,
            'old_rate': float | None,
            'new_rate': float | None,
            'source': str
        }
    """
    from app.models.tenant import PDREstimate, EstimateActivity

    estimate = PDREstimate.query.filter_by(
        id=estimate_id,
        tenant_id=tenant_id
    ).first()

    if not estimate:
        raise ValueError('Estimate not found')

    old_rate = float(estimate.ri_labor_rate) if estimate.ri_labor_rate else None
    old_source = estimate.ri_labor_rate_source
    old_rule_id = estimate.ri_labor_rate_rule_id

    if rate is not None:
        # Validate rate
        if rate < MIN_RATE or rate > MAX_RATE:
            raise ValueError(f'Rate must be between {MIN_RATE} and {MAX_RATE}')

        # Set override
        estimate.ri_labor_rate = rate
        estimate.ri_labor_rate_source = 'override'
        estimate.ri_labor_rate_rule_id = None

        # Log activity
        activity = EstimateActivity(
            estimate_id=estimate_id,
            tenant_id=tenant_id,
            activity_type='labor_rate_override_set',
            user_id=user_id,
            activity_data={
                'old_rate': old_rate,
                'new_rate': rate,
                'old_source': old_source,
                'new_source': 'override'
            }
        )
        db.session.add(activity)
    else:
        # Clear override - re-resolve rate
        resolved = resolve_ri_rate_for_estimate(estimate)
        estimate.ri_labor_rate = resolved['rate']
        estimate.ri_labor_rate_source = resolved['source']
        estimate.ri_labor_rate_rule_id = resolved.get('rule_id')

        # Log activity
        activity = EstimateActivity(
            estimate_id=estimate_id,
            tenant_id=tenant_id,
            activity_type='labor_rate_override_cleared',
            user_id=user_id,
            activity_data={
                'old_rate': old_rate,
                'new_rate': resolved['rate'],
                'old_source': old_source,
                'new_source': resolved['source'],
                'rule_id': resolved.get('rule_id')
            }
        )
        db.session.add(activity)

    db.session.commit()

    return {
        'success': True,
        'estimate_id': estimate_id,
        'old_rate': old_rate,
        'new_rate': float(estimate.ri_labor_rate) if estimate.ri_labor_rate else None,
        'source': estimate.ri_labor_rate_source
    }
