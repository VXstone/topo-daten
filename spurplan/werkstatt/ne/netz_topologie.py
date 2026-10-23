"""
Netz-Topologie aus OSM: Streckenachsen je Linie, Knoten (Bahnhöfe, Halte, Abzweige,
Abgänge am Rand), Kanten mit Gleiszahl.  Ausgabe: <name>_topologie.json

Aufruf: python3 netz_topologie.py region.json [name]
"""
import json, math, sys, collections
import numpy as np
import networkx as nx
from shapely.geometry import LineString, Point
from shapely.ops import linemerge

SRC = sys.argv[1] if len(sys.argv) > 1 else "region.json"
NAME = sys.argv[2] if len(sys.argv) > 2 else SRC.split(".")[0]
D = json.load(open(SRC))["elements"]
import os
ORTE = json.load(open("orte.json")) if os.path.exists("orte.json") else {}
LINE_TOWNS = {k: v for k, v in (json.load(open("region_lines.json")).items() if os.path.exists("region_lines.json") else []) if not k.startswith("_")}

lats = [g["lat"] for e in D if e["type"] == "way" for g in e["geometry"]]
lons = [g["lon"] for e in D if e["type"] == "way" for g in e["geometry"]]
LAT0, LON0 = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
xy = lambda la, lo: ((lo - LON0) * KX, (la - LAT0) * KY)
BB = (min(lons), min(lats), max(lons), max(lats))
if len(sys.argv) > 3:      # Abfrageperimeter S,W,N,E: Achsen werden dort abgeschnitten
    s_, w_, n_, e_ = map(float, sys.argv[3].split(","))
    BB = (w_, s_, e_, n_)
BX0, BY0 = xy(BB[1], BB[0]); BX1, BY1 = xy(BB[3], BB[2])

# ------------------------------------------------------------------ Streckengleise
run = [e for e in D if e["type"] == "way" and e["tags"].get("railway") == "rail"
       and not e["tags"].get("service") and e["tags"].get("gauge", "1435") == "1435"]
P = {}
for w in run:
    for n, g in zip(w["nodes"], w["geometry"]): P[n] = xy(g["lat"], g["lon"])
G = nx.Graph()
for w in run:
    for a, b in zip(w["nodes"], w["nodes"][1:]):
        G.add_edge(a, b, w=math.dist(P[a], P[b]), way=w["id"])
wref = {w["id"]: w["tags"].get("ref") for w in run}
# Gleise ohne Liniennummer: Nummer der Nachbargleise übernehmen
for _ in range(30):
    changed = False
    for w in run:
        if wref[w["id"]]: continue
        nb = collections.Counter(wref[G[n][m]["way"]] for n in (w["nodes"][0], w["nodes"][-1])
                                 for m in G[n] if wref[G[n][m]["way"]])
        if nb: wref[w["id"]] = nb.most_common(1)[0][0]; changed = True
    if not changed: break

# ------------------------------------------------------------------ Achsen je Linie
def spines_of(ref):
    H = nx.Graph()
    for w in run:
        if wref[w["id"]] != ref: continue
        for a, b in zip(w["nodes"], w["nodes"][1:]): H.add_edge(a, b, w=math.dist(P[a], P[b]))
    out = []
    covered = np.empty((0, 2))
    for comp in sorted(nx.connected_components(H), key=len, reverse=True):
        Hc = H.subgraph(comp)
        todo = set(comp)
        for _ in range(6):
            pts_left = [n for n in todo]
            if len(pts_left) < 3: break
            # längster Weg im Rest: doppelte Dijkstra-Suche (Durchmesser-Näherung)
            a = pts_left[0]
            dist = nx.single_source_dijkstra_path_length(Hc, a, weight="w")
            b = max((n for n in todo if n in dist), key=lambda n: dist[n])
            dist, path = nx.single_source_dijkstra(Hc, b, weight="w")
            c = max((n for n in todo if n in dist), key=lambda n: dist[n])
            p = path[c]
            L = dist[c]
            if L < 400: break
            line = LineString([P[n] for n in p])
            # Teil, der schon von einer früheren Achse abgedeckt ist, abschneiden
            out.append(line)
            todo -= {n for n in todo if line.distance(Point(P[n])) < 25}
    return out

