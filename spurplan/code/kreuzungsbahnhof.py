"""Kreuzungsbahnhof für den Regionalplan (27.10.2026, Kerzers, Hinweis eojeak D. Eckenstein):
zwei Linien kreuzen sich im Bahnhof; jede Linie ist eine eigene gerade Achse, die beiden Achsen kreuzen sich unter 60°.

  python3 kreuzungsbahnhof.py <bahnhof>          (im Arbeitsordner, nach der normalen Kette)

Liest <bahnhof>_override.json «kreuzungsbahnhof» und die Anschlüsse aus <bahnhof>_ports.json (Ort, Linie, Richtung, Way,
Koordinaten der Abgänge aus OSM) und schreibt <bahnhof>_bare.svg und <bahnhof>_ports.json neu:
  achsen        [{ref, orte: [Ort am Winkel, Ort gegenüber], winkel: Grad (0 = rechts, 60/120 = schräg oben),
                  gleise: [durchgehend, …], arm: Ort des Astes mit den Perrons, seite: +1 / -1 (Fächer im / gegen
                  den Uhrzeigersinn neben dem durchgehenden Gleis)}, …]   (zwei Achsen, Winkelabstand 60°)
  verbindungen  [[Ort, Ort], …]  Verbindungskurven zwischen zwei Ästen, die 120° auseinander liegen
Die Perrongleise liegen am Ast «arm» ihrer Achse: das erste Gleis durchgehend, die übrigen daneben (60°-Weichen,
Fächer), Perrons aussen am ersten und am letzten Gleis wie im Detailplan. Die Kreuzung liegt in der Mitte.
Ein Ast unter 0°/180° wird ein Längsabgang, unter ±60°/±120° ein seitlicher Abgang (Regionalplan).
"""
import json, math, sys

b = sys.argv[1]
K = json.load(open(f"{b}_override.json"))["kreuzungsbahnhof"]
P0 = json.load(open(f"{b}_ports.json"))
nach_ort = {p["town"]: p for p in P0["ports"]}
G, LANE, R = "#00862f", 24.0, 7.0
D60 = LANE / math.tan(math.radians(60))
ARM, ARM_KURZ, DV, S0 = 420.0, 170.0, 70.0, 130.0      # Ast mit Perrons / ohne, Verbindungskurve, erste Weiche
def u(deg): return (math.cos(math.radians(deg)), -math.sin(math.radians(deg)))
C = (0.0, 0.0)
def pt(s, n, ud, nd): return (C[0] + s * ud[0] + n * nd[0], C[1] + s * ud[1] + n * nd[1])

def rund(pts, r=R):
    """Polylinie mit Ausrundung an den Ecken (Q)"""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        a, p, c = pts[i - 1], pts[i], pts[i + 1]
        la, lc = math.dist(a, p), math.dist(p, c); ra = min(r, la / 2); rc = min(r, lc / 2)
        p1 = (p[0] + (a[0] - p[0]) * ra / la, p[1] + (a[1] - p[1]) * ra / la)
        p2 = (p[0] + (c[0] - p[0]) * rc / lc, p[1] + (c[1] - p[1]) * rc / lc)
        d += f"L{p1[0]:.1f},{p1[1]:.1f}Q{p[0]:.1f},{p[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d + f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"

AST = {}
for ax in K["achsen"]:
    AST[ax["orte"][0]] = ax["winkel"] % 360; AST[ax["orte"][1]] = (ax["winkel"] + 180) % 360
LANG = {o: (ARM if any(o == ax["arm"] for ax in K["achsen"]) else ARM_KURZ) for o in AST}
paths, rects, texts, ext = [], [], [], []
for o, dg in AST.items():                          # Streckengleis jedes Astes bis zur Mitte
    e = pt(LANG[o], 0, u(dg), (0, 0)); paths.append([C, e]); ext += [C, e]
