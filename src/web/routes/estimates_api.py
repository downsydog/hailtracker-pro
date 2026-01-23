"""
Estimates API Routes
====================
REST API for estimate management with line items, status workflow, and job conversion.
"""

from flask import Blueprint, request, jsonify, current_app, session, g
import sqlite3
from datetime import datetime, timedelta
import json
from src.core.auth.decorators import (
    login_required, require_any_permission, require_permission
)

estimates_api_bp = Blueprint('estimates_api', __name__, url_prefix='/api/estimates')


def get_db():
    """Get database connection."""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables_exist(conn):
    """Ensure estimate tables exist."""
    cursor = conn.cursor()

    # Estimates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_number TEXT UNIQUE,
            customer_id INTEGER NOT NULL,
            vehicle_id INTEGER,
            status TEXT DEFAULT 'DRAFT',
            subtotal REAL DEFAULT 0,
            tax_rate REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            total REAL DEFAULT 0,
            notes TEXT,
            terms TEXT,
            valid_until TEXT,
            sent_at TEXT,
            approved_date TEXT,
            declined_at TEXT,
            converted_at TEXT,
            converted_job_id INTEGER,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )
    ''')

    # Estimate line items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estimate_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            service_type TEXT,
            description TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            unit_price REAL DEFAULT 0,
            line_total REAL DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()


def generate_estimate_number(conn):
    """Generate unique estimate number."""
    cursor = conn.cursor()
    year = datetime.now().strftime('%Y')

    cursor.execute('''
        SELECT estimate_number FROM estimates
        WHERE estimate_number LIKE ?
        ORDER BY id DESC LIMIT 1
    ''', (f'EST-{year}-%',))

    last = cursor.fetchone()
    if last:
        try:
            last_num = int(last['estimate_number'].split('-')[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1

    return f'EST-{year}-{new_num:04d}'


def recalculate_totals(conn, estimate_id):
    """Recalculate estimate totals from line items."""
    cursor = conn.cursor()

    # Get sum of line items
    cursor.execute('''
        SELECT COALESCE(SUM(line_total), 0) as subtotal
        FROM estimate_items
        WHERE estimate_id = ?
    ''', (estimate_id,))
    subtotal = cursor.fetchone()['subtotal']

    # Get tax rate
    cursor.execute('SELECT tax_rate FROM estimates WHERE id = ?', (estimate_id,))
    result = cursor.fetchone()
    tax_rate = result['tax_rate'] if result else 0

    # Calculate tax and total
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount

    # Update estimate
    cursor.execute('''
        UPDATE estimates
        SET subtotal = ?, tax_amount = ?, total = ?, updated_at = ?
        WHERE id = ?
    ''', (subtotal, tax_amount, total, datetime.now().isoformat(), estimate_id))

    conn.commit()

    return {'subtotal': subtotal, 'tax_amount': tax_amount, 'total': total}


@estimates_api_bp.route('')
@login_required
@require_any_permission('estimates.view_all', 'estimates.view_own')
def list_estimates():
    """List estimates with filtering, sorting, and pagination."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Build query
    where_clauses = ['1=1']
    params = []

    # Status filter
    status = request.args.get('status')
    if status:
        where_clauses.append('e.status = ?')
        params.append(status.upper())

    # Customer filter
    customer_id = request.args.get('customer_id', type=int)
    if customer_id:
        where_clauses.append('j.customer_id = ?')
        params.append(customer_id)

    # Date range filter
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from:
        where_clauses.append('DATE(e.created_at) >= ?')
        params.append(date_from)
    if date_to:
        where_clauses.append('DATE(e.created_at) <= ?')
        params.append(date_to)

    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        where_clauses.append('''
            (e.estimate_number LIKE ? OR c.first_name || ' ' || c.last_name LIKE ? OR c.email LIKE ? OR
             v.year || ' ' || v.make || ' ' || v.model LIKE ?)
        ''')
        search_param = f'%{search}%'
        params.extend([search_param, search_param, search_param, search_param])

    where_sql = ' AND '.join(where_clauses)

    # Sorting
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc').upper()
    if sort_dir not in ('ASC', 'DESC'):
        sort_dir = 'DESC'

    valid_sorts = {
        'estimate_number': 'e.estimate_number',
        'customer': "c.first_name || ' ' || c.last_name",
        'total': 'e.total',
        'status': 'e.status',
        'created_at': 'e.created_at'
    }
    sort_column = valid_sorts.get(sort_by, 'e.created_at')

    # Get total count
    cursor.execute(f'''
        SELECT COUNT(*) as count
        FROM estimates e
        LEFT JOIN jobs j ON e.job_id = j.id
        LEFT JOIN customers c ON j.customer_id = c.id
        LEFT JOIN vehicles v ON j.vehicle_id = v.id
        WHERE {where_sql}
    ''', params)
    total = cursor.fetchone()['count']

    # Get estimates
    cursor.execute(f'''
        SELECT
            e.*,
            c.first_name || ' ' || c.last_name as customer_name,
            c.email as customer_email,
            c.phone as customer_phone,
            v.year as vehicle_year,
            v.make as vehicle_make,
            v.model as vehicle_model,
            v.vin as vehicle_vin
        FROM estimates e
        LEFT JOIN jobs j ON e.job_id = j.id
        LEFT JOIN customers c ON j.customer_id = c.id
        LEFT JOIN vehicles v ON j.vehicle_id = v.id
        WHERE {where_sql}
        ORDER BY {sort_column} {sort_dir}
        LIMIT ? OFFSET ?
    ''', params + [per_page, offset])

    estimates = [dict(row) for row in cursor.fetchall()]

    # Get stats
    cursor.execute('''
        SELECT
            COUNT(*) as total_count,
            SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) as pending_approval,
            SUM(CASE WHEN status = 'APPROVED' AND DATE(approved_date) >= DATE('now', '-30 days') THEN 1 ELSE 0 END) as approved_this_month,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted_count,
            SUM(CASE WHEN status IN ('APPROVED', 'CONVERTED') THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN status NOT IN ('DRAFT') THEN 1 ELSE 0 END) as sent_count
        FROM estimates
        WHERE deleted_at IS NULL
    ''')
    stats_row = cursor.fetchone()

    sent_count = stats_row['sent_count'] or 1
    success_count = stats_row['success_count'] or 0

    stats = {
        'total': stats_row['total_count'] or 0,
        'pending_approval': stats_row['pending_approval'] or 0,
        'approved_this_month': stats_row['approved_this_month'] or 0,
        'conversion_rate': round((success_count / sent_count) * 100, 1) if sent_count > 0 else 0
    }

    conn.close()

    return jsonify({
        'estimates': estimates,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'stats': stats
    })


@estimates_api_bp.route('/<int:estimate_id>')
@login_required
@require_any_permission('estimates.view_all', 'estimates.view_own')
def get_estimate(estimate_id):
    """Get single estimate with line items."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Get estimate
    cursor.execute('''
        SELECT
            e.*,
            c.first_name || ' ' || c.last_name as customer_name,
            c.email as customer_email,
            c.phone as customer_phone,
            c.street_address as customer_address,
            c.city as customer_city,
            c.state as customer_state,
            c.zip_code as customer_zip,
            v.year as vehicle_year,
            v.make as vehicle_make,
            v.model as vehicle_model,
            v.vin as vehicle_vin,
            v.color as vehicle_color,
            v.license_plate as vehicle_plate
        FROM estimates e
        LEFT JOIN jobs j ON e.job_id = j.id
        LEFT JOIN customers c ON j.customer_id = c.id
        LEFT JOIN vehicles v ON j.vehicle_id = v.id
        WHERE e.id = ?     ''', (estimate_id,))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    estimate = dict(estimate)

    # Get line items
    cursor.execute('''
        SELECT * FROM estimate_items
        WHERE estimate_id = ?
        ORDER BY sort_order, id
    ''', (estimate_id,))

    estimate['items'] = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify(estimate)


@estimates_api_bp.route('', methods=['POST'])
@login_required
@require_any_permission('estimates.create')
def create_estimate():
    """Create new estimate."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    data = request.get_json()

    if not data.get('customer_id'):
        conn.close()
        return jsonify({'error': 'Customer is required'}), 422

    # Generate estimate number
    estimate_number = generate_estimate_number(conn)

    # Set valid until (30 days from now by default)
    valid_until = data.get('valid_until') or (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    # Default tax rate (can be configured)
    tax_rate = data.get('tax_rate', 0)

    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO estimates (
            estimate_number, customer_id, vehicle_id, status,
            tax_rate, notes, terms, valid_until,
            created_by, created_at, updated_at
        ) VALUES (?, ?, ?, 'DRAFT', ?, ?, ?, ?, ?, ?, ?)
    ''', (
        estimate_number,
        data['customer_id'],
        data.get('vehicle_id'),
        tax_rate,
        data.get('notes', ''),
        data.get('terms', 'Estimate valid for 30 days. Subject to change upon inspection.'),
        valid_until,
        g.current_user.get('id') if g.current_user else None,
        now, now
    ))

    estimate_id = cursor.lastrowid

    # Add line items if provided
    if data.get('items'):
        for idx, item in enumerate(data['items']):
            line_total = (item.get('quantity', 1) or 1) * (item.get('unit_price', 0) or 0)
            cursor.execute('''
                INSERT INTO estimate_items (
                    estimate_id, service_type, description,
                    quantity, unit_price, line_total, sort_order,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                estimate_id,
                item.get('service_type', 'PDR'),
                item.get('description', ''),
                item.get('quantity', 1),
                item.get('unit_price', 0),
                line_total,
                idx,
                now, now
            ))

    conn.commit()

    # Recalculate totals
    recalculate_totals(conn, estimate_id)

    # Get created estimate
    cursor.execute('SELECT * FROM estimates WHERE id = ?', (estimate_id,))
    estimate = dict(cursor.fetchone())

    conn.close()

    return jsonify(estimate), 201


@estimates_api_bp.route('/<int:estimate_id>', methods=['PUT'])
@login_required
@require_any_permission('estimates.edit')
def update_estimate(estimate_id):
    """Update estimate."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Check estimate exists and is editable
    cursor.execute('''
        SELECT * FROM estimates WHERE id = ? AND deleted_at IS NULL
    ''', (estimate_id,))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    if estimate['status'] in ('CONVERTED',):
        conn.close()
        return jsonify({'error': 'Cannot edit converted estimate'}), 422

    data = request.get_json()
    now = datetime.now().isoformat()

    # Build update
    updates = []
    params = []

    if 'customer_id' in data:
        updates.append('customer_id = ?')
        params.append(data['customer_id'])

    if 'vehicle_id' in data:
        updates.append('vehicle_id = ?')
        params.append(data['vehicle_id'])

    if 'tax_rate' in data:
        updates.append('tax_rate = ?')
        params.append(data['tax_rate'])

    if 'notes' in data:
        updates.append('notes = ?')
        params.append(data['notes'])

    if 'terms' in data:
        updates.append('terms = ?')
        params.append(data['terms'])

    if 'valid_until' in data:
        updates.append('valid_until = ?')
        params.append(data['valid_until'])

    updates.append('updated_at = ?')
    params.append(now)
    params.append(estimate_id)

    cursor.execute(f'''
        UPDATE estimates SET {', '.join(updates)} WHERE id = ?
    ''', params)

    conn.commit()

    # Recalculate totals (in case tax rate changed)
    recalculate_totals(conn, estimate_id)

    cursor.execute('SELECT * FROM estimates WHERE id = ?', (estimate_id,))
    updated = dict(cursor.fetchone())

    conn.close()

    return jsonify(updated)


@estimates_api_bp.route('/<int:estimate_id>', methods=['DELETE'])
@login_required
@require_any_permission('estimates.delete')
def delete_estimate(estimate_id):
    """Soft delete estimate."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM estimates WHERE id = ? AND deleted_at IS NULL
    ''', (estimate_id,))

    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    cursor.execute('''
        UPDATE estimates SET deleted_at = ? WHERE id = ?
    ''', (datetime.now().isoformat(), estimate_id))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Estimate deleted'})


