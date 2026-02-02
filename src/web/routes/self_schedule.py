"""
Self-Scheduling Routes (Public)
Customer-facing routes for self-scheduling via token links.

Routes:
- GET  /schedule/<token>              - Self-scheduling page
- GET  /schedule/<token>/dates        - Get available dates
- GET  /schedule/<token>/slots        - Get available slots for date
- POST /schedule/<token>/book         - Book appointment

Auth: Token-based (no login required).
Tokens are validated against scheduling_tokens table.
"""

from flask import (
    Blueprint, render_template, request, jsonify, redirect, url_for, flash
)
from datetime import datetime, timedelta
import os

from src.crm.managers.scheduling_manager import SchedulingManager

# Create blueprint
self_schedule_bp = Blueprint('self_schedule', __name__, url_prefix='/schedule')

# Database path
DB_PATH = os.environ.get('HAILTRACKER_DB', 'data/hailtracker_crm.db')


def get_manager():
    """Get SchedulingManager instance"""
    return SchedulingManager(DB_PATH)


# ============================================================================
# PUBLIC SCHEDULING PAGES
# ============================================================================

@self_schedule_bp.route('/<token>')
def schedule_page(token):
    """
    Self-scheduling landing page.
    Validates token and shows available dates/times.
    """
    manager = get_manager()

    # Validate token
    token_info = manager.validate_token(token)

    if not token_info:
        return render_template('schedule/invalid_token.html',
                             error="This scheduling link is invalid or has expired.")

    # Get organization info for branding
    org_settings = manager.get_scheduling_settings(token_info['organization_id'])

    # Get available dates for next 2 weeks
    available_dates = manager.get_available_dates_for_self_scheduling(
        organization_id=token_info['organization_id'],
        days=14,
        appointment_type=token_info.get('appointment_type', 'DROP_OFF')
    )

    context = {
        'token': token,
        'token_info': token_info,
        'org_settings': org_settings,
        'available_dates': available_dates,
        'appointment_type': token_info.get('appointment_type', 'DROP_OFF'),
        'min_date': datetime.now().strftime('%Y-%m-%d'),
        'max_date': (datetime.now() + timedelta(days=org_settings.get('max_advance_days', 30))).strftime('%Y-%m-%d')
    }

    return render_template('schedule/self_schedule.html', **context)


@self_schedule_bp.route('/<token>/success')
def schedule_success(token):
    """
    Confirmation page after successful booking.
    """
    manager = get_manager()

    # Get appointment details from query params
    appointment_id = request.args.get('appointment_id')
    appointment = None

    if appointment_id:
        appointment = manager.get_appointment(int(appointment_id))

    return render_template('schedule/confirmation.html',
                         token=token,
                         appointment=appointment)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@self_schedule_bp.route('/<token>/dates', methods=['GET'])
def get_available_dates(token):
    """
    Get available dates for self-scheduling.

    Query params:
    - start_date: Optional start date (default: today)
    - days: Number of days to check (default: 14, max: 30)
    """
    manager = get_manager()

    # Validate token
    token_info = manager.validate_token(token)

    if not token_info:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 401

    # Get parameters
    start_date = request.args.get('start_date')
    days = min(request.args.get('days', 14, type=int), 30)

    # Get available dates
    available_dates = manager.get_available_dates_for_self_scheduling(
        organization_id=token_info['organization_id'],
        start_date=start_date,
        days=days,
        appointment_type=token_info.get('appointment_type', 'DROP_OFF')
    )

    return jsonify({
        'success': True,
        'dates': available_dates
    })


@self_schedule_bp.route('/<token>/slots', methods=['GET'])
def get_available_slots(token):
    """
    Get available time slots for a specific date.

    Query params:
    - date: Target date (required, ISO format)
    """
    manager = get_manager()

    # Validate token
    token_info = manager.validate_token(token)

    if not token_info:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 401

    # Get date parameter
    target_date = request.args.get('date')
    if not target_date:
        return jsonify({
            'success': False,
            'error': 'Date is required'
        }), 400

    # Validate date is within allowed range
    org_settings = manager.get_scheduling_settings(token_info['organization_id'])
    min_notice_hours = org_settings.get('min_notice_hours', 24)
    max_advance_days = org_settings.get('max_advance_days', 30)

    try:
        date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        now = datetime.now()

        # Check minimum notice
        min_datetime = now + timedelta(hours=min_notice_hours)
        if date_obj.date() < min_datetime.date():
            return jsonify({
                'success': False,
                'error': f'Appointments must be booked at least {min_notice_hours} hours in advance'
            }), 400

        # Check maximum advance
        max_datetime = now + timedelta(days=max_advance_days)
        if date_obj.date() > max_datetime.date():
            return jsonify({
                'success': False,
                'error': f'Appointments can only be booked up to {max_advance_days} days in advance'
            }), 400

    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400

    # Get available slots
    slots = manager.get_available_slots_for_self_scheduling(
        organization_id=token_info['organization_id'],
        target_date=target_date,
        appointment_type=token_info.get('appointment_type', 'DROP_OFF')
    )

    return jsonify({
        'success': True,
        'date': target_date,
        'slots': slots
    })


