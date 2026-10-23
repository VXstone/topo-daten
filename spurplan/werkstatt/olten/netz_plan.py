"""
Netzplan mit eingebetteten Spurplänen (Prinzip Dreieck Kerzers–Ins–Murten, vollautomatisch).

1. Topologie bereinigen (wie netz_layout.py); Bahnhöfe mit Spurplan = starre Kästen (waagrecht).
   Bahnhöfe, deren Gleise schon im Plan eines grösseren Nachbarn liegen, werden Halte.
2. Jede Netzkante an einem Bahnhof wird einer Anschlussgruppe im Spurplan zugeordnet
   (Peilung Strecke ↔ Peilung Anschluss, Linie als Zusatzkriterium). Daraus: Ankerpunkt im Kasten
   und Austrittsrichtung (rechts, links oder schräg).
3. Kantenrichtungen: 0/60/90/120° (+Gegenrichtungen); an Ankern nur Richtungen, die nicht in den
   Bahnhof zurückführen (±60° um die Austrittsrichtung).
4. Ausgleichsrechnung: Unbekannte = Kastenmittelpunkte und Punktknoten; Kantenendpunkte = Mittelpunkt
   + Anker. Richtung exakt, Länge ~ L_geo^0.75, schwacher Zug zur Geografie. Überlappen Kästen,
   wird der Massstab vergrössert.
5. Zeichnen: Spurpläne, je Strecke k parallele Gleise exakt an die Anschlüsse, Halte, Kreuzungsstellen,
   Abgänge.
Aufruf: python3 netz_plan.py olten_region "Region Olten" ausgabe.svg
"""
import json, math, sys, os, re, unicodedata, collections
import numpy as np

NAME, TITLE, OUTF = sys.argv[1], sys.argv[2], sys.argv[3]
GEO_W = float(os.environ.get("GEO_W", "0.03"))
CFG = dict(S=0.42, lane=24, scale=0.30, len_pow=0.75, merge_station_m=900, merge_junction_m=420,
           drop_end_m=700, cover_m=1300, stub=14, R=9, min_len=dict(inset=60, halt=55, junction=45, exit=60, via=40),
           box_gap=30)
G, BK = "#00862f", "#111"
TAN60 = math.tan(math.radians(60))
TG = CFG["lane"] * CFG["S"]                     # Gleisabstand Strecke = Ebenenabstand im Spurplan
T = json.load(open(f"{NAME}_topologie.json"))
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")
nodes = {n["id"]: dict(n) for n in T["nodes"]}
edges = [dict(e) for e in T["edges"]]
def dist(a, b): return math.hypot(nodes[a]["x"] - nodes[b]["x"], nodes[a]["y"] - nodes[b]["y"])
def relabel(old, new):
    for e in edges:
        if e["a"] == old: e["a"] = new
        if e["b"] == old: e["b"] = new
    nodes.pop(old, None)
def drop_loops():
    global edges
    edges = [e for e in edges if e["a"] != e["b"]]
    uniq = {}
    for e in edges:
        k = tuple(sorted((e["a"], e["b"])))
        if k in uniq:
            u = uniq[k]; u["tracks"] = max(u["tracks"], e["tracks"]); u["refs"] = sorted(set(u["refs"]) | set(e["refs"]))
            if e["length"] < u["length"]: u["geom"], u["length"] = (e["geom"] if e["a"] == u["a"] else e["geom"][::-1]), e["length"]
        else: uniq[k] = e
    edges = list(uniq.values())

# ------------------------------------------------------------------ 1. Bereinigen, Kästen
PORTS = {}
for i, n in nodes.items():
    n["inset"] = None
    if n["kind"] == "station" and os.path.exists(slug(n["name"]) + "_ports.json"):
        n["inset"] = slug(n["name"]); PORTS[i] = json.load(open(n["inset"] + "_ports.json"))
for a in [i for i in nodes if nodes[i]["inset"]]:
    for b in [i for i in nodes if nodes[i]["inset"]]:
        if a != b and dist(a, b) < CFG["cover_m"]:
            ka = (len(PORTS[a]["ports"]), PORTS[a]["W"]); kb = (len(PORTS[b]["ports"]), PORTS[b]["W"])
            if ka < kb: nodes[a]["covered"] = b
