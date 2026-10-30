"""Verkettung der Bahnhofspläne einer Linien-Region (30.10.2026, Wunsch D. Eckenstein: «merken, dass die Pfeile beim
nächsten Bahnhof ankommen»; «Geometrieprüfung insbesondere bei Verkettung von Bhf müsste in den Code»).

  python3 verkettung.py <region.json> <betriebspunkte.json> [--bericht verkettung.json] [--topologie <name>_topologie.json]

Für jeden Abgang (Port) und jeden Pfeil eines Bahnhofplans wird dem Gleis in den vollständigen Regionsdaten nach aussen
gefolgt (gleicher Way bevorzugt, sonst der geradeste Ast), bis es auf ein Gleis trifft, das ein anderer Bahnhofplan
zeichnet. Dessen Schlüssel kommt als "ziel" in <b>_ports.json (Ports und Pfeile). Gleise, die keinen Nachbarplan
erreichen (Anschluss, Abstellanlage, Strecke aus der Region), bleiben ohne Ziel.

Mit --topologie werden die Strecken zwischen zwei Bahnhofsplänen nach der Verkettung nachgeführt (die Pläne gelten,
nicht die Linienachsen): fehlt eine Strecke zwischen zwei Plänen, die Personengleise austauschen, kommt sie dazu;
eine Strecke zwischen zwei Plänen ohne gemeinsames Gleis entfällt; die Gleiszahl ist die der verketteten Personengleise
(Sasslatsch: die 960 läuft durch den Plan Sagliains Sasslatsch, nicht direkt zum Autoverlad).

Prüfung (Regel V, Befunde in verkettung.json und im Log):
  V1  zwei Nachbarpläne zeigen verschieden viele Gleise zueinander (A: n Gleise nach B, B: m Gleise nach A)
  V2  ein Gleis ist im einen Plan ein Streckenabgang, im anderen ein Pfeil (Darstellung uneinheitlich)
  V3  ein Gleis kommt beim Nachbarn an, der Nachbar zeigt aber kein Gleis zurück (fehlt dort ganz)
"""
import json, math, sys, os, collections
import networkx as nx

SRC, BPF = sys.argv[1], sys.argv[2]
OUTF = sys.argv[sys.argv.index("--bericht") + 1] if "--bericht" in sys.argv else "verkettung.json"
D = json.load(open(SRC))["elements"]; BP = json.load(open(BPF))
lat0 = sum(b["lat"] for b in BP.values()) / max(len(BP), 1); KX = 111320 * math.cos(math.radians(lat0)); KY = 110540
xy = lambda la, lo: (lo * KX, la * KY)

G = nx.Graph(); P = {}; WN = {}
for w in D:
    if w["type"] != "way" or w["tags"].get("railway") != "rail" or "geometry" not in w: continue
    WN[w["id"]] = w["nodes"]
    for n, g in zip(w["nodes"], w["geometry"]): P[n] = xy(g["lat"], g["lon"])
    for a, b in zip(w["nodes"], w["nodes"][1:]): G.add_edge(a, b, way=w["id"])

PL = {}
for k in BP:
    f = f"{k}_ports.json"
    if os.path.exists(f): PL[k] = json.load(open(f))
GEZ = {k: {n for n in p.get("knoten", []) if n in P} for k, p in PL.items()}
OWNER = {}
for k, ns in GEZ.items():
    for n in ns: OWNER.setdefault(n, k)

def _proj(pt, ns):
    """Lage von pt auf der Polylinie ns: (Index des Stücks, Anteil, Abstand)."""
    best = None
    for i in range(len(ns) - 1):
        if ns[i] not in P or ns[i + 1] not in P: continue
        (ax, ay), (bx, by) = P[ns[i]], P[ns[i + 1]]; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / L2))
        d = math.dist(pt, (ax + t * dx, ay + t * dy))
        if best is None or d < best[2]: best = (i, t, d)
    return best

def _walk(own, prev, cur, L=15000.0):
    d = math.dist(P[prev], P[cur]); w0 = G[prev][cur]["way"]; draussen = False
    while d < L:
        o = OWNER.get(cur)
        if o is not None and o != own: return o
        if o == own and draussen: return None          # zurück im eigenen Plan (Schleife)
        if o is None: draussen = True                  # erst ab dem ersten Knoten ausserhalb des eigenen Plans zählt die Rückkehr
        nx_ = [m for m in G[cur] if m != prev]
        if not nx_: return None
        h0 = math.atan2(P[cur][1] - P[prev][1], P[cur][0] - P[prev][0])
        m = min(nx_, key=lambda m: (G[cur][m]["way"] != w0, abs((math.atan2(P[m][1] - P[cur][1], P[m][0] - P[cur][0]) - h0 + math.pi) % (2 * math.pi) - math.pi)))
        w0 = G[cur][m]["way"]; d += math.dist(P[cur], P[m]); prev, cur = cur, m
    return None

