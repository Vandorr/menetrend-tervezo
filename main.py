# -*- coding: utf-8 -*-
"""Menetrend tervező – Kivy alkalmazás tabletre (Android) és asztali géphez.

Fülek: Járat | Megállók | Menetrend | Jelzések | PDF
"""
import copy
import os
import re
import traceback

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex

from menetrend import model, pdfgen, storage
from style import (ACCENT, MUTED, NAVY, ROW_H, TEXT, WHITE, Btn, Card, Drop, Inp, Swatch, Tog,
                   paint)

Window.softinput_mode = "below_target"      # a billentyűzet ne takarja a mezőt
Window.clearcolor = (0.93, 0.95, 0.99, 1)
HERE = os.path.dirname(os.path.abspath(__file__))
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


# ---------------------------------------------------------------- segédek
def lbl(text, **kw):
    """Balra igazított, sötét szövegű címke."""
    kw.setdefault("color", TEXT)
    kw.setdefault("font_size", sp(15))
    kw.setdefault("halign", "left")
    kw.setdefault("valign", "middle")
    lb = Label(text=text, **kw)
    lb.bind(size=lambda w, s: setattr(w, "text_size", s))
    return lb


def cap(text):
    """Szakaszcím."""
    lb = lbl("[b]%s[/b]" % text, markup=True, color=NAVY, size_hint_y=None, height=dp(34))
    return lb


def note(text):
    lb = Label(text=text, size_hint_y=None, halign="left", valign="top",
               font_size=sp(14), color=MUTED)
    lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
    lb.bind(texture_size=lambda w, s: setattr(w, "height", s[1] + dp(6)))
    return lb


def field(text, on_change, width=None, hint="", numeric=False, disabled=False):
    f = Inp(text=text, hint=hint, width=width, numeric=numeric, disabled=disabled)
    f.ti.bind(text=lambda inst, v: on_change(v))      # a kezdőérték beállítása után
    return f


def button(text, cb, width=None, kind="secondary", **kw):
    b = Btn(kind=kind, text=text, size_hint_y=None, height=ROW_H, **kw)
    if width:
        b.size_hint_x = None
        b.width = width
    b.bind(on_release=lambda *_: cb())
    return b


def hrow(*widgets, height=None):
    r = BoxLayout(size_hint_y=None, height=height or ROW_H, spacing=dp(8))
    for w in widgets:
        r.add_widget(w)
    return r


def vlist():
    g = GridLayout(cols=1, size_hint_y=None, spacing=dp(10), padding=[dp(14), dp(10)])
    g.bind(minimum_height=g.setter("height"))
    return g


def scroll(content):
    sv = ScrollView(do_scroll_x=False, bar_width=dp(6), bar_color=(0.18, 0.43, 0.93, 0.7),
                    bar_inactive_color=(0.18, 0.43, 0.93, 0.25))
    sv.add_widget(content)
    return sv


def check_row(text, value, on_change):
    cb = CheckBox(active=bool(value), size_hint_x=None, width=dp(52), color=NAVY)
    cb.bind(active=lambda inst, v: on_change(bool(v)))
    return hrow(cb, lbl(text, font_size=sp(16)))


def swatches(colors, current, on_pick):
    row = hrow(height=dp(52))
    for hexv in colors:
        b = Swatch(get_color_from_hex(hexv), selected=hexv.lower() == str(current).lower())
        b.bind(on_release=lambda w, hv=hexv: on_pick(hv))
        row.add_widget(b)
    return row


def popup(title, text, buttons=None):
    box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(12))
    box.add_widget(lbl(text, halign="center", font_size=sp(16)))
    p = Popup(title=title, content=box, size_hint=(0.7, 0.5), background="",
              background_color=(1, 1, 1, 1), title_color=NAVY, title_size=sp(18),
              separator_color=ACCENT)
    row = BoxLayout(size_hint_y=None, height=ROW_H, spacing=dp(10))
    buttons = buttons or [("Rendben", None)]
    for i, (label_text, cb) in enumerate(buttons):
        def _do(*_, cb=cb):
            p.dismiss()
            if cb:
                cb()
        b = Btn(kind="primary" if i == len(buttons) - 1 else "secondary", text=label_text)
        b.bind(on_release=_do)
        row.add_widget(b)
    box.add_widget(row)
    p.open()
    return p


