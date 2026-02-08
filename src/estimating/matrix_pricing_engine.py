"""
PDR Matrix Pricing Engine
Panel-based pricing using insurance company matrices.
Price is PER PANEL based on count range + majority size.

Key Concepts:
- Each insurance company has its own matrix
- Price lookup: panel + count range + majority size = base price
- Upcharges: aluminum +25%, HSS +25%, glue pull +25%, tall roof +25%
- Oversized dents: flat per-dent charge added AFTER multipliers
- CR (Conventional Repair) flags indicate when PDR is not recommended
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
import json

# Standard panel names
PANEL_NAMES = {
    'hood': 'Hood',
    'roof': 'Roof',
    'deck_lid': 'Deck Lid / Trunk',
    'lf_door': 'Left Front Door',
    'rf_door': 'Right Front Door',
    'lr_door': 'Left Rear Door',
    'rr_door': 'Right Rear Door',
    'l_fender': 'Left Fender',
    'r_fender': 'Right Fender',
    'l_quarter': 'Left Quarter Panel',
    'r_quarter': 'Right Quarter Panel',
    'l_roof_rail': 'Left Roof Rail',
    'r_roof_rail': 'Right Roof Rail',
    'metal_sunroof': 'Metal Sunroof',
    'cowl_other': 'Cowl / Other',
    'bedside_l': 'Left Bedside',
    'bedside_r': 'Right Bedside',
    'cab_corner_l': 'Left Cab Corner',
    'cab_corner_r': 'Right Cab Corner',
    'tailgate': 'Tailgate'
}

# Size labels for display
SIZE_LABELS = {
    'dime': 'Dime',
    'nickel': 'Nickel',
    'quarter': 'Quarter',
    'half': 'Half Dollar'
}

# Count ranges for matrix lookup
COUNT_RANGES = [
    (1, 5),
    (6, 15),
    (16, 30),
    (31, 50),
    (51, 75),
    (76, 100),
    (101, 150),
    (151, 200),
    (201, 250)
]


def get_count_range_label(count: int) -> str:
    """Get human-readable label for count range."""
    for min_val, max_val in COUNT_RANGES:
        if min_val <= count <= max_val:
            return f"{min_val}-{max_val}"
    return "250+"


def lookup_matrix_price(
    db_conn,
    matrix_profile_id: int,
    panel: str,
    dent_count: int,
    majority_size: str
) -> Dict:
    """
    Look up the matrix price for a panel.

    Args:
        db_conn: PostgreSQL connection
        matrix_profile_id: ID of the matrix profile to use
        panel: Panel name (e.g., 'hood', 'roof')
        dent_count: Total dent count on this panel
        majority_size: Majority dent size (dime, nickel, quarter, half)

    Returns:
        Dict with keys: price, is_cr, count_range, panel, size
    """
    cursor = db_conn.cursor()

    # Normalize size name
    size_column = f"price_{majority_size}"
    cr_column = f"is_cr_{majority_size}"

    # Find the count range row
    cursor.execute("""
        SELECT price_dime, price_nickel, price_quarter, price_half,
               is_cr_dime, is_cr_nickel, is_cr_quarter, is_cr_half,
               count_min, count_max
        FROM pdr_matrix_data
        WHERE matrix_profile_id = %s
          AND panel = %s
          AND count_min <= %s
          AND count_max >= %s
    """, (matrix_profile_id, panel.lower(), dent_count, dent_count))

    row = cursor.fetchone()

    if not row:
        # Try to find the highest count range for this panel
        cursor.execute("""
            SELECT price_dime, price_nickel, price_quarter, price_half,
                   is_cr_dime, is_cr_nickel, is_cr_quarter, is_cr_half,
                   count_min, count_max
            FROM pdr_matrix_data
            WHERE matrix_profile_id = %s AND panel = %s
            ORDER BY count_max DESC
            LIMIT 1
        """, (matrix_profile_id, panel.lower()))
        row = cursor.fetchone()

        if not row:
            return {
                'error': f"No matrix data found for panel '{panel}'",
                'price': None,
                'is_cr': True,
                'count_range': None
            }

    # Map size to column index
    size_map = {
        'dime': (0, 4),
        'nickel': (1, 5),
        'quarter': (2, 6),
        'half': (3, 7)
    }

    price_idx, cr_idx = size_map.get(majority_size, (1, 5))

    price = row[price_idx]
    is_cr = row[cr_idx] if row[cr_idx] is not None else False
    count_min = row[8]
    count_max = row[9]

    # If price is NULL, it means CR is required
    if price is None:
        is_cr = True

    return {
        'price': float(price) if price else None,
        'is_cr': is_cr,
        'count_range': f"{count_min}-{count_max}",
        'panel': panel,
        'size': majority_size,
        'dent_count': dent_count
    }


def get_matrix_profile(db_conn, profile_id: int) -> Optional[Dict]:
    """
    Get matrix profile with all multipliers.

    Args:
        db_conn: PostgreSQL connection
        profile_id: Matrix profile ID

    Returns:
        Dict with profile data or None
    """
    cursor = db_conn.cursor()

    cursor.execute("""
        SELECT id, tenant_id, name, is_default,
               oversized_charge, aluminum_multiplier, hss_multiplier,
               glue_pull_multiplier, tall_roof_multiplier,
               corrosion_per_panel, corrosion_max_vehicle, labor_rate, notes
        FROM pdr_matrix_profiles
        WHERE id = %s
    """, (profile_id,))

    row = cursor.fetchone()
    if not row:
        return None

    return {
        'id': row[0],
        'tenant_id': row[1],
        'name': row[2],
        'is_default': row[3],
        'oversized_charge': float(row[4]) if row[4] else 50.00,
        'aluminum_multiplier': float(row[5]) if row[5] else 1.25,
        'hss_multiplier': float(row[6]) if row[6] else 1.25,
        'glue_pull_multiplier': float(row[7]) if row[7] else 1.25,
        'tall_roof_multiplier': float(row[8]) if row[8] else 1.25,
        'corrosion_per_panel': float(row[9]) if row[9] else 10.00,
        'corrosion_max_vehicle': float(row[10]) if row[10] else 30.00,
        'labor_rate': float(row[11]) if row[11] else 75.00,
        'notes': row[12]
    }


def get_default_matrix_profile(db_conn, tenant_id: Optional[int] = None) -> Optional[Dict]:
    """Get the default matrix profile for a tenant or system default."""
    cursor = db_conn.cursor()

    # Try tenant default first
    if tenant_id:
        cursor.execute("""
            SELECT id FROM pdr_matrix_profiles
            WHERE tenant_id = %s AND is_default = TRUE
            LIMIT 1
        """, (tenant_id,))
        row = cursor.fetchone()
        if row:
            return get_matrix_profile(db_conn, row[0])

    # Fall back to system default
    cursor.execute("""
        SELECT id FROM pdr_matrix_profiles
        WHERE tenant_id IS NULL AND is_default = TRUE
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        return get_matrix_profile(db_conn, row[0])

    return None


