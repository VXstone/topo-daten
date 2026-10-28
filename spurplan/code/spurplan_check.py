"""
Prüfalgorithmus: vergleicht den gezeichneten Spurplan mit der OSM-Topologie.

Geprüft wird:
  A  Fehlende/versetzte Verbindung: An jedem OSM-Knoten, an dem sich Gleise
     treffen (Weiche, Kreuzung), müssen alle beteiligten Gleise in der Zeichnung
     durch denselben Punkt gehen.
  B  Scheinverbindung: Zwei Gleise ohne gemeinsamen OSM-Knoten dürfen sich in
     der Zeichnung nicht berühren (Linienende auf anderer Linie) und nicht auf
     einer Strecke überlagern.
  C  Kreuzung ohne OSM-Kreuzung: Schneiden sich zwei Linien, ohne dass OSM dort
     einen gemeinsamen Knoten hat (Info: kann eine Brücke/Überwerfung sein).
  D  Reihenfolge: An Stichstellen muss die Abfolge der Gleise quer zur Achse
     in der Zeichnung gleich sein wie in der Realität.
"""
import runpy, sys, collections, math
import numpy as np
from svgpathtools import parse_path

ST_ARGS = sys.argv[1:]
sys.argv = ["x"] + ST_ARGS
G = runpy.run_path("spurplan_schema.py")
segs, DBG, xpos, ypos, SD = G["segs"], G["DBG"], G["xpos"], G["ypos"], G["SD"]
TOL = 2.0
KXW = G.get("KX_WAYS", set())

# ---- gezeichnete Geometrie je Segment (Diagonalgruppen teilen sich eine Linie)
drawn = {}
for sid, d in DBG:
    p = parse_path(d)
    pts = []
    for seg in p:
        n = max(2, int(seg.length() / 1.0))
        pts += [seg.point(t) for t in np.linspace(0, 1, n)]
    pts = np.array([(z.real, z.imag) for z in pts])
    drawn.setdefault(sid, []).append(pts)
for sg in segs:
    g = sg.get("group")
    if g and len(g) > 1 and sg["id"] not in drawn:
        drawn[sg["id"]] = drawn.get(g[0]["id"], [])
poly = {k: np.vstack(v) for k, v in drawn.items() if v}

def dist_to(pts, q):
    return np.min(np.hypot(pts[:, 0] - q[0], pts[:, 1] - q[1]))

issues = []
inc = collections.defaultdict(list)
for sg in segs:
    inc[sg["nodes"][0]].append(sg); inc[sg["nodes"][-1]].append(sg)
label = lambda sg: f'{sg["tags"].get("railway:track_ref") or sg["tags"].get("service") or "Gleis"} (way {sg["way"]})'

# ---- A: Verbindungen an OSM-Knoten
for n, ss in inc.items():
    ss = [s for s in ss if s["id"] in poly]
    if len(ss) < 2: continue
    # Referenzpunkt: Punkt, der von allen Linien am wenigsten entfernt ist
    cands = np.vstack([poly[s["id"]] for s in ss])
    # nur Kandidaten in der Nähe der erwarteten Position
    exp = np.array([G["X"](SD[n][0]) if n in G.get("LAT_OWN", {}) else xpos(n, SD[n][0]), ypos(n)])
    near = cands[np.hypot(*(cands - exp).T) < 60]
    if len(near) == 0: near = cands
    if any(s["way"] in KXW for s in ss): continue
    worst = np.array([max(dist_to(poly[s["id"]], q) for s in ss) for q in near])
    k = worst.argmin()
    if worst[k] > TOL:
        q = near[k]
        far = [label(s) for s in ss if dist_to(poly[s["id"]], q) > TOL]
        issues.append(("A", q, f"Verbindung nicht geschlossen ({worst[k]:.0f}px): " + ", ".join(far)))

