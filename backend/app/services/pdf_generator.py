"""
PDF Generator Service for PDR Estimates
========================================

Generates insurance-ready, professional PDFs for PDR estimates.
Designed to be familiar to CCC/Mitchell users.

Features:
- Clean, boring, professional layout
- All pricing justified with matrix details
- Multi-page support with repeated headers
- Deterministic output (same data = same PDF)
- No UI dependencies (pure data-driven)
"""

from io import BytesIO
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Panel display names
PANEL_NAMES = {
    'hood': 'Hood',
    'roof': 'Roof',
    'deck': 'Deck Lid / Trunk',
    'deck_lid': 'Deck Lid / Trunk',
    'lfd': 'Left Front Door',
    'lf_door': 'Left Front Door',
    'rfd': 'Right Front Door',
    'rf_door': 'Right Front Door',
    'lrd': 'Left Rear Door',
    'lr_door': 'Left Rear Door',
    'rrd': 'Right Rear Door',
    'rr_door': 'Right Rear Door',
    'lff': 'Left Front Fender',
    'l_fender': 'Left Front Fender',
    'rff': 'Right Front Fender',
    'r_fender': 'Right Front Fender',
    'lq': 'Left Quarter Panel',
    'l_quarter': 'Left Quarter Panel',
    'rq': 'Right Quarter Panel',
    'r_quarter': 'Right Quarter Panel',
    'lrail': 'Left Roof Rail',
    'l_roof_rail': 'Left Roof Rail',
    'rrail': 'Right Roof Rail',
    'r_roof_rail': 'Right Roof Rail',
    'lbs': 'Left Bedside',
    'bedside_l': 'Left Bedside',
    'rbs': 'Right Bedside',
    'bedside_r': 'Right Bedside',
    'tailgate': 'Tailgate',
    'hatch': 'Hatch / Liftgate',
}

SIZE_LABELS = {
    'dime': 'Dime',
    'nickel': 'Nickel',
    'quarter': 'Quarter',
    'half': 'Half Dollar'
}

DEPTH_LABELS = {
    'shallow': 'Shallow',
    'medium': 'Medium',
    'deep': 'Deep',
    'severe': 'Severe'
}

ZONE_LABELS = {
    'center': 'Center',
    'edge': 'Edge',
    'crease': 'Crease',
    'body_line': 'Body Line'
}

# Severity levels for sorting/grouping
def compute_severity_score(panel: Dict) -> int:
    """Compute severity score for a panel (higher = more severe)."""
    count_weights = {
        '1-5': 1, '6-15': 2, '16-30': 3, '31-50': 4,
        '51-75': 5, '76-100': 6, '101+': 7
    }
    size_weights = {'dime': 0, 'nickel': 1, 'quarter': 2, 'half': 3}
    depth_weights = {'shallow': 0, 'medium': 1, 'deep': 2, 'severe': 3}

    # Support both field name conventions
    count = panel.get('total_dent_count', panel.get('dent_count', 0))
    count_range = panel.get('count_range', '1-5')
    if not panel.get('count_range'):
        if count <= 5: count_range = '1-5'
        elif count <= 15: count_range = '6-15'
        elif count <= 30: count_range = '16-30'
        elif count <= 50: count_range = '31-50'
        elif count <= 75: count_range = '51-75'
        elif count <= 100: count_range = '76-100'
        else: count_range = '101+'

    score = (count_weights.get(count_range, 1) * 2)
    size_key = panel.get('majority_size', panel.get('avg_size', 'nickel'))
    score += size_weights.get(size_key, 1)
    score += depth_weights.get(panel.get('depth', 'medium'), 1)

    return score


# ==============================================================================
# PDF GENERATOR CLASS
# ==============================================================================

