"""
PDR Matrix Pricing API Routes
Panel-based pricing using insurance company matrices.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import os

from .matrix_pricing_engine import (
    lookup_matrix_price,
    calculate_panel_total,
    calculate_estimate_totals,
    get_matrix_profile,
    get_default_matrix_profile,
    list_matrix_profiles,
    get_matrix_data_for_panel,
    check_aluminum_panels,
    PANEL_NAMES,
    SIZE_LABELS
)

# PostgreSQL configuration
import psycopg2
import psycopg2.extras

PG_CONFIG = {
    "host": os.environ.get('PG_HOST', '127.0.0.1'),
    "port": int(os.environ.get('PG_PORT', 5432)),
    "database": os.environ.get('PG_DATABASE', 'hailtracker_master'),
    "user": os.environ.get('PG_USER', 'hailtracker'),
    "password": os.environ.get('PG_PASSWORD', 'hailtracker_dev_2024')
}


def get_db():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(**PG_CONFIG)


def get_current_tenant_id():
    """Get tenant ID from JWT or default to 1 in DEV_MODE."""
    if hasattr(g, 'current_user') and g.current_user:
        return g.current_user.get('tenant_id', 1)
    return 1


# Create blueprint
matrix_bp = Blueprint('pdr_matrix', __name__, url_prefix='/api/pdr-estimates')


# =============================================================================
# MATRIX PROFILE ENDPOINTS
# =============================================================================

@matrix_bp.route('/matrix-profiles', methods=['GET'])
def list_profiles():
    """
    List all available matrix profiles.
    Returns system profiles + tenant custom profiles.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    profiles = list_matrix_profiles(conn, tenant_id)
    conn.close()

    return jsonify({
        "profiles": profiles,
        "count": len(profiles)
    })


