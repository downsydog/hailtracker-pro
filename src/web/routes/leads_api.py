"""
Leads API Routes
================
RESTful API for lead management (office inbox workflow).

Endpoints:
- GET    /api/leads          - List leads with filters
- GET    /api/leads/:id      - Get lead details
- POST   /api/leads          - Create new lead
- PUT    /api/leads/:id      - Update lead
- DELETE /api/leads/:id      - Delete (soft) lead
- POST   /api/leads/:id/convert  - Convert lead to customer
- POST   /api/leads/:id/status   - Update lead status
- POST   /api/leads/:id/schedule - Schedule appointment
"""

from flask import Blueprint, request, jsonify, g, current_app
from datetime import datetime
from src.core.auth.decorators import (
    login_required, require_any_permission, require_permission
)
from src.db.database import Database

leads_api_bp = Blueprint('leads_api', __name__, url_prefix='/api/leads')


def get_db():
    """Get database connection using app config"""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker_crm.db')
    return Database(db_path)


# ============================================================================
# LIST / SEARCH
# ============================================================================

@leads_api_bp.route('')
@login_required
@require_any_permission('leads.view_all', 'leads.view_own')
def list_leads():
    """List leads with filtering, sorting, and pagination"""
    db = get_db()

    # Filters
    status = request.args.get('status')
    temperature = request.args.get('temperature')
    source = request.args.get('source')
    assigned_to = request.args.get('assigned_to')
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
    where_clauses = ['deleted_at IS NULL']
    params = []

    # Only own leads for sales role
    user_role = g.current_user.get('role')
    if user_role == 'sales':
        where_clauses.append('assigned_to = ?')
        params.append(str(g.current_user['id']))

    if status:
        if status == 'active':
            where_clauses.append("status NOT IN ('CONVERTED', 'LOST')")
        else:
            where_clauses.append('status = ?')
            params.append(status.upper())

    if temperature:
        where_clauses.append('temperature = ?')
        params.append(temperature.upper())

    if source:
        where_clauses.append('source = ?')
        params.append(source)

    if assigned_to:
        where_clauses.append('assigned_to = ?')
        params.append(assigned_to)

    if search:
        where_clauses.append("""(
            first_name LIKE ? OR
            last_name LIKE ? OR
            email LIKE ? OR
            phone LIKE ? OR
            company_name LIKE ?
        )""")
        search_term = f'%{search}%'
        params.extend([search_term] * 5)

    where_sql = ' AND '.join(where_clauses)

    # Allowed sort columns
    allowed_sorts = ['created_at', 'updated_at', 'first_name', 'last_name', 'status', 'temperature', 'score']
    if sort_by not in allowed_sorts:
        sort_by = 'created_at'
    sort_dir = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

    # Count total
    count_result = db.execute(f"SELECT COUNT(*) as count FROM leads WHERE {where_sql}", tuple(params))
    total = count_result[0]['count'] if count_result else 0

    # Get leads
    query = f"""
        SELECT
            l.*,
            COALESCE(l.first_name || ' ' || l.last_name, l.company_name) as display_name
        FROM leads l
        WHERE {where_sql}
        ORDER BY {sort_by} {sort_dir}
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])

    leads = db.execute(query, tuple(params))

    # Calculate stats
    stats = get_lead_stats(db)

    return jsonify({
        'leads': leads,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'stats': stats
    })


def get_lead_stats(db):
    """Get lead statistics"""
    result = db.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'NEW' THEN 1 ELSE 0 END) as new,
            SUM(CASE WHEN status = 'CONTACTED' THEN 1 ELSE 0 END) as contacted,
            SUM(CASE WHEN status = 'QUALIFIED' THEN 1 ELSE 0 END) as qualified,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
            SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as lost
        FROM leads
        WHERE deleted_at IS NULL
    """)
    return result[0] if result else {}


# ============================================================================
# CRUD
# ============================================================================

