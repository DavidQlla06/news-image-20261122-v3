#!/usr/bin/env python3
"""Render the 22 November 2026 front page (entry.png, 1024x1024).

Reads stories.json next to this file and draws a dense broadsheet:
masthead, a big illustrated lead story, a 12-card illustrated grid,
region-grouped headline lists, a ticker strip and a footer.
Deterministic: no randomness, no clock, no network.
"""

import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W = H = 1024
MARGIN = 16
CONTENT_W = W - 2 * MARGIN

PAPER = (246, 240, 226)
INK = (26, 24, 22)
NAVY = (18, 30, 58)
NAVY2 = (27, 45, 82)
GOLD = (201, 162, 39)
GOLD_LT = (232, 197, 90)
RED = (185, 28, 28)
GREY = (92, 86, 76)
RULE = (60, 54, 46)
CARD_BG = (253, 250, 242)
CARD_EDGE = (120, 110, 92)

REGION_COLORS = {
    "MIDDLE EAST": (176, 32, 32),
    "EUROPE": (29, 78, 216),
    "AMERICAS": (13, 116, 144),
    "ASIA-PACIFIC": (180, 83, 9),
    "AFRICA": (146, 64, 14),
    "PLANET": (21, 128, 61),
    "PLANET & SCIENCE": (21, 128, 61),
    "SPORT": (109, 40, 217),
    "BUSINESS": (51, 65, 85),
}

SERIF_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_I = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"

_font_cache = {}


