"""
Netzplan aus eingebetteten Spurplänen (Prinzip Dreieck Kerzers–Ins–Murten, automatisch).

Eingaben:  <name>_topologie.json (netz_topologie.py), je Bahnhof <slug>_bare.svg + <slug>_ports.json
           (spurplan_schema.py --bare), optional <slug>_override.json, region_lines.json
Ablauf
 1. Hauptknoten = Bahnhöfe mit Spurplan, Abzweige, Abgänge. Halte und kleine Bahnhöfe ohne eigenen
    Plan (oder deren Plan einen grösseren überdeckt) liegen auf den Strecken.
 2. Strecken = Ketten von Kanten zwischen Hauptknoten.
 3. Lage: geografisch × Massstab, dann Überlappungen der Spurplan-Kästen auflösen (schieben).
 4. Anschlüsse zuordnen: Streckenrichtung am Bahnhof ↔ Peilung der Spurplan-Anschlüsse.
 5. Strecken zeichnen: 60°-Verbinder (0/60/90/120°), je Gleis eine Linie; Halte als Perronbalken,
    Kreuzungsstellen als Ausweiche.
Aufruf: python3 netz_spurplaene.py olten_region "Region Olten" ausgabe.svg
"""
import json, math, sys, os, re, unicodedata, collections
import numpy as np
from shapely.geometry import LineString, Point, box

NAME, TITLE, OUTF = sys.argv[1], sys.argv[2], sys.argv[3]
CFG = dict(S=0.42,            # Massstab der Spurpläne
           K=0.20,            # px je Meter für die geografische Grundlage
           gap=40,            # Mindestabstand zwischen Spurplan-Kästen [px]
           tg=8.0,            # Gleisabstand auf der Strecke [px]
           stub=18, R=9, merge_station_m=1300)
G, BK, GR = "#00862f", "#111", "#888"
TAN60 = math.tan(math.radians(60))
T = json.load(open(f"{NAME}_topologie.json"))
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")

nodes = {n["id"]: dict(n) for n in T["nodes"]}
edges = [dict(e) for e in T["edges"]]
# ------------------------------------------------------------------ 1. Hauptknoten
for n in nodes.values():
    n["inset"] = None
    if n["kind"] == "station" and os.path.exists(slug(n["name"]) + "_ports.json"):
        n["inset"] = slug(n["name"])
# Bahnhof, dessen Plan von einem grösseren Nachbarplan überdeckt wird -> wie Halt behandeln
def nsw(n): return len(json.load(open(n["inset"] + "_ports.json"))["ports"])
for a in nodes.values():
    if not a["inset"]: continue
    for b in nodes.values():
        if b is a or not b["inset"]: continue
        if math.dist((a["x"], a["y"]), (b["x"], b["y"])) < CFG["merge_station_m"]:
            wa = json.load(open(a["inset"] + "_ports.json"))["W"]; wb = json.load(open(b["inset"] + "_ports.json"))["W"]
            if (len(json.load(open(a["inset"] + "_ports.json"))["ports"]), wa) < (len(json.load(open(b["inset"] + "_ports.json"))["ports"]), wb):
                a["covered_by"] = b["id"]
for n in nodes.values():
    if n.get("covered_by") is not None: n["inset"] = None; n["kind"] = "halt"
    if n["kind"] == "station" and not n["inset"]: n["kind"] = "halt"
MAJOR = {i for i, n in nodes.items() if n["inset"] or n["kind"] in ("junction", "exit", "end")}
# Abzweige im Bereich eines Spurplans gehören zum Bahnhof
for j in [i for i in MAJOR if nodes[i]["kind"] == "junction"]:
    for s in [i for i in MAJOR if nodes[i]["inset"]]:
        if math.dist((nodes[j]["x"], nodes[j]["y"]), (nodes[s]["x"], nodes[s]["y"])) < 700:
            for e in edges:
                if e["a"] == j: e["a"] = s
                if e["b"] == j: e["b"] = s
            MAJOR.discard(j); break
edges = [e for e in edges if e["a"] != e["b"]]
inc = collections.defaultdict(list)
for e in edges:
    inc[e["a"]].append(e); inc[e["b"]].append(e)
