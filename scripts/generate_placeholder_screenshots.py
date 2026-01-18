#!/usr/bin/env python3
"""
Generate placeholder screenshot images for README
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_placeholder(filename: str, title: str, subtitle: str, width: int = 375, height: int = 667):
    """Create a mobile-sized placeholder image"""

    # Create image with dark gradient background (matching app theme)
    img = Image.new('RGB', (width, height), '#1a1a2e')
    draw = ImageDraw.Draw(img)

    # Draw gradient effect (simple horizontal bands)
    for y in range(height):
        # Gradient from #1a1a2e to #16213e
        ratio = y / height
        r = int(26 + (22 - 26) * ratio)
        g = int(26 + (33 - 26) * ratio)
        b = int(46 + (62 - 46) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Draw phone frame
    frame_color = '#2a2a4e'
    draw.rectangle([10, 10, width-10, height-10], outline=frame_color, width=2)

    # Draw status bar area
    draw.rectangle([10, 10, width-10, 40], fill='#0f0f1e')

    # Draw navigation bar area at bottom
    draw.rectangle([10, height-70, width-10, height-10], fill='#0f0f1e')

    # Draw 5 nav icons as circles
    nav_y = height - 40
    nav_spacing = (width - 40) // 5
    for i in range(5):
        x = 30 + i * nav_spacing
        # Highlight first icon (current page)
        color = '#00d4ff' if i == 0 else '#4a4a6e'
        draw.ellipse([x-12, nav_y-12, x+12, nav_y+12], fill=color)

    # Try to use a font, fall back to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 28)
        subtitle_font = ImageFont.truetype("arial.ttf", 16)
    except:
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

    # Draw centered title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, height // 2 - 60), title, fill='#00d4ff', font=title_font)

    # Draw subtitle
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    draw.text((subtitle_x, height // 2), subtitle, fill='#8888aa', font=subtitle_font)

    # Draw placeholder icon (camera/image icon)
    icon_y = height // 2 + 50
    icon_x = width // 2
    # Camera body
    draw.rounded_rectangle([icon_x-30, icon_y-20, icon_x+30, icon_y+20], radius=5, outline='#4a4a6e', width=2)
    # Lens
    draw.ellipse([icon_x-12, icon_y-12, icon_x+12, icon_y+12], outline='#4a4a6e', width=2)
    # Flash
    draw.rectangle([icon_x+15, icon_y-25, icon_x+25, icon_y-18], fill='#4a4a6e')

    # Draw "Screenshot Coming Soon" text
    coming_soon = "Screenshot Coming Soon"
    try:
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        small_font = subtitle_font
    cs_bbox = draw.textbbox((0, 0), coming_soon, font=small_font)
    cs_width = cs_bbox[2] - cs_bbox[0]
    cs_x = (width - cs_width) // 2
    draw.text((cs_x, icon_y + 40), coming_soon, fill='#6a6a8e', font=small_font)

    return img


def main():
    # Output directory
    output_dir = Path(__file__).parent.parent / 'docs' / 'screenshots'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Screenshot definitions
    screenshots = [
        ('mobile-dashboard.png', 'Dashboard', 'Sales metrics & goals'),
        ('mobile-route.png', 'Route Planning', 'Optimized daily routes'),
        ('mobile-leads.png', 'Lead Capture', 'Quick property entry'),
        ('mobile-leaderboard.png', 'Leaderboard', 'Team rankings'),
        ('mobile-scripts.png', 'Sales Scripts', 'Objection handling'),
        ('mobile-competitors.png', 'Competitor Intel', 'Market intelligence'),
    ]

    print("Generating placeholder screenshots...")

    for filename, title, subtitle in screenshots:
        img = create_placeholder(filename, title, subtitle)
        output_path = output_dir / filename
        img.save(output_path, 'PNG')
        print(f"  Created: {output_path}")

    print(f"\nGenerated {len(screenshots)} placeholder screenshots in {output_dir}")
    print("\nTo replace with actual screenshots:")
    print("  1. Run the app: python run.py")
    print("  2. Open mobile view in browser dev tools (375x667)")
    print("  3. Capture each screen and save to docs/screenshots/")


if __name__ == '__main__':
    main()
