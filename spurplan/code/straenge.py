"""Strangbild einer Linien-Region aus OSM (Strangprüfer, Wunsch D. Eckenstein 3.11.2026: «ein Linienbild bauen, um
sich über Fahrbeziehungen zu orientieren, und dann die gezeichneten Pläne damit checken»).

  python3 straenge.py <region.json> <betriebspunkte.json> <konfig.json> <name> [--topologie]

Knoten   Betriebspunkte (jede Weiche eines Streckengleises gehört zum nächsten Betriebspunkt in seinem Radius; Halte
         ohne Weiche berühren ein Gleis, das höchstens 60 m an ihnen vorbeiführt) und Abgänge (Datenende, an dem die
         Strecke in den vollständigen Daten weiterläuft, fern_enden.json).
Stränge  durchgehende Streckengleise (ohne service) zwischen zwei Knoten. Ein Gleis berührt einen Betriebspunkt nur
         an einer Weiche oder einem Halt; eine Kreuzung ohne Weiche (railway_crossing, Brücke) zählt nicht
         (Sagliains Sasslatsch: die 960 kreuzt die 910 und gehört zum Strang Autoverlad – Sasslatsch).
         Gleise zwischen denselben zwei Knoten bilden eine Strecke; Gleiszahl = Zahl der Stränge.
Fahrbeziehungen  je Betriebspunkt die Paare von Strängen, zwischen denen ein Zug über die Weichen fahren kann (alle
         Gleise im Bereich, Richtungsänderung je Schritt höchstens 50°, kein Spitzkehren).

Ausgabe <name>_straenge.json (Knoten, Strecken, Stränge mit Knoten- und Way-Listen, Fahrbeziehungen, Dreiecke).
Mit --topologie zusätzlich <name>_topologie.json im Format von topologie_linien.py (für netz_lage.py).
"""
import json, math, sys, os, collections, re, unicodedata
import networkx as nx

SRC, BPF, KONF, NAME = sys.argv[1:5]
D = json.load(open(SRC))["elements"]; BP = json.load(open(BPF)); K = json.load(open(KONF))
ORTE = json.load(open("orte.json")) if os.path.exists("orte.json") else {}
LINE_TOWNS = {k: v for k, v in (json.load(open("region_lines.json")).items() if os.path.exists("region_lines.json") else []) if not k.startswith("_")}
FERN_E = json.load(open("fern_enden.json")) if os.path.exists("fern_enden.json") else {}
# Koordinaten wie topologie_linien.py (Mitte der Daten), damit netz_lage dieselben Lagen bekommt
lats = [g["lat"] for e in D if e["type"] == "way" for g in e["geometry"]]
lons = [g["lon"] for e in D if e["type"] == "way" for g in e["geometry"]]
LAT0, LON0 = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
xy = lambda la, lo: ((lo - LON0) * KX, (la - LAT0) * KY)
ntag = {e["id"]: e.get("tags", {}) for e in D if e["type"] == "node"}
RAIL = [w for w in D if w["type"] == "way" and w["tags"].get("railway") == "rail" and len(w.get("nodes", [])) > 1]
P = {}
for w in RAIL:
    for n, g in zip(w["nodes"], w["geometry"]): P[n] = xy(g["lat"], g["lon"])
def graph(ws):
    G = nx.Graph()
    for w in ws:
        for a, b in zip(w["nodes"], w["nodes"][1:]):
            if a != b: G.add_edge(a, b, way=w["id"])
    return G
GA = graph(RAIL)                                                     # alle Gleise (Fahrbeziehungen)
MAIN = [w for w in RAIL if not w["tags"].get("service")]
GM = graph(MAIN)                                                     # Streckengleise (Stränge)
WREF = {w["id"]: w["tags"].get("ref") for w in RAIL}
SPUR = {w["id"]: w["tags"].get("spur", "1435") for w in RAIL}
def slug(s_):
    s_ = unicodedata.normalize("NFKD", s_).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s_).strip("_")

