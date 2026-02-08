"""
Scheduling Routes
API endpoints for the appointment calendar, technician schedules, and scheduling settings.

Routes:
- GET  /api/schedule/appointments       - Get appointments for calendar
- POST /api/schedule/appointments       - Create new appointment
- GET  /api/schedule/appointments/<id>  - Get appointment details
- PUT  /api/schedule/appointments/<id>  - Update appointment
- DELETE /api/schedule/appointments/<id> - Delete appointment

- GET  /api/schedule/availability       - Check availability for a date
- GET  /api/schedule/technicians        - Get technician list
- GET  /api/schedule/technicians/<id>/schedule - Get tech schedule

- GET  /api/schedule/settings           - Get scheduling settings
- PUT  /api/schedule/settings           - Update scheduling settings

- GET  /api/schedule/time-off           - Get time-off entries
- POST /api/schedule/time-off           - Add time-off entry
- DELETE /api/schedule/time-off/<id>    - Remove time-off entry

Auth: All routes require login and appropriate permissions.
"""

from flask import Blueprint, jsonify, request, g
from datetime import datetime, timedelta
import os

from src.core.auth.decorators import (
    login_required, require_permission, require_any_permission
)
from src.crm.managers.scheduling_manager import SchedulingManager

# Create blueprint
scheduling_bp = Blueprint('scheduling', __name__, url_prefix='/api/schedule')

# Database path
DB_PATH = os.environ.get('HAILTRACKER_DB', 'data/hailtracker_crm.db')


def get_manager():
    """Get SchedulingManager instance"""
    return SchedulingManager(DB_PATH)


# ============================================================================
# APPOINTMENT ENDPOINTS
# ============================================================================

@scheduling_bp.route('/appointments', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'schedule.view_own')
def get_appointments():
    """
    Get appointments for calendar display.

    Query params:
    - start: Start date (ISO format)
    - end: End date (ISO format)
    - technician_id: Filter by technician (optional)
    - status: Filter by status (optional)
    - view: Calendar view type (month/week/day)

    Returns FullCalendar-compatible event format.
    """
    manager = get_manager()
    organization_id = g.organization_id

    # Parse date range
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    technician_id = request.args.get('technician_id', type=int)
    status = request.args.get('status')

    # Default to current month if not specified
    if not start_str:
        today = datetime.now()
        start_date = today.replace(day=1)
        start_str = start_date.strftime('%Y-%m-%d')

    if not end_str:
        # Default to 6 weeks from start
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
        end_date = start_date + timedelta(weeks=6)
        end_str = end_date.strftime('%Y-%m-%d')

    # Get appointments from manager
    appointments = manager.get_appointments(
        organization_id=organization_id,
        start_date=start_str,
        end_date=end_str,
        technician_id=technician_id,
        status=status
    )

    # Convert to FullCalendar event format
    events = []
    for apt in appointments:
        # Determine color based on appointment type/status
        color = get_appointment_color(apt)

        event = {
            'id': apt['id'],
            'title': format_appointment_title(apt),
            'start': f"{apt['appointment_date']}T{apt['start_time']}",
            'end': f"{apt['appointment_date']}T{apt['end_time']}" if apt.get('end_time') else None,
            'allDay': False,
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'appointment_type': apt.get('appointment_type'),
                'status': apt.get('status'),
                'customer_id': apt.get('customer_id'),
                'customer_name': apt.get('customer_name'),
                'job_id': apt.get('job_id'),
                'technician_id': apt.get('technician_id'),
                'technician_name': apt.get('technician_name'),
                'notes': apt.get('notes'),
                'vehicle': apt.get('vehicle_description')
            }
        }
        events.append(event)

    return jsonify({
        'success': True,
        'events': events
    })


