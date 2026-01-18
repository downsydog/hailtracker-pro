"""
Generate PWA icons for Elite Sales Mobile App
Creates icons in all required sizes with consistent branding
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow")
    from PIL import Image, ImageDraw, ImageFont

import math

# Icon sizes needed for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
SHORTCUT_SIZE = 96
BADGE_SIZE = 72

# Brand colors
PRIMARY_COLOR = (0, 212, 255)      # Cyan #00d4ff
SECONDARY_COLOR = (0, 153, 204)    # Darker cyan #0099cc
DARK_BG = (26, 26, 46)             # Dark background #1a1a2e
ACCENT_COLOR = (255, 215, 0)       # Gold for accents #ffd700
WHITE = (255, 255, 255)
DARK_TEXT = (22, 33, 62)           # #16213e


def create_gradient_background(size, color1, color2):
    """Create a diagonal gradient background"""
    img = Image.new('RGBA', (size, size), color1)
    draw = ImageDraw.Draw(img)

    for i in range(size):
        # Diagonal gradient
        ratio = i / size
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)

        # Draw diagonal lines
        draw.line([(0, i), (i, 0)], fill=(r, g, b), width=1)
        draw.line([(size - i, size), (size, size - i)], fill=(r, g, b), width=1)

    return img


def create_base_icon(size):
    """Create the base Elite Sales icon"""
    # Create image with gradient background
    img = Image.new('RGBA', (size, size), DARK_BG)
    draw = ImageDraw.Draw(img)

    # Draw gradient circle background
    padding = int(size * 0.08)
    circle_bbox = [padding, padding, size - padding, size - padding]

    # Outer glow effect
    for i in range(5, 0, -1):
        glow_padding = padding - i * 2
        glow_bbox = [glow_padding, glow_padding, size - glow_padding, size - glow_padding]
        glow_alpha = int(255 * (0.1 * (6 - i) / 5))
        glow_color = (*PRIMARY_COLOR, glow_alpha)
        draw.ellipse(glow_bbox, fill=None, outline=glow_color, width=2)

    # Main circle with gradient effect (simulated)
    draw.ellipse(circle_bbox, fill=PRIMARY_COLOR, outline=None)

    # Inner darker circle for depth
    inner_padding = int(size * 0.12)
    inner_bbox = [inner_padding, inner_padding, size - inner_padding, size - inner_padding]
    draw.ellipse(inner_bbox, fill=SECONDARY_COLOR, outline=None)

    # Draw lightning bolt / hail symbol
    center_x = size // 2
    center_y = size // 2

    # Scale factor for the icon elements
    scale = size / 192  # Base design at 192px

    # Lightning bolt points (representing hail/storm)
    bolt_points = [
        (center_x - int(15 * scale), center_y - int(35 * scale)),
        (center_x + int(10 * scale), center_y - int(35 * scale)),
        (center_x + int(2 * scale), center_y - int(5 * scale)),
        (center_x + int(20 * scale), center_y - int(5 * scale)),
        (center_x - int(5 * scale), center_y + int(40 * scale)),
        (center_x + int(3 * scale), center_y + int(10 * scale)),
        (center_x - int(15 * scale), center_y + int(10 * scale)),
    ]

    # Draw lightning bolt
    draw.polygon(bolt_points, fill=WHITE, outline=None)

    # Add small circles for hail stones
    hail_positions = [
        (center_x - int(30 * scale), center_y - int(20 * scale), int(6 * scale)),
        (center_x + int(28 * scale), center_y - int(15 * scale), int(5 * scale)),
        (center_x - int(25 * scale), center_y + int(25 * scale), int(5 * scale)),
        (center_x + int(30 * scale), center_y + int(20 * scale), int(6 * scale)),
    ]

    for x, y, r in hail_positions:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=WHITE, outline=None)

    return img


def create_shortcut_icon(size, icon_type):
    """Create shortcut icons for quick actions"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    padding = int(size * 0.1)
    radius = int(size * 0.2)

    if icon_type == 'lead':
        bg_color = (76, 175, 80)  # Green
        symbol = '+'
    elif icon_type == 'route':
        bg_color = (33, 150, 243)  # Blue
        symbol = '>'
    else:
        bg_color = PRIMARY_COLOR
        symbol = '*'

    # Draw rounded rectangle
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=radius,
        fill=bg_color
    )

    # Draw symbol
    try:
        font_size = int(size * 0.5)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Center the symbol
    bbox = draw.textbbox((0, 0), symbol, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - int(size * 0.05)

    draw.text((x, y), symbol, fill=WHITE, font=font)

    return img


def create_badge_icon(size):
    """Create notification badge icon"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Simple circle badge
    padding = int(size * 0.15)
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=PRIMARY_COLOR,
        outline=WHITE,
        width=2
    )

    # Draw lightning bolt
    center = size // 2
    scale = size / 72

    bolt_points = [
        (center - int(5 * scale), center - int(12 * scale)),
        (center + int(5 * scale), center - int(12 * scale)),
        (center + int(2 * scale), center - int(2 * scale)),
        (center + int(8 * scale), center - int(2 * scale)),
        (center - int(2 * scale), center + int(15 * scale)),
        (center + int(2 * scale), center + int(5 * scale)),
        (center - int(5 * scale), center + int(5 * scale)),
    ]

    draw.polygon(bolt_points, fill=WHITE)

    return img


def create_maskable_icon(size):
    """Create maskable icon with safe zone padding"""
    # Maskable icons need 10% padding on each side
    img = Image.new('RGBA', (size, size), DARK_BG)
    draw = ImageDraw.Draw(img)

    # Safe zone is 80% of the icon (10% padding on each side)
    safe_zone = int(size * 0.8)
    offset = int(size * 0.1)

    # Create the base icon at safe zone size
    base = create_base_icon(safe_zone)

    # Paste onto the full size image
    img.paste(base, (offset, offset), base)

    return img


def create_apple_touch_icon(size):
    """Create Apple touch icon with no transparency"""
    img = create_base_icon(size)

    # Convert to RGB (no transparency for Apple)
    rgb_img = Image.new('RGB', (size, size), DARK_BG)
    rgb_img.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)

    return rgb_img


def generate_all_icons(output_dir):
    """Generate all PWA icons"""
    os.makedirs(output_dir, exist_ok=True)

    print("Generating PWA icons for Elite Sales...")
    print(f"Output directory: {output_dir}")
    print()

    # Generate main icons
    print("Creating main app icons:")
    for size in ICON_SIZES:
        icon = create_base_icon(size)
        filename = os.path.join(output_dir, f'icon-{size}.png')
        icon.save(filename, 'PNG')
        print(f"  Created: icon-{size}.png")

    # Generate maskable icons
    print("\nCreating maskable icons:")
    for size in [192, 512]:
        icon = create_maskable_icon(size)
        filename = os.path.join(output_dir, f'icon-{size}-maskable.png')
        icon.save(filename, 'PNG')
        print(f"  Created: icon-{size}-maskable.png")

    # Generate Apple touch icon
    print("\nCreating Apple touch icon:")
    apple_icon = create_apple_touch_icon(180)
    apple_filename = os.path.join(output_dir, 'apple-touch-icon.png')
    apple_icon.save(apple_filename, 'PNG')
    print(f"  Created: apple-touch-icon.png")

    # Generate shortcut icons
    print("\nCreating shortcut icons:")
    for icon_type in ['lead', 'route']:
        icon = create_shortcut_icon(SHORTCUT_SIZE, icon_type)
        filename = os.path.join(output_dir, f'shortcut-{icon_type}.png')
        icon.save(filename, 'PNG')
        print(f"  Created: shortcut-{icon_type}.png")

    # Generate badge icon
    print("\nCreating badge icon:")
    badge = create_badge_icon(BADGE_SIZE)
    badge_filename = os.path.join(output_dir, 'badge-72.png')
    badge.save(badge_filename, 'PNG')
    print(f"  Created: badge-72.png")

    # Generate favicon
    print("\nCreating favicon:")
    favicon = create_base_icon(32)
    favicon_filename = os.path.join(output_dir, 'favicon-32.png')
    favicon.save(favicon_filename, 'PNG')
    print(f"  Created: favicon-32.png")

    # Generate large favicon
    favicon_lg = create_base_icon(16)
    favicon_lg_filename = os.path.join(output_dir, 'favicon-16.png')
    favicon_lg.save(favicon_lg_filename, 'PNG')
    print(f"  Created: favicon-16.png")

    print("\n" + "=" * 50)
    print("All icons generated successfully!")
    print("=" * 50)

    # Print summary
    total_files = len(ICON_SIZES) + 2 + 1 + 2 + 1 + 2  # main + maskable + apple + shortcuts + badge + favicons
    print(f"\nTotal icons created: {total_files}")
    print(f"\nIcon sizes: {', '.join(str(s) + 'x' + str(s) for s in ICON_SIZES)}")

    return True


def main():
    # Determine output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, 'static', 'mobile', 'icons')

    generate_all_icons(output_dir)


if __name__ == '__main__':
    main()