# ---- Knoten: Betriebspunkte und ihre Weichen
BPX = {k: xy(v["lat"], v["lon"]) for k, v in BP.items()}
KIND = {k: ("station" if v.get("weichen", 0) > 0 or v.get("normalspur") or v["name"] in K.get("als_bahnhof", []) else "halt") for k, v in BP.items()}
for k, v in BP.items():
    if v["name"] in K.get("als_halt", []): KIND[k] = "halt"
def kreuzung(n):
    """Kreuzung ohne Weiche: zwei Gleise teilen einen Knoten, ohne verbunden zu sein."""
    return ntag.get(n, {}).get("railway") in ("railway_crossing", "crossing") and ntag.get(n, {}).get("railway") != "switch"
ANKER = {}                                                           # Knoten -> Betriebspunkt
for n in GM:
    if kreuzung(n): continue
    # Weiche auf ein beliebiges Gleis (auch Neben-/Verbindungsgleis) oder Ende des Streckengleises an einem Nebengleis
    # (Selfranga, Sagliains Nord: zweites Streckengleis nur über Weichenverbindungen angeschlossen)
    if not (GA.degree(n) >= 3 or (GM.degree(n) == 1 and GA.degree(n) >= 2)): continue
    cov = [(math.dist(P[n], c), k) for k, c in BPX.items() if math.dist(P[n], c) <= BP[k].get("radius", 700)]
    if cov: ANKER[n] = min(cov)[1]
    elif GM.degree(n) >= 3: ANKER[n] = f"_abzweig_{n}"               # Abzweig zweier Strecken ohne Betriebspunkt (Befund S0)
# Perrongleis ohne Weiche im Bahnhof (Sagliains: die 960 läuft am Perron 4 vorbei, ihre Weichen liegen im Autoverlad):
# ein Streckengleis, das bis 15 m an einem Perron des Betriebspunkts liegt, berührt ihn dort
from shapely.geometry import LineString as _LS, Point as _Pt
for e in D:
    if e["type"] != "way" or not (e["tags"].get("railway") == "platform" or e["tags"].get("public_transport") == "platform"): continue
    pts = [xy(g["lat"], g["lon"]) for g in e.get("geometry", [])]
    if len(pts) < 2: continue
    pl = _LS(pts); cx, cy = pl.centroid.x, pl.centroid.y
    cov = [(math.dist((cx, cy), c), k) for k, c in BPX.items() if math.dist((cx, cy), c) <= BP[k].get("radius", 700)]
    if not cov: continue
    k = min(cov)[1]
    for w in MAIN:
        wl = _LS([P[n] for n in w["nodes"]])
        if wl.distance(pl) > 15: continue
        if any(ANKER.get(n) == k for n in w["nodes"]): continue      # schon über eine Weiche angeschlossen
        n = min(w["nodes"], key=lambda n: math.dist(P[n], (cx, cy)))
        if n not in ANKER and GM.degree(n) == 2: ANKER[n] = k
for k, v in BP.items():                                              # Halte und Betriebspunkte ohne Weiche am Gleis
    if any(a_ == k for a_ in ANKER.values()): continue
    c = BPX[k]; best = {}
    for w in MAIN:
        for n in w["nodes"]:
            d = math.dist(P[n], c)
            if d < 60 and (w["id"] not in best or d < best[w["id"]][0]): best[w["id"]] = (d, n)
    for d, n in best.values():
        if n not in ANKER and GM.degree(n) == 2: ANKER[n] = k
ENDE = {}                                                            # offene Enden mit Fortsetzung -> Abgang
_bb = K.get("bbox")
def _am_rand(n):
    """Datenende: Fortsetzung in den vollständigen Daten bekannt, künstlicher Randpunkt oder Ausschnittrand (bbox)."""
    if str(n) in FERN_E or -2 * 10 ** 15 < n < -10 ** 14: return True
    if not _bb: return False
    la, lo = LAT0 + P[n][1] / KY, LON0 + P[n][0] / KX
    return min(la - _bb[0], _bb[2] - la) * KY < 300 or min(lo - _bb[1], _bb[3] - lo) * KX < 300 or not (_bb[0] <= la <= _bb[2] and _bb[1] <= lo <= _bb[3])
for n in GM:
    if GM.degree(n) == 1 and n not in ANKER and ntag.get(n, {}).get("railway") != "buffer_stop" and _am_rand(n): ENDE[n] = True

