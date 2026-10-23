"""
Prüfung 4: Gleise, die sich im fertigen Plan zu nahe kommen.
  - zwei Linien laufen über eine Strecke parallel in weniger als MIN_PX Abstand (Mittellinie zu Mittellinie),
    ohne sich zu berühren -> optisch ein Gleis / Weiche nicht erkennbar
Regel "alle Weichen auf Hauptgleisen sind sichtbar": zweigt ein Gleis von einem Hauptgleis ab, muss es sich
sofort mindestens MIN_PX entfernen; ein Nebengleis, das eng neben dem Hauptgleis herläuft, verdeckt die Weiche.
Aufruf: python3 abstand.py plan.svg [--min 4.5] [--png markiert.png] [--liste]
"""
import re, sys, math
from xml.etree import ElementTree as ET
import numpy as np
from svgpathtools import parse_path
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

src = sys.argv[1]
MIN = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 4.5
MINLEN = float(sys.argv[sys.argv.index("--len") + 1]) if "--len" in sys.argv else 2.5 * MIN    # parallele Strecke [px]
SHORT = 3 * MIN                                     # kürzere Linien (DKW-Bögen, Stummel) nicht prüfen
TOUCH = 1.5                                          # darunter: Linien treffen sich (Weiche, Zusammenführung)
NS = "{http://www.w3.org/2000/svg}"

def parse_tf(t):
    M = np.eye(3)
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", t or ""):
        a = [float(v) for v in re.split(r"[ ,]+", args.strip()) if v]
        if name == "translate":
            T = np.array([[1, 0, a[0]], [0, 1, a[1] if len(a) > 1 else 0], [0, 0, 1]])
        elif name == "scale":
            T = np.array([[a[0], 0, 0], [0, a[1] if len(a) > 1 else a[0], 0], [0, 0, 1]])
        elif name == "rotate":
            r = math.radians(a[0]); c, s = math.cos(r), math.sin(r)
            R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            if len(a) == 3:
                T = np.array([[1, 0, a[1]], [0, 1, a[2]], [0, 0, 1]]) @ R @ np.array([[1, 0, -a[1]], [0, 1, -a[2]], [0, 0, 1]])
            else: T = R
        elif name == "matrix":
            T = np.array([[a[0], a[2], a[4]], [a[1], a[3], a[5]], [0, 0, 1]])
        else: continue
        M = M @ T
    return M

lines = []          # (LineString, Farbe, Breite, id)
def walk(el, M, stroke=None, width=None):
    M = M @ parse_tf(el.get("transform"))
    stroke = el.get("stroke", stroke); width = el.get("stroke-width", width)
    tag = el.tag.replace(NS, "")
    if tag == "path" and stroke not in (None, "none") and el.get("fill", "none") in ("none", ""):
        try: p = parse_path(el.get("d"))
        except Exception: p = None
        if p is not None:
            cur = []
            sc = math.sqrt(abs(np.linalg.det(M[:2, :2])))
            for seg in p:
                if cur and abs(seg.start - cur[-1][2]) > 0.3:
                    if len(cur) > 1: lines.append((LineString([c[:2] for c in cur]), stroke, float(width or 1) * sc, len(lines)))
                    cur = []
                n = max(2, int(seg.length() * sc / 1.5))
                for t in np.linspace(0, 1, n):
                    z = seg.point(t); q = M @ np.array([z.real, z.imag, 1])
                    cur.append((q[0], q[1], z))
            if len(cur) > 1: lines.append((LineString([c[:2] for c in cur]), stroke, float(width or 1) * sc, len(lines)))
    for c in el: walk(c, M, stroke, width)
walk(ET.parse(src).getroot(), np.eye(3))

# in kurze Stücke zerlegen
pieces, owner, dirs = [], [], []
for L, col, w, i in lines:
    cs = list(L.coords)
    for a, b in zip(cs, cs[1:]):
        if math.dist(a, b) < 0.2: continue
        pieces.append(LineString([a, b])); owner.append(i)
        d = np.subtract(b, a); dirs.append(d / np.linalg.norm(d))
