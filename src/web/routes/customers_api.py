"""
Customers API Routes
====================
RESTful API for customer management.

Endpoints:
- GET    /api/customers          - List customers with filters
- GET    /api/customers/:id      - Get customer details
- POST   /api/customers          - Create new customer
- PUT    /api/customers/:id      - Update customer
- DELETE /api/customers/:id      - Delete (soft) customer
- GET    /api/customers/search   - Search customers (autocomplete)
"""

from flask import Blueprint, request, jsonify, g, current_app
from datetime import datetime
from src.core.auth.decorators import (
    login_required, require_any_permission, require_permission
)
from src.db.database import Database

customers_api_bp = Blueprint('customers_api', __name__, url_prefix='/api/customers')


def get_db():
    """Get database connection using CRM database"""
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return Database(db_path)


# ============================================================================
# LIST / SEARCH
# ============================================================================

@customers_api_bp.route('')
@login_required
@require_any_permission('customers.view_all', 'customers.view_own')
def list_customers():
    """List customers with filtering, sorting, and pagination"""
    db = get_db()

    # Filters
    status = request.args.get('status')
    source = request.args.get('source')
    has_active_job = request.args.get('has_active_job')
    search = request.args.get('search', '').strip()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    per_page = min(per_page, 100)  # Max 100 per page
    offset = (page - 1) * per_page

    # Sort
    sort_by = request.args.get('sort', 'created_at')
    sort_dir = request.args.get('dir', 'desc')

    # Build query
    where_clauses = ['c.deleted_at IS NULL']
    params = []

    if status:
        where_clauses.append('c.status = ?')
        params.append(status.upper())

    if source:
        where_clauses.append('c.source = ?')
        params.append(source)

    if has_active_job == 'true':
        where_clauses.append("""EXISTS (
            SELECT 1 FROM jobs j
            WHERE j.customer_id = c.id
            AND j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED')
            AND j.deleted_at IS NULL
        )""")

    if search:
        where_clauses.append("""(
            c.first_name LIKE ? OR
            c.last_name LIKE ? OR
            c.email LIKE ? OR
            c.phone LIKE ? OR
            c.company_name LIKE ?
        )""")
        search_term = f'%{search}%'
        params.extend([search_term] * 5)

    where_sql = ' AND '.join(where_clauses)

    # Allowed sort columns
    allowed_sorts = ['created_at', 'updated_at', 'first_name', 'last_name', 'email']
    if sort_by not in allowed_sorts:
        sort_by = 'created_at'
    sort_dir = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

    # Count total
    count_result = db.execute(f"""
        SELECT COUNT(*) as count
        FROM customers c
        WHERE {where_sql}
    """, tuple(params))
    total = count_result[0]['count'] if count_result else 0

    # Get customers with aggregated data
    query = f"""
        SELECT
            c.*,
            c.first_name || ' ' || c.last_name as display_name,
            (SELECT COUNT(*) FROM vehicles v WHERE v.customer_id = c.id) as vehicle_count,
            (SELECT COUNT(*) FROM jobs j WHERE j.customer_id = c.id AND j.deleted_at IS NULL) as job_count,
            (SELECT COUNT(*) FROM jobs j WHERE j.customer_id = c.id AND j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND j.deleted_at IS NULL) as active_jobs,
            (SELECT SUM(COALESCE(total_actual, total_estimate, 0)) FROM jobs j WHERE j.customer_id = c.id AND j.status = 'COMPLETED') as lifetime_revenue,
            (SELECT MAX(completed_at) FROM jobs j WHERE j.customer_id = c.id AND j.status = 'COMPLETED') as last_service_date
        FROM customers c
        WHERE {where_sql}
        ORDER BY c.{sort_by} {sort_dir}
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])

    customers = db.execute(query, tuple(params))

    # Calculate stats
    stats = get_customer_stats(db)

    return jsonify({
        'customers': customers,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'stats': stats
    })


def get_customer_stats(db):
    """Get customer statistics"""
    result = db.execute("""
        SELECT
            COUNT(*) as total,
            (SELECT COUNT(DISTINCT customer_id) FROM jobs WHERE status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND deleted_at IS NULL) as with_active_jobs,
            (SELECT SUM(COALESCE(total_actual, total_estimate, 0)) FROM jobs WHERE status = 'COMPLETED' AND deleted_at IS NULL) as lifetime_revenue,
            (SELECT AVG(COALESCE(total_actual, total_estimate, 0)) FROM jobs WHERE status = 'COMPLETED' AND deleted_at IS NULL) as avg_job_value
        FROM customers
        WHERE deleted_at IS NULL
    """)
    return result[0] if result else {}


@customers_api_bp.route('/search')
@login_required
def search_customers():
    """Search customers for autocomplete"""
    db = get_db()
    q = request.args.get('q', '').strip()

    if len(q) < 2:
        return jsonify({'customers': []})

    search_term = f'%{q}%'
    customers = db.execute("""
        SELECT id, first_name, last_name, email, phone, company_name,
               first_name || ' ' || last_name as display_name
        FROM customers
        WHERE deleted_at IS NULL
        AND (
            first_name LIKE ? OR
            last_name LIKE ? OR
            email LIKE ? OR
            phone LIKE ? OR
            company_name LIKE ?
        )
        ORDER BY first_name, last_name
        LIMIT 10
    """, (search_term, search_term, search_term, search_term, search_term))

    return jsonify({'customers': customers})


# ============================================================================
# CRUD
# ============================================================================

@customers_api_bp.route('/<int:customer_id>')
@login_required
@require_any_permission('customers.view_all', 'customers.view_own')
def get_customer(customer_id):
    """Get customer details"""
    db = get_db()

    customer = db.execute("""
        SELECT c.*,
               c.first_name || ' ' || c.last_name as display_name
        FROM customers c
        WHERE c.id = ? AND c.deleted_at IS NULL
    """, (customer_id,))

    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    customer = customer[0]

    # Get vehicles
    vehicles = db.execute("""
        SELECT * FROM vehicles
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer_id,))

    customer['vehicles'] = vehicles

    # Get jobs
    jobs = db.execute("""
        SELECT j.*,
               v.year || ' ' || v.make || ' ' || v.model as vehicle,
               t.first_name || ' ' || t.last_name as tech_name
        FROM jobs j
        LEFT JOIN vehicles v ON v.id = j.vehicle_id
        LEFT JOIN technicians t ON t.id = j.assigned_tech_id
        WHERE j.customer_id = ? AND j.deleted_at IS NULL
        ORDER BY j.created_at DESC
        LIMIT 20
    """, (customer_id,))

    customer['jobs'] = jobs

    # Get lifetime stats
    stats = db.execute("""
        SELECT
            COUNT(*) as total_jobs,
            SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_jobs,
            SUM(CASE WHEN status = 'COMPLETED' THEN COALESCE(total_actual, total_estimate, 0) ELSE 0 END) as lifetime_revenue,
            MIN(created_at) as first_job_date,
            MAX(completed_at) as last_service_date
        FROM jobs
        WHERE customer_id = ? AND deleted_at IS NULL
    """, (customer_id,))

    customer['stats'] = stats[0] if stats else {}

    return jsonify(customer)