# ---- Stränge
def weiter(prev, cur):
    nx_ = [m for m in GM[cur] if m != prev]
    if len(nx_) == 1: return nx_[0]
    if kreuzung(cur) and nx_:                                        # über die Kreuzung geradeaus
        h0 = math.atan2(P[cur][1] - P[prev][1], P[cur][0] - P[prev][0])
        return min(nx_, key=lambda m: abs((math.atan2(P[m][1] - P[cur][1], P[m][0] - P[cur][0]) - h0 + math.pi) % (2 * math.pi) - math.pi))
    return None
STR = []; seen = set()
for a in list(ANKER) + list(ENDE):
    for m in GM[a]:
        if (a, m) in seen: continue
        path = [a, m]; prev, cur = a, m
        while cur not in ANKER and cur not in ENDE:
            nx_ = weiter(prev, cur)
            if nx_ is None or nx_ in path: break
            path.append(nx_); prev, cur = cur, nx_
        seen.add((path[0], path[1])); seen.add((path[-1], path[-2]))
        ka = ANKER.get(path[0]) or ("_ende", path[0]); end = path[-1]
        kb = ANKER.get(end) or (("_ende", end) if end in ENDE else None)
        if kb is None: continue                                      # Stumpengleis, Prellbock
        if ka == kb: continue                                        # innerhalb eines Betriebspunkts
        if isinstance(ka, tuple) and isinstance(kb, tuple): continue # Ast läuft aus der Region und wieder hinein
        ways = [GM[x][y]["way"] for x, y in zip(path, path[1:])]
        L = sum(math.dist(P[x], P[y]) for x, y in zip(path, path[1:]))
        refs = collections.Counter(WREF[w] for w in ways if WREF[w])
        STR.append(dict(a=ka, b=kb, knoten=path, ways=sorted(set(ways)), laenge=round(L, 1),
                        ref=refs.most_common(1)[0][0] if refs else None, refs=sorted(refs), spur=SPUR[ways[0]]))

# Abgänge: offene Enden desselben Betriebspunkts nahe beieinander (Doppelspur aus der Region) = ein Abgang
EX = {}
for s in STR:
    for e_ in ("a", "b"):
        if isinstance(s[e_], tuple):
            n = s[e_][1]; other = s["b" if e_ == "a" else "a"]
            hit = next((x for x, v in EX.items() if v["bp"] == other and math.dist(P[v["knoten"][0]], P[n]) < 100), None)
            pfad = s["knoten"] if e_ == "b" else s["knoten"][::-1]        # zum Ende hin
            acc, innen = 0.0, pfad[0]
            for x_, y_ in zip(pfad[::-1], pfad[::-1][1:]):
                acc += math.dist(P[x_], P[y_]); innen = y_
                if acc > 300: break
            if hit is None:
                hit = f"_abgang_{len(EX)}"; EX[hit] = dict(bp=other, knoten=[n], refs=set(), innen=innen)
            else: EX[hit]["knoten"].append(n)
            EX[hit]["refs"] |= set(s["refs"]); s[e_] = hit
def ziel_ort(ex):
    n = ex["knoten"][0]; q = P[n]; town, best = None, None
    if str(n) in FERN_E: fx, fy = xy(*FERN_E[str(n)]); bx, by = fx - q[0], fy - q[1]
    else: bx, by = q[0] - P[ex["innen"]][0], q[1] - P[ex["innen"]][1]     # Richtung der letzten 300 m
    refs = sorted(ex["refs"]) or [None]
    for t in [t for r in refs for t in LINE_TOWNS.get(r, [])] or list(ORTE):
        if t not in ORTE: continue
        tx, ty = xy(*ORTE[t])
        if math.hypot(tx - q[0], ty - q[1]) < 1200: continue
        ca = (bx * (tx - q[0]) + by * (ty - q[1])) / (math.hypot(bx, by) * math.hypot(tx - q[0], ty - q[1]) + 1e-9)
        if best is None or ca > best: best, town = ca, t
    return town if best is not None and best > 0.2 else None

