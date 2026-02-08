"""
Jobs API Routes
===============
RESTful API for job management.

Endpoints:
- GET    /api/jobs          - List jobs with filters
- GET    /api/jobs/:id      - Get job details
- POST   /api/jobs          - Create new job
- PUT    /api/jobs/:id      - Update job
- DELETE /api/jobs/:id      - Delete (soft) job
- POST   /api/jobs/:id/status   - Update job status
- POST   /api/jobs/:id/assign   - Assign technician
"""

from flask import Blueprint, request, jsonify, g, current_app
from datetime import datetime, timedelta
from src.core.auth.decorators import (
    login_required, require_any_permission, require_permission
)
from src.db.database import Database

jobs_api_bp = Blueprint('jobs_api', __name__, url_prefix='/api/jobs')


def get_db():
    """Get database connection using app config"""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker_crm.db')
    return Database(db_path)


# ============================================================================
# LIST / SEARCH
# ============================================================================

@jobs_api_bp.route('')
@login_required
@require_any_permission('jobs.view_all', 'jobs.view_own')
def list_jobs():
    """List jobs with filtering, sorting, and pagination"""
    db = get_db()

    # Filters
    status = request.args.get('status')
    tech_id = request.args.get('tech_id')
    customer_id = request.args.get('customer_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
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
    where_clauses = ['j.deleted_at IS NULL']
    params = []

    # Filter by tech for tech role
    user_role = g.current_user.get('role')
    if user_role == 'technician':
        where_clauses.append('j.assigned_tech_id = ?')
        params.append(str(g.current_user['id']))

    if status:
        if status == 'active':
            where_clauses.append("j.status NOT IN ('COMPLETED', 'CANCELLED', 'INVOICED')")
        else:
            where_clauses.append('j.status = ?')
            params.append(status.upper())

    if tech_id:
        where_clauses.append('j.assigned_tech_id = ?')
        params.append(tech_id)

    if customer_id:
        where_clauses.append('j.customer_id = ?')
        params.append(customer_id)

    if date_from:
        where_clauses.append('j.scheduled_drop_off >= ?')
        params.append(date_from)

    if date_to:
        where_clauses.append('j.scheduled_drop_off <= ?')
        params.append(date_to)

    if search:
        where_clauses.append("""(
            j.job_number LIKE ? OR
            c.first_name LIKE ? OR
            c.last_name LIKE ? OR
            v.make LIKE ? OR
            v.model LIKE ?
        )""")
        search_term = f'%{search}%'
        params.extend([search_term] * 5)

    where_sql = ' AND '.join(where_clauses)

    # Allowed sort columns
    allowed_sorts = ['created_at', 'updated_at', 'scheduled_drop_off', 'status', 'job_number']
    if sort_by not in allowed_sorts:
        sort_by = 'created_at'
    sort_dir = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

    # Count total
    count_result = db.execute(f"""
        SELECT COUNT(*) as count
        FROM jobs j
        LEFT JOIN customers c ON c.id = j.customer_id
        LEFT JOIN vehicles v ON v.id = j.vehicle_id
        WHERE {where_sql}
    """, tuple(params))
    total = count_result[0]['count'] if count_result else 0

    # Get jobs with related data
    query = f"""
        SELECT
            j.*,
            c.first_name || ' ' || c.last_name as customer_name,
            c.phone as customer_phone,
            c.email as customer_email,
            v.year as vehicle_year,
            v.make as vehicle_make,
            v.model as vehicle_model,
            v.vin as vehicle_vin,
            t.first_name || ' ' || t.last_name as tech_name
        FROM jobs j
        LEFT JOIN customers c ON c.id = j.customer_id
        LEFT JOIN vehicles v ON v.id = j.vehicle_id
        LEFT JOIN technicians t ON t.id = j.assigned_tech_id
        WHERE {where_sql}
        ORDER BY j.{sort_by} {sort_dir}
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])

    jobs = db.execute(query, tuple(params))

    # Calculate stats
    stats = get_job_stats(db)

    return jsonify({
        'jobs': jobs,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'stats': stats
    })


def get_job_stats(db):
    """Get job statistics"""
    today = datetime.now().date().isoformat()
    week_start = (datetime.now().date() - timedelta(days=datetime.now().weekday())).isoformat()

    result = db.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status IN ('NEW', 'SCHEDULED', 'IN_PROGRESS', 'WAITING_PARTS') THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'COMPLETED' AND DATE(completed_at) >= ? THEN 1 ELSE 0 END) as completed_this_week,
            SUM(CASE WHEN status = 'COMPLETED' THEN COALESCE(total_actual, total_estimate, 0) ELSE 0 END) as total_revenue,
            SUM(CASE WHEN scheduled_drop_off = ? THEN 1 ELSE 0 END) as scheduled_today,
            SUM(CASE WHEN status = 'NEW' THEN 1 ELSE 0 END) as new_jobs
        FROM jobs
        WHERE deleted_at IS NULL
    """, (week_start, today))
    return result[0] if result else {}


