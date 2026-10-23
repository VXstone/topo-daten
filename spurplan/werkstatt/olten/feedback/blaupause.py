"""
Blaupausen-Bahnhof: Werkzeugkasten aller Zeichenelemente der Spurpläne (Designentscheide an einem Ort).
Gleiche Masse wie spurplan_schema.py: Ebenenabstand 24 px, Weichen 60°, Ausrundung 7 px,
Hauptgleis 3.6 px grün, Nebengleis 1.6 px schwarz, DKW-Standard 12/3/2.2 bzw. 9/2.2/1.4.
  python3 feedback/blaupause.py  -> feedback/blaupause.svg
Jedes Feld hat eine Kennung (A1, B2, ...), damit Hinweise sich darauf beziehen können.
"""
import math, os, re
G, K, BR = "#00862f", "#111", "#9a5b1e"
HW, NW = 3.6, 1.6
LANE = 24; T60 = math.tan(math.radians(60)); R = 7.0
TW, TH = 390, 170           # Feldgrösse
COLS = 4
out = []

def rund(pts, r=R):
    pts = [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 0.1]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[i + 1]
        l1, l2 = math.dist(pts[i - 1], pts[i]), math.dist(pts[i], pts[i + 1])
        rr = min(r, l1 / 2, l2 / 2)
        p_ = (bx + (ax - bx) * rr / l1, by + (ay - by) * rr / l1); q_ = (bx + (cx - bx) * rr / l2, by + (cy - by) * rr / l2)
        d += f"L{p_[0]:.1f},{p_[1]:.1f}Q{bx:.1f},{by:.1f} {q_[0]:.1f},{q_[1]:.1f}"
    return d + f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
def line(pts, pax=True, col=None, w=None, r=R):
    return f'<path d="{rund(pts, r)}" fill="none" stroke="{col or (G if pax else K)}" stroke-width="{w or (HW if pax else NW)}" stroke-linecap="round" stroke-linejoin="round"/>'
def diag(x, y, dy, dx_sign=1):
    """Endpunkt einer 60°-Schrägen von (x,y) um dy (px, + = nach unten)"""
    return (x + dx_sign * abs(dy) / T60, y + dy)
def dot(x, y, pax=True): return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.5 if pax else 3.2}" fill="{G if pax else K}"/>'
def arrow(x, y, ang, col=K):
    c, s = math.cos(ang), math.sin(ang)
    pts = [(x + 9 * c, y + 9 * s), (x - 4 * s, y + 4 * c), (x + 4 * s, y - 4 * c)]
    return '<path d="M' + "L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + f'Z" fill="{col}"/>'
def stub(x, y, dxs, dys, pax=False, L=26):
    """Weichenpfeil: ausgerundeter Stummel unter 60° mit Pfeil"""
    ex, ey = x + dxs * L * 0.5, y + dys * L * 0.866
    d = f'<path d="M{x - dxs * 6:.1f},{y:.1f}Q{x:.1f},{y:.1f} {x + dxs * 3:.1f},{y + dys * 5.2:.1f}L{ex:.1f},{ey:.1f}" fill="none" stroke="{G if pax else K}" stroke-width="{HW if pax else NW}" stroke-linecap="round"/>'
    return d + arrow(ex, ey, math.atan2(ey - y, ex - x), G if pax else K)
def perron(x0, x1, y): return f'<rect x="{x0:.1f}" y="{y - 4:.1f}" width="{x1 - x0:.1f}" height="8" rx="1.5" fill="{G}"/>'
def nummer(x, y, t, col=G): return (f'<rect x="{x - 13:.1f}" y="{y - 8:.1f}" width="26" height="16" fill="#fff"/>'
                                      f'<text x="{x:.1f}" y="{y + 6.5:.1f}" font-size="19" text-anchor="middle" fill="{col}">{t}</text>')