# Abzweige mit nur zwei Anschlüssen sind keine Hauptknoten
for j in [i for i in MAJOR if nodes[i]["kind"] == "junction" and len(inc[i]) <= 2]:
    MAJOR.discard(j); nodes[j]["kind"] = "via"

# ------------------------------------------------------------------ 2. Strecken (Ketten)
routes, used = [], set()
for m in MAJOR:
    for e in inc[m]:
        if id(e) in used: continue
        chain, cur, nodes_seq = [e], m, [m]
        used.add(id(e))
        nxt = e["b"] if e["a"] == m else e["a"]
        while nxt not in MAJOR:
            nodes_seq.append(nxt)
            cand = [f for f in inc[nxt] if id(f) not in used]
            if not cand: break
            f = cand[0]; used.add(id(f)); chain.append(f)
            nxt = f["b"] if f["a"] == nxt else f["a"]
        nodes_seq.append(nxt)
        geom = []
        c0 = m
        for f in chain:
            g = f["geom"] if f["a"] == c0 else f["geom"][::-1]
            geom += g; c0 = f["b"] if f["a"] == c0 else f["a"]
        routes.append(dict(a=m, b=nxt, seq=nodes_seq, edges=chain, geom=geom,
                           tracks=max(f["tracks"] for f in chain), refs=sorted({r for f in chain for r in f["refs"]}),
                           length=sum(f["length"] for f in chain)))
print("Hauptknoten:", collections.Counter(nodes[i]["kind"] if not nodes[i]["inset"] else "spurplan" for i in MAJOR), " Strecken:", len(routes))

# ------------------------------------------------------------------ 3. Lage
S, K = CFG["S"], CFG["K"]
pos, size, PORTS = {}, {}, {}
for i in MAJOR:
    n = nodes[i]; pos[i] = np.array([n["x"] * K, -n["y"] * K])
    if n["inset"]:
        P = json.load(open(n["inset"] + "_ports.json")); PORTS[i] = P
        w = (P["x_hi"] - P["x_lo"] + 60) * S; h = (P["y_hi"] - P["y_lo"] + 40) * S
        size[i] = (w, h)
    else: size[i] = (24, 24)
def overlap(i, j):
    (wi, hi), (wj, hj) = size[i], size[j]; d = pos[j] - pos[i]
    ox = (wi + wj) / 2 + CFG["gap"] - abs(d[0]); oy = (hi + hj) / 2 + CFG["gap"] - abs(d[1])
    return ox, oy, d
ids = sorted(MAJOR)
for it in range(400):
    moved = 0
    for a_ in range(len(ids)):
        for b_ in range(a_ + 1, len(ids)):
            i, j = ids[a_], ids[b_]
            ox, oy, d = overlap(i, j)
            if ox > 0 and oy > 0:
                # entlang der kleineren Eindringtiefe trennen, Reihenfolge beibehalten
                if ox / max(abs(d[0]), 1) < oy / max(abs(d[1]), 1) or oy > ox * 3:
                    s_ = 1 if d[0] >= 0 else -1; pos[i][0] -= s_ * ox / 2; pos[j][0] += s_ * ox / 2
                else:
                    s_ = 1 if d[1] >= 0 else -1; pos[i][1] -= s_ * oy / 2; pos[j][1] += s_ * oy / 2
                moved += 1
    if not moved: break
print("Überlappungen aufgelöst nach", it, "Durchläufen")

# ------------------------------------------------------------------ 4. Anschlüsse zuordnen
def route_bearing(r, at):
    """Geografische Richtung der Strecke beim Verlassen von Knoten 'at' (Grad, Osten=0)."""
    g = r["geom"] if r["a"] == at else r["geom"][::-1]
    p0 = np.array(g[0]); L = 0; q = p0
    for p in g[1:]:
        L += math.dist(q, p); q = np.array(p)
        if L > 500: break
    return math.degrees(math.atan2(q[1] - p0[1], q[0] - p0[0])) % 360
