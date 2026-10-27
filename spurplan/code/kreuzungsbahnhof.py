"""Kreuzungsbahnhof (27.10.2026, Kerzers, Hinweis eojeak D. Eckenstein): zwei Linien kreuzen sich im Bahnhof; jede
Linie wird eine eigene gerade Achse, die beiden Achsen kreuzen sich unter 60° (ein X).

  python3 kreuzungsbahnhof.py <bahnhof>      (im Arbeitsordner, nach der normalen Kette)

Der Plan wird nicht neu erfunden, sondern aus dem normal gerechneten Spurplan umgelegt (alle Regeln, alle Weichen,
Anschlussgleise und Abgänge aus OSM bleiben): Im normalen Plan laufen die beiden Linien parallel (oben/unten) und
kreuzen sich in einem Kreuzungsbereich (die zwei Diagonalen zwischen den Linien). Links und rechts davon liegen vier
Äste (oben links, unten links, oben rechts, unten rechts). Jeder Ast wird starr gedreht (Winkel bleiben, 60°-Weichen
bleiben 60° zur Achse) und an die Mitte gesetzt; das Streckengleis des Astes liegt auf der Achse. Der
Kreuzungsbereich wird ersetzt: die Hauptlinien gehen gerade durch die Mitte, die Verbindungen zwischen den Linien
(gerade Gleise im Kreuzungsbereich) werden Kurven seitlich der Kreuzung.

Override «kreuzungsbahnhof»: {"aeste": {Ort: Winkel, …}}  (Ort = Abgang des Astes wie in ports.json, Winkel in Grad,
0 = rechts, 60 = rechts oben, …); die Achsen sind die Paare gegenüberliegender Äste.
Schreibt <bahnhof>_bare.svg, <bahnhof>_spurplan.svg und <bahnhof>_ports.json neu (die alten als *_parallel.*).
"""
import json, math, re, sys, shutil, os

b = sys.argv[1]
K = json.load(open(f"{b}_override.json"))["kreuzungsbahnhof"]
P0 = json.load(open(f"{b}_ports.json"))
WINKEL = K["aeste"]
EP = [p for p in P0["ports"] if p["kind"] == "edge" and p["town"] in WINKEL]
assert len(EP) == 4, f"vier Längsabgänge erwartet, gefunden {[(p['town'], p['dx']) for p in EP]}"
ys = sorted({p["y"] for p in EP}); YM = (ys[0] + ys[-1]) / 2
def quad(x, y, xm): return ("l" if x < xm else "r") + ("o" if y < YM else "u")
NUM = r"-?[\d.]+"

def parse(d):
    """SVG-Pfad (M L H V Q, absolut) -> Liste von Teilpfaden, je Liste von Segmenten (art, punkte)"""
    out, cur, p = [], None, None
    for c, a in re.findall(r"([MLHVQZ])([^MLHVQZ]*)", d):
        v = [float(x) for x in re.findall(NUM, a)]
        if c == "M":
            p = (v[0], v[1]); cur = []; out.append(cur)
            for i in range(2, len(v), 2): cur.append(("L", [p, (v[i], v[i + 1])])); p = (v[i], v[i + 1])
        elif c == "L":
            for i in range(0, len(v), 2): cur.append(("L", [p, (v[i], v[i + 1])])); p = (v[i], v[i + 1])
        elif c == "H":
            for x in v: cur.append(("L", [p, (x, p[1])])); p = (x, p[1])
        elif c == "V":
            for y in v: cur.append(("L", [p, (p[0], y)])); p = (p[0], y)
        elif c == "Q":
            for i in range(0, len(v), 4): cur.append(("Q", [p, (v[i], v[i + 1]), (v[i + 2], v[i + 3])])); p = (v[i + 2], v[i + 3])
    return out

# ---- Kreuzungsbereich: Diagonalen im grünen Plan, die von der oberen zur unteren Linie laufen
bare0 = open(f"{b}_bare.svg").read()
gruen = [m.group(1) for m in re.finditer(r'<path d="([^"]*)" stroke="#00862f"', bare0)]
diag = []
for d in gruen:
    for sp in parse(d):
        for art, q in sp:
            if art == "L" and abs(q[1][1] - q[0][1]) > (ys[-1] - ys[0]) * 0.5: diag.append(q)
assert diag, "keine Kreuzungsdiagonalen gefunden"
XA = min(min(q[0][0], q[1][0]) for q in diag); XB = max(max(q[0][0], q[1][0]) for q in diag)
XC = (XA + XB) / 2
XA, XB = XA - 9, XB + 9            # Ausrundungen der Diagonalen gehören zum Kreuzungsbereich
ACHSE = {}                     # Quadrant -> (Ort, Gleis-y, Winkel)
for p in EP: ACHSE[quad(p["x"], p["y"], XC)] = (p["town"], p["y"], WINKEL[p["town"]])
assert len(ACHSE) == 4, ACHSE
def u(dg): return (math.cos(math.radians(dg)), -math.sin(math.radians(dg)))

