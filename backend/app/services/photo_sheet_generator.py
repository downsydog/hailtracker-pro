"""
Photo Sheet PDF Generator
=========================

Generates insurance-ready photo sheet PDFs for PDR estimates.
Photos are grouped by panel with captions and timestamps.

Features:
- Grid layout (2x2 photos per page)
- Panel headers with severity indicators
- Supplement evidence badges
- Graceful handling of missing images
- Multi-page support with repeated headers
"""

from io import BytesIO
from datetime import datetime
from typing import Any, Dict, List, Optional
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, Flowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.utils import ImageReader

# Try to import PIL for image processing
try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import requests for URL fetching
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Page layout
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 0.5 * inch
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)
CONTENT_HEIGHT = PAGE_HEIGHT - (2 * MARGIN) - (0.75 * inch)  # Leave room for footer

# Photo grid layout
PHOTOS_PER_ROW = 2
ROWS_PER_PAGE = 2
PHOTOS_PER_PAGE = PHOTOS_PER_ROW * ROWS_PER_PAGE

# Photo cell dimensions
CELL_WIDTH = CONTENT_WIDTH / PHOTOS_PER_ROW
CELL_HEIGHT = (CONTENT_HEIGHT - (1.5 * inch)) / ROWS_PER_PAGE  # Leave room for headers
PHOTO_MAX_WIDTH = CELL_WIDTH - (0.3 * inch)
PHOTO_MAX_HEIGHT = CELL_HEIGHT - (0.6 * inch)  # Leave room for caption

# Max image dimension for memory safety
MAX_IMAGE_DIMENSION = 1200

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


# ==============================================================================
# HELPER CLASSES
# ==============================================================================

class PlaceholderImage(Flowable):
    """Placeholder for missing/broken images."""

    def __init__(self, width, height, photo_id=None, message="Image unavailable"):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.photo_id = photo_id
        self.message = message

    def draw(self):
        # Draw border
        self.canv.setStrokeColor(colors.HexColor('#d1d5db'))
        self.canv.setFillColor(colors.HexColor('#f3f4f6'))
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=1)

        # Draw X pattern
        self.canv.setStrokeColor(colors.HexColor('#9ca3af'))
        self.canv.line(0, 0, self.width, self.height)
        self.canv.line(0, self.height, self.width, 0)

        # Draw message
        self.canv.setFillColor(colors.HexColor('#6b7280'))
        self.canv.setFont('Helvetica', 9)
        text = self.message
        if self.photo_id:
            text = f"{self.message} (ID: {self.photo_id})"
        text_width = self.canv.stringWidth(text, 'Helvetica', 9)
        self.canv.drawString(
            (self.width - text_width) / 2,
            self.height / 2 - 4,
            text
        )


# ==============================================================================
# IMAGE LOADING UTILITIES
# ==============================================================================

def load_image_from_path(file_path: str, max_dim: int = MAX_IMAGE_DIMENSION) -> Optional[BytesIO]:
    """Load and resize image from local file path."""
    if not os.path.exists(file_path):
        return None

    try:
        if HAS_PIL:
            img = PILImage.open(file_path)
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            # Resize if too large
            if max(img.size) > max_dim:
                ratio = max_dim / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, PILImage.Resampling.LANCZOS)
            # Save to buffer
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            return buffer
        else:
            # Without PIL, just read the file directly
            with open(file_path, 'rb') as f:
                return BytesIO(f.read())
    except Exception as e:
        print(f"Error loading image from {file_path}: {e}")
        return None


def load_image_from_url(url: str, max_dim: int = MAX_IMAGE_DIMENSION) -> Optional[BytesIO]:
    """Load and resize image from URL."""
    if not HAS_REQUESTS:
        return None

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        if HAS_PIL:
            img = PILImage.open(BytesIO(response.content))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            if max(img.size) > max_dim:
                ratio = max_dim / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, PILImage.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            return buffer
        else:
            return BytesIO(response.content)
    except Exception as e:
        print(f"Error loading image from URL {url}: {e}")
        return None


def load_image(file_path: str) -> Optional[BytesIO]:
    """Load image from path or URL."""
    if file_path.startswith(('http://', 'https://')):
        return load_image_from_url(file_path)
    else:
        return load_image_from_path(file_path)


def get_image_dimensions(image_buffer: BytesIO, max_width: float, max_height: float) -> tuple:
    """Calculate image dimensions that fit within bounds while preserving aspect ratio."""
    try:
        image_buffer.seek(0)
        reader = ImageReader(image_buffer)
        img_width, img_height = reader.getSize()

        # Calculate scaling
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        ratio = min(width_ratio, height_ratio)

        return img_width * ratio, img_height * ratio
    except Exception:
        return max_width * 0.8, max_height * 0.8


# ==============================================================================
# PHOTO SHEET GENERATOR CLASS
# ==============================================================================