def text(x, y, t, size=13, col="#555", anc="start", wt=400):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{wt}" text-anchor="{anc}" fill="{col}">{t}</text>'
DKW = {True: (12.0, 3.0, 2.2, G), False: (9.0, 2.2, 1.4, K)}
def klammer(c, a, b, hp):
    L, OFF, W, col = DKW[hp]
    a = (a[0] / math.hypot(*a), a[1] / math.hypot(*a)); b = (b[0] / math.hypot(*b), b[1] / math.hypot(*b))
    bis = (a[0] + b[0], a[1] + b[1]); n = math.hypot(*bis); bis = (bis[0] / n, bis[1] / n)
    def perp(u):
        p = (-u[1], u[0]); return p if p[0] * bis[0] + p[1] * bis[1] > 0 else (-p[0], -p[1])
    half = math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1]))) / 2
    pa, pb = perp(a), perp(b)
    p0 = (c[0] + a[0] * L + pa[0] * OFF, c[1] + a[1] * L + pa[1] * OFF)
    p1 = (c[0] + b[0] * L + pb[0] * OFF, c[1] + b[1] * L + pb[1] * OFF)
    q = (c[0] + bis[0] * OFF / math.sin(half), c[1] + bis[1] * OFF / math.sin(half))
    return f'<path d="M{p0[0]:.1f},{p0[1]:.1f}Q{q[0]:.1f},{q[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}" fill="none" stroke="{col}" stroke-opacity="0.55" stroke-width="{W}" stroke-linecap="round"/>'
# DKW-Varianten mit kleiner Ausrundung direkt auf den Gleisen (Hinweis 14.10.: 10–20 % einer normalen Weiche)
def dkw_rund(c, sgn, hp, t):
    """Ausrundung in den beiden stumpfen Winkeln, direkt auf den Gleisen; t = Tangentenlänge in px"""
    s_ = ""
    for a, b in (((-1, 0), (0.5, 0.866 * sgn)), ((1, 0), (-0.5, -0.866 * sgn))):
        p0 = (c[0] + a[0] * t, c[1] + a[1] * t); p1 = (c[0] + b[0] * t, c[1] + b[1] * t)
        s_ += f'<path d="M{p0[0]:.1f},{p0[1]:.1f}Q{c[0]:.1f},{c[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}" fill="none" stroke="{G if hp else K}" stroke-width="{HW if hp else NW}" stroke-linecap="round"/>'
    return s_
_sw = LANE / math.sin(math.radians(60))      # Länge der Schrägen einer normalen Weiche (eine Ebene)
def dkw(c, sgn, hp):
    """DKW-Symbol am Kreuzungspunkt c einer Waagrechten mit einer 60°-Schrägen; sgn=+1: Schräge von oben links nach unten rechts"""
    # Standard 14.10. (Blaupause E9): kleine Ausrundung auf den Gleisen (10 % einer Weiche) + Klammern
    return dkw_rund(c, sgn, hp, _sw * 0.10) + klammer(c, (-1, 0), (0.5, 0.866 * sgn), hp) + klammer(c, (1, 0), (-0.5, -0.866 * sgn), hp)

tiles = []
BIG = set()
def tile(kenn, titel, body, note=""):
    tiles.append((kenn, titel, body, note))
    if kenn.startswith("F"): BIG.add(kenn)

# ---------------------------------------------------------------- A Gleise
X0, X1 = 30, 360; Y = 85
tile("A1", "Hauptgleis (Personenverkehr)", line([(X0, Y), (X1, Y)]))
tile("A2", "Nebengleis", line([(X0, Y), (X1, Y)], False))
tile("A3", "Schräge steigend (60°)", line([(X0, Y + 36), (120, Y + 36), diag(120, Y + 36, -72), (X1, Y - 36)]))
tile("A4", "Schräge fallend (60°)", line([(X0, Y - 36), (120, Y - 36), diag(120, Y - 36, 72), (X1, Y + 36)]))
tile("A5", "Prellbock / Stumpfgleis", line([(X0, Y - 18), (220, Y - 18)]) + dot(220, Y - 18) + line([(X0, Y + 18), (180, Y + 18)], False) + dot(180, Y + 18, False))
tile("A6", "Gleis verlässt Plan / Nebengleis nicht dargestellt (Pfeil)", line([(X0, Y), (260, Y)], False) + arrow(260, Y, 0))
tile("A7", "Streckenabgang am Rand", line([(X0, Y - 10), (200, Y - 10)]) + line([(X0, Y + 10), (200, Y + 10)])
     + text(208, Y - 4, "Linie 450", 13, G) + text(208, Y + 13, "Bern →", 13, G))