@scheduling_bp.route('/appointments', methods=['POST'])
@login_required
@require_permission('schedule.manage')
def create_appointment():
    """
    Create a new appointment.

    Expected JSON body:
    {
        "appointment_date": "2024-01-15",
        "start_time": "09:00",
        "end_time": "10:00",
        "appointment_type": "DROP_OFF",
        "customer_id": 123,
        "job_id": 456,
        "technician_id": 789,
        "notes": "Customer prefers morning"
    }
    """
    manager = get_manager()
    organization_id = g.organization_id
    data = request.get_json()

    # Validate required fields
    required = ['appointment_date', 'start_time', 'appointment_type']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing)}'
        }), 400

    # Create appointment
    result = manager.create_appointment(
        organization_id=organization_id,
        appointment_date=data['appointment_date'],
        start_time=data['start_time'],
        end_time=data.get('end_time'),
        appointment_type=data['appointment_type'],
        customer_id=data.get('customer_id'),
        job_id=data.get('job_id'),
        technician_id=data.get('technician_id'),
        notes=data.get('notes'),
        created_by=g.current_user.get('id')
    )

    if result.get('success'):
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@scheduling_bp.route('/appointments/<int:appointment_id>', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'schedule.view_own')
def get_appointment(appointment_id):
    """Get appointment details"""
    manager = get_manager()

    appointment = manager.get_appointment(appointment_id)

    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404

    # Check organization access
    if appointment.get('organization_id') != g.organization_id:
        return jsonify({
            'success': False,
            'error': 'Access denied'
        }), 403

    return jsonify({
        'success': True,
        'appointment': appointment
    })


@scheduling_bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
@require_permission('schedule.manage')
def update_appointment(appointment_id):
    """
    Update an appointment.

    Supports partial updates - only include fields you want to change.
    """
    manager = get_manager()
    data = request.get_json()

    # Verify appointment exists and belongs to organization
    appointment = manager.get_appointment(appointment_id)
    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404

    if appointment.get('organization_id') != g.organization_id:
        return jsonify({
            'success': False,
            'error': 'Access denied'
        }), 403

    # Update appointment
    result = manager.update_appointment(
        appointment_id=appointment_id,
        **data
    )

    return jsonify(result), 200 if result.get('success') else 400


@scheduling_bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
@login_required
@require_permission('schedule.manage')
def delete_appointment(appointment_id):
    """Delete/cancel an appointment"""
    manager = get_manager()

    # Verify appointment exists and belongs to organization
    appointment = manager.get_appointment(appointment_id)
    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404

    if appointment.get('organization_id') != g.organization_id:
        return jsonify({
            'success': False,
            'error': 'Access denied'
        }), 403

    # Cancel the appointment (soft delete)
    result = manager.cancel_appointment(
        appointment_id=appointment_id,
        cancelled_by=g.current_user.get('id'),
        reason=request.args.get('reason', 'Cancelled by staff')
    )

    return jsonify(result), 200 if result.get('success') else 400


# ============================================================================
# AVAILABILITY ENDPOINTS
# ============================================================================

@scheduling_bp.route('/availability', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'schedule.view_own')
def get_availability():
    """
    Get available time slots for a specific date.

    Query params:
    - date: Target date (ISO format)
    - appointment_type: Type of appointment (optional)
    - technician_id: Specific technician (optional)
    - duration: Duration in minutes (optional, default 60)
    """
    manager = get_manager()
    organization_id = g.organization_id

    target_date = request.args.get('date')
    if not target_date:
        return jsonify({
            'success': False,
            'error': 'Date is required'
        }), 400

    appointment_type = request.args.get('appointment_type', 'DROP_OFF')
    technician_id = request.args.get('technician_id', type=int)
    duration = request.args.get('duration', type=int, default=60)

    slots = manager.get_available_slots(
        organization_id=organization_id,
        target_date=target_date,
        appointment_type=appointment_type,
        technician_id=technician_id,
        duration_minutes=duration
    )

    return jsonify({
        'success': True,
        'date': target_date,
        'slots': slots
    })


@scheduling_bp.route('/overview', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'schedule.view_own')
def get_overview():
    """
    Get schedule overview/statistics for dashboard.

    Query params:
    - date: Target date (default: today)
    """
    manager = get_manager()
    organization_id = g.organization_id

    target_date = request.args.get('date')

    overview = manager.get_schedule_overview(organization_id, target_date)

    return jsonify({
        'success': True,
        'overview': overview
    })


# ============================================================================
# TECHNICIAN SCHEDULE ENDPOINTS
# ============================================================================

