"""
Admin Customer Management Endpoints
====================================
Endpoints for managing tenants/customers (platform admin only).
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from backend.app.api.middleware import admin_required
from backend.app.models.master.tenant import Tenant
from backend.app.models.master.user import User
from backend.app.services.auth_service import AuthService
from backend.app.extensions import db

admin_customers_bp = Blueprint('admin_customers', __name__)


@admin_customers_bp.route('/customers', methods=['GET'])
@admin_required
def list_customers():
    """
    List all customers (tenants).

    Query params:
        status: Filter by status (active, suspended, cancelled)

    Returns:
        200: List of customers
    """
    status = request.args.get('status')

    query = Tenant.query

    if status:
        query = query.filter(Tenant.status == status)

    tenants = query.order_by(Tenant.created_at.desc()).all()

    result = []
    for tenant in tenants:
        user_count = User.query.filter_by(tenant_id=tenant.id, is_active=True).count()
        owner = User.query.filter_by(tenant_id=tenant.id, role='owner').first()

        result.append({
            'id': tenant.id,
            'company_name': tenant.company_name,
            'slug': tenant.slug,
            'owner_email': owner.email if owner else None,
            'plan': tenant.plan,
            'status': tenant.status,
            'user_count': user_count,
            'max_users': tenant.max_users,
            'created_at': tenant.created_at.isoformat() if tenant.created_at else None
        })

    return jsonify({'customers': result})


@admin_customers_bp.route('/customers/<int:customer_id>', methods=['GET'])
@admin_required
def get_customer(customer_id):
    """
    Get detailed customer info.

    Args:
        customer_id: Tenant ID

    Returns:
        200: Customer details with users
        404: Customer not found
    """
    tenant = Tenant.query.get(customer_id)
    if not tenant:
        return jsonify({'error': 'Customer not found'}), 404

    users = User.query.filter_by(tenant_id=customer_id).all()
    owner = User.query.filter_by(tenant_id=tenant.id, role='owner').first()

    return jsonify({
        'customer': {
            'id': tenant.id,
            'company_name': tenant.company_name,
            'slug': tenant.slug,
            'owner_email': owner.email if owner else None,
            'plan': tenant.plan,
            'status': tenant.status,
            'max_users': tenant.max_users,
            'created_at': tenant.created_at.isoformat() if tenant.created_at else None
        },
        'users': [u.to_dict() for u in users]
    })


@admin_customers_bp.route('/customers', methods=['POST'])
@admin_required
def create_customer():
    """
    Create a new customer.

    Request Body:
    {
        "company_name": "Acme PDR",
        "owner_name": "John Smith",
        "owner_email": "john@acmepdr.com",
        "password": "temppass123",
        "plan": "free"
    }

    Returns:
        201: Customer created
        400: Validation error
    """
    data = request.get_json()

    required = ['company_name', 'owner_name', 'owner_email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Use auth service to create tenant
    result = AuthService.register_tenant(
        company_name=data['company_name'],
        owner_name=data['owner_name'],
        owner_email=data['owner_email'],
        password=data['password']
    )

    if result[1] and isinstance(result[1], str):
        return jsonify({'error': result[1]}), 400

    tenant, owner = result

    # Set plan if provided
    if data.get('plan'):
        tenant.plan = data['plan']
        db.session.commit()

    return jsonify({
        'message': 'Customer created',
        'customer': {
            'id': tenant.id,
            'company_name': tenant.company_name,
            'slug': tenant.slug,
            'owner_email': owner.email
        }
    }), 201


@admin_customers_bp.route('/customers/<int:customer_id>', methods=['PATCH'])
@admin_required
def update_customer(customer_id):
    """
    Update customer settings.

    Request Body:
    {
        "status": "suspended",
        "plan": "pro",
        "max_users": 10
    }

    Returns:
        200: Customer updated
        404: Customer not found
    """
    tenant = Tenant.query.get(customer_id)
    if not tenant:
        return jsonify({'error': 'Customer not found'}), 404

    data = request.get_json()

    if 'status' in data:
        if data['status'] not in ['active', 'suspended', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400
        tenant.status = data['status']

    if 'plan' in data:
        if data['plan'] not in ['free', 'starter', 'pro', 'enterprise']:
            return jsonify({'error': 'Invalid plan'}), 400
        tenant.plan = data['plan']

    if 'max_users' in data:
        tenant.max_users = data['max_users']

    if 'company_name' in data:
        tenant.company_name = data['company_name']

    db.session.commit()

    return jsonify({
        'message': 'Customer updated',
        'customer': {
            'id': tenant.id,
            'company_name': tenant.company_name,
            'status': tenant.status,
            'plan': tenant.plan,
            'max_users': tenant.max_users
        }
    })


@admin_customers_bp.route('/customers/<int:customer_id>/users', methods=['GET'])
@admin_required
def get_customer_users(customer_id):
    """
    Get all users for a customer.

    Returns:
        200: List of users
        404: Customer not found
    """
    tenant = Tenant.query.get(customer_id)
    if not tenant:
        return jsonify({'error': 'Customer not found'}), 404

    users = User.query.filter_by(tenant_id=customer_id).all()

    return jsonify({
        'users': [u.to_dict() for u in users],
        'count': len(users)
    })


@admin_customers_bp.route('/customers/stats', methods=['GET'])
@admin_required
def get_customer_stats():
    """
    Get customer statistics.

    Returns:
        200: Customer stats by status and plan
    """
    # By status
    status_stats = {}
    for status in ['active', 'suspended', 'cancelled']:
        status_stats[status] = Tenant.query.filter_by(status=status).count()

    # By plan
    plan_stats = {}
    for plan in ['free', 'starter', 'pro', 'enterprise']:
        plan_stats[plan] = Tenant.query.filter_by(plan=plan).count()

    total = Tenant.query.count()
    total_users = User.query.filter_by(is_active=True).count()

    return jsonify({
        'total_customers': total,
        'total_users': total_users,
        'by_status': status_stats,
        'by_plan': plan_stats
    })
