"""PDR Estimate model - zone-based hail damage estimates with signature support.

Workflow:
- Customer Authorization: customer signs to authorize repair work
- Insurer Approval: insurance company approves the estimate for payment

Customer Status: draft -> pending_signature -> authorized (or declined)
Insurer Status: not_submitted -> submitted -> approved/declined/needs_revision

Locking: Estimate is locked for base edits only when insurer_status='approved'.
After insurer approval, changes must go through supplements.
"""

from datetime import datetime
from app.extensions import db


class PDREstimate(db.Model):
    """A PDR (Paintless Dent Repair) estimate with separate customer authorization and insurer approval."""
    __tablename__ = 'pdr_estimates'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Estimate identification
    estimate_number = db.Column(db.String(50), unique=True)

    # Vehicle info
    vehicle_year = db.Column(db.Integer)
    vehicle_make = db.Column(db.String(100))
    vehicle_model = db.Column(db.String(100))
    vehicle_type = db.Column(db.String(20), default='car')  # car, truck, suv
    vin = db.Column(db.String(17))
    license_plate = db.Column(db.String(20))
    color = db.Column(db.String(50))
    mileage = db.Column(db.Integer)

    # Customer/Lead linkage
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=True)
    customer_name = db.Column(db.String(255))

    # Pricing
    labor_total = db.Column(db.Numeric(12, 2), default=0)
    ri_total = db.Column(db.Numeric(12, 2), default=0)
    parts_total = db.Column(db.Numeric(12, 2), default=0)
    discount_amount = db.Column(db.Numeric(12, 2), default=0)
    discount_percent = db.Column(db.Numeric(5, 2), default=0)
    tax_rate = db.Column(db.Numeric(5, 4), default=0)
    tax_amount = db.Column(db.Numeric(12, 2), default=0)
    total_price = db.Column(db.Numeric(12, 2), default=0)

    # Insurance
    insurance_company = db.Column(db.String(255))
    claim_number = db.Column(db.String(100))
    deductible = db.Column(db.Numeric(12, 2))  # Customer deductible amount
    customer_oop = db.Column(db.Numeric(12, 2), default=0)  # Additional out-of-pocket (e.g., short-pay, betterment)
    adjuster_name = db.Column(db.String(255))
    adjuster_email = db.Column(db.String(255))
    adjuster_phone = db.Column(db.String(50))

    # Status and workflow
    status = db.Column(db.String(50), default='draft')

    # =========================================================================
    # SPLIT WORKFLOW: Customer Authorization vs Insurer Approval
    # =========================================================================

    # Customer authorization workflow (signature-based)
    # draft -> pending_signature -> authorized | declined
    customer_status = db.Column(db.String(50), default='draft')

    # Insurer approval workflow
    # not_submitted -> submitted -> approved | declined | needs_revision
    insurer_status = db.Column(db.String(50), default='not_submitted')

    # Legacy field for migration compatibility (will be populated from customer_status/insurer_status)
    approval_status = db.Column(db.String(50), default='draft')

    # Customer signature fields
    signed_at = db.Column(db.DateTime, nullable=True)
    signed_by_name = db.Column(db.String(255), nullable=True)
    signed_by_email = db.Column(db.String(255), nullable=True)
    signature_image = db.Column(db.LargeBinary, nullable=True)  # PNG bytes
    signature_meta = db.Column(db.JSON, nullable=True)  # {ip, user_agent, token_id, method}

    # Customer decline tracking
    customer_declined_at = db.Column(db.DateTime, nullable=True)
    customer_declined_reason = db.Column(db.Text, nullable=True)

    # Insurer workflow tracking
    submitted_to_insurer_at = db.Column(db.DateTime, nullable=True)
    submitted_to_insurer_by = db.Column(db.Integer, nullable=True)

    insurer_approved_at = db.Column(db.DateTime, nullable=True)
    insurer_approved_by = db.Column(db.Integer, nullable=True)  # User ID who recorded approval

    insurer_declined_at = db.Column(db.DateTime, nullable=True)
    insurer_declined_reason = db.Column(db.Text, nullable=True)

    # Insurer approval financial tracking (partial approvals)
    # Requested = total_price, Approved = insurer_approved_total
    insurer_approved_total = db.Column(db.Numeric(12, 2), nullable=True)
    insurer_approved_labor = db.Column(db.Numeric(12, 2), nullable=True)
    insurer_approved_ri = db.Column(db.Numeric(12, 2), nullable=True)
    insurer_approved_materials = db.Column(db.Numeric(12, 2), nullable=True)
    insurer_approved_tax = db.Column(db.Numeric(12, 2), nullable=True)
    insurer_approval_notes = db.Column(db.Text, nullable=True)
    insurer_approval_reference = db.Column(db.String(100), nullable=True)  # Adjuster ref ID

    # Legacy fields (kept for backward compatibility)
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by = db.Column(db.Integer, nullable=True)
    declined_at = db.Column(db.DateTime, nullable=True)
    declined_reason = db.Column(db.Text, nullable=True)

    # Notes
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)

    # Created by
    created_by = db.Column(db.Integer, nullable=True)

    # R&I Labor Rate (Stage 6E)
    ri_labor_rate = db.Column(db.Numeric(8, 2), nullable=True)  # Override rate if set
    ri_labor_rate_source = db.Column(db.String(20), nullable=True)  # 'default', 'rule', 'override'
    ri_labor_rate_rule_id = db.Column(db.String(50), nullable=True)  # ID of matched rule

    # Status constants
    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_INVOICED = 'invoiced'
    STATUS_CANCELLED = 'cancelled'

    STATUSES = [STATUS_DRAFT, STATUS_SENT, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_INVOICED, STATUS_CANCELLED]

    # Customer status constants
    CUSTOMER_DRAFT = 'draft'
    CUSTOMER_PENDING = 'pending_signature'
    CUSTOMER_AUTHORIZED = 'authorized'
    CUSTOMER_DECLINED = 'declined'

    CUSTOMER_STATUSES = [CUSTOMER_DRAFT, CUSTOMER_PENDING, CUSTOMER_AUTHORIZED, CUSTOMER_DECLINED]

    # Insurer status constants
    INSURER_NOT_SUBMITTED = 'not_submitted'
    INSURER_SUBMITTED = 'submitted'
    INSURER_APPROVED = 'approved'
    INSURER_DECLINED = 'declined'
    INSURER_NEEDS_REVISION = 'needs_revision'

    INSURER_STATUSES = [INSURER_NOT_SUBMITTED, INSURER_SUBMITTED, INSURER_APPROVED, INSURER_DECLINED, INSURER_NEEDS_REVISION]

    # Legacy approval status constants (for backward compatibility)
    APPROVAL_DRAFT = 'draft'
    APPROVAL_PENDING = 'pending_signature'
    APPROVAL_SIGNED = 'signed'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_DECLINED = 'declined'

    APPROVAL_STATUSES = [APPROVAL_DRAFT, APPROVAL_PENDING, APPROVAL_SIGNED, APPROVAL_APPROVED, APPROVAL_DECLINED]

    def generate_estimate_number(self):
        """Generate estimate number based on ID."""
        if not self.estimate_number and self.id:
            self.estimate_number = f'EST-{self.id:05d}'

    # =========================================================================
    # CUSTOMER AUTHORIZATION METHODS
    # =========================================================================

    def is_customer_authorized(self):
        """Check if customer has authorized (signed) the estimate."""
        return self.signed_at is not None and self.signature_image is not None

    def is_signed(self):
        """Alias for is_customer_authorized for backward compatibility."""
        return self.is_customer_authorized()

    def request_customer_signature(self):
        """Mark estimate as awaiting customer signature."""
        self.customer_status = self.CUSTOMER_PENDING
        self._sync_legacy_approval_status()

    def mark_customer_authorized(self, name: str, signature_bytes: bytes, email: str = None, meta: dict = None):
        """Record customer authorization signature."""
        self.signed_at = datetime.utcnow()
        self.signed_by_name = name
        self.signed_by_email = email
        self.signature_image = signature_bytes
        self.signature_meta = meta or {}
        self.customer_status = self.CUSTOMER_AUTHORIZED
        self._sync_legacy_approval_status()

    def mark_signed(self, name: str, signature_bytes: bytes, email: str = None, meta: dict = None):
        """Alias for mark_customer_authorized for backward compatibility."""
        self.mark_customer_authorized(name, signature_bytes, email, meta)

    def mark_customer_declined(self, reason: str = None):
        """Mark estimate as declined by customer."""
        self.customer_status = self.CUSTOMER_DECLINED
        self.customer_declined_at = datetime.utcnow()
        self.customer_declined_reason = reason
        self._sync_legacy_approval_status()

    # =========================================================================
    # INSURER APPROVAL METHODS
    # =========================================================================

    def is_insurer_approved(self):
        """Check if insurer has approved the estimate."""
        return self.insurer_status == self.INSURER_APPROVED

    def is_approved(self):
        """Check if insurer approved (for backward compatibility)."""
        return self.is_insurer_approved()

    def can_submit_to_insurer(self):
        """Check if estimate can be submitted to insurer."""
        # Can submit if not already approved and has some content
        return self.insurer_status in [self.INSURER_NOT_SUBMITTED, self.INSURER_NEEDS_REVISION, self.INSURER_DECLINED]

    def submit_to_insurer(self, user_id: int = None):
        """Mark estimate as submitted to insurer."""
        self.insurer_status = self.INSURER_SUBMITTED
        self.submitted_to_insurer_at = datetime.utcnow()
        self.submitted_to_insurer_by = user_id
        self._sync_legacy_approval_status()

    def mark_insurer_approved(
        self,
        user_id: int = None,
        approved_total: float = None,
        approved_labor: float = None,
        approved_ri: float = None,
        approved_materials: float = None,
        approved_tax: float = None,
        notes: str = None,
        reference: str = None
    ):
        """Mark estimate as approved by insurer with optional partial approval amounts.

        This locks the estimate for edits. After approval, changes require supplements.

        Args:
            user_id: User recording the approval
            approved_total: Total amount approved by insurer (may be less than requested)
            approved_labor: Labor portion approved (optional breakdown)
            approved_ri: R&I portion approved (optional breakdown)
            approved_materials: Materials portion approved (optional breakdown)
            approved_tax: Tax portion approved (optional breakdown)
            notes: Approval notes from adjuster
            reference: Adjuster reference ID
        """
        self.insurer_status = self.INSURER_APPROVED
        self.insurer_approved_at = datetime.utcnow()
        self.insurer_approved_by = user_id

        # Financial tracking
        if approved_total is not None:
            self.insurer_approved_total = approved_total
        if approved_labor is not None:
            self.insurer_approved_labor = approved_labor
        if approved_ri is not None:
            self.insurer_approved_ri = approved_ri
        if approved_materials is not None:
            self.insurer_approved_materials = approved_materials
        if approved_tax is not None:
            self.insurer_approved_tax = approved_tax
        if notes:
            self.insurer_approval_notes = notes
        if reference:
            self.insurer_approval_reference = reference

        # Also update legacy fields
        self.approved_at = self.insurer_approved_at
        self.approved_by = user_id
        self._sync_legacy_approval_status()

    def update_insurer_approval(
        self,
        approved_total: float = None,
        approved_labor: float = None,
        approved_ri: float = None,
        approved_materials: float = None,
        approved_tax: float = None,
        notes: str = None,
        reference: str = None
    ):
        """Update insurer approval amounts (for corrections after initial approval)."""
        if approved_total is not None:
            self.insurer_approved_total = approved_total
        if approved_labor is not None:
            self.insurer_approved_labor = approved_labor
        if approved_ri is not None:
            self.insurer_approved_ri = approved_ri
        if approved_materials is not None:
            self.insurer_approved_materials = approved_materials
        if approved_tax is not None:
            self.insurer_approved_tax = approved_tax
        if notes is not None:
            self.insurer_approval_notes = notes
        if reference is not None:
            self.insurer_approval_reference = reference

    # =========================================================================
    # FINANCIAL TRACKING HELPERS
    # =========================================================================

    def get_requested_total(self) -> float:
        """Get the total amount requested (our estimate total)."""
        return float(self.total_price) if self.total_price else 0.0

    def get_approved_total(self) -> float | None:
        """Get the insurer-approved total amount, or None if not yet approved."""
        if self.insurer_approved_total is not None:
            return float(self.insurer_approved_total)
        return None

    def get_short_paid_amount(self) -> float | None:
        """Get the short-paid amount (requested - approved).

        Returns None if not yet approved.
        Returns 0 if approved >= requested.
        Returns positive value if approved < requested.
        """
        approved = self.get_approved_total()
        if approved is None:
            return None
        requested = self.get_requested_total()
        delta = requested - approved
        return max(delta, 0.0)

    def get_approval_delta(self) -> float | None:
        """Get the difference between requested and approved (can be negative if overpaid)."""
        approved = self.get_approved_total()
        if approved is None:
            return None
        return self.get_requested_total() - approved

    def has_partial_approval(self) -> bool:
        """Check if insurer approved less than requested."""
        delta = self.get_short_paid_amount()
        return delta is not None and delta > 0

    # =========================================================================
    # SPLIT BILLING HELPERS (Deductible + Insurer Allocation)
    # =========================================================================

    def get_deductible_amount(self) -> float:
        """Get the customer deductible amount."""
        return float(self.deductible) if self.deductible else 0.0

    def get_customer_oop_amount(self) -> float:
        """Get additional customer out-of-pocket amount (beyond deductible)."""
        return float(self.customer_oop) if self.customer_oop else 0.0

    def get_customer_total(self) -> float:
        """Get total amount owed by customer (deductible + OOP)."""
        return self.get_deductible_amount() + self.get_customer_oop_amount()

    def get_insurer_invoice_suggested_total(self) -> float:
        """Calculate suggested insurer invoice amount.

        Logic:
        - If insurer_approved_total set, use (approved - deductible)
        - Otherwise use (total_price - deductible)
        - Never negative
        """
        base = self.get_approved_total()
        if base is None:
            base = self.get_requested_total()

        deductible = self.get_deductible_amount()
        return max(base - deductible, 0.0)

    def get_customer_invoice_suggested_total(self) -> float:
        """Calculate suggested customer invoice amount.

        Logic:
        - Deductible amount + any additional out-of-pocket
        """
        return self.get_customer_total()

    def get_billing_summary(self) -> dict:
        """Get a summary of billing allocations."""
        approved = self.get_approved_total()
        requested = self.get_requested_total()
        deductible = self.get_deductible_amount()
        oop = self.get_customer_oop_amount()

        return {
            'requested_total': requested,
            'approved_total': approved,
            'deductible': deductible,
            'customer_oop': oop,
            'customer_total': deductible + oop,
            'insurer_suggested': self.get_insurer_invoice_suggested_total(),
            'customer_suggested': self.get_customer_invoice_suggested_total(),
            'short_paid': self.get_short_paid_amount() or 0.0,
            'has_split_billing': deductible > 0 or oop > 0,
        }

    def mark_insurer_declined(self, reason: str = None):
        """Mark estimate as declined by insurer."""
        self.insurer_status = self.INSURER_DECLINED
        self.insurer_declined_at = datetime.utcnow()
        self.insurer_declined_reason = reason
        self._sync_legacy_approval_status()

    def mark_insurer_needs_revision(self, reason: str = None):
        """Mark estimate as needing revision per insurer."""
        self.insurer_status = self.INSURER_NEEDS_REVISION
        self.insurer_declined_at = datetime.utcnow()  # Reuse field for timestamp
        self.insurer_declined_reason = reason
        self._sync_legacy_approval_status()

    def mark_approved(self, approved_by: int = None):
        """Legacy method - now marks insurer approved."""
        self.mark_insurer_approved(approved_by)

    def mark_declined(self, reason: str = None):
        """Legacy method - marks insurer declined."""
        self.mark_insurer_declined(reason)

    def can_be_approved(self):
        """Legacy check - estimate can be insurer-approved if submitted."""
        return self.insurer_status == self.INSURER_SUBMITTED

    # =========================================================================
    # LOCKING & EDIT PROTECTION
    # =========================================================================

    def is_locked(self):
        """Check if estimate is locked for base edits.

        Estimate is locked ONLY when insurer has approved.
        Customer authorization does NOT lock the estimate.
        After insurer approval, changes must go through supplements.
        """
        return self.insurer_status == self.INSURER_APPROVED

    def can_edit(self):
        """Check if estimate can be edited (inverse of is_locked)."""
        return not self.is_locked()

    def require_supplement_for_changes(self):
        """Check if changes require a supplement (same as is_locked)."""
        return self.is_locked()

    # =========================================================================
    # STATUS SYNC & HELPERS
    # =========================================================================

    def _sync_legacy_approval_status(self):
        """Sync the legacy approval_status field for backward compatibility."""
        # Map new statuses to legacy approval_status
        if self.insurer_status == self.INSURER_APPROVED:
            self.approval_status = self.APPROVAL_APPROVED
        elif self.insurer_status == self.INSURER_DECLINED:
            self.approval_status = self.APPROVAL_DECLINED
        elif self.customer_status == self.CUSTOMER_AUTHORIZED:
            self.approval_status = self.APPROVAL_SIGNED
        elif self.customer_status == self.CUSTOMER_PENDING:
            self.approval_status = self.APPROVAL_PENDING
        elif self.customer_status == self.CUSTOMER_DECLINED:
            self.approval_status = self.APPROVAL_DECLINED
        else:
            self.approval_status = self.APPROVAL_DRAFT

    def mark_sent(self):
        """Mark estimate as sent."""
        self.status = self.STATUS_SENT
        self.sent_at = datetime.utcnow()
        if self.customer_status == self.CUSTOMER_DRAFT:
            self.customer_status = self.CUSTOMER_PENDING
        self._sync_legacy_approval_status()

    def get_signature_base64(self):
        """Get signature as base64 string for embedding in PDFs."""
        import base64
        if self.signature_image:
            return base64.b64encode(self.signature_image).decode('utf-8')
        return None

    def get_combined_status_display(self):
        """Get a human-readable combined status for display."""
        parts = []
        if self.customer_status == self.CUSTOMER_AUTHORIZED:
            parts.append('Customer Authorized')
        elif self.customer_status == self.CUSTOMER_PENDING:
            parts.append('Awaiting Customer Signature')
        elif self.customer_status == self.CUSTOMER_DECLINED:
            parts.append('Customer Declined')

        if self.insurer_status == self.INSURER_APPROVED:
            parts.append('Insurer Approved')
        elif self.insurer_status == self.INSURER_SUBMITTED:
            parts.append('Submitted to Insurer')
        elif self.insurer_status == self.INSURER_DECLINED:
            parts.append('Insurer Declined')
        elif self.insurer_status == self.INSURER_NEEDS_REVISION:
            parts.append('Needs Revision')

        return ' | '.join(parts) if parts else 'Draft'

    def to_dict(self, include_signature=False):
        """Convert to dictionary for API responses."""
        result = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'estimate_number': self.estimate_number,
            'vehicle_year': self.vehicle_year,
            'vehicle_make': self.vehicle_make,
            'vehicle_model': self.vehicle_model,
            'vehicle_type': self.vehicle_type,
            'vin': self.vin,
            'license_plate': self.license_plate,
            'color': self.color,
            'mileage': self.mileage,
            'customer_id': self.customer_id,
            'lead_id': self.lead_id,
            'customer_name': self.customer_name,
            'labor_total': float(self.labor_total) if self.labor_total else 0,
            'ri_total': float(self.ri_total) if self.ri_total else 0,
            'parts_total': float(self.parts_total) if self.parts_total else 0,
            'discount_amount': float(self.discount_amount) if self.discount_amount else 0,
            'discount_percent': float(self.discount_percent) if self.discount_percent else 0,
            'tax_rate': float(self.tax_rate) if self.tax_rate else 0,
            'tax_amount': float(self.tax_amount) if self.tax_amount else 0,
            'total_price': float(self.total_price) if self.total_price else 0,
            'insurance_company': self.insurance_company,
            'claim_number': self.claim_number,
            'deductible': float(self.deductible) if self.deductible else None,
            'customer_oop': float(self.customer_oop) if self.customer_oop else 0,
            'adjuster_name': self.adjuster_name,
            'adjuster_email': self.adjuster_email,
            'adjuster_phone': self.adjuster_phone,
            'status': self.status,

            # New split workflow fields
            'customer_status': self.customer_status,
            'insurer_status': self.insurer_status,
            'is_customer_authorized': self.is_customer_authorized(),
            'is_insurer_approved': self.is_insurer_approved(),
            'is_locked': self.is_locked(),
            'combined_status_display': self.get_combined_status_display(),

            # Customer authorization fields
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'signed_by_name': self.signed_by_name,
            'signed_by_email': self.signed_by_email,
            'customer_declined_at': self.customer_declined_at.isoformat() if self.customer_declined_at else None,
            'customer_declined_reason': self.customer_declined_reason,

            # Insurer approval fields
            'submitted_to_insurer_at': self.submitted_to_insurer_at.isoformat() if self.submitted_to_insurer_at else None,
            'submitted_to_insurer_by': self.submitted_to_insurer_by,
            'insurer_approved_at': self.insurer_approved_at.isoformat() if self.insurer_approved_at else None,
            'insurer_approved_by': self.insurer_approved_by,
            'insurer_declined_at': self.insurer_declined_at.isoformat() if self.insurer_declined_at else None,
            'insurer_declined_reason': self.insurer_declined_reason,

            # Insurer financial tracking (partial approvals)
            'requested_total': self.get_requested_total(),
            'insurer_approved_total': self.get_approved_total(),
            'insurer_approved_labor': float(self.insurer_approved_labor) if self.insurer_approved_labor else None,
            'insurer_approved_ri': float(self.insurer_approved_ri) if self.insurer_approved_ri else None,
            'insurer_approved_materials': float(self.insurer_approved_materials) if self.insurer_approved_materials else None,
            'insurer_approved_tax': float(self.insurer_approved_tax) if self.insurer_approved_tax else None,
            'insurer_approval_notes': self.insurer_approval_notes,
            'insurer_approval_reference': self.insurer_approval_reference,
            'short_paid_amount': self.get_short_paid_amount(),
            'approval_delta': self.get_approval_delta(),
            'has_partial_approval': self.has_partial_approval(),

            # Split billing fields
            'billing_summary': self.get_billing_summary(),
            'insurer_invoice_suggested': self.get_insurer_invoice_suggested_total(),
            'customer_invoice_suggested': self.get_customer_invoice_suggested_total(),

            # Legacy fields (for backward compatibility)
            'approval_status': self.approval_status,
            'is_signed': self.is_signed(),  # Legacy alias
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by,
            'declined_at': self.declined_at.isoformat() if self.declined_at else None,
            'declined_reason': self.declined_reason,

            # R&I Labor Rate (Stage 6E)
            'ri_labor_rate': float(self.ri_labor_rate) if self.ri_labor_rate else None,
            'ri_labor_rate_source': self.ri_labor_rate_source,
            'ri_labor_rate_rule_id': self.ri_labor_rate_rule_id,

            # Notes
            'notes': self.notes,
            'internal_notes': self.internal_notes,

            # Timestamps
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_by': self.created_by,
        }

        # Include signature image as base64 if requested
        if include_signature and self.signature_image:
            result['signature_base64'] = self.get_signature_base64()

        return result

    @classmethod
    def migrate_from_legacy_approval_status(cls, estimate):
        """Migrate an estimate from legacy approval_status to new split fields.

        Call this during migration or when loading old data.
        """
        if estimate.customer_status is None:
            estimate.customer_status = cls.CUSTOMER_DRAFT
        if estimate.insurer_status is None:
            estimate.insurer_status = cls.INSURER_NOT_SUBMITTED

        # Only migrate if new fields haven't been set yet
        if estimate.customer_status == cls.CUSTOMER_DRAFT and estimate.insurer_status == cls.INSURER_NOT_SUBMITTED:
            old_status = estimate.approval_status or 'draft'

            if old_status == 'approved':
                # Was approved - assume both customer authorized and insurer approved
                if estimate.signed_at:
                    estimate.customer_status = cls.CUSTOMER_AUTHORIZED
                estimate.insurer_status = cls.INSURER_APPROVED
                estimate.insurer_approved_at = estimate.approved_at
                estimate.insurer_approved_by = estimate.approved_by

            elif old_status == 'signed':
                # Customer signed but insurer not yet approved
                estimate.customer_status = cls.CUSTOMER_AUTHORIZED
                estimate.insurer_status = cls.INSURER_NOT_SUBMITTED

            elif old_status == 'pending_signature':
                estimate.customer_status = cls.CUSTOMER_PENDING
                estimate.insurer_status = cls.INSURER_NOT_SUBMITTED

            elif old_status == 'declined':
                # Assume insurer declined (more common case)
                estimate.insurer_status = cls.INSURER_DECLINED
                estimate.insurer_declined_at = estimate.declined_at
                estimate.insurer_declined_reason = estimate.declined_reason

            # else: draft - already set correctly

    def __repr__(self):
        return f'<PDREstimate {self.estimate_number} - {self.status} (customer:{self.customer_status}, insurer:{self.insurer_status})>'