for i, n in nodes.items():
    if n.get("covered") is not None or (n["kind"] == "station" and not n["inset"]):
        n["inset"] = None; n["kind"] = "halt"; PORTS.pop(i, None)
for nid in [n for n in nodes if nodes[n]["kind"] == "end"]:
    edges = [e for e in edges if nid not in (e["a"], e["b"]) or e["length"] > CFG["drop_end_m"]]
    if not any(nid in (e["a"], e["b"]) for e in edges): nodes.pop(nid)
for j in [n for n in nodes if nodes[n]["kind"] == "junction"]:
    st = [s for s in nodes if nodes[s]["inset"] and dist(j, s) < CFG["merge_station_m"]]
    if st: relabel(j, min(st, key=lambda s: dist(j, s)))
drop_loops()
changed = True
while changed:
    changed = False
    J = [n for n in nodes if nodes[n]["kind"] == "junction"]
    for a in J:
        for b in J:
            if a != b and a in nodes and b in nodes and dist(a, b) < CFG["merge_junction_m"]:
                relabel(b, a); drop_loops(); changed = True
changed = True
while changed:
    changed = False
    for j in list(nodes):
        if nodes[j]["kind"] != "junction": continue
        inc = [e for e in edges if j in (e["a"], e["b"])]
        if len(inc) == 2:
            e1, e2 = inc
            o1 = e1["b"] if e1["a"] == j else e1["a"]; o2 = e2["b"] if e2["a"] == j else e2["a"]
            g1 = e1["geom"] if e1["b"] == j else e1["geom"][::-1]; g2 = e2["geom"] if e2["a"] == j else e2["geom"][::-1]
            edges.remove(e1); edges.remove(e2)
            edges.append(dict(a=o1, b=o2, tracks=e1["tracks"] if e1["length"] >= e2["length"] else e2["tracks"],
                              length=e1["length"] + e2["length"], refs=sorted(set(e1["refs"]) | set(e2["refs"])), geom=g1 + g2))
            nodes.pop(j); changed = True; break
drop_loops()
ids = sorted(nodes); idx = {n: k for k, n in enumerate(ids)}
inc = collections.defaultdict(list)
for e in edges: inc[e["a"]].append(e); inc[e["b"]].append(e)
print("Knoten:", collections.Counter("spurplan" if nodes[n]["inset"] else nodes[n]["kind"] for n in ids), "Kanten:", len(edges))

# ------------------------------------------------------------------ 2. Anschlüsse zuordnen
def adiff(a, b): return abs((a - b + 180) % 360 - 180)
def geo_bearing(e, at, reach=500):
    g = e["geom"] if e["a"] == at else e["geom"][::-1]
    if math.dist(g[0], (nodes[at]["x"], nodes[at]["y"])) > math.dist(g[-1], (nodes[at]["x"], nodes[at]["y"])): g = g[::-1]
    p0 = np.array(g[0]); L = 0; q = p0
    for p in g[1:]:
        L += math.dist(q, p); q = np.array(p)
        if L > reach: break
    return math.degrees(math.atan2(q[1] - p0[1], q[0] - p0[0])) % 360
S = CFG["S"]
def port_vec(p):
    if p["kind"] == "side": return np.array([p["dx"] * 0.5, -p["dy"] * 0.866 * -1])   # SVG-y nach unten: dy=+1 -> unten
    return np.array([float(p["dx"]), 0.0])
