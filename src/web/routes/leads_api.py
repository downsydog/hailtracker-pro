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
    """Get database connection using CRM database"""
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
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
    where_clauses = ['l.deleted_at IS NULL']
    params = []

    # Only own leads for sales role
    user_role = g.current_user.get('role')
    if user_role == 'sales':
        where_clauses.append('l.assigned_to = ?')
        params.append(str(g.current_user['id']))

    if status:
        if status == 'active':
            where_clauses.append("l.status NOT IN ('CONVERTED', 'LOST')")
        else:
            where_clauses.append('l.status = ?')
            params.append(status.upper())

    if temperature:
        where_clauses.append('l.temperature = ?')
        params.append(temperature.upper())

    if source:
        where_clauses.append('l.source = ?')
        params.append(source)

    if assigned_to:
        where_clauses.append('l.assigned_to = ?')
        params.append(assigned_to)

    if search:
        where_clauses.append("""(
            l.first_name LIKE ? OR
            l.last_name LIKE ? OR
            l.email LIKE ? OR
            l.phone LIKE ? OR
            l.company_name LIKE ?
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
    count_result = db.execute(f"SELECT COUNT(*) as count FROM leads l WHERE {where_sql}", tuple(params))
    total = count_result[0]['count'] if count_result else 0

    # Get leads with coordinates from associated hail events
    query = f"""
        SELECT
            l.*,
            COALESCE(l.first_name || ' ' || l.last_name, l.company_name) as display_name,
            h.center_lat as latitude,
            h.center_lon as longitude,
            h.event_name as hail_event_name
        FROM leads l
        LEFT JOIN hail_events h ON h.id = l.hail_event_id
        WHERE {where_sql}
        ORDER BY l.{sort_by} {sort_dir}
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


# ============================================================================
# FLEET DISCOVERY INTEGRATION
# ============================================================================
# These endpoints connect Fleet Intelligence to the main CRM leads system

@leads_api_bp.route('/from-fleet-discovery', methods=['POST'])
@login_required
@require_permission('leads.create')
def create_lead_from_fleet_discovery():
    """
    Create a lead from Fleet Intelligence / Hail Swath discovery.

    This connects the Fleet Intelligence module to the main CRM.
    Businesses identified in hail swaths become HOT leads.

    POST body:
    {
        "business_id": 123,
        "company_name": "ABC Motors",
        "address": "123 Main St",
        "city": "Dallas",
        "state": "TX",
        "zip": "75001",
        "phone": "(214) 555-1234",
        "category": "car_dealership",
        "estimated_vehicles": 150,
        "tier": 1,
        "latitude": 32.7767,
        "longitude": -96.7970,
        "hail_affected": true,
        "hail_date": "2024-05-15",
        "hail_size": 1.75
    }
    """
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate required fields
    company_name = data.get('company_name') or data.get('name')
    if not company_name:
        return jsonify({'error': 'company_name required'}), 400

    # Check for duplicate (by name + city + state)
    existing = db.execute("""
        SELECT id, status FROM leads
        WHERE company_name = ? AND city = ? AND state = ? AND deleted_at IS NULL
    """, (company_name, data.get('city'), data.get('state')))

    if existing:
        return jsonify({
            'error': 'Lead already exists',
            'lead_id': existing[0]['id'],
            'status': existing[0]['status'],
            'duplicate': True
        }), 409

    # Determine temperature based on hail and tier
    hail_affected = data.get('hail_affected', False)
    hail_distance = data.get('hail_distance', 999)
    tier = data.get('tier', 3)

    if hail_affected and hail_distance <= 5:
        temperature = 'HOT'  # Inside swath or very close
    elif hail_affected:
        temperature = 'WARM'  # Near swath
    elif tier == 1:
        temperature = 'WARM'  # High value fleet
    else:
        temperature = 'COLD'

    # Build notes with context
    notes_parts = []
    notes_parts.append(f"Source: Fleet Discovery ({data.get('category', 'unknown')} - Tier {tier})")
    notes_parts.append(f"Estimated vehicles: {data.get('estimated_vehicles', 'unknown')}")
    if data.get('latitude') and data.get('longitude'):
        notes_parts.append(f"Coordinates: {data.get('latitude')}, {data.get('longitude')}")

    if hail_affected:
        notes_parts.append("")
        notes_parts.append("🌨️ HAIL AFFECTED:")
        notes_parts.append(f"  Storm date: {data.get('hail_date')}")
        notes_parts.append(f"  Hail size: {data.get('hail_size')}\"")
        if hail_distance == 0:
            notes_parts.append("  Location: INSIDE swath polygon")
        else:
            notes_parts.append(f"  Distance from swath: {hail_distance} miles")

    notes = '\n'.join(notes_parts)

    # Create lead
    lead_data = {
        'company_name': company_name,
        'first_name': '',
        'last_name': '',
        'phone': data.get('phone'),
        'email': data.get('contact_email'),
        'source': 'FLEET_DISCOVERY',
        'temperature': temperature,
        'status': 'NEW',
        'notes': notes,
        'damage_type': 'HAIL' if hail_affected else None,
        'assigned_to': str(g.current_user['id']),
        'assigned_at': datetime.now().isoformat(),
        'organization_id': g.organization_id,
        'created_at': datetime.now().isoformat()
    }

    lead_id = db.insert('leads', lead_data)

    return jsonify({
        'success': True,
        'lead_id': lead_id,
        'temperature': temperature,
        'message': f"Lead created: {company_name}"
    }), 201


@leads_api_bp.route('/from-fleet-discovery/bulk', methods=['POST'])
@login_required
@require_permission('leads.create')
def bulk_create_leads_from_fleet():
    """
    Bulk create leads from Fleet Intelligence.
    Used for "Add All Affected Businesses" button in hail swath view.

    POST body:
    {
        "businesses": [
            { ...business data... },
            { ...business data... }
        ],
        "hail_date": "2024-05-15",
        "hail_size": 1.75
    }
    """
    db = get_db()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    businesses = data.get('businesses', [])
    hail_date = data.get('hail_date')
    hail_size = data.get('hail_size')

    if not businesses:
        return jsonify({'error': 'No businesses provided'}), 400

    created = 0
    skipped = 0
    created_ids = []
    errors = []

    for biz in businesses:
        company_name = biz.get('company_name') or biz.get('name')
        if not company_name:
            errors.append('Skipped business with no name')
            continue

        # Check for duplicate
        existing = db.execute("""
            SELECT id FROM leads
            WHERE company_name = ? AND city = ? AND state = ? AND deleted_at IS NULL
        """, (company_name, biz.get('city'), biz.get('state')))

        if existing:
            skipped += 1
            continue

        try:
            # Determine temperature - all hail-affected are HOT
            hail_distance = biz.get('hail_distance', 0)
            if hail_distance <= 5:
                temperature = 'HOT'
            else:
                temperature = 'WARM'

            tier = biz.get('tier', 3)

            # Build notes
            notes = f"""Source: Fleet Discovery (Hail Swath Import)
Category: {biz.get('category', 'unknown')} - Tier {tier}
Estimated vehicles: {biz.get('estimated_vehicles', 'unknown')}

🌨️ HAIL AFFECTED:
  Storm date: {hail_date}
  Hail size: {hail_size}"
  Inside swath: YES"""

            lead_data = {
                'company_name': company_name,
                'first_name': '',
                'last_name': '',
                'phone': biz.get('phone'),
                'source': 'FLEET_DISCOVERY',
                'temperature': temperature,
                'status': 'NEW',
                'notes': notes,
                'damage_type': 'HAIL',
                'assigned_to': str(g.current_user['id']),
                'assigned_at': datetime.now().isoformat(),
                'organization_id': g.organization_id,
                'created_at': datetime.now().isoformat()
            }

            lead_id = db.insert('leads', lead_data)
            created += 1
            created_ids.append(lead_id)

        except Exception as e:
            errors.append(f"{company_name}: {str(e)}")

    return jsonify({
        'success': True,
        'created': created,
        'skipped': skipped,
        'created_ids': created_ids,
        'errors': errors[:10],  # Limit errors returned
        'message': f"Created {created} leads, skipped {skipped} duplicates"
    })


# ============================================================================
# FLEET LEAD CONVERSION REPORTING
# ============================================================================

@leads_api_bp.route('/reports/fleet')
@login_required
@require_any_permission('leads.view_all', 'reports.view')
def fleet_lead_reports():
    """
    Get comprehensive reports for fleet-sourced leads.

    Returns:
    - Sales funnel by status
    - Conversion rates
    - Hail vs non-hail performance
    - By category and city breakdown
    - Weekly trends
    - Top deals
    """
    db = get_db()

    # Date range filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    date_filter = ""
    date_params = []
    if start_date:
        date_filter += " AND l.created_at >= ?"
        date_params.append(start_date)
    if end_date:
        date_filter += " AND l.created_at <= ?"
        date_params.append(end_date + " 23:59:59")

    # 1. Sales Funnel by Status
    funnel = db.execute(f"""
        SELECT
            status,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM leads WHERE source = 'FLEET_DISCOVERY' AND deleted_at IS NULL {date_filter}), 1) as percentage
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY' AND deleted_at IS NULL {date_filter}
        GROUP BY status
        ORDER BY
            CASE status
                WHEN 'NEW' THEN 1
                WHEN 'CONTACTED' THEN 2
                WHEN 'QUALIFIED' THEN 3
                WHEN 'NEGOTIATING' THEN 4
                WHEN 'CONVERTED' THEN 5
                WHEN 'LOST' THEN 6
            END
    """, tuple(date_params + date_params))

    # 2. Conversion Rates
    conversion_stats = db.execute(f"""
        SELECT
            COUNT(*) as total_leads,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
            SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as lost,
            SUM(CASE WHEN status NOT IN ('CONVERTED', 'LOST') THEN 1 ELSE 0 END) as active,
            ROUND(SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as conversion_rate,
            ROUND(SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as loss_rate
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY' AND deleted_at IS NULL {date_filter}
    """, tuple(date_params))[0]

    # 3. Hail vs Non-Hail Performance
    hail_comparison = db.execute(f"""
        SELECT
            CASE WHEN damage_type = 'HAIL' THEN 'Hail Affected' ELSE 'Non-Hail' END as category,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
            SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as lost,
            ROUND(SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as conversion_rate,
            ROUND(AVG(follow_up_count), 1) as avg_follow_ups
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY' AND deleted_at IS NULL {date_filter}
        GROUP BY CASE WHEN damage_type = 'HAIL' THEN 'Hail Affected' ELSE 'Non-Hail' END
    """, tuple(date_params))

    # 4. By Temperature
    by_temperature = db.execute(f"""
        SELECT
            temperature,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
            ROUND(SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as conversion_rate
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY' AND deleted_at IS NULL {date_filter}
        GROUP BY temperature
        ORDER BY
            CASE temperature
                WHEN 'HOT' THEN 1
                WHEN 'WARM' THEN 2
                WHEN 'COLD' THEN 3
            END
    """, tuple(date_params))

    # 5. By City (Top 10)
    by_city = db.execute(f"""
        SELECT
            COALESCE(city, 'Unknown') as city,
            state,
            COUNT(*) as total_leads,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
            ROUND(SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as conversion_rate
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY' AND deleted_at IS NULL {date_filter}
        GROUP BY city, state
        ORDER BY total_leads DESC
        LIMIT 10
    """, tuple(date_params))

    # 6. Weekly Trends (last 12 weeks)
    weekly_trends = db.execute(f"""
        SELECT
            strftime('%Y-%W', created_at) as week,
            COUNT(*) as new_leads,
            SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
            SUM(CASE WHEN status = 'CONTACTED' OR status = 'QUALIFIED' OR status = 'NEGOTIATING' THEN 1 ELSE 0 END) as in_progress
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY'
            AND deleted_at IS NULL
            AND created_at >= date('now', '-12 weeks')
        GROUP BY strftime('%Y-%W', created_at)
        ORDER BY week DESC
        LIMIT 12
    """)

    # 7. Top Converted Deals (recent conversions)
    top_deals = db.execute(f"""
        SELECT
            l.id,
            l.company_name,
            l.city,
            l.state,
            l.temperature,
            l.created_at,
            l.updated_at as converted_at,
            l.notes
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY'
            AND status = 'CONVERTED'
            AND deleted_at IS NULL {date_filter}
        ORDER BY l.updated_at DESC
        LIMIT 10
    """, tuple(date_params))

    # 8. Lost Reasons Analysis
    lost_reasons = db.execute(f"""
        SELECT
            COALESCE(lost_reason, 'No reason provided') as reason,
            COUNT(*) as count
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY'
            AND status = 'LOST'
            AND deleted_at IS NULL {date_filter}
        GROUP BY lost_reason
        ORDER BY count DESC
        LIMIT 10
    """, tuple(date_params))

    # 9. Response Time Analysis (time to first contact)
    response_time = db.execute(f"""
        SELECT
            AVG(JULIANDAY(last_contact_date) - JULIANDAY(DATE(created_at))) as avg_days_to_contact,
            MIN(JULIANDAY(last_contact_date) - JULIANDAY(DATE(created_at))) as min_days,
            MAX(JULIANDAY(last_contact_date) - JULIANDAY(DATE(created_at))) as max_days
        FROM leads l
        WHERE source = 'FLEET_DISCOVERY'
            AND last_contact_date IS NOT NULL
            AND deleted_at IS NULL {date_filter}
    """, tuple(date_params))[0]

    return jsonify({
        'success': True,
        'reports': {
            'funnel': funnel,
            'conversion_stats': conversion_stats,
            'hail_comparison': hail_comparison,
            'by_temperature': by_temperature,
            'by_city': by_city,
            'weekly_trends': list(reversed(weekly_trends)),  # Chronological order
            'top_deals': top_deals,
            'lost_reasons': lost_reasons,
            'response_time': {
                'avg_days': round(response_time['avg_days_to_contact'] or 0, 1),
                'min_days': round(response_time['min_days'] or 0, 1),
                'max_days': round(response_time['max_days'] or 0, 1)
            }
        },
        'filters': {
            'start_date': start_date,
            'end_date': end_date
        }
    })
