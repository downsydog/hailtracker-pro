"""
PDR Pro Estimating - Professional PDF Generator
Generate professional estimate PDFs with all PDR-specific details.

FEATURES:
- Company header with logo
- Complete estimate summary
- Panel-by-panel PDR repairs
- R/I labor section with vehicle-specific times
- Parts section with markup
- Photo pages with damage markup
- Authorization/signature page
- Insurance supplement support

DEPENDENCIES:
- reportlab (pip install reportlab)
- Pillow for image handling
"""

import os
from typing import Optional, Dict, List, Any
from datetime import datetime
from io import BytesIO

# Try to import reportlab - provide helpful error if not installed
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, HRFlowable
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF generation disabled.")
    print("Install with: pip install reportlab")


class EstimatePDFManager:
    """
    Professional PDF generator for PDR estimates.

    Creates detailed, insurance-ready estimate documents.
    """

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize PDF manager"""
        self.db_path = db_path

        # Company info - should be loaded from settings
        self.company_info = {
            'name': 'PDR Pro',
            'address': '123 Main Street',
            'city_state_zip': 'Anytown, TX 75001',
            'phone': '(555) 123-4567',
            'email': 'info@pdrpro.com',
            'website': 'www.pdrpro.com',
            'logo_path': None  # Path to logo image
        }

        # PDF styles
        self.styles = None
        if REPORTLAB_AVAILABLE:
            self._setup_styles()

    def _setup_styles(self):
        """Set up PDF styles"""
        self.styles = getSampleStyleSheet()

        # Custom styles
        self.styles.add(ParagraphStyle(
            'CompanyName',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=6
        ))

        self.styles.add(ParagraphStyle(
            'EstimateTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_CENTER,
            spaceAfter=12
        ))

        self.styles.add(ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2d3748'),
            spaceBefore=12,
            spaceAfter=6,
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=4
        ))

        self.styles.add(ParagraphStyle(
            'SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#718096')
        ))

        self.styles.add(ParagraphStyle(
            'TotalLabel',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))

        self.styles.add(ParagraphStyle(
            'GrandTotal',
            parent=self.styles['Normal'],
            fontSize=16,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a365d'),
            alignment=TA_RIGHT
        ))

    def generate_estimate_pdf(
        self,
        export_data: Dict,
        output_path: str = None,
        include_photos: bool = True,
        include_signature_page: bool = True
    ) -> str:
        """
        Generate a professional estimate PDF.

        Args:
            export_data: Data from estimate_manager.get_estimate_for_export()
            output_path: Where to save the PDF (optional)
            include_photos: Include photo pages
            include_signature_page: Include authorization page

        Returns:
            Path to generated PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab not installed. Run: pip install reportlab")

        # Generate output path if not provided
        if not output_path:
            estimate_number = export_data['estimate']['number']
            output_dir = "output/estimates"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"{estimate_number.replace('/', '-')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            )

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        # Build PDF elements
        elements = []

        # Company header
        elements.extend(self._build_header(export_data))

        # Estimate info section
        elements.extend(self._build_estimate_info(export_data))

        # Customer and vehicle info
        elements.extend(self._build_customer_vehicle_section(export_data))

        # Damage summary
        if export_data.get('panel_damage'):
            elements.extend(self._build_damage_summary(export_data))

        # PDR Labor section
        elements.extend(self._build_pdr_labor_section(export_data))

        # R/I Labor section
        if export_data['line_items'].get('ri_items'):
            elements.extend(self._build_ri_section(export_data))

        # Parts section
        if export_data['line_items'].get('parts'):
            elements.extend(self._build_parts_section(export_data))

        # Totals
        elements.extend(self._build_totals_section(export_data))

        # Notes and terms
        elements.extend(self._build_notes_section(export_data))

        # Photo pages
        if include_photos and export_data.get('photos'):
            elements.append(PageBreak())
            elements.extend(self._build_photo_pages(export_data))

        # Signature/authorization page
        if include_signature_page:
            elements.append(PageBreak())
            elements.extend(self._build_signature_page(export_data))

        # Build PDF
        doc.build(elements)

        print(f"[OK] Generated estimate PDF: {output_path}")

        return output_path

    def _build_header(self, data: Dict) -> List:
        """Build company header"""
        elements = []

        # Company name and info
        header_data = [
            [
                Paragraph(self.company_info['name'], self.styles['CompanyName']),
                ''
            ],
            [
                Paragraph(self.company_info['address'], self.styles['Normal']),
                Paragraph(
                    f"<b>ESTIMATE</b><br/>{data['estimate']['number']}",
                    self.styles['Normal']
                )
            ],
            [
                Paragraph(self.company_info['city_state_zip'], self.styles['Normal']),
                Paragraph(
                    f"Date: {data['estimate']['created_date']}",
                    self.styles['Normal']
                )
            ],
            [
                Paragraph(
                    f"Phone: {self.company_info['phone']}",
                    self.styles['Normal']
                ),
                Paragraph(
                    f"Expires: {data['estimate']['expires_date']}",
                    self.styles['Normal']
                )
            ]
        ]

        header_table = Table(header_data, colWidths=[4*inch, 3*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 0.25*inch))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a365d')))
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_estimate_info(self, data: Dict) -> List:
        """Build estimate status info"""
        elements = []

        estimate = data['estimate']
        status = estimate['status']

        # Status badge color
        status_colors = {
            'DRAFT': '#718096',
            'SENT': '#3182ce',
            'VIEWED': '#38a169',
            'APPROVED': '#2f855a',
            'DECLINED': '#c53030'
        }
        status_color = status_colors.get(status, '#718096')

        info_text = f"<b>Status:</b> <font color='{status_color}'>{status}</font>"

        if estimate.get('approved_date'):
            info_text += f" &nbsp;|&nbsp; <b>Approved:</b> {estimate['approved_date']}"

        elements.append(Paragraph(info_text, self.styles['Normal']))
        elements.append(Spacer(1, 0.15*inch))

        return elements

    def _build_customer_vehicle_section(self, data: Dict) -> List:
        """Build customer and vehicle info section"""
        elements = []

        customer = data.get('customer', {})
        vehicle = data.get('vehicle', {})
        insurance = data.get('insurance')

        # Build customer info
        customer_lines = []
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        if name:
            customer_lines.append(f"<b>{name}</b>")
        if customer.get('street'):
            customer_lines.append(customer['street'])
        city_state = []
        if customer.get('city'):
            city_state.append(customer['city'])
        if customer.get('state'):
            city_state.append(customer['state'])
        if customer.get('zip'):
            city_state.append(customer['zip'])
        if city_state:
            customer_lines.append(', '.join(city_state))
        if customer.get('phone'):
            customer_lines.append(f"Phone: {customer['phone']}")
        if customer.get('email'):
            customer_lines.append(f"Email: {customer['email']}")

        # Build vehicle info
        vehicle_lines = []
        year_make_model = []
        if vehicle.get('year'):
            year_make_model.append(str(vehicle['year']))
        if vehicle.get('make'):
            year_make_model.append(vehicle['make'])
        if vehicle.get('model'):
            year_make_model.append(vehicle['model'])
        if year_make_model:
            vehicle_lines.append(f"<b>{' '.join(year_make_model)}</b>")
        if vehicle.get('trim'):
            vehicle_lines.append(f"Trim: {vehicle['trim']}")
        if vehicle.get('body_style'):
            vehicle_lines.append(f"Body: {vehicle['body_style']}")
        if vehicle.get('color'):
            vehicle_lines.append(f"Color: {vehicle['color']}")
        if vehicle.get('vin'):
            vehicle_lines.append(f"VIN: {vehicle['vin']}")

        # Build insurance info
        insurance_lines = []
        if insurance:
            insurance_lines.append(f"<b>{insurance.get('name', 'Insurance')}</b>")
            if insurance.get('claim_number'):
                insurance_lines.append(f"Claim #: {insurance['claim_number']}")
            if insurance.get('adjuster_name'):
                insurance_lines.append(f"Adjuster: {insurance['adjuster_name']}")
            if insurance.get('deductible'):
                insurance_lines.append(f"Deductible: ${insurance['deductible']:,.2f}")

        # Create table
        col_data = [
            [
                Paragraph("<b>CUSTOMER</b>", self.styles['Normal']),
                Paragraph("<b>VEHICLE</b>", self.styles['Normal']),
                Paragraph("<b>INSURANCE</b>", self.styles['Normal']) if insurance else ''
            ],
            [
                Paragraph('<br/>'.join(customer_lines), self.styles['Normal']),
                Paragraph('<br/>'.join(vehicle_lines), self.styles['Normal']),
                Paragraph('<br/>'.join(insurance_lines), self.styles['Normal']) if insurance else ''
            ]
        ]

        col_widths = [2.5*inch, 2.5*inch, 2.5*inch] if insurance else [3.5*inch, 3.5*inch]

        info_table = Table(col_data, colWidths=col_widths)
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f7fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_damage_summary(self, data: Dict) -> List:
        """Build damage summary section"""
        elements = []

        elements.append(Paragraph("DAMAGE SUMMARY", self.styles['SectionHeader']))

        panel_damage = data.get('panel_damage', [])

        if not panel_damage:
            elements.append(Paragraph("No damage data available.", self.styles['Normal']))
            return elements

        # Build table
        table_data = [['Panel', 'Dent Count', 'Avg Size', 'Difficult Access']]

        total_dents = 0
        for panel in panel_damage:
            panel_name = panel['panel'].replace('_', ' ').title()
            dent_count = panel.get('dent_count', 0)
            avg_size = panel.get('avg_size', 0)
            difficult = panel.get('difficult_count', 0)

            total_dents += dent_count

            # Size description
            if avg_size < 0.25:
                size_desc = "Dime"
            elif avg_size < 0.5:
                size_desc = "Nickel"
            elif avg_size < 1.0:
                size_desc = "Quarter"
            else:
                size_desc = "Half Dollar+"

            table_data.append([
                panel_name,
                str(dent_count),
                size_desc,
                f"{difficult} dents" if difficult > 0 else "-"
            ])

        # Total row
        table_data.append(['TOTAL', str(total_dents), '', ''])

        damage_table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 2*inch])
        damage_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f7fafc')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(damage_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_pdr_labor_section(self, data: Dict) -> List:
        """Build PDR labor section"""
        elements = []

        elements.append(Paragraph("PDR LABOR", self.styles['SectionHeader']))

        pdr_items = data['line_items'].get('pdr_labor', [])

        if not pdr_items:
            elements.append(Paragraph("No PDR labor items.", self.styles['Normal']))
            return elements

        # Build table
        table_data = [['Description', 'Qty', 'Unit Price', 'Total']]

        for item in pdr_items:
            if item.get('type', '').upper() != 'LABOR':
                continue

            table_data.append([
                item.get('description', ''),
                f"{item.get('quantity', 1):.1f}",
                f"${item.get('unit_price', 0):,.2f}",
                f"${item.get('total', 0):,.2f}"
            ])

        # Subtotal
        pdr_total = sum(i.get('total', 0) for i in pdr_items if i.get('type', '').upper() == 'LABOR')
        table_data.append(['', '', 'PDR Labor Total:', f"${pdr_total:,.2f}"])

        pdr_table = Table(table_data, colWidths=[3.5*inch, 1*inch, 1.25*inch, 1.25*inch])
        pdr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
            ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (2, -1), (-1, -1), colors.HexColor('#edf2f7')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(pdr_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_ri_section(self, data: Dict) -> List:
        """Build R/I labor section"""
        elements = []

        elements.append(Paragraph("R/I LABOR (Remove & Install)", self.styles['SectionHeader']))

        ri_items = data['line_items'].get('ri_items', [])

        if not ri_items:
            elements.append(Paragraph("No R/I labor items.", self.styles['Normal']))
            return elements

        # Build table
        table_data = [['Operation', 'Panel', 'Hours', 'Rate', 'Total']]

        for item in ri_items:
            table_data.append([
                item.get('operation_name', item.get('code', '')),
                (item.get('panel_name', '') or '').replace('_', ' ').title(),
                f"{item.get('hours', 0):.1f}",
                f"${item.get('rate', 0):,.2f}",
                f"${item.get('line_total', 0):,.2f}"
            ])

        # Subtotal
        ri_total = sum(i.get('line_total', 0) for i in ri_items)
        table_data.append(['', '', '', 'R/I Labor Total:', f"${ri_total:,.2f}"])

        ri_table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 0.75*inch, 1*inch, 1.25*inch])
        ri_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
            ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (3, -1), (-1, -1), colors.HexColor('#edf2f7')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(ri_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_parts_section(self, data: Dict) -> List:
        """Build parts section"""
        elements = []

        elements.append(Paragraph("PARTS & MATERIALS", self.styles['SectionHeader']))

        parts = data['line_items'].get('parts', [])

        if not parts:
            elements.append(Paragraph("No parts.", self.styles['Normal']))
            return elements

        # Build table
        table_data = [['Part #', 'Description', 'Qty', 'Price', 'Total']]

        for part in parts:
            table_data.append([
                part.get('part_number', '-'),
                part.get('description', part.get('part_name', '')),
                f"{part.get('quantity', 1):.0f}",
                f"${part.get('unit_price', 0):,.2f}",
                f"${part.get('line_total', 0):,.2f}"
            ])

        # Subtotal
        parts_total = sum(p.get('line_total', 0) for p in parts)
        table_data.append(['', '', '', 'Parts Total:', f"${parts_total:,.2f}"])

        parts_table = Table(table_data, colWidths=[1.25*inch, 2.75*inch, 0.75*inch, 1*inch, 1.25*inch])
        parts_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#e2e8f0')),
            ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (3, -1), (-1, -1), colors.HexColor('#edf2f7')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        elements.append(parts_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_totals_section(self, data: Dict) -> List:
        """Build totals section"""
        elements = []

        totals = data.get('totals', {})

        # Build totals table (right-aligned)
        totals_data = [
            ['PDR Labor:', f"${totals.get('pdr_labor', 0):,.2f}"],
            ['R/I Labor:', f"${totals.get('ri_labor', 0):,.2f}"],
            ['Parts & Materials:', f"${totals.get('parts_total', 0) + totals.get('materials', 0):,.2f}"],
            ['Subtotal:', f"${totals.get('subtotal', 0):,.2f}"],
        ]

        if totals.get('tax_rate', 0) > 0:
            totals_data.append([
                f"Tax ({totals['tax_rate']}%):",
                f"${totals.get('tax_amount', 0):,.2f}"
            ])

        totals_data.append(['TOTAL:', f"${totals.get('total', 0):,.2f}"])

        # Add deductible if insurance
        if data.get('insurance') and data['insurance'].get('deductible'):
            deductible = data['insurance']['deductible']
            customer_pays = max(0, totals.get('total', 0) - deductible)
            totals_data.append(['Deductible:', f"${deductible:,.2f}"])
            totals_data.append(['Customer Responsibility:', f"${customer_pays:,.2f}"])

        totals_table = Table(totals_data, colWidths=[2*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1a365d')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))

        # Right-align the totals table
        wrapper_table = Table([[Spacer(1, 1), totals_table]], colWidths=[3.5*inch, 3.5*inch])
        wrapper_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elements.append(wrapper_table)
        elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_notes_section(self, data: Dict) -> List:
        """Build notes and terms section"""
        elements = []

        estimate = data.get('estimate', {})

        if estimate.get('notes'):
            elements.append(Paragraph("NOTES", self.styles['SectionHeader']))
            elements.append(Paragraph(estimate['notes'], self.styles['Normal']))
            elements.append(Spacer(1, 0.25*inch))

        return elements

    def _build_photo_pages(self, data: Dict) -> List:
        """Build photo documentation pages"""
        elements = []

        elements.append(Paragraph("PHOTO DOCUMENTATION", self.styles['EstimateTitle']))
        elements.append(Spacer(1, 0.25*inch))

        photos = data.get('photos', [])

        if not photos:
            elements.append(Paragraph(
                "No photos attached to this estimate.",
                self.styles['Normal']
            ))
            return elements

        # Group photos by type
        photo_groups = {}
        for photo in photos:
            photo_type = photo.get('photo_type', 'Other')
            if photo_type not in photo_groups:
                photo_groups[photo_type] = []
            photo_groups[photo_type].append(photo)

        for photo_type, type_photos in photo_groups.items():
            elements.append(Paragraph(
                photo_type.replace('_', ' ').upper(),
                self.styles['SectionHeader']
            ))

            for photo in type_photos:
                # Photo path
                photo_path = photo.get('file_path', '')

                # Check if photo exists and add it
                if photo_path and os.path.exists(photo_path):
                    try:
                        img = Image(photo_path, width=4*inch, height=3*inch)
                        elements.append(img)
                    except Exception as e:
                        elements.append(Paragraph(
                            f"[Photo not available: {photo_path}]",
                            self.styles['SmallText']
                        ))
                else:
                    elements.append(Paragraph(
                        f"[Photo reference: {photo_path or 'No path'}]",
                        self.styles['SmallText']
                    ))

                # Photo caption
                caption_parts = []
                if photo.get('panel_name'):
                    caption_parts.append(photo['panel_name'].replace('_', ' ').title())
                if photo.get('notes'):
                    caption_parts.append(photo['notes'])

                if caption_parts:
                    elements.append(Paragraph(
                        ' - '.join(caption_parts),
                        self.styles['SmallText']
                    ))

                elements.append(Spacer(1, 0.15*inch))

        return elements

    def _build_signature_page(self, data: Dict) -> List:
        """Build authorization/signature page"""
        elements = []

        elements.append(Paragraph("AUTHORIZATION", self.styles['EstimateTitle']))
        elements.append(Spacer(1, 0.25*inch))

        estimate = data.get('estimate', {})
        totals = data.get('totals', {})
        customer = data.get('customer', {})

        # Authorization text
        auth_text = f"""
        I, the undersigned, authorize {self.company_info['name']} to perform paintless dent repair
        and related services as described in Estimate #{estimate.get('number', '')}.

        I understand and agree to the following:

        1. The total estimated cost is ${totals.get('total', 0):,.2f}

        2. A supplement may be required if additional damage is discovered during the repair process.

        3. I authorize my insurance company to pay {self.company_info['name']} directly for covered repairs.

        4. I am responsible for any deductible and any amounts not covered by insurance.

        5. {self.company_info['name']} warrants all PDR work for as long as I own this vehicle.

        6. This estimate is valid for 30 days from the date issued.
        """

        elements.append(Paragraph(auth_text, self.styles['Normal']))
        elements.append(Spacer(1, 0.5*inch))

        # Signature lines
        sig_data = [
            ['Customer Name (Print):', '_' * 40, 'Date:', '_' * 20],
            ['', '', '', ''],
            ['Customer Signature:', '_' * 40, '', ''],
        ]

        sig_table = Table(sig_data, colWidths=[1.5*inch, 3*inch, 0.75*inch, 1.75*inch])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
        ]))

        elements.append(sig_table)
        elements.append(Spacer(1, 0.5*inch))

        # Insurance assignment if applicable
        if data.get('insurance'):
            elements.append(Paragraph("INSURANCE ASSIGNMENT", self.styles['SectionHeader']))

            assignment_text = f"""
            I hereby assign all insurance benefits for this claim to {self.company_info['name']}.
            I authorize my insurance company to pay {self.company_info['name']} directly
            for all covered repairs related to Claim #{data['insurance'].get('claim_number', '')}.
            """

            elements.append(Paragraph(assignment_text, self.styles['Normal']))
            elements.append(Spacer(1, 0.25*inch))

            assign_data = [
                ['Policyholder Signature:', '_' * 40, 'Date:', '_' * 20],
            ]

            assign_table = Table(assign_data, colWidths=[1.75*inch, 3*inch, 0.75*inch, 1.5*inch])
            assign_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                ('TOPPADDING', (0, 0), (-1, -1), 20),
            ]))

            elements.append(assign_table)

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(
            f"{self.company_info['name']} | {self.company_info['phone']} | {self.company_info['email']}",
            self.styles['SmallText']
        ))

        return elements

    def set_company_info(self, company_info: Dict):
        """
        Set company information for PDF header.

        Args:
            company_info: Dict with name, address, city_state_zip, phone, email, logo_path
        """
        self.company_info.update(company_info)

    def generate_comparison_report_pdf(
        self,
        comparison_data: Dict,
        output_path: str = None
    ) -> str:
        """
        Generate a comparison report PDF for insurance negotiations.

        Args:
            comparison_data: Data from comparables_manager.get_comparable_for_negotiation()
            output_path: Where to save the PDF

        Returns:
            Path to generated PDF
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab not installed. Run: pip install reportlab")

        if not output_path:
            output_dir = "output/reports"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        elements = []

        # Title
        elements.append(Paragraph("HISTORICAL COMPARABLE ANALYSIS", self.styles['EstimateTitle']))
        elements.append(Spacer(1, 0.25*inch))

        # Vehicle info
        elements.append(Paragraph(
            f"<b>Vehicle:</b> {comparison_data.get('vehicle', 'Unknown')}",
            self.styles['Normal']
        ))
        elements.append(Paragraph(
            f"<b>This Estimate:</b> ${comparison_data.get('this_estimate', 0):,.2f}",
            self.styles['Normal']
        ))
        elements.append(Spacer(1, 0.25*inch))

        # Comparison stats
        elements.append(Paragraph("COMPARABLE STATISTICS", self.styles['SectionHeader']))

        stats_data = [
            ['Comparables Found:', str(comparison_data.get('comparables_found', 0))],
            ['Average Estimate:', f"${comparison_data.get('average_estimate', 0):,.2f}"],
            ['Average Approved:', f"${comparison_data.get('average_approved', 0):,.2f}"],
            ['Average Approval Rate:', f"{comparison_data.get('average_approval_rate', 0):.1f}%"],
            ['Variance from Average:', f"{comparison_data.get('variance_from_average', 0):+.1f}%"],
        ]

        stats_table = Table(stats_data, colWidths=[2.5*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f7fafc')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(stats_table)
        elements.append(Spacer(1, 0.25*inch))

        # Negotiation points
        if comparison_data.get('negotiation_points'):
            elements.append(Paragraph("NEGOTIATION POINTS", self.styles['SectionHeader']))

            for point in comparison_data['negotiation_points']:
                elements.append(Paragraph(f"• {point}", self.styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            self.styles['SmallText']
        ))

        doc.build(elements)

        print(f"[OK] Generated comparison report: {output_path}")

        return output_path
