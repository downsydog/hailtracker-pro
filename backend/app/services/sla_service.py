"""
SLA Service - Computed escalations and alerts.

No new models - computes alerts from existing data based on timing rules.
Reuses WorkflowService priority scoring patterns.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import and_, or_, func
from app.extensions import db


class SLAService:
    """
    Computes SLA escalations/alerts based on timing rules.

    Alert severities:
    - warn: Approaching SLA threshold
    - high: SLA breached, needs attention
    - critical: Severely overdue, urgent action required

    Priority score mapping:
    - warn: 65
    - high: 80
    - critical: 95
    """

    SEVERITY_SCORES = {
        'warn': 65,
        'high': 80,
        'critical': 95,
    }

    def __init__(self, tenant_id: int, user_identity: dict):
        self.tenant_id = tenant_id
        self.user_id = user_identity.get('user_id')
        self.user_role = user_identity.get('role', '')
        self.is_restricted_role = self.user_role in ['tech', 'technician', 'sales', 'salesman']
        self.now = datetime.utcnow()

    def get_escalations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all SLA escalations/alerts for the tenant.

        Returns list of alert items sorted by severity (critical first),
        then by age (oldest first).
        """
        alerts = []

        # Skip non-job alerts for restricted roles
        if not self.is_restricted_role:
            alerts.extend(self._get_insurer_submission_alerts())
            alerts.extend(self._get_needs_revision_alerts())
            alerts.extend(self._get_draft_supplement_alerts())
            alerts.extend(self._get_overdue_invoice_alerts())
            alerts.extend(self._get_lead_followup_alerts())
            alerts.extend(self._get_parts_blocker_alerts())
            # Stage 5V: PartRequest SLA alerts
            alerts.extend(self._get_part_request_alerts())

        # Job alerts - filter for assigned jobs if restricted role
        alerts.extend(self._get_stale_job_alerts())

        # Sort by severity score DESC, then by timestamp ASC (oldest first)
        alerts.sort(key=lambda x: (
            -x.get('priority_score', 0),
            x.get('timestamp') or '',
        ))

        return alerts[:limit]

    def _get_insurer_submission_alerts(self) -> List[Dict[str, Any]]:
        """Alerts for estimates submitted to insurer and waiting."""
        from app.models.tenant.pdr_estimate import PDREstimate

        alerts = []

        # Get estimates submitted to insurer
        estimates = PDREstimate.query.filter(
            PDREstimate.tenant_id == self.tenant_id,
            PDREstimate.status.notin_(['completed', 'cancelled']),
            PDREstimate.insurer_status == 'submitted',
            PDREstimate.submitted_to_insurer_at.isnot(None),
        ).all()

        for est in estimates:
            days_waiting = (self.now - est.submitted_to_insurer_at).days

            # Determine severity
            if days_waiting >= 14:
                severity = 'critical'
                reason = f'Insurer waiting {days_waiting}d - critical'
            elif days_waiting >= 7:
                severity = 'high'
                reason = f'Insurer waiting {days_waiting}d - high'
            elif days_waiting >= 3:
                severity = 'warn'
                reason = f'Insurer waiting {days_waiting}d'
            else:
                continue  # Not escalated yet

            vehicle_display = f"{est.vehicle_year or ''} {est.vehicle_make or ''} {est.vehicle_model or ''}".strip() or 'No vehicle'

            alerts.append({
                'id': f"sla:insurer_waiting:estimate:{est.id}",
                'severity': severity,
                'alert_type': 'insurer_waiting',
                'entity': 'estimate',
                'entity_id': est.id,
                'title': f"Estimate {est.estimate_number} waiting on insurer",
                'subtitle': f"{est.customer_name or 'Unknown'} • {vehicle_display} • {est.insurance_company or 'Unknown insurer'}",
                'timestamp': est.submitted_to_insurer_at.isoformat() if est.submitted_to_insurer_at else None,
                'age_days': days_waiting,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': f"/estimating/{est.id}",
                'primary_action': {
                    'key': 'nudge_insurer',
                    'label': 'Send Nudge',
                    'route': f"/estimating/{est.id}",
                },
            })

        return alerts

    def _get_needs_revision_alerts(self) -> List[Dict[str, Any]]:
        """Alerts for estimates needing revision from insurer."""
        from app.models.tenant.pdr_estimate import PDREstimate
        from app.models.tenant.estimate_activity import EstimateActivity

        alerts = []

        # Get estimates needing revision
        estimates = PDREstimate.query.filter(
            PDREstimate.tenant_id == self.tenant_id,
            PDREstimate.status.notin_(['completed', 'cancelled']),
            PDREstimate.insurer_status == 'needs_revision',
        ).all()

        # Get the timestamp when revision was requested (from activity log)
        estimate_ids = [e.id for e in estimates]
        revision_times = {}
        if estimate_ids:
            revision_activities = EstimateActivity.query.filter(
                EstimateActivity.estimate_id.in_(estimate_ids),
                EstimateActivity.activity_type == 'insurer_needs_revision',
            ).order_by(EstimateActivity.created_at.desc()).all()

            for act in revision_activities:
                if act.estimate_id not in revision_times:
                    revision_times[act.estimate_id] = act.created_at

        for est in estimates:
            revision_at = revision_times.get(est.id) or est.updated_at or self.now
            days_waiting = (self.now - revision_at).days

            # Determine severity
            if days_waiting >= 5:
                severity = 'critical'
                reason = f'Needs revision {days_waiting}d - critical'
            elif days_waiting >= 2:
                severity = 'high'
                reason = f'Needs revision {days_waiting}d'
            else:
                continue  # Not escalated yet

            vehicle_display = f"{est.vehicle_year or ''} {est.vehicle_make or ''} {est.vehicle_model or ''}".strip() or 'No vehicle'

            alerts.append({
                'id': f"sla:needs_revision:estimate:{est.id}",
                'severity': severity,
                'alert_type': 'needs_revision',
                'entity': 'estimate',
                'entity_id': est.id,
                'title': f"Estimate {est.estimate_number} needs revision",
                'subtitle': f"{est.customer_name or 'Unknown'} • {vehicle_display}",
                'timestamp': revision_at.isoformat() if revision_at else None,
                'age_days': days_waiting,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': f"/estimating/{est.id}",
                'primary_action': {
                    'key': 'revise_estimate',
                    'label': 'Revise',
                    'route': f"/estimating/{est.id}",
                },
            })

        return alerts

    def _get_draft_supplement_alerts(self) -> List[Dict[str, Any]]:
        """Alerts for draft supplements not yet sent."""
        from app.models.tenant.pdr_estimate import PDREstimate
        from app.models.tenant.estimate_supplement import EstimateSupplement

        alerts = []

        # Get draft supplements with estimate info
        supplements = db.session.query(
            EstimateSupplement,
            PDREstimate.estimate_number,
            PDREstimate.customer_name,
        ).join(
            PDREstimate,
            EstimateSupplement.estimate_id == PDREstimate.id
        ).filter(
            PDREstimate.tenant_id == self.tenant_id,
            EstimateSupplement.status == 'draft',
        ).all()

        for supp, est_number, cust_name in supplements:
            days_draft = (self.now - supp.created_at).days if supp.created_at else 0

            # Determine severity
            if days_draft >= 4:
                severity = 'critical'
                reason = f'Draft supplement {days_draft}d - critical'
            elif days_draft >= 2:
                severity = 'high'
                reason = f'Draft supplement {days_draft}d'
            else:
                continue  # Not escalated yet

            alerts.append({
                'id': f"sla:draft_supplement:supplement:{supp.id}",
                'severity': severity,
                'alert_type': 'draft_supplement',
                'entity': 'supplement',
                'entity_id': supp.id,
                'title': f"Supplement #{supp.supplement_number} draft for {est_number}",
                'subtitle': f"{cust_name or 'Unknown'} • ${float(supp.delta_amount or 0):.0f} delta",
                'timestamp': supp.created_at.isoformat() if supp.created_at else None,
                'age_days': days_draft,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': f"/estimating/{supp.estimate_id}?tab=supplements",
                'primary_action': {
                    'key': 'send_supplement',
                    'label': 'Send',
                    'route': f"/estimating/{supp.estimate_id}?tab=supplements",
                },
            })

        return alerts

    def _get_stale_job_alerts(self) -> List[Dict[str, Any]]:
        """Alerts for jobs in_progress that haven't been updated."""
        from app.models.tenant.job import Job
        from app.models.master.user import User

        alerts = []

        # Build query for in_progress jobs
        query = Job.query.filter(
            Job.tenant_id == self.tenant_id,
            Job.status == 'in_progress',
        )

        # Filter for assigned jobs if restricted role
        if self.is_restricted_role:
            query = query.filter(Job.assigned_tech == self.user_id)

        jobs = query.all()

        # Bulk fetch tech names
        tech_ids = [j.assigned_tech for j in jobs if j.assigned_tech]
        techs_by_id = {}
        if tech_ids:
            techs = User.query.filter(
                User.id.in_(tech_ids),
                User.tenant_id == self.tenant_id
            ).all()
            techs_by_id = {t.id: t.name for t in techs}

        for job in jobs:
            # Calculate hours since last update
            last_activity = job.updated_at or job.created_at or self.now
            hours_stale = int((self.now - last_activity).total_seconds() / 3600)

            # Determine severity
            if hours_stale >= 24:
                severity = 'critical'
                reason = f'In progress {hours_stale}h - critical'
            elif hours_stale >= 8:
                severity = 'high'
                reason = f'In progress {hours_stale}h'
            elif hours_stale >= 4:
                severity = 'warn'
                reason = f'In progress {hours_stale}h'
            else:
                continue  # Not escalated yet

            vehicle_display = f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or 'No vehicle'
            tech_name = techs_by_id.get(job.assigned_tech) or 'Unassigned'

            alerts.append({
                'id': f"sla:stale_job:job:{job.id}",
                'severity': severity,
                'alert_type': 'stale_job',
                'entity': 'job',
                'entity_id': job.id,
                'title': f"Job {job.job_number} stale in progress",
                'subtitle': f"{job.customer_name or 'Unknown'} • {vehicle_display} • {tech_name}",
                'timestamp': last_activity.isoformat() if last_activity else None,
                'age_hours': hours_stale,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': f"/jobs/{job.id}",
                'primary_action': {
                    'key': 'complete_job',
                    'label': 'Complete',
                    'route': f"/jobs/{job.id}",
                },
            })

        return alerts

    def _get_overdue_invoice_alerts(self) -> List[Dict[str, Any]]:
        """Alerts for overdue invoices."""
        from app.models.tenant.invoice import Invoice

        alerts = []

        # Get overdue invoices
        invoices = Invoice.query.filter(
            Invoice.tenant_id == self.tenant_id,
            Invoice.status.in_(['issued', 'partial_paid']),
            Invoice.due_at < self.now,
        ).all()

        for inv in invoices:
            days_overdue = (self.now - inv.due_at).days

            # Determine severity
            if days_overdue >= 7:
                severity = 'critical'
                reason = f'Overdue {days_overdue}d - critical'
            elif days_overdue >= 1:
                severity = 'high'
                reason = f'Overdue {days_overdue}d'
            else:
                continue  # Not escalated yet

            alerts.append({
                'id': f"sla:overdue_invoice:invoice:{inv.id}",
                'severity': severity,
                'alert_type': 'overdue_invoice',
                'entity': 'invoice',
                'entity_id': inv.id,
                'title': f"Invoice {inv.invoice_number} overdue",
                'subtitle': f"{inv.payer_name or 'Unknown'} • ${float(inv.balance_due):.0f} due",
                'timestamp': inv.due_at.isoformat() if inv.due_at else None,
                'age_days': days_overdue,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': f"/invoices/{inv.id}",
                'primary_action': {
                    'key': 'collect_payment',
                    'label': 'Collect',
                    'route': f"/invoices/{inv.id}",
                },
            })

        return alerts

    def _get_lead_followup_alerts(self) -> List[Dict[str, Any]]:
        """Alerts for leads needing follow-up calls."""
        from app.models.tenant.lead import Lead
        from app.models.tenant.call import Call

        alerts = []

        # Get the last call date per lead
        last_call_subq = db.session.query(
            Call.lead_id,
            func.max(Call.called_at).label('last_call')
        ).group_by(Call.lead_id).subquery()

        # Get leads that are still active (new/contacted)
        leads = db.session.query(
            Lead,
            last_call_subq.c.last_call
        ).outerjoin(
            last_call_subq,
            Lead.id == last_call_subq.c.lead_id
        ).filter(
            Lead.tenant_id == self.tenant_id,
            Lead.status.in_(['new', 'contacted']),
        ).all()

        for lead, last_call in leads:
            # Calculate days since last contact
            reference_date = last_call or lead.created_at or self.now
            days_since_contact = (self.now - reference_date).days

            # Determine severity
            if days_since_contact >= 7:
                severity = 'high'
                reason = f'No contact {days_since_contact}d - high'
            elif days_since_contact >= 3:
                severity = 'warn'
                reason = f'No contact {days_since_contact}d'
            else:
                continue  # Not escalated yet

            alerts.append({
                'id': f"sla:lead_followup:lead:{lead.id}",
                'severity': severity,
                'alert_type': 'lead_followup',
                'entity': 'lead',
                'entity_id': lead.id,
                'title': f"Lead needs follow-up",
                'subtitle': f"{lead.business_name or lead.contact_name or 'Unknown'} • {lead.phone or 'No phone'}",
                'timestamp': reference_date.isoformat() if reference_date else None,
                'age_days': days_since_contact,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': f"/leads/{lead.id}",
                'primary_action': {
                    'key': 'call_lead',
                    'label': 'Call',
                    'route': f"/leads/{lead.id}",
                },
            })

        return alerts

    def _get_parts_blocker_alerts(self) -> List[Dict[str, Any]]:
        """Alerts for jobs blocked waiting on parts."""
        from app.models.tenant.job import Job
        from app.models.master.user import User
        from app.services.blocker_helpers import get_bulk_job_blockers_with_timestamps

        alerts = []

        # Get all active jobs with potential blockers
        jobs = Job.query.filter(
            Job.tenant_id == self.tenant_id,
            Job.status.in_(['scheduled', 'in_progress']),
        ).all()

        if not jobs:
            return alerts

        # Bulk fetch tech names
        tech_ids = [j.assigned_tech for j in jobs if j.assigned_tech]
        techs_by_id = {}
        if tech_ids:
            techs = User.query.filter(
                User.id.in_(tech_ids),
                User.tenant_id == self.tenant_id
            ).all()
            techs_by_id = {t.id: t.name for t in techs}

        # Build job lookup
        jobs_by_id = {j.id: j for j in jobs}

        # Use centralized blocker helper (Stage 5O.1)
        job_ids_with_estimates = [(j.id, j.estimate_id) for j in jobs]
        blockers = get_bulk_job_blockers_with_timestamps(job_ids_with_estimates, self.tenant_id)

        # Process blockers (only parts blockers)
        for job_id, blocker_info in blockers.items():
            issue_type = blocker_info.get('issue_type', 'other')

            # Only process waiting_on_parts blockers
            if issue_type != 'waiting_on_parts':
                continue

            job = jobs_by_id.get(job_id)
            if not job:
                continue

            # Calculate days since blocker created/updated
            blocker_time = blocker_info.get('blocked_at')
            days_blocked = (self.now - blocker_time).days if blocker_time else 0

            # Get parts info
            parts = blocker_info.get('parts', {})
            eta_str = parts.get('eta') if parts else None
            has_eta = bool(eta_str)
            eta_overdue = False

            if eta_str:
                try:
                    if 'T' in eta_str:
                        eta = datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
                    else:
                        eta = datetime.strptime(eta_str, '%Y-%m-%d')
                    eta_overdue = eta < self.now
                except (ValueError, TypeError):
                    pass

            # Determine severity based on age and ETA
            # warn at 1 day, high at 3 days, critical at 5 days
            # If ETA exists and not overdue, reduce severity one level
            if eta_overdue:
                severity = 'critical'
                reason = f'Parts blocker {days_blocked}d - ETA missed'
            elif days_blocked >= 5:
                severity = 'critical' if not has_eta else 'high'
                reason = f'Parts blocker {days_blocked}d - critical'
            elif days_blocked >= 3:
                severity = 'high' if not has_eta else 'warn'
                reason = f'Parts blocker {days_blocked}d - high'
            elif days_blocked >= 1:
                severity = 'warn'
                reason = f'Parts blocker {days_blocked}d'
            else:
                continue  # Not escalated yet

            vehicle_display = f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or 'No vehicle'
            tech_name = techs_by_id.get(job.assigned_tech) or 'Unassigned'
            vendor = parts.get('vendor') if parts else None

            subtitle = f"{job.customer_name or 'Unknown'} • {vehicle_display} • {tech_name}"
            if vendor:
                subtitle += f" • Vendor: {vendor}"
            if eta_str:
                subtitle += f" • ETA: {eta_str[:10]}"

            alerts.append({
                'id': f"sla:parts_blocked:job:{job.id}",
                'severity': severity,
                'alert_type': 'job_parts_blocked',
                'entity': 'job',
                'entity_id': job.id,
                'title': f"Job {job.job_number} waiting on parts",
                'subtitle': subtitle,
                'timestamp': blocker_time.isoformat() if blocker_time else None,
                'age_days': days_blocked,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': f"/jobs/{job.id}",
                'parts': {
                    'ordered': parts.get('ordered', False) if parts else False,
                    'vendor': vendor,
                    'po_number': parts.get('po_number') if parts else None,
                    'eta': eta_str,
                    # Stage 5P fields
                    'parts_status': parts.get('parts_status', 'needed') if parts else 'needed',
                    'approved_to_order': parts.get('approved_to_order', False) if parts else False,
                    'approved_amount': parts.get('approved_amount') if parts else None,
                },
                'primary_action': {
                    'key': 'update_blocker',
                    'label': 'Update ETA',
                    'route': f"/jobs/{job.id}",
                },
            })

        return alerts

    def _get_part_request_alerts(self) -> List[Dict[str, Any]]:
        """
        Stage 5V: Alerts for PartRequests needing attention.

        SLA thresholds:
        - approved_to_order but not ordered: warn 1d / high 3d / critical 5d
        - ordered but no ETA: high immediately, critical after 2d
        - ETA missed (eta < now) and status not received/installed: critical immediately
        - shipped but not received: warn 3d / high 5d / critical 10d
        - exception status: critical immediately
        """
        from app.models.tenant.part_request import PartRequest
        from app.models.tenant.job import Job
        from app.models.master.user import User

        alerts = []

        # Get all open part requests (not installed)
        requests = PartRequest.query.filter(
            PartRequest.tenant_id == self.tenant_id,
            PartRequest.parts_status != 'installed',
        ).all()

        if not requests:
            return alerts

        # Bulk fetch jobs for context
        job_ids = [r.job_id for r in requests if r.job_id]
        jobs_by_id = {}
        if job_ids:
            jobs = Job.query.filter(
                Job.id.in_(job_ids),
                Job.tenant_id == self.tenant_id
            ).all()
            jobs_by_id = {j.id: j for j in jobs}

        # Bulk fetch tech names
        tech_ids = list(set(j.assigned_tech for j in jobs_by_id.values() if j.assigned_tech))
        techs_by_id = {}
        if tech_ids:
            techs = User.query.filter(
                User.id.in_(tech_ids),
                User.tenant_id == self.tenant_id
            ).all()
            techs_by_id = {t.id: t.name for t in techs}

        for req in requests:
            severity = None
            reason = None
            age_days = 0
            eta_days_overdue = None

            # Calculate age since status was set or created
            reference_time = req.status_updated_at or req.updated_at or req.created_at or self.now
            age_days = (self.now - reference_time).days

            # Check ETA overdue
            eta_overdue = False
            if req.eta:
                if req.eta < self.now and req.parts_status not in ['received', 'installed']:
                    eta_overdue = True
                    eta_days_overdue = (self.now - req.eta).days

            # Determine severity based on status and thresholds
            if req.parts_status == 'exception':
                severity = 'critical'
                reason = 'Part request exception'
            elif eta_overdue:
                severity = 'critical'
                reason = f'ETA missed by {eta_days_overdue}d'
            elif req.parts_status == 'ordered' and not req.eta:
                # Ordered but no ETA
                if age_days >= 2:
                    severity = 'critical'
                    reason = f'Ordered {age_days}d, no ETA - critical'
                else:
                    severity = 'high'
                    reason = 'Ordered without ETA'
            elif req.parts_status == 'approved_to_order':
                # Approved but not ordered
                if age_days >= 5:
                    severity = 'critical'
                    reason = f'Approved {age_days}d, not ordered - critical'
                elif age_days >= 3:
                    severity = 'high'
                    reason = f'Approved {age_days}d, not ordered'
                elif age_days >= 1:
                    severity = 'warn'
                    reason = f'Approved {age_days}d, not ordered'
            elif req.parts_status == 'shipped':
                # Shipped but not received
                shipped_at = req.shipped_at or reference_time
                days_shipped = (self.now - shipped_at).days
                if days_shipped >= 10:
                    severity = 'critical'
                    reason = f'Shipped {days_shipped}d, not received - critical'
                elif days_shipped >= 5:
                    severity = 'high'
                    reason = f'Shipped {days_shipped}d, not received'
                elif days_shipped >= 3:
                    severity = 'warn'
                    reason = f'Shipped {days_shipped}d, not received'

            # Skip if no escalation needed
            if not severity:
                continue

            # Build context
            job = jobs_by_id.get(req.job_id)
            job_number = job.job_number if job else None
            customer_name = job.customer_name if job else None
            vehicle_display = None
            tech_name = None
            if job:
                vehicle_display = f"{job.vehicle_year or ''} {job.vehicle_make or ''} {job.vehicle_model or ''}".strip() or None
                tech_name = techs_by_id.get(job.assigned_tech)

            subtitle_parts = [req.description[:50]]
            if job_number:
                subtitle_parts.insert(0, f"Job {job_number}")
            if customer_name:
                subtitle_parts.append(customer_name)
            if req.vendor:
                subtitle_parts.append(f"Vendor: {req.vendor}")

            alerts.append({
                'id': f"sla:part_request:{req.id}",
                'severity': severity,
                'alert_type': 'part_request_sla',
                'entity': 'part_request',
                'entity_id': req.id,
                'estimate_id': req.estimate_id,
                'job_id': req.job_id,
                'title': f"Part request: {req.description[:40]}{'...' if len(req.description) > 40 else ''}",
                'subtitle': ' • '.join(subtitle_parts),
                'timestamp': reference_time.isoformat() if reference_time else None,
                'age_days': age_days,
                'eta_days_overdue': eta_days_overdue,
                'priority_score': self.SEVERITY_SCORES[severity],
                'priority_reason': reason,
                'route': '/dashboard?tab=parts&attention=1' + (f'&request_id={req.id}' if req.id else ''),
                # PartRequest specific fields
                'parts_status': req.parts_status,
                'vendor': req.vendor,
                'po_number': req.po_number,
                'eta': req.eta.isoformat() if req.eta else None,
                'approved_to_order': req.approved_to_order,
                'approved_amount': float(req.approved_amount) if req.approved_amount else None,
                'primary_action': {
                    'key': 'update_part_request',
                    'label': 'Update Status',
                    'route': '/dashboard?tab=parts&attention=1',
                },
            })

        return alerts

    def get_summary(self) -> Dict[str, int]:
        """Get counts by severity for dashboard tiles."""
        alerts = self.get_escalations(limit=200)  # Get more for accurate counts

        return {
            'critical': sum(1 for a in alerts if a['severity'] == 'critical'),
            'high': sum(1 for a in alerts if a['severity'] == 'high'),
            'warn': sum(1 for a in alerts if a['severity'] == 'warn'),
            'total': len(alerts),
        }
