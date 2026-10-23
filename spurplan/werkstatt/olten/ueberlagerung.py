"""
Prüfung E: Überlagerungen von Elementen in einem fertigen Spurplan-SVG.
  E1 Beschriftung liegt auf einer Linie (ausser Gleisnummern mit weissem Hintergrund)
  E2 Prellbock-Punkt liegt auf einer fremden Linie
  E3 Pfeil (Abgang) liegt auf einer fremden Linie
  E4 Perronbalken berührt eine Linie
  E5 Beschriftungen überlappen sich
Aufruf: python3 ueberlagerung.py plan.svg [--png overlay.png]
"""
import re, sys, math
from xml.etree import ElementTree as ET
from svgpathtools import parse_path
from shapely.geometry import LineString, Point, box, Polygon
from shapely.ops import unary_union
import numpy as np

src = sys.argv[1]
root = ET.parse(src).getroot()
ns = "{http://www.w3.org/2000/svg}"
lines, texts, dots, arrows, bars, knock = [], [], [], [], [], []
def walk(el, tf=(1, 0, 0)):
    t = el.get("transform", "")
    m = re.search(r"translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+)\)", t)
    if m: tf = (float(m.group(3)) * tf[0], tf[1] + tf[0] * float(m.group(1)), tf[2] + tf[0] * float(m.group(2)))
    tag = el.tag.replace(ns, "")
    S = lambda x, y: (tf[1] + tf[0] * x, tf[2] + tf[0] * y)
    if tag == "path":
        d = el.get("d"); fill = el.get("fill", "")
        par_stroke = el.get("stroke") or ""
        try: p = parse_path(d)
        except Exception: p = None
        if p is not None and len(p):
            if fill not in ("", "none") and el.get("stroke") is None:          # Pfeil
                pts = [S(z.real, z.imag) for seg in p for z in (seg.start, seg.end)]
                if len(pts) >= 3: arrows.append(Polygon(pts).buffer(0))
            else:
                w = float(el.get("stroke-width") or 2) * tf[0]
                cur = []
                for seg in p:
                    if cur and abs(seg.start - cur[-1][2]) > 0.5:
                        lines.append((LineString([c[:2] for c in cur]), w)) if len(cur) > 1 else None; cur = []
                    n = max(2, int(seg.length() / 2))
                    for t_ in np.linspace(0, 1, n):
                        z = seg.point(t_); cur.append((*S(z.real, z.imag), z))
                if len(cur) > 1: lines.append((LineString([c[:2] for c in cur]), w))
    elif tag == "circle":
        x, y = S(float(el.get("cx")), float(el.get("cy"))); dots.append(Point(x, y).buffer(float(el.get("r")) * tf[0]))
    elif tag == "rect" and el.get("width") not in ("100%",):
        x, y = S(float(el.get("x")), float(el.get("y"))); w = float(el.get("width")) * tf[0]; h = float(el.get("height")) * tf[0]
        r = box(x, y, x + w, y + h)
        (knock if el.get("fill") == "#fff" else bars).append(r)
    elif tag == "text":
        x, y = S(float(el.get("x")), float(el.get("y"))); fs = float(el.get("font-size", 14)) * tf[0]
        s = "".join(el.itertext()); w = 0.56 * fs * len(s); a = el.get("text-anchor", "start")
        x0 = x - (w if a == "end" else w / 2 if a == "middle" else 0)
        texts.append((box(x0, y - 0.75 * fs, x0 + w, y + 0.2 * fs), s))
    for c in el: walk(c, tf)
walk(root)
# Perronbalken sind als dicke Linie gezeichnet (stroke-width >= 5) -> als Balken behandeln
thin = [(l, w) for l, w in lines if w < 5]
bars += [l.buffer(w / 2, cap_style=2) for l, w in lines if w >= 5]
L = [l for l, w in thin]
issues = []
knocked = unary_union(knock) if knock else None
for tb, s in texts:
    if knocked is not None and tb.buffer(-1).within(knocked.buffer(3)): continue      # Gleisnummer in Lücke
    for l in L:
        if l.intersects(tb.buffer(-1)): issues.append(("E1", tb.centroid, f"Beschriftung '{s}' auf Linie")); break
for d_ in dots:
    hits = [l for l in L if l.distance(d_.centroid) < d_.length / 6.28 + 0.5]
    ends = [l for l in hits if min(Point(l.coords[0]).distance(d_.centroid), Point(l.coords[-1]).distance(d_.centroid)) < 3]
    if len(hits) > len(ends): issues.append(("E2", d_.centroid, "Prellbock auf fremder Linie"))
for a in arrows:
    c = a.centroid
    hits = [l for l in L if l.intersects(a.buffer(-0.5))]
    tip_ends = [l for l in hits if min(Point(l.coords[0]).distance(c), Point(l.coords[-1]).distance(c)) < 12]
    if len(hits) > len(tip_ends): issues.append(("E3", c, "Pfeil auf fremder Linie"))
for b in bars:
    for l in L:
        if l.intersects(b.buffer(0.5)): issues.append(("E4", b.centroid, "Perron berührt Linie")); break
for i in range(len(texts)):
    for j in range(i + 1, len(texts)):
        if texts[i][0].intersects(texts[j][0]): issues.append(("E5", texts[i][0].centroid, f"'{texts[i][1]}' / '{texts[j][1]}'"))
from collections import Counter
print("Überlagerungen:", dict(Counter(i[0] for i in issues)))
for k, p, m in issues: print(f"  {k} x={p.x:6.0f} y={p.y:5.0f}  {m}")
if "--png" in sys.argv:
    svg = open(src).read()
    mk = "".join(f'<circle cx="{p.x:.0f}" cy="{p.y:.0f}" r="11" fill="none" stroke="#c0f" stroke-width="2.5"/>' for _, p, _ in issues)
    import cairosvg; cairosvg.svg2png(bytestring=svg.replace("</svg>", mk + "</svg>").encode(), write_to=sys.argv[sys.argv.index("--png") + 1])
