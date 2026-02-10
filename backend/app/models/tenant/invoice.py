"""Invoice and Payment models for billing PDR work.

Invoice lifecycle:
  draft -> issued -> partial_paid -> paid
                  -> void

An Invoice is created from a PDREstimate after insurer approval or job completion.
Line items capture the breakdown (PDR labor, R&I, materials, etc.).
Payments track individual receipts against the invoice.
"""

from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Invoice(db.Model):
    """An invoice for PDR work, linked to an estimate."""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, nullable=False, index=True)

    # Invoice identification
    invoice_number = db.Column(db.String(50), nullable=False)

    # Links to source
    estimate_id = db.Column(db.Integer, db.ForeignKey('pdr_estimates.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=True, index=True)

    # Payer info
    payer_type = db.Column(db.String(20), default='customer')  # customer, insurer, dealership, other
    payer_name = db.Column(db.String(255), nullable=True)
    allocation_type = db.Column(db.String(30), default='other')  # insurer, customer_deductible, customer_oop, other

    # Status
    status = db.Column(db.String(20), default='draft')  # draft, issued, partial_paid, paid, void

    # Totals
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    tax_rate = db.Column(db.Numeric(5, 4), default=0)
    tax_total = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)

    # Payment tracking
    amount_paid = db.Column(db.Numeric(12, 2), default=0)

    # Dates
    issued_at = db.Column(db.DateTime, nullable=True)
    due_at = db.Column(db.DateTime, nullable=True)

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)

    # Relationships
    estimate = db.relationship('PDREstimate', backref=db.backref('invoices', lazy='dynamic'))
    job = db.relationship('Job', backref=db.backref('invoices', lazy='dynamic'))
    line_items = db.relationship('InvoiceLineItem', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')

    # Unique constraint per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'invoice_number', name='uq_tenant_invoice_number'),
    )

    # Status constants
    STATUS_DRAFT = 'draft'
    STATUS_ISSUED = 'issued'
    STATUS_PARTIAL_PAID = 'partial_paid'
    STATUS_PAID = 'paid'
    STATUS_VOID = 'void'

    STATUSES = [STATUS_DRAFT, STATUS_ISSUED, STATUS_PARTIAL_PAID, STATUS_PAID, STATUS_VOID]

    # Payer type constants
    PAYER_CUSTOMER = 'customer'
    PAYER_INSURER = 'insurer'
    PAYER_DEALERSHIP = 'dealership'
    PAYER_OTHER = 'other'

    PAYER_TYPES = [PAYER_CUSTOMER, PAYER_INSURER, PAYER_DEALERSHIP, PAYER_OTHER]

    # Allocation type constants (for split billing)
    ALLOCATION_INSURER = 'insurer'
    ALLOCATION_CUSTOMER_DEDUCTIBLE = 'customer_deductible'
    ALLOCATION_CUSTOMER_OOP = 'customer_oop'
    ALLOCATION_OTHER = 'other'

    ALLOCATION_TYPES = [ALLOCATION_INSURER, ALLOCATION_CUSTOMER_DEDUCTIBLE, ALLOCATION_CUSTOMER_OOP, ALLOCATION_OTHER]

    def generate_invoice_number(self, sequence: int = None):
        """Generate invoice number based on ID or sequence."""
        if sequence is not None:
            self.invoice_number = f'INV-{sequence:05d}'
        elif self.id:
            self.invoice_number = f'INV-{self.id:05d}'

    @property
    def balance_due(self) -> Decimal:
        """Calculate remaining balance."""
        total = Decimal(str(self.total)) if self.total else Decimal('0')
        paid = Decimal(str(self.amount_paid)) if self.amount_paid else Decimal('0')
        return max(total - paid, Decimal('0'))

    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.balance_due <= Decimal('0.005')

    def is_overdue(self) -> bool:
        """Check if invoice is past due date."""
        if not self.due_at or self.status in [self.STATUS_PAID, self.STATUS_VOID]:
            return False
        return datetime.utcnow() > self.due_at

    def can_issue(self) -> bool:
        """Check if invoice can be issued."""
        return self.status == self.STATUS_DRAFT

    def can_void(self) -> bool:
        """Check if invoice can be voided."""
        return self.status in [self.STATUS_DRAFT, self.STATUS_ISSUED]

    def can_accept_payment(self) -> bool:
        """Check if invoice can accept payments."""
        return self.status in [self.STATUS_ISSUED, self.STATUS_PARTIAL_PAID]

    def issue(self):
        """Issue the invoice."""
        if self.can_issue():
            self.status = self.STATUS_ISSUED
            self.issued_at = datetime.utcnow()

    def void(self):
        """Void the invoice."""
        if self.can_void():
            self.status = self.STATUS_VOID

    def recalculate_totals(self):
        """Recalculate subtotal, tax, and total from line items."""
        subtotal = Decimal('0')
        for item in self.line_items:
            subtotal += Decimal(str(item.total)) if item.total else Decimal('0')

        self.subtotal = subtotal
        self.tax_total = subtotal * Decimal(str(self.tax_rate)) if self.tax_rate else Decimal('0')
        self.total = self.subtotal + self.tax_total

    def recalculate_payment_status(self):
        """Recalculate amount_paid and status based on payments."""
        total_paid = Decimal('0')
        for payment in self.payments:
            total_paid += Decimal(str(payment.amount)) if payment.amount else Decimal('0')

        self.amount_paid = total_paid

        # Update status based on payment
        if self.status not in [self.STATUS_DRAFT, self.STATUS_VOID]:
            if self.is_paid():
                self.status = self.STATUS_PAID
            elif total_paid > Decimal('0'):
                self.status = self.STATUS_PARTIAL_PAID
            else:
                self.status = self.STATUS_ISSUED

    @classmethod
    def create_from_estimate(cls, estimate, user_id=None, job_id=None, payer_type='insurer', allocation_type=None):
        """
        Create an invoice from a PDR estimate.

        Args:
            estimate: PDREstimate instance
            user_id: User creating the invoice
            job_id: Optional job ID if created from job
            payer_type: Who is paying (customer, insurer, etc.)
            allocation_type: Allocation type for split billing

        Returns:
            New Invoice instance (not yet committed)
        """
        # Default allocation type based on payer type
        if allocation_type is None:
            allocation_type = cls.ALLOCATION_INSURER if payer_type == 'insurer' else cls.ALLOCATION_OTHER

        invoice = cls(
            tenant_id=estimate.tenant_id,
            estimate_id=estimate.id,
            job_id=job_id,
            payer_type=payer_type,
            payer_name=estimate.insurance_company if payer_type == 'insurer' else estimate.customer_name,
            allocation_type=allocation_type,
            status=cls.STATUS_DRAFT,
            tax_rate=estimate.tax_rate or Decimal('0'),
            created_by=user_id
        )

        return invoice

    @classmethod
    def create_insurer_invoice(cls, estimate, user_id=None, job_id=None):
        """
        Create an insurer invoice from an approved PDR estimate.

        Total is set to insurer_approved_total minus deductible.

        Args:
            estimate: PDREstimate instance (must be insurer-approved)
            user_id: User creating the invoice
            job_id: Optional job ID

        Returns:
            New Invoice instance (not yet committed)
        """
        invoice = cls(
            tenant_id=estimate.tenant_id,
            estimate_id=estimate.id,
            job_id=job_id,
            payer_type=cls.PAYER_INSURER,
            payer_name=estimate.insurance_company,
            allocation_type=cls.ALLOCATION_INSURER,
            status=cls.STATUS_DRAFT,
            tax_rate=estimate.tax_rate or Decimal('0'),
            total=Decimal(str(estimate.get_insurer_invoice_suggested_total())),
            subtotal=Decimal(str(estimate.get_insurer_invoice_suggested_total())),
            created_by=user_id
        )
        return invoice

    @classmethod
    def create_customer_invoice(cls, estimate, user_id=None, job_id=None, include_oop=True):
        """
        Create a customer invoice for deductible (and optionally OOP) from a PDR estimate.

        Total is set to deductible + customer_oop.

        Args:
            estimate: PDREstimate instance
            user_id: User creating the invoice
            job_id: Optional job ID
            include_oop: Include out-of-pocket amount (default True)

        Returns:
            New Invoice instance (not yet committed)
        """
        deductible = estimate.get_deductible_amount()
        oop = estimate.get_customer_oop_amount() if include_oop else 0
        total = deductible + oop

        invoice = cls(
            tenant_id=estimate.tenant_id,
            estimate_id=estimate.id,
            job_id=job_id,
            payer_type=cls.PAYER_CUSTOMER,
            payer_name=estimate.customer_name,
            allocation_type=cls.ALLOCATION_CUSTOMER_DEDUCTIBLE,
            status=cls.STATUS_DRAFT,
            tax_rate=Decimal('0'),  # No tax on deductible typically
            total=Decimal(str(total)),
            subtotal=Decimal(str(total)),
            created_by=user_id
        )
        return invoice

    def to_dict(self, include_items=False, include_payments=False, include_estimate=False):
        """Convert to dictionary for API responses."""
        result = {
            'id': self.id,
            'tenant_id': self.tenant_id,
            'invoice_number': self.invoice_number,
            'estimate_id': self.estimate_id,
            'job_id': self.job_id,
            'payer_type': self.payer_type,
            'payer_name': self.payer_name,
            'allocation_type': self.allocation_type,
            'status': self.status,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'tax_rate': float(self.tax_rate) if self.tax_rate else 0,
            'tax_total': float(self.tax_total) if self.tax_total else 0,
            'total': float(self.total) if self.total else 0,
            'amount_paid': float(self.amount_paid) if self.amount_paid else 0,
            'balance_due': float(self.balance_due),
            'is_paid': self.is_paid(),
            'is_overdue': self.is_overdue(),
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'due_at': self.due_at.isoformat() if self.due_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }

        if include_items:
            result['line_items'] = [item.to_dict() for item in self.line_items]

        if include_payments:
            result['payments'] = [p.to_dict() for p in self.payments]

        if include_estimate and self.estimate:
            result['estimate'] = {
                'id': self.estimate.id,
                'estimate_number': self.estimate.estimate_number,
                'customer_name': self.estimate.customer_name,
                'vehicle_year': self.estimate.vehicle_year,
                'vehicle_make': self.estimate.vehicle_make,
                'vehicle_model': self.estimate.vehicle_model,
                'vehicle_display': f"{self.estimate.vehicle_year or ''} {self.estimate.vehicle_make or ''} {self.estimate.vehicle_model or ''}".strip(),
                'insurer_status': self.estimate.insurer_status,
                'total_price': float(self.estimate.total_price) if self.estimate.total_price else 0,
                'insurer_approved_total': float(self.estimate.insurer_approved_total) if self.estimate.insurer_approved_total else None,
            }

        return result

    def __repr__(self):
        return f'<Invoice {self.invoice_number} - {self.status} (${self.total})>'


