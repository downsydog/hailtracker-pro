"""
Main application routes - unified entry point for all roles.

Provides:
- Role-based dashboards
- Common navigation context
- Permission-checked routes for each module
"""

from flask import Blueprint, render_template, redirect, url_for, g, request
from src.core.auth.decorators import (
    login_required, require_permission, require_any_permission, require_role
)
from src.web.nav_config import get_nav_for_user

app_bp = Blueprint('app', __name__, url_prefix='/app')


@app_bp.before_request
def before_request():
    """Set up nav config for all app routes"""
    if g.get('current_user'):
        g.nav_config = get_nav_for_user(g.current_user)
    else:
        g.nav_config = {'layout': 'desktop', 'primary_action': None, 'items': []}


@app_bp.context_processor
def inject_nav_context():
    """Inject navigation context into all templates"""
    return {
        'nav_config': g.get('nav_config', {}),
        'current_user': g.get('current_user', {})
    }


# ============================================================================
# MAIN ROUTES
# ============================================================================

@app_bp.route('/')
@login_required
def index():
    """Redirect to dashboard"""
    return redirect(url_for('app.dashboard'))


@app_bp.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard"""
    role = g.current_user.get('role', 'office')

    # Get role-specific stats and data
    stats = get_dashboard_stats(role, g.organization_id)
    schedule_today = get_schedule_today(g.organization_id) if role in ['owner', 'admin', 'office'] else []
    alerts = get_alerts(g.organization_id) if role in ['owner', 'admin', 'office'] else []
    recent_activity = get_recent_activity(g.organization_id) if role in ['owner', 'admin', 'office'] else []

    # Role-specific data
    context = {
        'stats': stats,
        'schedule_today': schedule_today,
        'alerts': alerts,
        'recent_activity': recent_activity,
        'current_user': g.current_user,
        'nav_config': g.nav_config
    }

    # Add role-specific context
    if role == 'sales':
        context['leaderboard'] = get_sales_leaderboard(g.organization_id, g.current_user['id'])
        context['recent_leads'] = get_recent_leads_for_user(g.current_user['id'])
        context['active_storms'] = get_active_storms()

    elif role == 'tech':
        context['current_job'] = get_current_job_for_tech(g.current_user['id'])
        context['todays_jobs'] = get_todays_jobs_for_tech(g.current_user['id'])

    elif role == 'estimator':
        context['jobs_needing_estimate'] = get_jobs_needing_estimate(g.organization_id)
        context['recent_estimates'] = get_recent_estimates_for_user(g.current_user['id'])

    return render_template('app/dashboard/dashboard_base.html', **context)


# ============================================================================
# CRM ROUTES
# ============================================================================

@app_bp.route('/customers')
@login_required
@require_any_permission('customers.view_all', 'customers.view_own')
def customers():
    """Customer list"""
    return render_template('app/customers/list.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/customers/<int:customer_id>')
@login_required
@require_any_permission('customers.view_all', 'customers.view_own')
def customer_detail(customer_id):
    """Customer detail - redirects to list with drawer open"""
    return redirect(url_for('app.customers', open=customer_id))


@app_bp.route('/customers/new')
@login_required
@require_permission('customers.create')
def customers_new():
    """New customer form"""
    return render_template('app/customers/form.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user,
                         customer=None)


@app_bp.route('/leads')
@login_required
@require_any_permission('leads.view_all', 'leads.view_own')
def leads():
    """Lead list - Sales sees only their leads, office sees all"""
    return render_template('app/leads/list.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/leads/<int:lead_id>')
@login_required
@require_any_permission('leads.view_all', 'leads.view_own')
def lead_detail(lead_id):
    """Lead detail - redirects to list with drawer open"""
    return redirect(url_for('app.leads', open=lead_id))


@app_bp.route('/leads/new')
@login_required
@require_permission('leads.create')
def leads_new():
    """New lead form"""
    return render_template('app/leads/form.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user,
                         lead=None)


@app_bp.route('/vehicles')
@login_required
@require_permission('vehicles.view')
def vehicles():
    """Vehicle list"""
    return render_template('app/vehicles/list.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/vehicles/<int:vehicle_id>')
@login_required
@require_permission('vehicles.view')
def vehicle_detail(vehicle_id):
    """Vehicle detail - redirects to list with drawer open"""
    return redirect(url_for('app.vehicles', open=vehicle_id))


# ============================================================================
# OPERATIONS ROUTES
# ============================================================================

@app_bp.route('/jobs')
@login_required
@require_any_permission('jobs.view_all', 'jobs.view_assigned')
def jobs():
    """Job list - Tech sees only assigned jobs, office sees all"""
    return render_template('app/jobs/list.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/jobs/<int:job_id>')
@login_required
@require_any_permission('jobs.view_all', 'jobs.view_assigned')
def job_detail(job_id):
    """Job detail - redirects to list with drawer open"""
    return redirect(url_for('app.jobs', open=job_id))


@app_bp.route('/estimates')
@login_required
@require_any_permission('estimates.view_all', 'estimates.view_own')
def estimates():
    """Estimate list"""
    return render_template('app/estimates/list.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/estimates/<int:estimate_id>')
@login_required
@require_any_permission('estimates.view_all', 'estimates.view_own')
def estimate_detail(estimate_id):
    """Estimate detail - redirects to list with drawer open"""
    return redirect(url_for('app.estimates', open=estimate_id))


@app_bp.route('/estimates/new')
@login_required
@require_permission('estimates.create')
def estimates_new():
    """New estimate form"""
    job_id = request.args.get('job_id')
    return render_template('app/estimates/form.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user,
                         job_id=job_id,
                         estimate=None)


@app_bp.route('/schedule')
@login_required
@require_permission('schedule.view')
def schedule():
    """Schedule/calendar view"""
    return render_template('app/schedule/calendar.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/claims')
@login_required
@require_permission('claims.view')
def claims():
    """Insurance claims list"""
    return render_template('app/claims/list.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


# ============================================================================
# WEATHER/HAIL ROUTES
# ============================================================================

@app_bp.route('/hail-map')
@login_required
@require_permission('hail.view_map')
def hail_map():
    """Hail map view"""
    return render_template('app/hail/map.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/alerts')
@login_required
@require_permission('hail.manage_alerts')
def alerts():
    """Storm alerts"""
    return render_template('app/hail/alerts.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


# ============================================================================
# FINANCE ROUTES
# ============================================================================

@app_bp.route('/invoices')
@login_required
@require_permission('invoices.view')
def invoices():
    """Invoice list"""
    return render_template('app/invoices/list.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/reports')
@login_required
@require_permission('reports.view')
def reports():
    """Reports dashboard"""
    return render_template('app/reports/index.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app_bp.route('/team')
@login_required
@require_permission('users.view')
def team():
    """Team management"""
    return render_template('app/admin/team.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/kiosks')
@login_required
@require_permission('settings.manage')
def kiosks():
    """Kiosk device management"""
    return render_template('app/admin/kiosks.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/settings')
@login_required
@require_permission('settings.manage')
def settings():
    """Organization settings"""
    return render_template('app/admin/settings.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/billing')
@login_required
@require_permission('billing.view')
def billing():
    """Billing and subscription"""
    return render_template('app/admin/billing.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


# ============================================================================
# USER ROUTES
# ============================================================================

@app_bp.route('/profile')
@login_required
def profile():
    """User profile"""
    return render_template('app/profile/index.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/notifications')
@login_required
def notifications():
    """Notifications list"""
    return render_template('app/notifications/index.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


# ============================================================================
# TECH-SPECIFIC ROUTES
# ============================================================================

@app_bp.route('/hours')
@login_required
def hours():
    """Time tracking for techs"""
    return render_template('app/hours/index.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


@app_bp.route('/photos/upload')
@login_required
def photos_upload():
    """Photo upload page"""
    return render_template('app/photos/upload.html',
                         nav_config=g.nav_config,
                         current_user=g.current_user)


# ============================================================================
# HELPER FUNCTIONS - Mock data for now
# ============================================================================

def get_dashboard_stats(role: str, org_id: int) -> dict:
    """Get dashboard stats based on role"""
    # This will call various managers to get role-appropriate data
    # For now, return mock data

    if role in ['owner', 'admin', 'office']:
        return {
            'jobs_today': 12,
            'jobs_change': 8,
            'pending_claims': 5,
            'new_leads': 3,
            'revenue_mtd': 45000,
        }
    elif role == 'sales':
        return {
            'today': 3,
            'week': 12,
            'commission': 420,
        }
    elif role == 'tech':
        return {
            'assigned': 4,
            'in_progress': 1,
            'completed': 2,
            'hours_week': 32.5,
            'earnings_week': 1625,
        }
    elif role == 'estimator':
        return {
            'needs_estimate': 4,
            'drafts': 2,
            'completed_today': 3,
        }
    return {}


def get_schedule_today(org_id: int) -> list:
    """Get today's schedule"""
    # Mock data - replace with actual DB query
    return [
        {
            'time': '9:00 AM',
            'customer_name': 'John Smith',
            'vehicle': '2022 Toyota Camry',
            'status': 'scheduled',
            'status_display': 'Scheduled'
        },
        {
            'time': '10:30 AM',
            'customer_name': 'Jane Doe',
            'vehicle': '2021 Honda Accord',
            'status': 'in_progress',
            'status_display': 'In Progress'
        },
        {
            'time': '2:00 PM',
            'customer_name': 'Bob Wilson',
            'vehicle': '2023 Ford F-150',
            'status': 'scheduled',
            'status_display': 'Scheduled'
        },
    ]


