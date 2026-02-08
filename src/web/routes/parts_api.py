"""
Parts API Routes
================
RESTful API for parts catalog, inventory, and ordering.

Endpoints:
- GET    /api/parts              - List parts catalog
- GET    /api/parts/:id          - Get part details
- POST   /api/parts              - Create part
- PUT    /api/parts/:id          - Update part
- DELETE /api/parts/:id          - Delete part
- GET    /api/parts/search       - Search parts
- GET    /api/parts/low-stock    - Get parts below reorder level
- GET    /api/parts/stats        - Get parts statistics

Job Parts:
- GET    /api/jobs/:job_id/parts       - Get parts for job
- POST   /api/jobs/:job_id/parts       - Add part to job
- PUT    /api/jobs/:job_id/parts/:id   - Update job part
- DELETE /api/jobs/:job_id/parts/:id   - Remove part from job

Part Orders:
- GET    /api/parts/orders             - List orders
- GET    /api/parts/orders/:id         - Get order detail
- POST   /api/parts/orders             - Create order
- PUT    /api/parts/orders/:id/status  - Update order status
- GET    /api/parts/orders/:id/quotes  - Get order quotes
- POST   /api/parts/orders/:id/quotes  - Add quote
- POST   /api/parts/orders/:id/quotes/:quote_id/select - Select quote
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, date
import json
from src.core.auth.decorators import login_required, require_any_permission
from src.db.database import Database
from src.crm.managers.parts_manager import PartsManager

parts_api_bp = Blueprint('parts_api', __name__, url_prefix='/api/parts')


def get_db():
    """Get database connection"""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker_crm.db')
    return Database(db_path)


def get_parts_manager():
    """Get parts manager instance"""
    db = get_db()
    return PartsManager(db)


# ============================================================================
# PARTS CATALOG
# ============================================================================

@parts_api_bp.route('')
@login_required
def list_parts():
    """List parts with filtering and pagination"""
    db = get_db()

    # Filters
    search = request.args.get('search', '').strip()
    category = request.args.get('category')
    needs_reorder = request.args.get('needs_reorder', '').lower() == 'true'

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Build query
    where_clauses = ['deleted_at IS NULL']
    params = []

    if search:
        where_clauses.append("""(
            description LIKE ? OR
            part_number LIKE ? OR
            supplier_part_number LIKE ?
        )""")
        search_pattern = f"%{search}%"
        params.extend([search_pattern] * 3)

    if category:
        where_clauses.append('category = ?')
        params.append(category)

    if needs_reorder:
        where_clauses.append('in_stock <= reorder_level AND reorder_level > 0')

    where_sql = ' AND '.join(where_clauses)

    # Count total
    count_query = f"SELECT COUNT(*) as total FROM parts WHERE {where_sql}"
    count_result = db.execute(count_query, tuple(params))
    total = count_result[0]['total'] if count_result else 0

    # Get parts
    query = f"""
        SELECT * FROM parts
        WHERE {where_sql}
        ORDER BY description
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])
    parts = db.execute(query, tuple(params))

    return jsonify({
        'parts': parts,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })


@parts_api_bp.route('/<int:part_id>')
@login_required
def get_part(part_id):
    """Get part details"""
    manager = get_parts_manager()
    part = manager.get_part(part_id)

    if not part:
        return jsonify({'error': 'Part not found'}), 404

    return jsonify({'part': part})