class InvoiceLineItem(db.Model):
    """A line item on an invoice."""
    __tablename__ = 'invoice_line_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)

    # Category
    category = db.Column(db.String(50), default='pdr')  # pdr, ri, materials, parts, sublet, other

    # Details
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1)
    unit_price = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Category constants
    CATEGORY_PDR = 'pdr'
    CATEGORY_RI = 'ri'
    CATEGORY_MATERIALS = 'materials'
    CATEGORY_PARTS = 'parts'
    CATEGORY_SUBLET = 'sublet'
    CATEGORY_OTHER = 'other'

    CATEGORIES = [CATEGORY_PDR, CATEGORY_RI, CATEGORY_MATERIALS, CATEGORY_PARTS, CATEGORY_SUBLET, CATEGORY_OTHER]

    def calculate_total(self):
        """Calculate line item total from quantity and unit price."""
        qty = Decimal(str(self.quantity)) if self.quantity else Decimal('1')
        price = Decimal(str(self.unit_price)) if self.unit_price else Decimal('0')
        self.total = qty * price

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'category': self.category,
            'description': self.description,
            'quantity': float(self.quantity) if self.quantity else 1,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'total': float(self.total) if self.total else 0,
        }

    def __repr__(self):
        return f'<InvoiceLineItem {self.description} - ${self.total}>'


class Payment(db.Model):
    """A payment received against an invoice."""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)

    # Payment details
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    method = db.Column(db.String(20), default='check')  # cash, card, check, ach, other
    reference = db.Column(db.String(100), nullable=True)  # Check number, transaction ID, etc.

    # Timing
    received_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Notes
    notes = db.Column(db.Text, nullable=True)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, nullable=True)

    # Method constants
    METHOD_CASH = 'cash'
    METHOD_CARD = 'card'
    METHOD_CHECK = 'check'
    METHOD_ACH = 'ach'
    METHOD_OTHER = 'other'

    METHODS = [METHOD_CASH, METHOD_CARD, METHOD_CHECK, METHOD_ACH, METHOD_OTHER]

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'amount': float(self.amount) if self.amount else 0,
            'method': self.method,
            'reference': self.reference,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
        }

    def __repr__(self):
        return f'<Payment ${self.amount} via {self.method}>'