# ---- B/C: Berührungen und Kreuzungen ohne gemeinsamen OSM-Knoten
nodesets = {s["id"]: set(s["nodes"]) for s in segs}
ids = [s["id"] for s in segs if s["id"] in poly]
byid = {s["id"]: s for s in segs}
def eff_nodes(i):
    g = byid[i].get("group")
    if g and len(g) > 1: return set().union(*[set(x["nodes"]) for x in g])
    return nodesets[i]
PP = G["P"]
def share(a, b):
    ea, eb = eff_nodes(a), eff_nodes(b)
    if ea & eb: return True
    # real fast zusammenfallende Weichen (< 12 m) gelten als gemeinsamer Knoten
    ends_a = [byid[a]["nodes"][0], byid[a]["nodes"][-1]]; ends_b = [byid[b]["nodes"][0], byid[b]["nodes"][-1]]
    if any(math.dist(PP[x], PP[y]) < 12 for x in ends_a for y in ends_b): return True
    # über ein kurzes Zwischenstück (z.B. Brücken-Way, < 80 m) verbunden (Aarburg 15.10.)
    return any(frozenset((x, y)) in UNDRAWN for x in ends_a for y in ends_b)
UNDRAWN = {frozenset((s["nodes"][0], s["nodes"][-1])) for s in segs
           if s["nodes"][0] in PP and s["nodes"][-1] in PP and math.dist(PP[s["nodes"][0]], PP[s["nodes"][-1]]) < 80}