tree = STRtree(pieces)
hits = {}
for k, pc in enumerate(pieces):
    for j in tree.query(pc.buffer(MIN)):
        j = int(j)
        if owner[j] <= owner[k]: continue
        if abs(float(dirs[k] @ dirs[j])) < 0.97: continue          # nur (fast) parallele Stücke
        d = pc.distance(pieces[j])
        if TOUCH < d < MIN:
            key = (owner[k], owner[j]); hits.setdefault(key, {})[k] = (pc.centroid, d, pc.length)
# Paare nur melden, wenn sich die beiden Linien nirgends berühren (sonst: Zusammenführung, Weiche)
issues = []
for (a, b), dct in hits.items():
    lst = list(dct.values())
    ea = [Point(lines[a][0].coords[0]), Point(lines[a][0].coords[-1])]; eb = [Point(lines[b][0].coords[0]), Point(lines[b][0].coords[-1])]
    if min(p.distance(q) for p in ea for q in eb) < 4: continue          # Fortsetzung (Spurplan -> Strecke), keine zwei Gleise
    if min(p.distance(lines[b][0]) for p in ea) < 2.5 and min(p.distance(lines[a][0]) for p in eb) < 2.5: continue
    length = sum(l for _, _, l in lst)
    if length < MINLEN: continue
    if lines[a][0].length < SHORT or lines[b][0].length < SHORT: continue      # DKW-Bögen, Stummel
    touch = lines[a][0].distance(lines[b][0]) < TOUCH
    c = lst[len(lst) // 2][0]; dmin = min(d for _, d, _ in lst)
    kind = "Weiche verdeckt" if touch else "zu nah"
    issues.append((kind, c, dmin, length, lines[a][1], lines[b][1]))
# Prüfung R (nur Spurplan, --winkel): Gleisstücke quer zur Achse (steiler als 75°) - es gibt keine 90°-Winkel
if "--winkel" in sys.argv:
    for L, col, w, i in lines:
        cs = list(L.coords); run_, start_ = 0.0, None
        for a_, b_ in list(zip(cs, cs[1:])) + [((0, 0), (0, 0))]:
            dx_, dy_ = b_[0] - a_[0], b_[1] - a_[1]; ln_ = math.hypot(dx_, dy_)
            if ln_ > 0.2 and abs(dx_) < 0.26 * ln_:
                run_ += ln_; start_ = start_ or a_
            else:
                if run_ > 8:
                    issues.append(("90 Grad", Point(start_), 0.0, run_, col, col))
                run_, start_ = 0.0, None
from collections import Counter
print(f"Prüfung 4 (Abstand < {MIN} px): {dict(Counter(i[0] for i in issues))}")
if "--liste" in sys.argv:
    for kind, c, d, l, ca, cb in sorted(issues, key=lambda t: -t[3])[:60]:
        print(f"  {kind:16s} x={c.x:7.0f} y={c.y:7.0f}  Abstand {d:4.1f} px auf {l:5.0f} px  ({ca}/{cb})")
if "--png" in sys.argv:
    svg = open(src).read()
    m = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"', svg)
    mk = "".join(f'<circle cx="{c.x:.0f}" cy="{c.y:.0f}" r="9" fill="none" stroke="{"#c0f" if k == "zu nah" else "#f80"}" stroke-width="2"/>' for k, c, *_ in issues)
    import cairosvg
    cairosvg.svg2png(bytestring=svg.replace("</svg>", mk + "</svg>").encode(), write_to=sys.argv[sys.argv.index("--png") + 1], output_width=4000)
if "--json" in sys.argv:
    import json
    json.dump([dict(art=k, x=round(c.x, 1), y=round(c.y, 1), abstand=round(d, 1), laenge=round(l)) for k, c, d, l, *_ in issues],
              open(sys.argv[sys.argv.index("--json") + 1], "w"))
