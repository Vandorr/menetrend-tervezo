# -*- coding: utf-8 -*-
"""Adatmodell: egy járat = egy egyszerű dict (JSON-ba menthető)."""
import copy
import datetime
import json
import os
import uuid

TYPES = ["villamos", "busz", "trolibusz", "ejszakai"]
TYPE_HU = {"villamos": "Villamos", "busz": "Busz", "trolibusz": "Trolibusz",
           "ejszakai": "Éjszakai"}
# az éjszakai járat busz-piktogramot kap, és a menetrendje lista-szerű
TYPE_ICON = {"villamos": "villamos", "busz": "busz", "trolibusz": "trolibusz", "ejszakai": "busz"}

# lábjegyzet-ikonok (kulcs, megnevezés)
FOOTNOTE_ICONS = [("info", "Info"), ("access", "Akadálymentes"), ("none", "Nincs ikon")]

COLORS = [("Fekete", "#000000"), ("Sárga", "#FFD800"), ("Kék", "#009FE3"), ("Piros", "#E41F18"),
          ("Zöld", "#4CA82F"), ("Narancs", "#F28C00"), ("Lila", "#7A3E9D"),
          ("Sötétkék", "#1B1F5E"), ("Szürke", "#707070")]

# (cím, angol alcím, szín)
BLOCK_PRESETS = [
    ("Hétköznap", "Weekdays", "#999999"),
    ("Hétfőtől péntekig", "Mondays to Fridays", "#999999"),
    ("Hétfőtől csütörtökig", "Mondays to Thursdays", "#999999"),
    ("Péntek", "Fridays", "#999999"),
    ("Szombaton", "Saturdays", "#7DBA3A"),
    ("Munkaszüneti napokon", "Sundays and public holidays", "#E0545B"),
    ("Vasárnap", "Sundays", "#E0545B"),
    ("Tanítási szünetben munkanapokon", "Workdays during school holidays", "#3B9AD9"),
    ("Nyári szünetben", "Summer holidays", "#3B9AD9"),
]
ACCENTS = ["#999999", "#3B9AD9", "#7DBA3A", "#E0545B", "#F2B400", "#9B59B6"]

HOURS = list(range(0, 25))                # 0–24 óra is kitölthető
DEFAULT_HOURS = list(range(4, 24))          # ennyi sor jelenik meg, ha nincs kitöltve más
MAX_SECTIONS = 2
MAX_COLS = 3
MAX_STOPS = 30
MAX_FOOTNOTES = 4


def new_block(title="Hétköznap", sub="Weekdays", accent="#999999"):
    return {"title": title, "sub": sub, "accent": accent, "rows": {}}


def new_line():
    today = datetime.date.today().isoformat()
    return {
        "id": uuid.uuid4().hex[:10],
        "number": "1",
        "type": "villamos",
        "color": "#E41F18",
        "destination": ["Végállomás", ""],
        "stops": [["Kiinduló megálló", 0], ["Második megálló", 3], ["Végállomás", 8]],
        "sections": [[new_block()]],
        "footnotes": [],
        "legend": {"bike": False, "access": False},
        "door": {"enabled": False, "except_hu": "", "except_en": ""},
        "info": {"enabled": True, "name": "SAJÁT KÖZLEKEDÉS", "web": "",
                 "phone": "", "tagline": ""},
        "validFrom": today,
        "validYears": 1,
    }


def normalize(d):
    """Hiányzó mezők pótlása (régi / kézzel szerkesztett fájlokhoz)."""
    base = new_line()
    out = copy.deepcopy(base)
    out.update({k: v for k, v in d.items() if k in base})
    for k in ("legend", "door", "info"):
        if isinstance(d.get(k), dict):
            out[k] = dict(base[k], **d[k])
    if isinstance(d.get("legend"), list):               # régi séma
        out["legend"] = {"bike": "bike" in d["legend"], "access": "access" in d["legend"]}
    out["destination"] = (list(out["destination"]) + ["", ""])[:2]
    out["sections"] = [s for s in out["sections"] if s] or [[new_block()]]
    for sec in out["sections"]:
        for b in sec:
            b.setdefault("rows", {})
            b["rows"] = {str(k): str(v) for k, v in b["rows"].items()}
    if not out["stops"]:
        out["stops"] = base["stops"]
    out["stops"] = [(list(x) + ["", 0, ""][len(x):])[:3] if len(x) < 3 else list(x)[:3]
                    for x in out["stops"]]
    out["footnotes"] = [(list(f) + ["", "", "", "info"][len(f):])[:4] for f in out["footnotes"]]
    for f in out["footnotes"]:
        if f[3] not in dict(FOOTNOTE_ICONS):
            f[3] = "info"
    if d.get("type") not in TYPES:
        out["type"] = "busz"
    return out


def parse_date(text):
    try:
        return datetime.date.fromisoformat(str(text).strip())
    except ValueError:
        return None


def validity(d):
    """(kezdő, záró) dátum; a záró a kezdő + validYears év."""
    start = parse_date(d.get("validFrom")) or datetime.date.today()
    years = max(1, int(d.get("validYears") or 1))
    try:
        end = start.replace(year=start.year + years)
    except ValueError:                                   # feb. 29.
        end = start.replace(year=start.year + years, day=28)
    return start, end


# ---------- tárolás ----------
def _path(base, line_id):
    return os.path.join(base, "%s.json" % line_id)


def save_line(base, d):
    os.makedirs(base, exist_ok=True)
    with open(_path(base, d["id"]), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def load_all(base):
    res = []
    if not os.path.isdir(base):
        return res
    for fn in sorted(os.listdir(base)):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(base, fn), encoding="utf-8") as f:
                    res.append(normalize(json.load(f)))
            except (OSError, ValueError):
                pass
    return res


def delete_line(base, line_id):
    try:
        os.remove(_path(base, line_id))
    except OSError:
        pass