refs = sorted({r for r in wref.values() if r})
SP = []      # (ref, LineString)
for r in refs:
    for ln in spines_of(r):
        # bei Doppelspur liegt die Achse auf einem Gleis: ok (Abstand 4-5 m)
        SP.append((r, ln.simplify(3)))
# Achsen, die grösstenteils auf einer längeren Achse derselben Linie liegen, entfernen
keep = []
for i, (r, ln) in enumerate(SP):
    dup = False
    for j, (r2, ln2) in enumerate(SP):
        if i != j and r2 == r and ln2.length >= ln.length:
            share = ln.intersection(ln2.buffer(20)).length / ln.length
            if share > 0.8 and (ln2.length > ln.length or j < i): dup = True
    if not dup: keep.append((r, ln))
SP = keep
# Parallel laufende Achsen derselben Linie (Vierspur aus zwei Doppelspuren) abziehen:
# kürzere Achse verliert den Teil, der neben einer längeren liegt; Reststücke > 300 m bleiben als Abzweige
SP.sort(key=lambda t: -t[1].length)
cut = []
for r, ln in SP:
    rest = ln
    for r2, ln2 in cut:
        if r2 != r: continue
        rest = rest.difference(ln2.buffer(30))
    for part in getattr(rest, "geoms", [rest]):
        if part.geom_type == "LineString" and part.length > 300: cut.append((r, part))
SP = cut
from shapely.geometry import box
_box = box(BX0, BY0, BX1, BY1)
clip = []
for r, ln in SP:
    g_ = ln.intersection(_box)
    for part in getattr(g_, "geoms", [g_]):
        if part.geom_type == "LineString" and part.length > 300: clip.append((r, part))
SP = clip
print("Achsen:", [(r, round(ln.length)) for r, ln in SP])

# ------------------------------------------------------------------ Knoten
nodes = []        # dict(name, kind, x, y)
def add_node(name, kind, x, y, **kw):
    nodes.append(dict(name=name, kind=kind, x=x, y=y, **kw)); return len(nodes) - 1
ST = [e for e in D if e["type"] == "node" and e.get("tags", {}).get("railway") in ("station", "halt")]
for e in ST:
    x, y = xy(e["lat"], e["lon"])
    if min(ln.distance(Point(x, y)) for _, ln in SP) < 150:
        add_node(e["tags"].get("name", "?").split("/")[0].strip(), e["tags"]["railway"], x, y)

# Abzweige: Achsenende auf einer anderen Achse, oder Trennpunkt zweier Achsen
def near_edge(x, y, tol=40):
    return min(x - BX0, BX1 - x, y - BY0, BY1 - y) < tol
for i, (r, ln) in enumerate(SP):
    for end in (ln.coords[0], ln.coords[-1]):
        pt = Point(end)
        if near_edge(*end):
            # Richtung: letzte 400 m der Achse nach aussen; Zielort aus Linientabelle, nicht im Perimeter
            s_end = 0 if end == ln.coords[0] else ln.length
            q = ln.interpolate(min(max(s_end + (400 if s_end == 0 else -400), 0), ln.length))
            bx, by = end[0] - q.x, end[1] - q.y
            town = None; best = None
            for t in LINE_TOWNS.get(r, list(ORTE)):
                la, lo = ORTE[t]; tx, ty = xy(la, lo)
                if math.hypot(tx - end[0], ty - end[1]) < 1200: continue
                cosang = (bx * (tx - end[0]) + by * (ty - end[1])) / (math.hypot(bx, by) * math.hypot(tx - end[0], ty - end[1]) + 1e-9)
                if best is None or cosang > best: best, town = cosang, t
            add_node(f"Abgang {r}", "exit", *end, ref=r, town=town if best and best > 0.2 else None); continue
        best = None
        for j, (r2, ln2) in enumerate(SP):
            if j == i: continue
            d = ln2.distance(pt)
            if d < 60 and (best is None or d < best[0]): best = (d, j, ln2.interpolate(ln2.project(pt)))
        if best:
            add_node("Abzweig", "junction", best[2].x, best[2].y)
        else:
            add_node("Ende", "end", *end)
# Verzweigung mitten auf der Strecke: Achsen laufen zusammen und trennen sich
for i, (r, ln) in enumerate(SP):
    for j, (r2, ln2) in enumerate(SP):
        if j <= i: continue
        inter = ln.buffer(15).intersection(ln2)
        if inter.is_empty or inter.length < 1: continue
        geoms = getattr(inter, "geoms", [inter])
        for g_ in geoms:
            for q in (g_.coords[0], g_.coords[-1]):
                if near_edge(*q): continue
                add_node("Abzweig", "junction", *q)