anchor = {}        # (id(e), node) -> dict(off=np.array (px, rel. Kastenmitte, SVG-Koordinaten), v=Austritt, ports=[...])
for i in [i for i in ids if nodes[i]["inset"]]:
    P = PORTS[i]["ports"]; cx = (PORTS[i]["x_lo"] + PORTS[i]["x_hi"]) / 2; cy = (PORTS[i]["y_lo"] + PORTS[i]["y_hi"]) / 2
    es = [(e, geo_bearing(e, i)) for e in inc[i]]
    taken = set()
    for e, br in sorted(es, key=lambda t: min([adiff(t[1], p["bearing"]) for p in P] or [999])):
        cand = sorted((adiff(br, p["bearing"]) + (0 if p["ref"] in e["refs"] else 20), k) for k, p in enumerate(P) if k not in taken)
        cand = [c for c in cand if c[0] < 70]
        if cand:
            k0 = cand[0][1]; v0 = port_vec(P[k0])
            grp = [k for sc, k in cand if sc < cand[0][0] + 30 and np.allclose(port_vec(P[k]), v0)]
            grp = sorted(grp, key=lambda k: P[k]["y"])[:max(1, min(4, max(e["tracks"], 1) + 1))]
            for k in grp: taken.add(k)
            pts = [np.array([(P[k]["x"] - cx) * S, (P[k]["y"] - cy) * S]) for k in grp]
            anchor[(id(e), i)] = dict(off=np.mean(pts, axis=0), v=v0, pts=pts, pax=all(P[k]["pax"] for k in grp))
        else:     # kein passender Anschluss: Kastenende in Streckenrichtung
            right = math.cos(math.radians(br)) >= 0
            off = np.array([((PORTS[i]["x_hi"] - cx) if right else (PORTS[i]["x_lo"] - cx)) * S, 0.0])
            anchor[(id(e), i)] = dict(off=off, v=np.array([1.0 if right else -1.0, 0.0]), pts=[off], pax=True)
            print(f"  {nodes[i]['name']}: Strecke Richtung {br:.0f}° ohne Anschluss")
    free = [k for k in range(len(P)) if k not in taken]
    if free: print(f"  {nodes[i]['name']}: freie Anschlüsse {[(P[k]['ref'], round(P[k]['bearing'])) for k in free]}")

# ------------------------------------------------------------------ 3. Richtungen
DIRS = [0, 60, 90, 120, 180, 240, 270, 300]
def uvec(dg): return np.array([math.cos(math.radians(dg)), -math.sin(math.radians(dg))])   # SVG
def allowed(e, n):
    a = anchor.get((id(e), n))
    if not a: return DIRS
    out = []
    for d in DIRS:
        dd = d if e["a"] == n else (d + 180) % 360        # Richtung vom Knoten n weg
        if uvec(dd) @ a["v"] / np.linalg.norm(a["v"]) > 0.45: out.append(d)
    return out
for e in edges:
    A, B = nodes[e["a"]], nodes[e["b"]]
    e["geo"] = math.degrees(math.atan2(B["y"] - A["y"], B["x"] - A["x"])) % 360
    ok = [d for d in allowed(e, e["a"]) if d in allowed(e, e["b"])] or DIRS
    e["cands"] = sorted(ok, key=lambda d: adiff(e["geo"], d)); e["dir"] = e["cands"][0]
    # Anschlussrichtungen und Geografie widersprechen sich -> Kante wird als Verbinder mit Knick gezeichnet
    e["flex"] = adiff(e["geo"], e["dir"]) > 50
def out_dir(e, n): return e["dir"] if e["a"] == n else (e["dir"] + 180) % 360
for it in range(60):
    bad = False
    for n in ids:
        if nodes[n]["inset"]: continue            # an Kästen trennen die Anker
        seen = {}
        for e in sorted(inc[n], key=lambda e: adiff(e["geo"], e["dir"])):
            d = out_dir(e, n)
            if d in seen:
                for c in e["cands"]:
                    dc = c if e["a"] == n else (c + 180) % 360
                    if dc not in seen and adiff(e["geo"], c) < 100: e["dir"] = c; break
                bad = True
            seen[out_dir(e, n)] = e
    if not bad: break

# ------------------------------------------------------------------ 4. Ausgleichsrechnung
X0 = np.array([[nodes[n]["x"], -nodes[n]["y"]] for n in ids])          # SVG-Orientierung
def off(e, n): return anchor[(id(e), n)]["off"] if (id(e), n) in anchor else np.zeros(2)
def tlen(e, sc):
    L = sc * e["length"] ** CFG["len_pow"]
    m = sum(CFG["min_len"]["inset" if nodes[x]["inset"] else nodes[x]["kind"] if nodes[x]["kind"] in CFG["min_len"] else "via"] for x in (e["a"], e["b"])) / 2
    return max(L, m) * e.get("stretch", 1.0)
