# -*- coding: utf-8 -*-
"""Háttérkép (assets/bg.png): finom színátmenet + halvány, térképszerű vonalak megállókkal."""
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H, SS = 1600, 1000, 2            # kimeneti méret, szupermintavétel
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "bg.png")


def gradient():
    img = Image.new("RGB", (W * SS, H * SS))
    px = img.load()
    c0, c1 = (246, 249, 255), (210, 224, 245)
    for y in range(0, H * SS, 2):
        for x in range(0, W * SS, 2):
            t = (x / (W * SS) * 0.45 + y / (H * SS) * 0.55)
            col = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
            px[x, y] = px[x + 1, y] = px[x, y + 1] = px[x + 1, y + 1] = col
    return img


def chamfer(points, r):
    """Éles sarkok levágása 45°-os átmenetekkel (metrótérkép-hatás)."""
    out = [points[0]]
    for i in range(1, len(points) - 1):
        (x0, y0), (x1, y1), (x2, y2) = points[i - 1], points[i], points[i + 1]
        def toward(ax, ay, bx, by):
            dx, dy = bx - ax, by - ay
            d = max(1, (dx * dx + dy * dy) ** 0.5)
            return ax + dx / d * r, ay + dy / d * r
        out.append(toward(x1, y1, x0, y0))
        out.append(toward(x1, y1, x2, y2))
    out.append(points[-1])
    return out


def main():
    base = gradient().convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    s = SS
    lines = [
        ((255, 200, 0, 70),  [(-50, 760), (380, 760), (560, 580), (1000, 580), (1180, 400), (1700, 400)]),
        ((0, 150, 220, 60),  [(250, -50), (250, 260), (430, 440), (430, 1050)]),
        ((228, 31, 24, 52),  [(-50, 180), (700, 180), (880, 360), (880, 760), (1060, 940), (1700, 940)]),
        ((60, 160, 70, 48),  [(1350, -50), (1350, 230), (1500, 380), (1500, 1050)]),
    ]
    for col, pts in lines:
        pts = chamfer(pts, 110)
        pts = [(x * s, y * s) for x, y in pts]
        d.line(pts, fill=col, width=16 * s, joint="curve")
        # megállók a vonal mentén
        for (x, y) in pts[1::2]:
            r = 15 * s
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 190), outline=col[:3] + (150,), width=5 * s)
    layer = layer.filter(ImageFilter.GaussianBlur(1.2 * s))
    img = Image.alpha_composite(base, layer).convert("RGB").resize((W, H), Image.LANCZOS)
    # enyhe vignetta
    vig = Image.radial_gradient("L").resize((W, H))
    vig = ImageChops.invert(vig).point(lambda v: int(v * 0.10))
    img = Image.composite(Image.new("RGB", (W, H), (150, 170, 205)), img, vig)
    img.save(OUT, optimize=True)
    print("OK", OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