def get_alerts(org_id: int) -> list:
    """Get alerts that need attention"""
    # Mock data - replace with actual DB query
    return [
        {
            'icon': 'shield',
            'color': 'yellow',
            'title': '3 claims awaiting adjuster',
            'description': 'Oldest: 5 days ago',
            'link': '/app/claims?status=pending'
        },
        {
            'icon': 'clock',
            'color': 'red',
            'title': 'Estimate overdue',
            'description': '2022 BMW X5 - Customer waiting',
            'link': '/app/estimates/new?job_id=123'
        }
    ]


def get_recent_activity(org_id: int) -> list:
    """Get recent activity"""
    # Mock data - replace with actual DB query
    return [
        {
            'icon': 'check-circle',
            'description': 'Job #1234 completed by Mike',
            'time_ago': '15 minutes ago'
        },
        {
            'icon': 'user-plus',
            'description': 'New customer: Sarah Johnson',
            'time_ago': '1 hour ago'
        },
        {
            'icon': 'file-text',
            'description': 'Estimate sent to ABC Insurance',
            'time_ago': '2 hours ago'
        },
    ]


def get_sales_leaderboard(org_id: int, current_user_id: int) -> list:
    """Get sales leaderboard"""
    # Mock data
    return [
        {'name': 'Mike Johnson', 'initials': 'MJ', 'leads': 15, 'is_me': False},
        {'name': 'Sarah Smith', 'initials': 'SS', 'leads': 12, 'is_me': False},
        {'name': 'You', 'initials': 'YU', 'leads': 10, 'is_me': True},
        {'name': 'Tom Brown', 'initials': 'TB', 'leads': 8, 'is_me': False},
    ]


