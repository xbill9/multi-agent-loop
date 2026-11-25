#!/usr/bin/env python3
"""Textless cover: a research loop of three agents feeding a finished page,
set on a raised step (the move up to a new version). Kit palette.

usage: make_cover.py OUTDIR
writes devto-cover.<hash>.jpg (1376x578) and builder-cover.<hash>.jpg (1200x675)
"""
import hashlib
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SURFACE = (26, 26, 25)
RULE = (58, 58, 55)
INK_2 = (195, 194, 183)
INK_3 = (128, 127, 120)
BLUE = (57, 135, 229)
ORANGE = (217, 89, 38)
PAPER = (236, 234, 226)


def arrow_head(d, tip, angle, size, fill):
    a1, a2 = angle + math.radians(150), angle - math.radians(150)
    d.polygon([tip,
               (tip[0] + size * math.cos(a1), tip[1] + size * math.sin(a1)),
               (tip[0] + size * math.cos(a2), tip[1] + size * math.sin(a2))], fill=fill)


def draw(w, h):
    k = 2
    W, H = w * k, h * k
    im = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(im)
    # everything sits inside the band dev.to keeps (2.381:1 centre crop)
    band = W / 2.381
    top = (H - band) / 2
    cy = top + band * 0.52
    u = band / 10  # unit

    # raised step under the loop: lower ledge then higher ledge
    lw = 10 * k
    x0, x1, x2 = W * 0.10, W * 0.30, W * 0.62
    y_low, y_high = cy + 3.4 * u, cy + 2.6 * u
    d.line([(x0, y_low), (x1, y_low), (x1, y_high), (x2, y_high)], fill=RULE, width=lw, joint="curve")

    # loop of three agents on a circle
    lcx, lcy, R = W * 0.40, cy - 0.3 * u, 2.3 * u
    nodes = [(-90, BLUE), (30, ORANGE), (150, INK_3)]
    pts = [(lcx + R * math.cos(math.radians(a)), lcy + R * math.sin(math.radians(a))) for a, _ in nodes]
    r = 0.85 * u
    # arcs between nodes, clockwise, with heads
    for i in range(3):
        a_from = nodes[i][0] + 28
        a_to = nodes[(i + 1) % 3][0] - 28
        if a_to < a_from:
            a_to += 360
        bbox = [lcx - R, lcy - R, lcx + R, lcy + R]
        d.arc(bbox, a_from, a_to, fill=INK_2, width=6 * k)
        t = math.radians(a_to)
        tip = (lcx + R * math.cos(t), lcy + R * math.sin(t))
        arrow_head(d, tip, t + math.pi / 2, 0.42 * u, INK_2)
    for (cx, cy2), (_, col) in zip(pts, nodes, strict=True):
        if col == INK_3:
            d.ellipse([cx - r, cy2 - r, cx + r, cy2 + r], fill=SURFACE, outline=INK_3, width=6 * k)
            d.ellipse([cx - r * 0.35, cy2 - r * 0.35, cx + r * 0.35, cy2 + r * 0.35], fill=INK_3)
        else:
            d.ellipse([cx - r, cy2 - r, cx + r, cy2 + r], fill=col)

    # arrow out of the loop to the page
    ax0, ax1 = lcx + R + 1.3 * u, W * 0.66
    d.line([(ax0, lcy), (ax1, lcy)], fill=INK_2, width=6 * k)
    arrow_head(d, (ax1 + 0.2 * u, lcy), 0, 0.5 * u, INK_2)

    # finished page with a title bar and section lines
    pw, ph = 2.9 * u, 3.8 * u
    px, py = W * 0.70, lcy - ph / 2
    fold = 0.7 * u
    d.polygon([(px, py), (px + pw - fold, py), (px + pw, py + fold), (px + pw, py + ph), (px, py + ph)], fill=PAPER)
    d.polygon([(px + pw - fold, py), (px + pw - fold, py + fold), (px + pw, py + fold)], fill=INK_2)
    d.rectangle([px + 0.35 * u, py + 0.55 * u, px + pw * 0.62, py + 0.95 * u], fill=BLUE)
    yy = py + 1.45 * u
    for i in range(5):
        wfrac = 0.78 if i % 2 == 0 else 0.6
        if i in (2,):
            d.rectangle([px + 0.35 * u, yy, px + 0.35 * u + pw * 0.4, yy + 0.22 * u], fill=ORANGE)
        else:
            d.rectangle([px + 0.35 * u, yy, px + 0.35 * u + (pw - 0.7 * u) * wfrac, yy + 0.16 * u], fill=INK_3)
        yy += 0.42 * u

    return im.resize((w, h), Image.LANCZOS)


def save(im, outdir, stem):
    import io
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    data = buf.getvalue()
    name = f"{stem}.{hashlib.sha256(data).hexdigest()[:8]}.jpg"
    (outdir / name).write_bytes(data)
    print(f"wrote {name}  {im.size[0]}x{im.size[1]}  {len(data)//1024} KB")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    save(draw(1376, 578), out, "devto-cover")
    save(draw(1200, 675), out, "builder-cover")