# Abstand der Äste von der Mitte: die Gleise im spitzen Winkel zwischen zwei Ästen derselben Seite dürfen sich nicht
# berühren -> zusätzlicher Abstand E je Seite
def roh(x, y, q):
    _, y0, dg = ACHSE[q]; s = (XC - x) if q[0] == "l" else (x - XC); n = y - y0
    return s, n
def alle_punkte(svgs):
    for s_ in svgs:
        for d in re.findall(r' d="([^"]*)"', s_):
            for sp in parse(d):
                for art, q in sp:
                    for pt in q: yield pt
        for m in re.finditer(r'<rect x="(%s)" y="(%s)" width="(%s)" height="(%s)"' % (NUM, NUM, NUM, NUM), s_):
            x, y, w, h = map(float, m.groups()); yield (x, y); yield (x + w, y + h)
E = {}
plan0 = open(f"{b}_spurplan.svg").read()
for seite in "lr":
    halb = abs(WINKEL[ACHSE[seite + "o"][0]] - WINKEL[ACHSE[seite + "u"][0]]) % 360; halb = min(halb, 360 - halb) / 2
    need = 0.0
    for x, y in alle_punkte([bare0]):
        if (seite == "l" and x > XA) or (seite == "r" and x < XB): continue
        q = quad(x, y, XC); s, n = roh(x, y, q)
        innen = n if q[1] == "o" else -n          # zum anderen Ast derselben Seite hin
        if innen > -10: need = max(need, (innen + 12) / math.sin(math.radians(halb)) - s)
    E[seite] = max(0.0, need)

def abb(x, y, q=None):
    q = q or quad(x, y, XC); s, n = roh(x, y, q); s += E[q[0]]
    _, _, dg = ACHSE[q]; a, c = u(dg)
    v = (c, -a) if q[0] == "l" else (-c, a)       # Drehung ohne Spiegelung
    return (s * a + n * v[0], s * c + n * v[1])

def seg_teilen(art, q):
    """Segment an XA/XB teilen; Teile im Kreuzungsbereich fallen weg"""
    if art == "Q":
        xm = q[1][0]
        return [] if XA + 0.5 < xm < XB - 0.5 else [(art, q)]
    (x0, y0), (x1, y1) = q; cut = sorted({x0, x1, *[t for t in (XA, XB) if min(x0, x1) < t < max(x0, x1)]})
    if x0 > x1: cut = cut[::-1]
    out = []
    for xa_, xb_ in zip(cut, cut[1:]) if len(cut) > 1 else [(x0, x1)]:
        f = lambda x_: y0 + (y1 - y0) * ((x_ - x0) / (x1 - x0) if x1 != x0 else 0)
        xm = (xa_ + xb_) / 2
        if XA + 0.5 < xm < XB - 0.5: continue
        out.append(("L", [(xa_, f(xa_)), (xb_, f(xb_))]))
    return out

def pfad(d):
    teile = []
    for sp in parse(d):
        for art, q in sp:
            for art2, q2 in seg_teilen(art, q):
                xm = sum(p_[0] for p_ in q2) / len(q2); ym = sum(p_[1] for p_ in q2) / len(q2)
                qd = quad(xm, ym, XC); teile.append((art2, [abb(*p_, qd) for p_ in q2]))
    s_ = ""; last = None
    for art, q in teile:
        if last is None or math.dist(last, q[0]) > 0.05: s_ += f"M{q[0][0]:.1f},{q[0][1]:.1f}"
        s_ += (f"L{q[1][0]:.1f},{q[1][1]:.1f}" if art == "L" else f"Q{q[1][0]:.1f},{q[1][1]:.1f} {q[2][0]:.1f},{q[2][1]:.1f}")
        last = q[-1]
    return s_

# Mitte: Achsen durch die Kreuzung, Verbindungen als Kurven
def mitte():
    d_ = ""
    for q in ACHSE:
        p = abb(XA if q[0] == "l" else XB, ACHSE[q][1], q); d_ += f" M{p[0]:.1f},{p[1]:.1f}L0,0"
    for d in gruen:
        for sp in parse(d):
            for art, q in sp:
                if art != "L" or abs(q[0][1] - q[1][1]) > 0.5: continue
                x0, x1 = sorted((q[0][0], q[1][0]))
                if x0 <= XA + 0.5 and x1 >= XB - 0.5:
                    ql = [k for k in ACHSE if k[0] == "l" and abs(ACHSE[k][1] - q[0][1]) < 0.5]
                    qr = [k for k in ACHSE if k[0] == "r" and abs(ACHSE[k][1] - q[0][1]) < 0.5]
                    if ql and qr:
                        p1, p2 = abb(XA, q[0][1], ql[0]), abb(XB, q[0][1], qr[0])
                        d_ += f" M{p1[0]:.1f},{p1[1]:.1f}Q0,0 {p2[0]:.1f},{p2[1]:.1f}"
    return d_