# ============================================================================
# CRUD
# ============================================================================

@jobs_api_bp.route('/<int:job_id>')
@login_required
@require_any_permission('jobs.view_all', 'jobs.view_own')
def get_job(job_id):
    """Get job details"""
    db = get_db()

    job = db.execute("""
        SELECT j.*,
               c.first_name || ' ' || c.last_name as customer_name,
               c.phone as customer_phone,
               c.email as customer_email,
               c.street_address as customer_address,
               v.year as vehicle_year,
               v.make as vehicle_make,
               v.model as vehicle_model,
               v.vin as vehicle_vin,
               v.color as vehicle_color,
               v.license_plate as vehicle_plate,
               t.first_name || ' ' || t.last_name as tech_name
        FROM jobs j
        LEFT JOIN customers c ON c.id = j.customer_id
        LEFT JOIN vehicles v ON v.id = j.vehicle_id
        LEFT JOIN technicians t ON t.id = j.assigned_tech_id
        WHERE j.id = ? AND j.deleted_at IS NULL
    """, (job_id,))

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    job = job[0]

    # Get status history (changed_by stores user ID as string)
    history = db.execute("""
        SELECT jsh.*
        FROM job_status_history jsh
        WHERE jsh.job_id = ?
        ORDER BY jsh.changed_at DESC
        LIMIT 10
    """, (job_id,)) if table_exists(db, 'job_status_history') else []

    job['status_history'] = history

    return jsonify(job)


@jobs_api_bp.route('', methods=['POST'])
@login_required
@require_permission('jobs.create')
def create_job():
    """Create new job"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields
    if not data.get('customer_id'):
        return jsonify({'error': 'Customer is required'}), 400

    # Generate job number
    job_number = f"JOB-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    job_data = {
        'job_number': job_number,
        'customer_id': data.get('customer_id'),
        'vehicle_id': data.get('vehicle_id'),
        'status': 'NEW',
        'damage_type': data.get('damage_type', 'HAIL'),
        'tech_notes': data.get('damage_description') or data.get('tech_notes'),
        'total_estimate': data.get('estimated_repair_cost') or data.get('total_estimate'),
        'scheduled_drop_off': data.get('scheduled_drop_off'),
        'assigned_tech_id': data.get('assigned_tech_id'),
        'internal_notes': data.get('notes') or data.get('internal_notes'),
        'created_at': datetime.now().isoformat()
    }
    # Remove None values to avoid inserting NULLs for non-nullable columns
    job_data = {k: v for k, v in job_data.items() if v is not None}

    job_id = db.insert('jobs', job_data)

    # Log status history
    if table_exists(db, 'job_status_history'):
        db.insert('job_status_history', {
            'job_id': job_id,
            'from_status': None,
            'to_status': 'NEW',
            'changed_by': str(g.current_user['id']),
            'changed_at': datetime.now().isoformat(),
            'notes': 'Job created'
        }, auto_timestamps=False)

    return jsonify({
        'success': True,
        'job_id': job_id,
        'job_number': job_number,
        'message': 'Job created successfully'
    })


@jobs_api_bp.route('/<int:job_id>', methods=['PUT'])
@login_required
@require_permission('jobs.edit')
def update_job(job_id):
    """Update job"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Check job exists
    job = db.execute("SELECT id FROM jobs WHERE id = ? AND deleted_at IS NULL", (job_id,))
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Field mapping: API field -> database column
    field_mapping = {
        'customer_id': 'customer_id',
        'vehicle_id': 'vehicle_id',
        'damage_type': 'damage_type',
        'damage_description': 'tech_notes',
        'tech_notes': 'tech_notes',
        'estimated_repair_cost': 'total_estimate',
        'total_estimate': 'total_estimate',
        'final_cost': 'total_actual',
        'total_actual': 'total_actual',
        'scheduled_drop_off': 'scheduled_drop_off',
        'assigned_tech_id': 'assigned_tech_id',
        'notes': 'internal_notes',
        'internal_notes': 'internal_notes',
        'priority': 'priority',
        'status': 'status',
    }

    update_data = {}
    for api_field, db_column in field_mapping.items():
        if api_field in data:
            update_data[db_column] = data[api_field]
    update_data['updated_at'] = datetime.now().isoformat()

    if update_data:
        db.update('jobs', job_id, update_data)

    return jsonify({
        'success': True,
        'message': 'Job updated'
    })