# Knoten zusammenfassen: Abzweige in der Nähe eines Bahnhofs gehören zum Bahnhof
RANK = {"station": 0, "halt": 1, "junction": 2, "end": 3, "exit": 4}
merged = []
for n in sorted(nodes, key=lambda n: RANK[n["kind"]]):
    rad = 350 if n["kind"] in ("junction", "end") else 120
    hit = None
    for m in merged:
        r_ = 350 if "junction" in (n["kind"], m["kind"]) else 120
        if n["kind"] == "exit" or m["kind"] == "exit": r_ = 60 if n.get("ref") != m.get("ref") else 300
        if math.dist((n["x"], n["y"]), (m["x"], m["y"])) < r_: hit = m; break
    if hit is None:
        merged.append(dict(n))
    elif hit["kind"] == "junction" and n["kind"] == "junction":
        pass
nodes = merged
for i, n in enumerate(nodes): n["id"] = i
print("Knoten:", collections.Counter(n["kind"] for n in nodes))

# ------------------------------------------------------------------ Kanten entlang der Achsen
tree_pts = [(n["id"], Point(n["x"], n["y"])) for n in nodes]
def cross_count(x, y, ux, uy, half=16):
    """Anzahl Streckengleise im Querschnitt."""
    seg = LineString([(x - uy * half, y + ux * half), (x + uy * half, y - ux * half)])
    c = 0
    for w in run:
        ls = WL[w["id"]]
        if ls.distance(Point(x, y)) > half + 2: continue
        it = ls.intersection(seg)
        if not it.is_empty: c += len(getattr(it, "geoms", [it]))
    return c
WL = {w["id"]: LineString([P[n] for n in w["nodes"]]) for w in run if len(w["nodes"]) > 1}

edges = []
NP = np.array([(n["x"], n["y"]) for n in nodes])
NTOL = np.array([160 if n["kind"] == "station" else 90 for n in nodes])
for r, ln in SP:
    # Achse abschreiten (auch Schleifen und Parallelführungen): Folge der besuchten Knoten
    visits = []          # (s, nid)
    for s_ in np.arange(0, ln.length, 10.0):
        p = ln.interpolate(s_)
        d = np.hypot(NP[:, 0] - p.x, NP[:, 1] - p.y)
        k = int(np.argmin(d - NTOL))
        if d[k] < NTOL[k]:
            if visits and visits[-1][1] == k: visits[-1][2] = s_
            else: visits.append([s_, k, s_])
    seq = [((v[0] + v[2]) / 2, v[1]) for v in visits]
    for (s0, a), (s1, b) in zip(seq, seq[1:]):
        if s1 - s0 < 30 or a == b: continue
        sub = [ln.interpolate(s0 + (s1 - s0) * f) for f in np.linspace(0, 1, 30)]
        counts = []
        for f in (0.3, 0.5, 0.7):
            s_ = s0 + (s1 - s0) * f
            p0, p1 = ln.interpolate(s_ - 5), ln.interpolate(s_ + 5)
            L_ = math.dist((p0.x, p0.y), (p1.x, p1.y)) or 1
            counts.append(cross_count((p0.x + p1.x) / 2, (p0.y + p1.y) / 2, (p1.x - p0.x) / L_, (p1.y - p0.y) / L_))
        tracks = int(max(1, min(4, sorted(counts)[1])))
        edges.append(dict(a=a, b=b, ref=r, tracks=tracks, length=s1 - s0,
                          geom=[(round(p.x, 1), round(p.y, 1)) for p in sub]))
# doppelte Kanten (gleiche Knoten, andere Linie auf gleichem Gleis) zusammenfassen
uniq = {}
for e in edges:
    k = tuple(sorted((e["a"], e["b"])))
    if k not in uniq: uniq[k] = e
    else:
        u = uniq[k]; u.setdefault("refs", set()).add(e["ref"])
        if e["length"] < u["length"]: u["length"], u["geom"] = e["length"], e["geom"]
        u["tracks"] = max(u["tracks"], e["tracks"])
edges = list(uniq.values())
for e in edges: e["refs"] = sorted(set(e.get("refs", set())) | {e["ref"]})