@customers_api_bp.route('', methods=['POST'])
@login_required
@require_permission('customers.create')
def create_customer():
    """Create new customer"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields
    if not data.get('first_name') and not data.get('company_name'):
        return jsonify({'error': 'First name or company name required'}), 400

    customer_data = {
        'first_name': data.get('first_name', ''),
        'last_name': data.get('last_name', ''),
        'company_name': data.get('company_name'),
        'email': data.get('email'),
        'phone': data.get('phone'),
        'street_address': data.get('address') or data.get('street_address'),
        'city': data.get('city'),
        'state': data.get('state'),
        'zip_code': data.get('zip_code'),
        'source': data.get('source', 'DIRECT'),
        'notes': data.get('notes'),
        'organization_id': g.organization_id,
        'created_at': datetime.now().isoformat()
    }

    customer_id = db.insert('customers', customer_data)

    # Create vehicle if provided
    vehicle_id = None
    if data.get('vehicle'):
        vehicle = data['vehicle']
        vehicle_data = {
            'customer_id': customer_id,
            'year': vehicle.get('year'),
            'make': vehicle.get('make'),
            'model': vehicle.get('model'),
            'vin': vehicle.get('vin'),
            'color': vehicle.get('color'),
            'license_plate': vehicle.get('license_plate'),
            'organization_id': g.organization_id,
            'created_at': datetime.now().isoformat()
        }
        vehicle_id = db.insert('vehicles', vehicle_data)

    return jsonify({
        'success': True,
        'customer_id': customer_id,
        'vehicle_id': vehicle_id,
        'message': 'Customer created successfully'
    })


@customers_api_bp.route('/<int:customer_id>', methods=['PUT'])
@login_required
@require_permission('customers.edit')
def update_customer(customer_id):
    """Update customer"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Check customer exists
    customer = db.execute("SELECT id FROM customers WHERE id = ? AND deleted_at IS NULL", (customer_id,))
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    # Allowed update fields
    allowed = ['first_name', 'last_name', 'company_name', 'email', 'phone',
               'address', 'city', 'state', 'zip_code', 'notes', 'status']

    update_data = {k: v for k, v in data.items() if k in allowed}
    update_data['updated_at'] = datetime.now().isoformat()

    if update_data:
        db.update('customers', customer_id, update_data)

    return jsonify({
        'success': True,
        'message': 'Customer updated'
    })


@customers_api_bp.route('/<int:customer_id>', methods=['DELETE'])
@login_required
@require_permission('customers.delete')
def delete_customer(customer_id):
    """Soft delete customer"""
    db = get_db()

    # Check for active jobs
    active_jobs = db.execute("""
        SELECT COUNT(*) as count FROM jobs
        WHERE customer_id = ? AND status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND deleted_at IS NULL
    """, (customer_id,))

    if active_jobs and active_jobs[0]['count'] > 0:
        return jsonify({'error': 'Cannot delete customer with active jobs'}), 400

    db.execute("""
        UPDATE customers SET deleted_at = ?, updated_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), datetime.now().isoformat(), customer_id))

    return jsonify({
        'success': True,
        'message': 'Customer deleted'
    })


# ============================================================================
# VEHICLES
# ============================================================================

@customers_api_bp.route('/<int:customer_id>/vehicles')
@login_required
def list_customer_vehicles(customer_id):
    """List vehicles for a customer"""
    db = get_db()

    vehicles = db.execute("""
        SELECT * FROM vehicles
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (customer_id,))

    return jsonify({'vehicles': vehicles})


@customers_api_bp.route('/<int:customer_id>/vehicles', methods=['POST'])
@login_required
@require_permission('customers.edit')
def add_customer_vehicle(customer_id):
    """Add vehicle to customer"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    vehicle_data = {
        'customer_id': customer_id,
        'year': data.get('year'),
        'make': data.get('make'),
        'model': data.get('model'),
        'vin': data.get('vin'),
        'color': data.get('color'),
        'license_plate': data.get('license_plate'),
        'organization_id': g.organization_id,
        'created_at': datetime.now().isoformat()
    }

    vehicle_id = db.insert('vehicles', vehicle_data)

    return jsonify({
        'success': True,
        'vehicle_id': vehicle_id,
        'message': 'Vehicle added'
    })
