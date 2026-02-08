"""
PDR Estimate API Routes
Fast dent-based estimating with zone multipliers and auto R&I suggestions.
All routes are tenant-scoped.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import psycopg2
import psycopg2.extras
import os
import json

from .pricing_engine import (
    PricingEngine,
    calculate_estimate_total,
    get_tenant_pricing_config,
    create_pricing_profile,
    get_default_config,
    get_ri_library_items,
    get_ri_operation,
    get_vehicle_tier,
    TIER_MULTIPLIERS
)

# Create blueprint
pdr_estimates_bp = Blueprint('pdr_estimates', __name__, url_prefix='/api/pdr-estimates')

# PostgreSQL configuration
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


def login_required_wrapper(f):
    """Wrapper to check authentication."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        # Import here to avoid circular imports
        try:
            from auth.auth_middleware import login_required
            # Apply the real decorator
            return login_required(f)(*args, **kwargs)
        except ImportError:
            # Fallback for testing
            return f(*args, **kwargs)
    return decorated


def generate_estimate_number(cursor, tenant_id):
    """Generate unique estimate number: PDR-2024-0001."""
    year = datetime.now().year
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM pdr_estimates
        WHERE tenant_id = %s AND estimate_number LIKE %s
    """, (tenant_id, f"PDR-{year}-%"))
    result = cursor.fetchone()
    count = (result['cnt'] if result else 0) + 1
    return f"PDR-{year}-{count:04d}"


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/calculate-price', methods=['POST'])
def calculate_price():
    """
    Calculate price for a single dent with enhanced size/depth options.
    Request body: {size, zone, depth, panel_name, material}

    Sizes: dime, nickel, quarter, half_dollar, silver_dollar, oversized
           (also supports legacy: small, medium, large, xlarge)
    Zones: center, edge, crease, body_line
    Depths: shallow, medium, deep, severe
    """
    data = request.get_json()
    size = data.get('size', 'medium')
    zone = data.get('zone', 'center')
    depth = data.get('depth', 'medium')
    panel_name = data.get('panel_name', 'hood')
    material = data.get('material', 'steel')

    engine = PricingEngine()
    panel_difficulty = engine.get_panel_difficulty(panel_name)
    material_modifier = engine.get_material_modifier(material)

    price, breakdown = engine.calculate_dent_price(
        size=size,
        zone=zone,
        depth=depth,
        panel_difficulty=panel_difficulty,
        material_modifier=material_modifier
    )

    return jsonify({
        "price": float(price),
        "size": size,
        "zone": zone,
        "depth": depth,
        "panel_name": panel_name,
        "material": material,
        "breakdown": breakdown
    })


# =============================================================================
# ESTIMATE ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('', methods=['GET'])
def list_estimates():
    """
    List estimates for current tenant.
    Query params: status, page, per_page
    """
    tenant_id = get_current_tenant_id()
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    offset = (page - 1) * per_page

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Build query
    where = "WHERE tenant_id = %s"
    params = [tenant_id]
    if status:
        where += " AND status = %s"
        params.append(status)

    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM pdr_estimates {where}", params)
    total = cursor.fetchone()['count']

    # Get estimates
    cursor.execute(f"""
        SELECT id, estimate_number, vehicle_year, vehicle_make, vehicle_model,
               customer_name, status, total_price, created_at, updated_at
        FROM pdr_estimates
        {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])

    estimates = cursor.fetchall()

    # Convert to serializable format
    result = []
    for est in estimates:
        item = dict(est)
        if item.get('created_at'):
            item['created_at'] = item['created_at'].isoformat()
        if item.get('updated_at'):
            item['updated_at'] = item['updated_at'].isoformat()
        if item.get('total_price'):
            item['total_price'] = float(item['total_price'])
        result.append(item)

    conn.close()

    return jsonify({
        "estimates": result,
        "total": total,
        "page": page,
        "per_page": per_page,
        "tenant_id": tenant_id
    })


