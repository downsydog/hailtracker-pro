"""
Receipt PDF Generator Service
==============================

Generates professional receipt PDFs for payments.
Simple, clean 1-page receipts suitable for customer records.
"""

from io import BytesIO
from datetime import datetime
from decimal import Decimal
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


class ReceiptPDFGenerator:
    """Generates payment receipt PDFs."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReceiptTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=6,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e40af')
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='ReceiptSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#6b7280'),
            spaceAfter=12
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#374151'),
            borderPadding=4
        ))

        # Label style
        self.styles.add(ParagraphStyle(
            name='Label',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280')
        ))

        # Value style
        self.styles.add(ParagraphStyle(
            name='Value',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))

        # Amount style (large, bold)
        self.styles.add(ParagraphStyle(
            name='Amount',
            parent=self.styles['Normal'],
            fontSize=24,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            textColor=colors.HexColor('#059669'),
            spaceBefore=12,
            spaceAfter=12
        ))

        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#9ca3af'),
            alignment=TA_CENTER,
            spaceBefore=24
        ))

    def _format_currency(self, amount) -> str:
        """Format amount as currency."""
        if amount is None:
            return '$0.00'
        if isinstance(amount, Decimal):
            amount = float(amount)
        return f'${amount:,.2f}'

    def _format_date(self, dt) -> str:
        """Format datetime for display."""
        if dt is None:
            return 'N/A'
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        return dt.strftime('%B %d, %Y at %I:%M %p')

    def _format_date_short(self, dt) -> str:
        """Format datetime for short display."""
        if dt is None:
            return 'N/A'
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        return dt.strftime('%m/%d/%Y')

    def generate_receipt(
        self,
        payment: dict,
        invoice: dict,
        estimate: Optional[dict] = None,
        company_name: str = 'HailTracker PDR',
        company_address: Optional[str] = None,
        company_phone: Optional[str] = None,
        collected_by: Optional[str] = None
    ) -> bytes:
        """
        Generate a receipt PDF for a payment.

        Args:
            payment: Payment dictionary with amount, method, reference, etc.
            invoice: Invoice dictionary with invoice_number, total, etc.
            estimate: Optional estimate dictionary
            company_name: Business name to display
            company_address: Optional company address
            company_phone: Optional company phone
            collected_by: Name of user who collected payment

        Returns:
            PDF bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        elements = []

        # =====================================================================
        # HEADER
        # =====================================================================

        # Company name
        elements.append(Paragraph(company_name, self.styles['ReceiptTitle']))

        # Company contact info
        contact_parts = []
        if company_address:
            contact_parts.append(company_address)
        if company_phone:
            contact_parts.append(company_phone)
        if contact_parts:
            elements.append(Paragraph(' | '.join(contact_parts), self.styles['ReceiptSubtitle']))

        elements.append(Spacer(1, 0.25 * inch))

        # Receipt title
        elements.append(Paragraph('PAYMENT RECEIPT', self.styles['SectionHeader']))

        # Receipt number and date
        receipt_info = [
            ['Receipt #:', str(payment.get('id', 'N/A'))],
            ['Date:', self._format_date(payment.get('received_at') or payment.get('created_at'))],
        ]

        receipt_table = Table(receipt_info, colWidths=[1.5 * inch, 3 * inch])
        receipt_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(receipt_table)

        elements.append(Spacer(1, 0.25 * inch))

        # =====================================================================
        # PAYMENT AMOUNT (prominent display)
        # =====================================================================

        elements.append(Paragraph(
            self._format_currency(payment.get('amount', 0)),
            self.styles['Amount']
        ))

        elements.append(Paragraph(
            f"Payment received via {self._get_method_label(payment.get('method', 'other'))}",
            self.styles['ReceiptSubtitle']
        ))

        if payment.get('reference'):
            elements.append(Paragraph(
                f"Reference: {payment.get('reference')}",
                self.styles['ReceiptSubtitle']
            ))

        elements.append(Spacer(1, 0.25 * inch))

        # =====================================================================
        # INVOICE DETAILS
        # =====================================================================

        elements.append(Paragraph('Invoice Details', self.styles['SectionHeader']))

        # Build invoice info table
        invoice_data = [
            ['Invoice Number:', invoice.get('invoice_number', 'N/A')],
            ['Payer:', f"{self._get_payer_label(invoice.get('payer_type'))} - {invoice.get('payer_name', 'N/A')}"],
        ]

        if estimate:
            invoice_data.append(['Estimate:', estimate.get('estimate_number', f"#{estimate.get('id', 'N/A')}")])
            vehicle = f"{estimate.get('vehicle_year', '')} {estimate.get('vehicle_make', '')} {estimate.get('vehicle_model', '')}".strip()
            if vehicle:
                invoice_data.append(['Vehicle:', vehicle])
            if estimate.get('customer_name'):
                invoice_data.append(['Customer:', estimate.get('customer_name')])

        invoice_table = Table(invoice_data, colWidths=[1.5 * inch, 4.5 * inch])
        invoice_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(invoice_table)

        elements.append(Spacer(1, 0.25 * inch))

        # =====================================================================
        # PAYMENT SUMMARY
        # =====================================================================

        elements.append(Paragraph('Payment Summary', self.styles['SectionHeader']))

        invoice_total = float(invoice.get('total', 0) or 0)
        amount_paid_before = float(invoice.get('amount_paid', 0) or 0) - float(payment.get('amount', 0) or 0)
        this_payment = float(payment.get('amount', 0) or 0)
        balance_after = invoice_total - float(invoice.get('amount_paid', 0) or 0)

        summary_data = [
            ['Invoice Total:', self._format_currency(invoice_total)],
            ['Previously Paid:', self._format_currency(max(0, amount_paid_before))],
            ['This Payment:', self._format_currency(this_payment)],
            ['', ''],  # Separator row
            ['Balance Due:', self._format_currency(max(0, balance_after))],
        ]

        summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            # Line before balance
            ('LINEABOVE', (0, 4), (-1, 4), 1, colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 4), (-1, 4), 8),
            # Highlight balance row
            ('FONTSIZE', (0, 4), (-1, 4), 12),
            ('TEXTCOLOR', (1, 4), (1, 4), colors.HexColor('#059669') if balance_after <= 0 else colors.HexColor('#dc2626')),
        ]))
        elements.append(summary_table)

        # Paid in full badge
        if balance_after <= 0:
            elements.append(Spacer(1, 0.25 * inch))
            elements.append(Paragraph(
                '<b>PAID IN FULL</b>',
                ParagraphStyle(
                    'PaidInFull',
                    parent=self.styles['Normal'],
                    fontSize=14,
                    fontName='Helvetica-Bold',
                    alignment=TA_CENTER,
                    textColor=colors.HexColor('#059669'),
                    backColor=colors.HexColor('#d1fae5'),
                    borderPadding=8
                )
            ))

        # =====================================================================
        # NOTES
        # =====================================================================

        if payment.get('notes'):
            elements.append(Spacer(1, 0.25 * inch))
            elements.append(Paragraph('Notes', self.styles['SectionHeader']))
            elements.append(Paragraph(payment.get('notes'), self.styles['Normal']))

        # =====================================================================
        # FOOTER
        # =====================================================================

        elements.append(Spacer(1, 0.5 * inch))

        footer_parts = []
        if collected_by:
            footer_parts.append(f"Collected by: {collected_by}")
        footer_parts.append(f"Receipt generated: {datetime.now().strftime('%m/%d/%Y %I:%M %p')}")

        elements.append(Paragraph(' | '.join(footer_parts), self.styles['Footer']))
        elements.append(Paragraph(
            'Thank you for your payment. Please retain this receipt for your records.',
            self.styles['Footer']
        ))

        # Build PDF
        doc.build(elements)

        buffer.seek(0)
        return buffer.getvalue()

    def _get_method_label(self, method: str) -> str:
        """Get display label for payment method."""
        labels = {
            'cash': 'Cash',
            'card': 'Credit/Debit Card',
            'check': 'Check',
            'ach': 'ACH Transfer',
            'other': 'Other'
        }
        return labels.get(method, method.title() if method else 'Unknown')

    def _get_payer_label(self, payer_type: str) -> str:
        """Get display label for payer type."""
        labels = {
            'customer': 'Customer',
            'insurer': 'Insurance',
            'dealership': 'Dealership',
            'other': 'Other'
        }
        return labels.get(payer_type, payer_type.title() if payer_type else 'Unknown')


# Singleton instance
_generator = None


def get_receipt_generator() -> ReceiptPDFGenerator:
    """Get the receipt PDF generator singleton."""
    global _generator
    if _generator is None:
        _generator = ReceiptPDFGenerator()
    return _generator


def generate_payment_receipt(
    payment: dict,
    invoice: dict,
    estimate: dict = None,
    company_name: str = 'HailTracker PDR',
    company_address: str = None,
    company_phone: str = None,
    collected_by: str = None
) -> bytes:
    """
    Convenience function to generate a payment receipt PDF.

    Args:
        payment: Payment dictionary
        invoice: Invoice dictionary
        estimate: Optional estimate dictionary
        company_name: Business name
        company_address: Optional address
        company_phone: Optional phone
        collected_by: Name of collector

    Returns:
        PDF bytes
    """
    generator = get_receipt_generator()
    return generator.generate_receipt(
        payment=payment,
        invoice=invoice,
        estimate=estimate,
        company_name=company_name,
        company_address=company_address,
        company_phone=company_phone,
        collected_by=collected_by
    )