@self_schedule_bp.route('/<token>/book', methods=['POST'])
def book_appointment(token):
    """
    Book an appointment using a self-scheduling token.

    Expected JSON body:
    {
        "date": "2024-01-15",
        "time": "09:00",
        "customer_info": {           // Required if token not linked to customer
            "first_name": "John",
            "last_name": "Doe",
            "phone": "555-123-4567",
            "email": "john@example.com"  // optional
        },
        "notes": "Customer note"     // optional
    }
    """
    manager = get_manager()

    # Validate token first
    token_info = manager.validate_token(token)

    if not token_info:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 401

    # Get request data
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body is required'
        }), 400

    # Validate required fields
    if not data.get('date'):
        return jsonify({
            'success': False,
            'error': 'Date is required'
        }), 400

    if not data.get('time'):
        return jsonify({
            'success': False,
            'error': 'Time is required'
        }), 400

    # If token isn't linked to a customer, customer_info is required
    if not token_info.get('customer_id') and not data.get('customer_info'):
        return jsonify({
            'success': False,
            'error': 'Customer information is required'
        }), 400

    # Validate customer info if provided
    customer_info = data.get('customer_info')
    if customer_info:
        required_customer_fields = ['first_name', 'last_name', 'phone']
        missing = [f for f in required_customer_fields if not customer_info.get(f)]
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing customer information: {", ".join(missing)}'
            }), 400

    # Book the appointment
    result = manager.book_via_token(
        token=token,
        appointment_date=data['date'],
        start_time=data['time'],
        customer_info=customer_info,
        notes=data.get('notes')
    )

    if result.get('success'):
        return jsonify(result), 201
    else:
        return jsonify(result), 400


# ============================================================================
# CONFIRMATION/CANCELLATION
# ============================================================================

@self_schedule_bp.route('/<token>/cancel', methods=['POST'])
def cancel_appointment(token):
    """
    Cancel an appointment booked via self-scheduling.

    Expected JSON body:
    {
        "appointment_id": 123,
        "reason": "Schedule conflict"  // optional
    }
    """
    manager = get_manager()

    # Validate token
    token_info = manager.validate_token(token)

    if not token_info:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 401

    data = request.get_json()

    if not data.get('appointment_id'):
        return jsonify({
            'success': False,
            'error': 'Appointment ID is required'
        }), 400

    # Verify the appointment belongs to this token's customer/job
    appointment = manager.get_appointment(data['appointment_id'])

    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404

    # Security check: ensure appointment matches token scope
    if token_info.get('customer_id') and appointment.get('customer_id') != token_info['customer_id']:
        return jsonify({
            'success': False,
            'error': 'Access denied'
        }), 403

    if token_info.get('job_id') and appointment.get('job_id') != token_info['job_id']:
        return jsonify({
            'success': False,
            'error': 'Access denied'
        }), 403

    # Cancel the appointment
    result = manager.cancel_appointment(
        appointment_id=data['appointment_id'],
        cancelled_by=None,  # Self-cancelled
        reason=data.get('reason', 'Cancelled by customer')
    )

    return jsonify(result), 200 if result.get('success') else 400


# ============================================================================
# ORGANIZATION INFO
# ============================================================================

@self_schedule_bp.route('/<token>/info', methods=['GET'])
def get_org_info(token):
    """
    Get organization info for the scheduling page.
    Returns branding, contact info, etc.
    """
    manager = get_manager()

    # Validate token
    token_info = manager.validate_token(token)

    if not token_info:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 401

    # Get organization settings
    org_settings = manager.get_scheduling_settings(token_info['organization_id'])

    # Return only public info
    public_info = {
        'organization_name': org_settings.get('organization_name', 'Our Shop'),
        'business_hours': org_settings.get('business_hours'),
        'min_notice_hours': org_settings.get('min_notice_hours', 24),
        'max_advance_days': org_settings.get('max_advance_days', 30),
        'allowed_appointment_types': org_settings.get('allowed_appointment_types', ['DROP_OFF', 'ESTIMATE']),
        'confirmation_message': org_settings.get('confirmation_message')
    }

    return jsonify({
        'success': True,
        'info': public_info
    })