# Strecken: Stränge zwischen denselben Knoten
STRECKE = collections.defaultdict(list)
for i, s in enumerate(STR): STRECKE[tuple(sorted((str(s["a"]), str(s["b"]))))].append(i)

# ---- Fahrbeziehungen je Betriebspunkt (alle Gleise im Bereich, Abbiegen höchstens 50° je Schritt)
def _ang(u, v, w):
    a1 = math.atan2(P[v][1] - P[u][1], P[v][0] - P[u][0]); a2 = math.atan2(P[w][1] - P[v][1], P[w][0] - P[v][0])
    return abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)
def fahrbar(k, start, ziel_kanten, R):
    """Von der gerichteten Kante start=(u,v) in den Betriebspunkt k hinein zu einer der Zielkanten (x,y) hinaus."""
    c = BPX[k]; todo = [start]; seen_ = {start}
    while todo:
        u, v = todo.pop()
        for w in GA[v]:
            if w == u or (v, w) in seen_ or _ang(u, v, w) > math.radians(50): continue
            if (v, w) in ziel_kanten: return True
            if math.dist(P[w], c) > R: continue
            seen_.add((v, w)); todo.append((v, w))
    return False
FB = []
for k in BP:
    inc = [(i, e_) for i, s in enumerate(STR) for e_ in ("a", "b") if s[e_] == k]
    if len(inc) < 2: continue
    R = BP[k].get("radius", 700) + 100
    def kanten(i, e_):
        p = STR[i]["knoten"] if e_ == "a" else STR[i]["knoten"][::-1]
        return (p[1], p[0]), (p[0], p[1])                            # (hinein, hinaus)
    for x in range(len(inc)):
        for y in range(len(inc)):
            if x == y: continue
            (i, ei), (j, ej) = inc[x], inc[y]
            rein, _ = kanten(i, ei); _, raus = kanten(j, ej)
            if fahrbar(k, rein, {raus}, R):
                na = STR[i]["b" if ei == "a" else "a"]; nb = STR[j]["b" if ej == "a" else "a"]
                FB.append(dict(bp=k, von=str(na), nach=str(nb), strang_von=i, strang_nach=j))
# Fahrbeziehungen auf Knotenebene (ohne Gleisdoppel)
FBK = sorted({(f["von"], f["bp"], f["nach"]) for f in FB})
# Dreiecke: drei Betriebspunkte paarweise durch Strecken verbunden
NB = collections.defaultdict(set)
for a, b in STRECKE: NB[a].add(b); NB[b].add(a)
DREI = sorted({tuple(sorted((a, b, c))) for a in NB for b in NB[a] for c in NB[b] if c in NB[a] and len({a, b, c}) == 3})