from scipy.spatial import cKDTree
trees = {i: cKDTree(poly[i]) for i in ids}
seen = set()
for ii, a in enumerate(ids):
    A = poly[a]
    for b in ids[ii + 1:]:
        if share(a, b) or poly[a] is poly[b]: continue
        if byid[a]["way"] in KXW or byid[b]["way"] in KXW: continue   # schematische Kreuzung (Override "kreuzung")
        B = poly[b]
        if (A[:, 0].max() < B[:, 0].min() - 3 or B[:, 0].max() < A[:, 0].min() - 3 or
                A[:, 1].max() < B[:, 1].min() - 3 or B[:, 1].max() < A[:, 1].min() - 3):
            continue
        dA, _ = trees[b].query(A)
        close = dA < 1.5
        if not close.any(): continue
        # Überlagerung: lange zusammenhängende Strecke
        run = np.max(np.diff(np.r_[0, np.flatnonzero(np.diff(np.r_[0, close.astype(int), 0]))])[::2]) if close.any() else 0
        q = A[close][len(A[close]) // 2]
        key = (round(q[0] / 8), round(q[1] / 8))
        # Linienende berührt andere Linie?
        ends = [A[0], A[-1]]; dB, _ = trees[a].query(B); endsB = [B[0], B[-1]]
        touch = [e for e in ends if trees[b].query(e)[0] < 1.5] + [e for e in endsB if trees[a].query(e)[0] < 1.5]
        if run > 6:
            issues.append(("B", q, f"Überlagerung {run}px: {label(byid[a])} / {label(byid[b])}"))
        elif touch:
            issues.append(("B", touch[0], f"Scheinverbindung: {label(byid[a])} berührt {label(byid[b])}"))
        else:
            issues.append(("C", q, f"Kreuzung ohne OSM-Knoten: {label(byid[a])} × {label(byid[b])}"))

# ---- D: Reihenfolge quer zur Achse (nur flache Gleise)
_ZW = {int(w_) for w_ in (G["OVR"].get("zeichnen") or {}).get("weg", [])}
for s in np.arange(G["CFG"]["s_min"] + 50, G["CFG"]["s_max"], 50):
    rows = []
    for c in G["C"]:
        if _ZW and all(sg_["way"] in _ZW for sg_ in c["segs"]): continue     # von Hand gezeichnet (Override "zeichnen")
        if c["s0"] < s < c["s1"]:
            rows.append((G["d_at"](c, s), c["lane"], c))
    rows.sort(key=lambda r: r[0])
    for (d1, l1, c1), (d2, l2, c2) in zip(rows, rows[1:]):
        if d2 - d1 > 1.5 and l2 < l1:
            x = G["X"](s)
            issues.append(("D", (x, G["Y"](l1)), f"Reihenfolge vertauscht bei s={s:.0f}: Lane {l1} über {l2}, real umgekehrt"))

# ---- F: Weichenrichtung (28.10.2026, Vauseyon Hinweis gjx6: «gibt es eine Prüfung, ob die Weiche in die richtige
# Richtung abgeht?»). An jedem OSM-Knoten mit genau drei gezeichneten Gleisen: das Gleis, das den beiden anderen
# gegenüberliegt (Weichenanfang), muss in der Zeichnung dasselbe sein wie in OSM.
P_ = G["P"]; WAYS_ = G["ways"]
def _osm_v(sg, n):
    w = WAYS_[sg["way"]]["nodes"]; i = w.index(n) if n in w else -1
    nb = [w[j] for j in (i - 1, i + 1) if 0 <= j < len(w) and w[j] in sg["nodes"] and w[j] in P_]
    if i < 0 or not nb or n not in P_: return None
    v = np.subtract(P_[nb[0]], P_[n]); return v / (np.linalg.norm(v) or 1)
def _plan_v(sg, q):
    m_ = sg["nodes"][-1] if np.allclose([xpos(sg["nodes"][0], SD[sg["nodes"][0]][0]), ypos(sg["nodes"][0])], q, atol=1.5) else sg["nodes"][0]
    if m_ in SD:                                   # Richtung zum anderen Ende des Segments (robuster als Linienpunkte)
        v = np.array([xpos(m_, SD[m_][0]), ypos(m_)]) - q
        if np.linalg.norm(v) > 3: return v / np.linalg.norm(v)
    pts = poly.get(sg["id"])
    if pts is None: return None
    d = np.hypot(*(pts - q).T); ok = (d > 10) & (d < 30)
    if not ok.any() or d.min() > TOL + 1: return None
    v = pts[ok][np.argmin(d[ok])] - q; return v / (np.linalg.norm(v) or 1)
def _spitze(vs):
    k = [i for i in range(3) if all(float(vs[i] @ vs[j]) < 0.3 for j in range(3) if j != i)]
    return k[0] if len(k) == 1 else None
for n, ss in inc.items():
    ss = [s for s in ss if s["id"] in poly]
    if len(ss) != 3 or n not in SD or any(s["way"] in KXW for s in ss): continue
    q = np.array([xpos(n, SD[n][0]), ypos(n)])
    vo = [_osm_v(s, n) for s in ss]; vp = [_plan_v(s, q) for s in ss]
    if any(v is None for v in vo + vp): continue
    ko, kp = _spitze(vo), _spitze(vp)
    if ko is not None and kp is not None and ko != kp:
        issues.append(("F", q, f"Weiche falsch herum: Weichenanfang in OSM {label(ss[ko])}, gezeichnet {label(ss[kp])}"))

# ---- Ausgabe
cnt = collections.Counter(i[0] for i in issues)
print("Befunde:", dict(cnt))
_u = {}
for t, q, msg in issues: _u.setdefault(msg, (t, q, msg))
issues = list(_u.values())
cnt = collections.Counter(i[0] for i in issues)
print("eindeutig:", dict(cnt))
for t, q, msg in sorted(issues, key=lambda i: (i[0], i[1][0])):
    print(f"{t} x={q[0]:6.0f} y={q[1]:5.0f}  {msg}")

col = {"F": "#d06", "A": "#e00", "B": "#e00", "C": "#f90", "D": "#06c"}
svg = open(G["CFG"]["out"]).read()
marks = "".join(
    f'<circle cx="{q[0]:.1f}" cy="{q[1]:.1f}" r="9" fill="none" stroke="{col[t]}" stroke-width="2.5"/>'
    f'<text x="{q[0] + 11:.1f}" y="{q[1] - 8:.1f}" font-size="12" fill="{col[t]}">{t}</text>'
    for t, q, _ in issues)
open(G["CFG"]["out"].replace(".svg", "_check.svg"), "w").write(svg.replace("</svg>", marks + "</svg>"))
