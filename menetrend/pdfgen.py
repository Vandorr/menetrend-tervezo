# -*- coding: utf-8 -*-
"""A4 álló menetrendlap rajzolása reportlabbal (vektoros, nyomtatásra)."""
import os

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from . import model

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

W, H = 595.92, 842.88
M = 14            # külső margó
BAR_W = 160       # bal oldali vonalsáv szélessége
GAP = 10
NAVY = HexColor("#1B1F5E")
DOOR_YELLOW = HexColor("#FFD800")

_fonts_ready = False


def _fonts():
    global _fonts_ready
    if _fonts_ready:
        return
    d = os.path.join(ASSETS, "fonts")
    for name, fn in (("MT-R", "Regular"), ("MT-B", "Bold"),
                     ("MT-I", "Italic"), ("MT-BI", "BoldItalic")):
        pdfmetrics.registerFont(TTFont(name, os.path.join(d, "LiberationSansNarrow-%s.ttf" % fn)))
    _fonts_ready = True


def _img(name):
    return ImageReader(os.path.join(ASSETS, name))


def _is_light(hexcol):
    c = HexColor(hexcol)
    return 0.299 * c.red + 0.587 * c.green + 0.114 * c.blue > 0.6


def _tint(hexcol, a):
    c = HexColor(hexcol)
    return (1 - a + c.red * a, 1 - a + c.green * a, 1 - a + c.blue * a)


def _fit(text, font, size, maxw, minsize=5.0):
    """Betűméret csökkentése, amíg a szöveg belefér maxw-be."""
    while size > minsize and pdfmetrics.stringWidth(text, font, size) > maxw:
        size -= 0.2
    return size


