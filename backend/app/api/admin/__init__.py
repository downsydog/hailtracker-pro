"""
Admin API Endpoints
===================
Platform administration and owner-only features.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from backend.app.api.middleware import admin_required
from backend.app.models.master.tenant import Tenant
from backend.app.models.master.user import User
from backend.app.models.master.storm import Storm
from backend.app.services.usage_service import UsageService
from backend.app.extensions import db

admin_bp = Blueprint('admin', __name__)

# Register sub-blueprints
from backend.app.api.admin.storms import admin_storms_bp
from backend.app.api.admin.customers import admin_customers_bp

admin_bp.register_blueprint(admin_storms_bp)
admin_bp.register_blueprint(admin_customers_bp)


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Admin dashboard - owner only.
    Shows company stats and overview.

    Returns:
        200: Dashboard data
        404: Tenant not found
    """
    identity = get_jwt_identity()

    tenant = Tenant.query.get(identity['tenant_id'])
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    # Get user counts
    total_users = User.query.filter_by(tenant_id=identity['tenant_id']).count()
    active_users = User.query.filter_by(tenant_id=identity['tenant_id'], is_active=True).count()

    # Get role breakdown
    role_counts = {}
    for role in User.ROLES:
        count = User.query.filter_by(
            tenant_id=identity['tenant_id'],
            role=role,
            is_active=True
        ).count()
        role_counts[role] = count

    # Get storm stats
    pending_storms = Storm.query.filter(Storm.status == 'pending').count()
    ready_storms = Storm.query.filter(Storm.status == 'ready').count()
    processing_storms = Storm.query.filter(Storm.status == 'processing').count()

    # Get API usage
    usage = UsageService.get_month_usage()

    return jsonify({
        'tenant': {
            'id': tenant.id,
            'company_name': tenant.company_name,
            'slug': tenant.slug,
            'plan': tenant.plan,
            'status': tenant.status,
            'created_at': tenant.created_at.isoformat() if tenant.created_at else None
        },
        'users': {
            'total': total_users,
            'active': active_users,
            'max_allowed': tenant.max_users,
            'by_role': role_counts
        },
        'storms': {
            'pending': pending_storms,
            'processing': processing_storms,
            'ready': ready_storms
        },
        'plan_limits': tenant.get_plan_limits(),
        'api_usage': usage
    }), 200


@admin_bp.route('/usage')
@admin_required
def api_usage():
    """
    Detailed API usage - owner only.
    Shows daily and monthly usage.

    Returns:
        200: Usage statistics
    """
    month_usage = UsageService.get_month_usage()
    today_usage = UsageService.get_today_usage()
    history = UsageService.get_usage_history(days=30)

    return jsonify({
        'month': month_usage,
        'today': today_usage,
        'history': history
    })


@admin_bp.route('/billing')
@admin_required
def billing():
    """
    Billing info - owner only.
    Shows current plan and billing details.

    Returns:
        200: Billing information
        404: Tenant not found
    """
    identity = get_jwt_identity()

    tenant = Tenant.query.get(identity['tenant_id'])
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    # Get subscription if exists
    subscription = tenant.subscription

    return jsonify({
        'plan': tenant.plan,
        'status': tenant.status,
        'subscription': {
            'status': subscription.status if subscription else 'none',
            'current_period_end': subscription.current_period_end.isoformat() if subscription and subscription.current_period_end else None
        } if subscription else None,
        'limits': tenant.get_plan_limits(),
        'message': 'Stripe integration coming soon'
    }), 200


@admin_bp.route('/company', methods=['PUT'])
@admin_required
def update_company():
    """
    Update company info - owner only.

    Request Body:
    {
        "company_name": "New Company Name"
    }

    Returns:
        200: Company updated
        400: Validation error
        404: Tenant not found
    """
    data = request.get_json()
    identity = get_jwt_identity()

    tenant = Tenant.query.get(identity['tenant_id'])
    if not tenant:
        return jsonify({'error': 'Tenant not found'}), 404

    if data.get('company_name'):
        if len(data['company_name']) < 2:
            return jsonify({'error': 'Company name must be at least 2 characters'}), 400
        tenant.company_name = data['company_name']

    db.session.commit()

    return jsonify({
        'message': 'Company updated',
        'tenant': tenant.to_dict()
    }), 200