def ziel(own, it):
    """Nachbarplan, in dem das Gleis eines Abgangs/Pfeils als nächstes gezeichnet ist."""
    w = it.get("way"); ll = it.get("ll")
    if w is not None and w not in WN and w // 100 in WN: w = w // 100       # geteilter Way (Kreisausschnitt)
    if w in WN and ll:
        ns = WN[w]; pt = xy(*ll); pr = _proj(pt, ns)
        if pr is None or pr[2] > 40: return None
        i, t, _ = pr
        vor = None
        if it.get("aus_ll"):
            pa = _proj(xy(*it["aus_ll"]), ns)
            if pa: vor = (pa[0] + pa[1]) >= (i + t)
        if vor is None:                 # Richtung: die Seite, die nicht im eigenen Plan liegt
            vor = not (i + 1 < len(ns) and ns[i + 1] in GEZ.get(own, ()) and t < 0.99)
        prev, cur = (ns[i], ns[i + 1]) if vor else (ns[i + 1], ns[i])
        if cur not in P or prev not in P: return None
        return _walk(own, prev, cur)
    n = it.get("knoten")
    if n in G:                          # nur Knoten bekannt (Pfeil «läuft weiter»): alle Äste ausserhalb des eigenen Plans
        zs = {_walk(own, n, m) for m in G[n] if m not in GEZ.get(own, ())}
        zs.discard(None)
        return zs.pop() if len(zs) == 1 else None
    return None

BEF = []; PAAR = collections.defaultdict(lambda: collections.defaultdict(list))
for k, p in PL.items():
    _pk = {it.get("knoten") for it in p.get("ports", [])}
    _seen = set()
    for art in ("ports", "pfeile"):
        for it in p.get(art, []):
            it["ziel"] = ziel(k, it)
            # derselbe Randknoten zweimal (Pfeil auf einem Abgang, zwei Pfeile übereinander): nur einmal zählen
            it["doppelt"] = (art == "pfeile" and it.get("knoten") in _pk) or (art, it.get("knoten"), it.get("way")) in _seen
            _seen.add((art, it.get("knoten"), it.get("way")))
            if it["ziel"] and not it["doppelt"]: PAAR[tuple(sorted((k, it["ziel"])))][k].append((art, it.get("pax", False), it.get("ref")))
    json.dump(p, open(f"{k}_ports.json", "w"), ensure_ascii=False)

name = lambda k: BP.get(k, {}).get("name", k)
for (a, b), seiten in sorted(PAAR.items()):
    na, nb = len(seiten.get(a, [])), len(seiten.get(b, []))
    pa = collections.Counter(x[0] for x in seiten.get(a, [])); pb = collections.Counter(x[0] for x in seiten.get(b, []))
    if na and nb and na != nb:
        BEF.append(dict(regel="V1", a=a, b=b, text=f"{name(a)}: {na} Gleise nach {name(b)}, {name(b)}: {nb} Gleise nach {name(a)}"))
    if pa["pfeile"] and pb["ports"] and not pb["pfeile"] or pb["pfeile"] and pa["ports"] and not pa["pfeile"]:
        BEF.append(dict(regel="V2", a=a, b=b, text=f"{name(a)} – {name(b)}: Gleis im einen Plan als Pfeil, im anderen als Abgang"))
    if na and not nb or nb and not na:
        x, y = (a, b) if na else (b, a)
        BEF.append(dict(regel="V3", a=x, b=y, text=f"{name(x)}: {len(seiten[x])} Gleis(e) nach {name(y)}, dort kommt keines zurück"))
json.dump(dict(paare={f"{a}|{b}": {k: v for k, v in s.items()} for (a, b), s in PAAR.items()}, befunde=BEF),
          open(OUTF, "w"), ensure_ascii=False, indent=1)
for (a, b), s in sorted(PAAR.items()):
    print(f"  {name(a):24s} ↔ {name(b):24s} {len(s.get(a, []))}:{len(s.get(b, []))}  "
          + " / ".join(f"{name(k)}: " + ", ".join(f"{x[0][:4]}{'' if x[1] else '(N)'}" for x in v) for k, v in s.items()))