def get_recent_leads_for_user(user_id: int) -> list:
    """Get recent leads for a sales user"""
    # Mock data
    return [
        {
            'id': 1,
            'name': 'John Smith',
            'address': '123 Main St, Dallas TX',
            'time_ago': '2 hours ago',
            'status': 'new',
            'status_display': 'New'
        },
        {
            'id': 2,
            'name': 'Jane Doe',
            'address': '456 Oak Ave, Plano TX',
            'time_ago': 'Yesterday',
            'status': 'contacted',
            'status_display': 'Contacted'
        },
    ]


def get_active_storms() -> list:
    """Get active storm alerts"""
    # Mock data - would come from hail tracking system
    return []


def get_current_job_for_tech(user_id: int) -> dict:
    """Get current job in progress for a tech"""
    try:
        from flask import current_app
        from src.crm.models.database import Database
        from src.crm.managers.tech_manager import TechManager

        db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker_crm.db')
        db = Database(db_path)
        tech_manager = TechManager(db)

        # Get tech by user_id or email
        tech = tech_manager.get_tech_by_user_id(user_id)
        if not tech:
            return None

        # Get current (in progress) jobs
        current_jobs = tech_manager.get_tech_jobs(tech['id'], 'CURRENT')
        if current_jobs:
            job = current_jobs[0]
            return {
                'id': job['id'],
                'job_number': job.get('job_number'),
                'vehicle': job.get('vehicle_description', 'Unknown Vehicle'),
                'vehicle_color': job.get('vehicle_color'),
                'customer_name': job.get('customer_name', 'Unknown'),
                'customer_phone': job.get('customer_phone'),
                'status': job.get('status', '').lower(),
                'status_display': job.get('status', '').replace('_', ' ').title(),
                'estimated_hours': job.get('estimated_hours'),
                'tech_notes': job.get('tech_notes'),
                'last_tech_update': job.get('last_tech_update')
            }
        return None
    except Exception as e:
        print(f"Error getting current job: {e}")
        return None


