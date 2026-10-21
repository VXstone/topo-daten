"""Netz-Topologie für Linien-Regionen (Region MOB, 21.10.2026): Betriebspunkte entlang der Linien statt Achsensuche.

  python3 topologie_linien.py <region.json> <betriebspunkte.json> <konfig.json> <name>

Für jede Linie (ref) die Achse = längster Weg über die Streckengleise mit dieser Nummer (Gleise ohne Nummer übernehmen
die Nummer der Nachbarn). Betriebspunkte bis 400 m neben der Achse liegen in Achsrichtung auf der Linie; Kanten verbinden
aufeinanderfolgende Punkte. Achsenden ohne Betriebspunkt = Abgang (Ort aus region_lines.json / orte.json nach Peilung).
Betriebspunkte mit Weichen (betriebspunkte.json "weichen" > 0) sind Bahnhöfe (eigener Spurplan), sonst Halte.
Schreibt <name>_topologie.json (Format wie netz_topologie.py) und <slug>_axis.json je Bahnhof (Regel 25).
"""
import json, math, sys, os, collections, re, unicodedata
import numpy as np
import networkx as nx
from shapely.geometry import LineString, Point
from shapely.ops import substring

SRC, BPF, KONF, NAME = sys.argv[1:5]
D = json.load(open(SRC))["elements"]; BP = json.load(open(BPF)); K = json.load(open(KONF))
ORTE = json.load(open("orte.json")) if os.path.exists("orte.json") else {}
LINE_TOWNS = {k: v for k, v in (json.load(open("region_lines.json")).items() if os.path.exists("region_lines.json") else []) if not k.startswith("_")}
lats = [g["lat"] for e in D if e["type"] == "way" for g in e["geometry"]]
lons = [g["lon"] for e in D if e["type"] == "way" for g in e["geometry"]]
LAT0, LON0 = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
xy = lambda la, lo: ((lo - LON0) * KX, (la - LAT0) * KY)
to_ll = lambda x, y: [LAT0 + y / KY, LON0 + x / KX]
run = [e for e in D if e["type"] == "way" and e["tags"].get("railway") == "rail" and not e["tags"].get("service")]
P = {n: xy(g["lat"], g["lon"]) for w in run for n, g in zip(w["nodes"], w["geometry"])}
G = nx.Graph()
for w in run:
    for a, b in zip(w["nodes"], w["nodes"][1:]): G.add_edge(a, b, way=w["id"])
wref = {w["id"]: w["tags"].get("ref") for w in run}
WSP = {w["id"]: w["tags"].get("spur", "1435") for w in run}
_deg = collections.Counter(n for e in D if e["type"] == "way" and e["tags"].get("railway") == "rail" for n in (e["nodes"][0], e["nodes"][-1]))
_mid = {n for e in D if e["type"] == "way" and e["tags"].get("railway") == "rail" for n in e["nodes"][1:-1]}
_stop = {e["id"] for e in D if e["type"] == "node" and e.get("tags", {}).get("railway") == "buffer_stop"}
for _ in range(40):
    ch = False
    for w in run:
        if wref[w["id"]]: continue
        _sp = w["tags"].get("spur", "1435")          # Nummer nur innerhalb derselben Spur übernehmen (Zweisimmen: 320 neben 120/321)
        nb = collections.Counter(wref[G[n][m]["way"]] for n in (w["nodes"][0], w["nodes"][-1]) for m in G[n]
                                 if wref[G[n][m]["way"]] and WSP[G[n][m]["way"]] == _sp)
        if nb: wref[w["id"]] = nb.most_common(1)[0][0]; ch = True
    if not ch: break
WL = {w["id"]: LineString([P[n] for n in w["nodes"]]) for w in run if len(w["nodes"]) > 1}

def spine(ref):
    H = nx.Graph()
    for w in run:
        if wref[w["id"]] != ref: continue
        for a, b in zip(w["nodes"], w["nodes"][1:]): H.add_edge(a, b, w=math.dist(P[a], P[b]))
    if not H.number_of_nodes(): return None
    comp = max(nx.connected_components(H), key=lambda c: sum(math.dist(P[a], P[b]) for a, b in H.subgraph(c).edges))
    Hc = H.subgraph(comp)
    # Enden = Knoten mit einem Nachbarn; das Paar mit dem grössten Luftlinienabstand, dazwischen der kürzeste Weg
    # (nicht der längste Weg: der läuft in Bahnhöfen über Parallelgleise hin und zurück, Zweisimmen 320)
    ends = [n for n in Hc if Hc.degree(n) == 1] or list(Hc)
    a, b = max(((u, v) for i, u in enumerate(ends) for v in ends[i + 1:]), key=lambda t: math.dist(P[t[0]], P[t[1]]), default=(ends[0], ends[0]))
    p = nx.shortest_path(Hc, a, b, weight="w")
    return LineString([P[n] for n in p]) if len(p) > 1 else None

def cross_count(x, y, ux, uy, half=16):
    seg = LineString([(x - uy * half, y + ux * half), (x + uy * half, y - ux * half)]); c = 0
    for ls in WL.values():
        if ls.distance(Point(x, y)) > half + 2: continue
        it = ls.intersection(seg)
        if not it.is_empty: c += len(getattr(it, "geoms", [it]))
    return c
def tracks_at(ln, s_, half=16):
    p0, p1 = ln.interpolate(max(s_ - 5, 0)), ln.interpolate(min(s_ + 5, ln.length))
    L_ = math.dist((p0.x, p0.y), (p1.x, p1.y)) or 1
    return cross_count((p0.x + p1.x) / 2, (p0.y + p1.y) / 2, (p1.x - p0.x) / L_, (p1.y - p0.y) / L_, half)

