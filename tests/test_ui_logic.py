# -*- coding: utf-8 -*-
"""Fejetlen füstteszt: kamu Kivy-modulokkal lefuttatja a felület felépítését és a
szerkesztő műveleteit. Valódi Kivy-viselkedést NEM ellenőriz."""
import os, sys, tempfile, types
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

class _Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name):
        if name.startswith("__"): raise AttributeError(name)
        return lambda *a, **k: None

class Canvas(_Ctx):
    before = _Ctx()

class W:
    def __init__(self, *a, **kw):
        self.children = []
        self.canvas = Canvas()
        self.pos = (0, 0); self.size = (0, 0); self.x = self.y = self.width = self.height = 0
        self.__dict__.update(kw)
    def __getattr__(self, name):           # setter, bind, open, dismiss ... mind no-op
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None
    def add_widget(self, w, *a, **k): self.children.append(w)
    def clear_widgets(self): self.children = []
    def bind(self, **kw): self._bound = kw

class AppBase(W):
    user_data_dir = tempfile.mkdtemp()
    def run(self): pass

def mod(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m

names = {
 "kivy.uix.boxlayout": ["BoxLayout"], "kivy.uix.button": ["Button"], "kivy.uix.checkbox": ["CheckBox"],
 "kivy.uix.gridlayout": ["GridLayout"], "kivy.uix.label": ["Label"], "kivy.uix.popup": ["Popup"],
 "kivy.uix.screenmanager": ["Screen", "ScreenManager"], "kivy.uix.scrollview": ["ScrollView"],
 "kivy.uix.spinner": ["Spinner"], "kivy.uix.tabbedpanel": ["TabbedPanel", "TabbedPanelHeader"],
 "kivy.uix.textinput": ["TextInput"], "kivy.uix.togglebutton": ["ToggleButton"],
 "kivy.uix.floatlayout": ["FloatLayout"], "kivy.uix.image": ["Image"],
 "kivy.graphics": ["Color", "Line", "RoundedRectangle"]}
mod("kivy"); mod("kivy.uix")
for m, cls in names.items():
    mod(m, **{c: type(c, (W,), {}) for c in cls})
class Screen(W):
    def __init__(self, name="", **kw): super().__init__(**kw); self.name = name
sys.modules["kivy.uix.screenmanager"].Screen = Screen
sys.modules["kivy.uix.spinner"].SpinnerOption = type("SpinnerOption", (W,), {})
mod("kivy.app", App=AppBase)
mod("kivy.core"); mod("kivy.core.window", Window=W())
mod("kivy.metrics", dp=lambda x: x, sp=lambda x: x)
mod("kivy.utils", get_color_from_hex=lambda h: (0, 0, 0, 1))

os.environ["HOME"] = tempfile.mkdtemp()
import main
from menetrend import model

app = main.MenetrendApp()
app.build()
app.list_screen.refresh()
app.new_line()                           # új járat -> szerkesztő
e = app.edit_screen
d = e.data
e.refresh_all()
for _ in range(3): e._stop_add()
e._stop_move(1, 1); e._stop_del(0)
assert len(d["stops"]) == 5, d["stops"]
e._add_col(); e._add_col(); e._add_col()       # a 3. oszlopnál már nincs több
e._add_section(); e._add_section()
print("szakaszok:", [len(s) for s in d["sections"]])
assert len(d["sections"]) == model.MAX_SECTIONS
assert all(len(s) <= model.MAX_COLS for s in d["sections"])
b = e._block()
e._quick_fill(b, 5, 22, 0, 10)
assert b["rows"]["5"] == "00, 10, 20, 30, 40, 50", b["rows"]["5"]
e._quick_fill(b, 6, 8, 7, 8)               # átcsorduló lépés
print("6h:", b["rows"]["6"], "| 7h:", b["rows"]["7"])
e._fn_add(); e._fn_add()
e._del_block()
e.refresh_all()
d["door"]["enabled"] = True; d["legend"]["bike"] = True
e.show_tab("table"); e.show_tab("preview"); e.show_tab("pdf")
assert e.pv_png and os.path.getsize(e.pv_png) > 5000, e.pv_status.text
assert e.pv_status.text == "", e.pv_status.text
e._pv_step(0.25); e._pv_fit_page(); e._pv_fit_width()
e.show_tab("preview")                                  # második frissítés, régi PNG törlődik
print("előnézet:", os.path.basename(e.pv_png), round(e.pv_ratio, 3))
e.make_pdf()
out = [f for f in os.listdir(os.path.join(os.environ["HOME"], "Downloads"))] if os.path.isdir(os.path.join(os.environ["HOME"], "Downloads")) else os.listdir(os.getcwd())
print("kimenet:", [f for f in out if f.endswith(".pdf")])
assert e.status.text.startswith("Mentve"), e.status.text
app.copy_line(d); app.list_screen.refresh()
assert len(model.load_all(app.lines_dir)) == 2
print("UI-logika füstteszt OK")