@jobs_api_bp.route('/<int:job_id>', methods=['DELETE'])
@login_required
@require_permission('jobs.delete')
def delete_job(job_id):
    """Soft delete job"""
    db = get_db()

    db.execute("""
        UPDATE jobs SET deleted_at = ?, updated_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), datetime.now().isoformat(), job_id))

    return jsonify({
        'success': True,
        'message': 'Job deleted'
    })


# ============================================================================
# ACTIONS
# ============================================================================

@jobs_api_bp.route('/<int:job_id>/status', methods=['POST'])
@login_required
@require_permission('jobs.edit')
def update_status(job_id):
    """Update job status"""
    db = get_db()
    data = request.get_json()

    new_status = data.get('status', '').upper()
    valid_statuses = ['NEW', 'SCHEDULED', 'CHECKED_IN', 'IN_PROGRESS', 'WAITING_PARTS',
                      'QUALITY_CHECK', 'READY_FOR_PICKUP', 'COMPLETED', 'INVOICED', 'CANCELLED']

    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400

    # Get current status
    job = db.execute("SELECT status FROM jobs WHERE id = ? AND deleted_at IS NULL", (job_id,))
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    old_status = job[0]['status']

    update_data = {
        'status': new_status,
        'updated_at': datetime.now().isoformat(),
        'status_changed_at': datetime.now().isoformat()
    }

    # Set completed timestamp
    if new_status == 'COMPLETED':
        update_data['completed_at'] = datetime.now().isoformat()

    db.update('jobs', job_id, update_data)

    # Log status history
    if table_exists(db, 'job_status_history'):
        db.insert('job_status_history', {
            'job_id': job_id,
            'from_status': old_status,
            'to_status': new_status,
            'changed_by': str(g.current_user['id']),
            'changed_at': datetime.now().isoformat(),
            'notes': data.get('notes', '')
        }, auto_timestamps=False)

    return jsonify({
        'success': True,
        'message': f'Status updated to {new_status}'
    })


@jobs_api_bp.route('/<int:job_id>/assign', methods=['POST'])
@login_required
@require_permission('jobs.assign')
def assign_tech(job_id):
    """Assign technician to job"""
    db = get_db()
    data = request.get_json()

    tech_id = data.get('tech_id')
    if not tech_id:
        return jsonify({'error': 'tech_id required'}), 400

    # Verify tech exists and is a technician
    tech = db.execute("SELECT id, role FROM users WHERE id = ?", (tech_id,))
    if not tech:
        return jsonify({'error': 'Technician not found'}), 404

    db.update('jobs', job_id, {
        'assigned_tech_id': tech_id,
        'updated_at': datetime.now().isoformat()
    })

    # If job is NEW and now has a scheduled date, move to SCHEDULED
    job = db.execute("SELECT status, scheduled_drop_off FROM jobs WHERE id = ?", (job_id,))
    if job and job[0]['status'] == 'NEW' and job[0].get('scheduled_drop_off'):
        db.update('jobs', job_id, {'status': 'SCHEDULED'})

    return jsonify({
        'success': True,
        'message': 'Technician assigned'
    })


@jobs_api_bp.route('/techs')
@login_required
def list_techs():
    """List available technicians for assignment"""
    db = get_db()

    techs = db.execute("""
        SELECT id, first_name, last_name, email
        FROM users
        WHERE role = 'technician' AND is_active = 1
        ORDER BY first_name, last_name
    """)

    return jsonify({'techs': techs})


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