for b_ in BEF: print(b_["regel"], b_["text"])
print("Verkettung:", len(PAAR), "Nachbarpaare,", collections.Counter(b_["regel"] for b_ in BEF))

# Topologie nach der Verkettung nachführen
if "--topologie" in sys.argv:
    TF = sys.argv[sys.argv.index("--topologie") + 1]; T = json.load(open(TF))
    nid = {n["name"]: n["id"] for n in T["nodes"] if n["kind"] == "station"}
    kid = {k: nid[v["name"]] for k, v in BP.items() if v["name"] in nid and k in PL}
    NB = {n["id"]: n for n in T["nodes"]}
    pax = collections.defaultdict(lambda: collections.Counter()); refs = collections.defaultdict(set)
    for k, p in PL.items():
        for it in p.get("ports", []):
            if it.get("ziel") and it.get("pax") and not it.get("doppelt"):
                pax[tuple(sorted((k, it["ziel"])))][k] += 1
                if it.get("ref"): refs[tuple(sorted((k, it["ziel"])))].add(it["ref"])
    alt = len(T["edges"]); neu, weg, gl = 0, 0, 0
    def _paar(e):
        ka = next((k for k, i in kid.items() if i == e["a"]), None); kb = next((k for k, i in kid.items() if i == e["b"]), None)
        return tuple(sorted((ka, kb))) if ka and kb else None
    keep = []; schon = {}
    for e in T["edges"]:
        pr = _paar(e)
        if pr and not pax.get(pr):
            weg += 1; print("Topologie: Strecke", name(pr[0]), "–", name(pr[1]), "entfällt (kein gemeinsames Gleis in den Plänen)"); continue
        if pr in schon:                 # zweite Linie zwischen denselben Plänen (Sagliains – Autoverlad: 910 und 960): eine Strecke
            schon[pr]["refs"] = sorted(set(schon[pr].get("refs", [])) | set(e.get("refs", [])) | {e.get("ref")} - {None})
            weg += 1; print("Topologie: Strecke", name(pr[0]), "–", name(pr[1]), f"(Linie {e.get('ref')}) mit der parallelen zusammengelegt"); continue
        if pr:
            t_ = min(pax[pr].values()) if len(pax[pr]) == 2 else max(pax[pr].values())   # beide Seiten: die kleinere Zahl (V1 meldet den Unterschied)
            if t_ != e.get("tracks"): gl += 1; print("Topologie:", name(pr[0]), "–", name(pr[1]), "Gleise", e.get("tracks"), "->", t_)
            e["tracks"] = t_; e["refs"] = sorted(set(e.get("refs", [])) | refs[pr]) or e.get("refs", [])
            schon[pr] = e
        keep.append(e)
    da = {_paar(e) for e in keep if _paar(e)}
    _adj = collections.defaultdict(set)
    for e in keep: _adj[e["a"]].add(e["b"]); _adj[e["b"]].add(e["a"])
    def _ueber_halte(a, b):
        """a und b schon verbunden über Halte/Abzweige ohne eigenen Plan (Château-d'Oex – Rossinière über einen Halt)."""
        seen, todo = {a}, [a]
        while todo:
            x = todo.pop()
            for y in _adj[x]:
                if y == b: return True
                if y not in seen and NB.get(y, {}).get("kind") != "station": seen.add(y); todo.append(y)
        return False
    for pr, c in pax.items():
        if pr in da or pr[0] not in kid or pr[1] not in kid: continue
        if _ueber_halte(kid[pr[0]], kid[pr[1]]): continue
        a, b = NB[kid[pr[0]]], NB[kid[pr[1]]]; rs = sorted(refs[pr])
        keep.append(dict(a=a["id"], b=b["id"], ref=rs[0] if rs else None, refs=rs, tracks=min(c.values()) if len(c) == 2 else max(c.values()),
                         length=round(math.dist((a["x"], a["y"]), (b["x"], b["y"])), 1), geom=[[a["x"], a["y"]], [b["x"], b["y"]]], aus_verkettung=True))
        neu += 1; print("Topologie: Strecke", name(pr[0]), "–", name(pr[1]), "neu aus der Verkettung,", max(c.values()), "Gleis(e)")
    T["edges"] = keep
    used = {e["a"] for e in keep} | {e["b"] for e in keep}
    T["nodes"] = [n for n in T["nodes"] if n["id"] in used]
    json.dump(T, open(TF, "w"), ensure_ascii=False)
    print(f"Topologie nachgeführt: {alt} -> {len(keep)} Strecken ({neu} neu, {weg} entfallen, {gl} Gleiszahl geändert)")