@pdr_estimates_bp.route('', methods=['POST'])
def create_estimate():
    """
    Create new estimate.

    Body:
    {
        "vehicle_year": 2023,
        "vehicle_make": "Ford",
        "vehicle_model": "F-150",
        "vin": "optional",
        "customer_name": "John Smith",
        "customer_phone": "555-1234",
        "customer_email": "john@example.com"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Generate estimate number
    estimate_number = generate_estimate_number(cursor, tenant_id)

    cursor.execute("""
        INSERT INTO pdr_estimates (
            tenant_id, estimate_number, vehicle_year, vehicle_make, vehicle_model,
            vin, customer_name, customer_phone, customer_email, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')
        RETURNING *
    """, (
        tenant_id,
        estimate_number,
        data.get('vehicle_year'),
        data.get('vehicle_make'),
        data.get('vehicle_model'),
        data.get('vin'),
        data.get('customer_name'),
        data.get('customer_phone'),
        data.get('customer_email')
    ))

    estimate = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    # Convert datetime
    if estimate.get('created_at'):
        estimate['created_at'] = estimate['created_at'].isoformat()
    if estimate.get('updated_at'):
        estimate['updated_at'] = estimate['updated_at'].isoformat()

    return jsonify({"success": True, "estimate": estimate}), 201


@pdr_estimates_bp.route('/<int:estimate_id>', methods=['GET'])
def get_estimate(estimate_id):
    """
    Get estimate with all panels, dents, and R&I items.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get estimate
    cursor.execute("""
        SELECT * FROM pdr_estimates
        WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    estimate = dict(estimate)

    # Get panels with dents and R&I
    cursor.execute("""
        SELECT * FROM estimate_panels WHERE estimate_id = %s ORDER BY created_at
    """, (estimate_id,))
    panels = cursor.fetchall()

    panel_list = []
    for panel in panels:
        panel_dict = dict(panel)

        # Get dents
        cursor.execute("""
            SELECT * FROM dents WHERE panel_id = %s ORDER BY created_at
        """, (panel['id'],))
        panel_dict['dents'] = [dict(d) for d in cursor.fetchall()]

        # Get R&I items
        cursor.execute("""
            SELECT * FROM rin_items WHERE panel_id = %s ORDER BY created_at
        """, (panel['id'],))
        panel_dict['rin_items'] = [dict(r) for r in cursor.fetchall()]

        # Convert decimals
        for d in panel_dict['dents']:
            if d.get('base_price'):
                d['base_price'] = float(d['base_price'])
            if d.get('final_price'):
                d['final_price'] = float(d['final_price'])
            if d.get('multiplier'):
                d['multiplier'] = float(d['multiplier'])

        for r in panel_dict['rin_items']:
            if r.get('price'):
                r['price'] = float(r['price'])
            if r.get('time_hours'):
                r['time_hours'] = float(r['time_hours'])

        if panel_dict.get('panel_difficulty'):
            panel_dict['panel_difficulty'] = float(panel_dict['panel_difficulty'])
        if panel_dict.get('material_modifier'):
            panel_dict['material_modifier'] = float(panel_dict['material_modifier'])
        if panel_dict.get('panel_total'):
            panel_dict['panel_total'] = float(panel_dict['panel_total'])

        panel_list.append(panel_dict)

    estimate['panels'] = panel_list

    # Convert estimate fields
    if estimate.get('created_at'):
        estimate['created_at'] = estimate['created_at'].isoformat()
    if estimate.get('updated_at'):
        estimate['updated_at'] = estimate['updated_at'].isoformat()
    if estimate.get('approved_at'):
        estimate['approved_at'] = estimate['approved_at'].isoformat()
    if estimate.get('total_price'):
        estimate['total_price'] = float(estimate['total_price'])

    conn.close()

    return jsonify(estimate)


@pdr_estimates_bp.route('/<int:estimate_id>', methods=['PUT'])
def update_estimate(estimate_id):
    """
    Update estimate (only if status=draft).
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Check status
    cursor.execute("""
        SELECT status FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    if result['status'] != 'draft':
        conn.close()
        return jsonify({"error": "Cannot modify approved/completed estimate"}), 400

    # Build update
    fields = ['vehicle_year', 'vehicle_make', 'vehicle_model', 'vin',
              'customer_name', 'customer_phone', 'customer_email', 'notes']

    updates = []
    params = []
    for field in fields:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])

    if updates:
        updates.append("updated_at = NOW()")
        params.extend([estimate_id, tenant_id])

        cursor.execute(f"""
            UPDATE pdr_estimates SET {', '.join(updates)}
            WHERE id = %s AND tenant_id = %s
            RETURNING *
        """, params)

        estimate = dict(cursor.fetchone())
        conn.commit()
    else:
        cursor.execute("""
            SELECT * FROM pdr_estimates WHERE id = %s AND tenant_id = %s
        """, (estimate_id, tenant_id))
        estimate = dict(cursor.fetchone())

    conn.close()

    if estimate.get('created_at'):
        estimate['created_at'] = estimate['created_at'].isoformat()
    if estimate.get('updated_at'):
        estimate['updated_at'] = estimate['updated_at'].isoformat()

    return jsonify({"success": True, "estimate": estimate})


# =============================================================================
# PANEL ENDPOINTS
# =============================================================================

# NOTE: Panel adding is now handled by matrix_routes.py with matrix-based pricing
# The old per-dent add_panel route has been deprecated in favor of matrix-based panel entry
# See: src/estimating/matrix_routes.py - add_panel_matrix()
#
# @pdr_estimates_bp.route('/<int:estimate_id>/panels', methods=['POST'])
# def add_panel(estimate_id):
#     """DEPRECATED - Use matrix_routes.py add_panel_matrix instead"""
#     pass


# =============================================================================
# DENT ENDPOINTS (THE SPEED FEATURE)
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/panels/<int:panel_id>/dents', methods=['POST'])
def add_dent(estimate_id, panel_id):
    """
    Add single dent to panel. Instant - no confirmation needed.

    Body:
    {
        "zone": "center",    // center, edge, crease, body_line
        "size": "quarter",   // dime, nickel, quarter, half_dollar, silver_dollar, oversized
                             // (also supports legacy: small, medium, large, xlarge)
        "depth": "medium"    // shallow, medium, deep, severe
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    zone = data.get('zone', 'center')
    size = data.get('size', 'medium')
    depth = data.get('depth', 'medium')

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT ep.panel_difficulty, ep.material_modifier, ep.panel_name,
               pe.status, pe.vehicle_make, pe.vehicle_model
        FROM estimate_panels ep
        JOIN pdr_estimates pe ON pe.id = ep.estimate_id
        WHERE ep.id = %s AND ep.estimate_id = %s AND pe.tenant_id = %s
    """, (panel_id, estimate_id, tenant_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Panel not found"}), 404

    if result['status'] != 'draft':
        conn.close()
        return jsonify({"error": "Cannot modify approved estimate"}), 400

    # Calculate price
    config = get_tenant_pricing_config(conn, tenant_id)
    engine = PricingEngine(config)

    price, breakdown = engine.calculate_dent_price(
        size=size,
        zone=zone,
        depth=depth,
        panel_difficulty=float(result['panel_difficulty']),
        material_modifier=float(result['material_modifier'])
    )

    # Calculate total multiplier
    total_multiplier = (breakdown['zone_multiplier'] * breakdown['depth_multiplier'] *
                       breakdown['panel_difficulty'] * breakdown['material_modifier'])

    cursor.execute("""
        INSERT INTO dents (panel_id, zone, size, depth, complexity, multiplier, reason, base_price, final_price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        panel_id, zone, size, depth,
        breakdown['complexity'],
        total_multiplier,
        breakdown['reason'],
        breakdown['base_price'],
        float(price)
    ))

    dent = dict(cursor.fetchone())

    # Update panel total
    cursor.execute("""
        UPDATE estimate_panels SET panel_total = (
            SELECT COALESCE(SUM(final_price), 0) FROM dents WHERE panel_id = %s
        ) WHERE id = %s
    """, (panel_id, panel_id))

    conn.commit()

    # Get R&I suggestions with vehicle tier
    vehicle_tier = get_vehicle_tier(conn, result['vehicle_make'], result['vehicle_model'])
    ri_library_items = get_ri_library_items(conn, tenant_id)
    suggestions = engine.suggest_ri_for_panel(result['panel_name'], [zone], ri_library_items)

    # Enhance suggestions with time calculations
    for suggestion in suggestions:
        op = next((item for item in ri_library_items
                   if item['operation_code'] == suggestion['operation_code']), None)
        if op:
            adjusted_time, _ = engine.calculate_ri_time(
                operation_code=suggestion['operation_code'],
                vehicle_tier=vehicle_tier,
                scope_level='typical',
                ri_library=op
            )
            suggestion['adjusted_time'] = adjusted_time
            suggestion['vehicle_tier'] = vehicle_tier

    conn.close()

    dent['base_price'] = float(dent['base_price'])
    dent['final_price'] = float(dent['final_price'])
    dent['multiplier'] = float(dent['multiplier'])

    return jsonify({
        "success": True,
        "dent": dent,
        "breakdown": breakdown,
        "vehicle_tier": vehicle_tier,
        "rin_suggestions": suggestions
    }), 201


@pdr_estimates_bp.route('/<int:estimate_id>/panels/<int:panel_id>/dents/batch', methods=['POST'])
def add_dents_batch(estimate_id, panel_id):
    """
    Add multiple dents at once (quick-add feature).

    Body (option 1 - count-based):
    {
        "zone": "center",
        "dents": [
            {"size": "quarter", "count": 5, "depth": "shallow"},
            {"size": "half_dollar", "count": 3, "depth": "medium"},
            {"size": "silver_dollar", "count": 2, "depth": "deep"}
        ]
    }

    Body (option 2 - individual dents):
    {
        "dents": [
            {"size": "quarter", "zone": "center", "depth": "shallow"},
            {"size": "quarter", "zone": "center", "depth": "medium"},
            {"size": "nickel", "zone": "edge", "depth": "deep"},
            {"size": "half_dollar", "zone": "crease", "depth": "severe"}
        ]
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    default_zone = data.get('zone', 'center')
    default_depth = data.get('depth', 'medium')
    dent_specs = data.get('dents', [])

    if not dent_specs:
        return jsonify({"error": "dents array required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT ep.panel_difficulty, ep.material_modifier, ep.panel_name,
               pe.status, pe.vehicle_make, pe.vehicle_model
        FROM estimate_panels ep
        JOIN pdr_estimates pe ON pe.id = ep.estimate_id
        WHERE ep.id = %s AND ep.estimate_id = %s AND pe.tenant_id = %s
    """, (panel_id, estimate_id, tenant_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Panel not found"}), 404

    if result['status'] != 'draft':
        conn.close()
        return jsonify({"error": "Cannot modify approved estimate"}), 400

    config = get_tenant_pricing_config(conn, tenant_id)
    engine = PricingEngine(config)

    added_dents = []
    zones_used = set()
    total_price = 0

    for spec in dent_specs:
        size = spec.get('size', 'medium')
        zone = spec.get('zone', default_zone)
        depth = spec.get('depth', default_depth)
        count = spec.get('count', 1)
        zones_used.add(zone)

        for _ in range(count):
            price, breakdown = engine.calculate_dent_price(
                size=size,
                zone=zone,
                depth=depth,
                panel_difficulty=float(result['panel_difficulty']),
                material_modifier=float(result['material_modifier'])
            )

            total_multiplier = (breakdown['zone_multiplier'] * breakdown['depth_multiplier'] *
                               breakdown['panel_difficulty'] * breakdown['material_modifier'])

            cursor.execute("""
                INSERT INTO dents (panel_id, zone, size, depth, complexity, multiplier, reason, base_price, final_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                panel_id, zone, size, depth,
                breakdown['complexity'],
                total_multiplier,
                breakdown['reason'],
                breakdown['base_price'],
                float(price)
            ))
            added_dents.append(cursor.fetchone()['id'])
            total_price += float(price)

    # Update panel total
    cursor.execute("""
        UPDATE estimate_panels SET panel_total = (
            SELECT COALESCE(SUM(final_price), 0) FROM dents WHERE panel_id = %s
        ) WHERE id = %s
    """, (panel_id, panel_id))

    conn.commit()

    # Get R&I suggestions with vehicle tier
    vehicle_tier = get_vehicle_tier(conn, result['vehicle_make'], result['vehicle_model'])
    ri_library_items = get_ri_library_items(conn, tenant_id)
    suggestions = engine.suggest_ri_for_panel(result['panel_name'], list(zones_used), ri_library_items)

    # Enhance suggestions with time calculations
    for suggestion in suggestions:
        op = next((item for item in ri_library_items
                   if item['operation_code'] == suggestion['operation_code']), None)
        if op:
            adjusted_time, _ = engine.calculate_ri_time(
                operation_code=suggestion['operation_code'],
                vehicle_tier=vehicle_tier,
                scope_level='typical',
                ri_library=op
            )
            suggestion['adjusted_time'] = adjusted_time
            suggestion['vehicle_tier'] = vehicle_tier

    conn.close()

    return jsonify({
        "success": True,
        "count": len(added_dents),
        "dent_ids": added_dents,
        "batch_total": total_price,
        "zones_worked": list(zones_used),
        "vehicle_tier": vehicle_tier,
        "rin_suggestions": suggestions
    }), 201


# =============================================================================
# R&I ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/panels/<int:panel_id>/rin', methods=['POST'])
def add_rin_item(estimate_id, panel_id):
    """
    Add R&I item to panel.

    Body:
    {
        "item_name": "door_handle_removal",
        "price": 25,       // optional, uses default
        "time_hours": 0.25 // optional, uses default
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    if not data.get('item_name'):
        return jsonify({"error": "item_name required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT pe.status FROM estimate_panels ep
        JOIN pdr_estimates pe ON pe.id = ep.estimate_id
        WHERE ep.id = %s AND ep.estimate_id = %s AND pe.tenant_id = %s
    """, (panel_id, estimate_id, tenant_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Panel not found"}), 404

    if result['status'] != 'draft':
        conn.close()
        return jsonify({"error": "Cannot modify approved estimate"}), 400

    # Get default price/time from config
    config = get_tenant_pricing_config(conn, tenant_id)
    rin_items = config.get('rin_items', {})
    item_defaults = rin_items.get(data['item_name'], {"price": 25, "time": 0.25})

    price = data.get('price', item_defaults['price'])
    time_hours = data.get('time_hours', item_defaults['time'])

    cursor.execute("""
        INSERT INTO rin_items (panel_id, item_name, price, time_hours)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """, (panel_id, data['item_name'], price, time_hours))

    rin_item = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    rin_item['price'] = float(rin_item['price'])
    rin_item['time_hours'] = float(rin_item['time_hours'])

    return jsonify({"success": True, "rin_item": rin_item}), 201


# =============================================================================
# APPROVAL & WORKFLOW ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/calculate', methods=['POST'])
def calculate_total(estimate_id):
    """
    Recalculate and return estimate total.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT id FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    totals = calculate_estimate_total(conn, estimate_id)
    conn.close()

    return jsonify(totals)


@pdr_estimates_bp.route('/<int:estimate_id>/approve', methods=['POST'])
def approve_estimate(estimate_id):
    """
    Lock estimate and store approval signature.

    Body:
    {
        "signature": "base64_image_data"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership and status
    cursor.execute("""
        SELECT status FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    if result['status'] != 'draft':
        conn.close()
        return jsonify({"error": "Estimate already approved or completed"}), 400

    # Calculate final total
    calculate_estimate_total(conn, estimate_id)

    # Update status
    cursor.execute("""
        UPDATE pdr_estimates
        SET status = 'approved', approved_at = NOW(), approved_signature = %s
        WHERE id = %s AND tenant_id = %s
        RETURNING *
    """, (data.get('signature'), estimate_id, tenant_id))

    estimate = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    if estimate.get('approved_at'):
        estimate['approved_at'] = estimate['approved_at'].isoformat()
    if estimate.get('total_price'):
        estimate['total_price'] = float(estimate['total_price'])

    return jsonify({"success": True, "estimate": estimate})


@pdr_estimates_bp.route('/<int:estimate_id>/work-order', methods=['POST'])
def create_work_order(estimate_id):
    """
    Create work order from approved estimate.

    Body:
    {
        "technician_id": 1  // optional
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify estimate is approved
    cursor.execute("""
        SELECT status FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    if result['status'] not in ['approved', 'draft']:
        conn.close()
        return jsonify({"error": "Work order already exists or estimate not approved"}), 400

    cursor.execute("""
        INSERT INTO work_orders (estimate_id, technician_id, status, tenant_id)
        VALUES (%s, %s, 'assigned', %s)
        RETURNING *
    """, (estimate_id, data.get('technician_id'), tenant_id))

    work_order = dict(cursor.fetchone())

    # Update estimate status
    cursor.execute("""
        UPDATE pdr_estimates SET status = 'in_progress' WHERE id = %s
    """, (estimate_id,))

    conn.commit()
    conn.close()

    if work_order.get('created_at'):
        work_order['created_at'] = work_order['created_at'].isoformat()

    return jsonify({"success": True, "work_order": work_order}), 201


# =============================================================================
# WORK ORDER & DISCOVERY ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/work-orders/<int:work_order_id>/discoveries', methods=['POST'])
def add_discovery(work_order_id):
    """
    Add discovery event during repair.

    Body:
    {
        "type": "handle_interference",  // handle_interference, liner_removal, hidden_damage, etc.
        "description": "Door handle interferes with dent access",
        "dent_id": 123,           // optional: specific dent this relates to
        "additional_time_hours": 0.5,
        "additional_cost": 35,
        "photo_url": "optional"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    if not data.get('type'):
        return jsonify({"error": "type required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify work order belongs to tenant
    cursor.execute("""
        SELECT wo.id FROM work_orders wo
        JOIN pdr_estimates pe ON pe.id = wo.estimate_id
        WHERE wo.id = %s AND pe.tenant_id = %s
    """, (work_order_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Work order not found"}), 404

    cursor.execute("""
        INSERT INTO discovery_events (
            work_order_id, type, description, dent_id,
            additional_time_hours, additional_cost, photo_url
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (
        work_order_id,
        data['type'],
        data.get('description'),
        data.get('dent_id'),
        data.get('additional_time_hours', 0),
        data.get('additional_cost', 0),
        data.get('photo_url')
    ))

    discovery = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    if discovery.get('created_at'):
        discovery['created_at'] = discovery['created_at'].isoformat()
    if discovery.get('additional_time_hours'):
        discovery['additional_time_hours'] = float(discovery['additional_time_hours'])
    if discovery.get('additional_cost'):
        discovery['additional_cost'] = float(discovery['additional_cost'])

    return jsonify({"success": True, "discovery": discovery}), 201


@pdr_estimates_bp.route('/<int:estimate_id>/supplement', methods=['GET'])
def get_supplement(estimate_id):
    """
    Generate supplement from discoveries.
    Returns delta, evidence chain, and narrative.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get estimate and work order
    cursor.execute("""
        SELECT pe.*, wo.id as work_order_id
        FROM pdr_estimates pe
        LEFT JOIN work_orders wo ON wo.estimate_id = pe.id
        WHERE pe.id = %s AND pe.tenant_id = %s
    """, (estimate_id, tenant_id))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    if not estimate['work_order_id']:
        conn.close()
        return jsonify({"error": "No work order found"}), 404

    # Get discoveries
    cursor.execute("""
        SELECT de.*, d.zone, d.size, ep.panel_name
        FROM discovery_events de
        LEFT JOIN dents d ON d.id = de.dent_id
        LEFT JOIN estimate_panels ep ON ep.id = d.panel_id
        WHERE de.work_order_id = %s
        ORDER BY de.created_at
    """, (estimate['work_order_id'],))

    discoveries = [dict(d) for d in cursor.fetchall()]
    conn.close()

    # Generate narrative
    total_additional_time = 0
    total_additional_cost = 0
    narratives = []

    for disc in discoveries:
        if disc.get('additional_time_hours'):
            total_additional_time += float(disc['additional_time_hours'])
        if disc.get('additional_cost'):
            total_additional_cost += float(disc['additional_cost'])

        # Generate narrative for each discovery
        panel = disc.get('panel_name', 'panel')
        size = disc.get('size', 'dent')
        zone = disc.get('zone', 'zone')

        narrative = (
            f"During repair of the {size} {zone} dent on the {panel}, "
            f"technician discovered {disc['type'].replace('_', ' ')} was required "
            f"for proper tool access. This condition was not visible during the initial estimate. "
        )

        if disc.get('additional_time_hours'):
            narrative += f"Additional time: {disc['additional_time_hours']} hours. "
        if disc.get('additional_cost'):
            narrative += f"Additional cost: ${disc['additional_cost']:.2f}."

        disc['narrative'] = narrative
        narratives.append(narrative)

        # Format dates
        if disc.get('created_at'):
            disc['created_at'] = disc['created_at'].isoformat()

    return jsonify({
        "estimate_id": estimate_id,
        "original_total": float(estimate['total_price'] or 0),
        "additional_time_hours": total_additional_time,
        "additional_cost": total_additional_cost,
        "new_total": float(estimate['total_price'] or 0) + total_additional_cost,
        "discoveries": discoveries,
        "narrative": "\n\n".join(narratives)
    })


# =============================================================================
# PRICING PROFILE ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/pricing/config', methods=['GET'])
def get_pricing_config():
    """Get current tenant's pricing configuration."""
    tenant_id = get_current_tenant_id()

    conn = get_db()
    config = get_tenant_pricing_config(conn, tenant_id)
    conn.close()

    return jsonify({"config": config})


@pdr_estimates_bp.route('/pricing/profiles', methods=['POST'])
def create_profile():
    """
    Create new pricing profile.

    Body:
    {
        "name": "Premium Pricing",
        "config": { ... },  // optional, uses default
        "is_default": false
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    if not data.get('name'):
        return jsonify({"error": "name required"}), 400

    conn = get_db()
    profile_id = create_pricing_profile(
        conn,
        tenant_id,
        data['name'],
        data.get('config'),
        data.get('is_default', False)
    )
    conn.close()

    return jsonify({"success": True, "profile_id": profile_id}), 201


@pdr_estimates_bp.route('/discovery-types', methods=['GET'])
def list_discovery_types():
    """List all available discovery types with descriptions."""
    from .supplement_generator import list_discovery_types as get_types
    return jsonify(get_types())


# =============================================================================
# R&I LIBRARY ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/ri-library', methods=['GET'])
def get_ri_library():
    """
    Get R&I library operations.
    Query params: category (filter by category)
    Returns system operations plus any tenant custom operations.
    """
    tenant_id = get_current_tenant_id()
    category = request.args.get('category')

    conn = get_db()
    items = get_ri_library_items(conn, tenant_id, category)
    conn.close()

    # Group by category for easier frontend use
    by_category = {}
    for item in items:
        cat = item['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    return jsonify({
        "items": items,
        "by_category": by_category,
        "total_count": len(items),
        "tier_multipliers": TIER_MULTIPLIERS
    })


@pdr_estimates_bp.route('/ri-library', methods=['POST'])
def add_custom_ri_operation():
    """
    Add custom R&I operation for tenant.

    Body:
    {
        "operation_code": "RI_CUSTOM_PANEL",
        "name": "R&I Custom Panel",
        "category": "custom",
        "base_time_min": 0.25,
        "base_time_typical": 0.5,
        "base_time_max": 0.75,
        "scope_min": ["Step 1", "Step 2"],
        "scope_typical": ["Step 1", "Step 2", "Step 3"],
        "scope_max": ["Step 1", "Step 2", "Step 3", "Step 4"]
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    required = ['operation_code', 'name', 'category']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Check for duplicate operation code
    cursor.execute("""
        SELECT id FROM ri_library
        WHERE operation_code = %s AND (tenant_id IS NULL OR tenant_id = %s)
    """, (data['operation_code'], tenant_id))

    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Operation code already exists"}), 400

    cursor.execute("""
        INSERT INTO ri_library (
            tenant_id, operation_code, name, category,
            base_time_min, base_time_typical, base_time_max,
            scope_min, scope_typical, scope_max,
            tier_multipliers, is_active
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, TRUE
        )
        RETURNING id, operation_code, name, category
    """, (
        tenant_id,
        data['operation_code'],
        data['name'],
        data['category'],
        data.get('base_time_min', 0.25),
        data.get('base_time_typical', 0.5),
        data.get('base_time_max', 1.0),
        json.dumps(data.get('scope_min', [])),
        json.dumps(data.get('scope_typical', [])),
        json.dumps(data.get('scope_max', [])),
        json.dumps(data.get('tier_multipliers', TIER_MULTIPLIERS))
    ))

    result = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    return jsonify({"success": True, "operation": result}), 201


@pdr_estimates_bp.route('/ri-library/<operation_code>', methods=['GET'])
def get_ri_operation_details(operation_code):
    """
    Get detailed R&I operation with scope bullets.
    Query params: vehicle_tier, scope_level
    """
    tenant_id = get_current_tenant_id()
    vehicle_tier = request.args.get('vehicle_tier', 'standard')
    scope_level = request.args.get('scope_level', 'typical')

    conn = get_db()
    operation = get_ri_operation(conn, operation_code, tenant_id)
    conn.close()

    if not operation:
        return jsonify({"error": "Operation not found"}), 404

    # Calculate time with tier
    engine = PricingEngine()
    adjusted_time, time_details = engine.calculate_ri_time(
        operation_code=operation_code,
        vehicle_tier=vehicle_tier,
        scope_level=scope_level,
        ri_library=operation
    )

    # Generate scope text
    scope_text = engine.generate_ri_scope_text(
        ri_library=operation,
        scope_level=scope_level,
        vehicle_tier=vehicle_tier,
        include_time=True
    )

    return jsonify({
        "operation": operation,
        "calculated_time": adjusted_time,
        "time_details": time_details,
        "scope_text": scope_text,
        "requested_tier": vehicle_tier,
        "requested_scope": scope_level
    })


# =============================================================================
# VEHICLE TIER ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/vehicle-tier', methods=['GET'])
def lookup_vehicle_tier():
    """
    Look up vehicle tier by make/model.
    Query params: make (required), model (optional)
    Returns tier and multiplier info.
    """
    make = request.args.get('make')
    model = request.args.get('model')

    if not make:
        return jsonify({"error": "make parameter required"}), 400

    conn = get_db()
    tier = get_vehicle_tier(conn, make, model)
    conn.close()

    return jsonify({
        "make": make,
        "model": model,
        "tier": tier,
        "multiplier": TIER_MULTIPLIERS.get(tier, 1.0),
        "all_tiers": TIER_MULTIPLIERS
    })


@pdr_estimates_bp.route('/vehicle-tiers', methods=['GET'])
def list_vehicle_tiers():
    """
    List all vehicle tier classifications.
    Query params: tier (filter by tier)
    """
    tier_filter = request.args.get('tier')

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT make, model, tier, notes FROM vehicle_tiers"
    params = []

    if tier_filter:
        query += " WHERE tier = %s"
        params.append(tier_filter)

    query += " ORDER BY tier, make, model"

    cursor.execute(query, params)
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Group by tier
    by_tier = {}
    for v in vehicles:
        tier = v['tier']
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append(v)

    return jsonify({
        "vehicles": vehicles,
        "by_tier": by_tier,
        "tier_multipliers": TIER_MULTIPLIERS,
        "total_count": len(vehicles)
    })


# =============================================================================
# ENHANCED R&I ITEM ENDPOINTS (using ri_library)
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/panels/<int:panel_id>/rin-suggestions', methods=['GET'])
def get_rin_suggestions(estimate_id, panel_id):
    """
    Get R&I suggestions for a panel based on zones being worked.
    Query params: zone (optional, defaults to detecting from dents)
    """
    tenant_id = get_current_tenant_id()
    zone_filter = request.args.get('zone')

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get panel info
    cursor.execute("""
        SELECT ep.panel_name, e.vehicle_make, e.vehicle_model
        FROM estimate_panels ep
        JOIN pdr_estimates e ON e.id = ep.estimate_id
        WHERE ep.id = %s AND ep.estimate_id = %s AND e.tenant_id = %s
    """, (panel_id, estimate_id, tenant_id))

    panel = cursor.fetchone()
    if not panel:
        conn.close()
        return jsonify({"error": "Panel not found"}), 404

    # Get zones from existing dents or use filter
    if zone_filter:
        zones = [zone_filter]
    else:
        cursor.execute("""
            SELECT DISTINCT zone FROM dents WHERE panel_id = %s
        """, (panel_id,))
        zones = [row['zone'] for row in cursor.fetchall()] or ['center']

    # Get vehicle tier
    vehicle_tier = get_vehicle_tier(conn, panel['vehicle_make'], panel['vehicle_model'])

    # Get R&I library
    ri_library_items = get_ri_library_items(conn, tenant_id)
    conn.close()

    # Get suggestions
    engine = PricingEngine()
    suggestions = engine.suggest_ri_for_panel(
        panel_name=panel['panel_name'],
        zones_worked=zones,
        ri_library_items=ri_library_items
    )

    # Enhance suggestions with time calculations
    for suggestion in suggestions:
        op = next((item for item in ri_library_items
                   if item['operation_code'] == suggestion['operation_code']), None)
        if op:
            adjusted_time, _ = engine.calculate_ri_time(
                operation_code=suggestion['operation_code'],
                vehicle_tier=vehicle_tier,
                scope_level='typical',
                ri_library=op
            )
            suggestion['adjusted_time'] = adjusted_time
            suggestion['vehicle_tier'] = vehicle_tier
            suggestion['scope_typical'] = op.get('scope_typical', [])

    return jsonify({
        "panel_name": panel['panel_name'],
        "zones_detected": zones,
        "vehicle_tier": vehicle_tier,
        "tier_multiplier": TIER_MULTIPLIERS.get(vehicle_tier, 1.0),
        "suggestions": suggestions
    })


@pdr_estimates_bp.route('/<int:estimate_id>/panels/<int:panel_id>/rin-from-library', methods=['POST'])
def add_rin_from_library(estimate_id, panel_id):
    """
    Add R&I item from library with scope tracking.

    Body:
    {
        "operation_code": "RI_HEADLINER_FULL",
        "scope_level": "typical",  // min, typical, max
        "notes": "optional notes"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    operation_code = data.get('operation_code')
    scope_level = data.get('scope_level', 'typical')

    if not operation_code:
        return jsonify({"error": "operation_code required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify panel ownership
    cursor.execute("""
        SELECT ep.panel_name, pe.status, pe.vehicle_make, pe.vehicle_model
        FROM estimate_panels ep
        JOIN pdr_estimates pe ON pe.id = ep.estimate_id
        WHERE ep.id = %s AND ep.estimate_id = %s AND pe.tenant_id = %s
    """, (panel_id, estimate_id, tenant_id))

    panel = cursor.fetchone()
    if not panel:
        conn.close()
        return jsonify({"error": "Panel not found"}), 404

    if panel['status'] != 'draft':
        conn.close()
        return jsonify({"error": "Cannot modify approved estimate"}), 400

    # Get R&I operation from library
    operation = get_ri_operation(conn, operation_code, tenant_id)
    if not operation:
        conn.close()
        return jsonify({"error": "R&I operation not found in library"}), 404

    # Get vehicle tier
    vehicle_tier = get_vehicle_tier(conn, panel['vehicle_make'], panel['vehicle_model'])

    # Calculate time
    engine = PricingEngine()
    adjusted_time, time_details = engine.calculate_ri_time(
        operation_code=operation_code,
        vehicle_tier=vehicle_tier,
        scope_level=scope_level,
        ri_library=operation
    )

    # Get scope bullets
    scope_key = f"scope_{scope_level}"
    scope_bullets = operation.get(scope_key, operation.get('scope_typical', []))

    # Insert into estimate_ri_items (new table) or rin_items with enhanced data
    cursor.execute("""
        INSERT INTO rin_items (
            panel_id, item_name, price, time_hours, auto_suggested
        ) VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (
        panel_id,
        operation['name'],
        adjusted_time * 65,  # Assume $65/hr labor rate
        adjusted_time,
        False
    ))

    rin_item = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    rin_item['price'] = float(rin_item['price'])
    rin_item['time_hours'] = float(rin_item['time_hours'])

    return jsonify({
        "success": True,
        "rin_item": rin_item,
        "operation": {
            "code": operation_code,
            "name": operation['name'],
            "scope_level": scope_level,
            "scope_bullets": scope_bullets,
            "vehicle_tier": vehicle_tier,
            "adjusted_time": adjusted_time,
            "time_details": time_details
        }
    }), 201


# =============================================================================
# WORK ORDERS BLUEPRINT (separate routes for /api/work-orders)
# =============================================================================

work_orders_bp = Blueprint('work_orders', __name__, url_prefix='/api/work-orders')


@work_orders_bp.route('/<int:work_order_id>/discoveries', methods=['POST'])
def add_discovery_wo(work_order_id):
    """
    Log a discovery event during work.
    Redirect to pdr_estimates blueprint handler.
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    if not data.get('type'):
        return jsonify({"error": "discovery type required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify work order belongs to tenant
    cursor.execute("""
        SELECT id, estimate_id FROM work_orders
        WHERE id = %s AND tenant_id = %s
    """, (work_order_id, tenant_id))
    wo = cursor.fetchone()

    if not wo:
        conn.close()
        return jsonify({"error": "Work order not found"}), 404

    # Get template defaults if not provided
    from .supplement_generator import get_discovery_template
    template = get_discovery_template(data['type'])

    cursor.execute("""
        INSERT INTO discovery_events (
            work_order_id, type, description,
            additional_time_hours, additional_cost,
            photo_url, panel_name, dent_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, type, description, additional_time_hours, additional_cost,
                  photo_url, panel_name, dent_id, created_at
    """, (
        work_order_id,
        data['type'],
        data.get('description', template['description']),
        data.get('additional_time_hours', template['typical_time']),
        data.get('additional_cost', template['typical_cost']),
        data.get('photo_url'),
        data.get('panel_name'),
        data.get('dent_id')
    ))

    discovery = dict(cursor.fetchone())
    discovery['created_at'] = discovery['created_at'].isoformat()
    conn.commit()
    conn.close()

    return jsonify(discovery), 201


@work_orders_bp.route('/<int:work_order_id>/supplement', methods=['GET'])
def get_supplement_wo(work_order_id):
    """
    Generate supplement narrative for work order.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get work order with estimate info
    cursor.execute("""
        SELECT wo.id, wo.estimate_id, e.total_price as original_total,
               e.vehicle_year, e.vehicle_make, e.vehicle_model
        FROM work_orders wo
        JOIN pdr_estimates e ON e.id = wo.estimate_id
        WHERE wo.id = %s AND wo.tenant_id = %s
    """, (work_order_id, tenant_id))
    wo = cursor.fetchone()

    if not wo:
        conn.close()
        return jsonify({"error": "Work order not found"}), 404

    # Get discoveries
    cursor.execute("""
        SELECT id, type, description, additional_time_hours, additional_cost,
               photo_url, panel_name, dent_id, created_at
        FROM discovery_events
        WHERE work_order_id = %s
        ORDER BY created_at
    """, (work_order_id,))
    discoveries = [dict(row) for row in cursor.fetchall()]

    conn.close()

    if not discoveries:
        return jsonify({
            "work_order_id": work_order_id,
            "estimate_id": wo['estimate_id'],
            "discovery_count": 0,
            "message": "No discoveries logged - no supplement needed"
        })

    # Convert timestamps
    for d in discoveries:
        if d.get('created_at'):
            d['created_at'] = d['created_at'].isoformat()

    # Generate supplement
    from .supplement_generator import generate_supplement_narrative

    vehicle_info = {
        "vehicle_year": wo.get('vehicle_year'),
        "vehicle_make": wo.get('vehicle_make'),
        "vehicle_model": wo.get('vehicle_model')
    }

    supplement = generate_supplement_narrative(
        estimate_id=wo['estimate_id'],
        original_total=float(wo.get('original_total') or 0),
        discoveries=discoveries,
        vehicle_info=vehicle_info
    )

    return jsonify(supplement)


# =============================================================================
# INSURANCE PROFILES ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/insurance-profiles', methods=['GET'])
def list_insurance_profiles():
    """
    List all insurance profiles.
    Returns company names with rates and requirements.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id, company_name, labor_rate, ri_rate, requires_photos,
               requires_matrix_format, max_dents_before_conventional,
               supplement_email, adjuster_notes, is_active
        FROM insurance_profiles
        WHERE (tenant_id IS NULL OR tenant_id = %s) AND is_active = TRUE
        ORDER BY company_name
    """, (tenant_id,))

    profiles = []
    for row in cursor.fetchall():
        profile = dict(row)
        profile['labor_rate'] = float(profile['labor_rate'])
        profile['ri_rate'] = float(profile['ri_rate'])
        profiles.append(profile)

    conn.close()

    return jsonify({"profiles": profiles, "count": len(profiles)})


@pdr_estimates_bp.route('/insurance-profiles', methods=['POST'])
def create_insurance_profile():
    """
    Create custom insurance profile for tenant.

    Body:
    {
        "company_name": "Local Insurer",
        "labor_rate": 80.00,
        "ri_rate": 80.00,
        "requires_photos": true,
        "requires_matrix_format": false,
        "supplement_email": "claims@local.com"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    if not data.get('company_name'):
        return jsonify({"error": "company_name required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        INSERT INTO insurance_profiles (
            tenant_id, company_name, labor_rate, ri_rate, requires_photos,
            requires_matrix_format, max_dents_before_conventional,
            supplement_email, adjuster_notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, company_name, labor_rate, ri_rate
    """, (
        tenant_id,
        data['company_name'],
        data.get('labor_rate', 75.00),
        data.get('ri_rate', 75.00),
        data.get('requires_photos', True),
        data.get('requires_matrix_format', False),
        data.get('max_dents_before_conventional', 200),
        data.get('supplement_email'),
        data.get('adjuster_notes')
    ))

    profile = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    profile['labor_rate'] = float(profile['labor_rate'])
    profile['ri_rate'] = float(profile['ri_rate'])

    return jsonify({"success": True, "profile": profile}), 201


@pdr_estimates_bp.route('/insurance-profiles/<int:profile_id>', methods=['PUT'])
def update_insurance_profile(profile_id):
    """Update insurance profile."""
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Build update
    fields = ['labor_rate', 'ri_rate', 'requires_photos', 'requires_matrix_format',
              'max_dents_before_conventional', 'supplement_email', 'adjuster_notes']

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
            UPDATE insurance_profiles SET {', '.join(updates)}
            WHERE id = %s AND (tenant_id IS NULL OR tenant_id = %s)
            RETURNING id, company_name, labor_rate, ri_rate
        """, params)

        result = cursor.fetchone()
        conn.commit()
        conn.close()

        if result:
            profile = dict(result)
            profile['labor_rate'] = float(profile['labor_rate'])
            profile['ri_rate'] = float(profile['ri_rate'])
            return jsonify({"success": True, "profile": profile})

    conn.close()
    return jsonify({"error": "Profile not found or no updates"}), 404


# =============================================================================
# VIN DECODER ENDPOINT
# =============================================================================

@pdr_estimates_bp.route('/vin/decode/<vin>', methods=['GET'])
def decode_vin_endpoint(vin):
    """
    Decode VIN using NHTSA API.
    Returns: year, make, model, vehicle_tier, aluminum_panels, is_ev, adas_features
    """
    from src.utils.vin_decoder import decode_vin, format_vehicle_string, get_tier_multiplier

    result = decode_vin(vin)

    if result.get('valid'):
        result['vehicle_string'] = format_vehicle_string(result)
        result['tier_multiplier'] = get_tier_multiplier(result.get('vehicle_tier', 'standard'))

    return jsonify(result)


# =============================================================================
# ESTIMATE PHOTOS ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/photos', methods=['GET'])
def list_estimate_photos(estimate_id):
    """List all photos for an estimate."""
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT id FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    cursor.execute("""
        SELECT ep.*, est_p.panel_name
        FROM estimate_photos ep
        LEFT JOIN estimate_panels est_p ON est_p.id = ep.panel_id
        WHERE ep.estimate_id = %s
        ORDER BY ep.created_at
    """, (estimate_id,))

    photos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Group by type
    by_type = {}
    for photo in photos:
        ptype = photo['photo_type']
        if ptype not in by_type:
            by_type[ptype] = []
        by_type[ptype].append(photo)

    return jsonify({
        "photos": photos,
        "by_type": by_type,
        "count": len(photos)
    })


@pdr_estimates_bp.route('/<int:estimate_id>/photos', methods=['POST'])
def add_estimate_photo(estimate_id):
    """
    Add photo to estimate.

    Body (JSON):
    {
        "photo_type": "panel_overview",  // panel_overview, dent_cluster, measurement, vin_plate, odometer, full_vehicle
        "file_path": "/path/to/photo.jpg",
        "panel_id": 123,  // optional
        "notes": "optional notes"
    }

    OR multipart form data with 'photo' file
    """
    import hashlib
    import os

    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT id FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    # Handle JSON body (file path reference)
    if request.is_json:
        data = request.get_json()
        photo_type = data.get('photo_type', 'panel_overview')
        file_path = data.get('file_path')
        panel_id = data.get('panel_id')
        notes = data.get('notes')
        file_hash = None
        file_size = None

        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.md5(content).hexdigest()
                file_size = len(content)
    else:
        # Handle multipart form data
        if 'photo' not in request.files:
            conn.close()
            return jsonify({"error": "No photo file provided"}), 400

        photo_file = request.files['photo']
        photo_type = request.form.get('photo_type', 'panel_overview')
        panel_id = request.form.get('panel_id')
        notes = request.form.get('notes')

        # Save file
        content = photo_file.read()
        file_hash = hashlib.md5(content).hexdigest()
        file_size = len(content)

        upload_dir = os.path.join('data', 'estimate_photos', str(estimate_id))
        os.makedirs(upload_dir, exist_ok=True)

        ext = os.path.splitext(photo_file.filename)[1] or '.jpg'
        file_path = os.path.join(upload_dir, f"{file_hash}{ext}")

        with open(file_path, 'wb') as f:
            f.write(content)

    cursor.execute("""
        INSERT INTO estimate_photos (estimate_id, panel_id, photo_type, file_path, file_hash, file_size, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, photo_type, file_path, created_at
    """, (estimate_id, panel_id, photo_type, file_path, file_hash, file_size, notes))

    photo = dict(cursor.fetchone())
    photo['created_at'] = photo['created_at'].isoformat()

    conn.commit()
    conn.close()

    return jsonify({"success": True, "photo": photo}), 201


@pdr_estimates_bp.route('/<int:estimate_id>/photos/<int:photo_id>', methods=['DELETE'])
def delete_estimate_photo(estimate_id, photo_id):
    """Delete an estimate photo."""
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        DELETE FROM estimate_photos
        WHERE id = %s AND estimate_id = %s
        AND estimate_id IN (SELECT id FROM pdr_estimates WHERE tenant_id = %s)
        RETURNING id
    """, (photo_id, estimate_id, tenant_id))

    result = cursor.fetchone()
    conn.commit()
    conn.close()

    if result:
        return jsonify({"success": True, "deleted_id": photo_id})
    return jsonify({"error": "Photo not found"}), 404


# =============================================================================
# PRIOR DAMAGE ENDPOINTS
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/prior-damage', methods=['GET'])
def list_prior_damage(estimate_id):
    """List all prior damage records for an estimate."""
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT pd.* FROM prior_damage_records pd
        JOIN pdr_estimates e ON e.id = pd.estimate_id
        WHERE pd.estimate_id = %s AND e.tenant_id = %s
        ORDER BY pd.created_at
    """, (estimate_id, tenant_id))

    records = []
    for row in cursor.fetchall():
        record = dict(row)
        if record.get('created_at'):
            record['created_at'] = record['created_at'].isoformat()
        if record.get('acknowledged_at'):
            record['acknowledged_at'] = record['acknowledged_at'].isoformat()
        records.append(record)

    conn.close()

    return jsonify({"prior_damage": records, "count": len(records)})


@pdr_estimates_bp.route('/<int:estimate_id>/prior-damage', methods=['POST'])
def add_prior_damage(estimate_id):
    """
    Add prior damage record.

    Body:
    {
        "location": "driver door",
        "damage_type": "scratch",  // scratch, dent, chip, crack, rust, other
        "description": "6 inch scratch near handle",
        "photo_path": "/path/to/photo.jpg"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    required = ['location', 'damage_type', 'photo_path']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} required"}), 400

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify ownership
    cursor.execute("""
        SELECT id FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    cursor.execute("""
        INSERT INTO prior_damage_records (estimate_id, location, damage_type, description, photo_path)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (
        estimate_id,
        data['location'],
        data['damage_type'],
        data.get('description'),
        data['photo_path']
    ))

    record = dict(cursor.fetchone())
    record['created_at'] = record['created_at'].isoformat()

    conn.commit()
    conn.close()

    return jsonify({"success": True, "prior_damage": record}), 201


@pdr_estimates_bp.route('/<int:estimate_id>/prior-damage/<int:pd_id>/acknowledge', methods=['PUT'])
def acknowledge_prior_damage(estimate_id, pd_id):
    """
    Customer acknowledges prior damage.

    Body:
    {
        "signature": "base64_signature_data"
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        UPDATE prior_damage_records
        SET customer_acknowledged = TRUE,
            acknowledged_at = NOW(),
            acknowledged_signature = %s
        WHERE id = %s AND estimate_id = %s
        AND estimate_id IN (SELECT id FROM pdr_estimates WHERE tenant_id = %s)
        RETURNING id, location, customer_acknowledged, acknowledged_at
    """, (data.get('signature'), pd_id, estimate_id, tenant_id))

    result = cursor.fetchone()
    conn.commit()
    conn.close()

    if result:
        record = dict(result)
        record['acknowledged_at'] = record['acknowledged_at'].isoformat()
        return jsonify({"success": True, "prior_damage": record})

    return jsonify({"error": "Prior damage record not found"}), 404


# =============================================================================
# MATRIX FORMAT ENDPOINT (Insurance submission format)
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/matrix', methods=['GET'])
def get_estimate_matrix(estimate_id):
    """
    Get estimate in insurance matrix format.
    Returns dent counts by size per panel for insurance submission.
    """
    tenant_id = get_current_tenant_id()

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get estimate
    cursor.execute("""
        SELECT e.*, ip.company_name as insurance_name, ip.labor_rate, ip.ri_rate
        FROM pdr_estimates e
        LEFT JOIN insurance_profiles ip ON ip.id = e.insurance_profile_id
        WHERE e.id = %s AND e.tenant_id = %s
    """, (estimate_id, tenant_id))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    estimate = dict(estimate)

    # Get panels with dent counts by size
    cursor.execute("""
        SELECT ep.panel_name,
               COUNT(*) as total_dents,
               COUNT(*) FILTER (WHERE d.size = 'dime') as dime,
               COUNT(*) FILTER (WHERE d.size = 'nickel') as nickel,
               COUNT(*) FILTER (WHERE d.size = 'quarter') as quarter,
               COUNT(*) FILTER (WHERE d.size = 'half_dollar') as half_dollar,
               COUNT(*) FILTER (WHERE d.size = 'silver_dollar') as silver_dollar,
               COUNT(*) FILTER (WHERE d.size = 'oversized') as oversized,
               COUNT(*) FILTER (WHERE d.size = 'small') as small,
               COUNT(*) FILTER (WHERE d.size = 'medium') as medium,
               COUNT(*) FILTER (WHERE d.size = 'large') as large,
               COUNT(*) FILTER (WHERE d.size = 'xlarge') as xlarge,
               SUM(d.final_price) as panel_labor
        FROM estimate_panels ep
        LEFT JOIN dents d ON d.panel_id = ep.id
        WHERE ep.estimate_id = %s
        GROUP BY ep.id, ep.panel_name
        ORDER BY ep.panel_name
    """, (estimate_id,))

    panels = []
    total_dents = 0
    labor_total = 0

    for row in cursor.fetchall():
        panel = dict(row)
        panel['panel_labor'] = float(panel['panel_labor'] or 0)
        total_dents += panel['total_dents']
        labor_total += panel['panel_labor']
        panels.append(panel)

    # Get R&I items
    cursor.execute("""
        SELECT ri.item_name, ri.price, ri.time_hours, ep.panel_name
        FROM rin_items ri
        JOIN estimate_panels ep ON ep.id = ri.panel_id
        WHERE ep.estimate_id = %s
        ORDER BY ep.panel_name
    """, (estimate_id,))

    ri_items = []
    ri_total = 0
    for row in cursor.fetchall():
        item = dict(row)
        item['price'] = float(item['price'])
        item['time_hours'] = float(item['time_hours'])
        ri_total += item['price']
        ri_items.append(item)

    conn.close()

    # Build matrix format
    vehicle = f"{estimate.get('vehicle_year', '')} {estimate.get('vehicle_make', '')} {estimate.get('vehicle_model', '')}".strip()

    matrix = {
        "format": "insurance_matrix",
        "estimate_number": estimate.get('estimate_number'),
        "vehicle": vehicle,
        "vin": estimate.get('vin'),
        "vehicle_tier": estimate.get('vehicle_tier', 'standard'),
        "insurance_company": estimate.get('insurance_name'),
        "claim_number": estimate.get('claim_number'),
        "panels": panels,
        "total_dents": total_dents,
        "ri_items": ri_items,
        "labor_total": round(labor_total, 2),
        "ri_total": round(ri_total, 2),
        "grand_total": round(labor_total + ri_total, 2),
        "labor_rate": float(estimate.get('labor_rate') or 75),
        "generated_at": datetime.now().isoformat()
    }

    return jsonify(matrix)


# =============================================================================
# LINK TO CRM ENDPOINT
# =============================================================================

@pdr_estimates_bp.route('/<int:estimate_id>/link', methods=['PUT'])
def link_estimate_to_crm(estimate_id):
    """
    Link estimate to existing CRM records.

    Body:
    {
        "lead_id": 5,         // Link to leads table
        "contact_id": 12,     // Link to contacts table
        "job_id": 8,          // Link to jobs table
        "insurance_profile_id": 3  // Link to insurance_profiles
    }
    """
    tenant_id = get_current_tenant_id()
    data = request.get_json() or {}

    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Verify estimate
    cursor.execute("""
        SELECT id FROM pdr_estimates WHERE id = %s AND tenant_id = %s
    """, (estimate_id, tenant_id))

    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Estimate not found"}), 404

    # Build update
    updates = []
    params = []
    links = {}

    # Validate and link each foreign key
    if data.get('lead_id'):
        cursor.execute("SELECT id FROM leads WHERE id = %s AND tenant_id = %s", (data['lead_id'], tenant_id))
        if cursor.fetchone():
            updates.append("lead_id = %s")
            params.append(data['lead_id'])
            links['lead_id'] = data['lead_id']
        else:
            conn.close()
            return jsonify({"error": "Lead not found"}), 404

    if data.get('contact_id'):
        cursor.execute("SELECT id FROM contacts WHERE id = %s AND tenant_id = %s", (data['contact_id'], tenant_id))
        if cursor.fetchone():
            updates.append("contact_id = %s")
            params.append(data['contact_id'])
            links['contact_id'] = data['contact_id']
        else:
            conn.close()
            return jsonify({"error": "Contact not found"}), 404

    if data.get('job_id'):
        cursor.execute("SELECT id FROM jobs WHERE id = %s AND tenant_id = %s", (data['job_id'], tenant_id))
        if cursor.fetchone():
            updates.append("job_id = %s")
            params.append(data['job_id'])
            links['job_id'] = data['job_id']
        else:
            conn.close()
            return jsonify({"error": "Job not found"}), 404

    if data.get('insurance_profile_id'):
        cursor.execute("""
            SELECT id FROM insurance_profiles
            WHERE id = %s AND (tenant_id IS NULL OR tenant_id = %s)
        """, (data['insurance_profile_id'], tenant_id))
        if cursor.fetchone():
            updates.append("insurance_profile_id = %s")
            params.append(data['insurance_profile_id'])
            links['insurance_profile_id'] = data['insurance_profile_id']
        else:
            conn.close()
            return jsonify({"error": "Insurance profile not found"}), 404

    if not updates:
        conn.close()
        return jsonify({"error": "No valid links provided"}), 400

    updates.append("updated_at = NOW()")
    params.extend([estimate_id, tenant_id])

    cursor.execute(f"""
        UPDATE pdr_estimates SET {', '.join(updates)}
        WHERE id = %s AND tenant_id = %s
        RETURNING id, lead_id, contact_id, job_id, insurance_profile_id
    """, params)

    result = dict(cursor.fetchone())
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "estimate_id": estimate_id,
        "links": links,
        "estimate": result
    })