# Line Items Endpoints

@estimates_api_bp.route('/<int:estimate_id>/items', methods=['POST'])
@login_required
@require_any_permission('estimates.edit')
def add_line_item(estimate_id):
    """Add line item to estimate."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Check estimate exists and is editable
    cursor.execute('''
        SELECT * FROM estimates WHERE id = ? AND deleted_at IS NULL
    ''', (estimate_id,))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    if estimate['status'] in ('CONVERTED',):
        conn.close()
        return jsonify({'error': 'Cannot edit converted estimate'}), 422

    data = request.get_json()

    if not data.get('description'):
        conn.close()
        return jsonify({'error': 'Description is required'}), 422

    quantity = data.get('quantity', 1) or 1
    unit_price = data.get('unit_price', 0) or 0
    line_total = quantity * unit_price

    # Get next sort order
    cursor.execute('''
        SELECT COALESCE(MAX(sort_order), -1) + 1 as next_order
        FROM estimate_items WHERE estimate_id = ?
    ''', (estimate_id,))
    sort_order = cursor.fetchone()['next_order']

    now = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO estimate_items (
            estimate_id, service_type, description,
            quantity, unit_price, line_total, sort_order,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        estimate_id,
        data.get('service_type', 'PDR'),
        data['description'],
        quantity,
        unit_price,
        line_total,
        sort_order,
        now, now
    ))

    item_id = cursor.lastrowid
    conn.commit()

    # Recalculate totals
    totals = recalculate_totals(conn, estimate_id)

    cursor.execute('SELECT * FROM estimate_items WHERE id = ?', (item_id,))
    item = dict(cursor.fetchone())
    item['estimate_totals'] = totals

    conn.close()

    return jsonify(item), 201


@estimates_api_bp.route('/<int:estimate_id>/items/<int:item_id>', methods=['PUT'])
@login_required
@require_any_permission('estimates.edit')
def update_line_item(estimate_id, item_id):
    """Update line item."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Check estimate and item exist
    cursor.execute('''
        SELECT e.*, ei.id as item_exists
        FROM estimates e
        LEFT JOIN estimate_items ei ON ei.estimate_id = e.id AND ei.id = ?
        WHERE e.id = ?     ''', (item_id, estimate_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    if not result['item_exists']:
        conn.close()
        return jsonify({'error': 'Line item not found'}), 404

    if result['status'] in ('CONVERTED',):
        conn.close()
        return jsonify({'error': 'Cannot edit converted estimate'}), 422

    data = request.get_json()
    now = datetime.now().isoformat()

    # Get current values for calculation
    cursor.execute('SELECT * FROM estimate_items WHERE id = ?', (item_id,))
    current = dict(cursor.fetchone())

    quantity = data.get('quantity', current['quantity']) or 1
    unit_price = data.get('unit_price', current['unit_price']) or 0
    line_total = quantity * unit_price

    cursor.execute('''
        UPDATE estimate_items SET
            service_type = ?,
            description = ?,
            quantity = ?,
            unit_price = ?,
            line_total = ?,
            updated_at = ?
        WHERE id = ?
    ''', (
        data.get('service_type', current['service_type']),
        data.get('description', current['description']),
        quantity,
        unit_price,
        line_total,
        now,
        item_id
    ))

    conn.commit()

    # Recalculate totals
    totals = recalculate_totals(conn, estimate_id)

    cursor.execute('SELECT * FROM estimate_items WHERE id = ?', (item_id,))
    item = dict(cursor.fetchone())
    item['estimate_totals'] = totals

    conn.close()

    return jsonify(item)


@estimates_api_bp.route('/<int:estimate_id>/items/<int:item_id>', methods=['DELETE'])
@login_required
@require_any_permission('estimates.edit')
def delete_line_item(estimate_id, item_id):
    """Delete line item."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    # Check estimate and item exist
    cursor.execute('''
        SELECT e.status
        FROM estimates e
        JOIN estimate_items ei ON ei.estimate_id = e.id
        WHERE e.id = ? AND ei.id = ?     ''', (estimate_id, item_id))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'error': 'Item not found'}), 404

    if result['status'] in ('CONVERTED',):
        conn.close()
        return jsonify({'error': 'Cannot edit converted estimate'}), 422

    cursor.execute('DELETE FROM estimate_items WHERE id = ?', (item_id,))
    conn.commit()

    # Recalculate totals
    totals = recalculate_totals(conn, estimate_id)

    conn.close()

    return jsonify({'message': 'Item deleted', 'estimate_totals': totals})


# Status Workflow Endpoints

@estimates_api_bp.route('/<int:estimate_id>/send', methods=['POST'])
@login_required
@require_any_permission('estimates.send')
def send_estimate(estimate_id):
    """Send estimate to customer via email."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT e.*, c.email as customer_email, c.first_name || ' ' || c.last_name as customer_name
        FROM estimates e
        JOIN jobs j ON e.job_id = j.id
        JOIN customers c ON j.customer_id = c.id
        WHERE e.id = ?     ''', (estimate_id,))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    if estimate['status'] in ('CONVERTED',):
        conn.close()
        return jsonify({'error': 'Estimate already converted'}), 422

    # Check has line items
    cursor.execute('SELECT COUNT(*) as count FROM estimate_items WHERE estimate_id = ?', (estimate_id,))
    if cursor.fetchone()['count'] == 0:
        conn.close()
        return jsonify({'error': 'Cannot send estimate with no line items'}), 422

    now = datetime.now().isoformat()

    # Update status to SENT
    cursor.execute('''
        UPDATE estimates SET status = 'SENT', sent_at = ?, updated_at = ?
        WHERE id = ?
    ''', (now, now, estimate_id))

    conn.commit()

    # TODO: Actually send email using email_manager
    # For now, just mark as sent

    cursor.execute('SELECT * FROM estimates WHERE id = ?', (estimate_id,))
    updated = dict(cursor.fetchone())

    conn.close()

    return jsonify({
        'message': f'Estimate sent to {estimate["customer_email"]}',
        'estimate': updated
    })


@estimates_api_bp.route('/<int:estimate_id>/approve', methods=['POST'])
@login_required
@require_any_permission('estimates.approve')
def approve_estimate(estimate_id):
    """Mark estimate as approved."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM estimates WHERE id = ? AND deleted_at IS NULL
    ''', (estimate_id,))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    if estimate['status'] not in ('SENT', 'DRAFT'):
        conn.close()
        return jsonify({'error': f'Cannot approve estimate with status {estimate["status"]}'}), 422

    now = datetime.now().isoformat()

    cursor.execute('''
        UPDATE estimates SET status = 'APPROVED', approved_date = ?, updated_at = ?
        WHERE id = ?
    ''', (now, now, estimate_id))

    conn.commit()

    cursor.execute('SELECT * FROM estimates WHERE id = ?', (estimate_id,))
    updated = dict(cursor.fetchone())

    conn.close()

    return jsonify(updated)


@estimates_api_bp.route('/<int:estimate_id>/decline', methods=['POST'])
@login_required
@require_any_permission('estimates.approve')
def decline_estimate(estimate_id):
    """Mark estimate as declined."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM estimates WHERE id = ? AND deleted_at IS NULL
    ''', (estimate_id,))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    if estimate['status'] not in ('SENT', 'DRAFT'):
        conn.close()
        return jsonify({'error': f'Cannot decline estimate with status {estimate["status"]}'}), 422

    now = datetime.now().isoformat()
    data = request.get_json() or {}

    cursor.execute('''
        UPDATE estimates SET
            status = 'DECLINED',
            declined_at = ?,
            notes = COALESCE(notes, '') || CASE WHEN notes IS NOT NULL AND notes != '' THEN '\n' ELSE '' END || ?,
            updated_at = ?
        WHERE id = ?
    ''', (now, f'Declined: {data.get("reason", "")}', now, estimate_id))

    conn.commit()

    cursor.execute('SELECT * FROM estimates WHERE id = ?', (estimate_id,))
    updated = dict(cursor.fetchone())

    conn.close()

    return jsonify(updated)


@estimates_api_bp.route('/<int:estimate_id>/convert', methods=['POST'])
@login_required
@require_any_permission('estimates.convert', 'jobs.create')
def convert_to_job(estimate_id):
    """Convert approved estimate to job."""
    conn = get_db()
    ensure_tables_exist(conn)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT e.*, c.first_name || ' ' || c.last_name as customer_name,
               v.year as vehicle_year, v.make as vehicle_make, v.model as vehicle_model
        FROM estimates e
        JOIN jobs j ON e.job_id = j.id
        JOIN customers c ON j.customer_id = c.id
        LEFT JOIN vehicles v ON j.vehicle_id = v.id
        WHERE e.id = ?     ''', (estimate_id,))

    estimate = cursor.fetchone()
    if not estimate:
        conn.close()
        return jsonify({'error': 'Estimate not found'}), 404

    if estimate['status'] == 'CONVERTED':
        conn.close()
        return jsonify({'error': 'Estimate already converted', 'job_id': estimate['converted_job_id']}), 422

    if estimate['status'] not in ('APPROVED', 'SENT', 'DRAFT'):
        conn.close()
        return jsonify({'error': f'Cannot convert estimate with status {estimate["status"]}'}), 422

    now = datetime.now().isoformat()
    data = request.get_json() or {}

    # Create job
    # First check if jobs table exists
    cursor.execute('''
        SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'
    ''')

    if cursor.fetchone():
        # Get line items for job description
        cursor.execute('SELECT * FROM estimate_items WHERE estimate_id = ?', (estimate_id,))
        items = cursor.fetchall()

        description_lines = [f"Converted from Estimate {estimate['estimate_number']}"]
        for item in items:
            description_lines.append(f"- {item['description']}: ${item['line_total']:.2f}")

        description = '\n'.join(description_lines)

        cursor.execute('''
            INSERT INTO jobs (
                customer_id, vehicle_id, status, description,
                estimated_cost, source, source_id,
                created_by, created_at, updated_at
            ) VALUES (?, ?, 'PENDING', ?, ?, 'ESTIMATE', ?, ?, ?, ?)
        ''', (
            estimate['customer_id'],
            estimate['vehicle_id'],
            description,
            estimate['total'],
            estimate_id,
            g.current_user.get('id') if g.current_user else None,
            now, now
        ))

        job_id = cursor.lastrowid
    else:
        # Jobs table doesn't exist, just mark as converted
        job_id = None

    # Update estimate
    cursor.execute('''
        UPDATE estimates SET
            status = 'CONVERTED',
            converted_at = ?,
            converted_job_id = ?,
            updated_at = ?
        WHERE id = ?
    ''', (now, job_id, now, estimate_id))

    conn.commit()

    cursor.execute('SELECT * FROM estimates WHERE id = ?', (estimate_id,))
    updated = dict(cursor.fetchone())

    conn.close()

    return jsonify({
        'message': 'Estimate converted to job',
        'estimate': updated,
        'job_id': job_id
    })


# Service Types Endpoint

@estimates_api_bp.route('/service-types')
@login_required
def get_service_types():
    """Get available service types for line items."""
    service_types = [
        {'value': 'PDR', 'label': 'Paintless Dent Repair', 'description': 'Standard PDR service'},
        {'value': 'PDR_HAIL', 'label': 'Hail Damage PDR', 'description': 'Hail damage repair'},
        {'value': 'PDR_DOOR_DING', 'label': 'Door Ding Repair', 'description': 'Minor door ding repair'},
        {'value': 'PDR_CREASE', 'label': 'Crease Repair', 'description': 'Crease/line dent repair'},
        {'value': 'CONVENTIONAL', 'label': 'Conventional Repair', 'description': 'Body filler and paint'},
        {'value': 'PAINT_TOUCH_UP', 'label': 'Paint Touch-Up', 'description': 'Minor paint correction'},
        {'value': 'ASSESSMENT', 'label': 'Assessment Fee', 'description': 'Inspection/assessment'},
        {'value': 'OTHER', 'label': 'Other Service', 'description': 'Custom service'}
    ]

    return jsonify({'service_types': service_types})
