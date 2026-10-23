"""
Netzplan zeichnen (Stil Uppsala/Dreieck) aus <name>_layout.json + <name>_stationen.json.

Ebenen
- Streckengleise: grün, je Gleis eine Linie (1–4), Abstand 7 px; an Bahnhofsköpfen zusammengeführt
- Bahnhöfe: Gleisharfe in Bahnhofsrichtung, Perrongleise mit Nummer, Perrons (Ortskenntnis oder Annahme)
- Halte: Perronbalken; Kreuzungsstellen (2 Gleise auf Einspur) als Ausweiche
- Neben-, Abstell- und Güteranlagen: feine graue Kontur neben dem Bahnhof mit Gleiszahl (Detail im Spurplan)
- Abgänge: Liniennummer und Richtung
Aufruf: python3 netz_render.py olten_region "Region Olten" Ausgabe.svg
"""
import json, math, sys
import numpy as np

NAME = sys.argv[1]; TITLE = sys.argv[2] if len(sys.argv) > 2 else NAME
OUTF = sys.argv[3] if len(sys.argv) > 3 else f"{NAME}_netzplan.svg"
L = json.load(open(f"{NAME}_layout.json")); S = json.load(open(f"{NAME}_stationen.json"))
LT = {k: v for k, v in json.load(open("region_lines.json")).items() if not k.startswith("_")}
TOWNS = {"Basel": (47.5476, 7.5897), "Luzern": (47.0502, 8.3102), "Aarau": (47.3913, 8.0512),
         "Bern": (46.9490, 7.4391), "Solothurn": (47.2035, 7.5422), "Sissach": (47.4644, 7.8121),
         "Suhr": (47.3727, 8.0798), "Langenthal": (47.2172, 7.7834), "Olten": (47.3519, 7.9075),
         "Rothrist": (47.3064, 7.8795), "Zofingen": (47.2880, 7.9429), "Lenzburg": (47.3915, 8.1717)}
F = 2.4; GAP = 15; TG = 7.0; TAN = math.tan(math.radians(60)); R = 8
G, K, GR = "#00862f", "#111", "#8a8a8a"
N = {n["id"]: n for n in L["nodes"]}
P = {i: np.array([n["sx"] * F, n["sy"] * F]) for i, n in N.items()}
minx = min(p[0] for p in P.values()); miny = min(p[1] for p in P.values())
M = 260
for i in P: P[i] = P[i] - [minx - M, miny - M]
out, labels = [], []

def path(pts, color=G, w=3.0, dash=None):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = map(np.array, pts[i - 1:i + 2])
        l1, l2 = np.linalg.norm(p1 - p0), np.linalg.norm(p2 - p1)
        if l1 < 1e-6 or l2 < 1e-6: continue
        r = min(R, l1 / 2, l2 / 2); a = p1 - (p1 - p0) / l1 * r; b = p1 + (p2 - p1) / l2 * r
        d += f"L{a[0]:.1f},{a[1]:.1f}Q{p1[0]:.1f},{p1[1]:.1f} {b[0]:.1f},{b[1]:.1f}"
    d += f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
    da = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"{da}/>')
def text(x, y, t, size=15, anchor="middle", weight=400, color=G, rot=0):
    tr = f' transform="rotate({rot:.0f} {x:.1f} {y:.1f})"' if rot else ""
    out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}"{tr}>{t}</text>')
def bar(p, q, w=6, color=G): path([p, q], color, w)
def unit(dg): return np.array([math.cos(math.radians(dg)), -math.sin(math.radians(dg))])     # SVG (y nach unten)

# Knotentyp-Hilfen
def is_throat(i): return N[i]["kind"] == "throat"
def station_of(i): return N[N[i]["station"]] if is_throat(i) else None

# ------------------------------------------------------------------ Strecken
edges = [e for e in L["edges"] if not e.get("internal")]
inc = {}
for e in edges:
    for x in (e["a"], e["b"]): inc.setdefault(x, []).append(e)
def converge(i, e):
    """Laufen die Gleise am Knoten i zusammen?  Nein bei Halten/Abzweigen, wenn die Strecke gerade durchläuft."""
    if is_throat(i) or N[i]["kind"] == "exit": return True
    others = [f for f in inc[i] if f is not e]
    if N[i]["kind"] == "halt" and len(others) == 1 and others[0]["tracks"] == e["tracks"] and others[0]["dir"] % 180 == e["dir"] % 180:
        return False
    return True