def umlegen(s_, plan):
    erst = [True]
    def pf(m):
        neu = pfad(m.group(2))
        if erst[0] and 'stroke="#00862f" stroke-width="3.6"' in m.group(3): neu += mitte(); erst[0] = False
        return m.group(1) + neu + m.group(3)
    s_ = re.sub(r'(<path d=")([^"]*)("[^>]*>)', pf, s_)
    def rect(m):
        x, y, w, h = map(float, m.group(1, 2, 3, 4)); rest = m.group(6)
        if 'fill="#fff"' not in rest:                  # Perron: als gedrehtes Viereck
            q = [abb(*p_) for p_ in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))]
            return '<path d="M' + "L".join(f"{a:.1f},{c:.1f}" for a, c in q) + f'Z"{rest}'
        cx, cy = abb(x + w / 2, y + h / 2); return f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w:.0f}" height="{h:.0f}"{rest}'
    s_ = re.sub(r'<rect x="(%s)" y="(%s)" width="(%s)" height="(%s)"( rx="[\d.]+")?([^>]*>)' % (NUM, NUM, NUM, NUM), rect, s_)
    # Gleisnummern: mitdrehen (aufrecht); Abgangs-Beschriftung und Titel: neu setzen
    def text(m):
        x, y, rest, t = float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
        if 'font-size="19"' in rest:
            cx, cy = abb(x, y - 6.5); return f'<text x="{cx:.1f}" y="{cy + 6.5:.1f}"{rest}>{t}</text>'
        return ""                                   # Abgangs- und Titeltexte unten neu
    s_ = re.sub(r'<text x="(%s)" y="(%s)"([^>]*)>([^<]*)</text>' % (NUM, NUM), text, s_)
    return s_

bare = umlegen(bare0, False)
plan = umlegen(plan0, True)
# Abgänge
ports = []
for q, (ort, y0, dg) in ACHSE.items():
    p = dict([p_ for p_ in EP if p_["town"] == ort][0]); e = abb(p["x"], y0, q)
    p["x"], p["y"] = e
    if dg % 180 == 0: p.update(kind="edge", dx=1 if dg == 0 else -1, dy=0)
    else: p.update(kind="side", dx=1 if dg in (60, 300) else -1, dy=-1 if dg in (60, 120) else 1)
    ports.append(p)
# Rahmen
pts = [(float(a), float(c)) for a, c in re.findall(r"(%s),(%s)" % (NUM, NUM), bare)]
X0, Y0, X1, Y1 = min(a for a, c in pts) - 40, min(c for a, c in pts) - 40, max(a for a, c in pts) + 40, max(c for a, c in pts) + 40
def rahmen(s_, extra=0, unten=0):
    x0, y0, x1, y1 = X0 - extra, Y0 - extra, X1 + extra, Y1 + extra + unten
    return re.sub(r'<svg([^>]*?)viewBox="[^"]*" width="[^"]*" height="[^"]*"',
                  f'<svg\\1viewBox="{x0:.0f} {y0:.0f} {x1 - x0:.0f} {y1 - y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}"', s_, count=1) \
        .replace('<rect width="100%" height="100%"', f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}"', 1)
bare = rahmen(bare)
# Detailplan: Beschriftung der Abgänge am Astende, Titel unten
lab = []
for p in ports:
    dg = WINKEL[p["town"]]; a, c = u(dg); x, y = p["x"] + a * 30, p["y"] + c * 30
    anc = "start" if a > 0.1 else ("end" if a < -0.1 else "middle"); y += (-30 if c < 0 else 22)
    lab.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="22" text-anchor="{anc}" fill="#00862f">Linie {p["ref"]}</text>')
    lab.append(f'<text x="{x:.1f}" y="{y + 26:.1f}" font-size="22" text-anchor="{anc}" fill="#00862f">{p["town"]}</text>')
titel = re.search(r'font-weight="700"[^>]*>([^<]*)<', plan0)
lab.append(f'<text x="{(X0 + X1) / 2:.1f}" y="{Y1 + 120:.1f}" font-size="38" font-weight="700" text-anchor="middle" fill="#00862f">{titel.group(1) if titel else b}</text>')
plan = rahmen(plan.replace("</svg>", "\n".join(lab) + "\n</svg>"), extra=120, unten=40)
for f in ("bare.svg", "spurplan.svg", "ports.json"): shutil.copy(f"{b}_{f}", f"{b}_parallel_{f}")
open(f"{b}_bare.svg", "w").write(bare); open(f"{b}_spurplan.svg", "w").write(plan)
json.dump(dict(P0, ports=ports + [p for p in P0["ports"] if p not in EP and False], W=X1 - X0, H=Y1 - Y0, x_lo=X0 + 40, x_hi=X1 - 40,
               y_lo=Y0 + 40, y_hi=Y1 - 40), open(f"{b}_ports.json", "w"), ensure_ascii=False)
print(f"Kreuzungsbahnhof {b}: Kreuzungsbereich x={XA:.0f}…{XB:.0f}, Äste " +
      ", ".join(f"{o} {dg}°" for q, (o, y_, dg) in sorted(ACHSE.items())) + f", Zusatzabstand {E}")
