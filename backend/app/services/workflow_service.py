"""
Workflow Service - Centralized workflow rules and next action engine.

Computes the current state and available next actions for an estimate/job/invoice
workflow. Acts as the single source of truth for workflow logic.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
from datetime import datetime, timedelta


@dataclass
class WorkflowPriority:
    """Priority scoring for workflow items."""
    score: int  # Higher = more urgent (0-100 scale)
    reason: Optional[str] = None


@dataclass
class WorkflowAction:
    """Represents a possible next action in the workflow."""
    key: str
    label: str
    description: str
    enabled: bool
    reason_disabled: Optional[str] = None
    endpoint_hint: Optional[str] = None
    priority: int = 10  # Lower = higher priority


@dataclass
class WorkflowState:
    """Current state summary for workflow display."""
    estimate_status: str
    customer_status: str
    insurer_status: str
    job_status: Optional[str]
    job_id: Optional[int]
    invoices_count: int
    invoices_total: float
    invoices_paid: float
    invoices_balance: float
    has_insurer_invoice: bool
    has_customer_invoice: bool
    all_invoices_paid: bool
    deductible: float
    customer_oop: float


class WorkflowService:
    """
    Computes workflow state and next actions for PDR estimates.

    Usage:
        service = WorkflowService(estimate)
        result = service.get_workflow()
    """

    def __init__(self, estimate):
        """
        Initialize with a PDREstimate instance.

        Args:
            estimate: PDREstimate model instance with related job/invoices loaded
        """
        self.estimate = estimate
        self._job = None
        self._invoices = []
        self._state = None

    def _load_relationships(self):
        """Load related job and invoices."""
        # Get linked job (most recent)
        if hasattr(self.estimate, 'jobs') and self.estimate.jobs:
            jobs = list(self.estimate.jobs)
            if jobs:
                # Get most recent non-cancelled job
                active_jobs = [j for j in jobs if j.status not in ['cancelled', 'CANCELLED']]
                self._job = active_jobs[0] if active_jobs else None

        # Get linked invoices
        if hasattr(self.estimate, 'invoices'):
            self._invoices = list(self.estimate.invoices)

    def _compute_state(self) -> WorkflowState:
        """Compute the current workflow state."""
        self._load_relationships()

        # Invoice calculations
        invoices_total = sum(float(inv.total or 0) for inv in self._invoices)
        invoices_paid = sum(float(inv.amount_paid or 0) for inv in self._invoices)
        invoices_balance = sum(float(inv.balance_due) for inv in self._invoices)

        # Check for specific invoice types
        has_insurer_invoice = any(
            inv.allocation_type == 'insurer' and inv.status != 'void'
            for inv in self._invoices
        )
        has_customer_invoice = any(
            inv.allocation_type in ['customer_deductible', 'customer_oop'] and inv.status != 'void'
            for inv in self._invoices
        )

        # All paid check
        active_invoices = [inv for inv in self._invoices if inv.status != 'void']
        all_invoices_paid = len(active_invoices) > 0 and all(
            inv.is_paid() for inv in active_invoices
        )

        return WorkflowState(
            estimate_status=self.estimate.status or 'draft',
            customer_status=self.estimate.customer_status or 'draft',
            insurer_status=self.estimate.insurer_status or 'not_submitted',
            job_status=self._job.status if self._job else None,
            job_id=self._job.id if self._job else None,
            invoices_count=len(active_invoices),
            invoices_total=invoices_total,
            invoices_paid=invoices_paid,
            invoices_balance=invoices_balance,
            has_insurer_invoice=has_insurer_invoice,
            has_customer_invoice=has_customer_invoice,
            all_invoices_paid=all_invoices_paid,
            deductible=float(self.estimate.deductible or 0),
            customer_oop=float(getattr(self.estimate, 'customer_oop', 0) or 0),
        )

    def _compute_priority(self, state: WorkflowState, primary_action: Optional[WorkflowAction]) -> WorkflowPriority:
        """
        Compute priority score for this workflow item.

        Score scale (0-100):
        - 90-100: Critical - needs immediate action (needs_revision, overdue invoices)
        - 80-89: Very high - blocking revenue (draft supplements)
        - 70-79: High - needs attention soon (approved no job, job done no invoice)
        - 60-69: Medium-high - aging items (waiting on insurer)
        - 40-59: Medium - standard workflow items
        - 20-39: Low - can wait
        - 0-19: Very low - informational only
        """
        score = 50  # Default medium priority
        reason = None

        # Check for overdue invoices (critical)
        if state.invoices_balance > 0:
            # Check if any invoices are overdue - needs estimate.invoices access
            overdue_days = 0
            for inv in self._invoices:
                if inv.due_at and inv.status in ['issued', 'partial_paid']:
                    days_overdue = (datetime.utcnow() - inv.due_at).days
                    if days_overdue > 0:
                        overdue_days = max(overdue_days, days_overdue)

            if overdue_days > 0:
                score = min(100, 90 + overdue_days)  # 90-100 based on days overdue
                reason = f"Invoice overdue {overdue_days} day{'s' if overdue_days != 1 else ''}"
                return WorkflowPriority(score=score, reason=reason)

        # Check for needs_revision (critical priority - blocking revenue)
        if state.insurer_status == 'needs_revision':
            score = 90
            reason = "Needs revision"
            return WorkflowPriority(score=score, reason=reason)

        # Check for draft supplements (very high priority - needs to be sent)
        if hasattr(self.estimate, 'supplements'):
            draft_supplements = [s for s in self.estimate.supplements if s.status == 'draft']
            if draft_supplements:
                score = 85
                reason = f"Supplement draft ({len(draft_supplements)})"
                return WorkflowPriority(score=score, reason=reason)

        # Check for submitted to insurer (priority based on wait time)
        if state.insurer_status == 'submitted':
            days_waiting = 0
            if hasattr(self.estimate, 'submitted_to_insurer_at') and self.estimate.submitted_to_insurer_at:
                days_waiting = (datetime.utcnow() - self.estimate.submitted_to_insurer_at).days

            if days_waiting >= 14:
                score = 80
                reason = f"Waiting on insurer: {days_waiting} days"
            elif days_waiting >= 7:
                score = 70
                reason = f"Waiting on insurer: {days_waiting} days"
            elif days_waiting >= 3:
                score = 60
                reason = f"Waiting on insurer: {days_waiting} days"
            else:
                score = 45
                reason = "Awaiting insurer response"
            return WorkflowPriority(score=score, reason=reason)

        # Check for approved but no job (high priority - ready for scheduling)
        if state.insurer_status == 'approved' and not state.job_id:
            score = 75
            reason = "Approved: create job"
            return WorkflowPriority(score=score, reason=reason)

        # Check for job completed but no invoice issued (high priority)
        if state.job_status in ['completed', 'COMPLETED']:
            # Check if insurer invoice exists
            if not state.has_insurer_invoice:
                score = 70
                reason = "Job done: create invoice"
                return WorkflowPriority(score=score, reason=reason)

        # Check for job in progress (should complete soon)
        if state.job_status in ['in_progress', 'IN_PROGRESS']:
            score = 60
            reason = "Job in progress"
            return WorkflowPriority(score=score, reason=reason)

        # Check for pending customer signature
        if state.customer_status == 'pending':
            score = 45
            reason = "Awaiting customer signature"
            return WorkflowPriority(score=score, reason=reason)

        # Check for balance due (need to collect)
        if state.invoices_balance > 0:
            score = 55
            reason = f"${state.invoices_balance:.0f} balance due"
            return WorkflowPriority(score=score, reason=reason)

        # Check for draft (needs auth request)
        if state.customer_status == 'draft':
            score = 40
            reason = "Needs customer authorization"
            return WorkflowPriority(score=score, reason=reason)

        # Check for approved, ready for job
        if state.insurer_status == 'approved' and not state.job_id:
            score = 55
            reason = "Ready to create job"
            return WorkflowPriority(score=score, reason=reason)

        # Check for scheduled job
        if state.job_status in ['scheduled', 'SCHEDULED']:
            score = 45
            reason = "Job scheduled"
            return WorkflowPriority(score=score, reason=reason)

        # Default - use primary action if available
        if primary_action:
            reason = primary_action.label

        return WorkflowPriority(score=score, reason=reason)

    def _compute_actions(self, state: WorkflowState) -> List[WorkflowAction]:
        """Compute available next actions based on current state."""
        actions = []

        # 1. Customer Authorization Flow
        if state.customer_status == 'draft':
            actions.append(WorkflowAction(
                key='request_customer_auth',
                label='Request Customer Authorization',
                description='Send estimate to customer for signature approval',
                enabled=True,
                endpoint_hint=f'/pdr-estimates/{self.estimate.id}/sign',
                priority=1
            ))
        elif state.customer_status == 'pending':
            actions.append(WorkflowAction(
                key='awaiting_signature',
                label='Awaiting Customer Signature',
                description='Customer has been sent the estimate for review',
                enabled=False,
                reason_disabled='Waiting for customer to sign',
                priority=1
            ))

        # 2. Insurer Submission Flow
        if state.customer_status == 'authorized':
            if state.insurer_status == 'not_submitted':
                actions.append(WorkflowAction(
                    key='submit_to_insurer',
                    label='Submit to Insurer',
                    description='Submit estimate to insurance company for approval',
                    enabled=True,
                    endpoint_hint=f'/pdr-estimates/{self.estimate.id}/submit-insurer',
                    priority=2
                ))
            elif state.insurer_status == 'submitted':
                actions.append(WorkflowAction(
                    key='mark_insurer_approved',
                    label='Mark Insurer Approved',
                    description='Record insurance company approval',
                    enabled=True,
                    endpoint_hint=f'/pdr-estimates/{self.estimate.id}/insurer-approve',
                    priority=2
                ))
                actions.append(WorkflowAction(
                    key='mark_needs_revision',
                    label='Needs Revision',
                    description='Insurance requested changes to estimate',
                    enabled=True,
                    endpoint_hint=f'/pdr-estimates/{self.estimate.id}/insurer-revision',
                    priority=3
                ))
            elif state.insurer_status == 'needs_revision':
                actions.append(WorkflowAction(
                    key='resubmit_to_insurer',
                    label='Resubmit to Insurer',
                    description='Resubmit revised estimate to insurance',
                    enabled=True,
                    endpoint_hint=f'/pdr-estimates/{self.estimate.id}/submit-insurer',
                    priority=2
                ))

        # 3. Job Creation Flow (after insurer approval)
        if state.insurer_status == 'approved':
            if not state.job_id:
                actions.append(WorkflowAction(
                    key='create_job',
                    label='Create Job',
                    description='Create a repair job from this estimate',
                    enabled=True,
                    endpoint_hint=f'/pdr-estimates/{self.estimate.id}/job',
                    priority=3
                ))
            else:
                # Job status progression
                if state.job_status in ['scheduled', 'SCHEDULED']:
                    actions.append(WorkflowAction(
                        key='start_job',
                        label='Start Job',
                        description='Mark job as in progress',
                        enabled=True,
                        endpoint_hint=f'/jobs/{state.job_id}/status',
                        priority=4
                    ))
                elif state.job_status in ['in_progress', 'IN_PROGRESS']:
                    actions.append(WorkflowAction(
                        key='complete_job',
                        label='Complete Job',
                        description='Mark job as completed',
                        enabled=True,
                        endpoint_hint=f'/jobs/{state.job_id}/status',
                        priority=4
                    ))

        # 4. Invoice Creation Flow (after insurer approval)
        if state.insurer_status == 'approved':
            # Insurer invoice
            if not state.has_insurer_invoice:
                insurer_total = self.estimate.get_insurer_invoice_suggested_total() if hasattr(self.estimate, 'get_insurer_invoice_suggested_total') else 0
                if insurer_total > 0:
                    actions.append(WorkflowAction(
                        key='create_insurer_invoice',
                        label='Create Insurer Invoice',
                        description=f'Create invoice for insurance (${insurer_total:.2f})',
                        enabled=True,
                        endpoint_hint=f'/pdr-estimates/{self.estimate.id}/invoices/insurer',
                        priority=5
                    ))

            # Customer invoice (if deductible or OOP)
            customer_total = state.deductible + state.customer_oop
            if customer_total > 0 and not state.has_customer_invoice:
                actions.append(WorkflowAction(
                    key='create_customer_invoice',
                    label='Create Customer Invoice',
                    description=f'Create invoice for customer deductible/OOP (${customer_total:.2f})',
                    enabled=True,
                    endpoint_hint=f'/pdr-estimates/{self.estimate.id}/invoices/customer',
                    priority=5
                ))

        # 5. Payment Collection Flow
        if state.invoices_count > 0 and state.invoices_balance > 0:
            actions.append(WorkflowAction(
                key='collect_payment',
                label='Collect Payment',
                description=f'Record payment (${state.invoices_balance:.2f} outstanding)',
                enabled=True,
                endpoint_hint='/invoices/{id}/payments',
                priority=6
            ))

        # 6. Close Claim Flow
        job_completed = state.job_status in ['completed', 'COMPLETED'] if state.job_status else True
        if state.all_invoices_paid and job_completed and state.invoices_count > 0:
            if state.estimate_status not in ['completed', 'invoiced']:
                actions.append(WorkflowAction(
                    key='close_claim',
                    label='Close Claim',
                    description='Mark estimate as completed and invoiced',
                    enabled=True,
                    endpoint_hint=f'/pdr-estimates/{self.estimate.id}/close',
                    priority=7
                ))
            else:
                actions.append(WorkflowAction(
                    key='claim_closed',
                    label='Claim Closed',
                    description='This claim has been completed',
                    enabled=False,
                    reason_disabled='Claim is already closed',
                    priority=10
                ))

        # Sort by priority
        actions.sort(key=lambda a: a.priority)

        return actions

    def get_workflow(self) -> Dict[str, Any]:
        """
        Get the complete workflow state and next actions.

        Returns:
            Dict with:
                - state: Current state summary
                - next_actions: List of available actions
                - primary_action: The highest priority enabled action (if any)
                - priority_score: Numeric urgency score (higher = more urgent)
                - priority_reason: Human-readable explanation of priority
        """
        state = self._compute_state()
        self._state = state
        actions = self._compute_actions(state)

        # Find primary action (first enabled action)
        primary_action = next(
            (a for a in actions if a.enabled),
            None
        )

        # Compute priority score
        priority = self._compute_priority(state, primary_action)

        return {
            'state': asdict(state),
            'next_actions': [asdict(a) for a in actions],
            'primary_action': asdict(primary_action) if primary_action else None,
            'priority_score': priority.score,
            'priority_reason': priority.reason,
            'estimate_id': self.estimate.id,
            'estimate_number': self.estimate.estimate_number,
        }


class WorkflowGuard:
    """
    Validates workflow transitions and blocks illegal actions.

    Usage:
        guard = WorkflowGuard(estimate)
        can_proceed, reason = guard.can_set_status('invoiced')
        can_proceed, reason = guard.can_issue_invoice(invoice)
    """

    def __init__(self, estimate):
        self.estimate = estimate
        self._invoices = list(estimate.invoices) if hasattr(estimate, 'invoices') else []
        self._jobs = list(estimate.jobs) if hasattr(estimate, 'jobs') else []

    def can_set_status(self, new_status: str) -> tuple:
        """
        Check if estimate status can be changed to new_status.

        Returns:
            (bool, str): (can_proceed, reason_if_blocked)
        """
        # Cannot set 'invoiced' unless at least one invoice exists
        if new_status == 'invoiced':
            active_invoices = [inv for inv in self._invoices if inv.status != 'void']
            if not active_invoices:
                return False, "Cannot mark as invoiced: no invoices exist"

        # Cannot set 'completed' if job exists but not completed
        if new_status == 'completed':
            active_jobs = [j for j in self._jobs if j.status not in ['cancelled', 'CANCELLED']]
            for job in active_jobs:
                if job.status not in ['completed', 'COMPLETED']:
                    return False, f"Cannot mark as completed: job {job.job_number} is not completed"

        return True, None

    def can_issue_invoice(self, invoice) -> tuple:
        """
        Check if an invoice can be issued.

        Returns:
            (bool, str): (can_proceed, reason_if_blocked)
        """
        # Block issuing zero-total invoices
        total = float(invoice.total or 0)
        if total <= 0:
            return False, "Cannot issue invoice with zero or negative total"

        # Must have at least one line item (optional check)
        # if not list(invoice.line_items):
        #     return False, "Cannot issue invoice without line items"

        return True, None

    def can_create_supplement(self) -> tuple:
        """
        Check if a supplement can be created.

        Returns:
            (bool, str, bool): (can_proceed, warning_message, should_log)
        """
        # Check if any invoices are paid
        paid_invoices = [
            inv for inv in self._invoices
            if inv.status == 'paid' and inv.status != 'void'
        ]

        if paid_invoices:
            return True, "Warning: Creating supplement after payment has been received", True

        return True, None, False


def get_estimate_workflow(estimate) -> Dict[str, Any]:
    """
    Convenience function to get workflow for an estimate.

    Args:
        estimate: PDREstimate instance

    Returns:
        Workflow dict with state and next_actions
    """
    service = WorkflowService(estimate)
    return service.get_workflow()


def validate_estimate_status_change(estimate, new_status: str) -> tuple:
    """
    Validate an estimate status change.

    Args:
        estimate: PDREstimate instance
        new_status: The proposed new status

    Returns:
        (bool, str): (can_proceed, reason_if_blocked)
    """
    guard = WorkflowGuard(estimate)
    return guard.can_set_status(new_status)


def validate_invoice_issue(estimate, invoice) -> tuple:
    """
    Validate that an invoice can be issued.

    Args:
        estimate: PDREstimate instance
        invoice: Invoice instance to issue

    Returns:
        (bool, str): (can_proceed, reason_if_blocked)
    """
    guard = WorkflowGuard(estimate)
    return guard.can_issue_invoice(invoice)