def adiff(a, b): return abs((a - b + 180) % 360 - 180)
assign = {}
for i in [i for i in MAJOR if nodes[i]["inset"]]:
    P = PORTS[i]["ports"]
    rs = [(r, route_bearing(r, i)) for r in routes if i in (r["a"], r["b"])]
    taken = set()
    # Strecken mit klarer Richtung zuerst
    for r, br in sorted(rs, key=lambda t: min([adiff(t[1], p["bearing"]) for p in P] or [999])):
        cand = sorted(((adiff(br, p["bearing"]) + (0 if p["ref"] in r["refs"] else 15), k) for k, p in enumerate(P)
                       if k not in taken), key=lambda t: t[0])
        cand = [c for c in cand if c[0] < 55]
        if not cand: assign[(id(r), i)] = []; continue
        best = cand[0][0]
        grp = [k for sc, k in cand if sc < best + 25 and P[k]["pax"] == P[cand[0][1]]["pax"]][:max(r["tracks"], 1) + 2]
        for k in grp: taken.add(k)
        assign[(id(r), i)] = grp
    unused = [k for k in range(len(P)) if k not in taken]
    if unused: print(f"  {nodes[i]['name']}: Anschlüsse ohne Strecke {[(P[k]['ref'], round(P[k]['bearing'])) for k in unused]}")

def inset_tf(i):
    P = PORTS[i]; cx = (P["x_lo"] + P["x_hi"]) / 2; cy = (P["y_lo"] + P["y_hi"]) / 2
    return pos[i][0] - cx * S, pos[i][1] - cy * S
def port_pts(i, ks):
    tx, ty = inset_tf(i); P = PORTS[i]["ports"]; out = []
    for k in ks:
        p = P[k]; v = np.array([p["dx"], p["dy"] * TAN60 if p["kind"] == "side" else 0.0]); v = v / np.linalg.norm(v)
        if p["kind"] == "side": v = np.array([p["dx"] * 0.5, p["dy"] * 0.866])
        out.append((np.array([tx + p["x"] * S, ty + p["y"] * S]), v, p["pax"]))
    return out

# ------------------------------------------------------------------ 5. Zeichnen
out = []
def path(pts, color=G, w=2.4):
    pts = [np.array(p, float) for p in pts]
    clean = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - clean[-1]) > 0.3: clean.append(p)
    pts = clean
    if len(pts) < 2: return
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for k in range(1, len(pts) - 1):
        p0, p1, p2 = pts[k - 1], pts[k], pts[k + 1]
        l1, l2 = np.linalg.norm(p1 - p0), np.linalg.norm(p2 - p1)
        r = min(CFG["R"], l1 / 2, l2 / 2); a = p1 - (p1 - p0) / l1 * r; b = p1 + (p2 - p1) / l2 * r
        d += f"L{a[0]:.1f},{a[1]:.1f}Q{p1[0]:.1f},{p1[1]:.1f} {b[0]:.1f},{b[1]:.1f}"
    d += f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
def text(x, y, t, size=14, anchor="middle", weight=400, color=G):
    out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}">{t}</text>')
DIRS = [np.array([math.cos(math.radians(a)), -math.sin(math.radians(a))]) for a in (0, 60, 90, 120, 180, 240, 270, 300)]
def turn(u, v): return math.degrees(math.acos(max(-1, min(1, float(u @ v)))))
def connector(A, a, B, b):
    """Weg von A (Austrittsrichtung a) nach B (Austrittsrichtung b, zeigt von B weg) mit erlaubten Richtungen."""
    st = CFG["stub"]; A1 = A + a * st; B1 = B + b * st
    best = None
    d = B1 - A1
    if np.linalg.norm(d) < 1e-6: return [A, B]
    for u in DIRS:
        # gerade
        if abs(u[0] * d[1] - u[1] * d[0]) < 1e-6 * np.linalg.norm(d) and u @ d > 0:
            sc = turn(a, u) * 3 + turn(u, -b) * 3 + np.linalg.norm(d) * 0.01
            if best is None or sc < best[0]: best = (sc, [A, A1, B1, B])
        for v in DIRS:
            M = np.array([u, -v]).T
            if abs(np.linalg.det(M)) < 1e-6: continue
            t, s = np.linalg.solve(M, d)
            if t < 0 or s < 0: continue
            C = A1 + u * t
            sc = (turn(a, u) ** 1.5 + turn(u, v) ** 1.5 + turn(v, -b) ** 1.5) * 0.1 + (t + s) * 0.01
            if turn(a, u) > 90 or turn(v, -b) > 90 or turn(u, v) > 90: sc += 1e4
            if best is None or sc < best[0]: best = (sc, [A, A1, C, B1, B])
    return best[1]

