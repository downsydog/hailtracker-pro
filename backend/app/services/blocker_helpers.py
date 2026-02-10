"""
Job Blocker Helpers (Stage 5O.1 - Centralized blocker logic, extended 5P)

Shared helpers for consistent blocker state computation across:
- /ops/overview
- /notifications (SLA escalations)
- Individual job queries
- Parts Control Tower (Stage 5P)

NO NEW MODELS - uses existing EstimateActivity with activity_type:
- job_blocked
- job_blocker_updated
- job_blocker_cleared

Parts Status Flow (Stage 5P):
  needed -> approved_to_order -> ordered -> shipped -> received -> installed
  (exception can be set at any point)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

# Valid parts status values (Stage 5P)
PARTS_STATUS_VALUES = [
    'needed',           # Tech flagged, waiting for approval
    'approved_to_order', # Office approved, pending order
    'ordered',          # PO issued, waiting on delivery
    'shipped',          # Vendor shipped, in transit
    'received',         # Parts arrived at shop
    'installed',        # Parts installed, blocker can be cleared
    'exception',        # Issue with parts (wrong part, damaged, etc.)
]


def build_parts_info(parts: dict | None, issue_type: str = 'waiting_on_parts') -> dict | None:
    """
    Build normalized parts info dict from raw metadata.

    Stage 5P: Extended to include parts_status, approved fields.

    Returns:
        {
            'ordered': bool,
            'vendor': str | None,
            'po_number': str | None,
            'eta': str | None,
            'parts_status': str | None,  # Stage 5P
            'approved_to_order': bool,    # Stage 5P
            'approved_amount': float | None,  # Stage 5P
            'parts_notes': str | None,    # Stage 5P
        } or None
    """
    if not parts and issue_type != 'waiting_on_parts':
        return None

    # Default structure for waiting_on_parts
    return {
        'ordered': parts.get('ordered', False) if parts else False,
        'vendor': parts.get('vendor') if parts else None,
        'po_number': parts.get('po_number') if parts else None,
        'eta': parts.get('eta') if parts else None,
        # Stage 5P fields
        'parts_status': parts.get('parts_status', 'needed') if parts else 'needed',
        'approved_to_order': parts.get('approved_to_order', False) if parts else False,
        'approved_amount': parts.get('approved_amount') if parts else None,
        'parts_notes': parts.get('parts_notes') if parts else None,
    }


def normalize_eta(eta_input: str | None) -> str | None:
    """
    Normalize ETA to ISO-8601 datetime string.

    Accepts:
        - ISO datetime: "2024-03-15T14:30:00" -> stored as-is
        - Date only: "2024-03-15" -> stored as "2024-03-15T17:00:00" (5pm UTC)
        - None/empty -> None

    Returns normalized ISO datetime string or None.
    """
    if not eta_input or not eta_input.strip():
        return None

    eta_str = eta_input.strip()

    # Already a datetime
    if 'T' in eta_str:
        # Validate format
        try:
            datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
            return eta_str
        except ValueError:
            return None

    # Date only - add 17:00 UTC (5pm)
    try:
        datetime.strptime(eta_str, '%Y-%m-%d')
        return f"{eta_str}T17:00:00"
    except ValueError:
        return None


def get_current_job_blocker(job_id: int, estimate_id: int | None, tenant_id: int) -> Dict[str, Any]:
    """
    Get the current blocker state for a job.

    Centralized helper to ensure identical logic across:
    - /ops/overview
    - /notifications escalations
    - Individual job queries

    Returns:
        {
            'is_blocked': bool,
            'blocker_info': {
                'issue_type': str,
                'notes': str,
                'flagged_at': str,
                'parts': {...} | None,
            } | None,
            'blocked_at': datetime | None,
            'updated_at': datetime | None,
        }
    """
    if not estimate_id:
        return {'is_blocked': False, 'blocker_info': None, 'blocked_at': None, 'updated_at': None}

    from app.models.tenant.estimate_activity import EstimateActivity

    now = datetime.utcnow()
    blocker_threshold = now - timedelta(days=7)

    # Get most recent blocker/update activity for this job
    recent_blockers = EstimateActivity.query.filter(
        EstimateActivity.estimate_id == estimate_id,
        EstimateActivity.activity_type.in_(['job_blocked', 'job_blocker_updated']),
        EstimateActivity.created_at > blocker_threshold
    ).order_by(EstimateActivity.created_at.desc()).all()

    # Get most recent cleared activity
    cleared = EstimateActivity.query.filter(
        EstimateActivity.estimate_id == estimate_id,
        EstimateActivity.activity_type == 'job_blocker_cleared',
        EstimateActivity.created_at > blocker_threshold
    ).order_by(EstimateActivity.created_at.desc()).first()

    cleared_at = cleared.created_at if cleared and cleared.activity_data and cleared.activity_data.get('job_id') == job_id else None

    # Find the most recent blocker for this job that's after the last clear
    for blocker in recent_blockers:
        if not blocker.activity_data or blocker.activity_data.get('job_id') != job_id:
            continue

        # Skip if cleared after this blocker
        if cleared_at and blocker.created_at < cleared_at:
            continue

        # Found active blocker
        parts = blocker.activity_data.get('parts')
        issue_type = blocker.activity_data.get('issue_type', 'other')
        return {
            'is_blocked': True,
            'blocker_info': {
                'issue_type': issue_type,
                'notes': blocker.activity_data.get('notes', ''),
                'flagged_at': blocker.activity_data.get('flagged_at') or blocker.activity_data.get('updated_at'),
                'parts': build_parts_info(parts, issue_type),
            },
            'blocked_at': blocker.created_at,
            'updated_at': blocker.created_at,
        }

    return {'is_blocked': False, 'blocker_info': None, 'blocked_at': None, 'updated_at': None}


def get_bulk_job_blockers(job_ids_with_estimates: List[Tuple[int, Optional[int]]], tenant_id: int) -> Dict[int, Dict[str, Any]]:
    """
    Bulk fetch blocker info for multiple jobs.

    Args:
        job_ids_with_estimates: List of (job_id, estimate_id) tuples
        tenant_id: Tenant ID for safety

    Returns:
        Dict mapping job_id -> blocker_info dict with keys:
        - issue_type: str
        - notes: str
        - flagged_at: str (ISO timestamp)
        - parts: dict | None (with ordered, vendor, po_number, eta)
    """
    from app.models.tenant.estimate_activity import EstimateActivity

    if not job_ids_with_estimates:
        return {}

    estimate_ids = [eid for _, eid in job_ids_with_estimates if eid]
    if not estimate_ids:
        return {}

    now = datetime.utcnow()
    blocker_threshold = now - timedelta(days=7)

    # Get all blocker/update activities
    recent_blockers = EstimateActivity.query.filter(
        EstimateActivity.estimate_id.in_(estimate_ids),
        EstimateActivity.activity_type.in_(['job_blocked', 'job_blocker_updated']),
        EstimateActivity.created_at > blocker_threshold
    ).order_by(EstimateActivity.created_at.desc()).all()

    # Get all cleared activities
    cleared_blockers = EstimateActivity.query.filter(
        EstimateActivity.estimate_id.in_(estimate_ids),
        EstimateActivity.activity_type == 'job_blocker_cleared',
        EstimateActivity.created_at > blocker_threshold
    ).order_by(EstimateActivity.created_at.desc()).all()

    # Map job_id -> most recent cleared timestamp
    cleared_timestamps = {}
    for cleared in cleared_blockers:
        if cleared.activity_data and cleared.activity_data.get('job_id'):
            jid = cleared.activity_data['job_id']
            if jid not in cleared_timestamps:
                cleared_timestamps[jid] = cleared.created_at

    # Build result map
    result = {}
    for blocker in recent_blockers:
        if not blocker.activity_data or not blocker.activity_data.get('job_id'):
            continue

        job_id = blocker.activity_data['job_id']

        # Skip if already processed or cleared after this blocker
        if job_id in result:
            continue
        cleared_at = cleared_timestamps.get(job_id)
        if cleared_at and blocker.created_at < cleared_at:
            continue

        parts = blocker.activity_data.get('parts')
        issue_type = blocker.activity_data.get('issue_type', 'other')
        result[job_id] = {
            'issue_type': issue_type,
            'notes': blocker.activity_data.get('notes', ''),
            'flagged_at': blocker.activity_data.get('flagged_at') or blocker.activity_data.get('updated_at'),
            'parts': build_parts_info(parts, issue_type),
        }

    return result


def get_bulk_job_blockers_with_timestamps(
    job_ids_with_estimates: List[Tuple[int, Optional[int]]],
    tenant_id: int
) -> Dict[int, Dict[str, Any]]:
    """
    Bulk fetch blocker info with raw timestamps for SLA calculations.

    Same as get_bulk_job_blockers but includes 'blocked_at' datetime
    for calculating days_blocked in SLA alerts.

    Returns:
        Dict mapping job_id -> blocker_info dict with additional:
        - blocked_at: datetime (for days calculation)
    """
    from app.models.tenant.estimate_activity import EstimateActivity

    if not job_ids_with_estimates:
        return {}

    estimate_ids = [eid for _, eid in job_ids_with_estimates if eid]
    if not estimate_ids:
        return {}

    now = datetime.utcnow()
    blocker_threshold = now - timedelta(days=7)

    # Get all blocker/update activities
    recent_blockers = EstimateActivity.query.filter(
        EstimateActivity.estimate_id.in_(estimate_ids),
        EstimateActivity.activity_type.in_(['job_blocked', 'job_blocker_updated']),
        EstimateActivity.created_at > blocker_threshold
    ).order_by(EstimateActivity.created_at.desc()).all()

    # Get all cleared activities
    cleared_blockers = EstimateActivity.query.filter(
        EstimateActivity.estimate_id.in_(estimate_ids),
        EstimateActivity.activity_type == 'job_blocker_cleared',
        EstimateActivity.created_at > blocker_threshold
    ).order_by(EstimateActivity.created_at.desc()).all()

    # Map job_id -> most recent cleared timestamp
    cleared_timestamps = {}
    for cleared in cleared_blockers:
        if cleared.activity_data and cleared.activity_data.get('job_id'):
            jid = cleared.activity_data['job_id']
            if jid not in cleared_timestamps:
                cleared_timestamps[jid] = cleared.created_at

    # Build result map with timestamps
    result = {}
    for blocker in recent_blockers:
        if not blocker.activity_data or not blocker.activity_data.get('job_id'):
            continue

        job_id = blocker.activity_data['job_id']

        # Skip if already processed or cleared after this blocker
        if job_id in result:
            continue
        cleared_at = cleared_timestamps.get(job_id)
        if cleared_at and blocker.created_at < cleared_at:
            continue

        parts = blocker.activity_data.get('parts')
        issue_type = blocker.activity_data.get('issue_type', 'other')
        result[job_id] = {
            'issue_type': issue_type,
            'notes': blocker.activity_data.get('notes', ''),
            'flagged_at': blocker.activity_data.get('flagged_at') or blocker.activity_data.get('updated_at'),
            'blocked_at': blocker.created_at,  # Raw datetime for SLA calculations
            'parts': build_parts_info(parts, issue_type),
        }

    return result
