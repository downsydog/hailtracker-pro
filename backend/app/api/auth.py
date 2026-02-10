"""
Authentication API Endpoints
============================
Handles registration, login, and team management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from app.services.auth_service import AuthService
from app.api.middleware import login_required, manager_required, admin_required

auth_bp = Blueprint('auth', __name__)


# =============================================================================
# REGISTRATION & LOGIN
# =============================================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new company (tenant) with owner account.

    Request Body:
    {
        "company_name": "Acme PDR",
        "first_name": "John",
        "last_name": "Smith",
        "email": "john@acmepdr.com",
        "password": "securepassword123",
        "phone": "555-1234"  // optional
    }

    Returns:
        201: Registration successful with tokens
        400: Validation error
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    # Support both old format (owner_name) and new format (first_name, last_name)
    owner_name = data.get('owner_name')
    if not owner_name:
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        owner_name = f"{first_name} {last_name}".strip()

    if not owner_name:
        return jsonify({'error': 'first_name and last_name or owner_name is required'}), 400

    # Validate required fields
    required = ['company_name', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Validate password length
    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    # Validate company name length
    if len(data['company_name']) < 2:
        return jsonify({'error': 'Company name must be at least 2 characters'}), 400

    # Register
    result = AuthService.register_tenant(
        company_name=data['company_name'],
        owner_name=owner_name,
        owner_email=data['email'],
        password=data['password']
    )

    if result[1] and isinstance(result[1], str):
        # Error message
        return jsonify({'error': result[1]}), 400

    tenant, owner = result

    # Auto-login after registration
    login_result, error = AuthService.login(data['email'], data['password'])

    if error:
        return jsonify({'error': error}), 400

    return jsonify({
        'message': 'Registration successful',
        'data': login_result
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with email and password.

    Request Body:
    {
        "email": "john@acmepdr.com",
        "password": "securepassword123"
    }

    Returns:
        200: Login successful with tokens
        401: Invalid credentials
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    result, error = AuthService.login(data['email'], data['password'])

    if error:
        return jsonify({'error': error}), 401

    return jsonify(result), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Get a new access token using refresh token.

    Headers:
        Authorization: Bearer <refresh_token>

    Returns:
        200: New access token
    """
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({'access_token': access_token}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """
    Get current logged-in user info with permissions.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: User, tenant, and permissions info
    """
    identity = get_jwt_identity()

    from app.models.master.user import User
    from app.models.master.tenant import Tenant
    from app.services.permissions_service import (
        get_user_permissions, get_role_permissions_summary, get_role_display_name
    )

    user = User.query.get(identity['user_id'])
    tenant = Tenant.query.get(identity['tenant_id'])

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Get permissions for this user's role
    role = user.role
    permissions_list = get_user_permissions(role)
    permissions_summary = get_role_permissions_summary(role)

    return jsonify({
        'user': user.to_dict(),
        'tenant': tenant.to_dict() if tenant else None,
        'permissions': permissions_list,
        'can': permissions_summary,
        'role_display': get_role_display_name(role)
    }), 200


@auth_bp.route('/profile', methods=['PATCH'])
@login_required
def update_profile():
    """
    Update current user's profile.

    Request Body:
    {
        "first_name": "John",
        "last_name": "Smith",
        "phone": "555-1234"
    }

    Returns:
        200: Profile updated
        400: Validation error
    """
    data = request.get_json()
    identity = get_jwt_identity()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    from app.models.master.user import User
    from app.extensions import db

    user = User.query.get(identity['user_id'])

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Update allowed fields
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'phone' in data:
        user.phone = data['phone']

    db.session.commit()

    return jsonify({
        'message': 'Profile updated',
        'user': user.to_dict()
    }), 200


# =============================================================================
# PASSWORD MANAGEMENT
# =============================================================================

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Change current user's password.

    Request Body:
    {
        "old_password": "oldpass123",
        "new_password": "newpass456"
    }

    Returns:
        200: Password changed
        400: Validation error
    """
    data = request.get_json()
    identity = get_jwt_identity()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    if not data.get('old_password') or not data.get('new_password'):
        return jsonify({'error': 'Old and new password required'}), 400

    if len(data['new_password']) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400

    success, message = AuthService.change_password(
        identity['user_id'],
        data['old_password'],
        data['new_password']
    )

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request password reset email.

    Request Body:
    {
        "email": "john@acmepdr.com"
    }

    Returns:
        200: Reset email sent (or would be sent)
    """
    data = request.get_json()

    if not data or not data.get('email'):
        return jsonify({'error': 'Email required'}), 400

    success, message = AuthService.reset_password_request(data['email'])

    return jsonify({'message': message}), 200


# =============================================================================
# TEAM MANAGEMENT
# =============================================================================

@auth_bp.route('/team', methods=['GET'])
@login_required
def get_team():
    """
    Get all team members for current tenant.

    Returns:
        200: List of team members
    """
    identity = get_jwt_identity()

    members = AuthService.get_team_members(identity['tenant_id'])

    return jsonify({
        'team': members,
        'count': len(members)
    }), 200


@auth_bp.route('/team/active', methods=['GET'])
@login_required
def get_active_team():
    """
    Get only active team members.

    Returns:
        200: List of active team members
    """
    identity = get_jwt_identity()

    members = AuthService.get_active_team_members(identity['tenant_id'])

    return jsonify({
        'team': members,
        'count': len(members)
    }), 200


@auth_bp.route('/team', methods=['POST'])
@manager_required
def add_team_member():
    """
    Add a new team member.
    Only owner and manager can do this.

    Request Body:
    {
        "name": "Jane Doe",
        "email": "jane@acmepdr.com",
        "password": "temppass123",
        "role": "tech",
        "phone": "555-1234"  // optional
    }

    Valid roles: owner, manager, desk, tech, salesman

    Returns:
        201: Team member added
        400: Validation error
        403: Permission denied
    """
    data = request.get_json()
    identity = get_jwt_identity()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    required = ['name', 'email', 'password', 'role']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    user, error = AuthService.add_team_member(
        tenant_id=identity['tenant_id'],
        adder_role=identity['role'],
        name=data['name'],
        email=data['email'],
        password=data['password'],
        role=data['role'],
        phone=data.get('phone')
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify({
        'message': 'Team member added',
        'user': user.to_dict()
    }), 201


@auth_bp.route('/team/<int:user_id>', methods=['GET'])
@login_required
def get_team_member(user_id):
    """
    Get a specific team member.

    Returns:
        200: Team member info
        404: User not found
    """
    identity = get_jwt_identity()

    from app.models.master.user import User

    user = User.query.filter_by(id=user_id, tenant_id=identity['tenant_id']).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/team/<int:user_id>', methods=['PUT'])
@manager_required
def update_team_member(user_id):
    """
    Update a team member.
    Only owner and manager can do this.

    Request Body:
    {
        "name": "Jane Smith",
        "phone": "555-5678",
        "role": "salesman"
    }

    Returns:
        200: Team member updated
        400: Validation error
        403: Permission denied
    """
    data = request.get_json()
    identity = get_jwt_identity()

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    user, error = AuthService.update_team_member(
        tenant_id=identity['tenant_id'],
        user_id=user_id,
        updater_role=identity['role'],
        **data
    )

    if error:
        return jsonify({'error': error}), 400

    return jsonify({
        'message': 'Team member updated',
        'user': user.to_dict()
    }), 200


@auth_bp.route('/team/<int:user_id>', methods=['DELETE'])
@manager_required
def deactivate_team_member(user_id):
    """
    Deactivate a team member.
    Only owner and manager can do this.

    Returns:
        200: User deactivated
        400: Cannot deactivate
        403: Permission denied
    """
    identity = get_jwt_identity()

    success, message = AuthService.deactivate_user(
        tenant_id=identity['tenant_id'],
        user_id=user_id,
        deactivator_role=identity['role']
    )

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message}), 200