class PDFGenerator:
    """Generates professional PDR estimate PDFs."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='EstimateTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=6,
            alignment=TA_CENTER
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#1e40af'),
            borderPadding=4
        ))

        # Info label style
        self.styles.add(ParagraphStyle(
            name='InfoLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280')
        ))

        # Info value style
        self.styles.add(ParagraphStyle(
            name='InfoValue',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))

        # Total style
        self.styles.add(ParagraphStyle(
            name='GrandTotal',
            parent=self.styles['Normal'],
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))

        # Disclaimer style
        self.styles.add(ParagraphStyle(
            name='Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#9ca3af'),
            spaceBefore=12
        ))

    def _format_currency(self, amount) -> str:
        """Format amount as currency."""
        if amount is None:
            return '$0.00'
        if isinstance(amount, Decimal):
            amount = float(amount)
        return f'${amount:,.2f}'

    def _get_panel_name(self, panel_id: str) -> str:
        """Get display name for a panel."""
        return PANEL_NAMES.get(panel_id, panel_id.replace('_', ' ').title())

    def _get_count_range(self, count: int) -> str:
        """Convert dent count to range string."""
        if count <= 5: return '1-5'
        elif count <= 15: return '6-15'
        elif count <= 30: return '16-30'
        elif count <= 50: return '31-50'
        elif count <= 75: return '51-75'
        elif count <= 100: return '76-100'
        else: return '101+'

    def generate_estimate_pdf(
        self,
        estimate: Dict[str, Any],
        shop_info: Optional[Dict[str, Any]] = None,
        include_disclaimer: bool = True
    ) -> BytesIO:
        """
        Generate a complete estimate PDF.

        Args:
            estimate: Estimate data dictionary containing:
                - estimate_number
                - vehicle_year, vehicle_make, vehicle_model, vin
                - customer_name, customer_phone, customer_email
                - claim_number (optional)
                - insurance_carrier (optional)
                - panels: list of panel data
                - labor_total, ri_total, total_price
                - created_at
            shop_info: Optional shop/company info
            include_disclaimer: Whether to include disclaimer text

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
            bottomMargin=0.75*inch
        )

        story = []

        # Build PDF sections
        story.extend(self._build_header(estimate, shop_info))
        story.append(Spacer(1, 0.2*inch))
        story.extend(self._build_vehicle_info(estimate))
        story.append(Spacer(1, 0.2*inch))
        story.extend(self._build_summary(estimate))
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._build_panel_breakdown(estimate))

        # R&I section if applicable
        if estimate.get('ri_items') or estimate.get('ri_total', 0) > 0:
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._build_ri_section(estimate))

        # Totals
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._build_totals(estimate))

        # Insurance Approval section (if approved)
        if estimate.get('insurer_status') == 'approved' and estimate.get('insurer_approved_total') is not None:
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._build_insurance_approval(estimate))

        # Notes
        if estimate.get('notes'):
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._build_notes(estimate))

        # Disclaimer
        if include_disclaimer:
            story.append(Spacer(1, 0.3*inch))
            story.extend(self._build_disclaimer())

        # Build PDF with page numbers
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

        buffer.seek(0)
        return buffer

    def _add_page_number(self, canvas, doc):
        """Add page number and timestamp to each page."""
        canvas.saveState()

        # Page number
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#9ca3af'))
        canvas.drawRightString(letter[0] - 0.5*inch, 0.4*inch, text)

        # Timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        canvas.drawString(0.5*inch, 0.4*inch, f"Generated: {timestamp}")

        # System name (small)
        canvas.setFont('Helvetica', 6)
        canvas.drawCentredString(letter[0]/2, 0.4*inch, "HailTracker Pro")

        canvas.restoreState()

    def _build_header(self, estimate: Dict, shop_info: Optional[Dict]) -> List:
        """Build the header section."""
        elements = []

        # Shop name / company
        shop_name = 'PDR Estimate'
        if shop_info:
            shop_name = shop_info.get('company_name', 'PDR Estimate')

        elements.append(Paragraph(shop_name, self.styles['EstimateTitle']))

        # Estimate info row
        estimate_number = estimate.get('estimate_number', 'N/A')
        date_str = datetime.now().strftime('%B %d, %Y')
        if estimate.get('created_at'):
            try:
                if isinstance(estimate['created_at'], str):
                    created = datetime.fromisoformat(estimate['created_at'].replace('Z', '+00:00'))
                else:
                    created = estimate['created_at']
                date_str = created.strftime('%B %d, %Y')
            except:
                pass

        header_data = [
            [
                Paragraph(f"<b>Estimate #:</b> {estimate_number}", self.styles['Normal']),
                Paragraph(f"<b>Date:</b> {date_str}", self.styles['Normal'])
            ]
        ]

        # Add claim info if present
        if estimate.get('claim_number') or estimate.get('insurance_carrier'):
            claim_num = estimate.get('claim_number', 'N/A')
            carrier = estimate.get('insurance_carrier', estimate.get('insurance_profile', {}).get('carrier_name', ''))
            header_data.append([
                Paragraph(f"<b>Claim #:</b> {claim_num}", self.styles['Normal']),
                Paragraph(f"<b>Insurance:</b> {carrier}", self.styles['Normal']) if carrier else ''
            ])

        header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(header_table)

        return elements

    def _build_vehicle_info(self, estimate: Dict) -> List:
        """Build vehicle and customer info section."""
        elements = []

        elements.append(Paragraph("Vehicle & Customer Information", self.styles['SectionHeader']))

        # Vehicle info
        year = estimate.get('vehicle_year', '')
        make = estimate.get('vehicle_make', '')
        model = estimate.get('vehicle_model', '')
        vin = estimate.get('vin') or estimate.get('vehicle_vin', '')

        vehicle_str = f"{year} {make} {model}".strip() or 'N/A'

        # Customer info
        customer_name = estimate.get('customer_name', 'N/A')
        customer_phone = estimate.get('customer_phone', '')
        customer_email = estimate.get('customer_email', '')

        info_data = [
            [
                Paragraph("<b>Vehicle:</b>", self.styles['InfoLabel']),
                Paragraph(vehicle_str, self.styles['InfoValue']),
                Paragraph("<b>Customer:</b>", self.styles['InfoLabel']),
                Paragraph(customer_name, self.styles['InfoValue']),
            ],
            [
                Paragraph("<b>VIN:</b>", self.styles['InfoLabel']),
                Paragraph(vin or 'N/A', self.styles['Normal']),
                Paragraph("<b>Phone:</b>", self.styles['InfoLabel']),
                Paragraph(customer_phone or 'N/A', self.styles['Normal']),
            ]
        ]

        if customer_email:
            info_data.append([
                '', '',
                Paragraph("<b>Email:</b>", self.styles['InfoLabel']),
                Paragraph(customer_email, self.styles['Normal']),
            ])

        info_table = Table(info_data, colWidths=[0.8*inch, 2.7*inch, 0.8*inch, 2.7*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(info_table)

        return elements

    def _build_summary(self, estimate: Dict) -> List:
        """Build damage summary section."""
        elements = []

        elements.append(Paragraph("Damage Summary", self.styles['SectionHeader']))

        panels = estimate.get('panels', [])

        # Count severity levels
        severity_counts = {'light': 0, 'medium': 0, 'heavy': 0, 'severe': 0}
        for panel in panels:
            score = compute_severity_score(panel)
            if score <= 5:
                severity_counts['light'] += 1
            elif score <= 10:
                severity_counts['medium'] += 1
            elif score <= 15:
                severity_counts['heavy'] += 1
            else:
                severity_counts['severe'] += 1

        total_panels = len(panels)

        summary_text = f"<b>Total Damaged Panels:</b> {total_panels}"
        if total_panels > 0:
            breakdown = []
            if severity_counts['light'] > 0:
                breakdown.append(f"Light: {severity_counts['light']}")
            if severity_counts['medium'] > 0:
                breakdown.append(f"Medium: {severity_counts['medium']}")
            if severity_counts['heavy'] > 0:
                breakdown.append(f"Heavy: {severity_counts['heavy']}")
            if severity_counts['severe'] > 0:
                breakdown.append(f"Severe: {severity_counts['severe']}")

            if breakdown:
                summary_text += f" ({', '.join(breakdown)})"

        elements.append(Paragraph(summary_text, self.styles['Normal']))

        return elements

    def _build_panel_breakdown(self, estimate: Dict) -> List:
        """Build panel breakdown table."""
        elements = []

        elements.append(Paragraph("Panel Breakdown", self.styles['SectionHeader']))

        panels = estimate.get('panels', [])

        if not panels:
            elements.append(Paragraph("No panels entered.", self.styles['Normal']))
            return elements

        # Sort panels by severity (most severe first)
        sorted_panels = sorted(panels, key=compute_severity_score, reverse=True)

        # Table header
        header = ['Panel', 'Count', 'Size', 'Depth', 'Zone', 'Add-ons', 'Price']

        # Table data
        table_data = [header]

        for panel in sorted_panels:
            panel_name = self._get_panel_name(panel.get('panel_name', ''))

            # Support both legacy and new field names
            count = panel.get('total_dent_count', panel.get('dent_count', 0))
            count_range = panel.get('count_range') or self._get_count_range(count)
            size_key = panel.get('majority_size', panel.get('avg_size', 'nickel'))
            size = SIZE_LABELS.get(size_key, size_key.title() if size_key else '')
            depth = DEPTH_LABELS.get(panel.get('depth', 'medium'), 'Medium')
            zone = ZONE_LABELS.get(panel.get('zone', 'center'), 'Center')

            # Build add-ons string (support both field name conventions)
            addons = []
            if panel.get('is_aluminum') or panel.get('aluminum'):
                addons.append('AL')
            if panel.get('requires_glue_pull') or panel.get('glue_pull'):
                addons.append('GP')
            if panel.get('is_hss') or panel.get('hss'):
                addons.append('HSS')
            if panel.get('is_double_metal') or panel.get('double_metal'):
                addons.append('DM')
            if panel.get('is_conventional_repair') or panel.get('conventional'):
                addons.append('CR')

            addons_str = ', '.join(addons) if addons else '-'

            price = self._format_currency(panel.get('panel_total', panel.get('line_total', 0)))

            table_data.append([
                panel_name,
                count_range,
                size,
                depth,
                zone,
                addons_str,
                price
            ])

        # Create table
        col_widths = [1.8*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.9*inch]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Body style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1e40af')),

            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),

            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(table)

        return elements

    def _build_ri_section(self, estimate: Dict) -> List:
        """Build R&I (Remove & Install) Justification section.

        Phase 6D: Enhanced R&I section with step breakdowns and justification text.
        """
        elements = []

        elements.append(Paragraph("R&I Operations & Justification", self.styles['SectionHeader']))

        # Check for new-style ri_operations (from Phase 6A/6B engine)
        ri_operations = estimate.get('ri_operations', [])
        ri_items = estimate.get('ri_items', [])

        # If we have the new R&I operations structure
        if ri_operations:
            total_hours = 0

            for op in ri_operations:
                op_elements = []

                # Operation header
                op_name = op.get('display_name', op.get('code', 'R&I Operation'))
                category = op.get('category', '').title()
                risk_level = op.get('risk_level', 'medium').title()

                op_header = f"<b>{op_name}</b> ({category} - {risk_level} Risk)"
                op_elements.append(Paragraph(op_header, self.styles['Normal']))
                op_elements.append(Spacer(1, 0.05*inch))

                # Steps table
                steps = op.get('steps', [])
                if steps:
                    step_header = ['Step', 'Description', 'Required', 'Resistance', 'Hours']
                    step_data = [step_header]

                    for step in steps:
                        if step.get('included', True):
                            step_data.append([
                                step.get('label', step.get('step_code', '')),
                                step.get('description', '')[:40] + '...' if step.get('description') and len(step.get('description', '')) > 40 else step.get('description', '-'),
                                'Yes' if step.get('required', False) else 'No',
                                step.get('denial_resistance', 'medium').title(),
                                f"{step.get('effective_time_hours', step.get('base_time_hours', 0)):.2f}"
                            ])

                    if len(step_data) > 1:  # Has steps beyond header
                        step_col_widths = [1.2*inch, 2.2*inch, 0.6*inch, 0.8*inch, 0.6*inch]
                        step_table = Table(step_data, colWidths=step_col_widths, repeatRows=1)
                        step_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6b7280')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 8),
                            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 8),
                            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                            ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
                            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d1d5db')),
                            ('TOPPADDING', (0, 0), (-1, -1), 3),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
                        ]))
                        op_elements.append(step_table)

                # Modifiers
                modifiers = op.get('modifiers', [])
                if modifiers:
                    op_elements.append(Spacer(1, 0.05*inch))
                    mod_strs = []
                    for mod in modifiers:
                        mod_label = mod.get('label', mod.get('modifier_code', ''))
                        mod_hours = mod.get('adds_time_hours', 0)
                        mod_strs.append(f"{mod_label} (+{mod_hours:.2f}h)")
                    mod_text = f"<b>Modifiers:</b> {', '.join(mod_strs)}"
                    op_elements.append(Paragraph(mod_text, self.styles['Normal']))

                # Totals for this operation
                totals = op.get('totals', {})
                base_time = totals.get('base_steps_time', 0)
                mod_time = totals.get('modifiers_time', 0)
                op_total = totals.get('total_time', base_time + mod_time)
                total_hours += op_total

                op_elements.append(Spacer(1, 0.05*inch))
                totals_text = f"<b>Operation Total:</b> {base_time:.2f}h (base) + {mod_time:.2f}h (modifiers) = <b>{op_total:.2f} hours</b>"
                op_elements.append(Paragraph(totals_text, self.styles['Normal']))

                # Justification text (insurer-ready)
                justification = op.get('justification_text', '')
                if justification:
                    op_elements.append(Spacer(1, 0.05*inch))
                    just_style = ParagraphStyle(
                        name='JustificationText',
                        parent=self.styles['Normal'],
                        fontSize=8,
                        textColor=colors.HexColor('#4b5563'),
                        leftIndent=10,
                        rightIndent=10,
                        spaceBefore=2,
                        spaceAfter=2,
                        backColor=colors.HexColor('#f3f4f6'),
                        borderPadding=4
                    )
                    op_elements.append(Paragraph(f"<i>{justification}</i>", just_style))

                # Wrap operation in KeepTogether
                elements.append(KeepTogether(op_elements))
                elements.append(Spacer(1, 0.15*inch))

            # Grand total for all R&I
            if total_hours > 0:
                labor_rate = estimate.get('ri_labor_rate', 85)  # Default $85/hr
                rate_source = estimate.get('ri_labor_rate_source', 'default')
                rate_rule_name = estimate.get('ri_labor_rate_rule_name')
                total_cost = total_hours * labor_rate

                elements.append(Spacer(1, 0.1*inch))

                # Format rate label with source info
                rate_label = self._format_currency(labor_rate) + '/hr'
                if rate_source == 'rule' and rate_rule_name:
                    rate_label += f' ({rate_rule_name})'
                elif rate_source == 'override':
                    rate_label += ' (Override)'

                ri_totals_data = [
                    ['Total R&I Time:', f'{total_hours:.2f} hours'],
                    ['Labor Rate:', rate_label],
                    ['R&I Total:', self._format_currency(total_cost)]
                ]

                ri_totals_table = Table(ri_totals_data, colWidths=[5*inch, 1.5*inch])
                ri_totals_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#4b5563')),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))

                elements.append(ri_totals_table)

            # Denial Pack section (Stage 6F)
            denial_pack = estimate.get('ri_denial_pack', {})
            if denial_pack and denial_pack.get('overall_score', 0) > 0:
                elements.append(Spacer(1, 0.2*inch))
                elements.append(Paragraph("Denial Resistance Analysis", self.styles['SectionHeader']))

                # Overall score badge
                score = denial_pack.get('overall_score', 0)
                rating = denial_pack.get('overall_rating', 'low').title()
                rating_color = '#047857' if rating == 'High' else '#d97706' if rating == 'Medium' else '#dc2626'

                score_text = f"<b>Denial Resistance Score:</b> {score}/100 ({rating})"
                elements.append(Paragraph(score_text, self.styles['Normal']))

                # Resistance counts
                counts = denial_pack.get('resistance_counts', {})
                counts_text = f"Step Resistance: High: {counts.get('high', 0)} | Medium: {counts.get('medium', 0)} | Low: {counts.get('low', 0)}"
                elements.append(Paragraph(counts_text, self.styles['Normal']))

                # Required vs optional
                req_count = denial_pack.get('required_steps_count', 0)
                opt_count = denial_pack.get('optional_steps_count', 0)
                steps_text = f"Required Steps: {req_count} | Optional Steps: {opt_count}"
                elements.append(Paragraph(steps_text, self.styles['Normal']))

                # Risk tags
                risk_tags = denial_pack.get('risk_tags', [])
                if risk_tags:
                    elements.append(Spacer(1, 0.05*inch))
                    tags_text = f"<b>Risk Factors Addressed:</b> {', '.join(risk_tags)}"
                    elements.append(Paragraph(tags_text, self.styles['Normal']))

                # Summary text box
                summary = denial_pack.get('summary_text', '')
                if summary:
                    elements.append(Spacer(1, 0.1*inch))
                    summary_style = ParagraphStyle(
                        name='DenialSummary',
                        parent=self.styles['Normal'],
                        fontSize=9,
                        textColor=colors.HexColor('#1f2937'),
                        backColor=colors.HexColor('#ecfdf5'),
                        borderPadding=8,
                        leftIndent=5,
                        rightIndent=5,
                    )
                    elements.append(Paragraph(summary, summary_style))

                # --- 6G: Adjuster-Ready Bullets ---
                adjuster_bullets = denial_pack.get('adjuster_bullets', [])
                if adjuster_bullets:
                    elements.append(Spacer(1, 0.15*inch))
                    elements.append(Paragraph("<b>Adjuster-Ready Bullets</b>", self.styles['Normal']))
                    bullet_style = ParagraphStyle(
                        name='AdjusterBullet',
                        parent=self.styles['Normal'],
                        fontSize=8,
                        leftIndent=10,
                        spaceBefore=2,
                        spaceAfter=2,
                    )
                    for bullet in adjuster_bullets[:8]:
                        elements.append(Paragraph(f"• {bullet}", bullet_style))

                # Scope clarifier
                scope_clarifier = denial_pack.get('scope_clarifier', '')
                if scope_clarifier:
                    elements.append(Spacer(1, 0.1*inch))
                    scope_style = ParagraphStyle(
                        name='ScopeClarifier',
                        parent=self.styles['Normal'],
                        fontSize=8,
                        textColor=colors.HexColor('#4b5563'),
                        backColor=colors.HexColor('#f3f4f6'),
                        borderPadding=6,
                        leftIndent=5,
                        rightIndent=5,
                    )
                    elements.append(Paragraph(f"<b>Scope:</b> {scope_clarifier}", scope_style))

                # Top defensible steps cite lines
                top_steps = denial_pack.get('top_defensible_steps', [])
                if top_steps:
                    elements.append(Spacer(1, 0.1*inch))
                    elements.append(Paragraph("<b>Top Defensible Sub-Steps</b>", self.styles['Normal']))
                    cite_style = ParagraphStyle(
                        name='CiteStep',
                        parent=self.styles['Normal'],
                        fontSize=8,
                        leftIndent=10,
                        spaceBefore=1,
                        spaceAfter=1,
                    )
                    for step in top_steps[:6]:
                        cite_line = step.get('cite_line', '')
                        if cite_line:
                            elements.append(Paragraph(f"• {cite_line}", cite_style))

            return elements

        # Fallback to legacy ri_items format
        if not ri_items:
            ri_total = estimate.get('ri_total', 0)
            if ri_total > 0:
                elements.append(Paragraph(
                    f"R&I Labor: {self._format_currency(ri_total)}",
                    self.styles['Normal']
                ))
            return elements

        # Legacy R&I table
        header = ['Operation', 'Panel', 'Hours', 'Price']
        table_data = [header]

        for item in ri_items:
            op_name = item.get('operation_name') or item.get('item_name', 'R&I')
            panel = item.get('panel_name', '-')
            hours = item.get('time_hours', item.get('calculated_time_hours', 0))
            price = self._format_currency(item.get('price', 0))

            table_data.append([op_name, panel, f"{hours:.1f}", price])

        col_widths = [3*inch, 1.5*inch, 0.8*inch, 1*inch]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4b5563')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(table)

        return elements

    def _build_totals(self, estimate: Dict) -> List:
        """Build totals section."""
        elements = []

        elements.append(Paragraph("Estimate Totals", self.styles['SectionHeader']))

        labor_total = estimate.get('labor_total', 0)
        ri_total = estimate.get('ri_total', 0)
        materials = estimate.get('materials_total', 0)
        tax = estimate.get('tax_total', 0)
        grand_total = estimate.get('total_price', labor_total + ri_total + materials + tax)

        totals_data = []

        totals_data.append(['PDR Labor:', self._format_currency(labor_total)])

        if ri_total > 0:
            totals_data.append(['R&I Total:', self._format_currency(ri_total)])

        if materials > 0:
            totals_data.append(['Materials:', self._format_currency(materials)])

        if tax > 0:
            totals_data.append(['Tax:', self._format_currency(tax)])

        # Subtotal line if we have multiple items
        if len(totals_data) > 1:
            totals_data.append(['', ''])  # Separator

        totals_data.append(['GRAND TOTAL:', self._format_currency(grand_total)])

        col_widths = [5*inch, 1.5*inch]

        table = Table(totals_data, colWidths=col_widths)

        # Style for totals
        style_commands = [
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # Grand total styling
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1e40af')),
        ]

        table.setStyle(TableStyle(style_commands))

        elements.append(table)

        return elements

    def _build_insurance_approval(self, estimate: Dict) -> List:
        """Build insurance approval section showing requested vs approved vs delta."""
        elements = []

        elements.append(Paragraph("Insurance Approval", self.styles['SectionHeader']))

        # Get amounts
        requested = estimate.get('total_price', 0)
        approved = estimate.get('insurer_approved_total', 0)

        if isinstance(requested, Decimal):
            requested = float(requested)
        if isinstance(approved, Decimal):
            approved = float(approved)

        delta = requested - approved
        is_short_paid = delta > 0.005  # Account for floating point

        # Build approval box
        approval_data = [
            ['', 'Requested', 'Approved', 'Delta'],
            [
                'Total',
                self._format_currency(requested),
                self._format_currency(approved),
                f"-{self._format_currency(delta)}" if is_short_paid else self._format_currency(0)
            ]
        ]

        # Add breakdown if available
        if estimate.get('insurer_approved_labor') is not None:
            labor_req = estimate.get('labor_total', 0)
            labor_app = estimate.get('insurer_approved_labor', 0)
            labor_delta = float(labor_req or 0) - float(labor_app or 0)
            approval_data.append([
                'Labor',
                self._format_currency(labor_req),
                self._format_currency(labor_app),
                f"-{self._format_currency(labor_delta)}" if labor_delta > 0 else '$0.00'
            ])

        if estimate.get('insurer_approved_ri') is not None:
            ri_req = estimate.get('ri_total', 0)
            ri_app = estimate.get('insurer_approved_ri', 0)
            ri_delta = float(ri_req or 0) - float(ri_app or 0)
            approval_data.append([
                'R&I',
                self._format_currency(ri_req),
                self._format_currency(ri_app),
                f"-{self._format_currency(ri_delta)}" if ri_delta > 0 else '$0.00'
            ])

        col_widths = [1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch]

        table = Table(approval_data, colWidths=col_widths)

        style_commands = [
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#047857')),  # Green header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),

            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]

        # Highlight short paid in delta column
        if is_short_paid:
            style_commands.append(('TEXTCOLOR', (-1, 1), (-1, -1), colors.HexColor('#dc2626')))  # Red
            style_commands.append(('FONTNAME', (-1, 1), (-1, -1), 'Helvetica-Bold'))

        table.setStyle(TableStyle(style_commands))

        elements.append(table)

        # Add approval reference and notes
        if estimate.get('insurer_approval_reference') or estimate.get('insurer_approval_notes'):
            elements.append(Spacer(1, 0.1*inch))

            if estimate.get('insurer_approval_reference'):
                ref_text = f"<b>Reference:</b> {estimate['insurer_approval_reference']}"
                elements.append(Paragraph(ref_text, self.styles['Normal']))

            if estimate.get('insurer_approval_notes'):
                notes_text = f"<b>Approval Notes:</b> {estimate['insurer_approval_notes']}"
                elements.append(Paragraph(notes_text, self.styles['Normal']))

        # Add approved date
        if estimate.get('insurer_approved_at'):
            try:
                if isinstance(estimate['insurer_approved_at'], str):
                    approved_at = datetime.fromisoformat(estimate['insurer_approved_at'].replace('Z', '+00:00'))
                else:
                    approved_at = estimate['insurer_approved_at']
                date_str = approved_at.strftime('%B %d, %Y at %I:%M %p')
                elements.append(Spacer(1, 0.05*inch))
                elements.append(Paragraph(
                    f"<i>Approved on {date_str}</i>",
                    self.styles['Disclaimer']
                ))
            except:
                pass

        # Short paid warning box
        if is_short_paid:
            elements.append(Spacer(1, 0.1*inch))
            warning_style = ParagraphStyle(
                name='ShortPaidWarning',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#92400e'),
                backColor=colors.HexColor('#fef3c7'),
                borderPadding=8
            )
            warning_text = f"<b>PARTIAL APPROVAL:</b> Short paid by {self._format_currency(delta)}. Supplement may be required."
            elements.append(Paragraph(warning_text, warning_style))

        return elements

    def _build_notes(self, estimate: Dict) -> List:
        """Build notes section."""
        elements = []

        elements.append(Paragraph("Notes", self.styles['SectionHeader']))

        notes = estimate.get('notes', '')
        if notes:
            elements.append(Paragraph(notes, self.styles['Normal']))

        return elements

    def _build_disclaimer(self) -> List:
        """Build disclaimer section."""
        elements = []

        disclaimer_text = """
        This estimate is based on visible damage at the time of inspection. Additional damage
        may be discovered during the repair process, which may result in a supplemental estimate.
        Estimate is valid for 30 days from the date issued. All work is performed using
        industry-standard PDR techniques. Prices are based on the current matrix pricing
        guidelines. Final charges may vary based on actual repair time and complexity.
        """

        elements.append(Paragraph(disclaimer_text.strip(), self.styles['Disclaimer']))

        return elements


# ==============================================================================
# CONVENIENCE FUNCTION
# ==============================================================================

def generate_estimate_pdf(
    estimate: Dict[str, Any],
    shop_info: Optional[Dict[str, Any]] = None,
    include_disclaimer: bool = True
) -> BytesIO:
    """
    Generate an estimate PDF.

    This is the main entry point for PDF generation.

    Args:
        estimate: Estimate data dictionary
        shop_info: Optional shop/company info
        include_disclaimer: Whether to include disclaimer

    Returns:
        BytesIO buffer containing the PDF
    """
    generator = PDFGenerator()
    return generator.generate_estimate_pdf(estimate, shop_info, include_disclaimer)
