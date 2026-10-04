import os
BASE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(BASE, 'build')
OUT = os.path.join(BASE, 'output')
os.makedirs(BUILD, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
import sys, json, math, random, textwrap, subprocess
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import qrcode

W, H = 1920, 1080
OW, OH = 1280, 720
FPS = 30
meta = json.load(open(os.path.join(BUILD, 'vo_meta.json')))
D = [m + 1.4 for m in meta]
S = [0.0]
for d in D:
    S.append(S[-1] + d)
TOTAL = S[-1]
LOGO_T = 3.214

VIOLET = (139, 92, 246); CYAN = (34, 211, 238); PINK = (244, 114, 182)
GREEN = (52, 211, 153); RED = (248, 113, 113); GRAY = (160, 170, 200)

def lerp(a, b, x): return a + (b - a) * x
def c01(x): return max(0.0, min(1.0, x))
def e_out(x): x = c01(x); return 1 - (1 - x) ** 3
def e_in(x): x = c01(x); return x ** 3
def e_io(x): x = c01(x); return x * x * (3 - 2 * x)
def e_back(x):
    x = c01(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

FD = os.path.join(BASE, "fonts") + os.sep
FM = FD
FILES = {'b': FD + 'Poppins-Bold.ttf', 'sb': FD + 'Poppins-Medium.ttf', 'm': FD + 'Poppins-Medium.ttf',
         'r': FD + 'Poppins-Regular.ttf', 'mono': FM + 'DejaVuSansMono.ttf'}

@lru_cache(None)
def F(style, size):
    return ImageFont.truetype(FILES[style], size)

def text(img, xy, s, font, fill=(255, 255, 255), a=1.0, anchor="la"):
    if a <= 0.01 or not s:
        return
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = d.textbbox(xy, s, font=font, anchor=anchor)
    pad = 6
    bx0, by0, bx1, by1 = int(x0) - pad, int(y0) - pad, int(x1) + pad, int(y1) + pad
    mask = Image.new("L", (bx1 - bx0, by1 - by0), 0)
    ImageDraw.Draw(mask).text((xy[0] - bx0, xy[1] - by0), s, font=font, fill=int(255 * min(a, 1)), anchor=anchor)
    img.paste(Image.new("RGB", mask.size, fill), (bx0, by0), mask)

def panel(img, box, r, fill=(255, 255, 255), fa=0.08, outline=None, oa=0.25, ow=2):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    if w <= 2 or h <= 2:
        return
    if fa > 0:
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=int(255 * min(fa, 1)))
        img.paste(Image.new("RGB", (w, h), fill), (x0, y0), m)
    if outline:
        m2 = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m2).rounded_rectangle((0, 0, w - 1, h - 1), r, outline=int(255 * min(oa, 1)), width=ow)
        img.paste(Image.new("RGB", (w, h), outline), (x0, y0), m2)

@lru_cache(64)
def grad(w, h, c1, c2):
    yy, xx = np.mgrid[0:h, 0:w]
    t = ((xx / max(w, 1)) + (yy / max(h, 1))) / 2.0
    arr = np.zeros((h, w, 3), np.float32)
    for k in range(3):
        arr[..., k] = c1[k] + (c2[k] - c1[k]) * t
    return Image.fromarray(arr.astype(np.uint8))

def gpill(img, box, r, c1=VIOLET, c2=CYAN, a=1.0):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    if w <= 2 or h <= 2:
        return
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=int(255 * min(a, 1)))
    img.paste(grad(w, h, c1, c2), (x0, y0), m)

def paste_layer(img, layer, cx, cy, scale=1.0, a=1.0):
    if a <= 0.01 or scale <= 0.01:
        return
    if scale != 1:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.BICUBIC)
    if a < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel('A').point(lambda v: int(v * a)))
    img.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)

def ring(img, cx, cy, r, color, a, width=6):
    if a <= 0.01:
        return
    r = int(r); size = 2 * r + 20
    ov = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse((10, 10, size - 10, size - 10), outline=color + (int(255 * a),), width=width)
    img.paste(ov, (int(cx - size / 2), int(cy - size / 2)), ov)