tile("A8", "Seitlicher Abgang (ausgerundet)", line([(X0, Y + 30), (130, Y + 30), diag(130, Y + 30, -80)]) + text(190, Y - 30, "Linie 500", 13, G) + text(190, Y - 15, "Basel ↗", 13, G))
tile("A9", "Meterspur", line([(X0, Y - 12), (X1, Y - 12)], col=BR, w=HW) + line([(X0, Y + 14), (150, Y + 14)], col=BR, w=NW) + nummer(220, Y - 12, "11", BR))

# ---------------------------------------------------------------- B Perrons
def gleise(n, y0=Y - LANE * (0), pax=True, nums=None, x0=X0, x1=X1):
    s = ""
    for i in range(n):
        s += line([(x0, y0 + i * LANE), (x1, y0 + i * LANE)], pax)
    return s
yb = Y - LANE / 2
tile("B1", "Aussenperron oben", gleise(1, Y) + perron(90, 250, Y - 11) + nummer(170, Y, "1"))
tile("B2", "Aussenperron unten", gleise(1, Y) + perron(90, 250, Y + 11) + nummer(170, Y, "2"))
tile("B3", "Mittelperron zwischen zwei Gleisen", gleise(2, yb) + perron(90, 250, yb + LANE / 2) + nummer(170, yb, "2") + nummer(170, yb + LANE, "3"))
tile("B4", "Zwei Aussenperrons", gleise(2, yb) + perron(90, 250, yb - 11) + perron(90, 250, yb + LANE + 11) + nummer(170, yb, "1") + nummer(170, yb + LANE, "2"))
tile("B5", "Gespreizte Gleise mit eigenen Perrons", gleise(1, Y - 24) + gleise(1, Y + 24) + perron(90, 250, Y - 13) + perron(90, 250, Y + 13)
     + nummer(170, Y - 24, "3") + nummer(170, Y + 24, "4"), "Kerzers 3/4: zusätzliche Ebene dazwischen")
tile("B6", "Haltestelle an Doppelspur (Regionalplan)", line([(X0, Y - 5), (X1, Y - 5)]) + line([(X0, Y + 5), (X1, Y + 5)])
     + line([(130, Y - 12), (200, Y - 12)], w=4.2) + line([(130, Y + 12), (200, Y + 12)], w=4.2) + text(165, Y - 20, "Hägendorf", 11, G, "middle"))

# ---------------------------------------------------------------- C Weichen (4 Lagen) + Weiche an Schräge
def weiche(x, y, dxs, dys, pax=True, pax_ast=True, L=90):
    """Hauptgleis durchgehend, Ast unter 60° nach dys (+1 unten / -1 oben), Weichenanfang bei x, Richtung dxs"""
    s = line([(X0, y), (X1, y)], pax)
    p2 = diag(x, y, dys * LANE * 1.0, dxs)
    end = (p2[0] + dxs * L, p2[1])
    s += line([(x - dxs * 20, y), (x, y), p2, end], pax_ast)
    return s
tile("C1", "Weiche rechts, nach unten (von links befahren)", weiche(130, Y - 12, 1, 1))
tile("C2", "Weiche links, nach oben (von links befahren)", weiche(130, Y + 12, 1, -1))
tile("C3", "Weiche nach unten (von rechts befahren)", weiche(200, Y - 12, -1, 1))
tile("C4", "Weiche nach oben (von rechts befahren)", weiche(200, Y + 12, -1, -1))
tile("C5", "Abzweig Nebengleis von Hauptgleis", weiche(130, Y - 12, 1, 1, True, False) + dot(130 + LANE / T60 + 90, Y + 12, False))
tile("C6", "Weichenpfeil (verlässt Plan / nicht dargestellt)", line([(X0, Y), (X1, Y)]) + stub(140, Y, 1, -1) + stub(200, Y, -1, 1))
# Weiche aus einer Schrägen (Kerzers 2/3, Ins Rollbock)
s = line([(X0, Y - 36), (100, Y - 36), diag(100, Y - 36, 72), (X1, Y + 36)])
xc = 100 + 36 / T60
s += line([(xc - 0.1, Y), (xc, Y), (X1, Y)], r=0)
tile("C7", "Gleis zweigt aus der Schrägen ab", s, "Kerzers 2 aus der Schrägen 1→3")
# Weiche auf schräg liegendem Gleis: Gleis 5 fädelt in die Schräge
s = line([(X0, Y - 30), (100, Y - 30), diag(100, Y - 30, 60), (X1, Y + 30)]) + line([(X0, Y), (100 + 30 / T60, Y)])
tile("C8", "Gleis mündet in eine Schräge", s, "Kerzers 5 → Schräge 4–6")

