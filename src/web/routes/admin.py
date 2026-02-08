"""
Admin Panel Routes
Handles user management, team overview, and system administration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from src.auth.decorators import admin_required
from src.auth.auth_manager import AuthManager

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
auth_manager = AuthManager()

# ============================================================================
# USER MANAGEMENT
# ============================================================================

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management page"""

    # Get all users in company
    if current_user.company_id:
        users = auth_manager.get_company_users(current_user.company_id)
    else:
        # System admin - get all users
        conn = auth_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, username, full_name, role, active,
                   created_at, last_login, login_count, company_id
            FROM users
            ORDER BY created_at DESC
        """)
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # Get user counts by role
    role_counts = {}
    for user in users:
        role = user['role']
        role_counts[role] = role_counts.get(role, 0) + 1

    return render_template('admin/users.html',
                         users=users,
                         role_counts=role_counts)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user page"""

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'sales')

        # Validation
        if not all([email, username, password, full_name]):
            flash('All fields are required.', 'error')
            return render_template('admin/create_user.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('admin/create_user.html')

        # Create user
        user_id = auth_manager.create_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            role=role,
            company_id=current_user.company_id
        )

        if user_id:
            flash(f'User {username} created successfully!', 'success')
            return redirect(url_for('admin.users'))
        else:
            flash('Username or email already exists.', 'error')

    return render_template('admin/create_user.html')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user page"""

    user = auth_manager.get_user_by_id(user_id)

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    # Prevent editing users from other companies (unless system admin)
    if current_user.company_id and user['company_id'] != current_user.company_id:
        flash('You can only edit users in your company.', 'error')
        return redirect(url_for('admin.users'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', user['role'])
        active = request.form.get('active') == 'on'

        if not full_name:
            flash('Full name is required.', 'error')
            return render_template('admin/edit_user.html', user=user)

        # Update user
        auth_manager.update_user(
            user_id=user_id,
            full_name=full_name,
            role=role,
            active=active
        )

        flash(f'User {user["username"]} updated successfully!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""

    user = auth_manager.get_user_by_id(user_id)

    if not user:
        return jsonify({'success': False, 'message': 'User not found'})

    # Prevent deactivating yourself
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'You cannot deactivate yourself'})

    # Prevent editing users from other companies
    if current_user.company_id and user['company_id'] != current_user.company_id:
        return jsonify({'success': False, 'message': 'Cannot edit users from other companies'})

    # Toggle active status
    new_status = not user['active']
    auth_manager.update_user(user_id, active=new_status)

    action = 'activated' if new_status else 'deactivated'
    auth_manager.log_audit(
        current_user.id,
        f'user_{action}',
        'user',
        user_id,
        f'User {user["username"]} {action}'
    )

    return jsonify({
        'success': True,
        'active': new_status,
        'message': f'User {action} successfully'
    })

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user (soft delete by deactivating)"""

    user = auth_manager.get_user_by_id(user_id)

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    # Prevent deleting yourself
    if user_id == current_user.id:
        flash('You cannot delete yourself.', 'error')
        return redirect(url_for('admin.users'))

    # Soft delete (deactivate)
    auth_manager.update_user(user_id, active=False)

    auth_manager.log_audit(
        current_user.id,
        'user_deleted',
        'user',
        user_id,
        f'User {user["username"]} deleted (deactivated)'
    )

    flash(f'User {user["username"]} has been deactivated.', 'success')
    return redirect(url_for('admin.users'))

# ============================================================================
# TEAM OVERVIEW
# ============================================================================

