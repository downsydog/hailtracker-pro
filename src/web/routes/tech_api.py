"""
Tech App API - endpoints for technician mobile app.

All routes require tech role authentication.
Provides:
- Dashboard and stats
- Job management (view, start, update, complete)
- Photo upload
- Time tracking
- Walk-up lead capture (gas station mode)
"""

import os
from datetime import datetime, date
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename

from src.core.auth.decorators import login_required, require_role
from src.crm.models.database import Database

tech_api_bp = Blueprint('tech_api', __name__, url_prefix='/api/tech')

# Allowed photo extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'heic', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    """Get database connection"""
    db_path = current_app.config.get('CRM_DATABASE', 'data/hailtracker_crm.db')
    return Database(db_path)


def get_tech_manager():
    """Get TechManager instance"""
    from src.crm.managers.tech_manager import TechManager
    return TechManager(get_db())


def get_time_tracking_manager():
    """Get TimeTrackingManager instance"""
    from src.crm.managers.time_tracking_manager import TimeTrackingManager
    return TimeTrackingManager(get_db())


def get_tech_id_for_user(user_id: int) -> int:
    """
    Get technician record ID for a user.
    Links the user account to the technician record.
    """
    db = get_db()

    # First try by user_id column (if technicians table has it)
    try:
        results = db.execute("""
            SELECT id FROM technicians
            WHERE user_id = ? AND deleted_at IS NULL AND status = 'ACTIVE'
        """, (user_id,))
        if results:
            return results[0]['id']
    except:
        pass

    # Fallback: Look up by email
    user = db.execute("SELECT email FROM users_new WHERE id = ?", (user_id,))
    if user:
        email = user[0]['email']
        results = db.execute("""
            SELECT id FROM technicians
            WHERE email = ? AND deleted_at IS NULL AND status = 'ACTIVE'
        """, (email,))
        if results:
            return results[0]['id']

    return None


# ============================================================================
# DASHBOARD & STATS
# ============================================================================

@tech_api_bp.route('/dashboard')
@login_required
@require_role('tech', 'admin', 'owner')
def dashboard():
    """Get tech dashboard data. Admin/owner sees aggregated data for all techs."""
    user_role = g.current_user.get('role', '')
    tech_id = get_tech_id_for_user(g.current_user['id'])

    # If admin/owner without tech record, show aggregated dashboard
    if not tech_id and user_role in ('admin', 'owner'):
        db = get_db()
        # Get aggregated stats for all techs
        today = date.today().isoformat()

        # Count jobs by status
        jobs_today = db.execute("""
            SELECT COUNT(*) as count FROM jobs
            WHERE DATE(scheduled_drop_off) = ? AND status IN ('SCHEDULED', 'IN_PROGRESS')
        """, (today,))

        jobs_in_progress = db.execute("""
            SELECT COUNT(*) as count FROM jobs WHERE status = 'IN_PROGRESS'
        """)

        jobs_completed_today = db.execute("""
            SELECT COUNT(*) as count FROM jobs
            WHERE DATE(completed_at) = ? AND status = 'COMPLETED'
        """, (today,))

        # Get all active techs
        techs = db.execute("""
            SELECT id, first_name || ' ' || last_name as name, status FROM technicians
            WHERE status = 'ACTIVE' AND deleted_at IS NULL
        """)

        return jsonify({
            'success': True,
            'is_admin_view': True,
            'jobs_today': jobs_today[0]['count'] if jobs_today else 0,
            'jobs_in_progress': jobs_in_progress[0]['count'] if jobs_in_progress else 0,
            'jobs_completed_today': jobs_completed_today[0]['count'] if jobs_completed_today else 0,
            'active_techs': len(techs) if techs else 0,
            'technicians': techs or [],
            'time_status': {'clocked_in': False},
            'today_hours': {'total_hours': 0}
        })

    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    tech_manager = get_tech_manager()
    data = tech_manager.get_tech_dashboard(tech_id)

    if not data:
        return jsonify({'success': False, 'error': 'Failed to load dashboard'}), 500

    # Add time tracking status
    time_manager = get_time_tracking_manager()
    data['time_status'] = time_manager.get_current_status(tech_id)
    data['today_hours'] = time_manager.get_today(tech_id)

    return jsonify({'success': True, **data})