# ---------------------------------------------------------------- D Spurwechsel
ya, yb2 = Y - 12, Y + 12
def zwei(): return line([(X0, ya), (X1, ya)]) + line([(X0, yb2), (X1, yb2)])
def xo(x, y0, y1, dxs=1, pax=True, tail=8):
    p = diag(x, y0, y1 - y0, dxs)
    return line([(x - dxs * tail, y0), (x, y0), p, (p[0] + dxs * tail, y1)], pax)
tile("D1", "Einfacher Spurwechsel (oben → unten)", zwei() + xo(140, ya, yb2))
tile("D2", "Einfacher Spurwechsel (unten → oben)", zwei() + xo(140, yb2, ya))
tile("D3", "Doppelter Spurwechsel mit kleiner Zwischengerade", zwei() + xo(110, yb2, ya) + xo(110 + LANE / T60 + 12, ya, yb2))
tile("D4", "Hosenträger (gekreuzter Spurwechsel)", zwei() + line([(150 - LANE / T60 / 2 - 8, ya), (150 - LANE / T60 / 2, ya), (150 + LANE / T60 / 2, yb2), (150 + LANE / T60 / 2 + 8, yb2)])
     + line([(150 - LANE / T60 / 2 - 8, yb2), (150 - LANE / T60 / 2, yb2), (150 + LANE / T60 / 2, ya), (150 + LANE / T60 / 2 + 8, ya)]))
ys = [Y - 36, Y - 12, Y + 12, Y + 36]
s = "".join(line([(X0, y), (X1, y)]) for y in ys) + line([(90, ys[0]), (100, ys[0]), diag(100, ys[0], 72), (100 + 72 / T60 + 10, ys[3])])
s += dkw((100 + 24 / T60, ys[1]), 1, True) + dkw((100 + 48 / T60, ys[2]), 1, True)
tile("D5", "Spurwechsel über mehrere Gleise (DKW auf den Zwischengleisen)", s)
s = line([(X0, ya), (X1, ya)]) + line([(X0, yb2), (X1, yb2)], False) + xo(140, ya, yb2, 1, False)
tile("D6", "Spurwechsel ins Nebengleis (schwarz)", s)

# ---------------------------------------------------------------- E DKW / Kreuzungen
def kreuz(sgn, hp_h=True, hp_d=False, xc=165):
    s = line([(X0, Y), (X1, Y)], hp_h)
    a = (xc - 48 / T60, Y - 48 * sgn); b = (xc + 48 / T60, Y + 48 * sgn)
    s += line([(a[0] - 10, a[1]), a, b, (b[0] + 10, b[1])], hp_d)
    return s