@scheduling_bp.route('/technicians', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'schedule.view_own')
def get_technicians():
    """Get list of technicians with their schedules"""
    manager = get_manager()
    organization_id = g.organization_id

    # Get technicians from the organization
    technicians = manager.get_technicians_with_availability(organization_id)

    return jsonify({
        'success': True,
        'technicians': technicians
    })


@scheduling_bp.route('/technicians/<int:technician_id>/schedule', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'schedule.view_own')
def get_technician_schedule(technician_id):
    """Get technician's weekly schedule"""
    manager = get_manager()

    schedule = manager.get_technician_schedule(technician_id)

    return jsonify({
        'success': True,
        'technician_id': technician_id,
        'schedule': schedule
    })


@scheduling_bp.route('/technicians/<int:technician_id>/schedule', methods=['PUT'])
@login_required
@require_permission('admin.manage_settings')
def update_technician_schedule(technician_id):
    """
    Update technician's weekly schedule.

    Expected JSON body:
    {
        "schedule": [
            {"day_of_week": 0, "is_available": false},
            {"day_of_week": 1, "is_available": true, "start_time": "08:00", "end_time": "17:00"},
            ...
        ]
    }
    """
    manager = get_manager()
    organization_id = g.organization_id
    data = request.get_json()

    if 'schedule' not in data:
        return jsonify({
            'success': False,
            'error': 'Schedule data is required'
        }), 400

    result = manager.set_technician_schedule(
        organization_id=organization_id,
        technician_id=technician_id,
        schedule=data['schedule']
    )

    return jsonify({
        'success': result,
        'message': 'Schedule updated' if result else 'Failed to update schedule'
    })


# ============================================================================
# TIME OFF ENDPOINTS
# ============================================================================

@scheduling_bp.route('/time-off', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'admin.manage_settings')
def get_time_off():
    """
    Get time-off entries.

    Query params:
    - technician_id: Filter by technician (optional)
    - include_past: Include past entries (default: false)
    """
    manager = get_manager()

    technician_id = request.args.get('technician_id', type=int)
    include_past = request.args.get('include_past', 'false').lower() == 'true'

    if technician_id:
        entries = manager.get_technician_time_off(technician_id, include_past=include_past)
    else:
        # Get all time-off for the organization
        # This would need to be implemented in the manager
        entries = []

    return jsonify({
        'success': True,
        'time_off': entries
    })


@scheduling_bp.route('/time-off', methods=['POST'])
@login_required
@require_permission('admin.manage_settings')
def add_time_off():
    """
    Add time-off entry for a technician.

    Expected JSON body:
    {
        "technician_id": 123,
        "start_date": "2024-01-15",
        "end_date": "2024-01-15",
        "start_time": "13:00",  // optional
        "end_time": "17:00",    // optional
        "reason": "vacation",
        "notes": "Family trip"
    }
    """
    manager = get_manager()
    organization_id = g.organization_id
    data = request.get_json()

    required = ['technician_id', 'start_date', 'end_date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing)}'
        }), 400

    time_off_id = manager.add_time_off(
        organization_id=organization_id,
        technician_id=data['technician_id'],
        start_date=data['start_date'],
        end_date=data['end_date'],
        start_time=data.get('start_time'),
        end_time=data.get('end_time'),
        reason=data.get('reason'),
        notes=data.get('notes'),
        approved_by=g.current_user.get('id')
    )

    if time_off_id:
        return jsonify({
            'success': True,
            'time_off_id': time_off_id,
            'message': 'Time off added'
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to add time off'
        }), 400


@scheduling_bp.route('/time-off/<int:time_off_id>', methods=['DELETE'])
@login_required
@require_permission('admin.manage_settings')
def delete_time_off(time_off_id):
    """Remove a time-off entry"""
    manager = get_manager()

    result = manager.remove_time_off(time_off_id)

    return jsonify({
        'success': result,
        'message': 'Time off removed' if result else 'Failed to remove time off'
    })


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@scheduling_bp.route('/settings', methods=['GET'])
@login_required
@require_any_permission('schedule.view', 'admin.manage_settings')
def get_settings():
    """Get scheduling settings for the organization"""
    manager = get_manager()
    organization_id = g.organization_id

    settings = manager.get_scheduling_settings(organization_id)

    return jsonify({
        'success': True,
        'settings': settings
    })