# Spurpläne einbetten
for i in [i for i in MAJOR if nodes[i]["inset"]]:
    svg = open(nodes[i]["inset"] + "_bare.svg").read()
    body = re.sub(r"^.*?<svg[^>]*>", "", svg, flags=re.S).replace("</svg>", "")
    body = body.replace('<rect width="100%" height="100%" fill="#fff"/>', "")
    body = re.sub(r'stroke-width="([\d.]+)"', lambda m: f'stroke-width="{max(float(m.group(1)) * 0.75 / S, 1.0 / S):.2f}"', body)
    tx, ty = inset_tf(i)
    out.append(f'<g transform="translate({tx:.1f},{ty:.1f}) scale({S})">{body}</g>')
    P = PORTS[i]
    text(pos[i][0], ty + (P["y_lo"] - 18) * S, nodes[i]["name"], 17, weight=700)

def offset_poly(pts, o):
    """Parallele Linie im Abstand o (links positiv) mit Gehrung an den Knicken."""
    pts = [p for k_, p in enumerate(pts) if k_ == 0 or np.linalg.norm(p - pts[k_ - 1]) > 0.3]
    if len(pts) < 2 or abs(o) < 1e-9: return pts
    nrm = []
    for p, q in zip(pts, pts[1:]):
        u = (q - p) / np.linalg.norm(q - p); nrm.append(np.array([-u[1], u[0]]))
    res = [pts[0] + nrm[0] * o]
    for k_ in range(1, len(pts) - 1):
        m = nrm[k_ - 1] + nrm[k_]; m = m / (np.linalg.norm(m) or 1)
        res.append(pts[k_] + m * o / max(m @ nrm[k_], 0.3))
    res.append(pts[-1] + nrm[-1] * o)
    return res

# Strecken
halt_draw = []
for r in routes:
    a, b = r["a"], r["b"]
    def ends(i, other):
        if nodes[i]["inset"]:
            ks = assign.get((id(r), i), [])
            if ks: return port_pts(i, ks)
        # Punkt (Abzweig/Abgang) oder Bahnhof ohne passenden Anschluss: Mittelpunkt, Richtung zum Gegenüber
        v = pos[other] - pos[i]; v = v / (np.linalg.norm(v) or 1)
        best = max(DIRS, key=lambda u: u @ v)
        return [(pos[i] + (best * size[i][0] / 2 if nodes[i]["inset"] else 0), best, True)]
    EA, EB = ends(a, b), ends(b, a)
    k = max(len(EA), len(EB)) if (nodes[a]["inset"] or nodes[b]["inset"]) else max(1, r["tracks"])
    k = max(1, min(k, 4))
    # Mittellinie zwischen den Anschlussgruppen
    A = np.mean([p for p, _, _ in EA], axis=0); va = EA[0][1]
    B = np.mean([p for p, _, _ in EB], axis=0); vb = EB[0][1]
    core = connector(A, va, B, vb)
    line = LineString([tuple(p) for p in core])
    pax = all(x[2] for x in EA + EB)
    col, w = (G, 2.4) if pax else (BK, 1.4)
    offs = [(j - (k - 1) / 2) * CFG["tg"] for j in range(k)]
    # Anschlusspunkte je Gleis (nach Querlage sortiert)
    def lateral(pts, v):
        n_ = np.array([-v[1], v[0]]); return sorted(pts, key=lambda q: float(q @ n_))
    PA = lateral([p for p, _, _ in EA], va) if len(EA) > 1 else [EA[0][0]] * k
    PB = lateral([p for p, _, _ in EB], vb)[::-1] if len(EB) > 1 else [EB[0][0]] * k
    for j, o in enumerate(offs):
        pts = offset_poly([np.array(c) for c in line.coords], o)
        if len(pts) < 2: continue
        pa = PA[min(j, len(PA) - 1)]; pb = PB[min(j, len(PB) - 1)]
        path([pa] + pts[1:-1] + [pb], col, w)
    # Halte entlang der Strecke (Anteil der Länge)
    acc, Ltot = 0.0, r["length"]
    for f, nid in zip(r["edges"][:-1], r["seq"][1:-1]):
        acc += f["length"]
        n = nodes[nid]
        if n["kind"] not in ("halt", "station"): continue
        q = line.interpolate(min(max(acc / Ltot, 0.08), 0.92), normalized=True)
        t1 = line.interpolate(min(1, acc / Ltot + 0.01), normalized=True); t0 = line.interpolate(max(0, acc / Ltot - 0.01), normalized=True)
        u = np.array([t1.x - t0.x, t1.y - t0.y]); u = u / (np.linalg.norm(u) or 1)
        halt_draw.append((np.array([q.x, q.y]), u, k, n, pax))
