"""
Customer API Endpoints
======================
Tenant-specific operations for PDR business users.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from app.api.middleware import login_required, roles_required, permission_required, check_permission, parse_identity
from app.services.storm_service import StormService
from app.services.lead_service import LeadService
from app.services.permissions_service import Permission
from app.services.blocker_helpers import normalize_eta, get_current_job_blocker, get_bulk_job_blockers
from datetime import datetime, timedelta

customer_bp = Blueprint('customer', __name__)


# ==============================================================================
# STORM ENDPOINTS
# ==============================================================================

@customer_bp.route('/storms', methods=['GET'])
@login_required
def list_storms():
    """
    Get recent storms.

    Query params:
        days: Number of days to look back (default 30)
        state: Filter by state
        min_hail_size: Minimum hail size in inches

    Returns:
        200: List of storms
    """
    days = request.args.get('days', 30, type=int)
    state = request.args.get('state')
    min_hail = request.args.get('min_hail_size', type=float)

    storms = StormService.get_recent_storms(
        days=days,
        state=state,
        min_hail_size=min_hail
    )

    return jsonify({'storms': storms})


@customer_bp.route('/storms/<int:storm_id>', methods=['GET'])
@login_required
def get_storm(storm_id):
    """
    Get storm details with swaths.

    Args:
        storm_id: Storm ID

    Returns:
        200: Storm details with swaths
        404: Storm not found
    """
    storm = StormService.get_storm_detail(storm_id)

    if not storm:
        return jsonify({'error': 'Storm not found'}), 404

    return jsonify(storm)


@customer_bp.route('/storms/<int:storm_id>/businesses', methods=['GET'])
@login_required
def get_storm_businesses(storm_id):
    """
    Get businesses for a storm.

    Query params:
        category: Filter by business category
        min_vehicles: Minimum estimated vehicles
        limit: Max results (default 500)

    Returns:
        200: List of businesses
    """
    category = request.args.get('category')
    min_vehicles = request.args.get('min_vehicles', type=int)
    limit = request.args.get('limit', 500, type=int)

    businesses = StormService.get_storm_businesses(
        storm_id,
        category=category,
        min_vehicles=min_vehicles,
        limit=limit
    )

    return jsonify({'businesses': businesses, 'count': len(businesses)})


@customer_bp.route('/storms/<int:storm_id>/categories', methods=['GET'])
@login_required
def get_storm_categories(storm_id):
    """
    Get business categories for a storm.

    Returns:
        200: List of categories with counts
    """
    categories = StormService.get_business_categories(storm_id)

    return jsonify({'categories': categories})


@customer_bp.route('/storms/search', methods=['GET'])
@login_required
def search_storms():
    """
    Search storms by city, state, or ID.

    Query params:
        q: Search query (min 2 chars)

    Returns:
        200: List of matching storms
        400: Query too short
    """
    query = request.args.get('q', '')

    if len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400

    results = StormService.search_storms(query)

    return jsonify({'storms': results})


@customer_bp.route('/storms/by-date/<date_str>', methods=['GET'])
@login_required
def get_storms_by_date(date_str):
    """
    Get storms for a specific date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        200: List of storms for that date
        400: Invalid date format
    """
    from datetime import datetime

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    storms = StormService.get_storms_by_date(date)

    return jsonify({'storms': storms, 'date': date_str})


# ==============================================================================
# LEAD ENDPOINTS
# ==============================================================================

@customer_bp.route('/leads', methods=['GET'])
@login_required
def list_leads():
    """
    Get leads for current tenant.
    Techs/salesmen only see their assigned leads.

    Query params:
        status: Filter by status
        assigned_to: Filter by assignee ID
        storm_id: Filter by storm ID

    Returns:
        200: List of leads
    """
    identity = parse_identity(get_jwt_identity())

    status = request.args.get('status')
    assigned_to = request.args.get('assigned_to', type=int)
    storm_id = request.args.get('storm_id', type=int)

    leads = LeadService.get_leads(
        tenant_id=identity['tenant_id'],
        user_id=identity['user_id'],
        user_role=identity['role'],
        status=status,
        assigned_to=assigned_to,
        storm_id=storm_id
    )

    return jsonify({'leads': leads, 'count': len(leads)})


@customer_bp.route('/leads', methods=['POST'])
@login_required
def create_lead():
    """
    Create a new lead from a business.

    Request Body:
    {
        "business_id": 123,
        "storm_id": 456,
        "notes": "Optional notes",
        "priority": "medium"
    }

    Returns:
        201: Lead created
        400: Validation error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    if not data.get('business_id') or not data.get('storm_id'):
        return jsonify({'error': 'business_id and storm_id required'}), 400

    lead, error = LeadService.create_lead(
        tenant_id=identity['tenant_id'],
        user_id=identity['user_id'],
        business_id=data['business_id'],
        storm_id=data['storm_id'],
        notes=data.get('notes'),
        priority=data.get('priority', 'medium')
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify({'lead': lead.to_dict()}), 201


@customer_bp.route('/leads/bulk', methods=['POST'])
@login_required
def create_leads_bulk():
    """
    Create multiple leads at once.

    Request Body:
    {
        "business_ids": [1, 2, 3],
        "storm_id": 456
    }

    Returns:
        201: Result with created and skipped counts
        400: Validation error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    if not data.get('business_ids') or not data.get('storm_id'):
        return jsonify({'error': 'business_ids and storm_id required'}), 400

    result = LeadService.bulk_create_leads(
        tenant_id=identity['tenant_id'],
        user_id=identity['user_id'],
        business_ids=data['business_ids'],
        storm_id=data['storm_id']
    )

    return jsonify(result), 201


@customer_bp.route('/leads/<int:lead_id>', methods=['GET'])
@login_required
def get_lead(lead_id):
    """
    Get lead details with contacts and calls.

    Returns:
        200: Lead details
        404: Lead not found or not authorized
    """
    identity = parse_identity(get_jwt_identity())

    lead = LeadService.get_lead(
        lead_id=lead_id,
        user_id=identity['user_id'],
        user_role=identity['role']
    )

    if not lead:
        return jsonify({'error': 'Lead not found or not authorized'}), 404

    return jsonify(lead)


@customer_bp.route('/leads/<int:lead_id>', methods=['PATCH'])
@login_required
def update_lead(lead_id):
    """
    Update a lead.

    Request Body:
    {
        "status": "contacted",
        "priority": "high",
        "notes": "Updated notes",
        "assigned_to": 789  // Owner/manager only
    }

    Returns:
        200: Updated lead
        400: Validation error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    lead, error = LeadService.update_lead(
        lead_id=lead_id,
        user_id=identity['user_id'],
        user_role=identity['role'],
        updates=data
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify({'lead': lead.to_dict()})


@customer_bp.route('/leads/<int:lead_id>/contacts', methods=['POST'])
@login_required
def add_lead_contact(lead_id):
    """
    Add a contact to a lead.

    Request Body:
    {
        "name": "John Smith",
        "phone": "555-1234",
        "email": "john@example.com",
        "title": "Fleet Manager",
        "is_primary": true
    }

    Returns:
        201: Contact created
        400: Validation error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    if not data.get('name'):
        return jsonify({'error': 'name required'}), 400

    contact, error = LeadService.add_contact(
        lead_id=lead_id,
        user_id=identity['user_id'],
        name=data['name'],
        phone=data.get('phone'),
        email=data.get('email'),
        title=data.get('title'),
        is_primary=data.get('is_primary', False)
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify({'contact': contact.to_dict()}), 201


@customer_bp.route('/leads/<int:lead_id>/calls', methods=['POST'])
@login_required
def log_lead_call(lead_id):
    """
    Log a call for a lead.

    Request Body:
    {
        "call_type": "outbound",
        "outcome": "connected",
        "notes": "Spoke with owner about fleet",
        "duration_seconds": 180,
        "contact_id": 123
    }

    Returns:
        201: Call logged
        400: Validation error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    if not data.get('call_type') or not data.get('outcome'):
        return jsonify({'error': 'call_type and outcome required'}), 400

    call, error = LeadService.log_call(
        lead_id=lead_id,
        user_id=identity['user_id'],
        call_type=data['call_type'],
        outcome=data['outcome'],
        notes=data.get('notes'),
        duration_seconds=data.get('duration_seconds'),
        contact_id=data.get('contact_id')
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify({'call': call.to_dict()}), 201


@customer_bp.route('/leads/stats', methods=['GET'])
@login_required
def get_lead_stats():
    """
    Get lead statistics for dashboard.

    Returns:
        200: Lead statistics
    """
    identity = parse_identity(get_jwt_identity())

    stats = LeadService.get_lead_stats(
        tenant_id=identity['tenant_id'],
        user_id=identity['user_id'],
        user_role=identity['role']
    )

    return jsonify(stats)


# ==============================================================================
# DASHBOARD
# ==============================================================================

@customer_bp.route('/dashboard')
@login_required
def customer_dashboard():
    """
    Customer dashboard with stats.

    Returns:
        200: Dashboard statistics
    """
    identity = parse_identity(get_jwt_identity())

    from app.models.master.tenant import Tenant
    from app.models.master.user import User
    from app.services.usage_service import UsageService
    from datetime import datetime, timedelta

    tenant = Tenant.query.get(identity['tenant_id'])

    # Get lead stats
    lead_stats = LeadService.get_lead_stats(
        tenant_id=identity['tenant_id'],
        user_id=identity['user_id'],
        user_role=identity['role']
    )

    # Get recent storms count
    recent_storms = StormService.get_recent_storms(days=7)

    # Get team member count
    team_count = User.query.filter_by(tenant_id=identity['tenant_id'], is_active=True).count()

    # Get API usage
    usage = UsageService.get_current_usage(identity['tenant_id'])

    # Get leads today and this week
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    leads_today = lead_stats.get('today', 0)
    leads_this_week = lead_stats.get('this_week', 0)

    return jsonify({
        'user': {
            'id': identity['user_id'],
            'role': identity['role'],
            'email': identity['email']
        },
        'company': tenant.company_name if tenant else 'Unknown',
        'leads_today': leads_today,
        'leads_this_week': leads_this_week,
        'leads_total': lead_stats['total'],
        'active_storms': len(recent_storms),
        'team_members': team_count,
        'api_usage': {
            'used': usage.get('used', 0),
            'limit': usage.get('limit', 1000),
            'percentage': usage.get('percentage', 0)
        }
    })


# ==============================================================================
# TEAM ENDPOINTS
# ==============================================================================

@customer_bp.route('/team', methods=['GET'])
@login_required
def list_team():
    """
    Get team members for current tenant.

    Returns:
        200: List of team members
    """
    identity = parse_identity(get_jwt_identity())

    from app.models.master.user import User

    members = User.query.filter_by(tenant_id=identity['tenant_id']).all()

    return jsonify({
        'members': [m.to_dict() for m in members]
    })


@customer_bp.route('/team', methods=['POST'])
@login_required
@roles_required(['owner', 'manager'])
def add_team_member():
    """
    Add a new team member.

    Request Body:
    {
        "email": "jane@company.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "role": "salesman",
        "password": "temppass123"
    }

    Returns:
        201: Team member added
        400: Validation error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    required = ['email', 'first_name', 'last_name', 'role', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    from app.services.auth_service import AuthService

    name = f"{data['first_name']} {data['last_name']}"

    user, error = AuthService.add_team_member(
        tenant_id=identity['tenant_id'],
        adder_role=identity['role'],
        name=name,
        email=data['email'],
        password=data['password'],
        role=data['role'],
        phone=data.get('phone')
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify({
        'message': 'Team member added',
        'member': user.to_dict()
    }), 201


@customer_bp.route('/team/<int:user_id>', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager'])
def update_team_member(user_id):
    """
    Update a team member.

    Request Body:
    {
        "is_active": false,
        "role": "tech"
    }

    Returns:
        200: Team member updated
        400: Error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    from app.models.master.user import User
    from app.extensions import db

    user = User.query.filter_by(id=user_id, tenant_id=identity['tenant_id']).first()

    if not user:
        return jsonify({'error': 'Team member not found'}), 404

    # Cannot deactivate yourself
    if user_id == identity['user_id'] and data.get('is_active') is False:
        return jsonify({'error': 'Cannot deactivate yourself'}), 400

    # Cannot change owner's role
    if user.role == 'owner' and data.get('role') and data['role'] != 'owner':
        return jsonify({'error': 'Cannot change owner role'}), 400

    if 'is_active' in data:
        user.is_active = data['is_active']
    if 'role' in data and data['role'] in ['manager', 'desk', 'tech', 'salesman']:
        user.role = data['role']

    db.session.commit()

    return jsonify({
        'message': 'Team member updated',
        'member': user.to_dict()
    })


# ==============================================================================
# SETTINGS ENDPOINTS
# ==============================================================================

@customer_bp.route('/settings/company', methods=['PATCH'])
@login_required
@roles_required(['owner'])
def update_company_settings():
    """
    Update company settings.
    Owner only.

    Request Body:
    {
        "name": "New Company Name"
    }

    Returns:
        200: Settings updated
        400: Error
    """
    identity = parse_identity(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    from app.models.master.tenant import Tenant
    from app.extensions import db

    tenant = Tenant.query.get(identity['tenant_id'])

    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    if 'name' in data:
        tenant.company_name = data['name']

    db.session.commit()

    return jsonify({
        'message': 'Settings updated',
        'tenant': tenant.to_dict()
    })


# ==============================================================================
# PDR ESTIMATE CRUD ENDPOINTS
# ==============================================================================

@customer_bp.route('/pdr-estimates', methods=['GET'])
@login_required
def list_estimates():
    """
    List PDR estimates for the tenant.

    Query params:
        status: Filter by status (draft, in_progress, approved, completed)
        customer_id: Filter by customer ID
        lead_id: Filter by lead ID
        search: Search by estimate number, customer name, or vehicle
        limit: Max results (default 50)
        offset: Pagination offset (default 0)

    Returns:
        200: { estimates: [...], total: N }
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    status = request.args.get('status')
    customer_id = request.args.get('customer_id', type=int)
    lead_id = request.args.get('lead_id', type=int)
    search = request.args.get('search', '').strip()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = PDREstimate.query.filter_by(tenant_id=tenant_id)

    if status:
        query = query.filter_by(status=status)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)
    if lead_id:
        query = query.filter_by(lead_id=lead_id)
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                PDREstimate.estimate_number.ilike(search_pattern),
                PDREstimate.customer_name.ilike(search_pattern),
                PDREstimate.vehicle_make.ilike(search_pattern),
                PDREstimate.vehicle_model.ilike(search_pattern)
            )
        )

    total = query.count()
    estimates = query.order_by(PDREstimate.updated_at.desc()).offset(offset).limit(limit).all()

    return jsonify({
        'estimates': [e.to_dict() for e in estimates],
        'total': total
    })


@customer_bp.route('/pdr-estimates/<int:estimate_id>', methods=['GET'])
@login_required
def get_estimate(estimate_id):
    """
    Get a single PDR estimate by ID.

    Returns:
        200: Estimate object with panels
        404: Estimate not found
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.pdr_estimate_panel import PDREstimatePanel

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    result = estimate.to_dict()

    # Include panels
    panels = PDREstimatePanel.query.filter_by(estimate_id=estimate_id).all()
    result['panels'] = [p.to_dict() for p in panels]

    return jsonify(result)


@customer_bp.route('/pdr-estimates', methods=['POST'])
@login_required
def create_estimate():
    """
    Create a new PDR estimate.

    Request Body:
        vehicle_year: int
        vehicle_make: str
        vehicle_model: str
        vin: str (optional)
        customer_id: int (optional)
        lead_id: int (optional)
        customer_name: str (optional)
        matrix_profile_id: int (optional)

    Returns:
        201: { success: true, estimate: {...} }
        400: Validation error
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.extensions import db
    import uuid

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')
    data = request.get_json() or {}

    # Generate estimate number
    estimate_number = f"EST-{uuid.uuid4().hex[:8].upper()}"

    estimate = PDREstimate(
        tenant_id=tenant_id,
        estimate_number=estimate_number,
        vehicle_year=data.get('vehicle_year', datetime.now().year),
        vehicle_make=data.get('vehicle_make', 'Unknown'),
        vehicle_model=data.get('vehicle_model', 'Unknown'),
        vehicle_type=data.get('vehicle_type', 'car'),
        vin=data.get('vin'),
        customer_id=data.get('customer_id') or data.get('contact_id'),
        lead_id=data.get('lead_id'),
        customer_name=data.get('customer_name'),
        status='draft',
        created_by=user_id
    )

    # Set optional fields
    if data.get('matrix_profile_id'):
        estimate.matrix_profile_id = data['matrix_profile_id']
    if data.get('customer_phone'):
        estimate.customer_phone = data['customer_phone']

    db.session.add(estimate)
    db.session.commit()

    return jsonify({
        'success': True,
        'estimate': estimate.to_dict()
    }), 201


@customer_bp.route('/pdr-estimates/<int:estimate_id>', methods=['PUT', 'PATCH'])
@login_required
def update_estimate(estimate_id):
    """
    Update a PDR estimate.

    Request Body: Any estimate fields to update

    Returns:
        200: { success: true, estimate: {...} }
        404: Estimate not found
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    data = request.get_json() or {}

    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    # Allowed fields to update
    allowed_fields = [
        'vehicle_year', 'vehicle_make', 'vehicle_model', 'vehicle_type', 'vin',
        'license_plate', 'color', 'mileage', 'customer_id', 'lead_id',
        'customer_name', 'customer_phone', 'customer_email',
        'insurance_company', 'claim_number', 'deductible', 'adjuster_name',
        'adjuster_email', 'adjuster_phone', 'status', 'notes', 'internal_notes',
        'matrix_profile_id', 'vehicle_id', 'contact_id'
    ]

    for field in allowed_fields:
        if field in data:
            # Handle contact_id -> customer_id mapping
            if field == 'contact_id':
                setattr(estimate, 'customer_id', data[field])
            elif field == 'vehicle_id':
                # vehicle_id might be used for linking
                pass  # Skip if no direct column
            else:
                setattr(estimate, field, data[field])

    estimate.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'estimate': estimate.to_dict()
    })


@customer_bp.route('/pdr-estimates/<int:estimate_id>', methods=['DELETE'])
@login_required
@roles_required(['owner', 'manager'])
def delete_estimate(estimate_id):
    """
    Delete a PDR estimate.

    Only owner/manager can delete.
    Cannot delete if jobs or invoices are linked.

    Returns:
        200: { success: true }
        404: Estimate not found
        400: Cannot delete (has linked records)
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.job import Job
    from app.models.tenant.invoice import Invoice
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    # Check for linked jobs
    linked_job = Job.query.filter_by(estimate_id=estimate_id).first()
    if linked_job:
        return jsonify({'error': 'Cannot delete estimate with linked job'}), 400

    # Check for linked invoices
    linked_invoice = Invoice.query.filter_by(estimate_id=estimate_id).first()
    if linked_invoice:
        return jsonify({'error': 'Cannot delete estimate with linked invoices'}), 400

    db.session.delete(estimate)
    db.session.commit()

    return jsonify({'success': True})


# ==============================================================================
# PDF EXPORT ENDPOINTS
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/pdf', methods=['GET'])
@login_required
def get_estimate_pdf(estimate_id):
    """
    Generate and download PDF for a PDR estimate.

    Args:
        estimate_id: Estimate ID

    Returns:
        200: PDF file download
        404: Estimate not found
        500: PDF generation error
    """
    from flask import make_response
    from app.services.pdf_generator import generate_estimate_pdf
    from app.services.ri_justification_service import compute_estimate_ri_summary
    from app.models.master.tenant import Tenant
    from app.models.tenant import PDREstimate

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    # Try to get tenant info for shop name
    tenant = Tenant.query.get(tenant_id)
    shop_info = None
    if tenant:
        shop_info = {
            'company_name': tenant.company_name
        }

    # Fetch estimate from database
    estimate = PDREstimate.query.filter_by(
        id=estimate_id,
        tenant_id=tenant_id
    ).first()

    if estimate:
        estimate_data = estimate.to_dict()

        # Include panels data for PDF
        from app.models.tenant import PDREstimatePanel
        panels = PDREstimatePanel.query.filter_by(
            estimate_id=estimate_id,
            tenant_id=tenant_id
        ).all()
        estimate_data['panels'] = [p.to_dict() for p in panels]

        # Get R&I operations data (Phase 6D) with labor rate (Stage 6E)
        try:
            ri_summary = compute_estimate_ri_summary(estimate_id, tenant_id)
            if ri_summary and ri_summary.get('operations'):
                estimate_data['ri_operations'] = ri_summary['operations']
                estimate_data['ri_labor_rate'] = ri_summary.get('ri_labor_rate', 85)
                estimate_data['ri_labor_rate_source'] = ri_summary.get('ri_labor_rate_source')
                estimate_data['ri_labor_rate_rule_name'] = ri_summary.get('ri_labor_rate_rule_name')
                estimate_data['ri_total'] = ri_summary.get('total_ri_cost', ri_summary['total_ri_time_hours'] * estimate_data['ri_labor_rate'])
        except Exception as e:
            # Log but don't fail - R&I is optional
            import traceback
            traceback.print_exc()
    else:
        # Fallback for development
        estimate_data = {
            'id': estimate_id,
            'estimate_number': f'EST-{estimate_id:05d}',
            'vehicle_year': 2024,
            'vehicle_make': 'Sample',
            'vehicle_model': 'Vehicle',
            'customer_name': 'Sample Customer',
            'panels': [],
            'labor_total': 0,
            'ri_total': 0,
            'total_price': 0
        }

    try:
        pdf_buffer = generate_estimate_pdf(estimate_data, shop_info)

        # Create filename
        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        vehicle = f"{estimate_data.get('vehicle_year', '')} {estimate_data.get('vehicle_make', '')} {estimate_data.get('vehicle_model', '')}".strip()
        vehicle_slug = vehicle.replace(' ', '-')[:30] if vehicle else 'vehicle'
        filename = f"Estimate-{estimate_number}-{vehicle_slug}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/pdf/preview', methods=['POST'])
@login_required
def preview_estimate_pdf(estimate_id):
    """
    Generate PDF preview with estimate data from request body.

    This endpoint accepts estimate data directly and returns a PDF.
    Useful for previewing estimates before they're saved.

    Request Body:
    {
        "estimate_number": "EST-00001",
        "vehicle_year": 2024,
        "vehicle_make": "Ford",
        "vehicle_model": "F-150",
        "vin": "...",
        "customer_name": "John Doe",
        "panels": [...],
        "labor_total": 1500.00,
        "ri_total": 200.00,
        "total_price": 1700.00
    }

    Returns:
        200: PDF file download
        400: Invalid request
        500: PDF generation error
    """
    from flask import make_response
    from app.services.pdf_generator import generate_estimate_pdf
    from app.models.master.tenant import Tenant

    identity = parse_identity(get_jwt_identity())

    estimate_data = request.get_json()

    if not estimate_data:
        return jsonify({'error': 'Estimate data required'}), 400

    # Get tenant info for shop name
    tenant = Tenant.query.get(identity['tenant_id'])
    shop_info = None
    if tenant:
        shop_info = {
            'company_name': tenant.company_name
        }

    try:
        pdf_buffer = generate_estimate_pdf(estimate_data, shop_info)

        # Create filename
        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        vehicle = f"{estimate_data.get('vehicle_year', '')} {estimate_data.get('vehicle_make', '')} {estimate_data.get('vehicle_model', '')}".strip()
        vehicle_slug = vehicle.replace(' ', '-')[:30] if vehicle else 'vehicle'
        filename = f"Estimate-{estimate_number}-{vehicle_slug}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


# ==============================================================================
# PHOTO SHEET PDF ENDPOINTS
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/photosheet.pdf', methods=['GET'])
@login_required
def get_estimate_photosheet(estimate_id):
    """
    Generate and download photo sheet PDF for a PDR estimate.

    Args:
        estimate_id: Estimate ID

    Returns:
        200: PDF file download
        404: Estimate not found
        500: PDF generation error
    """
    from flask import make_response
    from app.services.photo_sheet_generator import generate_photo_sheet
    from app.models.master.tenant import Tenant
    from app.models.tenant.estimate_photo import EstimatePhoto

    identity = parse_identity(get_jwt_identity())

    # Get tenant info for shop name
    tenant = Tenant.query.get(identity['tenant_id'])
    shop_info = None
    if tenant:
        shop_info = {
            'company_name': tenant.company_name
        }

    # In production, fetch estimate from database
    # For now, use request body or placeholder
    estimate_data = request.get_json(silent=True) or {
        'id': estimate_id,
        'estimate_number': f'EST-{estimate_id:05d}',
        'vehicle_year': 2024,
        'vehicle_make': 'Sample',
        'vehicle_model': 'Vehicle',
        'customer_name': 'Sample Customer'
    }

    # Fetch photos from database
    try:
        photos = EstimatePhoto.query.filter_by(estimate_id=estimate_id).order_by(
            EstimatePhoto.panel_name,
            EstimatePhoto.created_at
        ).all()
        photos_data = [p.to_dict() for p in photos]
    except Exception:
        # If table doesn't exist yet, use empty list
        photos_data = []

    try:
        pdf_buffer = generate_photo_sheet(estimate_data, photos_data, shop_info)

        # Create filename
        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        filename = f"PhotoSheet-{estimate_number}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Photo sheet generation failed: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/photosheet/preview', methods=['POST'])
@login_required
def preview_estimate_photosheet(estimate_id):
    """
    Generate photo sheet PDF with data from request body.

    Request Body:
    {
        "estimate": {
            "estimate_number": "EST-00001",
            "vehicle_year": 2024,
            ...
        },
        "photos": [
            {
                "id": 1,
                "file_path": "/path/to/photo.jpg",
                "panel_name": "hood",
                "caption": "Front damage",
                "created_at": "2024-01-01T12:00:00Z",
                "is_supplement_evidence": false
            }
        ]
    }

    Returns:
        200: PDF file download
        400: Invalid request
        500: PDF generation error
    """
    from flask import make_response
    from app.services.photo_sheet_generator import generate_photo_sheet
    from app.models.master.tenant import Tenant

    identity = parse_identity(get_jwt_identity())

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    estimate_data = data.get('estimate', {
        'id': estimate_id,
        'estimate_number': f'EST-{estimate_id}'
    })
    photos_data = data.get('photos', [])

    # Get tenant info for shop name
    tenant = Tenant.query.get(identity['tenant_id'])
    shop_info = None
    if tenant:
        shop_info = {
            'company_name': tenant.company_name
        }

    try:
        pdf_buffer = generate_photo_sheet(estimate_data, photos_data, shop_info)

        # Create filename
        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        filename = f"PhotoSheet-{estimate_number}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Photo sheet generation failed: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/photos', methods=['GET'])
@login_required
def get_estimate_photos(estimate_id):
    """
    Get all photos for an estimate.

    Returns:
        200: List of photos
    """
    from app.models.tenant.estimate_photo import EstimatePhoto

    try:
        photos = EstimatePhoto.query.filter_by(estimate_id=estimate_id).order_by(
            EstimatePhoto.panel_name,
            EstimatePhoto.created_at
        ).all()

        return jsonify({
            'photos': [p.to_dict() for p in photos],
            'count': len(photos)
        })
    except Exception:
        # If table doesn't exist yet
        return jsonify({
            'photos': [],
            'count': 0
        })


@customer_bp.route('/pdr-estimates/<int:estimate_id>/photos', methods=['POST'])
@login_required
def add_estimate_photo(estimate_id):
    """
    Add a photo to an estimate.

    Request can be JSON or multipart form data.

    Returns:
        201: Photo added
        400: Validation error
    """
    from app.models.tenant.estimate_photo import EstimatePhoto
    from app.extensions import db

    try:
        # Handle JSON request
        if request.is_json:
            data = request.get_json()
            photo = EstimatePhoto(
                estimate_id=estimate_id,
                file_path=data.get('file_path', ''),
                file_name=data.get('file_name'),
                panel_name=data.get('panel_name'),
                photo_type=data.get('photo_type', 'damage'),
                caption=data.get('caption'),
                notes=data.get('notes'),
                is_supplement_evidence=data.get('is_supplement_evidence', False)
            )
        else:
            # Handle form data (file upload)
            # For now, just store the path - actual file handling would be implemented
            photo = EstimatePhoto(
                estimate_id=estimate_id,
                file_path=request.form.get('file_path', ''),
                file_name=request.form.get('file_name'),
                panel_name=request.form.get('panel_name'),
                photo_type=request.form.get('photo_type', 'damage'),
                caption=request.form.get('caption'),
                is_supplement_evidence=request.form.get('is_supplement_evidence', 'false').lower() == 'true'
            )

        db.session.add(photo)
        db.session.commit()

        return jsonify({
            'photo': photo.to_dict(),
            'message': 'Photo added successfully'
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to add photo: {str(e)}'}), 400


# ==============================================================================
# ESTIMATE EMAIL ENDPOINTS
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/send', methods=['POST'])
@login_required
@permission_required(Permission.ESTIMATE_SEND_EMAIL)
def send_estimate_package(estimate_id):
    """
    Send estimate package (PDF + Photo Sheet) to adjuster via email.

    Request body:
    {
        "to": "adjuster@insurance.com",
        "cc": ["optional@shop.com"],  // optional
        "subject": "Estimate #...",    // optional, auto-generated if not provided
        "message": "Hello..."          // optional, auto-generated if not provided
    }

    Returns:
        200: { status: "sent", message_id: "..." }
        400: { status: "failed", error: "..." }
    """
    from app.services.email_service import get_email_service

    identity = parse_identity(get_jwt_identity())
    data = request.get_json() or {}

    # Validate required fields
    to = data.get('to')
    if not to:
        return jsonify({'status': 'failed', 'error': 'Recipient email (to) is required'}), 400

    # Get optional fields
    cc = data.get('cc', [])
    if isinstance(cc, str):
        cc = [cc] if cc else []

    subject = data.get('subject')
    message = data.get('message')

    # Get current user ID for activity logging
    user_id = identity.get('user_id') if identity else None
    tenant_id = identity.get('tenant_id') if identity else None

    # Send email
    email_service = get_email_service()
    result = email_service.send_estimate_package(
        estimate_id=estimate_id,
        to=to,
        cc=cc,
        subject=subject,
        message=message,
        user_id=user_id,
        tenant_id=tenant_id
    )

    status_code = 200 if result.success else 400
    return jsonify(result.to_dict()), status_code


@customer_bp.route('/pdr-estimates/<int:estimate_id>/activities', methods=['GET'])
@login_required
def get_estimate_activities(estimate_id):
    """
    Get activity log for an estimate.

    Query params:
        limit: Max number of activities to return (default 20)
        type: Filter by activity type (optional)

    Returns:
        200: { activities: [...], count: N }
    """
    from app.models.tenant import EstimateActivity

    # Get query params
    limit = request.args.get('limit', 20, type=int)
    activity_type = request.args.get('type')

    try:
        # Build query
        query = EstimateActivity.query.filter_by(estimate_id=estimate_id)

        if activity_type:
            query = query.filter_by(activity_type=activity_type)

        # Order by most recent first
        activities = query.order_by(EstimateActivity.created_at.desc()).limit(limit).all()

        return jsonify({
            'activities': [a.to_dict() for a in activities],
            'count': len(activities)
        })
    except Exception:
        # If table doesn't exist yet
        return jsonify({
            'activities': [],
            'count': 0
        })


# ==============================================================================
# ESTIMATE VERSIONS (BASELINE SNAPSHOTS)
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/versions', methods=['GET'])
@login_required
def get_estimate_versions(estimate_id):
    """
    Get all versions (baseline snapshots) for an estimate.

    Returns:
        200: { versions: [...], count: N }
    """
    from app.models.tenant import EstimateVersion

    try:
        versions = EstimateVersion.query.filter_by(estimate_id=estimate_id).order_by(
            EstimateVersion.version_number.desc()
        ).all()

        return jsonify({
            'versions': [v.to_dict() for v in versions],
            'count': len(versions)
        })
    except Exception:
        return jsonify({'versions': [], 'count': 0})


@customer_bp.route('/pdr-estimates/<int:estimate_id>/versions', methods=['POST'])
@login_required
def create_estimate_version(estimate_id):
    """
    Create a baseline version snapshot of the current estimate state.

    Request body:
    {
        "snapshot": { ... },  // Current estimate state
        "description": "Pre-supplement #1"  // Optional
    }

    Returns:
        201: { version: {...} }
    """
    from app.models.tenant import EstimateVersion, EstimateActivity

    identity = parse_identity(get_jwt_identity())
    data = request.get_json() or {}

    snapshot = data.get('snapshot', {})
    description = data.get('description')

    if not snapshot:
        return jsonify({'error': 'Snapshot data is required'}), 400

    user_id = identity.get('user_id') if identity else None

    try:
        version = EstimateVersion.create_snapshot(
            estimate_id=estimate_id,
            snapshot_data=snapshot,
            user_id=user_id,
            description=description
        )

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='version_created',
            user_id=user_id,
            activity_data={'version_id': version.id, 'version_number': version.version_number}
        )

        return jsonify({'version': version.to_dict()}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ==============================================================================
# SUPPLEMENTS
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/supplements', methods=['GET'])
@login_required
def get_estimate_supplements(estimate_id):
    """
    Get all supplements for an estimate.

    Returns:
        200: { supplements: [...], count: N }
    """
    from app.models.tenant import EstimateSupplement

    try:
        supplements = EstimateSupplement.query.filter_by(estimate_id=estimate_id).order_by(
            EstimateSupplement.supplement_number.desc()
        ).all()

        return jsonify({
            'supplements': [s.to_dict() for s in supplements],
            'count': len(supplements)
        })
    except Exception:
        return jsonify({'supplements': [], 'count': 0})


@customer_bp.route('/pdr-estimates/<int:estimate_id>/supplements', methods=['POST'])
@login_required
@permission_required(Permission.SUPPLEMENT_CREATE)
def create_supplement(estimate_id):
    """
    Create a new supplement for an estimate.

    Request body:
    {
        "baseline_version_id": 1,
        "current_state": { ... },  // Current estimate data
        "discovery_type": "hidden_damage",
        "summary": "Additional damage found...",
        "photo_ids": [1, 2, 3]  // Optional
    }

    Returns:
        201: { supplement: {...}, delta: {...}, narrative: "..." }
    """
    from app.models.tenant import (
        EstimateVersion, EstimateSupplement, SupplementPhotoLink,
        EstimateActivity, DISCOVERY_TYPES
    )
    from app.services.supplement_diff import compute_supplement_diff, generate_supplement_narrative

    identity = parse_identity(get_jwt_identity())
    data = request.get_json() or {}

    baseline_version_id = data.get('baseline_version_id')
    current_state = data.get('current_state', {})
    discovery_type = data.get('discovery_type', 'hidden_damage')
    summary = data.get('summary', '')
    photo_ids = data.get('photo_ids', [])

    if not baseline_version_id:
        return jsonify({'error': 'baseline_version_id is required'}), 400

    if discovery_type not in DISCOVERY_TYPES:
        discovery_type = 'other'

    user_id = identity.get('user_id') if identity else None

    try:
        # Get baseline version
        baseline = EstimateVersion.query.get(baseline_version_id)
        if not baseline or baseline.estimate_id != estimate_id:
            return jsonify({'error': 'Invalid baseline version'}), 400

        # Compute diff
        delta = compute_supplement_diff(baseline.snapshot_json, current_state)

        # Generate narrative
        narrative = generate_supplement_narrative(delta, discovery_type, current_state)

        # Calculate totals
        baseline_total = baseline.snapshot_json.get('total_price') or baseline.snapshot_json.get('grand_total', 0)
        current_total = current_state.get('total_price') or current_state.get('grand_total', 0)

        # Get next supplement number
        max_supp = db.session.query(db.func.max(EstimateSupplement.supplement_number)).filter_by(
            estimate_id=estimate_id
        ).scalar() or 0

        # Create supplement
        supplement = EstimateSupplement(
            estimate_id=estimate_id,
            baseline_version_id=baseline_version_id,
            supplement_number=max_supp + 1,
            discovery_type=discovery_type,
            summary=summary,
            narrative=narrative,
            delta_json=delta,
            original_total=baseline_total,
            revised_total=current_total,
            delta_amount=float(current_total or 0) - float(baseline_total or 0),
            status='draft',
            created_by=user_id
        )
        db.session.add(supplement)
        db.session.flush()  # Get ID

        # Link photos
        for photo_id in photo_ids:
            link = SupplementPhotoLink(
                supplement_id=supplement.id,
                photo_id=photo_id
            )
            db.session.add(link)

        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='supplement_created',
            user_id=user_id,
            activity_data={
                'supplement_id': supplement.id,
                'supplement_number': supplement.supplement_number,
                'delta_amount': float(supplement.delta_amount or 0)
            }
        )

        return jsonify({
            'supplement': supplement.to_dict(),
            'delta': delta,
            'narrative': narrative
        }), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400


@customer_bp.route('/pdr-supplements/<int:supplement_id>', methods=['GET'])
@login_required
def get_supplement(supplement_id):
    """
    Get a single supplement by ID.

    Returns:
        200: { supplement: {...} }
        404: Not found
    """
    from app.models.tenant import EstimateSupplement

    supplement = EstimateSupplement.query.get(supplement_id)
    if not supplement:
        return jsonify({'error': 'Supplement not found'}), 404

    return jsonify({'supplement': supplement.to_dict()})


@customer_bp.route('/pdr-supplements/<int:supplement_id>/pdf', methods=['GET'])
@login_required
def get_supplement_pdf(supplement_id):
    """
    Generate and download PDF for a supplement.

    Returns:
        200: PDF file download
        404: Supplement not found
    """
    from flask import make_response
    from app.models.tenant import EstimateSupplement, EstimateVersion
    from app.models.master.tenant import Tenant
    from app.services.supplement_pdf_generator import generate_supplement_pdf

    identity = parse_identity(get_jwt_identity())

    supplement = EstimateSupplement.query.get(supplement_id)
    if not supplement:
        return jsonify({'error': 'Supplement not found'}), 404

    # Get baseline version for estimate context
    baseline = EstimateVersion.query.get(supplement.baseline_version_id)
    estimate_data = baseline.snapshot_json if baseline else {}

    # Override with current totals from supplement
    estimate_data['total_price'] = supplement.revised_total

    # Get shop info
    shop_info = None
    tenant = Tenant.query.get(identity['tenant_id']) if identity else None
    if tenant:
        shop_info = {'company_name': tenant.company_name}

    try:
        pdf_buffer = generate_supplement_pdf(
            supplement_data=supplement.to_dict(),
            estimate_data=estimate_data,
            shop_info=shop_info
        )

        # Create filename
        estimate_num = estimate_data.get('estimate_number', f'EST-{supplement.estimate_id}')
        filename = f"Supplement-{estimate_num}-S{supplement.supplement_number}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


@customer_bp.route('/pdr-supplements/<int:supplement_id>/send', methods=['POST'])
@login_required
@permission_required(Permission.SUPPLEMENT_SEND)
def send_supplement(supplement_id):
    """
    Send supplement PDF via email.

    Request body:
    {
        "to": "adjuster@insurance.com",
        "cc": ["optional@shop.com"],
        "subject": "Supplement #1 for Estimate...",
        "message": "Hello..."
    }

    Returns:
        200: { status: "sent", message_id: "..." }
        400: { status: "failed", error: "..." }
    """
    from app.models.tenant import EstimateSupplement, EstimateVersion, EstimateActivity
    from app.models.master.tenant import Tenant
    from app.services.supplement_pdf_generator import generate_supplement_pdf
    from app.services.email_service import get_email_service

    identity = parse_identity(get_jwt_identity())
    data = request.get_json() or {}

    to = data.get('to')
    if not to:
        return jsonify({'status': 'failed', 'error': 'Recipient email is required'}), 400

    supplement = EstimateSupplement.query.get(supplement_id)
    if not supplement:
        return jsonify({'status': 'failed', 'error': 'Supplement not found'}), 404

    # Get baseline version for estimate context
    baseline = EstimateVersion.query.get(supplement.baseline_version_id)
    estimate_data = baseline.snapshot_json if baseline else {}

    # Get shop info
    shop_info = None
    tenant = Tenant.query.get(identity['tenant_id']) if identity else None
    if tenant:
        shop_info = {'company_name': tenant.company_name}

    user_id = identity.get('user_id') if identity else None

    try:
        # Generate supplement PDF
        pdf_buffer = generate_supplement_pdf(
            supplement_data=supplement.to_dict(),
            estimate_data=estimate_data,
            shop_info=shop_info
        )
        pdf_bytes = pdf_buffer.read()

        # Build email
        cc = data.get('cc', [])
        if isinstance(cc, str):
            cc = [cc] if cc else []

        estimate_num = estimate_data.get('estimate_number', f'EST-{supplement.estimate_id}')
        vehicle = f"{estimate_data.get('vehicle_year', '')} {estimate_data.get('vehicle_make', '')} {estimate_data.get('vehicle_model', '')}".strip()

        subject = data.get('subject') or f"Supplement #{supplement.supplement_number} for {estimate_num}"
        message = data.get('message') or f"""Hello,

Please find attached Supplement #{supplement.supplement_number} for Estimate {estimate_num}.

Vehicle: {vehicle}
Supplement Amount: ${float(supplement.delta_amount or 0):,.2f}

Summary: {supplement.summary or 'Additional damage discovered during repair.'}

Please review and let us know if you have any questions.

Thank you"""

        # Send via email service
        email_service = get_email_service()
        filename = f"Supplement-{estimate_num}-S{supplement.supplement_number}.pdf"
        attachments = [(filename, pdf_bytes, 'application/pdf')]

        if email_service.is_configured:
            result = email_service._send_smtp(to, cc, subject, message, attachments)
        else:
            result = email_service._send_dev_mode(to, cc, subject, message, attachments)

        # Log activity
        activity_metadata = {
            'supplement_id': supplement.id,
            'supplement_number': supplement.supplement_number,
            'to': to,
            'cc': cc,
            'message_id': result.message_id
        }

        if result.success:
            supplement.mark_sent()
            db.session.commit()

            EstimateActivity.log(
                estimate_id=supplement.estimate_id,
                activity_type='supplement_sent',
                user_id=user_id,
                metadata=activity_metadata
            )
        else:
            activity_metadata['error'] = result.error
            EstimateActivity.log(
                estimate_id=supplement.estimate_id,
                activity_type='supplement_failed',
                user_id=user_id,
                metadata=activity_metadata
            )

        return jsonify(result.to_dict()), 200 if result.success else 400

    except Exception as e:
        import traceback
        traceback.print_exc()

        EstimateActivity.log(
            estimate_id=supplement.estimate_id,
            activity_type='supplement_failed',
            user_id=user_id,
            activity_data={'to': to, 'error': str(e)}
        )

        return jsonify({'status': 'failed', 'error': str(e)}), 400


# ==============================================================================
# DISPUTE PACK ENDPOINTS
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/dispute-pack.zip', methods=['GET'])
@login_required
@permission_required(Permission.ESTIMATE_DOWNLOAD_DISPUTE_PACK)
def get_estimate_dispute_pack(estimate_id):
    """
    Generate and download a dispute pack ZIP containing all estimate documents.

    Includes:
    - Estimate PDF
    - Photo Sheet PDF (if photos exist)
    - All Supplement PDFs
    - Activity Log (text file)

    Args:
        estimate_id: Estimate ID

    Returns:
        200: ZIP file download
        404: Estimate not found
        500: Generation error
    """
    from flask import make_response
    from app.services.dispute_pack_generator import generate_dispute_pack_zip, get_dispute_pack_filename
    from app.models.master.tenant import Tenant
    from app.models.tenant.estimate_photo import EstimatePhoto
    from app.models.tenant.estimate_supplement import EstimateSupplement
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.pdr_estimate_panel import PDREstimatePanel
    from app.models.tenant.part_request import PartRequest
    from app.services.ri_service import RIService

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    # Get tenant info
    tenant = Tenant.query.get(identity['tenant_id'])
    tenant_name = tenant.company_name if tenant else "HailTracker Pro"

    # Fetch estimate from database
    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        estimate_data = estimate.to_dict()
    except Exception:
        # Fallback if model not available
        estimate_data = {
            'id': estimate_id,
            'estimate_number': f'EST-{estimate_id:05d}',
            'vehicle_year': 2024,
            'vehicle_make': 'Unknown',
            'vehicle_model': 'Vehicle',
            'customer_name': 'Unknown'
        }

    # Fetch panels
    try:
        panels = PDREstimatePanel.query.filter_by(estimate_id=estimate_id).all()
        panels_data = [p.to_dict() for p in panels]
    except Exception:
        panels_data = []

    # Fetch photos
    try:
        photos = EstimatePhoto.query.filter_by(estimate_id=estimate_id).order_by(
            EstimatePhoto.panel_name,
            EstimatePhoto.created_at
        ).all()
        photos_data = [p.to_dict() for p in photos]
    except Exception:
        photos_data = []

    # Fetch supplements
    try:
        supplements = EstimateSupplement.query.filter_by(estimate_id=estimate_id).order_by(
            EstimateSupplement.supplement_number
        ).all()
        supplements_data = [s.to_dict() for s in supplements]
    except Exception:
        supplements_data = []

    # Fetch activities
    try:
        activities = EstimateActivity.query.filter_by(estimate_id=estimate_id).order_by(
            EstimateActivity.created_at.desc()
        ).limit(100).all()
        activities_data = [a.to_dict() for a in activities]
    except Exception:
        activities_data = []

    # Phase 7C: Fetch R&I summary and denial pack
    ri_summary = None
    ri_denial_pack = None
    try:
        ri_data = RIService.get_estimate_ri_summary(estimate_id, identity['tenant_id'])
        if ri_data:
            ri_summary = ri_data
            ri_denial_pack = ri_data.get('ri_denial_pack')
    except Exception:
        pass  # R&I data optional

    # Phase 7C: Fetch parts requests
    parts_requests_data = []
    try:
        parts = PartRequest.query.filter_by(estimate_id=estimate_id).all()
        parts_requests_data = [p.to_dict() for p in parts]
    except Exception:
        pass  # Parts data optional

    try:
        # Generate the ZIP
        zip_buffer = generate_dispute_pack_zip(
            estimate_data=estimate_data,
            panels=panels_data,
            photos=photos_data,
            supplements=supplements_data,
            activities=activities_data,
            tenant_name=tenant_name,
            ri_summary=ri_summary,
            ri_denial_pack=ri_denial_pack,
            parts_requests=parts_requests_data
        )

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='dispute_pack_downloaded',
            user_id=user_id,
            activity_data={
                'supplements_included': len(supplements_data),
                'photos_included': len(photos_data)
            }
        )

        # Create response
        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        filename = get_dispute_pack_filename(estimate_number)

        response = make_response(zip_buffer.read())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        import traceback
        traceback.print_exc()

        # Log failure
        try:
            EstimateActivity.log(
                estimate_id=estimate_id,
                activity_type='dispute_pack_failed',
                user_id=user_id,
                activity_data={'error': str(e)}
            )
        except:
            pass

        return jsonify({'error': f'Dispute pack generation failed: {str(e)}'}), 500


# ==============================================================================
# SHARE LINK ENDPOINTS (AUTHENTICATED)
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/share-link', methods=['POST'])
@login_required
@permission_required(Permission.ESTIMATE_CREATE_SHARE_LINK)
def create_estimate_share_link(estimate_id):
    """
    Create a share link for an estimate.

    Body:
        expires_in_days: Optional[int] - Days until expiration (default 14, max 90)
        allow_photosheet: Optional[bool] - Allow photo sheet download (default true)
        allow_dispute_pack: Optional[bool] - Allow dispute pack download (default true)
        allow_supplements: Optional[bool] - Allow supplement access (default true)

    Returns:
        200: { url, token, expires_at, permissions }
        404: Estimate not found
        500: Error creating share link
    """
    from app.services.share_token_service import create_estimate_share_token
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    # Verify estimate exists and belongs to tenant
    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404
    except Exception:
        pass  # Table may not exist in dev

    data = request.get_json() or {}

    try:
        # Get base URL from request or environment
        base_url = request.host_url.rstrip('/')
        if base_url.endswith('/api'):
            base_url = base_url[:-4]

        # Create the share token
        result = create_estimate_share_token(
            tenant_id=tenant_id,
            estimate_id=estimate_id,
            expires_in_days=data.get('expires_in_days', 14),
            allow_estimate_pdf=True,  # Always allow estimate PDF
            allow_photosheet=data.get('allow_photosheet', True),
            allow_dispute_pack=data.get('allow_dispute_pack', True),
            allow_supplements=data.get('allow_supplements', True),
            created_by=user_id,
            base_url=base_url
        )

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='share_link_created',
            user_id=user_id,
            activity_data={
                'expires_at': result.expires_at.isoformat(),
                'allow_photosheet': result.payload.allow_photosheet,
                'allow_dispute_pack': result.payload.allow_dispute_pack,
                'allow_supplements': result.payload.allow_supplements
            }
        )

        return jsonify({
            'url': result.url,
            'token': result.token,
            'expires_at': result.expires_at.isoformat(),
            'permissions': {
                'estimate_pdf': result.payload.allow_estimate_pdf,
                'photosheet': result.payload.allow_photosheet,
                'dispute_pack': result.payload.allow_dispute_pack,
                'supplements': result.payload.allow_supplements
            }
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create share link: {str(e)}'}), 500


# ==============================================================================
# PUBLIC SHARE ENDPOINTS (NO AUTH - TOKEN VALIDATED)
# ==============================================================================

@customer_bp.route('/public/share/estimate/<token>', methods=['GET'])
def get_shared_estimate(token):
    """
    Get shared estimate data (public, no auth required).

    Returns minimal data needed for the share portal page.
    Logs share_link_opened on first access.

    Returns:
        200: { estimate info, available exports, supplements if allowed }
        401: Token expired or invalid
        404: Estimate not found
    """
    from app.services.share_token_service import (
        verify_estimate_share_token,
        TokenExpiredError,
        TokenInvalidError
    )
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_supplement import EstimateSupplement
    from app.models.tenant.estimate_photo import EstimatePhoto
    from app.models.tenant.estimate_activity import EstimateActivity

    try:
        payload = verify_estimate_share_token(token)
    except TokenExpiredError:
        return jsonify({'error': 'This share link has expired', 'expired': True}), 401
    except TokenInvalidError as e:
        return jsonify({'error': str(e), 'invalid': True}), 401

    estimate_id = payload.estimate_id

    # Fetch estimate
    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404
        estimate_data = estimate.to_dict()
    except Exception:
        # Fallback for dev
        estimate_data = {
            'id': estimate_id,
            'estimate_number': f'EST-{estimate_id:05d}',
            'vehicle_year': 2024,
            'vehicle_make': 'Sample',
            'vehicle_model': 'Vehicle',
            'customer_name': 'Customer'
        }

    # Check if photos exist
    has_photos = False
    try:
        photo_count = EstimatePhoto.query.filter_by(estimate_id=estimate_id).count()
        has_photos = photo_count > 0
    except Exception:
        pass

    # Get supplements if allowed
    supplements_list = []
    if payload.allow_supplements:
        try:
            supplements = EstimateSupplement.query.filter_by(estimate_id=estimate_id).order_by(
                EstimateSupplement.supplement_number
            ).all()
            supplements_list = [
                {
                    'id': s.id,
                    'supplement_number': s.supplement_number,
                    'status': s.status,
                    'delta_amount': float(s.delta_amount) if s.delta_amount else None,
                    'created_at': s.created_at.isoformat() if s.created_at else None
                }
                for s in supplements
            ]
        except Exception:
            pass

    # Log share link opened
    try:
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='share_link_opened',
            user_id=None,  # Public access
            activity_data={
                'token_created_by': payload.created_by,
                'ip': request.remote_addr
            }
        )
    except Exception:
        pass

    # Build response
    return jsonify({
        'estimate': {
            'id': estimate_data.get('id'),
            'estimate_number': estimate_data.get('estimate_number'),
            'vehicle_year': estimate_data.get('vehicle_year'),
            'vehicle_make': estimate_data.get('vehicle_make'),
            'vehicle_model': estimate_data.get('vehicle_model'),
            'status': estimate_data.get('status'),
            'total': estimate_data.get('total_price') or estimate_data.get('total'),
            # Approval/signature info
            'approval_status': estimate_data.get('approval_status', 'draft'),
            'is_signed': estimate_data.get('is_signed', False),
            'signed_at': estimate_data.get('signed_at'),
            'signed_by_name': estimate_data.get('signed_by_name'),
            'customer_name': estimate_data.get('customer_name')
        },
        'permissions': {
            'estimate_pdf': payload.allow_estimate_pdf,
            'photosheet': payload.allow_photosheet and has_photos,
            'dispute_pack': payload.allow_dispute_pack,
            'supplements': payload.allow_supplements,
            'signing': payload.allow_signing
        },
        'supplements': supplements_list if payload.allow_supplements else [],
        'expires_at': payload.expires_at.isoformat()
    }), 200


@customer_bp.route('/public/share/estimate/<token>/pdf', methods=['GET'])
def download_shared_estimate_pdf(token):
    """
    Download shared estimate PDF (public, no auth).
    """
    from flask import make_response
    from app.services.share_token_service import (
        verify_estimate_share_token,
        require_token_permission,
        TokenExpiredError,
        TokenInvalidError,
        TokenPermissionError
    )
    from app.services.pdr_pdf_generator import generate_pdr_estimate_pdf
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.pdr_estimate_panel import PDREstimatePanel
    from app.models.tenant.estimate_photo import EstimatePhoto
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.tenant import Tenant

    try:
        payload = verify_estimate_share_token(token)
        require_token_permission(payload, 'estimate_pdf')
    except TokenExpiredError:
        return jsonify({'error': 'This share link has expired'}), 401
    except (TokenInvalidError, TokenPermissionError) as e:
        return jsonify({'error': str(e)}), 401

    estimate_id = payload.estimate_id
    tenant_id = payload.tenant_id

    # Get tenant name
    tenant_name = "HailTracker Pro"
    try:
        tenant = Tenant.query.get(tenant_id)
        if tenant:
            tenant_name = tenant.company_name
    except Exception:
        pass

    # Fetch estimate
    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404
        estimate_data = estimate.to_dict()
    except Exception:
        estimate_data = {
            'id': estimate_id,
            'estimate_number': f'EST-{estimate_id:05d}'
        }

    # Fetch panels
    try:
        panels = PDREstimatePanel.query.filter_by(estimate_id=estimate_id).all()
        panels_data = [p.to_dict() for p in panels]
    except Exception:
        panels_data = []

    # Fetch photos
    try:
        photos = EstimatePhoto.query.filter_by(estimate_id=estimate_id).all()
        photos_data = [p.to_dict() for p in photos]
    except Exception:
        photos_data = []

    try:
        pdf_buffer = generate_pdr_estimate_pdf(
            estimate_data=estimate_data,
            panels=panels_data,
            photos=photos_data,
            tenant_name=tenant_name
        )

        # Log download
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='share_downloaded_pdf',
            user_id=None,
            activity_data={'ip': request.remote_addr}
        )

        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        filename = f"Estimate-{estimate_number}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500


@customer_bp.route('/public/share/estimate/<token>/photosheet.pdf', methods=['GET'])
def download_shared_photosheet(token):
    """
    Download shared photo sheet PDF (public, no auth).
    """
    from flask import make_response
    from app.services.share_token_service import (
        verify_estimate_share_token,
        require_token_permission,
        TokenExpiredError,
        TokenInvalidError,
        TokenPermissionError
    )
    from app.services.photo_sheet_generator import generate_photo_sheet_pdf
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_photo import EstimatePhoto
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.tenant import Tenant

    try:
        payload = verify_estimate_share_token(token)
        require_token_permission(payload, 'photosheet')
    except TokenExpiredError:
        return jsonify({'error': 'This share link has expired'}), 401
    except (TokenInvalidError, TokenPermissionError) as e:
        return jsonify({'error': str(e)}), 401

    estimate_id = payload.estimate_id
    tenant_id = payload.tenant_id

    # Get tenant name
    tenant_name = "HailTracker Pro"
    try:
        tenant = Tenant.query.get(tenant_id)
        if tenant:
            tenant_name = tenant.company_name
    except Exception:
        pass

    # Fetch estimate
    try:
        estimate = PDREstimate.query.get(estimate_id)
        estimate_data = estimate.to_dict() if estimate else {}
    except Exception:
        estimate_data = {'id': estimate_id, 'estimate_number': f'EST-{estimate_id:05d}'}

    # Fetch photos
    try:
        photos = EstimatePhoto.query.filter_by(estimate_id=estimate_id).order_by(
            EstimatePhoto.panel_name,
            EstimatePhoto.created_at
        ).all()
        photos_data = [p.to_dict() for p in photos]
    except Exception:
        photos_data = []

    if not photos_data:
        return jsonify({'error': 'No photos available'}), 404

    try:
        pdf_buffer = generate_photo_sheet_pdf(
            estimate_data=estimate_data,
            photos=photos_data,
            tenant_name=tenant_name
        )

        # Log download
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='share_downloaded_photosheet',
            user_id=None,
            activity_data={'ip': request.remote_addr}
        )

        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        filename = f"PhotoSheet-{estimate_number}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Photo sheet generation failed: {str(e)}'}), 500


@customer_bp.route('/public/share/estimate/<token>/dispute-pack.zip', methods=['GET'])
def download_shared_dispute_pack(token):
    """
    Download shared dispute pack ZIP (public, no auth).
    """
    from flask import make_response
    from app.services.share_token_service import (
        verify_estimate_share_token,
        require_token_permission,
        TokenExpiredError,
        TokenInvalidError,
        TokenPermissionError
    )
    from app.services.dispute_pack_generator import generate_dispute_pack_zip, get_dispute_pack_filename
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.pdr_estimate_panel import PDREstimatePanel
    from app.models.tenant.estimate_photo import EstimatePhoto
    from app.models.tenant.estimate_supplement import EstimateSupplement
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.tenant import Tenant
    from app.models.tenant.part_request import PartRequest
    from app.services.ri_service import RIService

    try:
        payload = verify_estimate_share_token(token)
        require_token_permission(payload, 'dispute_pack')
    except TokenExpiredError:
        return jsonify({'error': 'This share link has expired'}), 401
    except (TokenInvalidError, TokenPermissionError) as e:
        return jsonify({'error': str(e)}), 401

    estimate_id = payload.estimate_id
    tenant_id = payload.tenant_id

    # Get tenant name
    tenant_name = "HailTracker Pro"
    try:
        tenant = Tenant.query.get(tenant_id)
        if tenant:
            tenant_name = tenant.company_name
    except Exception:
        pass

    # Fetch all data
    try:
        estimate = PDREstimate.query.get(estimate_id)
        estimate_data = estimate.to_dict() if estimate else {'id': estimate_id, 'estimate_number': f'EST-{estimate_id:05d}'}
    except Exception:
        estimate_data = {'id': estimate_id, 'estimate_number': f'EST-{estimate_id:05d}'}

    try:
        panels = PDREstimatePanel.query.filter_by(estimate_id=estimate_id).all()
        panels_data = [p.to_dict() for p in panels]
    except Exception:
        panels_data = []

    try:
        photos = EstimatePhoto.query.filter_by(estimate_id=estimate_id).all()
        photos_data = [p.to_dict() for p in photos]
    except Exception:
        photos_data = []

    try:
        supplements = EstimateSupplement.query.filter_by(estimate_id=estimate_id).all()
        supplements_data = [s.to_dict() for s in supplements]
    except Exception:
        supplements_data = []

    try:
        activities = EstimateActivity.query.filter_by(estimate_id=estimate_id).order_by(
            EstimateActivity.created_at.desc()
        ).limit(100).all()
        activities_data = [a.to_dict() for a in activities]
    except Exception:
        activities_data = []

    # Phase 7C: Fetch R&I summary and denial pack
    ri_summary = None
    ri_denial_pack = None
    try:
        ri_data = RIService.get_estimate_ri_summary(estimate_id, tenant_id)
        if ri_data:
            ri_summary = ri_data
            ri_denial_pack = ri_data.get('ri_denial_pack')
    except Exception:
        pass  # R&I data optional

    # Phase 7C: Fetch parts requests
    parts_requests_data = []
    try:
        parts = PartRequest.query.filter_by(estimate_id=estimate_id).all()
        parts_requests_data = [p.to_dict() for p in parts]
    except Exception:
        pass  # Parts data optional

    try:
        zip_buffer = generate_dispute_pack_zip(
            estimate_data=estimate_data,
            panels=panels_data,
            photos=photos_data,
            supplements=supplements_data,
            activities=activities_data,
            tenant_name=tenant_name,
            ri_summary=ri_summary,
            ri_denial_pack=ri_denial_pack,
            parts_requests=parts_requests_data
        )

        # Log download
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='share_downloaded_dispute_pack',
            user_id=None,
            activity_data={'ip': request.remote_addr}
        )

        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        filename = get_dispute_pack_filename(estimate_number)

        response = make_response(zip_buffer.read())
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Dispute pack generation failed: {str(e)}'}), 500


@customer_bp.route('/public/share/supplement/<token>/<int:supplement_id>/pdf', methods=['GET'])
def download_shared_supplement_pdf(token, supplement_id):
    """
    Download shared supplement PDF (public, no auth).
    """
    from flask import make_response
    from app.services.share_token_service import (
        verify_estimate_share_token,
        require_token_permission,
        TokenExpiredError,
        TokenInvalidError,
        TokenPermissionError
    )
    from app.services.supplement_pdf_generator import generate_supplement_pdf
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_supplement import EstimateSupplement
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.tenant import Tenant

    try:
        payload = verify_estimate_share_token(token)
        require_token_permission(payload, 'supplements')
    except TokenExpiredError:
        return jsonify({'error': 'This share link has expired'}), 401
    except (TokenInvalidError, TokenPermissionError) as e:
        return jsonify({'error': str(e)}), 401

    estimate_id = payload.estimate_id
    tenant_id = payload.tenant_id

    # Verify supplement belongs to this estimate
    try:
        supplement = EstimateSupplement.query.get(supplement_id)
        if not supplement or supplement.estimate_id != estimate_id:
            return jsonify({'error': 'Supplement not found'}), 404
    except Exception:
        return jsonify({'error': 'Supplement not found'}), 404

    # Get tenant name
    tenant_name = "HailTracker Pro"
    try:
        tenant = Tenant.query.get(tenant_id)
        if tenant:
            tenant_name = tenant.company_name
    except Exception:
        pass

    # Fetch estimate
    try:
        estimate = PDREstimate.query.get(estimate_id)
        estimate_data = estimate.to_dict() if estimate else {}
    except Exception:
        estimate_data = {'id': estimate_id, 'estimate_number': f'EST-{estimate_id:05d}'}

    try:
        pdf_buffer = generate_supplement_pdf(
            estimate_data=estimate_data,
            supplement_data=supplement.to_dict(),
            photos=[],  # Supplement photos if available
            tenant_name=tenant_name
        )

        # Log download
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='share_downloaded_supplement',
            user_id=None,
            activity_data={
                'supplement_id': supplement_id,
                'supplement_number': supplement.supplement_number,
                'ip': request.remote_addr
            }
        )

        estimate_number = estimate_data.get('estimate_number', f'EST-{estimate_id}')
        filename = f"Supplement-{estimate_number}-S{supplement.supplement_number}.pdf"

        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Supplement PDF generation failed: {str(e)}'}), 500


# ==============================================================================
# SIGNATURE & APPROVAL ENDPOINTS (AUTHENTICATED)
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/request-signature', methods=['POST'])
@login_required
@permission_required(Permission.ESTIMATE_REQUEST_SIGNATURE)
def request_estimate_signature(estimate_id):
    """
    Request customer signature by creating a share link with signing permission.

    Body:
        expires_in_days: Optional[int] - Days until expiration (default 14)

    Returns:
        200: { url, token, expires_at }
        404: Estimate not found
    """
    from app.extensions import db
    from app.services.share_token_service import create_estimate_share_token
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Update approval status to pending
        if estimate.approval_status == PDREstimate.APPROVAL_DRAFT:
            estimate.approval_status = PDREstimate.APPROVAL_PENDING
            db.session.commit()

        # Get base URL
        base_url = request.host_url.rstrip('/')
        if base_url.endswith('/api'):
            base_url = base_url[:-4]

        # Create share token with signing enabled
        result = create_estimate_share_token(
            tenant_id=tenant_id,
            estimate_id=estimate_id,
            expires_in_days=data.get('expires_in_days', 14),
            allow_estimate_pdf=True,
            allow_photosheet=True,
            allow_dispute_pack=False,
            allow_supplements=True,
            allow_signing=True,  # Enable signing
            created_by=user_id,
            base_url=base_url
        )

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='signature_requested',
            user_id=user_id,
            activity_data={
                'expires_at': result.expires_at.isoformat(),
                'url': result.url
            }
        )

        return jsonify({
            'url': result.url,
            'token': result.token,
            'expires_at': result.expires_at.isoformat(),
            'approval_status': estimate.approval_status
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to request signature: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/sign', methods=['POST'])
@login_required
def sign_estimate_internal(estimate_id):
    """
    Record customer authorization signature (internal/walk-in).

    This captures the customer's authorization to proceed with repairs.
    Note: This is separate from insurer approval.

    Body:
        name: str - Customer name (required)
        email: str - Customer email (optional)
        signature: str - Base64 PNG data URL (required)

    Returns:
        200: { success, signed_at, signed_by_name, customer_status }
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity
    import base64

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    signature_data_url = data.get('signature')

    if not name:
        return jsonify({'error': 'Customer name is required'}), 400
    if not signature_data_url:
        return jsonify({'error': 'Signature is required'}), 400

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Check if already authorized
        if estimate.is_customer_authorized():
            return jsonify({'error': 'Customer has already authorized this estimate'}), 400

        # Parse data URL and extract PNG bytes
        # Format: data:image/png;base64,<base64data>
        if ';base64,' in signature_data_url:
            sig_data = signature_data_url.split(';base64,')[1]
        else:
            sig_data = signature_data_url
        signature_bytes = base64.b64decode(sig_data)

        # Record customer authorization
        meta = {
            'method': 'internal',
            'user_id': user_id,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        }
        estimate.mark_customer_authorized(name=name, signature_bytes=signature_bytes, email=email, meta=meta)
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='customer_authorized',
            user_id=user_id,
            activity_data={
                'signed_by_name': name,
                'signed_by_email': email,
                'method': 'internal'
            }
        )

        return jsonify({
            'success': True,
            'signed_at': estimate.signed_at.isoformat(),
            'signed_by_name': estimate.signed_by_name,
            'customer_status': estimate.customer_status,
            # Legacy field
            'approval_status': estimate.approval_status
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to record customer authorization: {str(e)}'}), 500


# ==============================================================================
# LEGACY APPROVE/DECLINE ENDPOINTS (now maps to insurer workflow)
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/approve', methods=['POST'])
@login_required
@permission_required(Permission.INSURER_APPROVE)
def approve_estimate(estimate_id):
    """
    Legacy: Approve estimate (now marks insurer approved).

    This endpoint now maps to insurer approval workflow.
    For customer authorization, use /sign endpoint.

    Returns:
        200: { success, insurer_approved_at, insurer_status }
        400: Already approved
        409: Estimate locked - use supplements
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        if estimate.is_insurer_approved():
            return jsonify({'error': 'Estimate already insurer approved'}), 400

        # Mark insurer approved (this also locks the estimate)
        estimate.mark_insurer_approved(user_id=user_id)
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='insurer_approved',
            user_id=user_id,
            activity_data={
                'recorded_by': user_id
            }
        )

        return jsonify({
            'success': True,
            'insurer_approved_at': estimate.insurer_approved_at.isoformat() if estimate.insurer_approved_at else None,
            'insurer_status': estimate.insurer_status,
            'is_locked': estimate.is_locked(),
            # Legacy fields
            'approved_at': estimate.approved_at.isoformat() if estimate.approved_at else None,
            'approval_status': estimate.approval_status
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to approve estimate: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/decline', methods=['POST'])
@login_required
@permission_required(Permission.INSURER_DECLINE)
def decline_estimate(estimate_id):
    """
    Legacy: Decline estimate (now marks insurer declined).

    Body:
        reason: str - Decline reason (optional)

    Returns:
        200: { success, insurer_declined_at, insurer_status }
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    reason = data.get('reason', '')

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Mark insurer declined
        estimate.mark_insurer_declined(reason=reason)
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='insurer_declined',
            user_id=user_id,
            activity_data={
                'reason': reason
            }
        )

        return jsonify({
            'success': True,
            'insurer_declined_at': estimate.insurer_declined_at.isoformat() if estimate.insurer_declined_at else None,
            'insurer_declined_reason': estimate.insurer_declined_reason,
            'insurer_status': estimate.insurer_status,
            # Legacy fields
            'declined_at': estimate.declined_at.isoformat() if estimate.declined_at else None,
            'approval_status': estimate.approval_status
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to decline estimate: {str(e)}'}), 500


# ==============================================================================
# INSURER WORKFLOW ENDPOINTS (NEW)
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/submit-to-insurer', methods=['POST'])
@login_required
@permission_required(Permission.INSURER_SUBMIT)
def submit_to_insurer(estimate_id):
    """
    Submit estimate to insurer for approval.

    Sets insurer_status to 'submitted'.

    Returns:
        200: { success, submitted_at, insurer_status }
        400: Already submitted/approved
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        if estimate.insurer_status == 'approved':
            return jsonify({'error': 'Estimate already approved by insurer'}), 400

        if estimate.insurer_status == 'submitted':
            return jsonify({'error': 'Estimate already submitted to insurer'}), 400

        # Submit to insurer
        estimate.submit_to_insurer(user_id=user_id)
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='insurer_submitted',
            user_id=user_id,
            activity_data={
                'submitted_by': user_id
            }
        )

        return jsonify({
            'success': True,
            'submitted_to_insurer_at': estimate.submitted_to_insurer_at.isoformat() if estimate.submitted_to_insurer_at else None,
            'insurer_status': estimate.insurer_status
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to submit to insurer: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/insurer-approve', methods=['POST'])
@login_required
@permission_required(Permission.INSURER_APPROVE)
def insurer_approve(estimate_id):
    """
    Record insurer approval of estimate with optional partial approval amounts.

    This LOCKS the estimate - further changes require supplements.

    Body:
        approved_total: float - Total amount approved by insurer (required)
        approved_labor: float - Labor portion approved (optional)
        approved_ri: float - R&I portion approved (optional)
        approved_materials: float - Materials portion approved (optional)
        approved_tax: float - Tax portion approved (optional)
        notes: str - Approval notes from adjuster (optional)
        reference: str - Adjuster reference ID (optional)

    Returns:
        200: { success, insurer_approved_at, insurer_status, is_locked, financial data }
        400: Already approved or validation error
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    data = request.get_json() or {}

    # Parse financial fields
    approved_total = data.get('approved_total')
    approved_labor = data.get('approved_labor')
    approved_ri = data.get('approved_ri')
    approved_materials = data.get('approved_materials')
    approved_tax = data.get('approved_tax')
    notes = data.get('notes', '')
    reference = data.get('reference', '')

    # Validate approved_total is provided
    if approved_total is None:
        return jsonify({'error': 'approved_total is required'}), 400

    try:
        approved_total = float(approved_total)
        if approved_total < 0:
            return jsonify({'error': 'approved_total cannot be negative'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'approved_total must be a valid number'}), 400

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        if estimate.is_insurer_approved():
            return jsonify({'error': 'Estimate already approved by insurer'}), 400

        # Get requested total before approval
        requested_total = estimate.get_requested_total()

        # Mark insurer approved with financial data
        estimate.mark_insurer_approved(
            user_id=user_id,
            approved_total=approved_total,
            approved_labor=float(approved_labor) if approved_labor is not None else None,
            approved_ri=float(approved_ri) if approved_ri is not None else None,
            approved_materials=float(approved_materials) if approved_materials is not None else None,
            approved_tax=float(approved_tax) if approved_tax is not None else None,
            notes=notes,
            reference=reference
        )
        db.session.commit()

        # Calculate delta
        short_paid = estimate.get_short_paid_amount()

        # Log activity with financial details
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='insurer_approved',
            user_id=user_id,
            activity_data={
                'recorded_by': user_id,
                'requested_total': requested_total,
                'approved_total': approved_total,
                'short_paid': short_paid,
                'notes': notes,
                'reference': reference
            }
        )

        return jsonify({
            'success': True,
            'insurer_approved_at': estimate.insurer_approved_at.isoformat() if estimate.insurer_approved_at else None,
            'insurer_status': estimate.insurer_status,
            'is_locked': estimate.is_locked(),
            'requested_total': requested_total,
            'approved_total': approved_total,
            'short_paid_amount': short_paid,
            'has_partial_approval': estimate.has_partial_approval(),
            'message': 'Estimate is now locked. Further changes require supplements.'
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to record insurer approval: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/update-insurer-approval', methods=['POST'])
@login_required
@permission_required(Permission.INSURER_APPROVE)
def update_insurer_approval(estimate_id):
    """
    Update insurer approval amounts (for corrections after initial approval).

    Body:
        approved_total: float - Updated total amount approved (optional)
        approved_labor: float - Updated labor portion (optional)
        approved_ri: float - Updated R&I portion (optional)
        approved_materials: float - Updated materials portion (optional)
        approved_tax: float - Updated tax portion (optional)
        notes: str - Updated notes (optional)
        reference: str - Updated reference (optional)

    Returns:
        200: { success, updated financial data }
        400: Not approved yet
        404: Estimate not found
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    data = request.get_json() or {}

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        if not estimate.is_insurer_approved():
            return jsonify({'error': 'Estimate has not been approved by insurer yet'}), 400

        # Get old values for logging
        old_approved_total = estimate.get_approved_total()

        # Parse and update fields
        approved_total = data.get('approved_total')
        if approved_total is not None:
            try:
                approved_total = float(approved_total)
                if approved_total < 0:
                    return jsonify({'error': 'approved_total cannot be negative'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'approved_total must be a valid number'}), 400

        estimate.update_insurer_approval(
            approved_total=approved_total,
            approved_labor=float(data['approved_labor']) if data.get('approved_labor') is not None else None,
            approved_ri=float(data['approved_ri']) if data.get('approved_ri') is not None else None,
            approved_materials=float(data['approved_materials']) if data.get('approved_materials') is not None else None,
            approved_tax=float(data['approved_tax']) if data.get('approved_tax') is not None else None,
            notes=data.get('notes'),
            reference=data.get('reference')
        )
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='insurer_approval_updated',
            user_id=user_id,
            activity_data={
                'updated_by': user_id,
                'old_approved_total': old_approved_total,
                'new_approved_total': estimate.get_approved_total(),
                'short_paid': estimate.get_short_paid_amount()
            }
        )

        return jsonify({
            'success': True,
            'requested_total': estimate.get_requested_total(),
            'approved_total': estimate.get_approved_total(),
            'short_paid_amount': estimate.get_short_paid_amount(),
            'has_partial_approval': estimate.has_partial_approval(),
            'insurer_approval_notes': estimate.insurer_approval_notes,
            'insurer_approval_reference': estimate.insurer_approval_reference
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update insurer approval: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/insurer-decline', methods=['POST'])
@login_required
@permission_required(Permission.INSURER_DECLINE)
def insurer_decline(estimate_id):
    """
    Record insurer decline of estimate.

    Body:
        reason: str - Decline reason (optional)

    Returns:
        200: { success, insurer_declined_at, insurer_status }
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    reason = data.get('reason', '')

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Mark insurer declined
        estimate.mark_insurer_declined(reason=reason)
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='insurer_declined',
            user_id=user_id,
            activity_data={
                'reason': reason,
                'recorded_by': user_id
            }
        )

        return jsonify({
            'success': True,
            'insurer_declined_at': estimate.insurer_declined_at.isoformat() if estimate.insurer_declined_at else None,
            'insurer_declined_reason': estimate.insurer_declined_reason,
            'insurer_status': estimate.insurer_status
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to record insurer decline: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/insurer-needs-revision', methods=['POST'])
@login_required
@permission_required(Permission.INSURER_DECLINE)
def insurer_needs_revision(estimate_id):
    """
    Record insurer needs revision on estimate.

    Body:
        reason: str - Revision notes (optional)

    Returns:
        200: { success, insurer_status }
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    reason = data.get('reason', '')

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Mark needs revision
        estimate.mark_insurer_needs_revision(reason=reason)
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='insurer_needs_revision',
            user_id=user_id,
            activity_data={
                'reason': reason,
                'recorded_by': user_id
            }
        )

        return jsonify({
            'success': True,
            'insurer_status': estimate.insurer_status,
            'insurer_declined_reason': estimate.insurer_declined_reason
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to record revision request: {str(e)}'}), 500


# ==============================================================================
# PUBLIC SIGNATURE ENDPOINT (TOKEN-BASED)
# ==============================================================================

@customer_bp.route('/public/share/estimate/<token>/sign', methods=['POST'])
def sign_shared_estimate(token):
    """
    Record customer authorization via share link (public, no auth).

    This captures the customer's authorization to proceed with repairs.
    Note: This is separate from insurer approval.

    Body:
        name: str - Customer name (required)
        email: str - Customer email (optional)
        signature: str - Base64 PNG data URL (required)

    Returns:
        200: { success, signed_at, signed_by_name, customer_status }
        400: Already authorized or invalid data
        401: Token invalid/expired or no signing permission
    """
    from app.extensions import db
    from app.services.share_token_service import (
        verify_estimate_share_token,
        require_token_permission,
        TokenExpiredError,
        TokenInvalidError,
        TokenPermissionError
    )
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity
    import base64

    try:
        payload = verify_estimate_share_token(token)
        require_token_permission(payload, 'signing')
    except TokenExpiredError:
        return jsonify({'error': 'This share link has expired', 'expired': True}), 401
    except TokenInvalidError as e:
        return jsonify({'error': str(e), 'invalid': True}), 401
    except TokenPermissionError as e:
        return jsonify({'error': str(e), 'no_signing_permission': True}), 401

    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    signature_data_url = data.get('signature')

    if not name:
        return jsonify({'error': 'Customer name is required'}), 400
    if not signature_data_url:
        return jsonify({'error': 'Signature is required'}), 400

    estimate_id = payload.estimate_id

    try:
        estimate = PDREstimate.query.get(estimate_id)
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Check if already authorized
        if estimate.is_customer_authorized():
            return jsonify({
                'error': 'Customer has already authorized this estimate',
                'already_authorized': True,
                'signed_by_name': estimate.signed_by_name,
                'signed_at': estimate.signed_at.isoformat() if estimate.signed_at else None
            }), 400

        # Parse data URL and extract PNG bytes
        if ';base64,' in signature_data_url:
            sig_data = signature_data_url.split(';base64,')[1]
        else:
            sig_data = signature_data_url
        signature_bytes = base64.b64decode(sig_data)

        # Record customer authorization
        meta = {
            'method': 'portal',
            'token_created_by': payload.created_by,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        }
        estimate.mark_customer_authorized(name=name, signature_bytes=signature_bytes, email=email, meta=meta)
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='customer_authorized',
            user_id=None,  # Public
            activity_data={
                'signed_by_name': name,
                'signed_by_email': email,
                'method': 'portal',
                'ip': request.remote_addr
            }
        )

        return jsonify({
            'success': True,
            'signed_at': estimate.signed_at.isoformat(),
            'signed_by_name': estimate.signed_by_name,
            'customer_status': estimate.customer_status,
            # Legacy field
            'approval_status': estimate.approval_status
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to record customer authorization: {str(e)}'}), 500


# ==============================================================================
# JOB ENDPOINTS (ESTIMATE-LINKED)
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/job', methods=['GET'])
@login_required
def get_estimate_job(estimate_id):
    """
    Get the job linked to an estimate.

    Returns:
        200: { job: {...} }
        404: No job exists for this estimate
    """
    from app.models.tenant.job import Job
    from app.models.tenant.pdr_estimate import PDREstimate

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    # Verify estimate exists and belongs to tenant
    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    # Find linked job
    job = Job.query.filter_by(estimate_id=estimate_id, tenant_id=tenant_id).first()
    if not job:
        return jsonify({'error': 'No job exists for this estimate', 'has_job': False}), 404

    return jsonify({
        'job': job.to_dict(include_estimate=False),
        'has_job': True
    })


@customer_bp.route('/pdr-estimates/<int:estimate_id>/job', methods=['POST'])
@login_required
def create_job_from_estimate(estimate_id):
    """
    Create a job from an approved estimate.

    Requires insurer_status = 'approved' on the estimate.

    Body (optional):
        scheduled_date: str - ISO date for scheduling
        assigned_tech: int - User ID of assigned tech
        notes: str - Job notes

    Returns:
        201: { job: {...}, message: "..." }
        400: Estimate not approved or job already exists
        404: Estimate not found
    """
    from app.extensions import db
    from app.models.tenant.job import Job
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity
    from datetime import datetime

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}

    try:
        # Verify estimate exists and belongs to tenant
        estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Check if insurer has approved
        if not estimate.is_insurer_approved():
            return jsonify({
                'error': 'Cannot create job - estimate must be approved by insurer first',
                'insurer_status': estimate.insurer_status,
                'requires_approval': True
            }), 400

        # Check if job already exists
        existing_job = Job.query.filter_by(estimate_id=estimate_id, tenant_id=tenant_id).first()
        if existing_job:
            return jsonify({
                'error': 'Job already exists for this estimate',
                'job_id': existing_job.id,
                'job_number': existing_job.job_number,
                'already_exists': True
            }), 400

        # Parse optional fields
        scheduled_date = None
        if data.get('scheduled_date'):
            try:
                scheduled_date = datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00')).date()
            except:
                scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date()

        assigned_tech = data.get('assigned_tech')
        notes = data.get('notes')

        # Create job from estimate
        job = Job.create_from_estimate(
            estimate=estimate,
            user_id=user_id,
            scheduled_date=scheduled_date,
            assigned_tech=assigned_tech,
            notes=notes
        )

        db.session.add(job)
        db.session.flush()  # Get ID for job number

        # Generate job number
        job.generate_job_number()
        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='job_created_from_estimate',
            user_id=user_id,
            activity_data={
                'job_id': job.id,
                'job_number': job.job_number,
                'scheduled_date': scheduled_date.isoformat() if scheduled_date else None,
                'assigned_tech': assigned_tech
            }
        )

        return jsonify({
            'job': job.to_dict(include_estimate=True),
            'message': f'Job {job.job_number} created successfully'
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create job: {str(e)}'}), 500


@customer_bp.route('/jobs', methods=['GET'])
@login_required
def list_jobs():
    """
    List jobs for the tenant.

    Query params:
        status: Filter by status
        assigned_tech: Filter by assigned tech
        limit: Max results (default 50)

    Returns:
        200: { jobs: [...], count: N }
    """
    from app.models.tenant.job import Job

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    status = request.args.get('status')
    assigned_tech = request.args.get('assigned_tech', type=int)
    limit = request.args.get('limit', 50, type=int)

    query = Job.query.filter_by(tenant_id=tenant_id)

    if status:
        query = query.filter_by(status=status)
    if assigned_tech:
        query = query.filter_by(assigned_tech=assigned_tech)

    jobs = query.order_by(Job.created_at.desc()).limit(limit).all()

    return jsonify({
        'jobs': [j.to_dict(include_estimate=True) for j in jobs],
        'count': len(jobs)
    })


@customer_bp.route('/jobs/<int:job_id>', methods=['GET'])
@login_required
def get_job(job_id):
    """
    Get a job by ID.

    Returns:
        200: { job: {...} }
        404: Job not found
    """
    from app.models.tenant.job import Job

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    job = Job.query.filter_by(id=job_id, tenant_id=tenant_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'job': job.to_dict(include_estimate=True)
    })


@customer_bp.route('/jobs/<int:job_id>', methods=['PUT', 'PATCH'])
@login_required
def update_job(job_id):
    """
    Update a job's scheduling and status.

    Body:
        scheduled_date: str - ISO date
        scheduled_time: str - Time in HH:MM format
        assigned_tech: int - User ID
        estimated_hours: float
        notes: str
        status: str - scheduled, in_progress, completed, cancelled

    Returns:
        200: { job: {...} }
        400: Invalid status transition
        404: Job not found
    """
    from app.extensions import db
    from app.models.tenant.job import Job
    from app.models.tenant.estimate_activity import EstimateActivity
    from datetime import datetime, time

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}

    try:
        job = Job.query.filter_by(id=job_id, tenant_id=tenant_id).first()
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        old_status = job.status

        # Update scheduling fields
        if 'scheduled_date' in data:
            if data['scheduled_date']:
                try:
                    job.scheduled_date = datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00')).date()
                except:
                    job.scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date()
            else:
                job.scheduled_date = None

        if 'scheduled_time' in data:
            if data['scheduled_time']:
                try:
                    parts = data['scheduled_time'].split(':')
                    job.scheduled_time = time(int(parts[0]), int(parts[1]))
                except:
                    pass
            else:
                job.scheduled_time = None

        if 'assigned_tech' in data:
            job.assigned_tech = data['assigned_tech']

        if 'estimated_hours' in data:
            job.estimated_hours = data['estimated_hours']

        if 'notes' in data:
            job.notes = data['notes']

        # Handle status changes
        if 'status' in data and data['status'] != old_status:
            new_status = data['status']

            if new_status not in Job.STATUSES:
                return jsonify({'error': f'Invalid status: {new_status}'}), 400

            # Validate transitions
            if new_status == Job.STATUS_IN_PROGRESS and old_status != Job.STATUS_SCHEDULED:
                return jsonify({'error': 'Can only start a scheduled job'}), 400

            if new_status == Job.STATUS_COMPLETED and old_status != Job.STATUS_IN_PROGRESS:
                return jsonify({'error': 'Can only complete an in-progress job'}), 400

            job.status = new_status

            # Set completed date if completing
            if new_status == Job.STATUS_COMPLETED:
                job.completed_date = datetime.utcnow().date()

            # Log status change if job has estimate
            if job.estimate_id:
                EstimateActivity.log(
                    estimate_id=job.estimate_id,
                    activity_type='job_status_changed',
                    user_id=user_id,
                    activity_data={
                        'job_id': job.id,
                        'job_number': job.job_number,
                        'from_status': old_status,
                        'to_status': new_status
                    }
                )

        db.session.commit()

        return jsonify({
            'job': job.to_dict(include_estimate=True),
            'status_changed': old_status != job.status
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update job: {str(e)}'}), 500


# ==============================================================================
# INVOICE ENDPOINTS
# ==============================================================================

@customer_bp.route('/invoices', methods=['GET'])
@login_required
def list_invoices():
    """
    List invoices for the tenant.

    Query params:
        status: Filter by status (draft, issued, partial_paid, paid, void)
        payer_type: Filter by payer type
        search: Search by invoice_number, customer name, or vehicle
        limit: Max results (default 50)

    Returns:
        200: { invoices: [...], count: N }
    """
    from app.models.tenant.invoice import Invoice

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    status = request.args.get('status')
    payer_type = request.args.get('payer_type')
    search = request.args.get('search')
    limit = request.args.get('limit', 50, type=int)

    query = Invoice.query.filter_by(tenant_id=tenant_id)

    if status:
        query = query.filter_by(status=status)
    if payer_type:
        query = query.filter_by(payer_type=payer_type)
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Invoice.invoice_number.ilike(search_term),
                Invoice.payer_name.ilike(search_term)
            )
        )

    invoices = query.order_by(Invoice.created_at.desc()).limit(limit).all()

    return jsonify({
        'invoices': [inv.to_dict(include_estimate=True) for inv in invoices],
        'count': len(invoices)
    })


@customer_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@login_required
def get_invoice(invoice_id):
    """
    Get an invoice by ID with line items and payments.

    Returns:
        200: { invoice: {...} }
        404: Invoice not found
    """
    from app.models.tenant.invoice import Invoice

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    return jsonify({
        'invoice': invoice.to_dict(include_items=True, include_payments=True, include_estimate=True)
    })


@customer_bp.route('/pdr-estimates/<int:estimate_id>/invoice', methods=['POST'])
@login_required
def create_invoice_from_estimate(estimate_id):
    """
    Create an invoice from an approved estimate.

    Requires either:
    - insurer_status = 'approved', OR
    - linked job with status = 'completed'

    Body (optional):
        payer_type: str - customer, insurer, dealership, other (default: insurer)
        notes: str

    Returns:
        201: { invoice: {...}, message: "..." }
        400: Not approved/completed or invoice already exists
        404: Estimate not found
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.invoice import Invoice, InvoiceLineItem
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.tenant.job import Job
    from decimal import Decimal

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    payer_type = data.get('payer_type', 'insurer')
    notes = data.get('notes')

    try:
        # Verify estimate exists and belongs to tenant
        estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        # Check eligibility: insurer approved OR job completed
        job = Job.query.filter_by(estimate_id=estimate_id, tenant_id=tenant_id).first()
        job_completed = job and job.status == Job.STATUS_COMPLETED
        insurer_approved = estimate.is_insurer_approved()

        if not insurer_approved and not job_completed:
            return jsonify({
                'error': 'Cannot create invoice - estimate must be approved by insurer or job must be completed',
                'insurer_status': estimate.insurer_status,
                'job_status': job.status if job else None,
                'requires_approval': True
            }), 400

        # Check if invoice already exists for this estimate
        existing_invoice = Invoice.query.filter_by(
            estimate_id=estimate_id,
            tenant_id=tenant_id
        ).filter(Invoice.status != Invoice.STATUS_VOID).first()

        if existing_invoice:
            return jsonify({
                'error': 'An active invoice already exists for this estimate',
                'invoice_id': existing_invoice.id,
                'invoice_number': existing_invoice.invoice_number,
                'already_exists': True
            }), 400

        # Create invoice
        invoice = Invoice.create_from_estimate(
            estimate=estimate,
            user_id=user_id,
            job_id=job.id if job else None,
            payer_type=payer_type
        )
        invoice.notes = notes

        db.session.add(invoice)
        db.session.flush()  # Get ID for invoice number

        # Generate invoice number
        invoice.generate_invoice_number()

        # Create line items from estimate
        # Use insurer_approved_total if available, otherwise use estimate totals
        use_approved = estimate.insurer_approved_total is not None

        # PDR Labor line item
        labor_amount = estimate.insurer_approved_labor if use_approved and estimate.insurer_approved_labor else estimate.labor_total
        if labor_amount and float(labor_amount) > 0:
            labor_item = InvoiceLineItem(
                invoice_id=invoice.id,
                category='pdr',
                description='PDR Labor - Hail Damage Repair',
                quantity=1,
                unit_price=labor_amount,
                total=labor_amount
            )
            db.session.add(labor_item)

        # R&I line item
        ri_amount = estimate.insurer_approved_ri if use_approved and estimate.insurer_approved_ri else estimate.ri_total
        if ri_amount and float(ri_amount) > 0:
            ri_item = InvoiceLineItem(
                invoice_id=invoice.id,
                category='ri',
                description='Remove & Install Operations',
                quantity=1,
                unit_price=ri_amount,
                total=ri_amount
            )
            db.session.add(ri_item)

        # Materials line item (if any)
        materials_amount = estimate.insurer_approved_materials if use_approved and estimate.insurer_approved_materials else estimate.parts_total
        if materials_amount and float(materials_amount) > 0:
            materials_item = InvoiceLineItem(
                invoice_id=invoice.id,
                category='materials',
                description='Materials & Supplies',
                quantity=1,
                unit_price=materials_amount,
                total=materials_amount
            )
            db.session.add(materials_item)

        db.session.flush()

        # Recalculate invoice totals
        invoice.recalculate_totals()

        # If using approved amounts, override total
        if use_approved and estimate.insurer_approved_total:
            invoice.total = estimate.insurer_approved_total

        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='invoice_created',
            user_id=user_id,
            activity_data={
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total': float(invoice.total),
                'payer_type': payer_type
            }
        )

        return jsonify({
            'invoice': invoice.to_dict(include_items=True, include_estimate=True),
            'message': f'Invoice {invoice.invoice_number} created successfully'
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create invoice: {str(e)}'}), 500


# ============================================================================
# SPLIT BILLING ENDPOINTS (Deductible + Insurer Allocation)
# ============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/billing', methods=['PATCH'])
@login_required
def update_estimate_billing(estimate_id):
    """
    Update billing/deductible fields on an estimate.

    Body:
        deductible: number - Customer deductible amount
        customer_oop: number - Additional out-of-pocket amount

    Returns:
        200: { estimate: {...}, billing_summary: {...} }
        404: Estimate not found
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.estimate_activity import EstimateActivity
    from decimal import Decimal

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}

    try:
        estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        changed = False
        old_deductible = float(estimate.deductible) if estimate.deductible else 0
        old_oop = float(estimate.customer_oop) if estimate.customer_oop else 0

        if 'deductible' in data:
            deductible = data['deductible']
            if deductible is not None and deductible >= 0:
                estimate.deductible = Decimal(str(deductible))
                changed = True

        if 'customer_oop' in data:
            oop = data['customer_oop']
            if oop is not None and oop >= 0:
                estimate.customer_oop = Decimal(str(oop))
                changed = True

        if changed:
            db.session.commit()

            # Log activity
            EstimateActivity.log(
                estimate_id=estimate_id,
                activity_type='billing_updated',
                user_id=user_id,
                activity_data={
                    'deductible': float(estimate.deductible) if estimate.deductible else 0,
                    'customer_oop': float(estimate.customer_oop) if estimate.customer_oop else 0,
                    'old_deductible': old_deductible,
                    'old_oop': old_oop
                }
            )

        return jsonify({
            'estimate': estimate.to_dict(),
            'billing_summary': estimate.get_billing_summary(),
            'message': 'Billing updated successfully' if changed else 'No changes made'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update billing: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/invoices/insurer', methods=['POST'])
@login_required
def create_insurer_invoice(estimate_id):
    """
    Create an insurer invoice from an approved estimate.

    Total = insurer_approved_total - deductible

    Requires:
        - insurer_status = 'approved'
        - No active insurer invoice exists

    Body (optional):
        notes: str

    Returns:
        201: { invoice: {...}, billing_summary: {...} }
        400: Not approved or invoice exists
        404: Estimate not found
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.invoice import Invoice, InvoiceLineItem
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.tenant.job import Job

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    notes = data.get('notes')

    try:
        estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        if not estimate.is_insurer_approved():
            return jsonify({
                'error': 'Estimate must be approved by insurer to create insurer invoice',
                'insurer_status': estimate.insurer_status
            }), 400

        # Check for existing active insurer invoice
        existing = Invoice.query.filter_by(
            estimate_id=estimate_id,
            tenant_id=tenant_id,
            allocation_type=Invoice.ALLOCATION_INSURER
        ).filter(Invoice.status != Invoice.STATUS_VOID).first()

        if existing:
            return jsonify({
                'error': 'An active insurer invoice already exists for this estimate',
                'invoice_id': existing.id,
                'invoice_number': existing.invoice_number
            }), 400

        # Get job if linked
        job = Job.query.filter_by(estimate_id=estimate_id, tenant_id=tenant_id).first()

        # Create insurer invoice
        invoice = Invoice.create_insurer_invoice(
            estimate=estimate,
            user_id=user_id,
            job_id=job.id if job else None
        )
        invoice.notes = notes

        db.session.add(invoice)
        db.session.flush()

        # Generate invoice number
        invoice.generate_invoice_number()

        # Create single line item for insurer portion
        insurer_amount = estimate.get_insurer_invoice_suggested_total()
        if insurer_amount > 0:
            line_item = InvoiceLineItem(
                invoice_id=invoice.id,
                category='pdr',
                description='Hail Damage Repair - Insurance Portion',
                quantity=1,
                unit_price=insurer_amount,
                total=insurer_amount
            )
            db.session.add(line_item)

        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='invoice_created_insurer',
            user_id=user_id,
            activity_data={
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total': float(invoice.total),
                'allocation_type': 'insurer'
            }
        )

        return jsonify({
            'invoice': invoice.to_dict(include_items=True, include_estimate=True),
            'billing_summary': estimate.get_billing_summary(),
            'message': f'Insurer invoice {invoice.invoice_number} created successfully'
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create insurer invoice: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/invoices/customer', methods=['POST'])
@login_required
def create_customer_deductible_invoice(estimate_id):
    """
    Create a customer invoice for deductible + OOP from an estimate.

    Total = deductible + customer_oop

    Requires:
        - deductible > 0 OR customer_oop > 0
        - No active customer deductible invoice exists

    Body (optional):
        notes: str
        include_oop: bool (default true)

    Returns:
        201: { invoice: {...}, billing_summary: {...} }
        400: No deductible/OOP or invoice exists
        404: Estimate not found
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.invoice import Invoice, InvoiceLineItem
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.tenant.job import Job

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    notes = data.get('notes')
    include_oop = data.get('include_oop', True)

    try:
        estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        deductible = estimate.get_deductible_amount()
        oop = estimate.get_customer_oop_amount() if include_oop else 0
        customer_total = deductible + oop

        if customer_total <= 0:
            return jsonify({
                'error': 'No customer amount to invoice (deductible and OOP are zero)',
                'deductible': deductible,
                'customer_oop': oop
            }), 400

        # Check for existing active customer deductible invoice
        existing = Invoice.query.filter_by(
            estimate_id=estimate_id,
            tenant_id=tenant_id,
            allocation_type=Invoice.ALLOCATION_CUSTOMER_DEDUCTIBLE
        ).filter(Invoice.status != Invoice.STATUS_VOID).first()

        if existing:
            return jsonify({
                'error': 'An active customer deductible invoice already exists for this estimate',
                'invoice_id': existing.id,
                'invoice_number': existing.invoice_number
            }), 400

        # Get job if linked
        job = Job.query.filter_by(estimate_id=estimate_id, tenant_id=tenant_id).first()

        # Create customer invoice
        invoice = Invoice.create_customer_invoice(
            estimate=estimate,
            user_id=user_id,
            job_id=job.id if job else None,
            include_oop=include_oop
        )
        invoice.notes = notes

        db.session.add(invoice)
        db.session.flush()

        # Generate invoice number
        invoice.generate_invoice_number()

        # Create line items
        if deductible > 0:
            deductible_item = InvoiceLineItem(
                invoice_id=invoice.id,
                category='other',
                description='Customer Deductible',
                quantity=1,
                unit_price=deductible,
                total=deductible
            )
            db.session.add(deductible_item)

        if include_oop and oop > 0:
            oop_item = InvoiceLineItem(
                invoice_id=invoice.id,
                category='other',
                description='Customer Out-of-Pocket',
                quantity=1,
                unit_price=oop,
                total=oop
            )
            db.session.add(oop_item)

        db.session.commit()

        # Log activity
        EstimateActivity.log(
            estimate_id=estimate_id,
            activity_type='invoice_created_customer',
            user_id=user_id,
            activity_data={
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total': float(invoice.total),
                'deductible': deductible,
                'customer_oop': oop if include_oop else 0,
                'allocation_type': 'customer_deductible'
            }
        )

        return jsonify({
            'invoice': invoice.to_dict(include_items=True, include_estimate=True),
            'billing_summary': estimate.get_billing_summary(),
            'message': f'Customer invoice {invoice.invoice_number} created successfully'
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create customer invoice: {str(e)}'}), 500


@customer_bp.route('/pdr-estimates/<int:estimate_id>/invoices', methods=['GET'])
@login_required
def get_estimate_invoices(estimate_id):
    """
    Get all invoices for an estimate with billing summary.

    Returns:
        200: { invoices: [...], billing_summary: {...}, totals: {...} }
        404: Estimate not found
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.invoice import Invoice

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    try:
        estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
        if not estimate:
            return jsonify({'error': 'Estimate not found'}), 404

        invoices = Invoice.query.filter_by(
            estimate_id=estimate_id,
            tenant_id=tenant_id
        ).order_by(Invoice.created_at.desc()).all()

        # Calculate totals across all invoices
        total_invoiced = sum(float(inv.total) for inv in invoices if inv.status != Invoice.STATUS_VOID)
        total_paid = sum(float(inv.amount_paid) for inv in invoices if inv.status != Invoice.STATUS_VOID)
        total_balance = sum(float(inv.balance_due) for inv in invoices if inv.status != Invoice.STATUS_VOID)

        # Check which invoice types exist
        has_insurer_invoice = any(inv.allocation_type == Invoice.ALLOCATION_INSURER and inv.status != Invoice.STATUS_VOID for inv in invoices)
        has_customer_invoice = any(inv.allocation_type == Invoice.ALLOCATION_CUSTOMER_DEDUCTIBLE and inv.status != Invoice.STATUS_VOID for inv in invoices)

        return jsonify({
            'invoices': [inv.to_dict(include_items=True) for inv in invoices],
            'billing_summary': estimate.get_billing_summary(),
            'totals': {
                'total_invoiced': total_invoiced,
                'total_paid': total_paid,
                'total_balance': total_balance
            },
            'has_insurer_invoice': has_insurer_invoice,
            'has_customer_invoice': has_customer_invoice
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to get invoices: {str(e)}'}), 500


@customer_bp.route('/invoices/<int:invoice_id>/issue', methods=['POST'])
@login_required
def issue_invoice(invoice_id):
    """
    Issue a draft invoice.

    Returns:
        200: { invoice: {...} }
        400: Cannot issue (not draft)
        404: Invoice not found
    """
    from app.extensions import db
    from app.models.tenant.invoice import Invoice
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    try:
        invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404

        if not invoice.can_issue():
            return jsonify({
                'error': f'Cannot issue invoice with status: {invoice.status}',
                'current_status': invoice.status
            }), 400

        invoice.issue()
        db.session.commit()

        # Log activity
        if invoice.estimate_id:
            EstimateActivity.log(
                estimate_id=invoice.estimate_id,
                activity_type='invoice_issued',
                user_id=user_id,
                activity_data={
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'total': float(invoice.total)
                }
            )

        return jsonify({
            'invoice': invoice.to_dict(include_items=True, include_payments=True),
            'message': 'Invoice issued successfully'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to issue invoice: {str(e)}'}), 500


@customer_bp.route('/invoices/<int:invoice_id>/void', methods=['POST'])
@login_required
def void_invoice(invoice_id):
    """
    Void an invoice.

    Returns:
        200: { invoice: {...} }
        400: Cannot void (already paid or void)
        404: Invoice not found
    """
    from app.extensions import db
    from app.models.tenant.invoice import Invoice
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}
    reason = data.get('reason')

    try:
        invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404

        if not invoice.can_void():
            return jsonify({
                'error': f'Cannot void invoice with status: {invoice.status}',
                'current_status': invoice.status
            }), 400

        invoice.void()
        db.session.commit()

        # Log activity
        if invoice.estimate_id:
            EstimateActivity.log(
                estimate_id=invoice.estimate_id,
                activity_type='invoice_voided',
                user_id=user_id,
                activity_data={
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'reason': reason
                }
            )

        return jsonify({
            'invoice': invoice.to_dict(),
            'message': 'Invoice voided successfully'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to void invoice: {str(e)}'}), 500


@customer_bp.route('/invoices/<int:invoice_id>/payments', methods=['GET'])
@login_required
def list_invoice_payments(invoice_id):
    """
    List payments for an invoice.

    Returns:
        200: { payments: [...], total_paid: N }
        404: Invoice not found
    """
    from app.models.tenant.invoice import Invoice

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    payments = [p.to_dict() for p in invoice.payments.order_by('received_at')]

    return jsonify({
        'payments': payments,
        'total_paid': float(invoice.amount_paid) if invoice.amount_paid else 0,
        'balance_due': float(invoice.balance_due)
    })


@customer_bp.route('/invoices/<int:invoice_id>/payments', methods=['POST'])
@login_required
def add_payment(invoice_id):
    """
    Add a payment to an invoice.

    Body:
        amount: float (required)
        method: str - cash, card, check, ach, other (default: check)
        reference: str (optional) - check number, transaction ID
        received_at: str (optional) - ISO datetime, defaults to now
        notes: str (optional)

    Returns:
        201: { payment: {...}, invoice: {...} }
        400: Invalid amount or cannot accept payment
        404: Invoice not found
    """
    from app.extensions import db
    from app.models.tenant.invoice import Invoice, Payment
    from app.models.tenant.estimate_activity import EstimateActivity
    from datetime import datetime

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    data = request.get_json() or {}

    # Validate required fields
    amount = data.get('amount')
    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400

    method = data.get('method', 'check')
    reference = data.get('reference')
    notes = data.get('notes')

    # Parse received_at
    received_at = datetime.utcnow()
    if data.get('received_at'):
        try:
            received_at = datetime.fromisoformat(data['received_at'].replace('Z', '+00:00'))
        except:
            pass

    try:
        invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404

        if not invoice.can_accept_payment():
            return jsonify({
                'error': f'Cannot accept payment for invoice with status: {invoice.status}',
                'current_status': invoice.status
            }), 400

        # Create payment
        payment = Payment(
            invoice_id=invoice.id,
            amount=amount,
            method=method,
            reference=reference,
            received_at=received_at,
            notes=notes,
            created_by=user_id
        )

        db.session.add(payment)
        db.session.flush()

        # Recalculate invoice payment status
        invoice.recalculate_payment_status()
        db.session.commit()

        # Log activity
        if invoice.estimate_id:
            EstimateActivity.log(
                estimate_id=invoice.estimate_id,
                activity_type='payment_recorded',
                user_id=user_id,
                activity_data={
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'payment_id': payment.id,
                    'amount': amount,
                    'method': method,
                    'reference': reference,
                    'new_status': invoice.status,
                    'balance_due': float(invoice.balance_due)
                }
            )

        return jsonify({
            'payment': payment.to_dict(),
            'invoice': invoice.to_dict(include_payments=True),
            'message': f'Payment of ${amount:.2f} recorded successfully'
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to record payment: {str(e)}'}), 500


@customer_bp.route('/invoices/<int:invoice_id>', methods=['PUT', 'PATCH'])
@login_required
def update_invoice(invoice_id):
    """
    Update an invoice (only draft invoices can be edited).

    Body:
        payer_type: str
        payer_name: str
        due_at: str - ISO date
        notes: str
        tax_rate: float

    Returns:
        200: { invoice: {...} }
        400: Cannot edit (not draft)
        404: Invoice not found
    """
    from app.extensions import db
    from app.models.tenant.invoice import Invoice
    from datetime import datetime

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    data = request.get_json() or {}

    try:
        invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404

        if invoice.status != Invoice.STATUS_DRAFT:
            return jsonify({
                'error': 'Only draft invoices can be edited',
                'current_status': invoice.status
            }), 400

        # Update fields
        if 'payer_type' in data:
            invoice.payer_type = data['payer_type']
        if 'payer_name' in data:
            invoice.payer_name = data['payer_name']
        if 'notes' in data:
            invoice.notes = data['notes']
        if 'due_at' in data:
            if data['due_at']:
                try:
                    invoice.due_at = datetime.fromisoformat(data['due_at'].replace('Z', '+00:00'))
                except:
                    invoice.due_at = datetime.strptime(data['due_at'], '%Y-%m-%d')
            else:
                invoice.due_at = None
        if 'tax_rate' in data:
            invoice.tax_rate = data['tax_rate']
            invoice.recalculate_totals()

        db.session.commit()

        return jsonify({
            'invoice': invoice.to_dict(include_items=True)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update invoice: {str(e)}'}), 500


# ==============================================================================
# WORKFLOW ENDPOINTS
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/workflow', methods=['GET'])
@login_required
def get_estimate_workflow(estimate_id):
    """
    Get workflow state and next actions for an estimate.

    Returns:
        200: { state, next_actions, primary_action, estimate_id, estimate_number }
        404: Estimate not found
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.services.workflow_service import WorkflowService

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    service = WorkflowService(estimate)
    workflow = service.get_workflow()

    return jsonify(workflow)


@customer_bp.route('/jobs/<int:job_id>/workflow', methods=['GET'])
@login_required
def get_job_workflow(job_id):
    """
    Get workflow state and next actions for a job (via its linked estimate).

    Returns:
        200: { state, next_actions, primary_action, estimate_id, estimate_number, job_id }
        404: Job or linked estimate not found
    """
    from app.models.tenant.job import Job
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.services.workflow_service import WorkflowService

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    job = Job.query.filter_by(id=job_id, tenant_id=tenant_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Get linked estimate
    estimate_id = job.estimate_id
    if not estimate_id:
        return jsonify({
            'state': {
                'job_status': job.status,
                'job_id': job.id,
            },
            'next_actions': [],
            'primary_action': None,
            'job_id': job.id,
            'message': 'Job has no linked estimate'
        })

    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Linked estimate not found'}), 404

    service = WorkflowService(estimate)
    workflow = service.get_workflow()
    workflow['job_id'] = job.id
    workflow['job_number'] = job.job_number

    return jsonify(workflow)


@customer_bp.route('/jobs/<int:job_id>/flag-issue', methods=['POST'])
@login_required
def flag_job_issue(job_id):
    """
    Flag a job issue (blocker/needs help) from tech portal.

    Uses existing EstimateActivity model to log blocker with metadata.
    No new models required.

    Permission: Tech can only flag jobs assigned to them, OR dispatch roles (owner/manager/desk).

    Request body:
        {
            "issue_type": "waiting_on_parts" | "needs_tools" | "customer_no_show" | "access_problem" | "other",
            "notes": "optional description",
            "parts_ordered": boolean (optional, for waiting_on_parts),
            "vendor": string (optional),
            "po_number": string (optional),
            "eta": string ISO datetime or date (optional),
            "parts_status": string (optional, Stage 5P - one of: needed|approved_to_order|ordered|shipped|received|installed|exception),
            "approved_to_order": boolean (optional, Stage 5P),
            "approved_amount": number (optional, Stage 5P),
            "parts_notes": string (optional, Stage 5P)
        }

    Returns:
        200: { success: true, message: "Issue flagged" }
        403: Permission denied (not assigned to job and not dispatch role)
        404: Job not found

    Test cases (Stage 5O.1):
        - blocked -> updated -> cleared => not blocked
        - tech cannot flag-issue on job not assigned to them (403)
        - dispatch roles CAN flag-issue on any job
    """
    from app.models.tenant.job import Job
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']
    user_role = identity.get('role', '')

    # TENANT SAFETY: Filter by tenant_id
    job = Job.query.filter_by(id=job_id, tenant_id=tenant_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # PERMISSION CHECK: Tech can only flag jobs assigned to them, dispatch can flag any
    is_dispatch_role = user_role in ['owner', 'manager', 'desk', 'admin']
    is_assigned_to_job = job.assigned_tech == user_id

    if not is_dispatch_role and not is_assigned_to_job:
        return jsonify({
            'error': 'Permission denied',
            'message': f'Technicians can only flag issues on jobs assigned to them. Your role: {user_role}',
        }), 403

    data = request.get_json() or {}
    issue_type = data.get('issue_type', 'other')
    notes = data.get('notes', '')

    valid_issue_types = ['waiting_on_parts', 'needs_tools', 'customer_no_show', 'access_problem', 'other']
    if issue_type not in valid_issue_types:
        issue_type = 'other'

    # Build parts metadata for waiting_on_parts with ETA normalization (Stage 5P extended)
    parts_data = None
    if issue_type == 'waiting_on_parts':
        from app.services.blocker_helpers import PARTS_STATUS_VALUES
        raw_eta = data.get('eta')
        raw_status = data.get('parts_status', 'needed')
        # Validate parts_status
        if raw_status not in PARTS_STATUS_VALUES:
            raw_status = 'needed'
        # Parse approved_amount as float if provided
        approved_amount = None
        if data.get('approved_amount'):
            try:
                approved_amount = float(data.get('approved_amount'))
            except (ValueError, TypeError):
                pass
        parts_data = {
            'ordered': bool(data.get('parts_ordered', False)),
            'vendor': data.get('vendor') or None,
            'po_number': data.get('po_number') or None,
            'eta': normalize_eta(raw_eta),  # Normalize to ISO datetime
            # Stage 5P fields
            'parts_status': raw_status,
            'approved_to_order': bool(data.get('approved_to_order', False)),
            'approved_amount': approved_amount,
            'parts_notes': data.get('parts_notes') or None,
        }

    # Log activity using EstimateActivity if job has linked estimate
    if job.estimate_id:
        metadata = {
            'job_id': job.id,
            'job_number': job.job_number,
            'issue_type': issue_type,
            'notes': notes,
            'flagged_at': datetime.utcnow().isoformat(),
        }
        if parts_data:
            metadata['parts'] = parts_data

        EstimateActivity.log(
            estimate_id=job.estimate_id,
            activity_type='job_blocked',
            user_id=user_id,
            metadata=metadata
        )

    # Also append to job notes for visibility
    blocker_note = f"[BLOCKED - {issue_type.replace('_', ' ').title()}] {notes}".strip()
    if parts_data and parts_data.get('vendor'):
        blocker_note += f" (Vendor: {parts_data['vendor']})"
    if parts_data and parts_data.get('eta'):
        blocker_note += f" (ETA: {parts_data['eta']})"
    if job.notes:
        job.notes = f"{job.notes}\n\n{blocker_note}"
    else:
        job.notes = blocker_note

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Issue flagged successfully',
        'issue_type': issue_type,
    })


@customer_bp.route('/jobs/<int:job_id>/update-blocker', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def update_job_blocker(job_id):
    """
    Update a job blocker (dispatch role only) - e.g., set ETA, mark parts ordered.

    Does NOT change job.status, only updates blocker metadata via EstimateActivity.
    Logs 'job_blocker_updated' activity.

    Permission: Dispatch roles only (owner/manager/desk). Returns 403 for tech/sales.

    Request body:
        {
            "parts_ordered": boolean (optional),
            "vendor": string (optional),
            "po_number": string (optional),
            "eta": string ISO datetime or date (optional, normalized to ISO datetime),
            "notes": string (optional),
            "parts_status": string (optional, Stage 5P - one of: needed|approved_to_order|ordered|shipped|received|installed|exception),
            "approved_to_order": boolean (optional, Stage 5P),
            "approved_amount": number (optional, Stage 5P),
            "parts_notes": string (optional, Stage 5P)
        }

    Returns:
        200: { success: true, message: "Blocker updated", parts: {...} }
        403: Permission denied (tech cannot update blocker)
        404: Job not found

    Test cases (Stage 5O.1):
        - eta "2024-03-15" => stored as "2024-03-15T17:00:00"
        - eta "2024-03-15T14:30:00" => stored as-is
        - tech cannot update-blocker (403)
    """
    from app.models.tenant.job import Job
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # TENANT SAFETY: Filter by tenant_id
    job = Job.query.filter_by(id=job_id, tenant_id=tenant_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    data = request.get_json() or {}
    notes = data.get('notes', '')

    # Build parts metadata with ETA normalization (Stage 5P extended)
    from app.services.blocker_helpers import PARTS_STATUS_VALUES
    raw_eta = data.get('eta')
    raw_status = data.get('parts_status')
    # Validate parts_status if provided
    if raw_status and raw_status not in PARTS_STATUS_VALUES:
        raw_status = None  # Will inherit from current blocker
    # Parse approved_amount as float if provided
    approved_amount = None
    if data.get('approved_amount'):
        try:
            approved_amount = float(data.get('approved_amount'))
        except (ValueError, TypeError):
            pass
    parts_data = {
        'ordered': bool(data.get('parts_ordered', False)),
        'vendor': data.get('vendor') or None,
        'po_number': data.get('po_number') or None,
        'eta': normalize_eta(raw_eta),  # Normalize to ISO datetime
        # Stage 5P fields
        'parts_status': raw_status,
        'approved_to_order': bool(data.get('approved_to_order', False)),
        'approved_amount': approved_amount,
        'parts_notes': data.get('parts_notes') or None,
    }

    # Get current blocker to carry forward issue_type and merge existing parts fields
    current_issue_type = 'waiting_on_parts'
    if job.estimate_id:
        blocker_state = get_current_job_blocker(job.id, job.estimate_id, tenant_id)
        if blocker_state and blocker_state.get('blocker_info'):
            current_issue_type = blocker_state['blocker_info'].get('issue_type', 'waiting_on_parts')
            # Merge with existing parts data - only override if explicitly provided
            existing_parts = blocker_state['blocker_info'].get('parts') or {}
            if parts_data.get('parts_status') is None and existing_parts.get('parts_status'):
                parts_data['parts_status'] = existing_parts['parts_status']
            if parts_data.get('approved_amount') is None and existing_parts.get('approved_amount'):
                parts_data['approved_amount'] = existing_parts['approved_amount']
            # Default parts_status to 'needed' if still None
            if parts_data.get('parts_status') is None:
                parts_data['parts_status'] = 'needed'

    # Log activity if job has linked estimate
    if job.estimate_id:
        EstimateActivity.log(
            estimate_id=job.estimate_id,
            activity_type='job_blocker_updated',
            user_id=user_id,
            activity_data={
                'job_id': job.id,
                'job_number': job.job_number,
                'issue_type': current_issue_type,
                'notes': notes,
                'parts': parts_data,
                'updated_at': datetime.utcnow().isoformat(),
            }
        )

    # Append update to notes (Stage 5P: include parts_status)
    status_label = (parts_data.get('parts_status') or 'needed').replace('_', ' ').title()
    update_note = f"[BLOCKER UPDATE] Status: {status_label}"
    if parts_data.get('ordered'):
        update_note += ", Parts ordered"
    if parts_data.get('vendor'):
        update_note += f", Vendor: {parts_data['vendor']}"
    if parts_data.get('eta'):
        update_note += f", ETA: {parts_data['eta']}"
    if parts_data.get('approved_amount'):
        update_note += f", Approved: ${parts_data['approved_amount']:.2f}"
    if notes:
        update_note += f" - {notes}"
    if job.notes:
        job.notes = f"{job.notes}\n\n{update_note}"
    else:
        job.notes = update_note

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Blocker updated successfully',
        'parts': parts_data,
    })


@customer_bp.route('/jobs/<int:job_id>/clear-blocker', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def clear_job_blocker(job_id):
    """
    Clear a job blocker (dispatch role only).

    Logs a 'job_blocker_cleared' activity and optionally updates job notes.

    Permission: Dispatch roles only (owner/manager/desk). Returns 403 for tech/sales.

    Request body:
        {
            "notes": string (optional resolution notes),
            "cleared_reason": string (optional - e.g., "parts_arrived", "resolved", etc.)
        }

    Returns:
        200: { success: true, message: "Blocker cleared" }
        403: Permission denied (tech cannot clear blocker)
        404: Job not found

    Test cases (Stage 5O.1):
        - blocked -> updated -> cleared => get_current_job_blocker returns is_blocked=False
        - cleared resets priority score to non-blocked level
    """
    from app.models.tenant.job import Job
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    job = Job.query.filter_by(id=job_id, tenant_id=tenant_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    data = request.get_json() or {}
    resolution_notes = data.get('notes', '')
    cleared_reason = data.get('cleared_reason', 'resolved')

    # Log activity if job has linked estimate
    if job.estimate_id:
        EstimateActivity.log(
            estimate_id=job.estimate_id,
            activity_type='job_blocker_cleared',
            user_id=user_id,
            activity_data={
                'job_id': job.id,
                'job_number': job.job_number,
                'cleared_reason': cleared_reason,
                'resolution_notes': resolution_notes,
                'cleared_at': datetime.utcnow().isoformat(),
            }
        )

    # Append resolution to notes
    reason_display = cleared_reason.replace('_', ' ').title() if cleared_reason else 'Resolved'
    clear_note = f"[BLOCKER RESOLVED - {reason_display}]"
    if resolution_notes:
        clear_note += f" {resolution_notes}"
    if job.notes:
        job.notes = f"{job.notes}\n\n{clear_note}"
    else:
        job.notes = clear_note

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Blocker cleared successfully',
    })


# ==============================================================================
# PART REQUESTS ENDPOINTS (Stage 5Q)
# ==============================================================================

@customer_bp.route('/parts/requests', methods=['GET'])
@login_required
def list_part_requests():
    """
    List part requests with filtering.

    Query params:
        status: Filter by parts_status (comma-separated)
        job_id: Filter by job
        estimate_id: Filter by estimate
        assigned_tech: Filter by assigned tech (via job)
        overdue_eta: If 'true', only return requests with overdue ETA
        limit: Max results (default 100)

    Returns:
        { requests: [...], total: int, counts: { needed: int, ordered: int, ... } }
    """
    from app.models.tenant.part_request import PartRequest, PARTS_STATUS_VALUES
    from app.models.tenant.job import Job
    from app.models.master.user import User
    from sqlalchemy import func

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    # Base query with tenant safety
    query = PartRequest.query.filter(PartRequest.tenant_id == tenant_id)

    # Apply filters
    status_filter = request.args.get('status')
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',') if s.strip() in PARTS_STATUS_VALUES]
        if statuses:
            query = query.filter(PartRequest.parts_status.in_(statuses))

    job_id = request.args.get('job_id', type=int)
    if job_id:
        query = query.filter(PartRequest.job_id == job_id)

    estimate_id = request.args.get('estimate_id', type=int)
    if estimate_id:
        query = query.filter(PartRequest.estimate_id == estimate_id)

    assigned_tech = request.args.get('assigned_tech', type=int)
    if assigned_tech:
        # Join with jobs to filter by assigned tech
        query = query.join(Job, PartRequest.job_id == Job.id).filter(Job.assigned_tech == assigned_tech)

    overdue_only = request.args.get('overdue_eta') == 'true'
    if overdue_only:
        query = query.filter(
            PartRequest.eta.isnot(None),
            PartRequest.eta < datetime.utcnow()
        )

    # Get counts by status
    counts_query = PartRequest.query.filter(PartRequest.tenant_id == tenant_id)
    status_counts = db.session.query(
        PartRequest.parts_status,
        func.count(PartRequest.id)
    ).filter(
        PartRequest.tenant_id == tenant_id
    ).group_by(PartRequest.parts_status).all()
    counts = {s: 0 for s in PARTS_STATUS_VALUES}
    for status, count in status_counts:
        counts[status] = count

    # Limit and order
    limit = request.args.get('limit', 100, type=int)
    requests_list = query.order_by(PartRequest.updated_at.desc()).limit(limit).all()

    # Get job/estimate info for enrichment
    job_ids = list(set([r.job_id for r in requests_list if r.job_id]))
    jobs_by_id = {}
    techs_by_id = {}
    if job_ids:
        jobs = Job.query.filter(Job.id.in_(job_ids), Job.tenant_id == tenant_id).all()
        jobs_by_id = {j.id: j for j in jobs}
        tech_ids = list(set([j.assigned_tech for j in jobs if j.assigned_tech]))
        if tech_ids:
            techs = User.query.filter(User.id.in_(tech_ids), User.tenant_id == tenant_id).all()
            techs_by_id = {t.id: t.name for t in techs}

    # Stage 5S: Get pricing previews for all requests
    from app.services.parts_pricing_service import get_bulk_price_previews
    pricing_previews = get_bulk_price_previews(requests_list, tenant_id)

    # Build response with enriched data
    result = []
    for req in requests_list:
        item = req.to_dict()
        job = jobs_by_id.get(req.job_id)
        if job:
            item['job_number'] = job.job_number
            item['customer_name'] = job.customer_name
            item['vehicle_display'] = f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or 'No vehicle'
            item['tech_name'] = techs_by_id.get(job.assigned_tech)
        # Stage 5S: Add pricing preview
        item['pricing_preview'] = pricing_previews.get(req.id)
        result.append(item)

    return jsonify({
        'requests': result,
        'total': len(result),
        'counts': counts,
    })


@customer_bp.route('/parts/requests', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk', 'tech'])
def create_part_request():
    """
    Create a new part request.

    Request body:
        {
            "estimate_id": int (optional),
            "job_id": int (optional),
            "description": string (required),
            "part_number": string (optional),
            "qty": int (default 1),
            "parts_status": string (default 'needed'),
            "approved_to_order": boolean (optional),
            "approved_amount": number (optional),
            "vendor": string (optional),
            "po_number": string (optional),
            "eta": string ISO date (optional),
            "notes": string (optional)
        }

    Returns:
        201: { success: true, request: {...} }
    """
    from app.models.tenant.part_request import PartRequest, PARTS_STATUS_VALUES
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    data = request.get_json() or {}

    # Validate required fields
    description = data.get('description', '').strip()
    if not description:
        return jsonify({'error': 'Description is required'}), 400

    # Validate at least one of estimate_id or job_id
    estimate_id = data.get('estimate_id')
    job_id = data.get('job_id')
    if not estimate_id and not job_id:
        return jsonify({'error': 'Either estimate_id or job_id is required'}), 400

    # Validate parts_status
    parts_status = data.get('parts_status', 'needed')
    if parts_status not in PARTS_STATUS_VALUES:
        parts_status = 'needed'

    # Parse ETA
    eta = None
    if data.get('eta'):
        eta_str = normalize_eta(data.get('eta'))
        if eta_str:
            try:
                eta = datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
            except ValueError:
                pass

    # Create request
    part_req = PartRequest(
        tenant_id=tenant_id,
        estimate_id=estimate_id,
        job_id=job_id,
        description=description,
        part_number=data.get('part_number'),
        qty=data.get('qty', 1),
        parts_status=parts_status,
        approved_to_order=bool(data.get('approved_to_order', False)),
        approved_amount=data.get('approved_amount'),
        vendor=data.get('vendor'),
        po_number=data.get('po_number'),
        eta=eta,
        notes=data.get('notes'),
        created_by=user_id,
    )

    db.session.add(part_req)
    db.session.commit()

    # Log activity if linked to estimate
    if part_req.estimate_id:
        EstimateActivity.log(
            estimate_id=part_req.estimate_id,
            activity_type='parts_request_created',
            user_id=user_id,
            activity_data={
                'part_request_id': part_req.id,
                'description': description,
                'qty': part_req.qty,
                'job_id': part_req.job_id,
            }
        )

    return jsonify({
        'success': True,
        'request': part_req.to_dict(),
    }), 201


@customer_bp.route('/parts/requests/<int:request_id>', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def update_part_request(request_id):
    """
    Update a part request.

    Dispatch roles only can update.

    Request body (all optional):
        {
            "description": string,
            "part_number": string,
            "qty": int,
            "parts_status": string,
            "approved_to_order": boolean,
            "approved_amount": number,
            "vendor": string,
            "po_number": string,
            "eta": string ISO date,
            "notes": string
        }

    Returns:
        200: { success: true, request: {...} }
    """
    from app.models.tenant.part_request import PartRequest, PARTS_STATUS_VALUES
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    part_req = PartRequest.query.filter_by(id=request_id, tenant_id=tenant_id).first()
    if not part_req:
        return jsonify({'error': 'Part request not found'}), 404

    data = request.get_json() or {}
    old_status = part_req.parts_status

    # Update fields if provided
    if 'description' in data:
        part_req.description = data['description']
    if 'part_number' in data:
        part_req.part_number = data['part_number']
    if 'qty' in data:
        part_req.qty = data['qty']
    if 'notes' in data:
        part_req.notes = data['notes']
    if 'vendor' in data:
        part_req.vendor = data['vendor']
    if 'po_number' in data:
        part_req.po_number = data['po_number']

    # Update parts_status
    if 'parts_status' in data and data['parts_status'] in PARTS_STATUS_VALUES:
        part_req.parts_status = data['parts_status']

    # Update approval fields
    if 'approved_to_order' in data:
        was_approved = part_req.approved_to_order
        part_req.approved_to_order = bool(data['approved_to_order'])
        if part_req.approved_to_order and not was_approved:
            part_req.approved_by = user_id
            part_req.approved_at = datetime.utcnow()
    if 'approved_amount' in data:
        part_req.approved_amount = data['approved_amount']

    # Update ETA
    if 'eta' in data:
        if data['eta']:
            eta_str = normalize_eta(data['eta'])
            if eta_str:
                try:
                    part_req.eta = datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
        else:
            part_req.eta = None

    db.session.commit()

    # Log activity if status changed
    if part_req.estimate_id:
        if old_status != part_req.parts_status:
            EstimateActivity.log(
                estimate_id=part_req.estimate_id,
                activity_type='parts_request_status_changed',
                user_id=user_id,
                activity_data={
                    'part_request_id': part_req.id,
                    'description': part_req.description,
                    'old_status': old_status,
                    'new_status': part_req.parts_status,
                }
            )
        else:
            EstimateActivity.log(
                estimate_id=part_req.estimate_id,
                activity_type='parts_request_updated',
                user_id=user_id,
                activity_data={
                    'part_request_id': part_req.id,
                    'description': part_req.description,
                }
            )

    return jsonify({
        'success': True,
        'request': part_req.to_dict(),
    })


# ==============================================================================
# PARTS APPROVAL CONTROLS (Stage 5T)
# ==============================================================================

@customer_bp.route('/parts/requests/<int:request_id>/approve', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def approve_part_request(request_id):
    """
    Approve a part request for ordering.

    Sets approved_to_order = true and records approval metadata.
    Does NOT change parts_status, create vendor orders, or affect SLA.

    Request body:
        {
            "approved_amount": number (optional - override estimate),
            "approval_notes": string (optional)
        }

    Returns:
        200: { success: true, request: {...} }
        404: Part request not found
    """
    from app.models.tenant.part_request import PartRequest
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    part_req = PartRequest.query.filter_by(id=request_id, tenant_id=tenant_id).first()
    if not part_req:
        return jsonify({'error': 'Part request not found'}), 404

    data = request.get_json() or {}

    # Set approval fields
    part_req.approved_to_order = True
    part_req.approved_by = user_id
    part_req.approved_at = datetime.utcnow()

    if 'approved_amount' in data and data['approved_amount'] is not None:
        part_req.approved_amount = data['approved_amount']

    if 'approval_notes' in data:
        part_req.approval_notes = data['approval_notes']

    db.session.commit()

    # Log activity
    if part_req.estimate_id:
        EstimateActivity.log(
            estimate_id=part_req.estimate_id,
            activity_type='parts_request_approved',
            user_id=user_id,
            activity_data={
                'part_request_id': part_req.id,
                'description': part_req.description,
                'approved_amount': float(part_req.approved_amount) if part_req.approved_amount else None,
            }
        )

    return jsonify({
        'success': True,
        'request': part_req.to_dict(),
    })


@customer_bp.route('/parts/requests/<int:request_id>/unapprove', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def unapprove_part_request(request_id):
    """
    Revoke approval for a part request.

    Sets approved_to_order = false and clears approval metadata.
    Does NOT change parts_status or affect SLA.

    Returns:
        200: { success: true, request: {...} }
        404: Part request not found
    """
    from app.models.tenant.part_request import PartRequest
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    part_req = PartRequest.query.filter_by(id=request_id, tenant_id=tenant_id).first()
    if not part_req:
        return jsonify({'error': 'Part request not found'}), 404

    # Clear approval fields
    part_req.approved_to_order = False
    part_req.approved_by = None
    part_req.approved_at = None
    part_req.approved_amount = None
    part_req.approval_notes = None

    db.session.commit()

    # Log activity
    if part_req.estimate_id:
        EstimateActivity.log(
            estimate_id=part_req.estimate_id,
            activity_type='parts_request_unapproved',
            user_id=user_id,
            activity_data={
                'part_request_id': part_req.id,
                'description': part_req.description,
            }
        )

    return jsonify({
        'success': True,
        'request': part_req.to_dict(),
    })


@customer_bp.route('/parts/requests/bulk-approve', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def bulk_approve_part_requests():
    """
    Bulk approve multiple part requests.

    Request body:
        {
            "request_ids": [1, 2, 3],
            "approved_amount_map": { "1": 50.00, "2": 75.00 } (optional),
            "approval_notes": "Batch approved" (optional)
        }

    Returns:
        200: { success: true, approved_count: number, requests: [...] }
    """
    from app.models.tenant.part_request import PartRequest
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    data = request.get_json() or {}
    request_ids = data.get('request_ids', [])
    amount_map = data.get('approved_amount_map', {})
    notes = data.get('approval_notes', '')

    if not request_ids:
        return jsonify({'error': 'No request IDs provided'}), 400

    # Fetch all requests (tenant-safe)
    requests_to_approve = PartRequest.query.filter(
        PartRequest.id.in_(request_ids),
        PartRequest.tenant_id == tenant_id
    ).all()

    approved = []
    now = datetime.utcnow()

    for part_req in requests_to_approve:
        part_req.approved_to_order = True
        part_req.approved_by = user_id
        part_req.approved_at = now

        # Check for individual amount override
        if str(part_req.id) in amount_map:
            part_req.approved_amount = amount_map[str(part_req.id)]

        if notes:
            part_req.approval_notes = notes

        # Log activity
        if part_req.estimate_id:
            EstimateActivity.log(
                estimate_id=part_req.estimate_id,
                activity_type='parts_request_approved',
                user_id=user_id,
                activity_data={
                    'part_request_id': part_req.id,
                    'description': part_req.description,
                    'approved_amount': float(part_req.approved_amount) if part_req.approved_amount else None,
                    'bulk_operation': True,
                }
            )

        approved.append(part_req.to_dict())

    db.session.commit()

    return jsonify({
        'success': True,
        'approved_count': len(approved),
        'requests': approved,
    })


# ==============================================================================
# PARTS STATUS TRANSITIONS (Stage 5U)
# ==============================================================================

@customer_bp.route('/parts/requests/<int:request_id>/status', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def update_part_request_status(request_id):
    """
    Update the status of a part request with transition validation.

    Validates that the transition is allowed based on current status.
    Auto-sets timeline timestamps when transitioning to terminal states.
    Logs activity for all transitions.

    Request body:
        {
            "parts_status": string (required),
            "eta": string ISO date (optional),
            "vendor": string (optional),
            "po_number": string (optional),
            "notes": string (optional)
        }

    Returns:
        200: { success: true, request: {...} }
        400: Invalid transition
        404: Part request not found
    """
    from app.models.tenant.part_request import PartRequest, PARTS_STATUS_VALUES
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.services.blocker_helpers import normalize_eta
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    part_req = PartRequest.query.filter_by(id=request_id, tenant_id=tenant_id).first()
    if not part_req:
        return jsonify({'error': 'Part request not found'}), 404

    data = request.get_json() or {}
    new_status = data.get('parts_status')

    if not new_status:
        return jsonify({'error': 'parts_status is required'}), 400

    if new_status not in PARTS_STATUS_VALUES:
        return jsonify({'error': f'Invalid status: {new_status}'}), 400

    old_status = part_req.parts_status

    # Validate transition
    if new_status != old_status:
        if not part_req.can_transition_to(new_status):
            allowed = part_req.get_allowed_transitions()
            return jsonify({
                'error': f'Cannot transition from {old_status} to {new_status}',
                'allowed_transitions': allowed,
            }), 400

    now = datetime.utcnow()

    # Handle exception state
    if new_status == 'exception' and old_status != 'exception':
        part_req.previous_status = old_status

    # Handle recovery from exception
    if old_status == 'exception' and new_status != 'exception':
        part_req.previous_status = None  # Clear after recovery

    # Update status
    part_req.parts_status = new_status
    part_req.status_updated_at = now
    part_req.status_updated_by = user_id

    # Auto-set timeline timestamps for terminal transitions
    if new_status == 'ordered' and not part_req.ordered_at:
        part_req.ordered_at = now
        # Also set approved_to_order if transitioning to ordered
        if not part_req.approved_to_order:
            part_req.approved_to_order = True
            part_req.approved_by = user_id
            part_req.approved_at = now
    elif new_status == 'shipped' and not part_req.shipped_at:
        part_req.shipped_at = now
    elif new_status == 'received' and not part_req.received_at:
        part_req.received_at = now
    elif new_status == 'installed' and not part_req.installed_at:
        part_req.installed_at = now

    # Update optional fields if provided
    if 'vendor' in data:
        part_req.vendor = data['vendor']
    if 'po_number' in data:
        part_req.po_number = data['po_number']
    if 'notes' in data:
        part_req.notes = data['notes']
    if 'eta' in data:
        if data['eta']:
            eta_str = normalize_eta(data['eta'])
            if eta_str:
                try:
                    part_req.eta = datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
        else:
            part_req.eta = None

    db.session.commit()

    # Log activity
    if part_req.estimate_id and old_status != new_status:
        activity_type = 'parts_request_exception_set' if new_status == 'exception' else 'parts_request_status_changed'
        EstimateActivity.log(
            estimate_id=part_req.estimate_id,
            activity_type=activity_type,
            user_id=user_id,
            activity_data={
                'part_request_id': part_req.id,
                'description': part_req.description,
                'from_status': old_status,
                'to_status': new_status,
                'vendor': part_req.vendor,
                'po_number': part_req.po_number,
            }
        )

    return jsonify({
        'success': True,
        'request': part_req.to_dict(),
    })


@customer_bp.route('/parts/requests/<int:request_id>/nudge', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def nudge_part_request(request_id):
    """
    Stage 5V: Send a nudge notification for a part request.

    Recipients can be internal (by role) or external (vendor email).
    Logs activity and enforces anti-spam rate limiting.

    Request body:
        {
            "nudge_type": "internal" | "vendor" (default: internal),
            "target_role": string (for internal: owner/manager/desk),
            "vendor_email": string (for vendor nudge),
            "message": string (optional custom message)
        }

    Returns:
        200: { success: true, nudge_id: string }
        400: Invalid request or rate limited
        404: Part request not found
    """
    from app.models.tenant.part_request import PartRequest
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.user import User
    from app.services.email_service import get_email_service
    from app.extensions import db
    import hashlib

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    part_req = PartRequest.query.filter_by(id=request_id, tenant_id=tenant_id).first()
    if not part_req:
        return jsonify({'error': 'Part request not found'}), 404

    data = request.get_json() or {}
    nudge_type = data.get('nudge_type', 'internal')
    target_role = data.get('target_role')
    vendor_email = data.get('vendor_email')
    custom_message = data.get('message', '')

    # Validate nudge type
    if nudge_type not in ['internal', 'vendor']:
        return jsonify({'error': 'Invalid nudge_type. Must be "internal" or "vendor"'}), 400

    if nudge_type == 'internal' and not target_role:
        return jsonify({'error': 'target_role is required for internal nudge'}), 400

    if nudge_type == 'vendor' and not vendor_email:
        return jsonify({'error': 'vendor_email is required for vendor nudge'}), 400

    # Rate limit check - one nudge per request+type per 4 hours
    now = datetime.utcnow()
    rate_limit_hours = 4
    nudge_key = f"{request_id}:{nudge_type}:{target_role or vendor_email}"
    nudge_hash = hashlib.md5(nudge_key.encode()).hexdigest()[:12]

    # Check for recent nudges in activity log
    if part_req.estimate_id:
        recent_nudge = EstimateActivity.query.filter(
            EstimateActivity.estimate_id == part_req.estimate_id,
            EstimateActivity.activity_type == 'parts_request_nudge_sent',
            EstimateActivity.created_at > now - timedelta(hours=rate_limit_hours),
        ).filter(
            EstimateActivity.activity_data['nudge_hash'].astext == nudge_hash
        ).first()

        if recent_nudge:
            return jsonify({
                'error': 'Nudge rate limited',
                'message': f'A similar nudge was sent within the last {rate_limit_hours} hours',
                'last_sent': recent_nudge.created_at.isoformat() if recent_nudge.created_at else None,
            }), 400

    # Get sender info
    sender = User.query.filter_by(id=user_id, tenant_id=tenant_id).first()
    sender_name = sender.name if sender else 'Team'

    # Build email content
    subject = f"Parts Request Update Needed: {part_req.description[:50]}"
    job_info = ''
    if part_req.job_id:
        from app.models.tenant.job import Job
        job = Job.query.filter_by(id=part_req.job_id, tenant_id=tenant_id).first()
        if job:
            job_info = f"\nJob: {job.job_number}"
            if job.customer_name:
                job_info += f" - {job.customer_name}"

    body = f"""Hello,

This is a follow-up regarding the following part request:

Part: {part_req.description}
Status: {part_req.parts_status.replace('_', ' ').title()}
{f'Part Number: {part_req.part_number}' if part_req.part_number else ''}
{f'Vendor: {part_req.vendor}' if part_req.vendor else ''}
{f'PO Number: {part_req.po_number}' if part_req.po_number else ''}
{f'ETA: {part_req.eta.strftime("%Y-%m-%d") if part_req.eta else "Not set"}'}
{job_info}

{custom_message if custom_message else 'Please provide an update on this part request.'}

Sent by: {sender_name}
"""

    # Determine recipients
    recipients = []
    if nudge_type == 'internal':
        valid_roles = ['owner', 'manager', 'desk']
        if target_role not in valid_roles:
            return jsonify({'error': f'Invalid target_role. Must be one of: {valid_roles}'}), 400

        # Get users with the target role in this tenant
        role_users = User.query.filter(
            User.tenant_id == tenant_id,
            User.role == target_role,
            User.is_active == True,
        ).all()
        recipients = [u.email for u in role_users if u.email]
    else:
        # Vendor email
        recipients = [vendor_email]

    if not recipients:
        return jsonify({
            'error': 'No recipients found',
            'message': f'No active users with role "{target_role}"' if nudge_type == 'internal' else 'Invalid vendor email',
        }), 400

    # Send email
    email_service = get_email_service()
    success = True
    error_msg = None

    try:
        for recipient in recipients:
            email_service.send_simple(
                to_email=recipient,
                subject=subject,
                body=body,
                tenant_id=tenant_id,
            )
    except Exception as e:
        success = False
        error_msg = str(e)

    # Log activity
    activity_type = 'parts_request_nudge_sent' if success else 'parts_request_nudge_failed'
    if part_req.estimate_id:
        EstimateActivity.log(
            estimate_id=part_req.estimate_id,
            activity_type=activity_type,
            user_id=user_id,
            activity_data={
                'part_request_id': part_req.id,
                'description': part_req.description,
                'nudge_type': nudge_type,
                'target_role': target_role,
                'vendor_email': vendor_email if nudge_type == 'vendor' else None,
                'recipient_count': len(recipients),
                'nudge_hash': nudge_hash,
                'error': error_msg if not success else None,
            }
        )

    if not success:
        return jsonify({
            'error': 'Failed to send nudge',
            'message': error_msg,
        }), 500

    return jsonify({
        'success': True,
        'nudge_id': nudge_hash,
        'recipients': len(recipients),
    })


# ==============================================================================
# ESTIMATE → PARTS REQUESTS BRIDGE (Stage 5R)
# ==============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/parts/suggestions', methods=['GET'])
@login_required
@roles_required(['owner', 'manager', 'desk', 'tech'])
def get_estimate_parts_suggestions(estimate_id):
    """
    Get suggested parts requests for an estimate.

    Analyzes the estimate's R&I operations, supplements, and conventional
    repair panels to suggest parts that may need to be ordered.

    This is a PREVIEW endpoint - no database writes occur.

    Returns:
        200: {
            success: true,
            estimate_id: number,
            estimate_number: string,
            suggestions: [{
                description: string,
                source_type: 'panel_ri' | 'supplement' | 'panel_cr',
                source_id: number,
                part_number: string | null,
                qty: number,
                notes: string | null,
                reason: string,
                already_exists: boolean,
                existing_id: number | null
            }],
            new_suggestions: [...],  // Only suggestions that don't exist
            stats: {
                total_suggestions: number,
                new_suggestions: number,
                duplicates: number,
                by_source_type: { ... }
            }
        }
        404: Estimate not found
    """
    from app.services.parts_request_builder import get_parts_suggestions

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    result = get_parts_suggestions(estimate_id, tenant_id)

    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Estimate not found')}), 404

    return jsonify(result)


@customer_bp.route('/pdr-estimates/<int:estimate_id>/parts/requests', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def create_estimate_parts_requests(estimate_id):
    """
    Bulk create parts requests from suggestions.

    Takes the suggestions from the preview endpoint and creates
    PartRequest records. Supports selecting specific suggestions
    and skipping duplicates.

    Request body:
        {
            "selected_indices": [0, 1, 3],  // Optional - which suggestions to create
            "skip_duplicates": true  // Optional (default true) - skip already-existing
        }

    Returns:
        200: {
            success: true,
            estimate_id: number,
            created_count: number,
            skipped_duplicates: number,
            created: [{ part request objects }]
        }
        404: Estimate not found
    """
    from app.services.parts_request_builder import create_parts_requests_from_suggestions

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    data = request.get_json() or {}
    selected_indices = data.get('selected_indices')  # None means all
    skip_duplicates = data.get('skip_duplicates', True)

    result = create_parts_requests_from_suggestions(
        estimate_id=estimate_id,
        tenant_id=tenant_id,
        user_id=user_id,
        selected_indices=selected_indices,
        skip_duplicates=skip_duplicates,
    )

    if not result.get('success'):
        return jsonify({'error': result.get('error', 'Failed to create parts requests')}), 404

    return jsonify(result)


@customer_bp.route('/pdr-estimates/<int:estimate_id>/parts/requests', methods=['GET'])
@login_required
def get_estimate_parts_requests(estimate_id):
    """
    Get all part requests linked to an estimate.

    Returns:
        200: {
            success: true,
            estimate_id: number,
            requests: [{ part request objects }],
            count: number
        }
        404: Estimate not found
    """
    from app.models.tenant import PDREstimate, PartRequest

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    # Get requests directly linked to estimate
    requests = PartRequest.query.filter_by(
        tenant_id=tenant_id,
        estimate_id=estimate_id,
    ).order_by(PartRequest.created_at.desc()).all()

    return jsonify({
        'success': True,
        'estimate_id': estimate_id,
        'requests': [r.to_dict() for r in requests],
        'count': len(requests),
    })


# ==============================================================================
# R&I JUSTIFICATION ENGINE (Phase 6A)
# ==============================================================================

@customer_bp.route('/ri/catalog', methods=['GET'])
@login_required
def get_ri_catalog():
    """
    Get the R&I catalog (operations, steps, modifiers) for the tenant.

    Ensures default catalog exists on first access.

    Returns:
        200: {
            operations: [{ code, display_name, category, steps: [...] }],
            modifiers: [{ modifier_code, label, adds_time_hours, reason }]
        }
    """
    from app.services.ri_justification_service import get_ri_catalog

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    catalog = get_ri_catalog(tenant_id)

    return jsonify(catalog)


# =============================================================================
# STAGE 6H-C: R&I CATALOG BUILDER (ADMIN ONLY)
# =============================================================================

@customer_bp.route('/ri/catalog/operation', methods=['POST'])
@login_required
@roles_required(['owner', 'manager'])
def create_ri_operation():
    """
    Create a new custom R&I operation (Stage 6H-C).

    Guardrails:
    - Must include at least one HIGH denial resistance step
    - Must include at least one safety or liability risk tag

    Request body:
        {
            "code": "RI_CUSTOM_OPERATION",
            "display_name": "Custom Operation",
            "category": "interior",
            "description": "Description...",
            "risk_level": "medium",
            "difficulty_level": "standard",
            "steps": [{
                "step_code": "STEP_1",
                "label": "Step 1",
                "base_time_hours": 0.25,
                "required": true,
                "denial_resistance": "high",
                "risk_tags": ["airbag"]
            }]
        }

    Returns:
        201: { success: true, operation_id: int }
        400: Validation error
    """
    from app.models.tenant.ri_operation import RIOperation, RI_CATEGORIES, RI_RISK_LEVELS, RI_DIFFICULTY_LEVELS
    from app.models.tenant.ri_step import RIStep
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    data = request.get_json() or {}

    # Validate required fields
    code = data.get('code', '').strip().upper()
    display_name = data.get('display_name', '').strip()
    category = data.get('category', 'interior')
    description = data.get('description', '')
    risk_level = data.get('risk_level', 'medium')
    difficulty_level = data.get('difficulty_level', 'standard')
    steps_data = data.get('steps', [])

    if not code:
        return jsonify({'error': 'code is required'}), 400
    if not display_name:
        return jsonify({'error': 'display_name is required'}), 400
    if category not in RI_CATEGORIES:
        return jsonify({'error': f'category must be one of: {RI_CATEGORIES}'}), 400
    if risk_level not in RI_RISK_LEVELS:
        return jsonify({'error': f'risk_level must be one of: {RI_RISK_LEVELS}'}), 400
    if difficulty_level not in RI_DIFFICULTY_LEVELS:
        return jsonify({'error': f'difficulty_level must be one of: {RI_DIFFICULTY_LEVELS}'}), 400

    # Check for duplicate code
    existing = RIOperation.query.filter_by(tenant_id=tenant_id, code=code).first()
    if existing:
        return jsonify({'error': f'Operation with code {code} already exists'}), 400

    # Guardrail: Must have at least one step
    if not steps_data:
        return jsonify({'error': 'At least one step is required'}), 400

    # Guardrail: Must have at least one HIGH denial resistance step
    high_resistance_count = sum(1 for s in steps_data if s.get('denial_resistance') == 'high')
    if high_resistance_count == 0:
        return jsonify({'error': 'At least one step with HIGH denial resistance is required'}), 400

    # Guardrail: Must have at least one safety/liability risk tag
    all_risk_tags = set()
    for s in steps_data:
        for tag in s.get('risk_tags', []):
            all_risk_tags.add(tag.lower())

    safety_tags = {'airbag', 'seatbelt', 'safety_critical', 'electrical', 'torque', 'liability'}
    if not all_risk_tags.intersection(safety_tags):
        return jsonify({
            'error': 'At least one step must include a safety/liability risk tag',
            'valid_safety_tags': list(safety_tags)
        }), 400

    # Create operation
    operation = RIOperation(
        tenant_id=tenant_id,
        code=code,
        display_name=display_name,
        category=category,
        description=description,
        risk_level=risk_level,
        difficulty_level=difficulty_level,
        is_seeded=False,  # Custom operations are not seeded
    )
    db.session.add(operation)
    db.session.flush()  # Get ID

    # Create steps
    for idx, step_data in enumerate(steps_data):
        step = RIStep(
            tenant_id=tenant_id,
            operation_id=operation.id,
            step_code=step_data.get('step_code', f'STEP_{idx}').upper(),
            label=step_data.get('label', 'Step'),
            description=step_data.get('description'),
            base_time_hours=float(step_data.get('base_time_hours', 0.25)),
            required=step_data.get('required', True),
            denial_resistance=step_data.get('denial_resistance', 'medium'),
            risk_tags=step_data.get('risk_tags', []),
            oem_dependency=step_data.get('oem_dependency', False),
            safety_critical=step_data.get('safety_critical', False),
            order_index=idx,
        )
        db.session.add(step)

    db.session.commit()

    return jsonify({'success': True, 'operation_id': operation.id}), 201


@customer_bp.route('/ri/catalog/operation/<int:operation_id>', methods=['DELETE'])
@login_required
@roles_required(['owner', 'manager'])
def delete_ri_operation(operation_id):
    """
    Delete a custom R&I operation (Stage 6H-C).

    Guardrails:
    - Cannot delete seeded operations

    Returns:
        200: { success: true }
        400: Cannot delete seeded operation
        404: Operation not found
    """
    from app.models.tenant.ri_operation import RIOperation
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    operation = RIOperation.query.filter_by(id=operation_id, tenant_id=tenant_id).first()
    if not operation:
        return jsonify({'error': 'Operation not found'}), 404

    if operation.is_seeded:
        return jsonify({'error': 'Cannot delete seeded operations. These are system defaults.'}), 400

    db.session.delete(operation)
    db.session.commit()

    return jsonify({'success': True})


@customer_bp.route('/ri/catalog/operation/<int:operation_id>/step', methods=['POST'])
@login_required
@roles_required(['owner', 'manager'])
def add_ri_step(operation_id):
    """
    Add a step to an R&I operation (Stage 6H-C).

    Guardrails:
    - Step must have a label (justification text)

    Request body:
        {
            "step_code": "REMOVE_COMPONENT",
            "label": "Remove component",
            "base_time_hours": 0.25,
            "required": true,
            "denial_resistance": "high",
            "risk_tags": ["electrical"],
            "oem_dependency": false,
            "safety_critical": false
        }

    Returns:
        201: { success: true, step_id: int }
        400: Validation error
        404: Operation not found
    """
    from app.models.tenant.ri_operation import RIOperation
    from app.models.tenant.ri_step import RIStep
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    operation = RIOperation.query.filter_by(id=operation_id, tenant_id=tenant_id).first()
    if not operation:
        return jsonify({'error': 'Operation not found'}), 404

    data = request.get_json() or {}

    step_code = data.get('step_code', '').strip().upper()
    label = data.get('label', '').strip()

    if not label:
        return jsonify({'error': 'label is required (justification text)'}), 400

    # Auto-generate step_code if not provided
    if not step_code:
        step_code = 'STEP_' + label.upper().replace(' ', '_')[:30]

    # Check for duplicate
    existing = RIStep.query.filter_by(operation_id=operation_id, step_code=step_code).first()
    if existing:
        return jsonify({'error': f'Step with code {step_code} already exists in this operation'}), 400

    # Get next order index
    max_order = db.session.query(db.func.max(RIStep.order_index)).filter_by(
        operation_id=operation_id
    ).scalar() or 0

    step = RIStep(
        tenant_id=tenant_id,
        operation_id=operation_id,
        step_code=step_code,
        label=label,
        description=data.get('description'),
        base_time_hours=float(data.get('base_time_hours', 0.25)),
        required=data.get('required', True),
        denial_resistance=data.get('denial_resistance', 'medium'),
        risk_tags=data.get('risk_tags', []),
        oem_dependency=data.get('oem_dependency', False),
        safety_critical=data.get('safety_critical', False),
        order_index=max_order + 1,
    )
    db.session.add(step)
    db.session.commit()

    return jsonify({'success': True, 'step_id': step.id}), 201


@customer_bp.route('/ri/catalog/step/<int:step_id>', methods=['DELETE'])
@login_required
@roles_required(['owner', 'manager'])
def delete_ri_step(step_id):
    """
    Delete a step from an R&I operation (Stage 6H-C).

    Returns:
        200: { success: true }
        404: Step not found
    """
    from app.models.tenant.ri_step import RIStep
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    step = RIStep.query.filter_by(id=step_id, tenant_id=tenant_id).first()
    if not step:
        return jsonify({'error': 'Step not found'}), 404

    db.session.delete(step)
    db.session.commit()

    return jsonify({'success': True})


@customer_bp.route('/ri/catalog/validate', methods=['POST'])
@login_required
def validate_ri_operation():
    """
    Validate an R&I operation before saving (Stage 6H-C).

    Returns denial resistance warnings and guardrail checks.

    Request body: Same as create_ri_operation

    Returns:
        200: {
            valid: bool,
            warnings: [str],
            errors: [str],
            denial_resistance_score: float
        }
    """
    data = request.get_json() or {}
    steps_data = data.get('steps', [])

    errors = []
    warnings = []

    # Check required fields
    if not data.get('code'):
        errors.append('code is required')
    if not data.get('display_name'):
        errors.append('display_name is required')
    if not steps_data:
        errors.append('At least one step is required')

    # Check denial resistance
    high_count = sum(1 for s in steps_data if s.get('denial_resistance') == 'high')
    medium_count = sum(1 for s in steps_data if s.get('denial_resistance') == 'medium')
    low_count = sum(1 for s in steps_data if s.get('denial_resistance') == 'low')
    total_steps = len(steps_data)

    if high_count == 0:
        errors.append('At least one step with HIGH denial resistance is required')

    if low_count > high_count:
        warnings.append('More LOW resistance steps than HIGH - denial risk is elevated')

    # Check risk tags
    all_risk_tags = set()
    for s in steps_data:
        for tag in s.get('risk_tags', []):
            all_risk_tags.add(tag.lower())

    safety_tags = {'airbag', 'seatbelt', 'safety_critical', 'electrical', 'torque', 'liability'}
    if not all_risk_tags.intersection(safety_tags):
        errors.append('At least one step must include a safety/liability risk tag')

    # Calculate denial resistance score
    if total_steps > 0:
        score = ((high_count * 100) + (medium_count * 60) + (low_count * 20)) / total_steps
    else:
        score = 0

    if score < 60:
        warnings.append(f'Denial resistance score is {score:.0f}/100 (weak)')
    elif score < 80:
        warnings.append(f'Denial resistance score is {score:.0f}/100 (moderate)')

    return jsonify({
        'valid': len(errors) == 0,
        'warnings': warnings,
        'errors': errors,
        'denial_resistance_score': round(score, 1),
        'step_counts': {
            'high': high_count,
            'medium': medium_count,
            'low': low_count,
            'total': total_steps,
        }
    })


@customer_bp.route('/pdr-estimates/<int:estimate_id>/ri', methods=['GET'])
@login_required
def get_estimate_ri(estimate_id):
    """
    Get computed R&I summary for an estimate.

    Returns all attached R&I operations with computed times and justifications.

    Returns:
        200: {
            estimate_id: number,
            operations: [...],
            total_ri_time_hours: number,
            operation_count: number
        }
        404: Estimate not found
    """
    from app.models.tenant import PDREstimate
    from app.services.ri_justification_service import compute_estimate_ri_summary

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    # Tenant safety
    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    summary = compute_estimate_ri_summary(estimate_id, tenant_id)

    return jsonify(summary)


@customer_bp.route('/pdr-estimates/<int:estimate_id>/ri', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk', 'estimator'])
def add_estimate_ri(estimate_id):
    """
    Add an R&I operation to an estimate.

    Request body:
        {
            "operation_code": string,
            "selected_modifier_codes": string[] (optional),
            "step_overrides": [{ step_id, included, time_override_hours, notes }] (optional),
            "notes": string (optional)
        }

    Returns:
        201: { success: true, estimate_ri_operation_id: number }
        400: Invalid operation code or modifiers
        404: Estimate not found
        409: Operation already attached
    """
    from app.models.tenant import PDREstimate
    from app.models.tenant.ri_operation import RIOperation
    from app.models.tenant.ri_modifier import RIModifier
    from app.models.tenant.ri_step import RIStep
    from app.models.tenant.pdr_estimate_ri import (
        PDREstimateRIOperation,
        PDREstimateRIStepOverride,
        PDREstimateRIModifierSelection,
    )
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.services.ri_justification_service import ensure_default_ri_catalog
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    data = request.get_json() or {}
    operation_code = data.get('operation_code')
    selected_modifier_codes = data.get('selected_modifier_codes', [])
    step_overrides_data = data.get('step_overrides', [])
    notes = data.get('notes')

    if not operation_code:
        return jsonify({'error': 'operation_code is required'}), 400

    # Ensure catalog exists
    ensure_default_ri_catalog(tenant_id)

    # Find operation
    operation = RIOperation.query.filter_by(tenant_id=tenant_id, code=operation_code).first()
    if not operation:
        return jsonify({'error': f'Operation not found: {operation_code}'}), 400

    # Check if already attached
    existing = PDREstimateRIOperation.query.filter_by(
        estimate_id=estimate_id,
        operation_id=operation.id,
    ).first()
    if existing:
        return jsonify({'error': 'Operation already attached to this estimate'}), 409

    # Create the estimate R&I operation
    est_ri_op = PDREstimateRIOperation(
        tenant_id=tenant_id,
        estimate_id=estimate_id,
        operation_id=operation.id,
        notes=notes,
    )
    db.session.add(est_ri_op)
    db.session.flush()

    # Add modifier selections
    for mod_code in selected_modifier_codes:
        modifier = RIModifier.query.filter_by(tenant_id=tenant_id, modifier_code=mod_code).first()
        if modifier:
            selection = PDREstimateRIModifierSelection(
                tenant_id=tenant_id,
                estimate_ri_operation_id=est_ri_op.id,
                modifier_id=modifier.id,
            )
            db.session.add(selection)

    # Add step overrides
    for override_data in step_overrides_data:
        step_id = override_data.get('step_id')
        step = RIStep.query.filter_by(id=step_id, operation_id=operation.id).first()
        if step:
            override = PDREstimateRIStepOverride(
                tenant_id=tenant_id,
                estimate_ri_operation_id=est_ri_op.id,
                step_id=step.id,
                included=override_data.get('included', True),
                time_override_hours=override_data.get('time_override_hours'),
                notes=override_data.get('notes'),
            )
            db.session.add(override)

    db.session.commit()

    # Log activity
    EstimateActivity.log(
        estimate_id=estimate_id,
        activity_type='ri_added',
        user_id=user_id,
        activity_data={
            'operation_code': operation_code,
            'operation_name': operation.display_name,
            'modifier_count': len(selected_modifier_codes),
        }
    )

    return jsonify({
        'success': True,
        'estimate_ri_operation_id': est_ri_op.id,
    }), 201


@customer_bp.route('/pdr-estimates/<int:estimate_id>/ri/<int:estimate_ri_op_id>', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager', 'desk', 'estimator'])
def update_estimate_ri(estimate_id, estimate_ri_op_id):
    """
    Update an R&I operation on an estimate.

    Request body:
        {
            "selected_modifier_codes": string[] (replaces all),
            "step_overrides": [{ step_id, included, time_override_hours, notes }] (replaces all),
            "notes": string
        }

    Returns:
        200: { success: true }
        404: Estimate or operation not found
    """
    from app.models.tenant import PDREstimate
    from app.models.tenant.ri_modifier import RIModifier
    from app.models.tenant.ri_step import RIStep
    from app.models.tenant.pdr_estimate_ri import (
        PDREstimateRIOperation,
        PDREstimateRIStepOverride,
        PDREstimateRIModifierSelection,
    )
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    est_ri_op = PDREstimateRIOperation.query.filter_by(
        id=estimate_ri_op_id,
        estimate_id=estimate_id,
        tenant_id=tenant_id,
    ).first()
    if not est_ri_op:
        return jsonify({'error': 'R&I operation not found'}), 404

    data = request.get_json() or {}
    changes = []

    # Update notes if provided
    if 'notes' in data:
        est_ri_op.notes = data['notes']
        changes.append('notes')

    # Replace modifiers if provided
    if 'selected_modifier_codes' in data:
        # Remove existing
        PDREstimateRIModifierSelection.query.filter_by(
            estimate_ri_operation_id=est_ri_op.id
        ).delete()

        # Add new
        for mod_code in data['selected_modifier_codes']:
            modifier = RIModifier.query.filter_by(tenant_id=tenant_id, modifier_code=mod_code).first()
            if modifier:
                selection = PDREstimateRIModifierSelection(
                    tenant_id=tenant_id,
                    estimate_ri_operation_id=est_ri_op.id,
                    modifier_id=modifier.id,
                )
                db.session.add(selection)
        changes.append('modifiers')

    # Replace step overrides if provided
    if 'step_overrides' in data:
        # Remove existing
        PDREstimateRIStepOverride.query.filter_by(
            estimate_ri_operation_id=est_ri_op.id
        ).delete()

        # Add new
        for override_data in data['step_overrides']:
            step_id = override_data.get('step_id')
            step = RIStep.query.filter_by(id=step_id, operation_id=est_ri_op.operation_id).first()
            if step:
                override = PDREstimateRIStepOverride(
                    tenant_id=tenant_id,
                    estimate_ri_operation_id=est_ri_op.id,
                    step_id=step.id,
                    included=override_data.get('included', True),
                    time_override_hours=override_data.get('time_override_hours'),
                    notes=override_data.get('notes'),
                )
                db.session.add(override)
        changes.append('step_overrides')

    db.session.commit()

    # Log activity
    EstimateActivity.log(
        estimate_id=estimate_id,
        activity_type='ri_updated',
        user_id=user_id,
        activity_data={
            'operation_code': est_ri_op.operation.code,
            'changes': changes,
        }
    )

    return jsonify({'success': True})


@customer_bp.route('/pdr-estimates/<int:estimate_id>/ri/<int:estimate_ri_op_id>', methods=['DELETE'])
@login_required
@roles_required(['owner', 'manager', 'desk', 'estimator'])
def remove_estimate_ri(estimate_id, estimate_ri_op_id):
    """
    Remove an R&I operation from an estimate.

    Returns:
        200: { success: true }
        404: Estimate or operation not found
    """
    from app.models.tenant import PDREstimate
    from app.models.tenant.pdr_estimate_ri import PDREstimateRIOperation
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    est_ri_op = PDREstimateRIOperation.query.filter_by(
        id=estimate_ri_op_id,
        estimate_id=estimate_id,
        tenant_id=tenant_id,
    ).first()
    if not est_ri_op:
        return jsonify({'error': 'R&I operation not found'}), 404

    operation_code = est_ri_op.operation.code
    operation_name = est_ri_op.operation.display_name

    # Cascade delete will remove overrides and modifier selections
    db.session.delete(est_ri_op)
    db.session.commit()

    # Log activity
    EstimateActivity.log(
        estimate_id=estimate_id,
        activity_type='ri_removed',
        user_id=user_id,
        activity_data={
            'operation_code': operation_code,
            'operation_name': operation_name,
        }
    )

    return jsonify({'success': True})


# =============================================================================
# STAGE 6H-A: DENIAL SIMULATOR API
# =============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/ri/denial-simulator', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk', 'estimator'])
def denial_simulator(estimate_id):
    """
    Generate a rebuttal for a common carrier denial (Stage 6H-A).

    Request body:
        { "denial_code": "NOT_PAYING_SUNVISORS" }

    Valid denial_code values:
        - NOT_PAYING_SUNVISORS
        - NOT_PAYING_HEADLINER_TIME
        - NOT_PAYING_TRIM_REMOVAL
        - NOT_PAYING_SEATBELTS
        - TIME_EXCESSIVE
        - OPERATION_INCLUDED_ELSEWHERE

    Returns:
        200: {
            success: true,
            denial_code: str,
            insurer_claim: str,
            rebuttal_summary: str,
            rebuttal_bullets: [str],
            cited_steps: [{step_code, operation_name, label, hours, cite_line, ...}],
            risk_exposure: [str],
            copy_blocks: { short: str, full: str }
        }
        400: Invalid denial code or no matching steps
        404: Estimate not found
    """
    from app.models.tenant import PDREstimate
    from app.services.ri_justification_service import get_denial_rebuttal, DENIAL_DEFINITIONS

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    # Tenant safety
    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    data = request.get_json() or {}
    denial_code = data.get('denial_code', '')

    if not denial_code:
        return jsonify({
            'error': 'denial_code is required',
            'valid_codes': list(DENIAL_DEFINITIONS.keys()),
        }), 400

    result = get_denial_rebuttal(estimate_id, tenant_id, denial_code)

    if not result.get('success'):
        return jsonify(result), 400

    return jsonify(result)


@customer_bp.route('/pdr-estimates/<int:estimate_id>/ri/denial-simulator/codes', methods=['GET'])
@login_required
def get_denial_codes(estimate_id):
    """
    Get available denial codes for the simulator.

    Returns:
        200: { codes: [{ code, label, description }] }
    """
    from app.services.ri_justification_service import DENIAL_DEFINITIONS

    codes = []
    for code, definition in DENIAL_DEFINITIONS.items():
        codes.append({
            'code': code,
            'label': code.replace('_', ' ').title(),
            'description': definition.get('insurer_claim', ''),
        })

    return jsonify({'codes': codes})


# =============================================================================
# STAGE 6H-B: SUPPLEMENT WRITER API
# =============================================================================

@customer_bp.route('/pdr-estimates/<int:estimate_id>/ri/supplement-preview', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk', 'estimator'])
def supplement_preview(estimate_id):
    """
    Generate a full insurer-ready supplement letter (Stage 6H-B).

    Request body:
        { "denial_code": optional }

    Returns:
        200: {
            success: true,
            letter_text: str,
            estimate_number: str,
            claim_number: str,
            vehicle: str,
            customer_name: str,
            total_ri_hours: float,
            total_ri_cost: float,
            labor_rate: float,
            labor_source: str,
            denial_code: str | null
        }
        404: Estimate not found or no R&I operations
    """
    from app.models.tenant import PDREstimate
    from app.services.ri_justification_service import build_supplement_letter
    from app.models.tenant.estimate_activity import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    # Tenant safety
    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    data = request.get_json() or {}
    denial_code = data.get('denial_code')

    result = build_supplement_letter(estimate_id, tenant_id, denial_code)

    if not result.get('success'):
        return jsonify(result), 400

    # Log activity
    EstimateActivity.log(
        estimate_id=estimate_id,
        activity_type='supplement_generated',
        user_id=user_id,
        activity_data={
            'denial_code': denial_code,
            'total_ri_hours': result.get('total_ri_hours'),
            'total_ri_cost': result.get('total_ri_cost'),
        }
    )

    return jsonify(result)


@customer_bp.route('/jobs/<int:job_id>/check-in', methods=['POST'])
@login_required
def job_check_in(job_id):
    """
    Log a job check-in for tech location tracking.

    Tech can check-in to jobs assigned to them.
    Dispatch roles can check-in any job.

    Uses existing EstimateActivity model - NO new tables.

    Request body:
        {
            "location": "shop" | "field" | null,
            "notes": "optional notes"
        }

    Returns:
        200: { success: true, location, checked_in_at }
        403: Not authorized (tech can only check-in own jobs)
        404: Job not found
    """
    from app.models.tenant.job import Job
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.user import User
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']
    user_role = identity.get('role', '')

    job = Job.query.filter_by(id=job_id, tenant_id=tenant_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    # Permission check: tech can only check-in to their own jobs
    dispatch_roles = ['owner', 'manager', 'desk', 'admin']
    is_dispatch = user_role in dispatch_roles
    is_assigned_tech = job.assigned_tech == user_id

    if not is_dispatch and not is_assigned_tech:
        return jsonify({'error': 'You can only check-in to jobs assigned to you'}), 403

    data = request.get_json() or {}
    location = data.get('location')  # "shop" | "field" | null
    notes = data.get('notes', '')

    # Validate location
    if location and location not in ['shop', 'field']:
        location = None

    checked_in_at = datetime.utcnow()

    # Log activity if job has linked estimate
    if job.estimate_id:
        EstimateActivity.log(
            estimate_id=job.estimate_id,
            activity_type='job_checked_in',
            user_id=user_id,
            activity_data={
                'job_id': job.id,
                'job_number': job.job_number,
                'location': location,
                'notes': notes,
                'checked_in_at': checked_in_at.isoformat(),
            }
        )

    db.session.commit()

    return jsonify({
        'success': True,
        'location': location,
        'checked_in_at': checked_in_at.isoformat(),
        'job_id': job.id,
        'job_number': job.job_number,
    })


@customer_bp.route('/pdr-estimates/<int:estimate_id>/close', methods=['POST'])
@login_required
def close_estimate_claim(estimate_id):
    """
    Close/complete an estimate claim.

    Marks estimate as completed and invoiced after all invoices are paid.

    Returns:
        200: { estimate, message }
        400: Cannot close (validation failed)
        404: Estimate not found
    """
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate, EstimateActivity
    from app.services.workflow_service import WorkflowGuard

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    estimate = PDREstimate.query.filter_by(id=estimate_id, tenant_id=tenant_id).first()
    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    # Use guard to validate
    guard = WorkflowGuard(estimate)

    # Check if can set to completed
    can_complete, reason = guard.can_set_status('completed')
    if not can_complete:
        EstimateActivity.log(
            estimate_id=estimate.id,
            activity_type='workflow_guard_blocked',
            user_id=user_id,
            activity_data={
                'action': 'close_claim',
                'reason': reason
            }
        )
        return jsonify({'error': reason, 'code': 'GUARD_BLOCKED'}), 409

    # Check if can set to invoiced
    can_invoice, reason = guard.can_set_status('invoiced')
    if not can_invoice:
        EstimateActivity.log(
            estimate_id=estimate.id,
            activity_type='workflow_guard_blocked',
            user_id=user_id,
            activity_data={
                'action': 'close_claim',
                'reason': reason
            }
        )
        return jsonify({'error': reason, 'code': 'GUARD_BLOCKED'}), 409

    # Check that all invoices are paid
    invoices = list(estimate.invoices)
    active_invoices = [inv for inv in invoices if inv.status != 'void']
    unpaid_invoices = [inv for inv in active_invoices if not inv.is_paid()]

    if unpaid_invoices:
        total_balance = sum(float(inv.balance_due) for inv in unpaid_invoices)
        return jsonify({
            'error': f'Cannot close claim: ${total_balance:.2f} outstanding across {len(unpaid_invoices)} invoice(s)',
            'code': 'UNPAID_INVOICES'
        }), 400

    old_status = estimate.status

    # Update estimate status
    estimate.status = 'completed'
    db.session.commit()

    # Log activity
    EstimateActivity.log(
        estimate_id=estimate.id,
        activity_type='estimate_status_changed',
        user_id=user_id,
        activity_data={
            'old_status': old_status,
            'new_status': 'completed',
            'action': 'close_claim',
            'invoices_count': len(active_invoices),
            'total_collected': sum(float(inv.amount_paid or 0) for inv in active_invoices)
        }
    )

    return jsonify({
        'estimate': estimate.to_dict(),
        'message': 'Claim closed successfully'
    })


@customer_bp.route('/invoices/<int:invoice_id>/issue', methods=['POST'])
@login_required
def issue_invoice_with_guard(invoice_id):
    """
    Issue an invoice with workflow guardrails.

    Returns:
        200: { invoice, message }
        400: Cannot issue (validation failed)
        404: Invoice not found
        409: Guardrail blocked
    """
    from app.extensions import db
    from app.models.tenant.invoice import Invoice
    from app.models.tenant.pdr_estimate import PDREstimate, EstimateActivity
    from app.services.workflow_service import validate_invoice_issue

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    if not invoice.can_issue():
        return jsonify({
            'error': f'Invoice cannot be issued from status: {invoice.status}',
            'current_status': invoice.status
        }), 400

    # Get estimate for guard validation
    estimate = PDREstimate.query.filter_by(id=invoice.estimate_id, tenant_id=tenant_id).first()
    if estimate:
        can_issue, reason = validate_invoice_issue(estimate, invoice)
        if not can_issue:
            EstimateActivity.log(
                estimate_id=estimate.id,
                activity_type='workflow_guard_blocked',
                user_id=user_id,
                activity_data={
                    'action': 'issue_invoice',
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'reason': reason
                }
            )
            return jsonify({'error': reason, 'code': 'GUARD_BLOCKED'}), 409

    # Issue the invoice
    invoice.issue()
    db.session.commit()

    # Log activity
    if estimate:
        EstimateActivity.log(
            estimate_id=estimate.id,
            activity_type='invoice_issued',
            user_id=user_id,
            activity_data={
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'total': float(invoice.total or 0),
                'payer_type': invoice.payer_type,
                'allocation_type': invoice.allocation_type
            }
        )

    return jsonify({
        'invoice': invoice.to_dict(),
        'message': f'Invoice {invoice.invoice_number} issued successfully'
    })


# ==============================================================================
# RECEIPT + EXPORT ENDPOINTS
# ==============================================================================

@customer_bp.route('/invoices/<int:invoice_id>/payments/<int:payment_id>/receipt.pdf', methods=['GET'])
@login_required
def download_payment_receipt(invoice_id, payment_id):
    """
    Download a PDF receipt for a payment.

    Returns:
        200: PDF file (application/pdf)
        404: Invoice or payment not found
    """
    from flask import Response
    from app.models.tenant.invoice import Invoice, Payment
    from app.models.tenant.pdr_estimate import PDREstimate, EstimateActivity
    from app.models.tenant.user import User
    from app.services.receipt_pdf_generator import generate_payment_receipt

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    # Get invoice
    invoice = Invoice.query.filter_by(id=invoice_id, tenant_id=tenant_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    # Get payment
    payment = Payment.query.filter_by(id=payment_id, invoice_id=invoice_id).first()
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Get estimate if linked
    estimate = None
    if invoice.estimate_id:
        estimate = PDREstimate.query.get(invoice.estimate_id)

    # Get collector name if available
    collected_by = None
    if payment.created_by:
        collector = User.query.get(payment.created_by)
        if collector:
            collected_by = collector.name or collector.email

    # Get company info from tenant settings (if available)
    # For now, use defaults
    company_name = 'HailTracker PDR'
    company_address = None
    company_phone = None

    # Try to get tenant info
    try:
        from app.models.tenant.tenant import Tenant
        tenant = Tenant.query.get(tenant_id)
        if tenant:
            company_name = tenant.company_name or company_name
    except:
        pass

    # Generate PDF
    pdf_bytes = generate_payment_receipt(
        payment=payment.to_dict(),
        invoice=invoice.to_dict(),
        estimate=estimate.to_dict() if estimate else None,
        company_name=company_name,
        company_address=company_address,
        company_phone=company_phone,
        collected_by=collected_by
    )

    # Log activity
    if invoice.estimate_id:
        EstimateActivity.log(
            estimate_id=invoice.estimate_id,
            activity_type='receipt_downloaded',
            user_id=user_id,
            activity_data={
                'payment_id': payment.id,
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'amount': float(payment.amount)
            }
        )

    # Return PDF
    filename = f"receipt_{invoice.invoice_number}_{payment.id}.pdf"
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': len(pdf_bytes)
        }
    )


@customer_bp.route('/exports/invoices.csv', methods=['GET'])
@login_required
def export_invoices_csv():
    """
    Export invoices as CSV.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        status: Filter by status
        payer_type: Filter by payer type

    Returns:
        200: CSV file (text/csv)
    """
    import csv
    from io import StringIO
    from flask import Response
    from datetime import datetime, timedelta
    from app.models.tenant.invoice import Invoice
    from app.models.tenant.pdr_estimate import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    # Parse date filters
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    status = request.args.get('status')
    payer_type = request.args.get('payer_type')

    # Default to last 30 days
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')

    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include end date
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Build query
    query = Invoice.query.filter(
        Invoice.tenant_id == tenant_id,
        Invoice.created_at >= start_dt,
        Invoice.created_at < end_dt
    )

    if status:
        query = query.filter(Invoice.status == status)
    if payer_type:
        query = query.filter(Invoice.payer_type == payer_type)

    invoices = query.order_by(Invoice.created_at.desc()).all()

    # Generate CSV
    output = StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'invoice_number',
        'status',
        'issued_at',
        'due_at',
        'payer_type',
        'payer_name',
        'allocation_type',
        'subtotal',
        'tax_total',
        'total',
        'amount_paid',
        'balance_due',
        'estimate_id',
        'job_id',
        'created_at'
    ])

    # Data rows
    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.status,
            inv.issued_at.isoformat() if inv.issued_at else '',
            inv.due_at.isoformat() if inv.due_at else '',
            inv.payer_type,
            inv.payer_name or '',
            inv.allocation_type or '',
            float(inv.subtotal or 0),
            float(inv.tax_total or 0),
            float(inv.total or 0),
            float(inv.amount_paid or 0),
            float(inv.balance_due),
            inv.estimate_id or '',
            inv.job_id or '',
            inv.created_at.isoformat() if inv.created_at else ''
        ])

    # Log activity (using first invoice's estimate if available)
    if invoices and invoices[0].estimate_id:
        EstimateActivity.log(
            estimate_id=invoices[0].estimate_id,
            activity_type='invoices_exported',
            user_id=user_id,
            activity_data={
                'count': len(invoices),
                'start_date': start_date,
                'end_date': end_date,
                'filters': {'status': status, 'payer_type': payer_type}
            }
        )

    # Return CSV
    csv_content = output.getvalue()
    filename = f"invoices_{start_date}_to_{end_date}.csv"

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': len(csv_content.encode('utf-8'))
        }
    )


@customer_bp.route('/exports/payments.csv', methods=['GET'])
@login_required
def export_payments_csv():
    """
    Export payments as CSV.

    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        method: Filter by payment method
        payer_type: Filter by invoice payer type

    Returns:
        200: CSV file (text/csv)
    """
    import csv
    from io import StringIO
    from flask import Response
    from datetime import datetime, timedelta
    from app.models.tenant.invoice import Invoice, Payment
    from app.models.tenant.user import User
    from app.models.tenant.pdr_estimate import EstimateActivity

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity.get('user_id')

    # Parse date filters
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    method = request.args.get('method')
    payer_type = request.args.get('payer_type')

    # Default to last 30 days
    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.utcnow().strftime('%Y-%m-%d')

    # Parse dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    # Build query - join with Invoice to get tenant filter
    query = Payment.query.join(Invoice).filter(
        Invoice.tenant_id == tenant_id,
        Payment.received_at >= start_dt,
        Payment.received_at < end_dt
    )

    if method:
        query = query.filter(Payment.method == method)
    if payer_type:
        query = query.filter(Invoice.payer_type == payer_type)

    payments = query.order_by(Payment.received_at.desc()).all()

    # Cache user names
    user_cache = {}

    def get_user_name(uid):
        if not uid:
            return ''
        if uid not in user_cache:
            user = User.query.get(uid)
            user_cache[uid] = user.name or user.email if user else ''
        return user_cache[uid]

    # Generate CSV
    output = StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'received_at',
        'invoice_number',
        'payer_type',
        'allocation_type',
        'method',
        'amount',
        'reference',
        'invoice_total',
        'invoice_balance_after',
        'user',
        'estimate_id',
        'job_id'
    ])

    # Data rows
    for pmt in payments:
        invoice = pmt.invoice
        # Calculate balance after this payment
        # This is approximate - we'd need to sum all payments before this one for exact
        balance_after = float(invoice.balance_due)

        writer.writerow([
            pmt.received_at.isoformat() if pmt.received_at else '',
            invoice.invoice_number,
            invoice.payer_type,
            invoice.allocation_type or '',
            pmt.method,
            float(pmt.amount or 0),
            pmt.reference or '',
            float(invoice.total or 0),
            balance_after,
            get_user_name(pmt.created_by),
            invoice.estimate_id or '',
            invoice.job_id or ''
        ])

    # Log activity
    if payments and payments[0].invoice.estimate_id:
        EstimateActivity.log(
            estimate_id=payments[0].invoice.estimate_id,
            activity_type='payments_exported',
            user_id=user_id,
            activity_data={
                'count': len(payments),
                'start_date': start_date,
                'end_date': end_date,
                'filters': {'method': method, 'payer_type': payer_type}
            }
        )

    # Return CSV
    csv_content = output.getvalue()
    filename = f"payments_{start_date}_to_{end_date}.csv"

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': len(csv_content.encode('utf-8'))
        }
    )


# ==============================================================================
# OPS COMMAND CENTER ENDPOINT
# ==============================================================================

@customer_bp.route('/ops/overview', methods=['GET'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def get_ops_overview():
    """
    Aggregated ops dashboard data - single endpoint to avoid N+1 queries.

    Uses existing models and WorkflowService internally. No new models or logic.

    Returns:
        200: {
            needs_attention: [...],  # Items requiring action
            job_stats: {scheduled: n, in_progress: n, completed: n},
            invoice_stats: {draft: n, issued: n, overdue: n, draft_total: $, overdue_total: $},
            bottlenecks: [...],  # Estimates stuck in insurer workflow
            leads_needing_followup: [...]
        }
    """
    from datetime import datetime, timedelta
    from sqlalchemy import and_, or_, func
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.job import Job
    from app.models.tenant.invoice import Invoice
    from app.models.tenant.lead import Lead
    from app.models.master.user import User
    from app.services.workflow_service import WorkflowService

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    # Time thresholds
    now = datetime.utcnow()
    bottleneck_threshold = now - timedelta(days=3)  # Submitted > 3 days ago
    followup_threshold = now - timedelta(days=2)  # No call in 2 days

    # =========================================================================
    # TODO: INDEX RECOMMENDATIONS for ops dashboard performance
    # Consider adding indexes on these columns if query performance degrades:
    # - Invoice.status, Invoice.due_at (overdue queries)
    # - Job.status, Job.scheduled_date (job board queries)
    # - PDREstimate.insurer_status, PDREstimate.customer_status (workflow queries)
    # - PDREstimate.submitted_to_insurer_at (bottleneck queries)
    # =========================================================================

    # =========================================================================
    # 1. NEEDS ATTENTION QUEUE (estimates needing action)
    # =========================================================================
    # Subquery to find estimate IDs that have a job
    estimates_with_job = db.session.query(Job.estimate_id).filter(
        Job.estimate_id.isnot(None)
    ).distinct().subquery()

    # Get estimates that need attention (not closed, has pending actions)
    # Limit to 15 to reduce WorkflowService N+1 overhead
    estimates_needing_action = PDREstimate.query.filter(
        PDREstimate.tenant_id == tenant_id,
        PDREstimate.status.notin_(['completed', 'cancelled']),
        or_(
            # Customer auth pending
            PDREstimate.customer_status.in_(['draft', 'pending_signature']),
            # Insurer workflow in progress
            PDREstimate.insurer_status.in_(['submitted', 'needs_revision']),
            # Approved but no job created (use subquery instead of relationship)
            and_(
                PDREstimate.insurer_status == 'approved',
                ~PDREstimate.id.in_(estimates_with_job)
            ),
        )
    ).order_by(PDREstimate.updated_at.desc()).limit(15).all()

    needs_attention = []
    # N+1 MITIGATION: WorkflowService queries invoices per estimate via lazy='dynamic' backref.
    # Limited to 15 estimates (down from 20) to keep query count acceptable (~15 invoice queries).
    # Future optimization: bulk fetch invoices and attach to estimates, or modify WorkflowService.
    for est in estimates_needing_action:
        # Get primary action and priority from workflow service
        try:
            workflow = WorkflowService(est)
            workflow_data = workflow.get_workflow()
            primary_action = workflow_data.get('primary_action')
            priority_score = workflow_data.get('priority_score', 50)
            priority_reason = workflow_data.get('priority_reason')
        except Exception:
            primary_action = None
            priority_score = 50
            priority_reason = None

        needs_attention.append({
            'type': 'estimate',
            'id': est.id,
            'identifier': est.estimate_number,
            'customer_status': est.customer_status,
            'insurer_status': est.insurer_status,
            'customer_name': est.customer_name,
            'vehicle_display': f"{est.vehicle_year or ''} {est.vehicle_make or ''} {est.vehicle_model or ''}".strip() or 'No vehicle',
            'total_price': float(est.total_price or 0),
            'primary_action': primary_action,
            'priority_score': priority_score,
            'priority_reason': priority_reason,
            'updated_at': est.updated_at.isoformat() if est.updated_at else None,
        })

    # Add jobs needing attention (scheduled or in_progress)
    jobs_needing_action = Job.query.filter(
        Job.tenant_id == tenant_id,
        Job.status.in_(['scheduled', 'in_progress'])
    ).order_by(Job.scheduled_date.asc()).limit(10).all()

    # BULK FETCH: Get all tech names in one query to avoid N+1 and ensure tenant safety
    tech_ids = [job.assigned_tech for job in jobs_needing_action if job.assigned_tech]
    techs_by_id = {}
    if tech_ids:
        techs = User.query.filter(
            User.id.in_(tech_ids),
            User.tenant_id == tenant_id  # TENANT SAFETY: Ensure tech belongs to same tenant
        ).all()
        techs_by_id = {t.id: t.name for t in techs}

    # BULK FETCH: Get blocker info using centralized helper (Stage 5O.1)
    # This ensures identical logic across ops/overview, notifications, and job queries
    job_ids_with_estimates = [(job.id, job.estimate_id) for job in jobs_needing_action]
    blocked_jobs = get_bulk_job_blockers(job_ids_with_estimates, tenant_id)

    for job in jobs_needing_action:
        # Check if job is blocked
        is_blocked = job.id in blocked_jobs
        blocker_info = blocked_jobs.get(job.id)

        # Compute job priority score
        if is_blocked:
            # Blocked jobs get high priority (75)
            issue_type = blocker_info['issue_type'] if blocker_info else 'issue'
            job_priority_score = 75
            job_priority_reason = f"Blocked: {issue_type.replace('_', ' ').title()}"
        elif job.status == 'in_progress':
            job_priority_score = 60
            job_priority_reason = 'Job in progress'
        elif job.status == 'scheduled':
            # Higher priority if scheduled for today/past
            if job.scheduled_date:
                days_until = (job.scheduled_date - now.date()).days if hasattr(job.scheduled_date, 'date') else (job.scheduled_date - now).days
                if days_until <= 0:
                    job_priority_score = 55
                    job_priority_reason = 'Scheduled for today' if days_until == 0 else f'Overdue {-days_until}d'
                else:
                    job_priority_score = 45
                    job_priority_reason = f'Scheduled in {days_until}d'
            else:
                job_priority_score = 45
                job_priority_reason = 'Scheduled'
        else:
            job_priority_score = 40
            job_priority_reason = None

        needs_attention.append({
            'type': 'job',
            'id': job.id,
            'identifier': job.job_number,
            'status': job.status,
            'customer_name': job.customer_name,
            'vehicle_display': f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or 'No vehicle',
            'total_amount': float(job.total_amount or 0),
            'scheduled_date': job.scheduled_date.isoformat() if job.scheduled_date else None,
            'assigned_tech': job.assigned_tech,
            'tech_name': techs_by_id.get(job.assigned_tech),  # Use bulk-fetched map
            'is_blocked': is_blocked,
            'blocker_info': blocker_info if is_blocked else None,
            'primary_action': {
                'key': 'start_job' if job.status == 'scheduled' else 'complete_job',
                'label': 'Start Job' if job.status == 'scheduled' else 'Complete Job',
            },
            'priority_score': job_priority_score,
            'priority_reason': job_priority_reason,
            'updated_at': job.updated_at.isoformat() if job.updated_at else None,
        })

    # Add draft/overdue invoices
    invoices_needing_action = Invoice.query.filter(
        Invoice.tenant_id == tenant_id,
        or_(
            Invoice.status == 'draft',
            and_(
                Invoice.status.in_(['issued', 'partial_paid']),
                Invoice.due_at < now
            )
        )
    ).order_by(Invoice.created_at.desc()).limit(10).all()

    for inv in invoices_needing_action:
        is_overdue = inv.due_at and inv.due_at < now and inv.status in ['issued', 'partial_paid']

        # Compute invoice priority score
        if is_overdue:
            days_overdue = (now - inv.due_at).days
            inv_priority_score = min(100, 80 + days_overdue)
            inv_priority_reason = f'Overdue {days_overdue}d (${float(inv.balance_due):.0f})'
        elif inv.status == 'partial_paid':
            inv_priority_score = 55
            inv_priority_reason = f'Partial payment (${float(inv.balance_due):.0f} due)'
        elif inv.status == 'draft':
            inv_priority_score = 45
            inv_priority_reason = 'Ready to issue'
        else:
            inv_priority_score = 50
            inv_priority_reason = None

        needs_attention.append({
            'type': 'invoice',
            'id': inv.id,
            'identifier': inv.invoice_number,
            'status': inv.status,
            'is_overdue': is_overdue,
            'payer_name': inv.payer_name,
            'payer_type': inv.payer_type,
            'total': float(inv.total or 0),
            'balance_due': float(inv.balance_due),
            'due_at': inv.due_at.isoformat() if inv.due_at else None,
            'primary_action': {
                'key': 'issue_invoice' if inv.status == 'draft' else 'collect_payment',
                'label': 'Issue Invoice' if inv.status == 'draft' else 'Collect Payment',
            },
            'priority_score': inv_priority_score,
            'priority_reason': inv_priority_reason,
            'updated_at': inv.updated_at.isoformat() if inv.updated_at else None,
        })

    # =========================================================================
    # 2. JOB STATS (grouped by status)
    # =========================================================================
    job_counts = db.session.query(
        Job.status,
        func.count(Job.id)
    ).filter(
        Job.tenant_id == tenant_id
    ).group_by(Job.status).all()

    job_stats = {
        'scheduled': 0,
        'in_progress': 0,
        'completed': 0,
        'cancelled': 0,
    }
    for status, count in job_counts:
        if status in job_stats:
            job_stats[status] = count

    # =========================================================================
    # 3. INVOICE STATS
    # =========================================================================
    invoice_counts = db.session.query(
        Invoice.status,
        func.count(Invoice.id),
        func.coalesce(func.sum(Invoice.total), 0),
        func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)
    ).filter(
        Invoice.tenant_id == tenant_id
    ).group_by(Invoice.status).all()

    invoice_stats = {
        'draft': 0,
        'draft_total': 0,
        'issued': 0,
        'issued_balance': 0,
        'partial_paid': 0,
        'partial_balance': 0,
        'paid': 0,
        'void': 0,
        'overdue': 0,
        'overdue_total': 0,
    }
    for status, count, total, balance in invoice_counts:
        invoice_stats[status] = count
        if status == 'draft':
            invoice_stats['draft_total'] = float(total or 0)
        elif status in ['issued', 'partial_paid']:
            invoice_stats[f'{status}_balance'] = float(balance or 0)

    # Count overdue separately
    overdue_result = db.session.query(
        func.count(Invoice.id),
        func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)
    ).filter(
        Invoice.tenant_id == tenant_id,
        Invoice.status.in_(['issued', 'partial_paid']),
        Invoice.due_at < now
    ).first()
    invoice_stats['overdue'] = overdue_result[0] or 0
    invoice_stats['overdue_total'] = float(overdue_result[1] or 0)

    # =========================================================================
    # 4. INSURANCE BOTTLENECKS (estimates stuck)
    # =========================================================================
    bottleneck_estimates = PDREstimate.query.filter(
        PDREstimate.tenant_id == tenant_id,
        or_(
            # Submitted to insurer > 3 days ago
            and_(
                PDREstimate.insurer_status == 'submitted',
                PDREstimate.submitted_to_insurer_at < bottleneck_threshold
            ),
            # Needs revision
            PDREstimate.insurer_status == 'needs_revision',
        )
    ).order_by(PDREstimate.submitted_to_insurer_at.asc()).limit(10).all()

    bottlenecks = []
    for est in bottleneck_estimates:
        days_waiting = 0
        if est.submitted_to_insurer_at:
            days_waiting = (now - est.submitted_to_insurer_at).days

        bottlenecks.append({
            'id': est.id,
            'estimate_number': est.estimate_number,
            'customer_name': est.customer_name,
            'insurance_company': est.insurance_company,
            'insurer_status': est.insurer_status,
            'days_waiting': days_waiting,
            'submitted_at': est.submitted_to_insurer_at.isoformat() if est.submitted_to_insurer_at else None,
            'total_price': float(est.total_price or 0),
        })

    # =========================================================================
    # 5. LEADS NEEDING FOLLOW-UP
    # =========================================================================
    from app.models.tenant.call import Call

    # Subquery to get last call date per lead
    last_call_subq = db.session.query(
        Call.lead_id,
        func.max(Call.called_at).label('last_call')
    ).group_by(Call.lead_id).subquery()

    # Leads that are new/contacted with no recent calls
    leads_needing_followup = db.session.query(Lead).outerjoin(
        last_call_subq,
        Lead.id == last_call_subq.c.lead_id
    ).filter(
        Lead.tenant_id == tenant_id,
        Lead.status.in_(['new', 'contacted']),
        or_(
            last_call_subq.c.last_call == None,
            last_call_subq.c.last_call < followup_threshold
        )
    ).order_by(Lead.created_at.desc()).limit(10).all()

    followups = []
    for lead in leads_needing_followup:
        followups.append({
            'id': lead.id,
            'business_name': lead.business_name,
            'contact_name': lead.contact_name,
            'phone': lead.phone,
            'status': lead.status,
            'source': lead.source,
            'created_at': lead.created_at.isoformat() if lead.created_at else None,
        })

    # =========================================================================
    # 6. TEAM MEMBERS (for assignment dropdowns)
    # =========================================================================
    team_members = User.query.filter(
        User.tenant_id == tenant_id,
        User.is_active == True,
        User.role.in_(['technician', 'estimator', 'salesman', 'desk', 'manager', 'owner'])
    ).all()

    team = [
        {
            'id': u.id,
            'name': u.name or u.email,
            'role': u.role,
        }
        for u in team_members
    ]

    # Sort needs_attention by priority_score DESC, then updated_at DESC
    needs_attention.sort(
        key=lambda x: (
            -x.get('priority_score', 50),  # Higher priority first
            x.get('updated_at') or '',  # More recent first (as fallback)
        ),
        reverse=False  # priority_score already negated, updated_at needs natural order
    )

    # =========================================================================
    # 7. DISPATCH INBOX (jobs needing dispatch attention)
    # =========================================================================
    # Thresholds for stale jobs
    stale_in_progress_threshold = now - timedelta(hours=6)
    stale_created_threshold = now - timedelta(hours=12)
    next_7_days = now + timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    # Fetch all jobs for dispatch inbox (blocked, unassigned, stale, scheduled today)
    dispatch_jobs = Job.query.filter(
        Job.tenant_id == tenant_id,
        Job.status.in_(['scheduled', 'in_progress']),
        or_(
            # Unassigned jobs scheduled within next 7 days
            and_(
                Job.assigned_tech.is_(None),
                or_(
                    Job.scheduled_date.is_(None),
                    Job.scheduled_date <= next_7_days.date()
                )
            ),
            # Jobs scheduled today that haven't started
            and_(
                Job.status == 'scheduled',
                Job.scheduled_date >= today_start.date(),
                Job.scheduled_date < today_end.date()
            ),
            # In-progress jobs that may be stale
            Job.status == 'in_progress'
        )
    ).order_by(Job.updated_at.desc()).limit(25).all()

    # BULK FETCH: Get tech names for dispatch jobs
    dispatch_tech_ids = list(set([job.assigned_tech for job in dispatch_jobs if job.assigned_tech]))
    dispatch_techs_by_id = {}
    if dispatch_tech_ids:
        dispatch_techs = User.query.filter(
            User.id.in_(dispatch_tech_ids),
            User.tenant_id == tenant_id  # TENANT SAFETY
        ).all()
        dispatch_techs_by_id = {t.id: t.name for t in dispatch_techs}

    # BULK FETCH: Get blocker info using centralized helper (Stage 5O.1)
    dispatch_job_ids_with_estimates = [(job.id, job.estimate_id) for job in dispatch_jobs]
    dispatch_blocked_jobs = get_bulk_job_blockers(dispatch_job_ids_with_estimates, tenant_id)

    dispatch_inbox = []
    for job in dispatch_jobs:
        is_blocked = job.id in dispatch_blocked_jobs
        blocker_info = dispatch_blocked_jobs.get(job.id)
        is_unassigned = job.assigned_tech is None
        is_today = job.scheduled_date and today_start.date() <= job.scheduled_date < today_end.date()

        # Check if in_progress is stale
        is_stale = False
        age_hours = None
        if job.status == 'in_progress':
            if job.updated_at and job.updated_at < stale_in_progress_threshold:
                is_stale = True
                age_hours = int((now - job.updated_at).total_seconds() / 3600)
            elif job.created_at and job.created_at < stale_created_threshold:
                is_stale = True
                age_hours = int((now - job.created_at).total_seconds() / 3600)

        # Determine if this job belongs in dispatch inbox
        include_in_dispatch = False
        priority_score = 50
        priority_reason = None
        primary_action = None

        if is_blocked:
            include_in_dispatch = True
            issue_type = blocker_info['issue_type'] if blocker_info else 'issue'
            parts_info = blocker_info.get('parts') if blocker_info else None

            # Enhanced priority for parts blockers with ETA logic
            if issue_type == 'waiting_on_parts' and parts_info:
                eta_str = parts_info.get('eta')
                if eta_str:
                    try:
                        # Parse ETA (can be date or datetime)
                        if 'T' in eta_str:
                            eta = datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
                        else:
                            eta = datetime.strptime(eta_str, '%Y-%m-%d')
                        hours_until_eta = (eta - now).total_seconds() / 3600

                        if hours_until_eta < 0:
                            # ETA missed
                            priority_score = 95
                            priority_reason = "Blocked: Parts ETA missed"
                        elif hours_until_eta <= 24:
                            # Arriving soon
                            priority_score = 80
                            priority_reason = "Blocked: Parts arriving soon"
                        else:
                            # Has ETA, not urgent
                            priority_score = 75
                            priority_reason = f"Blocked: Parts (ETA in {int(hours_until_eta / 24)}d)"
                    except (ValueError, TypeError):
                        # Invalid ETA format
                        priority_score = 85
                        priority_reason = "Blocked: Waiting On Parts"
                else:
                    # No ETA set - higher priority
                    priority_score = 90
                    priority_reason = "Blocked: Parts (no ETA)"
            else:
                # Non-parts blockers
                priority_score = 85
                priority_reason = f"Blocked: {issue_type.replace('_', ' ').title()}"

            primary_action = {'key': 'review_blocker', 'label': 'Review Blocker'}
        elif is_stale and job.status == 'in_progress':
            include_in_dispatch = True
            priority_score = 75
            priority_reason = f"Stale in progress ({age_hours}h)"
            primary_action = {'key': 'complete_job', 'label': 'Complete Job'}
        elif is_today and job.status == 'scheduled':
            include_in_dispatch = True
            priority_score = 65
            priority_reason = "Scheduled today, not started"
            primary_action = {'key': 'start_job', 'label': 'Start Job'}
        elif is_unassigned:
            include_in_dispatch = True
            priority_score = 55
            if job.scheduled_date:
                days_until = (job.scheduled_date - now.date()).days
                priority_reason = f"Unassigned, scheduled in {days_until}d" if days_until > 0 else "Unassigned, scheduled today"
            else:
                priority_reason = "Unassigned, no date"
            primary_action = {'key': 'assign_tech', 'label': 'Assign Tech'}

        if include_in_dispatch:
            dispatch_inbox.append({
                'id': job.id,
                'job_number': job.job_number,
                'status': job.status,
                'scheduled_date': job.scheduled_date.isoformat() if job.scheduled_date else None,
                'assigned_tech': job.assigned_tech,
                'tech_name': dispatch_techs_by_id.get(job.assigned_tech),
                'customer_name': job.customer_name,
                'vehicle_display': f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or 'No vehicle',
                'is_blocked': is_blocked,
                'blocker_info': blocker_info if is_blocked else None,
                'age_hours': age_hours,
                'primary_action': primary_action,
                'priority_score': priority_score,
                'priority_reason': priority_reason,
                'updated_at': job.updated_at.isoformat() if job.updated_at else None,
            })

    # Sort dispatch_inbox by priority_score DESC
    dispatch_inbox.sort(key=lambda x: -x.get('priority_score', 50))

    # =========================================================================
    # 8. TECH LOAD (workload per technician)
    # =========================================================================
    # Get all techs from team (role='tech')
    tech_members = [t for t in team if t['role'] == 'tech']

    # Query job counts per tech
    tech_job_counts = db.session.query(
        Job.assigned_tech,
        Job.status,
        func.count(Job.id)
    ).filter(
        Job.tenant_id == tenant_id,
        Job.assigned_tech.isnot(None),
        Job.status.in_(['scheduled', 'in_progress'])
    ).group_by(Job.assigned_tech, Job.status).all()

    # Build counts per tech
    tech_counts = {}  # tech_id -> {scheduled: n, in_progress: n}
    for tech_id, status, count in tech_job_counts:
        if tech_id not in tech_counts:
            tech_counts[tech_id] = {'scheduled': 0, 'in_progress': 0}
        if status in tech_counts[tech_id]:
            tech_counts[tech_id][status] = count

    # Count jobs scheduled today per tech
    today_jobs = db.session.query(
        Job.assigned_tech,
        func.count(Job.id)
    ).filter(
        Job.tenant_id == tenant_id,
        Job.assigned_tech.isnot(None),
        Job.scheduled_date >= today_start.date(),
        Job.scheduled_date < today_end.date(),
        Job.status.in_(['scheduled', 'in_progress'])
    ).group_by(Job.assigned_tech).all()

    tech_today = {tech_id: count for tech_id, count in today_jobs}

    # Count blocked jobs per tech (from dispatch_blocked_jobs)
    tech_blocked = {}
    for job in dispatch_jobs:
        if job.id in dispatch_blocked_jobs and job.assigned_tech:
            tech_blocked[job.assigned_tech] = tech_blocked.get(job.assigned_tech, 0) + 1

    # Get in-progress jobs per tech for in_progress_job field
    in_progress_jobs_by_tech = {}
    in_progress_jobs = Job.query.filter(
        Job.tenant_id == tenant_id,
        Job.status == 'in_progress',
        Job.assigned_tech.isnot(None)
    ).all()
    for ip_job in in_progress_jobs:
        if ip_job.assigned_tech not in in_progress_jobs_by_tech:
            in_progress_jobs_by_tech[ip_job.assigned_tech] = {
                'job_id': ip_job.id,
                'job_number': ip_job.job_number,
            }

    # Get latest check-in per tech (within last 24h)
    last_checkin_by_tech = {}
    checkin_cutoff = now - timedelta(hours=24)

    # Get all estimate_ids for in-progress jobs to query activities
    ip_estimate_ids = [j.estimate_id for j in in_progress_jobs if j.estimate_id]
    if ip_estimate_ids:
        recent_checkins = EstimateActivity.query.filter(
            EstimateActivity.estimate_id.in_(ip_estimate_ids),
            EstimateActivity.activity_type == 'job_checked_in',
            EstimateActivity.created_at >= checkin_cutoff,
        ).order_by(EstimateActivity.created_at.desc()).all()

        for checkin in recent_checkins:
            if checkin.user_id and checkin.user_id not in last_checkin_by_tech:
                metadata = checkin.metadata or {}
                last_checkin_by_tech[checkin.user_id] = {
                    'job_id': metadata.get('job_id'),
                    'job_number': metadata.get('job_number'),
                    'location': metadata.get('location'),
                    'at': metadata.get('checked_in_at') or checkin.created_at.isoformat(),
                }

    tech_load = []
    for tech in tech_members:
        tech_id = tech['id']
        counts = tech_counts.get(tech_id, {'scheduled': 0, 'in_progress': 0})
        tech_load.append({
            'tech_id': tech_id,
            'tech_name': tech['name'],
            'scheduled_today': tech_today.get(tech_id, 0),
            'in_progress': counts.get('in_progress', 0),
            'blocked': tech_blocked.get(tech_id, 0),
            'total_assigned': counts.get('scheduled', 0) + counts.get('in_progress', 0),
            'in_progress_job': in_progress_jobs_by_tech.get(tech_id),
            'last_checkin': last_checkin_by_tech.get(tech_id),
        })

    # Sort tech_load by total_assigned DESC
    tech_load.sort(key=lambda x: -x.get('total_assigned', 0))

    # =========================================================================
    # 8B. DISPATCH SUGGESTIONS (auto-assign recommendations)
    # =========================================================================
    # Build tech lookup for quick access
    tech_load_by_id = {t['tech_id']: t for t in tech_load}

    def compute_tech_score(tech_info, job_item):
        """
        Compute assignment score for a tech-job pair.
        Higher score = better fit.

        Heuristic (simple, explainable):
        - Start at 100
        - Subtract for in_progress jobs (busy right now)
        - Subtract for blocked jobs (capacity issues)
        - Subtract for scheduled_today (already has work)
        - Subtract for total_assigned (overall workload)
        - Bonus if job is scheduled today and tech has light schedule
        - Bonus if job is high priority and tech is available
        """
        score = 100
        reasons = []

        in_progress = tech_info.get('in_progress', 0)
        blocked = tech_info.get('blocked', 0)
        scheduled_today = tech_info.get('scheduled_today', 0)
        total_assigned = tech_info.get('total_assigned', 0)

        # Subtract for current workload
        score -= in_progress * 20
        score -= blocked * 25
        score -= scheduled_today * 10
        score -= total_assigned * 2

        # Track reasons
        if in_progress == 0:
            reasons.append("No in-progress jobs")
        elif in_progress == 1:
            reasons.append("1 job in progress")
        else:
            reasons.append(f"{in_progress} jobs in progress")

        if blocked == 0:
            reasons.append("No blocked jobs")
        elif blocked > 0:
            reasons.append(f"{blocked} blocked job(s)")

        if scheduled_today < 3:
            reasons.append("Light schedule today")

        # Bonus for job scheduled today with light tech schedule
        is_job_today = job_item.get('scheduled_date') and today_start.date().isoformat() == job_item.get('scheduled_date', '')[:10]
        if is_job_today and scheduled_today < 3:
            score += 10
            reasons.append("Available for today's schedule")

        # Bonus for high priority job with available tech
        if job_item.get('priority_score', 0) >= 70 and in_progress == 0:
            score += 10
            reasons.append("Available for priority job")

        # Clamp score
        score = max(0, min(100, score))

        return score, reasons

    dispatch_suggestions = []

    # Only generate suggestions for jobs that need assignment or attention
    for job_item in dispatch_inbox[:20]:  # Limit to 20 suggestions
        # Skip already assigned jobs that aren't stale
        if job_item.get('assigned_tech') and not job_item.get('age_hours'):
            continue

        # Compute scores for all techs
        tech_scores = []
        for tech in tech_load:
            score, reasons = compute_tech_score(tech, job_item)
            tech_scores.append({
                'tech_id': tech['tech_id'],
                'tech_name': tech['tech_name'],
                'score': score,
                'reasons': reasons,
            })

        # Sort by score DESC
        tech_scores.sort(key=lambda x: -x['score'])

        # Determine suggestion
        suggested_tech_id = None
        suggested_tech_name = None
        confidence = 0
        reasons = []
        alternatives = []

        if tech_scores:
            top = tech_scores[0]
            suggested_tech_id = top['tech_id']
            suggested_tech_name = top['tech_name']
            confidence = top['score']

            # Build concise reasons
            if top['score'] >= 80:
                reasons.append("Lowest workload")
            if any("No blocked" in r for r in top['reasons']):
                reasons.append("No blocked jobs")
            if any("Light schedule" in r for r in top['reasons']):
                reasons.append("Light schedule today")
            if any("priority" in r.lower() for r in top['reasons']):
                reasons.append("Available for priority job")

            # Reduce confidence if top 2 are close
            if len(tech_scores) >= 2:
                second = tech_scores[1]
                if top['score'] - second['score'] < 5:
                    confidence = max(0, confidence - 15)
                    reasons.append("Close competition")

            # Reduce confidence if all scores are low
            if top['score'] < 40:
                confidence = max(0, confidence - 20)
                reasons.append("All techs busy")

            # Clamp confidence
            confidence = max(0, min(100, confidence))

            # Alternatives (top 3)
            alternatives = [
                {
                    'tech_id': t['tech_id'],
                    'tech_name': t['tech_name'],
                    'score': t['score'],
                    'reason': t['reasons'][0] if t['reasons'] else '',
                }
                for t in tech_scores[:3]
            ]

        dispatch_suggestions.append({
            'job_id': job_item['id'],
            'job_number': job_item['job_number'],
            'scheduled_date': job_item.get('scheduled_date'),
            'status': job_item['status'],
            'priority_score': job_item.get('priority_score', 50),
            'priority_reason': job_item.get('priority_reason'),
            'suggested_tech_id': suggested_tech_id,
            'suggested_tech_name': suggested_tech_name,
            'confidence': confidence,
            'reasons': reasons[:4],  # Max 4 reasons
            'alternatives': alternatives,
        })

    # =========================================================================
    # 9. SUPPLEMENTS QUEUE (draft or sent supplements)
    # =========================================================================
    from app.models.tenant.estimate_supplement import EstimateSupplement

    supplements_needing_action = db.session.query(
        EstimateSupplement,
        PDREstimate.estimate_number,
        PDREstimate.customer_name,
        PDREstimate.total_price
    ).join(
        PDREstimate,
        EstimateSupplement.estimate_id == PDREstimate.id
    ).filter(
        PDREstimate.tenant_id == tenant_id,
        EstimateSupplement.status.in_(['draft', 'sent'])
    ).order_by(EstimateSupplement.created_at.desc()).limit(15).all()

    supplements_queue = []
    for supp, est_number, cust_name, est_total in supplements_needing_action:
        days_open = (now - supp.created_at).days if supp.created_at else 0

        # Priority for supplements
        if supp.status == 'draft':
            supp_priority = 85
            supp_reason = f"Supplement #{supp.supplement_number} draft"
        elif supp.status == 'sent' and days_open >= 7:
            supp_priority = 75
            supp_reason = f"Supplement sent {days_open}d ago"
        elif supp.status == 'sent' and days_open >= 3:
            supp_priority = 65
            supp_reason = f"Supplement sent {days_open}d ago"
        else:
            supp_priority = 55
            supp_reason = "Supplement awaiting response"

        supplements_queue.append({
            'estimate_id': supp.estimate_id,
            'estimate_number': est_number,
            'supplement_id': supp.id,
            'supplement_number': supp.supplement_number,
            'status': supp.status,
            'discovery_type': supp.discovery_type,
            'delta_amount': float(supp.delta_amount) if supp.delta_amount else 0,
            'customer_name': cust_name,
            'created_at': supp.created_at.isoformat() if supp.created_at else None,
            'sent_at': supp.sent_at.isoformat() if supp.sent_at else None,
            'days_open': days_open,
            'priority_score': supp_priority,
            'priority_reason': supp_reason,
        })

    # Sort supplements by priority
    supplements_queue.sort(key=lambda x: -x.get('priority_score', 50))

    # =========================================================================
    # 10. REVISIONS QUEUE (needs_revision or submitted long time)
    # =========================================================================
    # Get estimates needing revision or waiting on insurer
    revisions_estimates = PDREstimate.query.filter(
        PDREstimate.tenant_id == tenant_id,
        PDREstimate.status.notin_(['completed', 'cancelled']),
        or_(
            PDREstimate.insurer_status == 'needs_revision',
            and_(
                PDREstimate.insurer_status == 'submitted',
                PDREstimate.submitted_to_insurer_at < now - timedelta(days=3)
            )
        )
    ).order_by(PDREstimate.submitted_to_insurer_at.asc()).limit(15).all()

    revisions_queue = []
    for est in revisions_estimates:
        days_waiting = 0
        if est.submitted_to_insurer_at:
            days_waiting = (now - est.submitted_to_insurer_at).days

        # Priority scoring
        if est.insurer_status == 'needs_revision':
            rev_priority = 90
            rev_reason = "Needs revision"
        elif days_waiting >= 14:
            rev_priority = 80
            rev_reason = f"Waiting on insurer: {days_waiting} days"
        elif days_waiting >= 7:
            rev_priority = 70
            rev_reason = f"Waiting on insurer: {days_waiting} days"
        else:
            rev_priority = 60
            rev_reason = f"Waiting on insurer: {days_waiting} days"

        revisions_queue.append({
            'estimate_id': est.id,
            'estimate_number': est.estimate_number,
            'customer_name': est.customer_name,
            'insurance_company': est.insurance_company,
            'insurer_status': est.insurer_status,
            'submitted_at': est.submitted_to_insurer_at.isoformat() if est.submitted_to_insurer_at else None,
            'days_waiting': days_waiting,
            'total_price': float(est.total_price or 0),
            'priority_score': rev_priority,
            'priority_reason': rev_reason,
        })

    # Sort revisions by priority
    revisions_queue.sort(key=lambda x: -x.get('priority_score', 50))

    # =========================================================================
    # 11. REVENUE AT RISK (totals for dashboard cards)
    # =========================================================================
    # Needs revision total
    needs_revision_total = db.session.query(
        func.coalesce(func.sum(PDREstimate.total_price), 0)
    ).filter(
        PDREstimate.tenant_id == tenant_id,
        PDREstimate.insurer_status == 'needs_revision',
        PDREstimate.status.notin_(['completed', 'cancelled'])
    ).scalar() or 0

    # Submitted waiting total (> 3 days)
    submitted_waiting_total = db.session.query(
        func.coalesce(func.sum(PDREstimate.total_price), 0)
    ).filter(
        PDREstimate.tenant_id == tenant_id,
        PDREstimate.insurer_status == 'submitted',
        PDREstimate.submitted_to_insurer_at < now - timedelta(days=3),
        PDREstimate.status.notin_(['completed', 'cancelled'])
    ).scalar() or 0

    # Draft supplements total (delta_amount)
    draft_supplements_total = db.session.query(
        func.coalesce(func.sum(EstimateSupplement.delta_amount), 0)
    ).join(
        PDREstimate,
        EstimateSupplement.estimate_id == PDREstimate.id
    ).filter(
        PDREstimate.tenant_id == tenant_id,
        EstimateSupplement.status == 'draft'
    ).scalar() or 0

    revenue_at_risk = {
        'needs_revision_total': float(needs_revision_total),
        'needs_revision_count': len([r for r in revisions_queue if r['insurer_status'] == 'needs_revision']),
        'submitted_waiting_total': float(submitted_waiting_total),
        'submitted_waiting_count': len([r for r in revisions_queue if r['insurer_status'] == 'submitted']),
        'draft_supplements_total': float(draft_supplements_total),
        'draft_supplements_count': len([s for s in supplements_queue if s['status'] == 'draft']),
    }

    # =========================================================================
    # 12. PARTS REQUESTS (Stage 5Q)
    # =========================================================================
    from app.models.tenant.part_request import PartRequest, PARTS_STATUS_VALUES as PR_STATUS_VALUES

    # Get open parts requests (not installed)
    open_requests = PartRequest.query.filter(
        PartRequest.tenant_id == tenant_id,
        PartRequest.parts_status != 'installed'
    ).order_by(PartRequest.updated_at.desc()).limit(50).all()

    # Get job info for parts requests
    pr_job_ids = list(set([r.job_id for r in open_requests if r.job_id]))
    pr_jobs_by_id = {}
    pr_techs_by_id = {}
    if pr_job_ids:
        pr_jobs = Job.query.filter(Job.id.in_(pr_job_ids), Job.tenant_id == tenant_id).all()
        pr_jobs_by_id = {j.id: j for j in pr_jobs}
        pr_tech_ids = list(set([j.assigned_tech for j in pr_jobs if j.assigned_tech]))
        if pr_tech_ids:
            pr_techs = User.query.filter(User.id.in_(pr_tech_ids), User.tenant_id == tenant_id).all()
            pr_techs_by_id = {t.id: t.name for t in pr_techs}

    # Stage 5S: Get pricing previews for parts requests
    from app.services.parts_pricing_service import get_bulk_price_previews, get_total_exposure
    pr_pricing_previews = get_bulk_price_previews(open_requests, tenant_id)

    parts_requests = []
    for req in open_requests:
        item = req.to_dict()
        job = pr_jobs_by_id.get(req.job_id)
        if job:
            item['job_number'] = job.job_number
            item['customer_name'] = job.customer_name
            item['vehicle_display'] = f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or 'No vehicle'
            item['tech_name'] = pr_techs_by_id.get(job.assigned_tech)
        # Stage 5S: Add pricing preview
        item['pricing_preview'] = pr_pricing_previews.get(req.id)
        parts_requests.append(item)

    # Stage 5S: Calculate total exposure
    parts_exposure = get_total_exposure(open_requests, tenant_id)

    # Get counts by status
    pr_status_counts = db.session.query(
        PartRequest.parts_status,
        func.count(PartRequest.id)
    ).filter(
        PartRequest.tenant_id == tenant_id,
        PartRequest.parts_status != 'installed'
    ).group_by(PartRequest.parts_status).all()
    parts_requests_counts = {s: 0 for s in PR_STATUS_VALUES}
    for status, count in pr_status_counts:
        parts_requests_counts[status] = count

    # =========================================================================
    # 13. PARTS REQUESTS ATTENTION (Stage 5V)
    # =========================================================================
    # Identify "at-risk" part requests for priority attention
    parts_requests_attention = []
    severity_counts = {'critical': 0, 'high': 0, 'warn': 0}
    total_approved_exposure = 0.0

    for item in parts_requests:
        req_id = item['id']
        parts_status = item['parts_status']
        eta_str = item.get('eta')
        approved_to_order = item.get('approved_to_order', False)
        approved_amount = item.get('approved_amount')

        # Track approved exposure
        if approved_to_order and approved_amount:
            total_approved_exposure += float(approved_amount)

        # Calculate age
        status_updated = item.get('status_updated_at') or item.get('updated_at') or item.get('created_at')
        if status_updated:
            try:
                if isinstance(status_updated, str):
                    ref_time = datetime.fromisoformat(status_updated.replace('Z', '+00:00'))
                else:
                    ref_time = status_updated
                age_days = (now - ref_time).days if hasattr(ref_time, 'days') else (now - ref_time.replace(tzinfo=None)).days
            except (ValueError, TypeError):
                age_days = 0
        else:
            age_days = 0

        # Check ETA overdue
        eta_overdue = False
        eta_days_overdue = None
        if eta_str:
            try:
                eta_dt = datetime.fromisoformat(eta_str.replace('Z', '+00:00')).replace(tzinfo=None)
                if eta_dt < now and parts_status not in ['received', 'installed']:
                    eta_overdue = True
                    eta_days_overdue = (now - eta_dt).days
            except (ValueError, TypeError):
                pass

        # Determine priority score and severity
        priority_score = 0
        priority_reason = None
        severity = None

        if parts_status == 'exception':
            priority_score = 85
            priority_reason = 'Exception - needs resolution'
            severity = 'critical'
        elif eta_overdue:
            priority_score = 95
            priority_reason = f'ETA missed by {eta_days_overdue}d'
            severity = 'critical'
        elif parts_status == 'ordered' and not eta_str:
            if age_days >= 2:
                priority_score = 90
                priority_reason = f'Ordered {age_days}d, no ETA'
                severity = 'critical'
            else:
                priority_score = 90
                priority_reason = 'Ordered without ETA'
                severity = 'high'
        elif parts_status == 'approved_to_order':
            if age_days >= 5:
                priority_score = 85
                priority_reason = f'Approved {age_days}d - not ordered'
                severity = 'critical'
            elif age_days >= 3:
                priority_score = 75
                priority_reason = f'Approved {age_days}d - not ordered'
                severity = 'high'
            elif age_days >= 1:
                priority_score = 65
                priority_reason = f'Approved {age_days}d - not ordered'
                severity = 'warn'
        elif parts_status == 'shipped':
            shipped_at_str = item.get('shipped_at')
            if shipped_at_str:
                try:
                    shipped_dt = datetime.fromisoformat(shipped_at_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    days_shipped = (now - shipped_dt).days
                except (ValueError, TypeError):
                    days_shipped = age_days
            else:
                days_shipped = age_days
            if days_shipped >= 10:
                priority_score = 80
                priority_reason = f'Shipped {days_shipped}d - not received'
                severity = 'critical'
            elif days_shipped >= 5:
                priority_score = 70
                priority_reason = f'Shipped {days_shipped}d - not received'
                severity = 'high'
            elif days_shipped >= 3:
                priority_score = 60
                priority_reason = f'Shipped {days_shipped}d - not received'
                severity = 'warn'

        # Add to attention list if escalated
        if severity:
            severity_counts[severity] += 1
            attention_item = dict(item)
            attention_item['priority_score'] = priority_score
            attention_item['priority_reason'] = priority_reason
            attention_item['severity'] = severity
            attention_item['age_days'] = age_days
            if eta_days_overdue is not None:
                attention_item['eta_days_overdue'] = eta_days_overdue
            parts_requests_attention.append(attention_item)

    # Sort by priority score descending
    parts_requests_attention.sort(key=lambda x: -x.get('priority_score', 0))
    parts_requests_attention = parts_requests_attention[:25]

    # Build stats summary
    parts_requests_stats = {
        'counts_by_status': parts_requests_counts,
        'counts_by_severity': severity_counts,
        'total_open': sum(parts_requests_counts.values()),
        'total_attention': len(parts_requests_attention),
        'total_approved_exposure': total_approved_exposure,
    }

    return jsonify({
        'needs_attention': needs_attention,
        'job_stats': job_stats,
        'invoice_stats': invoice_stats,
        'bottlenecks': bottlenecks,
        'leads_needing_followup': followups,
        'team': team,
        'dispatch_inbox': dispatch_inbox,
        'tech_load': tech_load,
        'dispatch_suggestions': dispatch_suggestions,
        'supplements_queue': supplements_queue,
        'revisions_queue': revisions_queue,
        'revenue_at_risk': revenue_at_risk,
        # Stage 5Q: Parts requests
        'parts_requests': parts_requests,
        'parts_requests_counts': parts_requests_counts,
        # Stage 5S: Parts exposure summary
        'parts_exposure': parts_exposure,
        # Stage 5V: Parts requests attention + stats
        'parts_requests_attention': parts_requests_attention,
        'parts_requests_stats': parts_requests_stats,
    })


# ==============================================================================
# WORK INBOX / NOTIFICATIONS (Stage 5J)
# ==============================================================================

# Activity type to human-readable title mapping
ACTIVITY_TITLES = {
    'email_sent': 'Estimate sent to adjuster',
    'email_failed': 'Email send failed',
    'supplement_created': 'Supplement created',
    'supplement_sent': 'Supplement sent to insurer',
    'supplement_failed': 'Supplement send failed',
    'job_created_from_estimate': 'Job created',
    'job_status_changed': 'Job status changed',
    'job_blocked': 'Job flagged as blocked',
    'job_blocker_cleared': 'Job blocker resolved',
    'invoice_created': 'Invoice created',
    'invoice_created_insurer': 'Insurer invoice created',
    'invoice_created_customer': 'Customer invoice created',
    'invoice_issued': 'Invoice issued',
    'invoice_voided': 'Invoice voided',
    'payment_recorded': 'Payment received',
    'receipt_downloaded': 'Receipt downloaded',
    'dispute_pack_downloaded': 'Dispute pack downloaded',
    'share_link_created': 'Share link created',
    'share_link_opened': 'Customer viewed estimate',
    'share_downloaded_pdf': 'Customer downloaded PDF',
    'signature_requested': 'Signature requested',
    'customer_authorized': 'Customer authorized estimate',
    'insurer_approved': 'Insurer approved estimate',
    'insurer_declined': 'Insurer declined estimate',
    'insurer_submitted': 'Submitted to insurer',
    'insurer_needs_revision': 'Insurer requested revision',
    'estimate_status_changed': 'Estimate status changed',
    'version_created': 'New version created',
    'billing_updated': 'Billing information updated',
}

# Activity types to entity mapping
ACTIVITY_ENTITY_MAP = {
    'supplement_created': 'supplement',
    'supplement_sent': 'supplement',
    'supplement_failed': 'supplement',
    'job_created_from_estimate': 'job',
    'job_status_changed': 'job',
    'job_blocked': 'job',
    'job_blocker_cleared': 'job',
    'invoice_created': 'invoice',
    'invoice_created_insurer': 'invoice',
    'invoice_created_customer': 'invoice',
    'invoice_issued': 'invoice',
    'invoice_voided': 'invoice',
    'payment_recorded': 'invoice',
    'receipt_downloaded': 'invoice',
}


@customer_bp.route('/notifications', methods=['GET'])
@login_required
def get_work_inbox():
    """
    Work Inbox / Notifications feed.

    Combines recent activity events with attention items.
    Role-aware: tech/sales see only their scope.

    Query params:
        limit: Max items (default 50, max 200)
        since: ISO datetime to filter activities after
        types: Comma-separated activity types filter
        assigned_to_me: If "1", show only items assigned to current user

    Returns:
        200: {
            feed: [...],  # Combined activity + attention items
            summary: { critical: n, high: n, standard: n }
        }
    """
    from datetime import datetime, timedelta
    from sqlalchemy import and_, or_, func, desc
    from app.extensions import db
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.job import Job
    from app.models.tenant.invoice import Invoice
    from app.models.tenant.lead import Lead
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.user import User
    from app.services.workflow_service import WorkflowService

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']
    user_role = identity.get('role', '')

    # Parse query params
    limit = min(request.args.get('limit', 50, type=int), 200)
    since_param = request.args.get('since')
    types_param = request.args.get('types')
    assigned_to_me = request.args.get('assigned_to_me') == '1'
    include_escalations = request.args.get('escalations') == '1'

    # Parse since datetime
    since_dt = None
    if since_param:
        try:
            since_dt = datetime.fromisoformat(since_param.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass

    # Default to last 14 days if no since provided
    now = datetime.utcnow()
    if not since_dt:
        since_dt = now - timedelta(days=14)

    # Parse types filter
    types_filter = None
    if types_param:
        types_filter = [t.strip() for t in types_param.split(',') if t.strip()]

    # Determine if user has restricted scope (tech/sales)
    is_restricted_role = user_role in ['tech', 'technician', 'sales', 'salesman']

    # =========================================================================
    # 1. RECENT ACTIVITIES (from EstimateActivity)
    # =========================================================================
    # Build base query with tenant safety via estimate join
    activity_query = db.session.query(
        EstimateActivity,
        PDREstimate.estimate_number,
        PDREstimate.customer_name,
        PDREstimate.vehicle_year,
        PDREstimate.vehicle_make,
        PDREstimate.vehicle_model,
    ).join(
        PDREstimate,
        EstimateActivity.estimate_id == PDREstimate.id
    ).filter(
        PDREstimate.tenant_id == tenant_id,
        EstimateActivity.created_at > since_dt
    )

    # Apply types filter
    if types_filter:
        activity_query = activity_query.filter(
            EstimateActivity.activity_type.in_(types_filter)
        )

    # For restricted roles, filter to their own activities or assigned items
    if is_restricted_role and assigned_to_me:
        # Only show activities where user was the actor or is assigned
        # Join to jobs to check assignment
        activity_query = activity_query.outerjoin(
            Job,
            and_(
                Job.estimate_id == PDREstimate.id,
                Job.assigned_tech == user_id
            )
        ).filter(
            or_(
                EstimateActivity.user_id == user_id,
                Job.id.isnot(None)
            )
        )

    # Order by created_at desc and limit
    activities = activity_query.order_by(
        desc(EstimateActivity.created_at)
    ).limit(limit).all()

    feed = []

    for activity, est_number, cust_name, v_year, v_make, v_model in activities:
        activity_type = activity.activity_type
        activity_meta = activity.activity_data or {}

        # Build title and subtitle
        title = ACTIVITY_TITLES.get(activity_type, activity_type.replace('_', ' ').title())
        vehicle_display = f"{v_year or ''} {v_make or ''} {v_model or ''}".strip() or 'No vehicle'
        subtitle = f"{est_number} • {cust_name or 'Unknown'} • {vehicle_display}"

        # Determine entity type
        entity = ACTIVITY_ENTITY_MAP.get(activity_type, 'estimate')

        # Get entity_id for routing
        entity_id = activity.estimate_id
        route = f"/estimating/{activity.estimate_id}"

        # Override for specific entity types
        if entity == 'job' and activity_meta.get('job_id'):
            entity_id = activity_meta['job_id']
            route = f"/jobs/{entity_id}"
        elif entity == 'invoice' and activity_meta.get('invoice_id'):
            entity_id = activity_meta['invoice_id']
            route = f"/invoices/{entity_id}"
        elif entity == 'supplement' and activity_meta.get('supplement_id'):
            # Supplements link to estimate with supplement tab
            route = f"/estimating/{activity.estimate_id}?tab=supplements"

        # Assign base priority (activities are informational, lower priority)
        priority_score = 30
        priority_reason = None

        # Bump priority for failures or blocked items
        if 'failed' in activity_type:
            priority_score = 70
            priority_reason = 'Action failed'
        elif activity_type == 'job_blocked':
            priority_score = 75
            priority_reason = 'Job blocked'
        elif activity_type == 'insurer_needs_revision':
            priority_score = 80
            priority_reason = 'Revision needed'
        elif activity_type == 'insurer_declined':
            priority_score = 75
            priority_reason = 'Declined'

        feed.append({
            'id': f"act:{activity.id}",
            'kind': 'activity',
            'entity': entity,
            'entity_id': entity_id,
            'title': title,
            'subtitle': subtitle,
            'timestamp': activity.created_at.isoformat() if activity.created_at else None,
            'priority_score': priority_score,
            'priority_reason': priority_reason,
            'route': route,
            'primary_action': None,
            'meta': metadata,
        })

    # =========================================================================
    # 2. ATTENTION ITEMS (from existing ops overview logic)
    # =========================================================================
    # Only include attention items for non-activity-only requests
    # and for roles that should see them
    if not types_filter or 'attention' in (types_filter or []):
        attention_limit = max(15, limit // 3)

        # --- Estimates needing attention ---
        estimates_with_job = db.session.query(Job.estimate_id).filter(
            Job.estimate_id.isnot(None)
        ).distinct().subquery()

        estimates_query = PDREstimate.query.filter(
            PDREstimate.tenant_id == tenant_id,
            PDREstimate.status.notin_(['completed', 'cancelled']),
            or_(
                PDREstimate.customer_status.in_(['draft', 'pending_signature']),
                PDREstimate.insurer_status.in_(['submitted', 'needs_revision']),
                and_(
                    PDREstimate.insurer_status == 'approved',
                    ~PDREstimate.id.in_(estimates_with_job)
                ),
            )
        )

        # For restricted roles with assigned_to_me, skip estimate attention
        # (they primarily care about jobs)
        if not (is_restricted_role and assigned_to_me):
            estimates_needing_action = estimates_query.order_by(
                PDREstimate.updated_at.desc()
            ).limit(attention_limit).all()

            for est in estimates_needing_action:
                # Get workflow for primary action and priority
                try:
                    workflow = WorkflowService(est)
                    workflow_data = workflow.get_workflow()
                    primary_action = workflow_data.get('primary_action')
                    priority_score = workflow_data.get('priority_score', 50)
                    priority_reason = workflow_data.get('priority_reason')
                except Exception:
                    primary_action = None
                    priority_score = 50
                    priority_reason = None

                vehicle_display = f"{est.vehicle_year or ''} {est.vehicle_make or ''} {est.vehicle_model or ''}".strip() or 'No vehicle'

                # Build primary action with route
                action_with_route = None
                if primary_action:
                    action_with_route = {
                        'key': primary_action.get('key'),
                        'label': primary_action.get('label'),
                        'route': f"/estimating/{est.id}",
                    }

                feed.append({
                    'id': f"wf:estimate:{est.id}",
                    'kind': 'attention',
                    'entity': 'estimate',
                    'entity_id': est.id,
                    'title': f"Estimate {est.estimate_number} needs action",
                    'subtitle': f"{est.customer_name or 'Unknown'} • {vehicle_display}",
                    'timestamp': est.updated_at.isoformat() if est.updated_at else None,
                    'priority_score': priority_score,
                    'priority_reason': priority_reason,
                    'route': f"/estimating/{est.id}",
                    'primary_action': action_with_route,
                    'meta': {
                        'customer_status': est.customer_status,
                        'insurer_status': est.insurer_status,
                        'total_price': float(est.total_price or 0),
                    },
                })

        # --- Jobs needing attention ---
        jobs_query = Job.query.filter(
            Job.tenant_id == tenant_id,
            Job.status.in_(['scheduled', 'in_progress'])
        )

        # For assigned_to_me, filter to user's assigned jobs
        if assigned_to_me:
            jobs_query = jobs_query.filter(Job.assigned_tech == user_id)

        jobs_needing_action = jobs_query.order_by(
            Job.scheduled_date.asc()
        ).limit(attention_limit).all()

        # Bulk fetch tech names
        tech_ids = [job.assigned_tech for job in jobs_needing_action if job.assigned_tech]
        techs_by_id = {}
        if tech_ids:
            techs = User.query.filter(
                User.id.in_(tech_ids),
                User.tenant_id == tenant_id
            ).all()
            techs_by_id = {t.id: t.name for t in techs}

        # Check for blocked jobs
        estimate_ids_for_jobs = [job.estimate_id for job in jobs_needing_action if job.estimate_id]
        blocked_jobs = {}
        if estimate_ids_for_jobs:
            blocker_threshold = now - timedelta(days=7)
            recent_blockers = EstimateActivity.query.filter(
                EstimateActivity.estimate_id.in_(estimate_ids_for_jobs),
                EstimateActivity.activity_type == 'job_blocked',
                EstimateActivity.created_at > blocker_threshold
            ).order_by(EstimateActivity.created_at.desc()).all()

            cleared_blockers = EstimateActivity.query.filter(
                EstimateActivity.estimate_id.in_(estimate_ids_for_jobs),
                EstimateActivity.activity_type == 'job_blocker_cleared',
                EstimateActivity.created_at > blocker_threshold
            ).order_by(EstimateActivity.created_at.desc()).all()

            cleared_job_ids = set()
            for cleared in cleared_blockers:
                if cleared.metadata and cleared.metadata.get('job_id'):
                    cleared_job_ids.add(cleared.metadata['job_id'])

            for blocker in recent_blockers:
                if blocker.metadata and blocker.metadata.get('job_id'):
                    job_id = blocker.metadata['job_id']
                    if job_id not in cleared_job_ids and job_id not in blocked_jobs:
                        blocked_jobs[job_id] = {
                            'issue_type': blocker.metadata.get('issue_type', 'other'),
                            'notes': blocker.metadata.get('notes', ''),
                        }

        for job in jobs_needing_action:
            is_blocked = job.id in blocked_jobs
            blocker_info = blocked_jobs.get(job.id)

            # Compute priority
            if is_blocked:
                job_priority = 75
                job_reason = f"Blocked: {blocker_info['issue_type'].replace('_', ' ').title()}" if blocker_info else 'Blocked'
            elif job.status == 'in_progress':
                job_priority = 60
                job_reason = 'In progress'
            elif job.scheduled_date:
                days_until = (job.scheduled_date - now.date()).days if hasattr(job.scheduled_date, 'date') else 0
                if days_until <= 0:
                    job_priority = 65
                    job_reason = 'Scheduled today' if days_until == 0 else f'Overdue {-days_until}d'
                else:
                    job_priority = 45
                    job_reason = f'Scheduled in {days_until}d'
            else:
                job_priority = 45
                job_reason = 'Scheduled'

            vehicle_display = f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or 'No vehicle'
            tech_name = techs_by_id.get(job.assigned_tech) or 'Unassigned'

            primary_action = {
                'key': 'start_job' if job.status == 'scheduled' else 'complete_job',
                'label': 'Start' if job.status == 'scheduled' else 'Complete',
                'route': f"/jobs/{job.id}",
            }

            feed.append({
                'id': f"wf:job:{job.id}",
                'kind': 'attention',
                'entity': 'job',
                'entity_id': job.id,
                'title': f"Job {job.job_number}",
                'subtitle': f"{job.customer_name or 'Unknown'} • {vehicle_display} • {tech_name}",
                'timestamp': job.updated_at.isoformat() if job.updated_at else None,
                'priority_score': job_priority,
                'priority_reason': job_reason,
                'route': f"/jobs/{job.id}",
                'primary_action': primary_action,
                'meta': {
                    'status': job.status,
                    'scheduled_date': job.scheduled_date.isoformat() if job.scheduled_date else None,
                    'is_blocked': is_blocked,
                    'assigned_tech': job.assigned_tech,
                },
            })

        # --- Invoices needing attention (not for restricted roles with assigned_to_me) ---
        if not (is_restricted_role and assigned_to_me):
            invoices_needing_action = Invoice.query.filter(
                Invoice.tenant_id == tenant_id,
                or_(
                    Invoice.status == 'draft',
                    and_(
                        Invoice.status.in_(['issued', 'partial_paid']),
                        Invoice.due_at < now
                    )
                )
            ).order_by(Invoice.created_at.desc()).limit(attention_limit).all()

            for inv in invoices_needing_action:
                is_overdue = inv.due_at and inv.due_at < now and inv.status in ['issued', 'partial_paid']

                if is_overdue:
                    days_overdue = (now - inv.due_at).days
                    inv_priority = min(100, 80 + days_overdue)
                    inv_reason = f'Overdue {days_overdue}d'
                elif inv.status == 'draft':
                    inv_priority = 45
                    inv_reason = 'Ready to issue'
                else:
                    inv_priority = 50
                    inv_reason = None

                primary_action = {
                    'key': 'issue_invoice' if inv.status == 'draft' else 'collect_payment',
                    'label': 'Issue' if inv.status == 'draft' else 'Collect',
                    'route': f"/invoices/{inv.id}",
                }

                feed.append({
                    'id': f"wf:invoice:{inv.id}",
                    'kind': 'attention',
                    'entity': 'invoice',
                    'entity_id': inv.id,
                    'title': f"Invoice {inv.invoice_number}",
                    'subtitle': f"{inv.payer_name or 'Unknown'} • ${float(inv.balance_due):.0f} due",
                    'timestamp': inv.updated_at.isoformat() if inv.updated_at else None,
                    'priority_score': inv_priority,
                    'priority_reason': inv_reason,
                    'route': f"/invoices/{inv.id}",
                    'primary_action': primary_action,
                    'meta': {
                        'status': inv.status,
                        'is_overdue': is_overdue,
                        'balance_due': float(inv.balance_due),
                    },
                })

        # --- Leads needing follow-up (office roles only) ---
        if not is_restricted_role and not assigned_to_me:
            from app.models.tenant.call import Call

            followup_threshold = now - timedelta(days=2)
            last_call_subq = db.session.query(
                Call.lead_id,
                func.max(Call.called_at).label('last_call')
            ).group_by(Call.lead_id).subquery()

            leads_needing_followup = db.session.query(Lead).outerjoin(
                last_call_subq,
                Lead.id == last_call_subq.c.lead_id
            ).filter(
                Lead.tenant_id == tenant_id,
                Lead.status.in_(['new', 'contacted']),
                or_(
                    last_call_subq.c.last_call == None,
                    last_call_subq.c.last_call < followup_threshold
                )
            ).order_by(Lead.created_at.desc()).limit(5).all()

            for lead in leads_needing_followup:
                feed.append({
                    'id': f"wf:lead:{lead.id}",
                    'kind': 'attention',
                    'entity': 'lead',
                    'entity_id': lead.id,
                    'title': f"Lead needs follow-up",
                    'subtitle': f"{lead.business_name or lead.contact_name or 'Unknown'} • {lead.phone or 'No phone'}",
                    'timestamp': lead.created_at.isoformat() if lead.created_at else None,
                    'priority_score': 40,
                    'priority_reason': 'No recent contact',
                    'route': f"/leads/{lead.id}",
                    'primary_action': {
                        'key': 'call_lead',
                        'label': 'Call',
                        'route': f"/leads/{lead.id}",
                    },
                    'meta': {
                        'status': lead.status,
                        'source': lead.source,
                    },
                })

    # =========================================================================
    # 3. SLA ESCALATIONS (if requested)
    # =========================================================================
    if include_escalations:
        from app.services.sla_service import SLAService

        sla_service = SLAService(tenant_id, identity)
        escalations = sla_service.get_escalations(limit=50)

        # Convert escalation alerts to feed items with kind='escalation'
        for alert in escalations:
            feed.append({
                'id': alert['id'],
                'kind': 'escalation',
                'entity': alert['entity'],
                'entity_id': alert['entity_id'],
                'title': alert['title'],
                'subtitle': alert['subtitle'],
                'timestamp': alert['timestamp'],
                'priority_score': alert['priority_score'],
                'priority_reason': alert['priority_reason'],
                'route': alert['route'],
                'primary_action': alert.get('primary_action'),
                'meta': {
                    'severity': alert['severity'],
                    'alert_type': alert['alert_type'],
                    'age_days': alert.get('age_days'),
                    'age_hours': alert.get('age_hours'),
                },
            })

    # =========================================================================
    # 5. DEDUPLICATE & SORT
    # =========================================================================
    # Remove duplicate attention items that might also appear as activities
    seen_ids = set()
    unique_feed = []
    for item in feed:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_feed.append(item)

    # Sort by priority_score DESC, then timestamp DESC
    unique_feed.sort(key=lambda x: (
        -x.get('priority_score', 0),
        x.get('timestamp') or '',
    ), reverse=False)

    # Apply limit
    unique_feed = unique_feed[:limit]

    # =========================================================================
    # 6. COMPUTE SUMMARY
    # =========================================================================
    critical_count = sum(1 for item in unique_feed if item.get('priority_score', 0) >= 80)
    high_count = sum(1 for item in unique_feed if 60 <= item.get('priority_score', 0) < 80)
    standard_count = sum(1 for item in unique_feed if item.get('priority_score', 0) < 60)

    # Escalation-specific counts
    escalation_critical = sum(1 for item in unique_feed if item.get('kind') == 'escalation' and item.get('meta', {}).get('severity') == 'critical')
    escalation_high = sum(1 for item in unique_feed if item.get('kind') == 'escalation' and item.get('meta', {}).get('severity') == 'high')
    escalation_warn = sum(1 for item in unique_feed if item.get('kind') == 'escalation' and item.get('meta', {}).get('severity') == 'warn')

    return jsonify({
        'feed': unique_feed,
        'summary': {
            'critical': critical_count,
            'high': high_count,
            'standard': standard_count,
            'escalations': {
                'critical': escalation_critical,
                'high': escalation_high,
                'warn': escalation_warn,
                'total': escalation_critical + escalation_high + escalation_warn,
            },
        }
    })


@customer_bp.route('/notifications/nudge', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'desk'])
def send_nudge():
    """
    Send a nudge email for an SLA escalation.

    Only owner/manager/desk can send nudges.

    Request body:
        alert_type: string (required)
        entity: string (required)
        entity_id: number (required)
        to: string (optional - recipient email)
        to_internal: boolean (optional - send to all desk/manager/owner)
        subject: string (optional)
        message: string (optional)

    Returns:
        200: { ok: true }
        400: Invalid request
        403: Permission denied
        500: Email send failed
    """
    from app.models.tenant.pdr_estimate import PDREstimate
    from app.models.tenant.job import Job
    from app.models.tenant.invoice import Invoice
    from app.models.tenant.estimate_activity import EstimateActivity
    from app.models.master.user import User
    from app.services.email_service import EmailService

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    data = request.get_json() or {}

    alert_type = data.get('alert_type')
    entity = data.get('entity')
    entity_id = data.get('entity_id')
    to_email = data.get('to')
    to_internal = data.get('to_internal', False)
    subject = data.get('subject')
    message = data.get('message')

    # Validate required fields
    if not alert_type or not entity or not entity_id:
        return jsonify({'error': 'Missing required fields: alert_type, entity, entity_id'}), 400

    # Find the related estimate_id for activity logging
    estimate_id = None

    if entity == 'estimate':
        est = PDREstimate.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not est:
            return jsonify({'error': 'Estimate not found'}), 404
        estimate_id = est.id
        entity_display = f"Estimate {est.estimate_number}"

    elif entity == 'supplement':
        from app.models.tenant.estimate_supplement import EstimateSupplement
        supp = EstimateSupplement.query.get(entity_id)
        if not supp:
            return jsonify({'error': 'Supplement not found'}), 404
        # Verify tenant via estimate
        est = PDREstimate.query.filter_by(id=supp.estimate_id, tenant_id=tenant_id).first()
        if not est:
            return jsonify({'error': 'Supplement not found'}), 404
        estimate_id = est.id
        entity_display = f"Supplement #{supp.supplement_number} for {est.estimate_number}"

    elif entity == 'job':
        job = Job.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        estimate_id = job.estimate_id
        entity_display = f"Job {job.job_number}"

    elif entity == 'invoice':
        inv = Invoice.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not inv:
            return jsonify({'error': 'Invoice not found'}), 404
        estimate_id = inv.estimate_id
        entity_display = f"Invoice {inv.invoice_number}"

    elif entity == 'lead':
        from app.models.tenant.lead import Lead
        lead = Lead.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404
        # Leads may not have estimate_id, skip logging
        estimate_id = None
        entity_display = f"Lead: {lead.business_name or lead.contact_name or 'Unknown'}"

    else:
        return jsonify({'error': f'Invalid entity type: {entity}'}), 400

    # Determine recipients
    recipients = []
    if to_email:
        recipients.append(to_email)
    elif to_internal:
        # Get all tenant users with office roles
        office_users = User.query.filter(
            User.tenant_id == tenant_id,
            User.is_active == True,
            User.role.in_(['owner', 'manager', 'desk'])
        ).all()
        recipients = [u.email for u in office_users if u.email]

    if not recipients:
        return jsonify({'error': 'No recipients specified'}), 400

    # Build default subject/message if not provided
    alert_type_display = alert_type.replace('_', ' ').title()
    if not subject:
        subject = f"[HailTracker] SLA Alert: {alert_type_display} - {entity_display}"
    if not message:
        message = f"This is an automated nudge for: {entity_display}\n\nAlert Type: {alert_type_display}\n\nPlease review and take action."

    # Attempt to send email
    try:
        email_service = EmailService()
        for recipient in recipients:
            email_service.send_simple(
                to=recipient,
                subject=subject,
                body=message
            )

        # Log success to EstimateActivity if we have an estimate_id
        if estimate_id:
            EstimateActivity.log(
                estimate_id=estimate_id,
                activity_type='sla_nudge_sent',
                user_id=user_id,
                activity_data={
                    'alert_type': alert_type,
                    'entity': entity,
                    'entity_id': entity_id,
                    'recipients': recipients,
                    'subject': subject,
                }
            )

        return jsonify({'ok': True, 'recipients': recipients})

    except Exception as e:
        # Log failure if we have estimate_id
        if estimate_id:
            EstimateActivity.log(
                estimate_id=estimate_id,
                activity_type='sla_nudge_failed',
                user_id=user_id,
                activity_data={
                    'alert_type': alert_type,
                    'entity': entity,
                    'entity_id': entity_id,
                    'error': str(e),
                }
            )

        return jsonify({'error': f'Failed to send nudge: {str(e)}'}), 500


# ==============================================================================
# AUTO-NUDGES SETTINGS ENDPOINTS
# ==============================================================================

@customer_bp.route('/settings/auto-nudges', methods=['GET'])
@login_required
@roles_required(['owner', 'manager'])
def get_auto_nudges_settings():
    """
    Get auto-nudges configuration for the tenant.

    Returns:
        200: Auto-nudges config with defaults applied
    """
    from app.models.master.tenant import Tenant

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    config = tenant.get_auto_nudges_config()

    return jsonify({
        'config': config,
        'timezone': tenant.timezone or 'America/Chicago',
    })


@customer_bp.route('/settings/auto-nudges', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager'])
def update_auto_nudges_settings():
    """
    Update auto-nudges configuration.

    Body:
        config: {
            enabled: bool,
            digest_schedule: 'daily' | 'hourly',
            digest_time_local: 'HH:MM',
            recipients: {
                mode: 'roles' | 'explicit',
                roles: ['owner', 'manager', 'desk'],
                emails: [],
            },
            thresholds: {
                send_if_at_least: { warn: 5, high: 2, critical: 1 },
                include_types: null | ['insurer_waiting', ...],
            },
            rate_limits: {
                per_entity_per_type_hours: { critical: 12, high: 24, warn: 48 },
                max_emails_per_run: 30,
            },
            dry_run: bool,
        }
        timezone: str (optional, e.g., 'America/Chicago')

    Returns:
        200: Updated config
    """
    from app.models.master.tenant import Tenant
    from app.extensions import db

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    data = request.get_json() or {}

    # Update config if provided
    if 'config' in data:
        new_config = data['config']

        # Validate required fields
        if 'enabled' in new_config and not isinstance(new_config['enabled'], bool):
            return jsonify({'error': 'enabled must be a boolean'}), 400

        if 'digest_schedule' in new_config:
            if new_config['digest_schedule'] not in ['daily', 'hourly']:
                return jsonify({'error': 'digest_schedule must be "daily" or "hourly"'}), 400

        if 'digest_time_local' in new_config:
            time_str = new_config['digest_time_local']
            try:
                parts = time_str.split(':')
                if len(parts) != 2:
                    raise ValueError()
                hour, minute = int(parts[0]), int(parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError()
            except (ValueError, AttributeError):
                return jsonify({'error': 'digest_time_local must be in HH:MM format'}), 400

        if 'recipients' in new_config:
            recipients = new_config['recipients']
            if 'mode' in recipients and recipients['mode'] not in ['roles', 'explicit']:
                return jsonify({'error': 'recipients.mode must be "roles" or "explicit"'}), 400

        # Merge with existing config
        current_config = tenant.get_auto_nudges_config()
        merged_config = {**current_config}

        for key, value in new_config.items():
            if isinstance(value, dict) and key in merged_config and isinstance(merged_config[key], dict):
                merged_config[key] = {**merged_config[key], **value}
            else:
                merged_config[key] = value

        tenant.set_auto_nudges_config(merged_config)

    # Update timezone if provided
    if 'timezone' in data:
        import pytz
        try:
            pytz.timezone(data['timezone'])
            tenant.timezone = data['timezone']
        except Exception:
            return jsonify({'error': f'Invalid timezone: {data["timezone"]}'}), 400

    db.session.commit()

    return jsonify({
        'config': tenant.get_auto_nudges_config(),
        'timezone': tenant.timezone,
    })


@customer_bp.route('/settings/auto-nudges/test', methods=['POST'])
@login_required
@roles_required(['owner', 'manager'])
def test_auto_nudges():
    """
    Test auto-nudges by running a dry-run and returning what would be sent.

    Returns:
        200: {
            would_send: bool,
            reason: str,
            recipients: [str],
            escalation_counts: { critical, high, warn },
            sample_items: [...],
        }
    """
    from app.models.master.tenant import Tenant
    from app.models.master.user import User
    from app.services.sla_service import SLAService

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    config = tenant.get_auto_nudges_config()

    # Get escalations
    service_identity = {
        'user_id': None,
        'role': 'system',
    }
    sla_service = SLAService(tenant_id, service_identity)
    escalations = sla_service.get_escalations(limit=100)

    # Group by severity
    by_severity = {'critical': [], 'high': [], 'warn': []}
    for esc in escalations:
        sev = esc.get('severity', 'warn')
        if sev in by_severity:
            by_severity[sev].append(esc)

    # Check thresholds
    thresholds = config.get('thresholds', {}).get('send_if_at_least', {})
    min_critical = thresholds.get('critical', 1)
    min_high = thresholds.get('high', 2)
    min_warn = thresholds.get('warn', 5)

    meets_critical = len(by_severity['critical']) >= min_critical
    meets_high = len(by_severity['high']) >= min_high
    meets_warn = len(by_severity['warn']) >= min_warn

    would_send = meets_critical or meets_high or meets_warn

    if not would_send:
        reason = f"Below thresholds: {len(by_severity['critical'])} critical (need {min_critical}), {len(by_severity['high'])} high (need {min_high}), {len(by_severity['warn'])} warn (need {min_warn})"
    else:
        triggered_by = []
        if meets_critical:
            triggered_by.append('critical')
        if meets_high:
            triggered_by.append('high')
        if meets_warn:
            triggered_by.append('warn')
        reason = f"Threshold met: {', '.join(triggered_by)}"

    # Get recipients
    recipients_config = config.get('recipients', {})
    mode = recipients_config.get('mode', 'roles')

    if mode == 'explicit':
        recipients = recipients_config.get('emails', [])
    else:
        roles = recipients_config.get('roles', ['owner', 'manager', 'desk'])
        users = User.query.filter(
            User.tenant_id == tenant_id,
            User.is_active == True,
            User.role.in_(roles),
        ).all()
        recipients = [u.email for u in users if u.email]

    # Sample items (first 5 of each severity)
    sample_items = []
    for sev in ['critical', 'high', 'warn']:
        for item in by_severity[sev][:3]:
            sample_items.append({
                'severity': sev,
                'title': item.get('title'),
                'subtitle': item.get('subtitle'),
                'alert_type': item.get('alert_type'),
            })

    return jsonify({
        'would_send': would_send,
        'reason': reason,
        'recipients': recipients,
        'escalation_counts': {
            'critical': len(by_severity['critical']),
            'high': len(by_severity['high']),
            'warn': len(by_severity['warn']),
        },
        'sample_items': sample_items,
        'config': config,
    })


# ==============================================================================
# LABOR RATES SETTINGS ENDPOINTS (Stage 6E)
# ==============================================================================

@customer_bp.route('/settings/labor-rates', methods=['GET'])
@login_required
@roles_required(['owner', 'manager', 'admin'])
def get_labor_rates_settings():
    """
    Get labor rates configuration for the tenant.

    Returns:
        200: Labor rates config with defaults applied
    """
    from app.models.master.tenant import Tenant

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    config = tenant.get_labor_rates_config()

    return jsonify({
        'config': config,
    })


@customer_bp.route('/settings/labor-rates', methods=['PATCH'])
@login_required
@roles_required(['owner', 'manager', 'admin'])
def update_labor_rates_settings():
    """
    Update labor rates configuration.

    Body:
        config: {
            default_ri_rate: number (0-500),
            currency: 'USD' | 'CAD',
            rules: [
                {
                    id: string,
                    name: string,
                    country: string (default 'US'),
                    state: string (optional),
                    zip_prefixes: [string] (optional),
                    city_keywords: [string] (optional),
                    effective_from: 'YYYY-MM-DD' (optional),
                    effective_to: 'YYYY-MM-DD' (optional),
                    ri_rate: number (0-500)
                }
            ]
        }

    Returns:
        200: Updated config
        400: Validation error
    """
    from app.models.master.tenant import Tenant
    from app.services.labor_rate_service import validate_labor_rates_config

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    data = request.get_json() or {}

    if 'config' not in data:
        return jsonify({'error': 'config is required'}), 400

    new_config = data['config']

    # Validate config
    errors = validate_labor_rates_config(new_config)
    if errors:
        return jsonify({'error': 'Validation failed', 'details': errors}), 400

    # Get current config and merge
    current_config = tenant.get_labor_rates_config()

    # For labor rates, we do a full replacement of the config (not a deep merge)
    # This is simpler and prevents orphaned rules
    merged_config = {
        'default_ri_rate': new_config.get('default_ri_rate', current_config.get('default_ri_rate', 85.0)),
        'currency': new_config.get('currency', current_config.get('currency', 'USD')),
        'rules': new_config.get('rules', current_config.get('rules', [])),
    }

    tenant.set_labor_rates_config(merged_config)
    db.session.commit()

    return jsonify({
        'config': tenant.get_labor_rates_config(),
    })


@customer_bp.route('/settings/labor-rates/preview', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'admin', 'estimator'])
def preview_labor_rate_resolution():
    """
    Preview labor rate resolution for testing.

    Body:
        state: string (optional, e.g., 'TX')
        zip_code: string (optional, e.g., '77001')
        date: 'YYYY-MM-DD' (optional, defaults to today)

    Returns:
        200: {
            rate: number,
            source: 'default' | 'rule',
            rule_id: string | null,
            rule_name: string | null,
            reason: string
        }
    """
    from app.services.labor_rate_service import preview_rate_resolution

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    data = request.get_json() or {}

    result = preview_rate_resolution(
        tenant_id=tenant_id,
        state=data.get('state'),
        zip_code=data.get('zip_code'),
        reference_date=data.get('date'),
    )

    return jsonify(result)


@customer_bp.route('/pdr-estimates/<int:estimate_id>/labor-rate/override', methods=['POST'])
@login_required
@roles_required(['owner', 'manager', 'admin', 'estimator'])
def set_estimate_labor_rate_override(estimate_id):
    """
    Set or clear an R&I labor rate override on an estimate.

    Body:
        ri_labor_rate: number (0-500) to set override, or null to clear

    Returns:
        200: {
            success: true,
            estimate_id: int,
            old_rate: number | null,
            new_rate: number | null,
            source: string
        }
        400: Validation error
        404: Estimate not found
    """
    from app.services.labor_rate_service import set_estimate_ri_rate_override

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']
    user_id = identity['user_id']

    data = request.get_json() or {}

    rate = data.get('ri_labor_rate')

    # Allow null to clear override
    if rate is not None:
        try:
            rate = float(rate)
        except (TypeError, ValueError):
            return jsonify({'error': 'ri_labor_rate must be a number or null'}), 400

    try:
        result = set_estimate_ri_rate_override(
            estimate_id=estimate_id,
            tenant_id=tenant_id,
            rate=rate,
            user_id=user_id,
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@customer_bp.route('/pdr-estimates/<int:estimate_id>/labor-rate', methods=['GET'])
@login_required
def get_estimate_labor_rate(estimate_id):
    """
    Get resolved labor rate for an estimate.

    Returns:
        200: {
            rate: number,
            source: 'default' | 'rule' | 'override',
            rule_id: string | null,
            rule_name: string | null,
            reason: string
        }
        404: Estimate not found
    """
    from app.models.tenant import PDREstimate
    from app.services.labor_rate_service import resolve_ri_rate_for_estimate

    identity = parse_identity(get_jwt_identity())
    tenant_id = identity['tenant_id']

    estimate = PDREstimate.query.filter_by(
        id=estimate_id,
        tenant_id=tenant_id
    ).first()

    if not estimate:
        return jsonify({'error': 'Estimate not found'}), 404

    result = resolve_ri_rate_for_estimate(estimate)

    return jsonify(result)
