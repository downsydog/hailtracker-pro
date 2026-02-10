"""R&I Justification Service - compute times and generate defensible justifications.

Phase 6A: R&I Justification Engine
Computes R&I times from steps + modifiers (vehicle-agnostic).
Generates insurer-resistant justification text.
"""

from typing import Dict, List, Any, Optional
from app.extensions import db


def ensure_default_ri_catalog(tenant_id: int) -> None:
    """
    Seed the default R&I catalog for a tenant if it doesn't exist.

    Idempotent - can be called multiple times safely.
    """
    from app.models.tenant.ri_operation import RIOperation
    from app.models.tenant.ri_step import RIStep
    from app.models.tenant.ri_modifier import RIModifier

    # Check if catalog already exists
    existing = RIOperation.query.filter_by(tenant_id=tenant_id).first()
    if existing:
        return

    # Default operations with steps
    operations_data = [
        {
            'code': 'RI_HEADLINER_REMOVAL',
            'display_name': 'Headliner Removal & Installation',
            'category': 'interior',
            'risk_level': 'high',
            'description': 'Complete removal and reinstallation of vehicle headliner for roof access.',
            'steps': [
                {'step_code': 'REMOVE_SUN_VISORS', 'label': 'Remove sun visors', 'base_time': 0.15,
                 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REMOVE_OVERHEAD_CONSOLE', 'label': 'Remove overhead console/dome light',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
                {'step_code': 'REMOVE_GRAB_HANDLES', 'label': 'Remove grab handles and coat hooks',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REMOVE_A_PILLAR_TRIM', 'label': 'Remove A-pillar trim covers',
                 'base_time': 0.3, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['airbag']},
                {'step_code': 'REMOVE_B_PILLAR_TRIM', 'label': 'Remove B-pillar trim covers',
                 'base_time': 0.3, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['airbag', 'seatbelt']},
                {'step_code': 'REMOVE_C_PILLAR_TRIM', 'label': 'Remove C-pillar trim covers',
                 'base_time': 0.3, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['airbag']},
                {'step_code': 'DISCONNECT_ELECTRICAL', 'label': 'Disconnect electrical connections',
                 'base_time': 0.25, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical', 'sensor']},
                {'step_code': 'CONTROLLED_LOWERING', 'label': 'Controlled lowering of headliner',
                 'base_time': 0.4, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['fragile']},
                {'step_code': 'REINSTALL_HEADLINER', 'label': 'Reinstall headliner with proper alignment',
                 'base_time': 0.5, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['fragile', 'alignment']},
                {'step_code': 'REINSTALL_COMPONENTS', 'label': 'Reinstall all trim and components',
                 'base_time': 0.45, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
            ],
        },
        {
            'code': 'RI_SUNROOF_ASSEMBLY',
            'display_name': 'Sunroof/Moonroof Assembly R&I',
            'category': 'interior',
            'risk_level': 'high',
            'description': 'Removal and reinstallation of sunroof cassette and trim for roof access.',
            'steps': [
                {'step_code': 'REMOVE_SUNROOF_TRIM', 'label': 'Remove sunroof interior trim ring',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'DISCONNECT_MOTOR', 'label': 'Disconnect sunroof motor and switches',
                 'base_time': 0.25, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
                {'step_code': 'REMOVE_DRAIN_TUBES', 'label': 'Disconnect drain tubes',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'medium', 'risk_tags': []},
                {'step_code': 'REMOVE_CASSETTE', 'label': 'Remove sunroof cassette assembly',
                 'base_time': 0.5, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['fragile', 'heavy']},
                {'step_code': 'REINSTALL_CASSETTE', 'label': 'Reinstall cassette with proper seal',
                 'base_time': 0.6, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['seal', 'alignment']},
            ],
        },
        {
            'code': 'RI_A_PILLAR_TRIM',
            'display_name': 'A-Pillar Trim R&I',
            'category': 'interior',
            'risk_level': 'medium',
            'description': 'Removal and reinstallation of A-pillar trim panels.',
            'steps': [
                {'step_code': 'REMOVE_WEATHERSTRIP', 'label': 'Partially remove door weatherstrip',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'DISCONNECT_AIRBAG', 'label': 'Disconnect side curtain airbag connector',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['airbag', 'safety_critical']},
                {'step_code': 'REMOVE_TRIM', 'label': 'Remove A-pillar trim panel',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REINSTALL', 'label': 'Reinstall trim and reconnect airbag',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['airbag']},
            ],
        },
        {
            'code': 'RI_B_PILLAR_TRIM',
            'display_name': 'B-Pillar Trim R&I',
            'category': 'interior',
            'risk_level': 'medium',
            'description': 'Removal and reinstallation of B-pillar trim panels.',
            'steps': [
                {'step_code': 'REMOVE_SEATBELT_COVER', 'label': 'Remove seatbelt anchor cover',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['seatbelt']},
                {'step_code': 'DISCONNECT_AIRBAG', 'label': 'Disconnect side airbag connections',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['airbag', 'safety_critical']},
                {'step_code': 'REMOVE_TRIM', 'label': 'Remove B-pillar trim panel',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REINSTALL', 'label': 'Reinstall trim and safety components',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['airbag', 'seatbelt']},
            ],
        },
        {
            'code': 'RI_C_PILLAR_TRIM',
            'display_name': 'C-Pillar Trim R&I',
            'category': 'interior',
            'risk_level': 'medium',
            'description': 'Removal and reinstallation of C-pillar (or D-pillar) trim panels.',
            'steps': [
                {'step_code': 'REMOVE_REAR_TRIM', 'label': 'Remove rear quarter trim access',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'DISCONNECT_AIRBAG', 'label': 'Disconnect curtain airbag if equipped',
                 'base_time': 0.15, 'required': False, 'denial_resistance': 'high',
                 'risk_tags': ['airbag']},
                {'step_code': 'REMOVE_TRIM', 'label': 'Remove C-pillar trim panel',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REINSTALL', 'label': 'Reinstall all components',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
            ],
        },
        {
            'code': 'RI_REAR_PACKAGE_TRAY',
            'display_name': 'Rear Package Tray R&I',
            'category': 'interior',
            'risk_level': 'low',
            'description': 'Removal and reinstallation of rear package tray/shelf.',
            'steps': [
                {'step_code': 'REMOVE_SPEAKERS', 'label': 'Remove rear speakers if mounted',
                 'base_time': 0.2, 'required': False, 'denial_resistance': 'medium',
                 'risk_tags': ['electrical']},
                {'step_code': 'REMOVE_TRAY', 'label': 'Remove package tray',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REINSTALL', 'label': 'Reinstall package tray and speakers',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
            ],
        },
        {
            'code': 'RI_DOOR_PANEL',
            'display_name': 'Door Panel R&I',
            'category': 'interior',
            'risk_level': 'medium',
            'description': 'Removal and reinstallation of interior door panel.',
            'steps': [
                {'step_code': 'REMOVE_SWITCH_PANEL', 'label': 'Remove window/lock switch panel',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
                {'step_code': 'DISCONNECT_ELECTRICAL', 'label': 'Disconnect electrical connectors',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
                {'step_code': 'REMOVE_PANEL', 'label': 'Remove door panel',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REMOVE_VAPOR_BARRIER', 'label': 'Remove vapor barrier if needed',
                 'base_time': 0.1, 'required': False, 'denial_resistance': 'medium',
                 'risk_tags': ['seal']},
                {'step_code': 'REINSTALL', 'label': 'Reinstall panel and reconnect',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
            ],
        },
        {
            'code': 'RI_HOOD_LINER',
            'display_name': 'Hood Liner/Insulator R&I',
            'category': 'exterior',
            'risk_level': 'low',
            'description': 'Removal and reinstallation of hood insulation liner.',
            'steps': [
                {'step_code': 'REMOVE_CLIPS', 'label': 'Remove retaining clips',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REMOVE_LINER', 'label': 'Remove liner',
                 'base_time': 0.05, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REINSTALL', 'label': 'Reinstall with new clips if needed',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
            ],
        },
        {
            'code': 'RI_TRUNK_TRIM',
            'display_name': 'Trunk Trim/Liner R&I',
            'category': 'interior',
            'risk_level': 'low',
            'description': 'Removal and reinstallation of trunk interior trim panels.',
            'steps': [
                {'step_code': 'REMOVE_FLOOR_MAT', 'label': 'Remove trunk floor mat/carpet',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REMOVE_SIDE_PANELS', 'label': 'Remove side trim panels',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REINSTALL', 'label': 'Reinstall all trunk trim',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
            ],
        },
        {
            'code': 'RI_TAILLIGHT_ASSEMBLY',
            'display_name': 'Taillight Assembly R&I',
            'category': 'exterior',
            'risk_level': 'low',
            'description': 'Removal and reinstallation of taillight assembly for access.',
            'steps': [
                {'step_code': 'REMOVE_TRIM', 'label': 'Remove access trim if needed',
                 'base_time': 0.1, 'required': False, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'DISCONNECT_ELECTRICAL', 'label': 'Disconnect electrical connector',
                 'base_time': 0.05, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
                {'step_code': 'REMOVE_ASSEMBLY', 'label': 'Remove taillight assembly',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REINSTALL', 'label': 'Reinstall and test',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical']},
            ],
        },
        {
            'code': 'RI_SEAT_REMOVAL',
            'display_name': 'Seat Removal R&I',
            'category': 'interior',
            'risk_level': 'high',
            'description': 'Removal and reinstallation of front or rear seat assembly.',
            'steps': [
                {'step_code': 'DISCONNECT_BATTERY', 'label': 'Disconnect battery (airbag safety)',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['safety_critical', 'airbag']},
                {'step_code': 'DISCONNECT_ELECTRICAL', 'label': 'Disconnect seat electrical (heat, motors, sensors)',
                 'base_time': 0.2, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['electrical', 'airbag']},
                {'step_code': 'REMOVE_BOLTS', 'label': 'Remove seat mounting bolts',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REMOVE_SEAT', 'label': 'Remove seat assembly',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['heavy']},
                {'step_code': 'REINSTALL', 'label': 'Reinstall seat and torque to spec',
                 'base_time': 0.3, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['safety_critical', 'torque']},
            ],
        },
        {
            'code': 'RI_SEATBELT_ANCHOR',
            'display_name': 'Seatbelt Anchor R&I',
            'category': 'structural',
            'risk_level': 'high',
            'description': 'Removal and reinstallation of seatbelt anchor point.',
            'steps': [
                {'step_code': 'REMOVE_COVER', 'label': 'Remove anchor point cover',
                 'base_time': 0.05, 'required': True, 'denial_resistance': 'high', 'risk_tags': []},
                {'step_code': 'REMOVE_BOLT', 'label': 'Remove anchor bolt',
                 'base_time': 0.1, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['safety_critical']},
                {'step_code': 'REINSTALL', 'label': 'Reinstall and torque to OEM spec',
                 'base_time': 0.15, 'required': True, 'denial_resistance': 'high',
                 'risk_tags': ['safety_critical', 'torque']},
            ],
        },
    ]

    # Default modifiers
    modifiers_data = [
        {
            'modifier_code': 'PANORAMIC_GLASS_PRESENT',
            'label': 'Panoramic Glass/Sunroof Present',
            'adds_time_hours': 0.4,
            'reason': 'Panoramic glass requires additional care and handling during headliner removal to prevent glass stress or seal damage.',
            'category': 'complexity',
        },
        {
            'modifier_code': 'MULTIPLE_CURTAIN_AIRBAGS',
            'label': 'Multiple Curtain Airbags',
            'adds_time_hours': 0.5,
            'reason': 'Side curtain airbags spanning A/B/C pillars require careful disconnection and routing during interior trim removal.',
            'category': 'risk',
        },
        {
            'modifier_code': 'LUXURY_HEADLINER_MATERIAL',
            'label': 'Luxury/Alcantara Headliner Material',
            'adds_time_hours': 0.3,
            'reason': 'Premium materials (Alcantara, suede) require additional handling care to prevent staining or damage.',
            'category': 'material',
        },
        {
            'modifier_code': 'POWERED_SUNSHADE',
            'label': 'Powered Sunshade System',
            'adds_time_hours': 0.25,
            'reason': 'Integrated powered sunshade requires disconnection and careful handling of motor and track assembly.',
            'category': 'complexity',
        },
        {
            'modifier_code': 'AMBIENT_LIGHTING',
            'label': 'Ambient Lighting System',
            'adds_time_hours': 0.2,
            'reason': 'LED ambient lighting strips integrated into trim require careful disconnection to avoid damage.',
            'category': 'complexity',
        },
        {
            'modifier_code': 'HEATED_WINDSHIELD_WIRING',
            'label': 'Heated Windshield Wiring',
            'adds_time_hours': 0.15,
            'reason': 'Heated windshield wiring routed through A-pillars requires careful handling.',
            'category': 'complexity',
        },
        {
            'modifier_code': 'ADVANCED_DRIVER_SENSORS',
            'label': 'Advanced Driver Assist Sensors',
            'adds_time_hours': 0.3,
            'reason': 'ADAS cameras, radar, or LiDAR sensors require careful handling and may need recalibration references.',
            'category': 'risk',
        },
        {
            'modifier_code': 'SUNROOF_WIND_DEFLECTOR',
            'label': 'Sunroof Wind Deflector',
            'adds_time_hours': 0.1,
            'reason': 'Pop-up wind deflector mechanism requires removal during sunroof R&I.',
            'category': 'complexity',
        },
    ]

    # Create operations with steps
    for op_data in operations_data:
        steps_data = op_data.pop('steps')
        operation = RIOperation(
            tenant_id=tenant_id,
            code=op_data['code'],
            display_name=op_data['display_name'],
            category=op_data['category'],
            risk_level=op_data['risk_level'],
            description=op_data['description'],
            is_seeded=True,  # Stage 6H-C: Mark as system-seeded (cannot be deleted)
        )
        db.session.add(operation)
        db.session.flush()  # Get operation ID

        for idx, step_data in enumerate(steps_data):
            step = RIStep(
                tenant_id=tenant_id,
                operation_id=operation.id,
                step_code=step_data['step_code'],
                label=step_data['label'],
                base_time_hours=step_data['base_time'],
                required=step_data['required'],
                denial_resistance=step_data['denial_resistance'],
                risk_tags=step_data['risk_tags'],
                order_index=idx,
            )
            db.session.add(step)

    # Create modifiers
    for mod_data in modifiers_data:
        modifier = RIModifier(
            tenant_id=tenant_id,
            modifier_code=mod_data['modifier_code'],
            label=mod_data['label'],
            adds_time_hours=mod_data['adds_time_hours'],
            reason=mod_data['reason'],
            category=mod_data['category'],
        )
        db.session.add(modifier)

    db.session.commit()


def get_ri_catalog(tenant_id: int) -> Dict[str, Any]:
    """
    Get the full R&I catalog for a tenant.

    Returns operations with steps and all modifiers.
    """
    from app.models.tenant.ri_operation import RIOperation
    from app.models.tenant.ri_modifier import RIModifier

    # Ensure catalog exists
    ensure_default_ri_catalog(tenant_id)

    operations = RIOperation.query.filter_by(tenant_id=tenant_id).all()
    modifiers = RIModifier.query.filter_by(tenant_id=tenant_id).all()

    return {
        'operations': [op.to_dict_with_steps() for op in operations],
        'modifiers': [mod.to_dict() for mod in modifiers],
    }


def compute_operation_time(
    estimate_ri_op,
    operation,
    step_overrides: Dict[int, dict],
    selected_modifiers: List,
) -> Dict[str, Any]:
    """
    Compute total time for an R&I operation on an estimate.

    Returns detailed breakdown of steps and modifiers.
    """
    steps_breakdown = []
    base_steps_time = 0.0

    for step in operation.steps.order_by('order_index').all():
        override = step_overrides.get(step.id, {})
        included = override.get('included', True) if not step.required else True

        if included:
            effective_time = override.get('time_override_hours') or step.base_time_hours
            base_steps_time += effective_time

            steps_breakdown.append({
                'step_id': step.id,
                'step_code': step.step_code,
                'label': step.label,
                'description': step.description,
                'base_time_hours': step.base_time_hours,
                'effective_time_hours': effective_time,
                'included': included,
                'required': step.required,
                'denial_resistance': step.denial_resistance,
                'risk_tags': step.risk_tags or [],
                'override_notes': override.get('notes'),
            })

    modifiers_breakdown = []
    modifiers_time = 0.0

    for selection in selected_modifiers:
        modifier = selection.modifier
        modifiers_time += modifier.adds_time_hours
        modifiers_breakdown.append({
            'modifier_id': modifier.id,
            'modifier_code': modifier.modifier_code,
            'label': modifier.label,
            'adds_time_hours': modifier.adds_time_hours,
            'reason': modifier.reason,
            'category': modifier.category,
            'notes': selection.notes,
        })

    total_time = base_steps_time + modifiers_time

    return {
        'operation_id': operation.id,
        'code': operation.code,
        'display_name': operation.display_name,
        'category': operation.category,
        'risk_level': operation.risk_level,
        'description': operation.description,
        'steps': steps_breakdown,
        'modifiers': modifiers_breakdown,
        'totals': {
            'base_steps_time': round(base_steps_time, 2),
            'modifiers_time': round(modifiers_time, 2),
            'total_time': round(total_time, 2),
        },
        'notes': estimate_ri_op.notes,
    }


def generate_justification_text(operation_summary: Dict[str, Any]) -> str:
    """
    Generate insurer-resistant justification text for an R&I operation.

    Returns formatted paragraphs with step breakdown and risk factors.
    """
    op = operation_summary
    lines = []

    # Header
    lines.append(f"**{op['display_name']}** — Total Time: {op['totals']['total_time']} hours")
    lines.append("")

    # Justification paragraph
    lines.append(f"This operation requires {op['display_name'].lower()} to provide proper access for paintless dent repair. "
                f"The operation involves {len(op['steps'])} discrete steps, each documented below with time allocations "
                f"based on industry-standard procedures.")
    lines.append("")

    # Steps breakdown
    lines.append("**Required Steps:**")
    for step in op['steps']:
        if step['included']:
            risk_info = f" [{', '.join(step['risk_tags'])}]" if step['risk_tags'] else ""
            lines.append(f"• {step['label']}: {step['effective_time_hours']} hrs{risk_info}")
    lines.append("")

    # Modifiers
    if op['modifiers']:
        lines.append("**Complexity Factors Applied:**")
        for mod in op['modifiers']:
            lines.append(f"• {mod['label']}: +{mod['adds_time_hours']} hrs")
            lines.append(f"  Reason: {mod['reason']}")
        lines.append("")

    # Summary
    lines.append(f"**Total Computed Time:** {op['totals']['total_time']} hours")
    lines.append(f"(Base steps: {op['totals']['base_steps_time']} hrs + Modifiers: {op['totals']['modifiers_time']} hrs)")

    return "\n".join(lines)


# --- 6G: Denial Ammo Builder ---
def _format_cite_line(operation_name: str, step_label: str, hours: float) -> str:
    """Single-line cite for adjuster discussions."""
    h = f"{hours:.2f}".rstrip('0').rstrip('.')
    return f"R&I {operation_name}: {step_label} ({h}h)"


def _build_adjuster_bullets(denial_pack: dict, operations: list) -> List[str]:
    """Create 4-8 insurer-ready bullets, focusing on safety/access/procedure necessity."""
    risk_tags = denial_pack.get('risk_tags') or []
    rating = denial_pack.get('overall_rating', 'medium')
    counts = denial_pack.get('resistance_counts') or {}
    hi = counts.get('high', 0)
    med = counts.get('medium', 0)
    lo = counts.get('low', 0)

    bullets = []
    bullets.append("R&I time is itemized by discrete sub-operations (trim, fasteners, safety restraints, access) so any denial must specify the exact sub-step being excluded.")
    bullets.append("Steps reflect access and safety requirements (airbags/seatbelts/trim retention) and are not duplicative of dent repair labor.")
    if risk_tags:
        bullets.append("Risk factors addressed: " + ", ".join(sorted(set(risk_tags))) + ".")
    bullets.append(f"Denial resistance profile: {rating.upper()} (High/Med/Low steps: {hi}/{med}/{lo}).")
    bullets.append("Where applicable, R&I includes disconnect/reconnect, clip/fastener handling, and re-fit verification to restore OEM fitment and function.")
    bullets.append("If the carrier elects to exclude a sub-step (e.g., sunvisor removal), approval is requested in writing acknowledging resulting access/fitment limitations.")

    # Trim to 4-8 bullets
    bullets = [b for b in bullets if b]
    return bullets[:8]


def _build_scope_clarifier() -> str:
    """Build scope clarification paragraph."""
    return (
        "Scope note: R&I covers access/safety disassembly and reassembly required to perform PDR and restore trim/fitment. "
        "It does not include unrelated mechanical repair, paint/refinish operations, or pre-existing damage correction unless separately itemized."
    )


def _build_top_defensible_steps(operations: list) -> List[Dict[str, Any]]:
    """Rank and return top defensible steps: high denial_resistance first, then required flag, then higher time."""
    steps = []
    for op in operations or []:
        op_name = op.get('display_name') or op.get('operation_name') or op.get('code') or "Operation"
        for st in op.get('steps') or []:
            if not st.get('included', True):
                continue
            steps.append({
                "operation_name": op_name,
                "step_code": st.get("step_code"),
                "label": st.get("label") or st.get("description") or st.get("step_code"),
                "denial_resistance": st.get("denial_resistance") or "medium",
                "required": bool(st.get("required")),
                "base_time_hours": float(st.get("base_time_hours") or st.get("effective_time_hours") or 0),
                "risk_tags": st.get("risk_tags") or [],
            })

    def key(s):
        dr = s["denial_resistance"]
        dr_w = 3 if dr == "high" else 2 if dr == "medium" else 1
        req_w = 1 if s["required"] else 0
        return (dr_w, req_w, s["base_time_hours"])

    steps.sort(key=key, reverse=True)

    top = []
    for s in steps[:6]:
        cite = _format_cite_line(s["operation_name"], s["label"], s["base_time_hours"])
        s2 = dict(s)
        s2["cite_line"] = cite
        top.append(s2)
    return top


def _build_copy_blocks(denial_pack: dict, bullets: list, scope: str, top_steps: list) -> Dict[str, str]:
    """Build copy/paste ready text blocks."""
    score = denial_pack.get("overall_score")
    rating = denial_pack.get("overall_rating")
    summary = denial_pack.get("summary_text") or ""

    top_lines = []
    for s in top_steps[:3]:
        top_lines.append(f"- {s.get('cite_line')}")

    header = f"R&I Denial Pack: {rating.upper()} ({score:.0f}/100)" if score is not None and rating else "R&I Denial Pack"

    short = "\n".join([
        header,
        "Top defensible sub-steps:",
        *top_lines
    ])

    full = "\n".join([
        header,
        "",
        "Adjuster bullets:",
        *[f"- {b}" for b in bullets],
        "",
        "Top defensible sub-steps (cite lines):",
        *[f"- {s.get('cite_line')}" for s in top_steps],
        "",
        "Scope clarifier:",
        scope,
        "",
        "Summary:",
        summary.strip()
    ]).strip()

    return {"short": short, "full": full}


def compute_denial_pack(operations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute denial resistance pack for R&I operations (Stage 6F).

    Aggregates denial resistance metrics and generates insurer-ready documentation.

    Returns:
        {
            'overall_score': float (0-100),
            'overall_rating': 'high' | 'medium' | 'low',
            'resistance_counts': { 'high': int, 'medium': int, 'low': int },
            'risk_tags': [str],
            'required_steps_count': int,
            'optional_steps_count': int,
            'high_resistance_steps': [{ step_code, label, operation_name }],
            'summary_text': str,
        }
    """
    if not operations:
        return {
            'overall_score': 0,
            'overall_rating': 'low',
            'resistance_counts': {'high': 0, 'medium': 0, 'low': 0},
            'risk_tags': [],
            'required_steps_count': 0,
            'optional_steps_count': 0,
            'high_resistance_steps': [],
            'summary_text': 'No R&I operations documented.',
        }

    resistance_counts = {'high': 0, 'medium': 0, 'low': 0}
    all_risk_tags = set()
    required_count = 0
    optional_count = 0
    high_resistance_steps = []

    for op in operations:
        for step in op.get('steps', []):
            if not step.get('included', True):
                continue

            resistance = step.get('denial_resistance', 'medium')
            resistance_counts[resistance] = resistance_counts.get(resistance, 0) + 1

            if step.get('required', False):
                required_count += 1
            else:
                optional_count += 1

            # Collect risk tags
            for tag in step.get('risk_tags', []):
                all_risk_tags.add(tag)

            # Track high resistance steps
            if resistance == 'high':
                high_resistance_steps.append({
                    'step_code': step.get('step_code'),
                    'label': step.get('label'),
                    'operation_name': op.get('display_name'),
                    'risk_tags': step.get('risk_tags', []),
                })

    # Calculate overall score (weighted: high=100, medium=60, low=20)
    total_steps = resistance_counts['high'] + resistance_counts['medium'] + resistance_counts['low']
    if total_steps > 0:
        weighted_sum = (resistance_counts['high'] * 100 +
                       resistance_counts['medium'] * 60 +
                       resistance_counts['low'] * 20)
        overall_score = round(weighted_sum / total_steps, 1)
    else:
        overall_score = 0

    # Determine overall rating
    if overall_score >= 80:
        overall_rating = 'high'
    elif overall_score >= 50:
        overall_rating = 'medium'
    else:
        overall_rating = 'low'

    # Generate summary text
    summary_parts = []
    summary_parts.append(f"This estimate includes {len(operations)} R&I operation(s) "
                        f"with {total_steps} documented steps.")

    if resistance_counts['high'] > 0:
        summary_parts.append(f"{resistance_counts['high']} step(s) have high denial resistance "
                            "and are industry-standard requirements.")

    if all_risk_tags:
        tag_str = ', '.join(sorted(all_risk_tags))
        summary_parts.append(f"Risk factors addressed: {tag_str}.")

    if required_count > 0:
        summary_parts.append(f"{required_count} step(s) are mandatory for proper vehicle access.")

    summary_text = ' '.join(summary_parts)

    denial_pack = {
        'overall_score': overall_score,
        'overall_rating': overall_rating,
        'resistance_counts': resistance_counts,
        'risk_tags': sorted(list(all_risk_tags)),
        'required_steps_count': required_count,
        'optional_steps_count': optional_count,
        'high_resistance_steps': high_resistance_steps,
        'summary_text': summary_text,
    }

    # --- 6G: Denial Ammo (copy/paste ready) ---
    adjuster_bullets = _build_adjuster_bullets(denial_pack, operations)
    scope_clarifier = _build_scope_clarifier()
    top_defensible_steps = _build_top_defensible_steps(operations)
    copy_blocks = _build_copy_blocks(denial_pack, adjuster_bullets, scope_clarifier, top_defensible_steps)

    denial_pack["adjuster_bullets"] = adjuster_bullets
    denial_pack["scope_clarifier"] = scope_clarifier
    denial_pack["top_defensible_steps"] = top_defensible_steps
    denial_pack["copy_blocks"] = copy_blocks

    return denial_pack


def compute_estimate_ri_summary(estimate_id: int, tenant_id: int) -> Dict[str, Any]:
    """
    Compute full R&I summary for an estimate.

    Returns all attached operations with computed times and justifications.
    Includes resolved labor rate (Stage 6E).
    """
    from app.models.tenant.pdr_estimate_ri import (
        PDREstimateRIOperation,
        PDREstimateRIStepOverride,
        PDREstimateRIModifierSelection,
    )
    from app.models.tenant import PDREstimate
    from app.services.labor_rate_service import resolve_ri_rate_for_estimate

    # Get estimate for labor rate resolution
    estimate = PDREstimate.query.filter_by(
        id=estimate_id,
        tenant_id=tenant_id
    ).first()

    # Resolve labor rate
    labor_rate_info = {'rate': 85.0, 'source': 'default', 'rule_id': None, 'rule_name': None, 'reason': 'Estimate not found'}
    if estimate:
        labor_rate_info = resolve_ri_rate_for_estimate(estimate)

    # Get all R&I operations attached to this estimate
    estimate_ri_ops = PDREstimateRIOperation.query.filter_by(
        estimate_id=estimate_id,
        tenant_id=tenant_id,
    ).all()

    operations = []
    total_time = 0.0

    for est_ri_op in estimate_ri_ops:
        # Get step overrides
        overrides = est_ri_op.step_overrides.all()
        step_overrides = {o.step_id: {'included': o.included, 'time_override_hours': o.time_override_hours, 'notes': o.notes}
                         for o in overrides}

        # Get modifier selections
        modifier_selections = est_ri_op.modifier_selections.all()

        # Compute time breakdown
        op_summary = compute_operation_time(
            est_ri_op,
            est_ri_op.operation,
            step_overrides,
            modifier_selections,
        )

        # Generate justification text
        op_summary['justification_text'] = generate_justification_text(op_summary)
        op_summary['estimate_ri_operation_id'] = est_ri_op.id

        operations.append(op_summary)
        total_time += op_summary['totals']['total_time']

        # Update computed time on the record
        est_ri_op.computed_time_hours = op_summary['totals']['total_time']

    db.session.commit()

    # Calculate total cost using resolved labor rate
    ri_labor_rate = labor_rate_info['rate']
    total_ri_cost = round(total_time * ri_labor_rate, 2)

    # Compute denial pack (Stage 6F)
    denial_pack = compute_denial_pack(operations)

    return {
        'estimate_id': estimate_id,
        'operations': operations,
        'total_ri_time_hours': round(total_time, 2),
        'operation_count': len(operations),
        # Labor rate info (Stage 6E)
        'ri_labor_rate': ri_labor_rate,
        'ri_labor_rate_source': labor_rate_info['source'],
        'ri_labor_rate_rule_id': labor_rate_info.get('rule_id'),
        'ri_labor_rate_rule_name': labor_rate_info.get('rule_name'),
        'ri_labor_rate_reason': labor_rate_info.get('reason'),
        'total_ri_cost': total_ri_cost,
        # Denial pack (Stage 6F)
        'ri_denial_pack': denial_pack,
    }


# =============================================================================
# STAGE 6H-A: CARRIER DENIAL SIMULATOR
# =============================================================================

# Common denial codes and their definitions
DENIAL_DEFINITIONS = {
    'NOT_PAYING_SUNVISORS': {
        'insurer_claim': 'The carrier is denying payment for sun visor removal, claiming it is not necessary or included elsewhere.',
        'target_step_codes': ['REMOVE_SUN_VISORS', 'REMOVE_SUNVISOR'],
        'target_labels': ['sun visor', 'sunvisor'],
        'risk_exposure': ['trim_damage', 'clip_breakage', 'incomplete_access'],
    },
    'NOT_PAYING_HEADLINER_TIME': {
        'insurer_claim': 'The carrier claims headliner R&I time is excessive or not justified for this repair.',
        'target_step_codes': ['CONTROLLED_LOWERING', 'REINSTALL_HEADLINER', 'HEADLINER'],
        'target_labels': ['headliner', 'lowering', 'alignment'],
        'risk_exposure': ['fragile_material', 'alignment_issues', 'electrical_damage', 'airbag'],
    },
    'NOT_PAYING_TRIM_REMOVAL': {
        'insurer_claim': 'The carrier is denying trim removal steps, suggesting they are unnecessary.',
        'target_step_codes': ['REMOVE_TRIM', 'REMOVE_A_PILLAR_TRIM', 'REMOVE_B_PILLAR_TRIM', 'REMOVE_C_PILLAR_TRIM'],
        'target_labels': ['trim', 'pillar', 'panel'],
        'risk_exposure': ['airbag', 'seatbelt', 'clip_breakage', 'incomplete_access'],
    },
    'NOT_PAYING_SEATBELTS': {
        'insurer_claim': 'The carrier claims seatbelt anchor or restraint system R&I is not required.',
        'target_step_codes': ['REMOVE_SEATBELT_COVER', 'SEATBELT', 'REINSTALL'],
        'target_labels': ['seatbelt', 'restraint', 'anchor', 'safety'],
        'risk_exposure': ['safety_critical', 'torque_spec', 'liability', 'seatbelt'],
    },
    'TIME_EXCESSIVE': {
        'insurer_claim': 'The carrier claims total R&I time is excessive compared to their guidelines.',
        'target_step_codes': [],  # All steps relevant
        'target_labels': [],
        'risk_exposure': ['incomplete_repair', 'liability', 'oem_procedure'],
    },
    'OPERATION_INCLUDED_ELSEWHERE': {
        'insurer_claim': 'The carrier claims this R&I operation is already included in another line item.',
        'target_step_codes': [],  # All steps relevant
        'target_labels': [],
        'risk_exposure': ['double_counting_false', 'discrete_operation', 'access_requirement'],
    },
}


def _find_relevant_steps(operations: List[Dict], denial_code: str) -> List[Dict]:
    """Find steps relevant to a specific denial."""
    denial_def = DENIAL_DEFINITIONS.get(denial_code, {})
    target_codes = [c.upper() for c in denial_def.get('target_step_codes', [])]
    target_labels = [l.lower() for l in denial_def.get('target_labels', [])]

    relevant = []
    for op in operations:
        op_name = op.get('display_name', '')
        for step in op.get('steps', []):
            if not step.get('included', True):
                continue

            step_code = (step.get('step_code') or '').upper()
            step_label = (step.get('label') or '').lower()

            # Match by code or label
            matches = False
            if target_codes and any(tc in step_code for tc in target_codes):
                matches = True
            if target_labels and any(tl in step_label for tl in target_labels):
                matches = True
            # For TIME_EXCESSIVE and OPERATION_INCLUDED_ELSEWHERE, include all high-resistance steps
            if not target_codes and not target_labels:
                if step.get('denial_resistance') == 'high':
                    matches = True

            if matches:
                hours = step.get('effective_time_hours') or step.get('base_time_hours') or 0
                relevant.append({
                    'step_code': step.get('step_code'),
                    'operation_name': op_name,
                    'label': step.get('label'),
                    'hours': hours,
                    'cite_line': _format_cite_line(op_name, step.get('label', ''), hours),
                    'denial_resistance': step.get('denial_resistance'),
                    'required': step.get('required', False),
                    'risk_tags': step.get('risk_tags', []),
                })

    # Sort by denial_resistance (high first), then required, then hours
    def sort_key(s):
        dr = s['denial_resistance']
        dr_w = 3 if dr == 'high' else 2 if dr == 'medium' else 1
        req_w = 1 if s['required'] else 0
        return (dr_w, req_w, s['hours'])

    relevant.sort(key=sort_key, reverse=True)
    return relevant[:10]  # Limit to top 10


def _build_rebuttal_bullets(denial_code: str, cited_steps: List[Dict], risk_exposure: List[str]) -> List[str]:
    """Build rebuttal bullets for a specific denial."""
    bullets = []

    denial_def = DENIAL_DEFINITIONS.get(denial_code, {})
    exposure = denial_def.get('risk_exposure', [])

    # Standard opening
    bullets.append("Each R&I sub-step is individually documented with time allocations based on industry-standard procedures.")

    # Denial-specific bullets
    if denial_code == 'NOT_PAYING_SUNVISORS':
        bullets.append("Sun visor removal is required to lower the headliner without damage to visor mounts or wiring.")
        bullets.append("Failure to remove sun visors risks clip breakage, mirror damage, and incomplete roof access.")
    elif denial_code == 'NOT_PAYING_HEADLINER_TIME':
        bullets.append("Headliner R&I requires controlled lowering to prevent substrate damage and maintain OEM alignment.")
        bullets.append("Modern headliners contain integrated wiring, sensors, and airbag components requiring careful handling.")
        bullets.append("Time includes electrical disconnect, controlled lowering, and proper re-fit verification.")
    elif denial_code == 'NOT_PAYING_TRIM_REMOVAL':
        bullets.append("Pillar trim removal is required for proper headliner/roof access and contains airbag routing.")
        bullets.append("Side curtain airbag connectors routed through A/B/C pillars require proper disconnect procedures.")
        bullets.append("Failure to remove trim creates incomplete access and risks damage to safety restraint systems.")
    elif denial_code == 'NOT_PAYING_SEATBELTS':
        bullets.append("Seatbelt anchor R&I is a safety-critical operation requiring OEM torque specifications.")
        bullets.append("Improper reinstallation of seatbelt anchors creates significant liability exposure.")
        bullets.append("This is not duplicative of other labor—it is a discrete safety procedure.")
    elif denial_code == 'TIME_EXCESSIVE':
        bullets.append("Time allocations are based on discrete sub-operations, each independently justified.")
        bullets.append("If specific sub-steps are disputed, carrier must identify which step is excessive and why.")
        bullets.append("Blanket denial of 'excessive time' without step-specific justification is not actionable.")
    elif denial_code == 'OPERATION_INCLUDED_ELSEWHERE':
        bullets.append("R&I operations are discrete access/safety procedures, not duplicative of repair labor.")
        bullets.append("PDR labor covers dent repair only; R&I covers disassembly, access, and reassembly.")
        bullets.append("If carrier claims duplication, request identification of the specific overlapping line item.")

    # Risk exposure
    if cited_steps:
        risk_tags = set()
        for step in cited_steps:
            for tag in step.get('risk_tags', []):
                risk_tags.add(tag)
        if risk_tags:
            bullets.append(f"Risk factors involved: {', '.join(sorted(risk_tags))}.")

    # Required steps count
    required_count = sum(1 for s in cited_steps if s.get('required'))
    if required_count > 0:
        bullets.append(f"{required_count} of the cited steps are mandatory for proper vehicle access.")

    # Closing
    bullets.append("If carrier elects to exclude any sub-step, written acknowledgment of resulting access/fitment limitations is requested.")

    return bullets[:8]


def _build_rebuttal_summary(denial_code: str, cited_steps: List[Dict]) -> str:
    """Build a short rebuttal summary paragraph."""
    denial_def = DENIAL_DEFINITIONS.get(denial_code, {})
    insurer_claim = denial_def.get('insurer_claim', 'The carrier has denied this R&I operation.')

    total_hours = sum(s.get('hours', 0) for s in cited_steps)
    step_count = len(cited_steps)

    if denial_code == 'NOT_PAYING_SUNVISORS':
        return (f"The carrier denial of sun visor removal is not supported. This step ({total_hours:.2f}h) "
                "is required to lower the headliner without damaging visor mounts or electrical connections. "
                "It is a discrete sub-operation, not included elsewhere.")
    elif denial_code == 'NOT_PAYING_HEADLINER_TIME':
        return (f"The documented headliner R&I time ({total_hours:.2f}h across {step_count} steps) reflects "
                "controlled lowering, electrical disconnect, and proper reinstallation with OEM alignment. "
                "Modern vehicles require careful handling of integrated sensors and airbag components.")
    elif denial_code == 'NOT_PAYING_TRIM_REMOVAL':
        return (f"Trim removal ({total_hours:.2f}h) is required for roof/headliner access and includes "
                "pillar-mounted airbag disconnection. These are safety-critical steps that cannot be skipped.")
    elif denial_code == 'NOT_PAYING_SEATBELTS':
        return (f"Seatbelt anchor R&I ({total_hours:.2f}h) is a safety-critical procedure requiring OEM torque. "
                "This is not duplicative—it is a discrete operation with significant liability implications if skipped.")
    elif denial_code == 'TIME_EXCESSIVE':
        return (f"The R&I time ({total_hours:.2f}h across {step_count} high-resistance steps) is itemized by "
                "sub-operation. If carrier disputes specific steps, identification of which step is excessive is required.")
    elif denial_code == 'OPERATION_INCLUDED_ELSEWHERE':
        return (f"R&I operations ({total_hours:.2f}h) are access/safety procedures, not repair labor. "
                "PDR labor covers dent removal only. If carrier claims overlap, the specific duplicate line item must be identified.")

    return f"The denied operation involves {step_count} documented steps totaling {total_hours:.2f}h. Each step is independently justified."


def get_denial_rebuttal(estimate_id: int, tenant_id: int, denial_code: str) -> Dict[str, Any]:
    """
    Generate a rebuttal for a common carrier denial (Stage 6H-A).

    Uses ONLY existing R&I steps attached to the estimate.
    Returns insurer-ready rebuttal with cite lines and copy blocks.
    """
    if denial_code not in DENIAL_DEFINITIONS:
        return {
            'success': False,
            'error': f"Unknown denial code: {denial_code}",
            'valid_codes': list(DENIAL_DEFINITIONS.keys()),
        }

    # Get the R&I summary for this estimate
    ri_summary = compute_estimate_ri_summary(estimate_id, tenant_id)
    operations = ri_summary.get('operations', [])

    if not operations:
        return {
            'success': False,
            'error': 'No R&I operations attached to this estimate.',
        }

    denial_def = DENIAL_DEFINITIONS[denial_code]
    insurer_claim = denial_def['insurer_claim']
    risk_exposure = denial_def.get('risk_exposure', [])

    # Find relevant steps
    cited_steps = _find_relevant_steps(operations, denial_code)

    if not cited_steps:
        return {
            'success': False,
            'error': f'No steps found matching denial type: {denial_code}. Add relevant R&I operations first.',
        }

    # Build rebuttal
    rebuttal_summary = _build_rebuttal_summary(denial_code, cited_steps)
    rebuttal_bullets = _build_rebuttal_bullets(denial_code, cited_steps, risk_exposure)

    # Build copy blocks
    cite_lines = [s['cite_line'] for s in cited_steps]

    short_block = "\n".join([
        f"REBUTTAL: {denial_code}",
        "",
        rebuttal_summary,
        "",
        "Cited steps:",
        *[f"- {c}" for c in cite_lines[:3]],
    ])

    full_block = "\n".join([
        f"REBUTTAL: {denial_code}",
        "",
        f"Insurer Claim: {insurer_claim}",
        "",
        "Rebuttal:",
        rebuttal_summary,
        "",
        "Key Points:",
        *[f"- {b}" for b in rebuttal_bullets],
        "",
        "Cited Steps:",
        *[f"- {c}" for c in cite_lines],
        "",
        "If this denial is maintained, written acknowledgment of the resulting access/safety limitations is requested.",
    ])

    return {
        'success': True,
        'denial_code': denial_code,
        'insurer_claim': insurer_claim,
        'rebuttal_summary': rebuttal_summary,
        'rebuttal_bullets': rebuttal_bullets,
        'cited_steps': cited_steps,
        'risk_exposure': risk_exposure,
        'copy_blocks': {
            'short': short_block,
            'full': full_block,
        },
    }


# =============================================================================
# STAGE 6H-B: ONE-CLICK SUPPLEMENT WRITER
# =============================================================================

def build_supplement_letter(
    estimate_id: int,
    tenant_id: int,
    denial_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a full insurer-ready supplement letter (Stage 6H-B).

    Uses R&I totals, denial pack, and optionally includes denial rebuttal.
    """
    from app.models.tenant import PDREstimate

    # Get estimate
    estimate = PDREstimate.query.filter_by(
        id=estimate_id,
        tenant_id=tenant_id
    ).first()

    if not estimate:
        return {'success': False, 'error': 'Estimate not found.'}

    # Get R&I summary
    ri_summary = compute_estimate_ri_summary(estimate_id, tenant_id)
    operations = ri_summary.get('operations', [])
    denial_pack = ri_summary.get('ri_denial_pack', {})

    if not operations:
        return {'success': False, 'error': 'No R&I operations attached to this estimate.'}

    # Build header info
    estimate_dict = estimate.to_dict()
    vehicle_str = f"{estimate_dict.get('vehicle_year', '')} {estimate_dict.get('vehicle_make', '')} {estimate_dict.get('vehicle_model', '')}".strip()
    customer_name = estimate_dict.get('customer_name', 'Customer')
    claim_number = estimate_dict.get('claim_number', 'N/A')
    estimate_number = estimate_dict.get('estimate_number', 'N/A')
    vin = estimate_dict.get('vin', 'N/A')

    # Labor rate info
    labor_rate = ri_summary.get('ri_labor_rate', 85.0)
    labor_source = ri_summary.get('ri_labor_rate_source', 'default')
    labor_rule_name = ri_summary.get('ri_labor_rate_rule_name')
    total_hours = ri_summary.get('total_ri_time_hours', 0)
    total_cost = ri_summary.get('total_ri_cost', 0)

    # Build letter sections
    sections = []

    # Header
    sections.append(f"SUPPLEMENT REQUEST - R&I JUSTIFICATION")
    sections.append(f"Estimate: {estimate_number}")
    sections.append(f"Claim: {claim_number}")
    sections.append(f"Vehicle: {vehicle_str}")
    sections.append(f"VIN: {vin}")
    sections.append(f"Customer: {customer_name}")
    sections.append("")

    # Scope clarification
    scope = denial_pack.get('scope_clarifier', '')
    if scope:
        sections.append("SCOPE OF R&I OPERATIONS")
        sections.append(scope)
        sections.append("")

    # R&I justification summary
    sections.append("R&I JUSTIFICATION SUMMARY")
    summary = denial_pack.get('summary_text', '')
    sections.append(summary)
    sections.append("")

    # Denial resistance info
    score = denial_pack.get('overall_score', 0)
    rating = denial_pack.get('overall_rating', 'low')
    counts = denial_pack.get('resistance_counts', {})
    sections.append(f"Denial Resistance: {rating.upper()} ({score}/100)")
    sections.append(f"Step Distribution: High={counts.get('high', 0)}, Medium={counts.get('medium', 0)}, Low={counts.get('low', 0)}")
    sections.append("")

    # Line-item breakdown
    sections.append("LINE-ITEM R&I BREAKDOWN")
    for op in operations:
        op_name = op.get('display_name', 'Operation')
        op_time = op.get('totals', {}).get('total_time', 0)
        sections.append(f"  {op_name}: {op_time:.2f}h")
        for step in op.get('steps', [])[:5]:
            if step.get('included', True):
                step_label = step.get('label', '')
                step_hours = step.get('effective_time_hours', 0)
                sections.append(f"    - {step_label}: {step_hours:.2f}h")
    sections.append("")

    # Labor rate explanation
    sections.append("LABOR RATE")
    if labor_source == 'rule' and labor_rule_name:
        sections.append(f"Rate: ${labor_rate:.2f}/hr (Region Rule: {labor_rule_name})")
    elif labor_source == 'override':
        sections.append(f"Rate: ${labor_rate:.2f}/hr (Estimate Override)")
    else:
        sections.append(f"Rate: ${labor_rate:.2f}/hr (Default)")
    sections.append(f"Total R&I Time: {total_hours:.2f} hours")
    sections.append(f"Total R&I Cost: ${total_cost:.2f}")
    sections.append("")

    # Denial rebuttal (if provided)
    if denial_code:
        rebuttal = get_denial_rebuttal(estimate_id, tenant_id, denial_code)
        if rebuttal.get('success'):
            sections.append("DENIAL REBUTTAL")
            sections.append(f"Denial Type: {denial_code}")
            sections.append(f"Insurer Claim: {rebuttal.get('insurer_claim', '')}")
            sections.append("")
            sections.append("Rebuttal:")
            sections.append(rebuttal.get('rebuttal_summary', ''))
            sections.append("")
            sections.append("Key Points:")
            for bullet in rebuttal.get('rebuttal_bullets', []):
                sections.append(f"  - {bullet}")
            sections.append("")

    # Closing liability paragraph
    sections.append("CLOSING")
    sections.append(
        "The R&I operations documented above are required for proper vehicle access and restoration "
        "of OEM fitment and function. Each step is individually justified with time allocations based "
        "on industry-standard procedures. If any sub-step is disputed, the carrier is requested to "
        "identify the specific step and provide written justification for exclusion. Blanket denial "
        "of documented R&I operations without step-specific reasoning is not actionable and may "
        "result in incomplete repair or safety system compromise."
    )
    sections.append("")
    sections.append("If the carrier elects to exclude any documented step, written acknowledgment of the "
                   "resulting access, fitment, or safety limitations is requested before proceeding.")

    letter_text = "\n".join(sections)

    return {
        'success': True,
        'letter_text': letter_text,
        'estimate_number': estimate_number,
        'claim_number': claim_number,
        'vehicle': vehicle_str,
        'customer_name': customer_name,
        'total_ri_hours': total_hours,
        'total_ri_cost': total_cost,
        'labor_rate': labor_rate,
        'labor_source': labor_source,
        'denial_code': denial_code,
    }
