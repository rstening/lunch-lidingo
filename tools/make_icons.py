"""Rita sidans ikoner (förslag A: grön prick på mörk ruta) som PNG.

Kör: .venv/bin/python tools/make_icons.py
SVG-versionen ligger i docs/favicon.svg och ritas inte här.
"""
from pathlib import Path

from PIL import Image, ImageDraw

DOCS = Path(__file__).resolve().parent.parent / "docs"
DARK = (18, 18, 18, 255)       # #121212
GREEN = (36, 204, 92, 255)     # #24cc5c
SCALE = 8                      # draw large, then shrink for smooth edges


def icon(size: int, rounded: bool) -> Image.Image:
    big = size * SCALE
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = round(big * 14 / 64) if rounded else 0
    draw.rounded_rectangle([0, 0, big - 1, big - 1], radius=radius, fill=DARK)
    r = big * 9 / 64
    c = big / 2
    draw.ellipse([c - r, c - r, c + r, c + r], fill=GREEN)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    icon(32, rounded=True).save(DOCS / "favicon-32.png")
    icon(192, rounded=True).save(DOCS / "icon-192.png")
    # iOS rounds the corners itself, so the home-screen icon is a full square.
    icon(180, rounded=False).convert("RGB").save(DOCS / "apple-touch-icon.png")
    print("Skrev favicon-32.png, icon-192.png, apple-touch-icon.png")