# ---- Knotenpläne (3.11.2026, Wunsch D. Eckenstein: «Bahnhofpläne flexibel … bis zwei Gleise wirklich parallel weggehen
# und die Situation klar, ruhig, eine Strecke ist»). Pläne werden nur an ruhigen Stellen geschnitten: einem Strang ohne
# Weiche von mindestens «knoten_ruhig_m» (500 m) Länge. Liegen zwei Betriebspunkte mit eigenen Weichen näher beieinander,
# entsteht ein gemeinsamer Plan (Sagliains – Autoverlad – Sagliains Sasslatsch – Sasslatsch). Halte ohne Weiche schneiden
# nie (sie liegen am Gleis, ruhig). Höchstens «knoten_max_m» (2500 m) Ausdehnung, sonst bleibt die kürzeste Verbindung offen.
SW_EIGEN = collections.Counter(k for n, k in ANKER.items() if GA.degree(n) >= 3 and k in BP)
KNOTEN = []
if K.get("knotenplaene", True):
    _par = {}
    def _f(x):
        while _par.get(x, x) != x: x = _par[x]
        return x
    _kand = []
    for (a, b), ix in STRECKE.items():
        # nur Mehrgleiszonen auf der Achse (Sagliains – Autoverlad, 2 Gleise 305 m); ein kurzer einspuriger Schenkel ist eine
        # saubere Schnittstelle und bleibt Abgang (Dreieck Sagliains: Schenkel nach Sasslatsch, Wunsch D. Eckenstein 3.11.:
        # «Susch–Sagliains eine Achse, die Linie von Klosters verteilt sich auf zwei Winkel unter 90°»)
        if a in BP and b in BP and SW_EIGEN[a] and SW_EIGEN[b] and (len(ix) >= 2 or K.get("knoten_einspur", False)):
            L_ = min(STR[i]["laenge"] for i in ix)
            if L_ < K.get("knoten_ruhig_m", 500): _kand.append((L_, a, b))
    # Nebengleis zwischen zwei Betriebspunkten (3.11.2026, D. Eckenstein: «Betriebspunkte vergrössern, damit Nebengleise
    # nicht über Betriebspunkte hinweg gehen», Sagliains Sasslatsch – Autoverlad: zwei Ladegleise): Nebengleise (service),
    # die Weichen zweier Betriebspunkte mit eigenen Weichen verbinden, legen beide in einen Plan. Konfig «knoten_nebengleis».
    if K.get("knoten_nebengleis", True):
        GS = graph([w for w in RAIL if w["tags"].get("service")])
        for comp in nx.connected_components(GS):
            bps_ = {ANKER[n] for n in comp if n in ANKER and ANKER[n] in BP and SW_EIGEN[ANKER[n]]}
            bps_ = sorted(bps_)
            for x_, y_ in zip(bps_, bps_[1:]):
                L_ = sum(math.dist(P[a], P[b]) for a, b in GS.subgraph(comp).edges())
                # nur nahe Betriebspunkte (Belmont – Châtelard 236 m); Sagliains – Sagliains Sasslatsch (1,2 km, Tunnel-
                # einmündung) ergab einen Plan ohne Einmündung und Schenkel (6 Topologie-Befunde)
                if math.dist(BPX[x_], BPX[y_]) > K.get("knoten_nebengleis_m", 600): continue
                _kand.append((-1.0, x_, y_)); print("Nebengleis verbindet", BP[x_]["name"], "–", BP[y_]["name"], f"({L_:.0f} m Nebengleis)")
    for L_, a, b in sorted(_kand):                                   # kürzeste (unruhigste) Verbindung zuerst
        ra, rb = _f(a), _f(b)
        if ra == rb: continue
        mem = [k for k in BP if _f(k) in (ra, rb)]
        if max(math.dist(BPX[x], BPX[y]) for x in mem for y in mem) > K.get("knoten_max_m", 2500): continue
        _par[ra] = rb
    _g = collections.defaultdict(list)
    for k in BP: _g[_f(k)].append(k)
    for v in _g.values():
        if len(v) < 2: continue
        # Hauptpunkt: Personenbahnhof vor Dienststelle, dann meiste eigene Weichen
        h = max(v, key=lambda k: (not BP[k].get("dienst"), SW_EIGEN[k], KIND[k] == "station"))
        KNOTEN.append(dict(haupt=BP[h]["name"], mitglieder=[BP[k]["name"] for k in sorted(v, key=lambda k: BPX[k][0])]))
    for g_ in KNOTEN: print("Knotenplan:", " · ".join(g_["mitglieder"]), "(Hauptpunkt", g_["haupt"] + ")")
    if "--knoten" in sys.argv: json.dump(KNOTEN, open("knoten.json", "w"), ensure_ascii=False, indent=1)

name = lambda k: BP[k]["name"] if k in BP else (f"Abgang {'/'.join(sorted(EX[k]['refs']))}" if k in EX else str(k))
BEF = [dict(regel="S0", text=f"Abzweig ohne Betriebspunkt bei Knoten {n}") for n, k in ANKER.items() if str(k).startswith("_abzweig_")]
out = dict(knoten={k: dict(name=v["name"], art=KIND[k]) for k, v in BP.items()},
           abgaenge={x: dict(bp=v["bp"], knoten=v["knoten"], refs=sorted(v["refs"]), ort=ziel_ort(v)) for x, v in EX.items()},
           straenge=STR, strecken={f"{a}|{b}": dict(straenge=ix, gleise=len(ix), refs=sorted({r for i in ix for r in STR[i]["refs"]}))
                                     for (a, b), ix in STRECKE.items()},
           fahrbeziehungen=[dict(von=a, bp=b, nach=c) for a, b, c in FBK], dreiecke=DREI, befunde=BEF, knotenplaene=KNOTEN,
           # Reichweite je Betriebspunkt (3.11.2026, Montbovon: Zusammenlauf in die Einspur nach La Tine 399 m vom Punkt,
           # Weichensuche 350 m -> Plan endete vor der Weiche, sah aus wie Doppelspur): fernste Weiche, an der ein Strang beginnt
           anker_m={k: round(max(math.dist(P[n], BPX[k]) for n, k2 in ANKER.items() if k2 == k and GA.degree(n) >= 3), 1)
                    for k in BP if any(k2 == k and GA.degree(n) >= 3 for n, k2 in ANKER.items())})
