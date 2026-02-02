"""
CRM Web Routes
Customer Relationship Management endpoints for HailTracker Pro
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import sys

# Add project root to path
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db.crm_database import CRMDatabase

crm_bp = Blueprint('crm', __name__, url_prefix='/crm')

# Initialize CRM database
db_path = os.path.join(PROJECT_ROOT, 'data', 'hailtracker_crm.db')
crm_db = CRMDatabase(db_path)

# ====================
# Web Pages
# ====================

@crm_bp.route('/dashboard')
@login_required
def dashboard():
    """CRM dashboard page"""

    # Get pipeline summary
    pipeline = crm_db.get_pipeline_summary()

    # Get conversion funnel
    funnel = crm_db.get_conversion_funnel()

    # Get recent revenue
    revenue = crm_db.get_revenue_by_period('month')

    # Get upcoming tasks
    tasks = crm_db.get_tasks(due_soon=True, status='pending')

    # Get activity summary
    activity = crm_db.get_activity_summary(days=7)

    return render_template('crm/dashboard.html',
                         pipeline=pipeline,
                         funnel=funnel,
                         revenue=revenue,
                         tasks=tasks,
                         activity=activity)

@crm_bp.route('/deals')
@login_required
def deals():
    """Deal pipeline page"""

    stage = request.args.get('stage')
    deals = crm_db.get_deals_by_stage(stage)

    # Get pipeline for sidebar
    pipeline = crm_db.get_pipeline_summary()

    return render_template('crm/deals.html',
                         deals=deals,
                         current_stage=stage,
                         pipeline=pipeline)

@crm_bp.route('/deal/<int:deal_id>')
@login_required
def deal_detail(deal_id):
    """Deal detail page"""

    deal = crm_db.get_deal(deal_id)
    if not deal:
        return render_template('errors/404.html'), 404

    # Get related data
    tasks = crm_db.get_tasks(status=None)
    tasks = [t for t in tasks if t.get('deal_id') == deal_id]

    notes = crm_db.get_notes(deal_id=deal_id)

    interactions = []
    if deal.get('location_id'):
        interactions = crm_db.get_location_interactions(deal['location_id'])

    return render_template('crm/deal_detail.html',
                         deal=deal,
                         tasks=tasks,
                         notes=notes,
                         interactions=interactions)

@crm_bp.route('/tasks')
@login_required
def tasks():
    """Task management page"""

    status = request.args.get('status', 'pending')
    user_id = request.args.get('user_id', type=int)

    tasks = crm_db.get_tasks(assigned_to=user_id, status=status if status != 'all' else None)
    overdue = crm_db.get_overdue_tasks()
    users = crm_db.get_users()

    return render_template('crm/tasks.html',
                         tasks=tasks,
                         overdue_tasks=overdue,
                         users=users,
                         current_status=status,
                         current_user=user_id)

@crm_bp.route('/location/<int:location_id>')
@login_required
def location_detail(location_id):
    """Location/contact CRM detail page"""

    # Get interactions for this location
    interactions = crm_db.get_location_interactions(location_id)

    # Get deals for this location
    deals = crm_db.get_deals_by_location(location_id)

    # Get notes
    notes = crm_db.get_notes(location_id=location_id)

    return render_template('crm/location_detail.html',
                         location_id=location_id,
                         interactions=interactions,
                         deals=deals,
                         notes=notes)

@crm_bp.route('/team')
@login_required
def team():
    """Team performance page"""

    users = crm_db.get_users()
    performance = crm_db.get_user_performance(days=30)

    return render_template('crm/team.html',
                         users=users,
                         performance=performance)

# ====================
# API - Dashboard
# ====================

@crm_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """Get dashboard data"""

    days = request.args.get('days', 7, type=int)

    return jsonify({
        'pipeline': crm_db.get_pipeline_summary(),
        'funnel': crm_db.get_conversion_funnel(),
        'activity': crm_db.get_activity_summary(days=days),
        'revenue': crm_db.get_revenue_by_period('month', limit=6)
    })

# ====================
# API - Interactions
# ====================

@crm_bp.route('/api/interaction', methods=['POST'])
@login_required
def log_interaction():
    """Log a new customer interaction"""

    data = request.get_json()

    if not data or 'location_id' not in data or 'type' not in data:
        return jsonify({'error': 'location_id and type required'}), 400

    interaction_id = crm_db.log_interaction(
        location_id=data['location_id'],
        interaction_type=data['type'],
        outcome=data.get('outcome'),
        notes=data.get('notes'),
        user_id=data.get('user_id'),
        duration_seconds=data.get('duration'),
        next_followup_date=data.get('followup_date')
    )

    return jsonify({
        'success': True,
        'interaction_id': interaction_id
    })

@crm_bp.route('/api/interactions/<int:location_id>')
@login_required
def get_interactions(location_id):
    """Get interactions for a location"""

    limit = request.args.get('limit', 50, type=int)
    interactions = crm_db.get_location_interactions(location_id, limit)

    return jsonify({
        'interactions': interactions,
        'count': len(interactions)
    })

@crm_bp.route('/api/interactions/recent')
@login_required
def get_recent_interactions():
    """Get recent interactions across all locations"""

    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 100, type=int)

    interactions = crm_db.get_recent_interactions(days, limit)

    return jsonify({
        'interactions': interactions,
        'count': len(interactions)
    })

# ====================
# API - Deals
# ====================

@crm_bp.route('/api/deal', methods=['POST'])
@login_required
def create_deal():
    """Create a new deal"""

    data = request.get_json()

    if not data or 'location_id' not in data:
        return jsonify({'error': 'location_id required'}), 400

    deal_id = crm_db.create_deal(
        location_id=data['location_id'],
        event_id=data.get('event_id'),
        stage=data.get('stage', 'lead'),
        estimated_value=data.get('estimated_value', 0),
        probability=data.get('probability', 0),
        assigned_to=data.get('assigned_to'),
        expected_close_date=data.get('expected_close_date')
    )

    return jsonify({
        'success': True,
        'deal_id': deal_id
    })

@crm_bp.route('/api/deal/<int:deal_id>')
@login_required
def get_deal(deal_id):
    """Get deal details"""

    deal = crm_db.get_deal(deal_id)

    if not deal:
        return jsonify({'error': 'Deal not found'}), 404

    return jsonify(deal)

@crm_bp.route('/api/deal/<int:deal_id>/stage', methods=['PUT'])
@login_required
def update_deal_stage(deal_id):
    """Update deal stage"""

    data = request.get_json()

    if not data or 'stage' not in data:
        return jsonify({'error': 'stage required'}), 400

    crm_db.update_deal_stage(
        deal_id=deal_id,
        stage=data['stage'],
        actual_value=data.get('actual_value'),
        lost_reason=data.get('lost_reason')
    )

    return jsonify({'success': True})

@crm_bp.route('/api/deals')
@login_required
def get_deals():
    """Get deals with optional filtering"""

    stage = request.args.get('stage')
    location_id = request.args.get('location_id', type=int)

    if location_id:
        deals = crm_db.get_deals_by_location(location_id)
    else:
        deals = crm_db.get_deals_by_stage(stage)

    return jsonify({
        'deals': deals,
        'count': len(deals)
    })

@crm_bp.route('/api/pipeline')
@login_required
def get_pipeline():
    """Get pipeline summary"""

    return jsonify(crm_db.get_pipeline_summary())

# ====================
# API - Tasks
# ====================

@crm_bp.route('/api/task', methods=['POST'])
@login_required
def create_task():
    """Create a new task"""

    data = request.get_json()

    if not data or 'title' not in data or 'type' not in data:
        return jsonify({'error': 'title and type required'}), 400

    task_id = crm_db.create_task(
        title=data['title'],
        task_type=data['type'],
        location_id=data.get('location_id'),
        deal_id=data.get('deal_id'),
        assigned_to=data.get('assigned_to'),
        due_date=data.get('due_date'),
        priority=data.get('priority', 'medium'),
        description=data.get('description')
    )

    return jsonify({
        'success': True,
        'task_id': task_id
    })

@crm_bp.route('/api/task/<int:task_id>')
@login_required
def get_task(task_id):
    """Get task details"""

    task = crm_db.get_task(task_id)

    if not task:
        return jsonify({'error': 'Task not found'}), 404

    return jsonify(task)

@crm_bp.route('/api/task/<int:task_id>/status', methods=['PUT'])
@login_required
def update_task_status(task_id):
    """Update task status"""

    data = request.get_json()

    if not data or 'status' not in data:
        return jsonify({'error': 'status required'}), 400

    crm_db.update_task_status(task_id, data['status'])

    return jsonify({'success': True})

@crm_bp.route('/api/task/<int:task_id>/complete', methods=['PUT'])
@login_required
def complete_task(task_id):
    """Mark task as completed"""

    crm_db.complete_task(task_id)

    return jsonify({'success': True})

@crm_bp.route('/api/tasks')
@login_required
def get_tasks():
    """Get tasks with optional filtering"""

    status = request.args.get('status', 'pending')
    assigned_to = request.args.get('assigned_to', type=int)
    due_soon = request.args.get('due_soon', 'false').lower() == 'true'
    limit = request.args.get('limit', 100, type=int)

    tasks = crm_db.get_tasks(
        assigned_to=assigned_to,
        status=status if status != 'all' else None,
        due_soon=due_soon,
        limit=limit
    )

    return jsonify({
        'tasks': tasks,
        'count': len(tasks)
    })

@crm_bp.route('/api/tasks/overdue')
@login_required
def get_overdue_tasks():
    """Get overdue tasks"""

    tasks = crm_db.get_overdue_tasks()

    return jsonify({
        'tasks': tasks,
        'count': len(tasks)
    })

# ====================
# API - Notes
# ====================

@crm_bp.route('/api/note', methods=['POST'])
@login_required
def add_note():
    """Add a note"""

    data = request.get_json()

    if not data or 'note_text' not in data:
        return jsonify({'error': 'note_text required'}), 400

    note_id = crm_db.add_note(
        note_text=data['note_text'],
        location_id=data.get('location_id'),
        deal_id=data.get('deal_id'),
        user_id=data.get('user_id'),
        attachment_path=data.get('attachment_path')
    )

    return jsonify({
        'success': True,
        'note_id': note_id
    })

@crm_bp.route('/api/notes')
@login_required
def get_notes():
    """Get notes with filtering"""

    location_id = request.args.get('location_id', type=int)
    deal_id = request.args.get('deal_id', type=int)
    limit = request.args.get('limit', 50, type=int)

    notes = crm_db.get_notes(
        location_id=location_id,
        deal_id=deal_id,
        limit=limit
    )

    return jsonify({
        'notes': notes,
        'count': len(notes)
    })

# ====================
# API - Users
# ====================

@crm_bp.route('/api/user', methods=['POST'])
@login_required
def create_user():
    """Create a new user"""

    data = request.get_json()

    if not data or 'name' not in data or 'email' not in data or 'role' not in data:
        return jsonify({'error': 'name, email, and role required'}), 400

    try:
        user_id = crm_db.create_user(
            name=data['name'],
            email=data['email'],
            role=data['role'],
            phone=data.get('phone')
        )

        return jsonify({
            'success': True,
            'user_id': user_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@crm_bp.route('/api/users')
@login_required
def get_users():
    """Get all users"""

    active_only = request.args.get('active_only', 'true').lower() == 'true'
    users = crm_db.get_users(active_only=active_only)

    return jsonify({
        'users': users,
        'count': len(users)
    })

# ====================
# API - Analytics
# ====================

@crm_bp.route('/api/analytics/funnel')
@login_required
def get_funnel():
    """Get conversion funnel"""

    return jsonify(crm_db.get_conversion_funnel())

@crm_bp.route('/api/analytics/revenue')
@login_required
def get_revenue():
    """Get revenue by period"""

    period = request.args.get('period', 'month')
    limit = request.args.get('limit', 12, type=int)

    revenue = crm_db.get_revenue_by_period(period, limit)

    return jsonify({
        'revenue': revenue,
        'period': period
    })

@crm_bp.route('/api/analytics/performance')
@login_required
def get_performance():
    """Get user performance metrics"""

    user_id = request.args.get('user_id', type=int)
    days = request.args.get('days', 30, type=int)

    performance = crm_db.get_user_performance(user_id, days)

    return jsonify({
        'performance': performance,
        'period_days': days
    })

@crm_bp.route('/api/analytics/activity')
@login_required
def get_activity():
    """Get activity summary"""

    days = request.args.get('days', 7, type=int)

    return jsonify(crm_db.get_activity_summary(days))


# Register error handlers for the blueprint
@crm_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@crm_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500
