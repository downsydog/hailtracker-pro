"""
Vehicles API Routes
===================
RESTful API for vehicle/fleet management.

Endpoints:
- GET    /api/vehicles          - List vehicles with filters
- GET    /api/vehicles/:id      - Get vehicle details
- POST   /api/vehicles          - Create new vehicle
- PUT    /api/vehicles/:id      - Update vehicle
- DELETE /api/vehicles/:id      - Delete (soft) vehicle
- GET    /api/vehicles/:id/jobs - Get job history for vehicle
- POST   /api/vehicles/:id/photos - Upload vehicle photos
"""

from flask import Blueprint, request, jsonify, g, current_app
from datetime import datetime
from src.core.auth.decorators import (
    login_required, require_any_permission, require_permission
)
from src.db.database import Database
import os
import uuid

vehicles_api_bp = Blueprint('vehicles_api', __name__, url_prefix='/api/vehicles')


def get_db():
    """Get database connection using CRM database"""
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return Database(db_path)


# ============================================================================
# LIST / SEARCH
# ============================================================================

@vehicles_api_bp.route('')
@login_required
@require_any_permission('vehicles.view_all', 'vehicles.view_own', 'vehicles.view')
def list_vehicles():
    """List vehicles with filtering, sorting, and pagination"""
    db = get_db()

    # Filters
    make = request.args.get('make')
    year_from = request.args.get('year_from', type=int)
    year_to = request.args.get('year_to', type=int)
    customer_id = request.args.get('customer_id')
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
    where_clauses = ['v.deleted_at IS NULL']
    params = []

    if make:
        where_clauses.append('LOWER(v.make) = LOWER(?)')
        params.append(make)

    if year_from:
        where_clauses.append('v.year >= ?')
        params.append(year_from)

    if year_to:
        where_clauses.append('v.year <= ?')
        params.append(year_to)

    if customer_id:
        where_clauses.append('v.customer_id = ?')
        params.append(customer_id)

    if has_active_job == 'true':
        where_clauses.append("""EXISTS (
            SELECT 1 FROM jobs j
            WHERE j.vehicle_id = v.id
            AND j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED')
            AND j.deleted_at IS NULL
        )""")

    if search:
        where_clauses.append("""(
            v.make LIKE ? OR
            v.model LIKE ? OR
            v.vin LIKE ? OR
            v.license_plate LIKE ? OR
            c.first_name LIKE ? OR
            c.last_name LIKE ?
        )""")
        search_term = f'%{search}%'
        params.extend([search_term] * 6)

    where_sql = ' AND '.join(where_clauses)

    # Allowed sort columns
    allowed_sorts = ['created_at', 'updated_at', 'year', 'make', 'model']
    if sort_by not in allowed_sorts:
        sort_by = 'created_at'
    sort_dir = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

    # Count total
    count_result = db.execute(f"""
        SELECT COUNT(*) as count
        FROM vehicles v
        LEFT JOIN customers c ON c.id = v.customer_id
        WHERE {where_sql}
    """, tuple(params))
    total = count_result[0]['count'] if count_result else 0

    # Get vehicles with aggregated data
    query = f"""
        SELECT
            v.*,
            v.year || ' ' || v.make || ' ' || v.model as display_name,
            c.first_name || ' ' || c.last_name as owner_name,
            c.phone as owner_phone,
            c.email as owner_email,
            (SELECT COUNT(*) FROM jobs j WHERE j.vehicle_id = v.id AND j.deleted_at IS NULL) as job_count,
            (SELECT COUNT(*) FROM jobs j WHERE j.vehicle_id = v.id AND j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND j.deleted_at IS NULL) as active_jobs,
            (SELECT j.id FROM jobs j WHERE j.vehicle_id = v.id AND j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND j.deleted_at IS NULL ORDER BY j.created_at DESC LIMIT 1) as current_job_id,
            (SELECT j.job_number FROM jobs j WHERE j.vehicle_id = v.id AND j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND j.deleted_at IS NULL ORDER BY j.created_at DESC LIMIT 1) as current_job_number,
            (SELECT j.status FROM jobs j WHERE j.vehicle_id = v.id AND j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND j.deleted_at IS NULL ORDER BY j.created_at DESC LIMIT 1) as current_job_status,
            (SELECT MAX(j.completed_at) FROM jobs j WHERE j.vehicle_id = v.id AND j.status = 'COMPLETED') as last_service_date,
            (SELECT SUM(COALESCE(j.total_actual, j.total_estimate, 0)) FROM jobs j WHERE j.vehicle_id = v.id AND j.status = 'COMPLETED') as lifetime_revenue
        FROM vehicles v
        LEFT JOIN customers c ON c.id = v.customer_id
        WHERE {where_sql}
        ORDER BY v.{sort_by} {sort_dir}
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])

    vehicles = db.execute(query, tuple(params))

    # Calculate stats
    stats = get_vehicle_stats(db)

    return jsonify({
        'vehicles': vehicles,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'stats': stats
    })


def get_vehicle_stats(db):
    """Get vehicle statistics"""
    result = db.execute("""
        SELECT
            COUNT(*) as total,
            (SELECT COUNT(DISTINCT v.id) FROM vehicles v
             JOIN jobs j ON j.vehicle_id = v.id
             WHERE j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED')
             AND j.deleted_at IS NULL AND v.deleted_at IS NULL) as in_shop_now,
            (SELECT COUNT(*) FROM jobs WHERE status = 'COMPLETED' AND deleted_at IS NULL) as completed_jobs,
            (SELECT COUNT(DISTINCT customer_id) FROM vehicles
             WHERE deleted_at IS NULL
             AND customer_id IN (
                 SELECT customer_id FROM vehicles
                 WHERE deleted_at IS NULL
                 GROUP BY customer_id HAVING COUNT(*) > 1
             )) as repeat_customers
        FROM vehicles
        WHERE deleted_at IS NULL
    """)
    return result[0] if result else {}


@vehicles_api_bp.route('/makes')
@login_required
def list_makes():
    """List unique makes for filter dropdown"""
    db = get_db()

    makes = db.execute("""
        SELECT DISTINCT make, COUNT(*) as count
        FROM vehicles
        WHERE deleted_at IS NULL AND make IS NOT NULL AND make != ''
        GROUP BY make
        ORDER BY count DESC, make ASC
    """)

    return jsonify({'makes': makes})


# ============================================================================
# CRUD
# ============================================================================

@vehicles_api_bp.route('/<int:vehicle_id>')
@login_required
@require_any_permission('vehicles.view_all', 'vehicles.view_own')
def get_vehicle(vehicle_id):
    """Get vehicle details"""
    db = get_db()

    vehicle = db.execute("""
        SELECT v.*,
               v.year || ' ' || v.make || ' ' || v.model as display_name,
               c.id as customer_id,
               c.first_name || ' ' || c.last_name as owner_name,
               c.phone as owner_phone,
               c.email as owner_email,
               c.address as owner_address,
               c.city as owner_city,
               c.state as owner_state,
               c.zip_code as owner_zip
        FROM vehicles v
        LEFT JOIN customers c ON c.id = v.customer_id
        WHERE v.id = ? AND v.deleted_at IS NULL
    """, (vehicle_id,))

    if not vehicle:
        return jsonify({'error': 'Vehicle not found'}), 404

    vehicle = vehicle[0]

    # Get job history
    jobs = db.execute("""
        SELECT j.*,
               t.first_name || ' ' || t.last_name as tech_name
        FROM jobs j
        LEFT JOIN users t ON t.id = j.assigned_tech_id
        WHERE j.vehicle_id = ? AND j.deleted_at IS NULL
        ORDER BY j.created_at DESC
        LIMIT 20
    """, (vehicle_id,))

    vehicle['jobs'] = jobs

    # Get photos
    photos = db.execute("""
        SELECT * FROM vehicle_photos
        WHERE vehicle_id = ?
        ORDER BY created_at DESC
    """, (vehicle_id,)) if table_exists(db, 'vehicle_photos') else []

    vehicle['photos'] = photos

    # Get stats
    stats = db.execute("""
        SELECT
            COUNT(*) as total_jobs,
            SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_jobs,
            SUM(CASE WHEN status = 'COMPLETED' THEN COALESCE(total_actual, total_estimate, 0) ELSE 0 END) as lifetime_revenue,
            MIN(created_at) as first_job_date,
            MAX(completed_at) as last_service_date
        FROM jobs
        WHERE vehicle_id = ? AND deleted_at IS NULL
    """, (vehicle_id,))

    vehicle['stats'] = stats[0] if stats else {}

    return jsonify(vehicle)


@vehicles_api_bp.route('', methods=['POST'])
@login_required
@require_permission('vehicles.create')
def create_vehicle():
    """Create new vehicle"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields
    if not data.get('customer_id'):
        return jsonify({'error': 'Customer is required'}), 400

    if not data.get('make') or not data.get('model'):
        return jsonify({'error': 'Make and model are required'}), 400

    # Verify customer exists
    customer = db.execute("SELECT id FROM customers WHERE id = ? AND deleted_at IS NULL", (data['customer_id'],))
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    vehicle_data = {
        'customer_id': data.get('customer_id'),
        'year': data.get('year'),
        'make': data.get('make'),
        'model': data.get('model'),
        'vin': data.get('vin'),
        'color': data.get('color'),
        'license_plate': data.get('license_plate'),
        'trim': data.get('trim'),
        'engine': data.get('engine'),
        'mileage': data.get('mileage'),
        'notes': data.get('notes'),
        'organization_id': g.organization_id,
        'created_at': datetime.now().isoformat()
    }

    vehicle_id = db.insert('vehicles', vehicle_data)

    return jsonify({
        'success': True,
        'vehicle_id': vehicle_id,
        'message': 'Vehicle created successfully'
    })


