"""
Customer Portal Routes
Self-service portal for customers to track repairs, manage referrals, and view flyers

Routes:
- /portal/login - Customer login
- /portal/logout - Customer logout
- /portal/dashboard - Main dashboard
- /portal/jobs - View all jobs
- /portal/jobs/<id> - Job details with timeline
- /portal/referrals - Referral dashboard
- /portal/referrals/create - Create new referral
- /portal/flyers - View personalized flyers
- /portal/flyers/<id> - View specific flyer
- /portal/profile - Customer profile
- /portal/documents - View documents
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, abort, Response
from functools import wraps
from datetime import datetime
import os
import json
import time

from src.crm.managers.customer_portal_manager import CustomerPortalManager
from src.crm.managers.digital_flyer_manager import DigitalFlyerManager
from src.crm.managers.job_notification_manager import JobNotificationManager

# Create blueprint
customer_portal_bp = Blueprint('customer_portal', __name__, url_prefix='/portal')

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '../../../data/pdr_crm.db')


# ============================================================================
# AUTHENTICATION DECORATOR
# ============================================================================

def portal_login_required(f):
    """Decorator to require customer portal login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'portal_customer_id' not in session:
            flash('Please log in to access the customer portal.', 'warning')
            return redirect(url_for('customer_portal.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_portal_manager():
    """Get CustomerPortalManager instance"""
    return CustomerPortalManager(DB_PATH)


def get_flyer_manager():
    """Get DigitalFlyerManager instance"""
    return DigitalFlyerManager(DB_PATH)


def get_notification_manager():
    """Get JobNotificationManager instance"""
    return JobNotificationManager(DB_PATH)


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@customer_portal_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Customer portal login page"""

    # Redirect if already logged in
    if 'portal_customer_id' in session:
        return redirect(url_for('customer_portal.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('customer_portal/login.html')

        manager = get_portal_manager()
        customer = manager.customer_login(username=username, password=password)

        if customer:
            # Set session variables
            session['portal_customer_id'] = customer['customer_id']
            session['portal_customer_name'] = f"{customer['first_name']} {customer['last_name']}"
            session['portal_username'] = username
            session['portal_login_time'] = datetime.now().isoformat()

            flash(f"Welcome back, {customer['first_name']}!", 'success')
            return redirect(url_for('customer_portal.dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('customer_portal/login.html')


@customer_portal_bp.route('/logout')
def logout():
    """Customer portal logout"""

    # Clear portal session
    session.pop('portal_customer_id', None)
    session.pop('portal_customer_name', None)
    session.pop('portal_username', None)
    session.pop('portal_login_time', None)

    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('customer_portal.login'))


# ============================================================================
# DASHBOARD
# ============================================================================

@customer_portal_bp.route('/')
@customer_portal_bp.route('/dashboard')
@portal_login_required
def dashboard():
    """Main customer portal dashboard"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Get dashboard data
    dashboard_data = manager.get_portal_dashboard(customer_id)

    return render_template('customer_portal/dashboard.html',
        customer_name=session.get('portal_customer_name'),
        dashboard=dashboard_data
    )


# ============================================================================
# JOB TRACKING
# ============================================================================

@customer_portal_bp.route('/jobs')
@portal_login_required
def jobs():
    """View all customer jobs"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Get active jobs
    active_jobs = manager.get_job_status(customer_id)

    # Get service history
    history = manager.get_service_history(customer_id, limit=10)

    return render_template('customer_portal/jobs.html',
        customer_name=session.get('portal_customer_name'),
        active_jobs=active_jobs,
        history=history
    )


@customer_portal_bp.route('/jobs/<int:job_id>')
@portal_login_required
def job_detail(job_id):
    """View specific job details with timeline"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Get job status (verifies ownership)
    jobs = manager.get_job_status(customer_id, job_id=job_id)

    if not jobs:
        flash('Job not found.', 'error')
        return redirect(url_for('customer_portal.jobs'))

    job = jobs[0]

    # Get status timeline
    timeline = manager.get_status_timeline(job_id)

    # Get status details for current status
    status_details = manager._get_job_status_details(job['status'])

    return render_template('customer_portal/job_detail.html',
        customer_name=session.get('portal_customer_name'),
        job=job,
        timeline=timeline,
        status_details=status_details
    )


# ============================================================================
# REFERRAL SYSTEM
# ============================================================================

@customer_portal_bp.route('/referrals')
@portal_login_required
def referrals():
    """Referral dashboard"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Get referral dashboard
    referral_data = manager.get_referral_dashboard(customer_id)

    return render_template('customer_portal/referrals.html',
        customer_name=session.get('portal_customer_name'),
        referrals=referral_data
    )


@customer_portal_bp.route('/referrals/share')
@portal_login_required
def share_referral():
    """Get shareable referral link and flyer"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()
    flyer_manager = get_flyer_manager()

    # Get referral link
    referral_data = manager.get_referral_dashboard(customer_id)
    referral_link = referral_data['referral_link']

    # Get customer's personalized flyers
    flyers = flyer_manager.get_customer_flyers(customer_id)

    return render_template('customer_portal/share_referral.html',
        customer_name=session.get('portal_customer_name'),
        referral_link=referral_link,
        flyers=flyers,
        earnings=referral_data['earnings']
    )


@customer_portal_bp.route('/referrals/track-click', methods=['POST'])
def track_referral_click():
    """Track when referral link is clicked (public endpoint)"""

    data = request.get_json() or {}
    referrer_id = data.get('referrer_id')
    click_source = data.get('source', 'LINK')

    if not referrer_id:
        return jsonify({'error': 'Missing referrer_id'}), 400

    manager = get_portal_manager()

    manager.track_referral_click(
        referrer_customer_id=int(referrer_id),
        click_source=click_source,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    return jsonify({'success': True})


# ============================================================================
# DIGITAL FLYERS
# ============================================================================

@customer_portal_bp.route('/flyers')
@portal_login_required
def flyers():
    """View personalized flyers"""

    customer_id = session['portal_customer_id']
    flyer_manager = get_flyer_manager()

    # Get customer's flyers
    customer_flyers = flyer_manager.get_customer_flyers(customer_id)

    # Get available flyer templates
    available_flyers = flyer_manager.get_active_flyers()

    return render_template('customer_portal/flyers.html',
        customer_name=session.get('portal_customer_name'),
        customer_flyers=customer_flyers,
        available_flyers=available_flyers
    )


@customer_portal_bp.route('/flyers/generate/<int:flyer_id>', methods=['POST'])
@portal_login_required
def generate_flyer(flyer_id):
    """Generate personalized flyer for customer"""

    customer_id = session['portal_customer_id']
    flyer_manager = get_flyer_manager()

    try:
        result = flyer_manager.generate_personalized_flyer(customer_id, flyer_id)
        flash('Your personalized flyer has been created!', 'success')
        return redirect(url_for('customer_portal.flyers'))
    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('customer_portal.flyers'))


@customer_portal_bp.route('/flyers/view/<flyer_token>')
def view_flyer(flyer_token):
    """Public view of personalized flyer (tracks views)"""

    flyer_manager = get_flyer_manager()

    flyer_url = f"https://flyers.pdrcrm.com/{flyer_token}"
    flyer = flyer_manager.get_personalized_flyer(flyer_url)

    if not flyer:
        abort(404)

    # Track the view
    flyer_manager.track_flyer_view(
        customer_id=flyer['customer_id'],
        flyer_id=flyer['flyer_id'],
        viewer_ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )

    return render_template('customer_portal/view_flyer.html',
        flyer=flyer
    )


@customer_portal_bp.route('/flyers/analytics')
@portal_login_required
def flyer_analytics():
    """View flyer analytics"""

    customer_id = session['portal_customer_id']
    flyer_manager = get_flyer_manager()

    analytics = flyer_manager.get_flyer_analytics(customer_id)

    return render_template('customer_portal/flyer_analytics.html',
        customer_name=session.get('portal_customer_name'),
        analytics=analytics
    )


# ============================================================================
# APPOINTMENTS
# ============================================================================

@customer_portal_bp.route('/appointments')
@portal_login_required
def appointments():
    """View and manage appointments"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Get upcoming appointments
    upcoming = manager.get_customer_appointments(customer_id, upcoming_only=True)

    # Get past appointments
    past = manager.get_customer_appointments(customer_id, upcoming_only=False)

    return render_template('customer_portal/appointments.html',
        customer_name=session.get('portal_customer_name'),
        upcoming_appointments=upcoming,
        past_appointments=past
    )


@customer_portal_bp.route('/appointments/book', methods=['GET', 'POST'])
@portal_login_required
def book_appointment():
    """Book a new appointment"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    if request.method == 'POST':
        from datetime import date

        service_date = request.form.get('service_date')
        service_time = request.form.get('service_time')
        service_type = request.form.get('service_type', 'PDR')
        damage_description = request.form.get('damage_description', '')

        # Parse date
        try:
            service_date = date.fromisoformat(service_date)
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('customer_portal.book_appointment'))

        # Vehicle info from form
        vehicle_info = {
            'year': request.form.get('vehicle_year'),
            'make': request.form.get('vehicle_make'),
            'model': request.form.get('vehicle_model')
        }

        appointment_id = manager.book_appointment(
            customer_id=customer_id,
            service_date=service_date,
            service_time=service_time,
            service_type=service_type,
            vehicle_info=vehicle_info,
            damage_description=damage_description
        )

        flash('Your appointment has been booked!', 'success')
        return redirect(url_for('customer_portal.appointments'))

    # GET - show booking form
    from datetime import date
    today = date.today()

    # Get available slots for next 14 days
    available_dates = []
    for i in range(1, 15):
        check_date = date(today.year, today.month, today.day)
        from datetime import timedelta
        check_date = today + timedelta(days=i)

        # Skip weekends
        if check_date.weekday() < 5:
            slots = manager.get_available_slots(check_date)
            available_slots = [s for s in slots if s['available']]
            if available_slots:
                available_dates.append({
                    'date': check_date.isoformat(),
                    'display': check_date.strftime('%A, %B %d, %Y'),
                    'slots': available_slots
                })

    return render_template('customer_portal/book_appointment.html',
        customer_name=session.get('portal_customer_name'),
        available_dates=available_dates
    )


@customer_portal_bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@portal_login_required
def cancel_appointment(appointment_id):
    """Cancel an appointment"""

    manager = get_portal_manager()
    reason = request.form.get('reason', '')

    manager.cancel_appointment(appointment_id, reason)

    flash('Your appointment has been cancelled.', 'info')
    return redirect(url_for('customer_portal.appointments'))


# ============================================================================
# INVOICES & PAYMENTS
# ============================================================================

@customer_portal_bp.route('/invoices')
@portal_login_required
def invoices():
    """View invoices"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Get all invoices
    all_invoices = manager.get_customer_invoices(customer_id, unpaid_only=False)

    # Get unpaid invoices
    unpaid = manager.get_customer_invoices(customer_id, unpaid_only=True)

    return render_template('customer_portal/invoices.html',
        customer_name=session.get('portal_customer_name'),
        invoices=all_invoices,
        unpaid_invoices=unpaid
    )


@customer_portal_bp.route('/invoices/<int:invoice_id>/pay', methods=['GET', 'POST'])
@portal_login_required
def pay_invoice(invoice_id):
    """Pay an invoice"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Create payment link
    # In production, this would integrate with Stripe/Square/etc.
    invoices = manager.get_customer_invoices(customer_id)
    invoice = next((inv for inv in invoices if inv['id'] == invoice_id), None)

    if not invoice:
        flash('Invoice not found.', 'error')
        return redirect(url_for('customer_portal.invoices'))

    if request.method == 'POST':
        # Handle payment (mock for now)
        flash('Payment processed successfully!', 'success')
        return redirect(url_for('customer_portal.invoices'))

    payment_link = manager.create_payment_link(invoice_id, invoice.get('balance_due', 0))

    return render_template('customer_portal/pay_invoice.html',
        customer_name=session.get('portal_customer_name'),
        invoice=invoice,
        payment_link=payment_link
    )


# ============================================================================
# MESSAGES
# ============================================================================

@customer_portal_bp.route('/messages')
@portal_login_required
def messages():
    """View messages"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    all_messages = manager.get_messages(customer_id)
    unread = manager.get_messages(customer_id, unread_only=True)

    return render_template('customer_portal/messages.html',
        customer_name=session.get('portal_customer_name'),
        messages=all_messages,
        unread_count=len(unread)
    )


@customer_portal_bp.route('/messages/send', methods=['POST'])
@portal_login_required
def send_message():
    """Send a message"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    subject = request.form.get('subject', '')
    message = request.form.get('message', '')
    job_id = request.form.get('job_id')

    if not message:
        flash('Please enter a message.', 'error')
        return redirect(url_for('customer_portal.messages'))

    manager.send_message(
        customer_id=customer_id,
        subject=subject,
        message=message,
        related_job_id=int(job_id) if job_id else None
    )

    flash('Your message has been sent!', 'success')
    return redirect(url_for('customer_portal.messages'))


@customer_portal_bp.route('/messages/<int:message_id>/read', methods=['POST'])
@portal_login_required
def mark_message_read(message_id):
    """Mark message as read"""

    manager = get_portal_manager()
    manager.mark_message_read(message_id)

    return jsonify({'success': True})


# ============================================================================
# LOYALTY PROGRAM
# ============================================================================

@customer_portal_bp.route('/loyalty')
@portal_login_required
def loyalty():
    """View loyalty points and rewards"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    loyalty_data = manager.get_loyalty_points(customer_id)

    return render_template('customer_portal/loyalty.html',
        customer_name=session.get('portal_customer_name'),
        loyalty=loyalty_data
    )


# ============================================================================
# REVIEWS
# ============================================================================

@customer_portal_bp.route('/reviews')
@portal_login_required
def reviews():
    """View submitted reviews"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    customer_reviews = manager.get_customer_reviews(customer_id)

    return render_template('customer_portal/reviews.html',
        customer_name=session.get('portal_customer_name'),
        reviews=customer_reviews
    )


@customer_portal_bp.route('/reviews/submit/<int:job_id>', methods=['GET', 'POST'])
@portal_login_required
def submit_review(job_id):
    """Submit a review for a completed job"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Check if review is eligible
    review_request = manager.get_review_request(job_id)

    if not review_request:
        flash('This job is not eligible for review.', 'error')
        return redirect(url_for('customer_portal.jobs'))

    if request.method == 'POST':
        rating = int(request.form.get('rating', 5))
        review_text = request.form.get('review_text', '')
        would_recommend = request.form.get('would_recommend', 'yes') == 'yes'

        manager.submit_review(
            customer_id=customer_id,
            job_id=job_id,
            rating=rating,
            review_text=review_text,
            would_recommend=would_recommend
        )

        flash('Thank you for your review!', 'success')
        return redirect(url_for('customer_portal.reviews'))

    return render_template('customer_portal/submit_review.html',
        customer_name=session.get('portal_customer_name'),
        job_id=job_id,
        review_request=review_request
    )


# ============================================================================
# PROFILE
# ============================================================================

@customer_portal_bp.route('/profile')
@portal_login_required
def profile():
    """View and edit customer profile"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Get customer info from dashboard
    dashboard = manager.get_portal_dashboard(customer_id)

    return render_template('customer_portal/profile.html',
        customer_name=session.get('portal_customer_name'),
        customer=dashboard.get('customer', {})
    )


# ============================================================================
# ESTIMATE REQUESTS
# ============================================================================

@customer_portal_bp.route('/estimates')
@portal_login_required
def estimates():
    """View estimate requests"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # This would need a get_customer_estimates method
    # For now, return empty list

    return render_template('customer_portal/estimates.html',
        customer_name=session.get('portal_customer_name'),
        estimates=[]
    )


@customer_portal_bp.route('/estimates/request', methods=['GET', 'POST'])
@portal_login_required
def request_estimate():
    """Request a new estimate"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    if request.method == 'POST':
        vehicle_info = {
            'year': request.form.get('vehicle_year'),
            'make': request.form.get('vehicle_make'),
            'model': request.form.get('vehicle_model')
        }
        damage_description = request.form.get('damage_description', '')
        urgency = request.form.get('urgency', 'NORMAL')

        request_id = manager.request_estimate(
            customer_id=customer_id,
            vehicle_info=vehicle_info,
            damage_description=damage_description,
            urgency=urgency
        )

        flash('Your estimate request has been submitted!', 'success')
        return redirect(url_for('customer_portal.estimates'))

    return render_template('customer_portal/request_estimate.html',
        customer_name=session.get('portal_customer_name')
    )


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

@customer_portal_bp.route('/api/job-status/<int:job_id>')
@portal_login_required
def api_job_status(job_id):
    """API: Get job status"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    jobs = manager.get_job_status(customer_id, job_id=job_id)

    if not jobs:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(jobs[0])


@customer_portal_bp.route('/api/timeline/<int:job_id>')
@portal_login_required
def api_timeline(job_id):
    """API: Get job timeline"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    # Verify customer owns this job
    jobs = manager.get_job_status(customer_id, job_id=job_id)
    if not jobs:
        return jsonify({'error': 'Job not found'}), 404

    timeline = manager.get_status_timeline(job_id)

    return jsonify(timeline)


@customer_portal_bp.route('/api/referral-stats')
@portal_login_required
def api_referral_stats():
    """API: Get referral statistics"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    dashboard = manager.get_referral_dashboard(customer_id)

    return jsonify({
        'summary': dashboard['summary'],
        'earnings': dashboard['earnings']
    })


@customer_portal_bp.route('/api/unread-count')
@portal_login_required
def api_unread_count():
    """API: Get unread message count"""

    customer_id = session['portal_customer_id']
    manager = get_portal_manager()

    unread = manager.get_messages(customer_id, unread_only=True)

    return jsonify({'unread_count': len(unread)})


# ============================================================================
# NOTIFICATIONS
# ============================================================================

@customer_portal_bp.route('/notifications')
@portal_login_required
def notifications():
    """View all notifications"""

    customer_id = session['portal_customer_id']
    notification_manager = get_notification_manager()

    all_notifications = notification_manager.get_notifications(customer_id, limit=100)
    unread_count = notification_manager.get_unread_count(customer_id)
    preferences = notification_manager.get_customer_preferences(customer_id)

    return render_template('customer_portal/notifications.html',
        customer_name=session.get('portal_customer_name'),
        notifications=all_notifications,
        unread_count=unread_count,
        preferences=preferences
    )


@customer_portal_bp.route('/notifications/preferences', methods=['GET', 'POST'])
@portal_login_required
def notification_preferences():
    """View and update notification preferences"""

    customer_id = session['portal_customer_id']
    notification_manager = get_notification_manager()

    if request.method == 'POST':
        # Build preferences from form
        preferences = {
            'email_enabled': request.form.get('email_enabled') == 'on',
            'sms_enabled': request.form.get('sms_enabled') == 'on',
            'push_enabled': request.form.get('push_enabled') == 'on',
            'in_app_enabled': request.form.get('in_app_enabled') == 'on',
            'quiet_hours_start': request.form.get('quiet_hours_start') or None,
            'quiet_hours_end': request.form.get('quiet_hours_end') or None
        }

        # Get selected statuses
        notify_statuses = request.form.getlist('notify_statuses')
        if notify_statuses:
            preferences['notify_on_statuses'] = notify_statuses

        notification_manager.update_customer_preferences(customer_id, preferences)
        flash('Notification preferences updated successfully!', 'success')
        return redirect(url_for('customer_portal.notification_preferences'))

    # GET - show preferences form
    preferences = notification_manager.get_customer_preferences(customer_id)

    # All available statuses for selection
    all_statuses = [
        ('APPROVED', 'Insurance Approved'),
        ('SCHEDULED', 'Repair Scheduled'),
        ('DROPPED_OFF', 'Vehicle Received'),
        ('IN_PROGRESS', 'Repair Started'),
        ('TECH_COMPLETE', 'Repair Work Complete'),
        ('QC_COMPLETE', 'Quality Check Passed'),
        ('READY_FOR_PICKUP', 'Ready for Pickup'),
        ('COMPLETED', 'Job Completed'),
        ('WAITING_PARTS', 'Waiting for Parts'),
        ('PARTS_RECEIVED', 'Parts Arrived'),
        ('ESTIMATE_CREATED', 'Estimate Ready'),
        ('INVOICED', 'Invoice Ready')
    ]

    return render_template('customer_portal/notification_preferences.html',
        customer_name=session.get('portal_customer_name'),
        preferences=preferences,
        all_statuses=all_statuses
    )


# ============================================================================
# NOTIFICATION API ENDPOINTS
# ============================================================================

@customer_portal_bp.route('/api/notifications')
@portal_login_required
def api_notifications():
    """API: Get all notifications"""

    customer_id = session['portal_customer_id']
    notification_manager = get_notification_manager()

    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = min(int(request.args.get('limit', 50)), 100)

    notifications = notification_manager.get_notifications(
        customer_id,
        unread_only=unread_only,
        limit=limit
    )

    return jsonify({
        'notifications': notifications,
        'unread_count': notification_manager.get_unread_count(customer_id)
    })


@customer_portal_bp.route('/api/notifications/unread-count')
@portal_login_required
def api_notification_unread_count():
    """API: Get unread notification count"""

    customer_id = session['portal_customer_id']
    notification_manager = get_notification_manager()

    return jsonify({
        'unread_count': notification_manager.get_unread_count(customer_id)
    })


@customer_portal_bp.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@portal_login_required
def api_mark_notification_read(notif_id):
    """API: Mark notification as read"""

    notification_manager = get_notification_manager()
    notification_manager.mark_as_read(notif_id)

    return jsonify({'success': True})


@customer_portal_bp.route('/api/notifications/mark-all-read', methods=['POST'])
@portal_login_required
def api_mark_all_notifications_read():
    """API: Mark all notifications as read"""

    customer_id = session['portal_customer_id']
    notification_manager = get_notification_manager()

    notification_manager.mark_all_as_read(customer_id)

    return jsonify({'success': True})


@customer_portal_bp.route('/api/notifications/<int:notif_id>/dismiss', methods=['POST'])
@portal_login_required
def api_dismiss_notification(notif_id):
    """API: Dismiss a notification"""

    notification_manager = get_notification_manager()
    notification_manager.dismiss_notification(notif_id)

    return jsonify({'success': True})


@customer_portal_bp.route('/api/notifications/stream')
@portal_login_required
def notification_stream():
    """Server-Sent Events stream for real-time notifications"""

    customer_id = session['portal_customer_id']

    def generate():
        notification_manager = get_notification_manager()
        last_check = datetime.now()

        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': last_check.isoformat()})}\n\n"

        while True:
            try:
                # Check for new notifications since last check
                new_notifications = notification_manager.get_notifications_since(customer_id, last_check)

                for notif in new_notifications:
                    # Convert to JSON-serializable format
                    notif_data = {
                        'type': 'notification',
                        'id': notif['id'],
                        'notification_type': notif['notification_type'],
                        'title': notif['title'],
                        'message': notif['message'],
                        'priority': notif['priority'],
                        'job_id': notif.get('job_id'),
                        'job_number': notif.get('job_number'),
                        'created_at': notif['created_at']
                    }
                    yield f"data: {json.dumps(notif_data)}\n\n"

                last_check = datetime.now()

                # Send heartbeat every 30 seconds
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': last_check.isoformat()})}\n\n"

                # Wait before next check
                time.sleep(5)

            except GeneratorExit:
                # Client disconnected
                break
            except Exception as e:
                # Send error and continue
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                time.sleep(5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@customer_portal_bp.route('/api/notifications/preferences', methods=['GET', 'POST'])
@portal_login_required
def api_notification_preferences():
    """API: Get or update notification preferences"""

    customer_id = session['portal_customer_id']
    notification_manager = get_notification_manager()

    if request.method == 'POST':
        data = request.get_json() or {}

        preferences = {
            'email_enabled': data.get('email_enabled', True),
            'sms_enabled': data.get('sms_enabled', False),
            'push_enabled': data.get('push_enabled', False),
            'in_app_enabled': data.get('in_app_enabled', True),
            'quiet_hours_start': data.get('quiet_hours_start'),
            'quiet_hours_end': data.get('quiet_hours_end')
        }

        if 'notify_on_statuses' in data:
            preferences['notify_on_statuses'] = data['notify_on_statuses']

        notification_manager.update_customer_preferences(customer_id, preferences)

        return jsonify({'success': True})

    # GET
    preferences = notification_manager.get_customer_preferences(customer_id)
    return jsonify(preferences)
