"""
Schematische Anordnung eines Netzes (Stil: Uppsala/Dreieck).

1. Topologie bereinigen: Abzweige im Bahnhofskopf -> Bahnhof, Abzweige mit 2 Anschlüssen auflösen,
   lose Enden weg, nahe Abzweige zusammenfassen.
2. Jede Kante auf eine erlaubte Richtung legen (0°, 60°, 90°, 120° und Gegenrichtungen),
   Konflikte an Knoten auflösen (zwei Kanten nie in dieselbe Richtung).
3. Knotenlagen per gewichteter Ausgleichsrechnung: Richtung exakt, Länge ~ geografisch (gestaucht),
   Mindestlängen für Bahnhöfe/Halte, schwacher Zug zur Geografie.
Ausgabe: <name>_layout.json
"""
import json, math, sys, collections
import numpy as np

NAME = sys.argv[1] if len(sys.argv) > 1 else "olten_region"
T = json.load(open(f"{NAME}_topologie.json"))
CFG = dict(
    dirs=[0, 60, 90, 120, 180, 240, 270, 300],
    merge_station_m=560, merge_junction_m=420, drop_end_m=700,
    scale=0.11, len_pow=0.75,        # Ziel-Länge [px] = scale * L_geo^len_pow * ...
    min_len=dict(station=150, halt=70, junction=50, exit=60),
)
nodes = {n["id"]: dict(n) for n in T["nodes"]}
edges = [dict(e) for e in T["edges"]]

def deg(nid): return sum(1 for e in edges if nid in (e["a"], e["b"]))
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
        else: uniq[k] = e
    edges = list(uniq.values())

# --- lose Enden
for nid in [n for n in nodes if nodes[n]["kind"] == "end"]:
    edges = [e for e in edges if nid not in (e["a"], e["b"]) or e["length"] > CFG["drop_end_m"]]
    if deg(nid) == 0: nodes.pop(nid)
# --- Abzweige im Bahnhofskopf
for j in [n for n in nodes if nodes[n]["kind"] == "junction"]:
    st = [s for s in nodes if nodes[s]["kind"] == "station" and dist(j, s) < CFG["merge_station_m"]]
    if st: relabel(j, min(st, key=lambda s: dist(j, s)))
drop_loops()
# --- nahe Abzweige zusammenfassen
changed = True
while changed:
    changed = False
    J = [n for n in nodes if nodes[n]["kind"] == "junction"]
    for i, a in enumerate(J):
        for b in J[i + 1:]:
            if a in nodes and b in nodes and dist(a, b) < CFG["merge_junction_m"]:
                nodes[a]["x"] = (nodes[a]["x"] + nodes[b]["x"]) / 2; nodes[a]["y"] = (nodes[a]["y"] + nodes[b]["y"]) / 2
                relabel(b, a); drop_loops(); changed = True
# --- Abzweige mit zwei Anschlüssen auflösen (Kanten verbinden)
changed = True
while changed:
    changed = False
    for j in list(nodes):
        if nodes[j]["kind"] != "junction": continue
        inc = [e for e in edges if j in (e["a"], e["b"])]
        if len(inc) == 2:
            e1, e2 = inc
            o1 = e1["b"] if e1["a"] == j else e1["a"]; o2 = e2["b"] if e2["a"] == j else e2["a"]
            g1 = e1["geom"] if e1["b"] == j else e1["geom"][::-1]
            g2 = e2["geom"] if e2["a"] == j else e2["geom"][::-1]
            L = e1["length"] + e2["length"]
            tr = e1["tracks"] if e1["length"] >= e2["length"] else e2["tracks"]
            edges.remove(e1); edges.remove(e2)
            edges.append(dict(a=o1, b=o2, tracks=tr, length=L, refs=sorted(set(e1["refs"]) | set(e2["refs"])),
                              ref=e1["ref"], geom=g1 + g2))
            nodes.pop(j); changed = True; break
        if len(inc) == 0: nodes.pop(j); changed = True; break
drop_loops()
ids = sorted(nodes); idx = {n: i for i, n in enumerate(ids)}
print("bereinigt:", collections.Counter(nodes[n]["kind"] for n in ids), "Kanten", len(edges))