@vehicles_api_bp.route('/<int:vehicle_id>', methods=['PUT'])
@login_required
@require_permission('vehicles.edit')
def update_vehicle(vehicle_id):
    """Update vehicle"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Check vehicle exists
    vehicle = db.execute("SELECT id FROM vehicles WHERE id = ? AND deleted_at IS NULL", (vehicle_id,))
    if not vehicle:
        return jsonify({'error': 'Vehicle not found'}), 404

    # Allowed update fields
    allowed = ['customer_id', 'year', 'make', 'model', 'vin', 'color',
               'license_plate', 'trim', 'engine', 'mileage', 'notes']

    update_data = {k: v for k, v in data.items() if k in allowed}
    update_data['updated_at'] = datetime.now().isoformat()

    if update_data:
        db.update('vehicles', vehicle_id, update_data)

    return jsonify({
        'success': True,
        'message': 'Vehicle updated'
    })


@vehicles_api_bp.route('/<int:vehicle_id>', methods=['DELETE'])
@login_required
@require_permission('vehicles.delete')
def delete_vehicle(vehicle_id):
    """Soft delete vehicle"""
    db = get_db()

    # Check for active jobs
    active_jobs = db.execute("""
        SELECT COUNT(*) as count FROM jobs
        WHERE vehicle_id = ? AND status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED') AND deleted_at IS NULL
    """, (vehicle_id,))

    if active_jobs and active_jobs[0]['count'] > 0:
        return jsonify({'error': 'Cannot delete vehicle with active jobs'}), 400

    db.execute("""
        UPDATE vehicles SET deleted_at = ?, updated_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), datetime.now().isoformat(), vehicle_id))

    return jsonify({
        'success': True,
        'message': 'Vehicle deleted'
    })