refs = sorted({r for r in wref.values() if r})
SP = {r: spine(r) for r in refs}; SP = {r: ln for r, ln in SP.items() if ln is not None and ln.length > 150}
SPUR = {r: collections.Counter(w["tags"].get("spur", "1435") for w in run if wref[w["id"]] == r).most_common(1)[0][0] for r in SP}
print("Achsen:", {r: round(ln.length) for r, ln in SP.items()})
nodes, edges = [], []
def add(**kw): kw["id"] = len(nodes); nodes.append(kw); return kw["id"]
bpid = {}
for key, b in BP.items():
    x, y = xy(b["lat"], b["lon"])
    kind = "station" if b.get("weichen", 0) > 0 or b.get("normalspur") or key in K.get("als_bahnhof", []) else "halt"
    if b["name"] in K.get("als_halt", []): kind = "halt"
    bpid[key] = add(name=b["name"], kind=kind, x=x, y=y)
for r, ln in SP.items():
    on = []
    for key, b in BP.items():
        pt = Point(nodes[bpid[key]]["x"], nodes[bpid[key]]["y"])
        if SPUR[r] not in b.get("spuren", []): continue          # nur Betriebspunkte derselben Spur (Montreux: 100/120/121 nebeneinander)
        if ln.distance(pt) < K.get("bp_abstand_je", {}).get(b["name"], K.get("bp_abstand_m", 300)): on.append((ln.project(pt), bpid[key]))
    on.sort()
    # Achsenden ohne Betriebspunkt: Abgang
    for s_end in (0.0, ln.length):
        q = ln.interpolate(s_end)
        # Abgang nur an offenen Enden (Gleis endet ohne Prellbock und ohne Anschluss: Ausschnittrand oder Datenrand)
        _n_end = min(P, key=lambda n_: math.dist(P[n_], (q.x, q.y)))
        if _deg[_n_end] != 1 or _n_end in _mid or _n_end in _stop: continue
        if on and min(math.dist((q.x, q.y), (nodes[i_]["x"], nodes[i_]["y"])) for _, i_ in on) < K.get("abgang_ab_m", 150): continue
        inner = ln.interpolate(min(max(s_end + (300 if s_end == 0 else -300), 0), ln.length))
        bx, by = q.x - inner.x, q.y - inner.y; town, best = None, None
        for t in LINE_TOWNS.get(r, list(ORTE)):
            if t not in ORTE: continue
            tx, ty = xy(*ORTE[t])
            if math.hypot(tx - q.x, ty - q.y) < 1200: continue
            ca = (bx * (tx - q.x) + by * (ty - q.y)) / (math.hypot(bx, by) * math.hypot(tx - q.x, ty - q.y) + 1e-9)
            if best is None or ca > best: best, town = ca, t
        if not (best and best > 0.2): continue          # kein Zielort in dieser Richtung: Bahnhofsgleis am Ausschnittrand, kein Abgang
        on.append((s_end, add(name=f"Abgang {r}", kind="exit", x=q.x, y=q.y, ref=r, town=town if best and best > 0.2 else None)))
    on.sort()
    for (s0, a), (s1, b) in zip(on, on[1:]):
        if a == b or s1 - s0 < 20: continue
        sub = substring(ln, s0, s1)
        gg = [(round(x, 1), round(y, 1)) for x, y in sub.coords]
        gg = [(nodes[a]["x"], nodes[a]["y"])] + gg + [(nodes[b]["x"], nodes[b]["y"])]
        tr = sorted(tracks_at(ln, s0 + (s1 - s0) * f) for f in (0.3, 0.5, 0.7))[1]
        edges.append(dict(a=a, b=b, ref=r, refs=[r], tracks=int(max(1, min(4, tr))), length=round(s1 - s0, 1), geom=[list(p) for p in gg]))
for n in nodes:
    if n["kind"] not in ("station", "halt"): continue
    best = min(SP.items(), key=lambda t: t[1].distance(Point(n["x"], n["y"])))
    n["tracks"] = tracks_at(best[1], best[1].project(Point(n["x"], n["y"])), half=30)
used = {e["a"] for e in edges} | {e["b"] for e in edges}
BB = [min(x for x, _ in P.values()), min(y for _, y in P.values()), max(x for x, _ in P.values()), max(y for _, y in P.values())]
json.dump(dict(nodes=[n for n in nodes if n["id"] in used], edges=edges, bbox=BB), open(f"{NAME}_topologie.json", "w"), ensure_ascii=False)
print("Kanten:", len(edges), "Knoten:", collections.Counter(n["kind"] for n in nodes if n["id"] in used))
fehlt = [n["name"] for n in nodes if n["id"] not in used]
if fehlt: print("ohne Strecke:", fehlt)
# Achsen der Bahnhöfe (Regel 25): Linie nach Konfig "achse_linie" {Bahnhof: ref}, sonst die nächste Achse, ±3 km
def slug(s_):
    s_ = unicodedata.normalize("NFKD", s_).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s_).strip("_")
for n in nodes:
    if n["kind"] != "station" or n["id"] not in used: continue
    pt = Point(n["x"], n["y"])
    r = K.get("achse_linie", {}).get(n["name"]) or min(SP, key=lambda r_: SP[r_].distance(pt))
    ln = SP[r]; s_ = ln.project(pt)
    sub = substring(ln, max(s_ - 3000, 0), min(s_ + 3000, ln.length))
    json.dump(dict(ref=r, coords=[to_ll(x, y) for x, y in sub.coords]), open(slug(n["name"]) + "_axis.json", "w"))