# --- Richtung je Kante: Sehne der ersten/letzten ~600 m an den Enden nicht, sondern Gesamt-Sehne
def ang(dx, dy): return math.degrees(math.atan2(dy, dx)) % 360
def snapdiff(a, d): return abs((a - d + 180) % 360 - 180)
for e in edges:
    A, B = nodes[e["a"]], nodes[e["b"]]
    e["geo_ang"] = ang(B["x"] - A["x"], B["y"] - A["y"])
    e["cands"] = sorted(CFG["dirs"], key=lambda d: snapdiff(e["geo_ang"], d))
    e["dir"] = e["cands"][0]
# Konflikte: an jedem Knoten darf jede Richtung nur einmal ausgehen
def out_dir(e, n): return e["dir"] if e["a"] == n else (e["dir"] + 180) % 360
for it in range(50):
    bad = False
    for n in ids:
        inc = [e for e in edges if n in (e["a"], e["b"])]
        seen = {}
        for e in sorted(inc, key=lambda e: snapdiff(e["geo_ang"], e["dir"])):
            d = out_dir(e, n)
            if d in seen:
                # die schlechter passende Kante auf die nächste freie Richtung
                for c in e["cands"]:
                    dc = c if e["a"] == n else (c + 180) % 360
                    if dc not in seen and snapdiff(e["geo_ang"], c) < 75:
                        e["dir"] = c; break
                bad = True
            seen[out_dir(e, n)] = e
    if not bad: break

# --- Bahnhöfe: zwei Köpfe (A/B) mit fester Länge in Bahnhofsrichtung
STLEN = json.load(open(f"{NAME}_stlen.json")) if __import__("os").path.exists(f"{NAME}_stlen.json") else {}
def vec(dg): return (math.cos(math.radians(dg)), math.sin(math.radians(dg)))
next_id = max(nodes) + 1
for sid in [n for n in ids if nodes[n]["kind"] == "station"]:
    inc = [e for e in edges if sid in (e["a"], e["b"])]
    if not inc: continue
    od = [(e, out_dir(e, sid)) for e in inc]
    best = None
    for i in range(len(od)):
        for j in range(i + 1, len(od)):
            diff = snapdiff(od[i][1], (od[j][1] + 180) % 360)
            w = od[i][0]["tracks"] + od[j][0]["tracks"]
            k = (diff, -w)
            if best is None or k < best[0]: best = (k, od[i][1])
    th = best[1] if best else od[0][1]
    if th % 360 >= 180 or th % 360 == 0 and False: th = (th + 180) % 360
    if th in (180, 240, 270, 300): th = (th + 180) % 360        # theta in {0, 60, 90, 120}
    a_id, b_id = next_id, next_id + 1; next_id += 2
    S = nodes[sid]
    for k_, tid in (("A", a_id), ("B", b_id)):
        nodes[tid] = dict(id=tid, kind="throat", name=S["name"] + " " + k_, x=S["x"], y=S["y"], station=sid, side=k_)
    S["theta"] = th; S["throats"] = [a_id, b_id]
    tv = vec(th)
    for e, d in od:
        other = e["b"] if e["a"] == sid else e["a"]
        dt = math.cos(math.radians(d - th))
        if abs(dt) < 0.3:     # quer abgehend: nach Geografie
            dt = (nodes[other]["x"] - S["x"]) * tv[0] + (nodes[other]["y"] - S["y"]) * tv[1]
        tgt = b_id if dt > 0 else a_id
        if e["a"] == sid: e["a"] = tgt
        else: e["b"] = tgt
    edges.append(dict(a=a_id, b=b_id, dir=th, internal=True, station=sid, tracks=0, refs=[],
                      length=0, fixlen=STLEN.get(S["name"], 70), geo_ang=th, cands=[th]))
ids = sorted(nodes); idx = {n: i for i, n in enumerate(ids)}
# Richtungskonflikte an den Köpfen erneut auflösen; zurück in den Bahnhof zeigen ist verboten
for it in range(50):
    bad = False
    for n in ids:
        inc = [e for e in edges if n in (e["a"], e["b"])]
        seen = {}
        for e in sorted(inc, key=lambda e: (not e.get("internal"), snapdiff(e["geo_ang"], e["dir"]))):
            d = out_dir(e, n)
            forbid = set()
            if nodes[n]["kind"] == "throat" and not e.get("internal"):
                th = nodes[nodes[n]["station"]]["theta"]
                inward = th if nodes[n]["side"] == "A" else (th + 180) % 360
                forbid = {inward, (inward + 60) % 360, (inward - 60) % 360}
            if d in seen or d in forbid:
                for c in e["cands"]:
                    dc = c if e["a"] == n else (c + 180) % 360
                    if dc not in seen and dc not in forbid and snapdiff(e["geo_ang"], c) < 95:
                        e["dir"] = c; break
                bad = True
            seen[out_dir(e, n)] = e
    if not bad: break