@leads_api_bp.route('/<int:lead_id>')
@login_required
@require_any_permission('leads.view_all', 'leads.view_own')
def get_lead(lead_id):
    """Get lead details"""
    db = get_db()

    lead = db.execute("""
        SELECT l.*,
               h.event_name as hail_event_name,
               h.event_date as hail_event_date
        FROM leads l
        LEFT JOIN hail_events h ON h.id = l.hail_event_id
        WHERE l.id = ? AND l.deleted_at IS NULL
    """, (lead_id,))

    if not lead:
        return jsonify({'error': 'Lead not found'}), 404

    lead = lead[0]

    # Get activity/notes
    activities = db.execute("""
        SELECT * FROM lead_activities
        WHERE lead_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (lead_id,)) if table_exists(db, 'lead_activities') else []

    lead['activities'] = activities

    return jsonify(lead)


@leads_api_bp.route('', methods=['POST'])
@login_required
@require_permission('leads.create')
def create_lead():
    """Create new lead"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields
    if not data.get('first_name') and not data.get('company_name'):
        return jsonify({'error': 'First name or company name required'}), 400

    lead_data = {
        'first_name': data.get('first_name', ''),
        'last_name': data.get('last_name', ''),
        'company_name': data.get('company_name'),
        'email': data.get('email'),
        'phone': data.get('phone'),
        'source': data.get('source', 'MANUAL'),
        'temperature': data.get('temperature', 'WARM'),
        'status': 'NEW',
        'hail_event_id': data.get('hail_event_id'),
        'assigned_to': data.get('assigned_to') or str(g.current_user['id']),
        'assigned_at': datetime.now().isoformat(),
        'vehicle_year': data.get('vehicle_year'),
        'vehicle_make': data.get('vehicle_make'),
        'vehicle_model': data.get('vehicle_model'),
        'damage_type': data.get('damage_type'),
        'damage_description': data.get('damage_description'),
        'notes': data.get('notes'),
        'organization_id': g.organization_id
    }

    lead_id = db.insert('leads', lead_data)

    return jsonify({
        'success': True,
        'lead_id': lead_id,
        'message': 'Lead created successfully'
    })


@leads_api_bp.route('/<int:lead_id>', methods=['PUT'])
@login_required
@require_permission('leads.edit')
def update_lead(lead_id):
    """Update lead"""
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Check lead exists
    lead = db.execute("SELECT id FROM leads WHERE id = ? AND deleted_at IS NULL", (lead_id,))
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404

    # Allowed update fields
    allowed = ['first_name', 'last_name', 'company_name', 'email', 'phone',
               'temperature', 'status', 'assigned_to', 'next_follow_up_date',
               'vehicle_year', 'vehicle_make', 'vehicle_model',
               'damage_type', 'damage_description', 'notes', 'lost_reason']

    update_data = {k: v for k, v in data.items() if k in allowed}
    update_data['updated_at'] = datetime.now().isoformat()

    if update_data:
        db.update('leads', lead_id, update_data)

    return jsonify({
        'success': True,
        'message': 'Lead updated'
    })


@leads_api_bp.route('/<int:lead_id>', methods=['DELETE'])
@login_required
@require_permission('leads.delete')
def delete_lead(lead_id):
    """Soft delete lead"""
    db = get_db()

    db.execute("""
        UPDATE leads SET deleted_at = ?, updated_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), datetime.now().isoformat(), lead_id))

    return jsonify({
        'success': True,
        'message': 'Lead deleted'
    })


# ============================================================================
# ACTIONS
# ============================================================================

@leads_api_bp.route('/<int:lead_id>/status', methods=['POST'])
@login_required
@require_permission('leads.edit')
def update_status(lead_id):
    """Update lead status"""
    db = get_db()
    data = request.get_json()

    new_status = data.get('status', '').upper()
    valid_statuses = ['NEW', 'CONTACTED', 'QUALIFIED', 'NEGOTIATING', 'CONVERTED', 'LOST']

    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400

    update_data = {
        'status': new_status,
        'updated_at': datetime.now().isoformat()
    }

    if new_status == 'CONTACTED':
        update_data['last_contact_date'] = datetime.now().date().isoformat()
        update_data['follow_up_count'] = db.execute(
            "SELECT follow_up_count FROM leads WHERE id = ?", (lead_id,)
        )[0]['follow_up_count'] + 1

    if new_status == 'LOST' and data.get('lost_reason'):
        update_data['lost_reason'] = data['lost_reason']

    db.update('leads', lead_id, update_data)

    return jsonify({
        'success': True,
        'message': f'Status updated to {new_status}'
    })


@leads_api_bp.route('/<int:lead_id>/convert', methods=['POST'])
@login_required
@require_permission('leads.convert')
def convert_lead(lead_id):
    """Convert lead to customer"""
    db = get_db()
    data = request.get_json() or {}

    # Get lead
    lead = db.execute("SELECT * FROM leads WHERE id = ? AND deleted_at IS NULL", (lead_id,))
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    lead = lead[0]

    if lead['status'] == 'CONVERTED':
        return jsonify({'error': 'Lead already converted'}), 400

    # Create customer
    customer_data = {
        'first_name': lead['first_name'],
        'last_name': lead['last_name'],
        'company_name': lead.get('company_name'),
        'email': lead['email'],
        'phone': lead['phone'],
        'source': lead['source'],
        'lead_id': lead_id,
        'notes': data.get('notes') or lead.get('notes'),
        'organization_id': g.organization_id,
        'created_at': datetime.now().isoformat()
    }

    customer_id = db.insert('customers', customer_data)

    # Create vehicle if info exists
    vehicle_id = None
    if lead.get('vehicle_year') or lead.get('vehicle_make'):
        vehicle_data = {
            'customer_id': customer_id,
            'year': lead.get('vehicle_year'),
            'make': lead.get('vehicle_make'),
            'model': lead.get('vehicle_model'),
            'organization_id': g.organization_id
        }
        vehicle_id = db.insert('vehicles', vehicle_data)

    # Update lead
    db.update('leads', lead_id, {
        'status': 'CONVERTED',
        'converted_to_customer_id': customer_id,
        'updated_at': datetime.now().isoformat()
    })

    # Create job if requested
    job_id = None
    if data.get('create_job'):
        job_data = {
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'status': 'NEW',
            'job_number': f"JOB-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'damage_type': lead.get('damage_type', 'HAIL'),
            'damage_description': lead.get('damage_description'),
            'hail_event_id': lead.get('hail_event_id'),
            'estimated_repair_cost': lead.get('estimated_repair_cost'),
            'organization_id': g.organization_id,
            'created_at': datetime.now().isoformat()
        }
        job_id = db.insert('jobs', job_data)

    return jsonify({
        'success': True,
        'message': 'Lead converted to customer',
        'customer_id': customer_id,
        'vehicle_id': vehicle_id,
        'job_id': job_id
    })


@leads_api_bp.route('/<int:lead_id>/schedule', methods=['POST'])
@login_required
@require_permission('schedule.create')
def schedule_appointment(lead_id):
    """Schedule appointment for lead"""
    db = get_db()
    data = request.get_json()

    if not data.get('date') or not data.get('time'):
        return jsonify({'error': 'Date and time required'}), 400

    # Get lead
    lead = db.execute("SELECT * FROM leads WHERE id = ? AND deleted_at IS NULL", (lead_id,))
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    lead = lead[0]

    # Create appointment
    appointment_data = {
        'lead_id': lead_id,
        'customer_name': f"{lead['first_name']} {lead['last_name']}".strip() or lead.get('company_name'),
        'phone': lead['phone'],
        'email': lead['email'],
        'appointment_date': data['date'],
        'appointment_time': data['time'],
        'appointment_type': data.get('type', 'ESTIMATE'),
        'notes': data.get('notes'),
        'status': 'SCHEDULED',
        'organization_id': g.organization_id,
        'created_at': datetime.now().isoformat()
    }

    # Check if appointments table exists, if not use a simple approach
    if table_exists(db, 'appointments'):
        appointment_id = db.insert('appointments', appointment_data)
    else:
        # Update lead with follow-up date
        db.update('leads', lead_id, {
            'next_follow_up_date': data['date'],
            'notes': (lead.get('notes', '') or '') + f"\n[{datetime.now().strftime('%Y-%m-%d')}] Appointment scheduled for {data['date']} at {data['time']}",
            'updated_at': datetime.now().isoformat()
        })
        appointment_id = None

    # Update lead status if still NEW
    if lead['status'] == 'NEW':
        db.update('leads', lead_id, {'status': 'CONTACTED'})

    return jsonify({
        'success': True,
        'message': 'Appointment scheduled',
        'appointment_id': appointment_id
    })


@leads_api_bp.route('/<int:lead_id>/assign', methods=['POST'])
@login_required
@require_permission('leads.assign')
def assign_lead(lead_id):
    """Assign lead to user"""
    db = get_db()
    data = request.get_json()

    assigned_to = data.get('assigned_to')
    if not assigned_to:
        return jsonify({'error': 'assigned_to required'}), 400

    db.update('leads', lead_id, {
        'assigned_to': str(assigned_to),
        'assigned_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    })

    return jsonify({
        'success': True,
        'message': 'Lead assigned'
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
