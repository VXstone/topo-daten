"""Gezeichnete Kreuzungen zählen und mit echten Kreuzungen (OSM railway_crossing / Kreuzungsweichen) vergleichen."""
import runpy, sys, json, math
import numpy as np
from svgpathtools import parse_path
from shapely.geometry import LineString, Point
args = sys.argv[1:]
sys.argv = ["x"] + args
G = runpy.run_path("spurplan_schema.py")
segs, DBG = G["segs"], G["DBG"]
lines = {}
for sid, d in DBG:
    p = parse_path(d); pts = []
    for s in p:
        n = max(2, int(s.length() / 2)); pts += [s.point(t) for t in np.linspace(0, 1, n)]
    if len(pts) > 1: lines.setdefault(sid, []).append(LineString([(z.real, z.imag) for z in pts]))
# Knotenpunkte in der Zeichnung (Weichen/Enden): hier sind Berührungen legitim
nodepts = []
for sg in segs:
    for n in (sg["nodes"][0], sg["nodes"][-1]):
        try: nodepts.append((G["xpos"](n, G["SD"][n][0]), G["ypos"](n)))
        except Exception: pass
NP = np.array(nodepts)
real_x = [n for n, t in G["ntag"].items() if t.get("railway") == "railway_crossing" and n in G["home"]]
real_pts = [(G["xpos"](n, G["SD"][n][0]), G["ypos"](n)) for n in real_x]
ids = list(lines); found = []
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        if segs[a].get("group") and segs[a].get("group") is segs[b].get("group"): continue
        for la in lines[a]:
            for lb in lines[b]:
                it = la.intersection(lb)
                if it.is_empty: continue
                for g in getattr(it, "geoms", [it]):
                    if g.geom_type != "Point": continue
                    # legitim nur, wenn beide Linien an diesem Punkt einen gemeinsamen Knoten haben
                    na = {n for x_ in ([segs[a]] + segs[a].get("group", [])) for n in x_["nodes"]}
                    nb = {n for x_ in ([segs[b]] + segs[b].get("group", [])) for n in x_["nodes"]}
                    shared = [n for n in na & nb if math.dist((G["xpos"](n, G["SD"][n][0]), G["ypos"](n)), (g.x, g.y)) < 8]
                    if shared: continue
                    real = any(math.dist((g.x, g.y), r) < 15 for r in real_pts)
                    found.append((round(g.x), round(g.y), segs[a]["way"], segs[b]["way"], real))
uniq = {}
for f in found: uniq.setdefault((f[0] // 8, f[1] // 8), f)
fl = list(uniq.values())
print(f"gezeichnete Kreuzungen: {len(fl)}  davon an echter OSM-Kreuzung: {sum(f[4] for f in fl)}  echte Kreuzungen im Ausschnitt: {len(real_pts)}")
for f in sorted(fl): print("  ", f)
# Engstellen: zwei Linien ohne gemeinsamen Knoten laufen näher als 5 px nebeneinander
eng = []
for i, a in enumerate(ids):
    for b in ids[i + 1:]:
        if segs[a].get("group") and segs[a].get("group") is segs[b].get("group"): continue
        na = {n for x_ in ([segs[a]] + segs[a].get("group", [])) for n in x_["nodes"]}
        nb = {n for x_ in ([segs[b]] + segs[b].get("group", [])) for n in x_["nodes"]}
        for la in lines[a]:
            for lb in lines[b]:
                if la.distance(lb) > 5: continue
                close = la.intersection(lb.buffer(5))
                Lc = close.length if not close.is_empty else 0
                if Lc < 8: continue
                c = close.centroid
                near_shared = [n for n in na & nb if math.dist((G["xpos"](n, G["SD"][n][0]), G["ypos"](n)), (c.x, c.y)) < 25]
                if near_shared: continue
                eng.append((round(c.x), round(c.y), round(Lc), segs[a]["way"], segs[b]["way"]))
u2 = {}
for f in eng: u2.setdefault((f[0] // 10, f[1] // 10), f)
print(f"Engstellen (< 5 px, > 8 px lang): {len(u2)}")
for f in sorted(u2.values()): print("  ", f)