@parts_api_bp.route('', methods=['POST'])
@login_required
@require_any_permission('inventory.manage', 'admin')
def create_part():
    """Create new part"""
    data = request.get_json()

    if not data.get('description'):
        return jsonify({'error': 'Description is required'}), 400

    manager = get_parts_manager()

    try:
        part_id = manager.add_part(
            description=data['description'],
            part_number=data.get('part_number'),
            category=data.get('category', 'BODY_PANEL'),
            preferred_supplier=data.get('preferred_supplier'),
            supplier_part_number=data.get('supplier_part_number'),
            cost=data.get('cost'),
            retail_price=data.get('retail_price'),
            in_stock=data.get('in_stock', 0),
            reorder_level=data.get('reorder_level', 0)
        )

        return jsonify({
            'success': True,
            'part_id': part_id,
            'message': 'Part created successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@parts_api_bp.route('/<int:part_id>', methods=['PUT'])
@login_required
@require_any_permission('inventory.manage', 'admin')
def update_part(part_id):
    """Update part"""
    data = request.get_json()
    manager = get_parts_manager()

    part = manager.get_part(part_id)
    if not part:
        return jsonify({'error': 'Part not found'}), 404

    # Filter allowed fields
    allowed_fields = [
        'part_number', 'description', 'category', 'preferred_supplier',
        'supplier_part_number', 'cost', 'retail_price', 'in_stock', 'reorder_level'
    ]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if update_data:
        manager.update_part(part_id, update_data)

    return jsonify({'success': True, 'message': 'Part updated successfully'})


@parts_api_bp.route('/<int:part_id>', methods=['DELETE'])
@login_required
@require_any_permission('inventory.manage', 'admin')
def delete_part(part_id):
    """Soft delete part"""
    db = get_db()

    db.execute("""
        UPDATE parts SET deleted_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), part_id))

    return jsonify({'success': True, 'message': 'Part deleted successfully'})


@parts_api_bp.route('/search')
@login_required
def search_parts():
    """Search parts by query"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)

    if not query:
        return jsonify({'parts': []})

    manager = get_parts_manager()
    parts = manager.search_parts(search_term=query, limit=limit)

    return jsonify({'parts': parts})


@parts_api_bp.route('/low-stock')
@login_required
def get_low_stock():
    """Get parts below reorder level"""
    manager = get_parts_manager()
    parts = manager.get_low_stock_parts()

    return jsonify({'parts': parts, 'count': len(parts)})


@parts_api_bp.route('/stats')
@login_required
def get_parts_stats():
    """Get parts statistics"""
    manager = get_parts_manager()
    stats = manager.get_parts_stats()

    return jsonify(stats)


@parts_api_bp.route('/categories')
@login_required
def get_categories():
    """Get list of part categories"""
    db = get_db()

    result = db.execute("""
        SELECT DISTINCT category FROM parts
        WHERE deleted_at IS NULL AND category IS NOT NULL
        ORDER BY category
    """)

    categories = [row['category'] for row in result]

    return jsonify({'categories': categories})


@parts_api_bp.route('/<int:part_id>/inventory', methods=['POST'])
@login_required
@require_any_permission('inventory.manage', 'admin')
def update_inventory(part_id):
    """Update part inventory level"""
    data = request.get_json()

    quantity_change = data.get('quantity_change', 0)
    notes = data.get('notes')

    manager = get_parts_manager()

    part = manager.get_part(part_id)
    if not part:
        return jsonify({'error': 'Part not found'}), 404

    manager.update_inventory(part_id, quantity_change, notes)

    updated_part = manager.get_part(part_id)

    return jsonify({
        'success': True,
        'new_stock': updated_part['in_stock'],
        'message': f'Inventory updated by {quantity_change}'
    })


# ============================================================================
# JOB PARTS
# ============================================================================

@parts_api_bp.route('/jobs/<int:job_id>/parts')
@login_required
def get_job_parts(job_id):
    """Get parts associated with a job"""
    db = get_db()

    parts = db.execute("""
        SELECT jp.*, p.part_number, p.description, p.category
        FROM job_parts jp
        JOIN parts p ON p.id = jp.part_id
        WHERE jp.job_id = ?
        ORDER BY jp.created_at DESC
    """, (job_id,))

    # Calculate totals
    total = sum(p.get('total', 0) or 0 for p in parts)

    return jsonify({
        'parts': parts,
        'count': len(parts),
        'total': total
    })


@parts_api_bp.route('/jobs/<int:job_id>/parts', methods=['POST'])
@login_required
def add_part_to_job(job_id):
    """Add part to a job"""
    data = request.get_json()
    db = get_db()

    part_id = data.get('part_id')
    quantity = data.get('quantity', 1)
    price = data.get('price')
    notes = data.get('notes')

    if not part_id:
        return jsonify({'error': 'part_id is required'}), 400

    # Get part for default price
    result = db.execute("SELECT * FROM parts WHERE id = ?", (part_id,))
    if not result:
        return jsonify({'error': 'Part not found'}), 404

    part = result[0]
    if price is None:
        price = part.get('retail_price') or 0

    total = quantity * price

    # Insert job_part
    db.execute("""
        INSERT INTO job_parts (job_id, part_id, quantity, price, total, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (job_id, part_id, quantity, price, total, notes, datetime.now().isoformat()))

    # Get the inserted ID
    result = db.execute("SELECT last_insert_rowid() as id")
    job_part_id = result[0]['id']

    return jsonify({
        'success': True,
        'job_part_id': job_part_id,
        'message': 'Part added to job'
    }), 201


@parts_api_bp.route('/jobs/<int:job_id>/parts/<int:job_part_id>', methods=['PUT'])
@login_required
def update_job_part(job_id, job_part_id):
    """Update job part"""
    data = request.get_json()
    db = get_db()

    # Verify job_part exists
    result = db.execute("""
        SELECT * FROM job_parts WHERE id = ? AND job_id = ?
    """, (job_part_id, job_id))

    if not result:
        return jsonify({'error': 'Job part not found'}), 404

    job_part = result[0]

    # Update fields
    quantity = data.get('quantity', job_part['quantity'])
    price = data.get('price', job_part['price'])
    notes = data.get('notes', job_part['notes'])
    total = quantity * price

    db.execute("""
        UPDATE job_parts
        SET quantity = ?, price = ?, total = ?, notes = ?, updated_at = ?
        WHERE id = ?
    """, (quantity, price, total, notes, datetime.now().isoformat(), job_part_id))

    return jsonify({'success': True, 'message': 'Job part updated'})


@parts_api_bp.route('/jobs/<int:job_id>/parts/<int:job_part_id>', methods=['DELETE'])
@login_required
def remove_job_part(job_id, job_part_id):
    """Remove part from job"""
    db = get_db()

    db.execute("""
        DELETE FROM job_parts WHERE id = ? AND job_id = ?
    """, (job_part_id, job_id))

    return jsonify({'success': True, 'message': 'Part removed from job'})


# ============================================================================
# PART ORDERS
# ============================================================================

@parts_api_bp.route('/orders')
@login_required
def list_orders():
    """List part orders"""
    db = get_db()

    status = request.args.get('status')
    job_id = request.args.get('job_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    offset = (page - 1) * per_page

    where_clauses = ['1=1']
    params = []

    if status:
        where_clauses.append('po.status = ?')
        params.append(status.upper())

    if job_id:
        where_clauses.append('po.job_id = ?')
        params.append(job_id)

    where_sql = ' AND '.join(where_clauses)

    # Count
    count_result = db.execute(f"""
        SELECT COUNT(*) as total FROM part_orders po WHERE {where_sql}
    """, tuple(params))
    total = count_result[0]['total'] if count_result else 0

    # Get orders
    query = f"""
        SELECT po.*, j.job_number
        FROM part_orders po
        LEFT JOIN jobs j ON j.id = po.job_id
        WHERE {where_sql}
        ORDER BY po.created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])
    orders = db.execute(query, tuple(params))

    # Parse parts_json for each order
    for order in orders:
        if order.get('parts_json'):
            order['parts_list'] = json.loads(order['parts_json'])
        else:
            order['parts_list'] = []

    return jsonify({
        'orders': orders,
        'total': total,
        'page': page,
        'per_page': per_page
    })


@parts_api_bp.route('/orders/<int:order_id>')
@login_required
def get_order(order_id):
    """Get order details"""
    manager = get_parts_manager()
    order = manager.get_order(order_id)

    if not order:
        return jsonify({'error': 'Order not found'}), 404

    # Get quotes for this order
    quotes = manager.get_order_quotes(order_id)
    order['quotes'] = quotes

    return jsonify({'order': order})


@parts_api_bp.route('/orders', methods=['POST'])
@login_required
def create_order():
    """Create part order"""
    data = request.get_json()

    supplier_name = data.get('supplier_name')
    if not supplier_name:
        return jsonify({'error': 'supplier_name is required'}), 400

    manager = get_parts_manager()

    try:
        order_id = manager.create_order(
            supplier_name=supplier_name,
            job_id=data.get('job_id'),
            parts=data.get('parts'),
            supplier_email=data.get('supplier_email'),
            supplier_phone=data.get('supplier_phone'),
            notes=data.get('notes')
        )

        order = manager.get_order(order_id)

        return jsonify({
            'success': True,
            'order_id': order_id,
            'order_number': order['order_number'],
            'message': 'Order created successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@parts_api_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@login_required
def update_order_status(order_id):
    """Update order status"""
    data = request.get_json()

    status = data.get('status')
    if not status:
        return jsonify({'error': 'status is required'}), 400

    manager = get_parts_manager()

    try:
        manager.update_order_status(
            order_id=order_id,
            status=status.upper(),
            quote_amount=data.get('quote_amount'),
            actual_amount=data.get('actual_amount'),
            expected_delivery_date=date.fromisoformat(data['expected_delivery_date']) if data.get('expected_delivery_date') else None,
            actual_delivery_date=date.fromisoformat(data['actual_delivery_date']) if data.get('actual_delivery_date') else None,
            return_cost=data.get('return_cost'),
            notes=data.get('notes')
        )

        return jsonify({'success': True, 'message': f'Order status updated to {status}'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@parts_api_bp.route('/orders/<int:order_id>/quotes')
@login_required
def get_order_quotes(order_id):
    """Get quotes for an order"""
    manager = get_parts_manager()
    quotes = manager.get_order_quotes(order_id)

    return jsonify({'quotes': quotes})


@parts_api_bp.route('/orders/<int:order_id>/quotes', methods=['POST'])
@login_required
def add_quote(order_id):
    """Add quote to order"""
    data = request.get_json()

    supplier_name = data.get('supplier_name')
    quoted_price = data.get('quoted_price')

    if not supplier_name or quoted_price is None:
        return jsonify({'error': 'supplier_name and quoted_price are required'}), 400

    manager = get_parts_manager()

    try:
        quote_id = manager.add_quote(
            order_id=order_id,
            supplier_name=supplier_name,
            quoted_price=quoted_price,
            quoted_delivery_days=data.get('quoted_delivery_days'),
            return_policy=data.get('return_policy'),
            core_charge=data.get('core_charge'),
            expires_date=date.fromisoformat(data['expires_date']) if data.get('expires_date') else None
        )

        return jsonify({
            'success': True,
            'quote_id': quote_id,
            'message': 'Quote added successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@parts_api_bp.route('/orders/<int:order_id>/quotes/<int:quote_id>/select', methods=['POST'])
@login_required
def select_quote(order_id, quote_id):
    """Select a quote as the winner"""
    manager = get_parts_manager()

    try:
        manager.select_quote(quote_id)
        return jsonify({'success': True, 'message': 'Quote selected successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@parts_api_bp.route('/suppliers')
@login_required
def get_suppliers():
    """Get list of suppliers with performance data"""
    manager = get_parts_manager()
    suppliers = manager.get_supplier_performance()

    return jsonify({'suppliers': suppliers})
