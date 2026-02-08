"""
PDR Supplement Narrative Generator
Auto-generates insurance-friendly supplement narratives from discovery events.
"""

from typing import Dict, List
from datetime import datetime


def generate_supplement_narrative(
    estimate_id: int,
    original_total: float,
    discoveries: List[Dict],
    vehicle_info: Dict = None
) -> Dict:
    """
    Generate complete supplement package with insurance-friendly narrative.

    Args:
        estimate_id: Estimate ID
        original_total: Original estimate total
        discoveries: List of discovery event dicts
        vehicle_info: Optional vehicle info dict

    Returns:
        Dict with narrative, line items, totals, and evidence chain
    """
    narratives = []
    line_items = []
    evidence_chain = []
    total_additional_cost = 0
    total_additional_time = 0

    for disc in discoveries:
        # Build narrative for each discovery
        narrative = generate_discovery_narrative(disc)
        narratives.append(narrative)

        # Build line item
        line_item = {
            "description": disc.get('type', 'Additional work').replace('_', ' ').title(),
            "details": disc.get('description', ''),
            "time_hours": float(disc.get('additional_time_hours', 0)),
            "cost": float(disc.get('additional_cost', 0)),
            "discovery_id": disc.get('id')
        }
        line_items.append(line_item)

        total_additional_cost += line_item['cost']
        total_additional_time += line_item['time_hours']

        # Build evidence chain
        evidence = {
            "discovery_id": disc.get('id'),
            "type": disc.get('type'),
            "timestamp": disc.get('created_at'),
            "photo_url": disc.get('photo_url'),
            "panel": disc.get('panel_name'),
            "dent_id": disc.get('dent_id')
        }
        evidence_chain.append(evidence)

    # Generate summary narrative
    summary = generate_summary_narrative(
        discoveries,
        total_additional_cost,
        total_additional_time,
        vehicle_info
    )

    return {
        "estimate_id": estimate_id,
        "supplement_date": datetime.now().isoformat(),
        "original_total": original_total,
        "additional_cost": total_additional_cost,
        "additional_time_hours": total_additional_time,
        "new_total": original_total + total_additional_cost,
        "summary_narrative": summary,
        "item_narratives": narratives,
        "line_items": line_items,
        "evidence_chain": evidence_chain,
        "discovery_count": len(discoveries)
    }


def generate_discovery_narrative(discovery: Dict) -> str:
    """
    Generate insurance-friendly narrative for a single discovery.

    Template:
    "During repair of the [size] [zone] dent on the [panel], technician discovered
    [discovery_type] was required for proper tool access. This condition was not
    visible during the initial estimate. Additional time: [hours] hours.
    Additional cost: $[amount]."
    """
    disc_type = discovery.get('type', 'additional_work').replace('_', ' ')
    panel = discovery.get('panel_name', 'panel')
    zone = discovery.get('zone', '')
    size = discovery.get('size', '')
    description = discovery.get('description', '')
    time_hours = discovery.get('additional_time_hours', 0)
    cost = discovery.get('additional_cost', 0)

    # Build dent reference
    dent_ref = ""
    if size and zone:
        dent_ref = f"the {size} {zone} dent on the {panel}"
    elif zone:
        dent_ref = f"the {zone} area of the {panel}"
    else:
        dent_ref = f"the {panel}"

    # Build main narrative
    narrative = f"During repair of {dent_ref}, technician discovered that {disc_type}"

    if description:
        narrative += f" ({description})"

    narrative += " was required for proper tool access. "
    narrative += "This condition was not visible during the initial estimate."

    # Add time/cost
    if time_hours and time_hours > 0:
        narrative += f" Additional time: {time_hours} hours."
    if cost and cost > 0:
        narrative += f" Additional cost: ${cost:.2f}."

    return narrative


def generate_summary_narrative(
    discoveries: List[Dict],
    total_cost: float,
    total_time: float,
    vehicle_info: Dict = None
) -> str:
    """
    Generate summary narrative for entire supplement.
    """
    vehicle_desc = ""
    if vehicle_info:
        year = vehicle_info.get('vehicle_year', '')
        make = vehicle_info.get('vehicle_make', '')
        model = vehicle_info.get('vehicle_model', '')
        if year and make and model:
            vehicle_desc = f"the {year} {make} {model}"
        else:
            vehicle_desc = "the vehicle"
    else:
        vehicle_desc = "the vehicle"

    count = len(discoveries)

    summary = f"SUPPLEMENT REQUEST\n\n"
    summary += f"During the paintless dent repair process on {vehicle_desc}, "
    summary += f"{count} additional item{'s were' if count != 1 else ' was'} "
    summary += "discovered that were not visible or accessible during the initial inspection.\n\n"

    # Group by type
    types = {}
    for d in discoveries:
        t = d.get('type', 'other')
        types[t] = types.get(t, 0) + 1

    summary += "DISCOVERIES:\n"
    for disc_type, count in types.items():
        summary += f"  - {disc_type.replace('_', ' ').title()}: {count}\n"

    summary += f"\nTOTAL ADDITIONAL TIME: {total_time:.2f} hours\n"
    summary += f"TOTAL ADDITIONAL COST: ${total_cost:.2f}\n\n"

    summary += "All additional items were documented at the time of discovery "
    summary += "with photographs where applicable. These items are necessary "
    summary += "for proper and complete repair of the hail damage.\n\n"

    summary += "Please review and approve this supplement to proceed with complete repair."

    return summary


# Discovery type templates
DISCOVERY_TEMPLATES = {
    "handle_interference": {
        "description": "Door handle removal required for tool access to dent area",
        "typical_time": 0.25,
        "typical_cost": 25
    },
    "liner_removal": {
        "description": "Inner liner removal required for backside access",
        "typical_time": 0.17,
        "typical_cost": 20
    },
    "hidden_damage": {
        "description": "Additional damage discovered under trim or liner",
        "typical_time": 0.5,
        "typical_cost": 75
    },
    "headliner_drop": {
        "description": "Partial headliner drop required for roof panel access",
        "typical_time": 1.5,
        "typical_cost": 150
    },
    "trim_removal": {
        "description": "Trim panel removal required for tool access",
        "typical_time": 0.33,
        "typical_cost": 35
    },
    "adhesive_removal": {
        "description": "Adhesive-mounted component removal required",
        "typical_time": 0.25,
        "typical_cost": 30
    },
    "wiring_disconnect": {
        "description": "Electrical component disconnect required for access",
        "typical_time": 0.25,
        "typical_cost": 25
    },
    "access_difficulty": {
        "description": "Difficult access requiring additional time",
        "typical_time": 0.5,
        "typical_cost": 50
    },
    "high_strength_steel": {
        "description": "High strength steel panel requiring specialized technique",
        "typical_time": 0.5,
        "typical_cost": 75
    },
    "aluminum_panel": {
        "description": "Aluminum panel requiring specialized tools and technique",
        "typical_time": 0.75,
        "typical_cost": 100
    }
}


def get_discovery_template(discovery_type: str) -> Dict:
    """Get template for a discovery type."""
    return DISCOVERY_TEMPLATES.get(
        discovery_type,
        {"description": "Additional work required", "typical_time": 0.25, "typical_cost": 25}
    )


def list_discovery_types() -> List[Dict]:
    """List all available discovery types with descriptions."""
    return [
        {
            "type": key,
            "display_name": key.replace('_', ' ').title(),
            "description": val["description"],
            "typical_time": val["typical_time"],
            "typical_cost": val["typical_cost"]
        }
        for key, val in DISCOVERY_TEMPLATES.items()
    ]
