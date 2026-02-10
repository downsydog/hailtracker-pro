"""
Supplement Diff Engine

Computes structured differences between a baseline estimate version
and the current estimate state for supplement creation.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal


def compute_supplement_diff(baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute the diff between baseline and current estimate states.

    Args:
        baseline: Snapshot from EstimateVersion.snapshot_json
        current: Current estimate data dict

    Returns:
        Structured diff with:
        - panels: list of panel changes
        - totals: before/after/delta for each total category
        - ri_ops: list of R&I operation changes
        - summary: quick stats
    """
    diff = {
        'panels': compute_panel_diff(
            baseline.get('panels', []),
            current.get('panels', [])
        ),
        'totals': compute_totals_diff(baseline, current),
        'ri_ops': compute_ri_ops_diff(
            baseline.get('ri_ops', []),
            current.get('ri_ops', [])
        ),
        'summary': {}
    }

    # Compute summary stats
    panel_changes = diff['panels']
    diff['summary'] = {
        'panels_added': len([p for p in panel_changes if p['change_type'] == 'added']),
        'panels_modified': len([p for p in panel_changes if p['change_type'] == 'modified']),
        'panels_removed': len([p for p in panel_changes if p['change_type'] == 'removed']),
        'total_delta': diff['totals'].get('grand_total', {}).get('delta', 0)
    }

    return diff


def compute_panel_diff(baseline_panels: List[Dict], current_panels: List[Dict]) -> List[Dict]:
    """
    Compare panels between baseline and current state.

    Returns list of panel changes with:
    - panel_name
    - change_type: added | modified | removed | unchanged
    - before: baseline values (if existed)
    - after: current values (if exists)
    - deltas: specific field changes
    """
    changes = []

    # Index panels by name
    baseline_by_name = {p.get('panel_name'): p for p in baseline_panels}
    current_by_name = {p.get('panel_name'): p for p in current_panels}

    all_panel_names = set(baseline_by_name.keys()) | set(current_by_name.keys())

    for panel_name in sorted(all_panel_names):
        before = baseline_by_name.get(panel_name)
        after = current_by_name.get(panel_name)

        if before and after:
            # Panel exists in both - check for modifications
            deltas = compute_panel_field_deltas(before, after)
            if deltas:
                changes.append({
                    'panel_name': panel_name,
                    'change_type': 'modified',
                    'before': before,
                    'after': after,
                    'deltas': deltas
                })
        elif after and not before:
            # Panel added
            changes.append({
                'panel_name': panel_name,
                'change_type': 'added',
                'before': None,
                'after': after,
                'deltas': None
            })
        elif before and not after:
            # Panel removed
            changes.append({
                'panel_name': panel_name,
                'change_type': 'removed',
                'before': before,
                'after': None,
                'deltas': None
            })

    return changes


def compute_panel_field_deltas(before: Dict, after: Dict) -> Optional[Dict]:
    """
    Compute field-level changes between two panel states.

    Tracked fields:
    - total_dent_count / count_range
    - majority_size / dent_size
    - depth
    - zone
    - oversized_count
    - is_aluminum, is_hss, requires_glue_pull, is_double_metal
    - panel_total / total_price
    """
    deltas = {}

    # Fields to compare with their display names
    fields = [
        ('total_dent_count', 'Dent Count'),
        ('majority_size', 'Dent Size'),
        ('depth', 'Depth'),
        ('zone', 'Zone'),
        ('oversized_count', 'Oversized'),
        ('is_aluminum', 'Aluminum'),
        ('is_hss', 'HSS'),
        ('requires_glue_pull', 'Glue Pull'),
        ('is_double_metal', 'Double Metal'),
        ('panel_total', 'Panel Total'),
    ]

    for field, display_name in fields:
        before_val = before.get(field)
        after_val = after.get(field)

        # Normalize numeric types
        if isinstance(before_val, (int, float, Decimal)):
            before_val = float(before_val) if before_val else 0
        if isinstance(after_val, (int, float, Decimal)):
            after_val = float(after_val) if after_val else 0

        if before_val != after_val:
            delta_val = None
            if isinstance(before_val, (int, float)) and isinstance(after_val, (int, float)):
                delta_val = after_val - before_val

            deltas[field] = {
                'display_name': display_name,
                'before': before_val,
                'after': after_val,
                'delta': delta_val
            }

    return deltas if deltas else None


def compute_totals_diff(baseline: Dict, current: Dict) -> Dict:
    """
    Compare totals between baseline and current.

    Returns dict with before/after/delta for each total category.
    """
    totals_diff = {}

    # Total fields to track
    total_fields = [
        ('labor_total', 'Labor Total'),
        ('ri_total', 'R&I Total'),
        ('parts_total', 'Parts Total'),
        ('total_price', 'Grand Total'),
        ('grand_total', 'Grand Total'),  # Alternate name
    ]

    for field, display_name in total_fields:
        before_val = baseline.get(field, 0) or 0
        after_val = current.get(field, 0) or 0

        if isinstance(before_val, (str, Decimal)):
            before_val = float(before_val) if before_val else 0
        if isinstance(after_val, (str, Decimal)):
            after_val = float(after_val) if after_val else 0

        if before_val != after_val or field in ('total_price', 'grand_total'):
            totals_diff[field] = {
                'display_name': display_name,
                'before': before_val,
                'after': after_val,
                'delta': after_val - before_val
            }

    return totals_diff