# ---------- logo ----------
def make_logo():
    fnt = F('b', 210)
    tw = int(fnt.getlength("Klip"))
    cw = 20 + 240 + 50 + tw + 20
    L = Image.new("RGBA", (cw, 300), (0, 0, 0, 0))
    m = Image.new("L", (240, 240), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 239, 239), 62, fill=255)
    L.paste(grad(240, 240, VIOLET, CYAN), (20, 30), m)
    d = ImageDraw.Draw(L)
    d.text((140, 154), "K", font=F('b', 170), fill=(255, 255, 255, 255), anchor="mm")
    d.text((310, 158), "Klip", font=fnt, fill=(255, 255, 255, 255), anchor="lm")
    return L
LOGO = make_logo()

# ---------- background ----------
def make_bg():
    yy, xx = np.mgrid[0:H, 0:W]
    t = (yy / H) * 0.8 + (xx / W) * 0.2
    c1 = np.array([8, 11, 26], np.float32); c2 = np.array([30, 18, 70], np.float32)
    arr = c1[None, None, :] + (c2 - c1)[None, None, :] * t[..., None]
    return Image.fromarray(arr.astype(np.uint8))
BG = make_bg()

def make_orb(r, color, alpha):
    yy, xx = np.mgrid[-r:r, -r:r]
    d = np.hypot(xx, yy) / r
    a = np.clip(1 - d, 0, 1) ** 2 * alpha * 255
    arr = np.zeros((2 * r, 2 * r, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = color
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")
ORBS = [(make_orb(560, VIOLET, 0.55), 0.35, 0.0, 380, 300), (make_orb(480, CYAN, 0.32), 0.28, 2.0, 1500, 800),
        (make_orb(420, PINK, 0.22), 0.22, 4.0, 1650, 220)]
_r = random.Random(11)
PARTS = [(_r.uniform(0, W), _r.uniform(0, H), _r.uniform(6, 22), _r.uniform(2, 5), _r.uniform(0.2, 0.6)) for _ in range(34)]

def decor(img, tt):
    for orb, sp, ph, bx, by in ORBS:
        x = bx + 140 * math.sin(tt * sp + ph); y = by + 90 * math.cos(tt * sp * 0.8 + ph)
        img.paste(orb, (int(x - orb.width / 2), int(y - orb.height / 2)), orb)
    d = ImageDraw.Draw(img)
    for x, y, v, s, b in PARTS:
        px = (x + v * 3 * tt) % W; py = (y - v * 4 * tt) % H
        c = int(60 + 90 * b)
        d.ellipse((px, py, px + s, py + s), fill=(c, c + 10, min(255, c + 70)))

# ---------- camera ----------
def kf(t, ks):
    if t <= ks[0][0]:
        return ks[0][1:]
    for (t0, *a), (t1, *b) in zip(ks, ks[1:]):
        if t0 <= t <= t1:
            x = e_io((t - t0) / (t1 - t0))
            return tuple(lerp(p, q, x) for p, q in zip(a, b))
    return ks[-1][1:]

def cam(i, t):
    Dd = D[i]
    if i == 0:
        z, fx, fy = kf(t, [(0, 1.0, 960, 540), (3.0, 1.07, 960, 520), (Dd, 1.02, 960, 520)])
        x = t - LOGO_T
        if x > 0:
            z += 0.16 * (x / 0.08 if x < 0.08 else math.exp(-(x - 0.08) * 4))
        return z, fx, fy
    if i == 1:
        return kf(t, [(0, 1.0, 960, 430, ), (1.6, 1.12, 960, 430), (3.0, 1.55, 1480, 430), (3.5, 1.55, 1480, 450),
                      (4.3, 1.3, 960, 640), (Dd, 1.35, 960, 650)])
    if i == 2:
        return kf(t, [(0, 1.0, 960, 540), (2.0, 1.2, 960, 560), (Dd, 1.42, 900, 660)])
    if i == 3:
        return kf(t, [(0, 1.0, 1000, 540), (1.5, 1.1, 1150, 540), (2.6, 1.35, 1260, 540), (Dd, 1.4, 1260, 560)])
    if i == 4:
        return kf(t, [(0, 1.0, 960, 540), (1.0, 1.1, 1100, 540), (2.4, 1.35, 1200, 520), (2.9, 1.35, 700, 520),
                      (Dd, 1.25, 900, 540)])
    return kf(t, [(0, 1.0, 960, 540), (Dd, 1.18, 960, 600)])

# ---------- scenes ----------
URL0 = ("https://www.example-store.com/collections/summer-sale/products/classic-sneakers"
        "?id=48291&utm_source=newsletter&utm_medium=email&utm_campaign=summer_launch&ref=homepage_banner")
LINES0 = textwrap.wrap(URL0, 54, break_long_words=True, break_on_hyphens=False)

def s0(img, t):
    if t < 3.4:
        n = int(len(URL0) * e_io((t - 0.3) / 1.4)) if t > 0.3 else 0
        card = Image.new("RGBA", (1640, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
        d.rounded_rectangle((0, 0, 1639, 559), 40, fill=(255, 255, 255, 24), outline=(255, 255, 255, 70), width=3)
        fm = F('mono', 42); rem = n; y = 90
        for li, line in enumerate(LINES0):
            shown = line[:max(0, rem)]; rem -= len(line)
            d.text((70, y), shown, font=fm, fill=(200, 215, 255, 255))
            sp = e_out((t - (2.1 + li * 0.15)) / 0.5)
            if sp > 0 and shown == line:
                w = fm.getlength(line)
                d.line((70, y + 30, 70 + w * sp, y + 30), fill=RED + (255,), width=6)
            y += 100
        if t > 1.9:
            d.text((1580, 40), "Too long!", font=F('sb', 36), fill=RED + (int(255 * e_out((t - 1.9) / 0.3)),), anchor="ra")
        shake = math.sin(t * 55) * 7 * (c01((t - 2.1) / 0.2) if t < 2.95 else 0)
        x = (t - 2.95) / 0.4
        sc = 1 - 0.45 * e_in(x) if x > 0 else 1
        a = 1 - e_in(x) if x > 0 else e_out((t - 0.05) / 0.3)
        paste_layer(img, card, 960 + shake, 500, sc, a)
    if t >= LOGO_T:
        x = t - LOGO_T
        paste_layer(img, LOGO, 960, 470, lerp(0.6, 1.0, e_back(x / 0.6)), e_out(x / 0.25))
        ring(img, 960, 470, lerp(150, 900, e_out(x / 0.8)), VIOLET, 0.5 * (1 - c01(x / 0.8)))
        e = e_out((x - 0.5) / 0.5)
        text(img, (960, 720 + (1 - e) * 24), "Short links. Big impact.", F('m', 58), GRAY, a=e, anchor="mm")

URL1 = "https://www.example-store.com/collections/summer-sale/prod\u2026"
CURSOR = [(0, 0), (0, 44), (11, 34), (19, 52), (27, 48), (19, 31), (33, 31)]

def s1(img, t):
    a = e_out((t - 0.1) / 0.5); dy = (1 - a) * 40
    if a > 0:
        panel(img, (210, 355 + dy, 1710, 485 + dy), 65, fa=0.10 * a + 0.0, outline=(255, 255, 255), oa=0.28 * a, ow=3)
        gpill(img, (248, 386 + dy, 316, 454 + dy), 34, a=a)
        text(img, (282, 420 + dy), "://", F('b', 28), a=a, anchor="mm")
        n = int(len(URL1) * e_io((t - 0.5) / 1.1))
        text(img, (345, 420 + dy), URL1[:n], F('mono', 32), (205, 215, 255), a=a, anchor="lm")
        press = c01(1 - abs(t - 3.1) / 0.15) * 0.06
        bx0, by0, bx1, by1 = 1440, 370, 1690, 470
        cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2 + dy
        hw, hh = (bx1 - bx0) / 2 * (1 - press), (by1 - by0) / 2 * (1 - press)
        gpill(img, (cx - hw, cy - hh, cx + hw, cy + hh), 50, a=a)
        text(img, (cx, cy), "Shorten", F('sb', 40), a=a, anchor="mm")
    if t > 3.1:
        x = (t - 3.1) / 0.5
        ring(img, 1565, 420, lerp(20, 140, e_out(x)), CYAN, 0.6 * (1 - c01(x)), width=5)
    if t > 3.25:
        x = e_out((t - 3.25) / 0.5); dy2 = (1 - x) * 50
        panel(img, (400, 590 + dy2, 1520, 800 + dy2), 44, fa=0.10 * x, outline=CYAN, oa=0.6 * x, ow=3)
        text(img, (470, 655 + dy2), "Your short link", F('m', 30), GRAY, a=x, anchor="lm")
        text(img, (470, 735 + dy2), "klip.kazisharif.dev/summer", F('b', 52), a=x, anchor="lm")
        copied = t > 3.9
        col = GREEN if copied else VIOLET
        panel(img, (1330, 690 + dy2, 1480, 760 + dy2), 35, fill=col, fa=0.25 * x, outline=col, oa=0.9 * x, ow=3)
        text(img, (1405, 725 + dy2), "Copied" if copied else "Copy", F('sb', 30), col if copied else (255, 255, 255), a=x, anchor="mm")
    if t > 1.5:
        p = kf(t, [(1.5, 1050, 780), (1.7, 1050, 780), (3.0, 1565, 430), (99, 1565, 430)])
        ca = e_out((t - 1.5) / 0.3)
        px, py = p
        pts = [(px + x, py + y) for x, y in CURSOR]
        sh = 0.0
        if ca > 0.5:
            d = ImageDraw.Draw(img)
            d.polygon(pts, fill=(255, 255, 255), outline=(20, 20, 40))

_rr = random.Random(7)
LINE_PTS = []
for i in range(40):
    LINE_PTS.append(0.18 + 0.62 * (i / 39) ** 1.3 + 0.07 * math.sin(i * 0.9) + _rr.uniform(-0.03, 0.03))
BARS = [0.45, 0.6, 0.5, 0.8, 0.7, 1.0, 0.65]

def s2(img, t):
    a = e_out((t - 0.05) / 0.4)
    panel(img, (280, 190, 1640, 890), 36, fa=0.07 * a, outline=(255, 255, 255), oa=0.2 * a, ow=2)
    text(img, (330, 250), "Link analytics", F('b', 42), a=a, anchor="lm")
    pulse = 0.6 + 0.4 * math.sin(t * 6)
    d = ImageDraw.Draw(img)
    gc = tuple(int(c * pulse) for c in GREEN)
    d.ellipse((1440, 230, 1458, 248), fill=gc)
    text(img, (1472, 239), "LIVE", F('sb', 28), GREEN, a=a, anchor="lm")
    text(img, (332, 330), "Total clicks", F('m', 30), GRAY, a=a, anchor="lm")
    val = int(12480 * e_out((t - 0.7) / 2.4))
    text(img, (330, 425), f"{val:,}", F('b', 128), a=a, anchor="lm")
    text(img, (335, 508), "+24% this week", F('m', 30), GREEN, a=e_out((t - 2.4) / 0.4), anchor="lm")
    # line chart
    cx0, cx1, cy0, cy1 = 340, 1120, 570, 840
    for k in range(4):
        y = cy0 + (cy1 - cy0) * k / 3
        d.line((cx0, y, cx1, y), fill=(52, 58, 100), width=2)
    p = e_out((t - 0.9) / 2.0)
    n = max(2, int(len(LINE_PTS) * p))
    pts = [(cx0 + (cx1 - cx0) * i / 39, cy1 - (cy1 - cy0) * LINE_PTS[i]) for i in range(n)]
    if p > 0.02:
        ov = Image.new("RGBA", (cx1 - cx0 + 20, cy1 - cy0 + 20), (0, 0, 0, 0))
        poly = [(x - cx0 + 10, y - cy0 + 10) for x, y in pts] + [(pts[-1][0] - cx0 + 10, cy1 - cy0 + 10), (10, cy1 - cy0 + 10)]
        ImageDraw.Draw(ov).polygon(poly, fill=CYAN + (55,))
        img.paste(ov, (cx0 - 10, cy0 - 10), ov)
        d.line(pts, fill=CYAN, width=7, joint="curve")
        ex, ey = pts[-1]
        d.ellipse((ex - 11, ey - 11, ex + 11, ey + 11), fill=(255, 255, 255))
        ring(img, ex, ey, 18 + 14 * ((t * 1.5) % 1), CYAN, 0.6 * (1 - (t * 1.5) % 1), width=4)
    # bars
    base = 840
    for k, hgt in enumerate(BARS):
        bp = e_out((t - (1.0 + k * 0.12)) / 0.6)
        bh = 280 * hgt * bp
        x0 = 1230 + k * 52
        if bh > 4:
            gpill(img, (x0, base - bh, x0 + 38, base), 12, CYAN, VIOLET)
        text(img, (x0 + 19, 868), "MTWTFSS"[k], F('m', 24), GRAY, a=a, anchor="mm")

random.seed(3)
_qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
_qr.add_data("https://klip.kazisharif.dev/"); _qr.make(fit=True)
QM = _qr.get_matrix(); NQ = len(QM)
_rq = random.Random(5)
REV = [[(_rq.uniform(1.7, 2.1) if ((r < 7 and c < 7) or (r < 7 and c >= NQ - 7) or (r >= NQ - 7 and c < 7))
         else _rq.uniform(1.9, 3.0)) for c in range(NQ)] for r in range(NQ)]

def s3(img, t):
    cx, cy, cs = 1260, 540, 640
    ca = e_out((t - 1.4) / 0.4)
    ta = e_out((t - 0.4) / 0.5)
    text(img, (180 - (1 - ta) * 60, 400), "Instant", F('b', 120), a=ta, anchor="lm")
    tb = e_out((t - 0.65) / 0.5)
    text(img, (180 - (1 - tb) * 60, 550), "QR codes", F('b', 120), CYAN, a=tb, anchor="lm")
    tc = e_out((t - 1.2) / 0.5)
    text(img, (184, 668), "klip.kazisharif.dev/summer", F('mono', 36), GRAY, a=tc, anchor="lm")
    if ca > 0:
        gpill(img, (cx - cs / 2 - 14, cy - cs / 2 - 14, cx + cs / 2 + 14, cy + cs / 2 + 14), 60, a=ca)
        panel(img, (cx - cs / 2, cy - cs / 2, cx + cs / 2, cy + cs / 2), 48, fill=(255, 255, 255), fa=ca)
        pad = 48; ms = (cs - 2 * pad) / NQ
        ox, oy = cx - cs / 2 + pad, cy - cs / 2 + pad
        d = ImageDraw.Draw(img)
        for r in range(NQ):
            for c in range(NQ):
                if QM[r][c]:
                    s = e_back((t - REV[r][c]) / 0.25)
                    if s > 0.02:
                        mx, my = ox + (c + 0.5) * ms, oy + (r + 0.5) * ms
                        h = ms * s / 2 * 1.02
                        d.rectangle((mx - h, my - h, mx + h, my + h), fill=(15, 18, 40))
        if 3.1 < t < 4.3:
            y = lerp(oy, oy + cs - 2 * pad, e_io((t - 3.1) / 1.0))
            ov = Image.new("RGBA", (cs, cs), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            yl = y - (cy - cs / 2)
            for k in range(36):
                od.line((20, yl - k, cs - 20, yl - k), fill=CYAN + (int(110 * (1 - k / 36)),), width=1)
            od.rectangle((20, yl - 3, cs - 20, yl + 3), fill=CYAN + (255,))
            img.paste(ov, (int(cx - cs / 2), int(cy - cs / 2)), ov)
    if t > 4.1:
        x = e_out((t - 4.1) / 0.4)
        panel(img, (cx - 190, 905 + (1 - x) * 30, cx + 190, 975 + (1 - x) * 30), 35, fill=GREEN, fa=0.25 * x, outline=GREEN, oa=0.9 * x, ow=3)
        text(img, (cx, 940 + (1 - x) * 30), "Scanned!", F('sb', 38), GREEN, a=x, anchor="mm")

DOM1, DOM2, ALIAS = "klip.kazisharif.dev", "go.yourbrand.com", "summer-sale"

def chip(img, cxy, label, col, a):
    f = F('sb', 28); w = int(f.getlength(label)) + 56
    x, y = cxy
    panel(img, (x - w / 2, y - 27, x + w / 2, y + 27), 27, fill=col, fa=0.18 * a, outline=col, oa=0.9 * a, ow=3)
    text(img, (x, y), label, f, col, a=a, anchor="mm")

def s4(img, t):
    a = e_out((t - 0.1) / 0.4)
    panel(img, (190, 430, 1730, 650), 100, fa=0.08 * a, outline=(255, 255, 255), oa=0.25 * a, ow=3)
    f = F('b', 72)
    w1, w2 = f.getlength(DOM1), f.getlength(DOM2); sw = f.getlength("/"); aw = f.getlength(ALIAS)
    q = e_io((t - 2.7) / 0.5)
    dw = lerp(w1, w2, q); x0 = 290; yc = 540
    text(img, (x0, yc - q * 40), DOM1, f, a=(1 - q) * a, anchor="lm")
    text(img, (x0, yc + (1 - q) * 40), DOM2, f, PINK, a=q, anchor="lm")
    text(img, (x0 + dw, yc), "/", f, GRAY, a=a, anchor="lm")
    n = int(len(ALIAS) * c01((t - 1.0) / 1.2))
    text(img, (x0 + dw + sw, yc), ALIAS[:n], f, CYAN, a=a, anchor="lm")
    if t < 3.8 and int(t * 2.5) % 2 == 0 and t > 0.8:
        cxp = x0 + dw + sw + f.getlength(ALIAS[:n]) + 6
        ImageDraw.Draw(img).rectangle((cxp, yc - 36, cxp + 5, yc + 36), fill=(255, 255, 255))
    ca = e_out((t - 1.0) / 0.4)
    if ca > 0:
        chip(img, (x0 + dw + sw + aw / 2, 385 - (1 - ca) * 20), "CUSTOM ALIAS", CYAN, ca)
    da = e_out((t - 2.8) / 0.4)
    if da > 0:
        chip(img, (x0 + dw / 2, 385 - (1 - da) * 20), "YOUR OWN DOMAIN", PINK, da)

def s5(img, t):
    paste_layer(img, LOGO, 960, 330, lerp(0.8, 1.15, e_back(t / 0.8)), e_out(t / 0.4))
    f = F('b', 104)
    words = [("Short", 1.6), ("links.", 1.85), ("Big", 2.3), ("impact.", 2.55)]
    sp = f.getlength(" ")
    total = sum(f.getlength(w) for w, _ in words) + sp * 3
    x = 960 - total / 2
    for k, (wd, tw) in enumerate(words):
        e = e_out((t - tw) / 0.35)
        col = CYAN if k >= 2 else (255, 255, 255)
        text(img, (x, 620 + (1 - e) * 36), wd, f, col, a=e, anchor="lm")
        x += f.getlength(wd) + sp
    if t > 3.6:
        x = t - 3.6; e = e_back(x / 0.5)
        glow = 0.5 + 0.5 * math.sin(x * 4)
        hw, hh = 350 * min(e, 1.05), 70 * min(e, 1.05)
        gpill(img, (960 - hw, 830 - hh, 960 + hw, 830 + hh), 70)
        text(img, (960, 830), "klip.kazisharif.dev", F('sb', 54), a=c01(e), anchor="mm")
        rp = (x * 0.9) % 1
        ring(img, 960, 830, 360 + 120 * rp, CYAN, 0.35 * (1 - rp), width=4)

SC = [s0, s1, s2, s3, s4, s5]

def render_frame(f):
    tt = f / FPS
    i = 0
    for j in range(6):
        if S[j] <= tt + 1e-9:
            i = j
    t = tt - S[i]; Dd = D[i]
    img = BG.copy(); decor(img, tt)
    SC[i](img, t)
    z, fx, fy = cam(i, t)
    m = 1.0
    if i < 5 and t > Dd - 0.4:
        m += 0.7 * e_in((t - (Dd - 0.4)) / 0.4)
    if i > 0 and t < 0.5:
        m += 0.7 * (1 - e_out(t / 0.5))
    z *= m
    cw, ch = W / z, H / z
    x0 = min(max(fx - cw / 2, 0), W - cw); y0 = min(max(fy - ch / 2, 0), H - ch)
    out = img.resize((OW, OH), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
    kin = c01(t / (0.5 if i == 0 else 0.18))
    kout = c01((Dd - t) / (0.9 if i == 5 else 0.12))
    k = min(kin, kout)
    if k < 1:
        out = Image.blend(Image.new("RGB", (OW, OH), (6, 8, 20)), out, k)
    return out.tobytes()

if __name__ == "__main__":
    if sys.argv[1] == "test":
        for ts in [float(x) for x in sys.argv[2:]]:
            Image.frombytes("RGB", (OW, OH), render_frame(int(ts * FPS))).save(os.path.join(BUILD, f"test_{ts}.png"))
        print("total", TOTAL, S)
    else:
        nfr = int(TOTAL * FPS)
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                              "-pix_fmt", "yuv420p", os.path.join(BUILD, "silent.mp4")], stdin=subprocess.PIPE)
        for f in range(nfr):
            p.stdin.write(render_frame(f))
            if f % 60 == 0:
                print("frame", f, "/", nfr, flush=True)
        p.stdin.close(); p.wait(); print("done")
