# -*- coding: utf-8 -*-
"""Modern, világos megjelenés: színek, lekerekített kártyák, gombok, beviteli mezők.

Mindent egyszerű Kivy-grafikai elemekkel (RoundedRectangle/Line) rajzolunk, így nincs
szükség külön képfájlokra a gombokhoz és a mezőkhöz.
"""
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

# ---------------------------------------------------------------- színek
NAVY = (0.106, 0.122, 0.369, 1)
NAVY_DOWN = (0.07, 0.08, 0.27, 1)
ACCENT = (0.184, 0.435, 0.929, 1)
ACCENT_DOWN = (0.12, 0.33, 0.80, 1)
DANGER = (0.84, 0.27, 0.27, 1)
DANGER_DOWN = (0.70, 0.20, 0.20, 1)
TEXT = (0.12, 0.14, 0.25, 1)
MUTED = (0.36, 0.39, 0.52, 1)
WHITE = (1, 1, 1, 1)
SURFACE = (1, 1, 1, 0.94)
FIELD = (1, 1, 1, 1)
LINE = (0.74, 0.79, 0.90, 1)
PRESS = (0.88, 0.91, 0.97, 1)

RADIUS = 12
ROW_H = dp(48)


def _alpha(color, k):
    return (color[0], color[1], color[2], color[3] * k)


def paint(widget, color_fn, radius=RADIUS, line_fn=None, line_w=1.2, watch=()):
    """Lekerekített háttér a widget canvas.before rétegébe; a színt color_fn(widget) adja."""
    r = dp(radius)
    with widget.canvas.before:
        col = Color(*color_fn(widget))
        rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[r])
        if line_fn:
            lcol = Color(*line_fn(widget))
            line = Line(rounded_rectangle=(widget.x, widget.y, widget.width, widget.height, r),
                        width=dp(line_w))

    def upd(*_):
        col.rgba = color_fn(widget)
        rect.pos = widget.pos
        rect.size = widget.size
        if line_fn:
            lcol.rgba = line_fn(widget)
            line.rounded_rectangle = (widget.x, widget.y, widget.width, widget.height, r)

    widget.bind(pos=upd, size=upd)
    for prop in ("state", "focus", "disabled") + tuple(watch):
        if widget.property(prop, quiet=True) is not None:
            widget.bind(**{prop: upd})
    return upd


# ---------------------------------------------------------------- kártya
class Card(BoxLayout):
    """Félig áttetsző fehér kártya enyhe árnyékkal."""

    def __init__(self, bg=SURFACE, radius=16, shadow=True, **kw):
        super().__init__(**kw)
        r = dp(radius)
        with self.canvas.before:
            if shadow:
                Color(0.10, 0.15, 0.35, 0.10)
                sh = RoundedRectangle(pos=(self.x, self.y - dp(2)), size=self.size, radius=[r])
            Color(*bg)
            rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[r])

        def upd(*_):
            rect.pos = self.pos
            rect.size = self.size
            if shadow:
                sh.pos = (self.x, self.y - dp(2))
                sh.size = self.size
        self.bind(pos=upd, size=upd)


# ---------------------------------------------------------------- gombok
_KINDS = {
    # fajta: (normál háttér, lenyomott háttér, szövegszín, keret)
    "primary": (NAVY, NAVY_DOWN, WHITE, None),
    "accent": (ACCENT, ACCENT_DOWN, WHITE, None),
    "danger": (DANGER, DANGER_DOWN, WHITE, None),
    "secondary": ((1, 1, 1, 0.97), PRESS, NAVY, LINE),
}