@scheduling_bp.route('/settings', methods=['PUT'])
@login_required
@require_permission('admin.manage_settings')
def update_settings():
    """
    Update scheduling settings.

    Expected JSON body (all fields optional):
    {
        "business_hours": {...},
        "default_slot_duration": 60,
        "buffer_between_appointments": 15,
        "max_appointments_per_day": 20,
        "allow_self_scheduling": true,
        "min_notice_hours": 24,
        "max_advance_days": 30,
        ...
    }
    """
    manager = get_manager()
    organization_id = g.organization_id
    data = request.get_json()

    result = manager.update_scheduling_settings(organization_id, data)

    return jsonify({
        'success': result,
        'message': 'Settings updated' if result else 'Failed to update settings'
    })


# ============================================================================
# SELF-SCHEDULING TOKEN ENDPOINTS
# ============================================================================

@scheduling_bp.route('/tokens', methods=['GET'])
@login_required
@require_permission('schedule.manage')
def get_tokens():
    """Get active self-scheduling tokens"""
    manager = get_manager()
    organization_id = g.organization_id

    # This would need to be implemented in the manager
    # For now, return empty list
    tokens = []

    return jsonify({
        'success': True,
        'tokens': tokens
    })


@scheduling_bp.route('/tokens', methods=['POST'])
@login_required
@require_permission('schedule.manage')
def create_token():
    """
    Create a self-scheduling token/link.

    Expected JSON body:
    {
        "customer_id": 123,      // optional
        "lead_id": 456,          // optional
        "job_id": 789,           // optional
        "appointment_type": "DROP_OFF",  // optional
        "expires_days": 7,       // optional, default 7
        "max_uses": 1            // optional, default 1
    }
    """
    manager = get_manager()
    organization_id = g.organization_id
    data = request.get_json()

    token = manager.create_scheduling_token(
        organization_id=organization_id,
        customer_id=data.get('customer_id'),
        lead_id=data.get('lead_id'),
        job_id=data.get('job_id'),
        appointment_type=data.get('appointment_type'),
        expires_days=data.get('expires_days', 7),
        max_uses=data.get('max_uses', 1),
        created_by=g.current_user.get('id')
    )

    if token:
        # Build the full URL
        base_url = request.host_url.rstrip('/')
        scheduling_url = f"{base_url}/schedule/{token}"

        return jsonify({
            'success': True,
            'token': token,
            'url': scheduling_url
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to create scheduling token'
        }), 400


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_appointment_color(appointment: dict) -> str:
    """Get color for appointment based on type and status"""
    type_colors = {
        'DROP_OFF': '#3B82F6',      # Blue
        'PICKUP': '#10B981',         # Green
        'ESTIMATE': '#F59E0B',       # Amber
        'INSPECTION': '#8B5CF6',     # Purple
        'FOLLOW_UP': '#6B7280',      # Gray
        'SERVICE': '#EF4444',        # Red
    }

    status_colors = {
        'COMPLETED': '#10B981',      # Green
        'CANCELLED': '#EF4444',      # Red
        'NO_SHOW': '#F59E0B',        # Amber
    }

    # Status takes precedence if not scheduled/confirmed
    status = appointment.get('status', 'SCHEDULED')
    if status in status_colors:
        return status_colors[status]

    # Otherwise use appointment type color
    apt_type = appointment.get('appointment_type', 'SERVICE')
    return type_colors.get(apt_type, '#6B7280')


def format_appointment_title(appointment: dict) -> str:
    """Format appointment title for calendar display"""
    customer_name = appointment.get('customer_name', 'Customer')
    apt_type = appointment.get('appointment_type', 'Appointment')

    # Abbreviate type for display
    type_abbrev = {
        'DROP_OFF': 'Drop-off',
        'PICKUP': 'Pickup',
        'ESTIMATE': 'Est.',
        'INSPECTION': 'Insp.',
        'FOLLOW_UP': 'Follow-up',
        'SERVICE': 'Service',
    }

    type_display = type_abbrev.get(apt_type, apt_type)

    return f"{type_display} - {customer_name}"