# ============================================================================
# JOB HISTORY
# ============================================================================

@vehicles_api_bp.route('/<int:vehicle_id>/jobs')
@login_required
def get_vehicle_jobs(vehicle_id):
    """Get job history for vehicle"""
    db = get_db()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page

    # Get jobs
    jobs = db.execute("""
        SELECT j.*,
               t.first_name || ' ' || t.last_name as tech_name,
               h.name as hail_event_name
        FROM jobs j
        LEFT JOIN users t ON t.id = j.assigned_tech_id
        LEFT JOIN hail_events h ON h.id = j.hail_event_id
        WHERE j.vehicle_id = ? AND j.deleted_at IS NULL
        ORDER BY j.created_at DESC
        LIMIT ? OFFSET ?
    """, (vehicle_id, per_page, offset))

    # Count total
    count_result = db.execute("""
        SELECT COUNT(*) as count FROM jobs
        WHERE vehicle_id = ? AND deleted_at IS NULL
    """, (vehicle_id,))
    total = count_result[0]['count'] if count_result else 0

    return jsonify({
        'jobs': jobs,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


# ============================================================================
# PHOTOS
# ============================================================================

@vehicles_api_bp.route('/<int:vehicle_id>/photos', methods=['POST'])
@login_required
@require_permission('vehicles.edit')
def upload_photo(vehicle_id):
    """Upload vehicle photo"""
    db = get_db()

    # Check vehicle exists
    vehicle = db.execute("SELECT id FROM vehicles WHERE id = ? AND deleted_at IS NULL", (vehicle_id,))
    if not vehicle:
        return jsonify({'error': 'Vehicle not found'}), 404

    if 'photo' not in request.files:
        return jsonify({'error': 'No photo provided'}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'error': 'Invalid file type'}), 400

    # Generate unique filename
    filename = f"{uuid.uuid4()}.{ext}"
    upload_dir = os.path.join('static', 'uploads', 'vehicles', str(vehicle_id))
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    file.save(filepath)

    # Save to database if table exists
    photo_id = None
    if table_exists(db, 'vehicle_photos'):
        photo_id = db.insert('vehicle_photos', {
            'vehicle_id': vehicle_id,
            'filename': filename,
            'filepath': filepath,
            'photo_type': request.form.get('type', 'general'),
            'notes': request.form.get('notes'),
            'uploaded_by': g.current_user['id'],
            'created_at': datetime.now().isoformat()
        })

    return jsonify({
        'success': True,
        'photo_id': photo_id,
        'filepath': '/' + filepath.replace('\\', '/'),
        'message': 'Photo uploaded'
    })


@vehicles_api_bp.route('/<int:vehicle_id>/photos/<int:photo_id>', methods=['DELETE'])
@login_required
@require_permission('vehicles.edit')
def delete_photo(vehicle_id, photo_id):
    """Delete vehicle photo"""
    db = get_db()

    if not table_exists(db, 'vehicle_photos'):
        return jsonify({'error': 'Photos not supported'}), 400

    photo = db.execute("SELECT filepath FROM vehicle_photos WHERE id = ? AND vehicle_id = ?", (photo_id, vehicle_id))
    if not photo:
        return jsonify({'error': 'Photo not found'}), 404

    # Delete file
    try:
        os.remove(photo[0]['filepath'])
    except OSError:
        pass

    # Delete from database
    db.execute("DELETE FROM vehicle_photos WHERE id = ?", (photo_id,))

    return jsonify({
        'success': True,
        'message': 'Photo deleted'
    })


# ============================================================================
# HELPERS
# ============================================================================

def table_exists(db, table_name):
    """Check if table exists"""
    result = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return len(result) > 0
