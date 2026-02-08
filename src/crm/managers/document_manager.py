"""
Document Manager
Professional PDF generation for estimates, invoices, and work orders

PDR CRM Part 12 - Document Generation!

FEATURES:
- Generate professional PDF estimates
- Generate invoices with payment details
- Generate work orders for technicians
- Company branding/customization
- HTML-to-PDF conversion approach
- Document storage and retrieval
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
import os
import json


class DocumentManager:
    """
    Generate professional PDF documents for PDR operations

    Uses HTML templates converted to PDF for professional output
    """

    # Default company information (can be overridden in config)
    DEFAULT_COMPANY = {
        'name': 'HailTracker Pro PDR',
        'address': '123 Main Street',
        'city': 'Dallas',
        'state': 'TX',
        'zip': '75001',
        'phone': '(214) 555-0100',
        'email': 'info@hailtrackerpdpr.com',
        'website': 'www.hailtrackerpdr.com',
        'logo_path': None,
        'tax_id': '12-3456789'
    }

    # Document types
    DOCUMENT_TYPES = ['ESTIMATE', 'INVOICE', 'WORK_ORDER', 'RECEIPT']

    def __init__(self, db, company_info: Optional[Dict] = None, output_dir: str = 'documents'):
        """
        Initialize document manager

        Args:
            db: Database connection
            company_info: Override default company information
            output_dir: Directory to store generated documents
        """
        self.db = db
        self.company = {**self.DEFAULT_COMPANY, **(company_info or {})}
        self.output_dir = output_dir

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'estimates'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'invoices'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'work_orders'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'receipts'), exist_ok=True)

    # ========================================================================
    # CSS STYLES
    # ========================================================================

    def _get_base_styles(self) -> str:
        """Return base CSS styles for all documents"""
        return """
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.4;
                color: #333;
                padding: 40px;
            }

            .header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 3px solid #2563eb;
            }

            .company-info {
                flex: 1;
            }

            .company-name {
                font-size: 24pt;
                font-weight: bold;
                color: #1e40af;
                margin-bottom: 5px;
            }

            .company-details {
                font-size: 10pt;
                color: #666;
                line-height: 1.6;
            }

            .document-info {
                text-align: right;
                min-width: 200px;
            }

            .document-type {
                font-size: 20pt;
                font-weight: bold;
                color: #1e40af;
                margin-bottom: 10px;
            }

            .document-number {
                font-size: 12pt;
                font-weight: bold;
                color: #333;
            }

            .document-date {
                font-size: 10pt;
                color: #666;
                margin-top: 5px;
            }

            .parties {
                display: flex;
                justify-content: space-between;
                margin-bottom: 30px;
            }

            .party-box {
                width: 48%;
                padding: 15px;
                background: #f8fafc;
                border-radius: 8px;
            }

            .party-label {
                font-size: 9pt;
                text-transform: uppercase;
                color: #666;
                margin-bottom: 8px;
                font-weight: bold;
            }

            .party-name {
                font-size: 12pt;
                font-weight: bold;
                color: #333;
                margin-bottom: 5px;
            }

            .party-details {
                font-size: 10pt;
                color: #666;
                line-height: 1.5;
            }

            .vehicle-info {
                background: #f0f9ff;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 30px;
                border-left: 4px solid #2563eb;
            }

            .vehicle-label {
                font-size: 9pt;
                text-transform: uppercase;
                color: #666;
                margin-bottom: 8px;
                font-weight: bold;
            }

            .vehicle-description {
                font-size: 14pt;
                font-weight: bold;
                color: #1e40af;
            }

            .vehicle-details {
                font-size: 10pt;
                color: #666;
                margin-top: 5px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }

            th {
                background: #1e40af;
                color: white;
                padding: 12px 10px;
                text-align: left;
                font-size: 10pt;
                text-transform: uppercase;
            }

            th:last-child {
                text-align: right;
            }

            td {
                padding: 10px;
                border-bottom: 1px solid #e2e8f0;
                font-size: 10pt;
            }

            td:last-child {
                text-align: right;
            }

            .item-description {
                font-weight: 500;
            }

            .item-type {
                font-size: 9pt;
                color: #666;
                text-transform: uppercase;
            }

            tr:nth-child(even) {
                background: #f8fafc;
            }

            .totals {
                margin-top: 20px;
                display: flex;
                justify-content: flex-end;
            }

            .totals-table {
                width: 300px;
            }

            .totals-table td {
                padding: 8px 10px;
                border: none;
            }

            .totals-table tr:last-child {
                background: #1e40af;
                color: white;
                font-weight: bold;
                font-size: 14pt;
            }

            .totals-table tr:last-child td {
                padding: 12px 10px;
            }

            .notes {
                margin-top: 30px;
                padding: 15px;
                background: #fffbeb;
                border-radius: 8px;
                border-left: 4px solid #f59e0b;
            }

            .notes-label {
                font-size: 9pt;
                text-transform: uppercase;
                color: #92400e;
                margin-bottom: 8px;
                font-weight: bold;
            }

            .notes-content {
                font-size: 10pt;
                color: #78350f;
                line-height: 1.5;
            }

            .terms {
                margin-top: 30px;
                padding: 15px;
                background: #f8fafc;
                border-radius: 8px;
            }

            .terms-label {
                font-size: 9pt;
                text-transform: uppercase;
                color: #666;
                margin-bottom: 8px;
                font-weight: bold;
            }

            .terms-content {
                font-size: 9pt;
                color: #666;
                line-height: 1.5;
            }

            .footer {
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e2e8f0;
                text-align: center;
                font-size: 9pt;
                color: #666;
            }

            .signature-section {
                margin-top: 40px;
                display: flex;
                justify-content: space-between;
            }

            .signature-box {
                width: 45%;
            }

            .signature-line {
                border-top: 1px solid #333;
                margin-top: 50px;
                padding-top: 5px;
                font-size: 10pt;
            }

            .status-badge {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 10pt;
                font-weight: bold;
                text-transform: uppercase;
            }

            .status-draft { background: #fef3c7; color: #92400e; }
            .status-sent { background: #dbeafe; color: #1e40af; }
            .status-approved { background: #d1fae5; color: #065f46; }
            .status-paid { background: #d1fae5; color: #065f46; }
            .status-pending { background: #fef3c7; color: #92400e; }
            .status-overdue { background: #fee2e2; color: #991b1b; }

            .payment-info {
                background: #d1fae5;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #10b981;
            }

            .payment-label {
                font-size: 9pt;
                text-transform: uppercase;
                color: #065f46;
                margin-bottom: 5px;
                font-weight: bold;
            }

            .payment-amount {
                font-size: 18pt;
                font-weight: bold;
                color: #065f46;
            }

            .balance-due {
                background: #fee2e2;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #ef4444;
            }

            .balance-label {
                font-size: 9pt;
                text-transform: uppercase;
                color: #991b1b;
                margin-bottom: 5px;
                font-weight: bold;
            }

            .balance-amount {
                font-size: 18pt;
                font-weight: bold;
                color: #991b1b;
            }

            .work-order-section {
                margin-bottom: 25px;
            }

            .section-title {
                font-size: 12pt;
                font-weight: bold;
                color: #1e40af;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 2px solid #e2e8f0;
            }

            .checklist {
                list-style: none;
                padding: 0;
            }

            .checklist li {
                padding: 8px 0;
                padding-left: 30px;
                position: relative;
                border-bottom: 1px solid #e2e8f0;
            }

            .checklist li:before {
                content: '☐';
                position: absolute;
                left: 5px;
                font-size: 14pt;
            }

            .damage-map {
                background: #f8fafc;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                margin-bottom: 20px;
            }

            .tech-notes {
                background: #fff;
                border: 2px dashed #cbd5e1;
                padding: 15px;
                min-height: 100px;
                border-radius: 8px;
            }

            @media print {
                body {
                    padding: 20px;
                }

                .header {
                    margin-bottom: 20px;
                }
            }
        </style>
        """

    # ========================================================================
    # ESTIMATE GENERATION
    # ========================================================================

    def generate_estimate_html(self, estimate_id: int) -> str:
        """
        Generate HTML for an estimate document

        Args:
            estimate_id: The estimate ID

        Returns:
            HTML string for the estimate
        """
        # Get estimate data
        estimate = self.db.execute("""
            SELECT e.*, j.job_number, j.damage_type,
                   c.first_name, c.last_name, c.email, c.phone,
                   c.street_address, c.city, c.state, c.zip_code,
                   v.year, v.make, v.model, v.color, v.vin, v.license_plate
            FROM estimates e
            JOIN jobs j ON e.job_id = j.id
            JOIN customers c ON j.customer_id = c.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE e.id = ?
        """, (estimate_id,))

        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        est = estimate[0]

        # Parse line items from JSON
        items = json.loads(est.get('line_items') or '[]')

        # Build HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Estimate {est['estimate_number']}</title>
            {self._get_base_styles()}
        </head>
        <body>
            <div class="header">
                <div class="company-info">
                    <div class="company-name">{self.company['name']}</div>
                    <div class="company-details">
                        {self.company['address']}<br>
                        {self.company['city']}, {self.company['state']} {self.company['zip']}<br>
                        {self.company['phone']}<br>
                        {self.company['email']}
                    </div>
                </div>
                <div class="document-info">
                    <div class="document-type">ESTIMATE</div>
                    <div class="document-number">{est['estimate_number']}</div>
                    <div class="document-date">Date: {self._format_date(est.get('created_date') or est.get('estimate_date', ''))}</div>
                    <div class="document-date">Expires: {self._format_date(est['expires_date'])}</div>
                    <br>
                    <span class="status-badge status-{est['status'].lower()}">{est['status']}</span>
                </div>
            </div>

            <div class="parties">
                <div class="party-box">
                    <div class="party-label">Prepared For</div>
                    <div class="party-name">{est['first_name']} {est['last_name']}</div>
                    <div class="party-details">
                        {est['street_address'] or ''}<br>
                        {est['city'] or ''}{', ' + est['state'] if est['state'] else ''} {est['zip_code'] or ''}<br>
                        {est['phone'] or ''}<br>
                        {est['email'] or ''}
                    </div>
                </div>
                <div class="party-box">
                    <div class="party-label">Job Information</div>
                    <div class="party-name">Job #{est['job_number']}</div>
                    <div class="party-details">
                        Damage Type: {est['damage_type'] or 'N/A'}
                    </div>
                </div>
            </div>

            <div class="vehicle-info">
                <div class="vehicle-label">Vehicle</div>
                <div class="vehicle-description">{est['year']} {est['make']} {est['model']}</div>
                <div class="vehicle-details">
                    Color: {est['color'] or 'N/A'} |
                    VIN: {est['vin'] or 'N/A'} |
                    Plate: {est['license_plate'] or 'N/A'}
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th style="width: 50%">Description</th>
                        <th style="width: 15%">Type</th>
                        <th style="width: 10%">Qty</th>
                        <th style="width: 12%">Unit Price</th>
                        <th style="width: 13%">Amount</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Add line items
        for item in items:
            qty = item.get('quantity', 1)
            price = item.get('unit_price', 0)
            amount = qty * price
            html += f"""
                    <tr>
                        <td class="item-description">{item.get('description', '')}</td>
                        <td class="item-type">{item.get('type', 'ITEM')}</td>
                        <td>{qty}</td>
                        <td>${price:,.2f}</td>
                        <td>${amount:,.2f}</td>
                    </tr>
            """

        html += f"""
                </tbody>
            </table>

            <div class="totals">
                <table class="totals-table">
                    <tr>
                        <td>Subtotal:</td>
                        <td>${est['subtotal']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>Tax ({(est['tax_rate'] or 0) * 100:.2f}%):</td>
                        <td>${est['tax_amount']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>TOTAL:</td>
                        <td>${est['total']:,.2f}</td>
                    </tr>
                </table>
            </div>
        """

        # Add notes if present
        if est.get('notes'):
            html += f"""
            <div class="notes">
                <div class="notes-label">Notes</div>
                <div class="notes-content">{est['notes']}</div>
            </div>
            """

        # Add terms if present
        if est.get('terms'):
            html += f"""
            <div class="terms">
                <div class="terms-label">Terms & Conditions</div>
                <div class="terms-content">{est['terms']}</div>
            </div>
            """

        # Signature section
        html += """
            <div class="signature-section">
                <div class="signature-box">
                    <div class="signature-line">Customer Signature</div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">Date</div>
                </div>
            </div>
        """

        # Footer
        html += f"""
            <div class="footer">
                Thank you for choosing {self.company['name']}!<br>
                {self.company['website']}
            </div>
        </body>
        </html>
        """

        return html

    def generate_estimate_pdf(self, estimate_id: int) -> Dict[str, Any]:
        """
        Generate a PDF estimate document

        Args:
            estimate_id: The estimate ID

        Returns:
            Dict with file_path, html_content, estimate_number
        """
        html = self.generate_estimate_html(estimate_id)

        # Get estimate number for filename
        estimate = self.db.execute(
            "SELECT estimate_number FROM estimates WHERE id = ?",
            (estimate_id,)
        )
        estimate_number = estimate[0]['estimate_number'] if estimate else f"EST-{estimate_id}"

        # Save HTML (PDF conversion would use weasyprint, pdfkit, or similar)
        filename = f"{estimate_number}.html"
        filepath = os.path.join(self.output_dir, 'estimates', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        # Record document generation
        self._record_document('ESTIMATE', estimate_id, filepath)

        print(f"  Generated estimate: {filepath}")

        return {
            'file_path': filepath,
            'html_content': html,
            'estimate_number': estimate_number,
            'document_type': 'ESTIMATE'
        }

    # ========================================================================
    # INVOICE GENERATION
    # ========================================================================

    def generate_invoice_html(self, invoice_id: int) -> str:
        """
        Generate HTML for an invoice document

        Args:
            invoice_id: The invoice ID

        Returns:
            HTML string for the invoice
        """
        # Get invoice data
        invoice = self.db.execute("""
            SELECT i.*, j.job_number, j.damage_type,
                   c.first_name, c.last_name, c.email, c.phone,
                   c.street_address, c.city, c.state, c.zip_code,
                   v.year, v.make, v.model, v.color, v.vin, v.license_plate
            FROM invoices i
            JOIN jobs j ON i.job_id = j.id
            JOIN customers c ON i.customer_id = c.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE i.id = ?
        """, (invoice_id,))

        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        inv = invoice[0]

        # Parse line items from JSON
        items = json.loads(inv.get('line_items') or '[]')

        # Get payments
        payments = self.db.execute("""
            SELECT * FROM payments
            WHERE invoice_id = ?
            ORDER BY payment_date DESC
        """, (invoice_id,))

        # Build HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Invoice {inv['invoice_number']}</title>
            {self._get_base_styles()}
        </head>
        <body>
            <div class="header">
                <div class="company-info">
                    <div class="company-name">{self.company['name']}</div>
                    <div class="company-details">
                        {self.company['address']}<br>
                        {self.company['city']}, {self.company['state']} {self.company['zip']}<br>
                        {self.company['phone']}<br>
                        {self.company['email']}
                    </div>
                </div>
                <div class="document-info">
                    <div class="document-type">INVOICE</div>
                    <div class="document-number">{inv['invoice_number']}</div>
                    <div class="document-date">Date: {self._format_date(inv['invoice_date'])}</div>
                    <div class="document-date">Due: {self._format_date(inv['due_date'])}</div>
                    <br>
                    <span class="status-badge status-{inv['status'].lower()}">{inv['status']}</span>
                </div>
            </div>

            <div class="parties">
                <div class="party-box">
                    <div class="party-label">Bill To</div>
                    <div class="party-name">{inv['first_name']} {inv['last_name']}</div>
                    <div class="party-details">
                        {inv['street_address'] or ''}<br>
                        {inv['city'] or ''}{', ' + inv['state'] if inv['state'] else ''} {inv['zip_code'] or ''}<br>
                        {inv['phone'] or ''}<br>
                        {inv['email'] or ''}
                    </div>
                </div>
                <div class="party-box">
                    <div class="party-label">Job Reference</div>
                    <div class="party-name">Job #{inv['job_number']}</div>
                    <div class="party-details">
                        Damage Type: {inv['damage_type'] or 'N/A'}
                    </div>
                </div>
            </div>

            <div class="vehicle-info">
                <div class="vehicle-label">Vehicle</div>
                <div class="vehicle-description">{inv['year']} {inv['make']} {inv['model']}</div>
                <div class="vehicle-details">
                    Color: {inv['color'] or 'N/A'} |
                    VIN: {inv['vin'] or 'N/A'} |
                    Plate: {inv['license_plate'] or 'N/A'}
                </div>
            </div>
        """

        # Add balance due or payment received banner
        if inv['balance_due'] > 0:
            html += f"""
            <div class="balance-due">
                <div class="balance-label">Balance Due</div>
                <div class="balance-amount">${inv['balance_due']:,.2f}</div>
            </div>
            """
        else:
            html += f"""
            <div class="payment-info">
                <div class="payment-label">Paid in Full</div>
                <div class="payment-amount">Thank You!</div>
            </div>
            """

        # Line items table
        html += """
            <table>
                <thead>
                    <tr>
                        <th style="width: 55%">Description</th>
                        <th style="width: 15%">Type</th>
                        <th style="width: 15%">Qty</th>
                        <th style="width: 15%">Amount</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Add line items
        for item in items:
            qty = item.get('quantity', 1)
            price = item.get('unit_price', 0)
            amount = qty * price
            html += f"""
                    <tr>
                        <td class="item-description">{item.get('description', '')}</td>
                        <td class="item-type">{item.get('type', 'ITEM')}</td>
                        <td>{qty}</td>
                        <td>${amount:,.2f}</td>
                    </tr>
            """

        html += f"""
                </tbody>
            </table>

            <div class="totals">
                <table class="totals-table">
                    <tr>
                        <td>Subtotal:</td>
                        <td>${inv['subtotal']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>Tax:</td>
                        <td>${inv['tax_amount']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>Total:</td>
                        <td>${inv['total']:,.2f}</td>
                    </tr>
        """

        # Add payments
        total_paid = sum(p['amount'] for p in payments)
        if total_paid > 0:
            html += f"""
                    <tr style="background: #d1fae5; color: #065f46;">
                        <td>Payments Received:</td>
                        <td>-${total_paid:,.2f}</td>
                    </tr>
            """

        html += f"""
                    <tr>
                        <td>BALANCE DUE:</td>
                        <td>${inv['balance_due']:,.2f}</td>
                    </tr>
                </table>
            </div>
        """

        # Payment history
        if payments:
            html += """
            <div class="work-order-section">
                <div class="section-title">Payment History</div>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Method</th>
                            <th>Reference</th>
                            <th>Amount</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for payment in payments:
                html += f"""
                        <tr>
                            <td>{self._format_date(payment['payment_date'])}</td>
                            <td>{payment['payment_method']}</td>
                            <td>{payment.get('payment_reference') or '-'}</td>
                            <td>${payment['amount']:,.2f}</td>
                        </tr>
                """
            html += """
                    </tbody>
                </table>
            </div>
            """

        # Add notes if present
        if inv.get('notes'):
            html += f"""
            <div class="notes">
                <div class="notes-label">Notes</div>
                <div class="notes-content">{inv['notes']}</div>
            </div>
            """

        # Footer
        html += f"""
            <div class="footer">
                Thank you for your business!<br>
                {self.company['name']} | {self.company['phone']} | {self.company['email']}
            </div>
        </body>
        </html>
        """

        return html

    def generate_invoice_pdf(self, invoice_id: int) -> Dict[str, Any]:
        """
        Generate a PDF invoice document

        Args:
            invoice_id: The invoice ID

        Returns:
            Dict with file_path, html_content, invoice_number
        """
        html = self.generate_invoice_html(invoice_id)

        # Get invoice number for filename
        invoice = self.db.execute(
            "SELECT invoice_number FROM invoices WHERE id = ?",
            (invoice_id,)
        )
        invoice_number = invoice[0]['invoice_number'] if invoice else f"INV-{invoice_id}"

        # Save HTML
        filename = f"{invoice_number}.html"
        filepath = os.path.join(self.output_dir, 'invoices', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        # Record document generation
        self._record_document('INVOICE', invoice_id, filepath)

        print(f"  Generated invoice: {filepath}")

        return {
            'file_path': filepath,
            'html_content': html,
            'invoice_number': invoice_number,
            'document_type': 'INVOICE'
        }

    # ========================================================================
    # WORK ORDER GENERATION
    # ========================================================================

    def generate_work_order_html(self, job_id: int) -> str:
        """
        Generate HTML for a work order document

        Args:
            job_id: The job ID

        Returns:
            HTML string for the work order
        """
        # Get job data
        job = self.db.execute("""
            SELECT j.*,
                   c.first_name, c.last_name, c.phone, c.email,
                   v.year, v.make, v.model, v.color, v.vin, v.license_plate,
                   t.first_name as tech_first, t.last_name as tech_last, t.employee_id
            FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            JOIN vehicles v ON j.vehicle_id = v.id
            LEFT JOIN technicians t ON j.assigned_tech_id = t.id
            WHERE j.id = ?
        """, (job_id,))

        if not job:
            raise ValueError(f"Job {job_id} not found")

        j = job[0]

        # Get estimate line items for work details from approved estimate's JSON
        items = []
        estimate = self.db.execute("""
            SELECT line_items FROM estimates
            WHERE job_id = ? AND status = 'APPROVED'
            ORDER BY id DESC LIMIT 1
        """, (job_id,))
        if estimate and estimate[0].get('line_items'):
            items = json.loads(estimate[0]['line_items'])

        # Get parts for this job from job's parts_needed JSON field
        parts = []
        if j.get('parts_needed'):
            try:
                parts = json.loads(j['parts_needed'])
            except:
                pass

        # Build HTML
        tech_name = f"{j['tech_first']} {j['tech_last']}" if j['tech_first'] else "Unassigned"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Work Order - Job #{j['job_number']}</title>
            {self._get_base_styles()}
        </head>
        <body>
            <div class="header">
                <div class="company-info">
                    <div class="company-name">{self.company['name']}</div>
                    <div class="company-details">
                        {self.company['address']}<br>
                        {self.company['city']}, {self.company['state']} {self.company['zip']}<br>
                        {self.company['phone']}
                    </div>
                </div>
                <div class="document-info">
                    <div class="document-type">WORK ORDER</div>
                    <div class="document-number">Job #{j['job_number']}</div>
                    <div class="document-date">Date: {self._format_date(datetime.now().date().isoformat())}</div>
                    <br>
                    <span class="status-badge status-{j['status'].lower().replace('_', '-')}">{j['status']}</span>
                </div>
            </div>

            <div class="parties">
                <div class="party-box">
                    <div class="party-label">Customer</div>
                    <div class="party-name">{j['first_name']} {j['last_name']}</div>
                    <div class="party-details">
                        Phone: {j['phone'] or 'N/A'}<br>
                        Email: {j['email'] or 'N/A'}
                    </div>
                </div>
                <div class="party-box">
                    <div class="party-label">Assigned Technician</div>
                    <div class="party-name">{tech_name}</div>
                    <div class="party-details">
                        Employee ID: {j['employee_id'] or 'N/A'}<br>
                        Est. Hours: {j['estimated_hours'] or 'TBD'}
                    </div>
                </div>
            </div>

            <div class="vehicle-info">
                <div class="vehicle-label">Vehicle</div>
                <div class="vehicle-description">{j['year']} {j['make']} {j['model']}</div>
                <div class="vehicle-details">
                    Color: {j['color'] or 'N/A'} |
                    VIN: {j['vin'] or 'N/A'} |
                    Plate: {j['license_plate'] or 'N/A'}
                </div>
            </div>

            <div class="work-order-section">
                <div class="section-title">Damage Information</div>
                <table>
                    <tr>
                        <td><strong>Damage Type:</strong></td>
                        <td>{j['damage_type'] or 'N/A'}</td>
                        <td><strong>Job Type:</strong></td>
                        <td>{j['job_type'] or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td><strong>Priority:</strong></td>
                        <td>{j['priority'] or 'NORMAL'}</td>
                        <td><strong>Insurance Job:</strong></td>
                        <td>{'Yes' if j.get('insurance_claim_id') else 'No'}</td>
                    </tr>
                </table>
            </div>
        """

        # Work items
        if items:
            html += """
            <div class="work-order-section">
                <div class="section-title">Repair Tasks</div>
                <ul class="checklist">
            """
            for item in items:
                html += f"""
                    <li>{item.get('description', 'Task')}</li>
                """
            html += """
                </ul>
            </div>
            """

        # Parts required
        if parts:
            html += """
            <div class="work-order-section">
                <div class="section-title">Parts Required</div>
                <table>
                    <thead>
                        <tr>
                            <th>Part Name</th>
                            <th>Part Number</th>
                            <th>Qty</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for part in parts:
                html += f"""
                        <tr>
                            <td>{part.get('name') or part.get('description', 'N/A')}</td>
                            <td>{part.get('part_number', '-')}</td>
                            <td>{part.get('quantity', 1)}</td>
                            <td>{part.get('status', 'NEEDED')}</td>
                        </tr>
                """
            html += """
                    </tbody>
                </table>
            </div>
            """

        # Tech notes area
        html += """
            <div class="work-order-section">
                <div class="section-title">Technician Notes</div>
                <div class="tech-notes">
                    <p style="color: #999; font-size: 9pt;">Use this space for notes during repair...</p>
                </div>
            </div>
        """

        # Quality checklist
        html += """
            <div class="work-order-section">
                <div class="section-title">Quality Checklist</div>
                <ul class="checklist">
                    <li>All dents removed or minimized per estimate</li>
                    <li>Paint surface intact - no cracking or peeling</li>
                    <li>No new damage created during repair</li>
                    <li>Vehicle cleaned and ready for customer</li>
                    <li>All tools and equipment removed from vehicle</li>
                    <li>Test drove (if applicable)</li>
                </ul>
            </div>
        """

        # Signature section
        html += """
            <div class="signature-section">
                <div class="signature-box">
                    <div class="signature-line">Technician Signature</div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">Date Completed</div>
                </div>
            </div>
        """

        # Footer
        html += f"""
            <div class="footer">
                {self.company['name']} - Internal Work Order<br>
                Questions? Contact management at {self.company['phone']}
            </div>
        </body>
        </html>
        """

        return html

    def generate_work_order_pdf(self, job_id: int) -> Dict[str, Any]:
        """
        Generate a PDF work order document

        Args:
            job_id: The job ID

        Returns:
            Dict with file_path, html_content, job_number
        """
        html = self.generate_work_order_html(job_id)

        # Get job number for filename
        job = self.db.execute(
            "SELECT job_number FROM jobs WHERE id = ?",
            (job_id,)
        )
        job_number = job[0]['job_number'] if job else f"JOB-{job_id}"

        # Save HTML
        filename = f"WO-{job_number}.html"
        filepath = os.path.join(self.output_dir, 'work_orders', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        # Record document generation
        self._record_document('WORK_ORDER', job_id, filepath)

        print(f"  Generated work order: {filepath}")

        return {
            'file_path': filepath,
            'html_content': html,
            'job_number': job_number,
            'document_type': 'WORK_ORDER'
        }

    # ========================================================================
    # RECEIPT GENERATION
    # ========================================================================

    def generate_receipt_html(self, payment_id: int) -> str:
        """
        Generate HTML for a payment receipt

        Args:
            payment_id: The payment ID

        Returns:
            HTML string for the receipt
        """
        # Get payment data
        payment = self.db.execute("""
            SELECT p.*, i.invoice_number, j.job_number,
                   c.first_name, c.last_name, c.email, c.phone,
                   v.year, v.make, v.model
            FROM payments p
            JOIN invoices i ON p.invoice_id = i.id
            JOIN jobs j ON p.job_id = j.id
            JOIN customers c ON i.customer_id = c.id
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE p.id = ?
        """, (payment_id,))

        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        pmt = payment[0]

        receipt_number = f"RCP-{pmt['id']:06d}"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Receipt {receipt_number}</title>
            {self._get_base_styles()}
        </head>
        <body>
            <div class="header">
                <div class="company-info">
                    <div class="company-name">{self.company['name']}</div>
                    <div class="company-details">
                        {self.company['address']}<br>
                        {self.company['city']}, {self.company['state']} {self.company['zip']}<br>
                        {self.company['phone']}
                    </div>
                </div>
                <div class="document-info">
                    <div class="document-type">RECEIPT</div>
                    <div class="document-number">{receipt_number}</div>
                    <div class="document-date">Date: {self._format_date(pmt['payment_date'])}</div>
                </div>
            </div>

            <div class="payment-info" style="text-align: center; margin: 30px 0;">
                <div class="payment-label">Payment Received</div>
                <div class="payment-amount">${pmt['amount']:,.2f}</div>
            </div>

            <div class="parties">
                <div class="party-box">
                    <div class="party-label">Received From</div>
                    <div class="party-name">{pmt['first_name']} {pmt['last_name']}</div>
                    <div class="party-details">
                        {pmt['phone'] or ''}<br>
                        {pmt['email'] or ''}
                    </div>
                </div>
                <div class="party-box">
                    <div class="party-label">Payment Details</div>
                    <div class="party-details">
                        <strong>Method:</strong> {pmt['payment_method']}<br>
                        <strong>Reference:</strong> {pmt.get('payment_reference') or 'N/A'}<br>
                        <strong>Invoice:</strong> {pmt['invoice_number']}<br>
                        <strong>Job:</strong> #{pmt['job_number']}
                    </div>
                </div>
            </div>

            <div class="vehicle-info">
                <div class="vehicle-label">Vehicle Serviced</div>
                <div class="vehicle-description">{pmt['year']} {pmt['make']} {pmt['model']}</div>
            </div>

            <div class="footer" style="margin-top: 60px;">
                Thank you for your payment!<br>
                {self.company['name']} | {self.company['phone']} | {self.company['email']}<br>
                <br>
                <em style="font-size: 8pt;">This receipt serves as confirmation of payment received.</em>
            </div>
        </body>
        </html>
        """

        return html

    def generate_receipt_pdf(self, payment_id: int) -> Dict[str, Any]:
        """
        Generate a PDF receipt document

        Args:
            payment_id: The payment ID

        Returns:
            Dict with file_path, html_content, receipt_number
        """
        html = self.generate_receipt_html(payment_id)

        receipt_number = f"RCP-{payment_id:06d}"

        # Save HTML
        filename = f"{receipt_number}.html"
        filepath = os.path.join(self.output_dir, 'receipts', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        # Record document generation
        self._record_document('RECEIPT', payment_id, filepath)

        print(f"  Generated receipt: {filepath}")

        return {
            'file_path': filepath,
            'html_content': html,
            'receipt_number': receipt_number,
            'document_type': 'RECEIPT'
        }

    # ========================================================================
    # BATCH GENERATION
    # ========================================================================

    def generate_job_documents(self, job_id: int) -> Dict[str, Any]:
        """
        Generate all documents for a job (estimate, invoice, work order)

        Args:
            job_id: The job ID

        Returns:
            Dict with all generated document paths
        """
        results = {
            'job_id': job_id,
            'documents': []
        }

        # Get job info
        job = self.db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Generate work order
        wo = self.generate_work_order_pdf(job_id)
        results['documents'].append(wo)

        # Get approved estimate
        estimates = self.db.execute("""
            SELECT id FROM estimates
            WHERE job_id = ? AND status = 'APPROVED'
            ORDER BY id DESC LIMIT 1
        """, (job_id,))

        if estimates:
            est = self.generate_estimate_pdf(estimates[0]['id'])
            results['documents'].append(est)

        # Get invoice
        invoices = self.db.execute("""
            SELECT id FROM invoices
            WHERE job_id = ?
            ORDER BY id DESC LIMIT 1
        """, (job_id,))

        if invoices:
            inv = self.generate_invoice_pdf(invoices[0]['id'])
            results['documents'].append(inv)

        return results

    # ========================================================================
    # DOCUMENT HISTORY
    # ========================================================================

    def get_document_history(
        self,
        document_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get history of generated documents

        Args:
            document_type: Filter by type (ESTIMATE, INVOICE, WORK_ORDER, RECEIPT)
            reference_id: Filter by reference ID
            limit: Max records to return

        Returns:
            List of document records
        """
        query = """
            SELECT * FROM document_history
            WHERE 1=1
        """
        params = []

        if document_type:
            query += " AND document_type = ?"
            params.append(document_type)

        if reference_id:
            query += " AND reference_id = ?"
            params.append(reference_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, params)

    def _record_document(self, doc_type: str, reference_id: int, file_path: str):
        """Record document generation in history"""
        # Check if document_history table exists, create if not
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS document_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_type TEXT NOT NULL,
                reference_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        self.db.execute("""
            INSERT INTO document_history (document_type, reference_id, file_path, created_at)
            VALUES (?, ?, ?, ?)
        """, (doc_type, reference_id, file_path, datetime.now().isoformat()))

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string for display"""
        if not date_str:
            return 'N/A'
        try:
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%B %d, %Y')
        except:
            return date_str

    def set_company_info(self, company_info: Dict):
        """Update company information for documents"""
        self.company.update(company_info)

    def get_company_info(self) -> Dict:
        """Get current company information"""
        return self.company.copy()

    # ========================================================================
    # REPORTS
    # ========================================================================

    def generate_document_report(self, days: int = 30) -> str:
        """Generate a report of document generation activity"""
        from datetime import timedelta

        start_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Get counts by type
        counts = self.db.execute("""
            SELECT document_type, COUNT(*) as count
            FROM document_history
            WHERE created_at >= ?
            GROUP BY document_type
        """, (start_date,))

        report = []
        report.append(f"DOCUMENT GENERATION REPORT (Last {days} Days)")
        report.append("=" * 50)
        report.append("")

        total = 0
        for row in counts:
            report.append(f"  {row['document_type']:15s}: {row['count']:5d}")
            total += row['count']

        report.append("-" * 30)
        report.append(f"  {'TOTAL':15s}: {total:5d}")
        report.append("")

        return "\n".join(report)
