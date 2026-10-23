"""Alle sichtbaren X-Kreuzungen (beide Linien laufen durch) nummeriert markieren -> PNG zur Durchsicht."""
import runpy, sys, math
import numpy as np
from svgpathtools import parse_path
from shapely.geometry import LineString, Point
args = sys.argv[1:-1]; outpng = sys.argv[-1]
sys.argv = ["x"] + args
G = runpy.run_path("spurplan_schema.py")
segs, DBG = G["segs"], G["DBG"]
L = []
for sid, d in DBG:
    p = parse_path(d); pts = []
    for s in p:
        n = max(2, int(s.length() / 2)); pts += [s.point(t) for t in np.linspace(0, 1, n)]
    if len(pts) > 1: L.append((sid, LineString([(z.real, z.imag) for z in pts])))
X = []
for i in range(len(L)):
    for j in range(i + 1, len(L)):
        a, la = L[i]; b, lb = L[j]
        if a == b: continue
        it = la.intersection(lb)
        for g in getattr(it, "geoms", [it]) if not it.is_empty else []:
            if g.geom_type != "Point": continue
            if min(Point(la.coords[0]).distance(g), Point(la.coords[-1]).distance(g),
                   Point(lb.coords[0]).distance(g), Point(lb.coords[-1]).distance(g)) < 6: continue
            if any(math.dist((g.x, g.y), x[:2]) < 10 for x in X): continue
            X.append((g.x, g.y, segs[a]["way"], segs[b]["way"]))
svg = open(G["CFG"]["out"]).read()
mk = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="none" stroke="#d0f" stroke-width="2"/>'
             f'<text x="{x + 10:.0f}" y="{y - 8:.0f}" font-size="13" font-weight="700" fill="#d0f">{k + 1}</text>'
             for k, (x, y, _, _) in enumerate(X))
import cairosvg; cairosvg.svg2png(bytestring=svg.replace("</svg>", mk + "</svg>").encode(), write_to=outpng, scale=1.3)
print(len(X), "X-Kreuzungen")
for k, x in enumerate(X): print(k + 1, x[2], x[3])