def boxes(Y):
    out = {}
    for n in ids:
        if not nodes[n]["inset"]: continue
        P = PORTS[n]; w = (P["x_hi"] - P["x_lo"] + 40) * S; h = (P["y_hi"] - P["y_lo"] + 50) * S
        c = Y[idx[n]]; out[n] = (c[0] - w / 2, c[1] - h / 2, c[0] + w / 2, c[1] + h / 2)
    return out
def GEOF(sc):
    """Massstab Geografie -> Plan, passend zu den Ziel-Kantenlängen (Median)."""
    r_ = [tlen(e, sc) / max(dist(e["a"], e["b"]), 1) for e in edges]
    return float(np.median(r_))
def solve(sc):
    N = len(ids); rows, rhs = [], []
    for e in edges:
        a, b = idx[e["a"]], idx[e["b"]]; d = uvec(e["dir"]); nv = np.array([-d[1], d[0]])
        const = off(e, e["b"]) - off(e, e["a"])
        if e.get("flex"):
            g_ = uvec(e["geo"]); terms = ((g_, tlen(e, sc), 0.3), (np.array([-g_[1], g_[0]]), 0.0, 0.3))
        else: terms = ((d, tlen(e, sc), 1.0), (nv, 0.0, 400.0))
        for vec, val, w in terms:
            r = np.zeros(2 * N); r[2 * b:2 * b + 2] += vec; r[2 * a:2 * a + 2] -= vec
            rows.append(r * math.sqrt(w)); rhs.append((val - const @ vec) * math.sqrt(w))
    for (i_, j_, u_, dmin) in SEP:            # Abstandsbedingungen gegen Überlappung
        r = np.zeros(2 * N); r[2 * idx[j_]:2 * idx[j_] + 2] += u_; r[2 * idx[i_]:2 * idx[i_] + 2] -= u_
        rows.append(r * math.sqrt(50.0)); rhs.append(dmin * math.sqrt(50.0))
    c0 = X0.mean(0)
    for i_ in range(N):
        for k in range(2):
            r = np.zeros(2 * N); r[2 * i_ + k] = 1; w = GEO_W
            rows.append(r * math.sqrt(w)); rhs.append((X0[i_, k] - c0[k]) * GEOF(sc) * math.sqrt(w))
    sol, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    return sol.reshape(-1, 2)
sc = CFG["scale"]
SEP = []
for it in range(25):
    Y = solve(sc)
    # zu kurze Kanten strecken
    for e in edges:
        a, b = idx[e["a"]], idx[e["b"]]
        pa = Y[a] + off(e, e["a"]); pb = Y[b] + off(e, e["b"])
        if not e.get("flex") and (pb - pa) @ uvec(e["dir"]) < 0.8 * tlen(e, sc): e["stretch"] = e.get("stretch", 1.0) * 1.25
    # Kastenüberlappungen: Kanten zwischen den beiden Kästen strecken
    bx = boxes(Y); hits = 0
    keys = list(bx)
    for p_ in range(len(keys)):
        for q_ in range(p_ + 1, len(keys)):
            A_, B_ = bx[keys[p_]], bx[keys[q_]]
            if A_[0] < B_[2] + CFG["box_gap"] and B_[0] < A_[2] + CFG["box_gap"] and A_[1] < B_[3] + CFG["box_gap"] and B_[1] < A_[3] + CFG["box_gap"]:
                hits += 1
                i_, j_ = keys[p_], keys[q_]
                ci, cj = Y[idx[i_]], Y[idx[j_]]
                wsum = (A_[2] - A_[0] + B_[2] - B_[0]) / 2 + CFG["box_gap"]; hsum = (A_[3] - A_[1] + B_[3] - B_[1]) / 2 + CFG["box_gap"]
                dx_, dy_ = cj[0] - ci[0], cj[1] - ci[1]
                # Trennung in der Richtung mit geringerer nötiger Verschiebung, Geografie entscheidet die Seite
                gx = X0[idx[j_]][0] - X0[idx[i_]][0]; gy = X0[idx[j_]][1] - X0[idx[i_]][1]
                if (wsum - abs(dx_)) * (1 if abs(gx) > 0.5 * abs(gy) else 3) < (hsum - abs(dy_)) * (1 if abs(gy) > 0.5 * abs(gx) else 3):
                    SEP.append((i_, j_, np.array([1.0 if gx >= 0 else -1.0, 0.0]), wsum))
                else:
                    SEP.append((i_, j_, np.array([0.0, 1.0 if gy >= 0 else -1.0]), hsum))
    # Punktknoten in Kästen
    for n in ids:
        if nodes[n]["inset"]: continue
        for k_, b_ in bx.items():
            if b_[0] - 15 < Y[idx[n]][0] < b_[2] + 15 and b_[1] - 15 < Y[idx[n]][1] < b_[3] + 15:
                hits += 1
                c_ = Y[idx[k_]]; gx = X0[idx[n]][0] - X0[idx[k_]][0]; gy = X0[idx[n]][1] - X0[idx[k_]][1]
                if abs(gx) * (b_[3] - b_[1]) > abs(gy) * (b_[2] - b_[0]):
                    SEP.append((k_, n, np.array([1.0 if gx >= 0 else -1.0, 0.0]), (b_[2] - b_[0]) / 2 + 25))
                else:
                    SEP.append((k_, n, np.array([0.0, 1.0 if gy >= 0 else -1.0]), (b_[3] - b_[1]) / 2 + 25))
    print(f"Durchlauf {it}: Überlappungen {hits}")
    if not hits: break
