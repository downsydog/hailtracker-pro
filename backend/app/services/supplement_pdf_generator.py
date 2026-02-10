"""
Supplement PDF Generator

Generates insurance-ready supplement documents with:
- Header with estimate/supplement info
- Summary of original vs revised totals
- Changes table with before/after/delta
- Narrative explanation
- Evidence photo references
"""

from io import BytesIO
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generate_supplement_pdf(
    supplement_data: Dict[str, Any],
    estimate_data: Dict[str, Any],
    shop_info: Optional[Dict[str, Any]] = None
) -> BytesIO:
    """
    Generate a supplement PDF document.

    Args:
        supplement_data: Supplement dict with delta_json, narrative, etc.
        estimate_data: Current estimate data for context
        shop_info: Optional shop information for header

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    # Build styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='SupplementTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#dc2626'),  # Red for supplement
        alignment=TA_CENTER,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=12,
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name='BodyText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    ))
    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey
    ))
    styles.add(ParagraphStyle(
        name='DeltaPositive',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#dc2626')
    ))
    styles.add(ParagraphStyle(
        name='NarrativeText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=10,
        rightIndent=10
    ))

    story = []

    # Build document sections
    story.extend(_build_header(supplement_data, estimate_data, shop_info, styles))
    story.extend(_build_summary(supplement_data, styles))
    story.extend(_build_changes_table(supplement_data, styles))
    story.extend(_build_narrative(supplement_data, styles))
    story.extend(_build_evidence_section(supplement_data, styles))
    story.extend(_build_footer(supplement_data, estimate_data, styles))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _build_header(
    supplement_data: Dict,
    estimate_data: Dict,
    shop_info: Optional[Dict],
    styles
) -> List:
    """Build header section with supplement identification."""
    elements = []

    # Shop name
    if shop_info and shop_info.get('company_name'):
        elements.append(Paragraph(shop_info['company_name'], styles['Title']))
        elements.append(Spacer(1, 6))

    # SUPPLEMENT banner
    elements.append(Paragraph("SUPPLEMENT", styles['SupplementTitle']))

    # Estimate and supplement numbers
    estimate_num = estimate_data.get('estimate_number', f"EST-{estimate_data.get('id', '?')}")
    supplement_num = supplement_data.get('supplement_number', 1)
    elements.append(Paragraph(
        f"Estimate: {estimate_num} | Supplement #{supplement_num}",
        styles['BodyText']
    ))

    # Date
    created_at = supplement_data.get('created_at')
    if isinstance(created_at, str):
        date_str = created_at[:10]
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
    elements.append(Paragraph(f"Date: {date_str}", styles['BodyText']))

    elements.append(Spacer(1, 12))

    # Vehicle and customer info table
    vehicle = f"{estimate_data.get('vehicle_year', '')} {estimate_data.get('vehicle_make', '')} {estimate_data.get('vehicle_model', '')}".strip()
    vin = estimate_data.get('vin', '')
    customer = estimate_data.get('customer_name', '')
    claim = estimate_data.get('claim_number', '')

    info_data = [
        ['Vehicle:', vehicle, 'Customer:', customer],
        ['VIN:', vin or 'N/A', 'Claim #:', claim or 'N/A'],
    ]

    info_table = Table(info_data, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)

    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 12))

    return elements


def _build_summary(supplement_data: Dict, styles) -> List:
    """Build financial summary section."""
    elements = []

    elements.append(Paragraph("FINANCIAL SUMMARY", styles['SectionHeader']))

    original = supplement_data.get('original_total', 0) or 0
    revised = supplement_data.get('revised_total', 0) or 0
    delta = supplement_data.get('delta_amount', 0) or 0

    # Format delta with sign
    delta_sign = '+' if delta > 0 else ''
    delta_color = colors.HexColor('#dc2626') if delta > 0 else colors.HexColor('#16a34a')

    summary_data = [
        ['Original Estimate Total:', f'${float(original):,.2f}'],
        ['Revised Estimate Total:', f'${float(revised):,.2f}'],
        ['Supplement Amount:', f'{delta_sign}${float(delta):,.2f}'],
    ]

    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Highlight delta row
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 2), (1, 2), delta_color),
        ('FONTSIZE', (0, 2), (-1, 2), 12),
        # Border on bottom row
        ('LINEABOVE', (0, 2), (-1, 2), 1, colors.grey),
    ]))
    elements.append(summary_table)

    elements.append(Spacer(1, 12))

    return elements


def _build_changes_table(supplement_data: Dict, styles) -> List:
    """Build changes table showing before/after/delta for each panel."""
    elements = []

    delta_json = supplement_data.get('delta_json', {})
    panel_changes = delta_json.get('panels', [])

    if not panel_changes:
        return elements

    elements.append(Paragraph("CHANGES DETAIL", styles['SectionHeader']))

    # Table header
    header = ['Panel', 'Change', 'Before', 'After', 'Delta']
    table_data = [header]

    for change in panel_changes:
        panel_name = change.get('panel_name', 'Unknown').replace('_', ' ').title()
        change_type = change.get('change_type', '').upper()

        if change_type == 'ADDED':
            after = change.get('after', {})
            price = float(after.get('panel_total', 0) or 0)
            table_data.append([
                panel_name,
                'ADDED',
                '—',
                f'${price:,.2f}',
                f'+${price:,.2f}'
            ])
        elif change_type == 'MODIFIED':
            deltas = change.get('deltas', {})
            price_delta = deltas.get('panel_total', {})
            before_price = float(price_delta.get('before', 0) or 0)
            after_price = float(price_delta.get('after', 0) or 0)
            delta_val = after_price - before_price
            delta_sign = '+' if delta_val > 0 else ''
            table_data.append([
                panel_name,
                'MODIFIED',
                f'${before_price:,.2f}',
                f'${after_price:,.2f}',
                f'{delta_sign}${delta_val:,.2f}'
            ])
        elif change_type == 'REMOVED':
            before = change.get('before', {})
            price = float(before.get('panel_total', 0) or 0)
            table_data.append([
                panel_name,
                'REMOVED',
                f'${price:,.2f}',
                '—',
                f'-${price:,.2f}'
            ])

    # Add R&I changes if present
    ri_changes = delta_json.get('ri_ops', [])
    for change in ri_changes:
        op_name = change.get('operation', 'Unknown')
        change_type = change.get('change_type', '').upper()
        price_delta = float(change.get('price_delta', 0) or 0)

        if change_type == 'ADDED':
            after = change.get('after', {})
            price = float(after.get('price', 0) or 0)
            table_data.append([
                f"R&I: {op_name}",
                'ADDED',
                '—',
                f'${price:,.2f}',
                f'+${price:,.2f}'
            ])
        elif change_type == 'MODIFIED':
            before = change.get('before', {})
            after = change.get('after', {})
            before_price = float(before.get('price', 0) or 0)
            after_price = float(after.get('price', 0) or 0)
            delta_sign = '+' if price_delta > 0 else ''
            table_data.append([
                f"R&I: {op_name}",
                'MODIFIED',
                f'${before_price:,.2f}',
                f'${after_price:,.2f}',
                f'{delta_sign}${price_delta:,.2f}'
            ])

    if len(table_data) > 1:
        col_widths = [2*inch, 1*inch, 1.25*inch, 1.25*inch, 1.25*inch]
        changes_table = Table(table_data, colWidths=col_widths)
        changes_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(changes_table)
        elements.append(Spacer(1, 12))

    return elements


def _build_narrative(supplement_data: Dict, styles) -> List:
    """Build narrative section."""
    elements = []

    narrative = supplement_data.get('narrative', '')
    if not narrative:
        return elements

    elements.append(Paragraph("EXPLANATION", styles['SectionHeader']))

    # Split narrative into paragraphs
    for para in narrative.split('\n\n'):
        if para.strip():
            elements.append(Paragraph(para.strip(), styles['NarrativeText']))
            elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 6))

    return elements


def _build_evidence_section(supplement_data: Dict, styles) -> List:
    """Build evidence photo references section."""
    elements = []

    # Get linked photos from delta_json or separate field
    evidence_photos = supplement_data.get('evidence_photos', [])

    if not evidence_photos:
        return elements

    elements.append(Paragraph("SUPPORTING EVIDENCE", styles['SectionHeader']))

    for i, photo in enumerate(evidence_photos, 1):
        photo_ref = f"Photo {i}: "
        caption = photo.get('caption', '')
        panel = photo.get('panel_name', '')
        if panel:
            photo_ref += f"[{panel.replace('_', ' ').title()}] "
        if caption:
            photo_ref += caption
        else:
            photo_ref += "Damage documentation"

        elements.append(Paragraph(f"• {photo_ref}", styles['BodyText']))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Full photo documentation available in attached Photo Sheet or upon request.",
        styles['SmallText']
    ))
    elements.append(Spacer(1, 12))

    return elements


def _build_footer(supplement_data: Dict, estimate_data: Dict, styles) -> List:
    """Build footer with approval section."""
    elements = []

    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("APPROVAL", styles['SectionHeader']))

    # Signature lines
    sig_data = [
        ['', '', ''],
        ['Technician Signature', 'Date', 'Adjuster Approval'],
        ['_' * 30, '_' * 20, '_' * 30],
    ]
    sig_table = Table(sig_data, colWidths=[2.5*inch, 1.5*inch, 2.5*inch])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 2), (-1, 2), 20),
    ]))
    elements.append(sig_table)

    elements.append(Spacer(1, 24))

    # Footer text
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"Estimate: {estimate_data.get('estimate_number', '')} | "
        f"Supplement #{supplement_data.get('supplement_number', 1)}",
        styles['SmallText']
    ))

    return elements