def compute_ri_ops_diff(baseline_ops: List[Dict], current_ops: List[Dict]) -> List[Dict]:
    """
    Compare R&I operations between baseline and current.

    Returns list of operation changes.
    """
    changes = []

    # Index by operation name/code
    baseline_by_name = {op.get('name') or op.get('code'): op for op in baseline_ops}
    current_by_name = {op.get('name') or op.get('code'): op for op in current_ops}

    all_op_names = set(baseline_by_name.keys()) | set(current_by_name.keys())

    for op_name in sorted(all_op_names):
        if not op_name:
            continue

        before = baseline_by_name.get(op_name)
        after = current_by_name.get(op_name)

        if before and after:
            # Check for changes
            before_price = float(before.get('price', 0) or 0)
            after_price = float(after.get('price', 0) or 0)
            before_hours = float(before.get('hours', 0) or 0)
            after_hours = float(after.get('hours', 0) or 0)

            if before_price != after_price or before_hours != after_hours:
                changes.append({
                    'operation': op_name,
                    'change_type': 'modified',
                    'before': before,
                    'after': after,
                    'price_delta': after_price - before_price,
                    'hours_delta': after_hours - before_hours
                })
        elif after and not before:
            changes.append({
                'operation': op_name,
                'change_type': 'added',
                'before': None,
                'after': after,
                'price_delta': float(after.get('price', 0) or 0),
                'hours_delta': float(after.get('hours', 0) or 0)
            })
        elif before and not after:
            changes.append({
                'operation': op_name,
                'change_type': 'removed',
                'before': before,
                'after': None,
                'price_delta': -float(before.get('price', 0) or 0),
                'hours_delta': -float(before.get('hours', 0) or 0)
            })

    return changes


def generate_supplement_narrative(
    diff: Dict[str, Any],
    discovery_type: str,
    estimate_data: Dict[str, Any]
) -> str:
    """
    Generate a narrative explanation for the supplement.

    Args:
        diff: The computed diff
        discovery_type: Type of discovery (hidden_damage, additional_panels, etc.)
        estimate_data: Current estimate data for context

    Returns:
        Narrative text suitable for supplement PDF
    """
    vehicle = f"{estimate_data.get('vehicle_year', '')} {estimate_data.get('vehicle_make', '')} {estimate_data.get('vehicle_model', '')}".strip()

    # Discovery type descriptions
    discovery_descriptions = {
        'hidden_damage': 'Upon further inspection and disassembly, additional damage was discovered that was not visible during the initial estimate.',
        'additional_panels': 'Additional panels were found to have hail damage that was not identified in the original estimate.',
        'severity_increase': 'The severity of damage on previously identified panels was found to be greater than originally assessed.',
        'access_limitation': 'Access limitations required additional R&I operations to properly repair the identified damage.',
        'part_condition': 'Part condition upon removal revealed damage that necessitates replacement rather than repair.',
        'corrosion': 'Corrosion was discovered during the repair process that must be addressed.',
        'prior_damage': 'Pre-existing damage was identified that affects the current repair.',
        'manufacturer_spec': 'Manufacturer specifications require additional procedures for proper repair.',
        'other': 'Additional work is required based on findings during the repair process.'
    }

    narrative_parts = []

    # Opening
    narrative_parts.append(f"SUPPLEMENT REQUEST - {vehicle}")
    narrative_parts.append("")
    narrative_parts.append("DISCOVERY:")
    narrative_parts.append(discovery_descriptions.get(discovery_type, discovery_descriptions['other']))
    narrative_parts.append("")

    # Panel changes
    summary = diff.get('summary', {})
    if summary.get('panels_added', 0) > 0 or summary.get('panels_modified', 0) > 0:
        narrative_parts.append("PANEL CHANGES:")

        for panel in diff.get('panels', []):
            panel_name = panel.get('panel_name', 'Unknown').replace('_', ' ').title()

            if panel['change_type'] == 'added':
                after = panel.get('after', {})
                count = after.get('total_dent_count', 'N/A')
                size = after.get('majority_size', 'N/A')
                price = after.get('panel_total', 0)
                narrative_parts.append(
                    f"- {panel_name}: ADDED - {count} dents, {size} size, ${price:.2f}"
                )
            elif panel['change_type'] == 'modified':
                deltas = panel.get('deltas', {})
                changes = []
                if 'total_dent_count' in deltas:
                    d = deltas['total_dent_count']
                    changes.append(f"count {d['before']} -> {d['after']}")
                if 'majority_size' in deltas:
                    d = deltas['majority_size']
                    changes.append(f"size {d['before']} -> {d['after']}")
                if 'panel_total' in deltas:
                    d = deltas['panel_total']
                    changes.append(f"${d['before']:.2f} -> ${d['after']:.2f}")

                narrative_parts.append(f"- {panel_name}: MODIFIED - {', '.join(changes)}")

        narrative_parts.append("")

    # Totals
    totals = diff.get('totals', {})
    grand_total = totals.get('total_price') or totals.get('grand_total')
    if grand_total:
        narrative_parts.append("FINANCIAL IMPACT:")
        narrative_parts.append(f"- Original Total: ${grand_total['before']:.2f}")
        narrative_parts.append(f"- Revised Total: ${grand_total['after']:.2f}")
        delta = grand_total['delta']
        sign = '+' if delta > 0 else ''
        narrative_parts.append(f"- Supplement Amount: {sign}${delta:.2f}")
        narrative_parts.append("")

    # Closing
    narrative_parts.append("This supplement is submitted for review and approval. ")
    narrative_parts.append("Photo documentation of the additional damage is available upon request.")

    return '\n'.join(narrative_parts)