for ax in K["achsen"]:
    ud = u(AST[ax["arm"]]); sg = ax.get("seite", 1)
    nd = (-ud[1] * sg, ud[0] * sg)
    s0, s1 = S0, ARM - 60.0; k = len(ax["gleise"]) - 1
    if k:
        paths.append([pt(s0, 0, ud, nd), pt(s0 + k * D60, k * LANE, ud, nd), pt(s1 - k * D60, k * LANE, ud, nd), pt(s1, 0, ud, nd)])
        for j in range(1, k):                      # mittlere Gleise zweigen vom Fächer ab
            paths.append([pt(s0 + j * D60, j * LANE, ud, nd), pt(s1 - j * D60, j * LANE, ud, nd)])
    sm = (s0 + s1) / 2; hl = 60.0
    for n_ in (-11.0, k * LANE + 11.0):            # Perrons aussen am ersten und letzten Gleis
        q = [pt(sm - hl, n_ - 4, ud, nd), pt(sm + hl, n_ - 4, ud, nd), pt(sm + hl, n_ + 4, ud, nd), pt(sm - hl, n_ + 4, ud, nd)]
        rects.append(q); ext += q
    for j, g in enumerate(ax["gleise"]):
        texts.append(pt(sm + (j % 2) * 34 - 17, j * LANE, ud, nd) + (g,))
kurven = []
for a, c in K.get("verbindungen", []):
    p1, p2 = pt(DV, 0, u(AST[a]), (0, 0)), pt(DV, 0, u(AST[c]), (0, 0)); kurven.append((p1, p2))
# in positive Koordinaten verschieben
xs = [x for x, y in ext]; ys = [y for x, y in ext]; ox, oy = 40 - min(xs), 40 - min(ys)
T = lambda p: (p[0] + ox, p[1] + oy)
W, H = max(xs) + ox + 40, max(ys) + oy + 40
d_ = " ".join(rund([T(p) for p in pl]) for pl in paths)
for p1, p2 in kurven:
    a_, c_, m_ = T(p1), T(p2), T(C); d_ += f" M{a_[0]:.1f},{a_[1]:.1f}Q{m_[0]:.1f},{m_[1]:.1f} {c_[0]:.1f},{c_[1]:.1f}"
ports = []
for o, dg in AST.items():
    p = dict(nach_ort[o]); e = T(pt(LANG[o], 0, u(dg), (0, 0)))
    p["x"], p["y"] = round(e[0], 1), round(e[1], 1)
    if dg in (0, 180): p.update(kind="edge", dx=1 if dg == 0 else -1, dy=0)
    else: p.update(kind="side", dx=1 if dg in (60, 300) else -1, dy=-1 if dg in (60, 120) else 1)
    ports.append(p)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">',
       '<rect width="100%" height="100%" fill="#fff"/>',
       f'<g fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="{d_}" stroke="{G}" stroke-width="3.6"/></g>']
svg += ['<path d="M' + "L".join(f"{T(p)[0]:.1f},{T(p)[1]:.1f}" for p in q) + f'Z" fill="{G}"/>' for q in rects]
for x, y, g in texts:
    x, y = T((x, y))
    svg.append(f'<rect x="{x - 13:.1f}" y="{y - 8:.1f}" width="26" height="16" fill="#fff"/>')
    svg.append(f'<text x="{x:.1f}" y="{y + 6.5:.1f}" font-size="19" text-anchor="middle" fill="{G}">{g}</text>')
svg.append("</svg>")
open(f"{b}_bare.svg", "w").write("\n".join(svg))
json.dump(dict(P0, ports=ports, W=W, H=H, x_lo=40.0, x_hi=W - 40, y_lo=40.0, y_hi=H - 40),
          open(f"{b}_ports.json", "w"), ensure_ascii=False)
print(f"Kreuzungsbahnhof {b}: Achsen " + ", ".join(f"{ax['ref']} {ax['winkel']}°" for ax in K["achsen"])
      + f", {len(ports)} Anschlüsse, {W:.0f}×{H:.0f} px")
