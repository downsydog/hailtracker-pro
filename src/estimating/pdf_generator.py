"""
PDR Estimate/Invoice PDF Generator

Generates professional PDF documents for estimates, invoices, and supplements.
Uses ReportLab for PDF generation.
"""

from typing import Dict, List, Optional
from datetime import datetime
from io import BytesIO

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_estimate_pdf(
    estimate_data: Dict,
    company_info: Optional[Dict] = None
) -> bytes:
    """
    Generate PDF for a PDR estimate.

    Args:
        estimate_data: Dict with estimate details
        company_info: Optional company branding info

    Returns:
        PDF bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6,
        textColor=colors.HexColor('#1a56db')
    )
    normal_style = styles['Normal']

    elements = []

    # Header
    company_name = company_info.get('name', 'HailTracker PDR') if company_info else 'HailTracker PDR'
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph(f"PDR Estimate #{estimate_data.get('id', 'N/A')}", heading_style))
    elements.append(Paragraph(f"Date: {estimate_data.get('created_at', datetime.now().strftime('%Y-%m-%d'))}", normal_style))
    elements.append(Spacer(1, 12))

    # Customer & Vehicle Info
    elements.append(Paragraph("Customer Information", heading_style))
    customer_name = estimate_data.get('customer_name', 'N/A')
    elements.append(Paragraph(f"Name: {customer_name}", normal_style))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Vehicle Information", heading_style))
    vehicle_info = f"{estimate_data.get('vehicle_year', '')} {estimate_data.get('vehicle_make', '')} {estimate_data.get('vehicle_model', '')}"
    elements.append(Paragraph(f"Vehicle: {vehicle_info.strip() or 'N/A'}", normal_style))
    if estimate_data.get('vehicle_vin'):
        elements.append(Paragraph(f"VIN: {estimate_data['vehicle_vin']}", normal_style))
    elements.append(Spacer(1, 12))

    # Panel Details
    elements.append(Paragraph("Repair Details", heading_style))

    panels = estimate_data.get('panels', [])
    for panel in panels:
        panel_name = panel.get('display_name', panel.get('panel_name', 'Unknown Panel'))
        elements.append(Paragraph(f"<b>{panel_name}</b>", normal_style))

        # Dents table
        dents = panel.get('dents', [])
        if dents:
            dent_data = [['Size', 'Zone', 'Price']]
            for dent in dents:
                dent_data.append([
                    dent.get('size', 'N/A').capitalize(),
                    dent.get('zone', 'N/A').capitalize(),
                    f"${dent.get('final_price', 0):.2f}"
                ])

            dent_table = Table(dent_data, colWidths=[1.5*inch, 1.5*inch, 1*inch])
            dent_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ]))
            elements.append(dent_table)

        # R&I items
        rin_items = panel.get('rin_items', [])
        if rin_items:
            elements.append(Spacer(1, 6))
            elements.append(Paragraph("<i>R&I Items:</i>", normal_style))
            for item in rin_items:
                elements.append(Paragraph(
                    f"  • {item.get('display_name', item.get('item_name', 'N/A'))}: ${item.get('price', 0):.2f}",
                    normal_style
                ))

        elements.append(Spacer(1, 12))

    # Totals
    elements.append(Paragraph("Summary", heading_style))

    totals_data = [
        ['Description', 'Amount'],
        ['Dent Repair Total', f"${estimate_data.get('dent_total', 0):.2f}"],
        ['R&I Items Total', f"${estimate_data.get('rin_total', 0):.2f}"],
    ]

    if estimate_data.get('supplement_total', 0) > 0:
        totals_data.append(['Supplement', f"${estimate_data.get('supplement_total', 0):.2f}"])

    totals_data.append(['Grand Total', f"${estimate_data.get('grand_total', 0):.2f}"])

    totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a56db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
    ]))
    elements.append(totals_table)

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "This estimate is valid for 30 days from the date above.",
        ParagraphStyle('Footer', parent=normal_style, fontSize=9, textColor=colors.gray)
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_supplement_pdf(
    supplement_data: Dict,
    company_info: Optional[Dict] = None
) -> bytes:
    """
    Generate PDF for a supplement request.

    Args:
        supplement_data: Dict with supplement details including narrative
        company_info: Optional company branding info

    Returns:
        PDF bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6,
        textColor=colors.HexColor('#ea580c')  # Orange for supplement
    )
    normal_style = styles['Normal']
    narrative_style = ParagraphStyle(
        'Narrative',
        parent=normal_style,
        fontSize=10,
        leading=14,
        spaceAfter=6
    )

    elements = []

    # Header
    company_name = company_info.get('name', 'HailTracker PDR') if company_info else 'HailTracker PDR'
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph("SUPPLEMENT REQUEST", heading_style))
    elements.append(Paragraph(f"Original Estimate: #{supplement_data.get('estimate_id', 'N/A')}", normal_style))
    elements.append(Paragraph(f"Date: {supplement_data.get('supplement_date', datetime.now().strftime('%Y-%m-%d'))}", normal_style))
    elements.append(Spacer(1, 12))

    # Summary Narrative
    elements.append(Paragraph("Summary", heading_style))
    narrative = supplement_data.get('summary_narrative', '')
    for line in narrative.split('\n'):
        if line.strip():
            elements.append(Paragraph(line, narrative_style))
    elements.append(Spacer(1, 12))

    # Discovery Details
    elements.append(Paragraph("Discovery Details", heading_style))

    discoveries = supplement_data.get('line_items', [])
    if discoveries:
        discovery_data = [['Item', 'Description', 'Time (hrs)', 'Cost']]
        for disc in discoveries:
            discovery_data.append([
                disc.get('description', 'N/A'),
                disc.get('details', '')[:50] + ('...' if len(disc.get('details', '')) > 50 else ''),
                f"{disc.get('time_hours', 0):.2f}",
                f"${disc.get('cost', 0):.2f}"
            ])

        discovery_table = Table(discovery_data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 1*inch])
        discovery_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fed7aa')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (-2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(discovery_table)
    elements.append(Spacer(1, 12))

    # Totals
    elements.append(Paragraph("Supplement Summary", heading_style))

    totals_data = [
        ['Description', 'Amount'],
        ['Original Estimate', f"${supplement_data.get('original_total', 0):.2f}"],
        ['Additional Cost (This Supplement)', f"${supplement_data.get('additional_cost', 0):.2f}"],
        ['Additional Time', f"{supplement_data.get('additional_time_hours', 0):.2f} hours"],
        ['New Total', f"${supplement_data.get('new_total', 0):.2f}"],
    ]

    totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ea580c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef3c7')),
    ]))
    elements.append(totals_table)

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "All additional items were documented at the time of discovery. "
        "Please review and approve this supplement to proceed with complete repair.",
        ParagraphStyle('Footer', parent=normal_style, fontSize=9, textColor=colors.gray)
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_invoice_pdf(
    invoice_data: Dict,
    company_info: Optional[Dict] = None,
    include_supplement: bool = True
) -> bytes:
    """
    Generate PDF for a final invoice, optionally including supplement details.

    Args:
        invoice_data: Dict with invoice details
        company_info: Optional company branding info
        include_supplement: Whether to include supplement section

    Returns:
        PDF bytes
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6,
        textColor=colors.HexColor('#16a34a')  # Green for invoice
    )
    normal_style = styles['Normal']

    elements = []

    # Header
    company_name = company_info.get('name', 'HailTracker PDR') if company_info else 'HailTracker PDR'
    elements.append(Paragraph(company_name, title_style))
    elements.append(Paragraph(f"INVOICE #{invoice_data.get('id', 'N/A')}", heading_style))
    elements.append(Paragraph(f"Date: {invoice_data.get('created_at', datetime.now().strftime('%Y-%m-%d'))}", normal_style))
    elements.append(Spacer(1, 12))

    # Customer & Vehicle Info
    elements.append(Paragraph("Bill To:", heading_style))
    elements.append(Paragraph(f"{invoice_data.get('customer_name', 'N/A')}", normal_style))
    if invoice_data.get('customer_email'):
        elements.append(Paragraph(f"{invoice_data['customer_email']}", normal_style))
    if invoice_data.get('customer_phone'):
        elements.append(Paragraph(f"{invoice_data['customer_phone']}", normal_style))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("Vehicle:", heading_style))
    vehicle_info = f"{invoice_data.get('vehicle_year', '')} {invoice_data.get('vehicle_make', '')} {invoice_data.get('vehicle_model', '')}"
    elements.append(Paragraph(vehicle_info.strip() or 'N/A', normal_style))
    if invoice_data.get('vehicle_vin'):
        elements.append(Paragraph(f"VIN: {invoice_data['vehicle_vin']}", normal_style))
    elements.append(Spacer(1, 12))

    # Services Rendered
    elements.append(Paragraph("Services Rendered", heading_style))

    # Group dents by panel
    dents = invoice_data.get('dents', [])
    panels_dict = {}
    for dent in dents:
        panel = dent.get('panel_name', 'Other')
        if panel not in panels_dict:
            panels_dict[panel] = []
        panels_dict[panel].append(dent)

    for panel_name, panel_dents in panels_dict.items():
        panel_total = sum(d.get('final_price', 0) for d in panel_dents)
        elements.append(Paragraph(f"<b>{panel_name}</b> ({len(panel_dents)} dents) - ${panel_total:.2f}", normal_style))

    elements.append(Spacer(1, 6))

    # R&I Items
    rin_items = invoice_data.get('rin_items', [])
    if rin_items:
        elements.append(Paragraph("R&I Items:", normal_style))
        for item in rin_items:
            elements.append(Paragraph(
                f"  • {item.get('display_name', item.get('item_name', 'N/A'))}: ${item.get('price', 0):.2f}",
                normal_style
            ))
        elements.append(Spacer(1, 6))

    # Supplement section
    discoveries = invoice_data.get('discoveries', [])
    if include_supplement and discoveries:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Supplemental Work", ParagraphStyle(
            'SupplementHeading',
            parent=heading_style,
            textColor=colors.HexColor('#ea580c')
        )))
        for disc in discoveries:
            elements.append(Paragraph(
                f"  • {disc.get('display_name', disc.get('type', 'N/A'))}: ${disc.get('additional_cost', 0):.2f}",
                normal_style
            ))
        elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 12))

    # Final totals
    elements.append(Paragraph("Invoice Summary", heading_style))

    dent_total = sum(d.get('final_price', 0) for d in dents)
    rin_total = sum(r.get('price', 0) for r in rin_items)
    supplement_total = sum(d.get('additional_cost', 0) for d in discoveries)
    grand_total = dent_total + rin_total + supplement_total

    totals_data = [
        ['Description', 'Amount'],
        ['Dent Repair', f"${dent_total:.2f}"],
        ['R&I Items', f"${rin_total:.2f}"],
    ]
    if supplement_total > 0:
        totals_data.append(['Supplemental Work', f"${supplement_total:.2f}"])
    totals_data.append(['TOTAL DUE', f"${grand_total:.2f}"])

    totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16a34a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dcfce7')),
    ]))
    elements.append(totals_table)

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "Thank you for your business!",
        ParagraphStyle('Footer', parent=normal_style, fontSize=10, textColor=colors.gray, alignment=1)
    ))

    doc.build(elements)
    return buffer.getvalue()


# Flask route helpers for PDF generation
def add_pdf_routes(app, db_conn_func):
    """
    Add PDF generation routes to Flask app.

    Args:
        app: Flask app instance
        db_conn_func: Function that returns database connection
    """
    from flask import send_file, jsonify
    from io import BytesIO

    @app.route('/api/pdr-estimates/<int:estimate_id>/pdf', methods=['GET'])
    def download_estimate_pdf(estimate_id):
        """Generate and download estimate PDF."""
        try:
            # In real implementation, fetch estimate from database
            # For now, return error if ReportLab not available
            if not REPORTLAB_AVAILABLE:
                return jsonify({"error": "PDF generation not available"}), 500

            # Mock data for testing
            estimate_data = {
                "id": estimate_id,
                "customer_name": "Test Customer",
                "vehicle_year": 2022,
                "vehicle_make": "Toyota",
                "vehicle_model": "Camry",
                "panels": [],
                "dent_total": 500,
                "rin_total": 100,
                "grand_total": 600
            }

            pdf_bytes = generate_estimate_pdf(estimate_data)
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'estimate_{estimate_id}.pdf'
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/work-orders/<int:work_order_id>/supplement-pdf', methods=['GET'])
    def download_supplement_pdf(work_order_id):
        """Generate and download supplement PDF."""
        try:
            if not REPORTLAB_AVAILABLE:
                return jsonify({"error": "PDF generation not available"}), 500

            # Mock data for testing
            supplement_data = {
                "estimate_id": work_order_id,
                "original_total": 1000,
                "additional_cost": 250,
                "additional_time_hours": 2.5,
                "new_total": 1250,
                "summary_narrative": "Supplement request for additional work discovered during repair.",
                "line_items": []
            }

            pdf_bytes = generate_supplement_pdf(supplement_data)
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'supplement_{work_order_id}.pdf'
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/invoices/<int:invoice_id>/pdf', methods=['GET'])
    def download_invoice_pdf(invoice_id):
        """Generate and download invoice PDF."""
        try:
            if not REPORTLAB_AVAILABLE:
                return jsonify({"error": "PDF generation not available"}), 500

            # Mock data for testing
            invoice_data = {
                "id": invoice_id,
                "customer_name": "Test Customer",
                "vehicle_year": 2022,
                "vehicle_make": "Toyota",
                "vehicle_model": "Camry",
                "dents": [],
                "rin_items": [],
                "discoveries": []
            }

            pdf_bytes = generate_invoice_pdf(invoice_data)
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'invoice_{invoice_id}.pdf'
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