# --- Ausgleichsrechnung
def target_len(e):
    if e.get("internal"): return e["fixlen"]
    L = CFG["scale"] * e["length"] ** CFG["len_pow"]
    mins = [CFG["min_len"].get(nodes[x]["kind"], 50) for x in (e["a"], e["b"])]
    mins = [m if nodes[x]["kind"] != "throat" else 45 for m, x in zip(mins, (e["a"], e["b"]))]
    return max(L, (mins[0] + mins[1]) / 2)
X0 = np.array([[nodes[n]["x"], nodes[n]["y"]] for n in ids])
STATION_IDS = [n for n in ids if nodes[n]["kind"] == "station"]
geo_s = CFG["scale"] * 6.0
def solve(w_len=1.0, w_perp=400.0, w_geo=0.002):
    rows, rhs, wts = [], [], []
    N = len(ids)
    for e in edges:
        a, b = idx[e["a"]], idx[e["b"]]
        th = math.radians(e["dir"]); d = np.array([math.cos(th), math.sin(th)]); nrm = np.array([-d[1], d[0]])
        wl = w_len * (200 if e.get("internal") else 1)
        for vec, val, w in ((d, target_len(e) * (1 if e.get("internal") else e.get("stretch", 1.0)), wl), (nrm, 0.0, w_perp)):
            r = np.zeros(2 * N)
            r[2 * b:2 * b + 2] += vec; r[2 * a:2 * a + 2] -= vec
            rows.append(r * math.sqrt(w)); rhs.append(val * math.sqrt(w))
    c0 = X0.mean(0)
    for i in range(N):
        if nodes[ids[i]]["kind"] == "station": continue          # Bahnhof selbst liegt zwischen den Köpfen
        for k in range(2):
            r = np.zeros(2 * N); r[2 * i + k] = 1
            rows.append(r * math.sqrt(w_geo)); rhs.append((X0[i, k] - c0[k]) * geo_s / 6.0 * 1.0 * math.sqrt(w_geo) * 0 + (X0[i, k] - c0[k]) * CFG["scale"] * 0.9 * math.sqrt(w_geo))
    sol, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    return sol.reshape(-1, 2)
for it in range(8):
    Y = solve()
    short = 0
    for e in edges:
        a, b = idx[e["a"]], idx[e["b"]]
        th = math.radians(e["dir"]); d = np.array([math.cos(th), math.sin(th)])
        proj = (Y[b] - Y[a]) @ d
        if proj < 0.8 * target_len(e):
            e["stretch"] = e.get("stretch", 1.0) * 1.3; short += 1
    if not short: break
for n in ids:
    nodes[n]["sx"], nodes[n]["sy"] = float(Y[idx[n], 0]), float(-Y[idx[n], 1])     # SVG: y nach unten
for n in STATION_IDS:
    a_, b_ = nodes[n]["throats"]
    nodes[n]["sx"] = (nodes[a_]["sx"] + nodes[b_]["sx"]) / 2; nodes[n]["sy"] = (nodes[a_]["sy"] + nodes[b_]["sy"]) / 2
# Abweichung von der Sollrichtung (Prüfgrösse)
dev = []
for e in edges:
    a, b = nodes[e["a"]], nodes[e["b"]]
    if math.hypot(b["sx"] - a["sx"], b["sy"] - a["sy"]) < 1e-6: continue
    dev.append(snapdiff(ang(b["sx"] - a["sx"], -(b["sy"] - a["sy"])), e["dir"]))
print("max. Richtungsabweichung %.1f°" % max(dev))
json.dump(dict(nodes=[nodes[n] for n in ids], edges=[{k: v for k, v in e.items() if k != "cands"} for e in edges]),
          open(f"{NAME}_layout.json", "w"), ensure_ascii=False)
