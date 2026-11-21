# -*- coding: utf-8 -*-
import copy, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from menetrend import model, pdfgen

def sample():
    d = model.new_line()
    d.update(number="7", type="villamos", color="#E41F18",
             destination=["Kis-tó /", "Végállomás"])
    d["stops"] = [["Mesevölgy kapu", 0], ["Szivárvány utca", 2], ["Kerekerdő tér / Mézeskalács utca", 3], ["Kis-tó, Végállomás", 18]]
    row = {str(h): "00, 08, 16, 24, 32, 40, 48, 56" for h in model.HOURS}
    d["sections"] = [[model.new_block("Hétköznap", "Weekdays"), model.new_block("Péntek", "Fridays")],
                     [model.new_block(*model.BLOCK_PRESETS[8]), model.new_block(*model.BLOCK_PRESETS[4]), model.new_block(*model.BLOCK_PRESETS[5])]]
    for sec in d["sections"]:
        for b in sec: b["rows"] = dict(row)
    d["footnotes"] = [["a", "Kerekerdő térig közlekedik", "runs only to Kerekerdő tér stop"]]
    d["legend"] = {"bike": True, "access": True}
    d["door"] = {"enabled": True, "except_hu": "Kivéve munkanapokon 20:00 előtt", "except_en": "Except on workdays before 20:00"}
    d["validFrom"] = "2026-11-21"
    return d

def main(outdir):
    cases = {}
    cases["alap"] = sample()
    x = sample(); x["type"] = "busz"; x["color"] = "#FFD800"; x["number"] = "900A"
    cases["sarga_busz"] = x
    x = sample(); x["type"] = "trolibusz"; x["color"] = "#009FE3"
    x["stops"] = [["Megálló %d hosszú névvel, ami több sorba tördelődik" % i, i * 2] for i in range(30)]
    x["sections"] = [[model.new_block()]]; x["legend"] = {"bike": False, "access": False}
    x["door"]["enabled"] = False; x["info"]["enabled"] = False; x["footnotes"] = [["a", "x", "y"]] * 4
    x["sections"][0][0]["rows"] = {str(h): "05, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 58, 59, 59, 59" for h in model.HOURS}
    cases["szelso"] = x
    x = sample(); x["destination"] = ["Közvágóhíd H", ""]; cases["egysoros"] = x
    x = sample(); x["destination"] = ["Budapest Nyugati pályaudvar / Vörösmarty tér, Nagykörút", ""]; cases["hosszu_egysoros"] = x
    x = model.new_line(); cases["ures"] = x
    for name, data in cases.items():
        out = os.path.join(outdir, name + ".pdf")
        pdfgen.render(data, out)
        assert os.path.getsize(out) > 2000, name
        pages = subprocess.check_output(["pdfinfo", out]).decode()
        assert any(l.split()[:2] == ["Pages:", "1"] for l in pages.splitlines()), (name, pages)
        print("OK", name)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
