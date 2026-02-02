"""
Generate PWA icons in all required sizes
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path
import math

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def generate_pwa_icons():
    """Generate all PWA icon sizes with a professional hail/storm theme."""

    sizes = [72, 96, 128, 144, 152, 192, 384, 512]

    output_dir = PROJECT_ROOT / 'static' / 'icons'
    output_dir.mkdir(parents=True, exist_ok=True)

    for size in sizes:
        # Create icon with dark background
        img = Image.new('RGBA', (size, size), color=(10, 10, 26, 255))
        draw = ImageDraw.Draw(img)

        # Draw gradient background (dark blue to darker)
        for y in range(size):
            progress = y / size
            r = int(10 + (26 - 10) * progress)
            g = int(10 + (26 - 10) * progress)
            b = int(26 + (62 - 26) * progress)
            for x in range(size):
                img.putpixel((x, y), (r, g, b, 255))

        draw = ImageDraw.Draw(img)

        # Draw a circle representing hail/radar
        center = size // 2
        outer_radius = int(size * 0.4)

        # Cyan glow effect (multiple circles)
        for i in range(5, 0, -1):
            glow_radius = outer_radius + i * 2
            alpha = int(50 - i * 10)
            for angle in range(0, 360, 2):
                rad = math.radians(angle)
                x = center + int(glow_radius * math.cos(rad))
                y = center + int(glow_radius * math.sin(rad))
                if 0 <= x < size and 0 <= y < size:
                    current = img.getpixel((x, y))
                    new_color = (
                        min(255, current[0] + alpha // 3),
                        min(255, current[1] + alpha),
                        min(255, current[2] + alpha),
                        255
                    )
                    img.putpixel((x, y), new_color)

        # Main cyan circle (outer ring)
        draw.ellipse(
            [center - outer_radius, center - outer_radius,
             center + outer_radius, center + outer_radius],
            outline=(0, 217, 255, 255),
            width=max(2, size // 40)
        )

        # Inner circle (hailstone representation)
        inner_radius = int(size * 0.25)
        draw.ellipse(
            [center - inner_radius, center - inner_radius,
             center + inner_radius, center + inner_radius],
            fill=(0, 180, 220, 200),
            outline=(0, 217, 255, 255),
            width=max(1, size // 60)
        )

        # Add "H" letter in center
        try:
            font_size = int(size * 0.3)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except:
                    font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        text = "H"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_pos = (
            (size - text_width) // 2,
            (size - text_height) // 2 - bbox[1]
        )
        draw.text(text_pos, text, fill=(255, 255, 255, 255), font=font)

        # Add small hail dots around
        import random
        random.seed(42)  # Consistent pattern
        for _ in range(max(3, size // 30)):
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(outer_radius * 1.1, outer_radius * 1.4)
            dot_x = int(center + distance * math.cos(angle))
            dot_y = int(center + distance * math.sin(angle))
            dot_size = max(1, size // 50)
            if 0 < dot_x < size - dot_size and 0 < dot_y < size - dot_size:
                draw.ellipse(
                    [dot_x - dot_size, dot_y - dot_size,
                     dot_x + dot_size, dot_y + dot_size],
                    fill=(200, 230, 255, 180)
                )

        # Convert to RGB for PNG saving
        img_rgb = Image.new('RGB', (size, size), (10, 10, 26))
        img_rgb.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)

        # Save
        filename = output_dir / f'icon-{size}.png'
        img_rgb.save(filename, 'PNG')
        print(f'Generated: {filename}')

    # Also create a badge icon (smaller, for notifications)
    badge_size = 72
    badge = Image.new('RGB', (badge_size, badge_size), color=(0, 217, 255))
    badge_draw = ImageDraw.Draw(badge)
    badge_center = badge_size // 2
    badge_radius = int(badge_size * 0.35)
    badge_draw.ellipse(
        [badge_center - badge_radius, badge_center - badge_radius,
         badge_center + badge_radius, badge_center + badge_radius],
        fill=(255, 255, 255)
    )
    badge.save(output_dir / 'badge-72.png', 'PNG')
    print(f'Generated: {output_dir / "badge-72.png"}')

    print(f'\nGenerated {len(sizes) + 1} PWA icons successfully!')
    return True


if __name__ == '__main__':
    generate_pwa_icons()