def to_int(text, default=0):
    try:
        return int(str(text).strip())
    except ValueError:
        return default


# ---------------------------------------------------------------- járatlista
class ListScreen(Screen):
    def __init__(self, app, **kw):
        super().__init__(name="list", **kw)
        self.app = app
        self.root_box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))
        self.add_widget(self.root_box)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        self.root_box.clear_widgets()
        head = Card(bg=NAVY, size_hint_y=None, height=dp(78), padding=[dp(18), dp(10)], spacing=dp(12))
        titles = BoxLayout(orientation="vertical")
        titles.add_widget(lbl("[b]Menetrend tervező[/b]", markup=True, color=WHITE, font_size=sp(26)))
        titles.add_widget(lbl("Saját menetrendek szerkesztése és PDF-be mentése",
                              color=(0.80, 0.86, 1, 1), font_size=sp(13)))
        head.add_widget(titles)
        head.add_widget(button("+ Új járat", self.app.new_line, width=dp(170), kind="accent"))
        self.root_box.add_widget(head)

        g = vlist()
        lines = model.load_all(self.app.lines_dir)
        if not lines:
            g.add_widget(note("Még nincs járat. A „+ Új járat” gombbal indulhat a tervezés."))
        for d in lines:
            dest = " ".join(s for s in d["destination"] if s)
            card = Card(size_hint_y=None, height=dp(76), padding=dp(10), spacing=dp(10))
            card.add_widget(self._badge(d))
            card.add_widget(button("%s  –  %s" % (model.TYPE_HU.get(d["type"], ""), dest),
                                   lambda d=d: self.app.open_line(d), halign="left"))
            card.add_widget(button("Másolat", lambda d=d: self.app.copy_line(d), width=dp(120)))
            card.add_widget(button("Törlés", lambda d=d: self.confirm_delete(d), width=dp(110),
                                   kind="danger"))
            g.add_widget(card)
        self.root_box.add_widget(scroll(g))

    @staticmethod
    def _badge(d):
        """Színes jelvény a járatszámmal."""
        rgba = get_color_from_hex(d["color"])
        light = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2] > 0.6
        b = Label(text="[b]%s[/b]" % d["number"], markup=True, size_hint_x=None, width=dp(86),
                  font_size=sp(24), color=(0, 0, 0, 1) if light else WHITE)
        paint(b, lambda w: rgba, radius=14)
        return b

    def confirm_delete(self, d):
        popup("Törlés", "Biztosan törli ezt a járatot?\n%s" % d["number"],
              [("Mégse", None), ("Törlés", lambda: (model.delete_line(self.app.lines_dir, d["id"]),
                                                   self.refresh()))])