for e in edges:
    a, b = P[e["a"]], P[e["b"]]
    k = max(1, e["tracks"]); d = b - a; Ld = np.linalg.norm(d)
    if Ld < 1e-6: continue
    u = d / Ld; nv = np.array([-u[1], u[0]])
    offs = [(i - (k - 1) / 2) * TG for i in range(k)]
    ca, cb = converge(e["a"], e), converge(e["b"], e)
    for o in offs:
        run = abs(o) / TAN + (4 if o else 0)
        pts = [a] if ca else [a + nv * o]
        if ca and o: pts.append(a + u * run + nv * o)
        if cb and o: pts.append(b - u * run + nv * o)
        pts.append(b if cb else b + nv * o)
        path([tuple(p) for p in pts], G, 2.6)

# ------------------------------------------------------------------ Halte
for i, n in N.items():
    if n["kind"] != "halt": continue
    es = inc.get(i, [])
    if not es: continue
    e = max(es, key=lambda e: e["tracks"]); u = unit(e["dir"]); nv = np.array([-u[1], u[0]])
    p = P[i]; k = max(1, e["tracks"]); half = (k - 1) / 2 * TG
    for sgn in ((-1, 1) if k >= 2 else (1,)):
        o = sgn * (half + 9)
        bar(tuple(p - u * 18 + nv * o), tuple(p + u * 18 + nv * o))
    side = 1 if abs(u[0]) > 0.5 else 1
    off = nv * (half + 26) * side
    anchor = "middle" if abs(nv[0]) < 0.5 else ("start" if (nv * side)[0] > 0 else "end")
    text(p[0] + off[0], p[1] + off[1] + 5, n["name"], 13, anchor)

# ------------------------------------------------------------------ Bahnhöfe
for i, n in N.items():
    if n["kind"] != "station": continue
    st = S.get(n["name"], {}); A_, B_ = n["throats"]
    pa, pb = P[A_], P[B_]; u = (pb - pa) / max(np.linalg.norm(pb - pa), 1e-6); nv = np.array([-u[1], u[0]])
    tracks = sorted(st.get("tracks", []), key=lambda r: st["lat"][r])
    # Querrichtung Geografie -> Zeichnung: Achse der Gleise auf Layout-Richtung ausrichten
    ax = np.array(st.get("axis", [1, 0])); lay = np.array([u[0], -u[1]])
    flip = 1 if ax @ lay >= 0 else -1
    tracks = tracks if flip > 0 else tracks[::-1]
    # in SVG zeigt nv = (-u_y, u_x) nach "links" bei y nach unten -> Reihenfolge links->rechts im Gelände ist +lat
    tracks = tracks[::-1]
    nt = len(tracks)
    if nt <= 1:                       # Bahnhof mit einem Perrongleis (oder ohne Nummern in OSM)
        path([tuple(pa), tuple(pb)], G, 2.6)
        bar(tuple(pa + u * 20 + nv * 10), tuple(pb - u * 20 + nv * 10), 5.5, color=G if nt == 1 else "#7fbf96")
        text(*(P[i] + nv * 30 + [0, 5]), n["name"], 15, weight=700)
        continue
    offs = {r: (j - (nt - 1) / 2) * GAP for j, r in enumerate(tracks)}
    for r, o in offs.items():
        run = abs(o) / TAN + 10
        pts = [pa, pa + u * run + nv * o, pb - u * run + nv * o, pb]
        path([tuple(p) for p in pts], G, 2.6)
        m = (pa + pb) / 2 + nv * o
        out.append(f'<rect x="{m[0] - 8:.1f}" y="{m[1] - 7:.1f}" width="16" height="14" fill="#fff"/>')
        text(m[0], m[1] + 4.5, r, 11)
    # Perrons
    Lp = np.linalg.norm(pb - pa); run_max = max(abs(o) for o in offs.values()) / TAN + 18
    p0, p1 = pa + u * run_max, pb - u * run_max
    def pl_bar(o): bar(tuple(p0 + nv * o), tuple(p1 + nv * o), 5.5)
    pls = st.get("platforms")
    if pls:
        for pl in pls:
            if "between" in pl:
                a_, b_ = pl["between"]
                if a_ in offs and b_ in offs: pl_bar((offs[a_] + offs[b_]) / 2)
            elif pl.get("outer") in offs:
                o = offs[pl["outer"]]
                side = 1 if o >= max(offs.values()) else (-1 if o <= min(offs.values()) else 1)
                pl_bar(o + side * GAP / 2)
    else:                                  # Annahme: Aussenperrons, gestrichelt
        for o in (min(offs.values()) - GAP / 2, max(offs.values()) + GAP / 2):
            bar(tuple(p0 + nv * o), tuple(p1 + nv * o), 5.5, color="#7fbf96")
    # Neben-/Abstell-/Güteranlagen: feine Kontur auf der Seite, wo sie liegen
    if st.get("yard_n", 0) >= 8:
        side = st["yard_side"] * flip * -1 or 1
        o0 = (max(offs.values()) if side > 0 else min(offs.values())) + side * (GAP / 2 + 14)
        w_ = 22
        c0 = p0 + nv * o0; c1 = p1 + nv * o0; c2 = p1 + nv * (o0 + side * w_); c3 = p0 + nv * (o0 + side * w_)
        out.append('<path d="M{:.1f},{:.1f}L{:.1f},{:.1f}L{:.1f},{:.1f}L{:.1f},{:.1f}Z" fill="#f4f4f4" stroke="{}" stroke-width="0.9" stroke-dasharray="3 2"/>'.format(*c0, *c1, *c2, *c3, GR))
        cm = (c0 + c2) / 2
        rot = -math.degrees(math.atan2(-u[1], u[0])) if abs(u[1]) < 0.9 else -90
        text(cm[0], cm[1] + 3.5, f"Anlage · {st['yard_n']} Gl.", 9.5, color="#666", rot=rot if abs(rot) < 91 else rot - 180)
        yard_extra = w_ + 14
    else:
        yard_extra = 0
    # Name neben dem Bahnhofskörper (Begrenzungsrechteck), auf der Seite ohne Anlage
    body = [pa, pb] + [pa + u * run_max + nv * o for o in (min(offs.values()) - GAP, max(offs.values()) + GAP)] \
         + [pb - u * run_max + nv * o for o in (min(offs.values()) - GAP, max(offs.values()) + GAP)]
    xs = [p[0] for p in body]; ys = [p[1] for p in body]; cy = (min(ys) + max(ys)) / 2; cx = (min(xs) + max(xs)) / 2
    yard_dir = None
    if st.get("yard_n", 0) >= 8:
        yv = nv * (st["yard_side"] * flip * -1 or 1); yard_dir = yv
    if abs(u[0]) > 0.9:          # waagrechter Bahnhof: Name unter (oder über) dem Körper
        below = not (yard_dir is not None and yard_dir[1] > 0)
        text(cx, (max(ys) + 24) if below else (min(ys) - 12), n["name"], 19, weight=700)
    else:                        # senkrecht/schräg: Name rechts (oder links)
        right = not (yard_dir is not None and yard_dir[0] > 0)
        text((max(xs) + 12) if right else (min(xs) - 12), cy + 6, n["name"], 19, "start" if right else "end", 700)