tile("E1", "DKW an Hauptgleis (Schräge fallend)", kreuz(1) + dkw((165, Y), 1, True))
tile("E2", "DKW an Hauptgleis (Schräge steigend)", kreuz(-1) + dkw((165, Y), -1, True))
tile("E3", "DKW nur Nebengleise", kreuz(1, False, False) + dkw((165, Y), 1, False))
s = line([(X0, Y - 24), (X1, Y - 24)]) + line([(X0, Y + 24), (X1, Y + 24)])
a = (130 - 48 / T60, Y - 48); b = (130 + 48 / T60, Y + 48)
s += line([(a[0] - 26, a[1]), a, b, (b[0] + 26, b[1])], False) + arrow(a[0] - 26, a[1], math.pi) + arrow(b[0] + 26, b[1], 0)
s += dkw((130 - 24 / T60, Y - 24), 1, True) + dkw((130 + 24 / T60, Y + 24), 1, True)
tile("E4", "Zwei DKW auf einer Schrägen", s, "Zofingen West")
tile("E5", "Kreuzung ohne Verbindung", kreuz(1, True, False, 165))
# Über-/Unterführung (Vorschlag): unteres Gleis mit Lücke, oberes Gleis mit Brückenflügeln
def unterf(c, u, under_col=G):
    """c Kreuzungspunkt, u Richtung des oberen Gleises (Einheitsvektor); das untere Gleis ist waagrecht"""
    n = (u[1], -u[0])
    s = f'<path d="M{c[0] - 14:.1f},{c[1]:.1f}H{c[0] + 14:.1f}" stroke="#fff" stroke-width="8"/>'
    for side in (-1, 1):
        q0 = (c[0] - u[0] * 12 + n[0] * side * 6, c[1] - u[1] * 12 + n[1] * side * 6)
        q1 = (c[0] + u[0] * 12 + n[0] * side * 6, c[1] + u[1] * 12 + n[1] * side * 6)
        f0 = (q0[0] - u[0] * 3 + n[0] * side * 3, q0[1] - u[1] * 3 + n[1] * side * 3)
        f1 = (q1[0] + u[0] * 3 + n[0] * side * 3, q1[1] + u[1] * 3 + n[1] * side * 3)
        s += f'<path d="M{f0[0]:.1f},{f0[1]:.1f}L{q0[0]:.1f},{q0[1]:.1f}L{q1[0]:.1f},{q1[1]:.1f}L{f1[0]:.1f},{f1[1]:.1f}" fill="none" stroke="{K}" stroke-width="1.2"/>'
    return s
xc = 195; a_ = (xc - 60 / T60, Y - 60); b_ = (xc + 60 / T60, Y + 60)
s = line([(X0, Y), (X1, Y)]) + unterf((xc, Y), (0.5, 0.866)) + line([(a_[0] - 10, a_[1]), a_, b_, (b_[0] + 10, b_[1])])
tile("E6", "Über-/Unterführung (Vorschlag)", s, "oben durchgehend + Brückenflügel, unten unterbrochen")
# Tunnelportal (Vorschlag): durchgehende Linie, Portale nach aussen geöffnet
s = line([(X0, Y), (X1, Y)])
for x_, d_ in ((120, -1), (220, 1)):
    s += f'<path d="M{x_ + d_ * 5},{Y - 10}L{x_},{Y - 7}L{x_},{Y + 7}L{x_ + d_ * 5},{Y + 10}" fill="none" stroke="{K}" stroke-width="1.4"/>'
tile("E7", "Tunnel mit Portalen (Vorschlag)", s, "Hauenstein-Basistunnel im Regionalplan")
# Rollbock / Spurwechsel Normal-/Meterspur
s = line([(X0, Y + 30), (X1, Y + 30)], False)
p0 = (90, Y + 30); m = diag(90, Y + 30, -30); t = diag(90, Y + 30, -60)
s += line([(p0[0] - 10, p0[1]), p0, m], False, r=R) + line([m, t, (X1, t[1])], col=BR, w=NW) + dot(*m, False)
tile("E8", "Übergang Normal-/Meterspur (Rollbock)", s, "Ins: in der Schrägen, ohne Knick")

# ---------------------------------------------------------------- F Zusammensetzungen
def bf(kenn, titel, parts, note=""):
    tile(kenn, titel, "".join(parts), note)
# F1 Kreuzungsbahnhof: 2 Gleise, Mittelperron, Weichen an beiden Enden
y1, y2 = Y - 12, Y + 12
bf("F1", "Kreuzungsbahnhof eingleisig", [line([(X0, Y), (70, Y), diag(70, Y, -12), (240, y1), diag(240, y1, 12, 1), (X1, Y)]),
    line([(X0, Y), (70, Y), diag(70, Y, 12), (240, y2), diag(240, y2, -12, 1), (X1, Y)]),
    perron(110, 210, Y), nummer(160, y1, "1"), nummer(160, y2, "2")])