def render(data, out_path):
    _fonts()
    d = model.normalize(data)
    c = canvas.Canvas(out_path, pagesize=(W, H))
    c.setTitle("%s %s" % (model.TYPE_HU.get(d["type"], ""), d["number"]))
    col = HexColor(d["color"])
    dark_ink = _is_light(d["color"])
    ink = black if dark_ink else white
    top = H - M
    hh = 60

    # ---------- fejléc ----------
    dia = 52
    c.setFillColor(col)
    c.circle(M + dia / 2 + 2, top - hh / 2, dia / 2, fill=1, stroke=0)
    icon = "%s_%s.png" % (d["type"], "k" if dark_ink else "w")
    c.drawImage(_img(icon), M + 2, top - hh / 2 - dia / 2, dia, dia, mask="auto")
    c.setFillColor(col)
    c.roundRect(M + 64, top - hh + 6, 84, hh - 12, 7, fill=1, stroke=0)
    c.setFillColor(ink)
    num = d["number"] or "?"
    fs = _fit(num, "MT-B", 36, 74, 14)
    c.setFont("MT-B", fs)
    c.drawCentredString(M + 106, top - hh / 2 - fs * 0.35, num)
    c.setFillColor(black)
    p = c.beginPath()
    ax, ay = M + BAR_W + 18, top - 30
    p.moveTo(ax, ay - 8); p.lineTo(ax, ay + 10); p.lineTo(ax + 14, ay + 1); p.close()
    c.drawPath(p, fill=1, stroke=0)
    tx = M + BAR_W + 42
    for i, line in enumerate([s for s in d["destination"] if s.strip()]):
        fs = _fit(line, "MT-B", 24, W - M - tx)
        c.setFont("MT-B", fs)
        c.drawString(tx, top - 28 - i * 26, line)

    # ---------- bal oldali vonalsáv ----------
    stops = d["stops"]
    n = len(stops)
    y_first = top - hh - 9
    bottom = 100
    step = min(40, (y_first - 20 - bottom) / max(1, n - 1))
    lx = M + 34
    c.setStrokeColor(col)
    c.setLineWidth(4)
    if n > 1:
        c.line(lx, y_first, lx, y_first - (n - 1) * step)
    c.setFillColor(NAVY)
    c.rect(M, y_first - 11, BAR_W - 4, 22, fill=1, stroke=0)
    name_w = M + BAR_W - 6 - (lx + 14)
    for i, (name, mins) in enumerate(stops):
        y = y_first - i * step
        c.setFillColor(white)
        c.setStrokeColor(col)
        c.setLineWidth(2.2)
        c.circle(lx, y, 4.5, fill=1, stroke=1)
        bold = i == 0 or i == n - 1
        font = "MT-B" if bold else "MT-R"
        if i == 0:
            c.setFillColor(white)
            c.setFont(font, _fit(name, font, 8.8, name_w))
            c.drawString(lx + 14, y - 3, name)
            continue
        c.setFillColor(black)
        c.setFont("MT-B" if bold else "MT-R", 7.8)
        c.drawRightString(lx - 9, y - 2.7, "%s'" % mins)
        max_lines = 3 if step >= 28 else (2 if step >= 18 else 1)
        lines = simpleSplit(name, font, 8.4, name_w)[:max_lines] or [""]
        c.setFont(font, 8.4)
        y_text = y - 3 + (len(lines) - 1) * 4.5
        for k, ln in enumerate(lines):
            c.drawString(lx + 14, y_text - k * 9, ln)

    # ---------- menetrendi blokkok ----------
    x0 = M + BAR_W + GAP
    xw = W - M - x0
    y = top - hh - 12
    row_h = 10.6 if len(d["sections"]) > 1 else 12.2
    for sec in d["sections"]:
        k = len(sec)
        bw = (xw - (k - 1) * 6) / k
        for j, b in enumerate(sec):
            bx = x0 + j * (bw + 6)
            c.setFillColor(black)
            c.setFont("MT-B", _fit(b["title"], "MT-B", 8, bw))
            c.drawString(bx, y - 8, b["title"])
            c.setFont("MT-I", _fit(b["sub"], "MT-I", 7, bw))
            c.drawString(bx, y - 16, b["sub"])
            c.setStrokeColor(HexColor(b["accent"]))
            c.setLineWidth(2)
            c.line(bx, y - 21, bx + bw, y - 21)
        ry = y - 22
        for h in model.HOURS:
            for j, b in enumerate(sec):
                bx = x0 + j * (bw + 6)
                if h % 2 == 1:
                    c.setFillColor(_tint(b["accent"], 0.28))
                    c.rect(bx, ry - row_h, bw, row_h, fill=1, stroke=0)
                txt = b["rows"].get(str(h), "").strip()
                c.setFillColor(black)
                c.setFont("MT-B", 7.6)
                c.drawString(bx + 1.5, ry - row_h + (row_h - 7.6) / 2 + 1.2, "%02d:" % h)
                if txt:
                    font = "MT-I" if "perc" in txt else "MT-R"
                    c.setFont(font, _fit(txt, font, 7.6, bw - 19))
                    c.drawString(bx + 17, ry - row_h + (row_h - 7.6) / 2 + 1.2, txt)
            ry -= row_h
        y = ry - 10

    # ---------- jelmagyarázat (alulról felfelé) ----------
    lx0 = x0 + 8
    iy = 84

    def legend_row(icon_name, hu, en, yy):
        c.drawImage(_img(icon_name), lx0, yy - 8, 24, 24, mask="auto")
        c.setFillColor(black)
        c.setFont("MT-B", 8)
        c.drawString(lx0 + 32, yy + 8, hu)
        c.setFont("MT-I", 7.5)
        c.drawString(lx0 + 32, yy - 1, en)

    if d["legend"].get("access"):
        legend_row("access.png",
                   "Akadálymentes jármű is közlekedik, és a megjelölt megállók akadálymentesek.",
                   "Some vehicles and the indicated stops are accessible.", iy)
        iy += 32
    if d["legend"].get("bike"):
        legend_row("bike.png",
                   "A piktogrammal megjelölt járműveken egy darab kerékpár szállítható.",
                   "Vehicles marked with this pictogram can take one bike on board.", iy)
        iy += 32
    notes = [f for f in d["footnotes"] if (f[0] or f[1])][:model.MAX_FOOTNOTES]
    if notes:
        top_fn = iy + (len(notes) - 1) * 28
        c.drawImage(_img("info.png"), lx0, top_fn - 8, 24, 24, mask="auto")
        for k, (key, hu, en) in enumerate(notes):
            yb = top_fn + 8 - k * 28
            c.setFillColor(black)
            c.setFont("MT-B", 8)
            c.drawString(lx0 + 32, yb, "%s: %s" % (key, hu))
            c.setFont("MT-I", 7.5)
            c.drawString(lx0 + 44, yb - 9, en)

    # ---------- első ajtós sáv ----------
    bx, bw, by, bh = x0, W - M - x0, 46, 24
    door = d["door"]
    if door.get("enabled"):
        c.setFillColor(DOOR_YELLOW)
        c.rect(bx, by, bw, bh, fill=1, stroke=0)
        c.drawImage(_img("door.png"), bx + 2, by + 1, 62, 22, mask="auto")
        c.setFillColor(black)
        has_sub = bool(door.get("except_hu", "").strip())
        ty = by + (12.5 if has_sub else 8)
        t1 = "Felszállás az első ajtón / "
        c.setFont("MT-B", 12.5)
        c.drawString(bx + 70, ty, t1)
        c.setFont("MT-I", 12.5)
        c.drawString(bx + 70 + pdfmetrics.stringWidth(t1, "MT-B", 12.5), ty, "Front-door boarding only")
        if has_sub:
            t2 = door["except_hu"].strip() + " / "
            c.setFont("MT-B", 7.5)
            c.drawString(bx + 70, by + 3, t2)
            c.setFont("MT-I", 7.5)
            c.drawString(bx + 70 + pdfmetrics.stringWidth(t2, "MT-B", 7.5), by + 3,
                         door.get("except_en", ""))

    # ---------- érvényesség ----------
    vf, vt = model.validity(d)
    fmt = lambda x: x.strftime("%Y.%m.%d.")
    lab = "Érvényesség / Valid (y/m/d): "
    c.setFillColor(black)
    c.setFont("MT-R", 7.5)
    c.drawString(bx, 36, lab)
    c.drawString(bx + pdfmetrics.stringWidth(lab, "MT-R", 7.5), 36, "%s – %s" % (fmt(vf), fmt(vt)))
    c.drawString(bx, 26, "Az adatok tájékoztató jellegűek. / Data provided for informational purposes only.")

    # ---------- bal alsó infóblokk ----------
    ib = d["info"]
    if ib.get("enabled"):
        ix, iw, iyb, ih = M, BAR_W - 4, 20, 50
        c.setFillColor(col)
        c.rect(ix, iyb, iw, ih, fill=1, stroke=0)
        c.setFillColor(ink)
        yy = iyb + ih - 15
        if ib.get("name"):
            c.setFont("MT-B", _fit(ib["name"], "MT-B", 11, iw - 16))
            c.drawString(ix + 8, yy, ib["name"])
            yy -= 12
        for key in ("web", "phone", "tagline"):
            if ib.get(key):
                c.setFont("MT-R", _fit(ib[key], "MT-R", 8, iw - 16))
                c.drawString(ix + 8, yy, ib[key])
                yy -= 10
    c.save()
    return out_path