def get_todays_jobs_for_tech(user_id: int) -> list:
    """Get today's jobs for a tech"""
    try:
        from flask import current_app
        from src.crm.models.database import Database
        from src.crm.managers.tech_manager import TechManager

        db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker_crm.db')
        db = Database(db_path)
        tech_manager = TechManager(db)

        # Get tech by user_id or email
        tech = tech_manager.get_tech_by_user_id(user_id)
        if not tech:
            return []

        # Get all active jobs (current + upcoming)
        jobs = tech_manager.get_tech_jobs(tech['id'], None)  # All active

        result = []
        for job in jobs[:10]:  # Limit to 10
            result.append({
                'id': job['id'],
                'job_number': job.get('job_number'),
                'vehicle': job.get('vehicle_description', 'Unknown Vehicle'),
                'vehicle_color': job.get('vehicle_color'),
                'customer_name': job.get('customer_name', 'Unknown'),
                'customer_phone': job.get('customer_phone'),
                'status': job.get('status', '').lower(),
                'status_display': job.get('status', '').replace('_', ' ').title(),
                'estimated_hours': job.get('estimated_hours'),
                'priority': job.get('priority')
            })
        return result
    except Exception as e:
        print(f"Error getting today's jobs: {e}")
        return []


def get_jobs_needing_estimate(org_id: int) -> list:
    """Get jobs that need estimates"""
    # Mock data
    return [
        {
            'id': 1,
            'customer_name': 'John Smith',
            'vehicle': '2022 Toyota Camry - Silver',
            'time_ago': '30 minutes ago'
        },
        {
            'id': 2,
            'customer_name': 'Jane Doe',
            'vehicle': '2023 Honda Civic - Blue',
            'time_ago': '2 hours ago'
        },
    ]


def get_recent_estimates_for_user(user_id: int) -> list:
    """Get recent estimates created by a user"""
    # Mock data
    return [
        {
            'id': 1,
            'customer_name': 'Bob Wilson',
            'vehicle': '2023 Ford F-150',
            'total': 2500,
            'status': 'approved',
            'status_display': 'Approved'
        },
        {
            'id': 2,
            'customer_name': 'Alice Brown',
            'vehicle': '2022 BMW X5',
            'total': 4200,
            'status': 'sent',
            'status_display': 'Sent'
        },
    ]