class Btn(Button):
    def __init__(self, kind="secondary", **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("font_size", sp(15))
        kw.setdefault("bold", True)
        super().__init__(**kw)
        self.kind = kind
        normal, down, txt, border = _KINDS[kind]

        def bg(w):
            c = down if w.state == "down" else normal
            return _alpha(c, 0.45) if w.disabled else c

        def ln(w):
            return _alpha(border, 0.5 if w.disabled else 1) if border else (0, 0, 0, 0)

        paint(self, bg, line_fn=ln)

        def txtcol(*_):
            self.color = _alpha(txt, 0.55) if self.disabled else txt
        self.bind(disabled=txtcol)
        txtcol()


class Tog(ToggleButton):
    """Fül / kapcsoló gomb: kiválasztva sötétkék, egyébként fehér."""

    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("font_size", sp(15))
        kw.setdefault("bold", True)
        super().__init__(**kw)
        paint(self, lambda w: NAVY if w.state == "down" else (1, 1, 1, 0.9),
              line_fn=lambda w: (0, 0, 0, 0) if w.state == "down" else LINE)

        def txtcol(*_):
            self.color = WHITE if self.state == "down" else NAVY
        self.bind(state=txtcol)
        txtcol()


class Swatch(Button):
    """Színválasztó négyzet; a kiválasztottat vastag keret jelöli."""

    def __init__(self, rgba, selected=False, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        super().__init__(**kw)
        self.selected = selected
        paint(self, lambda w: rgba,
              line_fn=lambda w: NAVY if self.selected else (0, 0, 0, 0.18), line_w=3 if selected else 1)
        light = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2] > 0.6
        self.color = (0, 0, 0, 1) if light else WHITE
        self.bold = True
        self.text = "OK" if selected else ""


class Opt(SpinnerOption):
    """Legördülő lista elemei."""

    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("color", TEXT)
        kw.setdefault("font_size", sp(15))
        super().__init__(**kw)
        paint(self, lambda w: PRESS if w.state == "down" else (1, 1, 1, 1), radius=6,
              line_fn=lambda w: LINE, line_w=0.8)


class Drop(Spinner):
    def __init__(self, **kw):
        kw.setdefault("background_normal", "")
        kw.setdefault("background_down", "")
        kw.setdefault("background_color", (0, 0, 0, 0))
        kw.setdefault("color", NAVY)
        kw.setdefault("font_size", sp(15))
        kw.setdefault("bold", True)
        kw.setdefault("option_cls", Opt)
        super().__init__(**kw)
        paint(self, lambda w: PRESS if w.state == "down" else (1, 1, 1, 0.97), line_fn=lambda w: LINE)


# ---------------------------------------------------------------- beviteli mező
class Inp(BoxLayout):
    """Lekerekített beviteli mező. A TextInput a .ti attribútumban van.

    (A TextInput saját canvas.before rétegét nem bántjuk: a lekerekített hátteret ez a
    tároló rajzolja.)
    """

    def __init__(self, text="", hint="", width=None, numeric=False, disabled=False, **kw):
        super().__init__(size_hint_y=None, height=ROW_H, **kw)
        if width:
            self.size_hint_x = None
            self.width = width
        self.ti = TextInput(
            text=str(text), hint_text=hint, multiline=False, write_tab=False,
            background_normal="", background_active="", background_disabled_normal="",
            background_color=(0, 0, 0, 0), foreground_color=TEXT,
            disabled_foreground_color=_alpha(TEXT, 0.5), hint_text_color=_alpha(MUTED, 0.8),
            cursor_color=ACCENT, selection_color=_alpha(ACCENT, 0.3),
            font_size=sp(16), padding=(dp(12), dp(13), dp(12), dp(8)), disabled=disabled)
        if numeric:
            self.ti.input_filter = "int"
        self.add_widget(self.ti)
        self._focus = False
        self._upd = paint(self,
                          lambda w: (0.93, 0.95, 0.98, 1) if disabled else FIELD,
                          line_fn=lambda w: ACCENT if self._focus else LINE,
                          line_w=1.2)

        def on_focus(inst, val):
            self._focus = bool(val)
            self._upd()
        self.ti.bind(focus=on_focus)

    # kényelmi proxy-k a TextInputhoz
    @property
    def text(self):
        return self.ti.text

    @text.setter
    def text(self, v):
        self.ti.text = v