pos = {n: Y[idx[n]] for n in ids}
dev = max([0] + [adiff(math.degrees(math.atan2(-((pos[e["b"]] + off(e, e["b"])) - (pos[e["a"]] + off(e, e["a"])))[1],
                                    ((pos[e["b"]] + off(e, e["b"])) - (pos[e["a"]] + off(e, e["a"])))[0])) % 360, e["dir"]) for e in edges if not e.get("flex")])
print("max. Richtungsabweichung %.1f°" % dev)

# ------------------------------------------------------------------ 5. Zeichnen
out = []
def path(pts, color=G, w=2.4):
    pts = [np.array(p, float) for p in pts]; cl = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - cl[-1]) > 0.3: cl.append(p)
    pts = cl
    if len(pts) < 2: return
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for k in range(1, len(pts) - 1):
        p0, p1, p2 = pts[k - 1], pts[k], pts[k + 1]; l1, l2 = np.linalg.norm(p1 - p0), np.linalg.norm(p2 - p1)
        r = min(CFG["R"], l1 / 2, l2 / 2); a = p1 - (p1 - p0) / l1 * r; b = p1 + (p2 - p1) / l2 * r
        d += f"L{a[0]:.1f},{a[1]:.1f}Q{p1[0]:.1f},{p1[1]:.1f} {b[0]:.1f},{b[1]:.1f}"
    d += f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
def text(x, y, t, size=14, anchor_="middle", weight=400, color=G):
    out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor_}" fill="{color}">{t}</text>')
DV = [uvec(a) for a in DIRS]
def turn(u, v): return math.degrees(math.acos(max(-1, min(1, float(u @ v)))))
def connector(A, a, B, b):
    st = CFG["stub"] * 2; A1 = A + a * st; B1 = B + b * st; d = B1 - A1; best = None
    for u in DV:
        for v in DV:
            M = np.array([u, -v]).T
            if abs(np.linalg.det(M)) < 1e-6: continue
            t, s_ = np.linalg.solve(M, d)
            if t < 0 or s_ < 0: continue
            sc_ = (turn(a, u) ** 1.5 + turn(u, v) ** 1.5 + turn(v, -b) ** 1.5) * 0.1 + (t + s_) * 0.01
            if max(turn(a, u), turn(u, v), turn(v, -b)) > 90: sc_ += 1e4
            if best is None or sc_ < best[0]: best = (sc_, [A, A1, A1 + u * t, B1, B])
    return best[1] if best else [A, B]