@auth_bp.route('/team/<int:user_id>/reactivate', methods=['POST'])
@manager_required
def reactivate_team_member(user_id):
    """
    Reactivate a deactivated team member.
    Only owner and manager can do this.

    Returns:
        200: User reactivated
        400: Cannot reactivate
        403: Permission denied
    """
    identity = get_jwt_identity()

    success, message = AuthService.reactivate_user(
        tenant_id=identity['tenant_id'],
        user_id=user_id,
        reactivator_role=identity['role']
    )

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message}), 200


@auth_bp.route('/team/<int:user_id>/reset-password', methods=['POST'])
@manager_required
def reset_team_member_password(user_id):
    """
    Reset a team member's password (admin action).
    Only owner and manager can do this.

    Request Body:
    {
        "new_password": "newpass123"
    }

    Returns:
        200: Password reset
        400: Validation error
        403: Permission denied
    """
    data = request.get_json()
    identity = get_jwt_identity()

    if not data or not data.get('new_password'):
        return jsonify({'error': 'new_password required'}), 400

    success, message = AuthService.reset_password_admin(
        tenant_id=identity['tenant_id'],
        user_id=user_id,
        new_password=data['new_password'],
        resetter_role=identity['role']
    )

    if not success:
        return jsonify({'error': message}), 400

    return jsonify({'message': message}), 200


# =============================================================================
# ROLE INFO
# =============================================================================

@auth_bp.route('/roles', methods=['GET'])
@login_required
def get_roles():
    """
    Get available roles and their descriptions.

    Returns:
        200: List of roles
    """
    from app.models.master.user import User

    roles = [
        {
            'role': User.ROLE_OWNER,
            'name': 'Owner',
            'description': 'Full access, billing, can delete company',
            'max_per_company': 1
        },
        {
            'role': User.ROLE_MANAGER,
            'name': 'Manager',
            'description': 'Manage team, view all leads, assign work',
            'max_per_company': 1
        },
        {
            'role': User.ROLE_DESK,
            'name': 'Desk Staff',
            'description': 'CRM access, view all leads, make calls',
            'max_per_company': 1
        },
        {
            'role': User.ROLE_TECH,
            'name': 'Technician',
            'description': 'View assigned jobs only',
            'max_per_company': 5
        },
        {
            'role': User.ROLE_SALESMAN,
            'name': 'Salesman',
            'description': 'View assigned leads only',
            'max_per_company': 5
        }
    ]

    return jsonify({'roles': roles}), 200
