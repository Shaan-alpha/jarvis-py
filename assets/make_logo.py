"""Generate the Jarvis app logo — an arc-reactor "J" mark.

Standalone build/asset tool (NOT imported by the app or tests, so Pillow stays a
dev-only need). Draws at 4x supersample then downscales for smooth edges, and
writes jarvis.png (256) + a multi-size jarvis.ico for the window/.exe icon.

    python assets/make_logo.py
"""

import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter


HERE = os.path.dirname(os.path.abspath(__file__))

S = 1024                       # supersample canvas; downscaled to 256 at the end

CORE = (139, 233, 255, 255)    # #8be9ff  HUD --orb-a
RING = (26, 160, 230, 255)     # #1aa0e6  HUD --accent2
TEAL = (65, 232, 198, 255)     # #41e8c6  HUD --orb-c
DARK = (5, 8, 15, 255)         # #05080f  HUD background
GLOW = (40, 170, 255, 255)     # halo


def _font(px):
    for name in ("segoeuib.ttf", "arialbd.ttf"):
        path = os.path.join(r"C:\Windows\Fonts", name)
        if os.path.exists(path):
            return ImageFont.truetype(path, px)
    return ImageFont.load_default()


def build():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cx = cy = S // 2
    R = int(S * 0.40)

    # --- soft outer glow (blurred ring + core) ---
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - R, cy - R, cx + R, cy + R], outline=GLOW, width=int(S * 0.055))
    cr = int(S * 0.19)
    gd.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=CORE)
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.045))
    img = Image.alpha_composite(img, glow)

    d = ImageDraw.Draw(img)

    # outer ring
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=RING, width=int(S * 0.045))

    # inner segmented ring (arc-reactor coils)
    r2 = int(S * 0.30)
    for start in range(0, 360, 45):
        d.arc([cx - r2, cy - r2, cx + r2, cy + r2],
              start + 7, start + 38, fill=TEAL, width=int(S * 0.024))

    # core: concentric discs for a soft dark-to-bright gradient
    for rr, col in ((0.205, RING), (0.165, CORE), (0.125, (210, 248, 255, 255))):
        rad = int(S * rr)
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=col)

    # the "J", dark on the bright core
    font = _font(int(S * 0.30))
    box = d.textbbox((0, 0), "J", font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text((cx - tw / 2 - box[0], cy - th / 2 - box[1]), "J", font=font, fill=DARK)

    return img.resize((256, 256), Image.LANCZOS)


def main():
    icon = build()
    icon.save(os.path.join(HERE, "jarvis.png"))
    icon.save(os.path.join(HERE, "jarvis.ico"),
              sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("wrote", os.path.join(HERE, "jarvis.png"), "+ jarvis.ico")


if __name__ == "__main__":
    main()