class PhotoSheetGenerator:
    """Generates photo sheet PDFs for PDR estimates."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.page_count = 0

    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='PhotoSheetTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=6,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='PanelHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.white,
            backColor=colors.HexColor('#1e40af'),
            borderPadding=(4, 8, 4, 8)
        ))

        self.styles.add(ParagraphStyle(
            name='PhotoCaption',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#4b5563'),
            alignment=TA_CENTER,
            spaceBefore=2
        ))

        self.styles.add(ParagraphStyle(
            name='EvidenceBadge',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#b91c1c'),
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='NoPhotos',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER,
            spaceBefore=72,
            spaceAfter=24
        ))

    def _get_panel_name(self, panel_id: str) -> str:
        """Get display name for a panel."""
        if not panel_id:
            return 'Unassigned'
        return PANEL_NAMES.get(panel_id, panel_id.replace('_', ' ').title())

    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return ''
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = timestamp
            return dt.strftime('%m/%d/%Y %I:%M %p')
        except:
            return str(timestamp)

    def generate_photo_sheet(
        self,
        estimate: Dict[str, Any],
        photos: List[Dict[str, Any]],
        shop_info: Optional[Dict[str, Any]] = None
    ) -> BytesIO:
        """
        Generate a photo sheet PDF.

        Args:
            estimate: Estimate data dictionary
            photos: List of photo dictionaries with:
                - id
                - file_path (local path or URL)
                - panel_name (nullable)
                - caption (optional)
                - created_at (optional)
                - is_supplement_evidence (optional)
            shop_info: Optional shop/company info

        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=MARGIN,
            leftMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=0.75 * inch
        )

        story = []

        # Build header
        story.extend(self._build_header(estimate, shop_info, len(photos)))
        story.append(Spacer(1, 0.3 * inch))

        if not photos:
            # No photos - generate single page with message
            story.append(Paragraph(
                "No photos attached to this estimate.",
                self.styles['NoPhotos']
            ))
            story.append(Paragraph(
                "Photos can be added during the inspection process.",
                self.styles['Normal']
            ))
        else:
            # Group photos by panel
            grouped = self._group_photos_by_panel(photos)

            # Generate photo sections
            for panel_name, panel_photos in grouped:
                story.extend(self._build_panel_section(panel_name, panel_photos))

        # Build PDF
        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)

        buffer.seek(0)
        return buffer

    def _add_footer(self, canvas, doc):
        """Add footer to each page."""
        canvas.saveState()

        page_num = canvas.getPageNumber()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#9ca3af'))

        # Left: timestamp
        canvas.drawString(MARGIN, 0.4 * inch, f"Generated: {timestamp}")

        # Center: system name
        canvas.drawCentredString(PAGE_WIDTH / 2, 0.4 * inch, "HailTracker Pro")

        # Right: page number
        canvas.drawRightString(PAGE_WIDTH - MARGIN, 0.4 * inch, f"Page {page_num}")

        canvas.restoreState()

    def _build_header(self, estimate: Dict, shop_info: Optional[Dict], photo_count: int) -> List:
        """Build the header section."""
        elements = []

        # Title
        title = "PHOTO SHEET"
        if shop_info and shop_info.get('company_name'):
            title = f"{shop_info['company_name']} - PHOTO SHEET"

        elements.append(Paragraph(title, self.styles['PhotoSheetTitle']))
        elements.append(Spacer(1, 0.1 * inch))

        # Estimate info
        estimate_number = estimate.get('estimate_number', 'N/A')
        date_str = datetime.now().strftime('%B %d, %Y')

        # Vehicle info
        year = estimate.get('vehicle_year', '')
        make = estimate.get('vehicle_make', '')
        model = estimate.get('vehicle_model', '')
        vin = estimate.get('vin') or estimate.get('vehicle_vin', '')
        vehicle_str = f"{year} {make} {model}".strip() or 'N/A'

        # Customer info
        customer_name = estimate.get('customer_name', 'N/A')

        # Claim info
        claim_number = estimate.get('claim_number', '')
        insurance = estimate.get('insurance_carrier', '')

        # Build info table
        info_data = [
            [
                Paragraph(f"<b>Estimate #:</b> {estimate_number}", self.styles['Normal']),
                Paragraph(f"<b>Date:</b> {date_str}", self.styles['Normal']),
            ],
            [
                Paragraph(f"<b>Customer:</b> {customer_name}", self.styles['Normal']),
                Paragraph(f"<b>Photos:</b> {photo_count}", self.styles['Normal']),
            ],
            [
                Paragraph(f"<b>Vehicle:</b> {vehicle_str}", self.styles['Normal']),
                Paragraph(f"<b>VIN:</b> {vin or 'N/A'}", self.styles['Normal']),
            ]
        ]

        if claim_number or insurance:
            info_data.append([
                Paragraph(f"<b>Claim #:</b> {claim_number or 'N/A'}", self.styles['Normal']),
                Paragraph(f"<b>Insurance:</b> {insurance or 'N/A'}", self.styles['Normal']),
            ])

        info_table = Table(info_data, colWidths=[CONTENT_WIDTH / 2, CONTENT_WIDTH / 2])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elements.append(info_table)

        return elements

    def _group_photos_by_panel(self, photos: List[Dict]) -> List[tuple]:
        """Group photos by panel, with unassigned last."""
        grouped = {}

        for photo in photos:
            panel = photo.get('panel_name') or 'unassigned'
            if panel not in grouped:
                grouped[panel] = []
            grouped[panel].append(photo)

        # Sort photos within each group by created_at
        for panel in grouped:
            grouped[panel].sort(key=lambda p: p.get('created_at', ''))

        # Sort panels alphabetically, with unassigned last
        sorted_panels = []
        for panel in sorted(grouped.keys()):
            if panel != 'unassigned':
                sorted_panels.append((panel, grouped[panel]))

        if 'unassigned' in grouped:
            sorted_panels.append(('unassigned', grouped['unassigned']))

        return sorted_panels

    def _build_panel_section(self, panel_name: str, photos: List[Dict]) -> List:
        """Build a section for a single panel's photos."""
        elements = []

        # Panel header
        display_name = self._get_panel_name(panel_name)
        photo_count = len(photos)

        header_table = Table(
            [[Paragraph(f"<b>{display_name}</b> ({photo_count} photo{'s' if photo_count != 1 else ''})",
                       self.styles['Normal'])]],
            colWidths=[CONTENT_WIDTH]
        )
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 0.1 * inch))

        # Build photo grid
        elements.extend(self._build_photo_grid(photos))

        elements.append(Spacer(1, 0.2 * inch))

        return elements

    def _build_photo_grid(self, photos: List[Dict]) -> List:
        """Build grid of photos."""
        elements = []

        # Process photos in groups of PHOTOS_PER_PAGE
        for i in range(0, len(photos), PHOTOS_PER_PAGE):
            page_photos = photos[i:i + PHOTOS_PER_PAGE]

            # Build rows
            rows = []
            for row_idx in range(ROWS_PER_PAGE):
                row_start = row_idx * PHOTOS_PER_ROW
                row_photos = page_photos[row_start:row_start + PHOTOS_PER_ROW]

                if not row_photos:
                    break

                row_cells = []
                for photo in row_photos:
                    cell = self._build_photo_cell(photo)
                    row_cells.append(cell)

                # Pad row if needed
                while len(row_cells) < PHOTOS_PER_ROW:
                    row_cells.append('')

                rows.append(row_cells)

            if rows:
                grid_table = Table(
                    rows,
                    colWidths=[CELL_WIDTH] * PHOTOS_PER_ROW,
                    rowHeights=[CELL_HEIGHT] * len(rows)
                )
                grid_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))

                elements.append(grid_table)

        return elements

    def _build_photo_cell(self, photo: Dict) -> List:
        """Build a single photo cell with image and caption."""
        cell_elements = []

        # Load image
        file_path = photo.get('file_path', '')
        photo_id = photo.get('id')

        image_buffer = load_image(file_path) if file_path else None

        if image_buffer:
            try:
                # Get dimensions
                width, height = get_image_dimensions(image_buffer, PHOTO_MAX_WIDTH, PHOTO_MAX_HEIGHT)
                image_buffer.seek(0)
                img = Image(image_buffer, width=width, height=height)
                cell_elements.append(img)
            except Exception as e:
                print(f"Error creating image for photo {photo_id}: {e}")
                placeholder = PlaceholderImage(PHOTO_MAX_WIDTH, PHOTO_MAX_HEIGHT, photo_id)
                cell_elements.append(placeholder)
        else:
            # Placeholder for missing image
            placeholder = PlaceholderImage(PHOTO_MAX_WIDTH, PHOTO_MAX_HEIGHT, photo_id)
            cell_elements.append(placeholder)

        # Build caption
        caption_parts = []

        # Panel name
        panel_name = photo.get('panel_name')
        if panel_name:
            caption_parts.append(self._get_panel_name(panel_name))

        # Timestamp
        timestamp = photo.get('created_at')
        if timestamp:
            caption_parts.append(self._format_timestamp(timestamp))

        # User caption
        user_caption = photo.get('caption')
        if user_caption:
            caption_parts.append(user_caption)

        caption_text = ' • '.join(caption_parts) if caption_parts else f"Photo {photo_id}"

        # Add evidence badge if applicable
        if photo.get('is_supplement_evidence'):
            caption_text = f"<font color='#b91c1c'><b>[EVIDENCE]</b></font> {caption_text}"

        cell_elements.append(Paragraph(caption_text, self.styles['PhotoCaption']))

        # Wrap in a table for vertical layout
        cell_table = Table([[e] for e in cell_elements], colWidths=[PHOTO_MAX_WIDTH])
        cell_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        return cell_table


# ==============================================================================
# CONVENIENCE FUNCTION
# ==============================================================================

def generate_photo_sheet(
    estimate: Dict[str, Any],
    photos: List[Dict[str, Any]],
    shop_info: Optional[Dict[str, Any]] = None
) -> BytesIO:
    """
    Generate a photo sheet PDF.

    Args:
        estimate: Estimate data dictionary
        photos: List of photo dictionaries
        shop_info: Optional shop/company info

    Returns:
        BytesIO buffer containing the PDF
    """
    generator = PhotoSheetGenerator()
    return generator.generate_photo_sheet(estimate, photos, shop_info)
