"""
R&I (Remove & Install) API Routes
==================================
RESTful API for R&I operations, times, and estimate integration.

Endpoints:
- GET    /api/ri/operations           - List R&I operations
- GET    /api/ri/operations/:id       - Get operation details
- POST   /api/ri/operations           - Create operation
- PUT    /api/ri/operations/:id       - Update operation
- DELETE /api/ri/operations/:id       - Delete operation

R&I Times:
- GET    /api/ri/times                - Get times with vehicle filters
- POST   /api/ri/times/corrections    - Submit time correction

Panels:
- GET    /api/ri/panels               - List panels with R&I associations
- GET    /api/ri/panels/:panel/operations - Get R&I ops for panel

Auto-Suggest:
- POST   /api/ri/suggest              - Suggest R&I for damage

Estimate R&I:
- GET    /api/estimates/:id/ri        - Get estimate R&I items
- POST   /api/estimates/:id/ri        - Add R&I to estimate
- PUT    /api/estimates/:id/ri/:item  - Update R&I item
- DELETE /api/estimates/:id/ri/:item  - Remove R&I item

Stats:
- GET    /api/ri/stats                - R&I usage statistics
- GET    /api/ri/labor-rates          - Labor rates
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from src.core.auth.decorators import login_required, require_any_permission
from src.crm.managers.ri_manager import RIManager

ri_api_bp = Blueprint('ri_api', __name__, url_prefix='/api/ri')


def get_ri_manager():
    """Get R&I manager instance"""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker_crm.db')
    return RIManager(db_path)


# ============================================================================
# R&I OPERATIONS CATALOG
# ============================================================================

@ri_api_bp.route('/operations')
@login_required
def list_operations():
    """List all R&I operations"""
    manager = get_ri_manager()

    category = request.args.get('category')
    search = request.args.get('search', '').strip()

    operations = manager.get_all_ri_operations(category=category)

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        operations = [
            op for op in operations
            if search_lower in op.get('name', '').lower()
            or search_lower in op.get('code', '').lower()
            or search_lower in op.get('description', '').lower()
        ]

    return jsonify({
        'operations': operations,
        'count': len(operations)
    })


@ri_api_bp.route('/operations/<int:operation_id>')
@login_required
def get_operation(operation_id):
    """Get R&I operation details"""
    manager = get_ri_manager()
    operation = manager.get_ri_operation(operation_id)

    if not operation:
        return jsonify({'error': 'Operation not found'}), 404

    return jsonify({'operation': operation})


@ri_api_bp.route('/operations/code/<code>')
@login_required
def get_operation_by_code(code):
    """Get R&I operation by code"""
    manager = get_ri_manager()
    operation = manager.get_ri_operation_by_code(code)

    if not operation:
        return jsonify({'error': 'Operation not found'}), 404

    return jsonify({'operation': operation})


@ri_api_bp.route('/operations', methods=['POST'])
@login_required
@require_any_permission('estimating.manage', 'admin')
def create_operation():
    """Create new R&I operation"""
    data = request.get_json()

    required = ['code', 'name']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    manager = get_ri_manager()

    try:
        result = manager.db.execute("""
            INSERT INTO ri_operations (
                code, name, category, description, default_hours,
                default_labor_type, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            data['code'],
            data['name'],
            data.get('category', 'trim'),
            data.get('description'),
            data.get('default_hours', 0.5),
            data.get('default_labor_type', 'body'),
            datetime.now().isoformat()
        ))

        operation_id = result[0]['id'] if result else None

        return jsonify({
            'success': True,
            'operation_id': operation_id,
            'message': 'R&I operation created successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ri_api_bp.route('/operations/<int:operation_id>', methods=['PUT'])
@login_required
@require_any_permission('estimating.manage', 'admin')
def update_operation(operation_id):
    """Update R&I operation"""
    data = request.get_json()
    manager = get_ri_manager()

    operation = manager.get_ri_operation(operation_id)
    if not operation:
        return jsonify({'error': 'Operation not found'}), 404

    # Build update
    allowed = ['code', 'name', 'category', 'description', 'default_hours', 'default_labor_type', 'is_active']
    updates = []
    params = []

    for field in allowed:
        if field in data:
            updates.append(f'{field} = ?')
            params.append(data[field])

    if not updates:
        return jsonify({'error': 'No fields to update'}), 400

    updates.append('updated_at = ?')
    params.append(datetime.now().isoformat())
    params.append(operation_id)

    manager.db.execute(f"""
        UPDATE ri_operations SET {', '.join(updates)} WHERE id = ?
    """, tuple(params))

    return jsonify({'success': True, 'message': 'Operation updated successfully'})


@ri_api_bp.route('/operations/<int:operation_id>', methods=['DELETE'])
@login_required
@require_any_permission('estimating.manage', 'admin')
def delete_operation(operation_id):
    """Deactivate R&I operation"""
    manager = get_ri_manager()

    manager.db.execute("""
        UPDATE ri_operations SET is_active = 0 WHERE id = ?
    """, (operation_id,))

    return jsonify({'success': True, 'message': 'Operation deactivated'})


# ============================================================================
# R&I TIMES
# ============================================================================

@ri_api_bp.route('/times')
@login_required
def get_times():
    """Get R&I times for a vehicle"""
    manager = get_ri_manager()

    vehicle_id = request.args.get('vehicle_id', type=int)
    year = request.args.get('year', type=int)
    make = request.args.get('make', '')
    model = request.args.get('model', '')
    operation_id = request.args.get('operation_id', type=int)

    # If vehicle_id provided, lookup vehicle info
    if vehicle_id:
        vehicle = manager.db.execute("""
            SELECT year, make, model FROM vehicles WHERE id = ?
        """, (vehicle_id,))
        if vehicle:
            year = vehicle[0].get('year', year)
            make = vehicle[0].get('make', make)
            model = vehicle[0].get('model', model)

    # Get times
    where_clauses = ['1=1']
    params = []

    if year:
        where_clauses.append('? BETWEEN rt.year_start AND rt.year_end')
        params.append(year)

    if make:
        where_clauses.append('LOWER(rt.make) = LOWER(?)')
        params.append(make)

    if model:
        where_clauses.append('LOWER(rt.model) = LOWER(?)')
        params.append(model)

    if operation_id:
        where_clauses.append('rt.ri_operation_id = ?')
        params.append(operation_id)

    where_sql = ' AND '.join(where_clauses)

    times = manager.db.execute(f"""
        SELECT rt.*, ri.name as operation_name, ri.code as operation_code, ri.category
        FROM ri_times rt
        JOIN ri_operations ri ON ri.id = rt.ri_operation_id
        WHERE {where_sql}
        ORDER BY ri.category, ri.name
    """, tuple(params))

    return jsonify({
        'times': times,
        'count': len(times),
        'vehicle': {'year': year, 'make': make, 'model': model}
    })


@ri_api_bp.route('/times/lookup')
@login_required
def lookup_time():
    """Lookup specific R&I time for vehicle"""
    manager = get_ri_manager()

    operation_id = request.args.get('operation_id', type=int)
    year = request.args.get('year', type=int)
    make = request.args.get('make', '')
    model = request.args.get('model', '')
    body_style = request.args.get('body_style')

    if not operation_id or not year or not make or not model:
        return jsonify({'error': 'operation_id, year, make, and model are required'}), 400

    hours, source, confidence, ri_time_id = manager.lookup_ri_time(
        ri_operation_id=operation_id,
        year=year,
        make=make,
        model=model,
        body_style=body_style
    )

    return jsonify({
        'hours': hours,
        'source': source,
        'confidence': confidence,
        'ri_time_id': ri_time_id
    })


@ri_api_bp.route('/times/corrections', methods=['POST'])
@login_required
def submit_time_correction():
    """Submit a time correction (crowdsourced)"""
    data = request.get_json()
    manager = get_ri_manager()

    required = ['ri_operation_id', 'suggested_hours', 'actual_hours', 'vehicle_year', 'vehicle_make', 'vehicle_model']
    for field in required:
        if field not in data and field.replace('vehicle_', '') not in data.get('vehicle_info', {}):
            return jsonify({'error': f'{field} is required'}), 400

    try:
        vehicle_info = data.get('vehicle_info', {
            'year': data.get('vehicle_year'),
            'make': data.get('vehicle_make'),
            'model': data.get('vehicle_model'),
            'body_style': data.get('vehicle_body_style')
        })

        submission_id = manager.submit_time_correction(
            ri_time_id=data.get('ri_time_id'),
            estimate_id=data.get('estimate_id', 0),
            ri_operation_id=data['ri_operation_id'],
            suggested_hours=data['suggested_hours'],
            actual_hours=data['actual_hours'],
            vehicle_info=vehicle_info,
            technician_id=data.get('technician_id'),
            notes=data.get('notes')
        )

        return jsonify({
            'success': True,
            'submission_id': submission_id,
            'message': 'Time correction submitted for review'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ri_api_bp.route('/times/corrections/pending')
@login_required
@require_any_permission('estimating.manage', 'admin')
def get_pending_corrections():
    """Get pending time corrections"""
    manager = get_ri_manager()
    corrections = manager.get_pending_time_corrections()

    return jsonify({'corrections': corrections, 'count': len(corrections)})


@ri_api_bp.route('/times/corrections/<int:submission_id>/approve', methods=['POST'])
@login_required
@require_any_permission('estimating.manage', 'admin')
def approve_correction(submission_id):
    """Approve a time correction"""
    manager = get_ri_manager()

    try:
        manager.approve_time_correction(submission_id)
        return jsonify({'success': True, 'message': 'Correction approved and applied'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# PANELS
# ============================================================================

@ri_api_bp.route('/panels')
@login_required
def list_panels():
    """List panels with R&I associations"""
    manager = get_ri_manager()

    panels = manager.db.execute("""
        SELECT DISTINCT panel_name,
               COUNT(*) as operation_count
        FROM panel_ri_associations
        GROUP BY panel_name
        ORDER BY panel_name
    """)

    return jsonify({'panels': panels})


@ri_api_bp.route('/panels/<panel>/operations')
@login_required
def get_panel_operations(panel):
    """Get R&I operations for a specific panel"""
    manager = get_ri_manager()

    # Normalize panel name
    panel_name = panel.lower().replace('-', '_').replace(' ', '_')

    operations = manager.db.execute("""
        SELECT pa.*, ri.name, ri.code, ri.category, ri.default_hours
        FROM panel_ri_associations pa
        JOIN ri_operations ri ON ri.id = pa.ri_operation_id
        WHERE pa.panel_name = ?
          AND ri.is_active = 1
        ORDER BY pa.priority, ri.name
    """, (panel_name,))

    return jsonify({
        'panel': panel_name,
        'operations': operations,
        'count': len(operations)
    })


# ============================================================================
# AUTO-SUGGEST
# ============================================================================

@ri_api_bp.route('/suggest', methods=['POST'])
@login_required
def suggest_ri():
    """Suggest R&I operations based on damage"""
    data = request.get_json()
    manager = get_ri_manager()

    panels = data.get('panels', [])
    vehicle_info = data.get('vehicle_info', {})
    estimate_id = data.get('estimate_id')

    if not panels:
        return jsonify({'error': 'panels array is required'}), 400

    suggestions = []

    for panel_data in panels:
        if isinstance(panel_data, str):
            panel_name = panel_data
            dent_count = 1
        else:
            panel_name = panel_data.get('name', panel_data.get('panel'))
            dent_count = panel_data.get('dent_count', 1)

        panel_suggestions = manager.get_suggested_ri_items(
            estimate_id=estimate_id or 0,
            panel_name=panel_name,
            dent_count=dent_count,
            vehicle_info=vehicle_info
        )

        suggestions.extend(panel_suggestions)

    # Remove duplicates (same operation might be suggested for multiple panels)
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        key = s['ri_operation_id']
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(s)

    # Calculate totals
    total_hours = sum(s['hours'] for s in unique_suggestions)
    total_amount = sum(s['total'] for s in unique_suggestions)

    return jsonify({
        'suggestions': unique_suggestions,
        'total_hours': round(total_hours, 2),
        'total_amount': round(total_amount, 2),
        'count': len(unique_suggestions)
    })


# ============================================================================
# ESTIMATE R&I ITEMS
# ============================================================================

@ri_api_bp.route('/estimates/<int:estimate_id>/ri')
@login_required
def get_estimate_ri(estimate_id):
    """Get R&I items for an estimate"""
    manager = get_ri_manager()
    items = manager.get_estimate_ri_items(estimate_id)

    total = manager.recalculate_ri_totals(estimate_id)

    return jsonify({
        'items': items,
        'count': len(items),
        'total': total
    })


@ri_api_bp.route('/estimates/<int:estimate_id>/ri', methods=['POST'])
@login_required
def add_ri_to_estimate(estimate_id):
    """Add R&I item to estimate"""
    data = request.get_json()
    manager = get_ri_manager()

    operation_id = data.get('operation_id') or data.get('ri_operation_id')
    if not operation_id:
        return jsonify({'error': 'operation_id is required'}), 400

    try:
        item_id = manager.add_ri_to_estimate(
            estimate_id=estimate_id,
            ri_operation_id=operation_id,
            hours=data.get('hours'),
            panel_name=data.get('panel_name'),
            auto_suggested=data.get('auto_suggested', False),
            notes=data.get('notes')
        )

        # Get updated total
        total = manager.recalculate_ri_totals(estimate_id)

        return jsonify({
            'success': True,
            'item_id': item_id,
            'ri_total': total,
            'message': 'R&I item added to estimate'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ri_api_bp.route('/estimates/<int:estimate_id>/ri/<int:item_id>', methods=['PUT'])
@login_required
def update_estimate_ri(estimate_id, item_id):
    """Update R&I item on estimate"""
    data = request.get_json()
    manager = get_ri_manager()

    try:
        manager.update_ri_item(
            ri_item_id=item_id,
            hours=data.get('hours'),
            notes=data.get('notes')
        )

        total = manager.recalculate_ri_totals(estimate_id)

        return jsonify({
            'success': True,
            'ri_total': total,
            'message': 'R&I item updated'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ri_api_bp.route('/estimates/<int:estimate_id>/ri/<int:item_id>', methods=['DELETE'])
@login_required
def remove_estimate_ri(estimate_id, item_id):
    """Remove R&I item from estimate"""
    manager = get_ri_manager()

    manager.remove_ri_from_estimate(item_id)
    total = manager.recalculate_ri_totals(estimate_id)

    return jsonify({
        'success': True,
        'ri_total': total,
        'message': 'R&I item removed'
    })


@ri_api_bp.route('/estimates/<int:estimate_id>/ri/bulk', methods=['POST'])
@login_required
def bulk_add_ri_to_estimate(estimate_id):
    """Add multiple R&I items to estimate (from suggestions)"""
    data = request.get_json()
    manager = get_ri_manager()

    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'items array is required'}), 400

    added_ids = []

    for item in items:
        try:
            item_id = manager.add_ri_to_estimate(
                estimate_id=estimate_id,
                ri_operation_id=item.get('ri_operation_id') or item.get('operation_id'),
                hours=item.get('hours'),
                panel_name=item.get('panel_name'),
                auto_suggested=item.get('auto_suggested', True),
                notes=item.get('notes')
            )
            added_ids.append(item_id)
        except Exception as e:
            print(f"Error adding R&I item: {e}")

    total = manager.recalculate_ri_totals(estimate_id)

    return jsonify({
        'success': True,
        'added_count': len(added_ids),
        'item_ids': added_ids,
        'ri_total': total
    }), 201


# ============================================================================
# LABOR RATES & STATS
# ============================================================================

@ri_api_bp.route('/labor-rates')
@login_required
def get_labor_rates():
    """Get current labor rates"""
    manager = get_ri_manager()

    rates = manager.db.execute("""
        SELECT DISTINCT rate_type, hourly_rate
        FROM labor_rates
        WHERE is_active = 1
        ORDER BY rate_type
    """)

    # Also provide defaults
    rate_types = ['body', 'paint', 'pdr', 'mechanical', 'electrical', 'glass', 'structural']
    rate_dict = {r['rate_type']: r['hourly_rate'] for r in rates}

    for rt in rate_types:
        if rt not in rate_dict:
            rate_dict[rt] = manager.get_labor_rate(rt)

    return jsonify({'rates': rate_dict})


@ri_api_bp.route('/stats')
@login_required
def get_ri_stats():
    """Get R&I usage statistics"""
    days = request.args.get('days', 30, type=int)

    manager = get_ri_manager()
    stats = manager.get_ri_usage_stats(days)

    return jsonify(stats)


@ri_api_bp.route('/categories')
@login_required
def get_categories():
    """Get R&I operation categories"""
    manager = get_ri_manager()

    categories = manager.db.execute("""
        SELECT DISTINCT category FROM ri_operations
        WHERE is_active = 1 AND category IS NOT NULL
        ORDER BY category
    """)

    return jsonify({
        'categories': [c['category'] for c in categories]
    })