@matrix_bp.route('/matrix-profiles/<int:profile_id>', methods=['GET'])
def get_profile(profile_id):
    """
    Get matrix profile with full matrix data.
    Query params: panel (optional - get data for specific panel)
    """
    panel = request.args.get('panel')

    conn = get_db()
    profile = get_matrix_profile(conn, profile_id)

    if not profile:
        conn.close()
        return jsonify({"error": "Matrix profile not found"}), 404

    # Get matrix data
    if panel:
        matrix_data = {panel: get_matrix_data_for_panel(conn, profile_id, panel)}
    else:
        # Get all panels
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT panel FROM pdr_matrix_data
            WHERE matrix_profile_id = %s
            ORDER BY panel
        """, (profile_id,))
        panels = [row[0] for row in cursor.fetchall()]

        matrix_data = {}
        for p in panels:
            matrix_data[p] = get_matrix_data_for_panel(conn, profile_id, p)

    conn.close()

    return jsonify({
        "profile": profile,
        "matrix_data": matrix_data,
        "panel_names": PANEL_NAMES,
        "size_labels": SIZE_LABELS
    })


@matrix_bp.route('/matrix-profiles', methods=['POST'])
def create_profile():
    """
    Create custom matrix profile (copy from existing).

    Body:
    {
        "name": "My Custom Profile",
        "copy_from_id": 1,  // optional - copy matrix data from another profile
        "oversized_charge": 55.00,
        "aluminum_multiplier": 1.30,
        "hss_multiplier": 1.25,
        "glue_pull_multiplier": 1.25,
        "tall_roof_multiplier": 1.30,
        "labor_rate": 80.00,
        "notes": "Custom pricing for my shop"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    if not data.get('name'):
        return jsonify({"error": "name required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Create profile
    cursor.execute("""
        INSERT INTO pdr_matrix_profiles (
            tenant_id, name, oversized_charge, aluminum_multiplier,
            hss_multiplier, glue_pull_multiplier, tall_roof_multiplier,
            labor_rate, notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, name
    """, (
        tenant_id,
        data['name'],
        data.get('oversized_charge', 50.00),
        data.get('aluminum_multiplier', 1.25),
        data.get('hss_multiplier', 1.25),
        data.get('glue_pull_multiplier', 1.25),
        data.get('tall_roof_multiplier', 1.25),
        data.get('labor_rate', 75.00),
        data.get('notes')
    ))

    new_profile = dict(cursor.fetchone())
    new_profile_id = new_profile['id']

    # Copy matrix data if requested
    copy_from_id = data.get('copy_from_id')
    if copy_from_id:
        cursor.execute("""
            INSERT INTO pdr_matrix_data (
                matrix_profile_id, panel, count_min, count_max,
                price_dime, price_nickel, price_quarter, price_half,
                is_cr_dime, is_cr_nickel, is_cr_quarter, is_cr_half
            )
            SELECT %s, panel, count_min, count_max,
                   price_dime, price_nickel, price_quarter, price_half,
                   is_cr_dime, is_cr_nickel, is_cr_quarter, is_cr_half
            FROM pdr_matrix_data
            WHERE matrix_profile_id = %s
        """, (new_profile_id, copy_from_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "profile": new_profile,
        "copied_from": copy_from_id
    }), 201


@matrix_bp.route('/matrix-profiles/<int:profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """
    Update matrix profile multipliers.
    Only tenant-owned profiles can be updated.
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT id FROM pdr_matrix_profiles
        WHERE id = %s AND tenant_id = %s
    """, (profile_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Profile not found or not editable"}), 404

    # Build update
    fields = ['name', 'oversized_charge', 'aluminum_multiplier', 'hss_multiplier',
              'glue_pull_multiplier', 'tall_roof_multiplier', 'labor_rate', 'notes']

    updates = []
    params = []
    for field in fields:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])

    if updates:
        updates.append("updated_at = NOW()")
        params.extend([profile_id, tenant_id])

        cursor.execute(f"""
            UPDATE pdr_matrix_profiles SET {', '.join(updates)}
            WHERE id = %s AND tenant_id = %s
            RETURNING *
        """, params)

        result = dict(cursor.fetchone())
        conn.commit()
        conn.close()

        return jsonify({"success": True, "profile": result})

    conn.close()
    return jsonify({"error": "No updates provided"}), 400


# =============================================================================
# MATRIX LOOKUP ENDPOINT
# =============================================================================

@matrix_bp.route('/matrix-lookup', methods=['POST'])
def matrix_lookup():
    """
    Calculate panel price using matrix.

    Body:
    {
        "matrix_profile_id": 1,
        "panel": "hood",
        "dent_count": 23,
        "majority_size": "nickel",
        "oversized_count": 2,
        "is_aluminum": false,
        "is_hss": false,
        "requires_glue_pull": false,
        "is_tall_roof": false
    }
    """
    data = request.get_json() or {}

    matrix_profile_id = data.get('matrix_profile_id')
    panel = data.get('panel')
    dent_count = data.get('dent_count', 0)
    majority_size = data.get('majority_size', 'nickel')

    if not panel:
        return jsonify({"error": "panel required"}), 400

    conn = get_db()

    # Get default profile if not specified
    if not matrix_profile_id:
        profile = get_default_matrix_profile(conn, get_current_tenant_id())
        if profile:
            matrix_profile_id = profile['id']
        else:
            conn.close()
            return jsonify({"error": "No matrix profile specified and no default found"}), 400

    result = calculate_panel_total(
        conn,
        matrix_profile_id,
        panel,
        dent_count,
        majority_size,
        data.get('oversized_count', 0),
        data.get('is_aluminum', False),
        data.get('is_hss', False),
        data.get('requires_glue_pull', False),
        data.get('is_tall_roof', False)
    )

    conn.close()

    return jsonify(result)


# =============================================================================
# PANEL ENTRY ENDPOINTS (Matrix-based)
# =============================================================================

@matrix_bp.route('/<int:estimate_id>/panels', methods=['POST'])
def add_panel_matrix(estimate_id):
    """
    Add panel to estimate with matrix-based pricing.

    Body:
    {
        "panel_name": "hood",
        "total_dent_count": 23,
        "majority_size": "nickel",
        "oversized_count": 2,
        "is_aluminum": false,
        "is_hss": false,
        "requires_glue_pull": false,
        "is_tall_roof": false
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    if not data.get('panel_name'):
        return jsonify({"error": "panel_name required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify estimate belongs to tenant and is draft
    cursor.execute("""
        SELECT status, matrix_profile_id, is_tall_roof_vehicle
        FROM pdr_estimates
        WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    if result['status'] not in ['draft', 'in_progress']:
        conn.close()
        return jsonify({"error": "Cannot modify approved/completed estimate"}), 400

    matrix_profile_id = result['matrix_profile_id']
    is_tall_roof_vehicle = result['is_tall_roof_vehicle'] or False

    # Get default profile if not set
    if not matrix_profile_id:
        profile = get_default_matrix_profile(conn, tenant_id)
        if profile:
            matrix_profile_id = profile['id']
            # Update estimate with default profile
            cursor.execute("""
                UPDATE pdr_estimates SET matrix_profile_id = %s WHERE id = %s
            """, (matrix_profile_id, estimate_id))

    panel_name = data['panel_name'].lower().replace(" ", "_")
    total_dent_count = data.get('total_dent_count', 0)
    majority_size = data.get('majority_size', 'nickel')
    oversized_count = data.get('oversized_count', 0)
    is_aluminum = data.get('is_aluminum', False)
    is_hss = data.get('is_hss', False)
    requires_glue_pull = data.get('requires_glue_pull', False)
    is_tall_roof = data.get('is_tall_roof', is_tall_roof_vehicle)

    # Calculate price
    pricing = calculate_panel_total(
        conn,
        matrix_profile_id,
        panel_name,
        total_dent_count,
        majority_size,
        oversized_count,
        is_aluminum,
        is_hss,
        requires_glue_pull,
        is_tall_roof
    )

    # Insert panel
    cursor.execute("""
        INSERT INTO estimate_panels (
            estimate_id, panel_name, total_dent_count, majority_size,
            oversized_count, is_aluminum, is_hss, requires_glue_pull, is_tall_roof,
            is_conventional_repair, matrix_base_price, upcharge_total, panel_total
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        estimate_id,
        panel_name,
        total_dent_count,
        majority_size,
        oversized_count,
        is_aluminum,
        is_hss,
        requires_glue_pull,
        is_tall_roof,
        pricing.get('is_cr', False),
        pricing.get('matrix_base_price'),
        pricing.get('upcharge_total'),
        pricing.get('panel_total')
    ))

    panel = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    # Convert decimals
    for key in ['matrix_base_price', 'upcharge_total', 'panel_total']:
        if panel.get(key):
            panel[key] = float(panel[key])

    return jsonify({
        "success": True,
        "panel": panel,
        "pricing": pricing
    }), 201


@matrix_bp.route('/<int:estimate_id>/panels/<int:panel_id>', methods=['PUT'])
def update_panel_matrix(estimate_id, panel_id):
    """
    Update panel with matrix-based pricing.

    Body: Same as add_panel_matrix
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT ep.id, pe.status, pe.matrix_profile_id, pe.is_tall_roof_vehicle
        FROM estimate_panels ep
        JOIN pdr_estimates pe ON pe.id = ep.estimate_id
        WHERE ep.id = %s AND ep.estimate_id = %s AND pe.tenant_id = %s
    """, (panel_id, estimate_id, tenant_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Panel not found"}), 404

    if result['status'] not in ['draft', 'in_progress']:
        conn.close()
        return jsonify({"error": "Cannot modify approved estimate"}), 400

    matrix_profile_id = result['matrix_profile_id']
    is_tall_roof_vehicle = result['is_tall_roof_vehicle'] or False

    # Build update
    panel_name = data.get('panel_name', '').lower().replace(" ", "_") if data.get('panel_name') else None
    total_dent_count = data.get('total_dent_count')
    majority_size = data.get('majority_size')
    oversized_count = data.get('oversized_count')
    is_aluminum = data.get('is_aluminum')
    is_hss = data.get('is_hss')
    requires_glue_pull = data.get('requires_glue_pull')
    is_tall_roof = data.get('is_tall_roof')

    # Get current values for non-updated fields
    cursor.execute("""
        SELECT panel_name, total_dent_count, majority_size, oversized_count,
               is_aluminum, is_hss, requires_glue_pull, is_tall_roof
        FROM estimate_panels WHERE id = %s
    """, (panel_id,))
    current = cursor.fetchone()

    # Use current values for unchanged fields
    final_panel_name = panel_name or current[0]
    final_dent_count = total_dent_count if total_dent_count is not None else (current[1] or 0)
    final_majority_size = majority_size or current[2] or 'nickel'
    final_oversized = oversized_count if oversized_count is not None else (current[3] or 0)
    final_aluminum = is_aluminum if is_aluminum is not None else (current[4] or False)
    final_hss = is_hss if is_hss is not None else (current[5] or False)
    final_glue = requires_glue_pull if requires_glue_pull is not None else (current[6] or False)
    final_tall = is_tall_roof if is_tall_roof is not None else (current[7] if current[7] is not None else is_tall_roof_vehicle)

    # Recalculate price
    pricing = calculate_panel_total(
        conn,
        matrix_profile_id,
        final_panel_name,
        final_dent_count,
        final_majority_size,
        final_oversized,
        final_aluminum,
        final_hss,
        final_glue,
        final_tall
    )

    # Update panel
    cursor.execute("""
        UPDATE estimate_panels SET
            panel_name = %s,
            total_dent_count = %s,
            majority_size = %s,
            oversized_count = %s,
            is_aluminum = %s,
            is_hss = %s,
            requires_glue_pull = %s,
            is_tall_roof = %s,
            is_conventional_repair = %s,
            matrix_base_price = %s,
            upcharge_total = %s,
            panel_total = %s
        WHERE id = %s
        RETURNING *
    """, (
        final_panel_name,
        final_dent_count,
        final_majority_size,
        final_oversized,
        final_aluminum,
        final_hss,
        final_glue,
        final_tall,
        pricing.get('is_cr', False),
        pricing.get('matrix_base_price'),
        pricing.get('upcharge_total'),
        pricing.get('panel_total'),
        panel_id
    ))

    panel = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    # Convert decimals
    for key in ['matrix_base_price', 'upcharge_total', 'panel_total']:
        if panel.get(key):
            panel[key] = float(panel[key])

    return jsonify({
        "success": True,
        "panel": panel,
        "pricing": pricing
    })


@matrix_bp.route('/<int:estimate_id>/panels/<int:panel_id>', methods=['DELETE'])
def delete_panel(estimate_id, panel_id):
    """Delete panel from estimate."""
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM estimate_panels
        WHERE id = %s AND estimate_id = %s
        AND estimate_id IN (
            SELECT id FROM pdr_estimates
            WHERE tenant_id = %s AND status IN ('draft', 'in_progress')
        )
        RETURNING id
    """, (panel_id, estimate_id, tenant_id))

    result = cursor.fetchone()
    conn.commit()
    conn.close()

    if result:
        return jsonify({"success": True, "deleted_id": panel_id})
    return jsonify({"error": "Panel not found or cannot be deleted"}), 404


# =============================================================================
# ESTIMATE TOTALS
# =============================================================================

@matrix_bp.route('/<int:estimate_id>/calculate-matrix', methods=['POST'])
def calculate_matrix_totals(estimate_id):
    """
    Recalculate estimate totals using matrix pricing.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor()

    # Verify ownership
    cursor.execute("""
        SELECT id FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    totals = calculate_estimate_totals(conn, estimate_id)
    conn.close()

    return jsonify(totals)


# =============================================================================
# ALUMINUM CHECK
# =============================================================================

@matrix_bp.route('/check-aluminum', methods=['GET'])
def check_aluminum():
    """
    Check which panels are aluminum for a vehicle.
    Query params: make (required), model (optional), year (optional)
    """
    make = request.args.get('make')
    model = request.args.get('model')
    year = request.args.get('year', type=int)

    if not make:
        return jsonify({"error": "make parameter required"}), 400

    conn = get_db()
    aluminum_panels = check_aluminum_panels(conn, make, model, year)
    conn.close()

    return jsonify({
        "make": make,
        "model": model,
        "year": year,
        "aluminum_panels": aluminum_panels,
        "has_aluminum": len(aluminum_panels) > 0
    })


# =============================================================================
# ESTIMATE MATRIX PROFILE ASSIGNMENT
# =============================================================================

@matrix_bp.route('/<int:estimate_id>/set-matrix-profile', methods=['PUT'])
def set_estimate_matrix_profile(estimate_id):
    """
    Set the matrix profile for an estimate.

    Body:
    {
        "matrix_profile_id": 1,
        "is_tall_roof_vehicle": false
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    matrix_profile_id = data.get('matrix_profile_id')
    is_tall_roof = data.get('is_tall_roof_vehicle')

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT id, status FROM pdr_estimates
        WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    # Update
    updates = []
    params = []

    if matrix_profile_id is not None:
        updates.append("matrix_profile_id = %s")
        params.append(matrix_profile_id)

    if is_tall_roof is not None:
        updates.append("is_tall_roof_vehicle = %s")
        params.append(is_tall_roof)

    if updates:
        updates.append("updated_at = NOW()")
        params.extend([estimate_id, tenant_id])

        cursor.execute(f"""
            UPDATE pdr_estimates SET {', '.join(updates)}
            WHERE id = %s AND tenant_id = %s
            RETURNING id, matrix_profile_id, is_tall_roof_vehicle
        """, params)

        estimate = dict(cursor.fetchone())
        conn.commit()

        # Recalculate all panels if profile changed
        if matrix_profile_id is not None:
            calculate_estimate_totals(conn, estimate_id)

        conn.close()

        return jsonify({
            "success": True,
            "estimate": estimate
        })

    conn.close()
    return jsonify({"error": "No updates provided"}), 400


# =============================================================================
# REFERENCE DATA
# =============================================================================

@matrix_bp.route('/panels', methods=['GET'])
def list_panels():
    """Get list of standard panel names."""
    return jsonify({
        "panels": PANEL_NAMES,
        "sizes": SIZE_LABELS
    })