def offset_poly(pts, o):
    pts = [p for k_, p in enumerate(pts) if k_ == 0 or np.linalg.norm(p - pts[k_ - 1]) > 0.3]
    if len(pts) < 2 or abs(o) < 1e-9: return pts
    nrm = []
    for p, q in zip(pts, pts[1:]):
        u = (q - p) / np.linalg.norm(q - p); nrm.append(np.array([-u[1], u[0]]))
    res = [pts[0] + nrm[0] * o]
    for k_ in range(1, len(pts) - 1):
        m = nrm[k_ - 1] + nrm[k_]; m = m / (np.linalg.norm(m) or 1); res.append(pts[k_] + m * o / max(m @ nrm[k_], 0.3))
    res.append(pts[-1] + nrm[-1] * o)
    return res
# Spurpläne
for n in [n for n in ids if nodes[n]["inset"]]:
    P = PORTS[n]; cx = (P["x_lo"] + P["x_hi"]) / 2; cy = (P["y_lo"] + P["y_hi"]) / 2
    tx, ty = pos[n][0] - cx * S, pos[n][1] - cy * S
    svg = open(nodes[n]["inset"] + "_bare.svg").read()
    body = re.sub(r"^.*?<svg[^>]*>", "", svg, flags=re.S).replace("</svg>", "").replace('<rect width="100%" height="100%" fill="#fff"/>', "")
    body = re.sub(r'stroke-width="([\d.]+)"', lambda m: f'stroke-width="{float(m.group(1)) * 0.72 / S:.2f}"', body)
    body = re.sub(r'font-size="([\d.]+)"', lambda m: f'font-size="{float(m.group(1)) * 0.6 / S:.1f}"', body)
    out.append(f'<g transform="translate({tx:.1f},{ty:.1f}) scale({S})">{body}</g>')
    text(pos[n][0], ty + (P["y_lo"] - 14) * S, nodes[n]["name"], 16, weight=700)
# Strecken
def track_ends(e, n, k):
    """k Anschlusspunkte (SVG) am Knoten n, quer sortiert."""
    a = anchor.get((id(e), n))
    if a:
        pts = [pos[n] + p for p in a["pts"]]
        if len(pts) >= k: return pts[:k], a["v"]
        base = pos[n] + a["off"]; return [base] * k, a["v"]
    return [pos[n]] * k, None
halts = []
for e in edges:
    na, nb = e["a"], e["b"]
    k = max(1, min(4, e["tracks"]))
    for n in (na, nb):
        a = anchor.get((id(e), n))
        if a: k = max(1, min(4, len(a["pts"])))
    d = uvec(e["dir"]); nv = np.array([-d[1], d[0]])
    A = pos[na] + off(e, na); B = pos[nb] + off(e, nb)
    pa, va = track_ends(e, na, k); pb, vb = track_ends(e, nb, k)
    pax = all(anchor[(id(e), n)]["pax"] for n in (na, nb) if (id(e), n) in anchor)
    col, w = (G, 2.4) if pax else (BK, 1.3)
    # Querreihenfolge: links->rechts bezogen auf Fahrtrichtung a->b
    pa = sorted(pa, key=lambda p: float((p - A) @ nv)); pb = sorted(pb, key=lambda p: float((p - B) @ nv))
    offs = [(j - (k - 1) / 2) * TG for j in range(k)]
    if e.get("flex"):
        core = connector(A, va if va is not None else uvec(e["geo"]), B, vb if vb is not None else -uvec(e["geo"]))
        for j, o in enumerate(offs):
            pts = offset_poly([np.array(c) for c in core], o)
            path([pa[j]] + pts[1:-1] + [pb[j]], col, w)
        continue
    for j, o in enumerate(offs):
        s0 = A + nv * o; s1 = B + nv * o
        pts = []
        p0 = pa[j]
        if va is not None: pts += [p0, p0 + va * CFG["stub"]]
        else: pts += [p0]
        pts += [s0 + d * (CFG["stub"] + 4 if va is not None else 0), s1 - d * (CFG["stub"] + 4 if vb is not None else 0)]
        p1 = pb[j]
        if vb is not None: pts += [p1 + vb * CFG["stub"], p1]
        else: pts += [p1]
        path(pts, col, w)
    # Halte auf dieser Kante?  (Knoten-Typ halt sind eigene Knoten -> werden unten gezeichnet)
