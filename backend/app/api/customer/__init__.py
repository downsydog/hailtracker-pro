"""
Customer API Endpoints
======================
Tenant-specific operations for PDR business users.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from backend.app.api.middleware import login_required, roles_required
from backend.app.services.storm_service import StormService
from backend.app.services.lead_service import LeadService

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
    identity = get_jwt_identity()

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
    identity = get_jwt_identity()
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
    identity = get_jwt_identity()
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
    identity = get_jwt_identity()

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
    identity = get_jwt_identity()
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
    identity = get_jwt_identity()
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
    identity = get_jwt_identity()
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
    identity = get_jwt_identity()

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
    identity = get_jwt_identity()

    from backend.app.models.master.tenant import Tenant
    from backend.app.models.master.user import User
    from backend.app.services.usage_service import UsageService
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
    identity = get_jwt_identity()

    from backend.app.models.master.user import User

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
    identity = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    required = ['email', 'first_name', 'last_name', 'role', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    from backend.app.services.auth_service import AuthService

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
    identity = get_jwt_identity()
    data = request.get_json()

    from backend.app.models.master.user import User
    from backend.app import db

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
    identity = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    from backend.app.models.master.tenant import Tenant
    from backend.app import db

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
