"""
Hail Impact Report PDF Generator
================================
Generates branded PDF reports showing hail impact history for a location.
Used for insurance adjusters, homeowners, and sales presentations.
"""

import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class HailImpactReportGenerator:
    """Generates PDF hail impact reports."""

    def __init__(self, company_name: str = "HailTracker Pro",
                 company_phone: str = "",
                 company_email: str = "",
                 company_website: str = "",
                 company_logo_path: Optional[str] = None):
        """
        Initialize the report generator.

        Args:
            company_name: Name to display on reports
            company_phone: Contact phone number
            company_email: Contact email
            company_website: Company website URL
            company_logo_path: Path to company logo image
        """
        self.company_name = company_name
        self.company_phone = company_phone
        self.company_email = company_email
        self.company_website = company_website
        self.company_logo_path = company_logo_path

        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")

    def generate_report(
        self,
        location: Dict[str, float],
        events: List[Dict[str, Any]],
        summary: Dict[str, Any],
        address: Optional[str] = None,
        radius_miles: float = 5,
        years_checked: int = 5
    ) -> bytes:
        """
        Generate a PDF hail impact report.

        Args:
            location: Dict with 'lat' and 'lon' keys
            events: List of hail events from check_location API
            summary: Summary stats from check_location API
            address: Optional street address for display
            radius_miles: Search radius used
            years_checked: Number of years searched

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()

        # Create the document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Build story
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            textColor=colors.HexColor('#1e3a5f'),
            alignment=TA_CENTER
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=10,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER
        )

        section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#1e3a5f')
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6
        )

        # Header with company info
        story.append(Paragraph(self.company_name, title_style))
        story.append(Paragraph("HAIL IMPACT REPORT", subtitle_style))

        if self.company_phone or self.company_email:
            contact_parts = []
            if self.company_phone:
                contact_parts.append(self.company_phone)
            if self.company_email:
                contact_parts.append(self.company_email)
            if self.company_website:
                contact_parts.append(self.company_website)
            story.append(Paragraph(" | ".join(contact_parts), subtitle_style))

        story.append(Spacer(1, 0.25*inch))

        # Horizontal line
        story.append(HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#3b82f6'),
            spaceBefore=10,
            spaceAfter=20
        ))

        # Report date
        story.append(Paragraph(
            f"Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            ParagraphStyle('ReportDate', parent=normal_style, alignment=TA_RIGHT, fontSize=10)
        ))

        story.append(Spacer(1, 0.2*inch))

        # Location Information Section
        story.append(Paragraph("PROPERTY LOCATION", section_header_style))

        location_info = []
        if address:
            location_info.append(f"<b>Address:</b> {address}")
        location_info.append(f"<b>Coordinates:</b> {location['lat']:.6f}, {location['lon']:.6f}")
        location_info.append(f"<b>Search Radius:</b> {radius_miles} miles")
        location_info.append(f"<b>Years Analyzed:</b> {years_checked}")

        for info in location_info:
            story.append(Paragraph(info, normal_style))

        story.append(Spacer(1, 0.3*inch))

        # Summary Section
        story.append(Paragraph("HAIL IMPACT SUMMARY", section_header_style))

        was_hit = len(events) > 0

        if was_hit:
            # Summary box with key stats
            summary_data = [
                ['Total Hail Events', 'Maximum Hail Size', 'Most Recent Event'],
                [
                    str(summary.get('total_events', len(events))),
                    f"{summary.get('max_hail_size', 0):.2f}\"",
                    summary.get('most_recent', 'N/A')
                ]
            ]

            summary_table = Table(summary_data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 14),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef3c7')),
                ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#1e3a5f')),
                ('INNERGRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(summary_table)

            story.append(Spacer(1, 0.2*inch))

            # Impact assessment
            max_size = summary.get('max_hail_size', 0)
            if max_size >= 2.0:
                severity = "SEVERE"
                impact_text = (
                    f"This location has experienced <b>SEVERE</b> hail damage with stones "
                    f"up to {max_size:.2f} inches in diameter. Hail of this size causes "
                    f"significant damage to vehicles, roofing, siding, and outdoor equipment. "
                    f"Insurance claims are highly likely for affected properties."
                )
                severity_color = colors.HexColor('#dc2626')
            elif max_size >= 1.0:
                severity = "MODERATE"
                impact_text = (
                    f"This location has experienced <b>MODERATE</b> hail damage with stones "
                    f"up to {max_size:.2f} inches in diameter. Hail of this size typically causes "
                    f"dents to vehicles and may damage roofing materials and outdoor fixtures."
                )
                severity_color = colors.HexColor('#ea580c')
            elif max_size >= 0.5:
                severity = "MINOR"
                impact_text = (
                    f"This location has experienced <b>MINOR</b> hail with stones "
                    f"up to {max_size:.2f} inches in diameter. While less likely to cause "
                    f"major damage, soft metals and older roofing materials may be affected."
                )
                severity_color = colors.HexColor('#ca8a04')
            else:
                severity = "MINIMAL"
                impact_text = (
                    f"This location has experienced minimal hail activity with stones "
                    f"under 0.5 inches. Damage is unlikely but may still affect "
                    f"sensitive equipment or older materials."
                )
                severity_color = colors.HexColor('#16a34a')

            story.append(Paragraph(impact_text, normal_style))

            story.append(Spacer(1, 0.3*inch))

            # Events by Year
            if summary.get('by_year'):
                story.append(Paragraph("EVENTS BY YEAR", section_header_style))

                by_year = summary['by_year']
                year_data = [['Year', 'Number of Events']]
                for year in sorted(by_year.keys(), reverse=True):
                    year_data.append([str(year), str(by_year[year])])

                year_table = Table(year_data, colWidths=[2*inch, 2*inch])
                year_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 11),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(year_table)

            story.append(Spacer(1, 0.3*inch))

            # Detailed Event List
            story.append(Paragraph("DETAILED EVENT HISTORY", section_header_style))

            event_data = [['Date', 'Event Name', 'Hail Size', 'Distance']]
            for event in events:
                event_data.append([
                    event.get('event_date', 'N/A'),
                    event.get('event_name', 'Unknown Event')[:40],
                    f"{event.get('hail_size_inches', 0):.2f}\"",
                    f"{event.get('distance_miles', 0):.1f} mi"
                ])

            event_table = Table(event_data, colWidths=[1.3*inch, 3.2*inch, 1*inch, 1*inch])
            event_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(event_table)

        else:
            # No hail found
            no_hail_style = ParagraphStyle(
                'NoHail',
                parent=normal_style,
                fontSize=14,
                textColor=colors.HexColor('#16a34a'),
                alignment=TA_CENTER,
                spaceBefore=20,
                spaceAfter=20
            )
            story.append(Paragraph(
                f"NO SIGNIFICANT HAIL EVENTS FOUND within {radius_miles} miles "
                f"of this location in the past {years_checked} years.",
                no_hail_style
            ))

            story.append(Paragraph(
                "Based on our analysis of NOAA Storm Events Database records, this location "
                "has not experienced documented hail events during the analyzed time period. "
                "This does not guarantee that hail damage has not occurred, as some events "
                "may not be recorded in the database.",
                normal_style
            ))

        story.append(Spacer(1, 0.5*inch))

        # Data Source & Disclaimer
        story.append(Paragraph("DATA SOURCE & DISCLAIMER", section_header_style))

        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=normal_style,
            fontSize=9,
            textColor=colors.HexColor('#6b7280')
        )

        story.append(Paragraph(
            "This report is based on data from the NOAA Storm Events Database and other public "
            "sources. While we strive for accuracy, this report should be used for informational "
            "purposes only and does not constitute a guarantee of hail damage or lack thereof. "
            "Actual damage assessment should be performed by a qualified professional.",
            disclaimer_style
        ))

        story.append(Spacer(1, 0.2*inch))

        story.append(Paragraph(
            f"Report ID: HIR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{abs(hash(str(location)))%10000:04d}",
            ParagraphStyle('ReportID', parent=disclaimer_style, alignment=TA_CENTER)
        ))

        # Build PDF
        doc.build(story)

        buffer.seek(0)
        return buffer.getvalue()


def generate_hail_impact_report(
    location: Dict[str, float],
    events: List[Dict[str, Any]],
    summary: Dict[str, Any],
    address: Optional[str] = None,
    radius_miles: float = 5,
    years_checked: int = 5,
    company_name: str = "HailTracker Pro",
    company_phone: str = "",
    company_email: str = "",
    company_website: str = ""
) -> bytes:
    """
    Convenience function to generate a hail impact report.

    Args:
        location: Dict with 'lat' and 'lon' keys
        events: List of hail events
        summary: Summary statistics
        address: Optional street address
        radius_miles: Search radius
        years_checked: Years of history
        company_name: Company name for branding
        company_phone: Contact phone
        company_email: Contact email
        company_website: Company website

    Returns:
        PDF content as bytes
    """
    generator = HailImpactReportGenerator(
        company_name=company_name,
        company_phone=company_phone,
        company_email=company_email,
        company_website=company_website
    )

    return generator.generate_report(
        location=location,
        events=events,
        summary=summary,
        address=address,
        radius_miles=radius_miles,
        years_checked=years_checked
    )
