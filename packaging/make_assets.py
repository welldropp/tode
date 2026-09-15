"""
packaging/make_assets.py
─────────────────────────
Regenerate the installer branding assets with Pillow:
  tode.ico            — app / setup / shortcut icon (multi-size)
  wizard-large.bmp    — Inno Setup welcome/finish banner (164×314)
  wizard-small.bmp    — Inno Setup header image (55×58)

Run:  python packaging/make_assets.py
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG = (20, 20, 27, 255)
ACCENT = (47, 107, 255, 255)
GREEN = (46, 204, 113, 255)
WHITE = (230, 232, 236, 255)


def icon(size: int) -> Image.Image:
    """A rounded dark square with an accent bounding-box + green corner handles."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([1, 1, size - 2, size - 2], radius=max(3, size // 6), fill=BG)
    m = size * 0.24
    d.rounded_rectangle([m, m, size - m, size - m], radius=max(2, size // 16),
                        outline=ACCENT, width=max(2, size // 18))
    hs = max(2, size // 16)
    for cx, cy in [(m, m), (size - m, m), (m, size - m), (size - m, size - m)]:
        d.rectangle([cx - hs, cy - hs, cx + hs, cy + hs], fill=GREEN)
    return img


def banner(w: int, h: int, big: bool) -> Image.Image:
    img = Image.new("RGB", (w, h), (14, 15, 19))
    d = ImageDraw.Draw(img)
    for y in range(h):                                   # subtle gradient
        t = y / h
        d.line([(0, y), (w, y)], fill=(14 + int(8 * t), 15 + int(9 * t), 19 + int(14 * t)))
    ic = icon(int(h * 0.34) if big else int(h * 0.7))
    x = int(w * 0.12) if big else (w - ic.width) // 2
    y = int(h * 0.14) if big else (h - ic.height) // 2
    img.paste(ic, (x, y), ic)
    if big:
        try:
            f = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
            f2 = ImageFont.truetype("DejaVuSans.ttf", 15)
        except OSError:
            f = f2 = ImageFont.load_default()
        d.text((int(w * 0.12), int(h * 0.52)), "tode", fill=WHITE, font=f)
        d.text((int(w * 0.12), int(h * 0.52) + 42), "AI annotation", fill=(139, 144, 156), font=f2)
    return img


def main() -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    icon(256).save(os.path.join(HERE, "tode.ico"), sizes=[(s, s) for s in sizes])
    banner(164, 314, True).save(os.path.join(HERE, "wizard-large.bmp"))
    banner(55, 58, False).save(os.path.join(HERE, "wizard-small.bmp"))
    print("Wrote tode.ico, wizard-large.bmp, wizard-small.bmp")


if __name__ == "__main__":
    main()
