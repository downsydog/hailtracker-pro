"""
Customer Self-Intake Routes
Public tablet form for lobby walk-ins

Routes:
- GET  /intake/customer     - Display intake form
- POST /intake/customer     - Process intake submission
- POST /intake/customer/api - JSON API for offline queue processing
- GET  /intake/success      - Success/confirmation page
- GET  /intake/api/makes    - Get vehicle makes
- GET  /intake/api/insurance - Get insurance companies
- GET  /intake/api/salespeople - Get salespeople for door knocker

No login required - public form with rate limiting
"""

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from functools import wraps
from datetime import datetime
import os
import json

from src.crm.managers.customer_intake_manager import CustomerIntakeManager

# Create blueprint
customer_intake_bp = Blueprint('customer_intake', __name__, url_prefix='/intake')

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '../../../data/pdr_crm.db')


def get_intake_manager():
    """Get CustomerIntakeManager instance"""
    return CustomerIntakeManager(DB_PATH)


def rate_limit(f):
    """Rate limiting decorator for intake form"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        manager = get_intake_manager()
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        if not manager.check_rate_limit(ip, limit=10, window_minutes=60):
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Too many submissions. Please wait and try again.'
                }), 429
            flash('Too many submissions. Please wait and try again.', 'error')
            return redirect(url_for('customer_intake.intake_form'))

        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# MAIN INTAKE FORM
# ============================================================================

@customer_intake_bp.route('/customer', methods=['GET'])
def intake_form():
    """Display customer intake form"""
    manager = get_intake_manager()

    context = {
        'insurance_companies': manager.get_insurance_companies(),
        'salespeople': manager.get_salespeople(),
        'vehicle_makes': manager.get_vehicle_makes(),
        'vehicle_years': manager.get_vehicle_years(),
        'us_states': manager.get_us_states(),
        'lead_sources': manager.get_lead_sources(),
        'current_step': 1,
        'total_steps': 5
    }

    return render_template('intake/customer_intake.html', **context)


@customer_intake_bp.route('/customer', methods=['POST'])
@rate_limit
def process_intake():
    """Process intake form submission"""
    manager = get_intake_manager()

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
        'mileage': request.form.get('mileage', ''),

        # Insurance info
        'insurance_company': request.form.get('insurance_company', ''),
        'insurance_company_other': request.form.get('insurance_company_other', ''),
        'policy_number': request.form.get('policy_number', ''),
        'claim_number': request.form.get('claim_number', ''),
        'has_deductible': request.form.get('has_deductible') == 'yes',
        'deductible_amount': request.form.get('deductible_amount', ''),

        # Source info
        'source': request.form.get('source', ''),
        'referrer_name': request.form.get('referrer_name', ''),
        'salesman_id': request.form.get('salesman_id', ''),

        # Consent
        'consent_sms': request.form.get('consent_sms') == 'on',
        'consent_email': request.form.get('consent_email') == 'on',
        'signature_data': request.form.get('signature_data', ''),

        # Metadata
        'ip_address': request.headers.get('X-Forwarded-For', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', ''),
        'submitted_at': datetime.now().isoformat()
    }

    # Handle "Other" insurance company
    if form_data['insurance_company'] == 'other' and form_data['insurance_company_other']:
        form_data['insurance_company'] = form_data['insurance_company_other']

    # Process the intake
    result = manager.process_intake(form_data)

    if result['success']:
        # Redirect to success page
        return redirect(url_for('customer_intake.success',
                               name=result.get('customer_name', ''),
                               vehicle=result.get('vehicle_description', '')))
    else:
        # Return to form with errors
        for error in result.get('errors', []):
            if isinstance(error, dict):
                flash(f"{error.get('field', 'Error')}: {error.get('message', '')}", 'error')
            else:
                flash(str(error), 'error')

        return redirect(url_for('customer_intake.intake_form'))


@customer_intake_bp.route('/success')
def success():
    """Display success/confirmation page"""
    return render_template('intake/intake_success.html',
                          customer_name=request.args.get('name', ''),
                          vehicle=request.args.get('vehicle', ''))


# ============================================================================
# API ENDPOINTS (for AJAX and offline queue)
# ============================================================================

@customer_intake_bp.route('/customer/api', methods=['POST'])
@rate_limit
def api_process_intake():
    """JSON API for intake form (supports offline queue)"""
    manager = get_intake_manager()

    if not request.is_json:
        return jsonify({'success': False, 'error': 'JSON required'}), 400

    form_data = request.get_json()

    # Add metadata
    form_data['ip_address'] = request.headers.get('X-Forwarded-For', request.remote_addr)
    form_data['user_agent'] = request.headers.get('User-Agent', '')

    # Process the intake
    result = manager.process_intake(form_data)

    return jsonify(result), 200 if result['success'] else 400


@customer_intake_bp.route('/api/makes', methods=['GET'])
def api_get_makes():
    """Get vehicle makes for dropdown"""
    manager = get_intake_manager()
    return jsonify({'makes': manager.get_vehicle_makes()})


@customer_intake_bp.route('/api/insurance', methods=['GET'])
def api_get_insurance():
    """Get insurance companies for dropdown"""
    manager = get_intake_manager()
    companies = manager.get_insurance_companies()
    return jsonify({'companies': [dict(c) for c in companies]})


@customer_intake_bp.route('/api/salespeople', methods=['GET'])
def api_get_salespeople():
    """Get salespeople for door knocker dropdown"""
    manager = get_intake_manager()
    salespeople = manager.get_salespeople()
    return jsonify({'salespeople': [dict(s) for s in salespeople]})


@customer_intake_bp.route('/api/decode-vin/<vin>', methods=['GET'])
def api_decode_vin(vin):
    """Decode VIN and return vehicle info"""
    from src.utils.vin_decoder import decode_vin
    result = decode_vin(vin, DB_PATH)
    return jsonify(result)


@customer_intake_bp.route('/api/autosave', methods=['POST'])
def api_autosave():
    """
    Autosave form data (stores in session/local storage on client).
    This endpoint just validates the data format.
    """
    if not request.is_json:
        return jsonify({'success': False}), 400

    # Just acknowledge receipt - actual storage is client-side
    return jsonify({
        'success': True,
        'saved_at': datetime.now().isoformat()
    })


@customer_intake_bp.route('/api/queue-sync', methods=['POST'])
@rate_limit
def api_queue_sync():
    """
    Process multiple queued submissions from offline mode.
    Used when tablet comes back online.
    """
    manager = get_intake_manager()

    if not request.is_json:
        return jsonify({'success': False, 'error': 'JSON required'}), 400

    data = request.get_json()
    submissions = data.get('submissions', [])

    results = []
    for submission in submissions:
        result = manager.process_queued_submission(submission)
        results.append({
            'queue_id': submission.get('queue_id'),
            'success': result['success'],
            'customer_id': result.get('customer_id'),
            'message': result.get('message')
        })

    successful = sum(1 for r in results if r['success'])

    return jsonify({
        'success': True,
        'processed': len(results),
        'successful': successful,
        'failed': len(results) - successful,
        'results': results
    })


# ============================================================================
# OFFICE VIEW (for staff to see recent submissions)
# ============================================================================

@customer_intake_bp.route('/office/recent')
def office_recent():
    """View recent intake submissions (requires staff login)"""
    # TODO: Add staff authentication check

    manager = get_intake_manager()
    submissions = manager.get_recent_submissions(limit=20)

    return render_template('intake/office_recent.html',
                          submissions=submissions)
