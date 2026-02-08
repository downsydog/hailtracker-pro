"""
Kiosk Customer Intake Routes
Tablet-friendly walk-in customer intake system.

Routes:
- GET  /kiosk/               - Device setup (enter token)
- POST /kiosk/activate       - Activate kiosk with token
- GET  /kiosk/welcome        - Welcome screen
- GET  /kiosk/intake         - Intake form
- POST /kiosk/intake         - Process intake
- GET  /kiosk/thankyou       - Thank you screen
- GET  /kiosk/error          - Error screen
- GET  /kiosk/api/status     - Device status check

Auth: Device token stored in session/cookie after activation.
No user login required - uses kiosk_devices table for auth.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    jsonify, flash, session, make_response, g
)
from functools import wraps
from datetime import datetime, timedelta
import os

from src.crm.managers.kiosk_intake_manager import KioskIntakeManager

# Create blueprint
kiosk_bp = Blueprint('kiosk', __name__, url_prefix='/kiosk')

# Database path
DB_PATH = os.environ.get('HAILTRACKER_DB', 'data/hailtracker_crm.db')


def get_manager():
    """Get KioskIntakeManager instance"""
    return KioskIntakeManager(DB_PATH)


def get_device_token():
    """Get device token from session or cookie"""
    return session.get('kiosk_token') or request.cookies.get('kiosk_token')


def kiosk_required(f):
    """Decorator to require valid kiosk device token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_device_token()
        if not token:
            return redirect(url_for('kiosk.setup'))

        manager = get_manager()
        device = manager.validate_device(token)

        if not device:
            # Invalid token - clear and redirect to setup
            session.pop('kiosk_token', None)
            response = make_response(redirect(url_for('kiosk.setup')))
            response.delete_cookie('kiosk_token')
            flash('Kiosk session expired. Please re-enter device token.', 'warning')
            return response

        # Store device info in g for use in route
        g.kiosk_device = device
        g.organization_id = device['organization_id']
        g.account_id = device['account_id']

        # Update device activity
        manager.update_device_activity(
            token,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )

        return f(*args, **kwargs)
    return decorated_function