# ---------------------------------------------------------------- szerkesztő
class EditScreen(Screen):
    TABS = (("basic", "Járat"), ("stops", "Megállók"), ("table", "Menetrend"),
            ("marks", "Jelzések"), ("pdf", "PDF"))

    def __init__(self, app, **kw):
        super().__init__(name="edit", **kw)
        self.app = app
        self.data = None
        self.sel = (0, 0)
        self.last_open = None

        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        head = Card(bg=NAVY, size_hint_y=None, height=dp(64), padding=[dp(10), dp(8)], spacing=dp(10))
        head.add_widget(button("< Vissza", self.back, width=dp(130)))
        self.title_label = lbl("", color=WHITE, font_size=sp(21), bold=True, halign="center")
        head.add_widget(self.title_label)
        head.add_widget(button("Mentés", self.save, width=dp(130), kind="accent"))
        root.add_widget(head)

        self.boxes = {}
        self.tab_buttons = {}
        bar = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        for key, text in self.TABS:
            tb = Tog(text=text, group="edittabs", allow_no_selection=False)
            tb.bind(on_release=lambda w, key=key: self.show_tab(key))
            bar.add_widget(tb)
            self.tab_buttons[key] = tb
            self.boxes[key] = BoxLayout(orientation="vertical")
        root.add_widget(bar)
        self.holder = Card(orientation="vertical", padding=dp(4))
        root.add_widget(self.holder)
        self.add_widget(root)
        self.show_tab("basic")

    def show_tab(self, key):
        self.cur = key
        self.tab_buttons[key].state = "down"
        self.holder.clear_widgets()
        self.holder.add_widget(self.boxes[key])

    # ---- életciklus
    def load(self, data):
        self.data = data
        self.sel = (0, 0)
        self.last_open = None
        self.refresh_all()

    def refresh_all(self):
        self.update_title()
        for key in self.boxes:
            self.refresh(key)

    def refresh(self, key):
        builder = {"basic": self.build_basic, "stops": self.build_stops,
                   "table": self.build_table, "marks": self.build_marks,
                   "pdf": self.build_pdf}[key]
        box = self.boxes[key]
        box.clear_widgets()
        box.add_widget(builder())

    def update_title(self):
        d = self.data
        self.title_label.text = "%s %s" % (model.TYPE_HU.get(d["type"], ""), d["number"])

    def save(self):
        try:
            model.save_line(self.app.lines_dir, self.data)
        except OSError as e:
            popup("Hiba", "Nem sikerült menteni:\n%s" % e)

    def back(self):
        self.save()
        self.app.sm.current = "list"

    def _set(self, key, value, title=False):
        self.data[key] = value
        if title:
            self.update_title()

    # ---- 1. fül: Járat
    def build_basic(self):
        d = self.data
        g = vlist()
        g.add_widget(cap("Jármű típusa"))
        row = hrow()
        for t in model.TYPES:
            b = Tog(text=model.TYPE_HU[t], group="vtype", allow_no_selection=False,
                    state="down" if d["type"] == t else "normal")
            b.bind(on_release=lambda w, t=t: self._set("type", t, True))
            row.add_widget(b)
        g.add_widget(row)
        g.add_widget(cap("Járatszám (pl. 7, 1A, 900A)"))
        g.add_widget(field(d["number"], lambda v: self._set("number", v, True)))
        g.add_widget(cap("Járat színe"))
        g.add_widget(swatches([h for _, h in model.COLORS], d["color"], self._pick_color))
        g.add_widget(field(d["color"], self._hex_color, hint="#RRGGBB"))
        g.add_widget(cap("Irány (végállomás) – 1. sor"))
        g.add_widget(field(d["destination"][0], lambda v: d["destination"].__setitem__(0, v)))
        g.add_widget(cap("Irány (végállomás) – 2. sor (elhagyható)"))
        g.add_widget(field(d["destination"][1], lambda v: d["destination"].__setitem__(1, v)))
        g.add_widget(cap("Érvényesség kezdete (ÉÉÉÉ-HH-NN) és időtartam"))
        end_lb = note("")

        def upd_end(*_):
            s, e = model.validity(d)
            end_lb.text = "Érvényes: %s – %s" % (s.strftime("%Y.%m.%d."), e.strftime("%Y.%m.%d."))
        upd_end()

        def set_from(v):
            d["validFrom"] = v
            upd_end()
        sp_years = Drop(text="%d év" % d["validYears"], values=["1 év", "2 év", "3 év", "4 év", "5 év"],
                        size_hint_x=None, width=dp(120), size_hint_y=None, height=ROW_H)

        def set_years(inst, v):
            d["validYears"] = to_int(v.split()[0], 1)
            upd_end()
        sp_years.bind(text=set_years)
        g.add_widget(hrow(field(d["validFrom"], set_from, hint="2026-11-21"), sp_years))
        g.add_widget(end_lb)
        return scroll(g)

    def _pick_color(self, hexv):
        self.data["color"] = hexv
        self.refresh("basic")

    def _hex_color(self, v):
        if HEX_RE.match(v.strip()):
            self.data["color"] = v.strip()

    # ---- 2. fül: Megállók
    def build_stops(self):
        d = self.data
        g = vlist()
        g.add_widget(note("Megálló neve és a menetidő az első megállótól (perc). "
                          "A hosszú nevek a lapon automatikusan sortörést kapnak. Legfeljebb %d megálló."
                          % model.MAX_STOPS))
        for i, (name, mins) in enumerate(d["stops"]):
            r = hrow()
            r.add_widget(lbl(str(i + 1), size_hint_x=None, width=dp(36), halign="center", color=MUTED))
            r.add_widget(field(name, lambda v, i=i: d["stops"][i].__setitem__(0, v)))
            r.add_widget(field("0" if i == 0 else str(mins),
                               lambda v, i=i: d["stops"][i].__setitem__(1, to_int(v)),
                               width=dp(80), hint="perc", numeric=True, disabled=(i == 0)))
            r.add_widget(button("Fel", lambda i=i: self._stop_move(i, -1), width=dp(64)))
            r.add_widget(button("Le", lambda i=i: self._stop_move(i, 1), width=dp(64)))
            r.add_widget(button("Töröl", lambda i=i: self._stop_del(i), width=dp(90), kind="danger"))
            g.add_widget(r)
        if len(d["stops"]) < model.MAX_STOPS:
            g.add_widget(button("+ Megálló hozzáadása", self._stop_add, kind="primary"))
        return scroll(g)

    def _stop_move(self, i, delta):
        s = self.data["stops"]
        j = i + delta
        if 0 <= j < len(s):
            s[i], s[j] = s[j], s[i]
            self.refresh("stops")

    def _stop_del(self, i):
        if len(self.data["stops"]) > 2:
            del self.data["stops"][i]
            self.refresh("stops")

    def _stop_add(self):
        s = self.data["stops"]
        if len(s) >= model.MAX_STOPS:
            return
        s.append(["Új megálló", (s[-1][1] + 2) if s else 0])
        self.refresh("stops")

    # ---- 3. fül: Menetrend
    def _block(self):
        secs = self.data["sections"]
        si = min(self.sel[0], len(secs) - 1)
        bi = min(self.sel[1], len(secs[si]) - 1)
        self.sel = (si, bi)
        return secs[si][bi]

    def _block_names(self):
        names = []
        for si, sec in enumerate(self.data["sections"]):
            for bi, b in enumerate(sec):
                names.append((si, bi, "%d. sor, %d. oszlop – %s" % (si + 1, bi + 1, b["title"])))
        return names

    def build_table(self):
        d = self.data
        b = self._block()
        g = vlist()
        names = self._block_names()
        cur = [n for si, bi, n in names if (si, bi) == self.sel][0]
        sp_sel = Drop(text=cur, values=[n for _, _, n in names], size_hint_y=None, height=ROW_H)

        def pick(inst, text):
            for si, bi, n in names:
                if n == text:
                    self.sel = (si, bi)
            self.refresh("table")
        sp_sel.bind(text=pick)
        g.add_widget(cap("Szerkesztett blokk"))
        g.add_widget(sp_sel)

        si, bi = self.sel
        ops = []
        if len(d["sections"][si]) < model.MAX_COLS:
            ops.append(button("+ Oszlop ebbe a sorba", self._add_col))
        if len(d["sections"]) < model.MAX_SECTIONS:
            ops.append(button("+ Új sor (alsó szakasz)", self._add_section))
        if sum(len(s) for s in d["sections"]) > 1:
            ops.append(button("Blokk törlése", self._del_block))
        if ops:
            g.add_widget(hrow(*ops))
        g.add_widget(note("Elrendezés: legfeljebb %d sor (szakasz), soronként legfeljebb %d oszlop (blokk)."
                          % (model.MAX_SECTIONS, model.MAX_COLS)))

        g.add_widget(cap("Blokk címe és angol alcíme"))
        presets = Drop(text="Minta kiválasztása…", values=[p[0] for p in model.BLOCK_PRESETS],
                       size_hint_y=None, height=ROW_H)

        def apply_preset(inst, text):
            for t, s, a in model.BLOCK_PRESETS:
                if t == text:
                    b["title"], b["sub"], b["accent"] = t, s, a
            self.refresh("table")
        presets.bind(text=apply_preset)
        g.add_widget(presets)
        g.add_widget(field(b["title"], lambda v: b.__setitem__("title", v)))
        g.add_widget(field(b["sub"], lambda v: b.__setitem__("sub", v)))
        g.add_widget(cap("Blokk színe"))
        g.add_widget(swatches(model.ACCENTS, b["accent"], self._pick_accent))

        # gyors kitöltés
        g.add_widget(cap("Gyors kitöltés: óra-tól, óra-ig, első perc, gyakoriság (perc)"))
        vals = ["5", "22", "0", "10"]
        fields = []
        row = hrow()
        for k, v in enumerate(vals):
            f = Inp(text=v, numeric=True)
            fields.append(f)
            row.add_widget(f)

        def fill():
            h0, h1, m0, step = [to_int(f.ti.text) for f in fields]
            self._quick_fill(b, h0, h1, m0, step)
        row.add_widget(button("Kitöltés", fill, width=dp(130), kind="accent"))
        g.add_widget(row)

        # másolás másik blokkból
        others = [n for s2, b2, n in names if (s2, b2) != self.sel]
        if others:
            cp = Drop(text="Sorok másolása másik blokkból…", values=others,
                      size_hint_y=None, height=ROW_H)

            def do_copy(inst, text):
                for s2, b2, n in names:
                    if n == text:
                        b["rows"] = copy.deepcopy(d["sections"][s2][b2]["rows"])
                self.refresh("table")
            cp.bind(text=do_copy)
            g.add_widget(cp)

        g.add_widget(cap("Indulások óránként (percek vesszővel, vagy pl. 2-4 perc / min)"))
        for h in model.HOURS:
            g.add_widget(hrow(
                lbl("%02d:" % h, size_hint_x=None, width=dp(52), font_size=sp(16), bold=True, color=NAVY),
                field(b["rows"].get(str(h), ""),
                      lambda v, h=h: b["rows"].__setitem__(str(h), v),
                      hint="pl. 05, 15, 25, 35, 45, 55")))
        return scroll(g)

    def _quick_fill(self, b, h0, h1, m0, step):
        if step < 1 or not (0 <= m0 < 60):
            popup("Gyors kitöltés", "A gyakoriság legalább 1 perc, az első perc 0–59 legyen.")
            return
        h0 = max(model.HOURS[0], h0)
        h1 = min(model.HOURS[-1], h1)
        buckets = {}
        t = h0 * 60 + m0
        while t < (h1 + 1) * 60:
            buckets.setdefault(t // 60, []).append("%02d" % (t % 60))
            t += step
        for h in range(h0, h1 + 1):
            b["rows"][str(h)] = ", ".join(buckets.get(h, []))
        self.refresh("table")

    def _pick_accent(self, hexv):
        self._block()["accent"] = hexv
        self.refresh("table")

    def _add_col(self):
        si = self.sel[0]
        if len(self.data["sections"][si]) >= model.MAX_COLS:
            return
        self.data["sections"][si].append(model.new_block("Új blokk", "", "#999999"))
        self.sel = (si, len(self.data["sections"][si]) - 1)
        self.refresh("table")

    def _add_section(self):
        if len(self.data["sections"]) >= model.MAX_SECTIONS:
            return
        self.data["sections"].append([model.new_block("Új blokk", "", "#999999")])
        self.sel = (len(self.data["sections"]) - 1, 0)
        self.refresh("table")

    def _del_block(self):
        si, bi = self.sel
        secs = self.data["sections"]
        if sum(len(x) for x in secs) <= 1:
            return
        del secs[si][bi]
        if not secs[si]:
            del secs[si]
        self.sel = (0, 0)
        self.refresh("table")

    # ---- 4. fül: Jelzések
    def build_marks(self):
        d = self.data
        g = vlist()
        g.add_widget(cap("Piktogramok a lap alján"))
        g.add_widget(check_row("Kerékpár szállítható", d["legend"]["bike"],
                               lambda v: d["legend"].__setitem__("bike", v)))
        g.add_widget(check_row("Akadálymentes jármű / megállók", d["legend"]["access"],
                               lambda v: d["legend"].__setitem__("access", v)))

        g.add_widget(cap("Első ajtós felszállás"))
        g.add_widget(check_row("Megjelenjen az „Felszállás az első ajtón” sáv", d["door"]["enabled"],
                               lambda v: d["door"].__setitem__("enabled", v)))
        g.add_widget(field(d["door"]["except_hu"], lambda v: d["door"].__setitem__("except_hu", v),
                           hint="Kivétel, magyarul (elhagyható), pl. Kivéve munkanapokon 20:00 előtt"))
        g.add_widget(field(d["door"]["except_en"], lambda v: d["door"].__setitem__("except_en", v),
                           hint="Kivétel, angolul (elhagyható)"))

        g.add_widget(cap("Bal alsó infóblokk"))
        g.add_widget(check_row("Megjelenjen az infóblokk", d["info"]["enabled"],
                               lambda v: d["info"].__setitem__("enabled", v)))
        for key, hint in (("name", "Név"), ("web", "Weboldal"), ("phone", "Telefon"),
                          ("tagline", "Alsó sor")):
            g.add_widget(field(d["info"][key], lambda v, key=key: d["info"].__setitem__(key, v), hint=hint))

        g.add_widget(cap("Lábjegyzetek (az időpontok után írt betűjelekhez, pl. 46a)"))
        for i, fn in enumerate(d["footnotes"]):
            while len(fn) < 3:
                fn.append("")
            g.add_widget(hrow(
                field(fn[0], lambda v, fn=fn: fn.__setitem__(0, v), width=dp(70), hint="jel"),
                field(fn[1], lambda v, fn=fn: fn.__setitem__(1, v), hint="Magyarul"),
                field(fn[2], lambda v, fn=fn: fn.__setitem__(2, v), hint="Angolul"),
                button("Töröl", lambda i=i: self._fn_del(i), width=dp(90), kind="danger")))
        if len(d["footnotes"]) < model.MAX_FOOTNOTES:
            g.add_widget(button("+ Lábjegyzet", self._fn_add, kind="primary"))
        return scroll(g)

    def _fn_add(self):
        if len(self.data["footnotes"]) >= model.MAX_FOOTNOTES:
            return
        used = {f[0] for f in self.data["footnotes"]}
        key = next((c for c in "abcdef" if c not in used), "x")
        self.data["footnotes"].append([key, "", ""])
        self.refresh("marks")

    def _fn_del(self, i):
        del self.data["footnotes"][i]
        self.refresh("marks")

    # ---- 5. fül: PDF
    def build_pdf(self):
        g = vlist()
        g.add_widget(note("A PDF A4 álló lapra készül, vektoros (élesen nyomtatható). "
                          "Androidon a Letöltések mappába kerül, onnan megnyitható és nyomtatható."))
        self.status = note("")
        g.add_widget(button("PDF generálása", self.make_pdf, kind="accent", font_size=sp(18)))
        g.add_widget(self.status)
        self.open_btn = button("Megnyitás", self.open_pdf, kind="primary")
        self.open_btn.disabled = self.last_open is None
        g.add_widget(self.open_btn)
        return scroll(g)

    def make_pdf(self):
        self.save()
        name = "menetrend_%s.pdf" % re.sub(r"[^0-9A-Za-z_-]+", "", self.data["number"] or "x")
        tmp = os.path.join(self.app.user_data_dir, "tmp_%s" % name)
        try:
            pdfgen.render(self.data, tmp)
            text, opener = storage.save_pdf(tmp, name)
        except Exception as e:                          # a felhasználó lássa a hibát
            traceback.print_exc()
            popup("Hiba a PDF készítésekor", "%s: %s" % (type(e).__name__, e))
            return
        self.last_open = opener
        self.status.text = text
        self.open_btn.disabled = opener is None

    def open_pdf(self):
        if self.last_open:
            try:
                self.last_open()
            except Exception as e:
                popup("Hiba", "A PDF nem nyitható meg: %s" % e)


# ---------------------------------------------------------------- alkalmazás
class MenetrendApp(App):
    title = "Menetrend tervező"

    def build(self):
        self.lines_dir = os.path.join(self.user_data_dir, "lines")
        os.makedirs(self.lines_dir, exist_ok=True)
        self.sm = ScreenManager()
        self.list_screen = ListScreen(self)
        self.edit_screen = EditScreen(self)
        self.sm.add_widget(self.list_screen)
        self.sm.add_widget(self.edit_screen)
        Window.bind(on_keyboard=self.on_key)
        root = FloatLayout()
        root.add_widget(Image(source=os.path.join(HERE, "assets", "bg.png"), fit_mode="cover"))
        root.add_widget(self.sm)
        return root

    def on_key(self, window, key, *args):
        if key == 27 and self.sm.current == "edit":      # Android vissza gomb
            self.edit_screen.back()
            return True
        return False

    def on_pause(self):
        if self.sm.current == "edit" and self.edit_screen.data:
            self.edit_screen.save()
        return True

    def new_line(self):
        d = model.new_line()
        model.save_line(self.lines_dir, d)
        self.open_line(d)

    def open_line(self, d):
        self.edit_screen.load(model.normalize(d))
        self.sm.current = "edit"

    def copy_line(self, d):
        c = copy.deepcopy(d)
        c["id"] = model.new_line()["id"]
        c["number"] = d["number"] + " (másolat)"
        model.save_line(self.lines_dir, c)
        self.list_screen.refresh()


if __name__ == "__main__":
    MenetrendApp().run()