# Gleiszahl an den Halten (Kreuzungsstelle?): Querschnitt am Knoten
for n in nodes:
    if n["kind"] not in ("station", "halt"): continue
    best = None
    for r, ln in SP:
        d = ln.distance(Point(n["x"], n["y"]))
        if best is None or d < best[0]: best = (d, ln)
    ln = best[1]; s_ = ln.project(Point(n["x"], n["y"]))
    p0, p1 = ln.interpolate(s_ - 5), ln.interpolate(s_ + 5)
    L_ = math.dist((p0.x, p0.y), (p1.x, p1.y)) or 1
    n["tracks"] = cross_count((p0.x + p1.x) / 2, (p0.y + p1.y) / 2, (p1.x - p0.x) / L_, (p1.y - p0.y) / L_, half=30)

used = {e["a"] for e in edges} | {e["b"] for e in edges}
json.dump(dict(nodes=[n for n in nodes if n["id"] in used], edges=edges,
               bbox=[BX0, BY0, BX1, BY1]), open(f"{NAME}_topologie.json", "w"), ensure_ascii=False)
print("Kanten:", len(edges), "Knoten in Verwendung:", len(used))
for n in nodes:
    if n["id"] in used: print(f'  {n["id"]:3d} {n["kind"]:8s} {n["name"]:28s} Gleise {n.get("tracks","")}')


# ------------------------------------------------------------------ Bahnhofsachsen für die Spurpläne
# Je Bahnhof die Streckenachse, die am besten mit der Richtung der Perrongleise übereinstimmt (bei Gleichstand:
# mehr Streckengleise), Ausschnitt ±3 km.  Datei <bahnhof>_axis.json (lat/lon), wird von spurplan_schema.py gelesen.
import unicodedata, re
from shapely.ops import substring
def slug(s_):
    s_ = unicodedata.normalize("NFKD", s_).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s_).strip("_")
def to_ll(x, y): return [LAT0 + y / KY, LON0 + x / KX]
numbered = [e for e in D if e["type"] == "way" and e["tags"].get("railway") == "rail"
            and (e["tags"].get("railway:track_ref") or "").isdigit() and int(e["tags"]["railway:track_ref"]) <= 12
            and e["tags"].get("service") != "yard"]
for e in ST:
    if e["tags"].get("railway") != "station": continue
    c = np.array(xy(e["lat"], e["lon"]))
    pts = np.array([xy(g["lat"], g["lon"]) for w in numbered for g in w["geometry"]
                    if math.dist(xy(g["lat"], g["lon"]), c) < 220])
    pdir = None
    if len(pts) > 5:
        _, _, vt = np.linalg.svd(pts - pts.mean(0)); pdir = vt[0]
    best = None
    for r, ln in SP:
        if ln.distance(Point(*c)) > 160: continue
        s_ = ln.project(Point(*c))
        p0, p1 = ln.interpolate(max(s_ - 150, 0)), ln.interpolate(min(s_ + 150, ln.length))
        v = np.array([p1.x - p0.x, p1.y - p0.y]); v = v / (np.linalg.norm(v) or 1)
        align = abs(v @ pdir) if pdir is not None else 1.0
        key = (round(align, 1), ln.length)
        if best is None or key > best[0]: best = (key, r, ln, s_)
    if not best: continue
    _, r, ln, s_ = best
    # Ausschnitt ±3 km, aber nur solange sich die Achse vom Bahnhof entfernt (Schleifen/Parallelführungen abschneiden)
    def reach(sign):
        far, t = 0.0, 0.0
        while t < 3000:
            t2 = t + 50; q = s_ + sign * t2
            if q < 0 or q > ln.length: break
            p_ = ln.interpolate(q); d_ = math.dist((p_.x, p_.y), c)
            if d_ < far - 150: break
            far = max(far, d_); t = t2
        return t
    sub = substring(ln, max(s_ - reach(-1), 0), min(s_ + reach(1), ln.length))
    coords = [to_ll(x, y) for x, y in sub.coords]
    json.dump(dict(ref=r, coords=coords), open(slug(e["tags"]["name"]) + "_axis.json", "w"))
    print(f"Achse {e['tags']['name']:22s} Linie {r}  Länge {sub.length:.0f} m  Ausrichtung {best[0][0]}")
