"""
Auto-Nudges Tasks
=================
Celery task for sending scheduled SLA digest emails.

Runs every 15 minutes and checks which tenants should receive digests
based on their configured digest_time_local + timezone.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pytz

from app.celery_app import celery_app
from app.extensions import db


@celery_app.task
def process_auto_nudges():
    """
    Process auto-nudges for all tenants.

    Runs every 15 minutes via Celery Beat.
    - Checks each tenant's auto-nudges config
    - Determines if digest should be sent based on schedule
    - Gathers escalation items and applies thresholds
    - Sends digest email to configured recipients
    - Logs to EstimateActivity for dedupe/anti-spam

    Returns:
        Dictionary with processing stats
    """
    from app import create_app
    app = create_app()

    with app.app_context():
        from app.models.master.tenant import Tenant

        now_utc = datetime.utcnow()
        stats = {
            'tenants_checked': 0,
            'digests_sent': 0,
            'digests_skipped_disabled': 0,
            'digests_skipped_not_scheduled': 0,
            'digests_skipped_below_threshold': 0,
            'digests_skipped_dry_run': 0,
            'errors': [],
        }

        # Get all active tenants
        tenants = Tenant.query.filter_by(status='active').all()

        for tenant in tenants:
            stats['tenants_checked'] += 1

            try:
                result = _process_tenant_nudges(tenant, now_utc)

                if result == 'disabled':
                    stats['digests_skipped_disabled'] += 1
                elif result == 'not_scheduled':
                    stats['digests_skipped_not_scheduled'] += 1
                elif result == 'below_threshold':
                    stats['digests_skipped_below_threshold'] += 1
                elif result == 'dry_run':
                    stats['digests_skipped_dry_run'] += 1
                elif result == 'sent':
                    stats['digests_sent'] += 1

            except Exception as e:
                stats['errors'].append({
                    'tenant_id': tenant.id,
                    'error': str(e)
                })

        return stats


def _process_tenant_nudges(tenant, now_utc: datetime) -> str:
    """
    Process auto-nudges for a single tenant.

    Returns:
        Status string: 'disabled', 'not_scheduled', 'below_threshold',
                      'dry_run', 'sent'
    """
    config = tenant.get_auto_nudges_config()

    # Check if enabled
    if not config.get('enabled', False):
        return 'disabled'

    # Check if it's time to send based on schedule
    if not _is_scheduled_time(tenant, config, now_utc):
        return 'not_scheduled'

    # Get escalations for this tenant
    from app.services.sla_service import SLAService

    # Use a service user context (not restricted to any role)
    service_identity = {
        'user_id': None,
        'role': 'system',
    }
    sla_service = SLAService(tenant.id, service_identity)
    escalations = sla_service.get_escalations(limit=100)

    # Group by severity
    by_severity = {'critical': [], 'high': [], 'warn': []}
    for esc in escalations:
        sev = esc.get('severity', 'warn')
        if sev in by_severity:
            by_severity[sev].append(esc)

    # Check thresholds
    thresholds = config.get('thresholds', {}).get('send_if_at_least', {})
    min_critical = thresholds.get('critical', 1)
    min_high = thresholds.get('high', 2)
    min_warn = thresholds.get('warn', 5)

    should_send = (
        len(by_severity['critical']) >= min_critical or
        len(by_severity['high']) >= min_high or
        len(by_severity['warn']) >= min_warn
    )

    if not should_send:
        return 'below_threshold'

    # Filter types if configured
    include_types = config.get('thresholds', {}).get('include_types')
    if include_types:
        for sev in by_severity:
            by_severity[sev] = [
                e for e in by_severity[sev]
                if e.get('alert_type') in include_types
            ]

    # Apply rate limits - filter out recently nudged items
    rate_limits = config.get('rate_limits', {})
    per_entity_hours = rate_limits.get('per_entity_per_type_hours', {})
    max_emails_per_run = rate_limits.get('max_emails_per_run', 30)

    filtered_escalations = _apply_rate_limits(
        tenant.id,
        escalations,
        per_entity_hours,
        now_utc
    )

    # Limit total items
    filtered_escalations = filtered_escalations[:max_emails_per_run]

    if not filtered_escalations:
        return 'below_threshold'

    # Regroup after filtering
    filtered_by_severity = {'critical': [], 'high': [], 'warn': []}
    for esc in filtered_escalations:
        sev = esc.get('severity', 'warn')
        if sev in filtered_by_severity:
            filtered_by_severity[sev].append(esc)

    # Get recipients
    recipients = _get_recipients(tenant, config)

    if not recipients:
        return 'below_threshold'

    # Check dry run mode
    if config.get('dry_run', True):
        # Log dry run
        _log_digest_sent(
            tenant.id,
            recipients,
            filtered_by_severity,
            is_dry_run=True
        )
        return 'dry_run'

    # Build and send digest email
    _send_digest_email(
        tenant,
        recipients,
        filtered_by_severity,
        config
    )

    # Log that digest was sent (for anti-spam)
    _log_digest_sent(
        tenant.id,
        recipients,
        filtered_by_severity,
        is_dry_run=False
    )

    return 'sent'


def _is_scheduled_time(tenant, config: Dict[str, Any], now_utc: datetime) -> bool:
    """
    Check if current time matches the scheduled digest time.

    Uses tenant timezone and digest_time_local setting.
    For 'hourly' schedule, runs at the top of each hour.
    For 'daily' schedule, runs at digest_time_local.

    Allows 15-minute window to account for task execution timing.
    """
    schedule = config.get('digest_schedule', 'daily')
    digest_time_local = config.get('digest_time_local', '08:30')

    # Get tenant timezone
    tz_name = tenant.timezone or 'America/Chicago'
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.timezone('America/Chicago')

    # Convert now_utc to tenant local time
    now_local = now_utc.replace(tzinfo=pytz.UTC).astimezone(tz)

    if schedule == 'hourly':
        # Check if we're at the top of an hour (within 15 min window)
        return now_local.minute < 15

    # Daily schedule
    try:
        target_hour, target_minute = map(int, digest_time_local.split(':'))
    except (ValueError, AttributeError):
        target_hour, target_minute = 8, 30

    # Check if current time is within 15-minute window of target
    current_minutes = now_local.hour * 60 + now_local.minute
    target_minutes = target_hour * 60 + target_minute

    return 0 <= (current_minutes - target_minutes) < 15


def _apply_rate_limits(
    tenant_id: int,
    escalations: List[Dict[str, Any]],
    per_entity_hours: Dict[str, int],
    now_utc: datetime
) -> List[Dict[str, Any]]:
    """
    Filter out escalations that were recently nudged.

    Uses EstimateActivity to track when nudges were last sent
    for each entity+alert_type combination.
    """
    from app.models.tenant.estimate_activity import EstimateActivity

    if not escalations:
        return []

    # Default rate limits by severity
    default_hours = {'critical': 12, 'high': 24, 'warn': 48}

    # Build list of entity IDs to check
    entity_ids = [e['entity_id'] for e in escalations]

    # Get recent auto-nudge activities
    max_hours = 48  # Look back maximum window
    cutoff = now_utc - timedelta(hours=max_hours)

    recent_nudges = EstimateActivity.query.filter(
        EstimateActivity.estimate_id.in_(entity_ids),
        EstimateActivity.activity_type == 'auto_nudge_sent',
        EstimateActivity.created_at >= cutoff,
    ).all()

    # Build lookup: (entity_id, alert_type) -> last_sent_at
    nudge_times = {}
    for nudge in recent_nudges:
        metadata = nudge.metadata or {}
        alert_type = metadata.get('alert_type', '')
        key = (nudge.estimate_id, alert_type)

        existing = nudge_times.get(key)
        if not existing or nudge.created_at > existing:
            nudge_times[key] = nudge.created_at

    # Filter escalations
    filtered = []
    for esc in escalations:
        entity_id = esc['entity_id']
        alert_type = esc.get('alert_type', '')
        severity = esc.get('severity', 'warn')

        key = (entity_id, alert_type)
        last_sent = nudge_times.get(key)

        if last_sent:
            # Calculate hours since last nudge
            hours_since = (now_utc - last_sent).total_seconds() / 3600

            # Get rate limit for this severity
            rate_limit = per_entity_hours.get(
                severity,
                default_hours.get(severity, 24)
            )

            if hours_since < rate_limit:
                continue  # Skip - too soon

        filtered.append(esc)

    return filtered


def _get_recipients(tenant, config: Dict[str, Any]) -> List[str]:
    """
    Get email recipients based on config.

    Supports two modes:
    - 'roles': Get emails of users with specified roles
    - 'explicit': Use explicit email list
    """
    from app.models.master.user import User

    recipients_config = config.get('recipients', {})
    mode = recipients_config.get('mode', 'roles')

    if mode == 'explicit':
        return recipients_config.get('emails', [])

    # Roles mode
    roles = recipients_config.get('roles', ['owner', 'manager', 'desk'])

    users = User.query.filter(
        User.tenant_id == tenant.id,
        User.is_active == True,
        User.role.in_(roles),
    ).all()

    return [u.email for u in users if u.email]


def _send_digest_email(
    tenant,
    recipients: List[str],
    by_severity: Dict[str, List[Dict[str, Any]]],
    config: Dict[str, Any]
):
    """
    Send the digest email to all recipients.
    """
    from app.services.email_service import get_email_service
    from flask import current_app

    email_service = get_email_service()

    # Build email content
    subject = f"[HailTracker] SLA Digest: {tenant.company_name}"
    body = _build_digest_body(tenant, by_severity)

    # Send to each recipient
    for recipient in recipients:
        try:
            email_service.send_simple(
                to=recipient,
                subject=subject,
                body=body
            )
        except Exception as e:
            current_app.logger.error(
                f"Failed to send digest to {recipient}: {e}"
            )


def _build_digest_body(
    tenant,
    by_severity: Dict[str, List[Dict[str, Any]]]
) -> str:
    """
    Build the plain text digest email body.
    """
    lines = [
        f"SLA Digest for {tenant.company_name}",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "=" * 50,
        "",
    ]

    total = sum(len(items) for items in by_severity.values())
    lines.append(f"Total Items Requiring Attention: {total}")
    lines.append("")

    # Summary counts
    lines.append("SUMMARY:")
    lines.append(f"  Critical: {len(by_severity['critical'])}")
    lines.append(f"  High: {len(by_severity['high'])}")
    lines.append(f"  Warning: {len(by_severity['warn'])}")
    lines.append("")

    # Critical items first
    if by_severity['critical']:
        lines.append("-" * 50)
        lines.append("CRITICAL ITEMS:")
        lines.append("")
        for item in by_severity['critical']:
            lines.extend(_format_item(item))

    # High priority items
    if by_severity['high']:
        lines.append("-" * 50)
        lines.append("HIGH PRIORITY ITEMS:")
        lines.append("")
        for item in by_severity['high']:
            lines.extend(_format_item(item))

    # Warning items
    if by_severity['warn']:
        lines.append("-" * 50)
        lines.append("WARNING ITEMS:")
        lines.append("")
        for item in by_severity['warn']:
            lines.extend(_format_item(item))

    lines.append("")
    lines.append("=" * 50)
    lines.append("")
    lines.append("View all items in your Work Inbox:")
    lines.append("https://app.hailtracker.pro/notifications")
    lines.append("")
    lines.append("--")
    lines.append("HailTracker Pro Auto-Nudges")
    lines.append("Configure these notifications in Settings > Auto-Nudges")

    return "\n".join(lines)


def _format_item(item: Dict[str, Any]) -> List[str]:
    """Format a single escalation item for the digest."""
    lines = []
    lines.append(f"  • {item.get('title', 'Unknown')}")

    if item.get('subtitle'):
        lines.append(f"    {item['subtitle']}")

    age_days = item.get('age_days')
    age_hours = item.get('age_hours')
    if age_days:
        lines.append(f"    Age: {age_days} days")
    elif age_hours:
        lines.append(f"    Age: {age_hours} hours")

    lines.append("")
    return lines


def _log_digest_sent(
    tenant_id: int,
    recipients: List[str],
    by_severity: Dict[str, List[Dict[str, Any]]],
    is_dry_run: bool
):
    """
    Log that a digest was sent for anti-spam tracking.

    Creates EstimateActivity entries for each escalation item
    so we can track when it was last included in a digest.
    """
    from app.models.tenant.estimate_activity import EstimateActivity

    # Log each item that was included
    for severity, items in by_severity.items():
        for item in items:
            # Only log for estimate entities
            if item.get('entity') != 'estimate':
                continue

            EstimateActivity.log(
                estimate_id=item['entity_id'],
                activity_type='auto_nudge_sent',
                user_id=None,  # System action
                activity_data={
                    'alert_type': item.get('alert_type'),
                    'severity': severity,
                    'recipients': recipients,
                    'dry_run': is_dry_run,
                    'tenant_id': tenant_id,
                }
            )

    db.session.commit()
