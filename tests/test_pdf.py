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
    x = model.new_line()
    x.update(number="6É", type="ejszakai", color="#000000", destination=["Széll Kálmán tér M", ""])
    x["stops"] = [["Móricz Zsigmond körtér M", 0, ""], ["Budafoki út / Karinthy Frigyes út", 0, ""]] + \
        [["Megálló %d" % i, i * 2, "a" if i == 5 else ""] for i in range(1, 15)]
    b = x["sections"][0][0]
    b["title"], b["sub"] = "Éjszakai karbantartások idején", "During night-time maintenance works"
    b["rows"] = {"0": "22, 27, 32, 37, 45, 52", "1": "00, 07, 15, 22, 30, 37, 45", "2": "00, 15, 30, 45",
                 "3": "00, 15, 30, 45", "4": "00, 09a, 19a"}
    x["footnotes"] = [["a", "Blaha Lujza tér M megállóig közlekedik", "runs only to Blaha Lujza tér M stop", "info"],
                      ["", "A pótlóbusz nem áll meg.", "The replacement bus does not stop.", "stop"],
                      ["", "Karbantartási tájékoztató a megállókban.", "Info boards in the stops.", "work"],
                      ["", "Minden jármű akadálymentes.", "All vehicles are accessible.", "access"]]
    cases["ejszakai"] = x
    x = sample(); x["color"] = "#000000"
    for sec in x["sections"]:
        for b in sec: b["rows"]["0"] = "10, 40"; b["rows"]["24"] = "00"
    cases["fekete_0_24"] = x
    for name, data in cases.items():
        out = os.path.join(outdir, name + ".pdf")
        pdfgen.render(data, out)
        assert os.path.getsize(out) > 2000, name
        pages = subprocess.check_output(["pdfinfo", out]).decode()
        assert any(l.split()[:2] == ["Pages:", "1"] for l in pages.splitlines()), (name, pages)
        print("OK", name)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