json.dump(out, open(f"{NAME}_straenge.json", "w"), ensure_ascii=False, indent=1, default=str)
print(f"Strangbild: {len(STR)} Stränge, {len(STRECKE)} Strecken, {len(EX)} Abgänge, {len(FBK)} Fahrbeziehungen, {len(DREI)} Dreiecke")
for (a, b), ix in sorted(STRECKE.items(), key=lambda t: (name(t[0][0]), name(t[0][1]))):
    print(f"  {name(a):24s} – {name(b):24s} {len(ix)} Gleis(e)  Linie(n) {'/'.join(sorted({r for i in ix for r in STR[i]['refs']}))}")
for d in DREI: print("  Dreieck:", " – ".join(name(x) for x in d))
for a, b, c in FBK: print(f"  Fahrbeziehung {name(a)} → {name(b)} → {name(c)}")
for b_ in BEF: print(b_["regel"], b_["text"])

# ---- Topologie für netz_lage (Format topologie_linien.py)
if "--topologie" in sys.argv:
    nodes, idx = [], {}
    def add(key, **kw):
        kw["id"] = len(nodes); nodes.append(kw); idx[key] = kw["id"]; return kw["id"]
    for k, v in BP.items():
        x, y = BPX[k]; add(k, name=v["name"], kind=KIND[k], x=x, y=y, **({"titel": v["titel"]} if v.get("titel") else {}))
    for x_, v in EX.items():
        px, py = (sum(P[n][0] for n in v["knoten"]) / len(v["knoten"]), sum(P[n][1] for n in v["knoten"]) / len(v["knoten"]))
        rs = sorted(v["refs"]); add(x_, name=f"Abgang {rs[0] if rs else ''}", kind="exit", x=px, y=py, ref=rs[0] if rs else None,
                                     refs=rs if len(rs) > 1 else None, town=ziel_ort(v))
    edges = []
    for (a, b), ix in STRECKE.items():
        if a not in idx or b not in idx: continue
        s0 = STR[ix[0]]; pts = s0["knoten"] if str(s0["a"]) == a else s0["knoten"][::-1]
        rs = sorted({r for i in ix for r in STR[i]["refs"]})
        geom = [list(P[n]) for n in pts]; geom[0] = [nodes[idx[a]]["x"], nodes[idx[a]]["y"]] + geom[0][2:]
        geom = [[nodes[idx[a]]["x"], nodes[idx[a]]["y"]]] + [list(P[n]) for n in pts] + [[nodes[idx[b]]["x"], nodes[idx[b]]["y"]]]
        edges.append(dict(a=idx[a], b=idx[b], ref=rs[0] if rs else None, refs=rs, tracks=int(min(4, len(ix))),
                          length=round(max(STR[i]["laenge"] for i in ix), 1), geom=[[round(x, 1), round(y, 1)] for x, y in geom]))
    for n in nodes:
        if n["kind"] in ("station", "halt"):
            n["tracks"] = max([e["tracks"] for e in edges if n["id"] in (e["a"], e["b"])] or [1])
    used = {e["a"] for e in edges} | {e["b"] for e in edges}
    BB = [min(x for x, _ in P.values()), min(y for _, y in P.values()), max(x for x, _ in P.values()), max(y for _, y in P.values())]
    json.dump(dict(nodes=[n for n in nodes if n["id"] in used], edges=edges, bbox=BB), open(f"{NAME}_topologie.json", "w"), ensure_ascii=False)
    fehlt = [n["name"] for n in nodes if n["id"] not in used and n["kind"] != "exit"]
    print("Topologie aus dem Strangbild:", len(edges), "Strecken,", collections.Counter(n["kind"] for n in nodes if n["id"] in used), ("ohne Strecke: " + ", ".join(fehlt)) if fehlt else "")

