"""
Notifications API Routes for HailTracker Pro
Manages user notifications with CRUD operations
"""

import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, current_app, g
from functools import wraps
import json
import random
from src.core.auth.decorators import login_required

notifications_api_bp = Blueprint('notifications_api', __name__, url_prefix='/api/notifications')


def get_db_connection():
    """Get database connection with row factory."""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_notifications_table():
    """Ensure notifications table exists."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT,
                link TEXT,
                link_id INTEGER,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                read_at TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(user_id, is_read)")
        conn.commit()
        conn.close()
    except Exception as e:
        current_app.logger.error(f"Error creating notifications table: {e}")


def generate_sample_notifications(user_id, count=20):
    """Generate sample notifications for demo purposes."""
    notification_types = [
        {
            'type': 'lead_new',
            'title': 'New Lead Received',
            'message': 'A new lead has been submitted from the website.',
            'link': '/app/leads',
            'icon': 'user-plus'
        },
        {
            'type': 'lead_assigned',
            'title': 'Lead Assigned to You',
            'message': 'You have been assigned a new lead: {name}',
            'link': '/app/leads',
            'icon': 'user-check'
        },
        {
            'type': 'job_assigned',
            'title': 'Job Assigned',
            'message': 'You have been assigned to job #{id} - {vehicle}',
            'link': '/app/jobs',
            'icon': 'briefcase'
        },
        {
            'type': 'job_status_changed',
            'title': 'Job Status Updated',
            'message': 'Job #{id} status changed to {status}',
            'link': '/app/jobs',
            'icon': 'refresh-cw'
        },
        {
            'type': 'job_completed',
            'title': 'Job Completed',
            'message': 'Job #{id} has been marked as completed.',
            'link': '/app/jobs',
            'icon': 'check-circle'
        },
        {
            'type': 'estimate_approved',
            'title': 'Estimate Approved!',
            'message': 'Customer approved estimate #{id} for ${amount}',
            'link': '/app/estimates',
            'icon': 'file-check'
        },
        {
            'type': 'estimate_declined',
            'title': 'Estimate Declined',
            'message': 'Customer declined estimate #{id}. Follow up may be needed.',
            'link': '/app/estimates',
            'icon': 'file-x'
        },
        {
            'type': 'appointment_reminder',
            'title': 'Appointment Reminder',
            'message': 'Upcoming appointment with {customer} at {time}',
            'link': '/app/calendar',
            'icon': 'calendar'
        },
        {
            'type': 'system_alert',
            'title': 'System Update',
            'message': 'New features have been added to HailTracker Pro.',
            'link': '/app/settings',
            'icon': 'bell'
        },
        {
            'type': 'payment_received',
            'title': 'Payment Received',
            'message': 'Payment of ${amount} received for job #{id}',
            'link': '/app/jobs',
            'icon': 'credit-card'
        }
    ]

    names = ['John Smith', 'Sarah Johnson', 'Mike Williams', 'Emily Davis', 'David Brown']
    vehicles = ['2023 Honda Accord', '2022 Toyota Camry', '2024 Ford F-150', '2023 Tesla Model 3', '2022 BMW X5']
    statuses = ['In Progress', 'Ready for Pickup', 'Scheduled', 'Waiting Parts']

    notifications = []
    for i in range(count):
        template = random.choice(notification_types)
        hours_ago = random.randint(0, 168)  # Up to 1 week ago

        # Replace placeholders
        message = template['message']
        message = message.replace('{name}', random.choice(names))
        message = message.replace('{vehicle}', random.choice(vehicles))
        message = message.replace('{status}', random.choice(statuses))
        message = message.replace('{customer}', random.choice(names))
        message = message.replace('{time}', f"{random.randint(8, 17)}:00")
        message = message.replace('{id}', str(random.randint(1000, 9999)))
        message = message.replace('{amount}', f"{random.randint(500, 5000):,}")

        created_at = datetime.now() - timedelta(hours=hours_ago)

        notifications.append({
            'id': i + 1,
            'user_id': user_id,
            'type': template['type'],
            'title': template['title'],
            'message': message,
            'link': template['link'],
            'link_id': random.randint(1, 100),
            'icon': template['icon'],
            'is_read': 1 if random.random() > 0.4 else 0,  # 60% read
            'created_at': created_at.isoformat(),
            'read_at': created_at.isoformat() if random.random() > 0.5 else None
        })

    # Sort by created_at descending
    notifications.sort(key=lambda x: x['created_at'], reverse=True)

    # Reassign IDs after sorting
    for i, n in enumerate(notifications):
        n['id'] = i + 1

    return notifications


# Store sample notifications in memory for demo
_sample_notifications = {}


def get_user_notifications(user_id):
    """Get notifications for a user (uses sample data for demo)."""
    if user_id not in _sample_notifications:
        _sample_notifications[user_id] = generate_sample_notifications(user_id)
    return _sample_notifications[user_id]


# ====================
# API Endpoints
# ====================

@notifications_api_bp.route('')
@login_required
def list_notifications():
    """List user's notifications with filtering and pagination."""
    user_id = g.current_user.get('id', 1)

    # Query params
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    filter_type = request.args.get('filter', 'all')  # all, unread, read
    notification_type = request.args.get('type')  # specific type filter

    notifications = get_user_notifications(user_id)

    # Apply filters
    if filter_type == 'unread':
        notifications = [n for n in notifications if not n['is_read']]
    elif filter_type == 'read':
        notifications = [n for n in notifications if n['is_read']]

    if notification_type:
        notifications = [n for n in notifications if n['type'] == notification_type]

    # Pagination
    total = len(notifications)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = notifications[start:end]

    # Add relative time
    for n in paginated:
        n['relative_time'] = get_relative_time(n['created_at'])

    return jsonify({
        'notifications': paginated,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page,
            'has_next': end < total,
            'has_prev': page > 1
        }
    })