@tech_api_bp.route('/stats')
@login_required
@require_role('tech', 'admin', 'owner')
def stats():
    """Get tech performance stats. Admin/owner sees aggregated stats."""
    user_role = g.current_user.get('role', '')
    tech_id = get_tech_id_for_user(g.current_user['id'])

    period = request.args.get('period', 'week')
    period_days = {'week': 7, 'month': 30, 'quarter': 90, 'year': 365}.get(period, 30)

    # Admin/owner without tech record sees all tech stats
    if not tech_id and user_role in ('admin', 'owner'):
        db = get_db()
        # Aggregated stats for all techs
        stats = db.execute(f"""
            SELECT
                COUNT(*) as jobs_completed,
                SUM(total_actual) as revenue,
                AVG(julianday(completed_at) - julianday(created_at)) as avg_completion_days
            FROM jobs
            WHERE status = 'COMPLETED'
            AND completed_at >= date('now', '-{period_days} days')
        """)
        return jsonify({
            'success': True,
            'is_admin_view': True,
            'jobs_completed': stats[0]['jobs_completed'] if stats else 0,
            'revenue': stats[0]['revenue'] or 0 if stats else 0,
            'avg_completion_days': round(stats[0]['avg_completion_days'] or 0, 1) if stats else 0
        })

    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    tech_manager = get_tech_manager()
    data = tech_manager.get_tech_stats(tech_id, period_days)

    return jsonify({'success': True, **data})


# ============================================================================
# JOBS
# ============================================================================

@tech_api_bp.route('/jobs')
@login_required
@require_role('tech', 'admin', 'owner')
def get_jobs():
    """Get tech's jobs - current, upcoming, or completed. Admin sees all."""
    user_role = g.current_user.get('role', '')
    tech_id = get_tech_id_for_user(g.current_user['id'])

    filter_type = request.args.get('filter', 'CURRENT').upper()

    # Admin/owner without tech record sees all jobs
    if not tech_id and user_role in ('admin', 'owner'):
        db = get_db()
        if filter_type == 'CURRENT':
            jobs = db.execute("""
                SELECT j.*, t.first_name || ' ' || t.last_name as tech_name,
                       c.first_name || ' ' || c.last_name as customer_name
                FROM jobs j
                LEFT JOIN technicians t ON j.assigned_tech_id = t.id
                LEFT JOIN customers c ON j.customer_id = c.id
                WHERE j.status IN ('SCHEDULED', 'IN_PROGRESS', 'CHECKED_IN')
                AND j.deleted_at IS NULL
                ORDER BY j.scheduled_drop_off
                LIMIT 50
            """)
        elif filter_type == 'COMPLETED':
            jobs = db.execute("""
                SELECT j.*, t.first_name || ' ' || t.last_name as tech_name,
                       c.first_name || ' ' || c.last_name as customer_name
                FROM jobs j
                LEFT JOIN technicians t ON j.assigned_tech_id = t.id
                LEFT JOIN customers c ON j.customer_id = c.id
                WHERE j.status = 'COMPLETED' AND j.deleted_at IS NULL
                ORDER BY j.completed_at DESC
                LIMIT 50
            """)
        else:
            jobs = db.execute("""
                SELECT j.*, t.first_name || ' ' || t.last_name as tech_name,
                       c.first_name || ' ' || c.last_name as customer_name
                FROM jobs j
                LEFT JOIN technicians t ON j.assigned_tech_id = t.id
                LEFT JOIN customers c ON j.customer_id = c.id
                WHERE j.deleted_at IS NULL
                ORDER BY j.created_at DESC
                LIMIT 50
            """)
        return jsonify({'success': True, 'is_admin_view': True, 'jobs': jobs or [], 'count': len(jobs or [])})

    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    tech_manager = get_tech_manager()
    jobs = tech_manager.get_tech_jobs(tech_id, filter_type if filter_type != 'ALL' else None)

    return jsonify({'success': True, 'jobs': jobs, 'count': len(jobs)})