def calculate_panel_total(
    db_conn,
    matrix_profile_id: int,
    panel: str,
    dent_count: int,
    majority_size: str,
    oversized_count: int = 0,
    is_aluminum: bool = False,
    is_hss: bool = False,
    requires_glue_pull: bool = False,
    is_tall_roof: bool = False
) -> Dict:
    """
    Calculate total price for a panel with all upcharges.

    Args:
        db_conn: PostgreSQL connection
        matrix_profile_id: Matrix profile to use
        panel: Panel name
        dent_count: Total dent count (not including oversized)
        majority_size: Majority dent size
        oversized_count: Number of oversized dents
        is_aluminum: Panel is aluminum
        is_hss: Panel is high-strength steel
        requires_glue_pull: Glue pull access required
        is_tall_roof: Tall roof vehicle (SUV, Van, Extended Cab)

    Returns:
        Dict with pricing breakdown
    """
    # Get matrix profile for multipliers
    profile = get_matrix_profile(db_conn, matrix_profile_id)
    if not profile:
        return {'error': 'Matrix profile not found', 'is_cr': True}

    # Get base price from matrix
    result = lookup_matrix_price(
        db_conn, matrix_profile_id, panel, dent_count, majority_size
    )

    if result.get('is_cr') or result.get('price') is None:
        return {
            'is_cr': True,
            'message': 'Conventional Repair Required',
            'panel': panel,
            'dent_count': dent_count,
            'majority_size': majority_size,
            'count_range': result.get('count_range')
        }

    base_price = Decimal(str(result['price']))
    upcharges = []
    multiplier_total = Decimal('1.0')

    # Apply multipliers (they stack multiplicatively)
    if is_aluminum:
        mult = Decimal(str(profile['aluminum_multiplier']))
        multiplier_total *= mult
        upcharges.append({
            'type': 'aluminum',
            'label': 'Aluminum Panel',
            'multiplier': float(mult),
            'percentage': f"+{int((mult - 1) * 100)}%"
        })

    if is_hss:
        mult = Decimal(str(profile['hss_multiplier']))
        multiplier_total *= mult
        upcharges.append({
            'type': 'hss',
            'label': 'High Strength Steel',
            'multiplier': float(mult),
            'percentage': f"+{int((mult - 1) * 100)}%"
        })

    if requires_glue_pull:
        mult = Decimal(str(profile['glue_pull_multiplier']))
        multiplier_total *= mult
        upcharges.append({
            'type': 'glue_pull',
            'label': 'Glue Pull Required',
            'multiplier': float(mult),
            'percentage': f"+{int((mult - 1) * 100)}%"
        })

    if is_tall_roof:
        mult = Decimal(str(profile['tall_roof_multiplier']))
        multiplier_total *= mult
        upcharges.append({
            'type': 'tall_roof',
            'label': 'Tall Roof Vehicle',
            'multiplier': float(mult),
            'percentage': f"+{int((mult - 1) * 100)}%"
        })

    # Calculate multiplied base price
    multiplied_price = base_price * multiplier_total
    multiplied_price = multiplied_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    # Add oversized dent charges AFTER multipliers
    oversized_charge = Decimal(str(profile['oversized_charge']))
    oversized_total = oversized_charge * oversized_count

    if oversized_count > 0:
        upcharges.append({
            'type': 'oversized',
            'label': f'Oversized Dents ({oversized_count})',
            'charge_each': float(oversized_charge),
            'count': oversized_count,
            'total': float(oversized_total)
        })

    panel_total = multiplied_price + oversized_total

    return {
        'panel': panel,
        'panel_display': PANEL_NAMES.get(panel.lower(), panel),
        'dent_count': dent_count,
        'majority_size': majority_size,
        'size_display': SIZE_LABELS.get(majority_size, majority_size),
        'count_range': result.get('count_range'),
        'matrix_base_price': float(base_price),
        'multiplier_total': float(multiplier_total),
        'multiplied_price': float(multiplied_price),
        'oversized_count': oversized_count,
        'oversized_charge_each': float(oversized_charge),
        'oversized_total': float(oversized_total),
        'upcharges': upcharges,
        'upcharge_total': float(multiplied_price - base_price + oversized_total),
        'panel_total': float(panel_total),
        'is_cr': False,
        'matrix_profile_id': matrix_profile_id,
        'matrix_profile_name': profile['name']
    }


