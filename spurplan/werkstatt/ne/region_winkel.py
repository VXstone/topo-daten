"""Sichtprüfung Regionalplan (Hinweis 19.10. Rothrist Ost): schwarze Spurwechsel/Nebengleise,
die quer (~90°) zu den grünen Strecken stehen oder sich kreuzen wie eine DKW.
python3 region_winkel.py plan.svg  -> Liste der Stellen (x,y, Art)"""
import re, sys, math
import numpy as np
from shapely.geometry import LineString
svg = open(sys.argv[1]).read()
def segs(d):
    toks = re.findall(r'[MLQHV]|-?[\d.]+', d); out = []; cur = None; i = 0; cmd = None
    while i < len(toks):
        if toks[i] in "MLQHV": cmd = toks[i]; i += 1; continue
        if cmd == "M": cur = (float(toks[i]), float(toks[i+1])); i += 2; cmd = "L"; continue
        if cmd == "L": p = (float(toks[i]), float(toks[i+1])); out.append((cur, p)); cur = p; i += 2
        elif cmd == "Q": p = (float(toks[i+2]), float(toks[i+3])); cur = p; i += 4
        elif cmd == "H": p = (float(toks[i]), cur[1]); out.append((cur, p)); cur = p; i += 1
        elif cmd == "V": p = (cur[0], float(toks[i])); out.append((cur, p)); cur = p; i += 1
        else: i += 1
    return out
import xml.etree.ElementTree as ET
G, B = [], []
def walk(el, tr):
    tr = tr or ("transform" in el.attrib)
    if el.tag.endswith("path") and not tr and el.get("stroke") and el.get("stroke") not in ("none", "#fff", "#ffffff"):
        yield el.get("d"), el.get("stroke")
    for ch in el: yield from walk(ch, tr)
for d, c in walk(ET.fromstring(svg), False):
    for a, b in segs(d):
        if math.dist(a, b) < 3: continue
        (G if c.lower() != "#111" else B).append((a, b))
Gl = [LineString(s) for s in G]
from shapely.strtree import STRtree
T = STRtree(Gl)
bef = []
for a, b in B:
    L = math.dist(a, b); 
    if L < 4: continue
    mid = ((a[0]+b[0])/2, (a[1]+b[1])/2); ls = LineString([a, b])
    if sum(1 for k in T.query(ls) if Gl[k].crosses(ls)) >= 2: continue      # Portal/Brückenflügel quer über alle Gleise
    for k in T.query(ls.buffer(1.5)):
        g = G[k]; v1 = np.subtract(b, a); v2 = np.subtract(g[1], g[0])
        ang = math.degrees(math.acos(min(1, abs(v1 @ v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))))
        if ang > 75 and Gl[k].length > 8: bef.append((round(mid[0], 1), round(mid[1], 1), f"quer {ang:.0f}°")); break
# sich kreuzende schwarze Spurwechsel (wirkt wie DKW)
Bl = [LineString(s) for s in B if math.dist(*s) >= 4]
for i in range(len(Bl)):
    for j in range(i + 1, len(Bl)):
        if Bl[i].crosses(Bl[j]):
            p = Bl[i].intersection(Bl[j])
            if p.geom_type == "Point": bef.append((round(p.x, 1), round(p.y, 1), "Spurwechsel kreuzen"))
seen = set()
for x, y, t in bef:
    k = (round(x / 10), round(y / 10), t[:4])
    if k in seen: continue
    seen.add(k); print(f"{x},{y}\t{t}")
print(f"Sichtprüfung: {len(seen)} Stellen", file=sys.stderr)