def rate_limit(f):
    """Rate limiting decorator for intake submissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        manager = get_manager()
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        token = get_device_token()

        # Check rate limit (10 submissions per hour per IP/device)
        if not manager.check_rate_limit(ip or token, limit=10, window_minutes=60):
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Too many submissions. Please wait and try again.'
                }), 429
            return redirect(url_for('kiosk.error', reason='rate_limit'))

        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# DEVICE SETUP
# ============================================================================

@kiosk_bp.route('/')
def setup():
    """
    Kiosk setup screen - enter device token.
    This is shown when the kiosk hasn't been activated yet.
    """
    # Check if already activated
    token = get_device_token()
    if token:
        manager = get_manager()
        device = manager.validate_device(token)
        if device:
            return redirect(url_for('kiosk.welcome'))

    return render_template('kiosk/setup.html')


@kiosk_bp.route('/<device_token>')
def quick_activate(device_token):
    """
    Quick activation via URL with device token.
    Allows direct link like /kiosk/ABC123 to auto-activate.
    """
    manager = get_manager()
    device = manager.validate_device(device_token)

    if not device:
        flash('Invalid device token. Please contact support.', 'error')
        return redirect(url_for('kiosk.setup'))

    # Store token in session
    session['kiosk_token'] = device_token

    # Create response with cookie
    response = make_response(redirect(url_for('kiosk.welcome')))
    response.set_cookie(
        'kiosk_token',
        device_token,
        max_age=60 * 60 * 24 * 365,  # 1 year
        httponly=True,
        secure=request.is_secure,
        samesite='Lax'
    )

    # Update device activity
    manager.update_device_activity(
        device_token,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    return response


@kiosk_bp.route('/activate', methods=['POST'])
def activate():
    """Activate kiosk with device token"""
    token = request.form.get('device_token', '').strip()

    if not token:
        flash('Please enter a device token.', 'error')
        return redirect(url_for('kiosk.setup'))

    manager = get_manager()
    device = manager.validate_device(token)

    if not device:
        flash('Invalid device token. Please check and try again.', 'error')
        return redirect(url_for('kiosk.setup'))

    # Store token in session and cookie
    session['kiosk_token'] = token
    session.permanent = True

    response = make_response(redirect(url_for('kiosk.welcome')))

    # Set long-lived cookie (30 days)
    response.set_cookie(
        'kiosk_token',
        token,
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        samesite='Lax'
    )

    # Update device activity
    manager.update_device_activity(
        token,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    flash(f'Kiosk activated: {device["name"]}', 'success')
    return response


@kiosk_bp.route('/deactivate', methods=['POST'])
def deactivate():
    """Deactivate kiosk (admin action)"""
    session.pop('kiosk_token', None)
    response = make_response(redirect(url_for('kiosk.setup')))
    response.delete_cookie('kiosk_token')
    flash('Kiosk deactivated.', 'info')
    return response


# ============================================================================
# MAIN FLOW
# ============================================================================

@kiosk_bp.route('/welcome')
@kiosk_required
def welcome():
    """
    Welcome screen - shown to walk-in customers.
    Big "Check In" button to start the intake process.
    """
    device = g.kiosk_device
    manager = get_manager()
    org_settings = manager.get_kiosk_settings(device['organization_id'])

    return render_template('kiosk/welcome.html',
                          device=device,
                          org_settings=org_settings,
                          welcome_message=device.get('welcome_message') or
                                         f"Welcome to {org_settings.get('organization_name', 'our shop')}!")


@kiosk_bp.route('/intake', methods=['GET'])
@kiosk_required
def intake_form():
    """Display the intake form"""
    device = g.kiosk_device
    manager = get_manager()

    context = {
        'device': device,
        'insurance_companies': manager.get_insurance_companies(device['organization_id']),
        'lead_sources': manager.get_lead_sources(),
        'vehicle_makes': manager.get_vehicle_makes(),
        'vehicle_years': manager.get_vehicle_years(),
        'us_states': manager.get_us_states(),
        'auto_reset_seconds': device.get('auto_reset_seconds', 30),
    }

    return render_template('kiosk/intake_form.html', **context)


@kiosk_bp.route('/intake', methods=['POST'])
@kiosk_required
@rate_limit
def process_intake():
    """Process the intake form submission"""
    device = g.kiosk_device
    token = get_device_token()
    manager = get_manager()

    # Gather form data
    form_data = {
        # Contact info
        'first_name': request.form.get('first_name', ''),
        'last_name': request.form.get('last_name', ''),
        'phone': request.form.get('phone', ''),
        'email': request.form.get('email', ''),
        'address_line1': request.form.get('address_line1', ''),
        'address_line2': request.form.get('address_line2', ''),
        'city': request.form.get('city', ''),
        'state': request.form.get('state', ''),
        'zip_code': request.form.get('zip_code', ''),

        # Vehicle info
        'vin': request.form.get('vin', ''),
        'vehicle_year': request.form.get('vehicle_year', ''),
        'vehicle_make': request.form.get('vehicle_make', ''),
        'vehicle_model': request.form.get('vehicle_model', ''),
        'vehicle_color': request.form.get('vehicle_color', ''),
        'license_plate': request.form.get('license_plate', ''),

        # Insurance info
        'insurance_company': request.form.get('insurance_company', ''),
        'policy_number': request.form.get('policy_number', ''),
        'claim_number': request.form.get('claim_number', ''),

        # Source info
        'source': request.form.get('source', 'WALK_IN'),
        'referrer_name': request.form.get('referrer_name', ''),

        # Consent
        'consent_sms': request.form.get('consent_sms') == 'on',
        'consent_email': request.form.get('consent_email') == 'on',

        # Metadata
        'ip_address': request.headers.get('X-Forwarded-For', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', ''),
        'submitted_at': datetime.now().isoformat()
    }

    # Handle "Other" insurance
    if form_data['insurance_company'] == 'other':
        form_data['insurance_company'] = request.form.get('insurance_company_other', '')

    # Process the intake
    result = manager.process_intake(token, form_data)

    if result['success']:
        return redirect(url_for('kiosk.thankyou',
                               name=result.get('customer_name', ''),
                               vehicle=result.get('vehicle_description', '')))
    else:
        # Store errors in session for display
        session['intake_errors'] = result.get('errors', [{'message': result.get('error', 'Unknown error')}])
        return redirect(url_for('kiosk.error', reason='validation'))


@kiosk_bp.route('/thankyou')
@kiosk_required
def thankyou():
    """
    Thank you screen after successful submission.
    Auto-resets to welcome screen after configured seconds.
    """
    device = g.kiosk_device
    manager = get_manager()
    org_settings = manager.get_kiosk_settings(device['organization_id'])

    return render_template('kiosk/thankyou.html',
                          device=device,
                          org_settings=org_settings,
                          customer_name=request.args.get('name', ''),
                          vehicle=request.args.get('vehicle', ''),
                          auto_reset_seconds=device.get('auto_reset_seconds', 30))


@kiosk_bp.route('/error')
@kiosk_required
def error():
    """
    Error screen for validation or processing errors.
    Shows errors and allows retry.
    """
    device = g.kiosk_device
    reason = request.args.get('reason', 'unknown')
    errors = session.pop('intake_errors', [])

    error_messages = {
        'validation': 'Please check the information below and try again.',
        'rate_limit': 'Too many submissions. Please wait a moment and try again.',
        'processing': 'There was a problem processing your information.',
        'unknown': 'An unexpected error occurred.'
    }

    return render_template('kiosk/error.html',
                          device=device,
                          reason=reason,
                          error_message=error_messages.get(reason, error_messages['unknown']),
                          errors=errors,
                          auto_reset_seconds=device.get('auto_reset_seconds', 30))


# ============================================================================
# API ENDPOINTS
# ============================================================================

@kiosk_bp.route('/api/status')
def api_status():
    """Check kiosk device status"""
    token = get_device_token()
    if not token:
        return jsonify({'active': False, 'error': 'No device token'})

    manager = get_manager()
    device = manager.validate_device(token)

    if device:
        return jsonify({
            'active': True,
            'device_name': device['name'],
            'organization': device['organization_name'],
            'auto_reset_seconds': device.get('auto_reset_seconds', 30)
        })
    else:
        return jsonify({'active': False, 'error': 'Invalid or inactive device'})


@kiosk_bp.route('/api/intake', methods=['POST'])
@kiosk_required
@rate_limit
def api_process_intake():
    """JSON API for intake form (supports offline queue)"""
    token = get_device_token()
    manager = get_manager()

    if not request.is_json:
        return jsonify({'success': False, 'error': 'JSON required'}), 400

    form_data = request.get_json()

    # Add metadata
    form_data['ip_address'] = request.headers.get('X-Forwarded-For', request.remote_addr)
    form_data['user_agent'] = request.headers.get('User-Agent', '')
    form_data['submitted_at'] = datetime.now().isoformat()

    # Process the intake
    result = manager.process_intake(token, form_data)

    return jsonify(result), 200 if result['success'] else 400


@kiosk_bp.route('/api/makes')
def api_get_makes():
    """Get vehicle makes for dropdown"""
    manager = get_manager()
    return jsonify({'makes': manager.get_vehicle_makes()})


@kiosk_bp.route('/api/insurance')
def api_get_insurance():
    """Get insurance companies for dropdown"""
    manager = get_manager()
    token = get_device_token()
    device = manager.validate_device(token) if token else None
    org_id = device['organization_id'] if device else None

    companies = manager.get_insurance_companies(org_id)
    return jsonify({'companies': companies})


@kiosk_bp.route('/api/decode-vin/<vin>')
def api_decode_vin(vin):
    """Decode VIN and return vehicle info"""
    try:
        from src.utils.vin_decoder import decode_vin
        result = decode_vin(vin, DB_PATH)
        return jsonify(result)
    except ImportError:
        return jsonify({'success': False, 'error': 'VIN decoder not available'})


# ============================================================================
# ADMIN ENDPOINTS (require staff login)
# ============================================================================

@kiosk_bp.route('/admin/recent')
def admin_recent_submissions():
    """
    View recent kiosk submissions.
    Requires staff authentication (handled by middleware).
    """
    from flask import g

    # Check for logged-in user via middleware
    if not g.get('current_user'):
        flash('Please log in to view submissions.', 'warning')
        return redirect(url_for('auth.login', next=request.url))

    # Check permission
    user_perms = g.current_user.get('permissions', [])
    if 'leads.view_all' not in user_perms and 'customers.view_all' not in user_perms:
        flash('You do not have permission to view submissions.', 'error')
        return redirect(url_for('crm.dashboard'))

    organization_id = g.get('organization_id')
    if not organization_id:
        flash('No organization context.', 'error')
        return redirect(url_for('crm.dashboard'))

    manager = get_manager()
    submissions = manager.get_recent_submissions(organization_id, limit=50)

    return render_template('kiosk/admin_recent.html', submissions=submissions)