def check_aluminum_panels(
    db_conn,
    make: str,
    model: Optional[str] = None,
    year: Optional[int] = None
) -> List[str]:
    """
    Check which panels are aluminum for a given vehicle.

    Args:
        db_conn: PostgreSQL connection
        make: Vehicle make
        model: Vehicle model (optional)
        year: Vehicle year (optional)

    Returns:
        List of panel names that are aluminum
    """
    cursor = db_conn.cursor()

    query = """
        SELECT aluminum_panels FROM vehicle_aluminum_panels
        WHERE LOWER(make) = LOWER(%s)
    """
    params = [make]

    if model:
        query += " AND (model IS NULL OR LOWER(model) = LOWER(%s))"
        params.append(model)

    if year:
        query += " AND (year_start IS NULL OR year_start <= %s)"
        query += " AND (year_end IS NULL OR year_end >= %s)"
        params.extend([year, year])

    query += " ORDER BY model DESC NULLS LAST LIMIT 1"

    cursor.execute(query, params)
    row = cursor.fetchone()

    if row and row[0]:
        panels = row[0] if isinstance(row[0], list) else json.loads(row[0])
        return panels

    return []


def calculate_estimate_totals(
    db_conn,
    estimate_id: int
) -> Dict:
    """
    Calculate complete estimate totals from all panels.

    Args:
        db_conn: PostgreSQL connection
        estimate_id: Estimate ID

    Returns:
        Dict with complete estimate breakdown
    """
    cursor = db_conn.cursor()

    # Get estimate with matrix profile
    cursor.execute("""
        SELECT matrix_profile_id, is_tall_roof_vehicle
        FROM pdr_estimates
        WHERE id = %s
    """, (estimate_id,))
    estimate = cursor.fetchone()

    if not estimate:
        return {'error': 'Estimate not found'}

    matrix_profile_id = estimate[0]
    is_tall_roof_vehicle = estimate[1] or False

    if not matrix_profile_id:
        # Get default profile
        profile = get_default_matrix_profile(db_conn)
        if profile:
            matrix_profile_id = profile['id']
        else:
            return {'error': 'No matrix profile set and no default found'}

    # Get all panels
    cursor.execute("""
        SELECT id, panel_name, total_dent_count, majority_size,
               oversized_count, is_aluminum, is_hss, requires_glue_pull, is_tall_roof
        FROM estimate_panels
        WHERE estimate_id = %s
    """, (estimate_id,))
    panels = cursor.fetchall()

    panel_results = []
    labor_total = Decimal('0')
    has_cr_panels = False

    for panel in panels:
        panel_id, panel_name, dent_count, majority_size, oversized_count, is_aluminum, is_hss, requires_glue_pull, is_tall_roof = panel

        # Use vehicle-level tall roof setting if panel doesn't override
        panel_tall_roof = is_tall_roof if is_tall_roof is not None else is_tall_roof_vehicle

        result = calculate_panel_total(
            db_conn,
            matrix_profile_id,
            panel_name,
            dent_count or 0,
            majority_size or 'nickel',
            oversized_count or 0,
            is_aluminum or False,
            is_hss or False,
            requires_glue_pull or False,
            panel_tall_roof
        )

        result['panel_id'] = panel_id
        panel_results.append(result)

        if result.get('is_cr'):
            has_cr_panels = True
        elif result.get('panel_total'):
            labor_total += Decimal(str(result['panel_total']))

            # Update panel in database
            cursor.execute("""
                UPDATE estimate_panels
                SET matrix_base_price = %s,
                    upcharge_total = %s,
                    panel_total = %s,
                    is_conventional_repair = %s
                WHERE id = %s
            """, (
                result.get('matrix_base_price'),
                result.get('upcharge_total'),
                result.get('panel_total'),
                result.get('is_cr', False),
                panel_id
            ))

    # Get R&I items total
    cursor.execute("""
        SELECT COALESCE(SUM(price), 0)
        FROM rin_items ri
        JOIN estimate_panels ep ON ep.id = ri.panel_id
        WHERE ep.estimate_id = %s
    """, (estimate_id,))
    ri_total = Decimal(str(cursor.fetchone()[0]))

    grand_total = labor_total + ri_total

    # Update estimate total
    cursor.execute("""
        UPDATE pdr_estimates
        SET total_price = %s, updated_at = NOW()
        WHERE id = %s
    """, (float(grand_total), estimate_id))

    db_conn.commit()

    return {
        'estimate_id': estimate_id,
        'matrix_profile_id': matrix_profile_id,
        'panels': panel_results,
        'panel_count': len(panels),
        'labor_total': float(labor_total),
        'ri_total': float(ri_total),
        'grand_total': float(grand_total),
        'has_cr_panels': has_cr_panels,
        'warning': 'One or more panels require conventional repair' if has_cr_panels else None
    }