@notifications_api_bp.route('/unread-count')
@login_required
def unread_count():
    """Get count of unread notifications."""
    user_id = g.current_user.get('id', 1)
    notifications = get_user_notifications(user_id)
    count = sum(1 for n in notifications if not n['is_read'])

    return jsonify({'count': count})


@notifications_api_bp.route('/recent')
@login_required
def recent_notifications():
    """Get most recent notifications for dropdown."""
    user_id = g.current_user.get('id', 1)
    limit = int(request.args.get('limit', 5))

    notifications = get_user_notifications(user_id)[:limit]

    # Add relative time
    for n in notifications:
        n['relative_time'] = get_relative_time(n['created_at'])

    unread_count = sum(1 for n in get_user_notifications(user_id) if not n['is_read'])

    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    })


@notifications_api_bp.route('/<int:notification_id>/read', methods=['PUT'])
@login_required
def mark_read(notification_id):
    """Mark a single notification as read."""
    user_id = g.current_user.get('id', 1)
    notifications = get_user_notifications(user_id)

    for n in notifications:
        if n['id'] == notification_id:
            n['is_read'] = 1
            n['read_at'] = datetime.now().isoformat()
            return jsonify({'success': True, 'notification': n})

    return jsonify({'error': 'Notification not found'}), 404


@notifications_api_bp.route('/read-all', methods=['PUT'])
@login_required
def mark_all_read():
    """Mark all notifications as read."""
    user_id = g.current_user.get('id', 1)
    notifications = get_user_notifications(user_id)

    count = 0
    now = datetime.now().isoformat()
    for n in notifications:
        if not n['is_read']:
            n['is_read'] = 1
            n['read_at'] = now
            count += 1

    return jsonify({'success': True, 'marked_count': count})


@notifications_api_bp.route('/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Delete a single notification."""
    user_id = g.current_user.get('id', 1)
    notifications = get_user_notifications(user_id)

    for i, n in enumerate(notifications):
        if n['id'] == notification_id:
            notifications.pop(i)
            return jsonify({'success': True})

    return jsonify({'error': 'Notification not found'}), 404


@notifications_api_bp.route('/clear', methods=['DELETE'])
@login_required
def clear_read():
    """Clear all read notifications."""
    user_id = g.current_user.get('id', 1)
    notifications = get_user_notifications(user_id)

    # Keep only unread
    unread = [n for n in notifications if not n['is_read']]
    cleared_count = len(notifications) - len(unread)

    _sample_notifications[user_id] = unread

    # Reassign IDs
    for i, n in enumerate(unread):
        n['id'] = i + 1

    return jsonify({'success': True, 'cleared_count': cleared_count})


# ====================
# Helper Functions
# ====================

def get_relative_time(iso_time):
    """Convert ISO timestamp to relative time string."""
    try:
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        now = datetime.now()

        diff = now - dt.replace(tzinfo=None)
        seconds = diff.total_seconds()

        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days} day{"s" if days != 1 else ""} ago'
        else:
            return dt.strftime('%b %d, %Y')
    except:
        return iso_time


# ====================
# Notification Creation Helper
# ====================

def create_notification(user_id, notification_type, title, message, link=None, link_id=None):
    """
    Helper function to create a notification.
    Call this from other parts of the app when events occur.
    """
    notifications = get_user_notifications(user_id)

    icon_map = {
        'lead_new': 'user-plus',
        'lead_assigned': 'user-check',
        'job_assigned': 'briefcase',
        'job_status_changed': 'refresh-cw',
        'job_completed': 'check-circle',
        'estimate_approved': 'file-check',
        'estimate_declined': 'file-x',
        'appointment_reminder': 'calendar',
        'system_alert': 'bell',
        'payment_received': 'credit-card'
    }

    new_notification = {
        'id': len(notifications) + 1,
        'user_id': user_id,
        'type': notification_type,
        'title': title,
        'message': message,
        'link': link,
        'link_id': link_id,
        'icon': icon_map.get(notification_type, 'bell'),
        'is_read': 0,
        'created_at': datetime.now().isoformat(),
        'read_at': None
    }

    notifications.insert(0, new_notification)

    # Reassign IDs
    for i, n in enumerate(notifications):
        n['id'] = i + 1

    return new_notification