# F2 Überholbahnhof Doppelspur mit Überholgleisen aussen
yo, yu = Y - 12, Y + 12
bf("F2", "Überholbahnhof (Doppelspur, Überholgleise aussen)", [line([(X0, yo), (X1, yo)]), line([(X0, yu), (X1, yu)]),
    line([(60, yo), diag(60, yo, -24), (240, yo - 24), diag(240, yo - 24, 24, 1)]), line([(60, yu), diag(60, yu, 24), (240, yu + 24), diag(240, yu + 24, -24, 1)]),
    perron(110, 210, yo - 12), perron(110, 210, yu + 12), nummer(160, yo - 24, "1"), nummer(160, yo, "2"), nummer(160, yu, "3"), nummer(160, yu + 24, "4"),
    xo(268, yu, yo), xo(268 + LANE / T60 + 12, yo, yu)])      # doppelter Spurwechsel (Hinweis 15.10.: in F2 auch)
# F3 Abzweigbahnhof (Keil): Strecke B zweigt unten ab
bf("F3", "Abzweigbahnhof (Keil)", [line([(X0, Y - 24), (X1, Y - 24)]), line([(X0, Y), (X1, Y)]),
    line([(60, Y), diag(60, Y, 24), (190, Y + 24), diag(190, Y + 24, 50)]), perron(90, 180, Y + 12), nummer(130, Y, "2"), nummer(130, Y + 24, "3"),
    text(225, Y + 70, "Linie 256", 12, G), text(225, Y + 84, "Murten →", 12, G)])
# F4 Fächer: vier parallele Gleise biegen gemeinsam ab (innerstes zuerst), zwei Gleise gehen als Bündel darunter durch
ys4 = [Y - 75, Y - 51, Y - 27, Y - 3]
s = ""; yBs = [Y + 45, Y + 69]
xk_ = [300 - (y - ys4[0]) / T60 for y in ys4]
ye = yBs[-1] + 22
for y, xk in zip(ys4, xk_): s += line([(X0, y), (xk, y), diag(xk, y, ye - y, 1)])
u = (0.5, 0.866); n = (0.866, -0.5)
for yB in yBs:
    xc = [xk + (yB - y) / T60 for y, xk in zip(ys4, xk_)]
    s += line([(X0, yB), (min(xc) - 13, yB)]) + line([(max(xc) + 13, yB), (700, yB)])
# Brückenflügel aussen am Bündel, über beide unteren Gleise
for idx, side in ((0, 1), (3, -1)):
    y, xk = ys4[idx], xk_[idx]
    pa = (xk + (yBs[0] - 14 - y) / T60, yBs[0] - 14); pb = (xk + (yBs[-1] + 14 - y) / T60, yBs[-1] + 14)
    o_ = (n[0] * side * 7, n[1] * side * 7)
    q0 = (pa[0] + o_[0], pa[1] + o_[1]); q1 = (pb[0] + o_[0], pb[1] + o_[1])
    f0 = (q0[0] - u[0] * 4 + n[0] * side * 4, q0[1] - u[1] * 4 + n[1] * side * 4); f1 = (q1[0] + u[0] * 4 + n[0] * side * 4, q1[1] + u[1] * 4 + n[1] * side * 4)
    s += f'<path d="M{f0[0]:.1f},{f0[1]:.1f}L{q0[0]:.1f},{q0[1]:.1f}L{q1[0]:.1f},{q1[1]:.1f}L{f1[0]:.1f},{f1[1]:.1f}" fill="none" stroke="{K}" stroke-width="1.3"/>'