def list_matrix_profiles(db_conn, tenant_id: Optional[int] = None) -> List[Dict]:
    """
    List all available matrix profiles.

    Args:
        db_conn: PostgreSQL connection
        tenant_id: Tenant ID (optional, also shows system profiles)

    Returns:
        List of matrix profiles
    """
    cursor = db_conn.cursor()

    query = """
        SELECT id, tenant_id, name, is_default,
               oversized_charge, aluminum_multiplier, hss_multiplier,
               glue_pull_multiplier, tall_roof_multiplier, labor_rate, notes
        FROM pdr_matrix_profiles
        WHERE tenant_id IS NULL
    """
    params = []

    if tenant_id:
        query += " OR tenant_id = %s"
        params.append(tenant_id)

    query += " ORDER BY is_default DESC, name"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    profiles = []
    for row in rows:
        profiles.append({
            'id': row[0],
            'tenant_id': row[1],
            'name': row[2],
            'is_default': row[3],
            'oversized_charge': float(row[4]) if row[4] else 50.00,
            'aluminum_multiplier': float(row[5]) if row[5] else 1.25,
            'hss_multiplier': float(row[6]) if row[6] else 1.25,
            'glue_pull_multiplier': float(row[7]) if row[7] else 1.25,
            'tall_roof_multiplier': float(row[8]) if row[8] else 1.25,
            'labor_rate': float(row[9]) if row[9] else 75.00,
            'notes': row[10],
            'is_system': row[1] is None
        })

    return profiles