# ------------------------------------------------------------------ Abgänge
for i, n in N.items():
    if n["kind"] != "exit": continue
    e = inc[i][0]; ref = e["refs"][0] if e["refs"] else ""
    other = e["b"] if e["a"] == i else e["a"]
    u = P[i] - P[other]; u = u / np.linalg.norm(u)
    town = n.get("town") or ""
    p = P[i] + u * 14
    arrow = "→" if u[0] > 0.3 else ("←" if u[0] < -0.3 else ("↑" if u[1] < 0 else "↓"))
    if abs(u[0]) > 0.3:
        anc = "start" if u[0] > 0 else "end"
        text(p[0], p[1] - 4, f"Linie {ref}", 15, anc)
        text(p[0], p[1] + 15, f"{arrow} {town}" if anc == "end" else f"{town} {arrow}", 15, anc)
    else:
        dy = -22 if u[1] < 0 else 14
        text(p[0], p[1] + dy, f"Linie {ref}", 15)
        text(p[0], p[1] + dy + 18, f"{town} {arrow}", 15)

W = max(p[0] for p in P.values()) + M; H = max(p[1] for p in P.values()) + M
legend = (f'<g transform="translate(40,{H - 120:.0f})" font-size="12" fill="#444">'
          f'<path d="M0,0H40" stroke="{G}" stroke-width="2.6"/><text x="50" y="4">Streckengleis (je Linie ein Gleis)</text>'
          f'<path d="M0,20H40" stroke="{G}" stroke-width="5.5"/><text x="50" y="24">Perron (Ortskenntnis)</text>'
          f'<path d="M0,40H40" stroke="#7fbf96" stroke-width="5.5"/><text x="50" y="44">Perron (Annahme, zu prüfen)</text>'
          f'<rect x="0" y="54" width="40" height="12" fill="#f4f4f4" stroke="{GR}" stroke-width="0.9" stroke-dasharray="3 2"/>'
          f'<text x="50" y="64">Neben-, Abstell- und Güteranlagen (Detail im Spurplan)</text></g>')
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
       f'font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif"><rect width="100%" height="100%" fill="#fff"/>'
       + "".join(out) + legend +
       f'<text x="40" y="60" font-size="34" font-weight="700" fill="{G}">{TITLE}</text>'
       f'<text x="{W - 40:.0f}" y="{H - 24:.0f}" font-size="12" text-anchor="end" fill="#888">'
       f'Gleisdaten © OpenStreetMap-Mitwirkende (ODbL) · schematisch, nicht massstäblich</text></svg>')
open(OUTF, "w").write(svg)
print("ok", round(W), round(H))