s += xo(440, yBs[1], yBs[0]) + xo(440 + LANE / T60 + 12, yBs[0], yBs[1])      # doppelter Spurwechsel (Hinweis 15.10.)
s += text(470, Y - 40, "Linie 540 Aarau ↘", 13, G) + text(560, Y + 38, "Linie 500 Basel →", 13, G)
tile("F4", "Fächer: vier Gleise biegen gemeinsam ab, zwei Gleise darunter durch", s, "Olten Nord: Aarauer Gleise über die Basler Gleise – eine Brücke für das ganze Bündel (Vorschlag)")
# F5 Kopfgleis mit Perron und Umfahrung
bf("F5", "Stumpfgleis mit Perron", [line([(X0, Y), (X1, Y)]), line([(80, Y), diag(80, Y, -24), (240, Y - 24)]), dot(240, Y - 24), perron(130, 230, Y - 35), nummer(180, Y - 24, "11")])
# F6 Anschlussgleis mit DKW und Weichenpfeilen
s = line([(X0, Y - 12), (X1, Y - 12)]) + line([(X0, Y + 12), (X1, Y + 12)])
a = (150 - 48 / T60, Y - 36); b = (150 + 48 / T60, Y + 60)
s += line([(X0 + 20, Y - 36), a, diag(*a, 96), (b[0] + 40, Y + 60)], False) + dkw((150 - 24 / T60 + 0.0, Y - 12), 1, True) + dkw((150, Y + 12), 1, True)
s += stub(260, Y - 12, 1, -1)
tile("F6", "Abstellgruppe: Schräge durch zwei Hauptgleise (DKW) + Pfeil", s)

# F7 Spurwechsel über mehrere Gleise als Weichen hintereinander (Treppe aus einfachen Spurwechseln)
ys = [Y - 36, Y - 12, Y + 12, Y + 36]
s = "".join(line([(X0, y), (X1 + 100, y)]) for y in ys)
for i_ in range(3):
    s += xo(140 + i_ * (LANE / T60 + 14), ys[i_], ys[i_ + 1])
tile("F7", "Spurwechsel über mehrere Gleise: Weichen hintereinander", s, "Alternative zu D5")
# ---------------------------------------------------------------- Ausgabe
small = [t for t in tiles if t[0] not in BIG]; big = [t for t in tiles if t[0] in BIG]
TW2, TH2 = 2 * TW, 250
rows = (len(small) + COLS - 1) // COLS; rows2 = (len(big) + 1) // 2
W, H = COLS * TW + 40, rows * TH + rows2 * TH2 + 140
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">',
     f'<rect width="100%" height="100%" fill="#fff"/>',
     text(20, 36, "Blaupausen-Bahnhof – Werkzeugkasten der Spurplan-Zeichen", 22, G, wt=700),
     text(20, 58, "Masse wie im Spurplan: Ebenenabstand 24 px · Weichen 60° · Ausrundung 7 px · Hauptgleis grün 3.6 · Nebengleis schwarz 1.6 · Kennung (A1 …) für Hinweise", 12)]
def put(cx, cy, w, h, kenn, titel, body, note, dy=6):
    o.append(f'<g transform="translate({cx},{cy})">')
    o.append(f'<rect x="0" y="0" width="{w - 10}" height="{h - 10}" rx="6" fill="none" stroke="#ddd"/>')
    o.append(text(10, 18, f"{kenn}", 13, G, wt=700) + text(14 + 9 * len(kenn), 18, titel, 12, "#333"))
    if note: o.append(text(10, h - 18, note, 10, "#888"))
    _el = re.findall(r'<path[^>]*/>|<circle[^>]*/>|<rect[^>]*/>|<text[^>]*>.*?</text>|<g[^>]*>|</g>', body)
    if "".join(_el) == body and "<g" not in body:          # schwarz hinter grün
        body = "".join([e for e in _el if 'stroke="#111"' in e] + [e for e in _el if 'stroke="#111"' not in e])
    o.append(f'<g transform="translate(0,{dy})">{body}</g></g>')
for i, (kenn, titel, body, note) in enumerate(small):
    put(20 + (i % COLS) * TW, 75 + (i // COLS) * TH, TW, TH, kenn, titel, body, note)
y2 = 75 + rows * TH + 30
o.append(text(20, y2 - 8, "Beispielzusammensetzungen", 16, G, wt=700))
for i, (kenn, titel, body, note) in enumerate(big):
    put(20 + (i % 2) * TW2, y2 + (i // 2) * TH2, TW2, TH2, kenn, titel, f'<g transform="translate(200,30)">{body}</g>' if kenn != "F4" else f'<g transform="translate(0,30)">{body}</g>', note)
o.append("</svg>")
here = os.path.dirname(os.path.abspath(__file__))
open(os.path.join(here, "blaupause.svg"), "w").write("\n".join(o))
print(len(tiles), "Felder")