for p, u, k, n, pax in halt_draw:
    nv = np.array([-u[1], u[0]]); half = (k - 1) / 2 * CFG["tg"]
    nt = n.get("tracks", 1) or 1
    if k == 1 and nt >= 2:             # Kreuzungsstelle: Ausweichgleis + Aussenperrons
        L_ = 34; run = CFG["tg"] * 1.6 / TAN60 + 4
        path([p - u * L_, p - u * (L_ - run) + nv * CFG["tg"] * 1.6, p + u * (L_ - run) + nv * CFG["tg"] * 1.6, p + u * L_], G, 2.4)
        for o in (-7, CFG["tg"] * 1.6 + 7):
            path([p - u * 18 + nv * o, p + u * 18 + nv * o], G, 4.5)
        lab = p + nv * (CFG["tg"] * 1.6 + 22)
    else:
        for o in ((-(half + 7), half + 7) if k >= 2 else (half + 7,)):
            path([p - u * 16 + nv * o, p + u * 16 + nv * o], G, 4.5)
        lab = p + nv * (half + 22)
    anc = "middle" if abs(nv[0]) < 0.4 else ("start" if nv[0] > 0 else "end")
    text(lab[0], lab[1] + 4, n["name"], 12.5, anc)
# Abgänge beschriften
for i in [i for i in MAJOR if nodes[i]["kind"] == "exit"]:
    n = nodes[i]; r = next(r for r in routes if i in (r["a"], r["b"]))
    other = r["b"] if r["a"] == i else r["a"]
    v = pos[i] - pos[other]; v = v / (np.linalg.norm(v) or 1)
    p = pos[i] + v * 16
    arrow = "→" if v[0] > 0.3 else ("←" if v[0] < -0.3 else ("↑" if v[1] < 0 else "↓"))
    anc = "start" if v[0] > 0.3 else ("end" if v[0] < -0.3 else "middle")
    dy = -6 if abs(v[1]) < 0.7 else (-22 if v[1] < 0 else 14)
    text(p[0], p[1] + dy, f"Linie {n.get('ref', '')}", 14, anc)
    town = n.get("town") or ""
    text(p[0], p[1] + dy + 17, (f"{arrow} {town}" if anc == "end" else f"{town} {arrow}").strip(), 14, anc)

allx = [float(v) for s_ in re.findall(r'[ML]([-\d.]+),', "".join(out)) for v in [s_]]
ally = [float(v) for v in re.findall(r'[ML][-\d.]+,([-\d.]+)', "".join(out))]
minx, miny = min(allx + [p[0] - size[i][0] / 2 for i, p in pos.items()]) - 220, min(ally + [p[1] - size[i][1] / 2 for i, p in pos.items()]) - 160
maxx, maxy = max(allx + [p[0] + size[i][0] / 2 for i, p in pos.items()]) + 220, max(ally + [p[1] + size[i][1] / 2 for i, p in pos.items()]) + 160
W, H = maxx - minx, maxy - miny
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx:.0f} {miny:.0f} {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
       f'font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif"><rect x="{minx:.0f}" y="{miny:.0f}" width="{W:.0f}" height="{H:.0f}" fill="#fff"/>'
       + "".join(out) +
       f'<text x="{minx + 40:.0f}" y="{miny + 60:.0f}" font-size="34" font-weight="700" fill="{G}">{TITLE}</text>'
       f'<text x="{maxx - 40:.0f}" y="{maxy - 24:.0f}" font-size="12" text-anchor="end" fill="#888">'
       f'Gleisdaten © OpenStreetMap-Mitwirkende (ODbL) · schematisch, nicht massstäblich</text></svg>')
open(OUTF, "w").write(svg)
print("ok", round(W), round(H))