# ---- Bereiche nach Strängen (--bereiche): ein Strang gehört nur den Betriebspunkten an seinen Enden. Gleise eines
# fremden Strangs (durchfahrend ohne Weiche, Sagliains Sasslatsch: 960) werden aus dem Ausschnitt eines Betriebspunkts
# entfernt; an der Schnittstelle entsteht ein Randpunkt (Abgang/Pfeil laufen dort weiter).
if "--bereiche" in sys.argv:
    INNEN = collections.defaultdict(set)                             # Strang-Innenknoten -> Betriebspunkte, denen sie gehören
    for s in STR:
        for n in s["knoten"][1:-1]: INNEN[n] |= {str(s["a"]), str(s["b"])}
    WEG_BP = collections.defaultdict(set)                            # Way -> Betriebspunkte an den Enden seiner Stränge
    for s in STR:
        for w_ in s["ways"]: WEG_BP[w_] |= {str(s["a"]), str(s["b"])}
    def _fremd_rest(w, k, ns):
        """Rest eines fremden Strangs aus lauter künstlichen Punkten (Kreisrand, Verdichtung, Randpunkt): weg
        (3.11.2026, Sagliains Sasslatsch: 2 Punkte der 960 blieben als Gleis «Linie 910 Sagliains →» im Plan)."""
        o_ = w["id"] if w["id"] in WEG_BP else w["id"] // 100
        return o_ in WEG_BP and k not in WEG_BP[o_] and all(n < -10 ** 14 for n in ns)
    cnt = [0]; geaendert = []
    for k in BP:
        f = f"{k}.json"
        if not os.path.exists(f): continue
        E = json.load(open(f)); el = E["elements"]; neu = []; weg = 0
        for w in el:
            if w["type"] != "way" or w["tags"].get("railway") != "rail" or w["tags"].get("service"):
                neu.append(w); continue
            ok = [not (n in INNEN and k not in INNEN[n]) for n in w["nodes"]]
            if all(ok):
                if _fremd_rest(w, k, w["nodes"]): weg += len(w["nodes"]); continue
                neu.append(w); continue
            weg += sum(1 for o in ok if not o)
            runs, cur = [], []
            for i, (n, g) in enumerate(zip(w["nodes"], w["geometry"])):
                if ok[i]:
                    if not cur and i > 0:                            # Randpunkt zwischen fremdem und eigenem Knoten
                        g0 = w["geometry"][i - 1]; cnt[0] += 1
                        cur.append((-1_900_000_000_000_000 - cnt[0], dict(lat=(g0["lat"] + g["lat"]) / 2, lon=(g0["lon"] + g["lon"]) / 2)))
                    cur.append((n, g))
                elif cur:
                    g1 = w["geometry"][i]; cnt[0] += 1
                    cur.append((-1_900_000_000_000_000 - cnt[0], dict(lat=(cur[-1][1]["lat"] + g1["lat"]) / 2, lon=(cur[-1][1]["lon"] + g1["lon"]) / 2)))
                    runs.append(cur); cur = []
            if cur: runs.append(cur)
            for j, r in enumerate(runs):
                if len(r) < 2 or _fremd_rest(w, k, [n for n, _ in r]): continue
                v = dict(w); v["id"] = w["id"] if j == 0 else w["id"] * 100 + 50 + j
                v["nodes"] = [n for n, _ in r]; v["geometry"] = [g for _, g in r]; neu.append(v)
        if weg:
            E["elements"] = neu; json.dump(E, open(f, "w")); geaendert.append(f"{BP[k]['name']} (-{weg} Knoten)")
    print("Bereiche nach Strängen:", ", ".join(geaendert) if geaendert else "keine fremden Stränge in den Ausschnitten")
