"""
Admin Storm Management Endpoints
================================
Endpoints for managing storm processing (owner only).
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from backend.app.api.middleware import admin_required
from backend.app.models.master.storm import Storm
from backend.app.models.master.swath import Swath
from backend.app.extensions import db
from backend.app.tasks.storm_tasks import process_storm, reprocess_storm
from celery.result import AsyncResult

admin_storms_bp = Blueprint('admin_storms', __name__)


@admin_storms_bp.route('/storms', methods=['GET'])
@admin_required
def list_all_storms():
    """
    List all storms with their status.

    Query params:
        status: Filter by status (pending, processing, ready, failed, expired)
        limit: Max results (default 50)

    Returns:
        200: List of storms
    """
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)

    query = Storm.query

    if status:
        query = query.filter(Storm.status == status)

    storms = query.order_by(Storm.event_date.desc()).limit(limit).all()

    result = []
    for storm in storms:
        swath_count = Swath.query.filter_by(storm_id=storm.id).count()
        result.append({
            'id': storm.id,
            'noaa_id': storm.noaa_id,
            'event_date': storm.event_date.isoformat(),
            'state': storm.state,
            'status': storm.status,
            'business_count': storm.business_count,
            'swath_count': swath_count,
            'processed_at': storm.processed_at.isoformat() if storm.processed_at else None,
            'expires_at': storm.expires_at.isoformat() if storm.expires_at else None
        })

    return jsonify({'storms': result})


@admin_storms_bp.route('/storms/<int:storm_id>/process', methods=['POST'])
@admin_required
def trigger_process_storm(storm_id):
    """
    Trigger storm processing.

    Args:
        storm_id: Storm ID to process

    Request Body:
        force: boolean - Force reprocess even if ready

    Returns:
        200: Task started
        400: Already processing or already ready
        404: Storm not found
    """
    storm = Storm.query.get(storm_id)
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404

    if storm.status == 'processing':
        return jsonify({'error': 'Storm is already being processed'}), 400

    data = request.get_json() or {}
    if storm.status == 'ready' and not data.get('force'):
        return jsonify({
            'error': 'Storm already processed. Use force=true to reprocess'
        }), 400

    # Start background task
    task = process_storm.delay(storm_id)

    return jsonify({
        'message': 'Storm processing started',
        'task_id': task.id,
        'storm_id': storm_id
    })


@admin_storms_bp.route('/storms/<int:storm_id>/reprocess', methods=['POST'])
@admin_required
def trigger_reprocess_storm(storm_id):
    """
    Reprocess a storm (clears existing data and runs discovery again).

    Args:
        storm_id: Storm ID to reprocess

    Returns:
        200: Task started
        404: Storm not found
    """
    storm = Storm.query.get(storm_id)
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404

    # Start reprocess task
    task = reprocess_storm.delay(storm_id)

    return jsonify({
        'message': 'Storm reprocessing started',
        'task_id': task.id,
        'storm_id': storm_id
    })


@admin_storms_bp.route('/tasks/<task_id>', methods=['GET'])
@admin_required
def get_task_status(task_id):
    """
    Get status of a background task.

    Args:
        task_id: Celery task ID

    Returns:
        200: Task status and result if ready
    """
    result = AsyncResult(task_id)

    response = {
        'task_id': task_id,
        'status': result.status,
        'ready': result.ready()
    }

    if result.ready():
        if result.successful():
            response['result'] = result.result
        else:
            response['error'] = str(result.result)
    elif result.status == 'PROGRESS':
        response['progress'] = result.info

    return jsonify(response)


@admin_storms_bp.route('/storms/pending', methods=['GET'])
@admin_required
def get_pending_storms():
    """
    Get storms that need processing.

    Returns:
        200: List of pending/failed/expired storms
    """
    storms = Storm.query.filter(
        Storm.status.in_(['pending', 'failed', 'expired'])
    ).order_by(Storm.event_date.desc()).limit(100).all()

    result = []
    for storm in storms:
        swath_count = Swath.query.filter_by(storm_id=storm.id).count()
        result.append({
            'id': storm.id,
            'noaa_id': storm.noaa_id,
            'event_date': storm.event_date.isoformat(),
            'state': storm.state,
            'status': storm.status,
            'swath_count': swath_count
        })

    return jsonify({'storms': result})


@admin_storms_bp.route('/storms/process-batch', methods=['POST'])
@admin_required
def process_batch():
    """
    Process multiple storms at once.

    Request Body:
    {
        "storm_ids": [1, 2, 3]
    }

    Returns:
        200: List of started tasks
        400: No storm_ids provided
    """
    data = request.get_json()
    storm_ids = data.get('storm_ids', [])

    if not storm_ids:
        return jsonify({'error': 'storm_ids required'}), 400

    tasks = []
    for storm_id in storm_ids:
        storm = Storm.query.get(storm_id)
        if storm and storm.status not in ['processing', 'ready']:
            task = process_storm.delay(storm_id)
            tasks.append({
                'storm_id': storm_id,
                'task_id': task.id
            })

    return jsonify({
        'message': f'Started processing {len(tasks)} storms',
        'tasks': tasks
    })


@admin_storms_bp.route('/storms/stats', methods=['GET'])
@admin_required
def get_storm_stats():
    """
    Get storm processing statistics.

    Returns:
        200: Storm counts by status
    """
    stats = {}
    for status in ['pending', 'processing', 'ready', 'failed', 'expired']:
        stats[status] = Storm.query.filter(Storm.status == status).count()

    stats['total'] = sum(stats.values())

    return jsonify({'stats': stats})