def get_matrix_data_for_panel(
    db_conn,
    matrix_profile_id: int,
    panel: str
) -> List[Dict]:
    """
    Get complete matrix data for a panel (for display).

    Args:
        db_conn: PostgreSQL connection
        matrix_profile_id: Matrix profile ID
        panel: Panel name

    Returns:
        List of matrix rows for this panel
    """
    cursor = db_conn.cursor()

    cursor.execute("""
        SELECT count_min, count_max,
               price_dime, price_nickel, price_quarter, price_half,
               is_cr_dime, is_cr_nickel, is_cr_quarter, is_cr_half
        FROM pdr_matrix_data
        WHERE matrix_profile_id = %s AND panel = %s
        ORDER BY count_min
    """, (matrix_profile_id, panel.lower()))

    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            'count_range': f"{row[0]}-{row[1]}",
            'count_min': row[0],
            'count_max': row[1],
            'dime': {'price': float(row[2]) if row[2] else None, 'is_cr': row[6]},
            'nickel': {'price': float(row[3]) if row[3] else None, 'is_cr': row[7]},
            'quarter': {'price': float(row[4]) if row[4] else None, 'is_cr': row[8]},
            'half': {'price': float(row[5]) if row[5] else None, 'is_cr': row[9]}
        })

    return result


# Quick test
if __name__ == "__main__":
    print("PDR Matrix Pricing Engine")
    print("=" * 50)
    print("\nPanel Names:")
    for code, name in PANEL_NAMES.items():
        print(f"  {code}: {name}")

    print("\nSize Labels:")
    for code, name in SIZE_LABELS.items():
        print(f"  {code}: {name}")

    print("\nCount Ranges:")
    for min_val, max_val in COUNT_RANGES:
        print(f"  {min_val}-{max_val}")