def F(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def text_w(draw, s, font):
    return draw.textlength(s, font=font)


def wrap(draw, s, font, max_w):
    """Greedy word wrap; returns list of lines that each fit max_w."""
    words = s.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_w(draw, trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_lines(draw, s, path, max_w, max_lines, size_hi, size_lo):
    """Largest font size (size_lo..size_hi) whose wrap fits max_lines."""
    for size in range(size_hi, size_lo - 1, -1):
        f = F(path, size)
        lines = wrap(draw, s, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    f = F(path, size_lo)
    return f, wrap(draw, s, f, max_w)[:max_lines]


def draw_lines(draw, x, y, lines, font, fill, leading):
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=fill)
        y += leading
    return y


def vgrad(draw, box, top, bottom, steps=48):
    x0, y0, x1, y1 = box
    for i in range(steps):
        t = i / max(1, steps - 1)
        c = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
        yy0 = y0 + (y1 - y0) * i / steps
        yy1 = y0 + (y1 - y0) * (i + 1) / steps + 1
        draw.rectangle([x0, yy0, x1, yy1], fill=c)


def starburst(draw, cx, cy, r_out, r_in, points, fill, rot=0.0):
    pts = []
    for i in range(points * 2):
        ang = rot + math.pi * i / points
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def bezier(p0, p1, p2, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def waves(draw, box, color, rows=3, amp=3, wl=26):
    x0, y0, x1, y1 = box
    for r in range(rows):
        yy = y0 + (y1 - y0) * (r + 0.5) / rows
        pts = []
        x = x0
        while x <= x1:
            pts.append((x, yy + amp * math.sin((x - x0) / wl * math.pi)))
            x += 4
        draw.line(pts, fill=color, width=2)


def flame(draw, cx, cy, w, h):
    """Layered teardrop flame centred at (cx, cy) base."""
    for scale, col in ((1.0, (220, 80, 20)), (0.68, (245, 140, 30)),
                       (0.4, (250, 200, 70))):
        fw, fh = w * scale, h * scale
        pts = [(cx - fw / 2, cy), (cx - fw * 0.28, cy - fh * 0.55),
               (cx, cy - fh), (cx + fw * 0.28, cy - fh * 0.55),
               (cx + fw / 2, cy)]
        draw.polygon(pts, fill=col)


def smoke(draw, cx, cy, r, n=4, col=(70, 66, 62)):
    for i in range(n):
        rr = r * (1 - i * 0.16)
        draw.ellipse([cx - rr + i * r * 0.35, cy - rr - i * r * 0.9,
                      cx + rr + i * r * 0.35, cy + rr - i * r * 0.9], fill=col)


def ship(draw, box, hull=(40, 44, 54), deck=(90, 96, 110), cargo=None):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    # hull
    draw.polygon([(x0, y0 + h * 0.45), (x1 - w * 0.06, y0 + h * 0.45),
                  (x1, y0 + h * 0.62), (x1 - w * 0.1, y1),
                  (x0 + w * 0.08, y1), (x0, y0 + h * 0.7)], fill=hull)
    draw.rectangle([x0 + w * 0.04, y0 + h * 0.36, x1 - w * 0.1, y0 + h * 0.47],
                   fill=deck)
    # superstructure + funnel
    draw.rectangle([x0 + w * 0.06, y0 + h * 0.08, x0 + w * 0.2, y0 + h * 0.38],
                   fill=(225, 228, 232))
    draw.rectangle([x0 + w * 0.09, y0, x0 + w * 0.15, y0 + h * 0.12],
                   fill=(180, 40, 40))
    if cargo:
        cols = [(200, 90, 40), (60, 120, 180), (70, 160, 90), (190, 160, 50)]
        cw = w * 0.16
        for i in range(4):
            cx = x0 + w * 0.26 + i * (cw + 3)
            draw.rectangle([cx, y0 + h * 0.16, cx + cw, y0 + h * 0.37],
                           fill=cols[i % len(cols)])


# ---------------------------------------------------------------- scenes

def scene_gulf(draw, box):
    """Lead scene: dusk over the Strait of Hormuz — tanker, air base, missiles."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (58, 40, 86), (232, 120, 52))
    # low sun
    sx, sy, sr = x0 + w * 0.3, y0 + h * 0.52, h * 0.13
    draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(250, 190, 90))
    # sea
    sea_y = y0 + h * 0.58
    draw.rectangle([x0, sea_y, x1, y1], fill=(24, 48, 84))
    waves(draw, (x0, sea_y + 4, x1, y1 - 4), (70, 120, 170), rows=3, amp=2)
    # sun glitter path
    for i in range(6):
        gy = sea_y + 6 + i * (h * 0.06)
        gw = sr * (1.6 - i * 0.12)
        draw.line([(sx - gw, gy), (sx + gw, gy)], fill=(240, 170, 90), width=3)
    # tanker mid-left with fire amidships
    ship(draw, (x0 + w * 0.03, sea_y - h * 0.16, x0 + w * 0.52, sea_y + h * 0.13),
         cargo=True)
    fx, fy = x0 + w * 0.33, sea_y - h * 0.05
    flame(draw, fx, fy, w * 0.09, h * 0.16)
    smoke(draw, fx + 4, fy - h * 0.14, h * 0.045, n=4)
    # air base on the right shore
    bx0 = x0 + w * 0.62
    draw.polygon([(bx0, sea_y), (x1, sea_y), (x1, y1), (bx0 + w * 0.06, y1)],
                 fill=(96, 84, 66))
    # runway
    draw.polygon([(bx0 + w * 0.05, y1 - h * 0.05), (x1 - w * 0.02, sea_y + h * 0.1),
                  (x1, sea_y + h * 0.16), (bx0 + w * 0.12, y1 - h * 0.01)],
                 fill=(52, 50, 52))
    # hangars (arched roofs)
    for i, hx in enumerate((0.66, 0.76, 0.86)):
        hx0, hx1 = x0 + w * hx, x0 + w * (hx + 0.085)
        hy1 = sea_y + h * 0.02
        hy0 = hy1 - h * 0.11
        draw.pieslice([hx0, hy0, hx1, hy1 + h * 0.05], 180, 360,
                      fill=(120, 124, 130))
        draw.rectangle([hx0, hy0 + h * 0.05, hx1, hy1], fill=(120, 124, 130))
        draw.rectangle([hx0 + 3, hy1 - h * 0.05, hx1 - 3, hy1], fill=(70, 72, 78))
    # radar dome on tower
    rx = x0 + w * 0.94
    draw.rectangle([rx - 3, sea_y - h * 0.16, rx + 3, sea_y], fill=(200, 204, 210))
    draw.ellipse([rx - w * 0.035, sea_y - h * 0.26, rx + w * 0.035,
                  sea_y - h * 0.15], fill=(235, 238, 242))
    # parked jet silhouette
    jx, jy = x0 + w * 0.8, sea_y + h * 0.14
    draw.polygon([(jx, jy), (jx + w * 0.07, jy + h * 0.015),
                  (jx + w * 0.045, jy + h * 0.045), (jx + w * 0.02, jy + h * 0.04)],
                 fill=(30, 30, 34))
    draw.polygon([(jx + w * 0.05, jy + h * 0.01), (jx + w * 0.075, jy - h * 0.02),
                  (jx + w * 0.08, jy + h * 0.015)], fill=(30, 30, 34))
    # missile arcs incoming from top-left
    targets = [(x0 + w * 0.7, sea_y - h * 0.02), (x0 + w * 0.88, sea_y - h * 0.04)]
    starts = [(x0 + w * 0.06, y0 + h * 0.05), (x0 + w * 0.2, y0 + h * 0.02)]
    for (sx2, sy2), (tx, ty) in zip(starts, targets):
        mid = ((sx2 + tx) / 2, min(sy2, ty) - h * 0.12)
        pts = bezier((sx2, sy2), mid, (tx, ty), n=36)
        for i in range(0, len(pts) - 3, 4):
            draw.line([pts[i], pts[i + 2]], fill=(250, 220, 160), width=2)
        starburst(draw, tx, ty, h * 0.075, h * 0.032, 9, (250, 160, 50))
        starburst(draw, tx, ty, h * 0.042, h * 0.018, 9, (252, 230, 160), rot=0.3)
    # drone silhouettes
    for dx, dy in ((0.45, 0.12), (0.55, 0.2)):
        cx, cy = x0 + w * dx, y0 + h * dy
        draw.line([(cx - 9, cy), (cx + 9, cy)], fill=(25, 22, 30), width=2)
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(25, 22, 30))
        draw.line([(cx - 9, cy - 4), (cx - 9, cy + 3)], fill=(25, 22, 30), width=2)
        draw.line([(cx + 9, cy - 4), (cx + 9, cy + 3)], fill=(25, 22, 30), width=2)
    draw.rectangle(box, outline=INK, width=2)


def scene_missile_city(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (30, 34, 66), (120, 80, 80))
    # skyline
    heights = [0.5, 0.72, 0.42, 0.8, 0.58, 0.68, 0.46, 0.62]
    bw = w / len(heights)
    for i, hf in enumerate(heights):
        bx0 = x0 + i * bw + 1
        bx1 = x0 + (i + 1) * bw - 1
        by0 = y1 - h * hf
        col = (44, 46, 60) if i != 3 else (66, 52, 48)
        draw.rectangle([bx0, by0, bx1, y1], fill=col)
        for wy in range(int(by0) + 5, int(y1) - 6, 8):
            for wx in range(int(bx0) + 4, int(bx1) - 4, 7):
                if (wx * 7 + wy * 13) % 5 == 0:
                    draw.rectangle([wx, wy, wx + 3, wy + 4], fill=(250, 210, 120))
    # missile descending with flame trail
    mx, my = x0 + w * 0.62, y0 + h * 0.16
    draw.line([(mx - w * 0.3, y0 + 2), (mx, my)], fill=(250, 200, 120), width=2)
    draw.polygon([(mx, my), (mx - 4, my - 9), (mx + 5, my - 7)], fill=(230, 230, 235))
    flame(draw, mx - 2, my - 8, 7, 10)
    # explosion at hit building
    ex, ey = x0 + w * 0.47, y1 - h * 0.8
    starburst(draw, ex, ey, h * 0.38, h * 0.16, 8, (250, 150, 40))
    starburst(draw, ex, ey, h * 0.2, h * 0.09, 8, (252, 225, 150), rot=0.4)
    smoke(draw, ex + 6, ey - h * 0.22, h * 0.09, n=3)
    draw.rectangle(box, outline=INK, width=1)


def scene_burning_ship(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (150, 180, 205), (210, 225, 235))
    sea_y = y0 + h * 0.62
    draw.rectangle([x0, sea_y, x1, y1], fill=(30, 80, 130))
    waves(draw, (x0, sea_y + 2, x1, y1 - 2), (110, 170, 215), rows=2, amp=2)
    ship(draw, (x0 + w * 0.06, sea_y - h * 0.34, x0 + w * 0.94, sea_y + h * 0.22),
         cargo=True)
    flame(draw, x0 + w * 0.5, sea_y - h * 0.18, w * 0.13, h * 0.34)
    flame(draw, x0 + w * 0.62, sea_y - h * 0.16, w * 0.09, h * 0.26)
    smoke(draw, x0 + w * 0.52, sea_y - h * 0.42, h * 0.1, n=4)
    # drone above
    cx, cy = x0 + w * 0.24, y0 + h * 0.16
    draw.line([(cx - 8, cy), (cx + 8, cy)], fill=(30, 30, 34), width=2)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(30, 30, 34))
    draw.rectangle(box, outline=INK, width=1)


def scene_globe_flame(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (16, 42, 66), (30, 90, 110))
    cx, cy, r = x0 + w * 0.42, y0 + h * 0.56, h * 0.4
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(52, 130, 190),
                 outline=(210, 235, 250), width=2)
    # continent blobs
    for bx, by, br in ((-0.4, -0.25, 0.3), (0.25, -0.35, 0.26), (0.05, 0.3, 0.3),
                       (-0.15, 0.05, 0.2)):
        draw.ellipse([cx + bx * r - br * r, cy + by * r - br * r * 0.7,
                      cx + bx * r + br * r, cy + by * r + br * r * 0.7],
                     fill=(70, 170, 90))
    # meridian arcs
    for k in (-0.55, 0.0, 0.55):
        draw.arc([cx - r * abs(k) - 2, cy - r, cx + r * abs(k) + 2, cy + r],
                 90, 270, fill=(200, 230, 245), width=1)
    draw.line([(cx - r, cy), (cx + r, cy)], fill=(200, 230, 245), width=1)
    # flame rising off the top
    flame(draw, cx + r * 0.25, cy - r * 0.92, r * 0.55, r * 0.85)
    smoke(draw, cx + r * 0.3, cy - r * 1.15, r * 0.16, n=3, col=(150, 150, 150))
    # thermometer at right
    tx = x0 + w * 0.8
    draw.rounded_rectangle([tx - 5, y0 + h * 0.12, tx + 5, y0 + h * 0.72],
                           radius=5, fill=(240, 244, 248))
    draw.ellipse([tx - 9, y0 + h * 0.66, tx + 9, y0 + h * 0.9], fill=(220, 60, 40))
    draw.rectangle([tx - 2, y0 + h * 0.3, tx + 2, y0 + h * 0.72], fill=(220, 60, 40))
    draw.rectangle(box, outline=INK, width=1)


def scene_prison(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (52, 54, 60), (34, 34, 40))
    # silhouette: head + shoulders
    cx = x0 + w * 0.5
    draw.ellipse([cx - h * 0.16, y0 + h * 0.24, cx + h * 0.16, y0 + h * 0.56],
                 fill=(12, 12, 14))
    draw.pieslice([cx - h * 0.34, y0 + h * 0.52, cx + h * 0.34, y0 + h * 1.1],
                  180, 360, fill=(12, 12, 14))
    # bars
    nb = 7
    for i in range(nb):
        bx = x0 + w * (i + 0.5) / nb
        draw.rectangle([bx - 2.5, y0 + 2, bx + 2.5, y1 - 2], fill=(150, 152, 158))
    draw.rectangle([x0 + 2, y0 + h * 0.3, x1 - 2, y0 + h * 0.3 + 4],
                   fill=(130, 132, 138))
    draw.rectangle([x0 + 2, y0 + h * 0.68, x1 - 2, y0 + h * 0.68 + 4],
                   fill=(130, 132, 138))
    # handcuff ring bottom right
    hx, hy = x0 + w * 0.82, y1 - h * 0.18
    draw.ellipse([hx - 8, hy - 8, hx + 8, hy + 8], outline=(210, 212, 216), width=3)
    draw.rectangle(box, outline=INK, width=1)


def scene_quake(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (196, 200, 208), (232, 224, 200))
    gy = y0 + h * 0.72
    draw.rectangle([x0, gy, x1, y1], fill=(120, 98, 74))
    # tilted buildings
    for bx, bw2, bh, tilt in ((0.08, 0.2, 0.5, -6), (0.34, 0.24, 0.62, 5),
                              (0.64, 0.2, 0.44, -4)):
        bx0 = x0 + w * bx
        bx1 = bx0 + w * bw2
        by0 = gy - h * bh
        draw.polygon([(bx0, gy), (bx0 + tilt, by0), (bx1 + tilt, by0), (bx1, gy)],
                     fill=(96, 92, 88))
        for wy in range(int(by0) + 5, int(gy) - 5, 8):
            draw.rectangle([bx0 + 4 + tilt * (gy - wy) / (h * bh), wy,
                            bx1 - 4 + tilt * (gy - wy) / (h * bh), wy + 3],
                           fill=(60, 58, 54))
    # crack zigzag across ground
    pts = []
    cx = x0 + 4
    up = True
    while cx < x1 - 4:
        pts.append((cx, gy + h * (0.1 if up else 0.2)))
        cx += w * 0.09
        up = not up
    draw.line(pts, fill=(30, 24, 18), width=3)
    # dust puffs
    for dx in (0.2, 0.55, 0.85):
        draw.ellipse([x0 + w * dx - 9, gy - 7, x0 + w * dx + 9, gy + 5],
                     fill=(196, 180, 152))
    # magnitude badge
    bx, by, br = x1 - h * 0.22, y0 + h * 0.24, h * 0.2
    draw.ellipse([bx - br, by - br, bx + br, by + br], fill=(200, 40, 30),
                 outline=(255, 255, 255), width=2)
    f = F(SANS_B, max(9, int(br * 0.85)))
    t = "6.9"
    draw.text((bx - text_w(draw, t, f) / 2, by - br * 0.42), t, font=f,
              fill=(255, 255, 255))
    draw.rectangle(box, outline=INK, width=1)


def scene_chart(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    draw.rectangle(box, fill=(14, 20, 34))
    # grid
    for i in range(1, 4):
        gy = y0 + h * i / 4
        draw.line([(x0 + 4, gy), (x1 - 4, gy)], fill=(46, 62, 92), width=1)
    for i in range(1, 6):
        gx = x0 + w * i / 6
        draw.line([(gx, y0 + 3), (gx, y1 - 3)], fill=(36, 50, 78), width=1)
    # candlesticks falling
    vals = [0.22, 0.3, 0.26, 0.42, 0.5, 0.62, 0.74, 0.86]
    cw = w * 0.07
    for i, v in enumerate(vals):
        cx = x0 + w * 0.1 + i * w * 0.105
        top = y0 + h * v
        bot = top + h * 0.14
        draw.line([(cx + cw / 2, top - 3), (cx + cw / 2, bot + 3)],
                  fill=(240, 90, 80), width=1)
        draw.rectangle([cx, top, cx + cw, bot], fill=(220, 60, 50))
    # plunge line + arrow
    pts = [(x0 + w * 0.06, y0 + h * 0.2), (x0 + w * 0.3, y0 + h * 0.32),
           (x0 + w * 0.5, y0 + h * 0.3), (x0 + w * 0.72, y0 + h * 0.55),
           (x0 + w * 0.92, y0 + h * 0.84)]
    draw.line(pts, fill=(255, 80, 70), width=3)
    draw.polygon([(x0 + w * 0.92, y0 + h * 0.88), (x0 + w * 0.85, y0 + h * 0.8),
                  (x0 + w * 0.94, y0 + h * 0.76)], fill=(255, 80, 70))
    draw.rectangle(box, outline=INK, width=1)


def scene_plane(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (90, 150, 210), (190, 220, 245))
    # clouds
    for cxr, cyr, cr in ((0.18, 0.3, 0.16), (0.78, 0.22, 0.13), (0.6, 0.72, 0.15)):
        cx, cy, r = x0 + w * cxr, y0 + h * cyr, h * cr
        for ox in (-0.7, 0, 0.7):
            draw.ellipse([cx + ox * r - r * 0.75, cy - r * 0.5,
                          cx + ox * r + r * 0.75, cy + r * 0.5],
                         fill=(245, 248, 252))
    # jet side profile
    jy = y0 + h * 0.52
    jx0, jx1 = x0 + w * 0.14, x0 + w * 0.88
    draw.polygon([(jx0, jy), (jx0 + w * 0.1, jy - h * 0.1), (jx1 - w * 0.1, jy - h * 0.1),
                  (jx1, jy - h * 0.02), (jx1 - w * 0.06, jy + h * 0.06),
                  (jx0 + w * 0.08, jy + h * 0.07)], fill=(240, 243, 247),
                 outline=(120, 130, 145))
    # tail fin + wing
    draw.polygon([(jx0 + w * 0.02, jy - h * 0.08), (jx0 + w * 0.1, jy - h * 0.3),
                  (jx0 + w * 0.16, jy - h * 0.09)], fill=(200, 40, 40))
    draw.polygon([(x0 + w * 0.42, jy + h * 0.05), (x0 + w * 0.58, jy + h * 0.24),
                  (x0 + w * 0.66, jy + h * 0.24), (x0 + w * 0.55, jy + h * 0.04)],
                 fill=(190, 198, 210))
    # windows
    for i in range(9):
        wx = jx0 + w * (0.2 + i * 0.06)
        draw.ellipse([wx, jy - h * 0.055, wx + 4, jy - h * 0.055 + 4],
                     fill=(70, 110, 160))
    # smoking engine under wing
    ex, ey = x0 + w * 0.55, jy + h * 0.16
    draw.ellipse([ex - 7, ey - 5, ex + 7, ey + 5], fill=(90, 96, 108))
    flame(draw, ex + 8, ey + 2, 8, 9)
    smoke(draw, ex + 16, ey - 4, 5, n=3, col=(90, 92, 98))
    # runway
    draw.rectangle([x0, y1 - h * 0.1, x1, y1], fill=(70, 72, 78))
    for i in range(6):
        rx = x0 + w * (0.06 + i * 0.16)
        draw.rectangle([rx, y1 - h * 0.055, rx + w * 0.08, y1 - h * 0.04],
                       fill=(245, 245, 240))
    draw.rectangle(box, outline=INK, width=1)


def scene_border(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (170, 195, 220), (225, 232, 238))
    gy = y0 + h * 0.74
    draw.rectangle([x0, gy, x1, y1], fill=(150, 148, 140))
    # fence with posts
    for i in range(9):
        fx = x0 + w * (0.04 + i * 0.115)
        draw.rectangle([fx, y0 + h * 0.3, fx + 3, gy], fill=(90, 92, 96))
    draw.line([(x0 + 2, y0 + h * 0.38), (x1 - 2, y0 + h * 0.38)],
              fill=(120, 122, 126), width=2)
    draw.line([(x0 + 2, y0 + h * 0.55), (x1 - 2, y0 + h * 0.55)],
              fill=(120, 122, 126), width=2)
    # barrier arm (striped, lowered)
    ax0, ay = x0 + w * 0.1, y0 + h * 0.62
    ax1 = x0 + w * 0.9
    draw.rectangle([ax0, ay - 4, ax1, ay + 4], fill=(245, 245, 245))
    seg = (ax1 - ax0) / 8
    for i in range(0, 8, 2):
        draw.rectangle([ax0 + i * seg, ay - 4, ax0 + (i + 1) * seg, ay + 4],
                       fill=(210, 40, 40))
    draw.rectangle([ax0 - 3, ay - 4, ax0 + 5, gy], fill=(70, 72, 78))
    # watchtower
    tx = x0 + w * 0.82
    draw.polygon([(tx - 10, gy), (tx - 6, y0 + h * 0.2), (tx + 6, y0 + h * 0.2),
                  (tx + 10, gy)], fill=(110, 100, 84))
    draw.rectangle([tx - 12, y0 + h * 0.1, tx + 12, y0 + h * 0.22],
                   fill=(130, 120, 100))
    draw.polygon([(tx - 14, y0 + h * 0.1), (tx, y0 + h * 0.02),
                  (tx + 14, y0 + h * 0.1)], fill=(80, 70, 56))
    # closed sign
    sx, sy, sr = x0 + w * 0.3, y0 + h * 0.3, h * 0.17
    draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 255, 255),
                 outline=(210, 40, 40), width=3)
    draw.line([(sx - sr * 0.6, sy + sr * 0.6), (sx + sr * 0.6, sy - sr * 0.6)],
              fill=(210, 40, 40), width=3)
    draw.rectangle(box, outline=INK, width=1)


def scene_racecar(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (12, 14, 38), (40, 30, 80))
    # neon skyline
    for i, hf in enumerate((0.4, 0.62, 0.5, 0.74, 0.56, 0.66, 0.44, 0.58)):
        bx0 = x0 + i * w / 8 + 1
        bx1 = x0 + (i + 1) * w / 8 - 1
        draw.rectangle([bx0, y1 - h * 0.34 - h * hf * 0.5, bx1, y1 - h * 0.3],
                       fill=(24, 24, 52))
        draw.line([(bx0, y1 - h * 0.34 - h * hf * 0.5),
                   (bx1, y1 - h * 0.34 - h * hf * 0.5)],
                  fill=(255, 90, 200) if i % 2 else (90, 220, 255), width=2)
    # track
    draw.rectangle([x0, y1 - h * 0.3, x1, y1], fill=(38, 38, 44))
    draw.line([(x0, y1 - h * 0.3), (x1, y1 - h * 0.3)], fill=(245, 245, 245),
              width=2)
    # F1 car profile
    cy = y1 - h * 0.22
    cx0 = x0 + w * 0.18
    # rear wing
    draw.rectangle([cx0, cy - h * 0.3, cx0 + w * 0.05, cy - h * 0.12],
                   fill=(200, 30, 40))
    draw.rectangle([cx0 - w * 0.02, cy - h * 0.32, cx0 + w * 0.08, cy - h * 0.27],
                   fill=(30, 30, 36))
    # body + nose
    draw.polygon([(cx0 + w * 0.03, cy - h * 0.1), (cx0 + w * 0.3, cy - h * 0.16),
                  (cx0 + w * 0.42, cy - h * 0.13), (cx0 + w * 0.62, cy - h * 0.05),
                  (cx0 + w * 0.64, cy), (cx0 + w * 0.03, cy)], fill=(210, 35, 45))
    # halo + driver helmet
    draw.arc([cx0 + w * 0.24, cy - h * 0.26, cx0 + w * 0.4, cy - h * 0.08],
             180, 360, fill=(30, 30, 36), width=3)
    draw.ellipse([cx0 + w * 0.28, cy - h * 0.22, cx0 + w * 0.34, cy - h * 0.12],
                 fill=(250, 200, 60))
    # front wing
    draw.rectangle([cx0 + w * 0.58, cy - h * 0.03, cx0 + w * 0.7, cy + 1],
                   fill=(30, 30, 36))
    # wheels
    for wx in (cx0 + w * 0.1, cx0 + w * 0.52):
        wr = h * 0.1
        draw.ellipse([wx - wr, cy - wr, wx + wr, cy + wr], fill=(16, 16, 20),
                     outline=(90, 90, 100), width=2)
        draw.ellipse([wx - wr * 0.4, cy - wr * 0.4, wx + wr * 0.4, cy + wr * 0.4],
                     fill=(160, 164, 172))
    # speed lines
    for i, sy in enumerate((0.18, 0.26, 0.34)):
        draw.line([(x0 + 4, y0 + h * sy), (x0 + w * (0.1 + i * 0.03), y0 + h * sy)],
                  fill=(200, 220, 255), width=2)
    # checkered flag top-right
    fx, fy = x1 - w * 0.16, y0 + h * 0.06
    draw.line([(fx, fy), (fx, fy + h * 0.34)], fill=(240, 240, 240), width=2)
    sq = w * 0.028
    for r in range(3):
        for c in range(4):
            col = (20, 20, 24) if (r + c) % 2 == 0 else (245, 245, 245)
            draw.rectangle([fx + c * sq, fy + r * sq, fx + (c + 1) * sq,
                            fy + (r + 1) * sq], fill=col)
    draw.rectangle(box, outline=INK, width=1)


def scene_desert(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (240, 190, 110), (248, 224, 170))
    # sun
    sx, sy, sr = x0 + w * 0.82, y0 + h * 0.22, h * 0.16
    draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(250, 170, 60))
    # dunes
    draw.polygon([(x0, y1), (x0, y0 + h * 0.66), (x0 + w * 0.35, y0 + h * 0.56),
                  (x0 + w * 0.7, y0 + h * 0.68), (x1, y0 + h * 0.6), (x1, y1)],
                 fill=(226, 178, 104))
    draw.polygon([(x0, y1), (x0, y0 + h * 0.8), (x0 + w * 0.5, y0 + h * 0.72),
                  (x1, y0 + h * 0.82), (x1, y1)], fill=(206, 154, 82))
    # huts
    for hx, hs in ((0.14, 1.0), (0.34, 0.8), (0.55, 0.9)):
        bx = x0 + w * hx
        bw2, bh = w * 0.16 * hs, h * 0.3 * hs
        by = y1 - h * 0.12
        draw.rectangle([bx, by - bh * 0.55, bx + bw2, by], fill=(150, 108, 66))
        draw.polygon([(bx - 3, by - bh * 0.55), (bx + bw2 / 2, by - bh),
                      (bx + bw2 + 3, by - bh * 0.55)], fill=(116, 80, 44))
        draw.rectangle([bx + bw2 * 0.38, by - bh * 0.34, bx + bw2 * 0.62, by],
                       fill=(70, 48, 28))
    # smoke column from village
    smoke(draw, x0 + w * 0.42, y0 + h * 0.42, h * 0.09, n=4, col=(80, 74, 68))
    flame(draw, x0 + w * 0.4, y1 - h * 0.2, w * 0.07, h * 0.18)
    # acacia tree
    tx = x0 + w * 0.9
    draw.line([(tx, y1 - h * 0.1), (tx, y0 + h * 0.42)], fill=(90, 64, 36), width=3)
    draw.ellipse([tx - w * 0.09, y0 + h * 0.28, tx + w * 0.09, y0 + h * 0.44],
                 fill=(96, 120, 52))
    draw.rectangle(box, outline=INK, width=1)


def scene_vaccine(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (225, 238, 248), (245, 250, 252))
    # virus dots background
    for vx, vy, vr in ((0.12, 0.2, 0.1), (0.85, 0.16, 0.08), (0.7, 0.8, 0.11),
                       (0.2, 0.82, 0.07)):
        cx, cy, r = x0 + w * vx, y0 + h * vy, h * vr
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(200, 90, 90))
        for k in range(8):
            ang = k * math.pi / 4
            draw.line([(cx + r * math.cos(ang), cy + r * math.sin(ang)),
                       (cx + r * 1.5 * math.cos(ang), cy + r * 1.5 * math.sin(ang))],
                      fill=(200, 90, 90), width=2)
            draw.ellipse([cx + r * 1.5 * math.cos(ang) - 2,
                          cy + r * 1.5 * math.sin(ang) - 2,
                          cx + r * 1.5 * math.cos(ang) + 2,
                          cy + r * 1.5 * math.sin(ang) + 2], fill=(200, 90, 90))
    # vial
    vx0, vx1 = x0 + w * 0.3, x0 + w * 0.52
    vy0, vy1 = y0 + h * 0.3, y1 - h * 0.08
    draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=5, fill=(250, 252, 254),
                           outline=(90, 120, 150), width=2)
    draw.rectangle([vx0 + 3, vy0 + (vy1 - vy0) * 0.45, vx1 - 3, vy1 - 3],
                   fill=(120, 190, 230))
    draw.rectangle([vx0 - 2, vy0 - h * 0.09, vx1 + 2, vy0], fill=(70, 110, 160))
    draw.rectangle([vx0 + 4, vy0 + (vy1 - vy0) * 0.12, vx1 - 4,
                    vy0 + (vy1 - vy0) * 0.38], fill=(255, 255, 255),
                   outline=(150, 170, 195))
    # syringe diagonal
    sx0, sy0 = x0 + w * 0.58, y0 + h * 0.18
    sx1, sy1 = x0 + w * 0.8, y0 + h * 0.62
    draw.line([(sx0, sy0), (sx1, sy1)], fill=(90, 120, 150), width=7)
    draw.line([(sx0, sy0), (sx1, sy1)], fill=(200, 230, 245), width=4)
    draw.line([(sx1, sy1), (sx1 + w * 0.07, sy1 + h * 0.14)], fill=(70, 80, 95),
              width=2)
    draw.line([(sx0 - 6, sy0 - 4), (sx0 + 4, sy0 - 8)], fill=(90, 120, 150), width=3)
    # red cross badge
    bx, by = x0 + w * 0.88, y0 + h * 0.78
    draw.ellipse([bx - 11, by - 11, bx + 11, by + 11], fill=(255, 255, 255),
                 outline=(200, 50, 50), width=2)
    draw.rectangle([bx - 2, by - 7, bx + 2, by + 7], fill=(200, 50, 50))
    draw.rectangle([bx - 7, by - 2, bx + 7, by + 2], fill=(200, 50, 50))
    draw.rectangle(box, outline=INK, width=1)


def scene_rugby(draw, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    vgrad(draw, box, (24, 60, 36), (40, 110, 56))
    # pitch stripes
    for i in range(5):
        if i % 2 == 0:
            draw.rectangle([x0 + i * w / 5, y0 + h * 0.55,
                            x0 + (i + 1) * w / 5, y1], fill=(46, 122, 62))
    draw.rectangle([x0, y0 + h * 0.55, x1, y1], outline=None)
    draw.line([(x0, y0 + h * 0.55), (x1, y0 + h * 0.55)], fill=(240, 245, 240),
              width=2)
    # goal posts
    px = x0 + w * 0.5
    draw.line([(px - w * 0.12, y0 + h * 0.06), (px - w * 0.12, y0 + h * 0.62)],
              fill=(245, 248, 245), width=3)
    draw.line([(px + w * 0.12, y0 + h * 0.06), (px + w * 0.12, y0 + h * 0.62)],
              fill=(245, 248, 245), width=3)
    draw.line([(px - w * 0.12, y0 + h * 0.42), (px + w * 0.12, y0 + h * 0.42)],
              fill=(245, 248, 245), width=3)
    # ball sailing between posts
    bx, by = px, y0 + h * 0.26
    draw.ellipse([bx - 11, by - 7, bx + 11, by + 7], fill=(150, 90, 50),
                 outline=(90, 55, 28), width=2)
    draw.line([(bx - 5, by), (bx + 5, by)], fill=(250, 250, 250), width=2)
    # floodlights
    for lx in (0.08, 0.92):
        cx = x0 + w * lx
        draw.line([(cx, y0 + h * 0.55), (cx, y0 + h * 0.14)], fill=(30, 34, 30),
                  width=3)
        for dx in (-6, 0, 6):
            draw.ellipse([cx + dx - 3, y0 + h * 0.08, cx + dx + 3, y0 + h * 0.14],
                         fill=(252, 240, 180))
    # crowd dots
    for i in range(28):
        cx = x0 + (i * 37 % int(w))
        cy = y0 + h * 0.6 + (i * 13 % int(h * 0.3))
        draw.ellipse([cx, cy, cx + 3, cy + 3], fill=(230, 225, 210))
    draw.rectangle(box, outline=INK, width=1)


SCENES = {
    "gulf": scene_gulf,
    "missile_city": scene_missile_city,
    "burning_ship": scene_burning_ship,
    "globe_flame": scene_globe_flame,
    "prison": scene_prison,
    "quake": scene_quake,
    "chart": scene_chart,
    "plane": scene_plane,
    "border": scene_border,
    "racecar": scene_racecar,
    "desert": scene_desert,
    "vaccine": scene_vaccine,
    "rugby": scene_rugby,
}


# ---------------------------------------------------------------- layout

def chip(draw, x, y, text, bg, fg=(255, 255, 255), size=10, pad_x=6, pad_y=3):
    f = F(SANS_B, size)
    tw = text_w(draw, text, f)
    th = size + pad_y * 2
    draw.rectangle([x, y, x + tw + pad_x * 2, y + th], fill=bg)
    draw.text((x + pad_x, y + pad_y - 1), text, font=f, fill=fg)
    return tw + pad_x * 2, th


def draw_masthead(draw, data):
    draw.rectangle([0, 0, W, 84], fill=NAVY)
    draw.rectangle([0, 84, W, 88], fill=GOLD)
    # title
    tf = F(SERIF_B, 41)
    draw.text((MARGIN, 10), data["masthead"], font=tf, fill=(250, 246, 235))
    sf = F(SANS_B, 10)
    draw.text((MARGIN + 2, 58), data["tagline"].upper(), font=sf, fill=GOLD_LT)
    # date block, right aligned
    d1 = F(SANS_B, 13)
    d2 = F(SERIF_B, 20)
    s1, s2 = "SUNDAY", "22 NOVEMBER 2026"
    draw.text((W - MARGIN - text_w(draw, s1, d1), 14), s1, font=d1, fill=GOLD_LT)
    draw.text((W - MARGIN - text_w(draw, s2, d2), 30), s2, font=d2,
              fill=(250, 246, 235))
    # thin vertical divider before date
    dx = W - MARGIN - text_w(draw, s2, d2) - 14
    draw.line([(dx, 14), (dx, 70)], fill=GOLD, width=2)
    # dateline strip
    lf = F(SANS_B, 10)
    draw.text((MARGIN, 93), "WORLD NEWS IN ONE IMAGE", font=lf, fill=GREY)
    right = "EVERYWHERE EDITION"
    draw.text((W - MARGIN - text_w(draw, right, lf), 93), right, font=lf,
              fill=GREY)
    draw.line([(MARGIN, 108), (W - MARGIN, 108)], fill=RULE, width=1)


def draw_lead(draw, data):
    lead = data["lead"]
    top, bot = 114, 344
    scene_box = (MARGIN, top, MARGIN + 528, bot - 16)
    SCENES[lead["scene"]](draw, scene_box)
    # caption under scene
    cap = F(SANS_I, 10)
    draw.text((MARGIN, bot - 13),
              "The Strait of Hormuz at dusk: a tanker burns as missiles "
              "fall on Gulf bases.", font=cap, fill=GREY)
    tx = MARGIN + 544
    tw = W - MARGIN - tx
    y = top
    cw, ch = chip(draw, tx, y, lead["kicker"], RED, size=11)
    y += ch + 8
    hf, hlines = fit_lines(draw, lead["headline"], SERIF_B, tw, 3, 30, 22)
    y = draw_lines(draw, tx, y, hlines, hf, INK, hf.size + 3)
    y += 4
    sf, slines = fit_lines(draw, lead["summary"], SANS, tw, 4, 14, 12)
    y = draw_lines(draw, tx, y, slines, sf, (48, 44, 40), sf.size + 3)
    y += 6
    bf = F(SANS, 12)
    for b in lead["bullets"]:
        blines = wrap(draw, b, bf, tw - 14)
        draw.rectangle([tx, y + 4, tx + 7, y + 11], fill=RED)
        y = draw_lines(draw, tx + 14, y, blines, bf, (40, 36, 32), 15)
        y += 3
    # double rule under lead
    draw.line([(MARGIN, bot + 6), (W - MARGIN, bot + 6)], fill=RULE, width=2)
    draw.line([(MARGIN, bot + 10), (W - MARGIN, bot + 10)], fill=RULE, width=1)


def draw_card(draw, box, story):
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=CARD_BG, outline=CARD_EDGE, width=1)
    scene_h = 34
    sbox = (x0 + 1, y0 + 1, x1 - 1, y0 + 1 + scene_h)
    SCENES[story["scene"]](draw, sbox)
    # region chip overlaid bottom-left of scene
    col = REGION_COLORS.get(story["region"], GREY)
    chip(draw, x0 + 4, y0 + scene_h - 11, story["region"], col, size=8,
         pad_x=4, pad_y=2)
    pad = 6
    tx, tw = x0 + pad, (x1 - x0) - 2 * pad
    y = y0 + scene_h + 4
    hf, hlines = fit_lines(draw, story["headline"], SANS_B, tw, 2, 13, 11)
    y = draw_lines(draw, tx, y, hlines, hf, INK, hf.size)
    y += 1
    sf, slines = fit_lines(draw, story["summary"], SANS, tw, 2, 11, 10)
    draw_lines(draw, tx, y, slines, sf, (70, 64, 56), sf.size)


def draw_grid(draw, data):
    top = 366
    cols, rows = 4, 3
    gap_x, gap_y = 10, 6
    cw = (CONTENT_W - (cols - 1) * gap_x) // cols
    ch = 90
    for i, story in enumerate(data["cards"][:12]):
        r, c = divmod(i, cols)
        x0 = MARGIN + c * (cw + gap_x)
        y0 = top + r * (ch + gap_y)
        draw_card(draw, (x0, y0, x0 + cw, y0 + ch), story)
    bot = top + rows * ch + (rows - 1) * gap_y
    draw.line([(MARGIN, bot + 6), (W - MARGIN, bot + 6)], fill=RULE, width=2)
    draw.line([(MARGIN, bot + 10), (W - MARGIN, bot + 10)], fill=RULE, width=1)
    return bot + 16


def draw_lists(draw, data, top, bottom):
    cols = 4
    gap = 14
    cw = (CONTENT_W - (cols - 1) * gap) // cols
    hf = F(SANS_B, 13)
    sf = F(SANS, 11)
    head_h = 17          # region header bar + gap
    item_gap = 4
    col = 0
    y = top
    drawn = 0

    def next_col():
        nonlocal col, y
        col += 1
        y = top

    def cx():
        return MARGIN + col * (cw + gap)

    for group in data["lists"]:
        region = group["region"]
        colr = REGION_COLORS.get(region, GREY)
        items = group["items"]
        # measure first item to decide whether the header fits here
        def item_h(it):
            hl = wrap(draw, it["headline"], hf, cw)
            sl = wrap(draw, it["summary"], sf, cw)
            return len(hl) * 13 + len(sl) * 11 + item_gap

        if y + head_h + item_h(items[0]) > bottom and col < cols - 1:
            next_col()
        # header bar
        draw.rectangle([cx(), y, cx() + cw, y + 15], fill=colr)
        draw.text((cx() + 6, y + 2), region, font=F(SANS_B, 10),
                  fill=(255, 255, 255))
        y += head_h
        for it in items:
            if col >= cols:
                break
            ih = item_h(it)
            if y + ih > bottom and col < cols - 1:
                next_col()
                draw.rectangle([cx(), y, cx() + cw, y + 15], fill=colr)
                draw.text((cx() + 6, y + 2), region + " (CONT.)",
                          font=F(SANS_B, 10), fill=(255, 255, 255))
                y += head_h
            hl = wrap(draw, it["headline"], hf, cw)
            y = draw_lines(draw, cx(), y, hl, hf, INK, 13)
            sl = wrap(draw, it["summary"], sf, cw)
            y = draw_lines(draw, cx(), y, sl, sf, (74, 68, 60), 11)
            y += item_gap
            drawn += 1
        y += 3
    # vertical hairlines between columns
    for c in range(1, cols):
        lx = MARGIN + c * (cw + gap) - gap // 2
        draw.line([(lx, top), (lx, bottom)], fill=(180, 170, 150), width=1)
    assert y - item_gap <= bottom, "lists overflow: y=%d bottom=%d" % (y, bottom)
    return drawn


def draw_ticker(draw, data, top):
    bot = top + 44
    draw.rectangle([0, top, W, bot], fill=NAVY)
    draw.rectangle([0, top, W, top + 2], fill=GOLD)
    lab_f = F(SANS_B, 12)
    draw.rectangle([0, top + 2, 92, bot], fill=RED)
    draw.text((12, top + 15), "LATEST", font=lab_f, fill=(255, 255, 255))
    tf = F(SANS, 11)
    joined = "  •  ".join(data["ticker"])
    lines = wrap(draw, joined, tf, W - 92 - 2 * MARGIN)
    assert len(lines) <= 3, "ticker needs %d lines" % len(lines)
    draw_lines(draw, 92 + MARGIN, top + 3, lines, tf, (238, 234, 222), 13)
    return bot


def draw_footer(draw, data, top, n_stories, n_regions, n_illus):
    lf = F(SANS_B, 11)
    left = "%d STORIES · %d REGIONS · %d ILLUSTRATIONS" % (
        n_stories, n_regions, n_illus)
    draw.text((MARGIN, top + 6), left, font=lf, fill=INK)
    mid = data["date_line"]
    mf = F(SERIF_B, 13)
    draw.text(((W - text_w(draw, mid, mf)) / 2, top + 4), mid, font=mf,
              fill=NAVY)
    rf = F(SANS, 10)
    right = "Sources: Reuters · AP · CNN · AFP · PAHO · UKMTO"
    draw.text((W - MARGIN - text_w(draw, right, rf), top + 7), right, font=rf,
              fill=GREY)
    draw.text((MARGIN, top + 22),
              "Drawn in code with Pillow from the day's reported news. "
              "Every headline above was reported on 22 November 2026.",
              font=F(SANS_I, 9), fill=GREY)


def main():
    with open(os.path.join(HERE, "stories.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_masthead(draw, data)
    draw_lead(draw, data)
    lists_top = draw_grid(draw, data)
    ticker_top = 938
    n_listed = draw_lists(draw, data, lists_top, ticker_top - 8)
    total_listed = sum(len(g["items"]) for g in data["lists"])
    assert n_listed == total_listed, (n_listed, total_listed)
    ticker_bot = draw_ticker(draw, data, ticker_top)
    n_stories = (1 + len(data["cards"])
                 + sum(len(g["items"]) for g in data["lists"])
                 + len(data["ticker"]))
    n_regions = len(data["lists"])
    n_illus = 1 + len(data["cards"])
    draw_footer(draw, data, ticker_bot + 4, n_stories, n_regions, n_illus)
    out = os.path.join(HERE, "entry.png")
    img.save(out, "PNG", optimize=True)
    print("wrote", out, os.path.getsize(out), "bytes;",
          n_stories, "stories,", n_regions, "regions,", n_illus,
          "illustrations")


if __name__ == "__main__":
    main()