@tech_api_bp.route('/jobs/<int:job_id>')
@login_required
@require_role('tech', 'admin', 'owner')
def get_job_detail(job_id):
    """Get detailed job info"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    tech_manager = get_tech_manager()
    job = tech_manager.get_job_details(job_id, tech_id)

    if not job:
        return jsonify({'success': False, 'error': 'Job not found or not assigned to you'}), 404

    # Get photos for this job
    photos = get_job_photos_internal(job_id)
    job['photos'] = photos

    return jsonify({'success': True, 'job': job})


@tech_api_bp.route('/jobs/<int:job_id>/start', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def start_job(job_id):
    """Start working on a job (ASSIGNED → IN_PROGRESS)"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    tech_manager = get_tech_manager()

    try:
        result = tech_manager.start_job(job_id, tech_id)
        return jsonify({'success': True, 'message': 'Job started'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@tech_api_bp.route('/jobs/<int:job_id>/progress', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def update_progress(job_id):
    """Update job progress"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json or {}
    notes = data.get('notes', '')
    hours_remaining = data.get('hours_remaining')

    if not notes:
        return jsonify({'success': False, 'error': 'Progress notes required'}), 400

    tech_manager = get_tech_manager()

    try:
        result = tech_manager.update_progress(
            job_id, tech_id,
            progress_note=notes,
            hours_remaining=float(hours_remaining) if hours_remaining else None
        )
        return jsonify({'success': True, 'message': 'Progress updated'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@tech_api_bp.route('/jobs/<int:job_id>/complete', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def complete_job(job_id):
    """Mark job as complete"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json or {}
    notes = data.get('notes', '')

    tech_manager = get_tech_manager()

    try:
        result = tech_manager.mark_complete(job_id, tech_id, completion_notes=notes)
        return jsonify({'success': True, 'message': 'Job marked complete'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@tech_api_bp.route('/jobs/<int:job_id>/pause', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def pause_job(job_id):
    """Pause a job (for lunch, end of day, etc.)"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json or {}
    reason = data.get('reason', 'Paused by tech')

    tech_manager = get_tech_manager()

    try:
        # Update progress with pause note
        tech_manager.update_progress(
            job_id, tech_id,
            progress_note=f"[PAUSED] {reason}"
        )
        return jsonify({'success': True, 'message': 'Job paused'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# PHOTOS
# ============================================================================

def get_job_photos_internal(job_id: int) -> list:
    """Get all photos for a job"""
    db = get_db()
    photos = db.execute("""
        SELECT * FROM documents
        WHERE job_id = ? AND document_type = 'photo' AND deleted_at IS NULL
        ORDER BY created_at DESC
    """, (job_id,))
    return photos


@tech_api_bp.route('/jobs/<int:job_id>/photos')
@login_required
@require_role('tech', 'admin', 'owner')
def get_job_photos(job_id):
    """Get all photos for a job"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    # Verify tech has access to this job
    tech_manager = get_tech_manager()
    job = tech_manager.get_job_details(job_id, tech_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found or not assigned to you'}), 404

    photos = get_job_photos_internal(job_id)

    # Group by photo type
    grouped = {
        'before': [p for p in photos if p.get('category') == 'before'],
        'progress': [p for p in photos if p.get('category') == 'progress'],
        'after': [p for p in photos if p.get('category') == 'after'],
        'detail': [p for p in photos if p.get('category') == 'detail'],
        'other': [p for p in photos if p.get('category') not in ['before', 'progress', 'after', 'detail']]
    }

    return jsonify({'success': True, 'photos': photos, 'grouped': grouped})


@tech_api_bp.route('/jobs/<int:job_id>/photos', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def upload_photo(job_id):
    """Upload a photo for a job"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    # Verify tech has access to this job
    tech_manager = get_tech_manager()
    job = tech_manager.get_job_details(job_id, tech_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found or not assigned to you'}), 404

    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'No photo provided'}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400

    photo_type = request.form.get('type', 'progress')  # before, progress, after, detail
    panel = request.form.get('panel')
    notes = request.form.get('notes')

    # Create upload directory
    upload_dir = os.path.join('uploads', str(g.organization_id), 'jobs', str(job_id))
    os.makedirs(upload_dir, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{photo_type}_{timestamp}.{ext}"
    filepath = os.path.join(upload_dir, filename)

    # Save file
    file.save(filepath)

    # Create database record
    db = get_db()
    photo_id = db.insert('documents', {
        'organization_id': g.organization_id,
        'job_id': job_id,
        'document_type': 'photo',
        'category': photo_type,
        'filename': filename,
        'file_path': filepath,
        'mime_type': f'image/{ext}',
        'description': notes,
        'metadata': f'{{"panel": "{panel}", "uploaded_by_tech": {tech_id}}}' if panel else f'{{"uploaded_by_tech": {tech_id}}}',
        'uploaded_by': g.current_user['id']
    })

    return jsonify({
        'success': True,
        'photo_id': photo_id,
        'photo_url': f'/uploads/{g.organization_id}/jobs/{job_id}/{filename}',
        'message': 'Photo uploaded'
    })


# ============================================================================
# SCHEDULE
# ============================================================================

@tech_api_bp.route('/schedule')
@login_required
@require_role('tech', 'admin', 'owner')
def get_schedule():
    """Get tech's schedule for the week. Admin sees all scheduled jobs."""
    user_role = g.current_user.get('role', '')
    tech_id = get_tech_id_for_user(g.current_user['id'])

    days = request.args.get('days', 7, type=int)

    # Admin/owner without tech record sees all scheduled jobs
    if not tech_id and user_role in ('admin', 'owner'):
        db = get_db()
        schedule = db.execute(f"""
            SELECT j.*, t.first_name || ' ' || t.last_name as tech_name,
                   c.first_name || ' ' || c.last_name as customer_name,
                   v.year as vehicle_year, v.make as vehicle_make, v.model as vehicle_model
            FROM jobs j
            LEFT JOIN technicians t ON j.assigned_tech_id = t.id
            LEFT JOIN customers c ON j.customer_id = c.id
            LEFT JOIN vehicles v ON j.vehicle_id = v.id
            WHERE j.status IN ('SCHEDULED', 'IN_PROGRESS', 'CHECKED_IN')
            AND j.deleted_at IS NULL
            AND DATE(j.scheduled_drop_off) BETWEEN DATE('now') AND DATE('now', '+{days} days')
            ORDER BY j.scheduled_drop_off
        """)
        return jsonify({'success': True, 'is_admin_view': True, 'schedule': schedule or []})

    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    tech_manager = get_tech_manager()
    schedule = tech_manager.get_schedule(tech_id, days_ahead=days)

    return jsonify({'success': True, 'schedule': schedule})


# ============================================================================
# TIME TRACKING
# ============================================================================

@tech_api_bp.route('/time/status')
@login_required
@require_role('tech', 'admin', 'owner')
def time_status():
    """Get current time tracking status"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    time_manager = get_time_tracking_manager()
    status = time_manager.get_current_status(tech_id)
    today = time_manager.get_today(tech_id)

    return jsonify({
        'success': True,
        'status': status,
        'today': today
    })


@tech_api_bp.route('/time/clock-in', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def clock_in():
    """Clock in for the day"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json or {}

    time_manager = get_time_tracking_manager()
    result = time_manager.clock_in(
        tech_id,
        location=data.get('location'),
        notes=data.get('notes')
    )

    return jsonify(result)


@tech_api_bp.route('/time/clock-out', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def clock_out():
    """Clock out for the day"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json or {}

    time_manager = get_time_tracking_manager()
    result = time_manager.clock_out(
        tech_id,
        location=data.get('location'),
        notes=data.get('notes')
    )

    return jsonify(result)


@tech_api_bp.route('/time/break/start', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def start_break():
    """Start a break"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    time_manager = get_time_tracking_manager()
    result = time_manager.start_break(tech_id)

    return jsonify(result)


@tech_api_bp.route('/time/break/end', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def end_break():
    """End a break"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    time_manager = get_time_tracking_manager()
    result = time_manager.end_break(tech_id)

    return jsonify(result)


@tech_api_bp.route('/time/log', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def log_time():
    """Log time to a specific job"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json
    if not data or 'job_id' not in data or 'hours' not in data:
        return jsonify({'success': False, 'error': 'job_id and hours required'}), 400

    time_manager = get_time_tracking_manager()
    result = time_manager.log_job_time(
        tech_id,
        job_id=data['job_id'],
        hours=float(data['hours']),
        description=data.get('description')
    )

    return jsonify(result)


@tech_api_bp.route('/time/today')
@login_required
@require_role('tech', 'admin', 'owner')
def today_time():
    """Get today's time entries"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    time_manager = get_time_tracking_manager()
    today = time_manager.get_today(tech_id)

    return jsonify({'success': True, **today})


@tech_api_bp.route('/time/week')
@login_required
@require_role('tech', 'admin', 'owner')
def week_time():
    """Get this week's time summary"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    time_manager = get_time_tracking_manager()
    week = time_manager.get_week_summary(tech_id)

    return jsonify({'success': True, **week})


# ============================================================================
# DAILY UPDATE
# ============================================================================

@tech_api_bp.route('/daily-update', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def submit_daily_update():
    """Submit end-of-day update"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json or {}

    db = get_db()

    # Create daily update record
    update_id = db.insert('tech_daily_updates', {
        'organization_id': g.organization_id,
        'technician_id': tech_id,
        'update_date': date.today().isoformat(),
        'jobs_summary': str(data.get('jobs_summary', [])),
        'total_hours': data.get('total_hours'),
        'notes': data.get('notes'),
        'issues': data.get('issues'),
        'submitted_at': datetime.now().isoformat()
    })

    # Mark time tracking as complete for today
    time_manager = get_time_tracking_manager()
    time_manager.mark_day_complete(tech_id)

    return jsonify({
        'success': True,
        'update_id': update_id,
        'message': 'Daily update submitted'
    })


# ============================================================================
# GAS STATION MODE (Walk-up Lead Capture)
# ============================================================================

@tech_api_bp.route('/leads', methods=['POST'])
@login_required
@require_role('tech', 'admin', 'owner')
def create_lead():
    """Create a walk-up lead (gas station mode)"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    data = request.json or {}

    # Validate required fields
    if not data.get('first_name') or not data.get('phone'):
        return jsonify({'success': False, 'error': 'First name and phone required'}), 400

    db = get_db()

    # Create lead
    lead_id = db.insert('leads', {
        'organization_id': g.organization_id,
        'source': 'TECH_WALKIN',
        'source_detail': f'Created by tech #{tech_id}',
        'first_name': data.get('first_name'),
        'last_name': data.get('last_name', ''),
        'phone': data.get('phone'),
        'email': data.get('email'),
        'address': data.get('address'),
        'city': data.get('city'),
        'state': data.get('state'),
        'zip_code': data.get('zip_code'),
        'vehicle_year': data.get('vehicle_year'),
        'vehicle_make': data.get('vehicle_make'),
        'vehicle_model': data.get('vehicle_model'),
        'vehicle_color': data.get('vehicle_color'),
        'vehicle_vin': data.get('vehicle_vin'),
        'notes': data.get('notes'),
        'status': 'NEW',
        'assigned_to': g.current_user['id'],
        'created_by': g.current_user['id']
    })

    result = {
        'success': True,
        'lead_id': lead_id,
        'message': 'Lead created'
    }

    # Create scheduling link if requested
    if data.get('create_scheduling_link', True):
        try:
            from src.crm.managers.scheduling_manager import SchedulingManager
            scheduling_manager = SchedulingManager(db)
            token = scheduling_manager.create_scheduling_token(
                organization_id=g.organization_id,
                lead_id=lead_id,
                expires_days=14,
                max_uses=1,
                created_by=g.current_user['id']
            )
            result['scheduling_link'] = f"/schedule/{token}"
            result['scheduling_token'] = token
        except Exception as e:
            # Don't fail the whole request if scheduling link fails
            result['scheduling_link_error'] = str(e)

    return jsonify(result)


@tech_api_bp.route('/leads')
@login_required
@require_role('tech', 'admin', 'owner')
def get_my_leads():
    """Get leads created by this tech"""
    tech_id = get_tech_id_for_user(g.current_user['id'])
    if not tech_id:
        return jsonify({'success': False, 'error': 'No technician record found'}), 404

    db = get_db()

    # Get leads created by this user
    leads = db.execute("""
        SELECT * FROM leads
        WHERE organization_id = ? AND created_by = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (g.organization_id, g.current_user['id']))

    return jsonify({'success': True, 'leads': leads, 'count': len(leads)})