for n in ids:
    if nodes[n]["kind"] != "halt": continue
    es = inc[n]
    if not es: continue
    e = max(es, key=lambda e: e["tracks"]); d = uvec(out_dir(e, n)); nv = np.array([-d[1], d[0]])
    k = max(1, min(4, e["tracks"])); half = (k - 1) / 2 * TG; p = pos[n]
    nt = nodes[n].get("tracks", 1) or 1
    if k == 1 and nt >= 2:
        L_ = 30; run = TG / TAN60 + 3
        path([p - d * L_, p - d * (L_ - run) + nv * TG, p + d * (L_ - run) + nv * TG, p + d * L_], G, 2.4)
        for o in (-6, TG + 6): path([p - d * 15 + nv * o, p + d * 15 + nv * o], G, 4.2)
        lab = p + nv * (TG + 20)
    else:
        for o in ((-(half + 6), half + 6) if k >= 2 else (half + 6,)): path([p - d * 14 + nv * o, p + d * 14 + nv * o], G, 4.2)
        lab = p + nv * (half + 20)
    anc = "middle" if abs(nv[0]) < 0.4 else ("start" if nv[0] > 0 else "end")
    text(lab[0], lab[1] + 4, nodes[n]["name"], 12, anc)
for n in ids:
    if nodes[n]["kind"] != "exit": continue
    e = inc[n][0]; v = uvec(out_dir(e, n)) * -1
    p = pos[n] + v * 12
    arrow = "→" if v[0] > 0.3 else ("←" if v[0] < -0.3 else ("↑" if v[1] < 0 else "↓"))
    anc = "start" if v[0] > 0.3 else ("end" if v[0] < -0.3 else "middle")
    dy = -5 if abs(v[1]) < 0.7 else (-22 if v[1] < 0 else 14)
    text(p[0], p[1] + dy, f"Linie {nodes[n].get('ref', '')}", 13, anc)
    town = nodes[n].get("town") or ""
    text(p[0], p[1] + dy + 16, (f"{arrow} {town}" if anc == "end" else f"{town} {arrow}").strip(), 13, anc)

xs = [float(v) for v in re.findall(r'[MLQ ](-?[\d.]+),', "".join(out))] + [p[0] for p in pos.values()]
ys = [float(v) for v in re.findall(r'[MLQ ]-?[\d.]+,(-?[\d.]+)', "".join(out))] + [p[1] for p in pos.values()]
bx = boxes(np.array([pos[n] for n in ids]))
xs += [b[0] for b in bx.values()] + [b[2] for b in bx.values()]; ys += [b[1] for b in bx.values()] + [b[3] for b in bx.values()]
minx, maxx, miny, maxy = min(xs) - 200, max(xs) + 200, min(ys) - 140, max(ys) + 120
W, H = maxx - minx, maxy - miny
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx:.0f} {miny:.0f} {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
       f'font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif"><rect x="{minx:.0f}" y="{miny:.0f}" width="{W:.0f}" height="{H:.0f}" fill="#fff"/>'
       + "".join(out) + f'<text x="{minx + 40:.0f}" y="{miny + 56:.0f}" font-size="32" font-weight="700" fill="{G}">{TITLE}</text>'
       f'<text x="{maxx - 40:.0f}" y="{maxy - 20:.0f}" font-size="12" text-anchor="end" fill="#888">Gleisdaten © OpenStreetMap-Mitwirkende (ODbL) · schematisch, nicht massstäblich</text></svg>')
open(OUTF, "w").write(svg)
print("ok", round(W), round(H))
if "--dbg" in sys.argv:
    for e in edges:
        pa = pos[e["a"]] + off(e, e["a"]); pb = pos[e["b"]] + off(e, e["b"])
        ang = math.degrees(math.atan2(-(pb - pa)[1], (pb - pa)[0])) % 360
        if adiff(ang, e["dir"]) > 5:
            print("ABW", nodes[e["a"]]["name"], "->", nodes[e["b"]]["name"], "soll", e["dir"], "ist %.0f" % ang, "geo %.0f" % e["geo"], "stretch %.2f" % e.get("stretch", 1), "cands", e["cands"][:3])