@admin_bp.route('/team')
@login_required
@admin_required
def team():
    """Team overview page"""

    # Get all users in company
    if current_user.company_id:
        users = auth_manager.get_company_users(current_user.company_id)
    else:
        conn = auth_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, username, full_name, role, active,
                   created_at, last_login, login_count, company_id
            FROM users
            ORDER BY created_at DESC
        """)
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()

    # Calculate team stats
    total_users = len(users)
    active_users = sum(1 for u in users if u['active'])
    inactive_users = total_users - active_users

    # Users by role
    by_role = {}
    for user in users:
        role = user['role']
        by_role[role] = by_role.get(role, 0) + 1

    # Recent activity
    recent_activity = auth_manager.get_audit_log(limit=50)

    return render_template('admin/team.html',
                         users=users,
                         total_users=total_users,
                         active_users=active_users,
                         inactive_users=inactive_users,
                         by_role=by_role,
                         recent_activity=recent_activity)

# ============================================================================
# AUDIT LOG
# ============================================================================

@admin_bp.route('/audit-log')
@login_required
@admin_required
def audit_log():
    """Audit log page"""

    # Filters
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    limit = request.args.get('limit', 100, type=int)

    # Get logs
    if user_id:
        logs = auth_manager.get_audit_log(user_id=user_id, limit=limit)
    else:
        logs = auth_manager.get_audit_log(limit=limit)

    # Filter by action if specified
    if action:
        logs = [log for log in logs if log['action'] == action]

    # Get unique actions for filter dropdown
    conn = auth_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT action FROM audit_log ORDER BY action")
    actions = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Get all users for filter dropdown
    if current_user.company_id:
        filter_users = auth_manager.get_company_users(current_user.company_id)
    else:
        conn = auth_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name FROM users ORDER BY username")
        filter_users = [dict(row) for row in cursor.fetchall()]
        conn.close()

    return render_template('admin/audit_log.html',
                         logs=logs,
                         actions=actions,
                         filter_users=filter_users,
                         selected_user_id=user_id,
                         selected_action=action)

# ============================================================================
# COMPANY SETTINGS
# ============================================================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Company settings page"""

    if not current_user.company_id:
        flash('System admins cannot edit company settings.', 'error')
        return redirect(url_for('admin.team'))

    # Get company info
    conn = auth_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM companies WHERE id = ?", (current_user.company_id,))
    company = cursor.fetchone()
    conn.close()

    if not company:
        flash('Company not found.', 'error')
        return redirect(url_for('admin.team'))

    company = dict(company)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        billing_email = request.form.get('billing_email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        zip_code = request.form.get('zip_code', '').strip()

        if not name:
            flash('Company name is required.', 'error')
            return render_template('admin/settings.html', company=company)

        # Update company
        conn = auth_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE companies
            SET name = ?, billing_email = ?, phone = ?,
                address = ?, city = ?, state = ?, zip_code = ?
            WHERE id = ?
        """, (name, billing_email, phone, address, city, state, zip_code, current_user.company_id))

        conn.commit()
        conn.close()

        auth_manager.log_audit(
            current_user.id,
            'company_settings_updated',
            'company',
            current_user.company_id,
            'Company settings updated'
        )

        flash('Company settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', company=company)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    """Get admin stats (for dashboard widgets)"""

    if current_user.company_id:
        users = auth_manager.get_company_users(current_user.company_id)
    else:
        conn = auth_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()

    total_users = len(users)
    active_users = sum(1 for u in users if u['active'])

    # Recent logins (last 24 hours)
    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    recent_logins = sum(1 for u in users if u.get('last_login', '') and u.get('last_login', '') > yesterday)

    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': total_users - active_users,
        'recent_logins': recent_logins
    })


# ============================================================================
# NOTIFICATION TEMPLATES
# ============================================================================

def get_template_manager():
    """Get the notification template manager."""
    import os
    from src.crm.managers.notification_template_manager import NotificationTemplateManager
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                           'data', 'hailtracker_crm.db')
    return NotificationTemplateManager(db_path)


@admin_bp.route('/templates')
@login_required
@admin_required
def templates():
    """Notification templates management page"""
    template_mgr = get_template_manager()

    # Get default templates
    default_templates = template_mgr.get_default_templates()

    # Get custom templates from database
    custom_templates = template_mgr.list_templates()

    # Group custom templates by key
    custom_by_key = {}
    for t in custom_templates:
        key = t['template_key']
        if key not in custom_by_key:
            custom_by_key[key] = []
        custom_by_key[key].append(t)

    # Get template usage stats
    stats = {}
    for key in default_templates.keys():
        stats[key] = template_mgr.get_template_stats(key, days=30)

    return render_template('admin/templates.html',
                         default_templates=default_templates,
                         custom_templates=custom_by_key,
                         stats=stats)


@admin_bp.route('/templates/<template_key>')
@login_required
@admin_required
def template_detail(template_key):
    """View/edit a specific template"""
    template_mgr = get_template_manager()

    # Get default template
    default_templates = template_mgr.get_default_templates()
    default = default_templates.get(template_key)

    if not default:
        flash('Template not found.', 'error')
        return redirect(url_for('admin.templates'))

    # Get custom versions
    custom_versions = template_mgr.list_templates(template_key)

    # Get usage stats
    stats = template_mgr.get_template_stats(template_key, days=30)

    # Available channels
    channels = ['email', 'sms', 'push', 'in_app']

    return render_template('admin/template_detail.html',
                         template_key=template_key,
                         default=default,
                         custom_versions=custom_versions,
                         stats=stats,
                         channels=channels)


@admin_bp.route('/templates/<template_key>/create', methods=['GET', 'POST'])
@login_required
@admin_required
def template_create(template_key):
    """Create a custom template version"""
    template_mgr = get_template_manager()

    # Get default template for reference
    default_templates = template_mgr.get_default_templates()
    default = default_templates.get(template_key)

    if not default:
        flash('Template not found.', 'error')
        return redirect(url_for('admin.templates'))

    channels = ['email', 'sms', 'push', 'in_app']

    if request.method == 'POST':
        channel = request.form.get('channel')
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()

        if not channel or not body:
            flash('Channel and body are required.', 'error')
            return render_template('admin/template_create.html',
                                 template_key=template_key,
                                 default=default,
                                 channels=channels)

        try:
            template_id = template_mgr.create_template(
                template_key=template_key,
                channel=channel,
                body=body,
                title=title if title else None,
                subject=subject if subject else None,
                created_by=current_user.username
            )

            auth_manager.log_audit(
                current_user.id,
                'template_created',
                'notification_template',
                template_id,
                f'Created custom template for {template_key} ({channel})'
            )

            flash(f'Custom template created successfully!', 'success')
            return redirect(url_for('admin.template_detail', template_key=template_key))

        except Exception as e:
            flash(f'Error creating template: {str(e)}', 'error')

    return render_template('admin/template_create.html',
                         template_key=template_key,
                         default=default,
                         channels=channels)


@admin_bp.route('/templates/custom/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def template_edit(template_id):
    """Edit a custom template"""
    template_mgr = get_template_manager()

    # Get the template
    from src.crm.models.database import Database
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                           'data', 'hailtracker_crm.db')
    db = Database(db_path)

    templates = db.execute("SELECT * FROM notification_templates WHERE id = ?", (template_id,))
    if not templates:
        flash('Template not found.', 'error')
        return redirect(url_for('admin.templates'))

    template = templates[0]

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()

        if not body:
            flash('Body is required.', 'error')
            return render_template('admin/template_edit.html', template=template)

        try:
            template_mgr.update_template(
                template_id=template_id,
                body=body,
                title=title if title else None,
                subject=subject if subject else None
            )

            auth_manager.log_audit(
                current_user.id,
                'template_updated',
                'notification_template',
                template_id,
                f'Updated template {template["template_key"]} ({template["channel"]})'
            )

            flash('Template updated successfully!', 'success')
            return redirect(url_for('admin.template_detail', template_key=template['template_key']))

        except Exception as e:
            flash(f'Error updating template: {str(e)}', 'error')

    return render_template('admin/template_edit.html', template=template)


@admin_bp.route('/templates/custom/<int:template_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def template_deactivate(template_id):
    """Deactivate a custom template"""
    template_mgr = get_template_manager()

    # Get template info for logging
    from src.crm.models.database import Database
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                           'data', 'hailtracker_crm.db')
    db = Database(db_path)

    templates = db.execute("SELECT * FROM notification_templates WHERE id = ?", (template_id,))
    if not templates:
        return jsonify({'success': False, 'message': 'Template not found'})

    template = templates[0]

    try:
        template_mgr.deactivate_template(template_id)

        auth_manager.log_audit(
            current_user.id,
            'template_deactivated',
            'notification_template',
            template_id,
            f'Deactivated template {template["template_key"]} ({template["channel"]})'
        )

        return jsonify({'success': True, 'message': 'Template deactivated'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/templates/<template_key>/preview', methods=['POST'])
@login_required
@admin_required
def template_preview(template_key):
    """Preview a template with sample data"""
    template_mgr = get_template_manager()

    # Sample variables for preview
    sample_variables = {
        'customer_name': 'John Smith',
        'vehicle': '2024 Tesla Model 3',
        'job_number': 'JOB-2024-0042',
        'estimate_amount': '$1,250.00',
        'approved_amount': '$1,250.00',
        'final_amount': '$1,250.00',
        'scheduled_date': 'January 25, 2024',
        'completion_date': 'January 27, 2024',
        'technician_name': 'Mike Johnson',
        'location_name': 'PDR Excellence - Downtown',
        'location_address': '123 Main St, Dallas, TX 75201',
        'business_hours': 'Mon-Fri 8AM-6PM, Sat 9AM-2PM',
        'portal_url': 'https://portal.pdrexcellence.com',
        'review_url': 'https://g.page/pdrexcellence/review',
        'referral_url': 'https://pdrexcellence.com/refer/abc123',
        'phone_number': '1-800-PDR-PROS'
    }

    try:
        rendered = template_mgr.render(template_key, sample_variables)
        return jsonify({
            'success': True,
            'rendered': rendered
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@admin_bp.route('/api/templates/stats')
@login_required
@admin_required
def api_template_stats():
    """Get template usage statistics"""
    template_mgr = get_template_manager()
    days = request.args.get('days', 30, type=int)

    default_templates = template_mgr.get_default_templates()
    all_stats = {}

    for key in default_templates.keys():
        all_stats[key] = template_mgr.get_template_stats(key, days=days)

    return jsonify(all_stats)
